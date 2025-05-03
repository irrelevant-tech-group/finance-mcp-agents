from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field, validator

# Enums para tipos y categorías
class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"

class DocumentType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CONTRACT = "contract"
    OTHER = "other"

class FrequencyType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    BOTH = "both"

# Modelos base
class BaseDBModel(BaseModel):
    id: Optional[UUID] = Field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# Modelos principales
class Transaction(BaseDBModel):
    type: TransactionType
    amount: float
    currency: str = "USD"
    description: str
    category: str
    tags: Optional[Dict[str, Any]] = None  # Asegurarnos de que sea un diccionario
    date: datetime
    payment_date: Optional[datetime] = None
    recurring_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('El monto debe ser mayor que cero')
        return v

class RecurringItem(BaseDBModel):
    type: TransactionType
    amount: float
    currency: str = "USD"
    description: str
    category: str
    frequency: FrequencyType
    start_date: datetime
    end_date: Optional[datetime] = None
    next_date: datetime
    metadata: Optional[Dict[str, Any]] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('El monto debe ser mayor que cero')
        return v

class Document(BaseDBModel):
    name: str
    type: DocumentType
    file_path: str
    content_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    transaction_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None

class Projection(BaseDBModel):
    name: str
    start_date: datetime
    end_date: datetime
    data: Dict[str, Any]
    assumptions: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None

class Category(BaseDBModel):
    name: str
    type: CategoryType
    description: Optional[str] = None
    parent_id: Optional[UUID] = None

class SearchIndex(BaseDBModel):
    reference_type: str
    reference_id: UUID
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None

# Modelos para crear y responder
class TransactionCreate(BaseModel):
    type: TransactionType
    amount: float
    currency: str = "USD"
    description: str
    category: str
    tags: Optional[Dict[str, Any]] = None
    date: datetime
    payment_date: Optional[datetime] = None
    recurring_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = None

class RecurringItemCreate(BaseModel):
    type: TransactionType
    amount: float
    currency: str = "USD"
    description: str
    category: str
    frequency: FrequencyType
    start_date: datetime
    end_date: Optional[datetime] = None
    next_date: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None