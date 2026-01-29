#!/usr/bin/env bash
# Install script for weather-alerts
# Sets up virtual environment, installs dependencies, and optionally creates shortcuts

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$SCRIPT_DIR/config.yaml"
CONFIG_EXAMPLE="$SCRIPT_DIR/config.example.yaml"

echo "Weather Alerts - Installation"
echo "=============================="
echo ""

# Check for Python 3
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is required but not found."
    exit 1
fi

# Verify Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Found Python $PYTHON_VERSION"

# Create virtual environment
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    read -p "Recreate it? (y/N): " recreate_venv
    if [[ "$recreate_venv" =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
        echo "Creating new virtual environment..."
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
else
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Install dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "Dependencies installed."

# Configuration file setup
echo ""
if [ -f "$CONFIG_FILE" ]; then
    echo "Configuration file already exists at $CONFIG_FILE"
else
    echo "No configuration file found."
    read -p "Create config.yaml from template? (Y/n): " create_config
    if [[ ! "$create_config" =~ ^[Nn]$ ]]; then
        cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
        echo "Created $CONFIG_FILE"
        echo "  -> Edit this file with your API keys, email settings, and alert rules."
    fi
fi

# Shortcut in ~/bin
echo ""
read -p "Create shortcut in ~/bin? (y/N): " create_shortcut
if [[ "$create_shortcut" =~ ^[Yy]$ ]]; then
    BIN_DIR="$HOME/bin"
    SHORTCUT="$BIN_DIR/check-weather-alerts"

    # Create ~/bin if it doesn't exist
    if [ ! -d "$BIN_DIR" ]; then
        echo "Creating $BIN_DIR..."
        mkdir -p "$BIN_DIR"
        echo "  -> You may need to add ~/bin to your PATH."
    fi

    # Create or update symlink
    if [ -L "$SHORTCUT" ] || [ -e "$SHORTCUT" ]; then
        read -p "  $SHORTCUT already exists. Overwrite? (y/N): " overwrite
        if [[ "$overwrite" =~ ^[Yy]$ ]]; then
            rm -f "$SHORTCUT"
            ln -s "$SCRIPT_DIR/check-weather-alerts" "$SHORTCUT"
            echo "  Shortcut updated."
        fi
    else
        ln -s "$SCRIPT_DIR/check-weather-alerts" "$SHORTCUT"
        echo "  Shortcut created: $SHORTCUT"
    fi
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "  1. Copy config.example.yaml to config.yaml"
    echo "  2. Edit config.yaml with your settings"
    echo "  3. Run: ./check-weather-alerts --dry-run"
else
    echo "  1. Edit config.yaml with your settings (if not already done)"
    echo "  2. Run: ./check-weather-alerts --dry-run"
fi
