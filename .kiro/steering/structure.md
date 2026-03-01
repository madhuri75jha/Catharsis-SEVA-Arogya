---
inclusion: auto
---

# Project Structure

## Root Directory Layout

```
seva-arogya/
├── app.py                      # Main Flask application entry point
├── socketio_handlers.py        # WebSocket event handlers
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container image definition
├── .env                        # Local environment variables (gitignored)
├── .env.example               # Environment template
├── deploy_to_aws.sh           # Deployment automation script
│
├── aws_services/              # AWS service integration layer
├── models/                    # Data models (Prescription, Transcription)
├── utils/                     # Shared utilities (logger, error_handler)
├── migrations/                # Database migration scripts
├── templates/                 # Jinja2 HTML templates
├── static/                    # Frontend assets (JS, CSS)
├── tests/                     # Test suite
├── seva-arogya-infra/        # Terraform infrastructure code
├── scripts/                   # Deployment and validation scripts
└── .kiro/                     # Kiro configuration and specs
```

## Core Application Files

### `app.py`
Main Flask application with:
- Application initialization (`init_app()`)
- Route definitions (login, home, transcription, final-prescription)
- API endpoints (`/api/v1/*`)
- Health check endpoints (`/health`, `/health/aws-connectivity`)
- Authentication decorator (`@login_required`)
- Error handlers (404, 500)
- Signal handlers for graceful shutdown

### `socketio_handlers.py`
WebSocket event handlers for real-time features:
- Audio streaming for live transcription
- Real-time transcription updates
- Session management

## AWS Services Layer (`aws_services/`)

Modular AWS service managers following single-responsibility principle:

```
aws_services/
├── __init__.py
├── base_client.py              # Base AWS client with retry logic
├── config_manager.py           # Configuration and Secrets Manager
├── auth_manager.py             # Cognito authentication
├── storage_manager.py          # S3 file operations
├── transcribe_manager.py       # Transcribe Medical (batch)
├── transcribe_streaming_manager.py  # Transcribe Medical (streaming)
├── comprehend_manager.py       # Comprehend Medical entity extraction
├── database_manager.py         # PostgreSQL connection pooling
├── session_manager.py          # Session state management
├── audio_buffer.py             # Audio buffering for streaming
└── connectivity_checker.py     # AWS connectivity validation
```

Each manager:
- Inherits from `BaseClient` for consistent error handling
- Uses boto3 for AWS SDK operations
- Implements retry logic with exponential backoff
- Provides clean interface for app.py

## Data Models (`models/`)

```
models/
├── __init__.py
├── prescription.py            # Prescription data model
└── transcription.py           # Transcription job tracking
```

Models include:
- Class definitions with attributes
- `save()`, `update()`, `get_by_id()` methods
- SQL schema creation methods
- Validation logic

## Utilities (`utils/`)

```
utils/
├── __init__.py
├── logger.py                  # Structured logging setup
└── error_handler.py           # Centralized error handling
```

## Database Migrations (`migrations/`)

```
migrations/
├── migration_manager.py       # Migration orchestration
├── run_migration.py          # CLI migration runner
├── 001_add_streaming_columns.sql
└── README.md
```

Migration pattern:
- Sequential numbered SQL files
- MigrationManager tracks applied migrations in `schema_migrations` table
- Supports up/down migrations
- Auto-runs on application startup

## Frontend (`templates/` and `static/`)

### Templates (`templates/`)
```
templates/
├── base.html                  # Base template with shared layout
├── login.html                 # Authentication page
├── home.html                  # Dashboard/start consultation
├── transcription.html         # Voice capture page
├── live_transcription.html    # Streaming transcription
├── final_prescription.html    # Prescription review
├── 404.html                   # Not found error
└── 500.html                   # Server error
```

### Static Assets (`static/`)
```
static/
├── js/
│   ├── transcription-controller.js  # Transcription page logic
│   └── ...
└── README.md
```

Frontend architecture:
- Server-side rendering with Jinja2
- Tailwind CSS via CDN (no build step)
- Vanilla JavaScript (no framework)
- Material Symbols for icons

## Infrastructure (`seva-arogya-infra/`)

```
seva-arogya-infra/
├── main.tf                    # Root module orchestration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── locals.tf                  # Local computed values
├── versions.tf                # Provider versions
├── backend.tf.example         # Remote state template
│
├── modules/                   # Reusable Terraform modules
│   ├── vpc/                   # VPC, subnets, NAT gateway
│   ├── alb/                   # Application Load Balancer
│   ├── ecs/                   # ECS cluster and service
│   ├── rds/                   # PostgreSQL database
│   ├── s3/                    # S3 buckets
│   ├── cognito/               # User pool
│   ├── iam/                   # IAM roles and policies
│   └── secrets/               # Secrets Manager
│
└── scripts/                   # Helper scripts
    ├── pre_deploy_check.sh    # Pre-deployment validation
    └── validate_deployment.sh # Post-deployment health checks
```

## Testing (`tests/`)

```
tests/
├── __init__.py
├── conftest.py                # Pytest fixtures and configuration
├── test_transcription_page_bug_exploration.py  # Bug exploration tests
├── test_transcription_page_preservation.py     # Preservation tests
└── BUG_EXPLORATION_RESULTS.md
```

Testing approach:
- pytest for test framework
- Hypothesis for property-based testing
- Mock AWS services in tests
- Fixtures in `conftest.py` for app and client setup

## Kiro Configuration (`.kiro/`)

```
.kiro/
├── specs/                     # Feature and bugfix specifications
│   ├── aws-services-flask-integration/
│   ├── live-audio-transcription-streaming/
│   ├── terraform-aws-infrastructure/
│   └── transcription-page-not-starting/
│       ├── .config.kiro       # Spec metadata
│       ├── bugfix.md          # Bug requirements
│       ├── design.md          # Fix design
│       └── tasks.md           # Implementation tasks
│
└── steering/                  # AI assistant guidance
    ├── product.md             # Product overview
    ├── tech.md                # Tech stack and commands
    └── structure.md           # This file
```

## Key Conventions

### File Naming
- Python modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Terraform: `kebab-case.tf`

### Import Organization
1. Standard library imports
2. Third-party imports (Flask, boto3, etc.)
3. Local application imports
4. Blank line between groups

### Error Handling
- Use `try/except` with specific exceptions
- Log errors with context using `logging.getLogger(__name__)`
- Return meaningful error messages to clients
- Use `handle_aws_error()` utility for AWS exceptions

### Configuration
- Environment-specific config in `.env`
- Secrets in AWS Secrets Manager (production)
- Config loaded via `ConfigManager` class
- Never commit secrets to git

### Database Access
- All queries through `DatabaseManager`
- Use parameterized queries (no string interpolation)
- Connection pooling managed automatically
- Transactions for multi-step operations
