# CI/CD Pipeline Documentation

## Overview

This CI/CD pipeline automates the entire Zabbix APK package lifecycle from version detection to deployment. It's designed to work with your Gitea repository and provides both automated and manual build capabilities.

## Pipeline Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Version Check   │ -> │ Update APKBUILD  │ -> │ Build Packages  │
│ (Zabbix Git)    │    │ (Auto-commit)    │    │ (Docker)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Deploy Test     │ <- │ Publish to Gitea │ <- │ Create Release  │
│ (Alpine Test)   │    │ (Package Repo)   │    │ (GitHub)        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Version Detection Strategy

### Primary Method: Zabbix Bitbucket API
- **Endpoint**: `https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags`
- **Process**: 
  1. Fetches all tags from Zabbix official repository
  2. Filters for stable releases (excludes rc, beta, alpha)
  3. Sorts versions and selects the latest
- **Advantages**: 
  - Official Zabbix repository
  - Real-time release information
  - Includes all release types for filtering

### Fallback Options
If the Bitbucket API fails:
1. **CDN Scraping**: Parse `https://cdn.zabbix.com/zabbix/sources/stable/`
2. **RSS Feed**: Monitor Zabbix blog/announcements
3. **Manual Trigger**: Force build via GitHub Actions

## Jobs Breakdown

### 1. **check-version**
- **Purpose**: Monitors Zabbix releases for new versions
- **Method**: Queries Zabbix Bitbucket API for latest stable release
- **Logic**: 
  ```bash
  # Filters tags to stable releases only
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | 
  grep -v 'rc\|beta\|alpha' | 
  sort -V | tail -1
  ```
- **Output**: Determines if build is needed and provides version info

### 2. **update-version** 
- **Purpose**: Automatically updates APKBUILD when new version found
- **Actions**:
  - Updates `pkgver` to latest version
  - Resets `pkgrel` to 0
  - Clears checksums (regenerated during build)
  - Commits and pushes changes

### 3. **build-packages**
- **Purpose**: Builds APK packages using Docker
- **Process**:
  - Sets up Docker Buildx
  - Runs `./build.sh` 
  - Uploads packages as artifacts
  - Creates GitHub release (main branch only)

### 4. **publish-to-gitea**
- **Purpose**: Publishes packages to your Gitea repository
- **Process**:
  - Downloads built packages
  - Clones Gitea repo using SSH
  - Organizes packages in Alpine repository structure
  - Updates package index
  - Commits and pushes to Gitea

### 5. **deploy-test**
- **Purpose**: Tests package installation (test branch only)
- **Process**:
  - Downloads packages
  - Tests installation in fresh Alpine containers
  - Verifies binaries work correctly

## Trigger Conditions

### Automatic Triggers
- **Daily Check**: Runs at 6 AM UTC to check for new Zabbix versions
- **Code Changes**: Triggers on pushes to main/test branches when relevant files change

### Manual Triggers
- **Workflow Dispatch**: Manual trigger with optional force build
- **Use Case**: Emergency builds or testing

## Configuration Requirements

### GitHub Secrets
You need to configure these secrets in your GitHub repository:

```bash
# For Gitea repository access
GITEA_SSH_KEY  # Private SSH key for gitea-repo access
```

### Repository Setup
1. **Branch Strategy**:
   - `main`: Production releases
   - `test`: Testing and validation

2. **File Structure**:
   ```
   .github/workflows/build.yml  # Main pipeline
   APKBUILD                     # Package definition
   build.sh                     # Build script
   Dockerfile                   # Build environment
   *.initd, *.confd            # Service files
   ```

## API Endpoints Used

### Zabbix Version Detection
```bash
# Primary endpoint - Zabbix Bitbucket API
https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100

# Response format:
{
  "values": [
    {
      "displayId": "7.4.2",
      "type": "TAG"
    }
  ]
}
```

### Version Processing
```bash
# Extract stable versions only
curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
  jq -r '.values[].displayId' | \
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
  grep -v 'rc\|beta\|alpha' | \
  sort -V | \
  tail -1
```

## Package Repository Structure

Your Gitea repository will follow Alpine Linux repository format:
```
alpine/
  v3.18/
    main/
      x86_64/
        zabbix-agent-X.Y.Z-r0.apk
        zabbix-proxy-X.Y.Z-r0.apk
        zabbix-X.Y.Z-r0.apk
        PACKAGES.txt
```

## Deployment Flow

### Development Workflow
1. **Code Changes** → Push to `test` branch
2. **Pipeline Runs** → Builds and tests packages
3. **Testing** → Verify in Alpine containers
4. **Merge** → To `main` branch for release

### Production Workflow  
1. **New Zabbix Release** → Detected by daily check
2. **Auto-Update** → APKBUILD updated and committed
3. **Build** → Packages built and tested
4. **Release** → GitHub release created
5. **Publish** → Packages pushed to Gitea repository

## Monitoring and Notifications

### Success Indicators
- ✅ Version check completes
- ✅ APKBUILD updated correctly
- ✅ Packages build successfully
- ✅ Tests pass in Alpine containers
- ✅ Packages published to Gitea

### Failure Handling
- 🚨 Build failures create GitHub issues
- 🚨 Failed deployments stop the pipeline
- 🚨 Version detection errors logged

## Usage Examples

### Manual Build
```bash
# Trigger manual build via GitHub Actions UI
# OR via GitHub CLI:
gh workflow run build.yml -f force_build=true
```

### Emergency Version Update
```bash
# Update version manually and push
sed -i 's/pkgver=.*/pkgver=7.4.3/' APKBUILD
git add APKBUILD
git commit -m "Emergency update to 7.4.3"
git push
```

### Using Built Packages
```bash
# Add your Gitea repository
echo "http://gitea-repo/mbuz/Zabbix/raw/branch/main/alpine/v3.18/main" >> /etc/apk/repositories

# Install packages
apk update
apk add zabbix-agent zabbix-proxy
```

## Testing the Version Detection

You can test the version detection logic locally:

```bash
# Get latest stable version
curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
  jq -r '.values[].displayId' | \
  grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | \
  grep -v 'rc\|beta\|alpha' | \
  sort -V | \
  tail -1

# Should output: 7.4.2 (or latest version)
```

## Maintenance

### Regular Tasks
- Monitor pipeline runs
- Update Alpine Linux version in repository structure
- Rotate SSH keys periodically
- Review and update dependencies

### Troubleshooting
- Check GitHub Actions logs for failures
- Verify SSH key access to Gitea
- Ensure Docker builds work locally
- Test package installation manually
- Verify Zabbix API connectivity

## Security Considerations

1. **SSH Keys**: Use dedicated deploy keys with minimal permissions
2. **Secrets**: Store sensitive data in GitHub Secrets
3. **API Access**: Monitor for API rate limits or authentication changes
4. **Package Signing**: Consider implementing APK package signing

This pipeline provides a fully automated solution for maintaining up-to-date Zabbix packages while ensuring quality through testing and proper repository management.
