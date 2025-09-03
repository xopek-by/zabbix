#!/bin/bash

# Test script for version checking logic
# This script simulates the version check workflow to ensure it works correctly

set -euo pipefail

echo "=== Zabbix Version Check Test ==="

# Test the API endpoint and version extraction
echo "Testing version check API..."

LATEST_VERSION=$(curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
  jq -r '.values[].displayId' | \
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
  grep -v 'rc\|beta\|alpha' | \
  sort -V | \
  tail -1)

# Validate version format
if [[ ! "$LATEST_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ Error: Invalid version format detected: $LATEST_VERSION"
  exit 1
fi

echo "✅ Latest upstream version: $LATEST_VERSION"

# Extract current version from APKBUILD
CURRENT_VERSION=$(grep '^pkgver=' zabbix/APKBUILD | cut -d'=' -f2)
echo "✅ Current package version: $CURRENT_VERSION"

# Compare versions
if [ "$LATEST_VERSION" = "$CURRENT_VERSION" ]; then
  echo "✅ No new version available. Current version $CURRENT_VERSION is up to date."
  echo "   Build would be skipped in CI/CD."
else
  echo "🔄 New version available: $LATEST_VERSION"
  echo "   Build would be triggered in CI/CD."
fi

echo ""
echo "=== Test completed successfully ==="
