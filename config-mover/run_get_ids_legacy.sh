#!/bin/bash

# Example script to run the Zabbix host IDs retriever for older Zabbix versions
# Replace the values below with your actual Zabbix configuration

# Set environment variables
export ZABBIX_URL="https://your.zabbix/api_jsonrpc.php"
export ZABBIX_USER="your_username"
export ZABBIX_PASSWORD="your_password"

# Activate virtual environment and run the script
cd /opt/python
source venv/bin/activate
python3 get_host_ids_legacy.py