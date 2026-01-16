from backend.database.connection import get_db, engine, SessionLocal
from backend.database.models import (
    Base,
    Setting,
    SettingHistory,
    AgentPrediction,
    MarketData,
    AggregatedInsight,
    PerformanceMetric,
    AgentWeight,
    # Alpha Generation Models
    TradeSignal,
    ExecutionOrder,
    TradeOutcome,
    AlternativeDataSignal,
    MarketRegime,
    EventCalendar,
    CorrelationSnapshot,
    LearningMetric,
)
from backend.database.auth_models import (
    User,
    Role,
    AuditLog,
    RefreshToken,
    DEFAULT_ROLES,
)

__all__ = [
    # Connection
    "get_db",
    "engine",
    "SessionLocal",
    # Base
    "Base",
    # Core Models
    "Setting",
    "SettingHistory",
    "AgentPrediction",
    "MarketData",
    "AggregatedInsight",
    "PerformanceMetric",
    "AgentWeight",
    # Alpha Generation Models
    "TradeSignal",
    "ExecutionOrder",
    "TradeOutcome",
    "AlternativeDataSignal",
    "MarketRegime",
    "EventCalendar",
    "CorrelationSnapshot",
    "LearningMetric",
    # Auth Models
    "User",
    "Role",
    "AuditLog",
    "RefreshToken",
    "DEFAULT_ROLES",
]
