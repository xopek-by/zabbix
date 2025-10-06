#!/usr/bin/env python3
"""
Legacy ID Retriever
===============================
Uses username/password authentication instead of tokens.
Note: This script is designed for Zabbix 5.0 and older versions!
Please do not use with Zabbix 6.0 and newer! Use token-based get_host_ids.py instead.
"""

import os
from datetime import datetime
from zabbix_utils import ZabbixAPI

# Configuration from environment variables
ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/api_jsonrpc.php")
ZABBIX_USER = os.environ.get("ZABBIX_USER")
ZABBIX_PASSWORD = os.environ.get("ZABBIX_PASSWORD")


def main():
    # Check required environment variables
    if not ZABBIX_USER or not ZABBIX_PASSWORD:
        print("Error: ZABBIX_USER and ZABBIX_PASSWORD environment variables must be set")
        return
    
    # Connect to Zabbix using username/password
    try:
        zapi = ZabbixAPI(url=ZABBIX_URL)
        zapi.login(user=ZABBIX_USER, password=ZABBIX_PASSWORD)
        print(f"Connected to Zabbix at {ZABBIX_URL}")
        print(f"Authenticated as user: {ZABBIX_USER}")
    except Exception as e:
        print(f"Failed to connect to Zabbix: {e}")
        return
    
    # Get all host IDs
    try:
        hosts = zapi.host.get(output=['hostid', 'host'])
        
        if not hosts:
            print("No hosts found")
            return
        
        # Extract host IDs
        host_ids = [host['hostid'] for host in hosts]
        host_ids.sort(key=int)  # Sort numerically
        
        print(f"Found {len(host_ids)} hosts")
        
        # Generate filename with current date
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"{current_date}_host_ids_legacy.txt"
        
        # Write host IDs to file (comma-separated on single line)
        with open(filename, 'w') as f:
            f.write(','.join(host_ids))
        
        print(f"Host IDs saved to: {filename}")
        
    except Exception as e:
        print(f"Error retrieving host IDs: {e}")
    
    finally:
        # Logout from Zabbix
        try:
            zapi.logout()
            print("Logged out from Zabbix")
        except:
            pass  # Ignore logout errors

if __name__ == "__main__":
    main()