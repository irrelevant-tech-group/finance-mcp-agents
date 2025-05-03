import os
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional, List
from datetime import datetime

from core.ai_engine import AIEngine
from services.transaction_service import TransactionService
from services.document_service import DocumentService
from services.search_service import SearchService
from services.report_service import ReportService
from services.projection_service import ProjectionService
from services.recurring_service import RecurringService
from config.logging import logger

console = Console()
app = typer.Typer(help="Sistema de Gestión Financiera con IA para Startups")

@app.command()
def query(
    text: str = typer.Argument(..., help="Consulta en lenguaje natural"),
    file: Optional[typer.FileText] = typer.Option(None, help="Archivo adjunto (opcional)")
):
    """
    Procesa consultas en lenguaje natural o comandos para el sistema financiero
    """
    console.print(f"[bold]Procesando:[/bold] {text}")
    
    try:
        # Initialize AI engine to analyze the query
        ai_engine = AIEngine()
        analysis = ai_engine.analyze_financial_query(text)
        intent = analysis.get('intent', 'general_query')
        parameters = analysis.get('parameters', {})
        
        # Process query based on intent
        if intent == 'transaction_create':
            # Create a transaction
            transaction_service = TransactionService()
            result = transaction_service.create_from_text(text)
            
            if result.get('success', False):
                console.print(f"[bold green]✓[/bold green] {result['message']}")
                _display_transaction(result['transaction'])
            else:
                console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Unknown error')}")
        
        elif intent == 'document_process' and file:
            # Process an uploaded document
            document_service = DocumentService()
            result = document_service.process_document(file, os.path.basename(file.name))
            
            if result.get('success', False):
                console.print(f"[bold green]✓[/bold green] {result['message']}")
                _display_document(result['document'])
                
                if result.get('transaction_id'):
                    console.print("[bold]Transacción generada automáticamente:[/bold]")
                    transaction_service = TransactionService()
                    transaction = transaction_service.get(result['transaction_id'])
                    if transaction:
                        _display_transaction(transaction)
            else:
                console.print(f"[bold red]Error:[/bold red] {result.get('error', 'Error procesando documento')}")
        
        elif intent == 'transaction_search' or intent == 'transaction_list':
            # Search or list transactions
            search_service = SearchService()
            results = search_service.search(text, search_type='transactions')
            
            if 'error' in results:
                console.print(f"[bold red]Error:[/bold red] {results['error']}")
            else:
                transactions = results.get('transactions', [])
                console.print(f"[bold]Resultados de búsqueda:[/bold] {len(transactions)} transacciones encontradas")
                
                if transactions:
                    table = Table(show_header=True, header_style="bold magenta")
                    table.add_column("Fecha")
                    table.add_column("Tipo")
                    table.add_column("Descripción")
                    table.add_column("Categoría")
                    table.add_column("Monto", justify="right")
                    
                    for tx in transactions:
                        # Formatear la fecha apropiadamente
                        date_str = _format_date(tx.get('date', ''))
                        
                        table.add_row(
                            date_str,
                            "[green]INGRESO[/green]" if tx['type'] == 'income' else "[red]GASTO[/red]",
                            tx['description'][:30],
                            tx['category'],
                            f"{tx['currency']} {tx['amount']:.2f}"
                        )
                    
                    console.print(table)
                    
                    if 'explanation' in results:
                        console.print(Panel(results['explanation'], title="Análisis", border_style="blue"))
        
        elif intent == 'financial_analysis':
            # Perform financial analysis
            analysis_type = parameters.get('analysis_type', 'runway')
            
            if analysis_type == 'runway':
                financial_analyzer = ReportService()
                result = financial_analyzer.generate_report('runway')
                
                if 'error' in result:
                    if 'message' in result:
                        console.print(f"[yellow]Nota:[/yellow] {result['message']}")
                        if 'suggestion' in result:
                            console.print(f"[yellow]Sugerencia:[/yellow] {result['suggestion']}")
                    else:
                        console.print(f"[bold red]Error:[/bold red] {result['error']}")
                else:
                    console.print(f"[bold]Análisis de Runway:[/bold]")
                    console.print(f"Balance actual: {result['cash_balance']:.2f}")
                    console.print(f"Tasa promedio de quema mensual: {result['avg_monthly_burn_rate']:.2f}")
                    console.print(f"Runway: {result['runway_status']}")
                    
                    if 'summary' in result:
                        console.print(Panel(result['summary'], title="Resumen", border_style="blue"))
            
            elif analysis_type == 'categories':
                report_service = ReportService()
                tx_type = parameters.get('transaction_type', 'expense')
                result = report_service.generate_report('category', parameters={'transaction_type': tx_type})
                
                if 'error' in result:
                    if 'message' in result:
                        console.print(f"[yellow]Nota:[/yellow] {result['message']}")
                        if 'suggestion' in result:
                            console.print(f"[yellow]Sugerencia:[/yellow] {result['suggestion']}")
                    else:
                        console.print(f"[bold red]Error:[/bold red] {result['error']}")
                else:
                    categories = result.get('categories', [])
                    console.print(f"[bold]Análisis de Categorías ({tx_type}):[/bold]")
                    
                    if categories:
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column("Categoría")
                        table.add_column("Monto", justify="right")
                        table.add_column("Porcentaje", justify="right")
                        
                        for cat in categories:
                            table.add_row(
                                cat['category'],
                                f"{cat['amount']:.2f}",
                                f"{cat['percentage']:.1f}%"
                            )
                        
                        console.print(table)
                    
                    if 'summary' in result:
                        console.print(Panel(result['summary'], title="Resumen", border_style="blue"))
            
            else:
                console.print(f"[yellow]Tipo de análisis no reconocido:[/yellow] {analysis_type}")
        
        elif intent == 'report_generate':
            # Generate a report
            report_type = parameters.get('report_type', 'summary')
            report_service = ReportService()
            result = report_service.generate_report(report_type)
            
            if 'error' in result:
                if 'message' in result:
                    console.print(f"[yellow]Nota:[/yellow] {result['message']}")
                    if 'suggestion' in result:
                        console.print(f"[yellow]Sugerencia:[/yellow] {result['suggestion']}")
                else:
                    console.print(f"[bold red]Error:[/bold red] {result['error']}")
            else:
                console.print(f"[bold]Reporte {report_type.capitalize()}:[/bold]")
                
                if report_type == 'summary':
                    console.print(f"Ingresos totales: {result['income']:.2f}")
                    console.print(f"Gastos totales: {result['expenses']:.2f}")
                    console.print(f"Neto: {result['net']:.2f}")
                
                elif report_type == 'cashflow':
                    monthly_data = result.get('monthly_data', [])
                    
                    if monthly_data:
                        table = Table(show_header=True, header_style="bold magenta")
                        table.add_column("Mes")
                        table.add_column("Ingresos", justify="right")
                        table.add_column("Gastos", justify="right")
                        table.add_column("Neto", justify="right")
                        table.add_column("Balance", justify="right")
                        
                        for month in monthly_data:
                            table.add_row(
                                month['month'],
                                f"{month['income']:.2f}",
                                f"{month['expenses']:.2f}",
                                f"{month['net']:.2f}",
                                f"{month['balance']:.2f}"
                            )
                        
                        console.print(table)
                
                if 'summary' in result:
                    console.print(Panel(result['summary'], title="Resumen", border_style="blue"))
        
        else:
            # General query or unknown intent
            if file:
                console.print("[yellow]Archivo adjunto detectado, pero la consulta no parece relacionada con procesamiento de documentos.[/yellow]")
                console.print("¿Quieres procesar este documento? Intenta con un comando como: 'Procesa esta factura' o 'Analiza este documento'")
            
            # Generate a response using the AI
            response = ai_engine.generate_response(text)
            console.print(Panel(response, title="Respuesta", border_style="green"))
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("[yellow]Intenta reformular tu consulta o comando.[/yellow]")

def _format_date(date_value) -> str:
    """Helper function to format dates consistently"""
    if isinstance(date_value, datetime):
        return date_value.strftime('%Y-%m-%d')
    elif isinstance(date_value, str):
        # Truncate ISO format string to just the date part
        if 'T' in date_value:
            return date_value.split('T')[0]
        elif len(date_value) > 10:
            return date_value[:10]
    return str(date_value)

def _display_transaction(transaction):
    """Helper function to display a transaction"""
    transaction_data = transaction
    if hasattr(transaction, 'model_dump'):
        transaction_data = transaction.model_dump()
    
    # Formatear la fecha apropiadamente
    date_str = _format_date(transaction_data.get('date', ''))
    
    console.print(Panel(
        f"[bold]{'INGRESO' if transaction_data['type'] == 'income' else 'GASTO'}:[/bold] {transaction_data['description']}\n"
        f"[bold]Monto:[/bold] {transaction_data['currency']} {transaction_data['amount']:.2f}\n"
        f"[bold]Categoría:[/bold] {transaction_data['category']}\n"
        f"[bold]Fecha:[/bold] {date_str}",
        title=f"Transacción {transaction_data['id']}",
        border_style="green" if transaction_data['type'] == 'income' else "red"
    ))

def _display_document(document):
    """Helper function to display a document"""
    document_data = document
    if hasattr(document, 'model_dump'):
        document_data = document.model_dump()
    
    # Extract key information from document
    extracted_data = document_data.get('extracted_data', {})
    issuer = extracted_data.get('issuer', 'Desconocido')
    
    # Formatear la fecha apropiadamente
    date_str = 'Desconocido'
    date_value = extracted_data.get('date')
    if date_value:
        date_str = _format_date(date_value)
    
    total = extracted_data.get('total_amount', 0)
    currency = extracted_data.get('currency', 'USD')
    
    console.print(Panel(
        f"[bold]Nombre:[/bold] {document_data['name']}\n"
        f"[bold]Tipo:[/bold] {document_data['type']}\n"
        f"[bold]Emisor:[/bold] {issuer}\n"
        f"[bold]Fecha:[/bold] {date_str}\n"
        f"[bold]Monto total:[/bold] {currency} {total}",
        title=f"Documento {document_data['id']}",
        border_style="blue"
    ))