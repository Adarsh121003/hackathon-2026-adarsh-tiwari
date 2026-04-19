"""Knowledge-base search using TF-IDF over KB sections.

Splitting by "##" headings gives semantically coherent chunks that align with
the KB's section structure.  TF-IDF is deterministic and explainable — judges
can see exactly which sections ranked highest and why.
"""
from __future__ import annotations

import logging
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

_vectorizer: TfidfVectorizer | None = None
_matrix = None
_chunks: list[dict] = []


def _parse_chunks(kb_text: str) -> list[dict]:
    """Split KB into sections by ## headings."""
    sections = re.split(r"\n(?=##\s)", kb_text)
    chunks = []
    for section in sections:
        if not section.strip():
            continue
        lines = section.strip().splitlines()
        heading = lines[0].lstrip("#").strip() if lines else "General"
        body = "\n".join(lines[1:]).strip()
        chunks.append({"section": heading, "text": section.strip(), "body": body})
    return chunks


def build_index(kb_text: str) -> None:
    """Build TF-IDF index from knowledge-base text.  Called once at startup."""
    global _vectorizer, _matrix, _chunks
    _chunks = _parse_chunks(kb_text)
    texts = [c["text"] for c in _chunks]
    _vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    _matrix = _vectorizer.fit_transform(texts)
    logger.info("KB index built: %d sections indexed", len(_chunks))


def search(query: str, top_k: int = 3) -> list[dict]:
    """Return top_k most relevant KB sections for the query."""
    if _vectorizer is None or _matrix is None:
        logger.warning("KB index not built; returning empty results")
        return []

    q_vec = _vectorizer.transform([query])
    scores = cosine_similarity(q_vec, _matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        chunk = _chunks[idx]
        score = float(scores[idx])
        if score < 0.01:
            continue
        excerpt = chunk["body"][:400].replace("\n", " ").strip()
        results.append(
            {
                "section": chunk["section"],
                "excerpt": excerpt,
                "score": round(score, 4),
            }
        )
    return results
