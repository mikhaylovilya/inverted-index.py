import json
from pathlib import Path


def convert_json_to_jsonl(source, target):
    with open(source, encoding="utf-8") as file:
        data = json.load(file)
    pages = data.get("pages") if isinstance(data, dict) else data
    if not isinstance(pages, list):
        raise ValueError("Input JSON must contain a pages list")
    path = Path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as file:
        for index, page in enumerate(pages, 1):
            if not isinstance(page, dict):
                raise ValueError(f"Page {index} is not an object")
            record = dict(page)
            record["id"] = index
            file.write(
                json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            count += 1
    return count


def iter_documents(path):
    with open(path, encoding="utf-8") as file:
        for line_number, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                document = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(document, dict):
                raise ValueError(f"Line {line_number} is not a JSON object")
            yield document


def load_documents(path):
    return list(iter_documents(path))


def document_text(document):
    title = str(document.get("title") or "")
    text = str(document.get("text") or "")
    return f"{title} {text}".strip()
