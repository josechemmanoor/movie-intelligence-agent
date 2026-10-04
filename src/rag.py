from __future__ import annotations

import argparse

from google import genai

from .config import GEMINI_API_KEY, GEMINI_MODEL
from .vector_store import MovieVectorStore


class MovieRAG:
    def __init__(self):
        self.store = MovieVectorStore()
        self.client = (
            genai.Client(api_key=GEMINI_API_KEY)
            if GEMINI_API_KEY
            else None
        )

    @staticmethod
    def citation(hit):
        m = hit["metadata"]
        return f"[{m['movie_title']} | {m['start']} - {m['end']}]"

    def retrieve(self, query, top_k=6, movie_title=None):
        return self.store.search(
            query,
            top_k=top_k,
            movie_title=movie_title,
        )

    def answer(self, query, top_k=6, movie_title=None):
        hits = self.retrieve(query, top_k, movie_title)

        if not hits:
            return {
                "answer": "I couldn't find a relevant scene in the indexed subtitles.",
                "sources": [],
                "hits": [],
            }

        # Build retrieved context
        context_parts = []

        for i, hit in enumerate(hits, 1):
            context_parts.append(
                f"SOURCE {i}\n"
                f"Movie: {hit['metadata']['movie_title']}\n"
                f"Time: {hit['metadata']['start']} --> "
                f"{hit['metadata']['end']}\n"
                f"Dialogue: {hit['text']}"
            )

        context = "\n\n".join(context_parts)

        # No Gemini API key
        if not self.client:
            answer = (
                "Relevant dialogue found:\n\n"
                + "\n\n".join(
                    f"{self.citation(h)} {h['text']}"
                    for h in hits[:3]
                )
            )

        # Gemini available
        else:
            prompt = f"""You are a movie subtitle research assistant.

Answer the user's question using ONLY the retrieved subtitle
evidence below.

Rules:
- Do not invent plot details, dialogue, characters, or timestamps.
- If the evidence is insufficient, explicitly say so.
- Every substantive claim must have a citation.
- Citations must use exactly this format:
  [Movie Title | HH:MM:SS,mmm - HH:MM:SS,mmm]

User question:
{query}

Retrieved subtitle evidence:

{context}
"""

            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )

                answer = response.text.strip()

            except Exception as e:
                print(f"Gemini generation unavailable: {e}")

                answer = (
                    "Gemini is temporarily unavailable, but the "
                    "RAG engine retrieved the following relevant "
                    "subtitle evidence:\n\n"
                )

                for hit in hits[:3]:
                    answer += (
                        f"{self.citation(hit)}\n"
                        f"{hit['text']}\n\n"
                    )

        # Build source information
        sources = []

        for hit in hits:
            sources.append(
                {
                    "citation": self.citation(hit),
                    "movie": hit["metadata"]["movie_title"],
                    "start": hit["metadata"]["start"],
                    "end": hit["metadata"]["end"],
                    "text": hit["text"],
                    "similarity": round(hit["similarity"], 4),
                }
            )

        return {
            "answer": answer,
            "sources": sources,
            "hits": hits,
        }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "query",
        nargs="?",
        default="What does Cooper say about his father?",
    )

    args = parser.parse_args()

    rag = MovieRAG()
    result = rag.answer(args.query)

    print("=" * 60)
    print("MOVIE RAG TEST")
    print("=" * 60)

    print(result["answer"])

    print("\nSources:")

    for source in result["sources"]:
        print(source["citation"])


if __name__ == "__main__":
    main()