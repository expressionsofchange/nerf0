from clef import BecomeNode, Insert, Delete, Replace, TextBecome
from trees import TreeNode, TreeText, YourOwnHash
from spacetime import st_become, st_insert, st_replace, st_delete
from legato import all_nhtups_for_nout_hash
from list_operations import l_become, l_insert, l_delete, l_replace


def x_note_play(note, structure, recurse, metadata):
    """
    Plays a single note.
    :: .... => tree, error

    Note an assymmetry between the *Become* notes and the others; the former requiring nothingness to precede them,
    the latter requiring an existing structure to further manipulate.
    """

    if isinstance(note, BecomeNode):
        if structure is not None:
            return structure, True  # "You can only BecomeNode out of nothingness"

        t2s, s2t = st_become()
        return TreeNode(l_become(), t2s, s2t, metadata), False

    if isinstance(note, TextBecome):
        # if structure is not None... return error -- in the present version, TextBecome _can_ actually be called on
        # an existing TreeText; This interpretation is tentative.
        return TreeText(note.unicode_, metadata), False

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            return structure, True  # "Out of bounds: %s" % note.index

        # rather than not play on a recursive error, we play (in this case: insert), but propagate the error. This
        # ensures we keep constructing up onto the point of failure. recurse is guaranteed (though this is not yet
        # implemented) to give us some tree always (its result is never None) so this is always possible.
        child, error = recurse(note.nout_hash)

        children = l_insert(structure.children[:], note.index, child)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata), error

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Replace the check is "inside bounds"
        return structure, True  # "Out of bounds: %s" % note.index

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata), False

    if isinstance(note, Replace):
        # See notes on error-handling in Insert
        child, error = recurse(note.nout_hash)
        children = l_replace(structure.children, note.index, child)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata), error

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
        # This is used for by `play` to construct Trees for nouts, i.e. for Replace & Insert.
        return construct_x(results_lookup, possible_timelines, nout_hash)

    tree = None  # In the beginning, there is nothing, which we model as `None`

    todo = []
    for tup in all_nhtups_for_nout_hash(possible_timelines, edge_nout_hash):
        if tup.nout_hash in results_lookup:
            tree = results_lookup[tup.nout_hash]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        tree, error = x_note_play(note, tree, recurse, YourOwnHash(edge_nout_hash))
        if error:
            return tree, True

        results_lookup[edge_nout_hash] = tree

    return tree, False
