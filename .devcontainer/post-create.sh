#!/bin/bash
set -e

echo "Updating system and installing venv support..."
sudo apt-get update && sudo apt-get install -y python3-venv

echo "Creating devcontainer virtual environment and installing dependencies..."
rm -rf .venv-devcontainer
python3 -m venv .venv-devcontainer
source .venv-devcontainer/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if ! grep -q "pyfolio-performance-mcp devcontainer venv" ~/.bashrc; then
  cat <<'EOF' >> ~/.bashrc

# pyfolio-performance-mcp devcontainer venv
if [ -d /workspaces/pyfolio-performance-mcp/.venv-devcontainer ] && [ -z "$VIRTUAL_ENV" ]; then
  source /workspaces/pyfolio-performance-mcp/.venv-devcontainer/bin/activate
fi
EOF
fi

echo "Setup complete!"
echo "OpenCode is available via: opencode"
echo "New devcontainer terminals auto-activate .venv-devcontainer"
echo "MCP server can be started: python mcp_server.py"
