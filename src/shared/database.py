"""
database.py — Clase base para manejar BDs SQLite
Reutilizable por Uptime, Terminal, Transacciones, etc.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from .logger import get_logger

logger = get_logger(__name__)


class SigmaDatabase:
    """
    Clase base para BD SQLite de SIGMA
    Cada extractor (uptime, terminal, etc.) hereda de esta
    """
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.connect()
    
    def connect(self):
        """Conecta a la BD"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            logger.info(f"Conectado a BD: {self.db_path}")
        except Exception as e:
            logger.error(f"Error conectando a BD: {e}")
            raise
    
    def execute(self, query: str, params: tuple = None):
        """Ejecuta un query (INSERT, UPDATE, DELETE)"""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Error ejecutando query: {e}")
            self.conn.rollback()
            raise
    
    def fetch_all(self, query: str, params: tuple = None) -> List[tuple]:
        """Obtiene todos los resultados"""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error obteniendo resultados: {e}")
            raise
    
    def fetch_one(self, query: str, params: tuple = None) -> tuple:
        """Obtiene un resultado"""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error obteniendo resultado: {e}")
            raise
    
    def read_to_dataframe(self, query: str) -> pd.DataFrame:
        """Retorna query como DataFrame (útil para procesamiento)"""
        try:
            df = pd.read_sql_query(query, self.conn)
            logger.info(f"DataFrame cargado: {len(df)} filas")
            return df
        except Exception as e:
            logger.error(f"Error leyendo a DataFrame: {e}")
            raise
    
    def insert_from_dataframe(self, df: pd.DataFrame, table_name: str, if_exists='append'):
        """
        Inserta un DataFrame en una tabla
        if_exists: 'append' | 'replace' | 'fail'
        """
        try:
            df.to_sql(table_name, self.conn, if_exists=if_exists, index=False)
            logger.info(f"DataFrame insertado en tabla '{table_name}': {len(df)} filas")
        except Exception as e:
            logger.error(f"Error insertando DataFrame: {e}")
            raise
    
    def create_index(self, table: str, column: str, index_name: str = None):
        """Crea índice en una columna"""
        if not index_name:
            index_name = f"idx_{table}_{column}"
        
        query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})"
        try:
            self.execute(query)
            logger.info(f"Índice creado: {index_name}")
        except Exception as e:
            logger.warning(f"No se pudo crear índice: {e}")
    
    def get_summary(self, table: str) -> Dict[str, Any]:
        """Retorna resumen básico de una tabla"""
        try:
            query = f"""
                SELECT 
                    COUNT(*) as total_filas,
                    (SELECT COUNT(DISTINCT DATE(SUBSTR(fecha, 1, 10))) FROM {table} LIMIT 1) as dias_unicos
                FROM {table}
            """
            result = self.fetch_one(query)
            return {
                'total_filas': result[0] if result else 0,
                'dias_unicos': result[1] if result else 0
            }
        except Exception as e:
            logger.warning(f"Error obteniendo resumen: {e}")
            return {}
    
    def close(self):
        """Cierra conexión"""
        if self.conn:
            self.conn.close()
            logger.info("Conexión BD cerrada")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
