# Zabbix APK Builder

Automated Alpine Linux package builder for Zabbix Agent and Proxy with CI/CD pipeline integration.

## Features

- 🔄 **Automatic Version Detection**: Monitors Zabbix releases using Bitbucket API
- 🚀 **CI/CD Pipeline**: Full automation from version detection to package deployment
- 📦 **Multi-package Support**: Builds agent and proxy packages
- 🧪 **Automated Testing**: Tests package installation in Alpine containers
- 📊 **Gitea Integration**: Publishes packages to Gitea repository

## Quick Start

### Prerequisites

- Docker installed
- Gitea repository with Actions enabled

### Manual Build

```bash
# Clone the repository
git clone <your-gitea-repo>
cd zabbix-apk-builder

# Build packages locally
chmod +x build.sh
./build.sh

# Check built packages
ls -la packages/builder/x86_64/
```

## Package Information

### Built Packages

1. **zabbix-agent** - Zabbix Agent only
2. **zabbix-proxy** - Zabbix Proxy
3. **zabbix** - Meta package

## CI/CD Pipeline

### Automatic Triggers

- **Daily**: Checks for new Zabbix versions at 6 AM UTC
- **Push**: Builds when code changes in main/test branches

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
zabbix-git/
└── zabbix-apk-builder/
    ├── .gitea/
    │   └── workflows/
    │       └── build.yaml         # Main CI/CD pipeline
    ├── APKBUILD                   # Alpine package definition
    ├── Dockerfile                 # Build environment container
    ├── README.md                  # This file
    ├── build.sh                   # Local build script
    ├── packages/                  # Generated packages (gitignored)
    ├── zabbix-agent.confd         # Agent configuration
    ├── zabbix-agent.initd         # Agent init script
    ├── zabbix-agent.pre-install   # Agent pre-install script
    ├── zabbix-proxy.confd         # Proxy configuration  
    ├── zabbix-proxy.initd         # Proxy init script
    └── zabbix-proxy.pre-install   # Proxy pre-install script
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

- **main**: Production releases, merge only
- **test**: Testing and validation

### Making Changes

1. Create feature branch from `main`
2. Test changes thoroughly
3. Validate CI
4. Merge to `main`


### Version Detection

```bash
# Test API manually
curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
  jq -r '.values[].displayId' | \
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+
 | \
  sort -V | tail -1
```

## License

This project follows the same license as Zabbix (AGPLv3).

---
