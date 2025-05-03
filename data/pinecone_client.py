import os
from typing import List, Dict, Any, Union, Optional
from uuid import UUID
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from config.logging import logger

load_dotenv()

class PineconeClient:
    def __init__(self):
        """Initialize Pinecone client with API key from environment"""
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.environment = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")
        self.dimension = int(os.getenv("VECTOR_DIMENSION", "1536"))
        self.index_name = "finance-ai-index"
        self.client = Pinecone(api_key=self.api_key)
    
    def setup_index(self):
        """Create the index if it doesn't exist"""
        try:
            # Verificar si el índice ya existe
            existing_indexes = self.client.list_indexes().names()
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone serverless index: {self.index_name}")
                
                # Crear índice serverless - Se requiere especificar cloud y region
                # Según la documentación reciente, especificar "aws" y "us-east-1" debe funcionar para el plan gratuito
                self.client.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                
                logger.info(f"Created Pinecone serverless index: {self.index_name}")
            else:
                logger.info(f"Pinecone index {self.index_name} already exists")
                
            # Connect to the index
            self.index = self.client.Index(self.index_name)
            return self.index
        except Exception as e:
            logger.error(f"Error setting up Pinecone index: {e}")
            raise
    
    def get_index(self):
        """Get the index instance"""
        if not hasattr(self, 'index'):
            # Connect to the index
            self.index = self.client.Index(self.index_name)
        return self.index
    
    def upsert_vector(self, 
                      id: Union[str, UUID], 
                      vector: List[float], 
                      metadata: Optional[Dict[str, Any]] = None):
        """Upload a single vector to Pinecone index"""
        index = self.get_index()
        try:
            return index.upsert(
                vectors=[(str(id), vector, metadata)]
            )
        except Exception as e:
            logger.error(f"Error upserting vector to Pinecone: {e}")
            raise
    
    def upsert_vectors(self, vectors: List[tuple]):
        """
        Upload vectors to Pinecone index
        Each vector should be a tuple of (id, vector, metadata)
        """
        index = self.get_index()
        try:
            # Convert all IDs to strings
            formatted_vectors = []
            for id, vector, metadata in vectors:
                formatted_vectors.append((str(id), vector, metadata))
            
            return index.upsert(vectors=formatted_vectors)
        except Exception as e:
            logger.error(f"Error upserting vectors to Pinecone: {e}")
            raise
    
    def query_vector(self, 
                    vector: List[float], 
                    filter: Optional[Dict[str, Any]] = None,
                    top_k: int = 5, 
                    include_metadata: bool = True):
        """Query the index with a vector"""
        index = self.get_index()
        try:
            return index.query(
                vector=vector,
                filter=filter,
                top_k=top_k,
                include_metadata=include_metadata
            )
        except Exception as e:
            logger.error(f"Error querying Pinecone: {e}")
            raise
    
    def delete_vector(self, id: Union[str, UUID]):
        """Delete a vector from the index"""
        index = self.get_index()
        try:
            return index.delete(ids=[str(id)])
        except Exception as e:
            logger.error(f"Error deleting vector from Pinecone: {e}")
            raise
    
    def delete_vectors(self, ids: List[Union[str, UUID]]):
        """Delete vectors from the index"""
        index = self.get_index()
        try:
            # Convert all IDs to strings
            string_ids = [str(id) for id in ids]
            return index.delete(ids=string_ids)
        except Exception as e:
            logger.error(f"Error deleting vectors from Pinecone: {e}")
            raise
        
    def delete_by_metadata(self, filter: Dict[str, Any]):
        """Delete vectors matching a metadata filter"""
        index = self.get_index()
        try:
            return index.delete(filter=filter)
        except Exception as e:
            logger.error(f"Error deleting vectors by metadata from Pinecone: {e}")
            raise