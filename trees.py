from vlq import to_vlq
from utils import pmts

# Type constructor codes
TREE_NODE = 0
TREE_TEXT = 1


class YourOwnHash(object):
    def __init__(self, nout_hash):
        self.nout_hash = nout_hash


class TreeNode(object):

    def __init__(self, children, metadata=None):
        self.children = children
        self.metadata = metadata

    def __repr__(self):
        return self.pp_flat()

    # TODO I'd rather factor out pp*

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
        # as of yet unused
        utf8 = self.unicode_.encode('utf-8')
        return bytes([TREE_TEXT]) + to_vlq(len(utf8)) + utf8
