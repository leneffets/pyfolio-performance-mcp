#!/bin/bash
set -e

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete!"
echo "OpenCode is available via: opencode"
echo "MCP server can be started: python mcp_server.py"
