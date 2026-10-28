#!/bin/bash
# =============================================================================
#  VDI Host Sizer - Mac installer and updater
#
#  Open Terminal, paste this line and press Return:
#    curl -fsSL https://raw.githubusercontent.com/adammarcum/VDI-Sizing-Tool/main/install_mac.sh | bash
#
#  Downloads the latest version from GitHub into ~/HostSizer/vdi-app, creates a
#  double-click "VDI Host Sizer" app in ~/Applications (also in Launchpad and
#  Spotlight), and starts the tool. Run the same line again any time to update;
#  your Python environment and saved projects (~/HostSizer/VDIProjects) are kept.
#
#  Everything is downloaded or built on this Mac, so nothing is quarantined and
#  macOS never shows "Apple could not verify..." prompts.
# =============================================================================
set -euo pipefail

REPO="${VDI_HOSTSIZER_REPO:-adammarcum/VDI-Sizing-Tool}"
DEST="${HOSTSIZER_HOME:-$HOME/HostSizer}/vdi-app"
APPS_DIR="${VDI_HOSTSIZER_APPS_DIR:-$HOME/Applications}"
APP="$APPS_DIR/VDI Host Sizer.app"
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
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true   # belt and braces
VERSION="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' "$DEST/vdi_app.py" | head -1)"

# -----------------------------------------------------------------------------
# Double-click app. Built here with macOS's own osacompile, so it is local (no
# quarantine) and signed ad hoc. It opens Run_on_mac.command in Terminal with
# `open -a`, which needs no "control Terminal" permission prompt.
# Failure here never stops the install - the launcher still works without it.
# -----------------------------------------------------------------------------
make_app() {
    command -v osacompile >/dev/null 2>&1 || return 1
    mkdir -p "$APPS_DIR"
    local scr="$TMP/launch.applescript"
    cat > "$scr" <<EOS
on run
    set launcher to "$DEST/Run_on_mac.command"
    try
        do shell script "test -f " & quoted form of launcher
    on error
        display dialog "VDI Host Sizer was not found. Run the install command from the ReadMe in Terminal to reinstall." buttons {"OK"} default button "OK" with icon caution
        return
    end try
    do shell script "open -a Terminal " & quoted form of launcher
end run
EOS
    rm -rf "$APP"
    osacompile -o "$APP" "$scr" || return 1
    # Icon from the app's own PNG
    if [ -f "$DEST/vdi_sizer_icon.png" ] && command -v sips >/dev/null 2>&1 && command -v iconutil >/dev/null 2>&1; then
        local set="$TMP/icon.iconset"
        mkdir -p "$set"
        for s in 16 32 64 128 256; do
            sips -z $s $s "$DEST/vdi_sizer_icon.png" --out "$set/tmp_$s.png" >/dev/null 2>&1 || true
        done
        cp "$set/tmp_16.png"  "$set/icon_16x16.png"      2>/dev/null || true
        cp "$set/tmp_32.png"  "$set/icon_16x16@2x.png"   2>/dev/null || true
        cp "$set/tmp_32.png"  "$set/icon_32x32.png"      2>/dev/null || true
        cp "$set/tmp_64.png"  "$set/icon_32x32@2x.png"   2>/dev/null || true
        cp "$set/tmp_128.png" "$set/icon_128x128.png"    2>/dev/null || true
        cp "$set/tmp_256.png" "$set/icon_128x128@2x.png" 2>/dev/null || true
        cp "$set/tmp_256.png" "$set/icon_256x256.png"    2>/dev/null || true
        rm -f "$set"/tmp_*.png
        if iconutil -c icns "$set" -o "$TMP/applet.icns" >/dev/null 2>&1; then
            cp "$TMP/applet.icns" "$APP/Contents/Resources/applet.icns"
            touch "$APP"
        fi
    fi
    xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
    codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
    return 0
}

APP_OK=0
if make_app; then APP_OK=1; fi

echo "Installed VDI Host Sizer ${VERSION} in: $DEST"
if [ "$APP_OK" = "1" ]; then
    echo "Next time, open 'VDI Host Sizer' from your Applications folder ($APPS_DIR),"
    echo "Launchpad or Spotlight. Run this same command again to update."
else
    echo "Next time, run:  bash \"$DEST/Run_on_mac.command\""
    echo "(Run this same command again to update.)"
fi
echo ""

if [ "${VDI_HOSTSIZER_NO_RUN:-0}" = "1" ]; then exit 0; fi

# Start the tool. Read prompts from the keyboard, not from the curl pipe.
if [ -r /dev/tty ]; then
    exec bash "$DEST/Run_on_mac.command" < /dev/tty
else
    exec bash "$DEST/Run_on_mac.command"
fi
