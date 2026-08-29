#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

python3 -m pip install -r requirements-build.txt
python3 -m PyInstaller --noconfirm --clean DeepSeekWebAgent-macos.spec

machine_arch="$(uname -m)"
case "$machine_arch" in
  arm64) package_arch="apple-silicon" ;;
  x86_64) package_arch="intel" ;;
  *) echo "Unsupported macOS architecture: $machine_arch" >&2; exit 1 ;;
esac

# Ad-hoc signing verifies bundle integrity. Public distribution still needs an
# Apple Developer ID signature and notarization to avoid Gatekeeper warnings.
codesign --force --deep --sign - "dist/DeepSeek Web Agent.app"

staging_dir="build/dmg-${package_arch}"
rm -rf "$staging_dir"
mkdir -p "$staging_dir"
cp -R "dist/DeepSeek Web Agent.app" "$staging_dir/"
cp "README-macOS.txt" "$staging_dir/"
ln -s /Applications "$staging_dir/Applications"

output="dist/DeepSeekWebAgent-macOS-${package_arch}.dmg"
hdiutil create \
  -volname "DeepSeek Web Agent" \
  -srcfolder "$staging_dir" \
  -ov \
  -format UDZO \
  "$output"

echo "Built $output"
