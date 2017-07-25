from spacetime import st_become, st_insert, st_replace, st_delete
from list_operations import l_become, l_insert, l_delete, l_replace

from dsn.s_expr.clef import BecomeNode, Insert, Delete, Replace, TextBecome
from dsn.s_expr.structure import TreeNode, TreeText, YourOwnHash


def x_note_play(note, structure, recurse, metadata):
    """
    Plays a single note.
    :: .... => tree

    Note an assymmetry between the *Become* notes and the others; the former requiring nothingness to precede them,
    the latter requiring an existing structure to further manipulate.

    Note on an asymmetry with y_note_play: here we have included it as an attribute of the treenodes, in y_note_play we
    pass around is_dissonent as an explicit paratemer/result-element,
    """
    if structure is not None and structure.broken:
        # alternatively: don't pass broken structures in here; deal with it in construct_x
        return structure.broken_equivalent(metadata)

    if isinstance(note, BecomeNode):
        if structure is not None:
            return structure.broken_equivalent(metadata)  # "You can only BecomeNode out of nothingness"

        t2s, s2t = st_become()
        return TreeNode(l_become(), t2s, s2t, metadata)

    if isinstance(note, TextBecome):
        # if structure is not None... return error -- in the present version, TextBecome _can_ actually be called on
        # an existing TreeText; This interpretation is tentative.
        return TreeText(note.unicode_, metadata)

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            return structure.broken_equivalent(metadata)  # "Out of bounds: %s" % note.index

        child = recurse(note.nout_hash)

        children = l_insert(structure.children[:], note.index, child)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata)

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Replace the check is "inside bounds"
        return structure.broken_equivalent(metadata)  # "Out of bounds: %s" % note.index

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata)

    if isinstance(note, Replace):
        child = recurse(note.nout_hash)
        children = l_replace(structure.children, note.index, child)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)
        return TreeNode(children, t2s, s2t, metadata)

    raise Exception("Unknown Note")


def construct_x(m, stores, edge_nout_hash):
    """Constructs a TreeNode by playing the full history represented by edge_nout_hash. The resulting TreeNode and any
    descendants have their own nout_hash as metadata.

    The idea of storing metadata on TreeNodes, i.e. any data that is not just the structure of the tree, is tentative:
    Pros & Cons of storing the NoutHash on the TreeNode itself are:

    * Pro: quite useful in any case where you want to reason about a TreeNode in its historical context.
    * Con: quite bothersome in all other cases, specifically
        * when reasoning about equality of identical TreeNodes with non-identical histories
        * when deduplicating (which is an instance of reasoning about equality)

    Reasons for having a separate, general metadata attribute, with a YourOwnHash implementation:

    * Opens the way for another method construct_x_2 which creates your-own-hash-less TreeNodes.
    * (YAGNI?) useful when storing something else than the node's own nout_hash

    The fact that this whole idea of Metadata is still somewhat tentative is reflected in the `_x` in the present
    method's name, rather than something more explicit.
    """
    def recurse(nout_hash):
        # This is used for by `play` to construct Trees for nouts, i.e. for Replace & Insert.
        return construct_x(m, stores, nout_hash)

    tree = None  # In the beginning, there is nothing, which we model as `None`

    todo = []
    for tup in stores.note_nout.all_nhtups_for_nout_hash(edge_nout_hash):
        if tup.nout_hash in m.construct_x:
            tree = m.construct_x[tup.nout_hash]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        tree = x_note_play(note, tree, recurse, YourOwnHash(edge_nout_hash))
        m.construct_x[edge_nout_hash] = tree

    return tree
