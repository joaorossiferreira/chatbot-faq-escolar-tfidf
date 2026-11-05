"""
Camada de persistência de dados do chatbot (PC.8) usando SQLite.

Guarda:
  - categories: categorias de perguntas que o chatbot sabe responder
  - intents: cada "intenção" (pergunta-tipo) tem uma resposta fixa
  - reference_questions: frases de treino (paráfrases) associadas a uma intent;
    são elas que formam o corpus de referência usado no BOW/TF-IDF
  - conversation_log: histórico de tudo que foi perguntado ao chatbot,
    a resposta dada, a categoria, a confiança (similaridade) e o status

SQLite foi escolhido por não exigir um servidor de banco de dados separado
(arquivo único em disco), o que facilita rodar o projeto em qualquer
máquina do grupo. Ver README.md para como trocar por outro banco.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "faq.db"
DEFAULT_SEED_PATH = BASE_DIR / "data" / "faq_seed.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    answer      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reference_questions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    intent_id INTEGER NOT NULL REFERENCES intents(id),
    question  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT NOT NULL,
    user_question    TEXT NOT NULL,
    matched_intent   TEXT,
    matched_category TEXT,
    answer           TEXT,
    confidence       REAL,
    status           TEXT NOT NULL
);
"""


@contextmanager
def get_connection(db_path: Path | str = DEFAULT_DB_PATH):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def is_seeded(conn: sqlite3.Connection) -> bool:
    row = conn.execute("SELECT COUNT(*) AS n FROM intents").fetchone()
    return row["n"] > 0


def seed_from_json(conn: sqlite3.Connection, seed_path: Path | str = DEFAULT_SEED_PATH, force: bool = False) -> None:
    """Popula o banco com as categorias/intents/perguntas de referência do FAQ.

    Idempotente: se já houver dados e force=False, não faz nada.
    """
    if is_seeded(conn) and not force:
        return

    if force:
        conn.execute("DELETE FROM reference_questions;")
        conn.execute("DELETE FROM intents;")
        conn.execute("DELETE FROM categories;")

    with open(seed_path, encoding="utf-8") as fh:
        data = json.load(fh)

    category_ids: dict[str, int] = {}
    for cat in data["categories"]:
        cur = conn.execute(
            "INSERT OR IGNORE INTO categories (slug, name, description) VALUES (?, ?, ?)",
            (cat["slug"], cat["name"], cat["description"]),
        )
        row = conn.execute("SELECT id FROM categories WHERE slug = ?", (cat["slug"],)).fetchone()
        category_ids[cat["slug"]] = row["id"]

    for intent in data["intents"]:
        cat_id = category_ids[intent["category"]]
        conn.execute(
            "INSERT OR IGNORE INTO intents (slug, category_id, answer) VALUES (?, ?, ?)",
            (intent["slug"], cat_id, intent["answer"]),
        )
        row = conn.execute("SELECT id FROM intents WHERE slug = ?", (intent["slug"],)).fetchone()
        intent_id = row["id"]
        for question in intent["questions"]:
            conn.execute(
                "INSERT INTO reference_questions (intent_id, question) VALUES (?, ?)",
                (intent_id, question),
            )


@dataclass
class ReferenceItem:
    question_id: int
    question: str
    intent_id: int
    intent_slug: str
    answer: str
    category_slug: str
    category_name: str


def fetch_reference_corpus(conn: sqlite3.Connection) -> list[ReferenceItem]:
    rows = conn.execute(
        """
        SELECT rq.id AS question_id, rq.question AS question,
               i.id AS intent_id, i.slug AS intent_slug, i.answer AS answer,
               c.slug AS category_slug, c.name AS category_name
        FROM reference_questions rq
        JOIN intents i ON i.id = rq.intent_id
        JOIN categories c ON c.id = i.category_id
        ORDER BY rq.id
        """
    ).fetchall()
    return [ReferenceItem(**dict(row)) for row in rows]


def fetch_categories(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT slug, name, description FROM categories ORDER BY name").fetchall()


def log_conversation(
    conn: sqlite3.Connection,
    user_question: str,
    matched_intent: str | None,
    matched_category: str | None,
    answer: str | None,
    confidence: float,
    status: str,
) -> None:
    conn.execute(
        """
        INSERT INTO conversation_log
            (created_at, user_question, matched_intent, matched_category, answer, confidence, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            user_question,
            matched_intent,
            matched_category,
            answer,
            confidence,
            status,
        ),
    )


def fetch_conversation_log(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM conversation_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
