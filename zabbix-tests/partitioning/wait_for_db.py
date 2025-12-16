import time
import pymysql
import sys

config = {
    'host': '127.0.0.1',
    'port': 33060,
    'user': 'root',
    'password': 'root_password',
    'database': 'zabbix'
}

max_retries = 90
for i in range(max_retries):
    try:
        conn = pymysql.connect(**config)
        print("Database is ready!")
        conn.close()
        sys.exit(0)
    except Exception as e:
        print(f"Waiting for DB... ({e})")
        time.sleep(2)

print("Timeout waiting for DB")
sys.exit(1)
