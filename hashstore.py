from binascii import unhexlify

from datastructure import Hash, Nout
from posacts import Possibility
from utils import pmts


class HashStore(object):

    def __init__(self, parser):
        self.d = {}
        self.parser = parser
        self.write_to = None

    def __repr__(self):
        return '\n'.join(
            repr(Hash(hash_bytes)) + ": " + repr(self.parser(iter((bytes_))))
            for hash_bytes, bytes_ in list(self.d.items())
            )

    def add(self, serializable):
        # Even though HashStore has, in theory, no hard relationship with "Nouts", in practice we yiled "Possibilities"
        # here, which require Nout objects; that may point to "pull Possibility out" refactoring
        pmts(serializable, Nout)

        bytes_ = serializable.as_bytes()
        hash_ = Hash.for_bytes(bytes_)
        self.d[hash_.as_bytes()] = bytes_
        if self.write_to is not None:
            # Yuk: # the conditional on write-to
            self.write_to.write(Possibility(serializable).as_bytes())

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
