from utils import pmts
from datastructure import Nout, parse_nout, Hash

POSSIBILITY = 0
ACTUALITY = 1


class Possibility(object):
    def __init__(self, nout):
        pmts(nout, Nout)
        self.nout = nout

    def as_bytes(self):
        return bytes([POSSIBILITY]) + self.nout.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Possibility(parse_nout(byte_stream))


class Actuality(object):
    def __init__(self, nout_hash):
        pmts(nout_hash, Hash)
        # better yet would be: a pmts that actually makes sure whether the given hash actually points at a Nout...
        self.nout_hash = nout_hash

    def as_bytes(self):
        return bytes([ACTUALITY]) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Actuality(Hash.from_stream(byte_stream))


def parse_pos_act(byte_stream):
    byte0 = next(byte_stream)
    return {
        ACTUALITY: Actuality,
        POSSIBILITY: Possibility,
    }[byte0].from_stream(byte_stream)


def parse_pos_acts(byte_stream):
    while True:
        yield parse_pos_act(byte_stream)  # Transparently yields the StopIteration at the lower level
