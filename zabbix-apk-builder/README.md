# Zabbix APK Builder

Automated build system for creating Zabbix monitoring packages for Alpine Linux using Docker.

## What it does

This project builds separate Alpine Linux packages for:
- **zabbix-agent** - Monitoring agent for data collection
- **zabbix-proxy** - Network monitoring proxy daemon
- **zabbix** - Meta-package that installs both components

Each package includes proper OpenRC init scripts and user management for production deployment.

## Quick Start

```bash
# Build packages
./build.sh

# Install on Alpine Linux
apk add --allow-untrusted packages/zabbix-agent-*.apk
apk add --allow-untrusted packages/zabbix-proxy-*.apk

# Enable and start services
rc-update add zabbix-agent default
rc-service zabbix-agent start
```

## Configuration

### Change Zabbix Version
Edit `APKBUILD`:
```bash
pkgver=7.4.2  # Change to desired version
```

### Change Architecture
Edit `APKBUILD`:
```bash
arch="all"           # All architectures
arch="x86_64"        # 64-bit Intel/AMD only
arch="x86_64 aarch64"  # 64-bit Intel/AMD and ARM64
```

### Update Checksums
After changing the version:
```bash
# Manual approach
wget https://cdn.zabbix.com/zabbix/sources/stable/X.Y/zabbix-X.Y.Z.tar.gz
sha512sum zabbix-X.Y.Z.tar.gz  # Update sha512sums in APKBUILD
# Or let the build system handle it
./build.sh  # Will download and verify against official SHA256
```
sha512 is used per Alpine recommendation:
https://wiki.alpinelinux.org/wiki/APKBUILD_Reference
`New packages should use only sha512sums. Support for md5sums and sha1sums was dropped.`

## Build Process

1. **Docker Build**: Creates Alpine Linux build environment 
2. **Download Sources**: `abuild checksum` downloads tarball and generates SHA512
2. **Package Build**: Compiles and packages using Alpine's `abuild` system
3. **Output**: Generated APK files in `packages/` directory

## Requirements

- Docker
- Internet connection (for source download and verification)

## Files

- `APKBUILD` - Alpine package definition
- `build.sh` - Build automation script
- `Dockerfile` - Build environment container
- `zabbix-agent.*` - Agent service configuration files
- `zabbix-proxy.*` - Proxy service configuration files
