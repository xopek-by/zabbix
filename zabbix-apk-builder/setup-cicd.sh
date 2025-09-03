#!/bin/bash

# Zabbix APK Builder CI/CD Setup Script
set -e

echo "🚀 Zabbix APK Builder CI/CD Setup"
echo "=================================="
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in a git repository
print_step "Checking Git repository status..."
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    print_error "Not in a Git repository. Please initialize git first:"
    echo "  git init"
    echo "  git add ."
    echo "  git commit -m 'Initial commit'"
    echo "  git remote add origin <your-github-repo>"
    exit 1
fi

# Check if we have required files
print_step "Verifying required files..."
required_files=("APKBUILD" "build.sh" "Dockerfile" ".github/workflows/build.yml")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_error "Required file missing: $file"
        exit 1
    fi
done
print_success "All required files present"

# Test version detection API
print_step "Testing Zabbix version detection API..."
if ! curl -s --connect-timeout 10 "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=5" | grep -q "displayId"; then
    print_warning "Could not reach Zabbix API. Pipeline will work but version detection may fail."
else
    latest_version=$(curl -s "https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=100" | \
        grep -o '"displayId":"[^"]*"' | cut -d'"' -f4 | \
        grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
    print_success "API working. Latest Zabbix version: $latest_version"
fi

# Check if GitHub CLI is available
print_step "Checking GitHub CLI availability..."
if command -v gh &> /dev/null; then
    if gh auth status &> /dev/null; then
        print_success "GitHub CLI authenticated"
        GITHUB_CLI_AVAILABLE=true
    else
        print_warning "GitHub CLI not authenticated. Manual secret configuration needed."
        GITHUB_CLI_AVAILABLE=false
    fi
else
    print_warning "GitHub CLI not installed. Manual secret configuration needed."
    GITHUB_CLI_AVAILABLE=false
fi

# SSH Key Setup
print_step "Setting up SSH key for Gitea access..."
echo
echo "You need an SSH key for the CI/CD pipeline to push packages to your Gitea repository."
echo

# Check if user has SSH keys
if [[ -f ~/.ssh/id_rsa ]] || [[ -f ~/.ssh/id_ed25519 ]]; then
    echo "Existing SSH keys found:"
    ls -la ~/.ssh/id_* 2>/dev/null | grep -v .pub || true
    echo
    read -p "Use existing SSH key? (y/N): " use_existing
    
    if [[ $use_existing =~ ^[Yy]$ ]]; then
        if [[ -f ~/.ssh/id_ed25519 ]]; then
            SSH_KEY_PATH=~/.ssh/id_ed25519
        elif [[ -f ~/.ssh/id_rsa ]]; then
            SSH_KEY_PATH=~/.ssh/id_rsa
        fi
        print_success "Using existing SSH key: $SSH_KEY_PATH"
    else
        create_new_key=true
    fi
else
    create_new_key=true
fi

if [[ $create_new_key == true ]]; then
    print_step "Creating new SSH key for CI/CD..."
    ssh-keygen -t ed25519 -f ~/.ssh/zabbix_cicd -N "" -C "zabbix-cicd@$(hostname)"
    SSH_KEY_PATH=~/.ssh/zabbix_cicd
    print_success "Created new SSH key: $SSH_KEY_PATH"
fi

# Display public key
echo
echo "📋 Public key to add to your Gitea repository:"
echo "=============================================="
cat "$SSH_KEY_PATH.pub"
echo "=============================================="
echo

print_warning "IMPORTANT: Add this public key to your Gitea repository with write access!"
echo "1. Go to your Gitea repository settings"
echo "2. Navigate to Deploy Keys section"
echo "3. Add the public key above"
echo "4. Enable write access for the key"
echo

read -p "Press Enter after adding the public key to Gitea..."

# Configure GitHub Secrets
print_step "Configuring GitHub repository secrets..."
echo

if [[ $GITHUB_CLI_AVAILABLE == true ]]; then
    echo "Setting up GitHub secrets using GitHub CLI..."
    
    # Set SSH key secret
    if gh secret set GITEA_SSH_KEY < "$SSH_KEY_PATH"; then
        print_success "SSH key secret configured"
    else
        print_error "Failed to set SSH key secret"
        exit 1
    fi
    
else
    echo "Manual secret configuration required:"
    echo
    echo "1. Go to your GitHub repository"
    echo "2. Navigate to Settings → Secrets and variables → Actions"
    echo "3. Add the following secret:"
    echo
    echo "   Name: GITEA_SSH_KEY"
    echo "   Value: (paste the private key below)"
    echo
    echo "📋 Private key content:"
    echo "======================"
    cat "$SSH_KEY_PATH"
    echo "======================"
    echo
    read -p "Press Enter after configuring the GitHub secret..."
fi

# Test build locally
print_step "Testing local build..."
if [[ -x ./build.sh ]]; then
    echo "Running test build (this may take a few minutes)..."
    if ./build.sh; then
        print_success "Local build test successful"
        if [[ -d packages ]] && [[ $(ls packages/*.apk 2>/dev/null | wc -l) -gt 0 ]]; then
            echo "Built packages:"
            ls -la packages/*.apk
        fi
    else
        print_warning "Local build test failed, but CI/CD setup continues"
    fi
else
    print_error "build.sh is not executable"
    chmod +x build.sh
    print_success "Fixed build.sh permissions"
fi

# Repository setup verification
print_step "Verifying repository configuration..."

# Check remote URL
remote_url=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$remote_url" ]]; then
    print_error "No Git remote 'origin' configured"
    echo "Please add your GitHub repository as remote:"
    echo "  git remote add origin https://github.com/username/repo.git"
    exit 1
else
    print_success "Git remote configured: $remote_url"
fi

# Check if we're on main or test branch
current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" ]] && [[ "$current_branch" != "test" ]]; then
    print_warning "Not on main or test branch (current: $current_branch)"
    echo "CI/CD pipeline triggers on main/test branches"
fi

# Final steps
echo
print_step "Final setup steps..."
echo
echo "✅ CI/CD Setup Complete!"
echo
echo "📋 Next Steps:"
echo "1. Commit and push your changes:"
echo "   git add ."
echo "   git commit -m 'Add CI/CD pipeline'"
echo "   git push origin main"
echo
echo "2. Check GitHub Actions tab in your repository"
echo "3. The pipeline will:"
echo "   - Check for new Zabbix versions daily"
echo "   - Build packages automatically"
echo "   - Publish to your Gitea repository"
echo
echo "📖 Documentation:"
echo "- CI-CD-DOCS.md: Comprehensive pipeline documentation"
echo "- README.md: Usage and setup guide"
echo
echo "🔧 Manual Operations:"
echo "- Force build: Go to Actions tab → Zabbix APK Builder → Run workflow"
echo "- Test build: ./build.sh"
echo "- Check version: curl -s 'https://git.zabbix.com/rest/api/1.0/projects/ZBX/repos/zabbix/tags?limit=5'"
echo
print_success "Setup completed successfully! 🎉"
