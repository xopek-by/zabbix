# Scripts Collection

This repository contains various system administration and utility scripts.

## Available Scripts

### 1. Docker Cleanup (`docker_cleanup.sh`)
A simple script for cleaning up Docker containers, images, and system resources.

### 2. Zabbix Agent Management Tool (`zbx-agent-backup/`)
A comprehensive Python tool for managing Zabbix agent configurations:

- **Backup**: Create timestamped backups of Zabbix agent configurations
- **Restore**: Restore configurations from previous backups  
- **Upgrade**: Upgrade Zabbix agent while preserving custom settings
- **List**: View all available backups with details

**Key Features:**
- Supports both Debian and RHEL-based distributions
- Automatic detection of `zabbix_agentd.conf` and `zabbix_agent2.conf` files
- Preserves custom configurations during upgrades
- Generates diff files showing what was changed
- Comprehensive logging and error handling
- Service management (restart/enable)

**Usage:**
```bash
cd zbx-agent-backup/
./agent_tool_linux.py backup                    # Create backup
./agent_tool_linux.py upgrade                   # Upgrade agent
./agent_tool_linux.py restore --backup-path <path>  # Restore from backup
./agent_tool_linux.py list-backups             # List available backups
```

See `zbx-agent-backup/README.md` for detailed documentation.

## Important Notice

When downloading and running scripts from the internet, it is crucial to understand what the script does. Running unknown scripts can pose security risks, such as exposing your system to malware or other malicious activities. Always review the code and ensure it comes from a trusted source before executing it.