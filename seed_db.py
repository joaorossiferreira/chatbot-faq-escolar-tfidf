"""Cria (ou recria, com --force) e popula o banco SQLite com os dados do FAQ.

Uso:
    python seed_db.py            # cria o banco se ele não existir / não estiver populado
    python seed_db.py --force    # apaga os dados e recarrega a partir de data/faq_seed.json
"""

from __future__ import annotations

import argparse

from chatbot import database as db


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="apaga categorias/intents/perguntas existentes e recarrega do zero",
    )
    args = parser.parse_args()

    with db.get_connection() as conn:
        db.init_schema(conn)
        db.seed_from_json(conn, force=args.force)
        n_intents = len(db.fetch_reference_corpus(conn))

    print(f"Banco pronto em: {db.DEFAULT_DB_PATH}")
    print(f"Perguntas de referência carregadas: {n_intents}")


if __name__ == "__main__":
    main()
