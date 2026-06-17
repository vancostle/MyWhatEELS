# Quick Build & Distribution Guide

## Building The Executable

### Prerequisites

- Python 3.13.4 recommended
- All dependencies from `requirements.txt`
- PyInstaller installed, or let `build_compressed_exe.py` install it in the temporary venv

### Build Command

```powershell
python build_compressed_exe.py
```

### What Happens

1. Creates `temporal_venv`.
2. Installs dependencies from `requirements.txt`.
3. Runs PyInstaller with `mywhateels.spec`.
4. Builds the single executable at `dist/WhatEELS.exe`.
5. Compresses that executable to `WhatEELS.zip`.
6. Optionally removes temporary build files.

## Distribution

### Package Contents

```text
WhatEELS.zip
`-- WhatEELS.exe
```

### User Instructions

1. Extract `WhatEELS.zip`.
2. Run `WhatEELS.exe`.
3. Upload DM3/DM4 files via the web interface.

## Pre-Release Checklist

- [ ] Built on a clean virtual environment
- [ ] Tested on Windows 10/11 without Python installed
- [ ] No SSL/DLL errors
- [ ] File upload works
- [ ] All visualizations render
- [ ] Clustering features work
- [ ] Multifitting runs successfully
- [ ] No antivirus false positives
- [ ] Executable size is reasonable

## Common Issues & Quick Fixes

### SSL Or DLL Import Error

The active Windows spec collects common conda runtime DLLs from `Library/bin`.
If warnings persist, check that the parent conda environment contains the
reported DLLs.

### Missing Panel Assets

Verify CSS, HTML, JS, and image files are present in the `datas` section of
`mywhateels.spec`.

### Slow Startup

The current spec builds one single executable. First startup can take longer
because PyInstaller extracts bundled files to a temporary runtime directory.

### Antivirus False Positive

Keep `upx=False` in the spec and consider signing the executable.

## Rebuilding After Code Changes

```powershell
# Quick rebuild if the spec did not change
pyinstaller mywhateels.spec

# Full rebuild with packaging
python build_compressed_exe.py
```

## Distribution Best Practices

1. Use versioned zip names for releases, for example `WhatEELS_v1.0.0.zip`.
2. Include a short README with basic instructions.
3. Test on the target OS before distributing.
4. Document system requirements, such as Windows 10+ and available RAM.
5. Provide sample data files for testing.
