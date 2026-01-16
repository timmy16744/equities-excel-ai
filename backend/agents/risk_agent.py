"""Risk Management Agent with veto power."""
import json
from datetime import datetime
from typing import Any, Optional

import structlog

from backend.agents.base_agent import BaseAgent, AgentResult
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe, RiskAssessment

logger = structlog.get_logger()


class RiskAgent(BaseAgent):
    """
    Risk Management Agent.

    Has VETO POWER over all trading decisions.
    Analyzes:
    - Portfolio concentration risk
    - Position sizing
    - Correlation risk
    - Drawdown exposure
    - Leverage limits
    """

    @property
    def agent_id(self) -> str:
        return "risk"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch risk parameters and portfolio state."""
        self._logger.info("Fetching risk data")

        # Get risk parameters from settings
        max_position = await self.settings.get(
            "max_position_size", category="risk_management", default=5.0
        )
        max_sector = await self.settings.get(
            "max_sector_exposure", category="risk_management", default=20.0
        )
        max_drawdown = await self.settings.get(
            "max_drawdown", category="risk_management", default=15.0
        )
        correlation_limit = await self.settings.get(
            "correlation_limit", category="risk_management", default=0.7
        )
        max_leverage = await self.settings.get(
            "max_leverage", category="risk_management", default=1.5
        )
        portfolio_size = await self.settings.get(
            "portfolio_size", category="risk_management", default=100000.0
        )

        # Mock current portfolio state (would come from real portfolio tracking)
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "risk_parameters": {
                "max_position_size": max_position,
                "max_sector_exposure": max_sector,
                "max_drawdown": max_drawdown,
                "correlation_limit": correlation_limit,
                "max_leverage": max_leverage,
                "portfolio_size": portfolio_size,
            },
            "current_portfolio": {
                "positions": [
                    {"symbol": "SPY", "allocation": 30.0, "sector": "broad"},
                    {"symbol": "QQQ", "allocation": 20.0, "sector": "tech"},
                    {"symbol": "XLF", "allocation": 10.0, "sector": "financials"},
                ],
                "cash": 40.0,
                "current_drawdown": 2.5,
                "current_leverage": 1.0,
            },
            "market_conditions": {
                "vix": 18.5,
                "market_regime": "normal",  # "normal", "volatile", "crisis"
            },
        }

        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build risk analysis prompt."""
        params = data.get("risk_parameters", {})
        portfolio = data.get("current_portfolio", {})
        market = data.get("market_conditions", {})

        prompt = f"""Perform risk assessment for the following portfolio.

## Risk Parameters (from settings):
- Max Position Size: {params.get('max_position_size')}%
- Max Sector Exposure: {params.get('max_sector_exposure')}%
- Max Drawdown Tolerance: {params.get('max_drawdown')}%
- Correlation Limit: {params.get('correlation_limit')}
- Max Leverage: {params.get('max_leverage')}x
- Portfolio Size: ${params.get('portfolio_size'):,.0f}

## Current Portfolio State:
"""
        for pos in portfolio.get("positions", []):
            prompt += f"- {pos['symbol']}: {pos['allocation']}% ({pos['sector']})\n"

        prompt += f"""
- Cash: {portfolio.get('cash')}%
- Current Drawdown: {portfolio.get('current_drawdown')}%
- Current Leverage: {portfolio.get('current_leverage')}x

## Market Conditions:
- VIX: {market.get('vix')}
- Market Regime: {market.get('market_regime')}

## Risk Assessment Request:

1. Check all risk limits
2. Identify any violations
3. Calculate portfolio risk score
4. Determine if position changes should be VETOED

IMPORTANT: You have VETO POWER. If any risk limits are breached or
if market conditions warrant caution, you MUST recommend a veto.

Respond with JSON:
{{
    "approved": true | false,
    "veto_reason": "<reason if vetoed, null if approved>",
    "risk_score": <float 0-1>,
    "violations": ["violation1", ...],
    "warnings": ["warning1", ...],
    "recommendations": ["recommendation1", ...],
    "position_adjustments": [
        {{"symbol": "XXX", "action": "reduce" | "increase" | "close", "reason": "..."}}
    ]
}}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's response and create risk assessment."""
        try:
            parsed = self._parse_json_response(response)

            # Create risk assessment
            risk_assessment = RiskAssessment(
                approved=parsed.get("approved", True),
                veto_reason=parsed.get("veto_reason"),
                risk_score=float(parsed.get("risk_score", 0.5)),
                portfolio_risk=float(parsed.get("risk_score", 0.5)),
                recommendations=parsed.get("recommendations", []),
            )

            # Determine outlook based on risk assessment
            if not risk_assessment.approved:
                outlook = Outlook.BEARISH
                confidence = 0.9
            elif risk_assessment.risk_score > 0.7:
                outlook = Outlook.BEARISH
                confidence = risk_assessment.risk_score
            elif risk_assessment.risk_score < 0.3:
                outlook = Outlook.BULLISH
                confidence = 1 - risk_assessment.risk_score
            else:
                outlook = Outlook.NEUTRAL
                confidence = 0.5

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=outlook,
                    confidence=confidence,
                    timeframe=Timeframe.ONE_WEEK,
                    specific_predictions={
                        "approved": risk_assessment.approved,
                        "risk_score": risk_assessment.risk_score,
                        "violations": parsed.get("violations", []),
                        "position_adjustments": parsed.get("position_adjustments", []),
                    },
                ),
                reasoning=parsed.get("veto_reason") or "Risk parameters within limits",
                key_factors=parsed.get("warnings", []),
                uncertainties=["Market regime can change rapidly"],
                data_sources=["Portfolio State", "Risk Settings"],
                supporting_evidence={"risk_assessment": risk_assessment.model_dump()},
            )

        except Exception as e:
            self._logger.error("Risk assessment parse failed", error=str(e))
            # Default to cautious approval
            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=Outlook.NEUTRAL,
                    confidence=0.5,
                    timeframe=Timeframe.ONE_WEEK,
                    specific_predictions={"approved": True, "risk_score": 0.5},
                ),
                reasoning=f"Risk assessment parse error: {str(e)}",
                key_factors=["Parse error"],
                uncertainties=["Assessment may be incomplete"],
                data_sources=["Portfolio State"],
            )

    def get_system_prompt(self) -> str:
        return """You are the Risk Management Agent with VETO POWER.

Your primary duty is to PROTECT THE PORTFOLIO from excessive risk.
You have the authority to VETO any trading decisions if:
1. Position size limits are exceeded
2. Sector concentration is too high
3. Drawdown limits are breached
4. Leverage is excessive
5. Market conditions are dangerous (high VIX, crisis regime)

Be CONSERVATIVE. When in doubt, VETO.
Better to miss an opportunity than suffer catastrophic loss.

Respond ONLY with valid JSON."""

    async def assess_risk(
        self,
        proposed_trades: Optional[list[dict]] = None,
    ) -> RiskAssessment:
        """
        Assess risk and return a RiskAssessment.

        This is the primary method for the workflow to check risk.
        """
        result = await self.run()

        if result.success and result.output:
            predictions = result.output.forecast.specific_predictions or {}
            return RiskAssessment(
                approved=predictions.get("approved", True),
                veto_reason=result.output.reasoning if not predictions.get("approved") else None,
                risk_score=predictions.get("risk_score", 0.5),
                portfolio_risk=predictions.get("risk_score", 0.5),
                recommendations=result.output.key_factors,
            )

        # Default to cautious approval on error
        return RiskAssessment(
            approved=True,
            risk_score=0.5,
            portfolio_risk=0.5,
            recommendations=["Risk assessment failed - proceed with caution"],
        )
