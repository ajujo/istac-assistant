"""Tools (herramientas) para el LLM.

Estas funciones son expuestas al LLM como herramientas que puede invocar.
Cada tool tiene un contrato JSON claro y no depende de ningún framework específico.
"""

from typing import Any, Dict, List, Optional

from ..data import get_client as get_istac_client
from ..policies import prepare_data_for_llm


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
                    "description": "Máximo de resultados a devolver (default: 20)",
                    "default": 20
                }
            },
            "required": []
        }
    },
    {
        "name": "get_indicator_info",
        "description": "Obtiene información detallada de un indicador: descripción, granularidades disponibles, años disponibles, etc. SIEMPRE usa esto antes de get_indicator_data para conocer las granularidades correctas.",
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
        "description": "Obtiene datos numéricos de un indicador. IMPORTANTE: Usa get_indicator_info primero para conocer las granularidades disponibles.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Código del indicador"
                },
                "geo": {
                    "type": "string",
                    "description": "Filtro geográfico: 'R'=regiones (Canarias), 'I'=islas, 'M'=municipios. NO uses 'R|Canarias', solo 'R'."
                },
                "time": {
                    "type": "string",
                    "description": "Filtro temporal. Solo si conoces la granularidad del indicador. Omítelo si no estás seguro."
                },
                "measure": {
                    "type": "string",
                    "description": "Tipo de medida: 'A'=absoluto, 'N'=tasa interanual"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "list_datasets",
        "description": "Lista los cubos de datos (datasets) disponibles en el ISTAC. Estos son diferentes a los indicadores.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 30
                }
            },
            "required": []
        }
    },
    {
        "name": "get_subjects",
        "description": "Obtiene las temáticas/categorías en las que se clasifican los indicadores.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_classifications",
        "description": "Lista las clasificaciones (codelists) disponibles, como clasificaciones de actividades económicas, territoriales, etc.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 30
                }
            },
            "required": []
        }
    },
    {
        "name": "list_statistical_operations",
        "description": "Lista las operaciones estadísticas (encuestas, censos, etc.) que realiza el ISTAC.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados",
                    "default": 30
                }
            },
            "required": []
        }
    },
]


# =============================================================================
# IMPLEMENTACIÓN DE TOOLS
# =============================================================================

def search_indicators(query: str = "", limit: int = 20) -> Dict[str, Any]:
    """Busca indicadores por texto."""
    client = get_istac_client()
    results = client.search_indicators(query, limit)
    return {
        "count": len(results),
        "indicators": results,
        "note": f"Se encontraron {len(results)} indicadores"
    }


def get_indicator_info(code: str) -> Dict[str, Any]:
    """Obtiene información de un indicador."""
    client = get_istac_client()
    info = client.get_indicator_info(code)
    if info:
        return info
    return {"error": f"No se encontró el indicador '{code}'"}


def get_indicator_data(
    code: str,
    geo: Optional[str] = None,
    time: Optional[str] = None,
    measure: Optional[str] = None
) -> Dict[str, Any]:
    """Obtiene datos de un indicador con trazabilidad."""
    client = get_istac_client()
    df, traceability = client.get_indicator_data(code, geo, time, measure)
    
    if df is None:
        return {"error": f"No se pudieron obtener datos de '{code}'"}
    
    # Convertir DataFrame a formato seguro para LLM
    data_dict = df.to_dict()
    
    # Preparar respuesta con trazabilidad
    result = {
        "data": data_dict,
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": list(df.columns),
        "index": list(df.index),
    }
    
    # Añadir trazabilidad
    if traceability:
        result["traceability"] = traceability.to_dict()
    
    return result


def list_datasets(limit: int = 30) -> Dict[str, Any]:
    """Lista datasets disponibles."""
    client = get_istac_client()
    results = client.list_datasets(limit)
    return {
        "count": len(results),
        "datasets": results
    }


def get_subjects() -> Dict[str, Any]:
    """Obtiene las temáticas disponibles."""
    client = get_istac_client()
    results = client.get_subjects()
    return {
        "count": len(results),
        "subjects": results
    }


def list_classifications(limit: int = 30) -> Dict[str, Any]:
    """Lista las clasificaciones (codelists) disponibles."""
    from istacpy.structuralresources import classifications
    
    try:
        response = classifications.get_structuralresources_codelists(limit=limit)
        items = response.get('codelist', [])
        results = [
            {
                "id": item.get('id', ''),
                "name": _get_localized_text(item.get('name', {})),
                "agency": item.get('agencyID', ''),
            }
            for item in items
        ]
        return {
            "count": len(results),
            "classifications": results
        }
    except Exception as e:
        return {"error": str(e)}


def list_statistical_operations(limit: int = 30) -> Dict[str, Any]:
    """Lista las operaciones estadísticas disponibles."""
    from istacpy.statisticalresources import cubes
    
    # Las operaciones están relacionadas con los datasets
    # Usamos la lista de datasets como proxy
    try:
        response = cubes.get_statisticalresources_datasets(limit=limit)
        items = response.get('dataset', [])
        
        # Extraer operaciones únicas
        operations = {}
        for item in items:
            op_id = item.get('statisticalOperation', {}).get('id', '')
            if op_id and op_id not in operations:
                operations[op_id] = {
                    "id": op_id,
                    "name": _get_localized_text(item.get('statisticalOperation', {}).get('name', {})),
                }
        
        return {
            "count": len(operations),
            "operations": list(operations.values())
        }
    except Exception as e:
        return {"error": str(e)}


def _get_localized_text(text_obj) -> str:
    """Extrae texto localizado."""
    if isinstance(text_obj, str):
        return text_obj
    if isinstance(text_obj, dict):
        if 'text' in text_obj and isinstance(text_obj['text'], list):
            for t in text_obj['text']:
                if t.get('lang') == 'es':
                    return t.get('value', '')
            if text_obj['text']:
                return text_obj['text'][0].get('value', '')
        return text_obj.get('__default__', str(text_obj))
    return str(text_obj) if text_obj else ''


# =============================================================================
# REGISTRO DE TOOLS
# =============================================================================

# Mapeo nombre -> función
TOOL_FUNCTIONS = {
    "search_indicators": search_indicators,
    "get_indicator_info": get_indicator_info,
    "get_indicator_data": get_indicator_data,
    "list_datasets": list_datasets,
    "get_subjects": get_subjects,
    "list_classifications": list_classifications,
    "list_statistical_operations": list_statistical_operations,
}


def register_tools(llm_client) -> None:
    """Registra todos los tools en el cliente LLM.
    
    Args:
        llm_client: Instancia de LMStudioClient
    """
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
    """Ejecuta un tool por nombre.
    
    Args:
        name: Nombre del tool
        **kwargs: Argumentos del tool
    
    Returns:
        Resultado del tool como diccionario.
    """
    if name in TOOL_FUNCTIONS:
        return TOOL_FUNCTIONS[name](**kwargs)
    return {"error": f"Tool '{name}' no encontrado"}
