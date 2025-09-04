FROM alpine:latest

# Install build dependencies
RUN apk add --no-cache \
    abuild \
    alpine-sdk \
    autoconf \
    automake \
    libtool \
    linux-headers \
    pkgconfig \
    sudo \
    curl-dev \
    libevent-dev \
    libxml2-dev \
    net-snmp-dev \
    openssl-dev \
    pcre2-dev \
    sqlite-dev \
    unixodbc-dev \
    zlib-dev \
    openldap-dev \
    libssh2-dev \
    && adduser -D -G abuild builder \
    && echo "builder ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Setup build environment
USER builder
WORKDIR /home/builder

# Generate signing keys
RUN abuild-keygen -a -i -n

# Copy package files
COPY --chown=builder:builder . /home/builder/zabbix/

WORKDIR /home/builder/zabbix

# Create build script
USER root
RUN cat > /usr/local/bin/build-and-copy.sh << 'EOF'
#!/bin/sh
set -e

echo "Building packages as builder user..."
sudo -u builder sh -c "
    cd /home/builder/zabbix
    abuild checksum
    abuild -r
"

echo "Copying packages to output..."
find /home/builder/packages -name '*.apk' -exec cp {} /output/ \;

# Make files readable and writable by everyone (fixes permission issues)
chmod 666 /output/*.apk 2>/dev/null || true

# Also try changing ownership to a generic user ID that should work
# Use UID 1000 which is common for CI runners
chown 1000:1000 /output/*.apk 2>/dev/null || true

echo "Build complete! Packages:"
ls -la /output/
EOF

RUN chmod +x /usr/local/bin/build-and-copy.sh

# Set build command
CMD ["/usr/local/bin/build-and-copy.sh"]