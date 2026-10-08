"""
config.py — Configuración centralizada para todos los extractores
No depende de ATM. Todos los extractores usan esto.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Rutas base (relativas al repo root)
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
UPTIME_DATA_DIR = DATA_DIR / "uptime"
SHARED_DATA_DIR = DATA_DIR / "shared"

# Crear directorios si no existen
for d in [DATA_DIR, UPTIME_DATA_DIR, SHARED_DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Credenciales SIGMA (desde env vars)
SIGMA_USERNAME = os.getenv("SIGMA_USERNAME")
SIGMA_PASSWORD = os.getenv("SIGMA_PASSWORD")

if not SIGMA_USERNAME or not SIGMA_PASSWORD:
    raise ValueError("Falta SIGMA_USERNAME o SIGMA_PASSWORD en env vars")

# URLs SIGMA
SIGMA_BASE_URL = "https://sigma.redlink.com.ar"
SIGMA_LOGIN_URL = f"{SIGMA_BASE_URL}/monitorhw/pages/login.xhtml"
SIGMA_UPTIME_URL = f"{SIGMA_BASE_URL}/monitorup/pages/vistaOnline.xhtml#protected"

# Configuración Selenium
SELENIUM_HEADLESS = True
SELENIUM_TIMEOUT = 20
SELENIUM_DOWNLOAD_DIR = "/tmp/sigma_downloads"

# BD
UPTIME_DB_PATH = UPTIME_DATA_DIR / "uptime_sigma.db"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# GitHub Actions
IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS", "false").lower() == "true"
