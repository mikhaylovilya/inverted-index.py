import json

import pytest

from inverted_index.corpus import (
    convert_json_to_jsonl,
    document_text,
    iter_documents,
    load_documents,
)


def test_convert_json_to_jsonl(tmp_path):
    source = tmp_path / "pages.json"
    target = tmp_path / "nested" / "pages.jsonl"
    source.write_text(
        json.dumps(
            {
                "stats": {"total_pages": 2},
                "pages": [
                    {"url": "https://spbu.ru/", "title": "СПбГУ", "text": "Ректор"},
                    {"url": "https://spbu.ru/a", "title": "A", "text": "Текст"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    count = convert_json_to_jsonl(source, target)

    lines = target.read_text(encoding="utf-8").splitlines()
    assert count == 2
    assert len(lines) == 2
    assert json.loads(lines[0]) == {
        "url": "https://spbu.ru/",
        "title": "СПбГУ",
        "text": "Ректор",
        "id": 1,
    }
    assert json.loads(lines[1])["id"] == 2
    assert "СПбГУ" in lines[0]


def test_convert_accepts_top_level_list(tmp_path):
    source = tmp_path / "pages.json"
    target = tmp_path / "pages.jsonl"
    source.write_text('[{"text": "one"}]', encoding="utf-8")

    assert convert_json_to_jsonl(source, target) == 1


def test_convert_rejects_missing_pages(tmp_path):
    source = tmp_path / "pages.json"
    target = tmp_path / "pages.jsonl"
    source.write_text('{"stats": {}}', encoding="utf-8")

    with pytest.raises(ValueError):
        convert_json_to_jsonl(source, target)


def test_convert_rejects_non_object_page(tmp_path):
    source = tmp_path / "pages.json"
    target = tmp_path / "pages.jsonl"
    source.write_text('{"pages": ["bad"]}', encoding="utf-8")

    with pytest.raises(ValueError):
        convert_json_to_jsonl(source, target)


def test_iter_documents_skips_blank_lines(tmp_path):
    path = tmp_path / "pages.jsonl"
    path.write_text('{"text": "one"}\n\n{"text": "two"}\n', encoding="utf-8")

    assert load_documents(path) == [{"text": "one"}, {"text": "two"}]
    assert list(iter_documents(path)) == [{"text": "one"}, {"text": "two"}]


def test_iter_documents_reports_invalid_json(tmp_path):
    path = tmp_path / "pages.jsonl"
    path.write_text('{"text": "one"}\nnot json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="line 2"):
        list(iter_documents(path))


def test_iter_documents_rejects_non_object_line(tmp_path):
    path = tmp_path / "pages.jsonl"
    path.write_text('["not", "an", "object"]\n', encoding="utf-8")

    with pytest.raises(ValueError, match="not a JSON object"):
        list(iter_documents(path))


def test_document_text_combines_title_and_text():
    assert document_text({"title": "Заголовок", "text": "Текст"}) == "Заголовок Текст"
    assert document_text({"title": None, "text": "Текст"}) == "Текст"
    assert document_text({}) == ""
