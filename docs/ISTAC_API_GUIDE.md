# 🏝️ GUÍA COMPLETA DE LA API DEL ISTAC

## URL Base
```
https://datos.canarias.es/api/estadisticas/
```

## 📊 INDICADORES

```bash
# Listar indicadores
GET /indicators/v1.0/indicators.json?query=población

# Datos de indicador
GET /indicators/v1.0/indicators/{CODE}/data.json

# Con filtros
GET .../data.json?representation=GEOGRAPHICAL[ES70]&granularity=GEOGRAPHICAL[MUNICIPALITIES]
```

## 📁 DATASETS

```bash
# Listar
GET /statistical-resources/v1.0/datasets.json

# Obtener
GET /datasets/{AGENCY}/{DATASET_ID}/~latest.json

# Exportar
GET /export/v1.0/datasets/ISTAC/{DATASET_ID}/~latest.csv
```

## 🏗️ CLASIFICACIONES

```bash
# Listar
GET /structural-resources/v1.0/codelists.json

# Territorios
GET /codelists/ISTAC/CL_TERRITORY/~latest/codes.json
```

## 📋 CÓDIGOS DE TERRITORIO

| Código | Territorio |
|--------|------------|
| ES70 | Canarias (total) |
| ES701 | Lanzarote |
| ES702 | Fuerteventura |
| ES703 | Gran Canaria |
| ES704 | Tenerife |
| ES705 | La Gomera |
| ES706 | La Palma |
| ES707 | El Hierro |

## DATASETS COMUNES

| Código | Descripción |
|--------|-------------|
| E30260A_000001 | Población por sexos y edades |
| E30245A_000002 | Población por municipios |
| E16033A_000001 | PIB por ramas |
| E04002A_000012 | Paro registrado |
