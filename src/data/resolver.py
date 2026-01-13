"""Resolver de IDs para anti-alucinación.

Este módulo implementa el mecanismo de resolución cuando el LLM
inventa códigos de indicador. Convierte códigos inválidos en
búsquedas y presenta candidatos para selección.
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .ids_cache import get_cache, ensure_cache_loaded, IndicatorInfo
from ..config import logger


@dataclass
class ResolverResult:
    """Resultado de una resolución de ID."""
    success: bool
    resolved_id: Optional[str] = None
    candidates: List[IndicatorInfo] = None
    message: str = ""
    needs_selection: bool = False
    
    def __post_init__(self):
        if self.candidates is None:
            self.candidates = []


def extract_keywords(code: str) -> List[str]:
    """Extrae keywords de un código de indicador.
    
    Convierte códigos como 'POBLACION_SEXOEDAD' en ['poblacion', 'sexo', 'edad'].
    
    Args:
        code: Código del indicador (inventado o real)
        
    Returns:
        Lista de keywords para búsqueda.
    """
    if not code:
        return []
    
    # Normalizar: mayúsculas, reemplazar separadores
    normalized = code.upper()
    
    # Separar por guion bajo
    parts = normalized.split('_')
    
    # Expandir partes que son combinaciones (SEXOEDAD → SEXO, EDAD)
    expanded = []
    common_prefixes = ['SEXO', 'EDAD', 'ISLA', 'MUN', 'REGION', 'HOMBRE', 'MUJER', 'TOTAL']
    
    for part in parts:
        # Intentar separar palabras pegadas
        if len(part) > 6:
            # Buscar prefijos conocidos
            found = False
            for prefix in common_prefixes:
                if part.startswith(prefix) and len(part) > len(prefix):
                    expanded.append(prefix.lower())
                    rest = part[len(prefix):]
                    if rest:
                        expanded.append(rest.lower())
                    found = True
                    break
            if not found:
                expanded.append(part.lower())
        else:
            expanded.append(part.lower())
    
    # Filtrar palabras muy cortas o números
    keywords = [k for k in expanded if len(k) > 2 and not k.isdigit()]
    
    return keywords


def resolve_indicator(
    code: str, 
    limit: int = 10
) -> ResolverResult:
    """Resuelve un código de indicador, buscando candidatos si no existe.
    
    Args:
        code: Código a resolver
        limit: Máximo de candidatos
        
    Returns:
        ResolverResult con candidatos si no existe.
    """
    # Asegurar cache cargado
    cache = ensure_cache_loaded()
    
    # Si existe, éxito directo
    if cache.is_valid(code):
        info = cache.get_info(code)
        return ResolverResult(
            success=True,
            resolved_id=code.upper(),
            message=f"Indicador válido: {info.title}"
        )
    
    # No existe - extraer keywords y buscar
    keywords = extract_keywords(code)
    logger.info(f"Resolviendo '{code}' con keywords: {keywords}")
    
    # Buscar con keywords
    candidates = []
    
    if keywords:
        # Buscar con cada keyword y combinar resultados
        query = " ".join(keywords[:3])  # Máximo 3 keywords
        candidates = cache.search(query, limit=limit)
    
    # Si no hay resultados, buscar similares por código
    if not candidates:
        candidates = cache.find_similar(code, limit=limit)
    
    if not candidates:
        return ResolverResult(
            success=False,
            message=f"No se encontraron indicadores similares a '{code}'. Intenta con otra búsqueda.",
            needs_selection=False
        )
    
    return ResolverResult(
        success=False,
        candidates=candidates,
        message=f"El indicador '{code}' no existe.",
        needs_selection=True
    )


def format_candidates_for_selection(candidates: List[IndicatorInfo]) -> str:
    """Formatea candidatos para presentar al usuario.
    
    Args:
        candidates: Lista de candidatos
        
    Returns:
        Texto formateado con lista numerada.
    """
    lines = [
        "Indicadores encontrados:",
        ""
    ]
    
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}) {c.code:<30} - {c.title[:40]}")
    
    lines.extend([
        "",
        "Elige escribiendo:",
        f"- el número (1–{len(candidates)}), o",
        "- el ID exacto (por ejemplo: {})".format(candidates[0].code if candidates else "POBLACION")
    ])
    
    return "\n".join(lines)


def validate_selection(
    selection: str, 
    candidates: List[IndicatorInfo]
) -> Tuple[bool, Optional[str], str]:
    """Valida una selección (número o ID).
    
    Args:
        selection: Entrada del usuario (número o ID)
        candidates: Lista de candidatos válidos
        
    Returns:
        Tupla (es_válido, id_seleccionado, mensaje)
    """
    if not selection or not candidates:
        return False, None, "Selección vacía"
    
    selection = selection.strip()
    
    # Caso 1: Es un número
    if selection.isdigit():
        num = int(selection)
        if 1 <= num <= len(candidates):
            selected = candidates[num - 1]
            return True, selected.code, f"Seleccionado: {selected.code} - {selected.title}"
        else:
            return False, None, f"Número fuera de rango. Elige entre 1 y {len(candidates)}."
    
    # Caso 2: Es un ID exacto
    selection_upper = selection.upper()
    for c in candidates:
        if c.code == selection_upper:
            return True, c.code, f"Seleccionado: {c.code} - {c.title}"
    
    # No coincide con nada
    valid_ids = [c.code for c in candidates[:5]]
    return False, None, f"El valor '{selection}' no coincide con ninguna opción. IDs válidos: {', '.join(valid_ids)}"


@dataclass
class SelectionState:
    """Estado de una selección pendiente.
    
    Se usa para rastrear intentos y candidatos.
    """
    candidates: List[IndicatorInfo]
    attempts: int = 0
    max_attempts: int = 2
    context: str = ""  # Para qué se necesita el ID
    
    def can_retry(self) -> bool:
        return self.attempts < self.max_attempts
    
    def record_attempt(self) -> None:
        self.attempts += 1


# Estado global de selección pendiente (por simplicidad)
_pending_selection: Optional[SelectionState] = None


def start_selection(candidates: List[IndicatorInfo], context: str = "") -> str:
    """Inicia un proceso de selección.
    
    Args:
        candidates: Candidatos a mostrar
        context: Contexto (ej: "para get_indicator_data")
        
    Returns:
        Mensaje formateado para el usuario.
    """
    global _pending_selection
    _pending_selection = SelectionState(
        candidates=candidates,
        context=context
    )
    
    return format_candidates_for_selection(candidates)


def process_selection(user_input: str) -> Tuple[bool, Optional[str], str]:
    """Procesa una selección del usuario.
    
    Args:
        user_input: Entrada del usuario
        
    Returns:
        Tupla (completado, id_seleccionado, mensaje)
    """
    global _pending_selection
    
    if _pending_selection is None:
        return False, None, "No hay selección pendiente"
    
    _pending_selection.record_attempt()
    
    valid, selected_id, message = validate_selection(
        user_input, 
        _pending_selection.candidates
    )
    
    if valid:
        _pending_selection = None  # Limpiar estado
        return True, selected_id, message
    
    if not _pending_selection.can_retry():
        _pending_selection = None
        return False, None, "Máximo de intentos alcanzado. Usa '/indicadores' para buscar de nuevo."
    
    return False, None, message + f" ({_pending_selection.max_attempts - _pending_selection.attempts} intentos restantes)"


def has_pending_selection() -> bool:
    """Verifica si hay una selección pendiente."""
    return _pending_selection is not None


def cancel_selection() -> None:
    """Cancela la selección pendiente."""
    global _pending_selection
    _pending_selection = None
