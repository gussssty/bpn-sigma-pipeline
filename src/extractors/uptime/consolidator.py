"""
src/extractors/uptime/consolidator.py
Consolida datos de Uptime para Power BI
"""

import pandas as pd
from pathlib import Path
from src.shared.logger import get_logger
from src.shared.database import SigmaDatabase
from src.shared.config import UPTIME_DB_PATH, UPTIME_DATA_DIR

logger = get_logger(__name__)


class UptimeConsolidator:
    """Consolida datos de Uptime desde BD para Power BI"""
    
    def __init__(self, db_path: str = None, output_dir: str = None):
        self.db_path = db_path or str(UPTIME_DB_PATH)
        self.output_dir = Path(output_dir or UPTIME_DATA_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.db = SigmaDatabase(self.db_path)
    
    def consolidate(self):
        """Ejecuta consolidación completa"""
        logger.info("=== Iniciando consolidación para Power BI ===")
        
        try:
            # 1. Tabla de hechos horaria
            fact_df = self._create_fact_uptime_horario()
            
            # 2. Resumen diario
            daily_df = self._create_resumen_diario()
            
            # 3. Exportar CSVs
            self._export_csvs(fact_df, daily_df)
            
            # 4. Generar metadatos
            self._generate_metadata()
            
            logger.info("=== Consolidación completada ===")
            return True
            
        except Exception as e:
            logger.error(f"Error en consolidación: {e}", exc_info=True)
            return False
        
        finally:
            self.db.close()
    
    def _create_fact_uptime_horario(self) -> pd.DataFrame:
        """Crea tabla de hechos: uptime por hora"""
        logger.info("Creando tabla de hechos horaria...")
        
        query = """
            SELECT 
                fecha,
                hora,
                uptime_porcentaje,
                fecha_descarga
            FROM uptime_por_hora
            ORDER BY fecha, hora
        """
        
        df = self.db.read_to_dataframe(query)
        
        # Agregar columnas derivadas
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['año'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['semana'] = df['fecha'].dt.isocalendar().week
        df['dia'] = df['fecha'].dt.day
        df['dia_semana'] = df['fecha'].dt.day_name()
        
        # Categorizar (semáforo)
        df['uptime_categoria'] = df['uptime_porcentaje'].apply(self._categorize_uptime)
        
        # Reordenar
        df = df[['fecha', 'año', 'mes', 'semana', 'dia', 'dia_semana', 'hora', 
                 'uptime_porcentaje', 'uptime_categoria', 'fecha_descarga']]
        
        logger.info(f"Tabla de hechos: {len(df)} registros")
        return df
    
    def _create_resumen_diario(self) -> pd.DataFrame:
        """Crea resumen diario agregado"""
        logger.info("Creando resumen diario...")
        
        query = """
            SELECT 
                fecha,
                ROUND(AVG(uptime_porcentaje), 2) as uptime_promedio,
                MIN(uptime_porcentaje) as uptime_minimo,
                MAX(uptime_porcentaje) as uptime_maximo,
                ROUND(STDEV(uptime_porcentaje), 2) as uptime_desv_est
            FROM uptime_por_hora
            GROUP BY fecha
            ORDER BY fecha
        """
        
        df = self.db.read_to_dataframe(query)
        
        # Conversión de tipos
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['año'] = df['fecha'].dt.year
        df['mes'] = df['fecha'].dt.month
        df['semana'] = df['fecha'].dt.isocalendar().week
        
        # Categoría
        df['uptime_categoria'] = df['uptime_promedio'].apply(self._categorize_uptime)
        
        # Reordenar
        df = df[['fecha', 'año', 'mes', 'semana', 'uptime_promedio', 'uptime_minimo', 
                 'uptime_maximo', 'uptime_desv_est', 'uptime_categoria']]
        
        logger.info(f"Resumen diario: {len(df)} días")
        return df
    
    def _categorize_uptime(self, value: float) -> str:
        """Categoriza uptime en semáforo"""
        if value >= 90:
            return 'Verde'
        elif value >= 70:
            return 'Amarillo'
        else:
            return 'Rojo'
    
    def _export_csvs(self, fact_df: pd.DataFrame, daily_df: pd.DataFrame):
        """Exporta DataFrames a CSVs"""
        logger.info("Exportando CSVs...")
        
        # Tabla de hechos
        fact_path = self.output_dir / "uptime_consolidado.csv"
        fact_df.to_csv(fact_path, index=False)
        logger.info(f"Exportado: {fact_path}")
        
        # Resumen diario
        daily_path = self.output_dir / "uptime_diario_resumen.csv"
        daily_df.to_csv(daily_path, index=False)
        logger.info(f"Exportado: {daily_path}")
    
    def _generate_metadata(self):
        """Genera metadatos JSON para documentación"""
        import json
        
        logger.info("Generando metadatos...")
        
        metadata = {
            "model": {
                "tables": [
                    {
                        "name": "fact_uptime_horario",
                        "description": "Uptime consolidado por hora desde SIGMA Monitor de Uptime",
                        "columns": [
                            {"name": "fecha", "type": "Date"},
                            {"name": "hora", "type": "Integer"},
                            {"name": "uptime_porcentaje", "type": "Decimal"},
                            {"name": "uptime_categoria", "type": "Text"},
                            {"name": "año", "type": "Integer"},
                            {"name": "mes", "type": "Integer"},
                            {"name": "semana", "type": "Integer"},
                            {"name": "dia_semana", "type": "Text"},
                        ],
                        "key_columns": ["fecha", "hora"]
                    },
                    {
                        "name": "fact_uptime_diario",
                        "description": "Resumen diario de uptime",
                        "columns": [
                            {"name": "fecha", "type": "Date"},
                            {"name": "uptime_promedio", "type": "Decimal"},
                            {"name": "uptime_minimo", "type": "Decimal"},
                            {"name": "uptime_maximo", "type": "Decimal"},
                            {"name": "uptime_desv_est", "type": "Decimal"},
                            {"name": "uptime_categoria", "type": "Text"},
                        ],
                        "key_columns": ["fecha"]
                    }
                ]
            }
        }
        
        metadata_path = self.output_dir / "uptime_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadatos: {metadata_path}")
    
    def close(self):
        if self.db:
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
