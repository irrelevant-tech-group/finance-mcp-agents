# scripts/generate_test_data.py

import os
import sys
import random
from datetime import datetime, timedelta
import uuid

# Asegurarnos de que podemos importar desde nuestros módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient
from services.transaction_service import TransactionService
from services.recurring_service import RecurringService
from utils.embedding_utils import generate_embedding
from config.logging import logger

def generate_test_data(num_transactions=50, num_recurring=5):
    """Generate test data for the system"""
    print(f"Generating {num_transactions} test transactions and {num_recurring} recurring items...")
    
    # Initialize clients
    supabase = SupabaseClient()
    pinecone = PineconeClient()
    
    # Initialize services
    tx_service = TransactionService()
    recurring_service = RecurringService()
    
    # Sample data
    expense_categories = [
        "Software", "Payroll", "Marketing", "Office", "Services", 
        "Hardware", "Travel", "Legal", "Taxes", "Other Expense"
    ]
    
    income_categories = [
        "Revenue", "Investment", "Grant", "Interest", "Other Income"
    ]
    
    expense_descriptions = [
        "AWS Cloud Services", "Google Workspace", "Office Rent", "Team Lunch", 
        "Software Licenses", "Developer Tools", "Marketing Campaign", 
        "Legal Consultation", "Hardware Purchase", "Conference Tickets"
    ]
    
    income_descriptions = [
        "Client Payment", "Product Sales", "Service Fee", "Consulting",
        "Investment Round", "Grant Disbursement", "Affiliate Revenue"
    ]
    
    # Generate transactions
    for i in range(num_transactions):
        # Randomize transaction data
        transaction_type = "expense" if random.random() < 0.7 else "income"
        
        # Date within the last 6 months
        days_ago = random.randint(0, 180)
        transaction_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        
        if transaction_type == "expense":
            category = random.choice(expense_categories)
            description = random.choice(expense_descriptions)
            amount = round(random.uniform(10, 2000), 2)
        else:
            category = random.choice(income_categories)
            description = random.choice(income_descriptions)
            amount = round(random.uniform(500, 10000), 2)
        
        # Create transaction data
        transaction_data = {
            "type": transaction_type,
            "amount": amount,
            "currency": "USD",
            "description": f"{description} #{i+1}",
            "category": category,
            "date": transaction_date,
            "metadata": {"test_data": True, "generated_at": datetime.now().isoformat()}
        }
        
        # Create transaction
        try:
            tx = tx_service.create(transaction_data)
            print(f"Created {transaction_type}: {description} #{i+1} - ${amount}")
        except Exception as e:
            print(f"Error creating transaction: {e}")
    
    # Generate recurring items
    for i in range(num_recurring):
        # Randomize recurring data
        transaction_type = "expense" if random.random() < 0.7 else "income"
        
        if transaction_type == "expense":
            category = random.choice(expense_categories)
            description = f"Recurring {random.choice(expense_descriptions)}"
            amount = round(random.uniform(10, 500), 2)
        else:
            category = random.choice(income_categories)
            description = f"Recurring {random.choice(income_descriptions)}"
            amount = round(random.uniform(500, 5000), 2)
        
        # Random frequency
        frequency = random.choice(["monthly", "quarterly", "yearly"])
        
        # Start date within the last 30 days
        days_ago = random.randint(0, 30)
        start_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
        
        # Calculate next date
        if frequency == "monthly":
            next_date = (datetime.now() + timedelta(days=30 - days_ago)).isoformat()
        elif frequency == "quarterly":
            next_date = (datetime.now() + timedelta(days=90 - days_ago)).isoformat()
        else:  # yearly
            next_date = (datetime.now() + timedelta(days=365 - days_ago)).isoformat()
        
        # Create recurring data
        recurring_data = {
            "type": transaction_type,
            "amount": amount,
            "currency": "USD",
            "description": f"{description} #{i+1}",
            "category": category,
            "frequency": frequency,
            "start_date": start_date,
            "next_date": next_date,
            "metadata": {"test_data": True, "generated_at": datetime.now().isoformat()}
        }
        
        # Create recurring item
        try:
            item = recurring_service.create(recurring_data)
            print(f"Created recurring {transaction_type}: {description} #{i+1} - ${amount} ({frequency})")
        except Exception as e:
            print(f"Error creating recurring item: {e}")
    
    print("\nTest data generation complete!")

if __name__ == "__main__":
    # Parse command line arguments
    num_tx = 50
    num_rec = 5
    
    if len(sys.argv) > 1:
        try:
            num_tx = int(sys.argv[1])
        except:
            pass
    
    if len(sys.argv) > 2:
        try:
            num_rec = int(sys.argv[2])
        except:
            pass
    
    generate_test_data(num_tx, num_rec)