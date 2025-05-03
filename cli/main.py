import typer
from rich.console import Console
from datetime import datetime
import os

from cli.commands import app as commands_app
from config.logging import logger

app = typer.Typer(help="Sistema de Gestión Financiera con IA para Startups")
console = Console()

# Add sub-commands from commands.py
app.add_typer(commands_app, name="")

@app.callback()
def callback():
    """
    Sistema de Gestión Financiera con IA para Startups
    
    Usa comandos en lenguaje natural para gestionar tus finanzas
    """
    pass

@app.command()
def test_command():
    """Ejecuta una serie de comandos de prueba para verificar que todo funciona correctamente"""
    console.print("[bold]Ejecutando comandos de prueba...[/bold]")
    
    try:
        # Test AI Engine
        console.print("\n[yellow]Probando el motor de IA...[/yellow]")
        from core.ai_engine import AIEngine
        ai_engine = AIEngine()
        result = ai_engine.process_text("Hola, soy un test", "Responde brevemente al usuario.")
        console.print(f"✓ Respuesta del AI Engine: {result[:50]}...")
        
        # Test transaction creation
        console.print("\n[yellow]Probando creación de transacción...[/yellow]")
        from services.transaction_service import TransactionService
        tx_service = TransactionService()
        result = tx_service.process_natural_language("Registra un gasto de prueba de $10 en categoría Test")
        console.print(f"✓ Transacción creada: {result}")
        
        # Test financial analyzer
        console.print("\n[yellow]Probando análisis financiero...[/yellow]")
        from core.financial_analyzer import FinancialAnalyzer
        analyzer = FinancialAnalyzer()
        result = analyzer.calculate_runway(months_back=1)
        console.print(f"✓ Análisis de runway completado")
        
        # Test search engine
        console.print("\n[yellow]Probando motor de búsqueda...[/yellow]")
        from core.search_engine import SearchEngine
        search_engine = SearchEngine()
        results = search_engine.search_transactions("prueba", limit=2)
        console.print(f"✓ Búsqueda completada, {len(results)} resultados")
        
        console.print("\n[bold green]¡Todas las pruebas completadas exitosamente![/bold green]")
    
    except Exception as e:
        console.print(f"[bold red]Error durante las pruebas:[/bold red] {str(e)}")
        logger.error(f"Error in test_command: {e}")

@app.command()
def process_recurring():
    """Procesa elementos recurrentes que estén pendientes"""
    from services.recurring_service import RecurringService
    
    console.print("[bold]Procesando elementos recurrentes...[/bold]")
    
    recurring_service = RecurringService()
    result = recurring_service.process_due_items()
    
    if 'error' in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
    else:
        console.print(f"[bold green]✓[/bold green] {result['message']}")

@app.command()
def setup():
    """Configura el sistema (crea buckets de almacenamiento y verifica conexiones)"""
    console.print("[bold]Configurando el sistema...[/bold]")
    
    try:
        # Import clients
        from data.supabase_client import SupabaseClient
        from data.pinecone_client import PineconeClient
        
        # Setup Supabase storage buckets
        console.print("[yellow]Configurando Supabase Storage...[/yellow]")
        supabase = SupabaseClient()
        
        # Check if documents bucket exists, create if not
        try:
            # Primero intentamos listar los buckets para ver si ya existe
            buckets = supabase.get_client().storage.list_buckets()
            bucket_exists = any(bucket['name'] == 'documents' for bucket in buckets)
            
            if bucket_exists:
                console.print("  Bucket 'documents' ya existe")
            else:
                try:
                    supabase.get_client().storage.create_bucket('documents')
                    console.print("  Bucket 'documents' creado")
                except Exception as bucket_error:
                    console.print(f"  [yellow]No se pudo crear el bucket 'documents': {bucket_error}[/yellow]")
                    console.print("  [yellow]Si eres administrador, crea este bucket manualmente en el panel de Supabase[/yellow]")
        except Exception as e:
            console.print(f"  [yellow]Error al verificar buckets: {e}[/yellow]")
            console.print("  [yellow]Es posible que necesites crear los buckets manualmente en el panel de Supabase[/yellow]")
        
        # Try to connect to Supabase anyways
        try:
            supabase_conn = supabase.get_client().table("categories").select("*").limit(1).execute()
            console.print("  Conexión a Supabase: OK")
        except Exception as e:
            console.print(f"  [red]Error de conexión a Supabase: {e}[/red]")
        
        console.print("[green]¡Configuración de Supabase completada![/green]")
        
        # Setup Pinecone
        console.print("[yellow]Configurando Pinecone...[/yellow]")
        try:
            pinecone = PineconeClient()
            pinecone.setup_index()
            
            # Verify connection
            pinecone_conn = pinecone.get_index().describe_index_stats()
            console.print("  Conexión a Pinecone: OK")
            console.print("[green]¡Pinecone configurado exitosamente![/green]")
        except Exception as e:
            console.print(f"  [red]Error configurando Pinecone: {e}[/red]")
        
        console.print("[bold green]¡Configuración completada![/bold green]")
        console.print("[yellow]Nota: Si hubo errores durante la configuración, es posible que necesites configurar algunos componentes manualmente.[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error durante la configuración:[/bold red] {str(e)}")
        logger.error(f"Error in setup: {e}")

@app.command()
def hello(name: str = typer.Option("usuario", help="Tu nombre")):
    """Saludo inicial para probar la CLI"""
    console.print(f"¡Hola, [bold green]{name}[/bold green]! Bienvenido al Sistema de Gestión Financiera con IA")
    console.print("\nPuedes usar comandos en lenguaje natural como:")
    console.print("  - [italic]\"Registra un gasto de $150 en software\"[/italic]")
    console.print("  - [italic]\"¿Cuál es mi runway actual?\"[/italic]")
    console.print("  - [italic]\"Carga esta factura\"[/italic] (adjuntando un archivo)")
    console.print("  - [italic]\"Muéstrame los gastos de marketing del último mes\"[/italic]")
    console.print("  - [italic]\"Configura un pago recurrente de $50 mensuales para Office 365\"[/italic]")
    console.print("\nPara procesar documentos, usa el comando [bold]financeai query[/bold] con --file:")
    console.print("  [italic]financeai query \"Procesa esta factura\" --file=documento.pdf[/italic]")
    logger.info(f"CLI iniciada y saludando a {name}")

if __name__ == "__main__":
    app()