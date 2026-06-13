#!/bin/bash

# PiPulse Installer Script
# Designed for Raspberry Pi OS

set -e

echo "🚀 Initializing PiPulse Setup..."

# Navigate to project directory
cd "$(dirname "$0")"

# Update system packages
echo "📦 Updating system dependencies..."
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip

# Create Virtual Environment
echo "🐍 Creating virtual environment..."
python3 -m venv venv

# Install Python dependencies
echo "📥 Installing Python requirements..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Setup Environment File
if [ ! -f .env ]; then
    echo "📄 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Action Required: Edit pipulse/.env with your API keys!"
fi

# Setup Systemd Service
echo "⚙️ Configuring system service..."
sudo cp pipulse.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pipulse.service
sudo systemctl restart pipulse.service

echo "✅ PiPulse is now ONLINE!"
echo "📍 Access your dashboard at: http://$(hostname -I | awk '{print $1}'):8000"
echo "🛠️ To check logs, run: journalctl -u pipulse.service -f"
