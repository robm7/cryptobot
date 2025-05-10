#!/bin/bash
# Cryptobot Service Configuration Generator for Linux/macOS
# This script generates service-specific configuration files from templates

# Function to display messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Function to generate a configuration file from a template and environment variables
generate_config() {
    local template_path="$1"
    local output_path="$2"
    local env_file="$3"
    
    if [ ! -f "$template_path" ]; then
        log "Error: Template file not found at $template_path"
        return 1
    fi
    
    log "Generating configuration file from $template_path to $output_path"
    
    # Read the template content
    local content=$(cat "$template_path")
    
    # Load environment variables
    if [ -f "$env_file" ]; then
        while IFS='=' read -r key value || [ -n "$key" ]; do
            # Skip comments and empty lines
            [[ $key =~ ^#.*$ || -z $key ]] && continue
            
            # Replace placeholders in the template
            placeholder="{{$key}}"
            content="${content//$placeholder/$value}"
        done < "$env_file"
    fi
    
    # Create the directory if it doesn't exist
    mkdir -p "$(dirname "$output_path")"
    
    # Write the content to the output file
    echo "$content" > "$output_path"
    
    log "Configuration file generated at $output_path"
    return 0
}

# Display welcome message
log "Generating service-specific configuration files..."

# Get project root directory
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Define services
services=("auth" "strategy" "trade" "backtest" "data")

# Process each service
for service in "${services[@]}"; do
    log "Processing $service service..."
    
    # Define paths
    template_path="$project_root/config/non-docker/$service/config.yaml"
    env_file_path="$project_root/$service/.env"
    output_path="$project_root/$service/config.yaml"
    
    # Generate configuration file
    if generate_config "$template_path" "$output_path" "$env_file_path"; then
        log "$service service configuration generated successfully."
    else
        log "Failed to generate $service service configuration."
    fi
done

log "Service configuration generation completed!"
exit 0