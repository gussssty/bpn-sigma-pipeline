"""
selenium_driver.py — Driver Selenium reutilizable
Todos los extractores usan esto en lugar de crear su propio driver
"""

import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .logger import get_logger
from .config import SELENIUM_HEADLESS, SELENIUM_TIMEOUT, SIGMA_LOGIN_URL, SIGMA_USERNAME, SIGMA_PASSWORD

logger = get_logger(__name__)


class SigmaSeleniumDriver:
    """
    Inicializa y gestiona driver Selenium para SIGMA
    Reutilizable por múltiples extractores
    """
    
    def __init__(self, headless: bool = SELENIUM_HEADLESS, download_dir: str = None):
        self.headless = headless
        self.download_dir = download_dir or "/tmp/sigma_downloads"
        self.driver = None
        self.wait = None
        self.initialize()
    
    def initialize(self):
        """Inicializa el driver"""
        os.makedirs(self.download_dir, exist_ok=True)
        
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Configurar descargas
        prefs = {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "safebrowsing.enabled": False,
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)
            logger.info("Driver Selenium inicializado")
        except Exception as e:
            logger.error(f"Error inicializando Selenium: {e}")
            raise
    
    def login(self, username: str = None, password: str = None):
        """
        Autentica en SIGMA
        Si no se pasan credenciales, usa las de env vars
        """
        username = username or SIGMA_USERNAME
        password = password or SIGMA_PASSWORD
        
        logger.info(f"Iniciando login en {SIGMA_LOGIN_URL}")
        
        try:
            self.driver.get(SIGMA_LOGIN_URL)
            
            # Usuario
            username_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "loginForm:username"))
            )
            username_field.send_keys(username)
            
            # Contraseña
            password_field = self.driver.find_element(By.ID, "loginForm:password")
            password_field.send_keys(password)
            
            # Login
            login_btn = self.driver.find_element(By.ID, "loginForm:btnLogin")
            login_btn.click()
            
            time.sleep(3)
            logger.info("Login exitoso")
            return True
            
        except Exception as e:
            logger.error(f"Error en login: {e}")
            return False
    
    def navigate_to_url(self, url: str, wait_for_element_id: str = None):
        """Navega a URL y espera elemento opcional"""
        logger.info(f"Navegando a {url}")
        try:
            self.driver.get(url)
            
            if wait_for_element_id:
                self.wait.until(EC.presence_of_element_located((By.ID, wait_for_element_id)))
            
            time.sleep(2)
            logger.info("Navegación completada")
            return True
            
        except Exception as e:
            logger.error(f"Error navegando: {e}")
            return False
    
    def click_element(self, by: By, value: str, wait_clickable: bool = True):
        """Click en elemento"""
        try:
            if wait_clickable:
                element = self.wait.until(EC.element_to_be_clickable((by, value)))
            else:
                element = self.driver.find_element(by, value)
            
            element.click()
            return True
        except Exception as e:
            logger.error(f"Error haciendo click: {e}")
            return False
    
    def fill_field(self, by: By, value: str, text: str):
        """Rellena un campo de texto"""
        try:
            field = self.wait.until(EC.presence_of_element_located((by, value)))
            field.clear()
            field.send_keys(text)
            return True
        except Exception as e:
            logger.error(f"Error rellenando campo: {e}")
            return False
    
    def wait_for_download(self, timeout: int = 10):
        """Espera a que se complete una descarga"""
        import glob
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            files = glob.glob(os.path.join(self.download_dir, "*"))
            # Archivos que NO son .crdownload (descarga incompleta)
            completed = [f for f in files if not f.endswith('.crdownload')]
            if completed:
                return completed[-1]  # Último archivo completado
            time.sleep(0.5)
        
        logger.warning(f"Timeout esperando descarga después de {timeout}s")
        return None
    
    def get_latest_download(self):
        """Retorna el archivo descargado más reciente"""
        import glob
        files = glob.glob(os.path.join(self.download_dir, "*"))
        completed = [f for f in files if not f.endswith('.crdownload')]
        
        if completed:
            return max(completed, key=os.path.getctime)
        return None
    
    def close(self):
        """Cierra el driver"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver Selenium cerrado")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
