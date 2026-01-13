# 📊 ISTAC Data Assistant

Asistente inteligente para explorar, consultar y analizar datos estadísticos del [Instituto Canario de Estadística (ISTAC)](https://www.gobiernodecanarias.org/istac/).

## ✨ Características

- 🔗 **API Directa ISTAC** - Conexión nativa a las 10 APIs del ISTAC
- 🤖 **LLM Local** - Compatible con LMStudio (Qwen, Llama, Mistral, Command-R)
- 📊 **Datos actualizados** - Acceso a indicadores, datasets, clasificaciones y operaciones
- 🔍 **Trazabilidad** - Todas las respuestas incluyen fuente y filtros aplicados
- 🛡️ **Anti-alucinación** - Sistema de validación que bloquea códigos inventados
- 🌐 **Bilingüe** - Español e inglés

## 🚀 Instalación

```bash
cd /Users/ajujo/Lab/Proyectos/ISTAC/istac-assistant

# Crear entorno virtual
conda create -n istac-assistant python=3.11
conda activate istac-assistant

# Instalar dependencias
pip install -r requirements.txt
```

## 📋 Requisitos

- **Python 3.8+**
- **LMStudio** ejecutándose en `http://localhost:1234`

## 🎯 Uso

```bash
python -m src.main chat              # Chat con asistente
python -m src.main search "turismo"  # Buscar indicadores
python -m src.main info POBLACION    # Info de indicador
python -m src.main datasets          # Listar datasets
python -m src.main chat --lang en    # Chat en inglés
python -m src.main chat --debug      # Con trazabilidad de tools
```

## 🛡️ Sistema Anti-Alucinación (Bloque A)

El sistema valida **antes y después** de la ejecución para evitar datos inventados:

| Capa | Descripción |
|------|-------------|
| **Cache Global** | 259 indicadores reales desde TSV, inmutable |
| **Normalización** | `POBLACIÓN` → `POBLACION` (quita tildes) |
| **Validación Pre-Ejecución** | Códigos inventados → bloqueo + sugerencias |
| **Post-Validación** | Escanea respuestas buscando códigos falsos |

```bash
# Ejecutar tests de validación
python tests/test_bloques.py
```

## 📐 Sistema de Dimensiones (Bloque B)

Distingue entre **indicadores** y **desgloses**:

| Concepto | Ejemplo |
|----------|---------|
| Indicador | `POBLACION` (finito, cerrado) |
| Dimensión | `isla`, `sexo`, `edad` (filtros) |

**Regla clave**: No existe `POBLACION_ISLA`. Existe `POBLACION` con filtro `geo=ISLANDS`.

### Islas reconocidas:
Tenerife (38), Gran Canaria (35), Lanzarote, Fuerteventura, La Palma, La Gomera, El Hierro, La Graciosa

### Filtros válidos:
- `geo="ISLANDS"` - Por isla
- `geo="MUNICIPALITIES"` - Por municipio
- `geo="38"` - Solo Tenerife

## 🌐 APIs del ISTAC Soportadas

| API | Descripción | Estado |
|-----|-------------|--------|
| Indicadores | Métricas y datos estadísticos | ✅ |
| Recursos Estadísticos | Cubos de datos/datasets | ✅ |
| Recursos Estructurales | Clasificaciones (CNAE, territorios) | ✅ |
| Operaciones Estadísticas | Encuestas, censos | ✅ |
| Metadatos Comunes | Info organizacional | 🔧 |
| Georreferenciación | Datos territoriales | 🔧 |

## 🤖 Modelos LLM Recomendados

| Modelo | VRAM | Notas |
|--------|------|-------|
| **Command-R (35B)** | ~20GB | ⭐ Mejor para tools/RAG |
| **Qwen2.5-32B** | ~18GB | ⭐ Excelente español |
| Qwen2.5-14B | ~8GB | Equilibrio calidad/velocidad |
| Mistral-Nemo-12B | ~7GB | Buen function calling |

## 🧪 Preguntas de Prueba

```
# Básico - debe usar search_indicators
"¿Qué indicadores hay sobre población?"

# Desglose - debe explicar que isla es dimensión
"Dame la población por isla"

# Datos reales - debe devolver datos con trazabilidad
"¿Cuál es la población de Canarias?"

# Anti-alucinación - NO debe inventar POBLACION_ISLA
"Dame datos de POBLACION_ISLA"
→ Error: "El indicador 'POBLACION_ISLA' no existe"
→ Sugerencia: POBLACION
```

## 📜 Políticas del Sistema

- **Trazabilidad**: Toda respuesta con datos incluye fuente, filtros y periodo
- **Límites**: Máximo 500 filas, 5000 celdas al LLM
- **Validación**: Códigos y filtros validados antes de API
- Configurables en `config/settings.yaml`

## 📄 Licencia

GPL-3.0 - Instituto Canario de Estadística
