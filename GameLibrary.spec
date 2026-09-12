# -*- mode: python ; coding: utf-8 -*-
#
# Build with:
#     py -m PyInstaller --noconfirm --clean GameLibrary.spec
#
# Why a .spec file instead of a one-line --onefile command:
# pygame and pywebview both ship native DLLs / data files (SDL2, the
# pythonnet/.NET interop pywebview uses on Windows, etc.). A plain
# `PyInstaller --onefile run_app.py` only follows plain Python imports, so
# those native files were left out of the build -- pygame silently failed to
# import inside the frozen exe (the try/except in backend/controller.py
# swallowed the error), which is why the controller never worked at all.
# collect_all() below pulls in every binary/data file each package ships so
# nothing gets left behind.

from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = [('frontend', 'frontend')]
binaries = []
hiddenimports = [
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
]

for pkg in ('pygame', 'webview', 'clr_loader', 'pythonnet'):
    try:
        pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    except Exception:
        continue

    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['run_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GameLibrary',
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
    icon='app.ico',
)
