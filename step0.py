# coding=utf-8
from hashlib import sha256
from binascii import hexlify, unhexlify

from vlq import to_vlq, from_vlq

# Type constructor codes
TREE_NODE = b'\x00'
TREE_TEXT = b'\x01'

NOUT_BEGIN = b'\x00'
NOUT_BLOCK = b'\x01'

NOTE_NODE_BECOME = b'\x04'
NOTE_NODE_INSERT = b'\x00'
NOTE_NODE_DELETE = b'\x01'
NOTE_NODE_REPLACE = b'\x02'
# NOTE_COMBINE = b'\x03'

NOTE_TEXT_BECOME = b'\x03'


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


class TreeNode(object):

    def __init__(self, children):
        self.children = children

    def __repr__(self):
        return self.pp_flat()

    def pp_flat(self):
        return "(" + " ".join(c.pp_flat() for c in self.children) + ")"

    def pp_2(self, indentation):
        if len(self.children) <= 2:
            return u"(" + u" ".join(repr(c) for c in self.children) + u")"

        my_arg_0 = u"(" + self.children[0].pp_flat()  # ...
        next_indentation = indentation + len(my_arg_0) + len(u" ")

        return (my_arg_0 + u" " + self.children[1].pp_2(next_indentation) + u"\n" +
                u"\n".join((u" " * next_indentation) + c.pp_2(next_indentation) for c in self.children[2:]) + u")")

    def as_bytes(self):
        return TREE_NODE + to_vlq(len(self.children)) + b''.join([c.to_bytes() for c in self.children])


class TreeText(object):

    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def __repr__(self):
        return self.unicode_.encode("utf-8")

    def pp_flat(self):
        return self.unicode_

    def pp_2(self, indentation):
        return self.unicode_

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return TREE_TEXT + to_vlq(len(utf8)) + utf8


pp_test = TreeNode([
    TreeText("if"),
    TreeNode([
        TreeText("="),
        TreeText('1'),
        TreeText('2'),
    ]),
    TreeNode([
        TreeNode([
            TreeText("+"),
            TreeText('23'),
            TreeText("34"),
        ]),
        TreeText('1'),
        TreeNode([
            TreeText("+"),
            TreeText(u'uro sign (€) is the cu'),
            TreeText("14"),
        ]),
        TreeText("foo"),
    ]),
    TreeNode([
        TreeText("list"),
        TreeText('3'),
        TreeNode([
            TreeText("+"),
            TreeText('7'),
            TreeText("8"),
        ]),
        TreeText("bar"),
    ]),
])

print pp_test.__repr__()


# ## Binary encoding of nouts
class NoutBegin(object):
    def __repr__(self):
        return "(BEGIN)"

    def as_bytes(self):
        return NOUT_BEGIN

    @staticmethod
    def from_stream(byte_stream):
        return NoutBegin()

    def __eq__(self, other):
        return isinstance(other, NoutBegin)


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


class BecomeNode(object):
    def __repr__(self):
        return "(NODE)"

    def as_bytes(self):
        return NOTE_NODE_BECOME

    def apply_(self, structure):
        return TreeNode([])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeNode()


class Insert(object):
    def __init__(self, index, nout_hash):
        # index :: index to be inserted at in the list of children
        # nout_hash: NoutHash of the history to be inserted
        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(INSERT " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def apply_(self, structure):
        l = structure.children[:]
        l.insert(self.index, play(possible_timelines.get(self.nout_hash)))
        return TreeNode(l)

    def as_bytes(self):
        return NOTE_NODE_INSERT + to_vlq(self.index) + self.nout_hash.as_bytes()

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

    def apply_(self, structure):
        l = structure.children[:]
        l.remove(self.index)
        return TreeNode(l)

    def as_bytes(self):
        return NOTE_NODE_DELETE + to_vlq(self.index)

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

    def apply_(self, structure):
        l = structure.children[:]
        l[self.index] = play(possible_timelines.get(self.nout_hash))
        return TreeNode(l)

    def as_bytes(self):
        return NOTE_NODE_REPLACE + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Replace(from_vlq(byte_stream), Hash.from_stream(byte_stream))


# Text-related notes: I'm starting with just one
class TextBecome(object):
    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def __repr__(self):
        return "(TEXT " + self.unicode_.encode('utf-8') + ")"

    def apply_(self, structure):
        return TreeText(self.unicode_)

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return NOTE_TEXT_BECOME + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return TextBecome(unicode(utf8, 'utf-8'))


def parse_note(byte_stream):
    byte0 = byte_stream.next()
    return {
        NOTE_NODE_BECOME: BecomeNode,
        NOTE_NODE_INSERT: Insert,
        NOTE_NODE_DELETE: Delete,
        NOTE_NODE_REPLACE: Replace,
        NOTE_TEXT_BECOME: TextBecome,
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


def play(edge_nout):

    if edge_nout == NoutBegin():
        # Does it make sense to allow for the "playing" of "begin only"?
        # Only if you think "nothing" is a thing; let's build a version which doesn't do that first.
        raise Exception("In this version, I don't think playing empty history makes sense")

    last_nout = possible_timelines.get(edge_nout.previous_hash)
    if last_nout == NoutBegin():
        tree_before_edge = None  # in theory: ignored, because the first note should always be a "Become" note
    else:
        tree_before_edge = play(last_nout)

    note = edge_nout.note
    result = note.apply_(tree_before_edge)
    return result


possible_timelines = HashStore(parse_nout)
actual_timeline = []


def imagine(nout):
    return possible_timelines.add(nout.as_bytes())


# Here is some example usage:
begin = imagine(NoutBegin())
new_node = imagine(NoutBlock(BecomeNode(), begin))

aap = imagine(NoutBlock(TextBecome(u'aap'), begin))
noot = imagine(NoutBlock(TextBecome(u'noot'), begin))

aap_in_tree = imagine(NoutBlock(Insert(0, aap), new_node))
shifted_down = imagine(NoutBlock(Replace(0, aap_in_tree), aap_in_tree))

print play(possible_timelines.get(aap_in_tree))
print play(possible_timelines.get(shifted_down))

# that_happend v.s. _a particular history_
# Stack-like behavior that exploits that difference


# Let's get to write-to-file; read from file as required on startup
