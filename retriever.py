"""
TF-IDF retrieval wrapper for SHL catalog.
Provides keyword/semantic-like search without external API calls.
"""

import json
import os
from typing import List, Dict
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Retriever:
    def __init__(self, data_path: str = None):
        self.data_path = data_path or os.path.join(BASE_DIR, "catalog_data.json")

        if not os.path.exists(self.data_path):
            raise FileNotFoundError(f"Catalog data not found: {self.data_path}")

        print(f"Loading catalog data from {self.data_path}")
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.documents = data["documents"]
        self.metadata = data["metadata"]

        print(f"Loading TF-IDF vectorizer...")
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 2),
            stop_words="english",
            lowercase=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
        print(f"Loaded {len(self.documents)} documents, vocab size: {len(self.vectorizer.vocabulary_)}")
        print("Retriever ready.")

    def retrieve(self, query: str, top_k: int = 15) -> List[Dict]:
        """
        Retrieve top-k assessments for a query using TF-IDF cosine similarity.
        """
        query = query.strip()
        if not query:
            return []

        # Transform query to TF-IDF vector
        query_vec = self.vectorizer.transform([query])

        # Compute cosine similarity
        scores = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        # Get top-k indices
        top_indices = scores.argsort()[::-1][:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            if scores[idx] <= 0:
                break
            meta = self.metadata[idx]
            results.append({
                "rank": rank + 1,
                "score": float(scores[idx]),
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
