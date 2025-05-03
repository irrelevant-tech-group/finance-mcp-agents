import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def create_tables():
    """Creates all necessary tables in Supabase"""
    print("Creating tables in Supabase...")
    
    # Create transactions table
    supabase.table("transactions").execute()
    transactions_sql = """
    CREATE TABLE IF NOT EXISTS transactions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense')),
        amount DECIMAL(12, 2) NOT NULL,
        currency VARCHAR(5) NOT NULL DEFAULT 'USD',
        description TEXT NOT NULL,
        category VARCHAR(100) NOT NULL,
        tags JSONB,
        date TIMESTAMP WITH TIME ZONE NOT NULL,
        payment_date TIMESTAMP WITH TIME ZONE,
        recurring_id UUID,
        document_id UUID,
        metadata JSONB,
        embedding JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create recurring_items table
    recurring_items_sql = """
    CREATE TABLE IF NOT EXISTS recurring_items (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense')),
        amount DECIMAL(12, 2) NOT NULL,
        currency VARCHAR(5) NOT NULL DEFAULT 'USD',
        description TEXT NOT NULL,
        category VARCHAR(100) NOT NULL,
        frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly', 'quarterly', 'yearly')),
        start_date TIMESTAMP WITH TIME ZONE NOT NULL,
        end_date TIMESTAMP WITH TIME ZONE,
        next_date TIMESTAMP WITH TIME ZONE NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create documents table
    documents_sql = """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        type VARCHAR(20) NOT NULL CHECK (type IN ('invoice', 'receipt', 'contract', 'other')),
        file_path VARCHAR(255) NOT NULL,
        content_text TEXT,
        extracted_data JSONB,
        embedding JSONB,
        transaction_id UUID,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create projections table
    projections_sql = """
    CREATE TABLE IF NOT EXISTS projections (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(255) NOT NULL,
        start_date TIMESTAMP WITH TIME ZONE NOT NULL,
        end_date TIMESTAMP WITH TIME ZONE NOT NULL,
        data JSONB NOT NULL,
        assumptions JSONB,
        created_by VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create categories table
    categories_sql = """
    CREATE TABLE IF NOT EXISTS categories (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name VARCHAR(100) NOT NULL UNIQUE,
        type VARCHAR(10) NOT NULL CHECK (type IN ('income', 'expense', 'both')),
        description TEXT,
        parent_id UUID,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create search_index table
    search_index_sql = """
    CREATE TABLE IF NOT EXISTS search_index (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        reference_type VARCHAR(50) NOT NULL,
        reference_id UUID NOT NULL,
        content TEXT NOT NULL,
        embedding JSONB,
        metadata JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Execute all SQL statements
    for sql in [transactions_sql, recurring_items_sql, documents_sql, 
                projections_sql, categories_sql, search_index_sql]:
        try:
            # Using the SQL API to execute raw SQL
            supabase.postgrest.rpc("execute_sql", {"sql": sql}).execute()
            print(f"Created table: {sql.split('CREATE TABLE IF NOT EXISTS')[1].split('(')[0].strip()}")
        except Exception as e:
            print(f"Error creating table: {e}")
    
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()