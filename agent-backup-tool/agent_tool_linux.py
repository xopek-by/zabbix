#!/usr/bin/env python3
"""
Zabbix Agent Management Tool
============================

This script provides functionality to:
1. Backup Zabbix agent configuration files
2. Restore Zabbix agent configuration files
3. Upgrade Zabbix agent while preserving custom configurations

Author: GitHub Copilot
Date: September 2025
"""

import os
import sys
import argparse
import subprocess
import shutil
import glob
import difflib
import logging
from datetime import datetime
from pathlib import Path
import re

# Configuration
ZABBIX_CONFIG_DIR = "/etc/zabbix"
SCRIPT_DIR = Path(__file__).parent.absolute()
DEFAULT_CONFIG_FILE = SCRIPT_DIR / "zabbix_agentd.conf"
BACKUP_DIR = SCRIPT_DIR / "backups"
LOG_FILE = SCRIPT_DIR / "agent_tool.log"

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ZabbixAgentTool:
    def __init__(self):
        self.distro_family = self._detect_distro_family()
        self.backup_dir = BACKUP_DIR
        self.backup_dir.mkdir(exist_ok=True)
        
    def _detect_distro_family(self):
        """Detect if the system is Debian-based or RHEL-based"""
        # Detection rules: (file_path, keywords_for_debian, keywords_for_rhel)
        detection_rules = [
            ('/etc/debian_version', True, False),
            ('/etc/redhat-release', False, True),
            ('/etc/centos-release', False, True),
            ('/etc/os-release', ['debian', 'ubuntu'], ['centos', 'rhel', 'fedora'])
        ]
        
        for file_path, debian_check, rhel_check in detection_rules:
            if not os.path.exists(file_path):
                continue
                
            try:
                if isinstance(debian_check, bool):
                    return 'debian' if debian_check else 'rhel'
                
                # For os-release, check content
                with open(file_path, 'r') as f:
                    content = f.read().lower()
                    if any(keyword in content for keyword in debian_check):
                        return 'debian'
                    elif any(keyword in content for keyword in rhel_check):
                        return 'rhel'
            except Exception as e:
                logger.debug(f"Error reading {file_path}: {e}")
                continue
        
        logger.warning("Unknown distribution family, defaulting to debian")
        return 'debian'
    
    def _get_config_files(self):
        """Find all Zabbix agent configuration files"""
        patterns = [f"{ZABBIX_CONFIG_DIR}/zabbix_agent*.conf"]
        return [f for pattern in patterns for f in glob.glob(pattern)]
    
    def _run_command(self, command, check=True, log_output=False):
        """Run a shell command and return the result"""
        logger.info(f"Running: {command}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
            if log_output and result.stdout:
                logger.debug(f"Output: {result.stdout.strip()}")
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {command}")
            if e.stderr:
                logger.error(f"Error: {e.stderr.strip()}")
            raise
    
    def _parse_config_file(self, config_path):
        """Parse configuration file and extract uncommented settings"""
        try:
            with open(config_path, 'r') as f:
                return [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except Exception as e:
            logger.error(f"Error parsing config file {config_path}: {e}")
            raise
    
    def backup_configs(self):
        """Backup existing Zabbix agent configuration files"""
        config_files = self._get_config_files()
        if not config_files:
            logger.warning("No Zabbix agent configuration files found to backup")
            return None
        
        # Create backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = self.backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir(exist_ok=True)
        
        # Backup files and track results
        backed_up_files = []
        for config_file in config_files:
            try:
                backup_file = backup_subdir / Path(config_file).name
                shutil.copy2(config_file, backup_file)
                logger.info(f"Backed up {config_file}")
                backed_up_files.append((config_file, str(backup_file)))
            except Exception as e:
                logger.error(f"Failed to backup {config_file}: {e}")
        
        # Create manifest
        self._create_backup_manifest(backup_subdir, backed_up_files)
        logger.info(f"Backup completed: {backup_subdir}")
        return str(backup_subdir)
    
    def _create_backup_manifest(self, backup_dir, backed_up_files):
        """Create backup manifest file"""
        manifest_file = backup_dir / "backup_manifest.txt"
        with open(manifest_file, 'w') as f:
            f.write(f"Backup created: {datetime.now()}\n")
            f.write(f"Distribution family: {self.distro_family}\n")
            f.write("Backed up files:\n")
            for original, backup in backed_up_files:
                f.write(f"  {original} -> {backup}\n")
    
    def restore_configs(self, backup_path):
        """Restore Zabbix agent configuration files from backup"""
        backup_dir = Path(backup_path)
        if not backup_dir.exists():
            raise FileNotFoundError(f"Backup directory not found: {backup_path}")
        
        # Log manifest if available
        manifest_file = backup_dir / "backup_manifest.txt"
        if manifest_file.exists():
            logger.info(f"Restoring from backup: {backup_path}")
            with open(manifest_file, 'r') as f:
                logger.info(f"Manifest:\n{f.read()}")
        
        # Find and restore config files
        backup_configs = list(backup_dir.glob("zabbix_agent*.conf"))
        if not backup_configs:
            raise FileNotFoundError("No configuration files found in backup directory")
        
        restored_files = []
        for backup_file in backup_configs:
            try:
                target_file = Path(ZABBIX_CONFIG_DIR) / backup_file.name
                
                # Backup current file if it exists
                if target_file.exists():
                    shutil.copy2(target_file, target_file.with_suffix(".conf.pre-restore"))
                
                shutil.copy2(backup_file, target_file)
                logger.info(f"Restored {backup_file.name}")
                restored_files.append(str(target_file))
            except Exception as e:
                logger.error(f"Failed to restore {backup_file}: {e}")
        
        self._restart_zabbix_agent()
        logger.info(f"Restore completed. Files: {[Path(f).name for f in restored_files]}")
        return restored_files
    
    def _restart_zabbix_agent(self):
        """Restart Zabbix agent service"""
        services = ['zabbix-agent2', 'zabbix-agent', 'zabbix-agentd']
        
        for service in services:
            try:
                # Check if service exists and restart it
                if self._run_command(f"systemctl list-unit-files {service}.service", check=False).returncode == 0:
                    self._run_command(f"sudo systemctl restart {service}")
                    self._run_command(f"sudo systemctl enable {service}")
                    logger.info(f"Successfully restarted {service}")
                    return
            except Exception as e:
                logger.debug(f"Could not restart {service}: {e}")
        
        logger.warning("Could not restart any Zabbix agent service")
    
    def upgrade_agent(self):
        """Upgrade Zabbix agent while preserving custom configurations"""
        logger.info("Starting Zabbix agent upgrade process")
        
        # Backup and extract custom settings
        backup_path = self.backup_configs()
        if not backup_path:
            raise Exception("Failed to create backup before upgrade")
        
        custom_settings = {Path(f).name: self._parse_config_file(f) for f in self._get_config_files()}
        
        # Upgrade package
        self._upgrade_zabbix_package()
        
        # Merge custom settings into new configs
        for config_file in self._get_config_files():
            config_name = Path(config_file).name
            if config_name in custom_settings:
                self._merge_custom_settings(config_file, custom_settings[config_name], backup_path)
        
        self._restart_zabbix_agent()
        logger.info("Zabbix agent upgrade completed successfully")
        return backup_path
    
    def _upgrade_zabbix_package(self):
        """Upgrade Zabbix agent package based on distribution family"""
        logger.info(f"Upgrading Zabbix agent on {self.distro_family}-based system")
        
        if self.distro_family == 'debian':
            # Update package lists
            self._run_command("sudo apt update")
            
            # Check what zabbix packages are installed first
            result = self._run_command("dpkg -l | grep -E 'zabbix-agent'", check=False, log_output=True)
            if result.returncode != 0:
                logger.warning("No Zabbix agent packages found installed")
                return
            
            # Get list of installed zabbix agent packages
            installed_packages = []
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if 'zabbix-agent' in line:
                        # Extract package name from dpkg output
                        parts = line.split()
                        if len(parts) >= 2:
                            package_name = parts[1]
                            installed_packages.append(package_name)
            
            if not installed_packages:
                logger.warning("No Zabbix agent packages found to upgrade")
                return
            
            # Upgrade each installed package individually
            for package in installed_packages:
                try:
                    logger.info(f"Upgrading {package}")
                    # Use DEBIAN_FRONTEND=noninteractive to avoid prompts
                    self._run_command(f"sudo DEBIAN_FRONTEND=noninteractive apt upgrade -y {package}")
                except Exception as e:
                    logger.warning(f"Could not upgrade {package}: {e}")
                    
        elif self.distro_family == 'rhel':
            # For RHEL-based systems
            try:
                # Try yum first
                result = self._run_command("yum list installed | grep zabbix-agent", check=False)
                if result.returncode == 0:
                    self._run_command("sudo yum update -y zabbix-agent*")
                else:
                    # Try dnf
                    result = self._run_command("dnf list installed | grep zabbix-agent", check=False)
                    if result.returncode == 0:
                        self._run_command("sudo dnf update -y zabbix-agent*")
                    else:
                        logger.warning("No Zabbix agent packages found to upgrade")
            except Exception as e:
                logger.warning(f"Could not upgrade packages: {e}")
        else:
            raise Exception(f"Unsupported distribution family: {self.distro_family}")
    
    def _merge_custom_settings(self, new_config_file, custom_settings, backup_path):
        """Merge custom settings into new configuration file"""
        logger.info(f"Merging custom settings into {new_config_file}")
        
        # Parse custom settings into key-value pairs
        custom_params = {}
        for setting in custom_settings:
            if '=' in setting:
                key, value = setting.split('=', 1)
                custom_params[key.strip()] = value.strip()
        
        # Read and process configuration file
        with open(new_config_file, 'r') as f:
            lines = f.readlines()
        
        original_lines = lines.copy()
        updated_lines = []
        
        # Process each line
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                updated_lines.append(line)
            elif '=' in stripped:
                key = stripped.split('=', 1)[0].strip()
                if key in custom_params:
                    updated_lines.append(f"{key}={custom_params.pop(key)}\n")
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Add remaining custom parameters
        if custom_params:
            updated_lines.extend(["\n# Custom parameters added during upgrade\n"] + 
                               [f"{k}={v}\n" for k, v in custom_params.items()])
        
        # Write updated configuration and save diff
        with open(new_config_file, 'w') as f:
            f.writelines(updated_lines)
        
        self._save_config_diff(new_config_file, original_lines, updated_lines, backup_path)
        logger.info(f"Custom settings merged into {new_config_file}")
    
    def _save_config_diff(self, config_file, original_lines, updated_lines, backup_path):
        """Save the differences between original and updated configuration"""
        config_name = Path(config_file).name
        diff_file = Path(backup_path) / f"{config_name}.diff"
        
        diff = difflib.unified_diff(
            original_lines,
            updated_lines,
            fromfile=f"{config_name}.original",
            tofile=f"{config_name}.updated",
            lineterm=''
        )
        
        with open(diff_file, 'w') as f:
            f.writelines(diff)
        
        logger.info(f"Configuration differences saved to {diff_file}")
    
    def list_backups(self):
        """List available backups"""
        if not self.backup_dir.exists():
            logger.info("No backups directory found")
            return []
        
        backup_dirs = [d for d in self.backup_dir.iterdir() if d.is_dir() and d.name.startswith('backup_')]
        backup_dirs.sort(key=lambda x: x.name, reverse=True)  # Most recent first
        
        backups = []
        for backup_dir in backup_dirs:
            manifest_file = backup_dir / "backup_manifest.txt"
            info = {"path": str(backup_dir), "timestamp": backup_dir.name.replace('backup_', '')}
            
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r') as f:
                        content = f.read()
                        info["manifest"] = content
                except Exception as e:
                    info["manifest"] = f"Error reading manifest: {e}"
            
            backups.append(info)
        
        return backups


def main():
    parser = argparse.ArgumentParser(description="Zabbix Agent Management Tool")
    parser.add_argument(
        'action',
        choices=['backup', 'restore', 'upgrade', 'list-backups'],
        help='Action to perform'
    )
    parser.add_argument(
        '--backup-path',
        help='Path to backup directory (required for restore action)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        tool = ZabbixAgentTool()
        
        if args.action == 'backup':
            backup_path = tool.backup_configs()
            if backup_path:
                print(f"Backup created successfully: {backup_path}")
            else:
                print("No configuration files found to backup")
        
        elif args.action == 'restore':
            if not args.backup_path:
                print("Error: --backup-path is required for restore action")
                sys.exit(1)
            
            restored_files = tool.restore_configs(args.backup_path)
            print(f"Restore completed successfully. Restored files: {restored_files}")
        
        elif args.action == 'upgrade':
            backup_path = tool.upgrade_agent()
            print(f"Upgrade completed successfully. Backup created: {backup_path}")
        
        elif args.action == 'list-backups':
            backups = tool.list_backups()
            if not backups:
                print("No backups found")
            else:
                print("Available backups:")
                for backup in backups:
                    print(f"\nBackup: {backup['path']}")
                    print(f"Timestamp: {backup['timestamp']}")
                    if 'manifest' in backup:
                        print("Manifest:")
                        print(backup['manifest'])
    
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()