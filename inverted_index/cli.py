import argparse
import json
from pathlib import Path
from time import perf_counter

from inverted_index import __version__
from inverted_index.benchmark import benchmark, save_report
from inverted_index.coding import SUPPORTED_CODINGS
from inverted_index.corpus import convert_json_to_jsonl, iter_documents
from inverted_index.index import InvertedIndex, collect_postings


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="inverted-index",
        description="Compressed inverted index for crawled web pages.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    convert = commands.add_parser("convert", help="Convert crawl JSON to JSONL")
    convert.add_argument("input")
    convert.add_argument("output")
    convert.set_defaults(handler=run_convert)

    build = commands.add_parser("build", help="Build a compressed index")
    build.add_argument("input")
    build.add_argument("index")
    build.add_argument("--coding", choices=SUPPORTED_CODINGS, default="gamma")
    build.set_defaults(handler=run_build)

    search = commands.add_parser("search", help="Search a saved index")
    search.add_argument("query")
    search.add_argument("--index", required=True)
    search.add_argument("--documents")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--all", action="store_true")
    search.add_argument("--json", action="store_true")
    search.set_defaults(handler=run_search)

    bench = commands.add_parser("benchmark", help="Measure indexing and search")
    bench.add_argument("input")
    bench.add_argument("--query", default="Ректор СПбГУ/МГУ")
    bench.add_argument("--target-docs", type=int, default=40000)
    bench.add_argument("--repeats", type=int, default=5)
    bench.add_argument("--coding", choices=SUPPORTED_CODINGS, default="gamma")
    bench.add_argument("--output", default="benchmark.json")
    bench.set_defaults(handler=run_benchmark)
    return parser.parse_args(argv)


def run_convert(args):
    count = convert_json_to_jsonl(args.input, args.output)
    print(json.dumps({"documents": count, "output": args.output}, ensure_ascii=False))
    return 0


def run_build(args):
    started = perf_counter()
    postings, document_count = collect_postings(iter_documents(args.input))
    index = InvertedIndex.from_postings(postings, document_count, args.coding)
    elapsed = perf_counter() - started
    index.save(args.index)
    report = index.stats()
    report["seconds"] = elapsed
    report["output"] = str(args.index)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def documents_for_ids(path, doc_ids):
    wanted = set(doc_ids)
    if not wanted:
        return {}
    limit = max(wanted)
    found = {}
    for index, document in enumerate(iter_documents(path), 1):
        if index in wanted:
            found[index] = document
        if index >= limit:
            break
    return found


def run_search(args):
    index = InvertedIndex.load(args.index)
    started = perf_counter()
    results = index.search(args.query, match_all=args.all)
    elapsed = perf_counter() - started
    top = results[: args.limit]
    documents = (
        documents_for_ids(args.documents, [doc_id for doc_id, _ in top])
        if args.documents
        else {}
    )
    rows = []
    for doc_id, score in top:
        document = documents.get(doc_id, {})
        rows.append(
            {
                "document_id": doc_id,
                "score": score,
                "title": document.get("title"),
                "url": document.get("url"),
            }
        )
    if args.json:
        print(
            json.dumps(
                {
                    "query": args.query,
                    "elapsed_seconds": elapsed,
                    "total_results": len(results),
                    "results": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print(f"Found {len(results)} documents in {elapsed:.6f}s")
    for position, row in enumerate(rows, 1):
        title = row["title"] or row["url"] or "without title"
        print(f"{position}. score={row['score']} [{row['document_id']}] {title}")
        if row["url"]:
            print(f"   {row['url']}")
    return 0


def run_benchmark(args):
    report = benchmark(
        args.input,
        args.query,
        target_docs=args.target_docs,
        repeats=args.repeats,
        coding=args.coding,
    )
    path = save_report(report, args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Saved benchmark report to {path}")
    return 0


def main(argv=None):
    args = parse_args(argv)
    return args.handler(args)
