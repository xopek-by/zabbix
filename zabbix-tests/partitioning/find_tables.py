import re

def get_partitionable_tables(schema_path):
    with open(schema_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Split into CREATE TABLE statements
    tables = content.split('CREATE TABLE')
    valid_tables = []

    for table_def in tables:
        # Extract table name
        name_match = re.search(r'`(\w+)`', table_def)
        if not name_match:
            continue
        table_name = name_match.group(1)

        # Check for PRIMARY KEY definition
        pk_match = re.search(r'PRIMARY KEY \((.*?)\)', table_def, re.DOTALL)
        if pk_match:
            pk_cols = pk_match.group(1)
            if 'clock' in pk_cols:
                valid_tables.append(table_name)
    
    return valid_tables

if __name__ == '__main__':
    tables = get_partitionable_tables('/opt/git/Zabbix/partitioning/70-schema-mysql.txt')
    print("Partitionable tables (PK contains 'clock'):")
    for t in tables:
        print(f" - {t}")
