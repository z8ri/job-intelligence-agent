import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import word_tokenize

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

_stemmer = PorterStemmer()
_stop_words = set(stopwords.words("english"))


def preprocess(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", "", (text or "").lower())
    tokens = word_tokenize(text)
    return [
        _stemmer.stem(w)
        for w in tokens
        if w not in _stop_words and len(w) > 2
    ]
