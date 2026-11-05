const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const toggleDebugBtn = document.getElementById("toggle-debug");

let showDebug = false;

toggleDebugBtn.addEventListener("click", () => {
    showDebug = !showDebug;
    toggleDebugBtn.textContent = showDebug
        ? "Ocultar detalhes técnicos"
        : "Mostrar detalhes técnicos (similaridade / votação)";
});

function appendMessage(role, text, extra) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    wrapper.appendChild(bubble);

    if (extra && extra.meta) {
        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = extra.meta;
        bubble.appendChild(meta);
    }

    if (extra && extra.matches && extra.matches.length && showDebug) {
        const debugBox = document.createElement("div");
        debugBox.className = "debug";
        const rows = extra.matches
            .map(
                (m) =>
                    `<tr><td>${m.question}</td><td>${m.intent}</td><td>${(m.similarity * 100).toFixed(1)}%</td></tr>`
            )
            .join("");
        debugBox.innerHTML = `
            <strong>Top-K similares (votação por maioria)</strong>
            <table>
                <thead><tr><th>Pergunta de referência</th><th>Intenção</th><th>Cosseno</th></tr></thead>
                <tbody>${rows}</tbody>
            </table>`;
        bubble.appendChild(debugBox);
    }

    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

chatForm.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const question = chatInput.value.trim();
    if (!question) return;

    appendMessage("user", question);
    chatInput.value = "";
    chatInput.disabled = true;

    try {
        const resp = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
        });
        const data = await resp.json();

        if (!resp.ok) {
            appendMessage("bot not_understood", data.error || "Erro ao consultar o chatbot.");
            return;
        }

        const confidencePct = (data.confidence * 100).toFixed(1);
        const meta = data.status === "answered"
            ? `categoria: ${data.category} · confiança (cosseno do voto vencedor): ${confidencePct}%`
            : `nenhuma categoria atingiu o limiar mínimo de similaridade`;

        appendMessage(
            data.status === "answered" ? "bot answered" : "bot not_understood",
            data.answer,
            { meta, matches: data.top_matches }
        );
    } catch (err) {
        appendMessage("bot not_understood", "Não foi possível falar com o servidor do chatbot.");
    } finally {
        chatInput.disabled = false;
        chatInput.focus();
    }
});
