# Zabbix Agent Management Tool

A comprehensive Python script for managing Zabbix agent configurations, including backup, restore, and upgrade operations.

## Features

- **Backup**: Create timestamped backups of all Zabbix agent configuration files
- **Restore**: Restore configuration files from previous backups
- **Upgrade**: Upgrade Zabbix agent while preserving custom configurations
- **List Backups**: View all available backups with timestamps and details

## Requirements

- Python 3.6+
- Root/sudo privileges for system operations
- Zabbix agent installed on the system

## Quick Start

```bash
# Make the script executable
chmod +x agent_tool_linux.py

# See all available options
./agent_tool_linux.py --help

# Most common use case - upgrade agent safely
./agent_tool_linux.py upgrade
```

## Usage

### Basic Commands

```bash
# Create a backup of current configurations
./agent_tool_linux.py backup

# List all available backups
./agent_tool_linux.py list-backups

# Restore from a specific backup
./agent_tool_linux.py restore --backup-path /path/to/backup/directory

# Upgrade agent while preserving custom settings
./agent_tool_linux.py upgrade

# Enable verbose logging
./agent_tool_linux.py backup --verbose
```

### Examples

1. **Create a backup before making changes:**
   ```bash
   ./agent_tool_linux.py backup
   ```

2. **Upgrade the agent (recommended workflow):**
   ```bash
   # The upgrade command automatically creates a backup first
   ./agent_tool_linux.py upgrade
   ```

3. **Restore from the most recent backup:**
   ```bash
   # First, list available backups
   ./agent_tool_linux.py list-backups
   
   # Then restore from a specific backup
   ./agent_tool_linux.py restore --backup-path ./backups/backup_20250925_143022
   ```

## How It Works

### Backup Process
- Automatically detects all Zabbix agent configuration files in `/etc/zabbix/`
- Supports both `zabbix_agentd.conf` and `zabbix_agent2.conf` files
- Creates timestamped backup directories
- Generates a backup manifest with metadata

### Restore Process
- Restores configuration files from backup directories
- Creates safety backups of current files before restoration
- Automatically restarts the Zabbix agent service

### Upgrade Process
1. **Backup**: Creates a backup of current configurations
2. **Parse**: Extracts all uncommented (custom) settings from current configs
3. **Upgrade**: Updates the Zabbix agent package using the appropriate package manager
4. **Merge**: Integrates custom settings into new configuration files
5. **Diff**: Saves differences showing what was added to new configs
6. **Restart**: Restarts the Zabbix agent service

### Distribution Support
- **Debian-based**: Ubuntu, Debian (uses `apt`)
- **RHEL-based**: CentOS, RHEL, Fedora (uses `yum`/`dnf`)

## File Structure

```
zbx-agent-backup/
├── agent_tool_linux.py          # Main script
├── zabbix_agentd.conf           # Default/template configuration
├── backups/                     # Backup storage directory
│   ├── backup_20250925_143022/  # Timestamped backup
│   │   ├── zabbix_agentd.conf   # Backed up config
│   │   ├── backup_manifest.txt  # Backup metadata
│   │   └── *.diff               # Configuration differences (after upgrade)
└── agent_tool.log               # Script execution log
```

## Configuration Files Handled

The script automatically detects and handles:
- `/etc/zabbix/zabbix_agentd.conf`
- `/etc/zabbix/zabbix_agent2.conf`
- `/etc/zabbix/zabbix_agentd*.conf` (any variant)
- `/etc/zabbix/zabbix_agent*.conf` (any variant)

## Logging

- All operations are logged to `agent_tool.log`
- Console output shows important status messages
- Use `--verbose` flag for detailed debug information
- Log rotation is handled automatically

## Safety Features

- **Pre-restoration backup**: Current configs are backed up before restoration
- **Manifest files**: Each backup includes metadata and file listings
- **Diff files**: Upgrade process saves differences showing what was changed
- **Service management**: Automatically handles service restart and enabling
- **Error handling**: Comprehensive error checking and logging

## Troubleshooting

### Common Issues

1. **Permission denied**: Make sure to run with sudo for system operations
2. **No config files found**: Verify Zabbix agent is installed and configs exist
3. **Service restart failed**: Check if Zabbix agent service is properly installed
4. **Package upgrade failed**: Verify package repositories are configured

### Debug Mode
```bash
./agent_tool_linux.py backup --verbose
```

### Manual Service Restart
If automatic service restart fails:
```bash
sudo systemctl restart zabbix-agent2
# or
sudo systemctl restart zabbix-agent
```

## Security Considerations

- Script requires sudo privileges for package management and service control
- Configuration files may contain sensitive information
- Backup files are stored locally and should be protected appropriately
- Log files may contain system information

## License

This script is provided as-is for system administration purposes.
