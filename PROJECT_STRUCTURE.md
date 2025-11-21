# Project Structure

```
call-center-ai-local/
│
├── app/                          # Main application code
│   ├── __init__.py
│   ├── main.py                   # FastAPI app initialization
│   ├── api/                      # API endpoints
│   │   ├── __init__.py
│   │   ├── v1/                   # API version 1
│   │   │   ├── __init__.py
│   │   │   ├── calls.py          # Call management endpoints
│   │   │   ├── health.py         # Health check endpoints
│   │   │   ├── metrics.py        # Metrics endpoints
│   │   │   └── websocket.py      # WebSocket handlers
│   │   └── deps.py               # API dependencies
│   │
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management
│   │   ├── security.py           # Security utilities
│   │   ├── logging.py            # Logging setup
│   │   └── exceptions.py         # Custom exceptions
│   │
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   ├── call.py               # Call-related models
│   │   ├── conversation.py       # Conversation models
│   │   ├── audio.py              # Audio-related models
│   │   └── database.py           # Database models
│   │
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── audio_processor.py    # Audio processing service
│   │   ├── call_manager.py       # Call management service
│   │   ├── conversation_manager.py # Conversation handling
│   │   ├── telephony/            # Telephony providers
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Base telephony interface
│   │   │   ├── twilio_handler.py # Twilio implementation
│   │   │   └── asterisk_handler.py # Asterisk implementation
│   │   ├── ai/                   # AI services
│   │   │   ├── __init__.py
│   │   │   ├── stt.py            # Speech-to-text service
│   │   │   ├── llm.py            # Language model service
│   │   │   └── tts.py            # Text-to-speech service
│   │   └── monitoring.py         # Monitoring service
│   │
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   ├── connection.py         # Database connection
│   │   ├── repositories/         # Data repositories
│   │   │   ├── __init__.py
│   │   │   ├── call_repository.py
│   │   │   └── conversation_repository.py
│   │   └── migrations/           # Database migrations
│   │       └── alembic/
│   │
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── audio.py              # Audio utilities
│       ├── validators.py         # Input validators
│       └── helpers.py            # General helpers
│
├── config/                       # Configuration files
│   ├── config.yaml               # Default configuration
│   ├── config-development.yaml   # Development config
│   ├── config-production.yaml    # Production config
│   └── logging_config.yaml       # Logging configuration
│
├── deployments/                  # Deployment configurations
│   ├── docker/                   # Docker files
│   │   ├── Dockerfile
│   │   ├── docker-compose.yml
│   │   └── docker-compose.prod.yml
│   ├── kubernetes/               # Kubernetes manifests
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── configmap.yaml
│   │   ├── secrets.yaml
│   │   └── ingress.yaml
│   └── terraform/                # Infrastructure as Code
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── scripts/                      # Utility scripts
│   ├── setup/                    # Setup scripts
│   │   ├── setup-local.sh
│   │   ├── setup-dev.sh
│   │   └── setup-prod.sh
│   ├── deployment/               # Deployment scripts
│   │   ├── deploy.sh
│   │   └── rollback.sh
│   ├── database/                 # Database scripts
│   │   ├── init_db.py
│   │   └── migrate.sh
│   └── monitoring/               # Monitoring scripts
│       └── health_check.sh
│
├── tests/                        # Test files
│   ├── __init__.py
│   ├── conftest.py               # Pytest configuration
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_audio_processor.py
│   │   ├── test_call_manager.py
│   │   └── test_services.py
│   ├── integration/              # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   └── test_telephony.py
│   ├── e2e/                      # End-to-end tests
│   │   └── test_call_flow.py
│   └── performance/              # Performance tests
│       └── locustfile.py
│
├── monitoring/                   # Monitoring configurations
│   ├── prometheus/
│   │   ├── prometheus.yml
│   │   └── alerts/
│   │       └── alerts.yml
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   └── logging/
│       └── fluentd.conf
│
├── docs/                         # Documentation
│   ├── api/                      # API documentation
│   │   └── openapi.yaml
│   ├── architecture/             # Architecture docs
│   │   ├── overview.md
│   │   └── diagrams/
│   ├── guides/                   # User guides
│   │   ├── installation.md
│   │   ├── configuration.md
│   │   └── troubleshooting.md
│   └── development/              # Developer docs
│       ├── contributing.md
│       └── code_style.md
│
├── models/                       # AI model files
│   ├── whisper/                  # Whisper models
│   ├── llm/                      # LLM models
│   └── tts/                      # TTS models
│
├── data/                         # Data files
│   ├── prompts/                  # System prompts
│   ├── responses/                # Canned responses
│   └── vocabularies/             # Custom vocabularies
│
├── .github/                      # GitHub specific
│   ├── workflows/                # GitHub Actions
│   │   ├── ci-cd.yml
│   │   ├── security.yml
│   │   └── codeql.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── nginx/                        # NGINX configuration
│   ├── nginx.conf
│   └── ssl/
│
├── secrets/                      # Secret files (gitignored)
│   └── .gitkeep
│
├── logs/                         # Log files (gitignored)
│   └── .gitkeep
│
├── cache/                        # Cache files (gitignored)
│   └── .gitkeep
│
├── .env.example                  # Environment variables example
├── .gitignore                    # Git ignore file
├── requirements.txt              # Python dependencies
├── requirements-dev.txt          # Development dependencies
├── requirements-prod.txt         # Production dependencies
├── pyproject.toml               # Python project configuration
├── setup.py                     # Package setup
├── Makefile                     # Make commands
├── README.md                    # Project documentation
├── LICENSE                      # License file
└── CHANGELOG.md                 # Change log
```

## Folder Descriptions

### `/app`
Core application code following clean architecture principles:
- **api/**: RESTful API endpoints and WebSocket handlers
- **core/**: Core functionality like config, security, logging
- **models/**: Pydantic models and database schemas
- **services/**: Business logic and external service integrations
- **db/**: Database layer with repositories pattern
- **utils/**: Shared utility functions

### `/config`
Configuration files for different environments using YAML format.

### `/deployments`
All deployment-related configurations:
- **docker/**: Containerization files
- **kubernetes/**: K8s manifests for orchestration
- **terraform/**: Infrastructure as Code

### `/scripts`
Utility scripts organized by purpose:
- **setup/**: Environment setup scripts
- **deployment/**: Deploy and rollback scripts
- **database/**: Database management scripts
- **monitoring/**: Health check and monitoring scripts

### `/tests`
Comprehensive test suite:
- **unit/**: Isolated component tests
- **integration/**: Service integration tests
- **e2e/**: Full workflow tests
- **performance/**: Load and stress tests

### `/monitoring`
Observability configurations:
- **prometheus/**: Metrics and alerts
- **grafana/**: Dashboards
- **logging/**: Log aggregation configs

### `/docs`
Complete documentation:
- **api/**: OpenAPI specs
- **architecture/**: System design docs
- **guides/**: User and admin guides
- **development/**: Developer documentation

### `/models`
Pre-trained AI models organized by type.

### `/data`
Static data files like prompts and responses.

### `/.github`
GitHub-specific files for CI/CD and community.

### `/nginx`
Web server configuration for production deployment.
