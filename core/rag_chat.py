import chromadb
from sentence_transformers import SentenceTransformer
import ollama

COLLECTION_NAME = "rfc_docs"
TOP_K = 6
OLLAMA_MODEL = "llama3.2:3b"

def retrieve_context(question, model, collection, top_k=TOP_K):
    query_embedding = model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )
    chunks = results["documents"][0]
    return chunks

def build_prompt(question, chunks):
    context = "\n\n---\n\n".join(chunks)
    prompt = f"""Answer the question using ONLY the context below. If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context}

Question:
{question}

Answer:"""
    return prompt

def main():
    print("🧠 Loading embedding model...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    print("💾 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print("\n✅ Ready! Type your networking question (or 'exit' to quit).\n")

    while True:
        question = input("🔎 Question: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        chunks = retrieve_context(question, embed_model, collection)
        prompt = build_prompt(question, chunks)

        print("\n📚 Retrieved context:")
        for i, c in enumerate(chunks):
            print(f"  [{i+1}] {c[:150]}...")

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