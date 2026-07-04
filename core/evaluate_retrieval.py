import chromadb
from sentence_transformers import SentenceTransformer
from hybrid_retrieval import HybridRetriever

COLLECTION_NAME = "rfc_docs"
TOP_K = 6

# Ground truth test set: question -> expected source RFC + required keywords
# A "hit" now requires the expected source AND at least one chunk containing
# ALL of the required keywords (case-insensitive).
TEST_SET = [
    {
        "question": "Why does OSPF adjacency fail?",
        "expected_source": "rfc2328",
        "required_keywords": ["dead"],  # Dead timer / RouterDeadInterval
    },
    {
        "question": "What is the Designated Router in OSPF?",
        "expected_source": "rfc2328",
        "required_keywords": ["designated router"],
    },
    {
        "question": "What are the OSPF neighbor states?",
        "expected_source": "rfc2328",
        "required_keywords": ["exstart"],
    },
    {
        "question": "How does the Hello protocol work in OSPF?",
        "expected_source": "rfc2328",
        "required_keywords": ["hello"],
    },
    {
        "question": "What is split horizon in RIP?",
        "expected_source": "rfc2453",
        "required_keywords": ["split horizon"],
    },
    {
        "question": "What is the maximum hop count in RIP?",
        "expected_source": "rfc2453",
        "required_keywords": ["16"],  # RIP infinity metric
    },
    {
        "question": "How does RIP handle routing loops?",
        "expected_source": "rfc2453",
        "required_keywords": ["poison"],  # poison reverse
    },
    {
        "question": "What is the purpose of BGP path attributes?",
        "expected_source": "rfc4271",
        "required_keywords": ["path attribute"],
    },
    {
        "question": "What is the BGP hold timer?",
        "expected_source": "rfc4271",
        "required_keywords": ["hold time"],
    },
    {
        "question": "How does BGP select the best path?",
        "expected_source": "rfc4271",
        "required_keywords": ["decision"],
    },
    {
        "question": "What is an autonomous system in BGP?",
        "expected_source": "rfc4271",
        "required_keywords": ["autonomous system"],
    },
    {
        "question": "Why would a BGP neighbor session reset?",
        "expected_source": "rfc4271",
        "required_keywords": ["notification"],
    },
]


def check_hit(sources, texts, expected_source, required_keywords):
    """A hit = at least one chunk that matches BOTH the expected source
    AND contains all required keywords in its text (case-insensitive)."""
    for source, text in zip(sources, texts):
        if source != expected_source:
            continue
        text_lower = text.lower()
        if all(kw.lower() in text_lower for kw in required_keywords):
            return True
    return False


def semantic_only_search(question, embed_model, collection, top_k=TOP_K):
    query_embedding = embed_model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=top_k)
    sources = [meta.get("source") for meta in results["metadatas"][0]]
    texts = results["documents"][0]
    return sources, texts


def evaluate():
    print("🧠 Loading embedding model...")
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")

    print("💾 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path="data/chroma_db")
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    print("🔧 Building hybrid retriever (BM25 index)...")
    retriever = HybridRetriever(collection)

    semantic_hits = 0
    hybrid_hits = 0
    total = len(TEST_SET)

    print(f"\n{'='*80}")
    print(f"Running STRICT evaluation on {total} test questions...")
    print(f"(hit = correct RFC source AND required keyword(s) present in chunk text)")
    print(f"{'='*80}\n")

    for item in TEST_SET:
        question = item["question"]
        expected = item["expected_source"]
        keywords = item["required_keywords"]

        # Semantic-only
        semantic_sources, semantic_texts = semantic_only_search(question, embed_model, collection)
        semantic_hit = check_hit(semantic_sources, semantic_texts, expected, keywords)

        # Hybrid
        hybrid_results = retriever.hybrid_search(question, embed_model, top_k=TOP_K)
        hybrid_sources = [r["metadata"].get("source") for r in hybrid_results]
        hybrid_texts = [r["text"] for r in hybrid_results]
        hybrid_hit = check_hit(hybrid_sources, hybrid_texts, expected, keywords)

        semantic_hits += int(semantic_hit)
        hybrid_hits += int(hybrid_hit)

        status_semantic = "✅" if semantic_hit else "❌"
        status_hybrid = "✅" if hybrid_hit else "❌"

        print(f"Q: {question}")
        print(f"   Required keywords: {keywords}")
        print(f"   Semantic-only: {status_semantic}")
        print(f"   Hybrid:        {status_hybrid}")
        print()

    semantic_accuracy = semantic_hits / total * 100
    hybrid_accuracy = hybrid_hits / total * 100

    print(f"{'='*80}")
    print(f"RESULTS (strict: correct source + required keywords in chunk text)")
    print(f"{'='*80}")
    print(f"Semantic-only accuracy: {semantic_hits}/{total} = {semantic_accuracy:.1f}%")
    print(f"Hybrid accuracy:        {hybrid_hits}/{total} = {hybrid_accuracy:.1f}%")
    print(f"{'='*80}")


if __name__ == "__main__":
    evaluate()