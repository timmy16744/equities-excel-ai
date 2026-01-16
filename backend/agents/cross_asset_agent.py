"""Cross-Asset Arbitrage and Regime Detection Agent.

This agent monitors relationships across asset classes to:
1. Detect correlation breakdowns (mean reversion opportunities)
2. Identify regime shifts through cross-asset signals
3. Find arbitrage opportunities in related instruments
4. Monitor the equity-bond-commodity-currency nexus
"""
import json
import math
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.agents.base_agent import BaseAgent
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe
from backend.utils.alpha_schemas import (
    MarketRegime,
    CorrelationBreak,
    CrossAssetSignal,
    TradeSignal,
    TradeAction,
    SignalStrength,
)

logger = structlog.get_logger()


class CrossAssetAgent(BaseAgent):
    """
    Cross-Asset Arbitrage and Regime Detection Agent.

    Monitors key relationships:
    1. Equity-Bond: SPY vs TLT (risk-on/risk-off indicator)
    2. Equity-Volatility: SPY vs VIX (fear gauge)
    3. Equity-Dollar: SPY vs UUP (dollar strength impact)
    4. Gold-Real Rates: GLD vs TIPS (inflation expectations)
    5. Sector Rotation: XLF/XLK/XLE relative strength

    Trading strategies:
    - Mean reversion when correlations break
    - Momentum when correlations strengthen
    - Pairs trading on divergences
    - Regime-based tactical allocation
    """

    # Historical correlation baselines (would be dynamically calculated in production)
    CORRELATION_BASELINES = {
        ("SPY", "TLT"): -0.3,    # Typically negative (flight to safety)
        ("SPY", "VIX"): -0.8,    # Strongly negative
        ("SPY", "GLD"): 0.1,     # Weakly positive
        ("SPY", "UUP"): -0.2,    # Dollar strength usually negative for equities
        ("TLT", "GLD"): 0.3,     # Both benefit from uncertainty
        ("QQQ", "SPY"): 0.95,    # Highly correlated
        ("IWM", "SPY"): 0.90,    # Small caps correlated with large
        ("XLF", "XLK"): 0.65,    # Sector correlation
    }

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        correlation_window: int = 20,
        deviation_threshold: float = 0.3,
    ) -> None:
        super().__init__(db, redis_client)
        self.correlation_window = correlation_window
        self.deviation_threshold = deviation_threshold

    @property
    def agent_id(self) -> str:
        return "cross_asset"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch cross-asset data for correlation analysis."""
        self._logger.info("Fetching cross-asset data")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "price_data": {},
            "returns": {},
            "correlations": {},
            "correlation_breaks": [],
            "regime_indicators": {},
        }

        # Asset universe for cross-asset analysis
        symbols = [
            "SPY",   # S&P 500
            "QQQ",   # Nasdaq 100
            "IWM",   # Russell 2000
            "TLT",   # Long-term treasuries
            "GLD",   # Gold
            "UUP",   # Dollar index
            "VIX",   # Volatility index (if available)
            "XLF",   # Financials
            "XLK",   # Technology
            "XLE",   # Energy
        ]

        from backend.data.api_clients import YFinanceClient
        yf = YFinanceClient()

        # Fetch historical data for each symbol
        for symbol in symbols:
            try:
                hist = await yf.get_historical_data(
                    symbol,
                    period="3mo",
                    interval="1d",
                )
                if hist and hist.get("data"):
                    prices = []
                    for date, values in sorted(hist["data"].items(), reverse=True)[:60]:
                        if values and values.get("Close"):
                            prices.append({
                                "date": str(date)[:10],
                                "close": values.get("Close"),
                                "volume": values.get("Volume", 0),
                            })
                    data["price_data"][symbol] = prices

                    # Calculate returns
                    if len(prices) >= 2:
                        returns = []
                        for i in range(len(prices) - 1):
                            if prices[i+1]["close"] > 0:
                                ret = (prices[i]["close"] - prices[i+1]["close"]) / prices[i+1]["close"]
                                returns.append(ret)
                        data["returns"][symbol] = returns

            except Exception as e:
                self._logger.warning(f"Failed to fetch {symbol}", error=str(e))

        # Calculate current correlations
        data["correlations"] = self._calculate_correlations(data["returns"])

        # Detect correlation breaks
        data["correlation_breaks"] = self._detect_correlation_breaks(data["correlations"])

        # Calculate regime indicators
        data["regime_indicators"] = self._calculate_regime_indicators(data)

        # Detect current regime
        data["current_regime"] = self._detect_regime(data["regime_indicators"])

        # Generate cross-asset signals
        data["signals"] = self._generate_signals(data)

        return data

    def _calculate_correlations(
        self,
        returns: dict[str, list[float]],
    ) -> dict[tuple[str, str], float]:
        """Calculate rolling correlations between asset pairs."""
        correlations = {}

        symbols = list(returns.keys())
        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                ret1 = returns.get(sym1, [])
                ret2 = returns.get(sym2, [])

                if len(ret1) >= self.correlation_window and len(ret2) >= self.correlation_window:
                    # Use most recent window
                    r1 = ret1[:self.correlation_window]
                    r2 = ret2[:self.correlation_window]

                    corr = self._pearson_correlation(r1, r2)
                    correlations[(sym1, sym2)] = corr

        return correlations

    def _pearson_correlation(self, x: list[float], y: list[float]) -> float:
        """Calculate Pearson correlation coefficient."""
        n = min(len(x), len(y))
        if n < 2:
            return 0.0

        x = x[:n]
        y = y[:n]

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n)) / n
        std_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x) / n)
        std_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y) / n)

        if std_x == 0 or std_y == 0:
            return 0.0

        return cov / (std_x * std_y)

    def _detect_correlation_breaks(
        self,
        current_correlations: dict[tuple[str, str], float],
    ) -> list[dict]:
        """Detect significant deviations from normal correlations."""
        breaks = []

        for pair, normal_corr in self.CORRELATION_BASELINES.items():
            current_corr = current_correlations.get(pair)
            if current_corr is None:
                # Try reversed pair
                current_corr = current_correlations.get((pair[1], pair[0]))

            if current_corr is not None:
                deviation = current_corr - normal_corr

                if abs(deviation) > self.deviation_threshold:
                    # Significant correlation break detected
                    significance = abs(deviation) / self.deviation_threshold

                    # Determine trading opportunity
                    if deviation > 0:
                        # Correlation is more positive than normal
                        implication = f"{pair[0]} and {pair[1]} moving together more than usual"
                        opportunity = f"Expect reversion: consider shorting the outperformer"
                    else:
                        # Correlation is more negative than normal
                        implication = f"{pair[0]} and {pair[1]} diverging more than usual"
                        opportunity = f"Expect convergence: consider pairs trade"

                    break_data = CorrelationBreak(
                        asset_pair=pair,
                        normal_correlation=normal_corr,
                        current_correlation=current_corr,
                        deviation=deviation,
                        significance=significance,
                        regime_implication=implication,
                        trading_opportunity=opportunity,
                    )
                    breaks.append(break_data.model_dump())

        return breaks

    def _calculate_regime_indicators(self, data: dict[str, Any]) -> dict[str, Any]:
        """Calculate regime indicators from cross-asset data."""
        indicators = {}

        returns = data.get("returns", {})
        prices = data.get("price_data", {})

        # Risk-on/Risk-off indicator (SPY vs TLT relative performance)
        spy_ret = returns.get("SPY", [])
        tlt_ret = returns.get("TLT", [])
        if spy_ret and tlt_ret:
            spy_cum = sum(spy_ret[:5])
            tlt_cum = sum(tlt_ret[:5])
            indicators["risk_appetite"] = spy_cum - tlt_cum

        # Volatility regime (from price action, since VIX may not be available)
        if spy_ret:
            vol = math.sqrt(sum(r**2 for r in spy_ret[:20]) / min(20, len(spy_ret)))
            annualized_vol = vol * math.sqrt(252)
            indicators["volatility"] = annualized_vol
            indicators["vol_regime"] = (
                "high" if annualized_vol > 0.25 else
                "low" if annualized_vol < 0.12 else
                "normal"
            )

        # Dollar strength
        uup_ret = returns.get("UUP", [])
        if uup_ret:
            indicators["dollar_trend"] = sum(uup_ret[:10])

        # Gold momentum (inflation/uncertainty proxy)
        gld_ret = returns.get("GLD", [])
        if gld_ret:
            indicators["gold_momentum"] = sum(gld_ret[:10])

        # Sector rotation signals
        xlf_ret = returns.get("XLF", [])
        xlk_ret = returns.get("XLK", [])
        xle_ret = returns.get("XLE", [])

        sector_momentum = {}
        if xlf_ret:
            sector_momentum["financials"] = sum(xlf_ret[:10])
        if xlk_ret:
            sector_momentum["technology"] = sum(xlk_ret[:10])
        if xle_ret:
            sector_momentum["energy"] = sum(xle_ret[:10])

        if sector_momentum:
            indicators["sector_rotation"] = sector_momentum
            indicators["leading_sector"] = max(sector_momentum, key=sector_momentum.get)
            indicators["lagging_sector"] = min(sector_momentum, key=sector_momentum.get)

        # Breadth indicator (small caps vs large caps)
        iwm_ret = returns.get("IWM", [])
        if iwm_ret and spy_ret:
            breadth = sum(iwm_ret[:5]) - sum(spy_ret[:5])
            indicators["breadth"] = breadth
            indicators["breadth_signal"] = (
                "expanding" if breadth > 0.01 else
                "contracting" if breadth < -0.01 else
                "neutral"
            )

        return indicators

    def _detect_regime(self, indicators: dict[str, Any]) -> MarketRegime:
        """Detect current market regime from indicators."""
        risk_appetite = indicators.get("risk_appetite", 0)
        vol_regime = indicators.get("vol_regime", "normal")
        breadth = indicators.get("breadth_signal", "neutral")

        # High volatility overrides other signals
        if vol_regime == "high":
            return MarketRegime.HIGH_VOL

        # Strong risk-on with expanding breadth
        if risk_appetite > 0.02 and breadth == "expanding":
            return MarketRegime.BULL

        # Strong risk-off with contracting breadth
        if risk_appetite < -0.02 and breadth == "contracting":
            return MarketRegime.BEAR

        # Low volatility environment
        if vol_regime == "low":
            return MarketRegime.LOW_VOL

        return MarketRegime.SIDEWAYS

    def _generate_signals(self, data: dict[str, Any]) -> list[dict]:
        """Generate trading signals from cross-asset analysis."""
        signals = []
        regime = data.get("current_regime", MarketRegime.SIDEWAYS)
        indicators = data.get("regime_indicators", {})
        correlation_breaks = data.get("correlation_breaks", [])

        # Regime-based tactical allocation signals
        if regime == MarketRegime.BULL:
            signals.append(CrossAssetSignal(
                signal_type="regime_shift",
                assets_involved=["SPY", "QQQ", "IWM"],
                direction="bullish",
                confidence=0.7,
                reasoning="Bull regime detected: risk-on with expanding breadth",
                suggested_trades=[
                    TradeSignal(
                        symbol="SPY",
                        action=TradeAction.BUY,
                        strength=SignalStrength.BUY,
                        confidence=0.7,
                        timeframe="1month",
                        reasoning="Bull regime tactical allocation",
                    ),
                ],
            ).model_dump())

        elif regime == MarketRegime.BEAR:
            signals.append(CrossAssetSignal(
                signal_type="regime_shift",
                assets_involved=["SPY", "TLT", "GLD"],
                direction="bearish",
                confidence=0.7,
                reasoning="Bear regime detected: risk-off with contracting breadth",
                suggested_trades=[
                    TradeSignal(
                        symbol="TLT",
                        action=TradeAction.BUY,
                        strength=SignalStrength.BUY,
                        confidence=0.65,
                        timeframe="1month",
                        reasoning="Flight to safety - long treasuries",
                    ),
                ],
            ).model_dump())

        # Correlation break signals
        for break_info in correlation_breaks:
            pair = break_info.get("asset_pair", ("", ""))
            deviation = break_info.get("deviation", 0)
            significance = break_info.get("significance", 0)

            if significance > 1.5:  # Strong break
                if deviation > 0:
                    # Assets moving together more than usual - expect reversion
                    direction = "convergence_expected"
                else:
                    # Assets diverging more than usual - expect convergence
                    direction = "divergence_expected"

                signals.append(CrossAssetSignal(
                    signal_type="correlation_break",
                    assets_involved=list(pair),
                    direction=direction,
                    confidence=min(0.6 + (significance - 1) * 0.1, 0.85),
                    reasoning=break_info.get("trading_opportunity", ""),
                    suggested_trades=[],  # Would generate pairs trade
                ).model_dump())

        # Sector rotation signal
        if indicators.get("sector_rotation"):
            leader = indicators.get("leading_sector")
            lagger = indicators.get("lagging_sector")

            if leader and lagger:
                sector_map = {
                    "financials": "XLF",
                    "technology": "XLK",
                    "energy": "XLE",
                }

                signals.append(CrossAssetSignal(
                    signal_type="sector_rotation",
                    assets_involved=[sector_map.get(leader, ""), sector_map.get(lagger, "")],
                    direction="rotation",
                    confidence=0.6,
                    reasoning=f"Sector rotation: {leader} leading, {lagger} lagging",
                    suggested_trades=[
                        TradeSignal(
                            symbol=sector_map.get(leader, "XLK"),
                            action=TradeAction.BUY,
                            strength=SignalStrength.WEAK_BUY,
                            confidence=0.55,
                            timeframe="1week",
                            reasoning=f"Momentum in {leader} sector",
                        ),
                    ],
                ).model_dump())

        return signals

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build prompt for cross-asset analysis."""
        prompt = f"""Analyze cross-asset relationships and regime indicators.

## Analysis Timestamp: {data.get('timestamp')}
## Detected Regime: {data.get('current_regime', 'unknown')}

## Regime Indicators:
"""
        indicators = data.get("regime_indicators", {})
        for key, value in indicators.items():
            if isinstance(value, dict):
                prompt += f"- {key}:\n"
                for k, v in value.items():
                    prompt += f"  - {k}: {v:.3f if isinstance(v, float) else v}\n"
            else:
                prompt += f"- {key}: {value:.3f if isinstance(value, float) else value}\n"

        prompt += """
## Current Correlations:
"""
        for pair, corr in list(data.get("correlations", {}).items())[:10]:
            baseline = self.CORRELATION_BASELINES.get(pair, 0)
            prompt += f"- {pair[0]}/{pair[1]}: {corr:.3f} (baseline: {baseline:.2f})\n"

        prompt += """
## Correlation Breaks Detected:
"""
        for break_info in data.get("correlation_breaks", []):
            prompt += f"""
### {break_info.get('asset_pair', [])}
- Normal: {break_info.get('normal_correlation', 0):.2f}
- Current: {break_info.get('current_correlation', 0):.2f}
- Deviation: {break_info.get('deviation', 0):.2f}
- Significance: {break_info.get('significance', 0):.1f}x threshold
- Implication: {break_info.get('regime_implication', '')}
"""

        prompt += f"""
## Preliminary Signals Generated: {len(data.get('signals', []))}

## Analysis Request:
1. Validate the detected market regime
2. Assess correlation break trading opportunities
3. Evaluate sector rotation signals
4. Identify any cross-asset divergences to exploit
5. Recommend tactical allocation changes

Consider:
- Correlation breaks often mean-revert within 1-3 weeks
- Regime shifts require confirmation across multiple indicators
- Sector rotation provides short-term alpha opportunities
- Dollar strength impacts international exposure

Respond with JSON:
{{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week",
    "reasoning": "<cross-asset analysis>",
    "key_factors": ["factor1", ...],
    "uncertainties": ["risk1", ...],
    "specific_predictions": {{
        "confirmed_regime": "bull" | "bear" | "sideways" | "high_vol" | "low_vol",
        "regime_confidence": <float>,
        "correlation_trades": [
            {{
                "pair": ["SYM1", "SYM2"],
                "trade_type": "mean_reversion" | "momentum",
                "direction": "long_first_short_second" | "opposite",
                "confidence": <float>,
                "expected_holding_period": "3 days" | "1 week" | "2 weeks"
            }}
        ],
        "sector_allocation": {{
            "overweight": ["sector1", ...],
            "underweight": ["sector1", ...]
        }},
        "risk_warnings": ["warning1", ...]
    }}
}}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's cross-asset analysis."""
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
                data_sources=[
                    "Cross-Asset Correlations",
                    "Regime Indicators",
                    "Sector Rotation Metrics",
                ],
                supporting_evidence={
                    "correlation_breaks": data.get("correlation_breaks", []),
                    "regime_indicators": data.get("regime_indicators", {}),
                    "signals": data.get("signals", []),
                },
            )
        except Exception as e:
            self._logger.error("Failed to parse response", error=str(e))
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are an expert in cross-asset analysis and regime detection.

Your expertise includes:
1. Correlation analysis and mean reversion strategies
2. Market regime identification (risk-on/off, vol regimes)
3. Sector rotation timing
4. Multi-asset tactical allocation

Key principles:
- Correlation breaks often mean-revert within 2-3 weeks
- Regime shifts require confirmation from multiple indicators
- Cross-asset divergences precede equity market moves
- Dollar strength impacts multinational earnings and EM flows
- Bond-equity correlation shifts signal regime changes

Respond ONLY with valid JSON."""
