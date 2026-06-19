# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import glob
import importlib.util
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None


def collect_runtime_binaries():
    # Gather runtime binaries needed by compiled stdlib extensions on Windows.
    candidates = {
        os.path.dirname(sys.executable),
        os.path.dirname(os.path.dirname(sys.executable)),
        os.path.join(os.path.dirname(sys.executable), 'DLLs'),
        os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'DLLs'),
        sys.prefix,
        os.path.join(sys.prefix, 'DLLs'),
        sys.base_prefix,
        os.path.join(sys.base_prefix, 'DLLs'),
        os.path.join(sys.prefix, 'Library', 'bin'),
        os.path.join(sys.base_prefix, 'Library', 'bin'),
        os.path.join(sys.prefix, 'Library', 'bin', 'openssl'),
        os.path.join(sys.base_prefix, 'Library', 'bin', 'openssl'),
    }

    patterns = (
        'libssl*.dll',
        'libcrypto*.dll',
        'libexpat*.dll',
        '_ssl*.pyd',
        '_hashlib*.pyd',
        'pyexpat*.pyd',
        'vcruntime*.dll',
        'msvcp*.dll',
    )

    binaries = []
    seen = set()

    for search_dir in candidates:
        if not search_dir or not os.path.exists(search_dir):
            continue
        for pattern in patterns:
            for path in glob.glob(os.path.join(search_dir, pattern)):
                norm = os.path.normcase(os.path.abspath(path))
                if norm in seen:
                    continue
                seen.add(norm)
                binaries.append((path, '.'))

    for ext_name in ('_ssl', '_hashlib', 'pyexpat'):
        spec = importlib.util.find_spec(ext_name)
        if spec and spec.origin and os.path.exists(spec.origin):
            norm = os.path.normcase(os.path.abspath(spec.origin))
            if norm not in seen:
                seen.add(norm)
                binaries.append((spec.origin, '.'))

    return binaries


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


runtime_paths = collect_runtime_binaries()
if sys.platform.startswith('win'):
    has_libssl = any(os.path.basename(path).lower().startswith('libssl') for path, _ in runtime_paths)
    has_libcrypto = any(os.path.basename(path).lower().startswith('libcrypto') for path, _ in runtime_paths)
    has_libexpat = any(os.path.basename(path).lower().startswith('libexpat') for path, _ in runtime_paths)
    if not (has_libssl and has_libcrypto):
        raise RuntimeError(
            'OpenSSL DLLs not found for PyInstaller build. '
            'Expected libssl*.dll and libcrypto*.dll in Python/venv DLL directories.'
        )
    if not has_libexpat:
        raise RuntimeError(
            'Expat runtime DLL not found for PyInstaller build. '
            'Expected libexpat*.dll in Python/venv DLL directories.'
        )


core_hiddenimports = [
    # Local package and lazy-loaded pages
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
    # Runtime extension modules
    '_ssl',
    '_hashlib',
    'pyexpat',
    'xml.parsers.expat',
    # Core deps
    'ssl',
    'certifi',
    'psutil',
    'psutil._pswindows',
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
for pkg in ('panel', 'bokeh', 'holoviews', 'matplotlib'):
    extra_datas.extend(collect_optional_data(pkg))

hiddenimports = sorted(set(core_hiddenimports + extra_hiddenimports))
datas = [
    ('whateels/assets/css/*.css', 'whateels/assets/css'),
    ('whateels/assets/html/*.html', 'whateels/assets/html'),
    ('whateels/assets/js/*.js', 'whateels/assets/js'),
    ('whateels/assets/img/*', 'whateels/assets/img'),
    ('whateels/data/oos/Hartree_Xsections_FSalvat/*.json', 'whateels/data/oos/Hartree_Xsections_FSalvat'),
    *extra_metadata,
    *extra_datas,
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=runtime_paths,
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)
