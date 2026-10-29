from inverted_index.tokenizer import tokenize


def test_tokenize_lowercases_and_splits_punctuation():
    assert tokenize("Ректор СПбГУ/МГУ!") == ["ректор", "спбгу", "мгу"]


def test_tokenize_folds_yo():
    assert tokenize("Ещё Ёлка") == ["еще", "елка"]


def test_tokenize_keeps_digits_and_letters():
    assert tokenize("Python 3.15, СПбГУ-2026") == ["python", "3", "15", "спбгу", "2026"]


def test_tokenize_ignores_underscores():
    assert tokenize("hello_world test_case") == ["hello", "world", "test", "case"]


def test_tokenize_handles_empty_text():
    assert tokenize("") == []
    assert tokenize(None) == []
