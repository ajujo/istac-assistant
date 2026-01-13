# ISTAC Data Assistant - Walkthrough Bloque 1

## ✅ Bloque 1 Completado

Estructura del proyecto creada y verificada.

---

## Archivos Principales

| Archivo | Descripción |
|---------|-------------|
| `src/main.py` | CLI principal (chat, search, info, datasets) |
| `src/config.py` | Configuración global |
| `src/policies.py` | Políticas de trazabilidad y límites |
| `src/i18n/` | Traducciones ES/EN |
| `src/llm/lmstudio.py` | Cliente LMStudio |
| `src/llm/tools.py` | Tools independientes de framework |
| `src/data/istac_client.py` | Wrapper de istacpy |

---

## Verificaciones ✅

```
✅ Config, i18n, policies - OK
✅ ISTAC Client - OK  
✅ Tools LLM definidos - OK
✅ CLI search - OK
✅ CLI info - OK
```

---

## Uso

```bash
conda activate istac
cd /Users/ajujo/Lab/Proyectos/ISTAC/istac-assistant

python -m src.main search turismo
python -m src.main info POBLACION
python -m src.main chat  # Requiere LMStudio
```

---

## Próximo: Probar chat con LMStudio
