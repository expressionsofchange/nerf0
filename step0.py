# coding=utf-8
from hashlib import sha256
from binascii import hexlify, unhexlify
from os.path import isfile

from vlq import to_vlq, from_vlq

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


def rfs(byte_stream, n):
    # read n bytes from stream
    return bytes((next(byte_stream) for i in range(n)))


class Hash(object):
    def __init__(self, hash_bytes):
        self.hash_bytes = hash_bytes

    def __repr__(self):
        return unicode(hexlify(self.hash_bytes)[:12], 'utf-8')

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
                "\n\n".join((" " * next_indentation) + "[%s] " % (i + 1) + c.pp_todo(next_indentation) for (i, c) in enumerate(self.children[1:])))

    def as_bytes(self):
        return bytes([TREE_NODE]) + to_vlq(len(self.children)) + b''.join([c.as_bytes() for c in self.children])


class TreeText(object):

    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def __repr__(self):
        return self.unicode_.encode("utf-8")

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
            TreeText('uro sign (€) is the cu'),
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

print(pp_test.__repr__())


# ## Binary encoding of nouts
class NoutBegin(object):
    def __repr__(self):
        return "(BEGIN)"

    def as_bytes(self):
        return bytes([NOUT_BEGIN])

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


class BecomeNode(object):
    def __repr__(self):
        return "(NODE)"

    def as_bytes(self):
        return bytes([NOTE_NODE_BECOME])

    def apply_(self, possible_timelines, structure):
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

    def apply_(self, possible_timelines, structure):
        h = structure.histories[:]
        h.insert(self.index, self.nout_hash)

        l = structure.children[:]
        l.insert(self.index, play(possible_timelines, possible_timelines.get(self.nout_hash)))

        return TreeNode(l, h)

    def as_bytes(self):
        return bytes([NOTE_NODE_INSERT]) + to_vlq(self.index) + self.nout_hash.as_bytes()

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

    def apply_(self, possible_timelines, structure):
        h = structure.histories[:]
        del h[self.index]

        l = structure.children[:]
        del l[self.index]
        return TreeNode(l, h)

    def as_bytes(self):
        return bytes([NOTE_NODE_DELETE]) + to_vlq(self.index)

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

    def apply_(self, possible_timelines, structure):
        h = structure.histories[:]
        h[self.index] = self.nout_hash

        l = structure.children[:]
        l[self.index] = play(possible_timelines, possible_timelines.get(self.nout_hash))
        return TreeNode(l, h)

    def as_bytes(self):
        return bytes([NOTE_NODE_REPLACE]) + to_vlq(self.index) + self.nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Replace(from_vlq(byte_stream), Hash.from_stream(byte_stream))


# Text-related notes: I'm starting with just one
class TextBecome(object):
    def __init__(self, unicode_):
        self.unicode_ = unicode_

    def __repr__(self):
        return "(TEXT " + self.unicode_.encode('utf-8') + ")"

    def apply_(self, possible_timelines, structure):
        return TreeText(self.unicode_)

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

    def add(self, bytes_):
        hash_ = Hash.from_bytes(bytes_)
        self.d[hash_.as_bytes()] = bytes_
        if self.write_to is not None:
            # Yuk:
            # a] the conditional on write-to
            # b] parsing here... suggests that .add's interface better be the whole object
            self.write_to.write(Possibility(self.parser(iter((bytes_)))).as_bytes())

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


def play(possible_timelines, edge_nout):
    if edge_nout == NoutBegin():
        # Does it make sense to allow for the "playing" of "begin only"?
        # Only if you think "nothing" is a thing; let's build a version which doesn't do that first.
        raise Exception("In this version, I don't think playing empty history makes sense")

    last_nout = possible_timelines.get(edge_nout.previous_hash)
    if last_nout == NoutBegin():
        tree_before_edge = None  # in theory: ignored, because the first note should always be a "Become" note
    else:
        tree_before_edge = play(possible_timelines, last_nout)

    note = edge_nout.note
    result = note.apply_(possible_timelines, tree_before_edge)
    return result


def edit_text(possible_timelines, text_node):
    print(text_node.unicode_)
    print('=' * 80)
    text = input(">>> ")

    # In the most basic version of the editor text has no history, which is why the editing of text spawns a new
    # (extremely brief) history
    # THE ABOVE IS A LIE
    # we could just as well choose to have history (just a history of full replaces) at the level of the text nodes
    # I have chosen against it for now, but we can always do it
    begin = imagine(possible_timelines, NoutBegin())
    return imagine(possible_timelines, NoutBlock(TextBecome(text), begin))


def edit_node(possible_timelines, present_nout):
    original_present_nout = present_nout

    while True:
        present_tree = play(possible_timelines, possible_timelines.get(present_nout))
        print(present_tree.pp_todo_numbered(0))
        print('=' * 80)

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
            begin = imagine(possible_timelines, NoutBegin())  # meh... this recurring imagining of begin is stupid;
            inserted_nout = imagine(possible_timelines, NoutBlock(BecomeNode(), begin))
            present_nout = imagine(possible_timelines, NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))

        if choice == 's':  # append text
            text = input(">>> ")
            begin = imagine(possible_timelines, NoutBegin())  # meh... this recurring imagining of begin is stupid;
            inserted_nout = imagine(possible_timelines, NoutBlock(TextBecome(text), begin))
            present_nout = imagine(possible_timelines, NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))

        if choice == '>':  # surround yourself with a new node
            begin = imagine(possible_timelines, NoutBegin())  # meh... this recurring imagining of begin is stupid;
            wrapping_nout = imagine(possible_timelines, NoutBlock(BecomeNode(), begin))
            present_nout = imagine(possible_timelines, NoutBlock(Insert(0, present_nout), wrapping_nout))

        # Note (TODO): edit & delete presume an existing node; insertion can happen at the end too.
        # i.e. check indexes
        if choice in 'edi<':
            index = int(input("Index>>> "))

        if choice == '<':  # remove a node; make it's contents available as _your_ children
            to_be_removed = present_tree.children[index]
            for i, (child, child_history) in enumerate(zip(to_be_removed.children, to_be_removed.histories)):
                present_nout = imagine(possible_timelines, NoutBlock(Insert(index + i + 1, child_history), present_nout))

            present_nout = imagine(possible_timelines, NoutBlock(Delete(index), present_nout))

        if choice == 'e':
            # Where do we distinguish the type? perhaps actually here, based on what we see.
            subject = present_tree.children[index]

            if isinstance(subject, TreeNode):
                old_nout = present_tree.histories[index]
                new_nout = edit_node(possible_timelines, old_nout)

                if new_nout != old_nout:
                    present_nout = imagine(possible_timelines, NoutBlock(Replace(index, new_nout), present_nout))

            else:
                present_nout = imagine(possible_timelines, NoutBlock(Replace(index, edit_text(possible_timelines, subject)), present_nout))

        if choice == 'i':
            type_choice = None
            while type_choice not in ['n', 't']:
                print("Choose type (n/t)")
                type_choice = getch()

            if type_choice == 't':
                text = input(">>> ")
                begin = imagine(possible_timelines, NoutBegin())  # meh... this recurring imagining of begin is stupid;
                inserted_nout = imagine(possible_timelines, NoutBlock(TextBecome(text), begin))

            else:  # type_choice == 'n'
                begin = imagine(possible_timelines, NoutBegin())  # meh... this recurring imagining of begin is stupid;
                inserted_nout = imagine(possible_timelines, NoutBlock(BecomeNode(), begin))

            present_nout = imagine(possible_timelines, NoutBlock(Insert(index, inserted_nout), present_nout))

        if choice == 'd':
            present_nout = imagine(possible_timelines, NoutBlock(Delete(index), present_nout))


def imagine(possible_timelines, nout):
    return possible_timelines.add(nout.as_bytes())


def edit(filename):
    possible_timelines = HashStore(parse_nout)

    def set_current(f, nout):
        f.write(Actuality(nout).as_bytes())

    if isfile(filename):
        byte_stream = iter(open(filename, 'rb').read())
        for pos_act in parse_pos_acts(byte_stream):
            if isinstance(pos_act, Possibility):
                possible_timelines.add(pos_act.nout.as_bytes())
            else:  # Actuality
                # this can be depended on to happen at least once ... if the file is correct
                present_nout = pos_act.nout_hash

    else:
        with open(filename, 'wb') as initialize_f:
            possible_timelines.write_to = initialize_f

            begin = imagine(possible_timelines, NoutBegin())
            present_nout = imagine(possible_timelines, NoutBlock(BecomeNode(), begin))

            set_current(initialize_f, present_nout)  # write the 'new file

    with open(filename, 'ab') as f:
        possible_timelines.write_to = f
        new_nout = edit_node(possible_timelines, present_nout)
        if new_nout != present_nout:
            set_current(f, new_nout)


# Possibility & Actuality data structures

POSSIBILITY = 0
ACTUALITY = 1


class Possibility(object):
    def __init__(self, nout):
        self.nout = nout

    def as_bytes(self):
        return bytes([POSSIBILITY]) + self.nout.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        return Possibility(parse_nout(byte_stream))


class Actuality(object):
    def __init__(self, nout_hash):
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


# The abilitiy to read a single character
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
