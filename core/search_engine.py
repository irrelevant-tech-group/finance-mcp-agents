from typing import List, Dict, Any, Optional
import numpy as np
from datetime import datetime, timedelta
from utils.embedding_utils import generate_embedding, calculate_similarity
from data.supabase_client import SupabaseClient
from data.pinecone_client import PineconeClient
from config.logging import logger

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
            logger.info(f"Buscando transacciones para la consulta: '{query}'")
            
            # Analizar la consulta para extraer información temporal
            temporal_info = self._extract_temporal_info(query)
            
            # Si hay filtros explícitos, usarlos
            if not filters:
                filters = {}
            
            # Añadir filtros de fecha si se detectaron en la consulta
            if temporal_info and 'date_range' not in filters:
                filters['date_range'] = temporal_info
                logger.info(f"Filtro temporal detectado: {temporal_info[0]} a {temporal_info[1]}")
            
            # Extraer posibles categorías o tipos de la consulta
            category_type_filters = self._extract_category_type_filters(query)
            if category_type_filters:
                filters.update(category_type_filters)
            
            # Considerar primero búsqueda exacta para categorías y tipos específicos
            exact_matches = self._try_exact_match(query)
            if exact_matches:
                logger.info(f"Encontradas {len(exact_matches)} coincidencias exactas")
                return exact_matches[:limit]
            
            # Generar embedding para la consulta
            query_embedding = generate_embedding(query)
            
            # Construir filtros para Pinecone
            filter_dict = {}
            if filters:
                # Convertir filtros a formato Pinecone
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
                    elif key == "date_range" and isinstance(value, list) and len(value) == 2:
                        # Convertir fechas a strings ISO si son objetos datetime
                        start_date = value[0].isoformat() if isinstance(value[0], datetime) else value[0]
                        end_date = value[1].isoformat() if isinstance(value[1], datetime) else value[1]
                        
                        filter_dict["date"] = {
                            "$gte": start_date,
                            "$lte": end_date
                        }
            
            # Buscar en Pinecone
            try:
                results = self.pinecone.query_vector(
                    vector=query_embedding,
                    filter=filter_dict if filter_dict else None,
                    top_k=limit,
                    include_metadata=True
                )
                
                # Convertir resultados a lista de transacciones
                transactions = []
                
                # Verificar si tenemos coincidencias
                if "matches" in results and results["matches"]:
                    for match in results["matches"]:
                        # Obtener transacción completa de Supabase
                        transaction_id = match["id"]
                        transaction = self.supabase.get_transaction(transaction_id)
                        
                        if transaction:
                            # Añadir puntuación de similitud a la transacción
                            transaction_dict = transaction.model_dump()
                            
                            # Corregir fechas antiguas (años anteriores a 2024)
                            self._fix_transaction_dates(transaction_dict)
                            
                            transaction_dict["similarity"] = match["score"]
                            transactions.append(transaction_dict)
                
                # Si no hay resultados suficientes, intentar con texto
                if len(transactions) < limit:
                    logger.info(f"Búsqueda vectorial devolvió pocos resultados ({len(transactions)}), probando búsqueda de texto")
                    text_results = self.text_search(query, "transaction", limit - len(transactions))
                    
                    # Añadir solo resultados que no estén ya incluidos
                    existing_ids = {t["id"] for t in transactions}
                    for result in text_results:
                        if result["reference_id"] not in existing_ids:
                            transaction = self.supabase.get_transaction(result["reference_id"])
                            if transaction:
                                transaction_dict = transaction.model_dump()
                                
                                # Corregir fechas antiguas (años anteriores a 2024)
                                self._fix_transaction_dates(transaction_dict)
                                
                                transaction_dict["similarity"] = 0.5  # Valor predeterminado
                                transactions.append(transaction_dict)
                                existing_ids.add(transaction_dict["id"])
                
                logger.info(f"Búsqueda completada, encontradas {len(transactions)} transacciones")
                return transactions
            
            except Exception as e:
                logger.error(f"Error en búsqueda vectorial: {e}")
                # Si falla la búsqueda vectorial, intentar con búsqueda de texto
                logger.info("Intentando búsqueda de respaldo con texto")
                fallback_results = self._fallback_search(query, filters, limit)
                return fallback_results
        
        except Exception as e:
            logger.error(f"Error buscando transacciones: {e}")
            return []
    
    def _fix_transaction_dates(self, transaction: Dict[str, Any]) -> None:
        """
        Corrige las fechas de transacciones antiguas para que sean del año actual
        
        Args:
            transaction: Diccionario de transacción a corregir (se modifica in-place)
        """
        current_year = datetime.now().year
        
        # Corregir fecha principal
        if "date" in transaction and transaction["date"]:
            try:
                # Si es una cadena, convertir a datetime
                if isinstance(transaction["date"], str):
                    # Manejar distintos formatos de fecha
                    if 'T' in transaction["date"]:
                        # Formato ISO con hora
                        date_str = transaction["date"].split('T')[0]
                    else:
                        date_str = transaction["date"]
                    
                    # Intentar convertir a datetime
                    date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    # Si el año es anterior al actual, actualizar al año actual
                    if date_obj.year < current_year - 1:
                        # Actualizar al mismo mes/día pero en el año actual
                        new_date = date_obj.replace(year=current_year)
                        transaction["date"] = new_date.strftime('%Y-%m-%d')
                        logger.info(f"Fecha corregida: {date_obj.strftime('%Y-%m-%d')} → {new_date.strftime('%Y-%m-%d')}")
            except Exception as e:
                logger.warning(f"Error al corregir fecha: {e}")
        
        # Corregir otras fechas relacionadas si existen
        for date_field in ['payment_date', 'due_date', 'start_date', 'end_date']:
            if date_field in transaction and transaction[date_field]:
                try:
                    # Si es una cadena, convertir a datetime
                    if isinstance(transaction[date_field], str):
                        # Manejar distintos formatos de fecha
                        if 'T' in transaction[date_field]:
                            # Formato ISO con hora
                            date_str = transaction[date_field].split('T')[0]
                        else:
                            date_str = transaction[date_field]
                        
                        # Intentar convertir a datetime
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        
                        # Si el año es anterior al actual, actualizar al año actual
                        if date_obj.year < current_year - 1:
                            # Actualizar al mismo mes/día pero en el año actual
                            new_date = date_obj.replace(year=current_year)
                            transaction[date_field] = new_date.strftime('%Y-%m-%d')
                except Exception as e:
                    logger.warning(f"Error al corregir fecha {date_field}: {e}")
    
    def _try_exact_match(self, query: str) -> List[Dict[str, Any]]:
        """Intenta encontrar coincidencias exactas para consultas específicas"""
        query_lower = query.lower()
        current_year = datetime.now().year
        
        try:
            # Buscar coincidencias exactas en categorías
            categories = ["Software", "Payroll", "Marketing", "Office", "Services", 
                         "Hardware", "Travel", "Legal", "Taxes", "Revenue", "Rent"]
            
            for category in categories:
                if category.lower() in query_lower:
                    transactions = self.supabase.list_transactions(
                        limit=10,
                        category=category
                    )
                    if transactions:
                        # Convertir a diccionarios y actualizar fechas antiguas
                        results = []
                        for tx in transactions:
                            tx_dict = tx.model_dump()
                            # Corregir fechas antiguas
                            self._fix_transaction_dates(tx_dict)
                            results.append(tx_dict)
                        return results
            
            # Buscar coincidencias en tipo (ingreso/gasto)
            if "ingreso" in query_lower or "ingresos" in query_lower or "income" in query_lower:
                transactions = self.supabase.list_transactions(
                    limit=10,
                    type="income"
                )
                if transactions:
                    # Actualizar fechas antiguas
                    results = []
                    for tx in transactions:
                        tx_dict = tx.model_dump()
                        # Corregir fechas antiguas
                        self._fix_transaction_dates(tx_dict)
                        results.append(tx_dict)
                    return results
            
            if "gasto" in query_lower or "gastos" in query_lower or "expense" in query_lower:
                transactions = self.supabase.list_transactions(
                    limit=10,
                    type="expense"
                )
                if transactions:
                    # Actualizar fechas antiguas
                    results = []
                    for tx in transactions:
                        tx_dict = tx.model_dump()
                        # Corregir fechas antiguas
                        self._fix_transaction_dates(tx_dict)
                        results.append(tx_dict)
                    return results
                    
            return []
        except Exception as e:
            logger.error(f"Error en búsqueda de coincidencia exacta: {e}")
            return []
    
    def _extract_temporal_info(self, query: str) -> Optional[List[datetime]]:
        """Extract temporal information from query"""
        query_lower = query.lower()
        now = datetime.now()
        
        # Último mes
        if "último mes" in query_lower or "mes pasado" in query_lower or "last month" in query_lower:
            # Primer día del mes actual
            first_day_current = datetime(now.year, now.month, 1)
            # Último día del mes pasado
            last_day_previous = first_day_current - timedelta(days=1)
            # Primer día del mes pasado
            first_day_previous = datetime(last_day_previous.year, last_day_previous.month, 1)
            return [first_day_previous, last_day_previous]
        
        # Este mes
        if "este mes" in query_lower or "mes actual" in query_lower or "this month" in query_lower:
            # Primer día del mes actual
            first_day = datetime(now.year, now.month, 1)
            # Último día (aproximado)
            last_day = datetime(now.year, now.month + 1 if now.month < 12 else 1, 1) - timedelta(days=1)
            return [first_day, last_day]
        
        # Año actual
        if "este año" in query_lower or "año actual" in query_lower or "this year" in query_lower:
            return [datetime(now.year, 1, 1), datetime(now.year, 12, 31)]
        
        # Año pasado
        if "año pasado" in query_lower or "last year" in query_lower:
            return [datetime(now.year - 1, 1, 1), datetime(now.year - 1, 12, 31)]
        
        # Meses específicos
        months = {
            "enero": 1, "february": 1,
            "febrero": 2, "february": 2,
            "marzo": 3, "march": 3,
            "abril": 4, "april": 4,
            "mayo": 5, "may": 5,
            "junio": 6, "june": 6,
            "julio": 7, "july": 7,
            "agosto": 8, "august": 8,
            "septiembre": 9, "september": 9,
            "octubre": 10, "october": 10,
            "noviembre": 11, "november": 11,
            "diciembre": 12, "december": 12
        }
        
        for month_name, month_num in months.items():
            if month_name in query_lower:
                # Si se menciona un año específico
                year = now.year
                for i in range(now.year - 3, now.year + 2):  # Buscar años cercanos
                    if str(i) in query:
                        year = i
                        break
                
                return [datetime(year, month_num, 1), 
                        (datetime(year, month_num + 1, 1) if month_num < 12 else datetime(year + 1, 1, 1)) - timedelta(days=1)]
        
        # Si no se encuentra información temporal, devolver None
        return None
    
    def _extract_category_type_filters(self, query: str) -> Dict[str, str]:
        """Extract category and type filters from query"""
        query_lower = query.lower()
        filters = {}
        
        # Detectar categorías comunes
        categories = {
            "software": "Software",
            "nómina": "Payroll", "payroll": "Payroll",
            "marketing": "Marketing",
            "oficina": "Office", "office": "Office",
            "servicios": "Services", "services": "Services",
            "hardware": "Hardware",
            "viajes": "Travel", "travel": "Travel",
            "legal": "Legal",
            "impuestos": "Taxes", "taxes": "Taxes",
            "ingresos": "Revenue", "revenue": "Revenue",
            "ventas": "Revenue", "sales": "Revenue",
            "alquiler": "Rent", "rent": "Rent"
        }
        
        for keyword, category in categories.items():
            if keyword in query_lower:
                filters["category"] = category
                break
        
        # Detectar tipo (ingreso/gasto)
        if "ingreso" in query_lower or "ingresos" in query_lower or "income" in query_lower:
            filters["type"] = "income"
        elif "gasto" in query_lower or "gastos" in query_lower or "expense" in query_lower:
            filters["type"] = "expense"
        
        return filters
    
    def _fallback_search(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Método de respaldo cuando falla la búsqueda vectorial"""
        try:
            logger.info("Ejecutando búsqueda de respaldo")
            
            # Intentar primero búsqueda de texto
            text_results = self.text_search(query, "transaction", limit * 2)  # Buscar más resultados para filtrar después
            
            if text_results:
                transactions = []
                for result in text_results:
                    transaction = self.supabase.get_transaction(result["reference_id"])
                    if transaction:
                        tx_dict = transaction.model_dump()
                        # Corregir fechas antiguas
                        self._fix_transaction_dates(tx_dict)
                        transactions.append(tx_dict)
                
                # Aplicar filtros si es necesario
                if filters and transactions:
                    filtered_transactions = []
                    for tx in transactions:
                        include = True
                        
                        for key, value in filters.items():
                            if key == "type" and tx.get("type") != value:
                                include = False
                                break
                            elif key == "category" and tx.get("category") != value:
                                include = False
                                break
                            elif key == "date_range" and isinstance(value, list) and len(value) == 2:
                                tx_date = tx.get("date")
                                if isinstance(tx_date, str):
                                    tx_date = datetime.fromisoformat(tx_date.replace("Z", "+00:00"))
                                
                                if not (value[0] <= tx_date <= value[1]):
                                    include = False
                                    break
                        
                        if include:
                            filtered_transactions.append(tx)
                    
                    return filtered_transactions[:limit]
                
                return transactions[:limit]
            
            # Si no hay resultados, obtener las transacciones más recientes
            logger.info("Sin resultados de texto, devolviendo transacciones recientes")
            recent_transactions = self.supabase.list_transactions(limit=limit)
            return [t.model_dump() for t in recent_transactions]
            
        except Exception as e:
            logger.error(f"Error en búsqueda de respaldo: {e}")
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
                    # Obtener la fecha de forma segura
                    if isinstance(tx.get('date'), datetime):
                        tx_date = tx['date'].strftime('%Y-%m-%d')
                    elif isinstance(tx.get('date'), str):
                        tx_date = tx['date'].split('T')[0] if 'T' in tx['date'] else tx['date']
                    else:
                        tx_date = "fecha desconocida"
                        
                    explanation.append(f"Found 1 transaction: {tx['type']} of {tx['currency']} {tx['amount']} for {tx['description']} on {tx_date}.")
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