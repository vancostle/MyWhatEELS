# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


block_cipher = None


def collect_optional_submodules(package_name):
    try:
        return collect_submodules(package_name)
    except Exception:
        return []


def collect_optional_metadata(dist_name):
    try:
        return copy_metadata(dist_name)
    except Exception:
        return []


def collect_optional_data(package_name):
    try:
        return collect_data_files(package_name)
    except Exception:
        return []


core_hiddenimports = [
    'whateels',
    'whateels.pages',
    'whateels.pages.home',
    'whateels.pages.metadata',
    'whateels.pages.clustering',
    'whateels.pages.clustering_2',
    'whateels.pages.quantification',
    'whateels.pages.fitting',
    'whateels.base',
    'whateels.components',
    'whateels.errors',
    'whateels.helpers',
    'whateels.interfaces',
    'whateels.state',
    'whateels.templates',
    '_ssl',
    '_hashlib',
    'ssl',
    'certifi',
    'psutil',
    'panel',
    'bokeh',
    'tornado',
    'numpy',
    'scipy',
    'xarray',
    'pandas',
    'plotly',
    'matplotlib',
    'sklearn',
    'lmfit',
    'numba',
    'holoviews',
    'umap',
    'hdbscan',
]

extra_hiddenimports = []
for pkg in (
    'whateels',
    'whateels.pages',
    'whateels.base',
    'whateels.components',
    'whateels.errors',
    'whateels.helpers',
    'whateels.interfaces',
    'whateels.state',
    'whateels.templates',
    'panel',
    'bokeh',
    'holoviews',
    'plotly',
    'sklearn',
    'scipy',
    'numba',
    'umap',
    'hdbscan',
    'xarray',
    'lmfit',
    'psutil',
):
    extra_hiddenimports.extend(collect_optional_submodules(pkg))

extra_metadata = []
for dist in (
    'numpy',
    'scipy',
    'pandas',
    'panel',
    'bokeh',
    'holoviews',
    'plotly',
    'scikit-learn',
    'numba',
    'llvmlite',
    'xarray',
    'lmfit',
    'umap-learn',
    'hdbscan',
):
    extra_metadata.extend(collect_optional_metadata(dist))

extra_datas = []
for pkg in ('panel', 'bokeh', 'holoviews'):
    extra_datas.extend(collect_optional_data(pkg))

hiddenimports = sorted(set(core_hiddenimports + extra_hiddenimports))
datas = [
    ('whateels/assets/css/*.css', 'whateels/assets/css'),
    ('whateels/assets/html/*.html', 'whateels/assets/html'),
    ('whateels/assets/js/*.js', 'whateels/assets/js'),
    ('whateels/assets/img/*', 'whateels/assets/img'),
    ('whateels/assets/oos/Hartree_Xsections_FSalvat/*.json', 'whateels/assets/oos/Hartree_Xsections_FSalvat'),
    *extra_metadata,
    *extra_datas,
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    icon='whateels/assets/img/we_white_logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
