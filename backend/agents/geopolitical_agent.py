"""Geopolitical Agent for analyzing global political events and their market impact."""
import json
from datetime import datetime, timedelta
from typing import Any, Optional

import structlog

from backend.agents.base_agent import BaseAgent
from backend.data.api_clients import NewsAPIClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class GeopoliticalAgent(BaseAgent):
    """
    Geopolitical Agent.

    Analyzes global political events and their market implications:
    - Trade relations and tariffs
    - Geopolitical conflicts and tensions
    - Political elections and policy changes
    - Sanctions and international relations
    - Supply chain disruptions
    """

    @property
    def agent_id(self) -> str:
        return "geopolitical"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch geopolitical news and events."""
        self._logger.info("Fetching geopolitical data")

        api_key = await self.settings.get(
            "news_api_key",
            category="api_config",
            default="",
        )
        client = NewsAPIClient(api_key=api_key if api_key else None)

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "news": {},
        }

        # Search for various geopolitical topics
        topics = [
            "trade war tariffs",
            "geopolitical conflict",
            "sanctions",
            "central bank policy",
            "election economy",
        ]

        for topic in topics:
            result = await client.search_news(
                query=topic,
                from_date=datetime.utcnow() - timedelta(days=7),
                page_size=5,
            )
            if result and result.get("articles"):
                data["news"][topic] = [
                    {
                        "title": a.get("title"),
                        "description": a.get("description"),
                        "source": a.get("source", {}).get("name"),
                        "published": a.get("publishedAt"),
                    }
                    for a in result["articles"]
                ]
                data["is_mock"] = result.get("is_mock", False)

        await client.close()
        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build analysis prompt."""
        news = data.get("news", {})

        prompt = f"""Analyze the following geopolitical news and events for market impact.

## Recent Geopolitical News (as of {data.get('timestamp')}):

"""
        for topic, articles in news.items():
            prompt += f"### {topic.replace('_', ' ').title()}\n"
            for article in articles[:3]:
                prompt += f"- **{article.get('title', 'No title')}**\n"
                prompt += f"  {article.get('description', 'No description')[:200]}...\n"
                prompt += f"  Source: {article.get('source', 'Unknown')} | {article.get('published', '')}\n\n"

        prompt += """
## Analysis Request:

Based on this geopolitical news:
1. Identify major geopolitical themes affecting markets
2. Assess overall risk level from geopolitical factors
3. Determine market outlook impact
4. Highlight specific sectors or regions at risk

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed analysis>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", ...],
    "specific_predictions": {
        "risk_regions": ["region1", ...],
        "risk_sectors": ["sector1", ...],
        "escalation_probability": <float 0-1>
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
                data_sources=["News API"],
            )
        except Exception as e:
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are a geopolitical risk analyst specializing in market implications of global events.
Focus on: trade relations, conflicts, sanctions, political changes, and supply chain risks.
Be specific about which sectors and regions are most affected.
Respond ONLY with valid JSON."""
