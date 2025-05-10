#!/bin/bash
# Cryptobot SSL/TLS Configuration Script for Linux/macOS
# This script sets up SSL/TLS certificates and configures the application to use HTTPS

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

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    log "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
else
    log "Warning: .env file not found. Using default values."
    # Set default values
    AUTH_SERVICE_PORT="8000"
    STRATEGY_SERVICE_PORT="8010"
    BACKTEST_SERVICE_PORT="8020"
    TRADE_SERVICE_PORT="8030"
    DATA_SERVICE_PORT="8001"
fi

log "Starting SSL/TLS configuration for Cryptobot..."

# Check if OpenSSL is installed
if ! command_exists openssl; then
    log "Error: OpenSSL is not installed. Please install OpenSSL and try again."
    exit 1
fi

# Create SSL directory if it doesn't exist
mkdir -p config/ssl
cd config/ssl

# Generate SSL configuration file
log "Generating SSL configuration file..."
cat > openssl.cnf << EOL
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C = US
ST = State
L = City
O = Cryptobot
OU = Security
CN = localhost

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
EOL

# Generate CA key and certificate
log "Generating CA key and certificate..."
openssl genrsa -out ca.key 4096
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 -subj "/C=US/ST=State/L=City/O=Cryptobot/OU=Security/CN=Cryptobot CA"

# Generate server key and certificate signing request
log "Generating server key and certificate signing request..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config openssl.cnf

# Sign the server certificate with the CA
log "Signing server certificate with CA..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -extensions v3_req -extfile openssl.cnf

# Generate Diffie-Hellman parameters for perfect forward secrecy
log "Generating Diffie-Hellman parameters (this may take a while)..."
openssl dhparam -out dhparam.pem 2048

# Clean up
rm server.csr ca.srl

# Set proper permissions
log "Setting proper permissions for SSL files..."
chmod 600 server.key ca.key
chmod 644 server.crt ca.crt dhparam.pem

# Return to the original directory
cd ../..

# Update environment configuration to use HTTPS
log "Updating environment configuration to use HTTPS..."
if grep -q "USE_HTTPS" .env; then
    # Replace existing USE_HTTPS
    sed -i.bak "s/USE_HTTPS=.*/USE_HTTPS=true/" .env
else
    # Add USE_HTTPS
    echo "USE_HTTPS=true" >> .env
fi

if grep -q "SSL_CERT_PATH" .env; then
    # Replace existing SSL_CERT_PATH
    sed -i.bak "s|SSL_CERT_PATH=.*|SSL_CERT_PATH=config/ssl/server.crt|" .env
else
    # Add SSL_CERT_PATH
    echo "SSL_CERT_PATH=config/ssl/server.crt" >> .env
fi

if grep -q "SSL_KEY_PATH" .env; then
    # Replace existing SSL_KEY_PATH
    sed -i.bak "s|SSL_KEY_PATH=.*|SSL_KEY_PATH=config/ssl/server.key|" .env
else
    # Add SSL_KEY_PATH
    echo "SSL_KEY_PATH=config/ssl/server.key" >> .env
fi

if grep -q "SSL_CA_PATH" .env; then
    # Replace existing SSL_CA_PATH
    sed -i.bak "s|SSL_CA_PATH=.*|SSL_CA_PATH=config/ssl/ca.crt|" .env
else
    # Add SSL_CA_PATH
    echo "SSL_CA_PATH=config/ssl/ca.crt" >> .env
fi

if grep -q "SSL_DH_PARAMS_PATH" .env; then
    # Replace existing SSL_DH_PARAMS_PATH
    sed -i.bak "s|SSL_DH_PARAMS_PATH=.*|SSL_DH_PARAMS_PATH=config/ssl/dhparam.pem|" .env
else
    # Add SSL_DH_PARAMS_PATH
    echo "SSL_DH_PARAMS_PATH=config/ssl/dhparam.pem" >> .env
fi

# Create HTTPS configuration for services
log "Creating HTTPS configuration for services..."

# Create SSL configuration file for services
cat > config/ssl/ssl_config.json << EOL
{
    "ssl": {
        "enabled": true,
        "cert_path": "config/ssl/server.crt",
        "key_path": "config/ssl/server.key",
        "ca_path": "config/ssl/ca.crt",
        "dh_params_path": "config/ssl/dhparam.pem",
        "protocols": ["TLSv1.2", "TLSv1.3"],
        "ciphers": "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384",
        "prefer_server_ciphers": true,
        "session_timeout": 3600,
        "session_cache": "shared:SSL:10m",
        "stapling": true,
        "stapling_verify": true,
        "headers": {
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
    }
}
EOL

# Create Python SSL configuration module
mkdir -p utils/ssl
cat > utils/ssl/__init__.py << EOL
# SSL/TLS Configuration Module
import os
import json
import ssl

def load_ssl_config():
    """Load SSL configuration from config file"""
    config_path = os.path.join(os.getcwd(), 'config', 'ssl', 'ssl_config.json')
    
    if not os.path.exists(config_path):
        return None
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    return config.get('ssl', {})

def create_ssl_context():
    """Create an SSL context for HTTPS servers"""
    ssl_config = load_ssl_config()
    
    if not ssl_config or not ssl_config.get('enabled', False):
        return None
    
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    
    # Load certificate and private key
    cert_path = os.path.join(os.getcwd(), ssl_config.get('cert_path', ''))
    key_path = os.path.join(os.getcwd(), ssl_config.get('key_path', ''))
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    else:
        return None
    
    # Set SSL/TLS protocol versions
    context.options |= ssl.OP_NO_SSLv2
    context.options |= ssl.OP_NO_SSLv3
    context.options |= ssl.OP_NO_TLSv1
    context.options |= ssl.OP_NO_TLSv1_1
    
    # Set cipher suite
    if ssl_config.get('ciphers'):
        context.set_ciphers(ssl_config.get('ciphers'))
    
    # Enable OCSP stapling if available
    if hasattr(ssl, 'OPENSSL_VERSION_NUMBER') and ssl.OPENSSL_VERSION_NUMBER >= 0x10002000:
        if ssl_config.get('stapling', False):
            context.options |= 0x4000  # SSL_OP_NO_TICKET
            context.options |= 0x2000000  # SSL_OP_SINGLE_DH_USE
            context.options |= 0x100000  # SSL_OP_SINGLE_ECDH_USE
    
    return context
EOL

# Update service startup scripts to use HTTPS
log "Updating service startup scripts to use HTTPS..."

# Update auth service
if [ -f auth/main.py ]; then
    # Check if SSL import already exists
    if ! grep -q "from utils.ssl import create_ssl_context" auth/main.py; then
        # Add SSL import
        sed -i.bak '/import uvicorn/a from utils.ssl import create_ssl_context' auth/main.py
        
        # Update uvicorn.run to use SSL
        sed -i.bak 's/uvicorn.run(/uvicorn.run(/g' auth/main.py
        sed -i.bak 's/    "main:app",/    "main:app",/g' auth/main.py
        sed -i.bak 's/    host="0.0.0.0",/    host="0.0.0.0",/g' auth/main.py
        sed -i.bak 's/    port=8000,/    port=8000,/g' auth/main.py
        sed -i.bak 's/    reload=True/    reload=True,\n    ssl_keyfile="config\/ssl\/server.key",\n    ssl_certfile="config\/ssl\/server.crt"/g' auth/main.py
    fi
fi

# Clean up backup files
rm -f .env.bak auth/main.py.bak

log "SSL/TLS configuration completed successfully!"
log "Note: You may need to restart services for the changes to take effect."
log "Important: The generated certificates are self-signed and intended for development/testing."
log "For production, please obtain certificates from a trusted certificate authority."
exit 0