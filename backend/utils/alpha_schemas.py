"""Extended schemas for alpha generation agents."""
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from pydantic import BaseModel, Field


class TradeAction(str, Enum):
    """Trade action types."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SHORT = "short"
    COVER = "cover"


class OrderType(str, Enum):
    """Order types for execution."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class MarketRegime(str, Enum):
    """Market regime classification."""
    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOL = "high_volatility"
    LOW_VOL = "low_volatility"
    CRISIS = "crisis"


class EventType(str, Enum):
    """Types of market events."""
    EARNINGS = "earnings"
    FED_MEETING = "fed_meeting"
    CPI_RELEASE = "cpi_release"
    OPEX = "options_expiration"
    INDEX_REBALANCE = "index_rebalance"
    DIVIDEND = "dividend"
    SPLIT = "split"
    IPO = "ipo"
    M_AND_A = "m_and_a"


class SignalStrength(str, Enum):
    """Signal strength classification."""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WEAK_BUY = "weak_buy"
    NEUTRAL = "neutral"
    WEAK_SELL = "weak_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"


# Execution Agent Schemas
class TradeSignal(BaseModel):
    """Individual trade signal."""
    symbol: str
    action: TradeAction
    strength: SignalStrength
    confidence: float = Field(ge=0, le=1)
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    timeframe: str = "1week"
    reasoning: str


class KellyPosition(BaseModel):
    """Kelly criterion position sizing."""
    symbol: str
    kelly_fraction: float = Field(ge=0, le=1, description="Full Kelly fraction")
    recommended_fraction: float = Field(ge=0, le=1, description="Fractional Kelly (safer)")
    position_size_dollars: float
    position_size_shares: int
    win_probability: float = Field(ge=0, le=1)
    win_loss_ratio: float
    edge: float


class ExecutionOrder(BaseModel):
    """Order to be executed."""
    symbol: str
    action: TradeAction
    quantity: int
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    kelly_sizing: KellyPosition
    signal: TradeSignal
    requires_approval: bool = False
    approval_reason: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result of trade execution."""
    order_id: str
    symbol: str
    action: TradeAction
    quantity: int
    filled_quantity: int
    avg_fill_price: float
    status: str  # filled, partial, rejected, pending
    executed_at: datetime
    commission: float = 0.0
    error: Optional[str] = None


# Alternative Data Agent Schemas
class SocialSentiment(BaseModel):
    """Social media sentiment data."""
    source: str  # reddit, twitter, stocktwits
    symbol: str
    mentions_1h: int
    mentions_24h: int
    sentiment_score: float = Field(ge=-1, le=1)
    sentiment_change_24h: float
    top_keywords: list[str] = Field(default_factory=list)
    influencer_mentions: int = 0


class OptionsFlow(BaseModel):
    """Unusual options activity."""
    symbol: str
    contract_type: str  # call, put
    strike: float
    expiry: str
    volume: int
    open_interest: int
    volume_oi_ratio: float
    premium_total: float
    is_unusual: bool
    is_sweep: bool
    sentiment: str  # bullish, bearish, neutral


class InsiderTransaction(BaseModel):
    """Insider trading data."""
    symbol: str
    insider_name: str
    insider_title: str
    transaction_type: str  # buy, sell, exercise
    shares: int
    price: float
    value: float
    transaction_date: datetime
    is_cluster: bool = False


class AlternativeSignal(BaseModel):
    """Aggregated alternative data signal."""
    symbol: str
    signal_type: str
    strength: SignalStrength
    confidence: float = Field(ge=0, le=1)
    data_points: dict[str, Any] = Field(default_factory=dict)
    reasoning: str


# Learning Loop Schemas
class PredictionOutcome(BaseModel):
    """Tracked prediction outcome."""
    prediction_id: int
    agent_id: str
    symbol: Optional[str] = None
    predicted_outlook: str
    predicted_confidence: float
    prediction_date: datetime
    target_date: datetime
    actual_return: Optional[float] = None
    actual_direction: Optional[str] = None
    was_correct: Optional[bool] = None
    attribution_score: Optional[float] = None


class AgentPerformance(BaseModel):
    """Agent performance metrics."""
    agent_id: str
    period: str  # 7d, 30d, 90d, all_time
    total_predictions: int
    correct_predictions: int
    accuracy: float
    avg_confidence_when_correct: float
    avg_confidence_when_wrong: float
    brier_score: float  # Probability calibration
    sharpe_contribution: float
    current_weight: float
    recommended_weight: float


class RegimePerformance(BaseModel):
    """Agent performance by market regime."""
    agent_id: str
    regime: MarketRegime
    accuracy: float
    sample_size: int
    recommended_weight_in_regime: float


# Cross-Asset Agent Schemas
class CorrelationBreak(BaseModel):
    """Detected correlation breakdown."""
    asset_pair: tuple[str, str]
    normal_correlation: float
    current_correlation: float
    deviation: float
    significance: float
    regime_implication: str
    trading_opportunity: Optional[str] = None


class CrossAssetSignal(BaseModel):
    """Cross-asset trading signal."""
    signal_type: str  # divergence, convergence, regime_shift
    assets_involved: list[str]
    direction: str
    confidence: float
    reasoning: str
    suggested_trades: list[TradeSignal] = Field(default_factory=list)


# Event-Driven Agent Schemas
class MarketEvent(BaseModel):
    """Upcoming market event."""
    event_type: EventType
    symbol: Optional[str] = None
    event_date: datetime
    description: str
    expected_impact: str  # high, medium, low
    historical_avg_move: Optional[float] = None
    historical_win_rate: Optional[float] = None


class EventStrategy(BaseModel):
    """Strategy for event-driven trading."""
    event: MarketEvent
    strategy_name: str
    entry_timing: str  # pre_event, at_event, post_event
    entry_days_before: Optional[int] = None
    exit_timing: str
    exit_days_after: Optional[int] = None
    position_type: str  # long, short, straddle, strangle
    historical_edge: float
    win_rate: float
    avg_return: float
    suggested_sizing: float  # fraction of portfolio


class EarningsSignal(BaseModel):
    """Earnings-specific signal."""
    symbol: str
    earnings_date: datetime
    estimate_revisions_30d: float
    whisper_vs_consensus: float
    implied_move: float
    historical_surprise_rate: float
    pre_earnings_drift: float
    post_earnings_drift: float
    recommended_strategy: str
    confidence: float
