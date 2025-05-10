# Dependency Inventory for Non-Docker Deployment

This document provides a comprehensive inventory of all dependencies required for the Cryptobot application when deployed without Docker.

## Core System Dependencies

### Database Systems
| Dependency | Version | Purpose | Installation Command |
|------------|---------|---------|---------------------|
| PostgreSQL | 13.0+ | Primary database for auth, strategy, and trade services | `sudo apt install postgresql-13` (Ubuntu) |
| SQLite | 3.35.0+ | Database for backtest service | Included with Python |
| Redis | 6.2+ | Caching, session management, and message broker | `sudo apt install redis-server` (Ubuntu) |

### System Libraries
| Dependency | Version | Purpose | Installation Command |
|------------|---------|---------|---------------------|
| Python | 3.10+ | Runtime environment for all services | `sudo apt install python3.10 python3.10-venv python3.10-dev` (Ubuntu) |
| pip | Latest | Python package manager | Included with Python |
| libpq-dev | Latest | PostgreSQL development headers | `sudo apt install libpq-dev` (Ubuntu) |
| build-essential | Latest | Compilation tools for native extensions | `sudo apt install build-essential` (Ubuntu) |
| curl | Latest | Health checks and API testing | `sudo apt install curl` (Ubuntu) |

## Python Package Dependencies by Service

### Auth Service
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.95.2 | Web framework |
| uvicorn | 0.22.0 | ASGI server |
| pydantic | 1.10.7 | Data validation |
| python-multipart | 0.0.6 | Form data parsing |
| email-validator | 2.0.0 | Email validation |
| python-jose | 3.3.0 | JWT token handling |
| passlib | 1.7.4 | Password hashing |
| argon2-cffi | 21.3.0 | Password hashing |
| pyotp | 2.8.0 | Two-factor authentication |
| qrcode | 7.4.2 | QR code generation for 2FA |
| sqlalchemy | 2.0.15 | ORM for database access |
| alembic | 1.10.4 | Database migrations |
| psycopg2-binary | 2.9.6 | PostgreSQL driver |
| pymysql | 1.1.0 | MySQL driver (alternative DB) |
| redis | 4.5.5 | Redis client |
| httpx | 0.24.1 | HTTP client |
| cachetools | 5.3.1 | Caching utilities |
| python-dotenv | 1.0.0 | Environment variable management |

### Strategy Service
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.95.2 | Web framework |
| uvicorn | 0.22.0 | ASGI server |
| sqlalchemy | 2.0.6 | ORM for database access |
| python-dotenv | 1.0.0 | Environment variable management |
| pydantic | 1.10.7 | Data validation |
| httpx | 0.24.1 | HTTP client |
| PyJWT | 2.6.0 | JWT token handling |

### Backtest Service
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.95.0 | Web framework |
| uvicorn | >=0.21.0 | ASGI server |
| pydantic | >=1.10.0 | Data validation |
| python-dotenv | >=0.21.0 | Environment variable management |
| backtesting | >=0.3.3 | Backtesting framework |
| pandas | >=1.5.0 | Data analysis |
| numpy | >=1.23.0 | Numerical computing |
| sqlalchemy | >=2.0.0 | ORM for database access |
| python-multipart | >=0.0.5 | Form data parsing |
| asyncpg | >=0.27.0 | Async PostgreSQL driver |
| celery | >=5.2.7 | Task queue |
| redis | >=4.5.5 | Redis client for Celery |

### Trade Service
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.95.2 | Web framework |
| uvicorn | 0.22.0 | ASGI server |
| slowapi | 0.1.7 | Rate limiting |
| python-multipart | 0.0.6 | Form data parsing |
| sqlalchemy | 2.0.6 | ORM for database access |
| ccxt | 3.0.74 | Cryptocurrency exchange API |
| python-dotenv | 1.0.0 | Environment variable management |

### Data Service
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | Latest | Web framework |
| uvicorn | Latest | ASGI server |
| pydantic | Latest | Data validation |
| redis | Latest | Caching |
| sqlalchemy | Latest | ORM for database access |
| pandas | Latest | Data analysis |
| numpy | Latest | Numerical computing |
| python-dotenv | Latest | Environment variable management |

### MCP Services
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.95.2 | Web framework |
| uvicorn | 0.22.0 | ASGI server |
| python-dotenv | 1.0.0 | Environment variable management |
| pydantic | 1.10.7 | Data validation |
| requests | 2.28.2 | HTTP client |
| pytest | 7.0.1 | Testing framework |

## Dependency Installation Scripts

### Ubuntu/Debian Installation Script
```bash
#!/bin/bash

# Update package lists
sudo apt update

# Install system dependencies
sudo apt install -y python3.10 python3.10-venv python3.10-dev
sudo apt install -y postgresql-13 postgresql-contrib
sudo apt install -y redis-server
sudo apt install -y build-essential libpq-dev
sudo apt install -y curl git

# Set up Python virtual environment
python3.10 -m venv venv
source venv/bin/activate

# Install common Python packages
pip install --upgrade pip
pip install wheel setuptools

# Install service-specific dependencies
# (These would be installed in separate virtual environments for each service)
```

### Windows Installation Script
```powershell
# Install Chocolatey if not already installed
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
}

# Install system dependencies
choco install -y python --version=3.10.0
choco install -y postgresql
choco install -y redis-64
choco install -y git

# Set up Python virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install common Python packages
pip install --upgrade pip
pip install wheel setuptools

# Install service-specific dependencies
# (These would be installed in separate virtual environments for each service)
```

## Dependency Conflicts and Resolutions

### Python Version Conflicts
- **Issue**: Auth service uses Python 3.9, while Strategy and Trade services use Python 3.10
- **Resolution**: Standardize on Python 3.10 for all services, as it's backward compatible with Python 3.9 code

### SQLAlchemy Version Conflicts
- **Issue**: Different services use different versions of SQLAlchemy (2.0.6, 2.0.15)
- **Resolution**: Standardize on SQLAlchemy 2.0.15 for all services

### Redis Version Conflicts
- **Issue**: Different services specify different Redis client versions
- **Resolution**: Standardize on Redis 4.5.5 for all services

## Dependency Management Strategy

1. **Virtual Environments**: Use separate virtual environments for each service to isolate dependencies
2. **Requirements Files**: Maintain service-specific requirements.txt files
3. **Version Pinning**: Pin specific versions to ensure consistency
4. **Dependency Updates**: Regular schedule for updating dependencies
5. **Vulnerability Scanning**: Regular scanning for security vulnerabilities

This inventory provides a comprehensive overview of all dependencies required for the Cryptobot application. It should be updated whenever dependencies change or new services are added.