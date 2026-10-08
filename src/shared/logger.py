"""
logger.py — Logging centralizado
Todos los extractores importan desde aquí
"""

import logging
from pathlib import Path
from .config import LOG_LEVEL, LOG_DIR

def get_logger(name):
    """
    Retorna logger configurado con formato estándar
    
    Uso:
        from src.shared.logger import get_logger
        logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)
    
    # Evitar handlers duplicados
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Formato estándar
    formatter = logging.Formatter(
        '[%(asctime)s] %(name)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler: consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler: archivo (en logs/)
    log_file = LOG_DIR / f"{name.split('.')[-1]}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
