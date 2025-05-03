from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from data.supabase_client import SupabaseClient
from config.logging import logger

class FinancialAnalyzer:
    def __init__(self):
        """Initialize the financial analyzer"""
        self.supabase = SupabaseClient()
    
    def calculate_runway(self, 
                        months_back: int = 3, 
                        cash_balance: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate startup runway based on current burn rate
        
        Args:
            months_back: Number of months to look back for burn rate calculation
            cash_balance: Current cash balance, if None will use latest income minus expenses
            
        Returns:
            Dictionary with runway analysis
        """
        try:
            # Get transactions for burn rate calculation
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30 * months_back)
            
            transactions = self.supabase.list_transactions(
                limit=1000,
                date_range=[start_date.isoformat(), end_date.isoformat()]
            )
            
            if not transactions:
                # No data yet, return a friendly message
                return {
                    'message': 'No hay suficientes datos de transacciones para calcular el runway.',
                    'suggestion': 'Intenta agregar algunas transacciones primero usando comandos como "Registra un gasto de $100 en software" o "Registra un ingreso de $5000 por ventas".',
                    'cash_balance': cash_balance or 0,
                    'avg_monthly_burn_rate': 0,
                    'runway_months': 0 if cash_balance == 0 else float('inf'),
                    'runway_status': 'No hay datos suficientes para calcular',
                    'error': "No transaction data available for runway calculation"
                }
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([t.model_dump() for t in transactions])
            
            # Calculate monthly burn rate
            df['month'] = pd.to_datetime(df['date']).dt.to_period('M')
            
            monthly_data = []
            for month, group in df.groupby('month'):
                income = group[group['type'] == 'income']['amount'].sum()
                expenses = group[group['type'] == 'expense']['amount'].sum()
                net = income - expenses
                burn_rate = expenses - income if expenses > income else 0
                
                monthly_data.append({
                    'month': month.strftime('%Y-%m'),
                    'income': float(income),
                    'expenses': float(expenses),
                    'net': float(net),
                    'burn_rate': float(burn_rate)
                })
            
            # Calculate average monthly burn rate
            if monthly_data:
                avg_burn_rate = np.mean([m['burn_rate'] for m in monthly_data])
            else:
                avg_burn_rate = 0
            
            # Calculate or use provided cash balance
            if cash_balance is None:
                # Calculate from all historical data
                all_transactions = self.supabase.list_transactions(limit=10000)
                if all_transactions:
                    df_all = pd.DataFrame([t.model_dump() for t in all_transactions])
                    total_income = df_all[df_all['type'] == 'income']['amount'].sum()
                    total_expenses = df_all[df_all['type'] == 'expense']['amount'].sum()
                    cash_balance = float(total_income - total_expenses)
                else:
                    cash_balance = 0
            
            # Calculate runway in months
            runway_months = 0
            if avg_burn_rate > 0:
                runway_months = cash_balance / avg_burn_rate
            elif cash_balance > 0:
                runway_months = float('inf')  # Infinite runway if no burn
            
            # Format the result
            result = {
                'cash_balance': cash_balance,
                'avg_monthly_burn_rate': avg_burn_rate,
                'runway_months': runway_months,
                'runway_status': 'Infinite' if runway_months == float('inf') else f"{runway_months:.1f} months",
                'monthly_data': monthly_data,
                'analysis_date': datetime.now().isoformat()
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error calculating runway: {e}")
            return {"error": str(e)}
    
    def category_analysis(self, 
                         period_start: Optional[datetime] = None,
                         period_end: Optional[datetime] = None,
                         transaction_type: str = "expense") -> Dict[str, Any]:
        """
        Analyze spending/income by category
        
        Args:
            period_start: Start date for analysis
            period_end: End date for analysis
            transaction_type: 'expense' or 'income'
            
        Returns:
            Dictionary with category analysis
        """
        try:
            # Set default period (last 3 months) if not provided
            if period_end is None:
                period_end = datetime.now()
            if period_start is None:
                period_start = period_end - timedelta(days=90)
            
            filters = {
                "date_range": [period_start.isoformat(), period_end.isoformat()],
                "type": transaction_type
            }
            
            transactions = self.supabase.list_transactions(limit=1000, **filters)
            
            if not transactions:
                return {
                    "error": f"No {transaction_type} data available for the selected period",
                    "message": f"No hay datos de {transaction_type} disponibles para el período seleccionado.",
                    "suggestion": "Intenta agregar algunas transacciones primero o selecciona un período diferente."
                }
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([t.model_dump() for t in transactions])
            
            # Group by category
            category_totals = df.groupby('category')['amount'].sum().sort_values(ascending=False)
            
            # Calculate percentage of total
            total_amount = category_totals.sum()
            category_percentages = (category_totals / total_amount * 100).round(1)
            
            # Format results
            categories = []
            for category, amount in category_totals.items():
                categories.append({
                    'category': category,
                    'amount': float(amount),
                    'percentage': float(category_percentages[category])
                })
            
            result = {
                'type': transaction_type,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'total': float(total_amount),
                'categories': categories,
                'analysis_date': datetime.now().isoformat()
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error performing category analysis: {e}")
            return {"error": str(e)}
    
    def monthly_comparison(self, 
                          months_back: int = 12,
                          include_current_month: bool = True) -> Dict[str, Any]:
        """
        Analyze monthly income and expenses over time
        
        Args:
            months_back: Number of months to include in the analysis
            include_current_month: Whether to include the current month
            
        Returns:
            Dictionary with monthly comparison data
        """
        try:
            # Calculate date range
            end_date = datetime.now()
            if not include_current_month:
                # Set to end of previous month
                end_date = end_date.replace(day=1) - timedelta(days=1)
            
            start_date = end_date.replace(day=1) - timedelta(days=30 * months_back)
            
            transactions = self.supabase.list_transactions(
                limit=10000,
                date_range=[start_date.isoformat(), end_date.isoformat()]
            )
            
            if not transactions:
                return {
                    "error": "No transaction data available for monthly comparison",
                    "message": "No hay datos de transacciones disponibles para la comparación mensual.",
                    "suggestion": "Intenta agregar algunas transacciones primero para poder realizar un análisis mensual."
                }
            
            # Convert to DataFrame for easier analysis
            df = pd.DataFrame([t.model_dump() for t in transactions])
            df['date'] = pd.to_datetime(df['date'])
            df['month'] = df['date'].dt.to_period('M')
            
            # Group by month and transaction type
            monthly_data = []
            
            for month, month_group in df.groupby('month'):
                income = month_group[month_group['type'] == 'income']['amount'].sum()
                expenses = month_group[month_group['type'] == 'expense']['amount'].sum()
                net = income - expenses
                
                monthly_data.append({
                    'month': month.strftime('%Y-%m'),
                    'income': float(income),
                    'expenses': float(expenses),
                    'net': float(net)
                })
            
            # Calculate month-over-month changes
            for i in range(1, len(monthly_data)):
                curr = monthly_data[i]
                prev = monthly_data[i-1]
                
                curr['income_change'] = ((curr['income'] - prev['income']) / prev['income'] * 100) if prev['income'] else 0
                curr['expenses_change'] = ((curr['expenses'] - prev['expenses']) / prev['expenses'] * 100) if prev['expenses'] else 0
                curr['net_change'] = ((curr['net'] - prev['net']) / abs(prev['net']) * 100) if prev['net'] else 0
            
            # The first month won't have change data
            if monthly_data:
                monthly_data[0]['income_change'] = 0
                monthly_data[0]['expenses_change'] = 0
                monthly_data[0]['net_change'] = 0
            
            result = {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'monthly_data': monthly_data,
                'analysis_date': datetime.now().isoformat()
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error performing monthly comparison: {e}")
            return {"error": str(e)}