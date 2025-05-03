from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import json

from data.models import RecurringItem, RecurringItemCreate, TransactionCreate, TransactionType, FrequencyType
from data.supabase_client import SupabaseClient
from config.logging import logger

class RecurringService:
    def __init__(self):
        self.supabase = SupabaseClient()
    
    def create(self, data: Dict[str, Any]) -> RecurringItem:
        """Create a new recurring item"""
        try:
            # Asegurar que todos los UUIDs se convierten a strings antes de pasarlos
            for key, value in data.items():
                if isinstance(value, UUID):
                    data[key] = str(value)
            # Prepare recurring item data
            create_data = RecurringItemCreate(**data)
            
            # Ensure next_date is set
            if not create_data.next_date:
                create_data.next_date = create_data.start_date
            
            # Create recurring item in Supabase
            recurring_item = self.supabase.create_recurring_item(create_data)
            
            return recurring_item
        except Exception as e:
            logger.error(f"Error creating recurring item: {e}")
            raise
    
    def get(self, item_id: Union[str, UUID]) -> Optional[RecurringItem]:
        """Get a recurring item by ID"""
        return self.supabase.get_recurring_item(item_id)
    
    def update(self, item_id: Union[str, UUID], data: Dict[str, Any]) -> RecurringItem:
        """Update a recurring item"""
        try:
            # Update the item in Supabase (no Vector DB update needed for recurring items)
            return self.supabase.update_recurring_item(item_id, data)
        except Exception as e:
            logger.error(f"Error updating recurring item: {e}")
            raise
    
    def delete(self, item_id: Union[str, UUID]) -> bool:
        """Delete a recurring item"""
        try:
            # This would typically also mark associated transactions as non-recurring
            return self.supabase.delete_recurring_item(item_id)
        except Exception as e:
            logger.error(f"Error deleting recurring item: {e}")
            raise
    
    def list(self, limit: int = 100, offset: int = 0, **filters) -> List[RecurringItem]:
        """List recurring items with optional filters"""
        return self.supabase.list_recurring_items(limit, offset, **filters)
    
    def process_due_items(self) -> Dict[str, Any]:
        """Process all recurring items that are due"""
        try:
            now = datetime.now()
            
            # Get all active recurring items that are due
            due_items = self.supabase.list_recurring_items(
                limit=1000,
                active=True,
                # Items where next_date is in the past or today
                next_date_max=now.isoformat()
            )
            
            if not due_items:
                return {"processed": 0, "message": "No recurring items due"}
            
            # Import transaction service here to avoid circular imports
            from services.transaction_service import TransactionService
            transaction_service = TransactionService()
            
            processed_count = 0
            for item in due_items:
                # Create a transaction for this recurring item
                transaction_data = {
                    "type": item.type.value,
                    "amount": item.amount,
                    "currency": item.currency,
                    "description": item.description,
                    "category": item.category,
                    "date": item.next_date.isoformat(),
                    "recurring_id": str(item.id),
                    "metadata": {"generated_from_recurring": True}
                }
                
                # Create the transaction
                transaction_service.create(transaction_data)
                
                # Update the next_date for this recurring item
                next_date = self._calculate_next_date(item.next_date, item.frequency)
                
                # Check if this was the last occurrence (end_date reached)
                is_last = item.end_date and next_date > item.end_date
                
                if is_last:
                    # This was the last occurrence, mark as inactive
                    self.update(item.id, {"is_active": False})
                else:
                    # Update next_date
                    self.update(item.id, {"next_date": next_date.isoformat()})
                
                processed_count += 1
            
            return {
                "processed": processed_count,
                "message": f"Successfully processed {processed_count} recurring items"
            }
        
        except Exception as e:
            logger.error(f"Error processing recurring items: {e}")
            return {"error": str(e)}
    
    def _calculate_next_date(self, current_date: datetime, frequency: FrequencyType) -> datetime:
        """Calculate the next date based on frequency"""
        if frequency == FrequencyType.DAILY:
            return current_date + timedelta(days=1)
        elif frequency == FrequencyType.WEEKLY:
            return current_date + timedelta(weeks=1)
        elif frequency == FrequencyType.MONTHLY:
            # Move to same day next month (handling month length differences)
            year = current_date.year + (current_date.month // 12)
            month = (current_date.month % 12) + 1
            day = min(current_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
            return current_date.replace(year=year, month=month, day=day)
        elif frequency == FrequencyType.QUARTERLY:
            # Move to same day 3 months later
            year = current_date.year + ((current_date.month + 3) // 12)
            month = ((current_date.month + 3) % 12) or 12
            day = min(current_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
            return current_date.replace(year=year, month=month, day=day)
        elif frequency == FrequencyType.YEARLY:
            # Move to same date next year (handling leap years)
            year = current_date.year + 1
            if current_date.month == 2 and current_date.day == 29 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                # Handle Feb 29 in leap years
                return current_date.replace(year=year, month=3, day=1)
            else:
                return current_date.replace(year=year)
        else:
            # Default to monthly if frequency not recognized
            return self._calculate_next_date(current_date, FrequencyType.MONTHLY)