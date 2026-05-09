"""
FAISS retrieval wrapper for SHL catalog.
Provides semantic search over assessment metadata.
"""

import json
import os
from typing import List, Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Retriever:
    def __init__(self, index_path: str = None, meta_path: str = None):
        self.index_path = index_path or os.path.join(BASE_DIR, "catalog.index")
        self.meta_path = meta_path or os.path.join(BASE_DIR, "catalog_meta.json")

        if not os.path.exists(self.index_path):
            raise FileNotFoundError(f"FAISS index not found: {self.index_path}")
        if not os.path.exists(self.meta_path):
            raise FileNotFoundError(f"Metadata not found: {self.meta_path}")

        print(f"Loading FAISS index from {self.index_path}")
        self.index = faiss.read_index(self.index_path)
        print(f"Loaded index with {self.index.ntotal} vectors")

        print(f"Loading metadata from {self.meta_path}")
        with open(self.meta_path, "r", encoding="utf-8") as f:
            self.metadata = json.load(f)

        print("Loading embedding model (all-MiniLM-L6-v2)...")
        # Use a smaller model for faster loading
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        print("Model loaded successfully")

    def retrieve(self, query: str, top_k: int = 15) -> List[Dict]:
        """
        Retrieve top-k assessments for a query.
        """
        top_k = min(top_k, self.index.ntotal)
        query = query.strip()

        if not query:
            return []

        # Embed query
        query_embedding = self.model.encode([query])
        query_embedding = np.array(query_embedding).astype("float32")

        # Normalize for cosine similarity
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm

        # Search
        scores, indices = self.index.search(query_embedding, top_k)

        # Build results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx >= 0 and idx < len(self.metadata):
                meta = self.metadata[idx]
                results.append({
                    "rank": i + 1,
                    "score": float(score),
                    "name": meta["name"],
                    "url": meta["url"],
                    "test_type": meta.get("test_type", []),
                })

        return results


# Global retriever instance (loaded once at startup)
_retriever = None


def get_retriever() -> Retriever:
    """Get or create the global retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = Retriever()
    return _retriever


def retrieve(query: str, top_k: int = 15) -> List[Dict]:
    """Retrieve top-k assessments from the catalog."""
    return get_retriever().retrieve(query, top_k)