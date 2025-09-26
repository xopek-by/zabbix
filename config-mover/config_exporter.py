#!/usr/bin/env python3

import os
import xml.etree.ElementTree as ET
from zabbix_utils import ZabbixAPI

# Configuration from environment variables
ZABBIX_URL = os.environ.get("ZABBIX_URL", "http://localhost/api_jsonrpc.php")
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
HOST_IDS = os.environ.get("HOST_IDS", "10591")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/opt/python/export")


def get_template_names(xml_data):
    """Extract template names from host XML."""
    try:
        root = ET.fromstring(xml_data)
        return [name.text for name in root.findall('.//hosts/host/templates/template/name')]
    except ET.ParseError:
        return []


def export_templates(zapi, template_names, output_dir):
    """Export templates to XML files."""
    if not template_names:
        return
    
    templates = zapi.template.get(output=['templateid', 'host'], filter={'host': template_names})
    
    for template in templates:
        name = template['host']
        template_id = template['templateid']
        
        xml_data = zapi.configuration.export(options={'templates': [template_id]}, format='xml')
        
        if xml_data:
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
            filename = f"template_{safe_name}.xml"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(xml_data)
            print(f"  Exported: {filename}")


def export_host(zapi, host_id, base_dir):
    """Export single host and its templates."""
    host_dir = os.path.join(base_dir, str(host_id))
    os.makedirs(host_dir, exist_ok=True)
    
    print(f"Exporting host {host_id}...")
    
    # Export host
    host_xml = zapi.configuration.export(options={'hosts': [host_id]}, format='xml')
    if not host_xml:
        print(f"  Failed to export host {host_id}")
        return
    
    # Save host XML
    host_file = os.path.join(host_dir, f"host_{host_id}.xml")
    with open(host_file, 'w', encoding='utf-8') as f:
        f.write(host_xml)
    print(f"  Host saved: host_{host_id}.xml")
    
    # Export templates
    template_names = get_template_names(host_xml)
    if template_names:
        print(f"  Found {len(template_names)} templates")
        export_templates(zapi, template_names, host_dir)


def main():
    if not BEARER_TOKEN:
        print("Error: BEARER_TOKEN not set")
        return
    
    host_ids = [h.strip() for h in HOST_IDS.split(',') if h.strip()]
    if not host_ids:
        print("Error: No HOST_IDS provided")
        return
    
    # Connect to Zabbix
    zapi = ZabbixAPI(url=ZABBIX_URL)
    zapi.login(token=BEARER_TOKEN)
    print(f"Connected to Zabbix at {ZABBIX_URL}")
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Export each host
    for host_id in host_ids:
        try:
            export_host(zapi, host_id, OUTPUT_DIR)
        except Exception as e:
            print(f"Error exporting host {host_id}: {e}")
    
    print(f"Export complete. Results in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

