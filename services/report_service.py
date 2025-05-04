from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from data.supabase_client import SupabaseClient
from core.financial_analyzer import FinancialAnalyzer
from core.ai_engine import AIEngine
from config.logging import logger

class ReportService:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.financial_analyzer = FinancialAnalyzer()
        self.ai_engine = AIEngine()
    
    def generate_report(self, report_type: str, 
                       period_start: Optional[datetime] = None,
                       period_end: Optional[datetime] = None,
                       parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a financial report
        
        Args:
            report_type: Type of report to generate
                - 'summary': Basic financial summary
                - 'cashflow': Cash flow statement
                - 'category': Category analysis
                - 'runway': Runway and burn rate analysis
                - 'comparison': Month-over-month comparison
                - 'expenses': Top expense analysis
                - 'top_expenses': Top expense analysis (alias)
            period_start: Start date for the report
            period_end: End date for the report
            parameters: Additional parameters for the report
                
        Returns:
            Dictionary with report data
        """
        try:
            # Set default period if not provided
            if period_end is None:
                period_end = datetime.now()
            if period_start is None:
                # Default to 3 months for most reports
                period_start = period_end - timedelta(days=90)
            
            # Default parameters if not provided
            if parameters is None:
                parameters = {}
            
            report_data = {}
            
            # Normalize report_type to handle case variations and synonyms
            report_type_lower = report_type.lower()
            
            # Map similar terms to standard report types
            if report_type_lower in ['summary', 'resumen', 'overview']:
                report_type = 'summary'
            elif report_type_lower in ['cashflow', 'cash', 'flujo', 'flujo_de_caja', 'cash_flow']:
                report_type = 'cashflow'
            elif report_type_lower in ['category', 'categorías', 'categorias', 'categories']:
                report_type = 'category'
            elif report_type_lower in ['runway', 'burn', 'quema', 'duracion']:
                report_type = 'runway'
            elif report_type_lower in ['comparison', 'compare', 'comparacion', 'comparación', 'monthly']:
                report_type = 'comparison'
            elif report_type_lower in ['expenses', 'expense', 'gastos', 'gasto', 'spending', 'costs', 'top_expenses']:
                report_type = 'expenses'
            
            # Generate appropriate report based on normalized type
            if report_type == 'summary':
                report_data = self._generate_summary_report(period_start, period_end)
            elif report_type == 'cashflow':
                report_data = self._generate_cashflow_report(period_start, period_end)
            elif report_type == 'category':
                transaction_type = parameters.get('transaction_type', 'expense')
                report_data = self.financial_analyzer.category_analysis(
                    period_start=period_start,
                    period_end=period_end,
                    transaction_type=transaction_type
                )
            elif report_type == 'expenses':
                # Use the specialized top expenses function
                limit = parameters.get('limit', 5)
                report_data = self.financial_analyzer.get_top_expenses(
                    period_start=period_start,
                    period_end=period_end,
                    limit=limit
                )
            elif report_type == 'runway':
                months_back = parameters.get('months_back', 3)
                cash_balance = parameters.get('cash_balance', None)
                report_data = self.financial_analyzer.calculate_runway(
                    months_back=months_back,
                    cash_balance=cash_balance
                )
            elif report_type == 'comparison':
                months_back = parameters.get('months_back', 12)
                include_current = parameters.get('include_current_month', True)
                report_data = self.financial_analyzer.monthly_comparison(
                    months_back=months_back,
                    include_current_month=include_current
                )
            else:
                # Fallback to summary report with warning
                logger.warning(f"Unknown report type '{report_type}', defaulting to summary")
                report_data = self._generate_summary_report(period_start, period_end)
                report_data['warning'] = f"Unknown report type: {report_type}. Showing summary report instead."
            
            # Add metadata to the report
            report_data.update({
                'report_type': report_type,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'generated_at': datetime.now().isoformat(),
                'parameters': parameters
            })
            
            # Generate a human-friendly summary of the report
            summary = self._generate_report_summary(report_type, report_data)
            report_data['summary'] = summary
            
            return report_data
        
        except Exception as e:
            logger.error(f"Error generating {report_type} report: {e}")
            return {
                'error': str(e),
                'report_type': report_type
            }
    
    def _generate_summary_report(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Generate a basic financial summary report"""
        try:
            # Get transactions for the period
            transactions = self.supabase.list_transactions(
                limit=10000,
                date_range=[period_start.isoformat(), period_end.isoformat()]
            )
            
            if not transactions:
                return {
                    'error': 'No transaction data available for the selected period',
                    'message': 'No hay datos de transacciones disponibles para el período seleccionado.',
                    'suggestion': 'Intenta agregar algunas transacciones primero o selecciona un período diferente.'
                }
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([t.model_dump() for t in transactions])
            
            # Calculate key metrics
            income = df[df['type'] == 'income']['amount'].sum()
            expenses = df[df['type'] == 'expense']['amount'].sum()
            net = income - expenses
            
            # Count transactions
            num_income = len(df[df['type'] == 'income'])
            num_expenses = len(df[df['type'] == 'expense'])
            
            # Top categories
            top_income_categories = df[df['type'] == 'income'].groupby('category')['amount'].sum().sort_values(ascending=False).head(3)
            top_expense_categories = df[df['type'] == 'expense'].groupby('category')['amount'].sum().sort_values(ascending=False).head(3)
            
            # Format top categories
            top_income = []
            for category, amount in top_income_categories.items():
                top_income.append({
                    'category': category,
                    'amount': float(amount),
                    'percentage': float(amount / income * 100) if income > 0 else 0
                })
            
            top_expenses = []
            for category, amount in top_expense_categories.items():
                top_expenses.append({
                    'category': category,
                    'amount': float(amount),
                    'percentage': float(amount / expenses * 100) if expenses > 0 else 0
                })
            
            # Prepare report data
            report_data = {
                'income': float(income),
                'expenses': float(expenses),
                'net': float(net),
                'num_income_transactions': num_income,
                'num_expense_transactions': num_expenses,
                'top_income_categories': top_income,
                'top_expense_categories': top_expenses
            }
            
            return report_data
        
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            raise
    
    def _generate_cashflow_report(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """Generate a cash flow report"""
        try:
            # Get transactions for the period
            transactions = self.supabase.list_transactions(
                limit=10000,
                date_range=[period_start.isoformat(), period_end.isoformat()]
            )
            
            if not transactions:
                return {
                    'error': 'No transaction data available for the selected period',
                    'message': 'No hay datos de transacciones disponibles para el período seleccionado.',
                    'suggestion': 'Intenta agregar algunas transacciones primero o selecciona un período diferente.'
                }
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([t.model_dump() for t in transactions])
            df['date'] = pd.to_datetime(df['date'])
            
            # Group by month and calculate cash flow
            df['month'] = df['date'].dt.to_period('M')
            
            monthly_data = []
            running_balance = 0
            
            for month, month_group in df.groupby('month'):
                income = month_group[month_group['type'] == 'income']['amount'].sum()
                expenses = month_group[month_group['type'] == 'expense']['amount'].sum()
                net = income - expenses
                running_balance += net
                
                monthly_data.append({
                    'month': month.strftime('%Y-%m'),
                    'income': float(income),
                    'expenses': float(expenses),
                    'net': float(net),
                    'balance': float(running_balance)
                })
            
            # Calculate totals
            total_income = df[df['type'] == 'income']['amount'].sum()
            total_expenses = df[df['type'] == 'expense']['amount'].sum()
            total_net = total_income - total_expenses
            
            # Prepare report data
            report_data = {
                'total_income': float(total_income),
                'total_expenses': float(total_expenses),
                'total_net': float(total_net),
                'final_balance': float(running_balance),
                'monthly_data': monthly_data
            }
            
            return report_data
        
        except Exception as e:
            logger.error(f"Error generating cashflow report: {e}")
            raise
    
    def _generate_report_summary(self, report_type: str, report_data: Dict[str, Any]) -> str:
        """
        Generate a human-friendly summary of the report using the AI engine
        """
        try:
            # Create a prompt for the AI to summarize the report
            if 'error' in report_data:
                return f"Error generating report: {report_data['error']}"
            
            prompt = f"""
            Please summarize the following {report_type} financial report in a concise, 
            informative way. Focus on the most important insights and trends.
            
            Report data:
            {report_data}
            
            Provide a 3-5 sentence summary with the key insights from this data.
            """
            
            # Use the AI to generate a summary
            system_prompt = """
            You are a financial analyst summarizing financial reports for a startup.
            Be clear, concise, and focus on actionable insights. Use a professional
            but accessible tone. Highlight both positive and concerning trends.
            """
            
            summary = self.ai_engine.process_text(prompt, system_prompt, temperature=0.7)
            return summary
        
        except Exception as e:
            logger.error(f"Error generating report summary: {e}")
            return "Report generated successfully. Summary not available."