#!/bin/bash
set -e

echo "Updating system and installing venv support..."
sudo apt-get update && sudo apt-get install -y python3-venv

echo "Creating virtual environment and installing dependencies..."
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete!"
echo "OpenCode is available via: opencode"
echo "MCP server can be started: ./venv/bin/python mcp_server.py"
