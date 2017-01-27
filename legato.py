from utils import pmts
from hashstore import Hash

NOUT_CAPO = 0
NOUT_SLUR = 1


def nout_factory(NoteClass, name_prefix):
    """nout_factory is some implementation of "Generic Types" (albeit as dynamic types), i.e. allows us to create the 3
    Nout classes for a given type of "payload" (note).

    The 3 classes are: `Nout` (abstract base class), `Capo` & `Slur`. They form a small class hierarchy with each
    other, but are unrelated to other types of Nout. This is intentional.
    """

    class NoutPrototype(object):
        @staticmethod
        def from_stream(byte_stream):
            byte0 = next(byte_stream)
            return {
                NOUT_CAPO: Capo,
                NOUT_SLUR: Slur,
            }[byte0].from_stream(byte_stream)

    class CapoPrototype(object):
        def __repr__(self):
            return "(CAPO)"

        def as_bytes(self):
            return bytes([NOUT_CAPO])

        @staticmethod
        def from_stream(byte_stream):
            return Capo()

        def __eq__(self, other):
            return isinstance(other, Capo)

    class SlurPrototype(object):
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
            return Slur(NoteClass.from_stream(byte_stream), Hash.from_stream(byte_stream))

    # Construct a small hierarchy with "readable names" (names that don't betray that the classes are created inside a
    # method). N.B.: The unqualified names `Nout`, `Capo` and `Slur` are local to this method, after returning the fully
    # qualified name (including the prefix) is used.
    Nout = type(name_prefix + "Nout", (object,), dict(NoutPrototype.__dict__))
    Capo = type(name_prefix + "Capo", (Nout,), dict(CapoPrototype.__dict__))
    Slur = type(name_prefix + "Slur", (Nout,), dict(SlurPrototype.__dict__))

    return Nout, Capo, Slur
