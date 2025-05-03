import os
from typing import Dict, Any, List, Optional
from anthropic import Anthropic
from config.settings import settings
from config.logging import logger
from datetime import datetime


class AIEngine:
    def __init__(self):
        """Initialize the AI engine with Claude"""
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-haiku-20240307"

    def process_text(
        self,
        text: str,
        system_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ) -> str:
        """Process text with Claude and return the response"""
        try:
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[{"role": "user", "content": text}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error processing text with Claude: {e}")
            raise

    def extract_transaction_data(self, text: str) -> Dict[str, Any]:
        """Extract transaction data from natural language"""
        system_prompt = """
        You are a financial assistant that extracts transaction information from text.
        Extract the following fields from the user's text and format them as a JSON object:
        - type: "income" or "expense"
        - amount: the numeric amount (as a number, not a string)
        - currency: the currency code (default to USD if not specified)
        - description: a brief description of the transaction
        - category: the category of the transaction (e.g., "Software", "Payroll", "Revenue")
        - date: the date in ISO format (YYYY-MM-DD) - default to today if not specified
        - payment_date: the payment date in ISO format (if specified, otherwise null)
        - recurring: whether this is a recurring transaction (boolean)
        - frequency: if recurring, the frequency (daily, weekly, monthly, quarterly, yearly)
        - start_date: if recurring, the start date in ISO format
        - end_date: if recurring, the end date in ISO format (if specified, otherwise null)
        - tags: a dictionary of tag key-value pairs (NOT an array)

        Only include fields that are mentioned or can be clearly inferred from the text.
        """

        try:
            response = self.process_text(text, system_prompt)

            # This would ideally be a proper JSON parser, but for simplicity we're
            # assuming the model will always return valid JSON
            import json

            data = json.loads(response)

            # Asegurarnos de que tags sea un diccionario si está presente
            if "tags" in data and not isinstance(data["tags"], dict):
                data["tags"] = {}  # Convertir a diccionario vacío
                
            # Asegurarnos de que haya una fecha (requerida)
            if 'date' not in data:
                data['date'] = datetime.now().strftime('%Y-%m-%d')

            return data
        except Exception as e:
            logger.error(f"Error extracting transaction data: {e}")
            # Return a minimal valid structure if extraction fails
            return {
                "type": "expense",
                "amount": 0,
                "currency": "USD",
                "description": text,
                "category": "Other Expense",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "tags": {},  # Asegurarnos de que sea un diccionario
            }

    def extract_document_data(
        self, text: str, document_type: str = "invoice"
    ) -> Dict[str, Any]:
        """Extract data from a document (invoice, receipt, etc.)"""
        system_prompt = f"""
        You are a financial assistant that extracts information from {document_type}s.
        Extract the following fields and format them as a JSON object:
        - type: the type of document ("{document_type}")
        - issuer: the company or person that issued the document
        - recipient: the company or person that received the document
        - date: the document date in ISO format (YYYY-MM-DD)
        - due_date: the payment due date in ISO format (if applicable)
        - total_amount: the total amount (as a number, not a string)
        - currency: the currency code (default to USD if not specified)
        - items: an array of line items, each with:
          - description: description of the item
          - quantity: quantity (as a number)
          - unit_price: price per unit (as a number)
          - amount: total for this item (as a number)
        - tax: the tax amount, if specified (as a number)
        - payment_status: whether the document has been paid ("paid", "unpaid", "partial")
        - payment_date: if paid, the payment date in ISO format (if specified, otherwise null)
        - reference_number: any invoice/receipt number or reference
        - notes: any additional relevant information

        Only include fields that are mentioned or can be clearly inferred from the text.
        """

        try:
            response = self.process_text(text, system_prompt)

            import json
            data = json.loads(response)
            
            # Asegurarnos de que haya una fecha
            if 'date' not in data:
                data['date'] = datetime.now().strftime('%Y-%m-%d')
                
            return data
        except Exception as e:
            logger.error(f"Error extracting document data: {e}")
            # Return a minimal valid structure if extraction fails
            return {
                "type": document_type,
                "issuer": "Unknown",
                "date": datetime.now().strftime('%Y-%m-%d'),
                "total_amount": 0,
                "currency": "USD",
            }

    def analyze_financial_query(self, query: str) -> Dict[str, Any]:
        """Analyze a financial query to determine its intent and parameters"""
        system_prompt = """
        You are a financial assistant that analyzes user queries to determine their intent.
        Analyze the query and classify it into one of these categories:
        - transaction_create: User wants to create a transaction
        - transaction_list: User wants to list transactions
        - transaction_search: User wants to search for specific transactions
        - document_process: User wants to process a document
        - financial_analysis: User wants a financial analysis (e.g., runway, burn rate)
        - report_generate: User wants to generate a report
        - general_query: General question about finances

        Extract any relevant parameters and format everything as a simple, valid JSON object with:
        - intent: the intent category (string)
        - parameters: an object with any relevant parameters for the intent

        Respond ONLY with the JSON object and nothing else.
        """

        try:
            response = self.process_text(query, system_prompt)

            # Clean the response to ensure it's valid JSON
            response = response.strip()

            # If response has multiple lines, join them (in case there are newlines in the JSON)
            response = "".join(line.strip() for line in response.splitlines())

            # Sometimes the AI might include markdown code blocks, remove them
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            response = response.strip()

            import json

            parsed = json.loads(response)

            # Ensure required fields exist
            if "intent" not in parsed:
                parsed["intent"] = "general_query"
            if "parameters" not in parsed:
                parsed["parameters"] = {}

            return parsed
        except Exception as e:
            logger.error(f"Error analyzing financial query: {e}")
            # Return a default analysis if it fails
            return {
                "intent": "general_query",
                "parameters": {"query": query},
            }

    def generate_response(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate a natural language response to a user query"""
        system_prompt = """
        You are a helpful financial assistant for startups. Provide clear, concise, and accurate
        responses to financial queries. If you have specific data to reference, include relevant numbers
        and insights in your response. Keep responses professional but conversational.
        """

        if context:
            # Augment the user query with context
            context_str = "\n\nContext:\n" + "\n".join(
                [f"{k}: {v}" for k, v in context.items()]
            )
            query = query + context_str

        return self.process_text(query, system_prompt, temperature=0.7)