#!/bin/bash
# Cryptobot Python Environment Setup Script for Linux/macOS
# This script sets up a Python virtual environment and installs all required dependencies

set -e  # Exit immediately if a command exits with a non-zero status

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    log "Detected Linux operating system"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    log "Detected macOS operating system"
else
    log "Error: Unsupported operating system. This script is for Linux and macOS only."
    exit 1
fi

# Check if Python is installed
if ! command_exists python3; then
    log "Error: Python 3 is not installed. Please run setup_base_system.sh first."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)

log "Detected Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    log "Error: Python 3.8 or higher is required. Please upgrade your Python installation."
    exit 1
fi

# Create virtual environment
log "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
log "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
log "Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
log "Installing core dependencies..."
pip install -r requirements.txt

# Install service-specific dependencies
log "Installing service-specific dependencies..."

# Check if service-specific requirements files exist and install them
SERVICES=("auth" "strategy" "backtest" "trade" "data")

for SERVICE in "${SERVICES[@]}"; do
    if [ -f "$SERVICE/requirements.txt" ]; then
        log "Installing dependencies for $SERVICE service..."
        pip install -r "$SERVICE/requirements.txt"
    else
        log "Warning: No requirements.txt found for $SERVICE service."
    fi
done

# Install development dependencies if available
if [ -f "requirements-dev.txt" ]; then
    log "Installing development dependencies..."
    pip install -r requirements-dev.txt
fi

# Create a script to activate the virtual environment
log "Creating activation script..."
cat > activate_env.sh << EOL
#!/bin/bash
# Cryptobot Environment Activation Script
# Source this script to activate the Python virtual environment

echo "Activating Cryptobot Python virtual environment..."
source venv/bin/activate

# Set environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export \$(grep -v '^#' .env | xargs)
fi

echo "Cryptobot environment activated!"
echo "Run 'deactivate' to exit the virtual environment."
EOL

chmod +x activate_env.sh

# Create a script to run the application
log "Creating run script..."
cat > run_cryptobot.sh << EOL
#!/bin/bash
# Cryptobot Run Script
# This script activates the virtual environment and starts the Cryptobot services

# Source the activation script
source ./activate_env.sh

# Start the services
echo "Starting Cryptobot services..."

# Start Auth Service
echo "Starting Auth Service..."
cd auth
python main.py &
cd ..

# Start Strategy Service
echo "Starting Strategy Service..."
cd strategy
python main.py &
cd ..

# Start Backtest Service
echo "Starting Backtest Service..."
cd backtest
python main.py &
cd ..

# Start Trade Service
echo "Starting Trade Service..."
cd trade
python main.py &
cd ..

# Start Data Service
echo "Starting Data Service..."
cd data
python main.py &
cd ..

echo "All services started!"
echo "Press Ctrl+C to stop all services."

# Wait for user to press Ctrl+C
wait
EOL

chmod +x run_cryptobot.sh

log "Python environment setup completed successfully!"
log "To activate the environment, run: source ./activate_env.sh"
log "To start the application, run: ./run_cryptobot.sh"

# Deactivate virtual environment
deactivate

exit 0