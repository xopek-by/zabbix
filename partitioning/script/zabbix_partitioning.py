#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zabbix Database Partitioning Management Script

Refactored for Zabbix 7.x compatibility, better maintainability, and standard logging.
"""

import os
import sys
import re
import argparse
import pymysql
from pymysql.constants import CLIENT
import yaml
import json
import logging
import logging.handlers
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Union, Tuple
from contextlib import contextmanager

# Semantic Versioning
VERSION = '0.3.0'

# Constants
PART_PERIOD_REGEX = r'([0-9]+)(h|d|m|y)'
PARTITION_TEMPLATE = 'PARTITION %s VALUES LESS THAN (UNIX_TIMESTAMP("%s") div 1) ENGINE = InnoDB'

# Custom Exceptions
class ConfigurationError(Exception):
    pass

class DatabaseError(Exception):
    pass

class ZabbixPartitioner:
    def __init__(self, config: Dict[str, Any], dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.conn = None
        self.logger = logging.getLogger('zabbix_partitioning')
        
        # Unpack database config
        db_conf = self.config['database']
        self.db_host = db_conf.get('host', 'localhost')
        self.db_port = int(db_conf.get('port', 3306))
        self.db_socket = db_conf.get('socket')
        self.db_user = db_conf['user']
        self.db_password = db_conf.get('passwd')
        self.db_name = db_conf['db']
        self.db_ssl = db_conf.get('ssl')

        self.replicate_sql = self.config.get('replicate_sql', False)

    @contextmanager
    def connect_db(self):
        """Context manager for database connection."""
        try:
            connect_args = {
                'user': self.db_user,
                'password': self.db_password,
                'database': self.db_name,
                'port': self.db_port,
                'cursorclass': pymysql.cursors.Cursor,
                # Enable multi-statements if needed, though we usually run single queries
                'client_flag': CLIENT.MULTI_STATEMENTS
            }

            if self.db_socket:
                connect_args['unix_socket'] = self.db_socket
            else:
                connect_args['host'] = self.db_host
            
            if self.db_ssl:
                connect_args['ssl'] = self.db_ssl
                # PyMySQL SSL options
                # Note: valid ssl keys for PyMySQL are 'ca', 'capath', 'cert', 'key', 'cipher', 'check_hostname'
            
            self.logger.info(f"Connecting to database: {self.db_name}")
            self.conn = pymysql.connect(**connect_args)
            
            # Setup session
            with self.conn.cursor() as cursor:
                cursor.execute('SET SESSION wait_timeout = 86400')
                if not self.replicate_sql:
                    cursor.execute('SET SESSION sql_log_bin = 0')
            
            yield self.conn
            
        except pymysql.MySQLError as e:
            self.logger.critical(f"Database connection failed: {e}")
            raise DatabaseError(f"Failed to connect to MySQL: {e}")
        finally:
            if self.conn and self.conn.open:
                self.conn.close()
                self.logger.info("Database connection closed")

    def execute_query(self, query: str, params: Optional[Union[List, Tuple]] = None, fetch: str = 'none') -> Any:
        """
        Execute a query.
        fetch: 'none', 'one', 'all'
        """
        if self.dry_run and not query.lower().startswith('select'):
            self.logger.info(f"[DRY-RUN] Query: {query} | Params: {params}")
            return None

        if not self.conn or not self.conn.open:
            raise DatabaseError("Connection not open")

        try:
            with self.conn.cursor() as cursor:
                if self.logger.level == logging.DEBUG:
                     self.logger.debug(f"Query: {query} | Params: {params}")
                
                cursor.execute(query, params)
                
                if fetch == 'one':
                    result = cursor.fetchone()
                    # Return first column if it's a single value result and a tuple
                    if result and isinstance(result, tuple) and len(result) == 1:
                        return result[0]
                    return result
                elif fetch == 'all':
                    return cursor.fetchall()
                
                self.conn.commit()
                return True
                
        except pymysql.MySQLError as e:
            self.logger.error(f"SQL Error: {e} | Query: {query}")
            raise DatabaseError(f"SQL Execution Error: {e}")

    # --- Utility Functions --- #
    
    def truncate_date(self, dt: datetime, period: str) -> datetime:
        """Truncate date to the start of the partitioning period."""
        if period == 'hourly':
            return dt.replace(microsecond=0, second=0, minute=0)
        elif period == 'daily':
            return dt.replace(microsecond=0, second=0, minute=0, hour=0)
        elif period == 'weekly':
             # Monday is 0, Sunday is 6. isoweekday() Mon=1, Sun=7.
             # Truncate to Monday
            dt = dt.replace(microsecond=0, second=0, minute=0, hour=0)
            return dt - timedelta(days=dt.isoweekday() - 1)
        elif period == 'monthly':
            return dt.replace(microsecond=0, second=0, minute=0, hour=0, day=1)
        elif period == 'yearly':
            return dt.replace(microsecond=0, second=0, minute=0, hour=0, day=1, month=1)
        else:
             raise ValueError(f"Unknown period: {period}")

    def get_next_date(self, dt: datetime, period: str, amount: int = 1) -> datetime:
        """Add 'amount' periods to the date."""
        if period == 'hourly':
            return dt + timedelta(hours=amount)
        elif period == 'daily':
            return dt + timedelta(days=amount)
        elif period == 'weekly':
            return dt + timedelta(weeks=amount)
        elif period == 'monthly':
             # Simple month addition
             m, y = (dt.month + amount) % 12, dt.year + ((dt.month + amount - 1) // 12)
             if not m: m = 12
             # Handle end of month days (e.g. Jan 31 + 1 month -> Feb 28) logic not strictly needed for 1st of month
             # but keeping robust
             d = min(dt.day, [31, 29 if y%4==0 and (y%100!=0 or y%400==0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m-1])
             return dt.replace(day=d, month=m, year=y)
        elif period == 'yearly':
            return dt.replace(year=dt.year + amount)
        else:
            return dt

    def get_lookback_date(self, period_str: str) -> datetime:
        """
        Calculate the retention date based on config string (e.g., "30d", "12m").
        """
        match = re.search(PART_PERIOD_REGEX, period_str)
        if not match:
            raise ConfigurationError(f"Invalid period format: {period_str}")
        
        amount = int(match.group(1))
        unit = match.group(2)
        
        now = datetime.now()
        
        if unit in ['h', 'hourly']:
            return now - timedelta(hours=amount)
        elif unit in ['d', 'daily']:
            return now - timedelta(days=amount)
        elif unit in ['w', 'weekly']:
            return now - timedelta(weeks=amount)
        elif unit in ['m', 'monthly']:
            # approximate 30 days per month for simple calculation or full month subtraction
            # using get_next_date with negative amount
            return self.get_next_date(now, 'monthly', -amount)
        elif unit in ['y', 'yearly']:
            return now.replace(year=now.year - amount)
        return now

    def get_partition_name(self, dt: datetime, period: str) -> str:
        if period == 'hourly':
            return dt.strftime('p%Y_%m_%d_%Hh')
        elif period == 'daily':
            return dt.strftime('p%Y_%m_%d')
        elif period == 'weekly':
            return dt.strftime('p%Y_%Uw')
        elif period == 'monthly':
            return dt.strftime('p%Y_%m')
        return "p_unknown"

    def get_partition_description(self, dt: datetime, period: str) -> str:
        """Generate the partition description (Unix Timestamp) for VALUES LESS THAN."""
        # Partition boundary is the START of the NEXT period
        next_dt = self.get_next_date(dt, period, 1)
        
        if period == 'hourly':
            fmt = '%Y-%m-%d %H:00:00'
        else:
            fmt = '%Y-%m-%d 00:00:00'
            
        return next_dt.strftime(fmt)

    # --- Core Logic --- #

    def check_compatibility(self):
        """Verify Zabbix version and partitioning support."""
        # 1. Check MySQL Version
        version_str = self.execute_query('SELECT version()', fetch='one')
        if not version_str:
            raise DatabaseError("Could not determine MySQL version")
        
        # MySQL 8.0+ supports partitioning natively
        # (Assuming MySQL 8+ or MariaDB 10+ for modern Zabbix)
        self.logger.info(f"MySQL Version: {version_str}")
        
        # 2. Check Zabbix DB Version (optional info)
        try:
            mandatory = self.execute_query('SELECT `mandatory` FROM `dbversion`', fetch='one')
            if mandatory:
                 self.logger.info(f"Zabbix DB Mandatory Version: {mandatory}")
        except Exception:
             self.logger.warning("Could not read 'dbversion' table. Is this a Zabbix DB?")

    def get_table_min_clock(self, table: str) -> Optional[datetime]:
        ts = self.execute_query(f"SELECT MIN(`clock`) FROM `{table}`", fetch='one')
        return datetime.fromtimestamp(int(ts)) if ts else None

    def get_existing_partitions(self, table: str) -> List[Tuple[str, int]]:
        """Return list of (partition_name, description_timestamp)."""
        query = """
            SELECT `partition_name`, `partition_description`
            FROM `information_schema`.`partitions`
            WHERE `table_schema` = %s AND `table_name` = %s AND `partition_name` IS NOT NULL
            ORDER BY `partition_description` ASC
        """
        rows = self.execute_query(query, (self.db_name, table), fetch='all')
        if not rows:
            return []
        
        partitions = []
        for row in rows:
            name, desc = row
            # 'desc' is a string or int depending on DB driver, usually unix timestamp for TIMESTAMP partitions
            try:
                partitions.append((name, int(desc)))
            except (ValueError, TypeError):
                pass # MAXVALUE or invalid
        return partitions

    def has_incompatible_primary_key(self, table: str) -> bool:
        """
        Returns True if the table has a Primary Key that DOES NOT include the 'clock' column.
        Partitioning requires the partition column to be part of the Primary/Unique key.
        """
        # 1. Check if PK exists
        pk_exists = self.execute_query(
            """SELECT COUNT(*) FROM `information_schema`.`table_constraints` 
               WHERE `constraint_type` = 'PRIMARY KEY' 
               AND `table_schema` = %s AND `table_name` = %s""",
            (self.db_name, table), fetch='one'
        )
        
        if not pk_exists:
            # No PK means no restriction on partitioning
            return False

        # 2. Check if 'clock' is in the PK
        clock_in_pk = self.execute_query(
            """SELECT COUNT(*) FROM `information_schema`.`key_column_usage` k
               JOIN `information_schema`.`table_constraints` t USING(`constraint_name`, `table_schema`, `table_name`)
               WHERE t.`constraint_type` = 'PRIMARY KEY' 
               AND t.`table_schema` = %s AND t.`table_name` = %s AND k.`column_name` = 'clock'""",
            (self.db_name, table), fetch='one'
        )
        
        return not bool(clock_in_pk)

    def create_future_partitions(self, table: str, period: str, premake_count: int):
        """Create partitions for the future."""
        # Determine start date
        # If table is partitioned, start from the latest partition
        # If not, start from NOW (or min clock if we were doing initial load, but usually NOW for future)
        
        top_partition_ts = self.execute_query(
            """SELECT MAX(`partition_description`) FROM `information_schema`.`partitions`
               WHERE `table_schema` = %s AND `table_name` = %s AND `partition_name` IS NOT NULL""",
            (self.db_name, table), fetch='one'
        )
        
        curr_time = self.truncate_date(datetime.now(), period)
        
        if top_partition_ts:
            start_dt = datetime.fromtimestamp(int(top_partition_ts))
            # Start from the period AFTER the last existing one
            # Actually, MAX(description) is the *end* of the last partition. 
            # e.g. p2023_10_01 VALUES LESS THAN (Oct 2)
            # So start_dt is Oct 2.
        else:
            # No partitions? Should be handled by init, but fallback to NOW
            start_dt = self.truncate_date(datetime.now(), period)

        # Create 'premake_count' partitions ahead of NOW
        # But we must ensure we cover the gap if the last partition is old
        # So we ensure we have partitions up to NOW + premake * period
        
        target_max_date = self.get_next_date(curr_time, period, premake_count)
        
        current_planning_dt = start_dt
        
        new_partitions = {}
        
        while current_planning_dt < target_max_date:
            part_name = self.get_partition_name(current_planning_dt, period)
            part_desc = self.get_partition_description(current_planning_dt, period)
            new_partitions[part_name] = part_desc
            current_planning_dt = self.get_next_date(current_planning_dt, period, 1)

        if not new_partitions:
            return

        # Generate ADD PARTITION query
        parts_sql = []
        for name, timestamp_expr in sorted(new_partitions.items()):
            parts_sql.append(PARTITION_TEMPLATE % (name, timestamp_expr))
        
        query = f"ALTER TABLE `{table}` ADD PARTITION (\n" + ",\n".join(parts_sql) + "\n)"
        self.logger.info(f"Adding {len(new_partitions)} partitions to {table}")
        self.execute_query(query)

    def remove_old_partitions(self, table: str, retention_str: str):
        """Drop partitions older than retention period."""
        cutoff_date = self.get_lookback_date(retention_str)
        cutoff_ts = int(cutoff_date.timestamp())
        
        existing = self.get_existing_partitions(table)
        to_drop = []
        
        for name, desc_ts in existing:
            # Drop if the *upper bound* of the partition is still older than cutoff?
            # Or if it contains ONLY data older than cutoff?
            # VALUES LESS THAN (desc_ts). 
            # If desc_ts <= cutoff_ts, then ALL data in partition is < cutoff. Safe to drop.
            if desc_ts <= cutoff_ts:
                to_drop.append(name)
        
        if not to_drop:
            return

        self.logger.info(f"Dropping {len(to_drop)} old partitions from {table} (Retain: {retention_str})")
        for name in to_drop:
            self.execute_query(f"ALTER TABLE `{table}` DROP PARTITION {name}")

    def initialize_partitioning(self, table: str, period: str, premake: int, retention_str: str):
        """Initial partitioning for a table (convert regular table to partitioned)."""
        self.logger.info(f"Initializing partitioning for {table}")
        
        if self.has_incompatible_primary_key(table):
             self.logger.error(f"Cannot partition {table}: Primary Key does not include 'clock' column.")
             return

        # If already partitioned, skip
        if self.get_existing_partitions(table):
             self.logger.info(f"Table {table} is already partitioned.")
             return

        init_strategy = self.config.get('initial_partitioning_start', 'db_min')
        start_dt = None
        p_archive_ts = None

        if init_strategy == 'retention':
            self.logger.info(f"Strategy 'retention': Calculating start date from retention ({retention_str})")
            retention_date = self.get_lookback_date(retention_str)
            # Start granular partitions from the retention date
            start_dt = self.truncate_date(retention_date, period)
            # Create a catch-all for anything older
            p_archive_ts = int(start_dt.timestamp())
        else:
            # Default 'db_min' strategy
            self.logger.info("Strategy 'db_min': Querying table for minimum clock (may be slow)")
            min_clock = self.get_table_min_clock(table)
            
            if not min_clock:
                # Empty table. Start from NOW
                start_dt = self.truncate_date(datetime.now(), period)
            else:
                 # Table has data. 
                 start_dt = self.truncate_date(min_clock, period)
        
        # Build list of partitions from start_dt up to NOW + premake
        target_dt = self.get_next_date(self.truncate_date(datetime.now(), period), period, premake)
        
        curr = start_dt
        partitions_def = {}
        
        # If we have an archive partition, add it first
        if p_archive_ts:
             partitions_def['p_archive'] = str(p_archive_ts)

        while curr < target_dt:
            name = self.get_partition_name(curr, period)
            desc = self.get_partition_description(curr, period)
            partitions_def[name] = desc
            curr = self.get_next_date(curr, period, 1)
            
        # Re-doing the loop to be cleaner on types
        parts_sql = []
        
        # 1. Archive Partition
        if p_archive_ts:
             parts_sql.append(f"PARTITION p_archive VALUES LESS THAN ({p_archive_ts}) ENGINE = InnoDB")
        
        # 2. Granular Partitions
        # We need to iterate again from start_dt
        curr = start_dt
        while curr < target_dt:
            name = self.get_partition_name(curr, period)
            desc_date_str = self.get_partition_description(curr, period) # Returns "YYYY-MM-DD HH:MM:SS"
            parts_sql.append(PARTITION_TEMPLATE % (name, desc_date_str))
            curr = self.get_next_date(curr, period, 1)
            
        query = f"ALTER TABLE `{table}` PARTITION BY RANGE (`clock`) (\n" + ",\n".join(parts_sql) + "\n)"
        self.logger.info(f"Applying initial partitioning to {table} ({len(parts_sql)} partitions)")
        self.execute_query(query)

    def discovery(self):
        """Output Zabbix Low-Level Discovery logic JSON."""
        partitions_conf = self.config.get('partitions', {})
        discovery_data = []
        
        for period, tables in partitions_conf.items():
            if not tables:
                continue
            for item in tables:
                table = list(item.keys())[0]
                discovery_data.append({"{#TABLE}": table, "{#PERIOD}": period})
        
        print(json.dumps(discovery_data))

    def check_partitions_coverage(self, table: str, period: str) -> int:
        """
        Check how many days of future partitions exist for a table.
        Returns: Number of days from NOW until the end of the last partition.
        """
        top_partition_ts = self.execute_query(
            """SELECT MAX(`partition_description`) FROM `information_schema`.`partitions`
               WHERE `table_schema` = %s AND `table_name` = %s AND `partition_name` IS NOT NULL""",
            (self.db_name, table), fetch='one'
        )
        
        if not top_partition_ts:
            return 0
        
        # partition_description is "VALUES LESS THAN (TS)"
        # So it represents the END of the partition (start of next)
        end_ts = int(top_partition_ts)
        end_dt = datetime.fromtimestamp(end_ts)
        now = datetime.now()
        
        diff = end_dt - now
        return max(0, diff.days)

    def run(self, mode: str, target_table: str = None):
        """Main execution loop."""
        with self.connect_db():
            partitions_conf = self.config.get('partitions', {})
            
            # --- Discovery Mode ---
            if mode == 'discovery':
                self.discovery()
                return

            # --- Check Mode ---
            if mode == 'check':
                if not target_table:
                    # Check all and print simple status? Or error?
                    # Zabbix usually queries one by one.
                    # Implementing simple check which returns days for specific table
                    raise ConfigurationError("Target table required for check mode")
                
                # Find period for table
                found_period = None
                for period, tables in partitions_conf.items():
                    for item in tables:
                        if list(item.keys())[0] == target_table:
                            found_period = period
                            break
                    if found_period: break
                
                if not found_period:
                     # Table not in config?
                     print("-1") # Error code
                     return

                days_left = self.check_partitions_coverage(target_table, found_period)
                print(days_left)
                return

            # --- Normal Mode (Init/Maintain) ---
            self.check_compatibility()
            premake = self.config.get('premake', 10)
            
            if mode == 'delete':
                self.logger.warning("Delete Mode: Removing ALL partitioning from configured tables is not fully implemented in refactor yet.")
                # Implement if needed, usually just ALTER TABLE REMOVE PARTITIONING
                return

            for period, tables in partitions_conf.items():
                if not tables:
                    continue
                for item in tables:
                     # Item is dict like {'history': '14d'}
                     table = list(item.keys())[0]
                     retention = item[table]
                     
                     if mode == 'init':
                         self.initialize_partitioning(table, period, premake, retention)
                     else:
                         # Maintenance mode (Add new, remove old)
                         self.create_future_partitions(table, period, premake)
                         self.remove_old_partitions(table, retention)
            
            # Housekeeping extras
            if mode != 'init' and not self.dry_run:
                 self.logger.info("Partitioning completed successfully")

            if mode != 'init' and not self.dry_run:
                pass 

def setup_logging(config_log_type: str):
    logger = logging.getLogger('zabbix_partitioning')
    logger.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    if config_log_type == 'syslog':
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        formatter = logging.Formatter('%(name)s: %(message)s') 
    else:
        handler = logging.StreamHandler(sys.stdout)
        
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def parse_args():
    parser = argparse.ArgumentParser(description='Zabbix Partitioning Manager')
    parser.add_argument('-c', '--config', default='/etc/zabbix/zabbix_partitioning.conf', help='Config file path')
    parser.add_argument('-i', '--init', action='store_true', help='Initialize partitions')
    parser.add_argument('-d', '--delete', action='store_true', help='Remove partitions (Not implemented)')
    parser.add_argument('--dry-run', action='store_true', help='Simulate queries')
    
    # Monitoring args
    parser.add_argument('--discovery', action='store_true', help='Output Zabbix LLD JSON')
    parser.add_argument('--check-days', type=str, help='Check days of future partitions left for table', metavar='TABLE')
    
    return parser.parse_args()

def load_config(path):
    if not os.path.exists(path):
        # Fallback to local
        if os.path.exists('zabbix_partitioning.conf'):
            return 'zabbix_partitioning.conf'
        raise ConfigurationError(f"Config file not found: {path}")
    return path

def main():
    args = parse_args()
    
    try:
        conf_path = load_config(args.config)
        with open(conf_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # For discovery/check, we might want minimal logging or specific output, so we handle that in run()
        # But we still need basic logging setup for db errors
        
        mode = 'maintain'
        target = None
        
        if args.discovery:
            mode = 'discovery'
            config['logging'] = 'console' # Force console for discovery? Or suppress?
            # actually we don't want logs mixing with JSON output
            # so checking mode before setup logging
        elif args.check_days:
            mode = 'check'
            target = args.check_days
        elif args.init: mode = 'init'
        elif args.delete: mode = 'delete'
        
        # Setup logging
        # If discovery or check, we mute info logs to stdout to keep output clean, 
        # unless errors happen.
        if mode in ['discovery', 'check']:
             logging.basicConfig(level=logging.ERROR) # Only show critical errors
        else:
             setup_logging(config.get('logging', 'console'))
             
        logger = logging.getLogger('zabbix_partitioning')
        
        if args.dry_run:
            logger.info("Starting in DRY-RUN mode")
        
        # ZabbixPartitioner expects dict config
        app = ZabbixPartitioner(config, dry_run=args.dry_run)
        app.run(mode, target)
        
    except Exception as e:
        # Important: Zabbix log monitoring needs to see "Failed"
        # We print to stderr for script failure, logging handles log file
        try:
             logging.getLogger('zabbix_partitioning').critical(f"Partitioning failed: {e}")
        except:
             pass
        print(f"Critical Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()