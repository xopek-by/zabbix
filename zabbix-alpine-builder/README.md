# Zabbix 7.4 APK Builder for Alpine Linux

## Overview

This project provides an automated solution for building Zabbix Agent and Proxy packages (.apk files) for Alpine Linux. The system automatically monitors the official Zabbix repository for new 7.4.x releases and builds updated packages when new versions are detected.

The project creates two separate packages from a single APKBUILD:
- **zabbix-agent**: Lightweight monitoring agent for data collection
- **zabbix-proxy**: Monitoring proxy with SQLite 3 support for distributed monitoring

## File Structure

```
/home/mbuz/zabbix-git/zabbix-alpine-builder/
├── .gitea/
│   └── workflows/
│       └── build.yml          # Gitea Actions CI/CD workflow
├── zabbix/
│   └── APKBUILD              # Alpine package build specification
├── build.sh                  # Local build script for testing
├── test-version-check.sh     # Version check validation script
└── README.md                 # This documentation file
```

## Prerequisites

For local building, you need the following Alpine Linux packages:

```bash
sudo apk add alpine-sdk git
```

The `alpine-sdk` package includes:
- `abuild` - Alpine package builder
- `build-base` - Essential build tools
- Development headers and libraries

## Manual Build

To build the packages locally for testing:

1. **Clone or navigate to the project directory:**
   ```bash
   cd /home/mbuz/zabbix-git/zabbix-alpine-builder
   ```

2. **Run the build script:**
   ```bash
   ./build.sh
   ```

3. **The script will:**
   - Check for required dependencies
   - Set up the abuild environment (create signing keys if needed)
   - Navigate to the `zabbix/` directory
   - Download Zabbix source code
   - Update checksums automatically
   - Build both agent and proxy packages
   - Create a local package repository

4. **Generated packages will be available in:**
   ```
   ~/packages/zabbix-agent-7.4.x-r0.apk
   ~/packages/zabbix-proxy-7.4.x-r0.apk
   ```

## Testing Version Check

To validate the version checking logic without running a full build:

```bash
./test-version-check.sh
```

This script tests the same version detection logic used by the CI/CD workflow and reports whether a build would be triggered.

## CI/CD Automation

The project includes automated package building through Gitea Actions:

### Workflow Configuration

The workflow file `.gitea/workflows/build.yml` provides:

- **Scheduled Execution**: Runs daily at 2:00 AM UTC to check for new versions
- **Manual Triggering**: Can be triggered manually via the Gitea Actions interface
- **Alpine Container**: Builds packages in a clean Alpine Linux environment

### Automated Process

1. **Version Detection**: 
   - Uses the Zabbix Bitbucket REST API for accurate version detection
   - Filters out release candidates, beta, and alpha versions
   - Only considers stable releases matching the pattern `X.Y.Z`
   - Compares with the current version in `APKBUILD`

2. **Build Trigger**:
   - Only proceeds if a newer version is detected
   - Gracefully stops if no update is needed

3. **Package Building**:
   - Updates `pkgver` in the `APKBUILD` file
   - Fetches source code using `abuild fetch`
   - Recalculates source checksums using `abuild checksum`
   - Builds both agent and proxy packages
   - Validates the build process

4. **Version Control**:
   - Commits the updated `APKBUILD` with new version information
   - Pushes changes to the `test` branch
   - Includes detailed commit messages with version changes

5. **Artifact Management**:
   - Archives generated `.apk` files as build artifacts
   - Provides downloadable packages for 30 days
   - Generates build summary reports

### Build Artifacts

Successful builds produce:
- `zabbix-agent-{version}-r0.apk` - Monitoring agent package
- `zabbix-proxy-{version}-r0.apk` - Monitoring proxy package with SQLite support

## Package Details

### Zabbix Agent Package
- **Binary**: `/usr/sbin/zabbix_agentd`
- **Configuration**: `/etc/zabbix/zabbix_agentd.conf`
- **Runtime Dependencies**: pcre2, libevent, openssl, net-snmp, curl
- **Log Directory**: `/var/log/zabbix/agent`
- **Data Directory**: `/var/lib/zabbix/agent`

### Zabbix Proxy Package
- **Binary**: `/usr/sbin/zabbix_proxy`
- **Configuration**: `/etc/zabbix/zabbix_proxy.conf`
- **Runtime Dependencies**: pcre2, libevent, openssl, net-snmp, curl, sqlite, libxml2
- **Database Support**: SQLite 3
- **Log Directory**: `/var/log/zabbix/proxy`
- **Data Directory**: `/var/lib/zabbix/proxy`

## Security Considerations

- Packages run under a dedicated `zabbix` user account
- Configuration files have restricted permissions (640)
- Service directories are owned by the zabbix user
- Signing keys are automatically generated for package integrity

## Troubleshooting

### Local Build Issues

1. **Missing dependencies**: Ensure `alpine-sdk` and `git` are installed
2. **Permission errors**: Don't run the build script as root
3. **Signing key errors**: The script will automatically generate keys on first run
4. **Network issues**: Ensure internet access for downloading Zabbix sources

### CI/CD Issues

1. **Build failures**: Check the workflow logs in Gitea Actions
2. **Version detection**: Verify access to the upstream Zabbix repository
3. **Push failures**: Ensure proper repository permissions for the bot account

## Contributing

To contribute to this project:

1. Test local builds before submitting changes
2. Update version numbers appropriately
3. Maintain compatibility with Alpine Linux packaging standards
4. Document any significant changes in commit messages

## License

This project follows the same licensing as Zabbix (AGPL-3.0-only for versions 7.0+) for package building scripts. The generated packages contain Zabbix software under its original license terms.
