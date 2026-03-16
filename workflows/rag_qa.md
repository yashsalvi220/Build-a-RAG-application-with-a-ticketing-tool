# RAG Document Q&A Workflow

## Objective

Answer user questions based on uploaded PDF documents using retrieval-augmented generation (RAG).

## Required Inputs

| Input | Source | Example |
|-------|--------|---------|
| PDF documents | User upload or file path | `policy.pdf` |
| User question | Chat UI or CLI | "What is the refund policy?" |
| Anthropic API key | `.env` → `ANTHROPIC_API_KEY` | — |
| OpenAI API key | `.env` → `OPENAI_API_KEY` | — |

## Tool Sequence

| Step | Tool | What It Does |
|------|------|-------------|
| 1 | `tools/ingest_documents.py` | Parse PDFs, chunk text, embed, store FAISS index in `.tmp/faiss_index/` |
| 2 | `tools/query_rag.py` | Embed question, retrieve top-5 chunks from FAISS, call Claude for answer |
| 3 | `tools/streamlit_app.py` | Orchestrate steps 1-2 via web chat UI |

## Expected Outputs

- `.tmp/faiss_index/index.faiss` — vector index (regenerated on each ingestion)
- `.tmp/faiss_index/metadata.pkl` — chunk metadata (source file, page number)
- Streamed answer in chat UI with `[Source N]` citations

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Empty or corrupt PDF | `pdfplumber` returns no text; user sees "No text extracted" error |
| Question not in documents | Claude responds "the answer is not in the provided documents" |
| OPENAI_API_KEY missing | Error message printed before any API call |
| ANTHROPIC_API_KEY missing | Error message printed before any API call |
| Very large PDF (100+ pages) | Embedding batched in groups of 100; may take a minute |
| Re-upload new documents | FAISS index is fully overwritten (no stale data) |
