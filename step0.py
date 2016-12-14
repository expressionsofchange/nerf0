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

    def __init__(self, children, histories=None):
        if histories is None:
            histories = []  # hack to keep the pp-code around for a bit
        self.histories = histories
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
        return TreeNode([], [])

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
        h = structure.histories[:]
        h.insert(self.index, self.nout_hash)

        l = structure.children[:]
        l.insert(self.index, play(possible_timelines.get(self.nout_hash)))

        return TreeNode(l, h)

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
        h = structure.histories[:]
        del h[self.index]

        l = structure.children[:]
        del l[self.index]
        return TreeNode(l, h)

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
        h = structure.histories[:]
        h[self.index] = self.nout_hash

        l = structure.children[:]
        l[self.index] = play(possible_timelines.get(self.nout_hash))
        return TreeNode(l, h)

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
        if hash_.as_bytes() not in self.d:
            raise KeyError(repr(hash_))
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


def edit_text(text_node):
    print text_node.unicode_
    print '=' * 80
    text = unicode(raw_input(">>> "), 'utf-8')

    # In the most basic version of the editor text has no history, which is why the editing of text spawns a new
    # (extremely brief) history
    # THE ABOVE IS A LIE
    # we could just as well choose to have history (just a history of full replaces) at the level of the text nodes
    # I have chosen against it for now, but we can always do it
    begin = imagine(NoutBegin())
    return imagine(NoutBlock(TextBecome(text), begin))


def edit_node(possible_timelines, present_nout):
    original_present_nout = present_nout

    while True:
        present_tree = play(possible_timelines.get(present_nout))
        print present_tree.pp_2(0)
        print '=' * 80

        choice = None
        while choice not in ['x', 'w', 'e', 'd', 'i', 'a', 's', '>', '<']:
            # DONE:
            # print "[E]dit"
            # print "[D]elete"
            # print "[I]nsert"
            # print "e[X]it without saving"
            # print "Exit and save (W)"

            # UNDO?
            # Save w/o exit?
            # Reload? (i.e. full undo?)

            # Simply "Add"
            # Create wrapping node
            # Collapse to index

            choice = getch()

        if choice in 'xw':
            if choice == 'x':
                return original_present_nout
            return present_nout

        if choice == 'a':  # append node
            begin = imagine(NoutBegin())  # meh... this recurring imagining of begin is stupid; let's make it global
            inserted_nout = imagine(NoutBlock(BecomeNode(), begin))
            present_nout = imagine(NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))

        if choice == 's':  # append text
            text = unicode(raw_input(">>> "), 'utf-8')
            begin = imagine(NoutBegin())  # meh... this recurring imagining of begin is stupid; let's make it global
            inserted_nout = imagine(NoutBlock(TextBecome(text), begin))
            present_nout = imagine(NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))

        if choice == '>':  # surround yourself with a new node
            begin = imagine(NoutBegin())  # meh... this recurring imagining of begin is stupid; let's make it global
            wrapping_nout = imagine(NoutBlock(BecomeNode(), begin))
            present_nout = imagine(NoutBlock(Insert(0, present_nout), wrapping_nout))

        # Note (TODO): edit & delete presume an existing node; insertion can happen at the end too.
        # i.e. check indexes
        if choice in 'edi<':
            index = int(raw_input("Index>>> "))

        if choice == '<':  # remove a node; make it's contents available as _your_ children
            to_be_removed = present_tree.children[index]
            for i, (child, child_history) in enumerate(zip(to_be_removed.children, to_be_removed.histories)):
                present_nout = imagine(NoutBlock(Insert(index + i + 1, child_history), present_nout))

            present_nout = imagine(NoutBlock(Delete(index), present_nout))

        if choice == 'e':
            # Where do we distinguish the type? perhaps actually here, based on what we see.
            subject = present_tree.children[index]

            if isinstance(subject, TreeNode):
                old_nout = present_tree.histories[index]
                new_nout = edit_node(possible_timelines, old_nout)

                if new_nout != old_nout:
                    present_nout = imagine(NoutBlock(Replace(index, new_nout), present_nout))

            else:
                present_nout = imagine(NoutBlock(Replace(index, edit_text(subject)), present_nout))

        if choice == 'i':
            type_choice = None
            while type_choice not in ['n', 't']:
                print "Choose type (n/t)"
                type_choice = getch()

            if type_choice == 't':
                text = unicode(raw_input(">>> "), 'utf-8')
                begin = imagine(NoutBegin())  # meh... this recurring imagining of begin is stupid; let's make it global
                inserted_nout = imagine(NoutBlock(TextBecome(text), begin))

            else:  # type_choice == 'n'
                begin = imagine(NoutBegin())  # meh... this recurring imagining of begin is stupid; let's make it global
                inserted_nout = imagine(NoutBlock(BecomeNode(), begin))

            present_nout = imagine(NoutBlock(Insert(index, inserted_nout), present_nout))

        if choice == 'd':
            present_nout = imagine(NoutBlock(Delete(index), present_nout))


def imagine(nout):
    return possible_timelines.add(nout.as_bytes())


def initialize():
    # Here is some example usage:
    begin = imagine(NoutBegin())
    root_nout = imagine(NoutBlock(BecomeNode(), begin))

    # TODO: 'save' at the highest level must be implemented here.
    # TODO think about "save without exit"
    edit_node(possible_timelines, root_nout)


# Possibility & Actuality data structures

POSSIBILITY = '\x00'
ACTUALITY = '\x01'


class Possibility(object):
    def __init__(self, nout):
        self.nout = nout

    def as_bytes(self):
        return POSSIBILITY + self.nout.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Possibility(parse_nout(byte_stream))


class Actuality(object):
    def __init__(self, nout):
        self.nout = nout

    def as_bytes(self):
        return ACTUALITY + self.nout.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Actuality(parse_nout(byte_stream))


# http://stackoverflow.com/a/21659588/339144
def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys
    import tty

    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch

getch = _find_getch()
