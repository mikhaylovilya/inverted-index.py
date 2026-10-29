import pickle

import pytest

from inverted_index.index import (
    InvertedIndex,
    collect_postings,
    search_lists,
)


def test_collect_postings_uses_sorted_unique_document_ids():
    documents = [
        {"title": "Ректор", "text": "СПбГУ ректор"},
        {"title": "МГУ", "text": "ректор"},
        {"title": "", "text": ""},
    ]

    postings, count = collect_postings(documents)

    assert count == 3
    assert list(postings["ректор"]) == [1, 2]
    assert list(postings["спбгу"]) == [1]
    assert list(postings["мгу"]) == [2]
    assert set(postings) == {"ректор", "спбгу", "мгу"}


def test_collect_postings_ignores_empty_documents():
    postings, count = collect_postings([{"title": "", "text": ""}])
    assert count == 1
    assert postings == {}


def test_from_postings_compresses_and_reports_stats():
    index = InvertedIndex.from_postings(
        {"a": [1, 2, 3], "b": [2]}, document_count=3
    )

    assert index.document_count == 3
    assert index.total_postings == 4
    assert index.postings_for("a") == [1, 2, 3]
    assert index.postings_for("b") == [2]
    assert index.postings_for("missing") == []
    stats = index.stats()
    assert stats["terms"] == 2
    assert stats["postings"] == 4
    assert stats["compressed_bytes"] == 2
    assert stats["classic_bytes"] == 16
    assert stats["compression_ratio"] == 0.125
    assert stats["saved_percent"] == 87.5


def test_search_ranks_by_number_of_matched_terms():
    index = InvertedIndex.from_postings(
        {"a": [1, 2, 3], "b": [2], "c": [3]}, document_count=3
    )

    assert index.search("a") == [(1, 1), (2, 1), (3, 1)]
    assert index.search("a b") == [(2, 2), (1, 1), (3, 1)]
    assert index.search("b c") == [(2, 1), (3, 1)]


def test_search_supports_match_all():
    index = InvertedIndex.from_postings(
        {"a": [1, 2, 3], "b": [2, 3]}, document_count=3
    )

    assert index.search("a b", match_all=True) == [(2, 2), (3, 2)]
    assert index.search("a missing", match_all=True) == []


def test_search_handles_empty_and_duplicate_terms():
    index = InvertedIndex.from_postings({"a": [1, 2]}, document_count=2)

    assert index.search("") == []
    assert index.search("a a") == [(1, 1), (2, 1)]
    assert index.search("!!!") == []


def test_search_accepts_slash_separated_query():
    index = InvertedIndex.from_postings(
        {"ректор": [1], "спбгу": [1], "мгу": [2]}, document_count=2
    )

    assert index.search("Ректор СПбГУ/МГУ") == [(1, 2), (2, 1)]


def test_search_lists_empty_input():
    assert search_lists([]) == []
    assert search_lists([], match_all=True) == []


def test_index_save_and_load_roundtrip(tmp_path):
    index = InvertedIndex.from_postings(
        {"ректор": [1, 3], "спбгу": [1]}, document_count=3
    )
    path = tmp_path / "nested" / "index.pkl"

    index.save(path)
    loaded = InvertedIndex.load(path)

    assert loaded.document_count == 3
    assert loaded.total_postings == 3
    assert loaded.postings_for("ректор") == [1, 3]
    assert loaded.stats() == index.stats()


def test_load_rejects_unknown_format(tmp_path):
    path = tmp_path / "index.pkl"
    path.write_bytes(pickle.dumps({"version": 999}))

    with pytest.raises(ValueError):
        InvertedIndex.load(path)
