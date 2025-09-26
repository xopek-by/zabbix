#!/usr/bin/env python3

import os
import glob
from zabbix_utils import ZabbixAPI

# Configuration from environment variables
ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/api_jsonrpc.php")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
IMPORT_DIR = os.environ.get("IMPORT_DIR", "/opt/python/export")


def get_import_rules():
    """Define import rules based on requirements."""
    return {
        # Host/Template level - only create/update, never delete
        "hosts": {
            "createMissing": True,
            "updateExisting": True
        },
        "templates": {
            "createMissing": True,
            "updateExisting": True
        },
        "host_groups": {
            "createMissing": True,
            "updateExisting": True
        },
        "template_groups": {
            "createMissing": True,
            "updateExisting": True
        },
        # Inside host/template - allow all changes including deletion
        "items": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "triggers": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "discoveryRules": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "graphs": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "httptests": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "valueMaps": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "templateDashboards": {
            "createMissing": True,
            "updateExisting": True,
            "deleteMissing": True
        },
        "templateLinkage": {
            "createMissing": True,
            "deleteMissing": False  # Don't unlink templates
        }
    }


def import_file(zapi, file_path, file_type):
    """Import a single XML file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        print(f"  Importing {file_type}: {os.path.basename(file_path)}")
        
        result = zapi.configuration.import_(
            format='xml',
            source=xml_content,
            rules=get_import_rules()
        )
        
        if result:
            print(f"    Success: {os.path.basename(file_path)}")
        else:
            print(f"    Failed: {os.path.basename(file_path)}")
        
        return result
        
    except Exception as e:
        print(f"    Error importing {file_path}: {e}")
        return False


def import_host_directory(zapi, host_dir):
    """Import all files from a single host directory."""
    host_id = os.path.basename(host_dir)
    print(f"Importing configuration for host directory: {host_id}")
    
    # Get all template and host files
    template_files = glob.glob(os.path.join(host_dir, "template_*.xml"))
    host_files = glob.glob(os.path.join(host_dir, "host_*.xml"))
    
    if not template_files and not host_files:
        print(f"  No XML files found in {host_dir}")
        return False
    
    success_count = 0
    total_count = 0
    
    # Import templates first
    for template_file in sorted(template_files):
        total_count += 1
        if import_file(zapi, template_file, "template"):
            success_count += 1
    
    # Import hosts after templates
    for host_file in sorted(host_files):
        total_count += 1
        if import_file(zapi, host_file, "host"):
            success_count += 1
    
    print(f"  Host {host_id}: {success_count}/{total_count} files imported successfully")
    return success_count == total_count


def main():
    if not BEARER_TOKEN:
        print("Error: BEARER_TOKEN not set")
        return
    
    if not os.path.exists(IMPORT_DIR):
        print(f"Error: Import directory does not exist: {IMPORT_DIR}")
        return
    
    # Connect to Zabbix
    try:
        zapi = ZabbixAPI(url=ZABBIX_URL)
        zapi.login(token=BEARER_TOKEN)
        print(f"Connected to Zabbix at {ZABBIX_URL}")
    except Exception as e:
        print(f"Failed to connect to Zabbix: {e}")
        return
    
    # Find all host directories
    host_dirs = [
        d for d in glob.glob(os.path.join(IMPORT_DIR, "*"))
        if os.path.isdir(d) and os.path.basename(d).isdigit()
    ]
    
    if not host_dirs:
        print(f"No host directories found in {IMPORT_DIR}")
        return
    
    host_dirs.sort(key=lambda x: int(os.path.basename(x)))
    print(f"Found {len(host_dirs)} host directories to import")
    
    # Import each host directory
    successful_hosts = 0
    for host_dir in host_dirs:
        try:
            if import_host_directory(zapi, host_dir):
                successful_hosts += 1
        except Exception as e:
            print(f"Error processing {host_dir}: {e}")
    
    print(f"\nImport completed! Successfully processed {successful_hosts}/{len(host_dirs)} host directories.")


if __name__ == "__main__":
    main()