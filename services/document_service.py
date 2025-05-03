from typing import Dict, Any, List, Optional, Union, BinaryIO
from uuid import UUID

from data.models import Document, DocumentType
from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient
from core.document_processor import DocumentProcessor
from core.ai_engine import AIEngine
from utils.embedding_utils import generate_embedding
from config.logging import logger

class DocumentService:
    def __init__(self):
        self.supabase = SupabaseClient()
        self.pinecone = PineconeClient()
        self.ai_engine = AIEngine()
        self.document_processor = DocumentProcessor(self.ai_engine)
    
    def process_document(self, file_obj: BinaryIO, filename: str) -> Dict[str, Any]:
        """Process a document file and extract information"""
        try:
            # Process document using the document processor
            result = self.document_processor.process_document(file_obj, filename)
            
            if not result.get("success", False):
                return result
            
            # Store the file in Supabase Storage
            file_path = f"documents/{filename}"
            file_obj.seek(0)  # Reset file pointer to beginning
            public_url = self.supabase.upload_file("documents", file_path, file_obj.read())
            
            # Create document record in database
            document_data = {
                "name": filename,
                "type": result["document_type"],
                "file_path": file_path,
                "content_text": result["content_text"],
                "extracted_data": result["extracted_data"],
                "embedding": result["embedding"],
                "metadata": {
                    "public_url": public_url,
                    "processed_at": result.get("processed_at", None)
                }
            }
            
            # Create document in Supabase
            document = self.supabase.create_document(document_data)
            
            # Store embedding in Pinecone
            metadata = {
                "name": filename,
                "type": result["document_type"],
                "extracted_data": {k: str(v) for k, v in result["extracted_data"].items() if k in ["issuer", "date", "total_amount", "currency"]},
                "reference_type": "document"
            }
            
            self.pinecone.upsert_vector(
                id=document.id,
                vector=result["embedding"],
                metadata=metadata
            )
            
            # Check if we should create a transaction from this document
            transaction_id = None
            if result["document_type"] in ["invoice", "receipt"]:
                # Create transaction from document
                transaction_id = self._create_transaction_from_document(document, result["extracted_data"])
                
                if transaction_id:
                    # Update document with transaction reference
                    self.supabase.update_document(document.id, {"transaction_id": transaction_id})
            
            return {
                "success": True,
                "document": document,
                "transaction_id": transaction_id,
                "message": f"Successfully processed document: {filename}"
            }
        
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_transaction_from_document(self, document: Document, extracted_data: Dict[str, Any]) -> Optional[UUID]:
        """Create a transaction from document data"""
        try:
            from services.transaction_service import TransactionService
            transaction_service = TransactionService()
            
            # Determine transaction type (receipts are expenses, invoices might be either)
            transaction_type = "expense"
            if document.type == "invoice" and extracted_data.get("role") == "issuer":
                transaction_type = "income"
                
            # Prepare transaction data
            transaction_data = {
                "type": transaction_type,
                "amount": extracted_data.get("total_amount", 0),
                "currency": extracted_data.get("currency", "USD"),
                "description": f"{extracted_data.get('issuer', 'Unknown')} - {document.name}",
                "category": self._guess_category(extracted_data, transaction_type),
                "date": extracted_data.get("date", None),
                "payment_date": extracted_data.get("payment_date", None),
                "document_id": str(document.id),
                "metadata": {
                    "document_reference": str(document.id),
                    "document_type": document.type,
                    "reference_number": extracted_data.get("reference_number", None),
                    "items": extracted_data.get("items", [])
                }
            }
            
            # Create the transaction
            transaction = transaction_service.create(transaction_data)
            
            return transaction.id
        except Exception as e:
            logger.error(f"Error creating transaction from document: {e}")
            return None
    
    def _guess_category(self, extracted_data: Dict[str, Any], transaction_type: str) -> str:
        """Guess an appropriate category based on document data"""
        # This is a simplified implementation, could be improved with more sophisticated logic
        description = extracted_data.get("description", "").lower()
        issuer = extracted_data.get("issuer", "").lower()
        
        if transaction_type == "income":
            return "Revenue"
        
        # Try to guess expense category
        if any(term in description or term in issuer for term in ["hosting", "server", "cloud", "aws", "azure", "domain"]):
            return "Software"
        elif any(term in description or term in issuer for term in ["salary", "compensation", "bonus", "payroll"]):
            return "Payroll"
        elif any(term in description or term in issuer for term in ["ad", "marketing", "promotion", "campaign"]):
            return "Marketing"
        elif any(term in description or term in issuer for term in ["office", "supplies", "furniture", "rent"]):
            return "Office"
        elif any(term in description or term in issuer for term in ["legal", "lawyer", "attorney", "compliance"]):
            return "Legal"
        elif any(term in description or term in issuer for term in ["tax", "taxes", "duty", "vat", "iva"]):
            return "Taxes"
        
        # Default
        return "Other Expense"
    
    def get(self, document_id: Union[str, UUID]) -> Optional[Document]:
        """Get a document by ID"""
        return self.supabase.get_document(document_id)
    
    def update(self, document_id: Union[str, UUID], data: Dict[str, Any]) -> Document:
        """Update a document"""
        try:
            # Update document in Supabase
            document = self.supabase.update_document(document_id, data)
            
            # If content_text changed, update embedding
            if "content_text" in data:
                content_text = data["content_text"]
                embedding = generate_embedding(content_text)
                
                # Update embedding in Supabase
                self.supabase.update_document(document_id, {"embedding": embedding})
                
                # Get full document
                full_doc = self.supabase.get_document(document_id)
                
                # Update embedding in Pinecone
                metadata = {
                    "name": full_doc.name,
                    "type": full_doc.type,
                    "extracted_data": {} if not full_doc.extracted_data else {k: str(v) for k, v in full_doc.extracted_data.items() if k in ["issuer", "date", "total_amount", "currency"]},
                    "reference_type": "document"
                }
                
                self.pinecone.upsert_vector(
                    id=document_id,
                    vector=embedding,
                    metadata=metadata
                )
            
            return document
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise
    
    def delete(self, document_id: Union[str, UUID]) -> bool:
        """Delete a document"""
        try:
            # Get document to get file path
            document = self.supabase.get_document(document_id)
            
            if document:
                # Delete file from storage
                self.supabase.delete_file("documents", document.file_path)
                
                # Delete document from database
                result = self.supabase.delete_document(document_id)
                
                # Delete from Pinecone
                self.pinecone.delete_vector(document_id)
                
                return result
            return False
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    def list(self, limit: int = 100, offset: int = 0, **filters) -> List[Document]:
        """List documents with optional filters"""
        return self.supabase.list_documents(limit, offset, **filters)
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documents similar to the query text"""
        try:
            # Use the search engine to search for documents
            from core.search_engine import SearchEngine
            search_engine = SearchEngine()
            
            return search_engine.search_documents(query, limit)
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []