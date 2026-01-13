"""Tools (herramientas) para el LLM.

Estas funciones son expuestas al LLM como herramientas que puede invocar.
Usa la API directa del ISTAC (sin istacpy).
"""

from typing import Any, Dict, List, Optional

from ..data import get_client


# =============================================================================
# DEFINICIONES DE TOOLS (JSON Schema)
# =============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "search_indicators",
        "description": "Busca indicadores estadísticos del ISTAC por texto. Útil para encontrar qué indicadores están disponibles sobre un tema.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar (ej: 'población', 'empleo', 'turismo')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados (default: 25)",
                    "default": 25
                }
            },
            "required": []
        }
    },
    {
        "name": "get_indicator_info",
        "description": "Obtiene información detallada de un indicador: descripción, granularidades, años disponibles. SIEMPRE usa esto primero antes de pedir datos.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código del indicador (ej: 'POBLACION', 'TASA_PARO')"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "get_indicator_data",
        "description": "Obtiene datos numéricos de un indicador con filtros opcionales.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código del indicador"
                },
                "geo": {
                    "type": "string",
                    "description": "Filtro geográfico: 'REGIONS'=Canarias, 'ISLANDS'=islas, 'MUNICIPALITIES'=municipios"
                },
                "time": {
                    "type": "string",
                    "description": "Filtro temporal: año(s) como '2025' o '2020|2021|2022'"
                },
                "measure": {
                    "type": "string",
                    "description": "Tipo de medida: 'ABSOLUTE' o 'ANNUAL_PERCENTAGE_RATE'",
                    "default": "ABSOLUTE"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "list_datasets",
        "description": "Lista los cubos de datos (datasets) disponibles. Son diferentes a los indicadores.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 25
                },
                "query": {
                    "type": "string",
                    "description": "Texto para filtrar datasets"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_subjects",
        "description": "Obtiene las temáticas/categorías de indicadores.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_classifications",
        "description": "Lista las clasificaciones (codelists) disponibles: CNAE, territorios, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 25
                }
            },
            "required": []
        }
    },
    {
        "name": "list_operations",
        "description": "Lista las operaciones estadísticas: encuestas, censos, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 25
                }
            },
            "required": []
        }
    },
]


# =============================================================================
# IMPLEMENTACIÓN DE TOOLS
# =============================================================================

def search_indicators(query: str = "", limit: int = 25) -> Dict[str, Any]:
    """Busca indicadores por texto."""
    client = get_client()
    results = client.search_indicators(query, limit)
    return {
        "count": len(results),
        "indicators": results,
        "note": f"Se encontraron {len(results)} indicadores"
    }


def get_indicator_info(code: str) -> Dict[str, Any]:
    """Obtiene información de un indicador."""
    client = get_client()
    info = client.get_indicator(code)
    if info:
        return info
    return {"error": f"No se encontró el indicador '{code}'"}


def get_indicator_data(
    code: str,
    geo: Optional[str] = None,
    time: Optional[str] = None,
    measure: str = "ABSOLUTE"
) -> Dict[str, Any]:
    """Obtiene datos de un indicador con trazabilidad."""
    client = get_client()
    df, traceability = client.get_indicator_data(code, geo, time, measure)
    
    if df is None:
        return {"error": f"No se pudieron obtener datos de '{code}'"}
    
    # Convertir DataFrame a formato para LLM
    data_dict = df.to_dict(orient='records')
    
    result = {
        "data": data_dict,
        "count": len(df),
        "columns": list(df.columns),
    }
    
    if traceability:
        result["traceability"] = traceability.to_dict()
    
    return result


def list_datasets(limit: int = 25, query: str = "") -> Dict[str, Any]:
    """Lista datasets disponibles."""
    client = get_client()
    results = client.list_datasets(limit, query)
    return {
        "count": len(results),
        "datasets": results
    }


def get_subjects() -> Dict[str, Any]:
    """Obtiene las temáticas disponibles."""
    client = get_client()
    results = client.get_subjects()
    return {
        "count": len(results),
        "subjects": results
    }


def list_classifications(limit: int = 25) -> Dict[str, Any]:
    """Lista las clasificaciones disponibles."""
    client = get_client()
    results = client.list_classifications(limit)
    return {
        "count": len(results),
        "classifications": results
    }


def list_operations(limit: int = 25) -> Dict[str, Any]:
    """Lista las operaciones estadísticas."""
    client = get_client()
    results = client.list_operations(limit)
    return {
        "count": len(results),
        "operations": results
    }


# =============================================================================
# REGISTRO DE TOOLS
# =============================================================================

TOOL_FUNCTIONS = {
    "search_indicators": search_indicators,
    "get_indicator_info": get_indicator_info,
    "get_indicator_data": get_indicator_data,
    "list_datasets": list_datasets,
    "get_subjects": get_subjects,
    "list_classifications": list_classifications,
    "list_operations": list_operations,
}


def register_tools(llm_client) -> None:
    """Registra todos los tools en el cliente LLM."""
    for tool_def in TOOL_DEFINITIONS:
        name = tool_def["name"]
        if name in TOOL_FUNCTIONS:
            llm_client.register_tool(
                name=name,
                func=TOOL_FUNCTIONS[name],
                description=tool_def["description"],
                parameters=tool_def["parameters"]
            )


def execute_tool(name: str, **kwargs) -> Dict[str, Any]:
    """Ejecuta un tool por nombre."""
    if name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[name](**kwargs)
    return {"error": f"Tool '{name}' no encontrado"}
