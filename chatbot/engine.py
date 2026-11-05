"""
Motor do chatbot de FAQ escolar (PC.8).

Resumo do algoritmo:
    1. As perguntas de referência (paráfrases cadastradas no banco) formam o
       corpus. Cada uma é convertida para bag of words com transformação
       TF-IDF (scikit-learn TfidfVectorizer, usando a pipeline de
       pré-processamento de chatbot/preprocessing.py como tokenizer).
    2. A pergunta do usuário é transformada usando o MESMO vocabulário
       (vectorizer já treinado / "fit" no corpus de referência).
    3. Calcula-se a similaridade de cosseno entre o vetor da pergunta do
       usuário e cada vetor de referência.
    4. Pega-se o top-K das perguntas de referência mais similares
       (K configurável, default 5).
    5. Faz-se VOTAÇÃO POR MAIORIA: cada pergunta de referência do top-K vota
       na "intenção" (answer) à qual pertence. A intenção mais votada
       define a resposta. Empate é desfeito pela soma das similaridades dos
       votos e, em último caso, pela maior similaridade individual.
    6. Se a melhor similaridade entre todas as perguntas de referência for
       menor que um limiar mínimo, o chatbot assume que não entendeu a
       pergunta e devolve uma resposta padrão sugerindo as categorias que
       ele sabe tratar (escopo/contexto do chatbot).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import database as db
from .preprocessing import preprocess

DEFAULT_TOP_K = 5
DEFAULT_MIN_SIMILARITY = 0.15


@dataclass
class MatchDebug:
    question: str
    intent: str
    category: str
    similarity: float


@dataclass
class AnswerResult:
    status: str  # "answered" | "not_understood"
    answer: str
    category: str | None = None
    intent: str | None = None
    confidence: float = 0.0
    top_matches: list[MatchDebug] = field(default_factory=list)


class ChatbotEngine:
    """Encapsula o vectorizer TF-IDF, o corpus de referência e a lógica de resposta."""

    def __init__(
        self,
        db_path: Path | str = db.DEFAULT_DB_PATH,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> None:
        self.db_path = db_path
        self.top_k = top_k
        self.min_similarity = min_similarity
        self.reference_items: list[db.ReferenceItem] = []
        self.vectorizer: TfidfVectorizer | None = None
        self.matrix = None
        self._load_corpus()

    # -- montagem do corpus / vetorização -----------------------------------
    def _load_corpus(self) -> None:
        with db.get_connection(self.db_path) as conn:
            db.init_schema(conn)
            db.seed_from_json(conn)
            self.reference_items = db.fetch_reference_corpus(conn)

        if not self.reference_items:
            raise RuntimeError(
                "Corpus de referência vazio. Rode 'python seed_db.py' para popular o banco."
            )

        corpus_texts = [item.question for item in self.reference_items]

        # tokenizer customizado = pipeline completa de pré-processamento
        # (minúsculas -> remoção de caracteres especiais -> tokenização ->
        #  remoção de stopwords -> stemização). lowercase=False e
        # preprocessor=identidade porque isso já é feito dentro de preprocess().
        self.vectorizer = TfidfVectorizer(
            tokenizer=preprocess,
            preprocessor=lambda x: x,
            lowercase=False,
            token_pattern=None,
            norm="l2",
            use_idf=True,
            smooth_idf=True,
        )
        self.matrix = self.vectorizer.fit_transform(corpus_texts)

    def categories(self):
        with db.get_connection(self.db_path) as conn:
            return [dict(row) for row in db.fetch_categories(conn)]

    # -- resposta -------------------------------------------------------------
    def answer(self, user_question: str, log: bool = True) -> AnswerResult:
        user_question = (user_question or "").strip()
        if not user_question:
            result = AnswerResult(
                status="not_understood",
                answer=self._fallback_message(),
            )
            if log:
                self._log(user_question, result)
            return result

        user_vec = self.vectorizer.transform([user_question])

        if user_vec.nnz == 0:
            result = AnswerResult(status="not_understood", answer=self._fallback_message())
            if log:
                self._log(user_question, result)
            return result

        sims = cosine_similarity(user_vec, self.matrix)[0]
        ranked_idx = sims.argsort()[::-1]

        top_candidates = [i for i in ranked_idx[: self.top_k] if sims[i] > 0]

        if not top_candidates or sims[top_candidates[0]] < self.min_similarity:
            result = AnswerResult(
                status="not_understood",
                answer=self._fallback_message(),
                confidence=float(sims[ranked_idx[0]]) if len(ranked_idx) else 0.0,
                top_matches=self._debug_matches(top_candidates, sims),
            )
            if log:
                self._log(user_question, result)
            return result

        # --- votação por maioria entre o top-K --------------------------------
        votes: Counter[str] = Counter()
        sim_sum: dict[str, float] = defaultdict(float)
        sim_max: dict[str, float] = defaultdict(float)
        for idx in top_candidates:
            intent_slug = self.reference_items[idx].intent_slug
            votes[intent_slug] += 1
            sim_sum[intent_slug] += sims[idx]
            sim_max[intent_slug] = max(sim_max[intent_slug], sims[idx])

        winner_slug = max(votes, key=lambda slug: (votes[slug], sim_sum[slug], sim_max[slug]))
        winner_item = next(
            item for i, item in enumerate(self.reference_items) if item.intent_slug == winner_slug
        )

        result = AnswerResult(
            status="answered",
            answer=winner_item.answer,
            category=winner_item.category_name,
            intent=winner_slug,
            confidence=float(sim_max[winner_slug]),
            top_matches=self._debug_matches(top_candidates, sims),
        )
        if log:
            self._log(user_question, result)
        return result

    # -- auxiliares -------------------------------------------------------------
    def _debug_matches(self, idxs: list[int], sims) -> list[MatchDebug]:
        return [
            MatchDebug(
                question=self.reference_items[i].question,
                intent=self.reference_items[i].intent_slug,
                category=self.reference_items[i].category_name,
                similarity=float(sims[i]),
            )
            for i in idxs
        ]

    def _fallback_message(self) -> str:
        cats = ", ".join(c["name"] for c in self.categories())
        return (
            "Desculpe, não entendi sua pergunta dentro do contexto deste chatbot escolar. "
            f"Posso ajudar com: {cats}. Tente reformular a pergunta."
        )

    def _log(self, user_question: str, result: AnswerResult) -> None:
        with db.get_connection(self.db_path) as conn:
            db.log_conversation(
                conn,
                user_question=user_question,
                matched_intent=result.intent,
                matched_category=result.category,
                answer=result.answer,
                confidence=result.confidence,
                status=result.status,
            )
