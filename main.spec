# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('assets/favicon.ico', 'assets'), ('assets/main.ui', 'assets'), ('assets/gs_not_found.ui', 'assets'), ('assets/logo.png', 'assets'), ('assets/poweredby.png', 'assets'), ('assets/load-bars.gif', 'assets'), ('assets/cloud_link.png', 'assets'), ('assets/printer.png', 'assets'), ('assets/queue_check.png', 'assets'), ('assets/refresh.png', 'assets'), ('assets/slotmachine.wav', 'assets'), ('assets/trash_folder.png', 'assets')],
    hiddenimports=['PyQt6', 'Flask', 'waitress'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='IdeYou Print',
    debug=False,
    icon='assets/favicon.ico',
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    windowed=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
