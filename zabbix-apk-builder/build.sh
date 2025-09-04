#!/bin/bash

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="zabbix-apk-builder"
CONTAINER_NAME="zabbix-build-$"
OUTPUT_DIR="$PROJECT_DIR/packages"

echo "=== Zabbix APK Builder ==="
echo "Project directory: $PROJECT_DIR"
echo "Output directory: $OUTPUT_DIR"

# Clean up any existing containers
cleanup() {
    echo "Cleaning up..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
}

trap cleanup EXIT

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Build Docker image
echo "Building Docker image..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

# Run the build in container
echo "Running package build..."
docker run --rm \
    --name "$CONTAINER_NAME" \
    -v "$OUTPUT_DIR:/output" \
    "$IMAGE_NAME"

echo "Build completed successfully!"
echo "To install packages:"
echo "  apk add --allow-untrusted $OUTPUT_DIR/zabbix-agent-*.apk"
echo "  apk add --allow-untrusted $OUTPUT_DIR/zabbix-proxy-*.apk"

