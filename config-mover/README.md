# Zabbix Configuration Export/Import Scripts

Simple POC scripts for exporting and importing Zabbix host configurations and templates.

## Files

- `config_exporter.py` - Export hosts and templates
- `config_importer.py` - Import hosts and templates  
- `run_export.sh` - Example export script
- `run_import.sh` - Example import script
- `requirements.txt` - Python dependencies

## Setup

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Set environment variables in run scripts

## Export

Exports hosts and their linked templates to organized directories:

```bash
export ZABBIX_URL="https://your-zabbix.com/api_jsonrpc.php"
export BEARER_TOKEN="your_api_token"
export HOST_IDS="10591,10592,10593"  # Comma-separated
export OUTPUT_DIR="/path/to/export"
./run_export.sh
```

### Output Structure
```
export/
├── 10591/
│   ├── host_10591.xml
│   ├── template_Linux_by_Zabbix_agent.xml
│   └── template_Generic_SNMP.xml
└── 10592/
    ├── host_10592.xml
    └── template_Windows_by_Zabbix_agent.xml
```

## Import

Imports configurations from export directory structure:

```bash
export ZABBIX_URL="https://your-zabbix.com/api_jsonrpc.php" 
export BEARER_TOKEN="your_api_token"
export IMPORT_DIR="/path/to/export"  # Directory with host subdirectories
./run_import.sh
```

### Import Rules

- **Hosts/Templates**: Create new, update existing, never delete
- **Inside hosts/templates**: Create, update, and delete items/triggers/etc
- **Templates imported first**, then hosts (for proper linking)

### Process

1. Finds all numbered directories (10591, 10592, etc)
2. For each directory:
   - Import all `template_*.xml` files first
   - Import all `host_*.xml` files after
3. Reports success/failure per directory

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ZABBIX_URL` | Zabbix API endpoint | `http://localhost/api_jsonrpc.php` |
| `BEARER_TOKEN` | API token | Required |
| `HOST_IDS` | Comma-separated host IDs to export | `10591` |
| `OUTPUT_DIR` | Export base directory | `/opt/python/export` |
| `IMPORT_DIR` | Import base directory | `/opt/python/export` |