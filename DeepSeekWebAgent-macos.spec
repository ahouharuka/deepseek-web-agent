# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all


playwright_datas, playwright_binaries, playwright_hiddenimports = collect_all("playwright")

a = Analysis(
    ["desktop_app.py"],
    pathex=[],
    binaries=playwright_binaries,
    datas=playwright_datas + [("agent_skills", "agent_skills")],
    hiddenimports=playwright_hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DeepSeekWebAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
collection = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DeepSeekWebAgent",
)
app = BUNDLE(
    collection,
    name="DeepSeek Web Agent.app",
    icon=None,
    bundle_identifier="com.deepseekwebagent.desktop",
    version="0.2.0",
    info_plist={
        "CFBundleDisplayName": "DeepSeek Web Agent",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
