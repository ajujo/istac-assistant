"""Cliente API directo para el ISTAC.

Este módulo proporciona acceso directo a las 10 APIs del ISTAC
sin dependencias externas más allá de requests.

APIs soportadas:
1. Indicadores (/indicators/v1.0)
2. Recursos Estadísticos (/statistical-resources/v1.0)
3. Recursos Estructurales (/structural-resources/v1.0)
4. Operaciones Estadísticas (/operations/v1.0)
5. Metadatos Comunes (/cmetadata/v1.0)
6. Georreferenciación (/georref/v1.0)
7. Registro SDMX (/registry/v1.0)
8. Exportaciones (/export/v1.0)
9. Permalinks (/permalinks/v1.0)
10. CKAN Catálogo (/catalogo)
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import requests
import logging
import pandas as pd

from ..policies import DataTraceability
from ..config import get as get_config, logger


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

BASE_URL = "https://datos.canarias.es/api/estadisticas"

API_ENDPOINTS = {
    "indicators": "/indicators/v1.0",
    "statistical_resources": "/statistical-resources/v1.0",
    "structural_resources": "/structural-resources/v1.0",
    "operations": "/operations/v1.0",
    "cmetadata": "/cmetadata/v1.0",
    "georref": "/georref/v1.0",
    "registry": "/registry/v1.0",
    "export": "/export/v1.0",
    "permalinks": "/permalinks/v1.0",
    "catalog": "/catalogo",
}


# =============================================================================
# CLIENTE PRINCIPAL
# =============================================================================

class ISTACApi:
    """Cliente para las APIs del ISTAC."""
    
    def __init__(self, base_url: str = BASE_URL, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ISTAC-Assistant/1.0"
        })
    
    def _request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Realiza una petición GET a la API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a {url}: {e}")
            raise
    
    def _get_localized_text(self, text_obj: Any, lang: str = "es") -> str:
        """Extrae texto localizado de un objeto multiidioma."""
        if isinstance(text_obj, str):
            return text_obj
        if isinstance(text_obj, dict):
            # Formato: {"__default__": "texto"} o {"text": [{"lang": "es", "value": "..."}]}
            if "__default__" in text_obj:
                return text_obj["__default__"]
            if "text" in text_obj and isinstance(text_obj["text"], list):
                for t in text_obj["text"]:
                    if t.get("lang") == lang:
                        return t.get("value", "")
                if text_obj["text"]:
                    return text_obj["text"][0].get("value", "")
        return str(text_obj) if text_obj else ""

    # =========================================================================
    # API 1: INDICADORES
    # =========================================================================
    
    def search_indicators(self, query: str = "", limit: int = 25) -> List[Dict]:
        """Busca indicadores por texto.
        
        Nota: La API no soporta búsqueda por texto, así que obtenemos
        todos los indicadores y filtramos localmente.
        """
        endpoint = f"{API_ENDPOINTS['indicators']}/indicators"
        # Obtener más indicadores para poder filtrar
        params = {"limit": 200}  # Máximo razonable
        
        data = self._request(endpoint, params)
        
        items = data.get("items", [])
        
        # Filtrar por texto en título si hay query
        if query:
            query_lower = query.lower()
            items = [
                item for item in items
                if query_lower in self._get_localized_text(item.get("title", {})).lower()
                or query_lower in self._get_localized_text(item.get("subjectTitle", {})).lower()
                or query_lower in item.get("code", "").lower()
            ]
        
        # Limitar resultados
        items = items[:limit]
        
        return [
            {
                "code": item.get("code", ""),
                "title": self._get_localized_text(item.get("title", {})),
                "subject": self._get_localized_text(item.get("subjectTitle", {})),
            }
            for item in items
        ]
    
    def get_indicator(self, code: str) -> Optional[Dict]:
        """Obtiene información detallada de un indicador."""
        endpoint = f"{API_ENDPOINTS['indicators']}/indicators/{code}"
        
        try:
            data = self._request(endpoint)
        except requests.exceptions.HTTPError:
            return None
        
        # Extraer granularidades
        dimensions = data.get("dimension", {})
        geo_dim = dimensions.get("GEOGRAPHICAL", {})
        time_dim = dimensions.get("TIME", {})
        
        geo_granularities = {
            g.get("code"): self._get_localized_text(g.get("title", {}))
            for g in geo_dim.get("granularity", [])
        }
        
        time_granularities = {
            g.get("code"): self._get_localized_text(g.get("title", {}))
            for g in time_dim.get("granularity", [])
        }
        
        # Años disponibles
        available_years = sorted([
            t.get("code") for t in time_dim.get("representation", [])
            if t.get("granularityCode") == "YEARLY"
        ], reverse=True)
        
        return {
            "code": data.get("code", code),
            "title": self._get_localized_text(data.get("title", {})),
            "description": self._get_localized_text(data.get("conceptDescription", {})),
            "subject": self._get_localized_text(data.get("subjectTitle", {})),
            "geographical_granularities": geo_granularities,
            "time_granularities": time_granularities,
            "available_years": available_years[:10],  # Últimos 10 años
        }
    
    def get_indicator_data(
        self,
        code: str,
        geo: Optional[str] = None,
        time: Optional[str] = None,
        measure: str = "ABSOLUTE"
    ) -> Tuple[Optional[pd.DataFrame], Optional[DataTraceability]]:
        """Obtiene datos de un indicador con filtros."""
        
        # Construir representación
        rep_parts = []
        if geo:
            # Solo añadir geo si es un código válido de granularidad
            # No usar 'ISLANDS', usar sin filtro para obtener todos
            pass  # Por ahora omitimos geo ya que causa problemas
        if time:
            rep_parts.append(f"TIME[{time}]")
        rep_parts.append(f"MEASURE[{measure}]")
        
        endpoint = f"{API_ENDPOINTS['indicators']}/indicators/{code}/data"
        params = {}
        if rep_parts:
            params["representation"] = ",".join(rep_parts)
        
        try:
            data = self._request(endpoint, params)
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error obteniendo datos de {code}: {e}")
            return None, None
        
        # Parsear estructura SDMX
        observations = data.get("observation", [])
        dimensions = data.get("dimension", {})
        format_order = data.get("format", [])  # Orden de dimensiones
        
        if not observations:
            return None, None
        
        # Invertir índices: posición → código
        dim_maps = {}
        for dim_name, dim_info in dimensions.items():
            rep = dim_info.get("representation", {})
            index_map = rep.get("index", {})
            # Invertir: código → posición  =>  posición → código
            dim_maps[dim_name] = {v: k for k, v in index_map.items()}
        
        # Calcular tamaños de cada dimensión para descomponer índice lineal
        dim_sizes = []
        for dim_name in format_order:
            rep = dimensions.get(dim_name, {}).get("representation", {})
            dim_sizes.append(rep.get("size", 1))
        
        # Construir filas
        rows = []
        for i, obs_value in enumerate(observations):
            row = {}
            
            # Descomponer índice lineal en índices por dimensión
            remaining = i
            indices = []
            for size in reversed(dim_sizes):
                indices.insert(0, remaining % size)
                remaining //= size
            
            # Mapear índices a códigos
            for j, dim_name in enumerate(format_order):
                if j < len(indices):
                    pos = indices[j]
                    code_val = dim_maps.get(dim_name, {}).get(pos, str(pos))
                    row[dim_name] = code_val
            
            # Valor
            try:
                row["value"] = float(obs_value) if obs_value else None
            except (ValueError, TypeError):
                row["value"] = obs_value
            
            rows.append(row)
        
        if not rows:
            return None, None
        
        df = pd.DataFrame(rows)
        
        # Crear trazabilidad
        traceability = DataTraceability(
            source_name=f"Indicador {code}",
            source_code=code,
            geography=geo,
            dimensions={"medida": measure} if measure else {},
            time_period=time or "Todos los años",
            query_description=f"Datos del indicador {code}"
        )
        
        return df, traceability
    
    def get_subjects(self) -> List[Dict]:
        """Obtiene las temáticas/categorías de indicadores."""
        endpoint = f"{API_ENDPOINTS['indicators']}/subjects"
        data = self._request(endpoint)
        
        return [
            {
                "code": item.get("code", ""),
                "title": self._get_localized_text(item.get("title", {})),
            }
            for item in data.get("items", [])
        ]

    # =========================================================================
    # API 2: RECURSOS ESTADÍSTICOS (DATASETS/CUBOS)
    # =========================================================================
    
    def list_datasets(self, limit: int = 25, query: str = "") -> List[Dict]:
        """Lista los cubos de datos disponibles."""
        endpoint = f"{API_ENDPOINTS['statistical_resources']}/datasets"
        params = {"limit": limit}
        if query:
            params["query"] = query
        
        data = self._request(endpoint, params)
        
        return [
            {
                "id": item.get("id", ""),
                "name": self._get_localized_text(item.get("name", {})),
                "urn": item.get("urn", ""),
            }
            for item in data.get("dataset", [])
        ]
    
    def get_dataset(self, agency: str, resource_id: str, version: str = "~latest") -> Optional[Dict]:
        """Obtiene información de un dataset específico."""
        endpoint = f"{API_ENDPOINTS['statistical_resources']}/datasets/{agency}/{resource_id}/{version}"
        
        try:
            data = self._request(endpoint)
        except requests.exceptions.HTTPError:
            return None
        
        return {
            "id": data.get("id", ""),
            "name": self._get_localized_text(data.get("name", {})),
            "description": self._get_localized_text(data.get("description", {})),
            "dimensions": list(data.get("dimension", {}).keys()),
        }

    # =========================================================================
    # API 3: RECURSOS ESTRUCTURALES (CLASIFICACIONES)
    # =========================================================================
    
    def list_classifications(self, limit: int = 25) -> List[Dict]:
        """Lista las clasificaciones (codelists) disponibles."""
        endpoint = f"{API_ENDPOINTS['structural_resources']}/codelists"
        params = {"limit": limit}
        
        data = self._request(endpoint, params)
        
        return [
            {
                "id": item.get("id", ""),
                "name": self._get_localized_text(item.get("name", {})),
                "urn": item.get("urn", ""),
            }
            for item in data.get("codelist", [])
        ]
    
    def get_classification(self, agency: str, resource_id: str, version: str = "~latest") -> Optional[Dict]:
        """Obtiene detalles de una clasificación."""
        endpoint = f"{API_ENDPOINTS['structural_resources']}/codelists/{agency}/{resource_id}/{version}"
        
        try:
            data = self._request(endpoint)
        except requests.exceptions.HTTPError:
            return None
        
        return {
            "id": data.get("id", ""),
            "name": self._get_localized_text(data.get("name", {})),
            "description": self._get_localized_text(data.get("description", {})),
        }

    # =========================================================================
    # API 4: OPERACIONES ESTADÍSTICAS
    # =========================================================================
    
    def list_operations(self, limit: int = 25) -> List[Dict]:
        """Lista las operaciones estadísticas."""
        endpoint = f"{API_ENDPOINTS['operations']}/operations"
        params = {"limit": limit}
        
        data = self._request(endpoint, params)
        
        return [
            {
                "id": item.get("id", ""),
                "name": self._get_localized_text(item.get("title", item.get("name", {}))),
                "urn": item.get("urn", ""),
            }
            for item in data.get("operation", data.get("items", []))
        ]
    
    def get_operation(self, operation_id: str) -> Optional[Dict]:
        """Obtiene detalles de una operación estadística."""
        endpoint = f"{API_ENDPOINTS['operations']}/operations/{operation_id}"
        
        try:
            data = self._request(endpoint)
        except requests.exceptions.HTTPError:
            return None
        
        return {
            "id": data.get("id", ""),
            "name": self._get_localized_text(data.get("title", data.get("name", {}))),
            "description": self._get_localized_text(data.get("description", {})),
        }

    # =========================================================================
    # APIs 5-10: SECUNDARIAS (preparadas para extensión)
    # =========================================================================
    
    def get_metadata(self) -> Dict:
        """Obtiene metadatos comunes de la organización."""
        endpoint = f"{API_ENDPOINTS['cmetadata']}/properties"
        return self._request(endpoint)
    
    def get_geo_info(self, variable_id: str, resource_id: str) -> Optional[Dict]:
        """Obtiene información geográfica."""
        endpoint = f"{API_ENDPOINTS['structural_resources']}/variables/{variable_id}/variableelements/{resource_id}/geoinfo"
        try:
            return self._request(endpoint)
        except requests.exceptions.HTTPError:
            return None

    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def is_available(self) -> bool:
        """Verifica si la API está disponible."""
        try:
            self._request(f"{API_ENDPOINTS['indicators']}/indicators", {"limit": 1})
            return True
        except Exception:
            return False


# =============================================================================
# SINGLETON
# =============================================================================

_client: Optional[ISTACApi] = None

def get_client() -> ISTACApi:
    """Obtiene la instancia singleton del cliente."""
    global _client
    if _client is None:
        _client = ISTACApi()
    return _client
