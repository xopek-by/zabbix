#!/usr/bin/env python3
import requests
import json
import time

# === CONFIGURATION ===
ZABBIX_URL = "http://10.0.0.101:8887/api_jsonrpc.php"
ZABBIX_TOKEN = "c785634354e760a6843055ba4581bc7b6cd6eb2ec75f7c2a79f251c1719933f7"
GROUP_ID = "19"
BATCH_SIZE = 100
HOST_PATTERN = "dummy-host-"

HEADERS = {
    "Content-Type": "application/json-rpc",
    "Authorization": f"Bearer {ZABBIX_TOKEN}"
}

def zbx_request(method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": int(time.time())
    }
    r = requests.post(ZABBIX_URL, headers=HEADERS, data=json.dumps(payload))
    r.raise_for_status()
    resp = r.json()
    if "error" in resp:
        raise Exception(f"API error: {resp['error']}")
    return resp

def cleanup_hosts():
    # Get all hosts in the group
    resp = zbx_request("host.get", {
        "groupids": [GROUP_ID],
        "output": ["hostid", "host"]
    })
    
    # Filter hosts that contain the dummy pattern
    hosts = [h for h in resp.get("result", []) if HOST_PATTERN in h["host"]]
    
    if not hosts:
        print("No dummy hosts found")
        return
    
    print(f"Deleting {len(hosts)} hosts")
    
    # Delete in batches
    host_ids = [h["hostid"] for h in hosts]
    total_deleted = 0
    
    for i in range(0, len(host_ids), BATCH_SIZE):
        batch = host_ids[i:i + BATCH_SIZE]
        try:
            resp = zbx_request("host.delete", batch)
            deleted = len(resp.get("result", {}).get("hostids", []))
            total_deleted += deleted
            print(f"Deleted batch {i//BATCH_SIZE + 1}: {deleted} hosts")
        except Exception as e:
            print(f"Error in batch {i//BATCH_SIZE + 1}: {e}")
        
        if i + BATCH_SIZE < len(host_ids):
            time.sleep(0.5)
    
    print(f"Total deleted: {total_deleted}")

if __name__ == "__main__":
    cleanup_hosts()