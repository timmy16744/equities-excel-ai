"""Pydantic schemas for data validation."""
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from pydantic import BaseModel, Field


class Outlook(str, Enum):
    """Market outlook enum."""
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"


class Timeframe(str, Enum):
    """Prediction timeframe enum."""
    ONE_WEEK = "1week"
    ONE_MONTH = "1month"
    THREE_MONTHS = "3month"
    ONE_YEAR = "1year"


class AgentForecast(BaseModel):
    """Forecast component of agent output."""
    outlook: Outlook
    confidence: float = Field(ge=0, le=1)
    timeframe: Timeframe
    specific_predictions: Optional[dict[str, Any]] = None


class AgentOutput(BaseModel):
    """
    Standard output schema for all agents.

    All agents must return data conforming to this schema.
    """
    agent_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    forecast: AgentForecast
    reasoning: str
    key_factors: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    supporting_evidence: Optional[dict[str, Any]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "macro_economics",
                "timestamp": "2026-01-15T10:30:00Z",
                "forecast": {
                    "outlook": "bullish",
                    "confidence": 0.75,
                    "timeframe": "1month",
                    "specific_predictions": {
                        "sp500_direction": "up",
                        "expected_move": "2-4%"
                    }
                },
                "reasoning": "Strong GDP growth and moderating inflation suggest continued economic expansion...",
                "key_factors": [
                    "GDP growth at 2.8%",
                    "Inflation declining to 2.5%",
                    "Unemployment stable at 3.7%"
                ],
                "uncertainties": [
                    "Fed policy uncertainty",
                    "Geopolitical tensions"
                ],
                "data_sources": [
                    "FRED API",
                    "Alpha Vantage"
                ]
            }
        }


class RiskAssessment(BaseModel):
    """Risk assessment from the Risk Agent."""
    approved: bool
    veto_reason: Optional[str] = None
    risk_score: float = Field(ge=0, le=1)
    position_risk: dict[str, float] = Field(default_factory=dict)
    portfolio_risk: float = Field(ge=0, le=1)
    recommendations: list[str] = Field(default_factory=list)


class AggregatedInsightOutput(BaseModel):
    """Output from the Aggregation Engine."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    overall_outlook: Outlook
    confidence: float = Field(ge=0, le=1)
    agent_outputs: dict[str, AgentOutput] = Field(default_factory=dict)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    resolution_reasoning: str
    final_recommendations: list[str] = Field(default_factory=list)
    risk_assessment: Optional[RiskAssessment] = None
    vetoed: bool = False
    veto_reason: Optional[str] = None


class MarketDataRequest(BaseModel):
    """Request for market data."""
    data_type: str
    symbol: Optional[str] = None
    indicator: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AnalysisRequest(BaseModel):
    """Request to trigger analysis."""
    agents: Optional[list[str]] = None
    symbols: Optional[list[str]] = None
    force_refresh: bool = False
