"""
Pipeline de pre-processamento de texto para o chatbot de FAQ escolar (PC.8).

Etapas aplicadas, na ordem, a toda frase (tanto nas perguntas de referencia
usadas para montar o corpus quanto na pergunta digitada pelo usuario):

    1. conversao para minusculas
    2. remocao de acentuacao/diacriticos (ex.: "horário" -> "horario")
    3. remocao de caracteres especiais / pontuacao
    4. tokenizacao
    5. remocao de stopwords (lista de stopwords do portugues, embutida no
       modulo para que o chatbot funcione mesmo sem conexao com a internet)
    6. stemizacao (RSLP Stemmer, via NLTK) com fallback silencioso caso o
       pacote de dados do NLTK nao esteja disponivel na maquina

O resultado dessa pipeline (lista de tokens normalizados) e o que alimenta o
TfidfVectorizer do scikit-learn em chatbot/engine.py.
"""

from __future__ import annotations

import re
import unicodedata

def strip_accents(text: str) -> str:
    """Remove acentuação/diacríticos (á->a, ç->c, ã->a, etc.).

    Importante: sem este passo, "horário" (como está cadastrado no FAQ) e
    "horario" (como um usuário frequentemente digita, sem acento) viram
    tokens DIFERENTES após a stemização, o vetor BOW/TF-IDF do usuário fica
    sem interseção nenhuma com o corpus de referência e a similaridade de
    cosseno dá 0 mesmo para perguntas claramente relacionadas.
    """
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


# ---------------------------------------------------------------------------
# 1) Lista de stopwords do portugues, embutida (nao depende de download).
#    Baseada na lista padrao do NLTK (corpus stopwords/portuguese), com
#    pequenos acrescimos de pronomes/conectivos comuns em perguntas de FAQ.
#    Mantida aqui COM acentos por legibilidade; é normalizada (accent-folded)
#    logo abaixo, na mesma passagem usada para o texto de entrada.
# ---------------------------------------------------------------------------
_STOPWORDS_PT_RAW = (
    """
    a ao aos aquela aquelas aquele aqueles aquilo as até com como da das de
    dela delas dele deles depois do dos e ela elas ele eles em entre era
    eram essa essas esse esses esta estas estava estavam este esteja
    estejam estejamos estes esteve estive estivemos estiver estivera
    estiveram estiverem estivermos estivesse estivessem estivéramos
    estivéssemos estou está estávamos estão eu foi fomos for fora foram
    forem formos fosse fossem fui fôramos fôssemos haja hajam hajamos havemos
    hei houve houvemos houver houvera houveram houverei houverem houveremos
    houveria houveriam houvermos houverá houverão houveríamos houvesse
    houvessem houvéramos houvéssemos há hão isso isto já lhe lhes mais mas
    me mesmo meu meus minha minhas muito na nas nem no nos nossa nossas
    nosso nossos num numa não nós o os ou para pela pelas pelo pelos por
    qual quando que quem se seja sejam sejamos sem serei seremos seria
    seriam será serão seríamos seu seus somos sou sua suas são só também
    te tem temos tenha tenham tenhamos tenho terei teremos teria teriam
    terá terão teríamos teu teus teve tinha tinham tive tivemos tiver
    tivera tiveram tiverem tivermos tivesse tivessem tivéramos tivéssemos
    tu tua tuas tém um uma você vocês vos à às éramos é
    qual quais onde aonde gostaria favor obrigado obrigada ola olá oi por
    favor quero queria quer queremos desejo desejaria necessito preciso
    gostaríamos""".split()
)

STOPWORDS_PT: frozenset[str] = frozenset(strip_accents(w) for w in _STOPWORDS_PT_RAW)

# Stemmer RSLP (via NLTK) é opcional: se não estiver disponível/baixado,
# o pipeline simplesmente não stemiza (ainda funciona, só fica um pouco
# menos agressivo na normalização). Isso evita que o chatbot quebre numa
# apresentação sem internet.
_STEMMER = None
_STEMMER_READY = False


def _get_stemmer():
    global _STEMMER, _STEMMER_READY
    if _STEMMER_READY:
        return _STEMMER
    _STEMMER_READY = True
    try:
        import nltk
        from nltk.stem import RSLPStemmer

        try:
            _STEMMER = RSLPStemmer()
            # força o uso para checar se os dados existem
            _STEMMER.stem("teste")
        except LookupError:
            try:
                nltk.download("rslp", quiet=True)
                _STEMMER = RSLPStemmer()
                _STEMMER.stem("teste")
            except Exception:
                _STEMMER = None
    except Exception:
        _STEMMER = None
    return _STEMMER


_SPECIAL_CHARS_RE = re.compile(r"[^a-z0-9\s]")
_MULTI_SPACE_RE = re.compile(r"\s+")


def to_lowercase(text: str) -> str:
    return text.lower()


def remove_special_characters(text: str) -> str:
    """Remove pontuação e símbolos, mantendo apenas letras, números e espaços."""
    text = _SPECIAL_CHARS_RE.sub(" ", text)
    return _MULTI_SPACE_RE.sub(" ", text).strip()


def tokenize(text: str) -> list[str]:
    return text.split() if text else []


def remove_stopwords(tokens: list[str]) -> list[str]:
    return [t for t in tokens if t not in STOPWORDS_PT and len(t) > 1]


def stem_tokens(tokens: list[str]) -> list[str]:
    stemmer = _get_stemmer()
    if stemmer is None:
        return tokens
    return [stemmer.stem(t) for t in tokens]


def preprocess(text: str) -> list[str]:
    """Aplica a pipeline completa de pre-processamento e devolve uma lista de tokens."""
    text = to_lowercase(text)
    text = strip_accents(text)
    text = remove_special_characters(text)
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = stem_tokens(tokens)
    return tokens


def preprocess_to_string(text: str) -> str:
    """Conveniência: pipeline completa devolvendo uma string (tokens separados por espaço)."""
    return " ".join(preprocess(text))
