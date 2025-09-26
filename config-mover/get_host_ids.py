#!/usr/bin/env python3

import os
from datetime import datetime
from zabbix_utils import ZabbixAPI

# Configuration from environment variables
ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/api_jsonrpc.php")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")


def main():
    if not BEARER_TOKEN:
        print("Error: BEARER_TOKEN not set")
        return
    
    # Connect to Zabbix
    try:
        zapi = ZabbixAPI(url=ZABBIX_URL)
        zapi.login(token=BEARER_TOKEN)
        print(f"Connected to Zabbix at {ZABBIX_URL}")
    except Exception as e:
        print(f"Failed to connect to Zabbix: {e}")
        return
    
    # Get all host IDs
    try:
        hosts = zapi.host.get(output=['hostid'])
        
        if not hosts:
            print("No hosts found")
            return
        
        # Extract host IDs
        host_ids = [host['hostid'] for host in hosts]
        host_ids.sort(key=int)  # Sort numerically
        
        print(f"Found {len(host_ids)} hosts")
        
        # Generate filename with current date
        current_date = datetime.now().strftime("%Y%m%d")
        filename = f"{current_date}_host_ids.txt"
        
        # Write host IDs to file (comma-separated on single line)
        with open(filename, 'w') as f:
            f.write(','.join(host_ids))
        
        print(f"Host IDs saved to: {filename}")
        print(f"Host IDs: {', '.join(host_ids)}")
        
    except Exception as e:
        print(f"Error retrieving host IDs: {e}")


if __name__ == "__main__":
    main()