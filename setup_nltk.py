"""Baixa, uma única vez, os dados do NLTK usados pela stemização (RSLP).

Rode isto ANTES da apresentação, com internet disponível. Os dados ficam
em cache local (pasta nltk_data do usuário) e depois disso o chatbot
funciona offline normalmente.

A lista de stopwords do português já vem embutida no código
(chatbot/preprocessing.py) e não depende deste download.
"""

import nltk

if __name__ == "__main__":
    nltk.download("rslp")
    print("Pronto: dados do stemmer RSLP baixados/cacheados com sucesso.")
