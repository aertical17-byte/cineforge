#!/bin/bash
# Builds the CineForge AI launcher .app (universal) and a fancy .dmg (dmgbuild).
# Designed for CI (GitHub Actions macOS runner): everything is scripted, no Finder tricks.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"          # installer/mac
ROOT="$(cd "$HERE/../.." && pwd)"              # repo root
cd "$ROOT"

echo "== 1/5 assets (icon + background)"
python3 installer/mac/make_assets.py
iconutil -c icns installer/mac/assets/icon.iconset -o installer/mac/assets/AppIcon.icns

echo "== 2/5 universal binary (x86_64 + arm64)"
mkdir -p dist
swiftc -O -target x86_64-apple-macos12.0 installer/mac/main.swift -o dist/build_x86
swiftc -O -target arm64-apple-macos12.0  installer/mac/main.swift -o dist/build_arm
lipo -create -output dist/build_universal dist/build_x86 dist/build_arm

echo "== 3/5 app bundle"
APP="dist/CineForge AI.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp dist/build_universal "$APP/Contents/MacOS/CineForgeAI"
cp installer/mac/assets/AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
cp installer/mac/Resources/guida.html "$APP/Contents/Resources/guida.html"
cp installer/mac/Info.plist "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"
codesign --force --deep --sign - "$APP"   # ad-hoc: honest, no paid Apple certificate

echo "== 4/5 dmg (dmgbuild: background + icon positions, no Finder scripting)"
dmgbuild -s installer/mac/dmgsettings.py "CineForge AI" "dist/CineForge-AI.dmg"

echo "== 5/5 done"
ls -lh dist/CineForge-AI.dmg
hdiutil imageinfo dist/CineForge-AI.dmg | head -n 6
