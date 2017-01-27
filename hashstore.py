from binascii import unhexlify
from utils import pmts, rfs
from binascii import hexlify
from hashlib import sha256

bytes_iterator = type(iter(bytes()))


class Hash(object):
    def __init__(self, hash_bytes):
        pmts(hash_bytes, bytes)

        # i.e. if you want to construct a hash _for_ a bunch of bytes, use 'for_bytes'
        assert len(hash_bytes) == 32, "Direct construction of Hash objects takes a 32-byte hash"

        self.hash_bytes = hash_bytes

    def __repr__(self):
        return str(hexlify(self.hash_bytes)[:12], 'utf-8')

    def as_bytes(self):
        return self.hash_bytes

    @staticmethod
    def for_bytes(bytes_):
        pmts(bytes_, bytes)
        hash_ = sha256(bytes_).digest()
        return Hash(hash_)

    @staticmethod
    def from_stream(byte_stream):
        """_reads_ (i.e. picks exactly 32 chars) from the stream"""
        pmts(byte_stream, bytes_iterator)
        return Hash(rfs(byte_stream, 32))

    def __hash__(self):
        # Based on the following understanding:
        # * AFAIK, Python's hash function works w/ 64-bit ints; hence I take 8 bytes
        # * byteorder was picked arbitrarily
        return int.from_bytes(self.hash_bytes[:8], byteorder='big')

    def __eq__(self, other):
        if not isinstance(other, Hash):
            return False
        return self.hash_bytes == other.hash_bytes


class HashStore(object):

    def __init__(self, type_, parser):
        self.d = {}
        self.type_ = type_
        self.parser = parser

    def __repr__(self):
        return '\n'.join(
            repr(Hash(hash_bytes)) + ": " + repr(self.parser(iter((bytes_))))
            for hash_bytes, bytes_ in list(self.d.items())
            )

    def add(self, serializable):
        pmts(serializable, self.type_)

        bytes_ = serializable.as_bytes()
        hash_ = Hash.for_bytes(bytes_)
        self.d[hash_.as_bytes()] = bytes_
        return hash_

    def get(self, hash_):
        if hash_.as_bytes() not in self.d:
            raise KeyError(repr(hash_))
        return self.parser(iter(self.d[hash_.as_bytes()]))

    def guess(self, human_readable_hash):
        prefix = unhexlify(human_readable_hash)
        for k, v in list(self.d.items()):
            if k.startswith(prefix):
                return self.get(Hash(k))
        raise KeyError()


class ReadOnlyHashStore(object):
    def __init__(self, delegate):
        self._delegate = delegate

    def get(self, hash_):
        return self._delegate.get(hash_)

    def guess(self, human_readable_hash):
        return self._delegate.guess(human_readable_hash)
