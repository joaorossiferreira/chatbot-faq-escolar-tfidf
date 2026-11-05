"""
Teste manual/smoke-test do chatbot (PC.8).

Não depende de pytest: roda com `python tests/test_chatbot.py` a partir da
raiz do projeto e imprime, para cada pergunta de teste, a resposta, a
categoria, a confiança e o top-K usado na votação por maioria — útil tanto
para validar o motor quanto para ensaiar a apresentação.

Usa um banco SQLite temporário (não mexe no data/faq.db "de produção").
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chatbot import database as db  # noqa: E402
from chatbot.engine import ChatbotEngine  # noqa: E402
from chatbot.preprocessing import preprocess  # noqa: E402

CASES = [
    # (pergunta do usuário, intent esperada)
    ("Que horas comeca a aula?", "horario_aulas"),
    ("Onde acho o horario das minhas materias", "horario_disciplinas"),
    ("Quando sao as ferias?", "calendario_academico"),
    ("Como eu me matriculo?", "como_matricular"),
    ("Preciso de uma declaracao que estou matriculado", "declaracao_matricula"),
    ("A biblioteca abre que horas", "horario_biblioteca"),
    ("Como pego um livro emprestado", "emprestimo_livro"),
    ("Qual o telefone pra falar com a secretaria", "contato_secretaria"),
    ("Onde fica a secretaria da faculdade", "localizacao_secretaria"),
    ("Como vejo minha nota da prova", "consultar_notas"),
    ("Quantas faltas eu tenho", "consultar_faltas"),
    ("Como funciona a prova de recuperacao", "recuperacao"),
]

OUT_OF_SCOPE = [
    "Qual a previsao do tempo para amanha?",
    "Quero pedir uma pizza",
]


def test_preprocessing_pipeline():
    tokens = preprocess("Olá! Qual é O HORÁRIO das Aulas???")
    assert "ola" not in tokens  # stopword / saudação removida
    assert all(t.islower() for t in tokens)
    assert not any(ch in "".join(tokens) for ch in "!?.,;")
    print("[OK] pré-processamento ->", tokens)


def _build_engine() -> ChatbotEngine:
    tmp_dir = tempfile.mkdtemp(prefix="pc8_chatbot_test_")
    tmp_db = Path(tmp_dir) / "faq_test.db"
    with db.get_connection(tmp_db) as conn:
        db.init_schema(conn)
        db.seed_from_json(conn)
    return ChatbotEngine(db_path=tmp_db)


def test_engine_matches_expected_intent():
    engine = _build_engine()
    correct = 0
    for question, expected_intent in CASES:
        result = engine.answer(question, log=False)
        ok = result.intent == expected_intent
        correct += int(ok)
        flag = "OK " if ok else "FAIL"
        print(
            f"[{flag}] '{question}' -> intent={result.intent} "
            f"(esperado={expected_intent}) confiança={result.confidence:.3f} status={result.status}"
        )
        if not ok:
            print("        top_matches:", [(m.intent, round(m.similarity, 3)) for m in result.top_matches])
    accuracy = correct / len(CASES)
    print(f"\nAcurácia nos casos de teste: {accuracy:.0%} ({correct}/{len(CASES)})")
    assert accuracy >= 0.8, "motor do chatbot errou demais nos casos de teste"


def test_out_of_scope_falls_back():
    engine = _build_engine()
    for question in OUT_OF_SCOPE:
        result = engine.answer(question, log=False)
        print(f"[fora de escopo] '{question}' -> status={result.status}")
        assert result.status == "not_understood"


if __name__ == "__main__":
    test_preprocessing_pipeline()
    print()
    test_engine_matches_expected_intent()
    print()
    test_out_of_scope_falls_back()
    print("\nTodos os smoke tests passaram.")
