#!/usr/bin/env bash
# Install script for weather-tools
# Sets up virtual environment, installs dependencies, and optionally creates shortcuts

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$SCRIPT_DIR/config.yaml"
CONFIG_EXAMPLE="$SCRIPT_DIR/config.example.yaml"
PLIST_FILE="$SCRIPT_DIR/net.bewilson.weather-collect.plist"
PLIST_EXAMPLE="$SCRIPT_DIR/net.bewilson.weather-collect.example.plist"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS/net.bewilson.weather-collect.plist"

echo "Weather Tools - Installation"
echo "============================"
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
        echo "  -> Edit this file with your location, email settings, and alert rules."
    fi
fi

# Shortcut in ~/bin
echo ""
read -p "Create shortcuts in ~/bin? (y/N): " create_shortcut
if [[ "$create_shortcut" =~ ^[Yy]$ ]]; then
    BIN_DIR="$HOME/bin"

    # Create ~/bin if it doesn't exist
    if [ ! -d "$BIN_DIR" ]; then
        echo "Creating $BIN_DIR..."
        mkdir -p "$BIN_DIR"
        echo "  -> You may need to add ~/bin to your PATH."
    fi

    for script in check-weather-alerts check-weather-collect; do
        SHORTCUT="$BIN_DIR/$script"
        if [ -L "$SHORTCUT" ] || [ -e "$SHORTCUT" ]; then
            read -p "  $SHORTCUT already exists. Overwrite? (y/N): " overwrite
            if [[ "$overwrite" =~ ^[Yy]$ ]]; then
                rm -f "$SHORTCUT"
                ln -s "$SCRIPT_DIR/$script" "$SHORTCUT"
                echo "  Shortcut updated: $SHORTCUT"
            fi
        else
            ln -s "$SCRIPT_DIR/$script" "$SHORTCUT"
            echo "  Shortcut created: $SHORTCUT"
        fi
    done
fi

# launchd plist setup
echo ""
read -p "Install launchd plist for daily weather collection? (y/N): " install_plist
if [[ "$install_plist" =~ ^[Yy]$ ]]; then
    if [ ! -f "$PLIST_FILE" ]; then
        if [ -f "$PLIST_EXAMPLE" ]; then
            echo "Creating plist from template..."
            sed "s|/path/to/weather-tools|$SCRIPT_DIR|g; s|/path/to/logs|$HOME/Library/CloudStorage/Dropbox/BEWMain/Data/logs|g" \
                "$PLIST_EXAMPLE" > "$PLIST_FILE"
            echo "  Created $PLIST_FILE"
            echo "  -> Review and edit if the log path needs adjustment."
        else
            echo "Error: No plist template found at $PLIST_EXAMPLE"
        fi
    fi

    if [ -f "$PLIST_FILE" ]; then
        mkdir -p "$LAUNCH_AGENTS"

        # Unload existing if present
        if [ -f "$PLIST_DEST" ]; then
            echo "  Unloading existing plist..."
            launchctl unload "$PLIST_DEST" 2>/dev/null || true
        fi

        cp "$PLIST_FILE" "$PLIST_DEST"
        launchctl load "$PLIST_DEST"
        echo "  Plist installed and loaded: $PLIST_DEST"
        echo "  Weather collection will run daily at 5:00 AM."
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
    echo "  4. Run: ./check-weather-collect --dry-run"
else
    echo "  1. Edit config.yaml with your settings (if not already done)"
    echo "  2. Run: ./check-weather-alerts --dry-run"
    echo "  3. Run: ./check-weather-collect --dry-run"
fi
