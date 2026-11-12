"""Mostra o que está salvo no banco SQLite (data/faq.db).

Uso:
    python ver_banco.py              # resumo + categorias, intenções e frases de treino
    python ver_banco.py historico    # últimas 20 conversas salvas

Útil na apresentação para provar que os dados estão persistidos no banco
(e não só no arquivo JSON).
"""

from __future__ import annotations

import sys

from chatbot import database as db


def mostrar_faq(conn) -> None:
    n_cat = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    n_int = conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0]
    n_q = conn.execute("SELECT COUNT(*) FROM reference_questions").fetchone()[0]
    n_log = conn.execute("SELECT COUNT(*) FROM conversation_log").fetchone()[0]

    print(f"Banco: {db.DEFAULT_DB_PATH}")
    print(f"{n_cat} categorias | {n_int} intenções | {n_q} frases de treino | {n_log} conversas no histórico\n")

    categorias = conn.execute("SELECT id, slug, name FROM categories ORDER BY id").fetchall()
    for cat in categorias:
        print(f"[{cat['slug']}] {cat['name']}")
        intents = conn.execute(
            "SELECT id, slug FROM intents WHERE category_id = ? ORDER BY id", (cat["id"],)
        ).fetchall()
        for intent in intents:
            perguntas = conn.execute(
                "SELECT question FROM reference_questions WHERE intent_id = ? ORDER BY id",
                (intent["id"],),
            ).fetchall()
            print(f"    {intent['slug']} ({len(perguntas)} frases)")
            for p in perguntas:
                print(f"        - {p['question']}")
        print()


def mostrar_historico(conn) -> None:
    rows = db.fetch_conversation_log(conn, limit=20)
    if not rows:
        print("Histórico vazio. Faça perguntas no chat (python app.py) e rode de novo.")
        return
    for r in rows:
        conf = f"{r['confidence']:.3f}" if r["confidence"] is not None else "-"
        print(f"{r['created_at']} | {r['status']:<14} | {r['matched_intent'] or '-':<32} | conf {conf} | {r['user_question']}")


if __name__ == "__main__":
    with db.get_connection() as conn:
        db.init_schema(conn)
        db.seed_from_json(conn)
        if len(sys.argv) > 1 and sys.argv[1] == "historico":
            mostrar_historico(conn)
        else:
            mostrar_faq(conn)
