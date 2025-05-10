# Service Architecture for Non-Docker Deployment

This document outlines the architecture of the Cryptobot application when deployed without Docker, including service relationships, communication patterns, and network configuration.

## System Architecture Overview

The Cryptobot application is a microservices-based cryptocurrency trading platform composed of several independent services that communicate with each other. In a non-Docker deployment, these services run directly on the host system rather than in containers.

![Architecture Diagram](../images/non-docker-architecture.png)

*Note: The above diagram reference is a placeholder. An actual architecture diagram should be created and placed in the docs/images directory.*

## Core Services

### Auth Service
- **Purpose**: Handles user authentication, authorization, and session management
- **Port**: 8000
- **Dependencies**: PostgreSQL, Redis
- **Communicates With**: All other services for authentication
- **Key Features**:
  - JWT token generation and validation
  - Two-factor authentication
  - User management
  - Session tracking

### Strategy Service
- **Purpose**: Manages trading strategies and their configurations
- **Port**: 8000 (requires configuration to avoid port conflict)
- **Dependencies**: PostgreSQL
- **Communicates With**: Trade Service, Backtest Service
- **Key Features**:
  - Strategy CRUD operations
  - Strategy parameter management
  - Strategy activation/deactivation

### Backtest Service
- **Purpose**: Performs historical backtesting of trading strategies
- **Port**: 8000 (requires configuration to avoid port conflict)
- **Dependencies**: SQLite, Redis, Celery
- **Communicates With**: Strategy Service, Data Service
- **Key Features**:
  - Historical data analysis
  - Strategy performance testing
  - Results visualization
  - Asynchronous task processing

### Trade Service
- **Purpose**: Executes trades on cryptocurrency exchanges
- **Port**: 8000 (requires configuration to avoid port conflict)
- **Dependencies**: PostgreSQL
- **Communicates With**: Strategy Service, Data Service, Exchange APIs
- **Key Features**:
  - Order execution
  - Position management
  - Exchange connectivity
  - Trade history tracking

### Data Service
- **Purpose**: Collects and provides market data
- **Port**: 8001
- **Dependencies**: Redis
- **Communicates With**: External exchanges, Backtest Service, Trade Service
- **Key Features**:
  - Real-time market data
  - Historical data storage
  - Data normalization
  - WebSocket data streaming

## MCP Services

### Paper Trading Service
- **Purpose**: Simulates trading without real money
- **Port**: 8002 (suggested)
- **Dependencies**: None
- **Communicates With**: Trade Service, Strategy Service
- **Key Features**:
  - Simulated order execution
  - Virtual balance management
  - Performance tracking

### Portfolio Management Service
- **Purpose**: Manages user portfolios and asset allocation
- **Port**: 8003 (suggested)
- **Dependencies**: None
- **Communicates With**: Trade Service, Data Service
- **Key Features**:
  - Portfolio tracking
  - Asset allocation
  - Performance metrics

### Reporting Service
- **Purpose**: Generates reports on trading performance
- **Port**: 8004 (suggested)
- **Dependencies**: None
- **Communicates With**: Trade Service, Portfolio Management Service
- **Key Features**:
  - Performance reporting
  - Visualization
  - Export capabilities

### Risk Management Service
- **Purpose**: Monitors and manages trading risk
- **Port**: 8005 (suggested)
- **Dependencies**: None
- **Communicates With**: Trade Service, Strategy Service
- **Key Features**:
  - Risk assessment
  - Position sizing
  - Exposure limits

### Strategy Execution Service
- **Purpose**: Executes trading strategies
- **Port**: 8006 (suggested)
- **Dependencies**: None
- **Communicates With**: Strategy Service, Trade Service
- **Key Features**:
  - Strategy execution
  - Signal generation
  - Execution timing

## External Dependencies

### PostgreSQL Database
- **Purpose**: Primary database for persistent storage
- **Port**: 5432
- **Used By**: Auth Service, Strategy Service, Trade Service
- **Data Stored**: User accounts, strategies, trades, settings

### Redis
- **Purpose**: Caching, session management, and message broker
- **Port**: 6379
- **Used By**: Auth Service, Data Service, Backtest Service
- **Data Stored**: Session data, cached market data, task queue

### External Cryptocurrency Exchanges
- **Purpose**: Provide market data and execute trades
- **Ports**: 443 (HTTPS)
- **Used By**: Data Service, Trade Service
- **Exchanges Supported**: Binance, Kraken, Coinbase

## Communication Patterns

### Service-to-Service Communication
- **Protocol**: HTTP/HTTPS
- **Format**: JSON
- **Authentication**: JWT tokens
- **Error Handling**: Standard HTTP status codes with detailed error messages

### Service-to-Database Communication
- **Protocol**: Native database protocols (PostgreSQL, SQLite)
- **Connection Pooling**: Implemented for efficient resource usage
- **Authentication**: Username/password or connection string

### External API Communication
- **Protocol**: HTTPS
- **Authentication**: API keys and secrets
- **Rate Limiting**: Implemented to respect exchange limits

## Network Configuration

### Internal Network
- All services communicate over localhost (127.0.0.1) in a non-Docker deployment
- Services must be configured with the correct host:port combinations
- No internal DNS is required, unlike in Docker

### Port Assignments
| Service | Default Port | Notes |
|---------|--------------|-------|
| Auth Service | 8000 | Primary authentication endpoint |
| Strategy Service | 8000 | Must be reconfigured to avoid conflict |
| Backtest Service | 8000 | Must be reconfigured to avoid conflict |
| Trade Service | 8000 | Must be reconfigured to avoid conflict |
| Data Service | 8001 | |
| Paper Trading | 8002 | Suggested port |
| Portfolio Management | 8003 | Suggested port |
| Reporting | 8004 | Suggested port |
| Risk Management | 8005 | Suggested port |
| Strategy Execution | 8006 | Suggested port |
| PostgreSQL | 5432 | Database server |
| Redis | 6379 | Cache and message broker |

### Port Conflict Resolution
In a non-Docker deployment, port conflicts must be manually resolved by:
1. Changing the port in the service configuration
2. Updating all services that communicate with the modified service
3. Ensuring firewall rules allow the new port

## Service Discovery

Unlike in Docker where service discovery can be handled by Docker's internal DNS, in a non-Docker deployment:

1. Services must be explicitly configured with the hostnames/IPs and ports of other services
2. Configuration files must be updated if service locations change
3. No automatic service discovery is available

## Configuration Management

### Environment Variables
- Each service requires specific environment variables
- These can be set in:
  - .env files in each service directory
  - System-wide environment variables
  - Service startup scripts

### Configuration Files
- JSON or YAML configuration files for each service
- Must be updated to reflect the non-Docker deployment
- Service URLs must be changed from Docker service names to localhost:port

## Scaling Considerations

### Vertical Scaling
- Services can be allocated more resources on the host machine
- Database connection pools should be sized appropriately

### Horizontal Scaling
- Multiple instances of stateless services can be run on different ports
- Load balancer required for distributing traffic
- Session stickiness may be required for certain services

## Monitoring and Logging

### Logging
- Each service logs to its own log file
- Log aggregation tool recommended for centralized logging
- Log rotation must be configured to manage disk space

### Monitoring
- Health check endpoints exposed by each service
- External monitoring tool recommended
- System metrics (CPU, memory, disk) should be monitored

## Security Considerations

### Authentication Between Services
- JWT tokens used for service-to-service authentication
- Token validation required for all protected endpoints

### Network Security
- Firewall rules to restrict access to service ports
- TLS/SSL for all external communications
- API keys stored securely

### Database Security
- Strong passwords for database access
- Least privilege principle for database users
- Regular security audits

## Deployment Process

For a non-Docker deployment, the following steps are required:

1. Install all system dependencies
2. Set up databases and message brokers
3. Install Python and create virtual environments
4. Install service-specific dependencies
5. Configure each service for the non-Docker environment
6. Start services in the correct order
7. Verify service connectivity and functionality

This architecture document provides a comprehensive overview of the Cryptobot application's structure when deployed without Docker. It should be used as a reference for system administrators and developers working with the application.