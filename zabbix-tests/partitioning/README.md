# Zabbix Partitioning Tests

This directory contains a Docker-based test environment for the Zabbix Partitioning script.

## Prerequisites
- Docker & Docker Compose
- Python 3

## Setup & Run
1. Start the database container:
   ```bash
   docker compose up -d
   ```
   This will start a MySQL 8.0 container and import the Zabbix schema.

2. Create valid config (done automatically):
   The `test_config.yaml` references the running container.

3. Run the partitioning script:
   ```bash
   # Create virtual environment if needed
   python3 -m venv venv
   ./venv/bin/pip install pymysql pyyaml

   # Dry Run
   ./venv/bin/python3 ../../partitioning/zabbix_partitioning.py -c test_config.yaml --dry-run --init

   # Live Run
   ./venv/bin/python3 ../../partitioning/zabbix_partitioning.py -c test_config.yaml --init
   ```

## Cleanup
```bash
docker compose down
rm -rf venv
```
