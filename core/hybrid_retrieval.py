import re
from rank_bm25 import BM25Okapi


def tokenize(text):
    return re.findall(r"\w+", text.lower())


class HybridRetriever:
    """
    Combines semantic (embedding) search with BM25 keyword search
    using Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, collection):
        self.collection = collection
        self._build_bm25_index()

    def _build_bm25_index(self):
        # Fetch ALL documents from the ChromaDB collection
        all_data = self.collection.get(include=["documents", "metadatas"])
        self.doc_ids = all_data["ids"]
        self.documents = all_data["documents"]
        self.metadatas = all_data["metadatas"]

        tokenized_corpus = [tokenize(doc) for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_corpus)

        # Map id -> index for quick lookup
        self.id_to_index = {doc_id: i for i, doc_id in enumerate(self.doc_ids)}

    def semantic_search(self, query, embed_model, top_k=20):
        query_embedding = embed_model.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_embedding, n_results=top_k)
        return results["ids"][0]  # ranked list of doc_ids

    def bm25_search(self, query, top_k=20):
        tokenized_query = tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        # Get top_k indices sorted by score descending
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.doc_ids[i] for i in ranked_indices]

    def hybrid_search(self, query, embed_model, top_k=6, candidate_k=20, rrf_k=60):
        semantic_ids = self.semantic_search(query, embed_model, top_k=candidate_k)
        bm25_ids = self.bm25_search(query, top_k=candidate_k)

        # Reciprocal Rank Fusion: score = sum(1 / (rrf_k + rank)) across both lists
        rrf_scores = {}
        for rank, doc_id in enumerate(semantic_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank + 1)
        for rank, doc_id in enumerate(bm25_ids):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (rrf_k + rank + 1)

        # Sort by combined RRF score, descending
        ranked_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)[:top_k]

        # Return the actual chunk text + metadata for the top results
        results = []
        for doc_id in ranked_ids:
            idx = self.id_to_index[doc_id]
            results.append({
                "id": doc_id,
                "text": self.documents[idx],
                "metadata": self.metadatas[idx],
                "score": rrf_scores[doc_id]
            })
        return results