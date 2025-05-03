from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from uuid import UUID
import json

from data.models import Transaction, TransactionCreate, TransactionType
from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient
from core.ai_engine import AIEngine
from utils.embedding_utils import generate_embedding
from config.logging import logger

class TransactionService:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.pinecone = PineconeClient()
        self.ai_engine = AIEngine()
    
    def process_natural_language(self, text: str) -> Dict[str, Any]:
        """Process natural language input to extract transaction data"""
        transaction_data = self.ai_engine.extract_transaction_data(text)
    
        # Asegurarnos de que tags sea un diccionario
        if 'tags' in transaction_data and not isinstance(transaction_data['tags'], dict):
            transaction_data['tags'] = {}
        
        return transaction_data
    
    def create_from_text(self, text: str) -> Dict[str, Any]:
        """Create a transaction from natural language text"""
        try:
            # Extract transaction data from text
            transaction_data = self.process_natural_language(text)
            
            # Check if this is a recurring transaction
            is_recurring = transaction_data.pop("recurring", False)
            frequency = transaction_data.pop("frequency", None)
            start_date = transaction_data.pop("start_date", None)
            end_date = transaction_data.pop("end_date", None)
            
            if is_recurring and frequency:
                # Handle as recurring transaction
                from services.recurring_service import RecurringService
                recurring_service = RecurringService()
                
                # Create recurring item first
                recurring_data = {
                    "type": transaction_data["type"],
                    "amount": transaction_data["amount"],
                    "currency": transaction_data["currency"],
                    "description": transaction_data["description"],
                    "category": transaction_data["category"],
                    "frequency": frequency,
                    "start_date": start_date or transaction_data["date"],
                    "end_date": end_date,
                    "metadata": {"source": "natural_language", "original_text": text}
                }
                
                recurring_item = recurring_service.create(recurring_data)
                
                # Now create the first transaction linked to the recurring item
                transaction_data["recurring_id"] = recurring_item.id
                
                # Create the transaction
                result = self.create(transaction_data)
                
                return {
                    "success": True,
                    "transaction": result,
                    "recurring_item": recurring_item,
                    "message": f"Created recurring {transaction_data['type']} of {transaction_data['currency']} {transaction_data['amount']} for {transaction_data['description']}"
                }
            else:
                # Handle as regular transaction
                result = self.create(transaction_data)
                
                return {
                    "success": True,
                    "transaction": result,
                    "message": f"Created {transaction_data['type']} of {transaction_data['currency']} {transaction_data['amount']} for {transaction_data['description']}"
                }
        
        except Exception as e:
            logger.error(f"Error creating transaction from text: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def create(self, transaction_data: Dict[str, Any]) -> Transaction:
        """Create a new transaction"""
        try:
            # Prepare transaction data
            create_data = TransactionCreate(**transaction_data)
            
            # Create transaction in Supabase
            created_transaction = self.supabase.create_transaction(create_data)
            
            # Generate embedding for semantic search
            description = transaction_data["description"]
            category = transaction_data["category"]
            search_text = f"{description} {category} {transaction_data['type']}"
            
            embedding = generate_embedding(search_text)
            
            # Store embedding in Pinecone
            # Convertir fecha a string si es un objeto datetime
            date_value = transaction_data["date"]
            if isinstance(date_value, datetime):
                date_str = date_value.isoformat()
            else:
                date_str = str(date_value)
                
            metadata = {
                "type": transaction_data["type"],
                "amount": float(transaction_data["amount"]),
                "currency": transaction_data["currency"],
                "category": transaction_data["category"],
                "date": date_str,
                "description": transaction_data["description"],
                "reference_type": "transaction"
            }
            
            self.pinecone.upsert_vector(
                id=created_transaction.id,
                vector=embedding,
                metadata=metadata
            )
            
            # Update transaction with embedding in Supabase
            self.supabase.update_transaction(
                created_transaction.id, 
                {"embedding": embedding}
            )
            
            return created_transaction
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            raise
    
    def get(self, transaction_id: Union[str, UUID]) -> Optional[Transaction]:
        """Get a transaction by ID"""
        return self.supabase.get_transaction(transaction_id)
    
    def update(self, transaction_id: Union[str, UUID], data: Dict[str, Any]) -> Transaction:
        """Update a transaction"""
        try:
            # Update transaction in Supabase
            updated_transaction = self.supabase.update_transaction(transaction_id, data)
            
            # If description or category changed, update embedding
            if "description" in data or "category" in data:
                # Get full transaction to create embedding
                transaction = self.supabase.get_transaction(transaction_id)
                
                search_text = f"{transaction.description} {transaction.category} {transaction.type.value}"
                embedding = generate_embedding(search_text)
                
                # Update embedding in Supabase
                self.supabase.update_transaction(transaction_id, {"embedding": embedding})
                
                # Convert date to string if it's a datetime object
                date_value = transaction.date
                if isinstance(date_value, datetime):
                    date_str = date_value.isoformat()
                else:
                    date_str = str(date_value)
                
                # Update embedding in Pinecone
                metadata = {
                    "type": transaction.type.value,
                    "amount": float(transaction.amount),
                    "currency": transaction.currency,
                    "category": transaction.category,
                    "date": date_str,
                    "description": transaction.description,
                    "reference_type": "transaction"
                }
                
                self.pinecone.upsert_vector(
                    id=transaction_id,
                    vector=embedding,
                    metadata=metadata
                )
            
            return updated_transaction
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            raise
    
    def delete(self, transaction_id: Union[str, UUID]) -> bool:
        """Delete a transaction"""
        try:
            # Delete from Supabase
            result = self.supabase.delete_transaction(transaction_id)
            
            # Delete from Pinecone
            self.pinecone.delete_vector(transaction_id)
            
            return result
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            raise
    
    def list(self, limit: int = 100, offset: int = 0, **filters) -> List[Transaction]:
        """List transactions with optional filters"""
        return self.supabase.list_transactions(limit, offset, **filters)
    
    def search(self, query: str, limit: int = 5, **filters) -> List[Dict[str, Any]]:
        """Search for transactions similar to the query text"""
        try:
            # Use the search engine to search for transactions
            from core.search_engine import SearchEngine
            search_engine = SearchEngine()
            
            return search_engine.search_transactions(query, limit, filters)
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []