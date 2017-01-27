# coding=utf-8

from vlq import to_vlq, from_vlq
from utils import pmts, rfs

bytes_iterator = type(iter(bytes()))

NOTE_NODE_BECOME = 4
NOTE_NODE_INSERT = 0
NOTE_NODE_DELETE = 1
NOTE_NODE_REPLACE = 2
# NOTE_COMBINE = 3

NOTE_TEXT_BECOME = 3


# ##  Vocabulary of change  (AKA "Clef")

# Potentially: explicitly reflect in the naming of Node-related nodes that they are just that.
# (As opposed to Text-related ones)


class Note(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            NOTE_NODE_BECOME: BecomeNode,
            NOTE_NODE_INSERT: Insert,
            NOTE_NODE_DELETE: Delete,
            NOTE_NODE_REPLACE: Replace,
            NOTE_TEXT_BECOME: TextBecome,
        }[byte0].from_stream(byte_stream)


class BecomeNode(Note):
    def __repr__(self):
        return "(NODE)"

    def as_bytes(self):
        return bytes([NOTE_NODE_BECOME])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeNode()


class Insert(Note):
    def __init__(self, index, nout_hash):
        """index : index to be inserted at in the list of children
        nout_hash: Hash pointing to a Nout of the history to be inserted"""

        # Avoids circular imports (NoteNout's definition depends on a definition of Note; and we depend on
        # NoteNoutHash). Strictly speaking we could reorder the definitions as well, as such:
        # * Note (the base class)
        # * NoteNout & NoteNoutHash
        # * Note's implementations (Insert, Replace)
        from dsn.s_expr.legato import NoteNoutHash

        pmts(index, int)
        pmts(nout_hash, NoteNoutHash)

        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(INSERT " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def as_bytes(self):
        return bytes([NOTE_NODE_INSERT]) + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.s_expr.legato import NoteNoutHash  # Avoids circular imports (see note in Insert.__init__)

        # N.B.: The TypeConstructor byte is not repeated here; it happens before we reach this point
        return Insert(from_vlq(byte_stream), NoteNoutHash.from_stream(byte_stream))


class Delete(Note):
    def __init__(self, index):
        """index :: index to be deleted"""
        pmts(index, int)
        self.index = index

    def __repr__(self):
        return "(DELETE " + repr(self.index) + ")"

    def as_bytes(self):
        return bytes([NOTE_NODE_DELETE]) + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return Delete(from_vlq(byte_stream))


class Replace(Note):
    def __init__(self, index, nout_hash):
        """index : index to be inserted at in the list of children
        nout_hash: NoteNoutHash pointing to a Nout of the history to be inserted"""

        from dsn.s_expr.legato import NoteNoutHash  # Avoids circular imports (see note in Insert.__init__)

        pmts(index, int)
        pmts(nout_hash, NoteNoutHash)

        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(REPLACE " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def as_bytes(self):
        return bytes([NOTE_NODE_REPLACE]) + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.s_expr.legato import NoteNoutHash  # Avoids circular imports (see note in Insert.__init__)
        return Replace(from_vlq(byte_stream), NoteNoutHash.from_stream(byte_stream))


# Text-related notes: I'm starting with just one
class TextBecome(Note):
    def __init__(self, unicode_):
        pmts(unicode_, str)
        self.unicode_ = unicode_

    def __repr__(self):
        return "(TEXT " + self.unicode_ + ")"

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return bytes([NOTE_TEXT_BECOME]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return TextBecome(str(utf8, 'utf-8'))
