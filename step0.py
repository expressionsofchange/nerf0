from hashlib import sha256
from binascii import hexlify, unhexlify

from vlq import to_vlq, from_vlq

# Type constructor codes
TREE_NODE = b'\x00'
TREE_TEXT = b'\x01'

NOUT_BEGIN = b'\x00'
NOUT_BLOCK = b'\x01'

NOTE_INSERT = b'\x00'
NOTE_DELETE = b'\x01'
NOTE_REPLACE = b'\x02'
# NOTE_COMBINE = b'\x03'

NOTE_TEXT_CREATE = b'\x03'


def rfs(byte_stream, n):
    # read n bytes from stream
    return "".join(byte_stream.next() for i in range(n))


class Hash(object):
    def __init__(self, hash_bytes):
        self.hash_bytes = hash_bytes

    def __repr__(self):
        return hexlify(self.hash_bytes)[:12]

    def as_bytes(self):
        return self.hash_bytes

    @staticmethod
    def from_bytes(bytes_):
        hash_ = sha256(bytes_).digest()
        return Hash(hash_)

    @staticmethod
    def from_stream(byte_stream):
        return Hash(rfs(byte_stream, 32))


def TreeNode(object):

    def __init__(self, children):
        self.children = children

    def as_bytes(self):
        return TREE_NODE + to_vlq(len(self.children)) + b''.join([c.to_bytes() for c in self.children])


def TreeText(text):

    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return TREE_TEXT + to_vlq(len(utf8)) + utf8


# ## Binary encoding of nouts
class NoutBegin(object):
    def __repr__(self):
        return "(BEGIN)"

    def as_bytes(self):
        return NOUT_BEGIN

    @staticmethod
    def from_stream(byte_stream):
        return NoutBegin()


class NoutBlock(object):
    def __init__(self, note, previous_hash):
        self.note = note
        self.previous_hash = previous_hash

    def __repr__(self):
        return "(BLOCK " + repr(self.note) + " -> " + repr(self.previous_hash) + ")"

    def as_bytes(self):
        return NOUT_BLOCK + self.note.as_bytes() + self.previous_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return NoutBlock(parse_note(byte_stream), Hash.from_stream(byte_stream))


def parse_nout(byte_stream):
    byte0 = byte_stream.next()
    return {
        NOUT_BEGIN: NoutBegin,
        NOUT_BLOCK: NoutBlock,
    }[byte0].from_stream(byte_stream)

# ##  Vocabulary of change  (AKA "Clef")

# Potentially: explicitly reflect in the naming of Node-related nodes that they are just that.
# (As opposed to Text-related ones)


class Insert(object):
    def __init__(self, index, nout_hash):
        # index :: index to be inserted at in the list of children
        # nout_hash: NoutHash of the history to be inserted
        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(INSERT " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def as_bytes(self):
        return NOTE_INSERT + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        # N.B.: The TypeConstructor byte is not repeated here; it happens before we reach this point
        return Insert(from_vlq(byte_stream), Hash.from_stream(byte_stream))


class Delete(object):
    def __init__(self, index):
        # index :: VLQ (index to be deleted)
        self.index = index

    def __repr__(self):
        return "(DELETE " + repr(self.index) + ")"

    def as_bytes(self):
        return NOTE_DELETE + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return Delete(from_vlq(byte_stream))


class Replace(object):
    def __init__(self, index, nout_hash):
        # index :: VLQ (index to be inserted at in the list of children;
        # nout_hash: NoutHash of the history to be inserted
        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(REPLACE " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def as_bytes(self):
        return NOTE_REPLACE + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Replace(from_vlq(byte_stream), Hash.from_stream(byte_stream))


# Text-related notes: I'm starting with just one
class TextCreate(object):
    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def __repr__(self):
        return "(TEXT " + self.unicode_.encode('utf-8') + ")"

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return NOTE_TEXT_CREATE + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return TextCreate(unicode(utf8, 'utf-8'))


def parse_note(byte_stream):
    byte0 = byte_stream.next()
    return {
        NOTE_INSERT: Insert,
        NOTE_DELETE: Delete,
        NOTE_REPLACE: Replace,
        NOTE_TEXT_CREATE: TextCreate,
    }[byte0].from_stream(byte_stream)


class HashStore(object):
    def __init__(self, parser):
        self.d = {}
        self.parser = parser

    def __repr__(self):
        return '\n'.join(
            repr(Hash(hash_bytes)) + ": " + repr(self.parser(iter((bytes_))))
            for hash_bytes, bytes_ in self.d.items()
            )

    def add(self, bytes_):
        hash_ = Hash.from_bytes(bytes_)
        self.d[hash_.as_bytes()] = bytes_
        return hash_

    def get(self, hash_):
        return self.parser(iter(self.d[hash_.as_bytes()]))

    def guess(self, human_readable_hash):
        prefix = unhexlify(human_readable_hash)
        for k, v in self.d.items():
            if k.startswith(prefix):
                return self.get(Hash(k))
        raise KeyError()


# Here is some example usage:
possible_timelines = HashStore(parse_nout)
actual_timeline = []


def imagine(nout):
    return possible_timelines.add(nout.as_bytes())

hash_0 = imagine(NoutBegin())

hash_1 = imagine(NoutBlock(Insert(0, hash_0), hash_0))
hash_2 = imagine(NoutBlock(Replace(0, hash_1), hash_1))

print possible_timelines

def play(timeline):
    What's the 'meaning of beginning?!

# Actually applying the changes on some structure :-D


# that_happend v.s. _a particular history_
# Stack-like behavior that exploits that difference


# Let's get to write-to-file; read from file as required on startup
