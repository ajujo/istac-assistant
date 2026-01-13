"""Validador de códigos y respuestas del ISTAC.

Este módulo implementa la validación "dura" que hace el sistema
independiente del modelo LLM:
- Pre-validación de códigos de indicadores
- Post-validación de respuestas con trazabilidad
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

from .ids_cache import get_cache, ensure_cache_loaded, IndicatorInfo
from ..config import logger


@dataclass
class ValidationResult:
    """Resultado de una validación."""
    is_valid: bool
    message: str
    suggestions: List[IndicatorInfo] = None
    
    def __post_init__(self):
        if self.suggestions is None:
            self.suggestions = []


class IndicatorValidator:
    """Validador de códigos de indicadores.
    
    Valida que los códigos usados realmente existen antes de
    hacer llamadas a la API. Si no existe, sugiere alternativas.
    """
    
    def __init__(self, auto_load: bool = True):
        """Inicializa el validador.
        
        Args:
            auto_load: Si cargar cache automáticamente
        """
        self._cache = get_cache()
        if auto_load and not self._cache.is_loaded():
            ensure_cache_loaded()  # Prefiere TSV
    
    def validate_code(self, code: str) -> ValidationResult:
        """Valida un código de indicador.
        
        Args:
            code: Código a validar
            
        Returns:
            ValidationResult con is_valid y posibles sugerencias.
        """
        if not code:
            return ValidationResult(
                is_valid=False,
                message="Código vacío"
            )
        
        code_upper = code.upper()
        
        # Verificar si existe
        if self._cache.is_valid(code_upper):
            info = self._cache.get_info(code_upper)
            return ValidationResult(
                is_valid=True,
                message=f"Indicador válido: {info.title}"
            )
        
        # No existe - buscar similares
        suggestions = self._cache.find_similar(code_upper, limit=5)
        
        if suggestions:
            suggestion_names = [f"'{s.code}' ({s.title[:30]}...)" for s in suggestions[:3]]
            message = f"El indicador '{code}' no existe. ¿Te refieres a: {', '.join(suggestion_names)}?"
        else:
            message = f"El indicador '{code}' no existe y no se encontraron alternativas similares."
        
        return ValidationResult(
            is_valid=False,
            message=message,
            suggestions=suggestions
        )
    
    def resolve_code(self, code: str) -> Tuple[bool, str, str]:
        """Intenta resolver un código, devolviendo el correcto o error.
        
        Args:
            code: Código a resolver
            
        Returns:
            Tupla (success, resolved_code, message)
        """
        result = self.validate_code(code)
        
        if result.is_valid:
            return True, code.upper(), result.message
        
        # Si hay exactamente 1 sugerencia muy similar, auto-resolver
        if len(result.suggestions) == 1:
            suggested = result.suggestions[0]
            logger.info(f"Auto-resolviendo '{code}' → '{suggested.code}'")
            return True, suggested.code, f"Resuelto a '{suggested.code}': {suggested.title}"
        
        return False, code, result.message
    
    def ensure_cache_loaded(self) -> bool:
        """Asegura que el cache esté cargado."""
        if not self._cache.is_loaded():
            load_cache_from_api()
        return self._cache.is_loaded()


class ResponseValidator:
    """Validador de respuestas del LLM.
    
    Verifica que las respuestas con datos numéricos incluyan
    trazabilidad obligatoria.
    """
    
    # Marcadores requeridos para trazabilidad
    REQUIRED_MARKERS = [
        "📌",  # Al menos un marcador de trazabilidad
    ]
    
    TRAZA_KEYWORDS = [
        "Fuente",
        "Indicador",
        "Código",
        "Periodo",
    ]
    
    def validate_response(self, response: str, has_data: bool = False) -> ValidationResult:
        """Valida que una respuesta tenga trazabilidad si contiene datos.
        
        Args:
            response: Respuesta del LLM
            has_data: Si la respuesta contiene datos numéricos
            
        Returns:
            ValidationResult
        """
        if not has_data:
            return ValidationResult(is_valid=True, message="Sin datos, no requiere trazabilidad")
        
        # Verificar presencia de marcadores
        has_markers = any(marker in response for marker in self.REQUIRED_MARKERS)
        
        if not has_markers:
            return ValidationResult(
                is_valid=False,
                message="La respuesta contiene datos pero NO tiene trazabilidad obligatoria."
            )
        
        # Verificar keywords de trazabilidad
        traza_count = sum(1 for kw in self.TRAZA_KEYWORDS if kw in response)
        
        if traza_count < 2:
            return ValidationResult(
                is_valid=False,
                message=f"Trazabilidad incompleta (solo {traza_count}/4 campos)."
            )
        
        return ValidationResult(
            is_valid=True,
            message="Respuesta con trazabilidad válida"
        )
    
    def response_has_numbers(self, response: str) -> bool:
        """Detecta si una respuesta contiene datos numéricos relevantes.
        
        Args:
            response: Respuesta a analizar
            
        Returns:
            True si contiene números que parecen datos estadísticos.
        """
        import re
        
        # Buscar patrones numéricos típicos de datos estadísticos
        patterns = [
            r'\d{1,3}(?:\.\d{3})+',  # Números con separador de miles (1.234.567)
            r'\d+(?:,\d+)?%',        # Porcentajes
            r'\d{4,}',               # Números grandes (>= 1000)
        ]
        
        for pattern in patterns:
            if re.search(pattern, response):
                return True
        
        return False


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def validate_indicator(code: str) -> ValidationResult:
    """Valida un código de indicador."""
    validator = IndicatorValidator()
    return validator.validate_code(code)


def validate_response(response: str) -> ValidationResult:
    """Valida una respuesta del LLM."""
    rv = ResponseValidator()
    has_numbers = rv.response_has_numbers(response)
    return rv.validate_response(response, has_numbers)


def resolve_indicator(code: str) -> Tuple[bool, str, str]:
    """Resuelve un código de indicador."""
    validator = IndicatorValidator()
    return validator.resolve_code(code)
