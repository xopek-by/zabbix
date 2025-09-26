#!/bin/bash

# Example script to run the Zabbix configuration importer
# Replace the values below with your actual Zabbix configuration

# Set environment variables
export ZABBIX_URL="http://10.0.0.101:8887/api_jsonrpc.php"
export BEARER_TOKEN="c785634354e760a6843055ba4581bc7b6cd6eb2ec75f7c2a79f251c1719933f7"
export IMPORT_DIR="/opt/python/export"  # Directory containing host subdirectories

# Activate virtual environment and run the script
cd /opt/python
source venv/bin/activate
python3 config_importer.py