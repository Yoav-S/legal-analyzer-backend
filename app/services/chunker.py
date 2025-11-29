"""
Document chunking service for LLM processing.
"""
from typing import List
import tiktoken

from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class DocumentChunker:
    """Service for splitting documents into LLM-friendly chunks."""
    
    def __init__(self, max_tokens: int = None):
        self.max_tokens = max_tokens or settings.MAX_TOKENS_PER_CHUNK
        # Use tiktoken for accurate token counting
        # Try GPT-5 first (if available), fallback to GPT-4, then to base encoding
        try:
            self.encoding = tiktoken.encoding_for_model(settings.DEFAULT_AI_MODEL)
        except:
            try:
                # Fallback to GPT-4 encoding (compatible with GPT-5)
                self.encoding = tiktoken.encoding_for_model("gpt-4")
            except:
                # Final fallback to base encoding
                self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def chunk_text(self, text: str, overlap: int = 200) -> List[dict]:
        """
        Split text into chunks with token limits.
        
        Args:
            text: Full document text
            overlap: Number of tokens to overlap between chunks
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        if not text or not text.strip():
            return []
        
        # Split by paragraphs first (preserve structure)
        paragraphs = text.split("\n\n")
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = len(self.encoding.encode(para))
            
            # If paragraph alone exceeds limit, split it further
            if para_tokens > self.max_tokens:
                # Save current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(current_chunk, len(chunks)))
                    current_chunk = []
                    current_tokens = 0
                
                # Split large paragraph by sentences
                sentences = para.split(". ")
                for sentence in sentences:
                    sent_tokens = len(self.encoding.encode(sentence))
                    if current_tokens + sent_tokens > self.max_tokens:
                        if current_chunk:
                            chunks.append(self._create_chunk(current_chunk, len(chunks)))
                            # Add overlap from previous chunk
                            overlap_text = self._get_overlap_text(current_chunk, overlap)
                            current_chunk = [overlap_text, sentence] if overlap_text else [sentence]
                            current_tokens = len(self.encoding.encode(" ".join(current_chunk)))
                        else:
                            current_chunk = [sentence]
                            current_tokens = sent_tokens
                    else:
                        current_chunk.append(sentence)
                        current_tokens += sent_tokens
            else:
                # Check if adding paragraph exceeds limit
                if current_tokens + para_tokens > self.max_tokens:
                    if current_chunk:
                        chunks.append(self._create_chunk(current_chunk, len(chunks)))
                        # Add overlap
                        overlap_text = self._get_overlap_text(current_chunk, overlap)
                        current_chunk = [overlap_text, para] if overlap_text else [para]
                        current_tokens = len(self.encoding.encode(" ".join(current_chunk)))
                    else:
                        current_chunk = [para]
                        current_tokens = para_tokens
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, len(chunks)))
        
        logger.info(f"Split document into {len(chunks)} chunks")
        return chunks
    
    def _create_chunk(self, text_parts: List[str], chunk_index: int) -> dict:
        """Create chunk dictionary."""
        text = "\n\n".join(text_parts)
        tokens = len(self.encoding.encode(text))
        
        return {
            "chunk_index": chunk_index,
            "text": text,
            "token_count": tokens,
        }
    
    def _get_overlap_text(self, text_parts: List[str], overlap_tokens: int) -> str:
        """Get overlap text from end of chunk."""
        if not text_parts:
            return ""
        
        # Get last paragraph and encode
        last_para = text_parts[-1]
        encoded = self.encoding.encode(last_para)
        
        if len(encoded) <= overlap_tokens:
            return last_para
        
        # Take last N tokens
        overlap_encoded = encoded[-overlap_tokens:]
        return self.encoding.decode(overlap_encoded)

