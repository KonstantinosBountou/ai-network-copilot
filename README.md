# 🌐 AI Network Copilot

A local, RAG-powered troubleshooting assistant for network engineers. It combines router configuration parsing, syslog analysis, and RFC knowledge retrieval to answer networking questions — grounded in real data, not just general LLM knowledge.

## Features

- **RAG over networking RFCs** — OSPF (RFC 2328), RIP (RFC 2453), BGP (RFC 4271)
- **Hybrid retrieval** — combines semantic search (embeddings) with keyword search (BM25) via Reciprocal Rank Fusion
- **Config parser** — extracts structured data (interfaces, OSPF/BGP settings) from Cisco-style configs
- **Log parser** — detects and classifies network events (OSPF/BGP adjacency changes, interface state changes, STP events) with severity levels
- **Orchestrator** — combines config + logs + RFC context into a single grounded prompt
- **100% local LLM** — runs on [Ollama](https://ollama.com) (llama3.2:3b), no API costs
- **Streamlit UI** — file upload for custom configs/logs, streaming responses
- **Dockerized** — fully containerized, runs anywhere with `docker-compose up`
- **Retrieval evaluation framework** — measures retrieval accuracy against a ground-truth test set

## 🧠 Architecture

```text
User Question
     |
     v
Hybrid Retriever
(Semantic Search + BM25)
     |
     v
RFC Knowledge Base
(ChromaDB Vector Store)
     |
     v
Orchestrator
(Config Parser + Log Parser + RFC Context)
     |
     v
Local LLM
(Ollama / llama3.2:3b)
     |
     v
Streamlit UI
(Streamed Response)

## Tech Stack

Python, LangChain (text splitting), ChromaDB (vector store), Sentence-Transformers (embeddings), rank_bm25 (keyword search), Ollama (local LLM), Streamlit (UI), Docker.

## Running locally

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed, with `llama3.2:3b` pulled (`ollama pull llama3.2:3b`)

### Setup

```bash
git clone <this-repo-url>
cd ai-network-copilot
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Ingest RFC knowledge base (first time only)

```bash
python core/ingest.py
```

### Run the app

```bash
streamlit run frontend/app.py
```

Open `http://localhost:8501` in your browser.

## Running with Docker

```bash
docker-compose up --build
```

This runs the app in a container while connecting to Ollama on your host machine.

## Evaluating retrieval quality

```bash
python core/evaluate_retrieval.py
```

Compares semantic-only vs. hybrid retrieval accuracy against a ground-truth test set of networking questions.

## Project structure
ai-network-copilot/
├── core/
│   ├── ingest.py              # RFC ingestion + chunking + embeddings
│   ├── config_parser.py       # Cisco-style config parser
│   ├── log_parser.py          # Syslog event parser
│   ├── hybrid_retrieval.py    # Semantic + BM25 hybrid search
│   ├── orchestrator.py        # Combines all sources for CLI use
│   └── evaluate_retrieval.py  # Retrieval accuracy evaluation
├── frontend/
│   └── app.py                 # Streamlit UI
├── data/
│   ├── rfc/                   # RFC source documents
│   ├── configs/                # Sample router configs
│   └── logs/                   # Sample router logs
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

## Known limitations

- Small local LLM (3B params) can occasionally produce plausible-sounding but incorrect details not present in the source data (mitigated via strict prompting, but not eliminated)
- Hybrid retrieval improves some queries but not universally — see `evaluate_retrieval.py` results for a concrete, measured comparison against semantic-only search
- Currently supports Cisco-style config syntax only

## Author

Built by Konstantinos Bountourasas — Electrical & Computer Engineering, University of Peloponnese.