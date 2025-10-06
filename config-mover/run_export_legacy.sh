#!/bin/bash

# Legacy script to run the Zabbix configuration exporter for older Zabbix versions
# Replace the values below with your actual Zabbix configuration

# Set environment variables
export ZABBIX_URL="https://your.zabbix/api_jsonrpc.php"
export HOST_IDS="10084,10584,10591,10595"  # Comma-separated list of host IDs
export OUTPUT_DIR="/opt/python/export"
export ZABBIX_USER="your_username"
export ZABBIX_PASSWORD="your_password"

# Activate virtual environment and run the script
cd /opt/python
source venv/bin/activate
python3 config_exporter_legacy.py