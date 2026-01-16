"""Commodities Agent for analyzing commodity markets and supply chains."""
import json
from datetime import datetime
from typing import Any, Optional

import structlog

from backend.agents.base_agent import BaseAgent
from backend.data.api_clients import AlphaVantageClient, YFinanceClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class CommoditiesAgent(BaseAgent):
    """
    Commodities Agent.

    Analyzes commodity markets:
    - Oil and natural gas prices
    - Precious metals (gold, silver)
    - Industrial metals (copper, aluminum)
    - Agricultural commodities
    - Supply chain signals
    """

    @property
    def agent_id(self) -> str:
        return "commodities"

    # Common commodity ETFs/symbols for tracking
    COMMODITY_SYMBOLS = {
        "oil": "USO",  # United States Oil Fund
        "natural_gas": "UNG",
        "gold": "GLD",
        "silver": "SLV",
        "copper": "CPER",
        "agriculture": "DBA",
        "commodities_broad": "DJP",
    }

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch commodity price data."""
        self._logger.info("Fetching commodity data")

        yf = YFinanceClient()
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "commodities": {},
        }

        for name, symbol in self.COMMODITY_SYMBOLS.items():
            info = await yf.get_stock_info(symbol)
            if info:
                data["commodities"][name] = {
                    "symbol": symbol,
                    "price": info.get("price"),
                    "name": info.get("name"),
                }

        # If yfinance not available, use mock data
        if not data["commodities"]:
            data["commodities"] = {
                "oil": {"symbol": "USO", "price": 75.50, "is_mock": True},
                "gold": {"symbol": "GLD", "price": 185.00, "is_mock": True},
                "copper": {"symbol": "CPER", "price": 22.50, "is_mock": True},
            }
            data["is_mock"] = True

        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build analysis prompt."""
        commodities = data.get("commodities", {})

        prompt = f"""Analyze the following commodity market data.

## Current Commodity Prices (as of {data.get('timestamp')}):

"""
        for name, info in commodities.items():
            mock = " [MOCK]" if info.get("is_mock") else ""
            prompt += f"- **{name.replace('_', ' ').title()}** ({info.get('symbol')}): ${info.get('price', 'N/A')}{mock}\n"

        prompt += """

## Analysis Request:

Based on commodity prices:
1. Assess overall commodity market trend
2. Identify inflation signals from commodities
3. Evaluate supply chain health
4. Determine impact on equity markets

Consider:
- Oil prices and energy sector implications
- Gold as safe haven indicator
- Copper as economic growth indicator
- Agricultural prices and consumer impact

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed analysis>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", ...],
    "specific_predictions": {
        "oil_direction": "up" | "down" | "stable",
        "gold_direction": "up" | "down" | "stable",
        "inflation_signal": "rising" | "falling" | "stable",
        "supply_chain_stress": "high" | "medium" | "low"
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
                data_sources=["Yahoo Finance", "Alpha Vantage"],
            )
        except Exception as e:
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are a commodities market analyst.
Focus on: energy, metals, agriculture, and supply chain dynamics.
Consider how commodity trends impact broader equity markets.
Respond ONLY with valid JSON."""
