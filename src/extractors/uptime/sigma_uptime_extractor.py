"""
src/extractors/uptime/sigma_uptime_extractor.py
Extractor de Monitor de Uptime desde SIGMA
INDEPENDIENTE DE ATM — usa módulos compartidos
"""

import time
import pandas as pd
from datetime import datetime, timedelta
from selenium.webdriver.common.by import By

from src.shared.logger import get_logger
from src.shared.selenium_driver import SigmaSeleniumDriver
from src.shared.database import SigmaDatabase
from src.shared.config import SIGMA_UPTIME_URL, UPTIME_DB_PATH

logger = get_logger(__name__)


class SigmaUptimeExtractor:
    """
    Extrae datos de Monitor de Uptime (parciales por hora)
    desde https://sigma.redlink.com.ar/monitorup/pages/vistaOnline.xhtml
    """
    
    def __init__(self, headless: bool = True):
        self.selenium = SigmaSeleniumDriver(headless=headless)
        self.db = SigmaDatabase(str(UPTIME_DB_PATH))
        self._init_db_schema()
    
    def _init_db_schema(self):
        """Crea tabla si no existe"""
        schema = """
            CREATE TABLE IF NOT EXISTS uptime_por_hora (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE NOT NULL,
                hora INTEGER NOT NULL,
                uptime_porcentaje REAL NOT NULL,
                fecha_descarga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fecha, hora)
            )
        """
        self.db.execute(schema)
        self.db.create_index("uptime_por_hora", "fecha", "idx_uptime_fecha")
        self.db.create_index("uptime_por_hora", "fecha, hora", "idx_uptime_fecha_hora")
        logger.info("Esquema de BD inicializado")
    
    def extract(self, target_date: datetime = None):
        """
        Flujo principal de extracción
        target_date: fecha a descargar (default: día anterior)
        """
        if target_date is None:
            target_date = datetime.now() - timedelta(days=1)
        
        logger.info(f"=== Iniciando extracción para {target_date.strftime('%Y-%m-%d')} ===")
        
        try:
            # 1. Login
            if not self.selenium.login():
                raise RuntimeError("Login fallido")
            
            # 2. Navegar a Uptime
            if not self.selenium.navigate_to_url(SIGMA_UPTIME_URL):
                raise RuntimeError("No se pudo navegar a Uptime")
            
            # 3. Activar pestaña Consolidado (si es necesario)
            self._activate_consolidado_tab()
            
            # 4. Seleccionar fecha
            self._select_date(target_date)
            
            # 5. Descargar Excel
            excel_file = self._download_excel()
            if not excel_file:
                raise RuntimeError("No se descargó archivo Excel")
            
            logger.info(f"Archivo descargado: {excel_file}")
            
            # 6. Procesar y cargar en BD
            self._process_and_load_excel(excel_file)
            
            logger.info("=== Extracción completada exitosamente ===")
            return True
            
        except Exception as e:
            logger.error(f"Error en extracción: {e}", exc_info=True)
            return False
        
        finally:
            self.close()
    
    def _activate_consolidado_tab(self):
        """Activa pestaña Consolidado si no está activa"""
        try:
            tab = self.selenium.wait.until(
                lambda driver: driver.find_element(By.XPATH, "//a[contains(text(), 'Consolidado')]")
            )
            tab.click()
            time.sleep(2)
            logger.info("Pestaña Consolidado activada")
        except Exception as e:
            logger.warning(f"No se activó Consolidado (puede estar ya activa): {e}")
    
    def _select_date(self, target_date: datetime):
        """Selecciona fecha en el calendar"""
        date_str = target_date.strftime("%d/%m/%Y")
        logger.info(f"Seleccionando fecha: {date_str}")
        
        try:
            # Buscar input de fecha (puede variar según SIGMA)
            date_input = self.selenium.wait.until(
                lambda driver: driver.find_element(By.XPATH, 
                    "//input[contains(@id, 'fecha') or contains(@id, 'date') or contains(@class, 'date')]")
            )
            
            date_input.clear()
            date_input.send_keys(date_str)
            date_input.send_keys("\n")
            
            time.sleep(2)
            logger.info(f"Fecha seleccionada: {date_str}")
            
        except Exception as e:
            logger.error(f"Error seleccionando fecha: {e}")
            raise
    
    def _download_excel(self, timeout: int = 10):
        """Descarga el Excel"""
        logger.info("Descargando Excel...")
        
        try:
            # Click en botón Descargar
            self.selenium.click_element(
                By.XPATH, 
                "//button[contains(text(), 'Descargar')] | //a[contains(text(), 'Descargar')]"
            )
            
            # Esperar descarga
            excel_file = self.selenium.wait_for_download(timeout=timeout)
            if not excel_file:
                excel_file = self.selenium.get_latest_download()
            
            return excel_file
            
        except Exception as e:
            logger.error(f"Error descargando: {e}")
            raise
    
    def _process_and_load_excel(self, excel_file: str):
        """Procesa Excel y carga en BD"""
        logger.info(f"Procesando {excel_file}...")
        
        try:
            # Leer Excel
            df = pd.read_excel(excel_file, sheet_name="parcial_x_hora")
            
            # Validar columnas
            expected_cols = {'hora', 'Uptim', 'dia'}
            if not expected_cols.issubset(df.columns):
                raise ValueError(f"Columnas esperadas: {expected_cols}, encontradas: {set(df.columns)}")
            
            # Renombrar y validar tipos
            df = df.rename(columns={'hora': 'hora', 'Uptim': 'uptime_porcentaje', 'dia': 'fecha'})
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            df['hora'] = df['hora'].astype(int)
            df['uptime_porcentaje'] = df['uptime_porcentaje'].astype(float)
            
            # Insertar en BD
            inserted = 0
            updated = 0
            
            for _, row in df.iterrows():
                try:
                    query = """
                        INSERT INTO uptime_por_hora (fecha, hora, uptime_porcentaje)
                        VALUES (?, ?, ?)
                    """
                    self.db.execute(query, (row['fecha'], row['hora'], row['uptime_porcentaje']))
                    inserted += 1
                except Exception:
                    # UPSERT
                    query = """
                        UPDATE uptime_por_hora 
                        SET uptime_porcentaje = ?, fecha_descarga = CURRENT_TIMESTAMP
                        WHERE fecha = ? AND hora = ?
                    """
                    self.db.execute(query, (row['uptime_porcentaje'], row['fecha'], row['hora']))
                    updated += 1
            
            logger.info(f"Datos cargados: {inserted} nuevos, {updated} actualizados")
            
        except Exception as e:
            logger.error(f"Error procesando Excel: {e}")
            raise
    
    def close(self):
        """Cierra recursos"""
        self.selenium.close()
        self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
