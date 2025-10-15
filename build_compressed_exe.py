import os
import shutil
import subprocess
import zipfile

# Configuración
MAIN_SCRIPT = "main.py"  # Cambia si tu entrypoint es otro
DIST_DIR = "dist"
BUILD_DIR = "build"
ZIP_NAME = "Whateels_dist.zip"
TEMP_VENV = "temporal_venv"
TEMP_VENV_PY = os.path.join(TEMP_VENV, "Scripts", "python.exe")
TEMP_VENV_PIP = os.path.join(TEMP_VENV, "Scripts", "pip.exe")
COMMAND = {
    "create_venv": f'"{os.sys.executable}" -m venv {TEMP_VENV}',
    "install_deps": f'"{TEMP_VENV_PY}" -m pip install -r requirements.txt',
    "build_exe": f'"{TEMP_VENV_PY}" -m PyInstaller mywhateels.spec',
}

# Function to run shell commands
def run(cmd):
    print(f"Ejecutando: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        raise RuntimeError(f"Error ejecutando: {cmd}")

# Check for required files before running commands
def check_file_exists(filename):
    if not os.path.isfile(filename):
        raise FileNotFoundError(f"Required file not found: {filename}")

def check_pip_available(python_exe):
    try:
        result = subprocess.run(f'"{python_exe}" -m pip --version', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode != 0:
            print(f"Error: pip is not installed for {python_exe}.")
            exit(1)
    except Exception as e:
        print(f"Error checking pip: {e}")
        exit(1)

check_file_exists("requirements.txt")
check_file_exists("mywhateels.spec")

# Check pip for system Python
check_pip_available(os.sys.executable)

print("Iniciando proceso de construcción...")
run(COMMAND["create_venv"])
print("Virtualenv temporal creado.")
run(COMMAND["install_deps"])
print("Dependencias instaladas en temporal_venv.")

print("Construyendo ejecutable...\n")
print("ESTO PUEDE TARDAR VARIOS MINUTOS, POR FAVOR ESPERA...")
run(COMMAND["build_exe"])
print("Ejecutable construido.")

# 3. Comprimir la carpeta dist/
if os.path.exists(ZIP_NAME):
    print("Eliminando archivo zip previo...")
    os.remove(ZIP_NAME)
    print("Archivo zip previo eliminado.")

print("Comprimiendo ejecutable...")
with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(DIST_DIR):
        for file in files:
            filepath = os.path.join(root, file)
            arcname = os.path.relpath(filepath, start=DIST_DIR)
            zipf.write(filepath, arcname=os.path.join(DIST_DIR, arcname))
print(f"Carpeta '{DIST_DIR}' comprimida como '{ZIP_NAME}'.")

print("Eliminando entorno virtual temporal...")
try:
    shutil.rmtree(TEMP_VENV)
    print(f"Entorno virtual temporal '{TEMP_VENV}' eliminado.")
except Exception as e:
    print(f"No se pudo eliminar '{TEMP_VENV}': {e}")

print("Limpiando otros archivos temporales...")
if os.path.exists(BUILD_DIR):
    shutil.rmtree(BUILD_DIR)
if os.path.exists(DIST_DIR):
    shutil.rmtree(DIST_DIR)
print("Archivos temporales eliminados.")

print("\n¡Listo! Distribuye el archivo Whateels_dist.zip.")
print("El usuario debe descomprimirlo y ejecutar el .exe dentro de la carpeta dist/.")
