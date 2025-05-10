#!/bin/bash
# setup_parallel_env.sh
# Script to set up parallel Docker and non-Docker environments for Cryptobot
# Part of Phase 11: Parallel Operation Strategy

set -e

echo "=== Cryptobot Parallel Environment Setup ==="
echo "This script will configure both Docker and non-Docker environments to run simultaneously."

# Check if running with sudo/root
if [ "$(id -u)" -ne 0 ]; then
    echo "This script requires root privileges. Please run with sudo."
    exit 1
fi

# Define directories
DOCKER_ENV_DIR="/opt/cryptobot/docker"
NON_DOCKER_ENV_DIR="/opt/cryptobot/non-docker"
SHARED_DATA_DIR="/opt/cryptobot/shared_data"
LOG_DIR="/var/log/cryptobot"

# Create directories
echo "Creating directory structure..."
mkdir -p $DOCKER_ENV_DIR
mkdir -p $NON_DOCKER_ENV_DIR
mkdir -p $SHARED_DATA_DIR
mkdir -p $LOG_DIR
mkdir -p $SHARED_DATA_DIR/database
mkdir -p $SHARED_DATA_DIR/historical_data
mkdir -p $SHARED_DATA_DIR/user_data
mkdir -p $SHARED_DATA_DIR/config

# Set permissions
echo "Setting directory permissions..."
chown -R $(whoami):$(whoami) $DOCKER_ENV_DIR
chown -R $(whoami):$(whoami) $NON_DOCKER_ENV_DIR
chown -R $(whoami):$(whoami) $SHARED_DATA_DIR
chown -R $(whoami):$(whoami) $LOG_DIR

# Configure Docker environment
echo "Configuring Docker environment..."
# Create Docker Compose override file to use shared volumes
cat > $DOCKER_ENV_DIR/docker-compose.override.yml << EOF
version: '3'

services:
  postgres:
    volumes:
      - $SHARED_DATA_DIR/database:/var/lib/postgresql/data
    ports:
      - "5432:5432"
      
  redis:
    volumes:
      - $SHARED_DATA_DIR/redis:/data
    ports:
      - "6379:6379"
      
  auth:
    volumes:
      - $SHARED_DATA_DIR/config:/app/config
      - $LOG_DIR:/app/logs
    ports:
      - "8000:8000"
      
  strategy:
    volumes:
      - $SHARED_DATA_DIR/config:/app/config
      - $LOG_DIR:/app/logs
    ports:
      - "8001:8001"
      
  backtest:
    volumes:
      - $SHARED_DATA_DIR/historical_data:/app/data
      - $SHARED_DATA_DIR/config:/app/config
      - $LOG_DIR:/app/logs
    ports:
      - "8002:8002"
      
  trade:
    volumes:
      - $SHARED_DATA_DIR/user_data:/app/user_data
      - $SHARED_DATA_DIR/config:/app/config
      - $LOG_DIR:/app/logs
    ports:
      - "8003:8003"
      
  data:
    volumes:
      - $SHARED_DATA_DIR/historical_data:/app/data
      - $SHARED_DATA_DIR/config:/app/config
      - $LOG_DIR:/app/logs
    ports:
      - "8004:8004"
EOF

# Configure non-Docker environment
echo "Configuring non-Docker environment..."
# Create configuration file for non-Docker services
cat > $NON_DOCKER_ENV_DIR/config.json << EOF
{
  "shared_data_dir": "$SHARED_DATA_DIR",
  "log_dir": "$LOG_DIR",
  "database": {
    "host": "localhost",
    "port": 5432,
    "user": "cryptobot",
    "password": "use_env_var_in_production",
    "database": "cryptobot"
  },
  "redis": {
    "host": "localhost",
    "port": 6379
  },
  "services": {
    "auth": {
      "host": "localhost",
      "port": 9000,
      "config_dir": "$SHARED_DATA_DIR/config",
      "log_dir": "$LOG_DIR"
    },
    "strategy": {
      "host": "localhost",
      "port": 9001,
      "config_dir": "$SHARED_DATA_DIR/config",
      "log_dir": "$LOG_DIR"
    },
    "backtest": {
      "host": "localhost",
      "port": 9002,
      "data_dir": "$SHARED_DATA_DIR/historical_data",
      "config_dir": "$SHARED_DATA_DIR/config",
      "log_dir": "$LOG_DIR"
    },
    "trade": {
      "host": "localhost",
      "port": 9003,
      "user_data_dir": "$SHARED_DATA_DIR/user_data",
      "config_dir": "$SHARED_DATA_DIR/config",
      "log_dir": "$LOG_DIR"
    },
    "data": {
      "host": "localhost",
      "port": 9004,
      "data_dir": "$SHARED_DATA_DIR/historical_data",
      "config_dir": "$SHARED_DATA_DIR/config",
      "log_dir": "$LOG_DIR"
    }
  }
}
EOF

# Configure networking
echo "Configuring networking for parallel operation..."
# Create hosts file entries for service discovery
cat >> /etc/hosts << EOF
# Cryptobot parallel environment service discovery
127.0.0.1 auth-docker auth-non-docker
127.0.0.1 strategy-docker strategy-non-docker
127.0.0.1 backtest-docker backtest-non-docker
127.0.0.1 trade-docker trade-non-docker
127.0.0.1 data-docker data-non-docker
EOF

# Create environment variables file
cat > $SHARED_DATA_DIR/config/environment.sh << EOF
#!/bin/bash
# Environment variables for Cryptobot parallel environment

# Shared directories
export CRYPTOBOT_SHARED_DATA_DIR="$SHARED_DATA_DIR"
export CRYPTOBOT_LOG_DIR="$LOG_DIR"

# Database configuration
export CRYPTOBOT_DB_HOST="localhost"
export CRYPTOBOT_DB_PORT="5432"
export CRYPTOBOT_DB_USER="cryptobot"
export CRYPTOBOT_DB_PASSWORD="use_env_var_in_production"
export CRYPTOBOT_DB_NAME="cryptobot"

# Redis configuration
export CRYPTOBOT_REDIS_HOST="localhost"
export CRYPTOBOT_REDIS_PORT="6379"

# Docker service ports (8000-8004)
export CRYPTOBOT_DOCKER_AUTH_PORT="8000"
export CRYPTOBOT_DOCKER_STRATEGY_PORT="8001"
export CRYPTOBOT_DOCKER_BACKTEST_PORT="8002"
export CRYPTOBOT_DOCKER_TRADE_PORT="8003"
export CRYPTOBOT_DOCKER_DATA_PORT="8004"

# Non-Docker service ports (9000-9004)
export CRYPTOBOT_NON_DOCKER_AUTH_PORT="9000"
export CRYPTOBOT_NON_DOCKER_STRATEGY_PORT="9001"
export CRYPTOBOT_NON_DOCKER_BACKTEST_PORT="9002"
export CRYPTOBOT_NON_DOCKER_TRADE_PORT="9003"
export CRYPTOBOT_NON_DOCKER_DATA_PORT="9004"

# Parallel environment flag
export CRYPTOBOT_PARALLEL_ENV="true"
EOF

chmod +x $SHARED_DATA_DIR/config/environment.sh

echo "Creating service startup scripts..."
# Create startup script for non-Docker services
cat > $NON_DOCKER_ENV_DIR/start_services.sh << EOF
#!/bin/bash
# Start non-Docker Cryptobot services

source $SHARED_DATA_DIR/config/environment.sh

echo "Starting non-Docker Cryptobot services..."

# Start auth service
cd $NON_DOCKER_ENV_DIR/auth
nohup python main.py --port \$CRYPTOBOT_NON_DOCKER_AUTH_PORT > $LOG_DIR/auth.log 2>&1 &
echo "Auth service started on port \$CRYPTOBOT_NON_DOCKER_AUTH_PORT"

# Start strategy service
cd $NON_DOCKER_ENV_DIR/strategy
nohup python main.py --port \$CRYPTOBOT_NON_DOCKER_STRATEGY_PORT > $LOG_DIR/strategy.log 2>&1 &
echo "Strategy service started on port \$CRYPTOBOT_NON_DOCKER_STRATEGY_PORT"

# Start backtest service
cd $NON_DOCKER_ENV_DIR/backtest
nohup python main.py --port \$CRYPTOBOT_NON_DOCKER_BACKTEST_PORT > $LOG_DIR/backtest.log 2>&1 &
echo "Backtest service started on port \$CRYPTOBOT_NON_DOCKER_BACKTEST_PORT"

# Start trade service
cd $NON_DOCKER_ENV_DIR/trade
nohup python main.py --port \$CRYPTOBOT_NON_DOCKER_TRADE_PORT > $LOG_DIR/trade.log 2>&1 &
echo "Trade service started on port \$CRYPTOBOT_NON_DOCKER_TRADE_PORT"

# Start data service
cd $NON_DOCKER_ENV_DIR/data
nohup python main.py --port \$CRYPTOBOT_NON_DOCKER_DATA_PORT > $LOG_DIR/data.log 2>&1 &
echo "Data service started on port \$CRYPTOBOT_NON_DOCKER_DATA_PORT"

echo "All non-Docker services started."
EOF

chmod +x $NON_DOCKER_ENV_DIR/start_services.sh

# Create stop script for non-Docker services
cat > $NON_DOCKER_ENV_DIR/stop_services.sh << EOF
#!/bin/bash
# Stop non-Docker Cryptobot services

echo "Stopping non-Docker Cryptobot services..."

# Find and kill processes by port
kill_by_port() {
    local port=\$1
    local pid=\$(lsof -t -i:\$port)
    if [ -n "\$pid" ]; then
        echo "Stopping service on port \$port (PID: \$pid)"
        kill \$pid
    else
        echo "No service found on port \$port"
    fi
}

# Stop all services
source $SHARED_DATA_DIR/config/environment.sh
kill_by_port \$CRYPTOBOT_NON_DOCKER_AUTH_PORT
kill_by_port \$CRYPTOBOT_NON_DOCKER_STRATEGY_PORT
kill_by_port \$CRYPTOBOT_NON_DOCKER_BACKTEST_PORT
kill_by_port \$CRYPTOBOT_NON_DOCKER_TRADE_PORT
kill_by_port \$CRYPTOBOT_NON_DOCKER_DATA_PORT

echo "All non-Docker services stopped."
EOF

chmod +x $NON_DOCKER_ENV_DIR/stop_services.sh

echo "=== Parallel Environment Setup Complete ==="
echo "Docker environment: $DOCKER_ENV_DIR"
echo "Non-Docker environment: $NON_DOCKER_ENV_DIR"
echo "Shared data directory: $SHARED_DATA_DIR"
echo "Log directory: $LOG_DIR"
echo ""
echo "Next steps:"
echo "1. Start Docker services: cd $DOCKER_ENV_DIR && docker-compose up -d"
echo "2. Start non-Docker services: $NON_DOCKER_ENV_DIR/start_services.sh"
echo "3. Set up data synchronization: scripts/non-docker-migration/sync_data.sh"
echo ""
echo "For more information, see the migration documentation."