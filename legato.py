from utils import pmts
from hashstore import Hash
from collections import namedtuple


NoutAndHash = namedtuple('NoutAndHash', (
    'nout',
    'nout_hash'))


NOUT_CAPO = 0
NOUT_SLUR = 1


class Nout(object):
    pass


class NoutCapo(Nout):
    # NoutCapo does not actually depend on the NoteClass/parse_note, which is why it's kept outside of the factory
    # symmetry

    def __repr__(self):
        return "(CAPO)"

    def as_bytes(self):
        return bytes([NOUT_CAPO])

    @staticmethod
    def from_stream(byte_stream):
        return NoutCapo()

    def __eq__(self, other):
        return isinstance(other, NoutCapo)


def nout_factory(NoteClass, parse_note):

    class NoutSlur(Nout):

        def __init__(self, note, previous_hash):
            pmts(note, NoteClass)
            pmts(previous_hash, Hash)

            self.note = note
            self.previous_hash = previous_hash

        def __repr__(self):
            return "(SLUR " + repr(self.note) + " -> " + repr(self.previous_hash) + ")"

        def as_bytes(self):
            return bytes([NOUT_SLUR]) + self.note.as_bytes() + self.previous_hash.as_bytes()

        @staticmethod
        def from_stream(byte_stream):
            return NoutSlur(parse_note(byte_stream), Hash.from_stream(byte_stream))

    def parse_nout(byte_stream):
        byte0 = next(byte_stream)
        return {
            NOUT_CAPO: NoutCapo,
            NOUT_SLUR: NoutSlur,
        }[byte0].from_stream(byte_stream)

    return NoutSlur, parse_nout


def all_nhtups_for_nout_hash(possible_timelines, nout_hash):
    while True:
        nout = possible_timelines.get(nout_hash)
        if nout == NoutCapo():
            raise StopIteration()

        yield NoutAndHash(nout, nout_hash)
        nout_hash = nout.previous_hash


def all_preceding_nout_hashes(possible_timelines, nout_hash):
    return (t.nout_hash for t in all_nhtups_for_nout_hash(possible_timelines, nout_hash))
