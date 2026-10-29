import pytest

from inverted_index.coding import decode_postings, encode_gamma, encode_postings


def test_elias_gamma_code_examples():
    assert encode_gamma(1) == "1"
    assert encode_gamma(2) == "010"
    assert encode_gamma(3) == "011"
    assert encode_gamma(4) == "00100"
    assert encode_gamma(7) == "00111"
    assert encode_gamma(8) == "0001000"


def test_encode_postings_delta_and_gamma_bit_layout():
    data, count = encode_postings([1, 3, 6])
    assert data == b"\xa6"
    assert count == 3


def test_encode_postings_consecutive_ids():
    data, count = encode_postings([1, 2, 3, 4])
    assert data == b"\xf0"
    assert count == 4


def test_encode_postings_first_document_is_not_one():
    data, _ = encode_postings([3, 5])
    assert data == b"\x68"


def test_decode_postings_roundtrip():
    doc_ids = [1, 3, 6, 7, 20, 21, 1000]
    data, count = encode_postings(doc_ids)
    assert decode_postings(data, count) == doc_ids


def test_decode_postings_large_roundtrip():
    doc_ids = list(range(1, 5000, 7))
    data, count = encode_postings(doc_ids)
    assert decode_postings(data, count) == doc_ids


def test_empty_postings_roundtrip():
    data, count = encode_postings([])
    assert data == b""
    assert count == 0
    assert decode_postings(data, count) == []


def test_encode_rejects_invalid_ids():
    with pytest.raises(ValueError):
        encode_postings([0])
    with pytest.raises(ValueError):
        encode_postings([2, 1])
    with pytest.raises(ValueError):
        encode_postings([1, 1])
    with pytest.raises(ValueError):
        encode_gamma(0)


def test_decode_rejects_truncated_data():
    with pytest.raises(ValueError):
        decode_postings(b"", 1)
    with pytest.raises(ValueError):
        decode_postings(b"\x00\x00", 1)


def test_decode_rejects_negative_count():
    with pytest.raises(ValueError):
        decode_postings(b"", -1)
