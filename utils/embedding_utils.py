import os
from typing import List, Optional
import numpy as np
import hashlib
from config.settings import settings
from config.logging import logger

# Inicializar cliente de Anthropic (solo para generación de texto, no para embeddings)
from anthropic import Anthropic
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding vector for text using a deterministic hash-based approach
    until we can use a proper embedding API.
    """
    try:
        # Si el texto está vacío, devolver un vector de ceros
        if not text or text.strip() == "":
            logger.warning("Attempted to generate embedding for empty text")
            return np.zeros(settings.VECTOR_DIMENSION).tolist()
        
        logger.info(f"Generando embedding para texto: '{text[:50]}...'")
        
        # Generar un hash de texto para crear un vector determinista
        # Esto asegura que el mismo texto siempre genere el mismo vector
        seed = int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16) % 10000000
        np.random.seed(seed)
        
        # Generar vector aleatorio pero determinista
        random_vector = np.random.randn(settings.VECTOR_DIMENSION)
        
        # Normalizar el vector para similitud de coseno
        norm = np.linalg.norm(random_vector)
        if norm > 0:
            normalized_vector = random_vector / norm
        else:
            normalized_vector = random_vector
        
        logger.info("Embedding generado usando método basado en hash")
        return normalized_vector.tolist()
        
    except Exception as e:
        logger.error(f"Error generando embedding: {e}")
        # Si todo falla, devolver un vector de ceros
        return np.zeros(settings.VECTOR_DIMENSION).tolist()

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings"""
    try:
        # Convertir a arrays de numpy
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        # Comprobar que los vectores no son cero
        if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
            return 0.0
        
        # Calcular similitud del coseno
        similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculando similitud: {e}")
        return 0.0

def generate_batch_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    embeddings = []
    
    for text in texts:
        embedding = generate_embedding(text)
        embeddings.append(embedding)
    
    return embeddings