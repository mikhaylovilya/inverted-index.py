import re

TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def tokenize(text):
    if not text:
        return []
    return TOKEN_RE.findall(text.lower().replace("ё", "е"))
