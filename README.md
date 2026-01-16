# Equities AI - Excel Interface

A professional-grade equity analysis platform featuring an Excel-styled interface backed by a multi-agent AI system. 14 specialized AI agents work together using LangGraph orchestration to provide comprehensive market analysis.

## Features

### Excel-Styled Interface
- Familiar spreadsheet-based UI with toolbar, formula bar, and status indicators
- Real-time WebSocket updates for live market data
- Multiple views: Dashboard, Agents, Portfolio, Performance, Signals, Risk, Execution
- Sheet tabs for organized data access
- Responsive design with theme support

### AI Analysis System
14 specialized agents working in orchestrated phases:

| Agent | Focus Area |
|-------|------------|
| Macro Economics | GDP, inflation, Fed policy, employment |
| Geopolitical | Global events, trade relations, political risk |
| Commodities | Oil, metals, agricultural markets |
| Sentiment | News, social media, market psychology |
| Fundamentals | Company financials, earnings, valuations |
| Technical | Price patterns, momentum, volume analysis |
| Alternative Data | Non-traditional signals and datasets |
| Cross-Asset | Inter-market correlations and flows |
| Event-Driven | Earnings, IPOs, M&A, catalysts |
| Execution | Order flow, timing, slippage optimization |
| Risk Management | Portfolio risk with veto authority |
| Learning | Performance feedback and model adaptation |
| Aggregation | Synthesis of all agent outputs |

### Backend Infrastructure
- FastAPI with async support
- PostgreSQL with pgvector for embeddings
- Redis for caching and pub/sub
- LangGraph for agent orchestration
- WebSocket for real-time updates
- JWT authentication

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- API key for at least one AI provider (Anthropic, OpenAI, or Google)

### 1. Clone and Configure

```bash
git clone https://github.com/your-username/equities-excel-ai.git
cd equities-excel-ai
cp .env.example .env
# Edit .env with your credentials
```

### 2. Start Infrastructure

```bash
cd docker
docker-compose up -d
```

This starts PostgreSQL and Redis.

### 3. Run the Backend

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.api.main:app --reload --port 8000
```

### 4. Run the Frontend

In a new terminal:

```bash
cd frontend
python server.py
```

### 5. Access the Application

- **Excel Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

### 6. Configure API Keys

Navigate to Settings in the UI or use the API:

```bash
curl -X PUT http://localhost:8000/api/settings/api_config/anthropic_api_key \
  -H "Content-Type: application/json" \
  -d '{"value": "your-api-key"}'
```

## Project Structure

```
equities-excel-ai/
├── frontend/                # Excel-styled web interface
│   ├── index.html          # Main HTML
│   ├── styles.css          # Excel-inspired styling
│   ├── app.js              # Application logic
│   ├── api.js              # REST API client
│   ├── spreadsheet.js      # Grid rendering
│   ├── websocket.js        # Real-time updates
│   └── server.py           # Development server
│
├── backend/                 # FastAPI backend
│   ├── agents/             # 14 AI agents
│   ├── api/                # REST endpoints
│   ├── database/           # SQLAlchemy models
│   ├── orchestration/      # LangGraph workflows
│   ├── settings/           # Configuration system
│   ├── data/               # External API clients
│   └── utils/              # Shared utilities
│
├── docker/                  # Container configuration
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.prod.yml
│
├── scripts/                 # Utility scripts
│   ├── install.sh
│   ├── start.sh
│   ├── stop.sh
│   └── backup.sh
│
├── docs/                    # Documentation
│   ├── INSTALLATION.md
│   ├── DEPLOYMENT.md
│   └── TROUBLESHOOTING.md
│
├── requirements.txt         # Python dependencies
└── .env.example            # Environment template
```

## API Endpoints

### Analysis
- `POST /api/analyze` - Trigger full analysis workflow
- `GET /api/agents/{agent_id}/latest` - Get latest agent output
- `GET /api/insights/latest` - Get aggregated insights
- `POST /api/agents/{agent_id}/run` - Run specific agent

### Settings
- `GET /api/settings` - Get all settings
- `PUT /api/settings/{category}/{key}` - Update a setting
- `POST /api/settings/reset?confirm=true` - Reset to defaults

### WebSocket
- `ws://localhost:8000/ws/updates` - Real-time agent updates
- `ws://localhost:8000/ws/settings` - Settings change notifications

## Configuration

All configuration is managed through the database-backed settings system:

| Category | Description |
|----------|-------------|
| `api_config` | API keys, rate limits, timeouts |
| `agent_config` | Enable/disable agents, model selection |
| `risk_management` | Position limits, drawdown tolerance |
| `scheduling` | Cron schedules for each agent |
| `performance` | Token budgets, cost alerts |

## Supported AI Providers

- **Anthropic Claude** (recommended)
- **OpenAI GPT-4**
- **Google Gemini**

Configure your preferred provider in Settings.

## Development

### Running Tests

```bash
pytest tests/ -v
pytest --cov=backend tests/
```

### Code Quality

```bash
black backend/
ruff check backend/
mypy backend/
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Excel-Styled Frontend                          │
│              (HTML/CSS/JS - No build required)                  │
├─────────────────────────────────────────────────────────────────┤
│                    FastAPI + WebSocket                          │
├─────────────────────────────────────────────────────────────────┤
│                  LangGraph Orchestrator                         │
│    ┌─────────────────────────────────────────────────────┐     │
│    │  Phase 1: Data    │  Phase 2: Analysis  │  Phase 3  │     │
│    │  Collection       │  & Synthesis        │  Risk     │     │
│    └─────────────────────────────────────────────────────┘     │
├────────┬────────┬────────┬────────┬────────┬────────┬──────────┤
│ Macro  │  Geo   │Commod. │Sentim. │Fundam. │ Tech   │ + 8 more │
├────────┴────────┴────────┴────────┴────────┴────────┴──────────┤
│              Aggregation Engine + Risk Veto                     │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL (pgvector)  │  Redis Cache  │  External APIs       │
└─────────────────────────────────────────────────────────────────┘
```

## License

MIT License - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
