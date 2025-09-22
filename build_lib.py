import os
import shutil
import subprocess
import zipfile

# Configuración
MAIN_SCRIPT = "main.py"  # Cambia si tu entrypoint es otro
DIST_DIR = "dist"
BUILD_DIR = "build"
ZIP_NAME = "Whateels_dist.zip"

def run(cmd):
    print(f"Ejecutando: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando: {cmd}")

# 1. Instalar dependencias (opcional, descomenta si quieres forzar)
run(f'"{os.sys.executable}" -m pip install -r requirements.txt')

# 2. Ejecutar PyInstaller
run(f'"{os.sys.executable}" -m PyInstaller --onefile --windowed {MAIN_SCRIPT}')

# 3. Comprimir la carpeta dist/
if os.path.exists(ZIP_NAME):
    os.remove(ZIP_NAME)
with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(DIST_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, start=DIST_DIR)
            zipf.write(filepath, arcname=os.path.join(DIST_DIR, arcname))
print(f"Carpeta '{DIST_DIR}' comprimida como '{ZIP_NAME}'.")

# 4. Limpiar archivos temporales
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
for f in os.listdir():
    if f.endswith(".spec"):
        os.remove(f)
print("Archivos temporales eliminados.")

print("\n¡Listo! Distribuye el archivo Whateels_dist.zip.")
print("El usuario debe descomprimirlo y ejecutar el .exe dentro de la carpeta dist/.")