import os
import shutil
import subprocess
import sys
import zipfile
import platform
import psutil
import time


# Color codes for console output
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'

def print_info(msg):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.RESET}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.RESET}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.RESET}")


# Configuración
MAIN_SCRIPT = "main.py"  # Cambia si tu entrypoint es otro
DIST_DIR = "dist"
BUILD_DIR = "build"
ZIP_NAME = "WhatEELS.zip"
TEMP_VENV = "temporal_venv"
IS_WINDOWS = platform.system() == "Windows"
TEMP_VENV_PY  = os.path.join(TEMP_VENV, "Scripts", "python.exe") if IS_WINDOWS else os.path.join(TEMP_VENV,"bin", "python")
if IS_WINDOWS:
    COMMAND = {
        "create_venv": f'"{sys.executable}" -m venv {TEMP_VENV}',
        "install_deps": f'"{TEMP_VENV_PY}" -m pip install -r requirements.txt',
        "build_exe": f'"{TEMP_VENV_PY}" -m PyInstaller --clean mywhateels.spec',    
    }
else:
    COMMAND = {
        "create_venv": f'"{sys.executable}" -m venv {TEMP_VENV}',
        "install_deps": f'"{TEMP_VENV_PY}" -m pip install -r requirements.txt',
        "build_exe": f'"{TEMP_VENV_PY}" -m PyInstaller mywhateels_linux.spec',
    }

# Function to run shell commands
def run(cmd):
    print_info(f"Ejecutando: {cmd}")
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
            print_error(f"pip is not installed for {python_exe}.")
            exit(1)
    except Exception as e:
        print_error(f"Error checking pip: {e}")
        exit(1)

def kill_process_by_name(process_name):
    """Kill all processes with the given name."""
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                print_warning(f"Killing process {proc.pid} ({proc.info['name']})")
                proc.kill()
                killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    if killed:
        time.sleep(1)  # Wait for processes to fully terminate
    return killed

def check_antivirus_exclusion():
    """Check if dist directory needs antivirus exclusion."""
    dist_path = os.path.abspath(DIST_DIR)
    print("\n" + "="*60)
    print("IMPORTANTE: CONFIGURACIÓN DE ANTIVIRUS")
    print("="*60)
    print(f"\nSi el build falla con Permission Denied, es probable que tu")
    print(f"antivirus esté bloqueando o eliminando el archivo .exe")
    print(f"\nAgrega esta carpeta a las EXCLUSIONES de tu antivirus:")
    print(f"  -> {dist_path}")
    print(f"\nPara Windows Defender:")
    print(f"  1. Configuración > Privacidad y seguridad > Seguridad de Windows")
    print(f"  2. Protección contra virus y amenazas > Configuración")
    print(f"  3. Exclusiones > Agregar exclusión > Carpeta")
    print(f"  4. Selecciona: {dist_path}")
    print("="*60 + "\n")
    
    input("Presiona ENTER cuando hayas configurado las exclusiones (o Ctrl+C para cancelar)...")

check_file_exists("requirements.txt")
check_file_exists("mywhateels.spec")
# Check pip for system Python
check_pip_available(sys.executable)

print_info("Iniciando proceso de construcción...")

# Kill any running instances of the executable
print_info("Verificando procesos en ejecución...")
kill_process_by_name("WhatEELS.exe")

# Clean up old build artifacts before starting (including PyInstaller cache)
print_info("Limpiando artefactos de compilación anteriores...")

if os.path.exists(BUILD_DIR):
    try:
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
        print_success(f"'{BUILD_DIR}' eliminado.")
    except Exception as e:
        print_warning(f"No se pudo eliminar '{BUILD_DIR}': {e}")

if os.path.exists(DIST_DIR):
    try:
        shutil.rmtree(DIST_DIR, ignore_errors=True)
        print_success(f"'{DIST_DIR}' eliminado.")
    except Exception as e:
        print_warning(f"No se pudo eliminar '{DIST_DIR}': {e}")

# Also remove __pycache__ to force Python to recompile
for root, dirs, files in os.walk('.'):
    if '__pycache__' in dirs:
        pycache_path = os.path.join(root, '__pycache__')
        try:
            shutil.rmtree(pycache_path, ignore_errors=True)
        except:
            pass

# Check if virtual environment already exists
if os.path.exists(TEMP_VENV) and os.path.exists(TEMP_VENV_PY):
    print_success(f"Virtualenv temporal '{TEMP_VENV}' ya existe, reutilizándolo...")
else:
    print_info("Creando virtualenv temporal...")
    run(COMMAND["create_venv"])
    print_success("Virtualenv temporal creado.")

# Check if dependencies are already installed
try:
    result = subprocess.run(
        f'"{TEMP_VENV_PY}" -c "import panel; import psutil; import pyinstaller"',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    if result.returncode == 0:
        print_success("Dependencias ya instaladas en temporal_venv, omitiendo instalación...")
    else:
        print_info("Instalando dependencias...")
        run(COMMAND["install_deps"])
        print_success("Dependencias instaladas en temporal_venv.")
except Exception:
    print_info("Instalando dependencias...")
    run(COMMAND["install_deps"])
    print_success("Dependencias instaladas en temporal_venv.")

print_info("Construyendo ejecutable...\n")
print_warning("ESTO PUEDE TARDAR VARIOS MINUTOS, POR FAVOR ESPERA...")
run(COMMAND["build_exe"])
print_success("Ejecutable construido.")

# Refresh Windows icon cache so the new icon shows immediately
if IS_WINDOWS:
    print_info("Actualizando caché de iconos de Windows...")
    try:
        subprocess.run("ie4uinit.exe -show", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print_success("Caché de iconos actualizado.")
    except:
        print_warning("No se pudo actualizar la caché de iconos. Presiona F5 en el explorador para ver el nuevo icono.")

# 3. Comprimir la carpeta dist/
if os.path.exists(ZIP_NAME):
    print_info("Eliminando archivo zip previo...")
    os.remove(ZIP_NAME)
    print_success("Archivo zip previo eliminado.")

print_info("Comprimiendo ejecutable...")

# Comprimir solo la carpeta WhatEELS (la que nos interesa)
app_folder = os.path.join(DIST_DIR, "WhatEELS")

if os.path.exists(app_folder):
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(app_folder):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, start=app_folder)
                zipf.write(filepath, arcname=arcname)
    print_success(f"Carpeta 'WhatEELS' comprimida correctamente como '{ZIP_NAME}'.")
else:
    # Si no existe WhatEELS, comprimir lo que haya en dist
    print_warning("No se encontró carpeta WhatEELS. Comprimiendo dist directamente...")
    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DIST_DIR):
            for file in files:
                filepath = os.path.join(root, file)
                arcname = os.path.relpath(filepath, start=DIST_DIR)
                zipf.write(filepath, arcname=arcname)

print_success(f"Carpeta '{DIST_DIR}' comprimida como '{ZIP_NAME}'.")

# Show antivirus exclusion recommendation after build
check_antivirus_exclusion()

# Ask user if they want to clean up temporary files
print("\n" + "="*60)
print("LIMPIEZA DE ARCHIVOS TEMPORALES")
print("="*60)
print(f"\nArchivos/carpetas que se pueden eliminar:")
print(f"  - {TEMP_VENV} (entorno virtual temporal)")
print(f"\nArchivos que se conservarán:")
print(f"  - {ZIP_NAME} (ejecutable comprimido)")
print("="*60)

cleanup = input("\n¿Deseas eliminar el entorno virtual temporal? (s/n): ").strip().lower()

if cleanup == 's' or cleanup == 'y' or cleanup == 'yes' or cleanup == 'si':
    print_info("\nEliminando entorno virtual temporal...")
    
    # Remove virtual environment
    if os.path.exists(TEMP_VENV):
        try:
            shutil.rmtree(TEMP_VENV, ignore_errors=False)
            print_success(f"'{TEMP_VENV}' eliminado.")
        except PermissionError:
            print_warning(f"Algunos archivos en '{TEMP_VENV}' están en uso. Intentando eliminación forzada...")
            time.sleep(1)
            try:
                shutil.rmtree(TEMP_VENV, ignore_errors=True)
                print_success(f"'{TEMP_VENV}' eliminado.")
            except Exception as e:
                print_error(f"No se pudo eliminar completamente '{TEMP_VENV}': {e}")
        except Exception as e:
            print_error(f"No se pudo eliminar '{TEMP_VENV}': {e}")
    
    print_success("Limpieza completada.")
else:
    print_info("\nEntorno virtual temporal conservado para futuras compilaciones.")
    
# Remove build directory
if os.path.exists(BUILD_DIR):
    try:
        shutil.rmtree(BUILD_DIR, ignore_errors=False)
        print_success(f"'{BUILD_DIR}' eliminado.")
    except PermissionError:
        print_warning(f"Algunos archivos en '{BUILD_DIR}' están en uso. Intentando eliminación forzada...")
        time.sleep(1)
        try:
            shutil.rmtree(BUILD_DIR, ignore_errors=True)
            print_success(f"'{BUILD_DIR}' eliminado.")
        except Exception as e:
            print_error(f"No se pudo eliminar completamente '{BUILD_DIR}': {e}")
    except Exception as e:
        print_error(f"No se pudo eliminar '{BUILD_DIR}': {e}")

# Remove dist directory
# if os.path.exists(DIST_DIR):
#     try:
#         shutil.rmtree(DIST_DIR, ignore_errors=False)
#         print_success(f"'{DIST_DIR}' eliminado.")
#     except PermissionError:
#         print_warning(f"Algunos archivos en '{DIST_DIR}' están en uso. Intentando eliminación forzada...")
#         time.sleep(1)
#         try:
#             shutil.rmtree(DIST_DIR, ignore_errors=True)
#             print_success(f"'{DIST_DIR}' eliminado.")
#         except Exception as e:
#             print_error(f"No se pudo eliminar completamente '{DIST_DIR}': {e}")
#     except Exception as e:
#         print_error(f"No se pudo eliminar '{DIST_DIR}': {e}")

print(f"\n{Colors.GREEN}{Colors.BOLD}¡Listo! Distribuye el archivo Whateels_dist.zip.{Colors.RESET}")
print_info("El usuario debe descomprimirlo y ejecutar el .exe dentro de la carpeta dist/.")
