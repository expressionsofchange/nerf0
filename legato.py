from utils import pmts
from hashstore import Hash
from clef import Note, parse_note
from collections import namedtuple


NoutAndHash = namedtuple('NoutAndHash', (
    'nout',
    'nout_hash'))


NOUT_BEGIN = 0
NOUT_BLOCK = 1


class Nout(object):
    pass


# ## Binary encoding of nouts
class NoutBegin(Nout):
    def __repr__(self):
        return "(BEGIN)"

    def as_bytes(self):
        return bytes([NOUT_BEGIN])

    @staticmethod
    def from_stream(byte_stream):
        return NoutBegin()

    def __eq__(self, other):
        return isinstance(other, NoutBegin)


class NoutBlock(Nout):
    # Thoughts for the future:
    # * I don't like the name "block"; it's borrowed from the bitcoin world; I'd rather have a musical metaphor
    # * The tie-in to (a particular) Note can be abstracted away from by pushing the class into a method that takes
    #       a type of note and parser as parameters.

    def __init__(self, note, previous_hash):
        pmts(note, Note)
        pmts(previous_hash, Hash)

        self.note = note
        self.previous_hash = previous_hash

    def __repr__(self):
        return "(BLOCK " + repr(self.note) + " -> " + repr(self.previous_hash) + ")"

    def as_bytes(self):
        return bytes([NOUT_BLOCK]) + self.note.as_bytes() + self.previous_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return NoutBlock(parse_note(byte_stream), Hash.from_stream(byte_stream))


def parse_nout(byte_stream):
    byte0 = next(byte_stream)
    return {
        NOUT_BEGIN: NoutBegin,
        NOUT_BLOCK: NoutBlock,
    }[byte0].from_stream(byte_stream)


def follow_nouts(possible_timelines, nout_hash):
    yield nout_hash

    nout = possible_timelines.get(nout_hash)
    if nout == NoutBegin():
        raise StopIteration()

    for x in follow_nouts(possible_timelines, nout.previous_hash):
        yield x


def all_nhtups_for_nout_hash(possible_timelines, nout_hash):
    while True:
        nout = possible_timelines.get(nout_hash)
        if nout == NoutBegin():
            raise StopIteration()

        yield NoutAndHash(nout, nout_hash)
        nout_hash = nout.previous_hash
