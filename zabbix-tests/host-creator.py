#!/usr/bin/env python3
import requests
import json
import time

# === CONFIGURATION ===
ZABBIX_URL = "http://10.0.0.101:8887/api_jsonrpc.php"
ZABBIX_TOKEN = "c785634354e760a6843055ba4581bc7b6cd6eb2ec75f7c2a79f251c1719933f7"
PROXY_GROUP_ID = "1"        # your proxy group ID
GROUP_ID = "19"              # host group for these hosts
NUM_HOSTS = 1000            # number of hosts to create
BATCH_SIZE = 100            # how many to create per call

HEADERS = {
    "Content-Type": "application/json-rpc",
    "Authorization": f"Bearer {ZABBIX_TOKEN}"
}

def zbx_request(method, params):
    """Send Zabbix API request using Bearer token authentication."""
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
        raise Exception(f"Zabbix API error: {resp['error']}")
    return resp

def create_hosts():
    hosts = []
    for i in range(1, NUM_HOSTS + 1):
        host_name = f"dummy-host-{i:04d}"
        host = {
            "host": host_name,
            "groups": [{"groupid": GROUP_ID}],
            "templates": [{"templateid": "10048"}],  # assign Proxy Health template
            "monitored_by": 2,               # 2 = proxy group
            "proxy_groupid": PROXY_GROUP_ID  # your proxy group ID
        }
        hosts.append(host)

    for i in range(0, len(hosts), BATCH_SIZE):
        batch = hosts[i:i + BATCH_SIZE]
        print(f"Creating hosts {i+1}-{i+len(batch)}...")
        try:
            resp = zbx_request("host.create", batch)
            created = len(resp.get("result", {}).get("hostids", []))
            print(f"Created {created} hosts.")
        except Exception as e:
            print(f"Error in batch {i+1}-{i+len(batch)}: {e}")
        time.sleep(1)

if __name__ == "__main__":
    try:
        create_hosts()
    except Exception as e:
        print(f"Fatal error: {e}")
