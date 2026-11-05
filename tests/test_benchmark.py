import json

import pytest

from inverted_index.benchmark import (
    benchmark,
    count_documents,
    save_report,
    scaled_documents,
    search_classic,
)


@pytest.fixture
def corpus(tmp_path):
    path = tmp_path / "pages.jsonl"
    documents = [
        {"id": 1, "title": "Ректор СПбГУ", "text": "ректор университет"},
        {"id": 2, "title": "МГУ", "text": "ректор москва"},
        {"id": 3, "title": "Новости", "text": "спорт"},
    ]
    path.write_text(
        "".join(
            json.dumps(document, ensure_ascii=False) + "\n" for document in documents
        ),
        encoding="utf-8",
    )
    return path


def test_count_documents(corpus):
    assert count_documents(corpus) == 3


def test_scaled_documents_cycles_corpus(corpus):
    documents = list(scaled_documents(corpus, 5))
    assert [document["id"] for document in documents] == [1, 2, 3, 1, 2]


def test_scaled_documents_uses_all_documents(corpus):
    documents = list(scaled_documents(corpus, 0))
    assert [document["id"] for document in documents] == [1, 2, 3]


def test_scaled_documents_limits_corpus(corpus):
    documents = list(scaled_documents(corpus, 2))
    assert [document["id"] for document in documents] == [1, 2]


def test_scaled_documents_rejects_negative_target(corpus):
    with pytest.raises(ValueError):
        list(scaled_documents(corpus, -1))


def test_scaled_documents_rejects_empty_corpus(tmp_path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        list(scaled_documents(path, 3))


def test_search_classic(corpus):
    from inverted_index.index import collect_postings

    postings, _ = collect_postings(scaled_documents(corpus, 0))
    assert search_classic(postings, "Ректор СПбГУ/МГУ") == [(1, 2), (2, 2)]


def test_benchmark_report(corpus):
    report = benchmark(corpus, "Ректор СПбГУ/МГУ", repeats=2)

    assert report["source_documents"] == 3
    assert report["indexed_documents"] == 3
    assert report["synthetic_documents"] == 0
    assert report["query_terms"] == ["ректор", "спбгу", "мгу"]
    assert report["results_match_classic"] is True
    assert report["result_documents"] >= 1
    assert report["index"]["postings"] > 0
    assert report["index"]["compressed_bytes"] < report["index"]["classic_bytes"]
    assert report["coding"] == "gamma"
    assert report["index"]["coding"] == "gamma"
    assert report["timings"]["search_repeats"] == 2
    assert report["timings"]["total_index_seconds"] >= 0
    assert report["timings"]["compressed_search_seconds"] >= 0


def test_benchmark_delta_coding(corpus):
    report = benchmark(corpus, "ректор", coding="delta", repeats=1)

    assert report["coding"] == "delta"
    assert report["index"]["coding"] == "delta"
    assert report["results_match_classic"] is True


def test_benchmark_scales_documents(corpus):
    report = benchmark(corpus, "ректор", target_docs=7, repeats=1)

    assert report["indexed_documents"] == 7
    assert report["synthetic_documents"] == 4


def test_benchmark_rejects_invalid_inputs(corpus, tmp_path):
    with pytest.raises(ValueError):
        benchmark(corpus, "query", repeats=0)
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        benchmark(empty, "query")


def test_save_report(corpus, tmp_path):
    report = benchmark(corpus, "ректор", repeats=1)
    path = save_report(report, tmp_path / "nested" / "benchmark.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["query"] == "ректор"
