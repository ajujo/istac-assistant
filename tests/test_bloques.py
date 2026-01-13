#!/usr/bin/env python
"""Tests manuales para verificar Bloque A y B.

Ejecutar: python tests/test_bloques.py

Verifica:
- A1: Cache global inmutable (259 indicadores)
- A2: Normalización de IDs (tildes)
- A3: Validación de códigos inventados
- A4: Post-validación de respuestas
- B0: Catálogo fijo
- B1: Indicador base vs desglose
"""

import sys
from pathlib import Path

# Añadir src al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def test_cache_global():
    """A1: Cache global con 259 indicadores desde TSV."""
    from src.data.ids_cache import ensure_cache_loaded, get_cache
    import src.data.ids_cache as cache_module
    
    # Reset singleton para test limpio
    cache_module._cache = None
    
    cache = ensure_cache_loaded()
    count = cache.count()
    
    passed = count == 259
    return passed, f"Cache tiene {count} indicadores (esperado: 259)"


def test_normalizacion():
    """A2: Normalización de IDs (tildes → sin tildes)."""
    from src.data.ids_cache import IndicatorCache
    
    tests = [
        ("POBLACIÓN", "POBLACION"),
        ("POBLACIÓN_HOMBRES", "POBLACION_HOMBRES"),
        ("Tasa_paro", "TASA_PARO"),
    ]
    
    all_passed = True
    messages = []
    
    for input_code, expected in tests:
        result = IndicatorCache.normalize_code(input_code)
        passed = result == expected
        all_passed = all_passed and passed
        messages.append(f"{input_code} → {result} {'✅' if passed else '❌'}")
    
    return all_passed, "\n".join(messages)


def test_cache_inmutable():
    """A3: Cache no se sobrescribe después de TSV."""
    from src.data.ids_cache import ensure_cache_loaded, get_cache
    import src.data.ids_cache as cache_module
    
    cache_module._cache = None
    cache = ensure_cache_loaded()
    count_before = cache.count()
    
    # Intentar sobrescribir
    cache.load([{"code": "FAKE_INDICATOR", "title": "Fake"}])
    count_after = cache.count()
    
    passed = count_before == count_after == 259
    return passed, f"Antes: {count_before}, Después: {count_after} (sobrescritura bloqueada)"


def test_validacion_codigos():
    """A4: Códigos válidos/inválidos detectados correctamente."""
    from src.data.validator import validate_indicator
    
    tests = [
        ("POBLACION", True),
        ("POBLACION_HOMBRES", True),
        ("POBLACION_ISLA", False),  # Inventado
        ("POBLACION_SEXOEDAD", False),  # Inventado
        ("TURISMO_FAKE", False),  # Inventado
    ]
    
    all_passed = True
    messages = []
    
    for code, expected_valid in tests:
        result = validate_indicator(code)
        passed = result.is_valid == expected_valid
        all_passed = all_passed and passed
        status = "válido" if result.is_valid else "inválido"
        emoji = "✅" if passed else "❌"
        messages.append(f"{code}: {status} {emoji}")
    
    return all_passed, "\n".join(messages)


def test_post_validacion():
    """A5: Post-validación detecta códigos inventados en texto."""
    from src.data.validator import validate_response_codes
    
    fake_response = """
    Los indicadores de población son:
    • POBLACION_ISLA
    • POBLACION_SEXOEDAD
    """
    
    result = validate_response_codes(fake_response)
    
    expected_invalid = {"POBLACION_ISLA", "POBLACION_SEXOEDAD"}
    detected = set(result.invalid_codes)
    
    passed = expected_invalid == detected
    return passed, f"Detectados: {result.invalid_codes}"


def test_exclusiones():
    """A6: TOOL_REQUEST no se detecta como código."""
    from src.data.validator import validate_response_codes
    
    response_with_tool = """
    [TOOL_REQUEST] get_indicator_data [END_TOOL_REQUEST]
    """
    
    result = validate_response_codes(response_with_tool)
    
    # No debe detectar TOOL_REQUEST como código inventado
    has_tool_request = "TOOL_REQUEST" in result.invalid_codes
    passed = not has_tool_request
    return passed, f"TOOL_REQUEST detectado: {has_tool_request} (esperado: False)"


def test_analyze_query():
    """B1: Separar indicador de dimensiones."""
    from src.data.dimensions import analyze_query
    
    tests = [
        ("población por isla", "población", ["isla"]),
        ("turismo por sexo", "turismo", ["sexo"]),
        ("tasa de paro según comarca", "tasa de paro", ["comarca"]),
    ]
    
    all_passed = True
    messages = []
    
    for query, expected_ind, expected_dims in tests:
        result = analyze_query(query)
        ind_match = expected_ind in result.indicator_query
        dims_match = set(expected_dims) == set(result.dimensions)
        passed = ind_match and dims_match
        all_passed = all_passed and passed
        emoji = "✅" if passed else "❌"
        messages.append(f'"{query}" → ind={result.indicator_query}, dims={result.dimensions} {emoji}')
    
    return all_passed, "\n".join(messages)


def test_resolve_query():
    """B1b: resolve_query con mensaje educativo."""
    from src.data.resolver import resolve_query
    
    result = resolve_query("población por isla")
    
    conditions = [
        result.indicator_code == "POBLACION",
        "isla" in result.dimensions_detected,
        result.has_breakdown,
        "desagregarse" in result.message or "puede" in result.message,
    ]
    
    passed = all(conditions)
    return passed, f"Indicador: {result.indicator_code}, Dims: {result.dimensions_detected}"


def run_all_tests():
    """Ejecuta todos los tests y muestra resultados."""
    
    console.print(Panel("🧪 Tests de Bloque A y B", style="bold blue"))
    console.print()
    
    tests = [
        ("A1: Cache global (259 IDs)", test_cache_global),
        ("A2: Normalización tildes", test_normalizacion),
        ("A3: Cache inmutable", test_cache_inmutable),
        ("A4: Validación códigos", test_validacion_codigos),
        ("A5: Post-validación texto", test_post_validacion),
        ("A6: Exclusiones (TOOL_REQUEST)", test_exclusiones),
        ("B1: Analyze query (dims)", test_analyze_query),
        ("B1b: Resolve query educativo", test_resolve_query),
    ]
    
    table = Table(title="Resultados")
    table.add_column("Test", style="cyan")
    table.add_column("Estado", justify="center")
    table.add_column("Detalle")
    
    total_passed = 0
    total_tests = len(tests)
    
    for name, test_func in tests:
        try:
            passed, detail = test_func()
            status = "✅ PASS" if passed else "❌ FAIL"
            if passed:
                total_passed += 1
            table.add_row(name, status, detail[:60] + "..." if len(detail) > 60 else detail)
        except Exception as e:
            table.add_row(name, "💥 ERROR", str(e)[:60])
    
    console.print(table)
    console.print()
    console.print(f"Resultado: {total_passed}/{total_tests} tests pasados")
    
    if total_passed == total_tests:
        console.print("[green]✅ Todos los tests pasan![/green]")
    else:
        console.print(f"[red]❌ {total_tests - total_passed} tests fallaron[/red]")


if __name__ == "__main__":
    run_all_tests()
