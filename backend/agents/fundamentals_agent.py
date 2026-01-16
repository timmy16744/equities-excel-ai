"""Fundamentals Agent for analyzing company and market fundamentals."""
import json
from datetime import datetime
from typing import Any

import structlog

from backend.agents.base_agent import BaseAgent
from backend.data.api_clients import YFinanceClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class FundamentalsAgent(BaseAgent):
    """
    Fundamentals Agent.

    Analyzes company and market fundamentals:
    - Market-wide valuation metrics (P/E, P/B)
    - Earnings trends
    - Revenue growth
    - Sector fundamentals
    - Market breadth
    """

    @property
    def agent_id(self) -> str:
        return "fundamentals"

    # Market indices and sector ETFs for analysis
    ANALYSIS_SYMBOLS = {
        "sp500": "SPY",
        "nasdaq": "QQQ",
        "dow": "DIA",
        "small_cap": "IWM",
        "tech": "XLK",
        "financials": "XLF",
        "healthcare": "XLV",
        "energy": "XLE",
        "consumer": "XLY",
        "industrials": "XLI",
    }

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch fundamental data."""
        self._logger.info("Fetching fundamentals data")

        yf = YFinanceClient()
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "indices": {},
            "sectors": {},
        }

        for name, symbol in self.ANALYSIS_SYMBOLS.items():
            info = await yf.get_stock_info(symbol)
            if info:
                entry = {
                    "symbol": symbol,
                    "price": info.get("price"),
                    "pe_ratio": info.get("pe_ratio"),
                    "market_cap": info.get("market_cap"),
                }
                if name in ["sp500", "nasdaq", "dow", "small_cap"]:
                    data["indices"][name] = entry
                else:
                    data["sectors"][name] = entry

        # Add mock data if yfinance unavailable
        if not data["indices"]:
            data["indices"] = {
                "sp500": {"symbol": "SPY", "price": 475.0, "pe_ratio": 21.5, "is_mock": True},
                "nasdaq": {"symbol": "QQQ", "price": 410.0, "pe_ratio": 28.0, "is_mock": True},
            }
            data["sectors"] = {
                "tech": {"symbol": "XLK", "price": 180.0, "pe_ratio": 30.0, "is_mock": True},
                "financials": {"symbol": "XLF", "price": 38.0, "pe_ratio": 14.0, "is_mock": True},
            }
            data["is_mock"] = True

        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build analysis prompt."""
        indices = data.get("indices", {})
        sectors = data.get("sectors", {})

        prompt = f"""Analyze the following market fundamentals data.

## Market Indices (as of {data.get('timestamp')}):

"""
        for name, info in indices.items():
            mock = " [MOCK]" if info.get("is_mock") else ""
            prompt += f"- **{name.upper()}** ({info.get('symbol')}): ${info.get('price', 'N/A')} | P/E: {info.get('pe_ratio', 'N/A')}{mock}\n"

        prompt += "\n## Sector ETFs:\n\n"
        for name, info in sectors.items():
            mock = " [MOCK]" if info.get("is_mock") else ""
            prompt += f"- **{name.title()}** ({info.get('symbol')}): ${info.get('price', 'N/A')} | P/E: {info.get('pe_ratio', 'N/A')}{mock}\n"

        prompt += """

## Analysis Request:

Based on fundamentals:
1. Assess overall market valuation (expensive vs cheap)
2. Identify sector rotation signals
3. Evaluate earnings outlook
4. Determine fundamental support for prices

Consider:
- Historical P/E averages (S&P 500 ~15-17x historically)
- Sector relative valuations
- Growth vs value dynamics
- Market breadth (large cap vs small cap)

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed analysis>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", ...],
    "specific_predictions": {
        "valuation_level": "undervalued" | "fair" | "overvalued",
        "favored_sectors": ["sector1", "sector2"],
        "avoid_sectors": ["sector1"],
        "earnings_outlook": "improving" | "stable" | "declining"
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
                data_sources=["Yahoo Finance"],
            )
        except Exception as e:
            return self._create_mock_output()

    def get_system_prompt(self) -> str:
        return """You are a fundamental equity analyst.
Focus on: valuations, earnings, sector analysis, and market breadth.
Compare current valuations to historical averages.
Respond ONLY with valid JSON."""
