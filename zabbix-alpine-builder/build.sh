#!/bin/bash

# Zabbix APK Builder - Local Build Script
# This script performs a local build of the Zabbix packages for testing purposes

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZABBIX_DIR="$SCRIPT_DIR/zabbix"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're running as root (required for abuild)
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        log_info "Please run as a regular user with sudo access"
        exit 1
    fi
}

# Check dependencies
check_dependencies() {
    log_info "Checking build dependencies..."
    
    if ! command -v abuild &> /dev/null; then
        log_error "abuild not found. Please install alpine-sdk:"
        log_info "  sudo apk add alpine-sdk"
        exit 1
    fi
    
    if ! command -v git &> /dev/null; then
        log_error "git not found. Please install git:"
        log_info "  sudo apk add git"
        exit 1
    fi
    
    log_info "Dependencies check passed"
}

# Setup abuild environment
setup_abuild() {
    log_info "Setting up abuild environment..."
    
    # Create abuild config if it doesn't exist
    if [[ ! -f "$HOME/.abuild/abuild.conf" ]]; then
        log_info "Creating abuild configuration..."
        mkdir -p "$HOME/.abuild"
        echo "PACKAGER_PRIVKEY=\"$HOME/.abuild/$(whoami)-$(date +%Y%m%d).rsa\"" > "$HOME/.abuild/abuild.conf"
    fi
    
    # Generate signing key if it doesn't exist
    if [[ ! -f "$HOME/.abuild/$(whoami)-"*".rsa" ]]; then
        log_info "Generating abuild signing key..."
        abuild-keygen -a -i
    fi
}

# Main build function
build_packages() {
    log_info "Starting Zabbix package build..."
    
    # Navigate to the zabbix directory containing APKBUILD
    if [[ ! -d "$ZABBIX_DIR" ]]; then
        log_error "Zabbix directory not found: $ZABBIX_DIR"
        exit 1
    fi
    
    cd "$ZABBIX_DIR"
    
    # Check if APKBUILD exists
    if [[ ! -f "APKBUILD" ]]; then
        log_error "APKBUILD file not found in $ZABBIX_DIR"
        exit 1
    fi
    
    log_info "Building packages with abuild..."
    
    # Clean any previous builds
    abuild clean || true
    
    # Fetch sources and verify checksums
    log_info "Fetching sources..."
    abuild fetch
    
    # Update checksums if needed (important for new versions)
    log_info "Updating checksums..."
    abuild checksum
    
    # Build the packages and create local repository index
    # -r flag creates a local repository with package index
    log_info "Building packages and creating repository index..."
    abuild -r
    
    if [[ $? -eq 0 ]]; then
        log_info "Build completed successfully!"
        log_info "Generated packages can be found in ~/packages/"
        
        # List generated packages
        if [[ -d "$HOME/packages" ]]; then
            log_info "Generated APK files:"
            find "$HOME/packages" -name "zabbix*.apk" -type f -exec basename {} \; | sort
        fi
    else
        log_error "Build failed!"
        exit 1
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up build artifacts..."
    cd "$ZABBIX_DIR"
    abuild clean || true
}

# Main execution
main() {
    log_info "Zabbix APK Builder - Local Build Script"
    log_info "========================================"
    
    check_root
    check_dependencies
    setup_abuild
    
    # Trap cleanup on exit
    trap cleanup EXIT
    
    build_packages
    
    log_info "Build process completed!"
}

# Run main function
main "$@"
