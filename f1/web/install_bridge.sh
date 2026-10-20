#!/bin/zsh
# Installs the Pocket bridge (USB + Bluetooth -> http://127.0.0.1:8091) as a login service on this Mac.
# It lives in ~/.sc02 because macOS does not let background services read ~/Downloads.
set -e
D=~/.sc02; P=~/Library/LaunchAgents/be.kobe.pocketbridge.plist
mkdir -p $D && cp "${0:a:h}/pocket_bridge.py" $D/
[ -x $D/venv/bin/python ] || { /opt/homebrew/bin/python3 -m venv $D/venv && $D/venv/bin/pip -q install hidapi; }
cat > $P <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>be.kobe.pocketbridge</string>
  <key>ProgramArguments</key><array><string>$D/venv/bin/python</string><string>$D/pocket_bridge.py</string></array>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/.pocket-bridge.log</string><key>StandardErrorPath</key><string>$HOME/.pocket-bridge.log</string>
</dict></plist>
PL
launchctl bootout gui/$(id -u)/be.kobe.pocketbridge 2>/dev/null || true
launchctl bootstrap gui/$(id -u) $P
echo "Pocket-brug draait (start vanzelf bij elke login): http://127.0.0.1:8091"
