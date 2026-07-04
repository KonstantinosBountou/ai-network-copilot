import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "core"))

import json
import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
import ollama

from config_parser import parse_config
from log_parser import parse_log
from hybrid_retrieval import HybridRetriever

COLLECTION_NAME = "rfc_docs"
TOP_K = 6
OLLAMA_MODEL = "llama3.2:3b"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "configs", "sample_router1.cfg")
DEFAULT_LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "logs", "sample_router1.log")

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


@st.cache_resource
def load_embed_model():
    return SentenceTransformer("all-MiniLM-L6-v2")


@st.cache_resource
def load_chroma_collection():
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME)


@st.cache_resource
def load_hybrid_retriever(_collection):
    return HybridRetriever(_collection)


def read_default_file(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def build_combined_prompt(question, config_summary, log_summary, rfc_results):
    config_text = json.dumps(config_summary, indent=2)
    log_text = json.dumps(log_summary, indent=2)
    rfc_text = "\n\n---\n\n".join(
        f"[Source: {r['metadata'].get('source')}] {r['text']}" for r in rfc_results
    )

    return f"""You are a network troubleshooting assistant. Use ONLY the information below to answer the question.

STRICT RULES:
- The "Cause" MUST be based only on what is explicitly present in the CONFIGURATION or LOG EVENTS below. Do not invent causes that are not shown in the logs.
- The RFC KNOWLEDGE section may or may not be relevant to this specific question. Only cite it if it directly explains a mechanism seen in the logs/config. If the RFC chunks are not relevant, ignore them and say the explanation is based on the logs only.
- Never invent commands, parameters, or limits (e.g. max-prefix, specific thresholds) that are not explicitly present in the provided data.
- If you are not sure about something, say "not determinable from the provided data" instead of guessing.

=== ROUTER CONFIGURATION ===
{config_text}

=== RECENT LOG EVENTS ===
{log_text}

=== RFC KNOWLEDGE (may or may not be relevant — use only if it clearly applies) ===
{rfc_text}

=== QUESTION ===
{question}

Provide your answer in this format:
Cause: <short explanation of what happened, based strictly on logs/config>
Explanation: <why it happened; cite RFC only if truly relevant>
Fix: <suggested next steps, based on standard practice for this type of issue>
"""


# --- Streamlit UI ---
st.set_page_config(page_title="AI Network Copilot", page_icon="🌐", layout="wide")
st.title("🌐 AI Network Copilot")
st.caption("RAG-powered troubleshooting assistant for network engineers")

with st.spinner("Loading models..."):
    embed_model = load_embed_model()
    collection = load_chroma_collection()
    retriever = load_hybrid_retriever(collection)

st.sidebar.header("📂 Input Data")
config_file = st.sidebar.file_uploader("Upload a router config (.cfg/.txt)", type=["cfg", "txt", "conf"])
log_file = st.sidebar.file_uploader("Upload a log file (.log/.txt)", type=["log", "txt"])

use_defaults = st.sidebar.checkbox("Use sample data instead", value=not (config_file or log_file))

if use_defaults:
    config_text = read_default_file(DEFAULT_CONFIG_PATH)
    log_text = read_default_file(DEFAULT_LOG_PATH)
    st.sidebar.info("Using built-in sample Router1 config/log.")
else:
    config_text = config_file.read().decode("utf-8", errors="ignore") if config_file else ""
    log_text = log_file.read().decode("utf-8", errors="ignore") if log_file else ""
    if not config_file:
        st.sidebar.warning("No config uploaded yet.")
    if not log_file:
        st.sidebar.warning("No log file uploaded yet.")

config_summary = parse_config(config_text) if config_text else {}
log_summary = [e for e in parse_log(log_text.splitlines()) if e["type"] != "UNKNOWN"] if log_text else []

col1, col2 = st.columns([1, 1])
with col1:
    with st.expander("📄 Loaded Router Config"):
        st.json(config_summary)
with col2:
    with st.expander("📋 Loaded Log Events"):
        st.json(log_summary)

st.divider()

question = st.text_input("🔎 Ask a troubleshooting question:", placeholder="Why did GigabitEthernet0/0 go down?")

if st.button("Ask") and question:
    if not config_summary and not log_summary:
        st.error("Please upload a config and/or log file first, or use sample data.")
    else:
        with st.spinner("Retrieving context (hybrid search)..."):
            rfc_results = retriever.hybrid_search(question, embed_model, top_k=TOP_K)
            prompt = build_combined_prompt(question, config_summary, log_summary, rfc_results)

        def stream_response():
            stream = ollama_client.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            for chunk in stream:
                yield chunk["message"]["content"]

        st.subheader("💬 Answer")
        answer = st.write_stream(stream_response())

        with st.expander("📚 Retrieved RFC context (hybrid search, for transparency)"):
            for i, r in enumerate(rfc_results):
                st.text(f"[{i+1}] Source: {r['metadata'].get('source')} (score: {r['score']:.4f})")
                st.text(r["text"][:300] + "...")
                st.text("")