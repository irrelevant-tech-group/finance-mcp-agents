import os
import sys
import uuid
from dotenv import load_dotenv
from datetime import datetime

# Asegurarnos de que podemos importar desde nuestros módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Cargar variables de entorno
load_dotenv()

# Importar nuestros clientes
from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient

def test_supabase_connection():
    """Prueba la conexión con Supabase"""
    print("\n--- Probando conexión con Supabase ---")
    try:
        supabase = SupabaseClient()
        client = supabase.get_client()
        
        # Verificar que podemos conectarnos y hacer una consulta simple
        response = client.table("categories").select("*").limit(1).execute()
        print(f"✅ Conexión exitosa con Supabase.")
        print(f"   Número de resultados: {len(response.data)}")
        return True
    except Exception as e:
        print(f"❌ Error al conectar con Supabase: {e}")
        return False

def test_pinecone_connection():
    """Prueba la conexión con Pinecone"""
    print("\n--- Probando conexión con Pinecone ---")
    try:
        pinecone = PineconeClient()
        pinecone.index_name = "finance-ai-index"  # Asegurar que el nombre es correcto
        
        # Modificar setup_index para usar la región correcta
        index = pinecone.setup_index()
        
        # Verificar que el índice existe
        stats = index.describe_index_stats()
        print(f"✅ Conexión exitosa con Pinecone.")
        print(f"   Estadísticas del índice: {stats}")
        return True
    except Exception as e:
        print(f"❌ Error al conectar con Pinecone: {e}")
        return False

def test_embedding_generation():
    """Prueba la generación de embeddings con un método alternativo"""
    print("\n--- Probando generación de embeddings ---")
    try:
        # Importar el método actualizado
        from utils.embedding_utils import generate_embedding
        
        test_text = "Esta es una prueba de generación de embeddings para nuestro sistema financiero"
        embedding = generate_embedding(test_text)
        
        if embedding and len(embedding) > 0:
            print(f"✅ Generación de embedding exitosa.")
            print(f"   Dimensión del embedding: {len(embedding)}")
            print(f"   Primeros 5 valores: {embedding[:5]}")
            return embedding
        else:
            print(f"❌ Error al generar embedding: vector vacío")
            return None
    except Exception as e:
        print(f"❌ Error al generar embedding: {e}")
        return None

def test_pinecone_vector_operations(embedding):
    """Prueba operaciones con vectores en Pinecone"""
    print("\n--- Probando operaciones con vectores en Pinecone ---")
    try:
        if not embedding:
            print("❌ No se puede probar sin un embedding válido.")
            return False
        
        pinecone = PineconeClient()
        index = pinecone.get_index()
        
        # Crear un ID único para prueba
        test_id = str(uuid.uuid4())
        test_metadata = {
            "test": True,
            "description": "Vector de prueba",
            "timestamp": datetime.now().isoformat()
        }
        
        # Insertar vector
        print(f"   Insertando vector de prueba con ID: {test_id}")
        result = pinecone.upsert_vector(
            id=test_id,
            vector=embedding,
            metadata=test_metadata
        )
        print(f"   Resultado de inserción: {result}")
        
        # Consultar vector
        print(f"   Consultando vector similar...")
        query_result = pinecone.query_vector(
            vector=embedding,
            top_k=1,
            include_metadata=True
        )
        print(f"   Resultado de consulta: {query_result}")
        
        # Eliminar vector
        print(f"   Eliminando vector de prueba...")
        delete_result = pinecone.delete_vector(test_id)
        print(f"   Resultado de eliminación: {delete_result}")
        
        print(f"✅ Operaciones con vectores en Pinecone exitosas.")
        return True
    except Exception as e:
        print(f"❌ Error en operaciones con vectores: {e}")
        return False

if __name__ == "__main__":
    print("=== PRUEBA DE CONEXIONES ===")
    
    # Probar conexión con Supabase
    supabase_ok = test_supabase_connection()
    
    # Probar conexión con Pinecone
    pinecone_ok = test_pinecone_connection()
    
    # Probar generación de embeddings
    embedding = test_embedding_generation()
    
    # Probar operaciones con vectores en Pinecone
    if pinecone_ok and embedding:
        vector_ops_ok = test_pinecone_vector_operations(embedding)
    else:
        vector_ops_ok = False
    
    # Resumen
    print("\n=== RESUMEN DE PRUEBAS ===")
    print(f"Conexión con Supabase: {'✅ OK' if supabase_ok else '❌ ERROR'}")
    print(f"Conexión con Pinecone: {'✅ OK' if pinecone_ok else '❌ ERROR'}")
    print(f"Generación de embeddings: {'✅ OK' if embedding else '❌ ERROR'}")
    print(f"Operaciones con vectores: {'✅ OK' if vector_ops_ok else '❌ ERROR'}")
    
    if supabase_ok and pinecone_ok and embedding and vector_ops_ok:
        print("\n✅ TODAS LAS PRUEBAS EXITOSAS")
    else:
        print("\n❌ ALGUNAS PRUEBAS FALLARON")