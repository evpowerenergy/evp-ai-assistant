#!/bin/bash
# Alternative script to install Python 3.11 without using PPA
# Use this if add-apt-repository fails

set -e

echo "=========================================="
echo "Installing Python 3.11 (Manual Method)"
echo "=========================================="

# Update package list
echo "Step 1: Updating package list..."
sudo apt update

# Fix apt_pkg issue
echo "Step 2: Fixing apt_pkg module issue..."
sudo apt install --reinstall -y python3-apt python3-distutils || {
    echo "Warning: Could not reinstall python3-apt"
}

# Install build dependencies
echo "Step 3: Installing build dependencies..."
sudo apt install -y build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev \
    libssl-dev libreadline-dev libffi-dev libsqlite3-dev wget libbz2-dev

# Download and compile Python 3.11 from source
echo "Step 4: Downloading Python 3.11 source..."
cd /tmp
PYTHON_VERSION="3.11.9"
wget https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tgz

echo "Step 5: Extracting Python source..."
tar -xzf Python-${PYTHON_VERSION}.tgz
cd Python-${PYTHON_VERSION}

echo "Step 6: Configuring Python build..."
./configure --enable-optimizations --prefix=/usr/local

echo "Step 7: Building Python (this may take a while)..."
make -j$(nproc)

echo "Step 8: Installing Python 3.11..."
sudo make altinstall

# Create symlink for python3.11-venv
echo "Step 9: Setting up python3.11-venv..."
sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3.11
sudo ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3.11

# Install ensurepip for venv support
echo "Step 10: Installing ensurepip..."
/usr/local/bin/python3.11 -m ensurepip --upgrade

# Verify installation
echo "Step 11: Verifying installation..."
python3.11 --version
pip3.11 --version

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
