import chromadb
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "rfc_docs"
QUERY = "Why does OSPF adjacency fail?"
TOP_K = 3

def main():
    print(f"🔎 Query: {QUERY}\n")

    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("🔢 Embedding the query...")
    query_embedding = model.encode([QUERY]).tolist()

    print("💾 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print(f"📚 Retrieving top {TOP_K} chunks...\n")
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=TOP_K
    )

    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    )):
        print(f"--- Result {i+1} (distance: {dist:.4f}) ---")
        print(f"Source: {meta.get('source')} | chunk_index: {meta.get('chunk_index')}")
        print(doc.strip()[:400])
        print()

if __name__ == "__main__":
    main()