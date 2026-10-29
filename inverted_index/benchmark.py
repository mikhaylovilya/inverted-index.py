import json
from pathlib import Path
from statistics import median
from time import perf_counter

from inverted_index.corpus import iter_documents
from inverted_index.index import InvertedIndex, collect_postings, search_lists
from inverted_index.tokenizer import tokenize


def count_documents(path):
    with open(path, encoding="utf-8") as file:
        return sum(1 for line in file if line.strip())


def scaled_documents(path, target):
    if target < 0:
        raise ValueError("Target document count must be non-negative")
    if target == 0:
        yield from iter_documents(path)
        return
    yielded = 0
    while yielded < target:
        produced = 0
        for document in iter_documents(path):
            produced += 1
            yield document
            yielded += 1
            if yielded >= target:
                break
        if produced == 0:
            raise ValueError("Input corpus is empty")


def search_classic(postings, query, match_all=False):
    terms = list(dict.fromkeys(tokenize(query)))
    return search_lists([postings.get(term, []) for term in terms], match_all)


def benchmark(path, query, target_docs=0, repeats=5):
    if repeats < 1:
        raise ValueError("Repeats must be at least 1")
    source_documents = count_documents(path)
    if source_documents == 0:
        raise ValueError("Input corpus is empty")
    documents = scaled_documents(path, target_docs)

    started = perf_counter()
    postings, document_count = collect_postings(documents)
    collect_seconds = perf_counter() - started

    started = perf_counter()
    index = InvertedIndex.from_postings(postings, document_count)
    compression_seconds = perf_counter() - started

    terms = tokenize(query)
    classic_results = search_classic(postings, query)
    compressed_results = index.search(query)
    for _ in range(max(1, repeats // 2)):
        search_classic(postings, query)
        index.search(query)

    classic_times = []
    compressed_times = []
    for _ in range(repeats):
        started = perf_counter()
        search_classic(postings, query)
        classic_times.append(perf_counter() - started)

        started = perf_counter()
        index.search(query)
        compressed_times.append(perf_counter() - started)

    total_index_seconds = collect_seconds + compression_seconds
    stats = index.stats()
    return {
        "source": str(path),
        "source_documents": source_documents,
        "indexed_documents": document_count,
        "synthetic_documents": max(0, document_count - source_documents),
        "query": query,
        "query_terms": terms,
        "result_documents": len(compressed_results),
        "results_match_classic": [
            doc_id for doc_id, _ in compressed_results
        ]
        == [doc_id for doc_id, _ in classic_results],
        "top_results": [
            {"document_id": doc_id, "score": score}
            for doc_id, score in compressed_results[:10]
        ],
        "timings": {
            "collect_postings_seconds": collect_seconds,
            "compression_seconds": compression_seconds,
            "total_index_seconds": total_index_seconds,
            "documents_per_second": (
                document_count / total_index_seconds if total_index_seconds else 0.0
            ),
            "classic_documents_per_second": (
                document_count / collect_seconds if collect_seconds else 0.0
            ),
            "compressed_search_seconds": median(compressed_times),
            "classic_search_seconds": median(classic_times),
            "search_repeats": repeats,
        },
        "index": stats,
    }


def save_report(report, path):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return target
