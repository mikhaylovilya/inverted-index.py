import pickle
from array import array
from collections import Counter
from pathlib import Path

from inverted_index.coding import decode_postings, encode_postings
from inverted_index.corpus import document_text
from inverted_index.tokenizer import tokenize

INDEX_VERSION = 1


def collect_postings(documents):
    postings = {}
    document_count = 0
    for document_count, document in enumerate(documents, 1):
        tokens = set(tokenize(document_text(document)))
        for token in tokens:
            postings.setdefault(token, array("I")).append(document_count)
    return postings, document_count


def search_lists(posting_lists, match_all=False):
    if not posting_lists:
        return []
    if match_all:
        matched = set(posting_lists[0])
        for doc_ids in posting_lists[1:]:
            matched.intersection_update(doc_ids)
            if not matched:
                return []
        return [(doc_id, len(posting_lists)) for doc_id in sorted(matched)]
    scores = Counter()
    for doc_ids in posting_lists:
        scores.update(doc_ids)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


class InvertedIndex:
    def __init__(self, postings, document_count, total_postings, coding="gamma"):
        self.postings = postings
        self.document_count = document_count
        self.total_postings = total_postings
        self.coding = coding

    @classmethod
    def from_postings(cls, postings, document_count, coding="gamma"):
        compressed = {}
        total_postings = 0
        for term, doc_ids in postings.items():
            data, count = encode_postings(doc_ids, coding)
            compressed[term] = (data, count)
            total_postings += count
        return cls(compressed, document_count, total_postings, coding)

    def postings_for(self, term):
        entry = self.postings.get(term)
        if entry is None:
            return []
        data, count = entry
        return decode_postings(data, count, self.coding)

    def search(self, query, match_all=False):
        return self.search_terms(tokenize(query), match_all)

    def search_terms(self, terms, match_all=False):
        unique_terms = list(dict.fromkeys(terms))
        if not unique_terms:
            return []
        posting_lists = [self.postings_for(term) for term in unique_terms]
        return search_lists(posting_lists, match_all)

    def stats(self):
        compressed_bytes = sum(len(data) for data, _ in self.postings.values())
        classic_bytes = self.total_postings * 4
        ratio = compressed_bytes / classic_bytes if classic_bytes else 0.0
        return {
            "documents": self.document_count,
            "terms": len(self.postings),
            "postings": self.total_postings,
            "compressed_bytes": compressed_bytes,
            "classic_bytes": classic_bytes,
            "compression_ratio": ratio,
            "saved_percent": (1.0 - ratio) * 100.0 if classic_bytes else 0.0,
            "coding": self.coding,
        }

    def save(self, path):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": INDEX_VERSION,
            "document_count": self.document_count,
            "total_postings": self.total_postings,
            "coding": self.coding,
            "postings": self.postings,
        }
        with target.open("wb") as file:
            pickle.dump(payload, file, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path):
        with open(path, "rb") as file:
            payload = pickle.load(file)
        if not isinstance(payload, dict) or payload.get("version") != INDEX_VERSION:
            raise ValueError("Unsupported index file format")
        return cls(
            payload["postings"],
            payload["document_count"],
            payload["total_postings"],
            payload.get("coding", "gamma"),
        )
