import os
from typing import Dict, Any, Optional, BinaryIO
import tempfile
from config.logging import logger
from utils.embedding_utils import generate_embedding
from core.ai_engine import AIEngine

class DocumentProcessor:
    def __init__(self, ai_engine: Optional[AIEngine] = None):
        """Initialize the document processor"""
        self.ai_engine = ai_engine or AIEngine()
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file"""
        try:
            import pypdf
            
            text = ""
            with open(file_path, "rb") as f:
                pdf = pypdf.PdfReader(f)
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return ""
    
    def extract_text_from_image(self, file_path: str) -> str:
        """Extract text from an image using OCR"""
        try:
            import pytesseract
            from PIL import Image
            
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return ""
    
    def process_document(self, file_obj: BinaryIO, filename: str) -> Dict[str, Any]:
        """Process a document file and extract information"""
        try:
            # Save file to temporary location
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, filename)
            
            with open(temp_path, 'wb') as f:
                f.write(file_obj.read())
            
            # Determine file type and extract text
            text = ""
            if filename.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(temp_path)
            elif filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                text = self.extract_text_from_image(temp_path)
            else:
                # For other file types, attempt to read as text
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
            
            # Clean up temporary file
            os.remove(temp_path)
            os.rmdir(temp_dir)
            
            if not text:
                return {
                    "success": False,
                    "error": "Could not extract text from document"
                }
            
            # Determine document type based on content
            doc_type = self.determine_document_type(text)
            
            # Extract structured data using AI
            extracted_data = self.ai_engine.extract_document_data(text, doc_type)
            
            # Generate embedding for the document
            embedding = generate_embedding(text)
            
            return {
                "success": True,
                "file_name": filename,
                "content_text": text,
                "document_type": doc_type,
                "extracted_data": extracted_data,
                "embedding": embedding
            }
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def determine_document_type(self, text: str) -> str:
        """Determine the type of document based on its content"""
        # Simple heuristic for document type determination
        text_lower = text.lower()
        
        if "invoice" in text_lower or "bill to" in text_lower:
            return "invoice"
        elif "receipt" in text_lower or "payment received" in text_lower:
            return "receipt"
        elif "contract" in text_lower or "agreement" in text_lower:
            return "contract"
        else:
            return "other"