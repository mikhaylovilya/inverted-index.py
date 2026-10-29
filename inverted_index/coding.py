class BitReader:
    __slots__ = ("data", "position", "limit")

    def __init__(self, data):
        self.data = data
        self.position = 0
        self.limit = len(data) * 8

    def read_bit(self):
        if self.position >= self.limit:
            raise ValueError("Unexpected end of encoded postings")
        byte = self.data[self.position >> 3]
        bit = (byte >> (7 - (self.position & 7))) & 1
        self.position += 1
        return bit

    def read_gamma(self):
        zeros = 0
        while self.read_bit() == 0:
            zeros += 1
            if zeros > 63:
                raise ValueError("Invalid Elias gamma code")
        value = 1
        for _ in range(zeros):
            value = (value << 1) | self.read_bit()
        return value


def encode_gamma(value):
    if value < 1:
        raise ValueError("Elias gamma encoding requires positive integers")
    bits = bin(value)[2:]
    return "0" * (len(bits) - 1) + bits


def encode_postings(doc_ids):
    parts = []
    previous = 0
    count = 0
    for doc_id in doc_ids:
        gap = doc_id - previous
        if gap < 1:
            raise ValueError("Document ids must be positive, sorted and unique")
        parts.append(encode_gamma(gap))
        previous = doc_id
        count += 1
    bits = "".join(parts)
    if bits:
        bits += "0" * (-len(bits) % 8)
    data = bytes(int(bits[index : index + 8], 2) for index in range(0, len(bits), 8))
    return data, count


def decode_postings(data, count):
    if count < 0:
        raise ValueError("Posting count must be non-negative")
    reader = BitReader(data)
    doc_ids = []
    previous = 0
    for _ in range(count):
        previous += reader.read_gamma()
        doc_ids.append(previous)
    return doc_ids
