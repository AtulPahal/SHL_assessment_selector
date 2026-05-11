"""
Build TF-IDF index from SHL catalog.
Saves documents and metadata to a single JSON file for retrieval.
"""

import json
import os
from typing import List, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_catalog() -> List[Dict]:
    """Load the catalog JSON file."""
    catalog_path = os.path.join(BASE_DIR, "catalog.json")
    with open(catalog_path, "r", encoding="utf-8") as f:
        return json.load(f)


def create_document(assessment: Dict) -> str:
    """Combine assessment metadata into a single text document for TF-IDF indexing."""
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
    """Build TF-IDF indexable data from catalog."""
    print("Loading catalog...")
    catalog = load_catalog()
    print(f"Loaded {len(catalog)} assessments")

    print("Creating documents...")
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

    # Save combined data file (retriever loads both documents and metadata)
    data_path = os.path.join(BASE_DIR, "catalog_data.json")
    data = {
        "documents": documents,
        "metadata": metadatas,
    }
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved catalog data to {data_path}")

    # Clean up old files that are no longer needed
    old_files = ["catalog.index", "catalog_meta.json"]
    for fname in old_files:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
            print(f"Removed old file: {fname}")

    print(f"\nIndex built successfully!")
    print(f"  - {len(documents)} documents")


if __name__ == "__main__":
    build_index()
