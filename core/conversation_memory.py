from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import os
from config.logging import logger

class ConversationMemory:
    def __init__(self, max_history: int = 10):
        """Initialize conversation memory with maximum history length"""
        self.max_history = max_history
        self.history = []
        self.session_id = datetime.now().strftime("%Y%m%d%H%M%S")
        self.memory_file = os.path.join("logs", f"conversation_{self.session_id}.json")
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
    
    def add(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to the conversation history"""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.history.append(entry)
        
        # Limitar el tamaño de la historia
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Guardar en disco
        self._save()
        
        return entry
    
    def _save(self):
        """Save conversation history to disk"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "session_id": self.session_id,
                    "history": self.history,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando historial de conversación: {e}")
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation history with optional limit"""
        if limit is None or limit >= len(self.history):
            return self.history
        return self.history[-limit:]
    
    def get_last_user_query(self) -> Optional[str]:
        """Get the last user query"""
        for entry in reversed(self.history):
            if entry["role"] == "user":
                return entry["content"]
        return None
    
    def get_context_for_llm(self, max_entries: int = 5) -> List[Dict[str, str]]:
        """Get formatted conversation history for LLM context"""
        entries = self.get_history(max_entries)
        formatted = []
        
        for entry in entries:
            formatted.append({
                "role": entry["role"],
                "content": entry["content"]
            })
        
        return formatted
    
    def clear(self):
        """Clear conversation history"""
        self.history = []
        self._save()
    
    def load_from_file(self, file_path: str) -> bool:
        """Load conversation history from file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if "history" in data and isinstance(data["history"], list):
                        self.history = data["history"]
                        self.session_id = data.get("session_id", self.session_id)
                        return True
            
            return False
        except Exception as e:
            logger.error(f"Error cargando historial de conversación: {e}")
            return False
    
    def get_relevant_context(self, query: str, max_entries: int = 3) -> List[Dict[str, Any]]:
        """Get most relevant context for the current query"""
        # Por ahora, simplemente devuelve las últimas entradas
        # En una implementación más avanzada, podríamos usar embeddings para
        # encontrar entradas similares al query actual
        return self.get_history(max_entries)