#!/bin/bash
# Script to install Python 3.11 on Ubuntu 22.04 (WSL)

set -e

echo "=========================================="
echo "Installing Python 3.11 on Ubuntu 22.04"
echo "=========================================="

# Update package list
echo "Step 1: Updating package list..."
sudo apt update

# Fix apt_pkg issue if exists
echo "Step 1.5: Fixing apt_pkg module issue..."
sudo apt install --reinstall -y python3-apt || {
    echo "Warning: Could not reinstall python3-apt, continuing..."
}

# Install prerequisites
echo "Step 2: Installing prerequisites..."
sudo apt install -y software-properties-common

# Add deadsnakes PPA (for Python 3.11)
echo "Step 3: Adding deadsnakes PPA..."
# Try using add-apt-repository, if fails use manual method
if ! sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null; then
    echo "add-apt-repository failed, using manual method..."
    echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/deadsnakes-ppa.list
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 || {
        echo "Warning: Could not add GPG key, trying alternative method..."
        sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 || true
    }
fi

# Update again after adding PPA
echo "Step 4: Updating package list again..."
sudo apt update

# Install Python 3.11 and venv
echo "Step 5: Installing Python 3.11 and python3.11-venv..."
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# Verify installation
echo "Step 6: Verifying installation..."
python3.11 --version

echo ""
echo "=========================================="
echo "✅ Python 3.11 installed successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. cd evp-ai-assistant/backend"
echo "2. rm -rf venv  # Remove old venv if exists"
echo "3. python3.11 -m venv venv"
echo "4. source venv/bin/activate"
echo "5. pip install --upgrade pip setuptools wheel"
echo "6. pip install -r requirements.txt"
echo ""
