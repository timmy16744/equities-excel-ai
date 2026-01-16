"""API clients for external data sources."""
import os
from datetime import datetime, timedelta
from typing import Optional, Any

import aiohttp
import structlog

logger = structlog.get_logger()


class BaseAPIClient:
    """Base class for API clients."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make HTTP request with error handling."""
        session = await self._get_session()
        try:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(
                        "API request failed",
                        url=url,
                        status=response.status,
                        reason=response.reason,
                    )
                    return None
        except Exception as e:
            logger.error("API request error", url=url, error=str(e))
            return None


class FREDClient(BaseAPIClient):
    """
    Federal Reserve Economic Data (FRED) API client.

    Provides access to economic indicators like GDP, unemployment, inflation.
    Get API key at: https://fred.stlouisfed.org/docs/api/api_key.html
    """

    BASE_URL = "https://api.stlouisfed.org/fred"

    # Common economic indicators
    INDICATORS = {
        "gdp": "GDP",  # Gross Domestic Product
        "gdp_growth": "A191RL1Q225SBEA",  # Real GDP Growth Rate
        "unemployment": "UNRATE",  # Unemployment Rate
        "cpi": "CPIAUCSL",  # Consumer Price Index
        "core_cpi": "CPILFESL",  # Core CPI (excluding food/energy)
        "pce": "PCEPI",  # Personal Consumption Expenditures
        "fed_funds": "FEDFUNDS",  # Federal Funds Rate
        "treasury_10y": "DGS10",  # 10-Year Treasury Rate
        "treasury_2y": "DGS2",  # 2-Year Treasury Rate
        "treasury_spread": "T10Y2Y",  # 10Y-2Y Spread
        "industrial_production": "INDPRO",
        "retail_sales": "RSXFS",
        "housing_starts": "HOUST",
        "consumer_sentiment": "UMCSENT",
        "initial_claims": "ICSA",  # Jobless Claims
    }

    async def get_series(
        self,
        series_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> Optional[dict]:
        """
        Get time series data for an economic indicator.

        Args:
            series_id: FRED series ID (e.g., "GDP", "UNRATE")
            start_date: Start date for data
            end_date: End date for data
            limit: Maximum observations to return

        Returns:
            Dict with observations or None if failed
        """
        if not self.api_key:
            logger.warning("FRED API key not configured, returning mock data")
            return self._mock_series(series_id)

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }

        if start_date:
            params["observation_start"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["observation_end"] = end_date.strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/series/observations"
        data = await self._request(url, params)

        if data and "observations" in data:
            return {
                "series_id": series_id,
                "observations": data["observations"],
                "count": len(data["observations"]),
            }
        return None

    async def get_indicator(self, indicator: str, **kwargs) -> Optional[dict]:
        """Get data for a named indicator."""
        series_id = self.INDICATORS.get(indicator, indicator)
        return await self.get_series(series_id, **kwargs)

    async def get_multiple_indicators(
        self,
        indicators: list[str],
        **kwargs,
    ) -> dict[str, Any]:
        """Get data for multiple indicators."""
        results = {}
        for indicator in indicators:
            data = await self.get_indicator(indicator, **kwargs)
            if data:
                results[indicator] = data
        return results

    def _mock_series(self, series_id: str) -> dict:
        """Return mock data when API key is not available."""
        mock_values = {
            "GDP": "28000.0",
            "UNRATE": "3.7",
            "CPIAUCSL": "308.5",
            "FEDFUNDS": "5.25",
            "DGS10": "4.2",
            "DGS2": "4.5",
        }
        value = mock_values.get(series_id, "100.0")
        return {
            "series_id": series_id,
            "observations": [
                {"date": datetime.now().strftime("%Y-%m-%d"), "value": value}
            ],
            "count": 1,
            "is_mock": True,
        }


class AlphaVantageClient(BaseAPIClient):
    """
    Alpha Vantage API client.

    Provides stock prices, forex, and economic indicators.
    Get API key at: https://www.alphavantage.co/support/#api-key
    """

    BASE_URL = "https://www.alphavantage.co/query"

    async def get_stock_quote(self, symbol: str) -> Optional[dict]:
        """Get current stock quote."""
        if not self.api_key:
            return self._mock_quote(symbol)

        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key,
        }
        data = await self._request(self.BASE_URL, params)

        if data and "Global Quote" in data:
            quote = data["Global Quote"]
            return {
                "symbol": symbol,
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%"),
                "volume": int(quote.get("06. volume", 0)),
                "timestamp": datetime.now().isoformat(),
            }
        return None

    async def get_daily_prices(
        self,
        symbol: str,
        outputsize: str = "compact",
    ) -> Optional[dict]:
        """Get daily price history."""
        if not self.api_key:
            return self._mock_daily(symbol)

        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": self.api_key,
        }
        data = await self._request(self.BASE_URL, params)

        if data and "Time Series (Daily)" in data:
            return {
                "symbol": symbol,
                "data": data["Time Series (Daily)"],
            }
        return None

    async def get_treasury_yield(self, maturity: str = "10year") -> Optional[dict]:
        """Get treasury yield data."""
        if not self.api_key:
            return {"maturity": maturity, "yield": 4.2, "is_mock": True}

        params = {
            "function": "TREASURY_YIELD",
            "interval": "daily",
            "maturity": maturity,
            "apikey": self.api_key,
        }
        data = await self._request(self.BASE_URL, params)

        if data and "data" in data:
            latest = data["data"][0] if data["data"] else {}
            return {
                "maturity": maturity,
                "yield": float(latest.get("value", 0)),
                "date": latest.get("date"),
            }
        return None

    def _mock_quote(self, symbol: str) -> dict:
        """Return mock quote data."""
        prices = {"SPY": 475.50, "QQQ": 410.25, "AAPL": 185.00, "MSFT": 380.00}
        return {
            "symbol": symbol,
            "price": prices.get(symbol, 100.0),
            "change": 1.50,
            "change_percent": "0.5%",
            "volume": 1000000,
            "timestamp": datetime.now().isoformat(),
            "is_mock": True,
        }

    def _mock_daily(self, symbol: str) -> dict:
        """Return mock daily data."""
        return {
            "symbol": symbol,
            "data": {
                datetime.now().strftime("%Y-%m-%d"): {
                    "1. open": "100.00",
                    "2. high": "102.00",
                    "3. low": "99.00",
                    "4. close": "101.00",
                    "5. volume": "1000000",
                }
            },
            "is_mock": True,
        }


class NewsAPIClient(BaseAPIClient):
    """
    News API client for news aggregation.

    Get API key at: https://newsapi.org/
    """

    BASE_URL = "https://newsapi.org/v2"

    async def get_top_headlines(
        self,
        category: str = "business",
        country: str = "us",
        page_size: int = 10,
    ) -> Optional[dict]:
        """Get top headlines."""
        if not self.api_key:
            return self._mock_headlines()

        params = {
            "category": category,
            "country": country,
            "pageSize": page_size,
            "apiKey": self.api_key,
        }
        url = f"{self.BASE_URL}/top-headlines"
        return await self._request(url, params)

    async def search_news(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        sort_by: str = "relevancy",
        page_size: int = 10,
    ) -> Optional[dict]:
        """Search for news articles."""
        if not self.api_key:
            return self._mock_search(query)

        params = {
            "q": query,
            "sortBy": sort_by,
            "pageSize": page_size,
            "apiKey": self.api_key,
        }
        if from_date:
            params["from"] = from_date.strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/everything"
        return await self._request(url, params)

    def _mock_headlines(self) -> dict:
        """Return mock headlines."""
        return {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": "Mock News: Markets Show Mixed Signals",
                    "description": "This is mock news data for development.",
                    "source": {"name": "Mock Source"},
                    "publishedAt": datetime.now().isoformat(),
                }
            ],
            "is_mock": True,
        }

    def _mock_search(self, query: str) -> dict:
        """Return mock search results."""
        return {
            "status": "ok",
            "totalResults": 1,
            "articles": [
                {
                    "title": f"Mock News about {query}",
                    "description": f"This is mock news about {query}.",
                    "source": {"name": "Mock Source"},
                    "publishedAt": datetime.now().isoformat(),
                }
            ],
            "is_mock": True,
        }


class YFinanceClient:
    """
    Yahoo Finance client using yfinance library.

    No API key required - serves as backup data source.
    """

    def __init__(self) -> None:
        try:
            import yfinance as yf
            self.yf = yf
            self._available = True
        except ImportError:
            self._available = False
            logger.warning("yfinance not installed")

    async def get_stock_info(self, symbol: str) -> Optional[dict]:
        """Get stock information."""
        if not self._available:
            return None

        try:
            ticker = self.yf.Ticker(symbol)
            info = ticker.info
            return {
                "symbol": symbol,
                "name": info.get("longName", symbol),
                "price": info.get("regularMarketPrice"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
            }
        except Exception as e:
            logger.error("yfinance error", symbol=symbol, error=str(e))
            return None

    async def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> Optional[dict]:
        """Get historical price data."""
        if not self._available:
            return None

        try:
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            return {
                "symbol": symbol,
                "data": hist.to_dict("index"),
                "period": period,
            }
        except Exception as e:
            logger.error("yfinance error", symbol=symbol, error=str(e))
            return None
