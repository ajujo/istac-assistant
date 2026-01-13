"""Sistema de internacionalización simple para ISTAC Data Assistant.

Uso:
    from src.i18n import t, set_language, get_language

    # Cambiar idioma
    set_language('en')

    # Obtener traducción
    print(t('welcome'))  # "Welcome to the ISTAC Data Assistant!"
    print(t('menu.chat'))  # "Chat with assistant"
    
    # Con variables
    print(t('limits.max_rows_exceeded', limit=1000, shown=100))
"""

import json
from pathlib import Path
from typing import Any, Optional

# Directorio de traducciones
_I18N_DIR = Path(__file__).parent

# Idioma actual y traducciones cargadas
_current_language: str = 'es'
_translations: dict = {}
_fallback_translations: dict = {}  # Siempre español como fallback


def _load_translations(lang: str) -> dict:
    """Carga las traducciones de un idioma."""
    file_path = _I18N_DIR / f'{lang}.json'
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def set_language(lang: str) -> bool:
    """Establece el idioma actual.
    
    Args:
        lang: Código de idioma ('es', 'en', etc.)
    
    Returns:
        True si el idioma se cargó correctamente.
    """
    global _current_language, _translations, _fallback_translations
    
    translations = _load_translations(lang)
    if translations:
        _current_language = lang
        _translations = translations
        
        # Cargar fallback si no es español
        if lang != 'es':
            _fallback_translations = _load_translations('es')
        else:
            _fallback_translations = {}
        
        return True
    return False


def get_language() -> str:
    """Devuelve el idioma actual."""
    return _current_language


def get_available_languages() -> list:
    """Devuelve los idiomas disponibles."""
    return [f.stem for f in _I18N_DIR.glob('*.json')]


def t(key: str, **kwargs: Any) -> str:
    """Obtiene una traducción por su clave.
    
    Args:
        key: Clave de traducción, puede usar puntos para anidamiento (ej: 'menu.chat')
        **kwargs: Variables para sustituir en la traducción
    
    Returns:
        Texto traducido o la clave si no se encuentra.
    
    Example:
        >>> t('welcome')
        '¡Bienvenido al Asistente de Datos del ISTAC!'
        >>> t('limits.max_rows_exceeded', limit=1000, shown=100)
        'El dataset supera el límite de 1000 filas. Se muestran las primeras 100.'
    """
    # Inicializar traducciones si es necesario
    if not _translations:
        set_language(_current_language)
    
    # Buscar en las traducciones actuales
    value = _get_nested_value(_translations, key)
    
    # Si no se encuentra, buscar en fallback
    if value is None and _fallback_translations:
        value = _get_nested_value(_fallback_translations, key)
    
    # Si aún no se encuentra, devolver la clave
    if value is None:
        return key
    
    # Sustituir variables
    if kwargs:
        try:
            value = value.format(**kwargs)
        except KeyError:
            pass
    
    return value


def _get_nested_value(d: dict, key: str) -> Optional[str]:
    """Obtiene un valor anidado de un diccionario usando notación de puntos."""
    keys = key.split('.')
    value = d
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return None
    
    return value if isinstance(value, str) else None


# Inicializar con español por defecto
set_language('es')
