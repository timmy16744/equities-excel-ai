"""Macro Economics Agent for analyzing economic indicators."""
import json
from datetime import datetime
from typing import Any, Optional

import structlog

from backend.agents.base_agent import BaseAgent, AgentResult
from backend.data.api_clients import FREDClient, AlphaVantageClient
from backend.utils.schemas import AgentOutput, AgentForecast, Outlook, Timeframe

logger = structlog.get_logger()


class MacroEconomicsAgent(BaseAgent):
    """
    Macro Economics Agent.

    Analyzes economic indicators to form a macroeconomic outlook:
    - GDP growth and trends
    - Unemployment rate
    - Inflation (CPI, PCE)
    - Federal Reserve policy (Fed Funds rate)
    - Treasury yields and yield curve
    - Consumer sentiment
    - Industrial production
    """

    @property
    def agent_id(self) -> str:
        return "macro_economics"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._fred: Optional[FREDClient] = None
        self._alpha_vantage: Optional[AlphaVantageClient] = None

    async def _get_fred_client(self) -> FREDClient:
        """Get FRED client with API key from settings."""
        if self._fred is None:
            api_key = await self.settings.get(
                "fred_api_key",
                category="api_config",
                default="",
            )
            self._fred = FREDClient(api_key=api_key if api_key else None)
        return self._fred

    async def _get_alpha_vantage_client(self) -> AlphaVantageClient:
        """Get Alpha Vantage client with API key from settings."""
        if self._alpha_vantage is None:
            api_key = await self.settings.get(
                "alpha_vantage_api_key",
                category="api_config",
                default="",
            )
            self._alpha_vantage = AlphaVantageClient(api_key=api_key if api_key else None)
        return self._alpha_vantage

    async def fetch_data(self) -> dict[str, Any]:
        """
        Fetch economic data from FRED and Alpha Vantage APIs.

        Returns:
            Dict containing all economic indicators for analysis
        """
        self._logger.info("Fetching economic data")
        data = {"timestamp": datetime.utcnow().isoformat(), "indicators": {}}

        # Fetch FRED indicators
        fred = await self._get_fred_client()
        indicators_to_fetch = [
            "gdp_growth",
            "unemployment",
            "cpi",
            "core_cpi",
            "fed_funds",
            "treasury_10y",
            "treasury_2y",
            "consumer_sentiment",
            "initial_claims",
            "industrial_production",
        ]

        fred_data = await fred.get_multiple_indicators(indicators_to_fetch, limit=12)
        for indicator, result in fred_data.items():
            if result and "observations" in result:
                obs = result["observations"]
                if obs:
                    # Get latest value and calculate trend
                    latest = obs[0]
                    data["indicators"][indicator] = {
                        "value": float(latest["value"]) if latest["value"] != "." else None,
                        "date": latest["date"],
                        "history": [
                            {"date": o["date"], "value": float(o["value"]) if o["value"] != "." else None}
                            for o in obs[:6]
                        ],
                        "is_mock": result.get("is_mock", False),
                    }

        # Calculate yield curve spread
        if "treasury_10y" in data["indicators"] and "treasury_2y" in data["indicators"]:
            t10 = data["indicators"]["treasury_10y"].get("value")
            t2 = data["indicators"]["treasury_2y"].get("value")
            if t10 is not None and t2 is not None:
                data["indicators"]["yield_spread"] = {
                    "value": t10 - t2,
                    "inverted": t10 < t2,
                }

        # Get SPY as market proxy
        alpha = await self._get_alpha_vantage_client()
        spy_data = await alpha.get_stock_quote("SPY")
        if spy_data:
            data["market"] = {
                "spy_price": spy_data.get("price"),
                "spy_change": spy_data.get("change_percent"),
                "is_mock": spy_data.get("is_mock", False),
            }

        self._logger.info(
            "Economic data fetched",
            indicators_count=len(data["indicators"]),
        )
        return data

    def build_prompt(self, data: dict[str, Any]) -> str:
        """Build the analysis prompt for Claude."""
        indicators = data.get("indicators", {})
        market = data.get("market", {})

        prompt = f"""Analyze the following economic data and provide a macroeconomic outlook.

## Current Economic Indicators (as of {data.get('timestamp', 'now')}):

### Employment
- Unemployment Rate: {self._format_indicator(indicators.get('unemployment'))}
- Initial Jobless Claims: {self._format_indicator(indicators.get('initial_claims'))}

### Inflation
- CPI (Consumer Price Index): {self._format_indicator(indicators.get('cpi'))}
- Core CPI (ex Food/Energy): {self._format_indicator(indicators.get('core_cpi'))}

### Growth
- GDP Growth Rate: {self._format_indicator(indicators.get('gdp_growth'))}
- Industrial Production: {self._format_indicator(indicators.get('industrial_production'))}

### Federal Reserve
- Fed Funds Rate: {self._format_indicator(indicators.get('fed_funds'))}

### Interest Rates
- 10-Year Treasury: {self._format_indicator(indicators.get('treasury_10y'))}
- 2-Year Treasury: {self._format_indicator(indicators.get('treasury_2y'))}
- Yield Curve Spread (10Y-2Y): {self._format_indicator(indicators.get('yield_spread'))}
- Yield Curve Inverted: {indicators.get('yield_spread', {}).get('inverted', 'N/A')}

### Sentiment
- Consumer Sentiment: {self._format_indicator(indicators.get('consumer_sentiment'))}

### Market
- SPY Price: ${market.get('spy_price', 'N/A')}
- SPY Daily Change: {market.get('spy_change', 'N/A')}

## Analysis Request:

Based on this data, provide:
1. An overall macroeconomic outlook (bearish, neutral, or bullish)
2. Your confidence level (0-1)
3. Recommended timeframe for this outlook
4. Key factors driving your analysis
5. Major uncertainties or risks
6. Specific predictions if applicable

Consider:
- Is the economy expanding or contracting?
- Is inflation above, at, or below the Fed's 2% target?
- What is the Fed's likely policy direction?
- Is the yield curve signaling recession risk?
- How does employment data look?
- What does consumer sentiment indicate about future spending?

Respond with a JSON object in this exact format:
{{
    "outlook": "bearish" | "neutral" | "bullish",
    "confidence": <float 0-1>,
    "timeframe": "1week" | "1month" | "3month" | "1year",
    "reasoning": "<detailed explanation>",
    "key_factors": ["factor1", "factor2", ...],
    "uncertainties": ["uncertainty1", "uncertainty2", ...],
    "specific_predictions": {{
        "gdp_direction": "up" | "down" | "flat",
        "inflation_trend": "rising" | "falling" | "stable",
        "fed_action": "hike" | "hold" | "cut",
        "recession_probability": <float 0-1>
    }}
}}
"""
        return prompt

    def _format_indicator(self, indicator: Optional[dict]) -> str:
        """Format an indicator for the prompt."""
        if not indicator:
            return "N/A"

        value = indicator.get("value")
        if value is None:
            return "N/A"

        date = indicator.get("date", "")
        history = indicator.get("history", [])

        # Calculate trend if we have history
        trend = ""
        if len(history) >= 2:
            prev_values = [h["value"] for h in history[1:4] if h.get("value") is not None]
            if prev_values:
                avg_prev = sum(prev_values) / len(prev_values)
                if value > avg_prev * 1.02:
                    trend = " (trending up)"
                elif value < avg_prev * 0.98:
                    trend = " (trending down)"
                else:
                    trend = " (stable)"

        mock_note = " [MOCK DATA]" if indicator.get("is_mock") else ""
        return f"{value:.2f} as of {date}{trend}{mock_note}"

    def parse_response(self, response: str, data: dict[str, Any]) -> AgentOutput:
        """Parse Claude's response into structured output."""
        try:
            parsed = self._parse_json_response(response)

            # Map outlook string to enum
            outlook_map = {
                "bearish": Outlook.BEARISH,
                "neutral": Outlook.NEUTRAL,
                "bullish": Outlook.BULLISH,
            }
            outlook = outlook_map.get(parsed.get("outlook", "neutral"), Outlook.NEUTRAL)

            # Map timeframe string to enum
            timeframe_map = {
                "1week": Timeframe.ONE_WEEK,
                "1month": Timeframe.ONE_MONTH,
                "3month": Timeframe.THREE_MONTHS,
                "1year": Timeframe.ONE_YEAR,
            }
            timeframe = timeframe_map.get(parsed.get("timeframe", "1month"), Timeframe.ONE_MONTH)

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=outlook,
                    confidence=float(parsed.get("confidence", 0.5)),
                    timeframe=timeframe,
                    specific_predictions=parsed.get("specific_predictions"),
                ),
                reasoning=parsed.get("reasoning", "No reasoning provided"),
                key_factors=parsed.get("key_factors", []),
                uncertainties=parsed.get("uncertainties", []),
                data_sources=["FRED API", "Alpha Vantage"],
                supporting_evidence={"raw_data": data},
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self._logger.error("Failed to parse Claude response", error=str(e))
            # Return a neutral output on parse failure
            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                forecast=AgentForecast(
                    outlook=Outlook.NEUTRAL,
                    confidence=0.3,
                    timeframe=Timeframe.ONE_MONTH,
                ),
                reasoning=f"Failed to parse AI response: {str(e)}. Raw response: {response[:500]}",
                key_factors=["Parse error - low confidence result"],
                uncertainties=["Response parsing failed"],
                data_sources=["FRED API", "Alpha Vantage"],
            )

    def get_system_prompt(self) -> str:
        """Get specialized system prompt for macro analysis."""
        return """You are a senior macroeconomist and market analyst with deep expertise in:
- Monetary policy and Federal Reserve decision-making
- Economic indicators and their market implications
- Business cycle analysis and recession prediction
- Yield curve analysis and interest rate dynamics

Your role is to analyze economic data and provide actionable market outlooks.

Guidelines:
1. Be data-driven - base conclusions on the provided indicators
2. Consider multiple timeframes and scenarios
3. Acknowledge uncertainty and provide confidence levels
4. Look for leading indicators of economic turning points
5. Consider both bullish and bearish interpretations

Important economic relationships to consider:
- Inverted yield curve often precedes recessions by 12-18 months
- Rising initial claims can signal labor market weakness
- Fed policy follows inflation with a lag
- Consumer sentiment often leads spending trends

Respond ONLY with valid JSON. No additional text or explanation outside the JSON object."""


# CLI interface for testing
if __name__ == "__main__":
    import asyncio
    import argparse

    async def main():
        parser = argparse.ArgumentParser(description="Run Macro Economics Agent")
        parser.add_argument("--analyze", action="store_true", help="Run analysis")
        parser.add_argument("--force", action="store_true", help="Force refresh (ignore cache)")
        args = parser.parse_args()

        if args.analyze:
            from backend.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                agent = MacroEconomicsAgent(db=db)
                result = await agent.run(force_refresh=args.force)

                if result.success:
                    print(f"\n{'='*60}")
                    print("MACRO ECONOMICS ANALYSIS")
                    print(f"{'='*60}")
                    print(f"Outlook: {result.output.forecast.outlook.value.upper()}")
                    print(f"Confidence: {result.output.forecast.confidence:.0%}")
                    print(f"Timeframe: {result.output.forecast.timeframe.value}")
                    print(f"\nReasoning:\n{result.output.reasoning}")
                    print(f"\nKey Factors:")
                    for factor in result.output.key_factors:
                        print(f"  - {factor}")
                    print(f"\nUncertainties:")
                    for unc in result.output.uncertainties:
                        print(f"  - {unc}")
                    if result.output.forecast.specific_predictions:
                        print(f"\nSpecific Predictions:")
                        for k, v in result.output.forecast.specific_predictions.items():
                            print(f"  - {k}: {v}")
                    print(f"\n{'='*60}")
                else:
                    print(f"Analysis failed: {result.error}")

    asyncio.run(main())
