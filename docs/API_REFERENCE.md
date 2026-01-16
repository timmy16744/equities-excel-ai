# API Reference

Base URL: `http://localhost:8000`

## Authentication

Most endpoints require JWT authentication.

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password"
}
```

Response:
```json
{
  "access_token": "eyJhbG...",
  "refresh_token": "eyJhbG...",
  "token_type": "bearer"
}
```

### Using Tokens
Include the access token in the Authorization header:
```http
Authorization: Bearer eyJhbG...
```

### Refresh Token
```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbG..."
}
```

---

## Analysis Endpoints

### Trigger Full Analysis
```http
POST /api/analyze
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbols": ["AAPL", "MSFT", "GOOGL"],
  "depth": "full"
}
```

Response:
```json
{
  "workflow_id": "wf_123abc",
  "status": "started",
  "estimated_agents": 14
}
```

### Get Workflow Status
```http
GET /api/analyze/{workflow_id}/status
Authorization: Bearer {token}
```

Response:
```json
{
  "workflow_id": "wf_123abc",
  "status": "running",
  "progress": {
    "completed": 8,
    "total": 14,
    "current_phase": 2
  },
  "agents_completed": ["macro", "geopolitical", "commodities", ...]
}
```

### Get Latest Insights
```http
GET /api/insights/latest
Authorization: Bearer {token}
```

Response:
```json
{
  "timestamp": "2025-01-17T12:00:00Z",
  "overall_outlook": "bullish",
  "confidence": 0.72,
  "key_factors": [...],
  "recommendations": [...],
  "risk_assessment": {...}
}
```

---

## Agent Endpoints

### List All Agents
```http
GET /api/agents
Authorization: Bearer {token}
```

Response:
```json
{
  "agents": [
    {
      "id": "macro",
      "name": "Macro Economics Agent",
      "enabled": true,
      "last_run": "2025-01-17T11:30:00Z",
      "status": "idle"
    },
    ...
  ]
}
```

### Get Agent Details
```http
GET /api/agents/{agent_id}
Authorization: Bearer {token}
```

### Get Agent's Latest Output
```http
GET /api/agents/{agent_id}/latest
Authorization: Bearer {token}
```

Response:
```json
{
  "agent_id": "macro",
  "timestamp": "2025-01-17T11:30:00Z",
  "analysis": {
    "outlook": "neutral",
    "confidence": 0.65,
    "key_points": [...],
    "data_sources": [...],
    "raw_output": "..."
  }
}
```

### Run Specific Agent
```http
POST /api/agents/{agent_id}/run
Authorization: Bearer {token}
Content-Type: application/json

{
  "force_refresh": true
}
```

### Get Agent History
```http
GET /api/agents/{agent_id}/history?limit=10&offset=0
Authorization: Bearer {token}
```

---

## Settings Endpoints

### Get All Settings
```http
GET /api/settings
Authorization: Bearer {token}
```

Response:
```json
{
  "api_config": {
    "anthropic_api_key": "sk-***masked***",
    "alpha_vantage_api_key": "***masked***",
    "request_timeout": 30
  },
  "agent_config": {
    "enabled_agents": ["macro", "technical", ...],
    "default_model": "claude-sonnet-4-20250514"
  },
  "risk_management": {
    "max_position_size": 0.1,
    "max_drawdown": 0.15
  },
  ...
}
```

### Get Settings by Category
```http
GET /api/settings/{category}
Authorization: Bearer {token}
```

### Update a Setting
```http
PUT /api/settings/{category}/{key}
Authorization: Bearer {token}
Content-Type: application/json

{
  "value": "new_value"
}
```

### Reset Settings to Defaults
```http
POST /api/settings/reset?confirm=true
Authorization: Bearer {token}
```

### Export Settings
```http
GET /api/settings/export
Authorization: Bearer {token}
```

### Import Settings
```http
POST /api/settings/import
Authorization: Bearer {token}
Content-Type: application/json

{
  "settings": {...}
}
```

---

## Portfolio Endpoints

### Get Portfolio Summary
```http
GET /api/portfolio
Authorization: Bearer {token}
```

### Add Position
```http
POST /api/portfolio/positions
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "AAPL",
  "quantity": 100,
  "entry_price": 150.00
}
```

### Update Position
```http
PUT /api/portfolio/positions/{position_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "quantity": 150,
  "notes": "Added to position"
}
```

### Close Position
```http
DELETE /api/portfolio/positions/{position_id}
Authorization: Bearer {token}
```

---

## WebSocket Endpoints

### Real-time Updates
```
ws://localhost:8000/ws/updates
```

Connect and receive events:
```json
{
  "type": "agent_update",
  "data": {
    "agent_id": "macro",
    "status": "completed",
    "summary": "..."
  }
}
```

Event types:
- `agent_update` - Agent completed analysis
- `workflow_progress` - Workflow phase change
- `insight_update` - New aggregated insight
- `error` - Error occurred

### Settings Changes
```
ws://localhost:8000/ws/settings
```

Receive notifications when settings change.

---

## Health Endpoints

### Basic Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Detailed Readiness Check
```http
GET /health/ready
```

Response:
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "external_apis": {
      "alpha_vantage": "ok",
      "fred": "ok"
    }
  }
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [...]
  }
}
```

Common HTTP status codes:
- `400` - Bad request / validation error
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not found
- `429` - Rate limit exceeded
- `500` - Internal server error

---

## Rate Limiting

Default limits:
- 100 requests per minute per user
- 10 analysis triggers per hour
- WebSocket: 1 connection per user

Headers returned:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705500000
```
