#!/bin/bash

# Example script to run the Zabbix host IDs retriever
# Replace the values below with your actual Zabbix configuration

# Set environment variables
export ZABBIX_URL="https://zabbix.mbuz.uk/api_jsonrpc.php"
export BEARER_TOKEN="7b7a372ef46f924f41f2eb163edcb04b99ea2a7a8683e891f531ff7b212adeff"

# Activate virtual environment and run the script
cd /opt/python
source venv/bin/activate
python3 get_host_ids.py