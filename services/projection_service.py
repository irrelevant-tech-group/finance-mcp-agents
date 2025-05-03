from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from uuid import UUID
import json
import pandas as pd
import numpy as np

from data.models import Projection
from data.supabase_client import SupabaseClient
from core.financial_analyzer import FinancialAnalyzer
from config.logging import logger

class ProjectionService:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.financial_analyzer = FinancialAnalyzer()
    
    def create_projection(self, 
                        name: str, 
                        months: int = 12, 
                        assumptions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a financial projection
        
        Args:
            name: Name of the projection
            months: Number of months to project
            assumptions: Optional dictionary of assumptions for the projection
                - growth_rate: Monthly income growth rate (default: 0)
                - expense_rate: Monthly expense growth rate (default: 0)
                - new_revenue: Dictionary of new revenue streams by month
                - new_expenses: Dictionary of new expense items by month
                - one_time_items: List of one-time income/expenses
        
        Returns:
            The created projection
        """
        try:
            start_date = datetime.now().replace(day=1)
            end_date = start_date + timedelta(days=30 * months)
            
            # Get historical data for baseline
            runway_data = self.financial_analyzer.calculate_runway(months_back=3)
            monthly_data = self.financial_analyzer.monthly_comparison(months_back=12)
            
            # Default assumptions if not provided
            if not assumptions:
                assumptions = {
                    "growth_rate": 0,  # Monthly income growth rate
                    "expense_rate": 0,  # Monthly expense growth rate
                    "new_revenue": {},  # New revenue streams by month
                    "new_expenses": {},  # New expense items by month
                    "one_time_items": []  # One-time income/expenses
                }
            
            # Get latest monthly data for baseline
            latest_month_data = None
            if monthly_data.get("monthly_data"):
                latest_month_data = monthly_data["monthly_data"][-1]
            
            if not latest_month_data:
                return {
                    "success": False,
                    "error": "Not enough historical data for projection"
                }
            
            # Generate projected months
            projected_months = []
            
            baseline_income = latest_month_data["income"]
            baseline_expenses = latest_month_data["expenses"]
            
            for i in range(months):
                month_date = start_date + timedelta(days=30 * i)
                month_key = month_date.strftime('%Y-%m')
                
                # Apply growth rates
                income_growth = 1 + (assumptions["growth_rate"] / 100)
                expense_growth = 1 + (assumptions["expense_rate"] / 100)
                
                projected_income = baseline_income * (income_growth ** i)
                projected_expenses = baseline_expenses * (expense_growth ** i)
                
                # Add new revenue streams for this month
                if month_key in assumptions["new_revenue"]:
                    for item in assumptions["new_revenue"][month_key]:
                        projected_income += item["amount"]
                
                # Add new expense items for this month
                if month_key in assumptions["new_expenses"]:
                    for item in assumptions["new_expenses"][month_key]:
                        projected_expenses += item["amount"]
                
                # Add one-time items
                for item in assumptions["one_time_items"]:
                    if item["month"] == month_key:
                        if item["type"] == "income":
                            projected_income += item["amount"]
                        else:
                            projected_expenses += item["amount"]
                
                projected_months.append({
                    "month": month_key,
                    "income": float(projected_income),
                    "expenses": float(projected_expenses),
                    "net": float(projected_income - projected_expenses)
                })
            
            # Calculate projected cash balance
            initial_balance = runway_data.get("cash_balance", 0)
            running_balance = initial_balance
            
            for month in projected_months:
                running_balance += month["net"]
                month["balance"] = float(running_balance)
            
            # Calculate runway
            last_balance = projected_months[-1]["balance"]
            avg_burn = 0
            burn_months = [m for m in projected_months if m["net"] < 0]
            
            if burn_months:
                avg_burn = np.mean([abs(m["net"]) for m in burn_months])
            
            projected_runway = 0
            if avg_burn > 0:
                projected_runway = last_balance / avg_burn
            elif last_balance > 0:
                projected_runway = float('inf')  # Infinite runway
            
            # Create projection data
            projection_data = {
                "name": name,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": {
                    "months": projected_months,
                    "initial_balance": float(initial_balance),
                    "final_balance": float(last_balance),
                    "avg_monthly_burn": float(avg_burn),
                    "projected_runway": float(projected_runway)
                },
                "assumptions": assumptions,
                "created_by": "AI Financial Assistant"
            }
            
            # Store projection in database
            projection = self.supabase.create_projection(projection_data)
            
            return {
                "success": True,
                "projection": projection,
                "message": f"Created {months}-month projection: {name}"
            }
        
        except Exception as e:
            logger.error(f"Error creating projection: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get(self, projection_id: Union[str, UUID]) -> Optional[Projection]:
        """Get a projection by ID"""
        return self.supabase.get_projection(projection_id)
    
    def update(self, projection_id: Union[str, UUID], data: Dict[str, Any]) -> Projection:
        """Update a projection"""
        try:
            return self.supabase.update_projection(projection_id, data)
        except Exception as e:
            logger.error(f"Error updating projection: {e}")
            raise
    
    def delete(self, projection_id: Union[str, UUID]) -> bool:
        """Delete a projection"""
        try:
            return self.supabase.delete_projection(projection_id)
        except Exception as e:
            logger.error(f"Error deleting projection: {e}")
            raise
    
    def list(self, limit: int = 100, offset: int = 0) -> List[Projection]:
        """List projections"""
        return self.supabase.list_projections(limit, offset)