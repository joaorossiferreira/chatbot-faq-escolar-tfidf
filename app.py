"""
Aplicação Flask do chatbot de FAQ escolar (PC.8).

Rotas:
    GET  /                 página única com a interface de chat
    POST /api/chat         recebe {"question": "..."} e devolve a resposta do chatbot
    GET  /api/categories   lista as categorias (contexto) que o chatbot sabe responder
    GET  /api/history      histórico de conversas persistido no banco (para demonstração)
"""

from __future__ import annotations

from dataclasses import asdict

from flask import Flask, jsonify, render_template, request

from chatbot import database as db
from chatbot.engine import ChatbotEngine

app = Flask(__name__)
engine = ChatbotEngine()


@app.get("/")
def index():
    return render_template("index.html", categories=engine.categories())


@app.get("/api/categories")
def api_categories():
    return jsonify(engine.categories())


@app.post("/api/chat")
def api_chat():
    payload = request.get_json(silent=True) or {}
    question = (payload.get("question") or "").strip()

    if not question:
        return jsonify({"error": "Envie um campo 'question' não vazio."}), 400

    result = engine.answer(question)
    data = asdict(result)
    return jsonify(data)


@app.get("/api/history")
def api_history():
    limit = request.args.get("limit", default=20, type=int)
    with db.get_connection() as conn:
        rows = db.fetch_conversation_log(conn, limit=limit)
    return jsonify([dict(row) for row in rows])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
