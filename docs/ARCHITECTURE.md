# Equities AI Architecture

## System Overview

Equities AI is a multi-agent system for equity market analysis. The platform consists of three main components:

1. **Excel-Styled Frontend** - Browser-based spreadsheet interface
2. **FastAPI Backend** - REST API and WebSocket server
3. **LangGraph Orchestrator** - AI agent coordination

```
┌─────────────────────────────────────────────────────────────────┐
│                    Client (Browser)                              │
│              Excel-Styled HTML/CSS/JS Interface                  │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────┴─────────────────────────────────────┐
│                     FastAPI Backend                              │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│   │  REST API   │  │  WebSocket  │  │  Background Tasks   │    │
│   │  Endpoints  │  │   Server    │  │     (Celery)        │    │
│   └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘    │
└──────────┼────────────────┼────────────────────┼────────────────┘
           │                │                    │
┌──────────┴────────────────┴────────────────────┴────────────────┐
│                   LangGraph Orchestrator                         │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    Workflow Engine                       │   │
│   │  Phase 1 → Phase 2 → Phase 3 → Phase 4 → Aggregation    │   │
│   └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│   ┌──────────────────────────┴───────────────────────────────┐  │
│   │                    Agent Pool                             │  │
│   │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │  │
│   │  │ Macro │ │  Geo  │ │Commod.│ │Sentim.│ │Fundam.│      │  │
│   │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘      │  │
│   │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐      │  │
│   │  │ Tech  │ │ Alt.  │ │Cross-A│ │ Event │ │ Exec  │      │  │
│   │  └───────┘ └───────┘ └───────┘ └───────┘ └───────┘      │  │
│   │  ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐                │  │
│   │  │ Risk  │ │ Agg.  │ │Learning│ │Synth. │                │  │
│   │  └───────┘ └───────┘ └───────┘ └───────┘                │  │
│   └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┴───────────────────────────────────┐
│                      Data Layer                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│   │ PostgreSQL  │  │    Redis    │  │   External APIs     │    │
│   │  (pgvector) │  │   (Cache)   │  │ (Markets, News...)  │    │
│   └─────────────┘  └─────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Layer

The Excel-styled frontend provides a familiar spreadsheet interface:

- **index.html** - Main structure with toolbar, grid, and status bar
- **styles.css** - Excel-inspired visual styling
- **app.js** - Application state and UI coordination
- **api.js** - REST API client with retry logic
- **spreadsheet.js** - Grid rendering and cell management
- **websocket.js** - Real-time update handling
- **server.py** - Simple development server

The frontend operates in two modes:
1. **Demo Mode** - Works standalone with simulated data
2. **Connected Mode** - Full integration with backend API

### Backend Layer

FastAPI application providing:

```
backend/
├── api/
│   ├── main.py          # Application entry point
│   ├── routes/          # API endpoint handlers
│   │   ├── analysis.py  # Analysis triggers
│   │   ├── agents.py    # Agent management
│   │   ├── settings.py  # Configuration
│   │   └── websocket.py # Real-time updates
│   └── middleware/      # Auth, CORS, logging
├── agents/              # AI agent implementations
├── database/            # SQLAlchemy models
├── orchestration/       # LangGraph workflows
├── settings/            # Configuration management
└── utils/               # Shared utilities
```

### Agent Orchestration

Agents execute in coordinated phases:

#### Phase 1: Data Collection
- Macro Economics Agent
- Geopolitical Agent
- Commodities Agent

#### Phase 2: Market Analysis
- Sentiment Agent
- Fundamentals Agent
- Technical Agent
- Alternative Data Agent

#### Phase 3: Cross-Market Synthesis
- Cross-Asset Agent
- Event-Driven Agent

#### Phase 4: Execution & Risk
- Execution Agent
- Risk Management Agent (with veto authority)

#### Final Phase: Aggregation
- Aggregation Engine
- Learning Agent (feedback loop)

### Data Flow

```
1. User triggers analysis via UI
       │
       ▼
2. REST API receives request
       │
       ▼
3. LangGraph workflow initiated
       │
       ▼
4. Agents execute in phases
   - Each agent fetches relevant data
   - AI model generates analysis
   - Results stored in database
       │
       ▼
5. WebSocket broadcasts updates
       │
       ▼
6. Frontend renders results in grid
       │
       ▼
7. Risk agent applies veto if needed
       │
       ▼
8. Final aggregated output displayed
```

### Database Schema

Key tables:

- **agent_outputs** - Raw analysis from each agent
- **insights** - Aggregated insights and recommendations
- **settings** - Configuration key-value pairs
- **audit_log** - Change tracking
- **positions** - Portfolio positions (if using execution features)

### Caching Strategy

Redis is used for:

- **Session caching** - User session data
- **API response caching** - Frequently accessed data
- **Pub/Sub** - Real-time event broadcasting
- **Rate limiting** - API throttling

### External APIs

The system integrates with:

| Provider | Data Type | Rate Limit |
|----------|-----------|------------|
| Alpha Vantage | Market quotes, fundamentals | 5 calls/min (free) |
| FRED | Economic indicators | 120 calls/min |
| News API | Headlines, articles | 100 calls/day (free) |
| Yahoo Finance | Real-time quotes | Varies |

### Security

- JWT-based authentication
- Role-based access control
- API key encryption at rest
- CORS configuration
- Input validation on all endpoints

## Deployment Patterns

### Development
```
Frontend (localhost:3000) → Backend (localhost:8000)
                                    ↓
                           PostgreSQL (localhost:5432)
                           Redis (localhost:6379)
```

### Production
```
                    Load Balancer
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Frontend       Frontend       Frontend
      (Static)       (Static)       (Static)
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                   API Gateway
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Backend        Backend        Backend
       Instance       Instance       Instance
          │              │              │
          └──────────────┼──────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      PostgreSQL     Redis          Celery
      (Primary)      Cluster        Workers
```

## Performance Considerations

- Agent execution is parallelized where possible
- Database queries use connection pooling
- Heavy computations offloaded to Celery workers
- WebSocket connections managed with connection limits
- Frontend uses debouncing for frequent updates
