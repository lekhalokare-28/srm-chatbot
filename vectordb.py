import chromadb
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "knowledge_base.json")
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name="srm_knowledge", metadata={"hnsw:space": "cosine"})


def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i:i + chunk_size]))
        i += chunk_size - overlap
    return chunks


def build_vector_store():
    if not os.path.exists(DATA_PATH):
        print("ERROR: knowledge_base.json not found. Run scraper first.")
        return False

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    collection = get_collection()
    print(f"\nIndexing {len(data)} pages into ChromaDB...")

    doc_id = 0
    for page in data:
        if page["status"] != "success" or not page["content"]:
            continue
        for i, chunk in enumerate(chunk_text(page["content"])):
            if len(chunk.strip()) < 50:
                continue
            try:
                collection.add(
                    documents=[chunk],
                    metadatas=[{"source": page["url"], "label": page["label"], "chunk_index": i}],
                    ids=[f"doc_{doc_id}"]
                )
                doc_id += 1
            except Exception:
                pass

    print(f"Indexed {doc_id} chunks from {len(data)} pages.")
    return True


def search(query, n_results=5):
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
    output = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            output.append({
                "content": doc,
                "source_url": results["metadatas"][0][i]["source"],
                "label": results["metadatas"][0][i]["label"],
            })
    return output


if __name__ == "__main__":
    print("Building vector store...")
    build_vector_store()
    print("\nTest search: 'robotics courses'")
    for r in search("robotics courses", n_results=3):
        print(f"\n[{r['label']}] {r['source_url']}")
        print(r["content"][:150])
