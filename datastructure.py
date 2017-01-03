# coding=utf-8
from hashlib import sha256
from binascii import hexlify

from vlq import to_vlq, from_vlq
from utils import pmts, rfs

bytes_iterator = type(iter(bytes()))

# Type constructor codes
TREE_NODE = 0
TREE_TEXT = 1

NOUT_BEGIN = 0
NOUT_BLOCK = 1

NOTE_NODE_BECOME = 4
NOTE_NODE_INSERT = 0
NOTE_NODE_DELETE = 1
NOTE_NODE_REPLACE = 2
# NOTE_COMBINE = 3

NOTE_TEXT_BECOME = 3


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


class YourOwnHash(object):
    def __init__(self, nout_hash):
        self.nout_hash = nout_hash


class TreeNode(object):

    def __init__(self, children, metadata=None):
        self.children = children
        self.metadata = metadata

    def __repr__(self):
        return self.pp_flat()

    def pp_flat(self):
        return "(" + " ".join(c.pp_flat() for c in self.children) + ")"

    def pp_2(self, indentation):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz
        if len(self.children) <= 2:
            return "(" + " ".join(c.pp_flat() for c in self.children) + ")"

        my_arg_0 = "(" + self.children[0].pp_flat()  # the first element is always shown flat;
        next_indentation = indentation + len(my_arg_0) + len(" ")

        return (my_arg_0 + " " + self.children[1].pp_2(next_indentation) + "\n" +
                "\n".join((" " * next_indentation) + c.pp_2(next_indentation) for c in self.children[2:]) + ")")

    def pp_todo(self, indentation):
        if len(self.children) < 1:
            return "(...)"

        # a somewhat unexpect scenario, because the first arg is supposed to be text in this setup
        my_arg_0 = "" + self.children[0].pp_flat()
        next_indentation = indentation + 4

        return (my_arg_0 + ("\n\n" if len(self.children) > 1 else "") +
                "\n\n".join((" " * next_indentation) + c.pp_todo(next_indentation) for c in self.children[1:]))

    def pp_todo_numbered(self, indentation):
        if len(self.children) < 1:
            return "(...)"

        # a somewhat unexpect scenario, because the first arg is supposed to be text in this setup
        my_arg_0 = "[0] " + self.children[0].pp_flat()
        next_indentation = indentation + 4

        return (my_arg_0 + ("\n\n" if len(self.children) > 1 else "") +
                "\n\n".join(
                    (" " * next_indentation) + "[%s] " % (i + 1) + c.pp_todo(next_indentation)
                    for (i, c) in enumerate(self.children[1:])))

    def as_bytes(self):
        return bytes([TREE_NODE]) + to_vlq(len(self.children)) + b''.join([c.as_bytes() for c in self.children])


class TreeText(object):

    def __init__(self, unicode_, metadata):
        pmts(unicode_, str)
        self.unicode_ = unicode_
        self.metadata = metadata

    def __repr__(self):
        return self.unicode_

    def pp_flat(self):
        return self.unicode_

    def pp_2(self, indentation):
        return self.unicode_

    def pp_todo(self, indentation):
        return self.unicode_

    def pp_todo_numbered(self, indentation):
        return self.unicode_

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return bytes([TREE_TEXT]) + to_vlq(len(utf8)) + utf8


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

# ##  Vocabulary of change  (AKA "Clef")

# Potentially: explicitly reflect in the naming of Node-related nodes that they are just that.
# (As opposed to Text-related ones)


class Note(object):
    pass


class BecomeNode(Note):
    def __repr__(self):
        return "(NODE)"

    def as_bytes(self):
        return bytes([NOTE_NODE_BECOME])

    def play(self, structure, recurse, metadata):
        return TreeNode([], metadata)

    @staticmethod
    def from_stream(byte_stream):
        return BecomeNode()


class Insert(Note):
    def __init__(self, index, nout_hash):
        """index : index to be inserted at in the list of children
        nout_hash: Hash pointing to a Nout of the history to be inserted"""

        pmts(index, int)
        pmts(nout_hash, Hash)
        # better yet would be: a pmts that actually makes sure whether the given hash actually points at a Nout...

        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(INSERT " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def play(self, structure, recurse, metadata):
        l = structure.children[:]
        l.insert(self.index, recurse(self.nout_hash))

        return TreeNode(l, metadata)

    def as_bytes(self):
        return bytes([NOTE_NODE_INSERT]) + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        # N.B.: The TypeConstructor byte is not repeated here; it happens before we reach this point
        return Insert(from_vlq(byte_stream), Hash.from_stream(byte_stream))


class Delete(Note):
    def __init__(self, index):
        """index :: index to be deleted"""
        pmts(index, int)
        self.index = index

    def __repr__(self):
        return "(DELETE " + repr(self.index) + ")"

    def play(self, structure, recurse, metadata):
        l = structure.children[:]
        del l[self.index]
        return TreeNode(l, metadata)

    def as_bytes(self):
        return bytes([NOTE_NODE_DELETE]) + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return Delete(from_vlq(byte_stream))


class Replace(Note):
    def __init__(self, index, nout_hash):
        """index : index to be inserted at in the list of children
        nout_hash: Hash pointing to a Nout of the history to be inserted"""

        pmts(index, int)
        pmts(nout_hash, Hash)
        # better yet would be: a pmts that actually makes sure whether the given hash actually points at a Nout...

        self.index = index
        self.nout_hash = nout_hash

    def __repr__(self):
        return "(REPLACE " + repr(self.index) + " " + repr(self.nout_hash) + ")"

    def play(self, structure, recurse, metadata):
        l = structure.children[:]
        l[self.index] = recurse(self.nout_hash)
        return TreeNode(l, metadata)

    def as_bytes(self):
        return bytes([NOTE_NODE_REPLACE]) + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Replace(from_vlq(byte_stream), Hash.from_stream(byte_stream))


# Text-related notes: I'm starting with just one
class TextBecome(Note):
    def __init__(self, unicode_):
        pmts(unicode_, str)
        self.unicode_ = unicode_

    def __repr__(self):
        return "(TEXT " + self.unicode_ + ")"

    def play(self, structure, recurse, metadata):
        return TreeText(self.unicode_, metadata)

    def as_bytes(self):
        utf8 = self.unicode_.encode('utf-8')
        return bytes([NOTE_TEXT_BECOME]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return TextBecome(str(utf8, 'utf-8'))


def parse_note(byte_stream):
    byte0 = next(byte_stream)
    return {
        NOTE_NODE_BECOME: BecomeNode,
        NOTE_NODE_INSERT: Insert,
        NOTE_NODE_DELETE: Delete,
        NOTE_NODE_REPLACE: Replace,
        NOTE_TEXT_BECOME: TextBecome,
    }[byte0].from_stream(byte_stream)


def construct_x(results_lookup, possible_timelines, edge_nout_hash):
    """Constructs a TreeNode with the appropriate metadata. The fact that I'm not really sure what's appropriate yet (I
    just refactored it) is reflected in the `_x` part of this procedure's name.

    What do I mean by 'metadata'?
    By that I mean that for any single defined structure (until now there's only one) multiple choices may be made about
    whch attributes need to be available for the rest of the program.

    The prime example of this is the fact that I just added the node's own Nout Hash as an attribute on any node. This
    is useful if you want to see a tree as "a tree of histories" and in fact expresses such trees more elegantly than
    the previous solution (which has a special-case attribute `histories` to deal with that scenario)

    The alternative case is where you're _not_ interested in the history of the node (e.g. when you want to display the
    node you may want to ignore the history). And in general I'm not so charmed by a TreeNode having to know what it's
    point in NoutHistory is (also because many different points in NoutHistory may map to a single treenode)

    As an alternative solution I considered to pass the n (in this case 2: for TreeNode and TreeText) mechanisms of
    construction to `play`, rather than just some metadata.

    One more reason I came up with the idea of 'metadata' is: the name 'nout_hash' is bound to become quite overloaded;
    better to reflect which nout_hash we're talking about.

    (I may be overthinking this, I'm too sleepy today, but I want it documented at least somewhere)

    The points where this is reflected are:
    * metadata as an attribute on TreeNode and TreeText
    * YourOwnHash as a class
    * the `_x` in the present method's name
    """
    def recurse(nout_hash):
        return construct_x(results_lookup, possible_timelines, nout_hash)

    if edge_nout_hash.as_bytes() in results_lookup:
        return results_lookup[edge_nout_hash.as_bytes()]

    edge_nout = possible_timelines.get(edge_nout_hash)

    if edge_nout == NoutBegin():
        # Does it make sense to allow for the "playing" of "begin only"?
        # Only if you think "nothing" is a thing; let's build a version which doesn't do that first.
        raise Exception("In this version, I don't think playing empty history makes sense")

    last_nout_hash = edge_nout.previous_hash
    last_nout = possible_timelines.get(last_nout_hash)
    if last_nout == NoutBegin():
        tree_before_edge = None  # in theory: ignored, because the first note should always be a "Become" note
    else:
        tree_before_edge = construct_x(results_lookup, possible_timelines, last_nout_hash)

    note = edge_nout.note

    def hash_for(nout):
        # copy/pasta... e.g. from cli.py (at the time of copy/pasting)
        bytes_ = nout.as_bytes()
        return Hash.for_bytes(bytes_)

    result = note.play(tree_before_edge, recurse, YourOwnHash(hash_for(edge_nout)))
    results_lookup[edge_nout_hash.as_bytes()] = result
    return result
