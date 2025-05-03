import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Type
from uuid import UUID
from supabase import create_client, Client
from dotenv import load_dotenv
from config.logging import logger
from .models import (
    Transaction, TransactionCreate, RecurringItem, RecurringItemCreate,
    Document, Projection, Category, SearchIndex
)

load_dotenv()

class SupabaseClient:
    def __init__(self):
        """Initialize Supabase client with credentials from environment"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client = create_client(self.url, self.key)
    
    def get_client(self):
        """Get the Supabase client instance"""
        return self.client
    
    # Transactions
    def create_transaction(self, transaction: TransactionCreate) -> Transaction:
        """Insert a new transaction"""
        try:
            data = transaction.model_dump(exclude_unset=True)
            # Convert datetime objects to ISO format strings
            for date_field in ["date", "payment_date"]:
                if date_field in data and data[date_field] is not None:
                    data[date_field] = data[date_field].isoformat()
            
            response = self.client.table("transactions").insert(data).execute()
            
            if len(response.data) > 0:
                return Transaction(**response.data[0])
            else:
                logger.error(f"Error creating transaction: {response.error}")
                raise Exception(f"Error creating transaction: {response.error}")
        except Exception as e:
            logger.error(f"Exception when creating transaction: {e}")
            raise
    
    def get_transaction(self, transaction_id: Union[str, UUID]) -> Optional[Transaction]:
        """Get a transaction by ID"""
        try:
            response = self.client.table("transactions").select("*").eq("id", str(transaction_id)).execute()
            if len(response.data) > 0:
                return Transaction(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Exception when getting transaction {transaction_id}: {e}")
            raise
    
    def update_transaction(self, transaction_id: Union[str, UUID], transaction_data: Dict[str, Any]) -> Transaction:
        """Update a transaction"""
        try:
            # Convert datetime objects to ISO format strings
            for date_field in ["date", "payment_date"]:
                if date_field in transaction_data and transaction_data[date_field] is not None:
                    if isinstance(transaction_data[date_field], datetime):
                        transaction_data[date_field] = transaction_data[date_field].isoformat()
            
            response = self.client.table("transactions").update(transaction_data).eq("id", str(transaction_id)).execute()
            
            if len(response.data) > 0:
                return Transaction(**response.data[0])
            else:
                logger.error(f"Error updating transaction: {response.error}")
                raise Exception(f"Error updating transaction: {response.error}")
        except Exception as e:
            logger.error(f"Exception when updating transaction {transaction_id}: {e}")
            raise
    
    def delete_transaction(self, transaction_id: Union[str, UUID]) -> bool:
        """Delete a transaction"""
        try:
            response = self.client.table("transactions").delete().eq("id", str(transaction_id)).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Exception when deleting transaction {transaction_id}: {e}")
            raise
    
    def list_transactions(self, limit: int = 100, offset: int = 0, **filters) -> List[Transaction]:
        """List transactions with optional filters"""
        try:
            query = self.client.table("transactions").select("*").order("date", desc=True).limit(limit).offset(offset)
            
            # Apply filters if provided
            for key, value in filters.items():
                if key == "date_range" and isinstance(value, list) and len(value) == 2:
                    query = query.gte("date", value[0].isoformat() if isinstance(value[0], datetime) else value[0])
                    query = query.lte("date", value[1].isoformat() if isinstance(value[1], datetime) else value[1])
                elif key == "category":
                    query = query.eq("category", value)
                elif key == "type":
                    query = query.eq("type", value)
                elif key == "search" and value:
                    # Full text search in description
                    query = query.ilike("description", f"%{value}%")
                # Add more filter options as needed
                
            response = query.execute()
            
            return [Transaction(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Exception when listing transactions: {e}")
            raise
    
    # Recurring Items
    def create_recurring_item(self, item: RecurringItemCreate) -> RecurringItem:
        """Insert a new recurring item"""
        try:
            data = item.model_dump(exclude_unset=True)
            
            # Convert datetime objects to ISO format strings
            for key, value in data.items():
                if isinstance(value, UUID):
                    data[key] = str(value)
            
            response = self.client.table("recurring_items").insert(data).execute()
            
            if len(response.data) > 0:
                return RecurringItem(**response.data[0])
            else:
                logger.error(f"Error creating recurring item: {response.error}")
                raise Exception(f"Error creating recurring item: {response.error}")
        except Exception as e:
            logger.error(f"Exception when creating recurring item: {e}")
            raise
    
    def get_recurring_item(self, item_id: Union[str, UUID]) -> Optional[RecurringItem]:
        """Get a recurring item by ID"""
        try:
            response = self.client.table("recurring_items").select("*").eq("id", str(item_id)).execute()
            if len(response.data) > 0:
                return RecurringItem(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Exception when getting recurring item {item_id}: {e}")
            raise
    
    def list_recurring_items(self, limit: int = 100, offset: int = 0, **filters) -> List[RecurringItem]:
        """List recurring items with optional filters"""
        try:
            query = self.client.table("recurring_items").select("*").order("next_date", desc=False).limit(limit).offset(offset)
            
            # Apply filters
            for key, value in filters.items():
                if key == "type":
                    query = query.eq("type", value)
                elif key == "category":
                    query = query.eq("category", value)
                elif key == "frequency":
                    query = query.eq("frequency", value)
                elif key == "active":
                    if value:
                        # Only active items (end_date is null or in the future)
                        query = query.or_(f"end_date.gt.{datetime.now().isoformat()},end_date.is.null")
                    else:
                        # Only inactive items (end_date is in the past)
                        query = query.lt("end_date", datetime.now().isoformat())
            
            response = query.execute()
            
            return [RecurringItem(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Exception when listing recurring items: {e}")
            raise
    
    # Documents
    def create_document(self, document: Document) -> Document:
        """Insert a new document"""
        try:
            data = document.model_dump(exclude_unset=True)
            response = self.client.table("documents").insert(data).execute()
            
            if len(response.data) > 0:
                return Document(**response.data[0])
            else:
                logger.error(f"Error creating document: {response.error}")
                raise Exception(f"Error creating document: {response.error}")
        except Exception as e:
            logger.error(f"Exception when creating document: {e}")
            raise
    
    def update_document(self, document_id: Union[str, UUID], data: Dict[str, Any]) -> Document:
        """Update a document"""
        try:
            response = self.client.table("documents").update(data).eq("id", str(document_id)).execute()
            
            if len(response.data) > 0:
                return Document(**response.data[0])
            else:
                logger.error(f"Error updating document: {response.error}")
                raise Exception(f"Error updating document: {response.error}")
        except Exception as e:
            logger.error(f"Exception when updating document {document_id}: {e}")
            raise
    
    def get_document(self, document_id: Union[str, UUID]) -> Optional[Document]:
        """Get a document by ID"""
        try:
            response = self.client.table("documents").select("*").eq("id", str(document_id)).execute()
            if len(response.data) > 0:
                return Document(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Exception when getting document {document_id}: {e}")
            raise
    
    # Categories
    def list_categories(self, type: Optional[str] = None) -> List[Category]:
        """List categories with optional type filter"""
        try:
            query = self.client.table("categories").select("*").order("name")
            
            if type:
                query = query.or_(f"type.eq.{type},type.eq.both")
            
            response = query.execute()
            
            return [Category(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Exception when listing categories: {e}")
            raise
    
    # Search Index
    def search_text(self, query: str, reference_type: Optional[str] = None, limit: int = 10) -> List[SearchIndex]:
        """Search for content using text search"""
        try:
            sql = f"""
            SELECT * 
            FROM search_index 
            WHERE to_tsvector('spanish', content) @@ plainto_tsquery('spanish', '{query}')
            """
            
            if reference_type:
                sql += f" AND reference_type = '{reference_type}'"
            
            sql += f" LIMIT {limit}"
            
            response = self.client.postgrest.rpc("execute_sql", {"sql": sql}).execute()
            
            return [SearchIndex(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Exception when searching text {query}: {e}")
            raise
    
    # Storage operations for document uploads
    def upload_file(self, bucket_name: str, file_path: str, file_data: bytes) -> str:
        """Upload a file to Supabase Storage"""
        try:
            response = self.client.storage.from_(bucket_name).upload(file_path, file_data)
            return self.client.storage.from_(bucket_name).get_public_url(file_path)
        except Exception as e:
            logger.error(f"Exception when uploading file {file_path}: {e}")
            raise
    
    def download_file(self, bucket_name: str, file_path: str) -> bytes:
        """Download a file from Supabase Storage"""
        try:
            return self.client.storage.from_(bucket_name).download(file_path)
        except Exception as e:
            logger.error(f"Exception when downloading file {file_path}: {e}")
            raise