"""Módulo de dimensiones para el ISTAC.

Este módulo detecta y procesa las dimensiones de desagregación.
Regla clave: UN INDICADOR ≠ UN DESGLOSE

- Los IDs de indicadores son finitos y cerrados
- isla, municipio, sexo, edad son DIMENSIONES
- El sistema debe detectar cuándo el usuario pide desglose
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass


# =============================================================================
# VOCABULARIO DE DIMENSIONES
# =============================================================================

# Mapeo de palabras a tipos de dimensión
DIMENSION_KEYWORDS = {
    # Geográficas
    'isla': 'GEOGRAPHICAL',
    'islas': 'GEOGRAPHICAL',
    'municipio': 'GEOGRAPHICAL',
    'municipios': 'GEOGRAPHICAL',
    'comarca': 'GEOGRAPHICAL',
    'comarcas': 'GEOGRAPHICAL',
    'provincia': 'GEOGRAPHICAL',
    'provincias': 'GEOGRAPHICAL',
    'canarias': 'GEOGRAPHICAL',
    
    # Sexo
    'sexo': 'SEX',
    'género': 'SEX',
    'hombre': 'SEX',
    'hombres': 'SEX',
    'mujer': 'SEX',
    'mujeres': 'SEX',
    
    # Edad
    'edad': 'AGE',
    'edades': 'AGE',
    'años': 'AGE',
    'grupo de edad': 'AGE',
    'grupos de edad': 'AGE',
    'jóvenes': 'AGE',
    'mayores': 'AGE',
    'niños': 'AGE',
    
    # Temporal
    'año': 'TIME',
    'trimestre': 'TIME',
    'mes': 'TIME',
    'mensual': 'TIME',
    'anual': 'TIME',
    'trimestral': 'TIME',
    
    # Nacionalidad
    'nacionalidad': 'NATIONALITY',
    'extranjero': 'NATIONALITY',
    'extranjeros': 'NATIONALITY',
    'español': 'NATIONALITY',
    'españoles': 'NATIONALITY',
}

# Preposiciones que indican desglose
BREAKDOWN_PREPOSITIONS = {'por', 'según', 'desglosado', 'desagregado', 'distribuido'}


@dataclass
class QueryAnalysis:
    """Resultado del análisis de una consulta."""
    original_query: str
    indicator_query: str          # Query limpia solo con indicador
    dimensions: List[str]         # Dimensiones detectadas
    dimension_types: Set[str]     # Tipos de dimensión
    has_breakdown: bool           # Si pide desglose
    breakdown_phrase: str         # Frase de desglose detectada


def detect_dimensions(text: str) -> Tuple[List[str], Set[str]]:
    """Detecta palabras clave de dimensiones en un texto.
    
    Args:
        text: Texto a analizar
        
    Returns:
        Tupla (lista de dimensiones encontradas, set de tipos)
    """
    text_lower = text.lower()
    dimensions = []
    types = set()
    
    for keyword, dim_type in DIMENSION_KEYWORDS.items():
        if keyword in text_lower:
            dimensions.append(keyword)
            types.add(dim_type)
    
    return dimensions, types


def analyze_query(query: str) -> QueryAnalysis:
    """Analiza una consulta para separar indicador de dimensiones.
    
    Esta es la función clave: detecta cuándo el usuario pide desglose
    y separa el indicador base de las dimensiones.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        QueryAnalysis con indicador y dimensiones separados.
        
    Examples:
        "población por isla" → indicator="población", dimensions=["isla"]
        "turismo por municipio" → indicator="turismo", dimensions=["municipio"]
    """
    query_lower = query.lower()
    original = query
    
    # Detectar si hay frase de desglose
    has_breakdown = False
    breakdown_phrase = ""
    
    for prep in BREAKDOWN_PREPOSITIONS:
        pattern = rf'\b{prep}\b\s+(\w+)'
        match = re.search(pattern, query_lower)
        if match:
            has_breakdown = True
            breakdown_phrase = match.group(0)
            break
    
    # Detectar dimensiones
    dimensions, dimension_types = detect_dimensions(query_lower)
    
    # Construir query limpia (sin dimensiones)
    indicator_query = query_lower
    
    # Remover frases de desglose
    for prep in BREAKDOWN_PREPOSITIONS:
        for dim in dimensions:
            patterns = [
                rf'\b{prep}\s+{dim}\b',
                rf'\b{prep}\s+\w*{dim}\w*\b',
            ]
            for pattern in patterns:
                indicator_query = re.sub(pattern, '', indicator_query)
    
    # Remover dimensiones sueltas
    for dim in dimensions:
        indicator_query = re.sub(rf'\b{dim}\b', '', indicator_query)
    
    # Limpiar espacios extra
    indicator_query = ' '.join(indicator_query.split()).strip()
    
    return QueryAnalysis(
        original_query=original,
        indicator_query=indicator_query,
        dimensions=dimensions,
        dimension_types=dimension_types,
        has_breakdown=has_breakdown,
        breakdown_phrase=breakdown_phrase
    )


# =============================================================================
# DIMENSIONES DISPONIBLES POR INDICADOR
# =============================================================================

# Mapeo de indicadores base a sus dimensiones disponibles
INDICATOR_DIMENSIONS = {
    'POBLACION': {
        'GEOGRAPHICAL': ['isla', 'municipio', 'comarca'],
        'SEX': ['hombres', 'mujeres'],
        'AGE': ['0-14', '15-64', '65+'],
    },
    'TASA_PARO': {
        'GEOGRAPHICAL': ['isla', 'provincia'],
        'SEX': ['hombres', 'mujeres'],
        'AGE': ['16-24', '25-54', '55+'],
    },
    'TURISMO': {
        'GEOGRAPHICAL': ['isla', 'municipio'],
        'TIME': ['mensual', 'trimestral', 'anual'],
    },
    # Se puede expandir dinámicamente desde la API
}


def get_available_dimensions(indicator_code: str) -> Dict[str, List[str]]:
    """Obtiene las dimensiones disponibles para un indicador.
    
    Args:
        indicator_code: Código del indicador
        
    Returns:
        Diccionario con tipos de dimensión y valores disponibles.
    """
    # Primero buscar en mapeo estático
    if indicator_code in INDICATOR_DIMENSIONS:
        return INDICATOR_DIMENSIONS[indicator_code]
    
    # TODO: Obtener dinámicamente desde get_indicator_info
    # Por ahora, devolver dimensiones genéricas
    return {
        'GEOGRAPHICAL': ['isla', 'municipio'],
        'SEX': ['hombres', 'mujeres'],
        'AGE': ['grupos de edad'],
    }


def format_dimensions_message(indicator_code: str, dimensions: Dict[str, List[str]]) -> str:
    """Formatea un mensaje explicando las dimensiones disponibles.
    
    Args:
        indicator_code: Código del indicador
        dimensions: Dimensiones disponibles
        
    Returns:
        Mensaje formateado para el usuario.
    """
    lines = [
        f"El indicador **{indicator_code}** puede desagregarse por:",
        ""
    ]
    
    type_names = {
        'GEOGRAPHICAL': 'Territorio',
        'SEX': 'Sexo',
        'AGE': 'Edad',
        'TIME': 'Periodo',
        'NATIONALITY': 'Nacionalidad',
    }
    
    for dim_type, values in dimensions.items():
        type_name = type_names.get(dim_type, dim_type)
        values_str = ', '.join(values)
        lines.append(f"• **{type_name}**: {values_str}")
    
    lines.extend([
        "",
        "¿Por cuál dimensión quieres verlo?"
    ])
    
    return "\n".join(lines)


def suggest_correct_usage(
    invalid_code: str, 
    base_indicator: str,
    requested_dimension: str
) -> str:
    """Sugiere el uso correcto cuando el usuario pide un indicador inexistente.
    
    Args:
        invalid_code: Código que el usuario/LLM inventó
        base_indicator: Indicador real que debería usar
        requested_dimension: Dimensión que probablemente quería
        
    Returns:
        Mensaje de corrección.
    """
    lines = [
        f"El ISTAC no publica un indicador llamado `{invalid_code}`.",
        "",
        f"Para ver **{base_indicator}** por **{requested_dimension}**, usa:",
        f"```",
        f"get_indicator_data('{base_indicator}', geo='ISLANDS')",
        f"```",
        "",
        "Los indicadores son finitos. Las dimensiones (isla, sexo, edad) son filtros."
    ]
    
    return "\n".join(lines)


# =============================================================================
# B2: VALORES DE DIMENSIÓN (MVP con listas locales)
# =============================================================================

# Códigos geográficos del ISTAC (NUTS-3 estándar Eurostat)
# Formato: ES70 = Canarias, ES70X = Islas
# Fuente: https://ec.europa.eu/eurostat/web/nuts/background
GEO_CODES = {
    # Canarias total (NUTS-2)
    'ES70': 'Canarias',
    
    # Islas (NUTS-3) - Códigos oficiales Eurostat
    'ES703': 'Gran Canaria',
    'ES704': 'Fuerteventura',
    'ES705': 'Lanzarote', 
    'ES706': 'Tenerife',
    'ES707': 'La Palma',
    'ES708': 'La Gomera',
    'ES709': 'El Hierro',
    # Nota: La Graciosa no tiene código NUTS-3 propio, está en Lanzarote (ES705)
}

# Prefijos de municipios por provincia (códigos INE)
MUNICIPIOS_POR_ISLA = {
    '35': 'Las Palmas (Gran Canaria, Fuerteventura, Lanzarote)',
    '38': 'Santa Cruz de Tenerife (Tenerife, La Palma, La Gomera, El Hierro)',
}

# Islas de Canarias con sus códigos (múltiples formatos)
ISLAS_CANARIAS = {
    # nombre_normalizado: (nombre_oficial, código_NUTS3, prefijo_municipios)
    'tenerife': ('Tenerife', 'ES706', '38'),
    'gran canaria': ('Gran Canaria', 'ES703', '35'),
    'grancanaria': ('Gran Canaria', 'ES703', '35'),
    'lanzarote': ('Lanzarote', 'ES705', '35'),
    'fuerteventura': ('Fuerteventura', 'ES704', '35'),
    'la palma': ('La Palma', 'ES707', '38'),
    'lapalma': ('La Palma', 'ES707', '38'),
    'la gomera': ('La Gomera', 'ES708', '38'),
    'lagomera': ('La Gomera', 'ES708', '38'),
    'el hierro': ('El Hierro', 'ES709', '38'),
    'elhierro': ('El Hierro', 'ES709', '38'),
    'hierro': ('El Hierro', 'ES709', '38'),
    'la graciosa': ('La Graciosa', 'ES705', '35'),  # En Lanzarote
    'canarias': ('Canarias', 'ES70', None),
}

# Valores de sexo
SEXO_VALUES = {
    'total': ('Total', 'TOTAL'),
    'hombre': ('Hombres', 'MALE'),
    'hombres': ('Hombres', 'MALE'),
    'mujer': ('Mujeres', 'FEMALE'),
    'mujeres': ('Mujeres', 'FEMALE'),
}

# Granularidades geográficas para la API
GEO_GRANULARITIES = {
    'isla': 'ISLANDS',
    'islas': 'ISLANDS',
    'municipio': 'MUNICIPALITIES',
    'municipios': 'MUNICIPALITIES',
    'comarca': 'COUNTIES',
    'comarcas': 'COUNTIES',
    'provincia': 'PROVINCES',
    'provincias': 'PROVINCES',
    'region': 'REGIONS',
    'comunidad': 'REGIONS',
    'canarias': 'REGIONS',
}


@dataclass
class DimensionValue:
    """Valor de dimensión resuelto."""
    dimension_type: str    # GEOGRAPHICAL, SEX, etc.
    user_input: str        # Lo que escribió el usuario
    resolved_name: str     # Nombre oficial
    api_code: str          # Código para la API
    is_valid: bool


def resolve_island(text: str) -> Optional[DimensionValue]:
    """Resuelve un nombre de isla a su código ISTAC.
    
    Args:
        text: Nombre de la isla (ej: "Tenerife", "gran canaria")
        
    Returns:
        DimensionValue o None si no es una isla.
    """
    text_lower = text.lower().strip()
    
    if text_lower in ISLAS_CANARIAS:
        name, code, _ = ISLAS_CANARIAS[text_lower]
        return DimensionValue(
            dimension_type='GEOGRAPHICAL',
            user_input=text,
            resolved_name=name,
            api_code=code,
            is_valid=True
        )
    
    # Buscar parcial
    for key, (name, code, _) in ISLAS_CANARIAS.items():
        if text_lower in key or key in text_lower:
            return DimensionValue(
                dimension_type='GEOGRAPHICAL',
                user_input=text,
                resolved_name=name,
                api_code=code,
                is_valid=True
            )
    
    return None


def resolve_sex(text: str) -> Optional[DimensionValue]:
    """Resuelve un valor de sexo.
    
    Args:
        text: Valor de sexo (ej: "hombres", "mujeres")
        
    Returns:
        DimensionValue o None.
    """
    text_lower = text.lower().strip()
    
    if text_lower in SEXO_VALUES:
        name, code = SEXO_VALUES[text_lower]
        return DimensionValue(
            dimension_type='SEX',
            user_input=text,
            resolved_name=name,
            api_code=code,
            is_valid=True
        )
    
    return None


def resolve_geo_granularity(text: str) -> Optional[str]:
    """Resuelve una palabra a granularidad geográfica de la API.
    
    Args:
        text: Palabra (ej: "isla", "municipio")
        
    Returns:
        Código de granularidad para la API (ej: "ISLANDS")
    """
    text_lower = text.lower().strip()
    return GEO_GRANULARITIES.get(text_lower)


def resolve_dimension_value(text: str) -> Optional[DimensionValue]:
    """Intenta resolver un valor de dimensión de cualquier tipo.
    
    Args:
        text: Texto del usuario
        
    Returns:
        DimensionValue o None.
    """
    # Intentar como isla
    result = resolve_island(text)
    if result:
        return result
    
    # Intentar como sexo
    result = resolve_sex(text)
    if result:
        return result
    
    return None


def format_islands_list() -> str:
    """Formatea lista de islas para mostrar al usuario."""
    islands = [
        "Tenerife", "Gran Canaria", "Lanzarote", "Fuerteventura",
        "La Palma", "La Gomera", "El Hierro", "La Graciosa"
    ]
    
    lines = ["Islas de Canarias disponibles:", ""]
    for i, island in enumerate(islands, 1):
        lines.append(f"{i}) {island}")
    
    return "\n".join(lines)
