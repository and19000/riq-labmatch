"""
Embedding service with caching for semantic similarity.
"""

import json
import os
import hashlib
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Try imports
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class EmbeddingService:
    """Embedding computation with caching."""
    
    def __init__(self, openai_client=None, cache_dir: str = "embeddings_cache"):
        self.client = openai_client
        self.cache_dir = cache_dir
        self.memory_cache = {}
        os.makedirs(cache_dir, exist_ok=True)
    
    def get_embedding(self, text: str) -> Optional[Any]:
        """Get embedding for text."""
        if not text or not self.client:
            return None
        
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()[:16]
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]
        
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path) as f:
                    data = json.load(f)
                    emb = np.array(data["embedding"]) if HAS_NUMPY else data["embedding"]
                    self.memory_cache[cache_key] = emb
                    return emb
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        # Compute
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000],
            )
            embedding = response.data[0].embedding
            if HAS_NUMPY:
                embedding = np.array(embedding)
            
            # Cache
            self.memory_cache[cache_key] = embedding
            with open(cache_path, 'w') as f:
                emb_list = embedding.tolist() if HAS_NUMPY else embedding
                json.dump({"embedding": emb_list}, f)
            
            return embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None
    
    def cosine_similarity(self, emb1, emb2) -> float:
        """Calculate cosine similarity."""
        if emb1 is None or emb2 is None:
            return 0.0
        if HAS_NUMPY:
            dot = np.dot(emb1, emb2)
            norm = np.linalg.norm(emb1) * np.linalg.norm(emb2)
            return dot / norm if norm > 0 else 0.0
        else:
            dot = sum(a * b for a, b in zip(emb1, emb2))
            norm1 = sum(a * a for a in emb1) ** 0.5
            norm2 = sum(b * b for b in emb2) ** 0.5
            return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0
