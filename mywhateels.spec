# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Locate OpenSSL DLLs from the Python installation
import ssl
ssl_paths = []
if hasattr(ssl, 'get_default_verify_paths'):
    ssl_dir = os.path.dirname(ssl.__file__)
    python_dir = os.path.dirname(sys.executable)
    # Common locations for OpenSSL DLLs
    for search_dir in [ssl_dir, python_dir, os.path.join(python_dir, 'DLLs')]:
        if os.path.exists(search_dir):
            for file in os.listdir(search_dir):
                if file.startswith(('libssl', 'libcrypto')) and file.endswith('.dll'):
                    ssl_paths.append((os.path.join(search_dir, file), '.'))

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=ssl_paths,  # Include SSL DLLs
    datas=[
        ('whateels/assets/css/*.css', 'whateels/assets/css'),
        ('whateels/assets/html/*.html', 'whateels/assets/html'),
        ('whateels/assets/js/*.js', 'whateels/assets/js'),
        ('whateels/assets/img/*', 'whateels/assets/img'),
        # Add other asset folders as needed
    ],
    hiddenimports=[
        # SSL and networking
        '_ssl',
        '_hashlib',
        'ssl',
        'certifi',
        
        # Panel and dependencies
        'panel',
        'panel.io',
        'panel.io.server',
        'panel.widgets',
        'panel.pane',
        'panel.template',
        'bokeh',
        'bokeh.server',
        'bokeh.server.tornado',
        'tornado',
        'tornado.web',
        'tornado.ioloop',
        
        # Scientific computing
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'scipy',
        'scipy.special',
        'scipy.special._ufuncs_cxx',
        'xarray',
        'pandas',
        
        # Plotting
        'plotly',
        'plotly.graph_objs',
        'matplotlib',
        
        # Machine learning
        'sklearn',
        'sklearn.cluster',
        'sklearn.decomposition',
        
        # Fitting
        'lmfit',
        'lmfit.models',
        
        # Other
        'numba',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='WhatEELS',
    icon='whateels/assets/img/logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
