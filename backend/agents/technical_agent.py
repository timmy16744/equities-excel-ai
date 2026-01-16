"""Technical Analysis Agent for price pattern and momentum analysis."""
import json
from datetime import datetime
from typing import Any

import structlog

from backend.agents.base_agent import BaseAgent
from backend.data.api_clients import AlphaVantageClient, YFinanceClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class TechnicalAgent(BaseAgent):
    """
    Technical Analysis Agent.

    Analyzes price patterns and technical indicators:
    - Moving averages (SMA, EMA)
    - Momentum indicators (RSI, MACD)
    - Volume analysis
    - Support/resistance levels
    - Chart patterns
    """

    @property
    def agent_id(self) -> str:
        return "technical"

    async def fetch_data(self) -> dict[str, Any]:
        """Fetch price data for technical analysis."""
        self._logger.info("Fetching technical data")

        yf = YFinanceClient()
        api_key = await self.settings.get(
            "alpha_vantage_api_key",
            category="api_config",
            default="",
        )
        alpha = AlphaVantageClient(api_key=api_key if api_key else None)

        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "price_data": {},
            "technicals": {},
        }

        # Get SPY historical data
        hist = await yf.get_historical_data("SPY", period="3mo", interval="1d")
        if hist and hist.get("data"):
            prices = []
            for date, values in list(hist["data"].items())[:30]:
                if hasattr(values, "get"):
                    prices.append({
                        "date": str(date),
                        "close": values.get("Close"),
                        "volume": values.get("Volume"),
                    })
            data["price_data"]["SPY"] = prices

            # Calculate basic technicals from price data
            if prices:
                closes = [p["close"] for p in prices if p.get("close")]
                if len(closes) >= 20:
                    data["technicals"]["sma_20"] = sum(closes[:20]) / 20
                    data["technicals"]["sma_50"] = sum(closes) / len(closes) if len(closes) >= 50 else None
                    data["technicals"]["current_price"] = closes[0]

                    # Simple RSI approximation
                    gains = [closes[i] - closes[i+1] for i in range(min(14, len(closes)-1)) if closes[i] > closes[i+1]]
                    losses = [closes[i+1] - closes[i] for i in range(min(14, len(closes)-1)) if closes[i] < closes[i+1]]
                    avg_gain = sum(gains) / 14 if gains else 0
                    avg_loss = sum(losses) / 14 if losses else 0.001
                    rs = avg_gain / avg_loss
                    data["technicals"]["rsi_14"] = 100 - (100 / (1 + rs))

        # Fallback mock data
        if not data["technicals"]:
            data["technicals"] = {
                "current_price": 475.0,
                "sma_20": 470.0,
                "sma_50": 465.0,
                "rsi_14": 55.0,
                "is_mock": True,
            }
            data["is_mock"] = True

        await alpha.close()
        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build analysis prompt."""
        tech = data.get("technicals", {})
        prices = data.get("price_data", {}).get("SPY", [])

        prompt = f"""Analyze the following technical data for SPY (S&P 500 ETF).

## Technical Indicators (as of {data.get('timestamp')}):

- Current Price: ${tech.get('current_price', 'N/A')}
- 20-Day SMA: ${tech.get('sma_20', 'N/A')}
- 50-Day SMA: ${tech.get('sma_50', 'N/A')}
- RSI (14): {tech.get('rsi_14', 'N/A')}

## Price Trend Analysis:
- Price vs 20 SMA: {'Above' if tech.get('current_price', 0) > tech.get('sma_20', 0) else 'Below'}
- Price vs 50 SMA: {'Above' if tech.get('current_price', 0) > tech.get('sma_50', 0) else 'Below'}
- RSI Zone: {'Overbought' if tech.get('rsi_14', 50) > 70 else 'Oversold' if tech.get('rsi_14', 50) < 30 else 'Neutral'}

## Recent Price Action:
"""
        for p in prices[:5]:
            prompt += f"- {p.get('date', 'N/A')}: ${p.get('close', 'N/A')}\n"

        prompt += """

## Analysis Request:

Based on technical indicators:
1. Identify current trend direction
2. Assess momentum strength
3. Identify key support/resistance levels
4. Evaluate overbought/oversold conditions

Consider:
- Price relative to moving averages
- RSI extremes (>70 overbought, <30 oversold)
- Trend confirmation signals
- Volume patterns

Respond with JSON:
{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed analysis>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", ...],
    "specific_predictions": {
        "trend_direction": "up" | "down" | "sideways",
        "momentum": "strong" | "moderate" | "weak",
        "support_level": <price>,
        "resistance_level": <price>,
        "reversal_signal": true | false
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
                    timeframe=timeframe.get(parsed.get("timeframe", "1week"), Timeframe.ONE_WEEK),
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
        return """You are a technical analyst specializing in price action and momentum.
Focus on: moving averages, RSI, support/resistance, and trend analysis.
Technical analysis is most reliable for short-term timeframes.
Respond ONLY with valid JSON."""
