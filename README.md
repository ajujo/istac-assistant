# 📊 ISTAC Data Assistant

Asistente inteligente para explorar, consultar y analizar datos estadísticos del [Instituto Canario de Estadística (ISTAC)](https://www.gobiernodecanarias.org/istac/).

## ✨ Características

- � **API Directa ISTAC** - Conexión nativa a las 10 APIs del ISTAC
- 🤖 **LLM Local** - Compatible con LMStudio (Qwen, Llama, Mistral, Command-R)
- 📊 **Datos actualizados** - Acceso a indicadores, datasets, clasificaciones y operaciones
- 🔍 **Trazabilidad** - Todas las respuestas incluyen fuente y filtros aplicados
- 🌐 **Bilingüe** - Español e inglés

## �🚀 Instalación

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
```

## 🌐 APIs del ISTAC Soportadas

| API | Descripción | Estado |
|-----|-------------|--------|
| Indicadores | Métricas y datos estadísticos | ✅ |
| Recursos Estadísticos | Cubos de datos/datasets | ✅ |
| Recursos Estructurales | Clasificaciones (CNAE, territorios) | ✅ |
| Operaciones Estadísticas | Encuestas, censos | ✅ |
| Metadatos Comunes | Info organizacional | 🔧 |
| Georreferenciación | Datos territoriales | 🔧 |
| Registro SDMX | Formato estándar | 🔧 |
| Exportaciones | Descargas | 🔧 |
| Permalinks | Enlaces permanentes | 🔧 |
| CKAN Catálogo | Catálogo datos abiertos | 🔧 |

## 🤖 Modelos LLM Recomendados

| Modelo | VRAM | Notas |
|--------|------|-------|
| **Command-R (35B)** | ~20GB | ⭐ Mejor para tools/RAG |
| **Qwen2.5-32B** | ~18GB | ⭐ Excelente español |
| Qwen2.5-14B | ~8GB | Equilibrio calidad/velocidad |
| Mistral-Nemo-12B | ~7GB | Buen function calling |

## 🧪 Preguntas de Prueba

```
# Nivel 1: Básico
¿Qué indicadores hay sobre turismo?
¿Cuáles son las temáticas disponibles?

# Nivel 2: Datos
¿Cuál es la población de Canarias en 2025?
¿Cuál es la tasa de paro?

# Nivel 3: Razonamiento
¿Qué isla tiene más población?
¿Ha crecido la población de Lanzarote?

# Nivel 4: Límites
¿Cuánto mide el Teide? → Debe rechazar (no es dato ISTAC)
```

## 📜 Políticas del Sistema

- **Trazabilidad**: Toda respuesta con datos incluye fuente, filtros y periodo
- **Límites**: El LLM nunca recibe datos crudos masivos
- Configurables en `config/settings.yaml`

## 📄 Licencia

GPL-3.0 - Instituto Canario de Estadística
