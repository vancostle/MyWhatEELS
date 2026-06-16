# -*- mode: python ; coding: utf-8 -*-
import glob
import importlib.util
import os
import sys

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

block_cipher = None


def collect_runtime_binaries():
    """Collect DLLs used by conda-backed venv extension modules on Windows."""
    executable_dir = os.path.dirname(sys.executable)
    base_executable = getattr(sys, '_base_executable', '') or ''

    roots = {
        executable_dir,
        os.path.dirname(executable_dir),
        sys.prefix,
        sys.base_prefix,
        os.environ.get('CONDA_PREFIX', ''),
    }
    if base_executable:
        base_executable_dir = os.path.dirname(base_executable)
        roots.add(base_executable_dir)
        roots.add(os.path.dirname(base_executable_dir))

    candidates = set()
    for root in roots:
        if not root:
            continue
        candidates.update(
            {
                root,
                os.path.join(root, 'Scripts'),
                os.path.join(root, 'DLLs'),
                os.path.join(root, 'Library', 'bin'),
                os.path.join(root, 'Library', 'bin', 'openssl'),
            }
        )

    patterns = (
        'libssl*.dll',
        'libcrypto*.dll',
        'libexpat*.dll',
        'ffi*.dll',
        'libffi*.dll',
        'libmpdec*.dll',
        'sqlite3.dll',
        'zlib*.dll',
        'vcruntime*.dll',
        'msvcp*.dll',
        '_ssl*.pyd',
        '_hashlib*.pyd',
        'pyexpat*.pyd',
        '_ctypes*.pyd',
        '_decimal*.pyd',
    )

    binaries = []
    seen = set()
    for search_dir in candidates:
        if not os.path.exists(search_dir):
            continue
        for pattern in patterns:
            for path in glob.glob(os.path.join(search_dir, pattern)):
                norm = os.path.normcase(os.path.abspath(path))
                if norm in seen:
                    continue
                seen.add(norm)
                binaries.append((path, '.'))

    for ext_name in ('_ssl', '_hashlib', 'pyexpat', '_ctypes', '_decimal'):
        spec = importlib.util.find_spec(ext_name)
        if spec and spec.origin and os.path.exists(spec.origin):
            norm = os.path.normcase(os.path.abspath(spec.origin))
            if norm not in seen:
                seen.add(norm)
                binaries.append((spec.origin, '.'))

    return binaries


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


def expose_runtime_binary_dirs(binaries):
    if not sys.platform.startswith('win'):
        return []

    runtime_dirs = sorted(
        {
            os.path.dirname(path)
            for path, _ in binaries
            if path and os.path.exists(os.path.dirname(path))
        }
    )
    if runtime_dirs:
        os.environ['PATH'] = os.pathsep.join(runtime_dirs + [os.environ.get('PATH', '')])

    handles = []
    if hasattr(os, 'add_dll_directory'):
        for runtime_dir in runtime_dirs:
            try:
                handles.append(os.add_dll_directory(runtime_dir))
            except OSError:
                pass
    return handles


runtime_binaries = collect_runtime_binaries()
_dll_directory_handles = expose_runtime_binary_dirs(runtime_binaries)

metadata = []
for dist in (
    'numpy',
    'scipy',
    'pandas',
    'panel',
    'bokeh',
    'holoviews',
    'scikit-learn',
    'numba',
    'llvmlite',
    'xarray',
    'lmfit',
    'umap-learn',
    'hdbscan',
):
    metadata.extend(collect_optional_metadata(dist))

package_data = []
for pkg in ('panel', 'bokeh', 'holoviews', 'matplotlib'):
    package_data.extend(collect_optional_data(pkg))


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=runtime_binaries,
    datas=[
        ('whateels/assets/css/*.css', 'whateels/assets/css'),
        ('whateels/assets/html/*.html', 'whateels/assets/html'),
        ('whateels/assets/js/*.js', 'whateels/assets/js'),
        ('whateels/assets/img/*', 'whateels/assets/img'),
        ('whateels/assets/oos/Hartree_Xsections_FSalvat/*.json', 'whateels/assets/oos/Hartree_Xsections_FSalvat'),
        *metadata,
        *package_data,
    ],
    hiddenimports=[
        # SSL and networking
        '_ssl',
        '_hashlib',
        '_ctypes',
        '_decimal',
        'pyexpat',
        'xml.parsers.expat',
        'ssl',
        'certifi',
        
        # System utilities
        'psutil',
        'psutil._pswindows',
        
        # Panel and dependencies
        'panel',
        'panel.io',
        'panel.io.server',
        'panel.widgets',
        'panel.pane',
        'panel.template',
        'panel.custom',
        'panel.reactive',
        'panel.viewable',
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
        'holoviews',
        
        # Plotting
        'matplotlib',
        
        # Machine learning
        'sklearn',
        'sklearn.cluster',
        'sklearn.decomposition',
        'umap',
        'hdbscan',
        
        # Fitting
        'lmfit',
        'lmfit.models',
        
        # Other
        'numba',
        'numba.core',
        'numba.core.typing',
        'numba.core.datamodel',
        'numba.cpython',
        'numba.np',
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
    icon='whateels/assets/img/we_color_logo.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
)
