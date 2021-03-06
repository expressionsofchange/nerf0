from vlq import to_vlq
from utils import pmts

# Type constructor codes
TREE_NODE = 0
TREE_TEXT = 1


class YourOwnHash(object):
    def __init__(self, nout_hash):
        self.nout_hash = nout_hash


class SExpr(object):
    def __init__(self, *args, **kwargs):
        raise TypeError("SExpr is Abstract; use TreeNode or TreeText instead")


class TreeNode(SExpr):

    def __init__(self, children, t2s=None, s2t=None, metadata=None):
        self.children = children
        self.t2s = t2s
        self.s2t = s2t
        self.broken = False

        self.metadata = metadata

    def __repr__(self):
        return pp_flat(self)

    def __eq__(self, other):
        """NOTE:  __eq__ ignores any time-aspects (i.e. metadata, t2s), only eqqing on the present structure"""
        return isinstance(other, TreeNode) and self.children == other.children and self.broken == other.broken

    def as_bytes(self):
        # as of yet unused
        return bytes([TREE_NODE]) + to_vlq(len(self.children)) + b''.join([c.as_bytes() for c in self.children])

    def broken_equivalent(self, metadata):
        result = TreeNode(self.children, self.t2s, self.s2t, metadata)
        result.broken = True
        return result


class TreeText(SExpr):

    def __init__(self, unicode_, metadata):
        pmts(unicode_, str)
        self.unicode_ = unicode_
        self.metadata = metadata
        self.broken = False  # as it stands: TreeText cannot be broken

    def __repr__(self):
        return pp_flat(self)

    def __eq__(self, other):
        """NOTE:  __eq__ ignores any time-aspects (i.e. metadata), only eqqing on the present structure"""
        return isinstance(other, TreeText) and self.unicode_ == other.unicode_ and self.broken == other.broken

    def as_bytes(self):
        # as of yet unused
        utf8 = self.unicode_.encode('utf-8')
        return bytes([TREE_TEXT]) + to_vlq(len(utf8)) + utf8


# Tools for Pretty Printing

def pp_flat(node):
    if isinstance(node, TreeText):
        return node.unicode_
    return "(" + " ".join(pp_flat(c) for c in node.children) + ")"


def pp_2(node, indentation):
    """"Lisp Style indentation, i.e. xxx yyy
                                     zzz
    """
    if isinstance(node, TreeText):
        return node.unicode_

    if len(node.children) <= 2:
        return "(" + " ".join(pp_flat(c) for c in node.children) + ")"

    my_arg_0 = "(" + pp_flat(node.children[0])  # the first element is always shown flat;
    next_indentation = indentation + len(my_arg_0) + len(" ")

    return (my_arg_0 + " " + pp_2(node.children[1], next_indentation) + "\n" +
            "\n".join((" " * next_indentation) + pp_2(c, next_indentation) for c in node.children[2:]) + ")")


def pp_todo(node, indentation):
    if isinstance(node, TreeText):
        return node.unicode_

    if len(node.children) < 1:
        return "(...)"

    # a somewhat unexpect scenario, because the first arg is supposed to be text in this setup
    my_arg_0 = "" + pp_flat(node.children[0])
    next_indentation = indentation + 4

    return (my_arg_0 + ("\n\n" if len(node.children) > 1 else "") +
            "\n\n".join((" " * next_indentation) + pp_todo(c, next_indentation) for c in node.children[1:]))


def pp_todo_numbered(node, indentation):
    if isinstance(node, TreeText):
        return node.unicode_

    if len(node.children) < 1:
        return "(...)"

    # a somewhat unexpect scenario, because the first arg is supposed to be text in this setup
    my_arg_0 = "[0] " + pp_flat(node.children[0])
    next_indentation = indentation + 4

    return (my_arg_0 + ("\n\n" if len(node.children) > 1 else "") +
            "\n\n".join(
                (" " * next_indentation) + "[%s] " % (i + 1) + pp_todo(c, next_indentation)
                for (i, c) in enumerate(node.children[1:])))
