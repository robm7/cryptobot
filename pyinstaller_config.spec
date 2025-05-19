# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Cryptobot

This file configures PyInstaller to create a standalone executable
for the Cryptobot trading system.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Add project root to path
# Use os.getcwd() instead of __file__ since PyInstaller doesn't define __file__ when running the spec
project_root = os.path.abspath(os.getcwd())
sys.path.insert(0, project_root)

# Collect all necessary data files
data_files = []
data_files.extend(collect_data_files('static'))
data_files.extend(collect_data_files('templates'))
data_files.extend(collect_data_files('config'))

# Add specific configuration files
data_files.extend([
    ('config/default_config.json', 'config/default_config.json', 'DATA'),
    ('LICENSE', 'LICENSE', 'DATA'),
    ('README.md', 'README.md', 'DATA'),
])

# Collect all submodules to ensure they're included
hidden_imports = []
hidden_imports.extend(collect_submodules('services'))
hidden_imports.extend(collect_submodules('auth'))
hidden_imports.extend(collect_submodules('strategy'))
hidden_imports.extend(collect_submodules('backtest'))
hidden_imports.extend(collect_submodules('trade'))
hidden_imports.extend(collect_submodules('data'))
hidden_imports.extend(collect_submodules('utils'))

# Add specific imports that might be missed
hidden_imports.extend([
    'sqlalchemy.ext.baked',
    'sqlalchemy.ext.declarative',
    'redis',
    'numpy',
    'pandas',
    'fastapi',
    'uvicorn',
    'jinja2',
    'pydantic',
    'email_validator',
    'passlib.handlers.argon2',
    'cryptography',
])

# Main executable
a = Analysis(
    ['main.py'],  # Main entry point
    pathex=[project_root],
    binaries=[],
    datas=data_files,
    hiddenimports=hidden_imports,
    hookspath=['hooks'],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure, 
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='cryptobot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='static/favicon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='cryptobot'
)

# Create a single-file executable as well
exe_onefile = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='cryptobot_onefile',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='static/favicon.ico'
)