from binascii import unhexlify

from datastructure import Hash


class HashStore(object):

    def __init__(self, parser):
        self.d = {}
        self.parser = parser

    def __repr__(self):
        return '\n'.join(
            repr(Hash(hash_bytes)) + ": " + repr(self.parser(iter((bytes_))))
            for hash_bytes, bytes_ in list(self.d.items())
            )

    def add(self, serializable):
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
