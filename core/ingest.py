import os
import glob
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

# --- Config ---
RFC_DIR = "data/rfc"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
COLLECTION_NAME = "rfc_docs"

def load_text(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    return splitter.split_text(text)

def main():
    rfc_files = glob.glob(os.path.join(RFC_DIR, "*.txt"))
    print(f"📄 Found {len(rfc_files)} RFC file(s): {[os.path.basename(f) for f in rfc_files]}")

    print("🧠 Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("💾 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    total_chunks = 0

    for rfc_path in rfc_files:
        rfc_name = os.path.splitext(os.path.basename(rfc_path))[0]  # e.g. "rfc2328"
        print(f"\n--- Processing {rfc_name} ---")

        text = load_text(rfc_path)
        print(f"Loaded {len(text)} characters.")

        chunks = chunk_text(text)
        print(f"Created {len(chunks)} chunks.")

        print("Computing embeddings...")
        embeddings = model.encode(chunks, show_progress_bar=True)

        ids = [f"{rfc_name}_chunk_{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            embeddings=embeddings.tolist(),
            ids=ids,
            metadatas=[{"source": rfc_name, "chunk_index": i} for i in range(len(chunks))]
        )

        total_chunks += len(chunks)

    print(f"\n✅ Done. Stored {total_chunks} total chunks from {len(rfc_files)} RFC(s) in collection '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    main()