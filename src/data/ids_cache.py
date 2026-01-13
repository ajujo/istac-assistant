"""Cache de IDs válidos del ISTAC.

Este módulo mantiene un cache de indicadores conocidos para validar
que los códigos usados por el LLM realmente existen.
"""

from typing import Dict, List, Optional, Set
import threading
from dataclasses import dataclass, field
from difflib import get_close_matches

from ..config import logger


@dataclass
class IndicatorInfo:
    """Información básica de un indicador."""
    code: str
    title: str
    subject: str = ""


class IndicatorCache:
    """Cache de indicadores conocidos.
    
    Este cache se carga al inicio y permite validar códigos
    antes de hacer llamadas a la API.
    """
    
    def __init__(self):
        self._indicators: Dict[str, IndicatorInfo] = {}
        self._codes: Set[str] = set()
        self._loaded = False
        self._from_tsv = False  # Si cargó desde TSV, es inmutable
        self._lock = threading.Lock()
    
    @staticmethod
    def normalize_code(code: str) -> str:
        """Normaliza un código de indicador.
        
        Quita tildes, convierte a mayúsculas.
        POBLACIÓN → POBLACION
        """
        import unicodedata
        
        # Quitar tildes
        normalized = unicodedata.normalize('NFD', code)
        normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        
        return normalized.upper().strip()
    
    def load(self, indicators: List[Dict], from_tsv: bool = False) -> None:
        """Carga indicadores en el cache.
        
        Args:
            indicators: Lista de indicadores con 'code', 'title', 'subject'
            from_tsv: Si True, marca como carga desde TSV (inmutable)
        """
        with self._lock:
            # Si ya cargamos desde TSV, no sobrescribir
            if self._from_tsv and not from_tsv:
                logger.debug("Cache ya cargado desde TSV, ignorando carga parcial")
                return
            
            for ind in indicators:
                code_raw = ind.get("code", "")
                code = self.normalize_code(code_raw)
                if code:
                    self._indicators[code] = IndicatorInfo(
                        code=code,
                        title=ind.get("title", ""),
                        subject=ind.get("subject", "")
                    )
                    self._codes.add(code)
            
            self._loaded = True
            if from_tsv:
                self._from_tsv = True
            logger.info(f"Cache cargado con {len(self._codes)} indicadores")
    
    def is_loaded(self) -> bool:
        """Verifica si el cache está cargado."""
        return self._loaded
    
    def is_valid(self, code: str) -> bool:
        """Verifica si un código de indicador existe.
        
        Args:
            code: Código del indicador (normalizado automáticamente)
            
        Returns:
            True si el código existe en el cache.
        """
        normalized = self.normalize_code(code)
        return normalized in self._codes
    
    def get_info(self, code: str) -> Optional[IndicatorInfo]:
        """Obtiene información de un indicador.
        
        Args:
            code: Código del indicador
            
        Returns:
            IndicatorInfo o None si no existe.
        """
        return self._indicators.get(code.upper())
    
    def find_similar(self, code: str, limit: int = 5) -> List[IndicatorInfo]:
        """Busca indicadores similares a un código dado.
        
        Útil para sugerir alternativas cuando el LLM inventa un código.
        
        Args:
            code: Código a buscar
            limit: Máximo de sugerencias
            
        Returns:
            Lista de indicadores similares.
        """
        code_upper = code.upper()
        
        # Primero buscar por match parcial en código
        matches = []
        for known_code in self._codes:
            if code_upper in known_code or known_code in code_upper:
                matches.append(self._indicators[known_code])
        
        # Si no hay matches, usar difflib
        if not matches:
            similar_codes = get_close_matches(
                code_upper, 
                list(self._codes), 
                n=limit, 
                cutoff=0.4
            )
            matches = [self._indicators[c] for c in similar_codes]
        
        return matches[:limit]
    
    def search(self, query: str, limit: int = 10) -> List[IndicatorInfo]:
        """Busca indicadores por texto en título o código.
        
        Args:
            query: Texto a buscar
            limit: Máximo de resultados
            
        Returns:
            Lista de indicadores que coinciden.
        """
        query_lower = query.lower()
        results = []
        
        for info in self._indicators.values():
            if (query_lower in info.code.lower() or 
                query_lower in info.title.lower() or
                query_lower in info.subject.lower()):
                results.append(info)
                if len(results) >= limit:
                    break
        
        return results
    
    def all_codes(self) -> List[str]:
        """Devuelve todos los códigos conocidos."""
        return list(self._codes)
    
    def count(self) -> int:
        """Número de indicadores en cache."""
        return len(self._codes)


# =============================================================================
# SINGLETON
# =============================================================================

_cache: Optional[IndicatorCache] = None

def get_cache() -> IndicatorCache:
    """Obtiene la instancia singleton del cache."""
    global _cache
    if _cache is None:
        _cache = IndicatorCache()
    return _cache


def load_cache_from_api() -> IndicatorCache:
    """Carga el cache desde la API del ISTAC.
    
    Returns:
        Cache cargado.
    """
    from .istac_api import get_client
    
    cache = get_cache()
    if cache.is_loaded():
        return cache
    
    try:
        client = get_client()
        # Cargar todos los indicadores (hasta 500)
        indicators = client.search_indicators("", limit=500)
        cache.load(indicators)
    except Exception as e:
        logger.error(f"Error cargando cache: {e}")
    
    return cache


def load_cache_from_tsv(filepath: str = None) -> IndicatorCache:
    """Carga el cache desde un archivo TSV de indicadores.
    
    Este método es preferido porque carga la lista REAL de indicadores
    exportada directamente del ISTAC.
    
    Args:
        filepath: Ruta al archivo TSV (por defecto tests/Indicadores_actuales.tsv)
        
    Returns:
        Cache cargado.
    """
    import csv
    from pathlib import Path
    
    cache = get_cache()
    if cache.is_loaded():
        return cache
    
    # Ruta por defecto
    if filepath is None:
        # Buscar en la raíz del proyecto
        project_root = Path(__file__).parent.parent.parent
        filepath = project_root / "tests" / "Indicadores_actuales.tsv"
    
    filepath = Path(filepath)
    if not filepath.exists():
        logger.warning(f"Archivo TSV no encontrado: {filepath}")
        return load_cache_from_api()  # Fallback a API
    
    try:
        indicators = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                code = row.get('code', '').strip()
                title = row.get('production-title#es', '').strip()
                if code and code.upper() != 'CODE':  # Ignorar header
                    indicators.append({
                        'code': code,
                        'title': title,
                        'subject': ''
                    })
        
        if indicators:
            # Marcar como carga desde TSV (inmutable)
            cache.load(indicators, from_tsv=True)
            logger.info(f"Cache cargado desde TSV con {len(indicators)} indicadores")
        else:
            logger.warning("TSV vacío, cargando desde API")
            return load_cache_from_api()
            
    except Exception as e:
        logger.error(f"Error cargando TSV: {e}")
        return load_cache_from_api()
    
    return cache


def ensure_cache_loaded() -> IndicatorCache:
    """Asegura que el cache esté cargado, preferentemente desde TSV.
    
    Returns:
        Cache cargado.
    """
    cache = get_cache()
    if not cache.is_loaded():
        # Intentar primero desde TSV (más confiable)
        cache = load_cache_from_tsv()
    return cache
