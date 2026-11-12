# PC.8 — Chatbot FAQ Escolar (Bag of Words + TF-IDF)

Chatbot de perguntas frequentes (FAQ) de uma escola, que responde com base em
representação **bag of words com transformação TF-IDF**, **similaridade de
cosseno** e **votação por maioria** entre as perguntas de referência mais
parecidas com a pergunta do usuário.

Este README cobre **apenas como instalar e rodar o projeto**. Para entender
os conceitos por trás do código (o que explicar para o professor), leia o
PDF `guia_pc8_de_cabeca.pdf` que acompanha a entrega.

## 1. Pré-requisitos

- **Python 3.10, 3.11, 3.12 ou 3.13** instalado. Confira com `python --version`.
  Python 3.14 ainda **não** funciona com as versões fixadas no
  `requirements.txt` (o `pip install` tenta compilar o scipy e falha).
  No Windows, ao instalar o Python, marque a opção **"Add python.exe to PATH"**.
- Acesso à internet **na primeira vez** que o projeto for configurado (para
  instalar as bibliotecas e baixar um pequeno pacote de dados do NLTK).

## 2. Instalação (só uma vez por computador)

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

## 3. Toda vez que abrir um terminal novo

A instalação é feita uma vez só, mas o ambiente virtual precisa ser
**ativado de novo em cada terminal novo**. Sem isso aparece
`ModuleNotFoundError`.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

(No cmd.exe: `.venv\Scripts\activate.bat`. No Linux/macOS:
`source .venv/bin/activate`.)

## 4. Rodar os testes automáticos

Valida o pré-processamento e a precisão do chatbot num conjunto de perguntas
de exemplo (usa um banco SQLite temporário, não mexe no `data/faq.db`):

```bash
python tests/test_chatbot.py
```

A saída mostra, pergunta por pergunta, qual intenção foi reconhecida e a
confiança (similaridade de cosseno do voto vencedor). No final deve aparecer
`Acurácia nos casos de teste: 100% (12/12)` e `Todos os smoke tests passaram.`

## 5. Rodar a aplicação web

```bash
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador. A interface permite digitar
perguntas no chat e, opcionalmente, clicar em "Mostrar detalhes técnicos"
para ver as perguntas de referência que mais pontuaram na votação por
maioria e a similaridade de cosseno de cada uma.

O histórico de conversas salvo no banco pode ser visto em
**http://127.0.0.1:5000/api/history**.

Para parar o servidor, use `Ctrl+C` no terminal.

## 6. Banco de dados (SQLite)

O projeto usa **SQLite**: o banco inteiro é um arquivo só, `data/faq.db`, e
não precisa instalar nenhum servidor. Para o uso normal **não é preciso fazer
nada**: o arquivo é criado e preenchido sozinho na primeira vez que o
`app.py` (ou os scripts abaixo) roda.

### Como os dados se dividem

| Onde | O que guarda | Quem edita |
|---|---|---|
| `data/faq_seed.json` | o conteúdo do FAQ: categorias, respostas e frases de treino | vocês, à mão |
| `data/faq.db` | uma cópia desse conteúdo **+ o histórico de todas as conversas** | o programa |

O JSON é a "fonte". O banco é o que o chatbot realmente usa. **Mudar o JSON
não muda o banco sozinho**: é preciso recarregar (seção 7).

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

## 7. Adicionar ou editar perguntas do FAQ

Sempre os mesmos 3 passos:

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

## 8. Estrutura do projeto

```
pasta do projeto/
├── app.py                  # aplicação Flask (rotas web e API)
├── seed_db.py              # script para (re)popular o banco SQLite
├── ver_banco.py            # mostra o conteúdo do banco e o histórico
├── setup_nltk.py           # baixa dados do NLTK (stemmer RSLP) uma vez
├── requirements.txt
├── chatbot/
│   ├── preprocessing.py    # pipeline de pré-processamento de texto
│   ├── engine.py           # TF-IDF + similaridade de cosseno + votação
│   └── database.py         # persistência (SQLite)
├── data/
│   ├── faq_seed.json       # categorias, perguntas e respostas do FAQ
│   └── faq.db              # criado automaticamente (não versionar)
├── templates/index.html    # interface web (página única)
├── static/{style.css,script.js}
├── tests/test_chatbot.py   # smoke tests do motor do chatbot
└── guia_pc8_de_cabeca.pdf  # guia de estudo para a apresentação
```

## 9. Problemas comuns

| Sintoma | Causa provável | Solução |
|---|---|---|
| `pip install` falha no **scipy** com `Unknown compiler(s): ['ifort'], ['gfortran']...` | versão do Python sem pacote pronto (ex.: Python 3.14) | instale o Python 3.13 (ou 3.10 a 3.12), apague a pasta `.venv` e refaça o passo 2 |
| `Activate.ps1 não pode ser carregado porque a execução de scripts foi desabilitada` | política de execução do PowerShell | rode `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo |
| `ModuleNotFoundError: No module named 'flask'` (ou `nltk`, `sklearn`) | `.venv` não ativado neste terminal, ou o `pip install` não terminou | ative o `.venv` (passo 3); se continuar, rode `pip install -r requirements.txt` de novo |
| Testes dão 83% em vez de 100% | dados do NLTK não baixados, stemização desligada | rode `python setup_nltk.py` (com internet) |
| `'python' não é reconhecido como um comando` | Python não está no PATH | reinstale o Python marcando "Add python.exe to PATH", ou use `py` no lugar de `python` |
| Porta 5000 já em uso | outro programa (ou outro `app.py`) usando a porta | feche o outro terminal que está rodando o `app.py`, ou troque a porta em `app.run(port=5000)` no final do `app.py` |
