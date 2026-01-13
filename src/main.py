"""ISTAC Data Assistant - CLI Principal.

Interfaz de línea de comandos para interactuar con el asistente.

Uso:
    python -m src.main chat       # Iniciar conversación
    python -m src.main search     # Buscar indicadores/datasets
    python -m src.main info CODE  # Info de un indicador
"""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from .config import get, logger
from .i18n import t, set_language, get_language
from .llm import get_client as get_llm_client, get_system_prompt
from .llm.tools import register_tools
from .data import get_client as get_istac_client

# CLI app
app = typer.Typer(
    name="istac-assistant",
    help="Asistente de Datos del ISTAC",
    add_completion=False,
)

# Console para rich output
console = Console()


@app.command()
def chat(
    language: str = typer.Option("es", "--lang", "-l", help="Idioma (es/en)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Modo debug"),
):
    """Inicia una conversación con el asistente."""
    
    # Configurar idioma
    set_language(language)
    
    # Verificar LMStudio
    console.print(Panel(t("welcome"), title=t("app_name"), border_style="blue"))
    console.print()
    
    llm = get_llm_client()
    
    if not llm.is_available():
        console.print(f"[red]❌ {t('chat.no_connection')}[/red]")
        console.print("[yellow]Asegúrate de que LMStudio está ejecutándose en http://localhost:1234[/yellow]")
        raise typer.Exit(1)
    
    console.print("[green]✅ Conectado a LMStudio[/green]")
    console.print()
    
    # Pre-cargar cache de indicadores desde TSV (259 indicadores)
    from .data.ids_cache import ensure_cache_loaded
    cache = ensure_cache_loaded()
    console.print(f"[dim]📊 Cache: {cache.count()} indicadores cargados[/dim]")
    
    # Registrar tools
    register_tools(llm)
    
    # Obtener system prompt
    system_prompt = get_system_prompt(language)
    
    # Historial de conversación
    history = []
    
    console.print(f"[dim]Escribe 'salir' o 'exit' para terminar, '/debug' para activar trazabilidad[/dim]")
    console.print()
    
    # Estado de debug interactivo
    debug_mode = debug
    
    while True:
        try:
            # Input del usuario
            user_input = Prompt.ask(f"[bold cyan]{t('chat.prompt')}[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Comandos especiales
            if user_input.lower() in ('salir', 'exit', 'quit', 'q'):
                console.print(f"\n[blue]{t('goodbye')}[/blue]")
                break
            
            if user_input.startswith('/lang '):
                new_lang = user_input.split(' ')[1].strip()
                if new_lang in ('es', 'en'):
                    set_language(new_lang)
                    system_prompt = get_system_prompt(new_lang)
                    console.print(f"[green]{t('language_changed')}[/green]")
                continue
            
            # Comando /debug - toggle
            if user_input.lower() == '/debug':
                debug_mode = not debug_mode
                status = "✅ ACTIVADO" if debug_mode else "❌ DESACTIVADO"
                console.print(f"[yellow]Modo debug: {status}[/yellow]")
                if debug_mode:
                    console.print("[dim]Verás las llamadas a herramientas y respuestas de la API[/dim]")
                continue
            
            # Comando /tools - listar herramientas
            if user_input.lower() == '/tools':
                from .llm.tools import TOOL_FUNCTIONS
                console.print("[bold]Herramientas disponibles:[/bold]")
                for name in TOOL_FUNCTIONS:
                    console.print(f"  • {name}")
                continue
            
            # Comando /indicadores - buscar indicadores reales
            if user_input.lower().startswith('/indicadores'):
                query = user_input[12:].strip() or "poblacion"
                from .data import get_client
                istac = get_client()
                results = istac.search_indicators(query, limit=10)
                console.print(f"[bold]Indicadores con '{query}':[/bold]")
                for r in results:
                    console.print(f"  • [green]{r['code']}[/green]: {r['title']}")
                continue
            
            # Enviar al LLM
            console.print(f"[dim]{t('chat.thinking')}[/dim]")
            
            try:
                # Usar chat con tools
                response = llm.chat(
                    message=user_input,
                    system_prompt=system_prompt,
                    history=history,
                    use_tools=True,
                    debug=debug_mode,  # Pasar modo debug
                )
                
                # En modo debug, mostrar info de herramientas usadas
                if debug_mode and hasattr(llm, '_last_tool_calls'):
                    for tc in llm._last_tool_calls:
                        console.print(Panel(
                            f"[bold]Herramienta:[/bold] {tc.get('name', 'unknown')}\n"
                            f"[bold]Args:[/bold] {tc.get('args', {})}\n"
                            f"[bold]Resultado:[/bold] {str(tc.get('result', ''))[:200]}...",
                            title="🔧 Tool Call",
                            border_style="yellow"
                        ))
                
                # Mostrar respuesta en Panel verde
                console.print()
                console.print(Panel(
                    Markdown(response),
                    title=t('chat.assistant'),
                    border_style="green"
                ))
                
                # POST-VALIDACIÓN: Detectar códigos inventados
                from .data.validator import validate_response_codes, format_code_correction
                
                code_validation = validate_response_codes(response)
                if not code_validation.is_valid:
                    # Mostrar advertencia con códigos inválidos y sugerencias
                    correction_msg = format_code_correction(code_validation)
                    console.print(Panel(
                        Markdown(correction_msg),
                        title="⚠️ Códigos Inventados Detectados",
                        border_style="red"
                    ))
                
                console.print()
                
                # Añadir al historial
                history.append({"role": "user", "content": user_input})
                history.append({"role": "assistant", "content": response})
                
                # Limitar historial
                if len(history) > 20:
                    history = history[-20:]
                    
            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                if debug_mode:
                    console.print_exception()
                    
        except KeyboardInterrupt:
            console.print(f"\n[blue]{t('goodbye')}[/blue]")
            break


@app.command()
def search(
    query: str = typer.Argument("", help="Texto a buscar"),
    limit: int = typer.Option(20, "--limit", "-n", help="Número de resultados"),
):
    """Busca indicadores por texto."""
    
    client = get_istac_client()
    
    console.print(f"[dim]Buscando '{query}'...[/dim]" if query else "[dim]Listando indicadores...[/dim]")
    
    results = client.search_indicators(query, limit)
    
    if not results:
        console.print("[yellow]No se encontraron resultados[/yellow]")
        return
    
    table = Table(title=f"Indicadores ({len(results)} resultados)")
    table.add_column("Código", style="cyan")
    table.add_column("Título", style="white")
    
    for item in results:
        table.add_row(item["code"], item["title"][:60])
    
    console.print(table)


@app.command()
def info(
    code: str = typer.Argument(..., help="Código del indicador"),
):
    """Muestra información detallada de un indicador."""
    
    client = get_istac_client()
    
    console.print(f"[dim]Obteniendo info de {code}...[/dim]")
    
    indicator = client.get_indicator_info(code)
    
    if not indicator:
        console.print(f"[red]No se encontró el indicador '{code}'[/red]")
        raise typer.Exit(1)
    
    # Mostrar info
    console.print(Panel(
        f"[bold]{indicator['title']}[/bold]\n\n"
        f"[dim]Código:[/dim] {indicator['code']}\n"
        f"[dim]Tema:[/dim] {indicator['subject']}\n\n"
        f"{indicator['description']}\n\n"
        f"[dim]Granularidades geográficas:[/dim] {indicator['geographical_granularities']}\n"
        f"[dim]Granularidades temporales:[/dim] {indicator['time_granularities']}\n"
        f"[dim]Medidas:[/dim] {indicator['measures']}\n"
        f"[dim]Años disponibles:[/dim] {indicator['available_years'][0]} - {indicator['available_years'][-1]}",
        title="Información del Indicador",
        border_style="blue"
    ))


@app.command()
def datasets(
    limit: int = typer.Option(30, "--limit", "-n", help="Número de resultados"),
):
    """Lista los datasets disponibles."""
    
    client = get_istac_client()
    
    console.print("[dim]Listando datasets...[/dim]")
    
    results = client.list_datasets(limit)
    
    if not results:
        console.print("[yellow]No se encontraron datasets[/yellow]")
        return
    
    table = Table(title=f"Datasets ({len(results)} resultados)")
    table.add_column("ID", style="cyan")
    table.add_column("Nombre", style="white")
    
    for item in results:
        table.add_row(item["id"], item["name"][:50])
    
    console.print(table)


@app.command()
def version():
    """Muestra la versión del asistente."""
    from . import __version__
    console.print(f"ISTAC Data Assistant v{__version__}")


def main():
    """Entry point principal."""
    app()


if __name__ == "__main__":
    main()
