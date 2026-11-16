# PC.8 — Chatbot FAQ Escolar (Bag of Words + TF-IDF)

Chatbot de perguntas frequentes (FAQ) de uma escola. Ele responde com base em
representação **bag of words com transformação TF-IDF**, **similaridade de
cosseno** e **votação por maioria** entre as perguntas de referência mais
parecidas com a pergunta do usuário. As perguntas, respostas e o histórico de
conversas ficam num banco **SQLite**, e a interface é uma página web em
**Flask**.

- As seções 1 a 4 explicam **o que o projeto faz e como funciona**.
- As seções 5 a 12 explicam **como instalar, rodar e editar**.

## 1. Contexto do chatbot

O chatbot responde só sobre **5 assuntos** de uma escola. Cada assunto tem
3 intenções, e cada intenção tem uma resposta pronta e várias formas de fazer
a mesma pergunta, que são as frases de treino.

| Categoria | Intenções |
|---|---|
| Horários e Calendário Acadêmico | horário das aulas, horário das disciplinas, calendário acadêmico |
| Matrícula e Documentos | como se matricular, declaração de matrícula, trancamento |
| Biblioteca | horário da biblioteca, empréstimo de livro, renovação |
| Secretaria e Atendimento | horário de atendimento, contato, localização |
| Notas, Faltas e Avaliações | consultar notas, consultar faltas, recuperação |

No total são **5 categorias, 15 intenções e 77 frases de treino**. Depois da
limpeza do texto, essas frases formam um **vocabulário de 96 palavras**.

Quando a pergunta não tem relação com nenhum desses assuntos, o chatbot **não
inventa resposta**. Ele diz que não entendeu e mostra a lista de assuntos que
conhece.

## 2. Como funciona: 5 passos

```
pergunta → LIMPA → CONTA → COMPARA → VOTA → resposta
                                        ↘ (ou DESISTE, se nada for parecido)
```

### Passo 1 — Limpa (pré-processamento)

Para o computador, "Horário", "horário" e "horario" são palavras diferentes.
Por isso todo texto, tanto as frases de treino quanto a pergunta do usuário,
passa pelas mesmas 6 etapas:

1. minúsculas
2. remoção de acentos
3. remoção de pontuação e caracteres especiais
4. tokenização (separar em palavras)
5. remoção de stopwords (palavras que não indicam o assunto, como "qual", "o",
   "da" e também "quero", "preciso")
6. stemização com o stemmer **RSLP** do NLTK, próprio para português (corta o
   final das palavras para juntar a mesma família)

Exemplo: `"Qual é o Horário da Biblioteca?"` vira `['horari', 'bibliotec']`.

### Passo 2 — Conta (bag of words + TF-IDF)

As 77 frases de treino já limpas formam um **vocabulário de 96 palavras**.
Cada frase vira um **vetor de 96 números**, um para cada palavra do
vocabulário. Esse é o **bag of words**: ele registra quais palavras aparecem,
sem considerar a ordem.

Em cima disso aplicamos o **TF-IDF**:

- **TF** é quantas vezes a palavra aparece na frase.
- **IDF** diminui o peso das palavras que aparecem em muitas frases. Ou seja,
  **palavra rara vale mais**, porque é ela que diferencia um assunto do outro.

O scikit-learn usa a versão suavizada do IDF, com N = 77 frases e df = em
quantas frases a palavra aparece:

```
idf = ln( (1 + N) / (1 + df) ) + 1
```

| Palavra (radical) | Aparece em (df) | IDF |
|---|---|---|
| `secret` (secretaria) | 15 frases | 2,58 |
| `horari` (horário) | 9 frases | 3,05 |
| `bibliotec` (biblioteca) | 7 frases | 3,28 |
| `almoc` (almoço) | 1 frase | 4,66 |

Por fim, cada vetor é normalizado (norma L2) para ter tamanho 1.

**O vetor do usuário** é montado do mesmo jeito, com o **mesmo vocabulário**.
`"Qual o horário da biblioteca?"` vira um vetor de 96 posições em que só duas
não são zero: `{'bibliotec': 0.732, 'horari': 0.682}`. Uma palavra que não
existe no vocabulário é ignorada.

### Passo 3 — Compara (similaridade de cosseno)

O vetor da pergunta é comparado com os 77 vetores de treino pela
**similaridade de cosseno**:

```
cos(A, B) = (A · B) / (|A| × |B|)
```

O resultado vai de 0 (nenhuma palavra em comum) a 1 (mesmo conteúdo). O
cosseno olha a direção do vetor, e não o tamanho, então uma pergunta curta e
uma frase de treino longa sobre o mesmo assunto ainda ficam parecidas.

### Passo 4 — Vota (votação por maioria entre os top-K)

As **K = 5** frases de treino mais parecidas votam, cada uma na intenção a que
pertence, e ganha a intenção mais votada. É a mesma ideia do KNN (K vizinhos
mais próximos). Se houver empate, ganha a intenção com a maior soma de
cossenos, e depois a com o maior cosseno.

Exemplo real com `"Qual o horário da biblioteca?"`:

| # | Frase de treino | Vota em | Cosseno |
|---|---|---|---|
| 1 | Qual o horário de atendimento da biblioteca? | horario_biblioteca | 0,767 |
| 2 | Qual o horário de funcionamento da biblioteca? | horario_biblioteca | 0,693 |
| 3 | Qual o horário das aulas? | horario_aulas | 0,465 |
| 4 | Que horas a biblioteca abre? | horario_biblioteca | 0,397 |
| 5 | Qual o horário de atendimento da secretaria? | horario_atendimento_secretaria | 0,380 |

O placar fica 3 × 1 × 1, então ganha **horario_biblioteca**. A confiança
mostrada (0,767) é o maior cosseno entre as frases que votaram na vencedora.

A votação existe para que uma única frase de treino parecida por acaso não
decida a resposta sozinha.

### Passo 5 — Desiste (fallback)

Se a frase mais parecida tiver cosseno **menor que 0,15**, ou se nenhuma
palavra da pergunta existir no vocabulário, o chatbot responde que não
entendeu e lista os assuntos que conhece. Exemplo: `"Qual a previsão do
tempo?"` dá cosseno 0, porque "previsão" e "tempo" não aparecem em nenhuma
frase de treino.

## 3. Onde fica cada coisa no código

| O quê | Arquivo | Linha | Começa com |
|---|---|---|---|
| Pré-processamento (6 etapas) | [`chatbot/preprocessing.py`](chatbot/preprocessing.py#L134) | 134 | `def preprocess(text` |
| Lista de stopwords | [`chatbot/preprocessing.py`](chatbot/preprocessing.py#L70) | 70 | `STOPWORDS_PT` |
| Stemmer RSLP | [`chatbot/preprocessing.py`](chatbot/preprocessing.py#L80) | 80 | `def _get_stemmer():` |
| K = 5 e limiar 0,15 | [`chatbot/engine.py`](chatbot/engine.py#L37) | 37 | `DEFAULT_TOP_K = 5` |
| **Bag of words + TF-IDF** | [`chatbot/engine.py`](chatbot/engine.py#L94) | 94 | `self.vectorizer = TfidfVectorizer(` |
| Treino (monta o vocabulário e os vetores) | [`chatbot/engine.py`](chatbot/engine.py#L103) | 103 | `self.matrix = self.vectorizer.fit_transform(` |
| **Vetor do usuário** | [`chatbot/engine.py`](chatbot/engine.py#L121) | 121 | `user_vec = self.vectorizer.transform(` |
| Similaridade de cosseno | [`chatbot/engine.py`](chatbot/engine.py#L129) | 129 | `sims = cosine_similarity(` |
| Fallback | [`chatbot/engine.py`](chatbot/engine.py#L134) | 134 | `if not top_candidates or` |
| Votação por maioria | [`chatbot/engine.py`](chatbot/engine.py#L146) | 146 | `votes: Counter[str] = Counter()` |
| Tabelas do banco | [`chatbot/database.py`](chatbot/database.py#L31) | 31 | `CREATE TABLE IF NOT EXISTS categories` |
| Rotas web e API | [`app.py`](app.py) | — | `def api_chat():`, `def api_history():` |
| Conteúdo do FAQ | [`data/faq_seed.json`](data/faq_seed.json) | — | categorias, respostas e frases de treino |

O `TfidfVectorizer` do scikit-learn equivale a um `CountVectorizer` (o bag of
words) seguido de um `TfidfTransformer` (os pesos TF-IDF). Ele recebe a nossa
função `preprocess` como tokenizador, então o vocabulário é formado pelas
palavras já limpas.

O vocabulário e os vetores de treino são calculados **uma vez, quando o app
liga** (`fit_transform`). Cada pergunta do usuário só é transformada com esse
vocabulário (`transform`).

## 4. Decisões, testes e limitações

**Por que stemização e não lematização?** Lematização precisa de um modelo de
linguagem pesado (como o spaCy). Para juntar palavras da mesma família, como
"matrícula" e "matricular", cortar o final por regra já basta.

**Por que K = 5 e limiar 0,15?** São valores escolhidos testando. Com eles, os
testes automáticos acertam 100%. Os dois são configuráveis no construtor de
`ChatbotEngine`.

**Um problema encontrado nos testes:** a frase "Quero pedir uma pizza" era
respondida como *trancamento de curso*, com confiança 0,48. O motivo era que
"quero" aparecia em uma única frase de treino ("Quero trancar o curso"), e
como palavra rara ganha peso alto no TF-IDF, "quero" pesava muito sem ter
relação com o assunto. A correção foi incluir "quero", "queria", "preciso" e
"desejo" nas stopwords. Hoje essa frase cai no fallback.

**Testes:** `tests/test_chatbot.py` roda 12 perguntas escritas de forma
diferente das frases de treino e 2 perguntas fora do escopo. Resultado:
**12/12 (100%)** e as 2 fora do escopo caem no fallback.

**Limitações:**

- O bag of words ignora a ordem das palavras.
- O chatbot não entende sinônimos que não estão nas frases de treino.
- Erros de digitação viram outro radical, que não existe no vocabulário. Por
  exemplo, "recupreação" não é reconhecida.
- Palavras raras podem pesar demais, como no caso da pizza.
- Ele não lembra da pergunta anterior; cada pergunta é tratada sozinha.

Uma melhoria seria trocar o TF-IDF por **embeddings** (como Word2Vec ou
modelos de sentenças), em que palavras de significado parecido ficam próximas
mesmo sem nunca aparecerem juntas no treino.

---

## 5. Pré-requisitos

- **Python 3.10, 3.11, 3.12 ou 3.13** instalado. Confira com `python --version`.
  Python 3.14 ainda **não** funciona com as versões fixadas no
  `requirements.txt` (o `pip install` tenta compilar o scipy e falha).
  No Windows, ao instalar o Python, marque a opção **"Add python.exe to PATH"**.
- Acesso à internet **na primeira vez** que o projeto for configurado (para
  instalar as bibliotecas e baixar um pequeno pacote de dados do NLTK).

## 6. Instalação (só uma vez por computador)

Abra um terminal **dentro da pasta do projeto** (a pasta onde está este
README) e rode os comandos abaixo, um por vez.

### Windows (PowerShell)

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_nltk.py
```

A linha `Set-ExecutionPolicy` libera a ativação do `.venv` só nesse terminal
(sem ela, o PowerShell costuma bloquear o `Activate.ps1`). Depois de ativar,
o começo da linha do terminal passa a mostrar `(.venv)`.

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

**Não pule o `python setup_nltk.py`.** Ele baixa (uma única vez) o pacote
`rslp` do NLTK, usado na stemização das palavras em português. Sem ele o
chatbot ainda abre, mas a stemização fica desligada sem aviso e ele erra mais
(os testes caem de 100% para 83%). Depois desse passo, o projeto roda **sem
precisar de internet**.

## 7. Toda vez que abrir um terminal novo

A instalação é feita uma vez só, mas o ambiente virtual precisa ser
**ativado de novo em cada terminal novo**. Sem isso aparece
`ModuleNotFoundError`.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

(No cmd.exe: `.venv\Scripts\activate.bat`. No Linux/macOS:
`source .venv/bin/activate`.)

## 8. Rodar os testes automáticos

Valida o pré-processamento e a precisão do chatbot num conjunto de perguntas
de exemplo (usa um banco SQLite temporário, não mexe no `data/faq.db`):

```bash
python tests/test_chatbot.py
```

A saída mostra, pergunta por pergunta, qual intenção foi reconhecida e a
confiança (similaridade de cosseno do voto vencedor). No final deve aparecer
`Acurácia nos casos de teste: 100% (12/12)` e `Todos os smoke tests passaram.`

## 9. Rodar a aplicação web

```bash
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador e digite perguntas no chat.

Para ver como a resposta foi escolhida, clique em **"Mostrar detalhes
técnicos"** na barra lateral **antes** de perguntar. Embaixo de cada resposta
aparecem as 5 frases de treino que votaram e o cosseno de cada uma.

O histórico de conversas salvo no banco pode ser visto em
**http://127.0.0.1:5000/api/history**.

Para parar o servidor, use `Ctrl+C` no terminal.

## 10. Banco de dados (SQLite)

O projeto usa **SQLite**: o banco inteiro é um arquivo só, `data/faq.db`, e
não precisa instalar nenhum servidor. Para o uso normal **não é preciso fazer
nada**: o arquivo é criado e preenchido sozinho na primeira vez que o
`app.py` (ou os scripts abaixo) roda.

### Como os dados se dividem

| Onde | O que guarda | Quem edita |
|---|---|---|
| `data/faq_seed.json` | o conteúdo do FAQ: categorias, respostas e frases de treino | à mão |
| `data/faq.db` | uma cópia desse conteúdo **+ o histórico de todas as conversas** | o programa |

O JSON é a "fonte". O banco é o que o chatbot realmente usa. **Mudar o JSON
não muda o banco sozinho**: é preciso recarregar (seção 11).

O banco tem 4 tabelas:

- `categories`: as categorias (ex.: Biblioteca)
- `intents`: as intenções, cada uma com sua resposta pronta
- `reference_questions`: as frases de treino de cada intenção (é o corpus do TF-IDF)
- `conversation_log`: o histórico (pergunta, resposta, categoria, confiança, data)

### Ver o que tem dentro do banco

```bash
python ver_banco.py
```

Mostra quantas categorias, intenções, frases e conversas existem, e lista
todas as categorias, intenções e frases de treino.

```bash
python ver_banco.py historico
```

Mostra as últimas 20 conversas salvas. O mesmo histórico também aparece no
navegador em http://127.0.0.1:5000/api/history (com o `app.py` rodando).

### Criar o banco do zero

```bash
python seed_db.py
```

Se o arquivo `data/faq.db` não existir, ele é criado e preenchido com o
conteúdo do JSON. Se já existir, nada muda. Para começar realmente do zero,
**incluindo apagar o histórico**, apague o arquivo `data/faq.db` e rode o
comando acima.

### Recarregar o conteúdo do FAQ

```bash
python seed_db.py --force
```

Apaga as categorias, intenções e frases do banco e carrega de novo a partir
do `data/faq_seed.json`. **O histórico de conversas é mantido.** No final ele
mostra quantas frases de treino carregou (`Perguntas de referência
carregadas: 77`). Se você adicionou frases, esse número tem que ter subido.

## 11. Adicionar ou editar perguntas do FAQ

Sempre os mesmos 3 passos, sem mexer no código:

1. **Editar** o `data/faq_seed.json` (de preferência no VS Code, que avisa se
   o JSON ficar com erro).
2. **Recarregar o banco:** `python seed_db.py --force`
3. **Reiniciar o app:** se o `app.py` estiver rodando, pare com `Ctrl+C` e
   rode `python app.py` de novo. O TF-IDF é treinado só quando o app liga.

> Se pular o passo 2 ou o 3, o chatbot continua usando as perguntas antigas.
> Testamos: com a categoria "Cantina" já no JSON mas sem o `--force`, a
> pergunta "Que horas abre a cantina?" foi respondida como horário da
> **biblioteca**. Depois do `--force` e de reiniciar, acertou com
> confiança 1,0.

### Como o JSON está organizado

O arquivo tem duas listas: `categories` (no começo) e `intents` (embaixo).
Cada intenção aponta para a sua categoria pelo campo `category`:

```json
{
  "categories": [
    { "slug": "biblioteca", "name": "Biblioteca", "description": "..." }
  ],
  "intents": [
    {
      "slug": "horario_biblioteca",
      "category": "biblioteca",
      "answer": "A biblioteca funciona de segunda a sexta-feira, das 08h00 às 21h00...",
      "questions": [
        "Qual o horário de funcionamento da biblioteca?",
        "Que horas a biblioteca abre?"
      ]
    }
  ]
}
```

- `slug`: um nome interno, sem espaço e sem acento (ex.: `horario_cantina`).
- `name` / `description`: o que aparece na barra lateral do site.
- `answer`: a resposta que o chatbot dá.
- `questions`: as frases de treino, ou seja, jeitos diferentes de fazer a
  mesma pergunta. Quanto mais variadas, melhor ele acerta.

### Exemplo A: ensinar uma nova forma de perguntar

Ache a intenção no JSON (ex.: `"slug": "horario_biblioteca"`) e acrescente uma
frase na lista `questions`. Coloque uma vírgula no fim da frase anterior:

```json
      "questions": [
        "Qual o horário de funcionamento da biblioteca?",
        "Que horas a biblioteca abre?",
        "A biblioteca fecha que horas?"
      ]
```

Depois: `python seed_db.py --force` e reinicie o `app.py`.

### Exemplo B: criar uma categoria nova (ex.: Cantina)

**1)** Na lista `categories`, depois da última categoria (`"slug": "notas"`),
coloque uma vírgula depois do `}` dela e cole:

```json
    {
      "slug": "cantina",
      "name": "Cantina",
      "description": "Horário e funcionamento da cantina."
    }
```

**2)** Na lista `intents`, depois da última intenção (`"slug": "recuperacao"`),
coloque uma vírgula depois do `}` dela e cole:

```json
    {
      "slug": "horario_cantina",
      "category": "cantina",
      "answer": "A cantina funciona de segunda a sexta, das 07h00 às 21h30.",
      "questions": [
        "Qual o horário da cantina?",
        "Que horas a cantina abre?",
        "Até que horas a cantina fica aberta?",
        "A cantina abre no sábado?"
      ]
    }
```

**3)** Recarregue, confira e reinicie:

```bash
python seed_db.py --force
python ver_banco.py
python app.py
```

O `seed_db.py` deve mostrar `81` frases (eram 77), o `ver_banco.py` deve
mostrar `6 categorias | 16 intenções`, e "Cantina" aparece na barra lateral
do site. Pergunte "Que horas abre a cantina?" para testar.

### Regras que não podem ser quebradas

- O `category` de uma intenção tem que ser **exatamente** o `slug` de uma
  categoria que existe. Se não for, o `seed_db.py` para com `KeyError:` e o
  nome que está errado.
- Cada intenção precisa de um `slug` **diferente** de todas as outras. Se
  repetir, o banco junta as duas numa só e usa a resposta da primeira, sem
  avisar.
- Entre um item e outro de uma lista vai **vírgula**; depois do último item
  **não** vai vírgula. Texto sempre entre aspas duplas `"..."`.

### Se der erro no JSON

Se aparecer algo como:

```
json.decoder.JSONDecodeError: Expecting ',' delimiter: line 223 column 9
```

é erro de digitação no JSON. O número da `line` diz a linha (no VS Code,
`Ctrl+G` e digite o número). Quase sempre é uma vírgula faltando no fim da
linha **anterior**, ou sobrando depois do último item. O banco não é alterado
quando isso acontece; é só corrigir e rodar `python seed_db.py --force` de
novo.

## 12. Estrutura do projeto

```
pasta do projeto/
├── app.py                  # aplicação Flask (rotas web e API)
├── seed_db.py              # script para (re)popular o banco SQLite
├── ver_banco.py            # mostra o conteúdo do banco e o histórico
├── setup_nltk.py           # baixa dados do NLTK (stemmer RSLP) uma vez
├── requirements.txt
├── chatbot/
│   ├── preprocessing.py    # pipeline de pré-processamento de texto
│   ├── engine.py           # bag of words + TF-IDF, cosseno, votação e fallback
│   └── database.py         # persistência (SQLite)
├── data/
│   ├── faq_seed.json       # categorias, perguntas e respostas do FAQ
│   └── faq.db              # criado automaticamente (não versionar)
├── templates/index.html    # interface web (página única)
├── static/{style.css,script.js}
└── tests/test_chatbot.py   # smoke tests do motor do chatbot
```

## 13. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `pip install` falha no **scipy** com `Unknown compiler(s): ['ifort'], ['gfortran']...` | versão do Python sem pacote pronto (ex.: Python 3.14) | instale o Python 3.13 (ou 3.10 a 3.12), apague a pasta `.venv` e refaça a seção 6 |
| `Activate.ps1 não pode ser carregado porque a execução de scripts foi desabilitada` | política de execução do PowerShell | rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo |
| `ModuleNotFoundError: No module named 'flask'` (ou `nltk`, `sklearn`) | `.venv` não ativado neste terminal, ou o `pip install` não terminou | ative o `.venv` (seção 7); se continuar, rode `pip install -r requirements.txt` de novo |
| Testes dão 83% em vez de 100% | dados do NLTK não baixados, stemização desligada | rode `python setup_nltk.py` (com internet) |
| `'python' não é reconhecido como um comando` | Python não está no PATH | reinstale o Python marcando "Add python.exe to PATH", ou use `py` no lugar de `python` |
| Porta 5000 já em uso | outro programa (ou outro `app.py`) usando a porta | feche o outro terminal que está rodando o `app.py`, ou troque a porta em `app.run(port=5000)` no final do `app.py` |
