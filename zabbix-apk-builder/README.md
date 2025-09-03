# Zabbix APK Builder

Automated Alpine Linux package builder for Zabbix Agent and Proxy with CI/CD pipeline integration.

## Features

- 🔄 **Automatic Version Detection**: Monitors Zabbix releases using official Bitbucket API
- 🏗️ **Docker-based Building**: Consistent, reproducible builds in isolated environment
- 🚀 **CI/CD Pipeline**: Full automation from version detection to package deployment
- 📦 **Multi-package Support**: Builds agent, proxy, and main packages
- 🧪 **Automated Testing**: Tests package installation in Alpine containers
- 📊 **Gitea Integration**: Publishes packages to your private Gitea repository

## Quick Start

### 1. Repository Setup

```bash
# Clone this repository
git clone <your-repo-url>
cd zabbix-apk-builder

# Make build script executable
chmod +x build.sh setup-cicd.sh
```

### 2. Manual Build

```bash
# Build packages locally
./build.sh

# Packages will be in ./packages/
ls -la packages/
```

### 3. CI/CD Setup

```bash
# Run the setup script
./setup-cicd.sh

# Follow the prompts to configure GitHub secrets
```

## Package Information

### Built Packages

1. **zabbix-agent** - Zabbix Agent only
2. **zabbix-proxy** - Zabbix Proxy (without LDAP)
3. **zabbix** - Main package with libraries

### Current Version

- **Zabbix Version**: 7.4.2
- **Alpine Base**: 3.18
- **Architecture**: x86_64

### Dependencies Removed

- LDAP support removed from proxy build
- Simplified configuration for smaller footprint

## CI/CD Pipeline

### Automatic Triggers

- **Daily**: Checks for new Zabbix versions at 6 AM UTC
- **Push**: Builds when code changes in main/test branches
- **Manual**: Force builds via GitHub Actions

### Version Detection

Uses Zabbix Bitbucket API:
```bash
https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags
```

### Pipeline Jobs

1. **check-version**: Detects new Zabbix releases
2. **update-version**: Updates APKBUILD automatically  
3. **build-packages**: Builds APK packages
4. **publish-to-gitea**: Deploys to your repository
5. **deploy-test**: Tests installation (test branch)

## Configuration

### GitHub Secrets Required

```bash
GITEA_SSH_KEY  # SSH private key for Gitea access
```

### File Structure

```
.
├── APKBUILD                 # Alpine package definition
├── build.sh                 # Build automation script
├── Dockerfile              # Build environment
├── .github/workflows/       # CI/CD pipeline
├── packages/               # Built packages
├── zabbix-agent.initd      # Agent init script
├── zabbix-agent.confd      # Agent config
├── zabbix-proxy.initd      # Proxy init script
└── zabbix-proxy.confd      # Proxy config
```

## Usage

### Install Packages

```bash
# Add repository
echo "http://gitea-repo/mbuz/Zabbix/raw/branch/main/alpine/v3.18/main" >> /etc/apk/repositories

# Update and install
apk update
apk add zabbix-agent

# Enable and start
rc-update add zabbix-agent default
rc-service zabbix-agent start
```

### Configuration

```bash
# Configure agent
vim /etc/zabbix/zabbix_agentd.conf

# Set server IP
Server=your.zabbix.server

# Restart service
rc-service zabbix-agent restart
```

## Development

### Local Testing

```bash
# Test build locally
./build.sh

# Test in Docker
docker run --rm -it \
  -v $(pwd)/packages:/packages \
  alpine:3.18 sh -c "
    apk add --allow-untrusted /packages/zabbix-agent-*.apk
    zabbix_agentd --version
  "
```

### Branch Strategy

- **main**: Production releases, auto-deployed
- **test**: Testing and validation, no auto-deploy

### Making Changes

1. Create feature branch from `test`
2. Test changes thoroughly
3. Merge to `test` for CI validation
4. Merge to `main` for production release

## Troubleshooting

### Build Issues

```bash
# Check build logs
docker logs $(docker ps -l -q)

# Manual build debug
docker run -it --rm -v $(pwd):/build alpine:3.18 sh
cd /build && ./build.sh
```

### Version Detection

```bash
# Test API manually
curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
  jq -r '.values[].displayId' | \
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
  sort -V | tail -1
```

### CI/CD Issues

1. Check GitHub Actions logs
2. Verify SSH key permissions
3. Test Gitea connectivity
4. Validate APKBUILD syntax

## Documentation

- **[CI-CD-DOCS.md](CI-CD-DOCS.md)**: Comprehensive CI/CD documentation
- **[setup-cicd.sh](setup-cicd.sh)**: Setup script for CI/CD configuration

## Security

- Uses SSH keys for Gitea access
- Minimal package dependencies
- Regular security updates via automated builds
- No secrets stored in repository

## Contributing

1. Fork the repository
2. Create feature branch
3. Test changes in `test` branch
4. Submit pull request to `main`

## License

This project follows the same license as Zabbix (GPL v2).

## Support

For issues:
1. Check troubleshooting section
2. Review CI/CD logs
3. Test manual build process
4. Check Zabbix API connectivity

---

**Built with ❤️ for Alpine Linux and Zabbix monitoring**
