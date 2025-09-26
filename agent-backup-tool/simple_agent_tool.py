#!/usr/bin/env python3
"""
Simple Zabbix Agent Backup/Upgrade Tool - PoC
"""

import os
import sys
import argparse
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

ZABBIX_CONFIG_DIR = "/etc/zabbix"
SCRIPT_DIR = Path(__file__).parent.absolute()
BACKUP_DIR = SCRIPT_DIR / "backups"

def run_command(cmd):
    """Run command and return result"""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.strip()}")
        sys.exit(1)
    return result

def backup_configs():
    """Backup zabbix configs"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_DIR / f"backup_{timestamp}"
    backup_dir.mkdir()
    
    config_files = list(Path(ZABBIX_CONFIG_DIR).glob("zabbix_agent*.conf"))
    if not config_files:
        print("No config files found")
        return None
    
    for config_file in config_files:
        shutil.copy2(config_file, backup_dir / config_file.name)
        print(f"Backed up: {config_file.name}")
    
    print(f"Backup saved to: {backup_dir}")
    return str(backup_dir)

def restore_configs(backup_path):
    """Restore configs from backup"""
    backup_dir = Path(backup_path)
    if not backup_dir.exists():
        print(f"Backup not found: {backup_path}")
        sys.exit(1)
    
    config_files = list(backup_dir.glob("zabbix_agent*.conf"))
    for config_file in config_files:
        target = Path(ZABBIX_CONFIG_DIR) / config_file.name
        shutil.copy2(config_file, target)
        print(f"Restored: {config_file.name}")
    
    # Restart service
    services = ['zabbix-agent2', 'zabbix-agent']
    for service in services:
        try:
            run_command(f"sudo systemctl restart {service}")
            print(f"Restarted: {service}")
            break
        except:
            continue

def upgrade_system():
    """Simple system upgrade"""
    if os.path.exists('/etc/debian_version'):
        run_command("sudo apt update")
        run_command("sudo apt upgrade -y")
    else:
        try:
            run_command("sudo yum update -y")
        except:
            run_command("sudo dnf update -y")

def main():
    parser = argparse.ArgumentParser(description="Simple Zabbix Agent Tool")
    parser.add_argument('action', choices=['backup', 'restore', 'upgrade'])
    parser.add_argument('--backup-path', help='Backup path for restore')
    args = parser.parse_args()

    if args.action == 'backup':
        backup_path = backup_configs()
        if backup_path:
            print(f"SUCCESS: Backup created at {backup_path}")
    
    elif args.action == 'restore':
        if not args.backup_path:
            print("ERROR: --backup-path required")
            sys.exit(1)
        restore_configs(args.backup_path)
        print("SUCCESS: Restore completed")
    
    elif args.action == 'upgrade':
        print("Creating backup before upgrade...")
        backup_path = backup_configs()
        print("Upgrading system...")
        upgrade_system()
        print("Restoring configs...")
        restore_configs(backup_path)
        print(f"SUCCESS: Upgrade completed. Backup at {backup_path}")

if __name__ == "__main__":
    main()