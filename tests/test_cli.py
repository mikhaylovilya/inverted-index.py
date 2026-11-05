import json

import pytest

from inverted_index.cli import (
    documents_for_ids,
    main,
    parse_args,
    run_build,
)


@pytest.fixture
def crawl_json(tmp_path):
    path = tmp_path / "pages.json"
    path.write_text(
        json.dumps(
            {
                "stats": {"total_pages": 3},
                "pages": [
                    {
                        "url": "https://spbu.ru/",
                        "title": "Ректор СПбГУ",
                        "text": "Ректор университета",
                    },
                    {
                        "url": "https://spbu.ru/news",
                        "title": "Новости",
                        "text": "МГУ и СПбГУ",
                    },
                    {
                        "url": "https://spbu.ru/sport",
                        "title": "Спорт",
                        "text": "Футбол",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_parse_defaults():
    args = parse_args(["benchmark", "pages.jsonl"])
    assert args.command == "benchmark"
    assert args.query == "Ректор СПбГУ/МГУ"
    assert args.target_docs == 40000
    assert args.repeats == 5
    assert args.coding == "gamma"

    delta = parse_args(["build", "pages.jsonl", "index.pkl", "--coding", "delta"])
    assert delta.coding == "delta"

    search = parse_args(["search", "query", "--index", "index.pkl"])
    assert search.limit == 10
    assert search.all is False
    assert search.json is False


def test_convert_build_and_search(crawl_json, tmp_path, capsys):
    jsonl = tmp_path / "pages.jsonl"
    index_path = tmp_path / "index.pkl"

    assert main(["convert", str(crawl_json), str(jsonl)]) == 0
    converted = json.loads(capsys.readouterr().out)
    assert converted["documents"] == 3

    assert main(["build", str(jsonl), str(index_path)]) == 0
    built = json.loads(capsys.readouterr().out)
    assert built["documents"] == 3
    assert built["compressed_bytes"] < built["classic_bytes"]

    assert (
        main(
            [
                "search",
                "Ректор СПбГУ/МГУ",
                "--index",
                str(index_path),
                "--documents",
                str(jsonl),
                "--json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["total_results"] == 2
    assert result["elapsed_seconds"] >= 0
    assert result["results"][0]["title"] == "Ректор СПбГУ"
    assert result["results"][0]["url"] == "https://spbu.ru/"


def test_search_all_and_human_output(crawl_json, tmp_path, capsys):
    jsonl = tmp_path / "pages.jsonl"
    index_path = tmp_path / "index.pkl"
    main(["convert", str(crawl_json), str(jsonl)])
    main(["build", str(jsonl), str(index_path)])
    capsys.readouterr()

    main(
        [
            "search",
            "СПбГУ/МГУ",
            "--index",
            str(index_path),
            "--documents",
            str(jsonl),
            "--all",
        ]
    )

    output = capsys.readouterr().out
    assert "Found 1 documents" in output
    assert "Новости" in output
    assert "https://spbu.ru/news" in output


def test_search_without_documents(crawl_json, tmp_path, capsys):
    jsonl = tmp_path / "pages.jsonl"
    index_path = tmp_path / "index.pkl"
    main(["convert", str(crawl_json), str(jsonl)])
    main(["build", str(jsonl), str(index_path)])
    capsys.readouterr()

    main(["search", "футбол", "--index", str(index_path), "--json"])

    result = json.loads(capsys.readouterr().out)
    assert result["results"][0]["title"] is None
    assert result["results"][0]["url"] is None


def test_documents_for_ids_reads_only_needed_prefix(tmp_path):
    path = tmp_path / "pages.jsonl"
    path.write_text(
        '{"id": 1, "title": "one"}\n{"id": 2, "title": "two"}\n',
        encoding="utf-8",
    )

    assert documents_for_ids(path, [2])[2]["title"] == "two"
    assert documents_for_ids(path, []) == {}


def test_run_benchmark_command(tmp_path, capsys, crawl_json):
    jsonl = tmp_path / "pages.jsonl"
    main(["convert", str(crawl_json), str(jsonl)])
    capsys.readouterr()
    report_path = tmp_path / "benchmark.json"

    assert (
        main(
            [
                "benchmark",
                str(jsonl),
                "--target-docs",
                "5",
                "--repeats",
                "1",
                "--output",
                str(report_path),
            ]
        )
        == 0
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["indexed_documents"] == 5
    assert report["synthetic_documents"] == 2
    assert "Saved benchmark report" in capsys.readouterr().out


def test_run_build_rejects_missing_file(tmp_path):
    args = parse_args(
        ["build", str(tmp_path / "missing.jsonl"), str(tmp_path / "index.pkl")]
    )
    with pytest.raises(FileNotFoundError):
        run_build(args)
