import chromadb
import time
from config import CHROMA_PERSIST_DIR


class VectorMemory:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.paths_collection = self.client.get_or_create_collection(
            name="generated_paths",
            metadata={"hnsw:space": "cosine"},
        )

    def save_path(self, goal: str, output: str, meta: dict = None):
        doc_id = f"path_{int(time.time() * 1000)}"
        self.paths_collection.add(
            documents=[output],
            metadatas=[{
                "goal": goal,
                "created_at": str(time.time()),
                **(meta or {}),
            }],
            ids=[doc_id],
        )
        return doc_id

    def search_similar_paths(self, query: str, n_results: int = 3) -> list[dict]:
        if self.paths_collection.count() == 0:
            return []
        results = self.paths_collection.query(
            query_texts=[query],
            n_results=min(n_results, self.paths_collection.count()),
        )
        return [
            {"content": doc, "metadata": results["metadatas"][0][i]}
            for i, doc in enumerate(results["documents"][0])
        ]

    def get_recent_paths(self, n: int = 10) -> list[dict]:
        count = self.paths_collection.count()
        if count == 0:
            return []
        results = self.paths_collection.get(
            limit=min(count, 200),
        )
        items = [
            {"id": results["ids"][i], "content": doc, "metadata": results["metadatas"][i]}
            for i, doc in enumerate(results["documents"])
        ]
        items.sort(key=lambda p: float(p["metadata"].get("created_at", 0)), reverse=True)
        return items[:n]

    def delete_path(self, doc_id: str) -> bool:
        existing = self.paths_collection.get(ids=[doc_id])
        if not existing or not existing["ids"]:
            return False
        self.paths_collection.delete(ids=[doc_id])
        return True

    def update_path(self, doc_id: str, output: str, meta: dict = None) -> bool:
        existing = self.get_path(doc_id)
        if existing is None:
            return False
        merged = {**existing["metadata"], **(meta or {})}
        self.paths_collection.update(
            ids=[doc_id],
            documents=[output],
            metadatas=[merged],
        )
        return True

    def count_paths(self) -> int:
        return self.paths_collection.count()

    def get_path(self, doc_id: str) -> dict | None:
        results = self.paths_collection.get(ids=[doc_id])
        if not results or not results["ids"]:
            return None
        return {
            "id": results["ids"][0],
            "content": results["documents"][0],
            "metadata": results["metadatas"][0],
        }


vector_memory = VectorMemory()
