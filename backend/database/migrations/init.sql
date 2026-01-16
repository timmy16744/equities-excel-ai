-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Settings table for all configurable parameters
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT,
    value_type VARCHAR(20) NOT NULL DEFAULT 'string',
    description TEXT,
    is_sensitive BOOLEAN DEFAULT FALSE,
    validation_rules JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    UNIQUE(category, key)
);

-- Settings history for audit trail
CREATE TABLE IF NOT EXISTS settings_history (
    id SERIAL PRIMARY KEY,
    setting_id INTEGER REFERENCES settings(id) ON DELETE SET NULL,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100),
    change_type VARCHAR(20) NOT NULL -- 'create', 'update', 'delete'
);

-- Agent predictions storage
CREATE TABLE IF NOT EXISTS agent_predictions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    outlook VARCHAR(20), -- 'bearish', 'neutral', 'bullish'
    confidence FLOAT,
    timeframe VARCHAR(20), -- '1week', '1month', '3month', '1year'
    specific_predictions JSONB,
    reasoning TEXT,
    key_factors JSONB,
    uncertainties JSONB,
    data_sources JSONB,
    supporting_evidence JSONB,
    embedding vector(1536), -- For semantic search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Market data cache
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    data_type VARCHAR(50) NOT NULL, -- 'stock', 'economic', 'commodity', etc.
    symbol VARCHAR(20),
    indicator VARCHAR(100),
    data JSONB NOT NULL,
    source VARCHAR(50) NOT NULL,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(data_type, symbol, indicator, source)
);

-- Aggregated insights from all agents
CREATE TABLE IF NOT EXISTS aggregated_insights (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    overall_outlook VARCHAR(20),
    confidence FLOAT,
    agent_outputs JSONB, -- All contributing agent outputs
    conflicts JSONB, -- Any disagreements between agents
    resolution_reasoning TEXT,
    final_recommendations JSONB,
    risk_assessment JSONB,
    vetoed BOOLEAN DEFAULT FALSE,
    veto_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance metrics for tracking accuracy
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL,
    prediction_id INTEGER REFERENCES agent_predictions(id),
    predicted_outlook VARCHAR(20),
    actual_outcome VARCHAR(20),
    prediction_date TIMESTAMP WITH TIME ZONE,
    outcome_date TIMESTAMP WITH TIME ZONE,
    accuracy_score FLOAT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Agent weights based on historical performance
CREATE TABLE IF NOT EXISTS agent_weights (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(50) NOT NULL UNIQUE,
    weight FLOAT DEFAULT 1.0,
    accuracy_30d FLOAT,
    accuracy_90d FLOAT,
    accuracy_all_time FLOAT,
    total_predictions INTEGER DEFAULT 0,
    correct_predictions INTEGER DEFAULT 0,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
CREATE INDEX IF NOT EXISTS idx_settings_category_key ON settings(category, key);
CREATE INDEX IF NOT EXISTS idx_agent_predictions_agent_id ON agent_predictions(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_predictions_timestamp ON agent_predictions(timestamp);
CREATE INDEX IF NOT EXISTS idx_market_data_type_symbol ON market_data(data_type, symbol);
CREATE INDEX IF NOT EXISTS idx_market_data_expires ON market_data(expires_at);
CREATE INDEX IF NOT EXISTS idx_aggregated_insights_timestamp ON aggregated_insights(timestamp);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_agent ON performance_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_settings_history_setting ON settings_history(setting_id);

-- Insert default settings
INSERT INTO settings (category, key, value, value_type, description, is_sensitive, validation_rules) VALUES
-- API Configuration
('api_config', 'anthropic_api_key', '', 'string', 'Anthropic API key for Claude access', TRUE, '{"required": false, "pattern": "^sk-ant-.*$"}'),
('api_config', 'alpha_vantage_api_key', '', 'string', 'Alpha Vantage API key for market data', TRUE, '{"required": false}'),
('api_config', 'news_api_key', '', 'string', 'News API key for news aggregation', TRUE, '{"required": false}'),
('api_config', 'fred_api_key', '', 'string', 'FRED API key for economic data', TRUE, '{"required": false}'),
('api_config', 'anthropic_rpm', '50', 'integer', 'Anthropic API requests per minute limit', FALSE, '{"min": 1, "max": 1000}'),
('api_config', 'request_timeout', '30', 'integer', 'Default request timeout in seconds', FALSE, '{"min": 5, "max": 300}'),
('api_config', 'max_retries', '3', 'integer', 'Maximum retry attempts for failed requests', FALSE, '{"min": 0, "max": 10}'),

-- Agent Configuration
('agent_config', 'macro_enabled', 'true', 'boolean', 'Enable Macro Economics Agent', FALSE, NULL),
('agent_config', 'macro_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Macro Agent', FALSE, NULL),
('agent_config', 'macro_max_tokens', '4000', 'integer', 'Max tokens for Macro Agent responses', FALSE, '{"min": 100, "max": 16000}'),
('agent_config', 'macro_cache_ttl', '3600', 'integer', 'Cache TTL for Macro Agent in seconds', FALSE, '{"min": 60, "max": 86400}'),
('agent_config', 'geopolitical_enabled', 'true', 'boolean', 'Enable Geopolitical Agent', FALSE, NULL),
('agent_config', 'geopolitical_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Geopolitical Agent', FALSE, NULL),
('agent_config', 'commodities_enabled', 'true', 'boolean', 'Enable Commodities Agent', FALSE, NULL),
('agent_config', 'commodities_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Commodities Agent', FALSE, NULL),
('agent_config', 'sentiment_enabled', 'true', 'boolean', 'Enable Sentiment Agent', FALSE, NULL),
('agent_config', 'sentiment_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Sentiment Agent', FALSE, NULL),
('agent_config', 'fundamentals_enabled', 'true', 'boolean', 'Enable Fundamentals Agent', FALSE, NULL),
('agent_config', 'fundamentals_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Fundamentals Agent', FALSE, NULL),
('agent_config', 'technical_enabled', 'true', 'boolean', 'Enable Technical Analysis Agent', FALSE, NULL),
('agent_config', 'technical_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Technical Agent', FALSE, NULL),
('agent_config', 'risk_enabled', 'true', 'boolean', 'Enable Risk Management Agent', FALSE, NULL),
('agent_config', 'risk_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Risk Agent', FALSE, NULL),
('agent_config', 'aggregation_model', 'claude-sonnet-4-5-20250929', 'string', 'Claude model for Aggregation Engine', FALSE, NULL),

-- Risk Management
('risk_management', 'max_position_size', '5.0', 'float', 'Maximum position size as percentage of portfolio', FALSE, '{"min": 0.1, "max": 100}'),
('risk_management', 'max_sector_exposure', '20.0', 'float', 'Maximum sector exposure as percentage', FALSE, '{"min": 1, "max": 100}'),
('risk_management', 'max_drawdown', '15.0', 'float', 'Maximum acceptable drawdown percentage', FALSE, '{"min": 1, "max": 50}'),
('risk_management', 'correlation_limit', '0.7', 'float', 'Maximum correlation coefficient between positions', FALSE, '{"min": 0, "max": 1}'),
('risk_management', 'max_leverage', '1.5', 'float', 'Maximum leverage multiplier', FALSE, '{"min": 1, "max": 10}'),
('risk_management', 'portfolio_size', '100000.0', 'float', 'Portfolio size in USD', FALSE, '{"min": 1000}'),

-- Scheduling
('scheduling', 'macro_schedule', '0 9 * * *', 'string', 'Cron schedule for Macro Agent (daily at 9am)', FALSE, NULL),
('scheduling', 'geopolitical_schedule', '0 */6 * * *', 'string', 'Cron schedule for Geopolitical Agent (every 6 hours)', FALSE, NULL),
('scheduling', 'commodities_schedule', '0 */4 * * *', 'string', 'Cron schedule for Commodities Agent (every 4 hours)', FALSE, NULL),
('scheduling', 'sentiment_schedule', '0 */2 * * *', 'string', 'Cron schedule for Sentiment Agent (every 2 hours)', FALSE, NULL),
('scheduling', 'fundamentals_schedule', '0 9 * * 0', 'string', 'Cron schedule for Fundamentals Agent (weekly)', FALSE, NULL),
('scheduling', 'technical_schedule', '*/15 * * * *', 'string', 'Cron schedule for Technical Agent (every 15 min)', FALSE, NULL),
('scheduling', 'risk_schedule', '*/5 * * * *', 'string', 'Cron schedule for Risk Agent (every 5 min)', FALSE, NULL),
('scheduling', 'timezone', 'America/New_York', 'string', 'Timezone for scheduling', FALSE, NULL),

-- Performance & Cost
('performance', 'token_budget_daily', '1000000', 'integer', 'Daily token budget', FALSE, '{"min": 1000}'),
('performance', 'token_budget_monthly', '20000000', 'integer', 'Monthly token budget', FALSE, '{"min": 10000}'),
('performance', 'cost_alert_threshold', '80', 'integer', 'Alert when budget usage exceeds this percentage', FALSE, '{"min": 1, "max": 100}'),
('performance', 'cache_ttl_default', '3600', 'integer', 'Default cache TTL in seconds', FALSE, '{"min": 60, "max": 86400}'),

-- UI Preferences
('ui_preferences', 'theme', 'dark', 'string', 'UI theme (dark/light/auto)', FALSE, '{"enum": ["dark", "light", "auto"]}'),
('ui_preferences', 'default_view', 'dashboard', 'string', 'Default view on load', FALSE, NULL),
('ui_preferences', 'refresh_interval', '30', 'integer', 'Data refresh interval in seconds', FALSE, '{"min": 5, "max": 300}'),
('ui_preferences', 'notifications_enabled', 'true', 'boolean', 'Enable browser notifications', FALSE, NULL),

-- System Configuration
('system', 'log_level', 'INFO', 'string', 'Logging level', FALSE, '{"enum": ["DEBUG", "INFO", "WARNING", "ERROR"]}'),
('system', 'environment', 'development', 'string', 'Environment name', FALSE, '{"enum": ["development", "staging", "production"]}'),
('system', 'db_pool_size', '10', 'integer', 'Database connection pool size', FALSE, '{"min": 1, "max": 100}'),
('system', 'redis_max_connections', '50', 'integer', 'Redis max connections', FALSE, '{"min": 1, "max": 500}')

ON CONFLICT (category, key) DO NOTHING;
