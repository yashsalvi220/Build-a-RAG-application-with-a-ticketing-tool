"""
Query the FAISS index and answer questions using Claude.

Usage:
    python tools/query_rag.py "What is the baggage policy?"
"""

import argparse
import os
import pickle
import sys

import faiss
import numpy as np
from anthropic import Anthropic
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

FAISS_DIR = os.path.join(os.path.dirname(__file__), "..", ".tmp", "faiss_index")
TOP_K = 5


def load_index():
    """Load FAISS index and metadata from disk."""
    index_path = os.path.join(FAISS_DIR, "index.faiss")
    meta_path = os.path.join(FAISS_DIR, "metadata.pkl")

    if not os.path.exists(index_path):
        print("ERROR: No FAISS index found. Run ingest_documents.py first.")
        sys.exit(1)

    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        metadata = pickle.load(f)

    return index, metadata


def embed_query(query: str, client: OpenAI, model: str) -> np.ndarray:
    """Embed a single query string."""
    response = client.embeddings.create(input=[query], model=model)
    return np.array([response.data[0].embedding], dtype="float32")


def retrieve_chunks(query: str, index, metadata, openai_client, model, top_k=TOP_K) -> list[dict]:
    """Retrieve the most relevant chunks for a query."""
    query_embedding = embed_query(query, openai_client, model)
    distances, indices = index.search(query_embedding, top_k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(metadata):
            chunk = metadata[idx].copy()
            chunk["score"] = float(distances[0][i])
            results.append(chunk)

    return results


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Build the context prompt from retrieved chunks."""
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Source {i}: {chunk['source']}, Page {chunk['page']}]\n{chunk['text']}"
        )

    context = "\n\n---\n\n".join(context_parts)
    return (
        "Answer the user's question based ONLY on the provided document excerpts. "
        "If the answer is not in the documents, say so clearly. "
        "Cite your sources using [Source N] notation.\n\n"
        f"## Document Excerpts\n\n{context}\n\n"
        f"## Question\n\n{question}"
    )


def query_rag(question: str) -> dict:
    """
    Main RAG query function. Returns dict with 'answer' and 'sources'.
    Importable by streamlit_app.py.
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not openai_key:
        return {"answer": "ERROR: OPENAI_API_KEY not set in .env", "sources": []}
    if not anthropic_key:
        return {"answer": "ERROR: ANTHROPIC_API_KEY not set in .env", "sources": []}

    embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_client = OpenAI(api_key=openai_key)
    anthropic_client = Anthropic(api_key=anthropic_key)

    index, metadata = load_index()
    chunks = retrieve_chunks(question, index, metadata, openai_client, embedding_model)

    if not chunks:
        return {"answer": "No relevant information found in the documents.", "sources": []}

    prompt = build_prompt(question, chunks)

    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    answer = response.content[0].text
    sources = [{"source": c["source"], "page": c["page"]} for c in chunks]

    return {"answer": answer, "sources": sources}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query documents using RAG")
    parser.add_argument("question", help="The question to ask")
    args = parser.parse_args()

    result = query_rag(args.question)
    print("\n" + result["answer"])

    if result["sources"]:
        print("\n--- Sources ---")
        seen = set()
        for s in result["sources"]:
            key = (s["source"], s["page"])
            if key not in seen:
                seen.add(key)
                print(f"  - {s['source']}, Page {s['page']}")
