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

## 8. Troubleshooting
- **Connection Refused**: Check `host`, `port` in config. Ensure MySQL is running.
- **Access Denied (1227)**: The DB user needs `SUPER` privileges to disable binary logging (`replicate_sql: False`). Either grant the privilege or set `replicate_sql: True` (if replication load is acceptable).
- **Primary Key Error**: "Primary Key does not include 'clock'". The table cannot be partitioned by range on `clock` without schema changes. Remove it from config.
