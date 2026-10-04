from __future__ import annotations
import argparse
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

from .config import DATA_DIR, CHROMA_DIR, COLLECTION_NAME, EMBEDDING_MODEL
from .subtitle_parser import parse_srt, chunk_entries

class MovieVectorStore:
    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self.model = SentenceTransformer(EMBEDDING_MODEL)

    def reset(self):
        try:
            self.client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_directory(self, directory=DATA_DIR, window_size=8, overlap=2):
        directory = Path(directory)
        files = sorted(directory.glob("*.srt"))
        if not files:
            raise FileNotFoundError(f"No .srt files found in {directory}")

        total = 0
        for path in files:
            entries = parse_srt(path)
            chunks = chunk_entries(entries, window_size, overlap)
            if not chunks:
                continue

            documents = [c["text"] for c in chunks]
            embeddings = self.model.encode(
                documents, normalize_embeddings=True
            ).tolist()

            ids = [
                f"{path.stem}_{c['subtitle_start_index']}_{c['subtitle_end_index']}"
                for c in chunks
            ]
            metadatas = [
                {
                    "movie_title": c["movie_title"],
                    "start": c["start"],
                    "end": c["end"],
                    "start_seconds": c["start_seconds"],
                    "end_seconds": c["end_seconds"],
                    "source_file": c["source_file"],
                    "subtitle_start_index": c["subtitle_start_index"],
                    "subtitle_end_index": c["subtitle_end_index"],
                }
                for c in chunks
            ]

            # Upsert allows re-running ingestion safely.
            self.collection.upsert(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            total += len(chunks)
            print(f"Ingested {path.name}: {len(chunks)} chunks")

        print(f"Total chunks indexed: {total}")
        return total

    def search(self, query: str, top_k: int = 6, movie_title: str | None = None):
        embedding = self.model.encode([query], normalize_embeddings=True).tolist()[0]

        where = {"movie_title": movie_title} if movie_title else None
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        for doc, meta, distance in zip(docs, metas, distances):
            hits.append({
                "text": doc,
                "metadata": meta,
                "distance": distance,
                "similarity": 1 - distance,
            })
        return hits

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    store = MovieVectorStore()
    if args.reset:
        store.reset()
    store.ingest_directory()

if __name__ == "__main__":
    main()
