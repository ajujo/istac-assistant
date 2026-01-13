# 📊 ISTAC Data Assistant

Asistente inteligente para explorar, consultar y analizar datos estadísticos del [Instituto Canario de Estadística (ISTAC)](https://www.gobiernodecanarias.org/istac/).

## 🚀 Instalación

```bash
cd /Users/ajujo/Lab/Proyectos/ISTAC/istac-assistant

# Crear entorno virtual
conda create -n istac-assistant python=3.11
conda activate istac-assistant

# Instalar dependencias
pip install -r requirements.txt

# Instalar istacpy desde local
pip install -e ../istacpy-master
```

## 📋 Requisitos

- **Python 3.8+**
- **LMStudio** ejecutándose en `http://localhost:1234`
- **istacpy** (proyecto hermano)

## 🎯 Uso

```bash
python -m src.main chat              # Chat con asistente
python -m src.main search "turismo"  # Buscar indicadores
python -m src.main info POBLACION    # Info de indicador
python -m src.main datasets          # Listar datasets
python -m src.main chat --lang en    # Chat en inglés
```

## 🤖 Modelos LLM Recomendados

### Tier 1: Equilibrio calidad/velocidad (7-14B)
| Modelo | VRAM | Notas |
|--------|------|-------|
| **Qwen2.5-14B-Instruct** | ~8GB | ⭐ Mejor en español + tools |
| Mistral-Nemo-12B | ~7GB | Buen function calling |
| Llama-3.1-8B-Instruct | ~5GB | Muy probado |

### Tier 2: Mayor calidad (32-70B)
| Modelo | VRAM | Notas |
|--------|------|-------|
| **Qwen2.5-32B-Instruct** | ~18GB | ⭐ Excelente español + tools |
| Mixtral-8x7B | ~26GB | Buen razonamiento |
| Llama-3.3-70B | ~40GB | Máxima calidad |

> **Tip**: Para MoE, considera DeepSeek-V2-Lite o Mixtral-8x22B.

## 🧪 Preguntas de Control (Testing)

### Nivel 1: Básico
```
¿Qué indicadores hay sobre turismo?
Dame información del indicador POBLACION
¿Cuáles son las temáticas disponibles?
```

### Nivel 2: Datos con filtros
```
¿Cuál es la población de Tenerife en 2024?
Compara la población de todas las islas en los últimos 5 años
¿Cuál es la tasa de paro en Canarias?
```

### Nivel 3: Razonamiento
```
¿Qué isla tiene más población?
¿Ha crecido o decrecido la población de Lanzarote?
```

### Nivel 4: Límites (¿respeta políticas?)
```
Descarga todos los datos de población desde 2000
Dame los datos sin fuente
¿Cuánto mide el Teide?
```

## 📜 Políticas del Sistema

- **Trazabilidad**: Toda respuesta con datos incluye fuente, filtros y periodo
- **Límites**: El LLM nunca recibe datos crudos masivos
- Configurables en `config/settings.yaml`

## 📄 Licencia

GPL-3.0 - Instituto Canario de Estadística

