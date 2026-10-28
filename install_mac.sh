#!/bin/bash
# =============================================================================
#  VDI Host Sizer - Mac installer and updater
#
#  Open Terminal, paste this line and press Return:
#    curl -fsSL https://raw.githubusercontent.com/adammarcum/VDI-Host-Sizer/main/install_mac.sh | bash
#
#  Downloads the latest version from GitHub into ~/HostSizer/vdi-app and starts it.
#  Run the same line again any time to update; your Python environment and
#  saved projects (~/HostSizer/VDIProjects) are kept.
#  Files downloaded this way are not quarantined, so macOS doesn't block the
#  launcher or ask the user to approve anything.
# =============================================================================
set -euo pipefail

REPO="${VDI_HOSTSIZER_REPO:-adammarcum/VDI-Host-Sizer}"
DEST="${HOSTSIZER_HOME:-$HOME/HostSizer}/vdi-app"
ZIP_URL="${VDI_HOSTSIZER_ZIP_URL:-https://github.com/${REPO}/archive/refs/heads/main.zip}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==========================================="
echo "   VDI Host Sizer  -  installer / updater"
echo "==========================================="
echo "Downloading the latest version..."
if ! curl -fsSL "$ZIP_URL" -o "$TMP/vdi.zip"; then
    echo ""
    echo "Download failed. Check your internet connection (and VPN, if required)"
    echo "and that github.com is reachable, then run the command again."
    exit 1
fi

unzip -q "$TMP/vdi.zip" -d "$TMP/unzipped"
SRC="$(find "$TMP/unzipped" -mindepth 1 -maxdepth 1 -type d | head -1)"
if [ -z "$SRC" ] || [ ! -f "$SRC/vdi_app.py" ]; then
    echo "The download didn't contain VDI Host Sizer. Please try again later."
    exit 1
fi

mkdir -p "$DEST"
cp -R "$SRC/." "$DEST/"          # updates the app files, keeps .venv and settings
chmod +x "$DEST/Run_on_mac.command" 2>/dev/null || true
# Belt and braces: clear any download flag so the launcher is never blocked
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$DEST/vdi_app.py" | head -1)"

echo "Installed VDI Host Sizer ${VERSION} in: $DEST"
echo "Next time, run this same command again to update, or run:"
echo "    bash \"$DEST/Run_on_mac.command\""
echo ""

if [ "${VDI_HOSTSIZER_NO_RUN:-0}" = "1" ]; then exit 0; fi
open "$DEST" 2>/dev/null || true   # show the folder in Finder

# Start the tool. Read prompts from the keyboard, not from the curl pipe.
if [ -r /dev/tty ]; then
    exec bash "$DEST/Run_on_mac.command" < /dev/tty
else
    exec bash "$DEST/Run_on_mac.command"
fi
