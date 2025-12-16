import os
import sys
import yaml
import subprocess

def generate_config():
    # Base Configuration
    config = {
        'database': {
            'type': 'mysql',
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'zabbix'),
            'passwd': os.getenv('DB_PASSWORD', 'zabbix'),
            'db': os.getenv('DB_NAME', 'zabbix'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'socket': os.getenv('DB_SOCKET', '')
        },
        'logging': 'console',
        'premake': int(os.getenv('PREMAKE', 10)),
        'replicate_sql': os.getenv('REPLICATE_SQL', 'False').lower() == 'true',
        'initial_partitioning_start': os.getenv('INITIAL_PARTITIONING_START', 'db_min'),
        'partitions': {
            'daily': [],
            'weekly': [],
            'monthly': []
        }
    }

    # SSL Config
    if os.getenv('DB_SSL_CA'):
         config['database']['ssl'] = {'ca': os.getenv('DB_SSL_CA')}
         if os.getenv('DB_SSL_CERT'): config['database']['ssl']['cert'] = os.getenv('DB_SSL_CERT')
         if os.getenv('DB_SSL_KEY'): config['database']['ssl']['key'] = os.getenv('DB_SSL_KEY')

    # Retention Mapping
    retention_history = os.getenv('RETENTION_HISTORY', '14d')
    retention_trends = os.getenv('RETENTION_TRENDS', '365d')
    retention_audit = os.getenv('RETENTION_AUDIT', '365d')

    # Standard Zabbix Tables
    history_tables = ['history', 'history_uint', 'history_str', 'history_log', 'history_text', 'history_bin']
    trends_tables = ['trends', 'trends_uint']
    
    # Auditlog: Disabled by default because Zabbix 7.0+ 'auditlog' table lacks 'clock' in Primary Key.
    # Only enable if the user has manually altered the schema and explicitly requests it.
    
    # Collect overrides first to prevent duplicates
    overrides = set()
    for key in os.environ:
        if key.startswith(('PARTITION_DAILY_', 'PARTITION_WEEKLY_', 'PARTITION_MONTHLY_')):
             table = key.split('_', 2)[-1].lower()
             overrides.add(table)

    for table in history_tables:
        if table not in overrides:
             config['partitions']['daily'].append({table: retention_history})
        
    for table in trends_tables:
        if table not in overrides:
             config['partitions']['monthly'].append({table: retention_trends})
        
    if os.getenv('ENABLE_AUDITLOG_PARTITIONING', 'false').lower() == 'true':
         config['partitions']['weekly'].append({'auditlog': retention_audit})

    # Custom/Generic Overrides
    # Look for env vars like PARTITION_DAILY_mytable=7d
    for key, value in os.environ.items():
        if key.startswith('PARTITION_DAILY_'):
            table = key.replace('PARTITION_DAILY_', '').lower()
            config['partitions']['daily'].append({table: value})
        elif key.startswith('PARTITION_WEEKLY_'):
             table = key.replace('PARTITION_WEEKLY_', '').lower()
             config['partitions']['weekly'].append({table: value})
        elif key.startswith('PARTITION_MONTHLY_'):
             table = key.replace('PARTITION_MONTHLY_', '').lower()
             config['partitions']['monthly'].append({table: value})

    # Filter empty lists
    config['partitions'] = {k: v for k, v in config['partitions'].items() if v}

    print("Generated Configuration:")
    print(yaml.dump(config, default_flow_style=False))
    
    with open('/etc/zabbix/zabbix_partitioning.conf', 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def main():
    generate_config()
    
    cmd = [sys.executable, '/usr/local/bin/zabbix_partitioning.py', '-c', '/etc/zabbix/zabbix_partitioning.conf']
    
    run_mode = os.getenv('RUN_MODE', 'maintenance')
    if run_mode == 'init':
        cmd.append('--init')
    elif run_mode == 'dry-run':
        cmd.append('--dry-run')
        if os.getenv('DRY_RUN_INIT') == 'true':
             cmd.append('--init')
    elif run_mode == 'discovery':
        cmd.append('--discovery')
    elif run_mode == 'check':
        target = os.getenv('CHECK_TARGET')
        if not target:
             print("Error: CHECK_TARGET env var required for check mode")
             sys.exit(1)
        cmd.append('--check-days')
        cmd.append(target)
    elif run_mode == 'stats':
        target = os.getenv('CHECK_TARGET')
        if not target:
             print("Error: CHECK_TARGET env var required for stats mode")
             sys.exit(1)
        cmd.append('--stats')
        cmd.append(target)
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
