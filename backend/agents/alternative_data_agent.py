"""Alternative Data Alpha Discovery Agent.

This agent analyzes non-traditional data sources to identify alpha opportunities
that may not be visible in standard market data:
- Social media sentiment and mention velocity
- Unusual options activity and flow
- Insider trading patterns
- Web traffic and app download trends
- Satellite imagery proxies (retail parking lots, shipping)
"""
import json
import math
from datetime import datetime, timedelta
from typing import Any, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.agents.base_agent import BaseAgent
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe
from backend.utils.alpha_schemas import (
    SignalStrength,
    SocialSentiment,
    OptionsFlow,
    InsiderTransaction,
    AlternativeSignal,
)

logger = structlog.get_logger()


class AlternativeDataAgent(BaseAgent):
    """
    Alternative Data Alpha Discovery Agent.

    Analyzes unconventional data sources:
    1. Social Sentiment: Reddit (WSB, investing), Twitter, StockTwits
    2. Options Flow: Unusual volume, sweeps, dark pool prints
    3. Insider Activity: Cluster buys, Form 4 filings
    4. Web/App Metrics: Traffic trends, download velocity
    5. Supply Chain: Shipping data, inventory signals

    These signals often lead traditional metrics by days or weeks.
    """

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        sentiment_threshold: float = 0.3,
        unusual_volume_multiplier: float = 3.0,
    ) -> None:
        super().__init__(db, redis_client)
        self.sentiment_threshold = sentiment_threshold
        self.unusual_volume_multiplier = unusual_volume_multiplier

    @property
    def agent_id(self) -> str:
        return "alternative_data"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch alternative data from various sources."""
        self._logger.info("Fetching alternative data")

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "social_sentiment": [],
            "options_flow": [],
            "insider_activity": [],
            "web_metrics": {},
            "supply_chain": {},
        }

        # Fetch social sentiment data
        sentiment_data = await self._fetch_social_sentiment()
        data["social_sentiment"] = sentiment_data

        # Fetch options flow data
        options_data = await self._fetch_options_flow()
        data["options_flow"] = options_data

        # Fetch insider transactions
        insider_data = await self._fetch_insider_activity()
        data["insider_activity"] = insider_data

        # Aggregate signals
        data["aggregated_signals"] = self._aggregate_signals(data)

        return data

    async def _fetch_social_sentiment(self) -> list[dict]:
        """
        Fetch social media sentiment.

        In production, would connect to:
        - Reddit API (r/wallstreetbets, r/investing, r/stocks)
        - Twitter API (cashtags, financial influencers)
        - StockTwits API
        """
        # Simulated data structure for demonstration
        # In production, replace with actual API calls
        symbols = ["SPY", "AAPL", "NVDA", "TSLA", "AMD"]
        sentiment_data = []

        for symbol in symbols:
            # Simulate sentiment calculation
            import random
            random.seed(hash(symbol + datetime.utcnow().strftime("%Y%m%d")))

            sentiment = SocialSentiment(
                source="aggregated",
                symbol=symbol,
                mentions_1h=random.randint(50, 500),
                mentions_24h=random.randint(500, 5000),
                sentiment_score=random.uniform(-0.5, 0.8),
                sentiment_change_24h=random.uniform(-0.3, 0.3),
                top_keywords=["earnings", "AI", "growth", "buy", "momentum"][:random.randint(2, 5)],
                influencer_mentions=random.randint(0, 20),
            )
            sentiment_data.append(sentiment.model_dump())

        return sentiment_data

    async def _fetch_options_flow(self) -> list[dict]:
        """
        Fetch unusual options activity.

        In production, would connect to:
        - CBOE data feeds
        - Options clearing data
        - Dark pool aggregators
        """
        symbols = ["SPY", "QQQ", "AAPL", "NVDA", "TSLA"]
        options_data = []

        for symbol in symbols:
            import random
            random.seed(hash(symbol + "options" + datetime.utcnow().strftime("%Y%m%d")))

            # Simulate some unusual activity
            if random.random() > 0.6:  # 40% chance of unusual activity
                flow = OptionsFlow(
                    symbol=symbol,
                    contract_type=random.choice(["call", "put"]),
                    strike=random.randint(400, 500),
                    expiry=(datetime.utcnow() + timedelta(days=random.randint(7, 45))).strftime("%Y-%m-%d"),
                    volume=random.randint(5000, 50000),
                    open_interest=random.randint(1000, 20000),
                    volume_oi_ratio=random.uniform(2, 10),
                    premium_total=random.uniform(500000, 5000000),
                    is_unusual=True,
                    is_sweep=random.random() > 0.7,
                    sentiment="bullish" if random.random() > 0.4 else "bearish",
                )
                options_data.append(flow.model_dump())

        return options_data

    async def _fetch_insider_activity(self) -> list[dict]:
        """
        Fetch insider trading data from SEC filings.

        In production, would connect to:
        - SEC EDGAR API (Form 4 filings)
        - OpenInsider
        - InsiderMonkey
        """
        insider_data = []
        symbols = ["AAPL", "GOOGL", "MSFT", "NVDA", "META"]

        for symbol in symbols:
            import random
            random.seed(hash(symbol + "insider" + datetime.utcnow().strftime("%Y%m%d")))

            # Simulate occasional insider activity
            if random.random() > 0.7:  # 30% chance of insider activity
                transaction = InsiderTransaction(
                    symbol=symbol,
                    insider_name=f"Executive {random.randint(1, 10)}",
                    insider_title=random.choice(["CEO", "CFO", "Director", "VP"]),
                    transaction_type=random.choice(["buy", "sell"]),
                    shares=random.randint(1000, 50000),
                    price=random.uniform(100, 500),
                    value=random.uniform(100000, 5000000),
                    transaction_date=datetime.utcnow() - timedelta(days=random.randint(1, 7)),
                    is_cluster=random.random() > 0.8,
                )
                insider_data.append(transaction.model_dump())

        return insider_data

    def _aggregate_signals(self, data: dict) -> list[dict]:
        """Aggregate alternative data into actionable signals."""
        signals = []

        # Process social sentiment signals
        for sentiment in data["social_sentiment"]:
            if abs(sentiment["sentiment_score"]) > self.sentiment_threshold:
                direction = "bullish" if sentiment["sentiment_score"] > 0 else "bearish"
                confidence = min(abs(sentiment["sentiment_score"]), 1.0)

                # Boost confidence for high mention velocity
                if sentiment["mentions_1h"] > 200:
                    confidence = min(confidence + 0.1, 1.0)

                # Boost for influencer attention
                if sentiment["influencer_mentions"] > 5:
                    confidence = min(confidence + 0.1, 1.0)

                strength = self._confidence_to_strength(confidence, direction)

                signal = AlternativeSignal(
                    symbol=sentiment["symbol"],
                    signal_type="social_sentiment",
                    strength=strength,
                    confidence=confidence,
                    data_points={
                        "sentiment_score": sentiment["sentiment_score"],
                        "mentions_1h": sentiment["mentions_1h"],
                        "mentions_24h": sentiment["mentions_24h"],
                        "sentiment_change": sentiment["sentiment_change_24h"],
                    },
                    reasoning=f"Social sentiment {direction} with score {sentiment['sentiment_score']:.2f}, "
                             f"{sentiment['mentions_1h']} mentions in last hour",
                )
                signals.append(signal.model_dump())

        # Process options flow signals
        for flow in data["options_flow"]:
            if flow["is_unusual"]:
                direction = "bullish" if flow["sentiment"] == "bullish" else "bearish"
                confidence = min(flow["volume_oi_ratio"] / 10, 0.9)

                # Boost for sweeps (aggressive buying)
                if flow["is_sweep"]:
                    confidence = min(confidence + 0.15, 0.95)

                strength = self._confidence_to_strength(confidence, direction)

                signal = AlternativeSignal(
                    symbol=flow["symbol"],
                    signal_type="options_flow",
                    strength=strength,
                    confidence=confidence,
                    data_points={
                        "contract_type": flow["contract_type"],
                        "strike": flow["strike"],
                        "expiry": flow["expiry"],
                        "volume": flow["volume"],
                        "premium": flow["premium_total"],
                        "is_sweep": flow["is_sweep"],
                    },
                    reasoning=f"Unusual {flow['contract_type']} activity: {flow['volume']:,} contracts, "
                             f"${flow['premium_total']:,.0f} premium, "
                             f"{'SWEEP' if flow['is_sweep'] else 'block'} order",
                )
                signals.append(signal.model_dump())

        # Process insider activity
        for insider in data["insider_activity"]:
            # Insider buys are more significant than sells
            direction = "bullish" if insider["transaction_type"] == "buy" else "bearish"
            confidence = 0.6 if insider["transaction_type"] == "buy" else 0.4

            # Boost for cluster activity
            if insider["is_cluster"]:
                confidence = min(confidence + 0.2, 0.85)

            # Boost for large transactions
            if insider["value"] > 1000000:
                confidence = min(confidence + 0.1, 0.9)

            strength = self._confidence_to_strength(confidence, direction)

            signal = AlternativeSignal(
                symbol=insider["symbol"],
                signal_type="insider_activity",
                strength=strength,
                confidence=confidence,
                data_points={
                    "insider_name": insider["insider_name"],
                    "insider_title": insider["insider_title"],
                    "transaction_type": insider["transaction_type"],
                    "shares": insider["shares"],
                    "value": insider["value"],
                    "is_cluster": insider["is_cluster"],
                },
                reasoning=f"{insider['insider_title']} {insider['transaction_type']} "
                         f"${insider['value']:,.0f} worth of shares"
                         f"{' (CLUSTER BUY)' if insider['is_cluster'] else ''}",
            )
            signals.append(signal.model_dump())

        return signals

    def _confidence_to_strength(self, confidence: float, direction: str) -> SignalStrength:
        """Convert confidence level to signal strength."""
        if direction == "bullish":
            if confidence >= 0.8:
                return SignalStrength.STRONG_BUY
            elif confidence >= 0.6:
                return SignalStrength.BUY
            elif confidence >= 0.4:
                return SignalStrength.WEAK_BUY
            return SignalStrength.NEUTRAL
        else:
            if confidence >= 0.8:
                return SignalStrength.STRONG_SELL
            elif confidence >= 0.6:
                return SignalStrength.SELL
            elif confidence >= 0.4:
                return SignalStrength.WEAK_SELL
            return SignalStrength.NEUTRAL

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build prompt for alternative data analysis."""
        prompt = f"""Analyze the following alternative data signals for alpha opportunities.

## Data Timestamp: {data.get('timestamp')}

## Social Sentiment Analysis:
"""
        for sentiment in data.get("social_sentiment", [])[:5]:
            prompt += f"""
### {sentiment['symbol']}
- Sentiment Score: {sentiment['sentiment_score']:.2f}
- Mentions (1h/24h): {sentiment['mentions_1h']}/{sentiment['mentions_24h']}
- 24h Change: {sentiment['sentiment_change_24h']:+.2f}
- Influencer Mentions: {sentiment['influencer_mentions']}
- Top Keywords: {', '.join(sentiment.get('top_keywords', []))}
"""

        prompt += "\n## Unusual Options Activity:\n"
        for flow in data.get("options_flow", [])[:5]:
            prompt += f"""
### {flow['symbol']} {flow['contract_type'].upper()} ${flow['strike']} exp {flow['expiry']}
- Volume: {flow['volume']:,} (OI: {flow['open_interest']:,})
- Volume/OI Ratio: {flow['volume_oi_ratio']:.1f}x
- Premium: ${flow['premium_total']:,.0f}
- Type: {'SWEEP' if flow['is_sweep'] else 'Block'}
- Sentiment: {flow['sentiment']}
"""

        prompt += "\n## Insider Activity:\n"
        for insider in data.get("insider_activity", [])[:5]:
            prompt += f"""
### {insider['symbol']}
- {insider['insider_title']}: {insider['transaction_type'].upper()}
- Shares: {insider['shares']:,} @ ${insider['price']:.2f}
- Value: ${insider['value']:,.0f}
- Cluster Activity: {'YES' if insider['is_cluster'] else 'No'}
"""

        prompt += f"""
## Aggregated Signals:
Total signals detected: {len(data.get('aggregated_signals', []))}

## Analysis Request:
1. Identify the strongest alpha opportunities from this alternative data
2. Assess conviction level for each signal type
3. Look for signal confluence (multiple sources pointing same direction)
4. Flag any potential manipulation or false signals
5. Prioritize actionable insights

Consider:
- Social sentiment often leads price by 1-3 days
- Unusual options flow may indicate informed trading
- Insider cluster buys have historically high win rates
- Look for divergence between signals and current price action

Respond with JSON:
{{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week",
    "reasoning": "<comprehensive analysis of alternative data>",
    "key_factors": ["factor1", ...],
    "uncertainties": ["risk1", ...],
    "specific_predictions": {{
        "top_opportunities": [
            {{
                "symbol": "...",
                "direction": "bullish" | "bearish",
                "signal_types": ["social", "options", "insider"],
                "confluence_score": <float 0-1>,
                "expected_move": "<percentage>",
                "timeframe": "1-3 days" | "1 week" | "2 weeks"
            }}
        ],
        "avoid_list": ["symbols with negative signals"],
        "manipulation_flags": ["any suspicious patterns"],
        "signal_quality": "high" | "medium" | "low"
    }}
}}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's alternative data analysis."""
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
                    "Social Media Sentiment",
                    "Options Flow Data",
                    "SEC Insider Filings",
                ],
                supporting_evidence={
                    "aggregated_signals": data.get("aggregated_signals", []),
                    "raw_signal_count": len(data.get("aggregated_signals", [])),
                },
            )
        except Exception as e:
            self._logger.error("Failed to parse response", error=str(e))
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are an expert in alternative data analysis for alpha generation.

Your expertise includes:
1. Social media sentiment analysis (Reddit, Twitter, StockTwits)
2. Options flow interpretation (unusual activity, sweeps, dark pool)
3. Insider trading pattern recognition
4. Web traffic and app metrics analysis

Key principles:
- Alternative data often leads traditional indicators by days/weeks
- Look for signal confluence across multiple data types
- Be skeptical of extreme readings (potential manipulation)
- Insider cluster buys have historically high predictive value
- Options sweeps near expiry indicate urgency/conviction

Respond ONLY with valid JSON."""
