from dataclasses import dataclass
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    source: str
    content: str


class KnowledgeBase:
    """A small local retrieval baseline using Chinese character n-gram vectors."""

    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.documents: list[KnowledgeDocument] = []
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        self.document_vectors = None
        self.reindex()

    def reindex(self) -> int:
        documents: list[KnowledgeDocument] = []
        for path in sorted(self.knowledge_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8").strip()
            if not content:
                continue
            first_line = content.splitlines()[0].lstrip("# ").strip()
            documents.append(
                KnowledgeDocument(
                    title=first_line or path.stem,
                    source=path.name,
                    content=content,
                )
            )

        self.documents = documents
        corpus = [document.content for document in documents]
        self.document_vectors = self.vectorizer.fit_transform(corpus) if corpus else None
        return len(documents)

    def search(self, question: str, top_k: int = 2) -> list[dict]:
        if not self.documents or self.document_vectors is None:
            return []

        query_vector = self.vectorizer.transform([question])
        scores = cosine_similarity(query_vector, self.document_vectors)[0]
        ranked_indices = scores.argsort()[::-1][:top_k]
        matches = []
        for index in ranked_indices:
            score = float(scores[index])
            if score <= 0:
                continue
            document = self.documents[int(index)]
            matches.append(
                {
                    "title": document.title,
                    "source": document.source,
                    "content": document.content,
                    "score": round(score, 4),
                }
            )
        return matches


