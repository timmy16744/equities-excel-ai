"""SQLAlchemy database models."""
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Setting(Base):
    """System settings stored in database."""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text)
    value_type = Column(String(20), nullable=False, default="string")
    description = Column(Text)
    is_sensitive = Column(Boolean, default=False)
    validation_rules = Column(JSON)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    updated_by = Column(String(100))

    __table_args__ = (
        UniqueConstraint("category", "key", name="uq_settings_category_key"),
        Index("idx_settings_category", "category"),
    )

    def get_typed_value(self) -> Any:
        """Return value converted to appropriate Python type."""
        if self.value is None:
            return None

        if self.value_type == "integer":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "boolean":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        return self.value

    def __repr__(self) -> str:
        return f"<Setting {self.category}.{self.key}={self.value}>"


class SettingHistory(Base):
    """Audit trail for settings changes."""
    __tablename__ = "settings_history"

    id = Column(Integer, primary_key=True)
    setting_id = Column(Integer, ForeignKey("settings.id", ondelete="SET NULL"))
    category = Column(String(50), nullable=False)
    key = Column(String(100), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    changed_at = Column(DateTime(timezone=True), default=func.now())
    changed_by = Column(String(100))
    change_type = Column(String(20), nullable=False)  # 'create', 'update', 'delete'

    setting = relationship("Setting", backref="history")

    def __repr__(self) -> str:
        return f"<SettingHistory {self.category}.{self.key} {self.change_type}>"


class AgentPrediction(Base):
    """Predictions from individual agents."""
    __tablename__ = "agent_predictions"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    outlook = Column(String(20))  # 'bearish', 'neutral', 'bullish'
    confidence = Column(Float)
    timeframe = Column(String(20))  # '1week', '1month', '3month', '1year'
    specific_predictions = Column(JSON)
    reasoning = Column(Text)
    key_factors = Column(JSON)
    uncertainties = Column(JSON)
    data_sources = Column(JSON)
    supporting_evidence = Column(JSON)
    # Note: embedding column handled separately for pgvector
    created_at = Column(DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        return f"<AgentPrediction {self.agent_id} {self.outlook} ({self.confidence:.2f})>"


class MarketData(Base):
    """Cached market data from various sources."""
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True)
    data_type = Column(String(50), nullable=False)  # 'stock', 'economic', 'commodity'
    symbol = Column(String(20))
    indicator = Column(String(100))
    data = Column(JSON, nullable=False)
    source = Column(String(50), nullable=False)
    fetched_at = Column(DateTime(timezone=True), default=func.now())
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("data_type", "symbol", "indicator", "source",
                        name="uq_market_data_unique"),
        Index("idx_market_data_type_symbol", "data_type", "symbol"),
        Index("idx_market_data_expires", "expires_at"),
    )

    def is_expired(self) -> bool:
        """Check if cached data has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(self.expires_at.tzinfo) > self.expires_at

    def __repr__(self) -> str:
        return f"<MarketData {self.data_type} {self.symbol or self.indicator}>"


class AggregatedInsight(Base):
    """Aggregated insights from all agents."""
    __tablename__ = "aggregated_insights"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    overall_outlook = Column(String(20))
    confidence = Column(Float)
    agent_outputs = Column(JSON)
    conflicts = Column(JSON)
    resolution_reasoning = Column(Text)
    final_recommendations = Column(JSON)
    risk_assessment = Column(JSON)
    vetoed = Column(Boolean, default=False)
    veto_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        status = "VETOED" if self.vetoed else self.overall_outlook
        return f"<AggregatedInsight {status} ({self.confidence:.2f})>"


class PerformanceMetric(Base):
    """Track prediction accuracy over time."""
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), nullable=False, index=True)
    prediction_id = Column(Integer, ForeignKey("agent_predictions.id"))
    predicted_outlook = Column(String(20))
    actual_outcome = Column(String(20))
    prediction_date = Column(DateTime(timezone=True))
    outcome_date = Column(DateTime(timezone=True))
    accuracy_score = Column(Float)
    details = Column(JSON)
    created_at = Column(DateTime(timezone=True), default=func.now())

    prediction = relationship("AgentPrediction", backref="metrics")

    def __repr__(self) -> str:
        return f"<PerformanceMetric {self.agent_id} {self.accuracy_score:.2f}>"


class AgentWeight(Base):
    """Dynamic weights for agents based on performance."""
    __tablename__ = "agent_weights"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), nullable=False, unique=True)
    weight = Column(Float, default=1.0)
    accuracy_30d = Column(Float)
    accuracy_90d = Column(Float)
    accuracy_all_time = Column(Float)
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AgentWeight {self.agent_id} w={self.weight:.2f}>"


# ============================================================================
# Alpha Generation Models
# ============================================================================


class TradeSignal(Base):
    """Generated trade signals from analysis."""
    __tablename__ = "trade_signals"

    id = Column(Integer, primary_key=True)
    signal_id = Column(String(50), unique=True, nullable=False)  # UUID
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # buy, sell, hold, short, cover
    strength = Column(String(20))  # strong_buy, buy, weak_buy, neutral, weak_sell, sell, strong_sell
    confidence = Column(Float)
    target_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    timeframe = Column(String(20))
    reasoning = Column(Text)
    source_agent = Column(String(50), index=True)  # Which agent generated this
    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="pending")  # pending, executed, expired, cancelled

    __table_args__ = (
        Index("idx_trade_signals_symbol_created", "symbol", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<TradeSignal {self.symbol} {self.action} ({self.confidence:.2f})>"


class ExecutionOrder(Base):
    """Execution orders generated by the execution agent."""
    __tablename__ = "execution_orders"

    id = Column(Integer, primary_key=True)
    order_id = Column(String(50), unique=True, nullable=False)  # UUID or broker order ID
    signal_id = Column(Integer, ForeignKey("trade_signals.id"))
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False)  # buy, sell, short, cover
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(20), default="market")  # market, limit, stop, stop_limit
    limit_price = Column(Float)
    stop_price = Column(Float)
    time_in_force = Column(String(20), default="day")

    # Kelly sizing details
    kelly_fraction = Column(Float)
    recommended_fraction = Column(Float)
    position_size_dollars = Column(Float)
    win_probability = Column(Float)
    edge = Column(Float)

    # Status tracking
    status = Column(String(20), default="pending")  # pending, submitted, filled, partial, rejected, cancelled
    requires_approval = Column(Boolean, default=False)
    approval_reason = Column(String(200))
    approved_by = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime(timezone=True))

    # Execution details
    submitted_at = Column(DateTime(timezone=True))
    filled_at = Column(DateTime(timezone=True))
    filled_quantity = Column(Integer)
    avg_fill_price = Column(Float)
    commission = Column(Float, default=0.0)

    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    signal = relationship("TradeSignal", backref="orders")

    __table_args__ = (
        Index("idx_execution_orders_status", "status"),
        Index("idx_execution_orders_symbol_created", "symbol", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ExecutionOrder {self.order_id} {self.symbol} {self.action} {self.quantity}>"


class TradeOutcome(Base):
    """Track outcomes of executed trades for learning."""
    __tablename__ = "trade_outcomes"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("execution_orders.id"), unique=True)
    symbol = Column(String(20), nullable=False, index=True)

    # Entry details
    entry_price = Column(Float, nullable=False)
    entry_date = Column(DateTime(timezone=True), nullable=False)
    position_size = Column(Integer, nullable=False)
    position_type = Column(String(20))  # long, short

    # Exit details
    exit_price = Column(Float)
    exit_date = Column(DateTime(timezone=True))
    exit_reason = Column(String(50))  # target_hit, stop_hit, time_exit, manual

    # Performance metrics
    realized_pnl = Column(Float)
    realized_pnl_pct = Column(Float)
    holding_period_days = Column(Integer)
    max_drawdown = Column(Float)
    max_gain = Column(Float)

    # Prediction accuracy
    predicted_direction = Column(String(20))
    actual_direction = Column(String(20))
    was_correct = Column(Boolean)

    # Attribution
    source_agent = Column(String(50), index=True)
    attribution_score = Column(Float)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    order = relationship("ExecutionOrder", backref="outcome")

    def __repr__(self) -> str:
        status = f"${self.realized_pnl:+.2f}" if self.realized_pnl else "open"
        return f"<TradeOutcome {self.symbol} {status}>"


class AlternativeDataSignal(Base):
    """Signals from alternative data sources."""
    __tablename__ = "alternative_data_signals"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)  # social_sentiment, options_flow, insider_activity
    strength = Column(String(20))
    confidence = Column(Float)
    data_points = Column(JSON)  # Raw signal data
    reasoning = Column(Text)

    # Source details
    source = Column(String(50))  # reddit, twitter, cboe, sec_edgar
    source_timestamp = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_alt_data_type_symbol", "signal_type", "symbol"),
    )

    def __repr__(self) -> str:
        return f"<AlternativeDataSignal {self.signal_type} {self.symbol} ({self.strength})>"


class MarketRegime(Base):
    """Track detected market regimes over time."""
    __tablename__ = "market_regimes"

    id = Column(Integer, primary_key=True)
    regime = Column(String(30), nullable=False)  # bull, bear, sideways, high_vol, low_vol, crisis
    confidence = Column(Float)
    start_date = Column(DateTime(timezone=True), nullable=False, index=True)
    end_date = Column(DateTime(timezone=True))

    # Indicators that triggered the regime detection
    indicators = Column(JSON)  # risk_appetite, volatility, breadth, etc.

    # Performance during this regime
    spy_return = Column(Float)
    best_performing_agents = Column(JSON)
    worst_performing_agents = Column(JSON)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<MarketRegime {self.regime} from {self.start_date}>"


class EventCalendar(Base):
    """Track market events for event-driven strategies."""
    __tablename__ = "event_calendar"

    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)  # earnings, fed_meeting, cpi, opex
    symbol = Column(String(20), index=True)  # Null for market-wide events
    event_date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(String(200))
    expected_impact = Column(String(20))  # high, medium, low

    # Historical stats
    historical_avg_move = Column(Float)
    historical_win_rate = Column(Float)

    # Actual outcome (filled after event)
    actual_move = Column(Float)
    actual_direction = Column(String(20))

    # Strategy tracking
    strategy_used = Column(String(50))
    strategy_return = Column(Float)

    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_event_calendar_date_type", "event_date", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<EventCalendar {self.event_type} {self.symbol or 'MARKET'} {self.event_date}>"


class CorrelationSnapshot(Base):
    """Track cross-asset correlations over time."""
    __tablename__ = "correlation_snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    asset_pair = Column(String(50), nullable=False)  # e.g., "SPY_TLT"
    correlation = Column(Float, nullable=False)
    baseline_correlation = Column(Float)  # Historical normal
    deviation = Column(Float)  # From baseline
    is_break = Column(Boolean, default=False)  # Significant deviation detected

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        Index("idx_correlation_date_pair", "snapshot_date", "asset_pair"),
        UniqueConstraint("snapshot_date", "asset_pair", name="uq_correlation_snapshot"),
    )

    def __repr__(self) -> str:
        return f"<CorrelationSnapshot {self.asset_pair} {self.correlation:.2f}>"


class LearningMetric(Base):
    """Track learning loop metrics and agent calibration."""
    __tablename__ = "learning_metrics"

    id = Column(Integer, primary_key=True)
    agent_id = Column(String(50), nullable=False, index=True)
    metric_date = Column(DateTime(timezone=True), nullable=False, index=True)
    period = Column(String(20))  # 7d, 30d, 90d, all_time

    # Accuracy metrics
    total_predictions = Column(Integer)
    correct_predictions = Column(Integer)
    accuracy = Column(Float)

    # Calibration metrics
    brier_score = Column(Float)  # Lower is better
    avg_confidence_correct = Column(Float)
    avg_confidence_wrong = Column(Float)
    calibration_status = Column(String(20))  # overconfident, underconfident, well_calibrated

    # Attribution metrics
    total_attribution = Column(Float)
    sharpe_contribution = Column(Float)

    # Weight recommendations
    current_weight = Column(Float)
    recommended_weight = Column(Float)
    weight_change_applied = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=func.now())

    __table_args__ = (
        UniqueConstraint("agent_id", "metric_date", "period", name="uq_learning_metric"),
    )

    def __repr__(self) -> str:
        return f"<LearningMetric {self.agent_id} {self.period} acc={self.accuracy:.1%}>"
