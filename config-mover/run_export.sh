#!/bin/bash

# Example script to run the Zabbix configuration exporter
# Replace the values below with your actual Zabbix configuration

# Set environment variables
export ZABBIX_URL="https://zabbix.mbuz.uk/api_jsonrpc.php"
export BEARER_TOKEN="7b7a372ef46f924f41f2eb163edcb04b99ea2a7a8683e891f531ff7b212adeff"
export HOST_IDS="10084,10584,10591,10595,10596,10607,10618,10623,10624,10637,10659"  # Comma-separated list of host IDs
export OUTPUT_DIR="/opt/python/export"

# Activate virtual environment and run the script
cd /opt/python
source venv/bin/activate
python3 config_exporter.py