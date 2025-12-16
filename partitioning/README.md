# Zabbix Database Partitioning Guide (Python based)

This guide describes how to set up and manage database partitioning for Zabbix using the `zabbix_partitioning.py` script. 

## Overview
The script manages MySQL table partitions based on time (Range Partitioning on the `clock` column). It automatically:
1.  Creates future partitions to ensure new data can be written.
2.  Drops old partitions based on configured retention periods.

**Benefits**:
- **Performance**: Faster cleanup of old data (dropping a partition is instantaneous compared to Zabbix internal housekeeping).
- **Recommended**: For database bigger than 100GB.
- **Must have!**: For database bigger than 500G.

> [!WARNING]
> Support for **MySQL/MariaDB** only.
> Always **BACKUP** your database before initializing partitioning!

---

## 1. Prerequisites
- **Python 3.6+**
- **Python Libraries**: `pymysql`, `pyyaml`
  ```bash
  # Debian/Ubuntu
  sudo apt install python3-pymysql python3-yaml
  # RHEL/AlmaLinux/Rocky
  sudo dnf install python3-pymysql python3-pyyaml
  # Or via pip
  pip3 install pymysql pyyaml
  ```
- **Database Permissions**: The user configured in the script needs:
  - `SELECT`, `INSERT`, `CREATE`, `DROP`, `ALTER` on the Zabbix database.
  - `SUPER` or `SESSION_VARIABLES_ADMIN` privilege (required to disable binary logging via `SET SESSION sql_log_bin=0` if `replicate_sql: False`).

---

## 2. Installation
1.  Copy the script and config to a precise location (e.g., `/usr/local/bin` or specialized directory).
    ```bash
    mkdir -p /opt/zabbix_partitioning
    cp zabbix_partitioning.py /opt/zabbix_partitioning/
    cp zabbix_partitioning.conf /etc/zabbix/
    chmod +x /opt/zabbix_partitioning/zabbix_partitioning.py
    ```

---

## 3. Configuration
Edit `/etc/zabbix/zabbix_partitioning.conf`:

```yaml
database:
    host: localhost
    user: zbx_part
    passwd: YOUR_PASSWORD
    db: zabbix
    # port: 3306  # Optional, default is 3306

partitions:
    daily:
        - history: 14d
        - history_uint: 14d
        - trends: 365d
        # ... add other options as needed. Please check the config file for more options.
```

### Configuration Parameters
- **`partitions`**: Defines your retention policy globally.
  - Syntax: `period: [ {table: retention_period}, ... ]`
  - **`daily`**: Partitions are created for each day.
  - **`weekly`**: Partitions are created for each week.
  - **`monthly`**: Partitions are created for each month.
  - **`yearly`**: Partitions are created for each year. 
  - Retention Format: `14d` (days), `12w` (weeks), `12m` (months), `1y` (years).

- **`initial_partitioning_start`**: Controls how the very FIRST partition is determined during initialization (`--init` mode).
  - `db_min`: (Default) Queries the table for the oldest record (`MIN(clock)`). Accurate but **slow** on large tables.
  - `retention`: (Recommended for large DBs) Skips the query. Calculates the start date as `Now - Retention Period`. Creates a single `p_archive` partition for all data older than that date.

- **`premake`**: Number of future partitions to create in advance.
  - Default: `10`. Ensures you have a buffer if the script fails to run for a few days.

- **`replicate_sql`**: Controls MySQL Binary Logging for partitioning commands.
  - `False`: (Default) Disables binary logging (`SET SESSION sql_log_bin = 0`). Partition creation/dropping is **NOT** replicated to slaves. Useful if you want to manage partitions independently on each node or avoid replication lag storms.
  - `True`: Commands are replicated. Use this if you want absolute schema consistency across your cluster automatically.

- **`auditlog`**:
  - In Zabbix 7.0+, the `auditlog` table does **not** have the `clock` column in its Primary Key by default. **Do not** add it to the config unless you have manually altered the table schema.

---

## 4. Zabbix Preparation (CRITICAL)
Before partitioning, you **must disable** Zabbix's internal housekeeping for the tables you intend to partition. If you don't, Zabbix will try to delete individual rows while the script tries to drop partitions, causing conflicts.

1.  Log in to Zabbix Web Interface.
2.  Go to **Administration** -> **General** -> **Housekeeping**.
3.  **Uncheck** the following (depending on what you partition):
    - [ ] Enable internal housekeeping for **History**
    - [ ] Enable internal housekeeping for **Trends**
4.  Click **Update**.

---

## 5. Initialization
This step converts existing standard tables into partitioned tables.

1.  **Dry Run** (Verify what will happen):
    ```bash
    /opt/zabbix_partitioning/zabbix_partitioning.py --init --dry-run
    ```
    *Check the output for any errors.*

2.  **Execute Initialization**:
    ```bash
    /opt/zabbix_partitioning/zabbix_partitioning.py --init
    ```
    *This may take time depending on table size.*

---

## 6. Automation (Cron Job)
Set up a daily cron job to create new partitions and remove old ones.

1.  Open crontab:
    ```bash
    crontab -e
    ```
2.  Add the line (run daily at 00:30):
    ```cron
    30 0 * * * /usr/bin/python3 /opt/zabbix_partitioning/zabbix_partitioning.py -c /etc/zabbix/zabbix_partitioning.conf >> /var/log/zabbix_partitioning.log 2>&1
    ```

---

## 7. Automation (Systemd Timer) — Recommended
Alternatively, use systemd timers for more robust scheduling and logging.

1.  **Create Service Unit** (`/etc/systemd/system/zabbix-partitioning.service`):
    ```ini
    [Unit]
    Description=Zabbix Database Partitioning Service
    After=network.target mysql.service

    [Service]
    Type=oneshot
    User=root
    ExecStart=/usr/bin/python3 /opt/zabbix_partitioning/zabbix_partitioning.py -c /etc/zabbix/zabbix_partitioning.conf
    ```

2.  **Create Timer Unit** (`/etc/systemd/system/zabbix-partitioning.timer`):
    ```ini
    [Unit]
    Description=Run Zabbix Partitioning Daily

    [Timer]
    OnCalendar=*-*-* 00:30:00
    Persistent=true

    [Install]
    WantedBy=timers.target
    ```

3.  **Enable and Start**:
    ```bash
    systemctl daemon-reload
    systemctl enable --now zabbix-partitioning.timer
    ```

4.  **View Logs**:
    ```bash
    journalctl -u zabbix-partitioning.service
    ```

---

---

## 8. Troubleshooting
- **Connection Refused**: Check `host`, `port` in config. Ensure MySQL is running.
- **Access Denied (1227)**: The DB user needs `SUPER` privileges to disable binary logging (`replicate_sql: False`). Either grant the privilege or set `replicate_sql: True` (if replication load is acceptable).
- **Primary Key Error**: "Primary Key does not include 'clock'". The table cannot be partitioned by range on `clock` without schema changes. Remove it from config.

## 9. Docker Usage

You can run the partitioning script as a stateless Docker container. This is ideal for Kubernetes CronJobs or environments where you don't want to manage Python dependencies on the host.

### 9.1 Build the Image
The image is not yet published to a public registry, so you must build it locally:
```bash
cd /opt/git/Zabbix/partitioning
docker build -t zabbix-partitioning -f docker/Dockerfile .
```

### 9.2 Operations
The container uses `entrypoint.py` to auto-generate the configuration file from Environment Variables at runtime.

#### Scenario A: Dry Run (Check Configuration)
Verify that your connection and retention settings are correct without making changes.
```bash
docker run --rm \
  -e DB_HOST=10.0.0.5 -e DB_USER=zabbix -e DB_PASSWORD=secret \
  -e RETENTION_HISTORY=7d \
  -e RETENTION_TRENDS=365d \
  -e RUN_MODE=dry-run \
  zabbix-partitioning
```

#### Scenario B: Initialization (First Run)
Convert your existing tables to partitioned tables. 
> [!WARNING]
> Ensure backup exists and Zabbix Housekeeper is disabled!
```bash
docker run --rm \
  -e DB_HOST=10.0.0.5 -e DB_USER=zabbix -e DB_PASSWORD=secret \
  -e RETENTION_HISTORY=14d \
  -e RETENTION_TRENDS=365d \
  -e RUN_MODE=init \
  zabbix-partitioning
```

#### Scenario C: Daily Maintenance (Cron/Scheduler)
Run this daily (e.g., via K8s CronJob) to create future partitions and drop old ones.
```bash
docker run --rm \
  -e DB_HOST=10.0.0.5 -e DB_USER=zabbix -e DB_PASSWORD=secret \
  -e RETENTION_HISTORY=14d \
  -e RETENTION_TRENDS=365d \
  zabbix-partitioning
```

#### Scenario D: Custom Overrides
You can override the retention period for specific tables or change their partitioning interval.
*Example: Force `history_log` to be partitioned **Weekly** with 30-day retention.*
```bash
docker run --rm \
  -e DB_HOST=10.0.0.5 \
  -e RETENTION_HISTORY=7d \
  -e PARTITION_WEEKLY_history_log=30d \
  zabbix-partitioning
```

#### Scenario E: SSL Connection
Mount your certificates and provide the paths.
```bash
docker run --rm \
  -e DB_HOST=zabbix-db \
  -e DB_SSL_CA=/certs/ca.pem \
  -e DB_SSL_CERT=/certs/client-cert.pem \
  -e DB_SSL_KEY=/certs/client-key.pem \
  -v /path/to/local/certs:/certs \
  zabbix-partitioning
```

### 9.3 Supported Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | localhost | Database hostname |
| `DB_PORT` | 3306 | Database port |
| `DB_USER` | zabbix | Database user |
| `DB_PASSWORD` | zabbix | Database password |
| `DB_NAME` | zabbix | Database name |
| `DB_SSL_CA` | - | Path to CA Certificate |
| `DB_SSL_CERT` | - | Path to Client Certificate |
| `DB_SSL_KEY` | - | Path to Client Key |
| `RETENTION_HISTORY` | 14d | Retention for `history*` tables |
| `RETENTION_TRENDS` | 365d | Retention for `trends*` tables |
| `RETENTION_AUDIT` | 365d | Retention for `auditlog` (if enabled) |
| `ENABLE_AUDITLOG_PARTITIONING` | false | Set to `true` to partition `auditlog` |
| `RUN_MODE` | maintenance | `init`, `maintenance`, `dry-run`, `discovery`, `check` |
| `CHECK_TARGET` | - | Required if `RUN_MODE=check`. Table name to check (e.g. `history`). |
| `PARTITION_DAILY_[TABLE]` | - | Custom daily retention (e.g., `PARTITION_DAILY_mytable=30d`) |
| `PARTITION_WEEKLY_[TABLE]` | - | Custom weekly retention |
| `PARTITION_MONTHLY_[TABLE]` | - | Custom monthly retention |

#### Scenario F: Monitoring (Discovery)
Output Zabbix LLD JSON for table discovery.
```bash
docker run --rm \
  -e DB_HOST=zabbix-db \
  -e RUN_MODE=discovery \
  zabbix-partitioning
```

#### Scenario G: Monitoring (Health Check)
Check days remaining for a specific table (e.g., `history`). Returns integer days.
```bash
docker run --rm \
  -e DB_HOST=zabbix-db \
  -e RUN_MODE=check \
  -e CHECK_TARGET=history \
  zabbix-partitioning
```

---

## 10. Monitoring
The script includes built-in features for monitoring the health of your partitions via Zabbix.

### 10.1 CLI Usage
- **Discovery (LLD)**:
  ```bash
  ./zabbix_partitioning.py --discovery
  # Output: [{"{#TABLE}": "history", "{#PERIOD}": "daily"}, ...]
  ```
- **Check Days**:
  ```bash
  ./zabbix_partitioning.py --check-days history
  # Output: 30 (integer days remaining)
  ```
- **Version**:
  ```bash
  ./zabbix_partitioning.py --version
  # Output: zabbix_partitioning.py 0.3.1-test
  ```

### 10.2 Zabbix Template
A Zabbix 7.0 template is provided: `zabbix_partitioning_template.yaml`.

**Setup**:
1.  Import the YAML template into Zabbix.
2.  Install the script on the Zabbix Server or Proxy.
3.  Add the `UserParameter` commands to your Zabbix Agent config (see Template description).
4.  Link the template to the host running the script.

**Features**:
- **Discovery**: Automatically finds all partitioned tables.
- **Triggers**: Alerts if a table has less than 3 days of future partitions pre-created.
- **Log Monitoring**: Alerts on script execution failures.

