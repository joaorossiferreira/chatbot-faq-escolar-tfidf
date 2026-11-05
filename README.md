# PC.8 — Chatbot FAQ Escolar (Bag of Words + TF-IDF)

Chatbot de perguntas frequentes (FAQ) de uma escola, que responde com base em
representação **bag of words com transformação TF-IDF**, **similaridade de
cosseno** e **votação por maioria** entre as perguntas de referência mais
parecidas com a pergunta do usuário.

Este README cobre **apenas como instalar e rodar o projeto**. Para entender
os conceitos por trás do código (o que explicar para o professor), leia o
PDF `guia_de_estudo_apresentacao_pc8.pdf` que acompanha a entrega.

## 1. Pré-requisitos

- Python 3.10 ou superior instalado (`python --version`)
- Acesso à internet **na primeira vez** que o projeto for configurado (para
  instalar as bibliotecas e baixar um pequeno pacote de dados do NLTK)

## 2. Criar o ambiente virtual e instalar as dependências

Abra um terminal **dentro da pasta `pc8_chatbot_faq_escola`** e rode:

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_nltk.py
```

### Windows (cmd.exe)

```bat
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python setup_nltk.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup_nltk.py
```

`setup_nltk.py` baixa (uma única vez) o pacote `rslp` do NLTK, usado na
stemização das palavras em português. Depois desse passo, o projeto roda
**sem precisar de internet**.

> Se der erro de permissão ao ativar o `.venv` no PowerShell, rode antes:
> `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

## 3. Popular o banco de dados do FAQ

O projeto usa **SQLite** (arquivo local, sem precisar instalar um servidor de
banco de dados). O banco é criado e populado automaticamente na primeira
execução, mas também pode ser feito manualmente:

```bash
python seed_db.py
```

Para apagar os dados e recarregar do zero a partir de `data/faq_seed.json`:

```bash
python seed_db.py --force
```

O arquivo do banco fica em `data/faq.db`.

## 4. Rodar a aplicação web

```bash
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador. A interface permite digitar
perguntas no chat e, opcionalmente, clicar em "Mostrar detalhes técnicos"
para ver as perguntas de referência que mais pontuaram na votação por
maioria e a similaridade de cosseno de cada uma.

Para parar o servidor, use `Ctrl+C` no terminal.

## 5. Rodar os testes automáticos (smoke tests)

Valida o pré-processamento e a precisão do chatbot num conjunto de perguntas
de exemplo (usa um banco SQLite temporário, não mexe no `data/faq.db`):

```bash
python tests/test_chatbot.py
```

A saída mostra, pergunta por pergunta, qual intenção foi reconhecida, a
confiança (similaridade de cosseno do voto vencedor) e a acurácia final.

## 6. Estrutura do projeto

```
pc8_chatbot_faq_escola/
├── app.py                  # aplicação Flask (rotas web e API)
├── seed_db.py               # script para (re)popular o banco SQLite
├── setup_nltk.py             # baixa dados do NLTK (stemmer RSLP) uma vez
├── requirements.txt
├── chatbot/
│   ├── preprocessing.py     # pipeline de pré-processamento de texto
│   ├── engine.py             # TF-IDF + similaridade de cosseno + votação
│   └── database.py           # persistência (SQLite)
├── data/
│   ├── faq_seed.json         # categorias, perguntas e respostas do FAQ
│   └── faq.db                # criado automaticamente (não versionar)
├── templates/index.html      # interface web (página única)
├── static/{style.css,script.js}
└── tests/test_chatbot.py     # smoke tests do motor do chatbot
```

## 7. Adicionar ou editar perguntas do FAQ

Edite `data/faq_seed.json` (categorias, intenções/respostas e as frases de
treino de cada intenção) e rode `python seed_db.py --force` para recarregar
o banco com o conteúdo novo.

## 8. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `ModuleNotFoundError: No module named 'flask'` | ambiente virtual não ativado ou dependências não instaladas | repita o passo 2 |
| Chatbot sempre responde "não entendi" | banco não populado ou dados do NLTK não baixados | rode `python seed_db.py` e `python setup_nltk.py` |
| Porta 5000 já em uso | outro processo usando a porta | `python app.py` e depois edite a porta em `app.run(port=...)` em `app.py` |
