#!/bin/bash
# Script to setup virtual environment with Python 3.11

set -e

echo "=========================================="
echo "Setting up virtual environment (Python 3.11)"
echo "=========================================="

# Check if Python 3.11 is installed
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found!"
    echo "Please run: bash install_python311.sh"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "Current directory: $(pwd)"
echo "Python 3.11 version: $(python3.11 --version)"

# Remove old venv if exists
if [ -d "venv" ]; then
    echo "Removing old virtual environment..."
    rm -rf venv
fi

# Create new venv with Python 3.11
echo "Creating new virtual environment with Python 3.11..."
python3.11 -m venv venv

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Verify Python version in venv
echo "Python version in venv: $(python --version)"

# Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

# Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "✅ Virtual environment setup complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment:"
echo "  source venv/bin/activate"
echo ""
echo "To run the backend:"
echo "  uvicorn app.main:app --reload"
echo ""
