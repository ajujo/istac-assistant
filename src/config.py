"""Configuración global del ISTAC Data Assistant.

Este módulo carga la configuración desde config/settings.yaml
y proporciona acceso a los valores en toda la aplicación.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml


# Rutas base
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config' / 'settings.yaml'
DATA_PATH = PROJECT_ROOT / 'data'
OUTPUT_PATH = PROJECT_ROOT / 'output'

# Configuración cargada
_config: dict = {}


def load_config(config_path: Optional[Path] = None) -> dict:
    """Carga la configuración desde el archivo YAML.
    
    Args:
        config_path: Ruta al archivo de configuración (opcional).
    
    Returns:
        Diccionario con la configuración.
    """
    global _config
    
    path = config_path or CONFIG_PATH
    
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            _config = yaml.safe_load(f) or {}
    else:
        _config = {}
    
    # Expandir variables de entorno
    _expand_env_vars(_config)
    
    return _config


def _expand_env_vars(d: dict) -> None:
    """Expande variables de entorno ${VAR} en los valores."""
    for key, value in d.items():
        if isinstance(value, dict):
            _expand_env_vars(value)
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            d[key] = os.environ.get(env_var, '')


def get(key: str, default: Any = None) -> Any:
    """Obtiene un valor de configuración.
    
    Args:
        key: Clave usando notación de puntos (ej: 'llm.provider')
        default: Valor por defecto si no existe.
    
    Returns:
        El valor de configuración o el default.
    
    Example:
        >>> get('llm.provider')
        'lmstudio'
        >>> get('llm.lmstudio.base_url')
        'http://localhost:1234/v1'
    """
    if not _config:
        load_config()
    
    keys = key.split('.')
    value = _config
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value


def get_llm_config() -> dict:
    """Obtiene la configuración del proveedor LLM actual."""
    provider = get('llm.provider', 'lmstudio')
    return get(f'llm.{provider}', {})


def get_storage_config() -> dict:
    """Obtiene la configuración de almacenamiento."""
    return get('storage', {})


# Cargar configuración al importar
load_config()


# =============================================================================
# Logging
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configura y devuelve el logger principal."""
    log_level = get('logging.level', 'INFO')
    log_file = get('logging.file')
    
    logger = logging.getLogger('istac_assistant')
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Handler de consola
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(console_handler)
    
    # Handler de archivo si está configurado
    if log_file:
        log_path = PROJECT_ROOT / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
    
    return logger


# Logger global
logger = setup_logging()
