from dsn.s_expr.structure import TreeText

from dsn.s_expr.clef import BecomeNode, TextBecome, Insert, Replace, Delete
from spacetime import st_become, st_insert, st_replace, st_delete
from collections import namedtuple
from list_operations import l_become, l_insert, l_delete, l_replace

from historiography import HistoriographyTreeNode
from dsn.historiography.construct import construct_historiography

from dsn.historiography.clef import SetNoteNoutHash
from dsn.historiography.legato import HistoriographyNoteSlur, HistoriographyNoteNoutHash, HistoriographyNoteCapo


# A tuple containing information about histories at a lower level
RecursiveHistoryInfo = namedtuple('RecursiveHistoryInfo', (
    # the history at the lower level takes place at a certain t_address
    't_address',

    # historiography_note_nout is fully descriptive of the children_steps; those are left in for convenience sake
    'historiography_note_nout',
    'children_steps'))


AnnotatedHash = namedtuple('AnnotatedHash', (
    'hash',
    'dissonant',
    'recursive_information',
))


def y_note_play(stores, note, structure, structure_is_dissonant, recurse):
    # Note on an asymmetry with x_note_play: here we pass around is_dissonent as an explicit paratemer/result-element,
    # in x_note_play we have included it as an attribute of the treenodes.

    def dissonant():
        return structure, True, RecursiveHistoryInfo(None, HistoriographyNoteCapo(), [])

    if structure_is_dissonant:
        # perhaps: don't do this inside y_note_play ? i.e. make y_note_play take non-dissonant structures only.
        return dissonant()

    if isinstance(note, BecomeNode):
        if structure is not None:
            return dissonant()  # "You can only BecomeNode out of nothingness"

        t2s, s2t = st_become()
        return HistoriographyTreeNode(
            l_become(), l_become(), t2s, s2t), False, RecursiveHistoryInfo(None, HistoriographyNoteCapo(), [])

    if isinstance(note, TextBecome):
        # We're "misreusing" TextBecome here (it serves as the leaf of both TreeNode and HistoriographyTreeNode).
        return TreeText(
            note.unicode_, 'no metadata available'), False, RecursiveHistoryInfo(None, HistoriographyNoteCapo(), [])

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            return dissonant()  # "Out of bounds: %s" % note.index

        historiography_note_nout = HistoriographyNoteSlur(
            SetNoteNoutHash(note.nout_hash),
            HistoriographyNoteNoutHash.for_object(HistoriographyNoteCapo())
        )

        child, child_annotated_hashes = recurse(historiography_note_nout)

        children = l_insert(structure.children, note.index, child)
        historiographies = l_insert(
            structure.historiographies,
            note.index,
            HistoriographyNoteNoutHash.for_object(historiography_note_nout))

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        new_t = len(t2s) - 1

        rhi = RecursiveHistoryInfo(new_t, historiography_note_nout, child_annotated_hashes)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), False, rhi

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Replace the check is "inside bounds"
        return dissonant()  # "Out of bounds: %s" % note.index

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        historiographies = l_delete(structure.historiographies, note.index)

        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)

        return HistoriographyTreeNode(
            children, historiographies, t2s, s2t), False, RecursiveHistoryInfo(None, HistoriographyNoteCapo(), [])

    if isinstance(note, Replace):
        historiography_note_nout = HistoriographyNoteSlur(
            SetNoteNoutHash(note.nout_hash),
            structure.historiographies[note.index]
        )

        child, child_annotated_hashes = recurse(historiography_note_nout)

        children = l_replace(structure.children, note.index, child)
        historiographies = l_replace(
            structure.historiographies,
            note.index,
            HistoriographyNoteNoutHash.for_object(historiography_note_nout))

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)

        rhi = RecursiveHistoryInfo(s2t[note.index], historiography_note_nout, child_annotated_hashes)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), False, rhi

    raise Exception("Unknown Note")


def construct_y(m, stores, historiography_note_nout):
    """
    construct_y constructs a structure that can be used to understand history (e.g. display it in a GUI to humans)

    In particular operates on:
    * The historiography
    * An edge_nout_hash to advance to
    (These 2 parameters are folded into a single historiography_note_nout)

    And it returns:
    * "Per step info": for each step that's required to advance: its hash and recursive information if it exists.
        (this can be used to draw recursive structures without knowledge of which notes have history-information)

    * The HistoriographyTreeNode, advanced to the edge_nout_hash.

    The idea is that `construct_y` can be used in a special way while playing "Replace": by passing in the existing
    historiography of the to-be-replaced node, we can "connect the historiographic dots". (For Insert, and the
    construction of the root node, we simply pass in an empty historiography)

    For any given nout_hash, construct_y recursively constructs a single HistoriographyTreeNode with HistoriographyAt
    information for all descendants. Such a structure is useful if we want to provide insight about which notes from the
    past are sung in alternative histories.

    `construct_y` acts on both the linear historic level, and the historiographic level, but not at the same time. It is
    very important to keep seeing the distinction: [is it desirable to split these 2 levels into 2 functions?]

    1. the constructed steps are is "historiographically aware"
    2. the constructed HistoriographyTreeNode, however, is not. By that we mean that it's constructed for a single
        linear history (NoteNout level). Collary: the treenode is deduced fully from the last nout_hash, ignoring
        alternate (dead) histories.

        Of course, we _do_ create (potentially non-linear) historiographies for our children: that's the whole point of
        this excercise.

        As a consequence of this: historiographic information about "dead branches of history" is not available
        anywhere; (while drawing this is not actually problematic, because you'll see the dead parent, which signals
        that no further querying of deadness is required)
    """
    # Reservations about Historiography & HistoriographyTreeNode: are those not over-engineered? As it stands, they're
    # being used only for:
    # * answering the "what's new?" questions.
    # * spacetime mappings
    # Perhapse we can simply use a set of all seen hashes, and a spacetime mapping? TBD...

    # As long as we add historiography_note_nout in chronological order, we never run into problems. This usually
    # happens automatically (to be able to point to a preceding nout hash, you'll have to thave seen it first)... but
    # I'd still like to somehow make that more explicit to get better correctness guarantees.
    historiography_note_nout_hash = stores.historiography_note_nout.add(historiography_note_nout)
    if historiography_note_nout_hash in m.construct_y:
        return m.construct_y[historiography_note_nout_hash]

    historiography_at = construct_historiography(m, stores, historiography_note_nout_hash)

    def recurse(historiography_note_nout):
        return construct_y(m, stores, historiography_note_nout)

    whats_new_pod = historiography_at.whats_new_pod()
    if whats_new_pod is None:
        # if there's _nothing_ you've seen before, start with an empty structure
        structure, dissonant = None, False
    else:
        # The below is by definition: the POD with "what's new", so you must have seen (and built and stored) it before
        assert whats_new_pod in m.construct_historiography_treenode
        structure, dissonant = m.construct_historiography_treenode[whats_new_pod]

    new_hashes = reversed(list(historiography_at.whats_new()))
    annotated_hashes = []

    for new_hash in new_hashes:
        new_nout = stores.note_nout.get(new_hash)

        structure, dissonant, rhi = y_note_play(stores, new_nout.note, structure, dissonant, recurse)
        m.construct_historiography_treenode[new_hash] = structure, dissonant

        annotated_hashes.append(AnnotatedHash(new_hash, dissonant, rhi))

    m.construct_y[historiography_note_nout_hash] = structure, annotated_hashes
    return structure, annotated_hashes


def construct_y_from_scratch(m, stores, edge_nout_hash):
    """Construct a historiography by jumping, in a single step, to edge_nout_hash."""
    historiography_note_nout = HistoriographyNoteSlur(
        SetNoteNoutHash(edge_nout_hash),
        HistoriographyNoteNoutHash.for_object(HistoriographyNoteCapo())
    )

    return construct_y(m, stores, historiography_note_nout)
