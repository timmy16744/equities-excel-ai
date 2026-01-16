"""Execution Agent with Kelly-Optimal Position Sizing.

This agent generates actionable trade signals with mathematically-optimal position
sizing using the Kelly Criterion. It translates high-confidence forecasts into
executable orders while managing risk.
"""
import json
import math
from datetime import datetime
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.agents.base_agent import BaseAgent, AgentResult
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe
from backend.utils.alpha_schemas import (
    TradeAction,
    OrderType,
    SignalStrength,
    TradeSignal,
    KellyPosition,
    ExecutionOrder,
    ExecutionResult,
)

logger = structlog.get_logger()


class ExecutionAgent(BaseAgent):
    """
    Autonomous Execution Agent with Kelly-Optimal Position Sizing.

    Capabilities:
    - Converts aggregated forecasts into trade signals
    - Calculates Kelly-optimal position sizes
    - Applies fractional Kelly (half/quarter) for safety
    - Generates executable orders with stops and targets
    - Tracks execution outcomes for learning

    The Kelly Criterion: f* = (p * b - q) / b
    Where:
    - f* = optimal fraction of bankroll to bet
    - p = probability of winning
    - q = probability of losing (1 - p)
    - b = win/loss ratio (expected win / expected loss)
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        portfolio_value: float = 100000.0,
        max_position_pct: float = 0.25,
        kelly_fraction: float = 0.5,  # Half-Kelly for safety
    ) -> None:
        super().__init__(db, redis_client)
        self.portfolio_value = portfolio_value
        self.max_position_pct = max_position_pct
        self.kelly_fraction = kelly_fraction
        self._pending_orders: list[ExecutionOrder] = []

    @property
    def agent_id(self) -> str:
        return "execution"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch aggregated forecasts and market data for execution."""
        self._logger.info("Fetching data for execution decisions")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "forecasts": {},
            "market_prices": {},
            "volatility": {},
            "historical_accuracy": {},
        }

        # Fetch aggregated forecasts from cache
        if self.redis:
            try:
                # Get the latest aggregated insight
                cached_insight = await self.redis.get("aggregated:latest")
                if cached_insight:
                    data["aggregated_insight"] = json.loads(cached_insight)

                # Get individual agent forecasts
                agent_ids = ["macro", "technical", "sentiment", "fundamentals", "geopolitical"]
                for agent_id in agent_ids:
                    cached = await self.redis.get(f"agent:{agent_id}:output")
                    if cached:
                        data["forecasts"][agent_id] = json.loads(cached)

                # Get historical accuracy for Kelly calculations
                accuracy_data = await self.redis.get("learning:agent_accuracy")
                if accuracy_data:
                    data["historical_accuracy"] = json.loads(accuracy_data)

            except Exception as e:
                self._logger.warning("Error fetching cached data", error=str(e))

        # Fetch current market prices (for position sizing)
        from backend.data.api_clients import YFinanceClient
        yf = YFinanceClient()

        symbols = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
        for symbol in symbols:
            try:
                quote = await yf.get_quote(symbol)
                if quote:
                    data["market_prices"][symbol] = {
                        "price": quote.get("regularMarketPrice", 0),
                        "change": quote.get("regularMarketChangePercent", 0),
                        "volume": quote.get("regularMarketVolume", 0),
                    }
            except Exception as e:
                self._logger.warning(f"Failed to fetch {symbol}", error=str(e))

        # Get volatility estimates
        for symbol in symbols:
            try:
                hist = await yf.get_historical_data(symbol, period="1mo", interval="1d")
                if hist and hist.get("data"):
                    closes = [v.get("Close", 0) for v in hist["data"].values() if v]
                    if len(closes) >= 10:
                        returns = [(closes[i] - closes[i+1]) / closes[i+1]
                                 for i in range(len(closes)-1) if closes[i+1] > 0]
                        if returns:
                            data["volatility"][symbol] = {
                                "daily_vol": math.sqrt(sum(r**2 for r in returns) / len(returns)),
                                "annualized_vol": math.sqrt(252) * math.sqrt(sum(r**2 for r in returns) / len(returns)),
                            }
            except Exception:
                pass

        return data

    def calculate_kelly_position(
        self,
        symbol: str,
        win_probability: float,
        expected_win_pct: float,
        expected_loss_pct: float,
        current_price: float,
    ) -> KellyPosition:
        """
        Calculate Kelly-optimal position size.

        Args:
            symbol: Trading symbol
            win_probability: Estimated probability of profit (0-1)
            expected_win_pct: Expected return if profitable (e.g., 0.05 for 5%)
            expected_loss_pct: Expected loss if unprofitable (e.g., 0.03 for 3%)
            current_price: Current price per share

        Returns:
            KellyPosition with sizing recommendations
        """
        p = win_probability
        q = 1 - p
        b = expected_win_pct / expected_loss_pct if expected_loss_pct > 0 else 1

        # Full Kelly fraction
        full_kelly = (p * b - q) / b if b > 0 else 0
        full_kelly = max(0, min(1, full_kelly))  # Clamp to [0, 1]

        # Apply fractional Kelly for safety (default: half-Kelly)
        recommended = full_kelly * self.kelly_fraction

        # Apply maximum position constraint
        recommended = min(recommended, self.max_position_pct)

        # Calculate position sizes
        position_dollars = self.portfolio_value * recommended
        position_shares = int(position_dollars / current_price) if current_price > 0 else 0

        # Edge calculation: expected value per dollar risked
        edge = p * expected_win_pct - q * expected_loss_pct

        return KellyPosition(
            symbol=symbol,
            kelly_fraction=full_kelly,
            recommended_fraction=recommended,
            position_size_dollars=position_dollars,
            position_size_shares=position_shares,
            win_probability=p,
            win_loss_ratio=b,
            edge=edge,
        )

    def outlook_to_signal_strength(
        self,
        outlook: str,
        confidence: float,
    ) -> SignalStrength:
        """Convert outlook + confidence to signal strength."""
        if outlook == "bullish":
            if confidence >= 0.8:
                return SignalStrength.STRONG_BUY
            elif confidence >= 0.6:
                return SignalStrength.BUY
            else:
                return SignalStrength.WEAK_BUY
        elif outlook == "bearish":
            if confidence >= 0.8:
                return SignalStrength.STRONG_SELL
            elif confidence >= 0.6:
                return SignalStrength.SELL
            else:
                return SignalStrength.WEAK_SELL
        return SignalStrength.NEUTRAL

    def generate_trade_signals(
        self,
        data: dict[str, Any],
    ) -> list[TradeSignal]:
        """Generate trade signals from aggregated forecasts."""
        signals = []

        aggregated = data.get("aggregated_insight", {})
        if not aggregated:
            return signals

        outlook = aggregated.get("overall_outlook", "neutral")
        confidence = aggregated.get("confidence", 0.5)

        # Only generate signals for actionable confidence levels
        if confidence < 0.6:
            self._logger.info("Confidence too low for signals", confidence=confidence)
            return signals

        # Determine primary action and symbol
        if outlook in ["bullish", "bearish"]:
            action = TradeAction.BUY if outlook == "bullish" else TradeAction.SHORT
            strength = self.outlook_to_signal_strength(outlook, confidence)

            # Generate signal for SPY (primary market proxy)
            spy_price = data.get("market_prices", {}).get("SPY", {}).get("price", 475)
            vol = data.get("volatility", {}).get("SPY", {}).get("daily_vol", 0.01)

            # Set targets based on volatility and outlook
            atr_multiplier = 2.0  # 2x daily volatility for targets
            if outlook == "bullish":
                target_price = spy_price * (1 + vol * atr_multiplier * 5)  # 5-day target
                stop_loss = spy_price * (1 - vol * atr_multiplier * 2)  # 2-day risk
            else:
                target_price = spy_price * (1 - vol * atr_multiplier * 5)
                stop_loss = spy_price * (1 + vol * atr_multiplier * 2)

            signal = TradeSignal(
                symbol="SPY",
                action=action,
                strength=strength,
                confidence=confidence,
                target_price=round(target_price, 2),
                stop_loss=round(stop_loss, 2),
                take_profit=round(target_price, 2),
                timeframe="1week",
                reasoning=aggregated.get("resolution_reasoning", "Based on aggregated agent analysis"),
            )
            signals.append(signal)

            # Add correlated positions for diversification
            if confidence >= 0.7:
                # Add QQQ for tech exposure
                qqq_price = data.get("market_prices", {}).get("QQQ", {}).get("price", 400)
                signals.append(TradeSignal(
                    symbol="QQQ",
                    action=action,
                    strength=strength,
                    confidence=confidence * 0.9,  # Slightly lower confidence for secondary
                    target_price=round(qqq_price * (1.05 if outlook == "bullish" else 0.95), 2),
                    stop_loss=round(qqq_price * (0.97 if outlook == "bullish" else 1.03), 2),
                    timeframe="1week",
                    reasoning="Correlated position for tech sector exposure",
                ))

        return signals

    def generate_execution_orders(
        self,
        signals: list[TradeSignal],
        data: dict[str, Any],
    ) -> list[ExecutionOrder]:
        """Convert trade signals into execution orders with Kelly sizing."""
        orders = []

        historical_accuracy = data.get("historical_accuracy", {})

        for signal in signals:
            # Get historical win rate or estimate from confidence
            win_prob = historical_accuracy.get(signal.symbol, {}).get(
                "win_rate", signal.confidence
            )

            # Calculate expected returns from signal
            price = data.get("market_prices", {}).get(signal.symbol, {}).get("price", 100)
            expected_win = abs(signal.target_price - price) / price if signal.target_price else 0.05
            expected_loss = abs(price - signal.stop_loss) / price if signal.stop_loss else 0.03

            # Calculate Kelly position
            kelly = self.calculate_kelly_position(
                symbol=signal.symbol,
                win_probability=win_prob,
                expected_win_pct=expected_win,
                expected_loss_pct=expected_loss,
                current_price=price,
            )

            # Determine if approval required (large positions or low edge)
            requires_approval = (
                kelly.recommended_fraction > 0.15 or  # Large position
                kelly.edge < 0.02 or  # Low edge
                signal.strength in [SignalStrength.STRONG_BUY, SignalStrength.STRONG_SELL]  # Extreme signal
            )

            order = ExecutionOrder(
                symbol=signal.symbol,
                action=signal.action,
                quantity=kelly.position_size_shares,
                order_type=OrderType.LIMIT if signal.confidence < 0.8 else OrderType.MARKET,
                limit_price=price if signal.confidence < 0.8 else None,
                stop_price=signal.stop_loss,
                time_in_force="day",
                kelly_sizing=kelly,
                signal=signal,
                requires_approval=requires_approval,
                approval_reason="Large position size or extreme signal" if requires_approval else None,
            )
            orders.append(order)

        return orders

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build prompt for execution decision refinement."""
        signals = self.generate_trade_signals(data)
        orders = self.generate_execution_orders(signals, data)

        # Store for later use
        self._pending_orders = orders

        prompt = f"""Analyze the following trade execution plan and provide recommendations.

## Market Context
Timestamp: {data.get('timestamp')}

## Current Prices:
"""
        for symbol, price_data in data.get("market_prices", {}).items():
            prompt += f"- {symbol}: ${price_data.get('price', 'N/A')} ({price_data.get('change', 0):.2f}%)\n"

        prompt += "\n## Volatility (Annualized):\n"
        for symbol, vol_data in data.get("volatility", {}).items():
            prompt += f"- {symbol}: {vol_data.get('annualized_vol', 0)*100:.1f}%\n"

        prompt += f"""
## Aggregated Forecast:
- Outlook: {data.get('aggregated_insight', {}).get('overall_outlook', 'N/A')}
- Confidence: {data.get('aggregated_insight', {}).get('confidence', 'N/A')}

## Proposed Orders:
"""
        for order in orders:
            prompt += f"""
### {order.symbol}
- Action: {order.action.value}
- Quantity: {order.quantity} shares (${order.kelly_sizing.position_size_dollars:,.0f})
- Kelly Fraction: {order.kelly_sizing.kelly_fraction:.1%} (using {order.kelly_sizing.recommended_fraction:.1%})
- Win Probability: {order.kelly_sizing.win_probability:.1%}
- Edge: {order.kelly_sizing.edge:.2%}
- Stop Loss: ${order.stop_price or 'N/A'}
- Target: ${order.signal.target_price or 'N/A'}
- Requires Approval: {order.requires_approval}
"""

        prompt += """
## Analysis Request:
1. Evaluate the risk/reward of each proposed trade
2. Assess if Kelly sizing is appropriate given current volatility
3. Identify any execution timing concerns
4. Recommend order type (market vs limit)
5. Suggest any position adjustments

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week",
    "reasoning": "<execution analysis>",
    "key_factors": ["factor1", ...],
    "uncertainties": ["risk1", ...],
    "specific_predictions": {
        "recommended_orders": [
            {
                "symbol": "SPY",
                "action": "buy" | "sell" | "hold",
                "adjust_quantity": true | false,
                "new_quantity": <int or null>,
                "order_type": "market" | "limit",
                "urgency": "high" | "medium" | "low",
                "notes": "<reasoning>"
            }
        ],
        "overall_risk_level": "high" | "medium" | "low",
        "execution_timing": "now" | "wait_for_dip" | "scale_in"
    }
}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's execution recommendations."""
        try:
            parsed = self._parse_json_response(response)

            outlook_map = {
                "bearish": Outlook.BEARISH,
                "neutral": Outlook.NEUTRAL,
                "bullish": Outlook.BULLISH,
            }

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=outlook_map.get(parsed.get("outlook", "neutral"), Outlook.NEUTRAL),
                    confidence=float(parsed.get("confidence", 0.5)),
                    timeframe=Timeframe.ONE_WEEK,
                    specific_predictions=parsed.get("specific_predictions", {}),
                ),
                reasoning=parsed.get("reasoning", ""),
                key_factors=parsed.get("key_factors", []),
                uncertainties=parsed.get("uncertainties", []),
                data_sources=["Aggregated Forecasts", "Market Data", "Kelly Calculator"],
                supporting_evidence={
                    "pending_orders": [o.model_dump() for o in self._pending_orders],
                },
            )
        except Exception as e:
            self._logger.error("Failed to parse execution response", error=str(e))
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are an expert trade execution analyst specializing in position sizing and risk management.

Your role is to:
1. Evaluate proposed trades for risk/reward optimization
2. Verify Kelly Criterion position sizing is appropriate
3. Recommend execution strategies (market vs limit, timing, scaling)
4. Flag any concerns about position concentration or correlation risk

Key principles:
- Never risk more than Kelly suggests (fractional Kelly preferred)
- Consider current volatility regime
- Account for liquidity and slippage
- Prefer limit orders in volatile markets
- Scale into large positions

Respond ONLY with valid JSON."""

    def get_pending_orders(self) -> list[ExecutionOrder]:
        """Get the current pending orders."""
        return self._pending_orders

    async def execute_order(self, order: ExecutionOrder) -> ExecutionResult:
        """
        Execute an order (paper trading simulation).

        In production, this would connect to a broker API.
        """
        self._logger.info(
            "Executing order",
            symbol=order.symbol,
            action=order.action.value,
            quantity=order.quantity,
        )

        # Paper trading simulation
        return ExecutionResult(
            order_id=f"PAPER-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{order.symbol}",
            symbol=order.symbol,
            action=order.action,
            quantity=order.quantity,
            filled_quantity=order.quantity,  # Assume full fill in simulation
            avg_fill_price=order.limit_price or 0,
            status="filled",
            executed_at=datetime.utcnow(),
            commission=0.0,
        )
