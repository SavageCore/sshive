# -*- mode: python ; -*-
# type: ignore


a = Analysis(  # noqa: F821
    ["sshive/main.py"],
    pathex=[],
    binaries=[],
    datas=[("sshive/resources", "sshive/resources")],
    hiddenimports=["PySide6.QtXml", "PySide6.QtNetwork"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SSHive",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=["sshive/resources/icon.png"],
)
coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SSHive",
)
app = BUNDLE(  # noqa: F821
    coll,
    name="SSHive.app",
    icon="sshive/resources/icon.png",
    bundle_identifier="org.sshive.SSHive",
)
