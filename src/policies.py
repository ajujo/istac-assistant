"""Políticas fundamentales del ISTAC Data Assistant.

Este módulo define las reglas obligatorias del sistema para garantizar:
- Fiabilidad estadística
- Reproducibilidad
- Seguridad
- Uso responsable de LLMs

Estas políticas son aplicadas por el CORE, no dependen del LLM.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from . import config


# =============================================================================
# LÍMITES DEL SISTEMA
# =============================================================================

@dataclass
class SystemLimits:
    """Límites configurables del sistema."""
    
    # Máximo de filas a descargar por dataset
    max_download_rows: int = 500_000
    
    # Máximo de filas a mostrar en UI
    max_display_rows: int = 1_000
    
    # Máximo de filas a pasar al LLM (NUNCA datos crudos masivos)
    max_llm_rows: int = 100
    
    # Tamaño máximo de chunk para procesamiento
    chunk_size: int = 100_000
    
    @classmethod
    def from_config(cls) -> 'SystemLimits':
        """Carga límites desde la configuración."""
        storage = config.get_storage_config()
        return cls(
            max_download_rows=storage.get('max_download_rows', 500_000),
            max_display_rows=storage.get('max_display_rows', 1_000),
        )


# Límites globales
LIMITS = SystemLimits.from_config()


# =============================================================================
# BLOQUE DE TRAZABILIDAD (Obligatorio en respuestas con datos)
# =============================================================================

@dataclass
class DataTraceability:
    """Bloque de trazabilidad para respuestas con datos numéricos.
    
    TODA respuesta que contenga valores numéricos DEBE incluir
    este bloque de trazabilidad. No es opcional.
    """
    
    # Fuente
    source_name: str              # Nombre del dataset/indicador
    source_code: Optional[str]    # Código oficial ISTAC
    
    # Filtros aplicados
    geography: Optional[str]      # Ámbito geográfico
    dimensions: Dict[str, str]    # Otras dimensiones (sexo, edad, etc.)
    
    # Periodo temporal
    time_period: str              # Año(s), trimestre(s), rango
    
    # Consulta realizada
    query_description: str        # Descripción humana
    query_technical: Optional[str] = None  # SQL/pseudocódigo (opcional)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para serialización."""
        return {
            'fuente': {
                'nombre': self.source_name,
                'codigo': self.source_code,
            },
            'filtros': {
                'ambito': self.geography,
                **self.dimensions,
            },
            'periodo': self.time_period,
            'consulta': self.query_description,
            'consulta_tecnica': self.query_technical,
        }
    
    def to_markdown(self) -> str:
        """Genera el bloque de trazabilidad en formato Markdown."""
        lines = [
            "",
            "---",
            "📌 **Fuente ISTAC**",
            f"- Indicador/Dataset: {self.source_name}",
        ]
        
        if self.source_code:
            lines.append(f"- Código: `{self.source_code}`")
        
        lines.append("")
        lines.append("📌 **Filtros aplicados**")
        
        if self.geography:
            lines.append(f"- Ámbito: {self.geography}")
        
        for key, value in self.dimensions.items():
            lines.append(f"- {key}: {value}")
        
        lines.append("")
        lines.append("📌 **Periodo**")
        lines.append(f"- {self.time_period}")
        
        lines.append("")
        lines.append("📌 **Consulta**")
        lines.append(f"- {self.query_description}")
        
        if self.query_technical:
            lines.append(f"- Técnica: `{self.query_technical}`")
        
        lines.append("---")
        
        return "\n".join(lines)


# =============================================================================
# VALIDADORES DE POLÍTICAS
# =============================================================================

def check_download_limit(row_count: int) -> tuple[bool, str]:
    """Verifica si la descarga está dentro del límite.
    
    Returns:
        (allowed, message)
    """
    if row_count > LIMITS.max_download_rows:
        return (
            False,
            f"El dataset tiene {row_count:,} filas, superando el límite de {LIMITS.max_download_rows:,}. "
            f"Por favor, aplica filtros para reducir el volumen."
        )
    return (True, "")


def check_display_limit(row_count: int) -> tuple[bool, int, str]:
    """Verifica límite de visualización.
    
    Returns:
        (within_limit, rows_to_show, message)
    """
    if row_count > LIMITS.max_display_rows:
        return (
            False,
            LIMITS.max_display_rows,
            f"Mostrando primeras {LIMITS.max_display_rows:,} de {row_count:,} filas. "
            f"Usa filtros o solicita agregados para ver más."
        )
    return (True, row_count, "")


def prepare_data_for_llm(
    data: List[Dict],
    include_sample: bool = True,
    max_sample: int = 10
) -> Dict[str, Any]:
    """Prepara datos para enviar al LLM de forma segura.
    
    El LLM NUNCA recibe datos crudos masivos.
    Solo recibe: metadatos, estadísticas, muestras pequeñas.
    
    Returns:
        Diccionario con información segura para el LLM.
    """
    row_count = len(data)
    
    result = {
        'row_count': row_count,
        'column_count': len(data[0]) if data else 0,
        'columns': list(data[0].keys()) if data else [],
    }
    
    # Solo incluir muestra si está permitido
    if include_sample and row_count > 0:
        result['sample'] = data[:min(max_sample, row_count)]
        result['sample_note'] = f"Muestra de {len(result['sample'])} de {row_count} filas"
    
    return result
