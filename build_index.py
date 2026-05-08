"""
Build FAISS vector index from SHL catalog.
Embeds each assessment and saves to catalog.index for fast retrieval.
"""

import json
import os
from typing import List, Dict
import numpy as np

# Use sentence-transformers with all-MiniLM-L6-v2 (local, free embedding model)
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_catalog() -> List[Dict]:
    """Load the catalog JSON file."""
    catalog_path = os.path.join(BASE_DIR, "catalog.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_document(assessment: Dict) -> str:
    """Combine assessment metadata into a single text document for embedding."""
    parts = [
        assessment["name"],
        assessment.get("description", ""),
        f"Test types: {', '.join(assessment.get('test_type', []))}",
        f"Job levels: {', '.join(assessment.get('job_levels', []))}",
        f"Languages: {', '.join(assessment.get('languages', []))}",
    ]

    if assessment.get("duration"):
        parts.append(f"Duration: {assessment['duration']}")
    if assessment.get("remote_testing") == "Yes":
        parts.append("Supports remote testing")
    if assessment.get("adaptive") == "Yes":
        parts.append("Adaptive/IRT assessment")

    return " | ".join(parts)


def build_index():
    """Build the FAISS index from catalog embeddings."""
    print("Loading catalog...")
    catalog = load_catalog()
    print(f"Loaded {len(catalog)} assessments")

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Creating embedding documents...")
    documents = []
    metadatas = []

    for i, assessment in enumerate(catalog):
        doc = create_document(assessment)
        documents.append(doc)
        metadatas.append({
            "index": i,
            "name": assessment["name"],
            "url": assessment["url"],
            "test_type": assessment.get("test_type", []),
        })

    print(f"Embedding {len(documents)} documents...")
    embeddings = model.encode(documents, show_progress_bar=True)
    embeddings = np.array(embeddings).astype("float32")

    # Normalize for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    embeddings = embeddings / norms

    print(f"Building FAISS index with dimension {embeddings.shape[1]}...")
    import faiss
    index = faiss.IndexFlatIP(embeddings.shape[1])  # Inner product for normalized vectors = cosine
    index.add(embeddings)

    # Save index
    index_path = os.path.join(BASE_DIR, "catalog.index")
    faiss.write_index(index, index_path)
    print(f"Saved FAISS index to {index_path}")

    # Save metadata
    meta_path = os.path.join(BASE_DIR, "catalog_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadatas, f, indent=2)
    print(f"Saved metadata to {meta_path}")

    print("\nIndex built successfully!")
    print(f"  - {index.ntotal} vectors")
    print(f"  - Dimension: {embeddings.shape[1]}")


if __name__ == "__main__":
    build_index()
