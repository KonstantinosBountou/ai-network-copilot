import json
import chromadb
from sentence_transformers import SentenceTransformer
import ollama

from config_parser import load_config, parse_config, CONFIG_PATH
from log_parser import load_log, parse_log, LOG_PATH

COLLECTION_NAME = "rfc_docs"
TOP_K = 6
OLLAMA_MODEL = "llama3.2:3b"


def get_config_summary():
    text = load_config(CONFIG_PATH)
    parsed = parse_config(text)
    return parsed


def get_log_summary():
    lines = load_log(LOG_PATH)
    events = parse_log(lines)
    # Only keep the "interesting" events (not UNKNOWN) to reduce noise
    return [e for e in events if e["type"] != "UNKNOWN"]


def retrieve_rfc_context(question, embed_model, collection, top_k=TOP_K):
    query_embedding = embed_model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    return results["documents"][0]


def build_combined_prompt(question, config_summary, log_summary, rfc_chunks):
    config_text = json.dumps(config_summary, indent=2)
    log_text = json.dumps(log_summary, indent=2)
    rfc_text = "\n\n---\n\n".join(rfc_chunks)

    prompt = f"""You are a network troubleshooting assistant. Use the information below to answer the question.
Ground your answer in the provided data. If something cannot be determined from the data, say so clearly.

=== ROUTER CONFIGURATION ===
{config_text}

=== RECENT LOG EVENTS ===
{log_text}

=== RELEVANT RFC KNOWLEDGE (RFC 2328 - OSPF) ===
{rfc_text}

=== QUESTION ===
{question}

Provide your answer in this format:
Cause: <short explanation of what happened>
Explanation: <why it happened, referencing config/logs/RFC as relevant>
Fix: <suggested next steps or commands>
"""
    return prompt


def main():
    print("🧠 Loading embedding model...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    print("💾 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print("📄 Loading config and logs...")
    config_summary = get_config_summary()
    log_summary = get_log_summary()

    print("\n✅ Ready! Ask a troubleshooting question (or 'exit' to quit).\n")

    while True:
        question = input("🔎 Question: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        rfc_chunks = retrieve_rfc_context(question, embed_model, collection)
        prompt = build_combined_prompt(question, config_summary, log_summary, rfc_chunks)

        print("\n🤖 Thinking...\n")
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )

        print("💬 Answer:")
        print(response["message"]["content"])
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()