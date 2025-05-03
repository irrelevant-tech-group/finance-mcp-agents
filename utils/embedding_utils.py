import os
from typing import List, Optional
import numpy as np
from anthropic import Anthropic
from config.settings import settings
from config.logging import logger

# Initialize Anthropic client
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def generate_embedding(text: str) -> List[float]:
    """Generate embedding vector for text"""
    try:
        # Para este proyecto, usaremos vectores simulados hasta que 
        # tengamos acceso a la API de embeddings apropiada
        logger.info("Generando embedding simulado para uso de prueba")
        
        # Crear un vector aleatorio con la dimensión correcta
        random_vector = np.random.randn(settings.VECTOR_DIMENSION)
        
        # Normalizar el vector para que tenga magnitud unitaria (cosine similarity)
        normalized_vector = random_vector / np.linalg.norm(random_vector)
        
        # Convertir a lista de float
        return normalized_vector.tolist()
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        # Return a random vector as fallback
        random_vector = np.random.randn(settings.VECTOR_DIMENSION)
        normalized_vector = random_vector / np.linalg.norm(random_vector)
        return normalized_vector.tolist()

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

def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    embeddings = []
    
    for text in texts:
        embedding = generate_embedding(text)
        embeddings.append(embedding)
    
    return embeddings