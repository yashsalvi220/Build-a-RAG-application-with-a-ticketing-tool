"""
Ingest PDF documents: parse, chunk, embed, and store in FAISS index.

Usage:
    python tools/ingest_documents.py doc1.pdf doc2.pdf
"""

import argparse
import os
import pickle
import sys

import faiss
import numpy as np
import pdfplumber
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

FAISS_DIR = os.path.join(os.path.dirname(__file__), "..", ".tmp", "faiss_index")
CHUNK_SIZE = 2000  # characters (~500 tokens)
CHUNK_OVERLAP = 200  # characters (~50 tokens)


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text from each page of a PDF. Returns list of {page, text}."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                pages.append({"page": i, "text": text.strip()})
    return pages


def chunk_text(text: str, source: str, page: int) -> list[dict]:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]
        if chunk.strip():
            chunks.append({
                "text": chunk.strip(),
                "source": source,
                "page": page,
            })
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def embed_texts(texts: list[str], client: OpenAI, model: str) -> np.ndarray:
    """Embed a list of texts using OpenAI embeddings API."""
    response = client.embeddings.create(input=texts, model=model)
    embeddings = [item.embedding for item in response.data]
    return np.array(embeddings, dtype="float32")


def ingest(pdf_paths: list[str]) -> dict:
    """Main ingestion pipeline. Returns summary stats."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    client = OpenAI(api_key=api_key)

    all_chunks = []
    for pdf_path in pdf_paths:
        if not os.path.exists(pdf_path):
            print(f"WARNING: File not found, skipping: {pdf_path}")
            continue

        filename = os.path.basename(pdf_path)
        print(f"Parsing: {filename}")
        pages = extract_text_from_pdf(pdf_path)

        for page_data in pages:
            chunks = chunk_text(page_data["text"], filename, page_data["page"])
            all_chunks.extend(chunks)

    if not all_chunks:
        print("ERROR: No text extracted from any document.")
        sys.exit(1)

    print(f"Chunked into {len(all_chunks)} pieces. Embedding...")

    # Embed in batches of 100 (API limit)
    chunk_texts = [c["text"] for c in all_chunks]
    all_embeddings = []
    for i in range(0, len(chunk_texts), 100):
        batch = chunk_texts[i : i + 100]
        embeddings = embed_texts(batch, client, model)
        all_embeddings.append(embeddings)

    embeddings_matrix = np.vstack(all_embeddings)

    # Build FAISS index
    dimension = embeddings_matrix.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings_matrix)

    # Save index and metadata
    os.makedirs(FAISS_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(FAISS_DIR, "index.faiss"))
    with open(os.path.join(FAISS_DIR, "metadata.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)

    summary = {
        "documents": len(pdf_paths),
        "chunks": len(all_chunks),
        "dimension": dimension,
    }
    print(f"Done. Indexed {summary['chunks']} chunks from {summary['documents']} documents.")
    print(f"FAISS index saved to: {FAISS_DIR}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest PDF documents into FAISS vector store")
    parser.add_argument("pdfs", nargs="+", help="Paths to PDF files")
    args = parser.parse_args()
    ingest(args.pdfs)
