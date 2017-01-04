from clef import BecomeNode, Insert, Delete, Replace, TextBecome
from trees import TreeNode, TreeText, YourOwnHash
from legato import NoutBegin
from hashstore import Hash


def x_note_play(note, structure, recurse, metadata):
    if isinstance(note, BecomeNode):
        return TreeNode([], metadata)

    if isinstance(note, Insert):
        l = structure.children[:]
        l.insert(note.index, recurse(note.nout_hash))

        return TreeNode(l, metadata)

    if isinstance(note, Delete):
        l = structure.children[:]
        del l[note.index]
        return TreeNode(l, metadata)

    if isinstance(note, Replace):
        l = structure.children[:]
        l[note.index] = recurse(note.nout_hash)
        return TreeNode(l, metadata)

    if isinstance(note, TextBecome):
        return TreeText(note.unicode_, metadata)

    raise Exception("Unknown Note")


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

    result = x_note_play(note, tree_before_edge, recurse, YourOwnHash(hash_for(edge_nout)))
    results_lookup[edge_nout_hash.as_bytes()] = result
    return result
