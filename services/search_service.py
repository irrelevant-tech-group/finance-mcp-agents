from typing import Dict, Any, List, Optional
from core.search_engine import SearchEngine
from core.ai_engine import AIEngine
from config.logging import logger

class SearchService:
    def __init__(self):
        self.search_engine = SearchEngine()
        self.ai_engine = AIEngine()
    
    def search(self, query: str, search_type: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """
        Search for content based on natural language query
        
        Args:
            query: The search query in natural language
            search_type: Optional type of search ('transactions', 'documents', 'all')
            limit: Maximum number of results to return
            
        Returns:
            Dictionary with search results
        """
        try:
            # Analyze the query to understand intent
            query_analysis = self.ai_engine.analyze_financial_query(query)
            intent = query_analysis.get('intent', 'general_query')
            parameters = query_analysis.get('parameters', {})
            
            # Default to 'all' if not specified
            if not search_type:
                # Guess search type based on intent
                if intent == 'transaction_search' or intent == 'transaction_list':
                    search_type = 'transactions'
                elif intent == 'document_process' or 'document' in query.lower():
                    search_type = 'documents'
                else:
                    search_type = 'all'
            
            results = {
                'query': query,
                'intent': intent,
                'parameters': parameters,
                'transactions': [],
                'documents': []
            }
            
            # Extract filters from parameters
            filters = {}
            if 'filters' in parameters:
                filters = parameters['filters']
            
            # Perform search based on type
            if search_type in ['transactions', 'all']:
                transactions = self.search_engine.search_transactions(query, limit, filters)
                results['transactions'] = transactions
            
            if search_type in ['documents', 'all']:
                documents = self.search_engine.search_documents(query, limit)
                results['documents'] = documents
            
            # Generate a human-friendly response
            explanation = self._generate_search_explanation(results)
            results['explanation'] = explanation
            
            return results
        
        except Exception as e:
            logger.error(f"Error performing search: {e}")
            return {
                'error': str(e),
                'query': query,
                'transactions': [],
                'documents': []
            }
    
    def search_text(self, query: str, reference_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Perform text-based search (not semantic search)
        
        Args:
            query: The search query text
            reference_type: Optional type filter
            limit: Maximum number of results to return
            
        Returns:
            List of results
        """
        try:
            return self.search_engine.text_search(query, reference_type, limit)
        except Exception as e:
            logger.error(f"Error performing text search: {e}")
            return []
    
    def _generate_search_explanation(self, results: Dict[str, Any]) -> str:
        """Generate a human-friendly explanation of search results"""
        try:
            transactions = results.get('transactions', [])
            documents = results.get('documents', [])
            
            if not transactions and not documents:
                return "No results found for your query. Try different search terms or broaden your search."
            
            explanation = []
            
            if transactions:
                if len(transactions) == 1:
                    tx = transactions[0]
                    explanation.append(f"Found 1 transaction: {tx['type']} of {tx['currency']} {tx['amount']} for {tx['description']} on {tx['date'][:10]}.")
                else:
                    explanation.append(f"Found {len(transactions)} transactions.")
                    # Summarize transaction types
                    expenses = sum(1 for t in transactions if t['type'] == 'expense')
                    incomes = sum(1 for t in transactions if t['type'] == 'income')
                    
                    if expenses > 0:
                        explanation.append(f"- {expenses} {'expense' if expenses == 1 else 'expenses'}")
                    if incomes > 0:
                        explanation.append(f"- {incomes} {'income' if incomes == 1 else 'incomes'}")
            
            if documents:
                if len(documents) == 1:
                    doc = documents[0]
                    explanation.append(f"Found 1 document: {doc['name']} (type: {doc['type']}).")
                else:
                    explanation.append(f"Found {len(documents)} documents.")
                    # Summarize document types
                    doc_types = {}
                    for d in documents:
                        doc_type = d['type']
                        doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                    
                    for doc_type, count in doc_types.items():
                        explanation.append(f"- {count} {doc_type}{'s' if count > 1 else ''}")
            
            return "\n".join(explanation)
            
        except Exception as e:
            logger.error(f"Error generating search explanation: {e}")
            return "Search results found. Unable to generate detailed explanation."