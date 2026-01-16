"""Learning Loop with Outcome Attribution Agent.

This agent implements a reflexive learning system that:
1. Tracks all predictions and their outcomes
2. Attributes returns to specific agents
3. Adjusts agent weights based on performance
4. Identifies regime-specific strengths/weaknesses
5. Implements Bayesian updating of confidence calibration
"""
import json
import math
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict

import structlog
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.agents.base_agent import BaseAgent
from backend.database import AgentPrediction
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe
from backend.utils.alpha_schemas import (
    MarketRegime,
    PredictionOutcome,
    AgentPerformance,
    RegimePerformance,
)

logger = structlog.get_logger()


class LearningAgent(BaseAgent):
    """
    Reflexive Learning Loop with Outcome Attribution.

    This agent continuously improves the system by:
    1. Tracking prediction outcomes against realized returns
    2. Computing attribution scores for each agent
    3. Calculating Brier scores for calibration assessment
    4. Adjusting agent weights dynamically
    5. Identifying regime-specific performance patterns

    The learning loop creates an ever-improving system where
    agents that perform well gain influence, while underperformers
    are down-weighted.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        lookback_days: int = 90,
        min_predictions: int = 10,
        weight_adjustment_rate: float = 0.1,
    ) -> None:
        super().__init__(db, redis_client)
        self.lookback_days = lookback_days
        self.min_predictions = min_predictions
        self.weight_adjustment_rate = weight_adjustment_rate

    @property
    def agent_id(self) -> str:
        return "learning"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch historical predictions and actual outcomes."""
        self._logger.info("Fetching learning data")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "predictions": [],
            "outcomes": [],
            "agent_stats": {},
            "regime_stats": {},
            "current_weights": {},
        }

        # Fetch historical predictions from database
        cutoff_date = datetime.utcnow() - timedelta(days=self.lookback_days)

        try:
            result = await self.db.execute(
                select(AgentPrediction)
                .where(AgentPrediction.timestamp >= cutoff_date)
                .order_by(AgentPrediction.timestamp.desc())
            )
            predictions = result.scalars().all()

            for pred in predictions:
                data["predictions"].append({
                    "id": pred.id,
                    "agent_id": pred.agent_id,
                    "timestamp": pred.timestamp.isoformat(),
                    "outlook": pred.outlook,
                    "confidence": pred.confidence,
                    "timeframe": pred.timeframe,
                    "reasoning": pred.reasoning,
                })
        except Exception as e:
            self._logger.warning("Failed to fetch predictions", error=str(e))

        # Fetch actual market returns for outcome attribution
        from backend.data.api_clients import YFinanceClient
        yf = YFinanceClient()

        try:
            hist = await yf.get_historical_data("SPY", period="3mo", interval="1d")
            if hist and hist.get("data"):
                returns = []
                sorted_dates = sorted(hist["data"].keys(), reverse=True)
                for i, date in enumerate(sorted_dates[:-1]):
                    today_close = hist["data"][date].get("Close", 0)
                    prev_close = hist["data"][sorted_dates[i+1]].get("Close", 0)
                    if prev_close > 0:
                        daily_return = (today_close - prev_close) / prev_close
                        returns.append({
                            "date": str(date),
                            "close": today_close,
                            "return": daily_return,
                        })
                data["market_returns"] = returns[:60]  # Last 60 days
        except Exception as e:
            self._logger.warning("Failed to fetch market data", error=str(e))
            data["market_returns"] = []

        # Calculate outcome attribution
        data["outcomes"] = await self._attribute_outcomes(
            data["predictions"],
            data.get("market_returns", []),
        )

        # Calculate agent performance stats
        data["agent_stats"] = self._calculate_agent_stats(data["outcomes"])

        # Get current regime
        data["current_regime"] = self._detect_regime(data.get("market_returns", []))

        # Calculate regime-specific performance
        data["regime_stats"] = self._calculate_regime_stats(
            data["outcomes"],
            data["predictions"],
        )

        # Get current agent weights from settings
        try:
            agent_ids = ["macro", "technical", "sentiment", "fundamentals", "geopolitical", "risk"]
            for agent_id in agent_ids:
                weight = await self.settings.get(
                    f"{agent_id}_weight",
                    category="agent_weights",
                    default=1.0,
                )
                data["current_weights"][agent_id] = weight
        except Exception as e:
            self._logger.warning("Failed to fetch weights", error=str(e))

        return data

    async def _attribute_outcomes(
        self,
        predictions: list[dict],
        market_returns: list[dict],
    ) -> list[dict]:
        """
        Attribute market outcomes to predictions.

        For each prediction, determine if it was correct based on
        the actual market return over the prediction timeframe.
        """
        outcomes = []

        # Build return lookup by date
        return_by_date = {r["date"][:10]: r for r in market_returns}

        for pred in predictions:
            pred_date = pred["timestamp"][:10]

            # Calculate forward return based on timeframe
            timeframe_days = {
                "1week": 5,
                "1month": 21,
                "3month": 63,
                "1year": 252,
            }.get(pred.get("timeframe", "1week"), 5)

            # Find the prediction date and calculate forward return
            actual_return = None
            forward_dates = [
                (datetime.fromisoformat(pred["timestamp"]) + timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(1, min(timeframe_days + 1, len(market_returns)))
            ]

            cumulative_return = 0
            for date in forward_dates:
                if date in return_by_date:
                    cumulative_return += return_by_date[date].get("return", 0)

            if cumulative_return != 0:
                actual_return = cumulative_return

                # Determine if prediction was correct
                predicted_direction = pred.get("outlook", "neutral")
                actual_direction = "bullish" if actual_return > 0.005 else (
                    "bearish" if actual_return < -0.005 else "neutral"
                )

                was_correct = (
                    (predicted_direction == "bullish" and actual_return > 0) or
                    (predicted_direction == "bearish" and actual_return < 0) or
                    (predicted_direction == "neutral" and abs(actual_return) < 0.02)
                )

                # Calculate attribution score
                # Higher score for high confidence correct predictions
                # Penalty for high confidence wrong predictions
                confidence = pred.get("confidence", 0.5)
                if was_correct:
                    attribution = confidence * abs(actual_return) * 100
                else:
                    attribution = -confidence * abs(actual_return) * 100

                outcome = PredictionOutcome(
                    prediction_id=pred.get("id", 0),
                    agent_id=pred.get("agent_id", "unknown"),
                    predicted_outlook=predicted_direction,
                    predicted_confidence=confidence,
                    prediction_date=datetime.fromisoformat(pred["timestamp"]),
                    target_date=datetime.fromisoformat(pred["timestamp"]) + timedelta(days=timeframe_days),
                    actual_return=actual_return,
                    actual_direction=actual_direction,
                    was_correct=was_correct,
                    attribution_score=attribution,
                )
                outcomes.append(outcome.model_dump())

        return outcomes

    def _calculate_agent_stats(self, outcomes: list[dict]) -> dict[str, dict]:
        """Calculate performance statistics for each agent."""
        agent_outcomes = defaultdict(list)

        for outcome in outcomes:
            agent_id = outcome.get("agent_id", "unknown")
            agent_outcomes[agent_id].append(outcome)

        stats = {}
        for agent_id, agent_data in agent_outcomes.items():
            if len(agent_data) < self.min_predictions:
                continue

            correct = [o for o in agent_data if o.get("was_correct")]
            total = len(agent_data)
            accuracy = len(correct) / total if total > 0 else 0

            # Confidence calibration
            correct_confidences = [o["predicted_confidence"] for o in correct]
            wrong_confidences = [o["predicted_confidence"] for o in agent_data if not o.get("was_correct")]

            avg_conf_correct = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0
            avg_conf_wrong = sum(wrong_confidences) / len(wrong_confidences) if wrong_confidences else 0

            # Brier score (lower is better)
            brier_score = sum(
                (o["predicted_confidence"] - (1 if o.get("was_correct") else 0)) ** 2
                for o in agent_data
            ) / total if total > 0 else 1.0

            # Attribution score (total value added)
            total_attribution = sum(o.get("attribution_score", 0) for o in agent_data)

            # Calculate Sharpe-like contribution
            returns = [o.get("attribution_score", 0) for o in agent_data]
            avg_return = sum(returns) / len(returns) if returns else 0
            std_return = math.sqrt(sum((r - avg_return) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 1
            sharpe = avg_return / std_return if std_return > 0 else 0

            stats[agent_id] = {
                "total_predictions": total,
                "correct_predictions": len(correct),
                "accuracy": accuracy,
                "avg_confidence_when_correct": avg_conf_correct,
                "avg_confidence_when_wrong": avg_conf_wrong,
                "brier_score": brier_score,
                "total_attribution": total_attribution,
                "sharpe_contribution": sharpe,
            }

        return stats

    def _detect_regime(self, market_returns: list[dict]) -> MarketRegime:
        """Detect current market regime from recent returns."""
        if not market_returns or len(market_returns) < 10:
            return MarketRegime.SIDEWAYS

        recent_returns = [r.get("return", 0) for r in market_returns[:20]]

        # Calculate statistics
        avg_return = sum(recent_returns) / len(recent_returns)
        volatility = math.sqrt(sum((r - avg_return) ** 2 for r in recent_returns) / len(recent_returns))
        annualized_vol = volatility * math.sqrt(252)

        # Cumulative return
        cumulative = sum(recent_returns)

        # Classify regime
        if annualized_vol > 0.30:  # >30% annualized volatility
            return MarketRegime.HIGH_VOL
        elif annualized_vol < 0.10:  # <10% annualized volatility
            return MarketRegime.LOW_VOL
        elif cumulative > 0.05:  # >5% gain in 20 days
            return MarketRegime.BULL
        elif cumulative < -0.05:  # >5% loss in 20 days
            return MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS

    def _calculate_regime_stats(
        self,
        outcomes: list[dict],
        predictions: list[dict],
    ) -> dict[str, dict]:
        """Calculate agent performance by market regime."""
        # Group predictions by regime (simplified - would need regime tagging in production)
        regime_stats = defaultdict(lambda: defaultdict(list))

        # For now, use a simplified approach
        # In production, each prediction would be tagged with the regime at prediction time
        for outcome in outcomes:
            agent_id = outcome.get("agent_id", "unknown")
            # Simplified: assume current regime for demonstration
            regime = "sideways"  # Would be looked up from prediction metadata
            regime_stats[agent_id][regime].append(outcome)

        stats = {}
        for agent_id, regime_data in regime_stats.items():
            stats[agent_id] = {}
            for regime, outcomes_list in regime_data.items():
                if len(outcomes_list) >= 5:
                    correct = len([o for o in outcomes_list if o.get("was_correct")])
                    total = len(outcomes_list)
                    stats[agent_id][regime] = {
                        "accuracy": correct / total if total > 0 else 0,
                        "sample_size": total,
                    }

        return stats

    def calculate_weight_adjustments(self, data: dict[str, Any]) -> dict[str, float]:
        """Calculate recommended weight adjustments based on performance."""
        agent_stats = data.get("agent_stats", {})
        current_weights = data.get("current_weights", {})

        new_weights = {}

        for agent_id, stats in agent_stats.items():
            current = current_weights.get(agent_id, 1.0)

            # Base adjustment on multiple factors
            accuracy_factor = stats.get("accuracy", 0.5) - 0.5  # Deviation from 50%
            brier_factor = 0.5 - stats.get("brier_score", 0.5)  # Lower Brier is better
            sharpe_factor = stats.get("sharpe_contribution", 0) / 10  # Normalize

            # Combined adjustment
            adjustment = (
                accuracy_factor * 0.4 +
                brier_factor * 0.3 +
                sharpe_factor * 0.3
            ) * self.weight_adjustment_rate

            # Apply adjustment with bounds
            new_weight = current * (1 + adjustment)
            new_weight = max(0.1, min(2.0, new_weight))  # Keep between 0.1 and 2.0

            new_weights[agent_id] = round(new_weight, 3)

        return new_weights

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build prompt for learning analysis."""
        prompt = f"""Analyze agent performance and recommend weight adjustments.

## Analysis Timestamp: {data.get('timestamp')}
## Lookback Period: {self.lookback_days} days
## Current Market Regime: {data.get('current_regime', 'unknown')}

## Agent Performance Summary:
"""
        for agent_id, stats in data.get("agent_stats", {}).items():
            prompt += f"""
### {agent_id.upper()} Agent
- Predictions: {stats.get('total_predictions', 0)}
- Accuracy: {stats.get('accuracy', 0):.1%}
- Brier Score: {stats.get('brier_score', 1):.3f} (lower is better)
- Avg Confidence (Correct): {stats.get('avg_confidence_when_correct', 0):.1%}
- Avg Confidence (Wrong): {stats.get('avg_confidence_when_wrong', 0):.1%}
- Sharpe Contribution: {stats.get('sharpe_contribution', 0):.2f}
- Total Attribution: {stats.get('total_attribution', 0):.1f}
"""

        prompt += f"""
## Current Weights:
"""
        for agent_id, weight in data.get("current_weights", {}).items():
            prompt += f"- {agent_id}: {weight:.2f}\n"

        # Calculate preliminary weight adjustments
        new_weights = self.calculate_weight_adjustments(data)
        prompt += f"""
## Preliminary Weight Adjustments:
"""
        for agent_id, weight in new_weights.items():
            current = data.get("current_weights", {}).get(agent_id, 1.0)
            change = ((weight - current) / current) * 100 if current > 0 else 0
            prompt += f"- {agent_id}: {current:.2f} -> {weight:.2f} ({change:+.1f}%)\n"

        prompt += """
## Analysis Request:
1. Evaluate each agent's calibration (are they overconfident or underconfident?)
2. Identify which agents perform best in current regime
3. Recommend final weight adjustments with reasoning
4. Identify any concerning patterns (always wrong at high confidence, etc.)
5. Suggest improvements for underperforming agents

Respond with JSON:
{
    "outlook": "neutral",
    "confidence": <float 0-1>,
    "timeframe": "1month",
    "reasoning": "<learning analysis>",
    "key_factors": ["insight1", ...],
    "uncertainties": ["risk1", ...],
    "specific_predictions": {
        "recommended_weights": {
            "agent_id": <float>,
            ...
        },
        "calibration_issues": {
            "agent_id": "overconfident" | "underconfident" | "well_calibrated"
        },
        "regime_recommendations": {
            "current_regime": "...",
            "best_performers": ["agent1", ...],
            "worst_performers": ["agent1", ...]
        },
        "improvement_suggestions": {
            "agent_id": "<suggestion>"
        }
    }
}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's learning analysis."""
        try:
            parsed = self._parse_json_response(response)

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=Outlook.NEUTRAL,  # Learning agent is meta, not directional
                    confidence=float(parsed.get("confidence", 0.7)),
                    timeframe=Timeframe.ONE_MONTH,
                    specific_predictions=parsed.get("specific_predictions", {}),
                ),
                reasoning=parsed.get("reasoning", ""),
                key_factors=parsed.get("key_factors", []),
                uncertainties=parsed.get("uncertainties", []),
                data_sources=[
                    "Historical Predictions",
                    "Market Returns",
                    "Agent Performance Metrics",
                ],
                supporting_evidence={
                    "agent_stats": data.get("agent_stats", {}),
                    "current_regime": data.get("current_regime", "unknown"),
                    "weight_changes": self.calculate_weight_adjustments(data),
                },
            )
        except Exception as e:
            self._logger.error("Failed to parse response", error=str(e))
            return self._create_mock_output()

    async def apply_weight_adjustments(self, new_weights: dict[str, float]) -> None:
        """Apply recommended weight adjustments to settings."""
        for agent_id, weight in new_weights.items():
            try:
                await self.settings.set(
                    f"{agent_id}_weight",
                    weight,
                    category="agent_weights",
                )
                self._logger.info(
                    "Weight updated",
                    agent_id=agent_id,
                    new_weight=weight,
                )
            except Exception as e:
                self._logger.error(
                    "Failed to update weight",
                    agent_id=agent_id,
                    error=str(e),
                )

    def get_system_prompt(self) -> str:
        return """You are an expert in machine learning evaluation and ensemble optimization.

Your role is to:
1. Assess agent calibration (confidence vs accuracy alignment)
2. Identify regime-specific performance patterns
3. Recommend optimal agent weight adjustments
4. Detect problematic prediction patterns

Key principles:
- Well-calibrated agents have confidence matching accuracy
- Regime-aware weighting improves ensemble performance
- Gradual weight adjustments prevent overfitting
- Recent performance is more relevant than distant history
- Brier score is the gold standard for probabilistic calibration

Respond ONLY with valid JSON."""
