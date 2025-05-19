# Dependency Management

This document describes the dependency management approach used in the Crypto Trading Bot project.

## Overview

The project uses [pip-tools](https://github.com/jazzband/pip-tools) to manage Python dependencies. This approach provides several benefits:

- Clear separation between direct dependencies and transitive dependencies
- Pinned versions for reproducible builds
- Separation of development and production dependencies
- Service-specific dependency management

## Structure

The dependency management structure is as follows:

- `requirements.in`: Primary dependencies for the core application
- `requirements.txt`: Pinned dependencies generated from requirements.in
- `requirements-dev.in`: Development dependencies
- `requirements-dev.txt`: Pinned development dependencies

Each service has its own requirements files:
- `<service>/requirements.in`: Primary dependencies for the service
- `<service>/requirements.txt`: Pinned dependencies for the service

## Updating Dependencies

To update dependencies, use the provided script:

```bash
# On Unix-like systems
python scripts/update_dependencies.py

# On Windows
scripts\update_dependencies.bat
```

This script will update all `requirements.txt` files from their corresponding `requirements.in` files.

## Adding New Dependencies

To add a new dependency:

1. Add the dependency to the appropriate `requirements.in` file
   - For core dependencies, add to the root `requirements.in`
   - For service-specific dependencies, add to the service's `requirements.in`
   - For development dependencies, add to `requirements-dev.in`

2. Run the update script to regenerate the `requirements.txt` files

```bash
python scripts/update_dependencies.py
```

## Manual Updates

You can also manually update a specific requirements file:

```bash
# Update root requirements
pip-compile requirements.in --output-file=requirements.txt

# Update service requirements
pip-compile <service>/requirements.in --output-file=<service>/requirements.txt

# Update development requirements
pip-compile requirements-dev.in --output-file=requirements-dev.txt
```

## Installing Dependencies

To install dependencies for development:

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

To install dependencies for a specific service:

```bash
pip install -r <service>/requirements.txt
```

## Docker Builds

Each service's Dockerfile should use its specific `requirements.txt` file for installing dependencies:

```dockerfile
COPY <service>/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

This ensures that each service only includes the dependencies it needs, keeping container sizes minimal.