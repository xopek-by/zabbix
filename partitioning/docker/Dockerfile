FROM python:3.12-slim

# Install dependencies
RUN pip install --no-cache-dir pymysql pyyaml

# Copy main script and entrypoint
# Note: Build context should be the parent directory 'partitioning/'
COPY script/zabbix_partitioning.py /usr/local/bin/
RUN mkdir -p /etc/zabbix
COPY docker/entrypoint.py /usr/local/bin/entrypoint.py

# Set permissions
RUN chmod +x /usr/local/bin/zabbix_partitioning.py /usr/local/bin/entrypoint.py

# Entrypoint
ENTRYPOINT ["python3", "/usr/local/bin/entrypoint.py"]
