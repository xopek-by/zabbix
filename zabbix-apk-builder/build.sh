#!/bin/bash

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="zabbix-apk-builder"
CONTAINER_NAME="zabbix-build-$$"
OUTPUT_DIR="$PROJECT_DIR/packages"

echo "=== Zabbix APK Builder ==="
echo "Project directory: $PROJECT_DIR"
echo "Output directory: $OUTPUT_DIR"

# Clean up function
cleanup() {
    echo "Cleaning up container..."
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
}

trap cleanup EXIT

# Clean and create output directory
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Build Docker image
echo "Building Docker image..."
docker build -t "$IMAGE_NAME" "$PROJECT_DIR"

# Run the build in the container
echo "Running package build in container..."
docker run --name "$CONTAINER_NAME" "$IMAGE_NAME"

# Copy packages from container to host
echo "Copying packages from container..."
if docker cp "$CONTAINER_NAME:/home/builder/packages/." "$OUTPUT_DIR/"; then
    echo "✅ Packages copied successfully"
    
    # Remove APKINDEX files (we only want the .apk packages)
    echo "Removing repository index files..."
    find "$OUTPUT_DIR" -name "APKINDEX.tar.gz" -delete 2>/dev/null || true
    
    # Fix permissions on copied files
    echo "Fixing file permissions..."
    find "$OUTPUT_DIR" -name "*.apk" -exec chmod 644 {} \; 2>/dev/null || true
    
    echo "Build completed successfully!"
    echo "Packages are in $OUTPUT_DIR:"
    find "$OUTPUT_DIR" -name "*.apk" -exec ls -la {} \;
else
    echo "❌ Failed to copy packages"
    echo "Checking what's in the container..."
    docker exec "$CONTAINER_NAME" find /home/builder -name "*.apk" -exec ls -la {} \; 2>/dev/null || true
    docker exec "$CONTAINER_NAME" ls -la /home/builder/packages/ 2>/dev/null || true
    exit 1
fi