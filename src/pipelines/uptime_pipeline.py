"""
src/pipelines/uptime_pipeline.py
Orquestador del pipeline de Uptime
Independiente de ATM, ejecutable de forma autónoma
"""

import sys
from datetime import datetime
from src.shared.logger import get_logger
from src.extractors.uptime.sigma_uptime_extractor import SigmaUptimeExtractor
from src.extractors.uptime.consolidator import UptimeConsolidator

logger = get_logger(__name__)


def run_uptime_pipeline(target_date=None):
    """
    Ejecuta pipeline completo de Uptime:
    1. Extrae datos de SIGMA
    2. Consolida para Power BI
    
    Args:
        target_date: fecha a descargar (default: día anterior)
    
    Returns:
        bool: True si exitoso
    """
    
    logger.info("=" * 60)
    logger.info("SIGMA UPTIME PIPELINE")
    logger.info("=" * 60)
    
    success = False
    
    try:
        # Paso 1: Extracción
        logger.info("\n[1/2] Iniciando EXTRACCIÓN desde SIGMA...")
        extractor = SigmaUptimeExtractor(headless=True)
        
        if extractor.extract(target_date=target_date):
            logger.info("✓ Extracción completada")
        else:
            logger.error("✗ Error en extracción")
            return False
        
        # Paso 2: Consolidación
        logger.info("\n[2/2] Iniciando CONSOLIDACIÓN para Power BI...")
        consolidator = UptimeConsolidator()
        
        if consolidator.consolidate():
            logger.info("✓ Consolidación completada")
            success = True
        else:
            logger.error("✗ Error en consolidación")
            return False
        
    except Exception as e:
        logger.error(f"Error en pipeline: {e}", exc_info=True)
        return False
    
    finally:
        logger.info("\n" + "=" * 60)
        if success:
            logger.info("✓ PIPELINE UPTIME: EXITOSO")
        else:
            logger.error("✗ PIPELINE UPTIME: FALLÓ")
        logger.info("=" * 60)
    
    return success


if __name__ == "__main__":
    # Ejecutable desde línea de comandos
    success = run_uptime_pipeline()
    sys.exit(0 if success else 1)
