from typing import List, Dict, Any, Optional
import numpy as np
# Importamos solo lo que necesitamos, para evitar problemas
from utils.embedding_utils import generate_embedding
from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient
from config.logging import logger

# Añadimos la función calculate_similarity aquí si es necesario
def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    try:
        # Convert to numpy arrays
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        # Calculate cosine similarity
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating similarity: {e}")
        return 0.0

class SearchEngine:
    def __init__(self):
        """Initialize the search engine"""
        self.supabase = SupabaseClient()
        self.pinecone = PineconeClient()
    
    def search_transactions(self, query: str, limit: int = 5, 
                           filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search for transactions using semantic search
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            filters: Optional filters (e.g., date range, category)
            
        Returns:
            List of matching transactions
        """
        try:
            # Generate embedding for the query
            query_embedding = generate_embedding(query)
            
            # Search in Pinecone
            filter_dict = {}
            if filters:
                # Convert filters to Pinecone format
                for key, value in filters.items():
                    if key == "type":
                        filter_dict["type"] = {"$eq": value}
                    elif key == "category":
                        filter_dict["category"] = {"$eq": value}
                    elif key == "min_amount":
                        filter_dict["amount"] = {"$gte": value}
                    elif key == "max_amount":
                        if "amount" not in filter_dict:
                            filter_dict["amount"] = {}
                        filter_dict["amount"]["$lte"] = value
                    # Add more filters as needed
            
            results = self.pinecone.query_vector(
                vector=query_embedding,
                filter=filter_dict if filter_dict else None,
                top_k=limit,
                include_metadata=True
            )
            
            # Convert results to list of transactions
            transactions = []
            
            # Check if we have matches
            if "matches" in results and results["matches"]:
                for match in results["matches"]:
                    # Get full transaction from Supabase
                    transaction_id = match["id"]
                    transaction = self.supabase.get_transaction(transaction_id)
                    
                    if transaction:
                        # Add similarity score to transaction
                        transaction_dict = transaction.model_dump()
                        transaction_dict["similarity"] = match["score"]
                        transactions.append(transaction_dict)
            
            return transactions
        
        except Exception as e:
            logger.error(f"Error searching transactions: {e}")
            return []
    
    def search_documents(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for documents using semantic search"""
        try:
            # Generate embedding for the query
            query_embedding = generate_embedding(query)
            
            # Search in Pinecone with filter for documents
            results = self.pinecone.query_vector(
                vector=query_embedding,
                filter={"type": {"$eq": "document"}},
                top_k=limit,
                include_metadata=True
            )
            
            # Convert results to list of documents
            documents = []
            
            # Check if we have matches
            if "matches" in results and results["matches"]:
                for match in results["matches"]:
                    # Get full document from Supabase
                    document_id = match["id"]
                    document = self.supabase.get_document(document_id)
                    
                    if document:
                        # Add similarity score to document
                        document_dict = document.model_dump()
                        document_dict["similarity"] = match["score"]
                        documents.append(document_dict)
            
            return documents
        
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []
    
    def text_search(self, query: str, 
                   reference_type: Optional[str] = None, 
                   limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform a text-based search using Supabase's full-text search
        
        Args:
            query: The search query
            reference_type: Optional type filter (e.g., "transaction", "document")
            limit: Maximum number of results to return
            
        Returns:
            List of matching items
        """
        try:
            # Use Supabase's text search
            results = self.supabase.search_text(query, reference_type, limit)
            
            # Process and return results
            return [item.model_dump() for item in results]
        except Exception as e:
            logger.error(f"Error performing text search: {e}")
            return []