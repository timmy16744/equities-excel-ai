# AI Agents Documentation

Equities AI uses 14 specialized agents orchestrated through LangGraph. Each agent focuses on a specific domain of market analysis.

## Agent Overview

| Agent | Phase | Focus | Veto Power |
|-------|-------|-------|------------|
| Macro Economics | 1 | Economic indicators | No |
| Geopolitical | 1 | Global events | No |
| Commodities | 1 | Resource markets | No |
| Sentiment | 2 | Market psychology | No |
| Fundamentals | 2 | Company financials | No |
| Technical | 2 | Price patterns | No |
| Alternative Data | 2 | Non-traditional signals | No |
| Cross-Asset | 3 | Inter-market flows | No |
| Event-Driven | 3 | Catalysts & events | No |
| Execution | 4 | Trade optimization | No |
| Risk Management | 4 | Portfolio risk | **Yes** |
| Aggregation | Final | Synthesis | No |
| Learning | Final | Feedback loop | No |
| Synthesis | Final | Final output | No |

---

## Phase 1: Data Collection

### Macro Economics Agent

**Purpose**: Analyze macroeconomic conditions affecting equity markets.

**Data Sources**:
- FRED (Federal Reserve Economic Data)
- Bureau of Labor Statistics
- Federal Reserve announcements

**Analysis Focus**:
- GDP growth and trends
- Inflation metrics (CPI, PPI, PCE)
- Employment data
- Interest rate environment
- Fed policy stance

**Output Format**:
```json
{
  "outlook": "neutral",
  "confidence": 0.7,
  "key_indicators": {
    "gdp_growth": 2.1,
    "inflation": 3.2,
    "unemployment": 4.1
  },
  "fed_stance": "hawkish",
  "market_impact": "Elevated rates continue to pressure valuations..."
}
```

---

### Geopolitical Agent

**Purpose**: Monitor and assess geopolitical risks affecting markets.

**Data Sources**:
- News APIs
- Government publications
- International relations data

**Analysis Focus**:
- Trade relations and tariffs
- Political stability
- Regional conflicts
- Regulatory changes
- Supply chain disruptions

**Output Format**:
```json
{
  "outlook": "cautious",
  "confidence": 0.6,
  "active_risks": [
    {"region": "Asia-Pacific", "severity": "moderate", "description": "..."},
    {"region": "Europe", "severity": "low", "description": "..."}
  ],
  "sectors_affected": ["Technology", "Energy"]
}
```

---

### Commodities Agent

**Purpose**: Track commodity markets and their equity implications.

**Data Sources**:
- Alpha Vantage
- EIA (Energy Information Administration)
- USDA

**Analysis Focus**:
- Oil and natural gas
- Precious metals (gold, silver)
- Base metals (copper, aluminum)
- Agricultural commodities
- Supply/demand dynamics

**Output Format**:
```json
{
  "outlook": "bullish",
  "confidence": 0.65,
  "commodities": {
    "oil": {"price": 78.50, "trend": "rising", "outlook": "bullish"},
    "gold": {"price": 2050, "trend": "stable", "outlook": "neutral"}
  },
  "equity_implications": "Energy sector likely to outperform..."
}
```

---

## Phase 2: Market Analysis

### Sentiment Agent

**Purpose**: Gauge market sentiment and investor psychology.

**Data Sources**:
- News sentiment analysis
- Social media trends
- Put/call ratios
- VIX levels

**Analysis Focus**:
- News tone and frequency
- Social media sentiment
- Options market positioning
- Fear/greed indicators
- Institutional flows

**Output Format**:
```json
{
  "outlook": "neutral",
  "confidence": 0.55,
  "sentiment_score": 0.45,
  "fear_greed_index": 52,
  "vix_level": 18.5,
  "notable_trends": ["Increased bearish options activity", "..."]
}
```

---

### Fundamentals Agent

**Purpose**: Evaluate company fundamentals and valuations.

**Data Sources**:
- Company filings (SEC)
- Earnings reports
- Analyst estimates

**Analysis Focus**:
- Revenue and earnings trends
- Valuation metrics (P/E, P/S, EV/EBITDA)
- Balance sheet health
- Cash flow analysis
- Competitive positioning

**Output Format**:
```json
{
  "outlook": "bullish",
  "confidence": 0.72,
  "market_valuation": {
    "sp500_pe": 22.5,
    "historical_avg": 18.2,
    "assessment": "moderately overvalued"
  },
  "sector_rankings": [
    {"sector": "Technology", "rating": "overweight"},
    {"sector": "Utilities", "rating": "underweight"}
  ]
}
```

---

### Technical Agent

**Purpose**: Analyze price patterns and technical indicators.

**Data Sources**:
- Price and volume data
- Technical indicator calculations

**Analysis Focus**:
- Trend identification
- Support/resistance levels
- Momentum indicators (RSI, MACD)
- Volume analysis
- Pattern recognition

**Output Format**:
```json
{
  "outlook": "bullish",
  "confidence": 0.68,
  "sp500_analysis": {
    "trend": "uptrend",
    "rsi": 58,
    "macd": "bullish crossover",
    "support": 4800,
    "resistance": 5100
  },
  "signals": ["Golden cross on daily chart", "Volume confirming breakout"]
}
```

---

### Alternative Data Agent

**Purpose**: Analyze non-traditional data sources for alpha generation.

**Data Sources**:
- Satellite imagery metrics
- Web traffic data
- App download trends
- Credit card spending

**Analysis Focus**:
- Real-time economic activity
- Consumer behavior patterns
- Corporate activity indicators
- Emerging trends

**Output Format**:
```json
{
  "outlook": "neutral",
  "confidence": 0.5,
  "signals": [
    {"source": "web_traffic", "sector": "E-commerce", "trend": "increasing"},
    {"source": "app_downloads", "sector": "Fintech", "trend": "stable"}
  ],
  "novel_insights": "..."
}
```

---

## Phase 3: Cross-Market Synthesis

### Cross-Asset Agent

**Purpose**: Analyze correlations and flows across asset classes.

**Analysis Focus**:
- Equity/bond correlations
- Currency impacts
- Sector rotation patterns
- Risk-on/risk-off dynamics
- International equity flows

**Output Format**:
```json
{
  "outlook": "cautious",
  "confidence": 0.62,
  "correlations": {
    "equity_bond": -0.3,
    "equity_usd": -0.15
  },
  "regime": "risk-off",
  "rotation_signals": ["Defensive sectors outperforming", "..."]
}
```

---

### Event-Driven Agent

**Purpose**: Identify and assess market-moving events.

**Analysis Focus**:
- Earnings calendar
- Economic data releases
- IPOs and M&A activity
- Dividend announcements
- Index rebalancing

**Output Format**:
```json
{
  "outlook": "neutral",
  "confidence": 0.6,
  "upcoming_events": [
    {"date": "2025-01-20", "event": "Fed Minutes", "impact": "high"},
    {"date": "2025-01-22", "event": "AAPL Earnings", "impact": "high"}
  ],
  "recent_catalysts": [...]
}
```

---

## Phase 4: Execution & Risk

### Execution Agent

**Purpose**: Optimize trade execution and timing.

**Analysis Focus**:
- Market microstructure
- Liquidity conditions
- Optimal execution strategies
- Slippage estimation
- Order flow analysis

**Output Format**:
```json
{
  "outlook": "neutral",
  "confidence": 0.65,
  "liquidity_assessment": "adequate",
  "execution_recommendations": {
    "strategy": "TWAP",
    "optimal_window": "10:00-14:00 ET",
    "estimated_slippage": "0.05%"
  }
}
```

---

### Risk Management Agent

**Purpose**: Assess portfolio risk and enforce risk limits.

**Special Authority**: **Can veto recommendations** if risk thresholds exceeded.

**Analysis Focus**:
- Portfolio VaR (Value at Risk)
- Maximum drawdown scenarios
- Concentration risk
- Correlation risk
- Tail risk assessment

**Output Format**:
```json
{
  "outlook": "cautious",
  "confidence": 0.75,
  "risk_metrics": {
    "portfolio_var_95": 0.025,
    "max_drawdown_estimate": 0.08,
    "concentration_score": 0.3
  },
  "veto_status": false,
  "warnings": ["Tech sector exposure approaching limit"],
  "recommendations": ["Consider hedging through put options"]
}
```

**Veto Conditions**:
- VaR exceeds configured threshold
- Drawdown limit would be breached
- Concentration exceeds limits
- Liquidity concerns

---

## Final Phase: Aggregation

### Aggregation Engine

**Purpose**: Synthesize all agent outputs into unified recommendations.

**Process**:
1. Collect all agent outputs
2. Weight by confidence and relevance
3. Identify consensus and divergences
4. Generate unified outlook
5. Apply risk agent veto if triggered

**Output Format**:
```json
{
  "overall_outlook": "moderately_bullish",
  "confidence": 0.68,
  "consensus_factors": ["Technical strength", "Solid fundamentals"],
  "divergent_views": ["Macro vs Technical on rate sensitivity"],
  "final_recommendations": [
    {"action": "maintain exposure", "confidence": 0.7},
    {"action": "hedge tail risk", "confidence": 0.6}
  ]
}
```

---

### Learning Agent

**Purpose**: Track prediction accuracy and improve models.

**Analysis Focus**:
- Historical prediction accuracy
- Agent performance tracking
- Model calibration
- Feedback incorporation

**Output Format**:
```json
{
  "performance_metrics": {
    "overall_accuracy_30d": 0.62,
    "best_performing_agent": "technical",
    "worst_performing_agent": "sentiment"
  },
  "calibration_suggestions": [...]
}
```

---

## Agent Configuration

Agents can be configured in Settings:

```json
{
  "agent_config": {
    "enabled_agents": ["macro", "technical", "fundamentals", "risk"],
    "default_model": "claude-sonnet-4-20250514",
    "agent_models": {
      "risk": "claude-sonnet-4-20250514",
      "aggregation": "claude-sonnet-4-20250514"
    },
    "confidence_threshold": 0.5,
    "max_tokens_per_agent": 4000
  }
}
```

Enable/disable agents via API:
```http
PUT /api/settings/agent_config/enabled_agents
Content-Type: application/json

{
  "value": ["macro", "technical", "risk", "aggregation"]
}
```
