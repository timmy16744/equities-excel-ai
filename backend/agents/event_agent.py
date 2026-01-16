"""Event-Driven Alpha Agent for Catalyst Trading.

This agent specializes in trading around predictable market events:
1. Earnings announcements (pre/post earnings drift)
2. Fed meetings (FOMC rate decisions)
3. Economic releases (CPI, NFP, GDP)
4. Options expiration (OPEX week dynamics)
5. Index rebalances (S&P 500 additions/deletions)
6. Corporate events (M&A, splits, buybacks)
"""
import json
from datetime import datetime, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.agents.base_agent import BaseAgent
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe
from backend.utils.alpha_schemas import (
    EventType,
    MarketEvent,
    EventStrategy,
    EarningsSignal,
    TradeSignal,
    TradeAction,
    SignalStrength,
)

logger = structlog.get_logger()


class EventAgent(BaseAgent):
    """
    Event-Driven Alpha Agent for Catalyst Trading.

    Exploits predictable patterns around market events:
    - Pre-earnings drift (PEAD) - stocks drift toward earnings surprise direction
    - Post-earnings announcement drift - momentum continues after surprise
    - FOMC drift - market tends to rally after rate decisions
    - OPEX pinning - stocks gravitate to max pain
    - Index inclusion effect - added stocks outperform temporarily

    Historical edges:
    - Positive earnings surprises: +2.3% avg drift over 60 days
    - FOMC meetings: +0.5% avg on announcement day
    - S&P 500 additions: +3.2% avg from announcement to inclusion
    """

    # Historical event edges (would be dynamically updated in production)
    EVENT_EDGES = {
        EventType.EARNINGS: {
            "pre_drift_days": 5,
            "post_drift_days": 20,
            "avg_surprise_impact": 0.04,
            "win_rate": 0.58,
        },
        EventType.FED_MEETING: {
            "announcement_day_bias": 0.005,
            "post_drift_days": 3,
            "win_rate": 0.62,
        },
        EventType.CPI_RELEASE: {
            "avg_vol_expansion": 1.5,
            "mean_reversion_days": 2,
            "win_rate": 0.52,
        },
        EventType.OPEX: {
            "pinning_window_days": 3,
            "max_pain_pull": 0.02,
            "win_rate": 0.55,
        },
        EventType.INDEX_REBALANCE: {
            "inclusion_edge": 0.032,
            "deletion_edge": -0.02,
            "window_days": 5,
            "win_rate": 0.68,
        },
    }

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        lookahead_days: int = 14,
    ) -> None:
        super().__init__(db, redis_client)
        self.lookahead_days = lookahead_days

    @property
    def agent_id(self) -> str:
        return "event_driven"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch upcoming events and historical patterns."""
        self._logger.info("Fetching event calendar data")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "upcoming_events": [],
            "earnings_calendar": [],
            "fed_calendar": [],
            "economic_calendar": [],
            "corporate_actions": [],
            "historical_patterns": {},
        }

        # Get upcoming earnings (simulated - would use earnings calendar API)
        data["earnings_calendar"] = await self._fetch_earnings_calendar()

        # Get Fed meeting dates
        data["fed_calendar"] = self._get_fed_calendar()

        # Get economic release calendar
        data["economic_calendar"] = self._get_economic_calendar()

        # Get options expiration dates
        data["opex_dates"] = self._get_opex_dates()

        # Compile all events
        data["upcoming_events"] = self._compile_events(data)

        # Generate event strategies
        data["strategies"] = self._generate_strategies(data)

        # Fetch current market data for context
        from backend.data.api_clients import YFinanceClient
        yf = YFinanceClient()

        data["market_context"] = {}
        try:
            spy_quote = await yf.get_quote("SPY")
            if spy_quote:
                data["market_context"]["spy_price"] = spy_quote.get("regularMarketPrice", 0)
                data["market_context"]["spy_change"] = spy_quote.get("regularMarketChangePercent", 0)
        except Exception as e:
            self._logger.warning("Failed to fetch market context", error=str(e))

        return data

    async def _fetch_earnings_calendar(self) -> list[dict]:
        """
        Fetch upcoming earnings announcements.

        In production, would connect to:
        - Yahoo Finance earnings calendar
        - Refinitiv earnings estimates
        - Alpha Vantage earnings API
        """
        # Simulated earnings calendar
        # In production, fetch from actual earnings calendar API
        upcoming = []

        # Major tech earnings (simulated based on typical Q4 reporting)
        earnings_schedule = [
            ("AAPL", 3, 0.02, 0.03),   # (symbol, days_until, estimate_revision, implied_move)
            ("MSFT", 5, 0.01, 0.04),
            ("GOOGL", 7, -0.01, 0.05),
            ("META", 8, 0.03, 0.06),
            ("NVDA", 10, 0.05, 0.08),
            ("TSLA", 12, -0.02, 0.10),
        ]

        for symbol, days, revision, implied_move in earnings_schedule:
            earnings_date = datetime.utcnow() + timedelta(days=days)

            # Simulate historical data
            import random
            random.seed(hash(symbol + "earnings"))

            signal = EarningsSignal(
                symbol=symbol,
                earnings_date=earnings_date,
                estimate_revisions_30d=revision,
                whisper_vs_consensus=random.uniform(-0.02, 0.02),
                implied_move=implied_move,
                historical_surprise_rate=random.uniform(0.55, 0.75),
                pre_earnings_drift=random.uniform(-0.02, 0.03),
                post_earnings_drift=random.uniform(-0.01, 0.02),
                recommended_strategy="long_straddle" if implied_move > 0.06 else "directional",
                confidence=random.uniform(0.5, 0.8),
            )
            upcoming.append(signal.model_dump())

        return upcoming

    def _get_fed_calendar(self) -> list[dict]:
        """Get FOMC meeting dates."""
        # 2026 FOMC meeting schedule (approximate)
        fomc_dates = [
            datetime(2026, 1, 28),
            datetime(2026, 3, 18),
            datetime(2026, 5, 6),
            datetime(2026, 6, 17),
            datetime(2026, 7, 29),
            datetime(2026, 9, 16),
            datetime(2026, 11, 4),
            datetime(2026, 12, 16),
        ]

        now = datetime.utcnow()
        upcoming = []

        for date in fomc_dates:
            days_until = (date - now).days
            if 0 <= days_until <= self.lookahead_days:
                event = MarketEvent(
                    event_type=EventType.FED_MEETING,
                    event_date=date,
                    description=f"FOMC Rate Decision - {date.strftime('%B %d')}",
                    expected_impact="high",
                    historical_avg_move=0.008,
                    historical_win_rate=0.62,
                )
                upcoming.append(event.model_dump())

        return upcoming

    def _get_economic_calendar(self) -> list[dict]:
        """Get major economic release dates."""
        now = datetime.utcnow()
        events = []

        # CPI typically released mid-month
        cpi_date = datetime(now.year, now.month, 12)
        if cpi_date < now:
            cpi_date = datetime(now.year, now.month + 1 if now.month < 12 else 1, 12)

        if 0 <= (cpi_date - now).days <= self.lookahead_days:
            events.append(MarketEvent(
                event_type=EventType.CPI_RELEASE,
                event_date=cpi_date,
                description="Consumer Price Index Release",
                expected_impact="high",
                historical_avg_move=0.012,
                historical_win_rate=0.52,
            ).model_dump())

        return events

    def _get_opex_dates(self) -> list[dict]:
        """Get options expiration dates."""
        now = datetime.utcnow()
        events = []

        # Monthly OPEX is third Friday
        # Weekly OPEX is every Friday
        for week_offset in range(3):
            opex_date = now + timedelta(days=(4 - now.weekday() + 7 * week_offset) % 7)
            if opex_date == now.date():
                opex_date = now + timedelta(days=7)

            # Check if this is monthly OPEX (third Friday)
            is_monthly = 15 <= opex_date.day <= 21

            events.append(MarketEvent(
                event_type=EventType.OPEX,
                event_date=datetime.combine(opex_date.date() if hasattr(opex_date, 'date') else opex_date, datetime.min.time()),
                description=f"{'Monthly' if is_monthly else 'Weekly'} Options Expiration",
                expected_impact="high" if is_monthly else "medium",
                historical_avg_move=0.015 if is_monthly else 0.008,
                historical_win_rate=0.55,
            ).model_dump())

        return events

    def _compile_events(self, data: dict) -> list[dict]:
        """Compile all events into unified timeline."""
        all_events = []

        # Add earnings events
        for earning in data.get("earnings_calendar", []):
            all_events.append({
                "type": EventType.EARNINGS.value,
                "date": earning.get("earnings_date"),
                "symbol": earning.get("symbol"),
                "details": earning,
            })

        # Add Fed events
        for fed_event in data.get("fed_calendar", []):
            all_events.append({
                "type": EventType.FED_MEETING.value,
                "date": fed_event.get("event_date"),
                "symbol": None,
                "details": fed_event,
            })

        # Add economic events
        for econ_event in data.get("economic_calendar", []):
            all_events.append({
                "type": econ_event.get("event_type", "economic"),
                "date": econ_event.get("event_date"),
                "symbol": None,
                "details": econ_event,
            })

        # Add OPEX events
        for opex in data.get("opex_dates", []):
            all_events.append({
                "type": EventType.OPEX.value,
                "date": opex.get("event_date"),
                "symbol": None,
                "details": opex,
            })

        # Sort by date
        all_events.sort(key=lambda x: x.get("date", ""))

        return all_events

    def _generate_strategies(self, data: dict) -> list[dict]:
        """Generate trading strategies for upcoming events."""
        strategies = []

        # Earnings strategies
        for earning in data.get("earnings_calendar", []):
            symbol = earning.get("symbol")
            revision = earning.get("estimate_revisions_30d", 0)
            implied_move = earning.get("implied_move", 0.05)
            confidence = earning.get("confidence", 0.5)

            # Pre-earnings drift strategy
            if abs(revision) > 0.01:
                direction = "long" if revision > 0 else "short"
                strategy = EventStrategy(
                    event=MarketEvent(
                        event_type=EventType.EARNINGS,
                        symbol=symbol,
                        event_date=datetime.fromisoformat(earning.get("earnings_date")) if isinstance(earning.get("earnings_date"), str) else earning.get("earnings_date"),
                        description=f"{symbol} Earnings",
                        expected_impact="high",
                    ),
                    strategy_name="pre_earnings_drift",
                    entry_timing="pre_event",
                    entry_days_before=5,
                    exit_timing="pre_event",
                    exit_days_after=-1,  # Exit day before earnings
                    position_type=direction,
                    historical_edge=self.EVENT_EDGES[EventType.EARNINGS]["avg_surprise_impact"] * (1 if direction == "long" else -1),
                    win_rate=self.EVENT_EDGES[EventType.EARNINGS]["win_rate"],
                    avg_return=abs(revision) * 2,  # Drift tends to be 2x revision
                    suggested_sizing=min(confidence * 0.1, 0.05),  # Max 5% of portfolio
                )
                strategies.append(strategy.model_dump())

            # Straddle strategy for high implied move
            if implied_move > 0.06:
                strategy = EventStrategy(
                    event=MarketEvent(
                        event_type=EventType.EARNINGS,
                        symbol=symbol,
                        event_date=datetime.fromisoformat(earning.get("earnings_date")) if isinstance(earning.get("earnings_date"), str) else earning.get("earnings_date"),
                        description=f"{symbol} Earnings Volatility Play",
                        expected_impact="high",
                    ),
                    strategy_name="earnings_straddle",
                    entry_timing="pre_event",
                    entry_days_before=3,
                    exit_timing="post_event",
                    exit_days_after=1,
                    position_type="straddle",
                    historical_edge=0.15,  # Straddles often mispriced before earnings
                    win_rate=0.55,
                    avg_return=implied_move * 0.3,  # Capture portion of move
                    suggested_sizing=0.02,
                )
                strategies.append(strategy.model_dump())

        # FOMC strategy
        for fed_event in data.get("fed_calendar", []):
            strategy = EventStrategy(
                event=MarketEvent(
                    event_type=EventType.FED_MEETING,
                    event_date=datetime.fromisoformat(fed_event.get("event_date")) if isinstance(fed_event.get("event_date"), str) else fed_event.get("event_date"),
                    description="FOMC Rate Decision",
                    expected_impact="high",
                ),
                strategy_name="fomc_drift",
                entry_timing="pre_event",
                entry_days_before=1,
                exit_timing="post_event",
                exit_days_after=2,
                position_type="long",
                historical_edge=self.EVENT_EDGES[EventType.FED_MEETING]["announcement_day_bias"],
                win_rate=self.EVENT_EDGES[EventType.FED_MEETING]["win_rate"],
                avg_return=0.008,
                suggested_sizing=0.05,
            )
            strategies.append(strategy.model_dump())

        # OPEX pinning strategy
        for opex in data.get("opex_dates", []):
            if opex.get("expected_impact") == "high":  # Monthly OPEX
                strategy = EventStrategy(
                    event=MarketEvent(
                        event_type=EventType.OPEX,
                        event_date=datetime.fromisoformat(opex.get("event_date")) if isinstance(opex.get("event_date"), str) else opex.get("event_date"),
                        description="Monthly Options Expiration",
                        expected_impact="high",
                    ),
                    strategy_name="opex_pinning",
                    entry_timing="pre_event",
                    entry_days_before=2,
                    exit_timing="at_event",
                    position_type="short_gamma",  # Sell premium expecting pinning
                    historical_edge=self.EVENT_EDGES[EventType.OPEX]["max_pain_pull"],
                    win_rate=self.EVENT_EDGES[EventType.OPEX]["win_rate"],
                    avg_return=0.01,
                    suggested_sizing=0.03,
                )
                strategies.append(strategy.model_dump())

        return strategies

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build prompt for event-driven analysis."""
        prompt = f"""Analyze upcoming market events and recommend trading strategies.

## Analysis Timestamp: {data.get('timestamp')}
## Market Context: SPY at ${data.get('market_context', {}).get('spy_price', 'N/A')} ({data.get('market_context', {}).get('spy_change', 0):+.2f}%)

## Upcoming Events Timeline:
"""
        for event in data.get("upcoming_events", [])[:10]:
            event_date = event.get("date", "")
            if isinstance(event_date, datetime):
                event_date = event_date.strftime("%Y-%m-%d")
            prompt += f"""
- [{event.get('type', 'unknown')}] {event_date}
  Symbol: {event.get('symbol', 'Market-wide')}
  Impact: {event.get('details', {}).get('expected_impact', 'unknown')}
"""

        prompt += """
## Earnings Calendar:
"""
        for earning in data.get("earnings_calendar", [])[:5]:
            prompt += f"""
### {earning.get('symbol')}
- Date: {earning.get('earnings_date')}
- Estimate Revisions (30d): {earning.get('estimate_revisions_30d', 0):+.1%}
- Implied Move: {earning.get('implied_move', 0):.1%}
- Historical Surprise Rate: {earning.get('historical_surprise_rate', 0):.0%}
- Pre-earnings Drift: {earning.get('pre_earnings_drift', 0):+.1%}
- Recommended: {earning.get('recommended_strategy', 'none')}
"""

        prompt += f"""
## Generated Strategies: {len(data.get('strategies', []))}
"""
        for strategy in data.get("strategies", [])[:5]:
            prompt += f"""
### {strategy.get('strategy_name')}
- Event: {strategy.get('event', {}).get('event_type', 'unknown')}
- Position: {strategy.get('position_type')}
- Entry: {strategy.get('entry_days_before', 0)} days before
- Exit: {strategy.get('exit_days_after', 0)} days after
- Historical Edge: {strategy.get('historical_edge', 0):.1%}
- Win Rate: {strategy.get('win_rate', 0):.0%}
- Suggested Size: {strategy.get('suggested_sizing', 0):.1%} of portfolio
"""

        prompt += """
## Analysis Request:
1. Evaluate the quality of upcoming event opportunities
2. Rank strategies by risk-adjusted expected return
3. Identify any crowded trades to avoid
4. Recommend position sizing adjustments
5. Flag any event clustering that increases risk

Consider:
- Pre-earnings drift is strongest for stocks with estimate revisions
- FOMC days have historically positive bias
- OPEX week has unique gamma dynamics
- Event clustering increases correlation risk

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week",
    "reasoning": "<event analysis>",
    "key_factors": ["factor1", ...],
    "uncertainties": ["risk1", ...],
    "specific_predictions": {
        "top_opportunities": [
            {
                "event_type": "...",
                "symbol": "...",
                "strategy": "...",
                "expected_return": <float>,
                "risk_adjusted_score": <float 0-10>,
                "timing": "entry X days before, exit Y days after"
            }
        ],
        "avoid_list": [
            {
                "symbol": "...",
                "reason": "crowded trade" | "poor risk/reward" | "..."
            }
        ],
        "portfolio_event_exposure": "low" | "medium" | "high",
        "recommended_hedges": ["hedge1", ...]
    }
}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's event-driven analysis."""
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
                    "Earnings Calendar",
                    "FOMC Schedule",
                    "Economic Calendar",
                    "Options Expiration Calendar",
                ],
                supporting_evidence={
                    "upcoming_events": len(data.get("upcoming_events", [])),
                    "strategies_generated": len(data.get("strategies", [])),
                    "earnings_in_window": len(data.get("earnings_calendar", [])),
                },
            )
        except Exception as e:
            self._logger.error("Failed to parse response", error=str(e))
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are an expert in event-driven trading strategies.

Your expertise includes:
1. Earnings momentum and drift patterns
2. FOMC meeting market dynamics
3. Economic release trading
4. Options expiration week mechanics
5. Corporate action arbitrage

Key principles:
- Pre-earnings drift is strongest with positive estimate revisions
- Post-earnings drift continues in direction of surprise
- FOMC announcements have historical upward bias
- OPEX week sees increased gamma exposure and pinning
- Index inclusions create predictable buying pressure

Risk management:
- Size positions based on historical win rates
- Avoid crowded trades (everyone knows about FOMC drift)
- Event clustering increases tail risk
- Implied vol often overstates actual moves

Respond ONLY with valid JSON."""
