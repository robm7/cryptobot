#!/bin/bash

# Script to generate OpenAPI specifications from running FastAPI services.

# --- Configuration ---
# Adjust these service names and ports according to your project's setup.
# The service name here is used for the output filename and informational messages.
# The hostname is assumed to be localhost.

SERVICES=(
  "auth:8000"
  "auth-service:8001"
  "backtest:8002"
  "data:8003"
  "strategy:8004"
  "trade:8005"
)

OUTPUT_DIR="docs/api"
BASE_URL_PREFIX="http://localhost"

# --- Script Logic ---

echo "Starting OpenAPI specification generation..."

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
if [ $? -ne 0 ]; then
  echo "Error: Could not create output directory '$OUTPUT_DIR'. Please check permissions."
  exit 1
fi
echo "Output directory: '$OUTPUT_DIR'"

# Loop through services and fetch their openapi.json
for service_info in "${SERVICES[@]}"; do
  IFS=':' read -r service_name service_port <<< "$service_info"
  
  service_url="${BASE_URL_PREFIX}:${service_port}/openapi.json"
  output_file="${OUTPUT_DIR}/${service_name}-openapi.json"
  
  echo ""
  echo "Fetching OpenAPI spec for '$service_name' from $service_url..."
  
  # Use curl to fetch the openapi.json
  # The --fail flag ensures curl exits with an error if the HTTP request fails (e.g., 404)
  # The --silent flag suppresses progress meter but still shows errors
  # The --show-error flag shows an error message if --silent is also used and curl fails
  curl --fail --silent --show-error -o "$output_file" "$service_url"
  
  if [ $? -eq 0 ]; then
    echo "Successfully saved OpenAPI spec to '$output_file'"
  else
    echo "Error: Failed to fetch OpenAPI spec for '$service_name'."
    echo "Please ensure the '$service_name' service is running on port '$service_port' and accessible at '$service_url'."
    echo "Partially generated file '$output_file' (if any) might be empty or incomplete."
    # Consider whether to exit on first error or continue with other services
    # For now, it continues.
  fi
done

echo ""
echo "OpenAPI specification generation process completed."
echo "Please check the '$OUTPUT_DIR' directory for the generated files."
echo "If any errors occurred, ensure the respective services are running and accessible."