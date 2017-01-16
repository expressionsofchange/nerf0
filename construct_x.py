from clef import BecomeNode, Insert, Delete, Replace, TextBecome
from trees import TreeNode, TreeText, YourOwnHash
from spacetime import st_become, st_insert, st_replace, st_delete
from legato import all_nhtups_for_nout_hash


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
        return TreeNode([], t2s, s2t, metadata), False

    if isinstance(note, TextBecome):
        # if structure is not None... return error -- in the present version, TextBecome _can_ actually be called on
        # an existing TreeText; This interpretation is tentative.
        return TreeText(note.unicode_, metadata), False

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            return structure, True  # "Out of bounds: %s" % note.index

        child, error = recurse(note.nout_hash)
        if error:
            # TODO thoughts about "as much as possible" at the lower level
            # one reason _not_ to do that... what if the lower level doesn't even succesfully recurse from None to a
            # tree?? then you'd construct a non-typed tree at this point.
            # we'll see... once we have this integrated in the GUI

            # Counterpoint: we could also say that construct_x should always at least return a tree (whether it's stuck
            # on an error or not)

            # who's enforcing these things? and what is enforced in terms of the notes?
            # let's start with the _what_.
            # as long as your first note is a become (of some kind), you'll have some tree constructed.
            # I'm not sure who's providing that guarantee.... but for now I'm going to assume it.
            return structure, error

        l = structure.children[:]
        l.insert(note.index, child)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        return TreeNode(l, t2s, s2t, metadata), False

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Replace the check is "inside bounds"
        return structure, True  # "Out of bounds: %s" % note.index

    if isinstance(note, Delete):
        l = structure.children[:]
        del l[note.index]
        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)
        return TreeNode(l, t2s, s2t, metadata), False

    if isinstance(note, Replace):
        child, error = recurse(note.nout_hash)
        if error:
            # similar remarks as above apply!
            return structure, error

        l = structure.children[:]
        l[note.index] = child
        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)
        return TreeNode(l, t2s, s2t, metadata), False

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
        if tup.nout_hash.as_bytes() in results_lookup:
            tree = results_lookup[tup.nout_hash.as_bytes()]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        tree, error = x_note_play(note, tree, recurse, YourOwnHash(edge_nout_hash))
        if error:
            return tree, True

        results_lookup[edge_nout_hash.as_bytes()] = tree

    return tree, False
