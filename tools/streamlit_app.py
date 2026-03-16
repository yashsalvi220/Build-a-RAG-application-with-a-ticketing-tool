"""
Streamlit chatbot UI with two tabs:
  1. Ask Documents — upload PDFs and ask questions (RAG)
  2. File a Case — guided form to file a case on an external website

Run:
    streamlit run tools/streamlit_app.py
"""

import json
import os
import subprocess
import sys
import tempfile

import streamlit as st

# Ensure tools/ is importable
sys.path.insert(0, os.path.dirname(__file__))

from ingest_documents import ingest
from query_rag import query_rag

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", ".tmp", "uploaded_docs")
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Document Chatbot", page_icon="💬", layout="wide")
st.title("Document Chatbot")

tab1, tab2 = st.tabs(["📄 Ask Documents", "📝 File a Case"])

# ── Tab 1: Document Q&A ──────────────────────────────────────────────────────

with tab1:
    st.header("Ask Questions About Your Documents")

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_uploader",
    )

    if uploaded_files and st.button("Ingest Documents", key="ingest_btn"):
        pdf_paths = []
        for uploaded_file in uploaded_files:
            save_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            pdf_paths.append(save_path)

        with st.spinner("Parsing and indexing documents..."):
            try:
                summary = ingest(pdf_paths)
                st.success(
                    f"Indexed {summary['chunks']} chunks from "
                    f"{summary['documents']} document(s)."
                )
                st.session_state["docs_ingested"] = True
            except Exception as e:
                st.error(f"Ingestion failed: {e}")

    # Chat interface
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display chat history
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if question := st.chat_input("Ask a question about your documents..."):
        # Show user message
        st.session_state["messages"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Get answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    result = query_rag(question)
                    answer = result["answer"]

                    # Add source citations
                    if result["sources"]:
                        seen = set()
                        citations = []
                        for s in result["sources"]:
                            key = (s["source"], s["page"])
                            if key not in seen:
                                seen.add(key)
                                citations.append(f"- {s['source']}, Page {s['page']}")
                        answer += "\n\n**Sources:**\n" + "\n".join(citations)

                    st.markdown(answer)
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": answer}
                    )
                except Exception as e:
                    error_msg = f"Error: {e}"
                    st.error(error_msg)
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": error_msg}
                    )

# ── Tab 2: File a Case ───────────────────────────────────────────────────────

with tab2:
    st.header("File a Case")

    freshdesk_domain = os.getenv("FRESHDESK_DOMAIN", "")
    freshdesk_key = os.getenv("FRESHDESK_API_KEY", "")
    if not freshdesk_domain or not freshdesk_key:
        st.warning(
            "Freshdesk is not configured. "
            "Set FRESHDESK_DOMAIN and FRESHDESK_API_KEY in your .env file."
        )

    with st.form("case_form"):
        st.subheader("Case Details")
        email = st.text_input("Email Address")
        subject = st.text_input("Subject")
        priority = st.selectbox(
            "Priority",
            options=[1, 2, 3, 4],
            format_func=lambda x: {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}[x],
            index=0,
        )
        description = st.text_area("Describe the Issue")

        submitted = st.form_submit_button("Submit Case")

    if submitted:
        if not email or not subject or not description:
            st.error("Please fill in Email, Subject, and Description.")
        else:
            case_data = {
                "email": email,
                "subject": subject,
                "description": description,
                "priority": priority,
            }

            with st.spinner("Filing case..."):
                try:
                    from file_case import file_case

                    result = file_case(case_data)

                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(f"Case filing failed: {result['message']}")
                except Exception as e:
                    st.error(f"Error: {e}")
