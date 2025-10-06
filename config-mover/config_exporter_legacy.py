#!/usr/bin/env python3
"""
Legacy Zabbix Configuration Exporter
====================================
Uses username/password authentication instead of Bearer tokens.
Note: This script is designed for Zabbix 5.0 and older versions!
Please do not use with Zabbix 6.0 and newer! Use token-based method instead.
"""

import os
import xml.etree.ElementTree as ET
from zabbix_utils import ZabbixAPI

# Configuration from environment variables
ZABBIX_URL = os.environ.get("ZABBIX_URL")
ZABBIX_USER = os.environ.get("ZABBIX_USER")
ZABBIX_PASSWORD = os.environ.get("ZABBIX_PASSWORD")
HOST_IDS = os.environ.get("HOST_IDS")
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


def export_host(zapi, host_id, base_dir):
    """Export single host and its templates."""
    host_dir = os.path.join(base_dir, str(host_id))
    os.makedirs(host_dir, exist_ok=True)
    
    # Export host
    host_xml = zapi.configuration.export(options={'hosts': [host_id]}, format='xml')
    if not host_xml:
        return False
    
    # Save host XML
    host_file = os.path.join(host_dir, f"host_{host_id}.xml")
    with open(host_file, 'w', encoding='utf-8') as f:
        f.write(host_xml)
    
    # Export templates
    template_names = get_template_names(host_xml)
    if template_names:
        export_templates(zapi, template_names, host_dir)
    
    return True


def main():
    # Check required environment variables
    if not ZABBIX_USER or not ZABBIX_PASSWORD or not HOST_IDS:
        print("Error: ZABBIX_USER, ZABBIX_PASSWORD, and HOST_IDS must be set")
        return
    
    host_ids = [h.strip() for h in HOST_IDS.split(',') if h.strip()]
    if not host_ids:
        print("Error: No valid HOST_IDS provided")
        return
    
    # Connect to Zabbix
    try:
        zapi = ZabbixAPI(url=ZABBIX_URL)
        zapi.login(user=ZABBIX_USER, password=ZABBIX_PASSWORD)
        print(f"Connected to Zabbix. Processing {len(host_ids)} hosts...")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Export hosts
    successful = 0
    failed = 0
    
    for i, host_id in enumerate(host_ids, 1):
        try:
            if export_host(zapi, host_id, OUTPUT_DIR):
                successful += 1
            else:
                failed += 1
        except Exception:
            failed += 1
        
        # Progress indicator for large batches
        if i % 50 == 0 or i == len(host_ids):
            print(f"Progress: {i}/{len(host_ids)} ({successful} ok, {failed} failed)")
    
    print(f"Export complete: {successful} successful, {failed} failed")
    print(f"Results in: {OUTPUT_DIR}")
    
    # Logout
    try:
        zapi.logout()
    except:
        pass


if __name__ == "__main__":
    main()