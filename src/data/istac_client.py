"""Wrapper para istacpy optimizado para el ISTAC Data Assistant.

Este módulo proporciona una interfaz simplificada y optimizada
para acceder a los datos del ISTAC, aplicando las políticas del sistema.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

# Importar istacpy
from istacpy.indicators import indicators as api_indicators
from istacpy.indicators import geographic as api_geographic
from istacpy.indicators.lite import indicators as lite_indicators
from istacpy.statisticalresources import cubes, queries

from .. import config
from ..policies import (
    DataTraceability,
    check_download_limit,
    check_display_limit,
    prepare_data_for_llm,
    LIMITS,
)


class ISTACClient:
    """Cliente unificado para acceder a datos del ISTAC.
    
    Example:
        >>> client = ISTACClient()
        >>> indicators = client.search_indicators("población")
        >>> data = client.get_indicator_data("POBLACION", geo="I", time="Y|2023")
    """
    
    def __init__(self):
        """Inicializa el cliente."""
        self.logger = config.logger
    
    # =========================================================================
    # INDICADORES
    # =========================================================================
    
    def search_indicators(
        self,
        query: str = "",
        limit: int = 50
    ) -> List[Dict[str, str]]:
        """Busca indicadores por texto.
        
        Args:
            query: Texto a buscar
            limit: Máximo de resultados
        
        Returns:
            Lista de diccionarios con código y título.
        """
        try:
            if query:
                # Usar lite indicators para búsqueda
                results = lite_indicators.get_indicators(query)
                return [{"code": code, "title": title} for code, title in results[:limit]]
            else:
                # Listar todos
                response = api_indicators.get_indicators(limit=limit)
                items = response.get('items', [])
                return [
                    {
                        "code": item.get('code', ''),
                        "title": self._get_localized_text(item.get('title', {}))
                    }
                    for item in items
                ]
        except Exception as e:
            self.logger.error(f"Error buscando indicadores: {e}")
            return []
    
    def get_indicator_info(self, code: str) -> Optional[Dict[str, Any]]:
        """Obtiene información detallada de un indicador.
        
        Args:
            code: Código del indicador
        
        Returns:
            Diccionario con metadatos del indicador.
        """
        try:
            indicator = lite_indicators.get_indicator(code)
            return {
                "code": indicator.code,
                "title": indicator.title,
                "subject": indicator.subject,
                "description": indicator.description,
                "geographical_granularities": indicator.geographical_granularities,
                "time_granularities": indicator.time_granularities,
                "measures": indicator.measures,
                "available_years": indicator.available_years,
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo info de {code}: {e}")
            return None
    
    def get_indicator_data(
        self,
        code: str,
        geo: Optional[str] = None,
        time: Optional[str] = None,
        measure: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[DataTraceability]]:
        """Obtiene datos de un indicador con trazabilidad.
        
        Args:
            code: Código del indicador
            geo: Filtro geográfico (ej: "I", "M|Tenerife")
            time: Filtro temporal (ej: "Y|2020:2023")
            measure: Tipo de medida (ej: "A" para absoluto)
        
        Returns:
            Tupla de (DataFrame, Trazabilidad) o (None, None) si hay error.
        """
        try:
            indicator = lite_indicators.get_indicator(code)
            data = indicator.get_data(geo=geo, time=time, measure=measure)
            df = data.as_dataframe()
            
            # Crear trazabilidad
            traceability = DataTraceability(
                source_name=indicator.title,
                source_code=code,
                geography=data.geographical_granularity,
                dimensions={},
                time_period=", ".join(data.index) if data.index else "N/A",
                query_description=f"Datos de {indicator.title}"
            )
            
            return df, traceability
            
        except Exception as e:
            self.logger.error(f"Error obteniendo datos de {code}: {e}")
            return None, None
    
    # =========================================================================
    # DATASETS
    # =========================================================================
    
    def list_datasets(self, limit: int = 50) -> List[Dict[str, str]]:
        """Lista los datasets disponibles.
        
        Args:
            limit: Máximo de resultados
        
        Returns:
            Lista de diccionarios con id y nombre.
        """
        try:
            response = cubes.get_statisticalresources_datasets(limit=limit)
            items = response.get('dataset', [])
            return [
                {
                    "id": item.get('id', ''),
                    "name": self._get_localized_text(item.get('name', {})),
                    "version": item.get('version', ''),
                }
                for item in items
            ]
        except Exception as e:
            self.logger.error(f"Error listando datasets: {e}")
            return []
    
    def get_dataset(
        self,
        agency: str,
        resource_id: str,
        version: str = "~latest",
        filters: Optional[str] = None,
    ) -> Tuple[Optional[pd.DataFrame], Optional[DataTraceability]]:
        """Obtiene un dataset con trazabilidad.
        
        Args:
            agency: Agencia (normalmente "ISTAC")
            resource_id: ID del recurso
            version: Versión (default: última)
            filters: Filtro de dimensiones
        
        Returns:
            Tupla de (DataFrame, Trazabilidad) o (None, None) si hay error.
        """
        try:
            result = cubes.get_statisticalresources_datasets_agency_resource_version(
                agencyid=agency,
                resourceid=resource_id,
                version=version,
                dim=filters or "",
                as_dataframe=True
            )
            
            df = result.dataframe
            
            # Verificar límites
            allowed, msg = check_download_limit(len(df))
            if not allowed:
                self.logger.warning(msg)
            
            traceability = DataTraceability(
                source_name=resource_id,
                source_code=f"{agency}/{resource_id}/{version}",
                geography=None,
                dimensions={"filtros": filters} if filters else {},
                time_period="",
                query_description=f"Dataset {resource_id}"
            )
            
            return df, traceability
            
        except Exception as e:
            self.logger.error(f"Error obteniendo dataset: {e}")
            return None, None
    
    # =========================================================================
    # UTILIDADES
    # =========================================================================
    
    def get_geographic_granularities(self) -> List[Dict[str, str]]:
        """Obtiene las granularidades geográficas disponibles."""
        try:
            response = api_geographic.get_indicators_geographic_granularities()
            items = response.get('items', [])
            return [
                {
                    "code": item.get('code', ''),
                    "title": self._get_localized_text(item.get('title', {}))
                }
                for item in items
            ]
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return []
    
    def get_subjects(self) -> List[Dict[str, str]]:
        """Obtiene las temáticas disponibles."""
        try:
            subjects = lite_indicators.get_subjects()
            return [{"code": code, "title": title} for code, title in subjects]
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return []
    
    def _get_localized_text(self, text_obj: Any) -> str:
        """Extrae texto localizado de un objeto de la API."""
        if isinstance(text_obj, str):
            return text_obj
        if isinstance(text_obj, dict):
            return text_obj.get('__default__', str(text_obj))
        if isinstance(text_obj, dict) and 'text' in text_obj:
            texts = text_obj.get('text', [])
            if texts and isinstance(texts, list):
                return texts[0].get('value', '')
        return str(text_obj) if text_obj else ''


# Cliente singleton
_client: Optional[ISTACClient] = None


def get_client() -> ISTACClient:
    """Obtiene el cliente singleton de ISTAC."""
    global _client
    if _client is None:
        _client = ISTACClient()
    return _client
