"""Sentiment Agent for analyzing market sentiment."""
import json
from datetime import datetime, timedelta
from typing import Any

import structlog

from backend.agents.base_agent import BaseAgent
from backend.data.api_clients import NewsAPIClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class SentimentAgent(BaseAgent):
    """
    Sentiment Agent.

    Analyzes market sentiment from:
    - Financial news sentiment
    - Market fear/greed indicators
    - Social media trends
    - Analyst sentiment
    """

    @property
    def agent_id(self) -> str:
        return "sentiment"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch sentiment data from news sources."""
        self._logger.info("Fetching sentiment data")

        api_key = await self.settings.get(
            "news_api_key",
            category="api_config",
            default="",
        )
        client = NewsAPIClient(api_key=api_key if api_key else None)

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "market_news": [],
            "sentiment_indicators": {},
        }

        # Get market-related news
        result = await client.search_news(
            query="stock market economy",
            from_date=datetime.utcnow() - timedelta(days=3),
            page_size=15,
        )

        if result and result.get("articles"):
            data["market_news"] = [
                {
                    "title": a.get("title"),
                    "description": a.get("description"),
                    "source": a.get("source", {}).get("name"),
                }
                for a in result["articles"]
            ]
            data["is_mock"] = result.get("is_mock", False)

        # Mock sentiment indicators (would come from real APIs in production)
        data["sentiment_indicators"] = {
            "fear_greed_index": 55,  # 0-100, >50 is greed
            "put_call_ratio": 0.85,  # <1 is bullish
            "vix": 18.5,  # Volatility index
            "is_mock": True,
        }

        await client.close()
        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build analysis prompt."""
        news = data.get("market_news", [])
        indicators = data.get("sentiment_indicators", {})

        prompt = f"""Analyze market sentiment from the following data.

## Sentiment Indicators (as of {data.get('timestamp')}):

- Fear & Greed Index: {indicators.get('fear_greed_index', 'N/A')}/100
- Put/Call Ratio: {indicators.get('put_call_ratio', 'N/A')}
- VIX (Volatility Index): {indicators.get('vix', 'N/A')}

## Recent Market Headlines:

"""
        for article in news[:10]:
            prompt += f"- {article.get('title', 'No title')}\n"
            prompt += f"  {article.get('description', '')[:150]}...\n\n"

        prompt += """
## Analysis Request:

Based on sentiment data:
1. Assess overall market sentiment (fear vs greed)
2. Identify dominant narratives in news
3. Evaluate contrarian signals
4. Determine sentiment impact on market direction

Consider:
- Are headlines overly bullish or bearish?
- What is the VIX telling us about expected volatility?
- Is sentiment at extremes (contrarian opportunity)?

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed analysis>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", ...],
    "specific_predictions": {
        "sentiment_level": "extreme_fear" | "fear" | "neutral" | "greed" | "extreme_greed",
        "contrarian_signal": true | false,
        "volatility_outlook": "increasing" | "stable" | "decreasing"
    }
}"""
        return prompt

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's response."""
        try:
            parsed = self._parse_json_response(response)
            outlook = {"bearish": Outlook.BEARISH, "neutral": Outlook.NEUTRAL, "bullish": Outlook.BULLISH}
            timeframe = {"1week": Timeframe.ONE_WEEK, "1month": Timeframe.ONE_MONTH,
                        "3month": Timeframe.THREE_MONTHS, "1year": Timeframe.ONE_YEAR}

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=outlook.get(parsed.get("outlook", "neutral"), Outlook.NEUTRAL),
                    confidence=float(parsed.get("confidence", 0.5)),
                    timeframe=timeframe.get(parsed.get("timeframe", "1month"), Timeframe.ONE_MONTH),
                    specific_predictions=parsed.get("specific_predictions"),
                ),
                reasoning=parsed.get("reasoning", ""),
                key_factors=parsed.get("key_factors", []),
                uncertainties=parsed.get("uncertainties", []),
                data_sources=["News API", "Sentiment Indicators"],
            )
        except Exception as e:
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are a market sentiment analyst.
Focus on: news sentiment, fear/greed indicators, and contrarian signals.
Look for extreme sentiment as potential reversal indicators.
Respond ONLY with valid JSON."""
