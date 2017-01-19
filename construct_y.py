from trees import TreeText
from historiography import Historiography, HistoriographyTreeNode

from clef import BecomeNode, TextBecome, Insert, Replace, Delete
from spacetime import st_become, st_insert, st_replace, st_delete
from collections import namedtuple
from list_operations import l_become, l_insert, l_delete, l_replace


# A tuple containing information about histories at a lower level
RecursiveHistoryInfo = namedtuple('RecursiveHistory', (
    't_address',  # the history at the lower level takes place at a certain t_address
    'children_steps'))


def y_note_play(note, structure, structure_is_dissonant, recurse, possible_timelines):
    def dissonant():
        return structure, True, None

    if structure_is_dissonant:
        # perhaps: don't do this inside y_note_play ? i.e. make y_note_play take non-dissonant structures only.
        return dissonant()

    if isinstance(note, BecomeNode):
        if structure is not None:
            return dissonant()  # "You can only BecomeNode out of nothingness"

        t2s, s2t = st_become()
        return HistoriographyTreeNode(l_become(), l_become(), t2s, s2t), False, None

    if isinstance(note, TextBecome):
        # We're "misreusing" TextBecome here (it serves as the leaf of both TreeNode and HistoriographyTreeNode).
        return TreeText(note.unicode_, 'no metadata available'), False, None

    if isinstance(note, Insert):
        if not (0 <= note.index <= len(structure.children)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            return dissonant()  # "Out of bounds: %s" % note.index

        empty_historiography = y_origin(possible_timelines)

        child, child_historiography_at, child_per_step_info = recurse(
            empty_historiography, note.nout_hash)

        children = l_insert(structure.children, note.index, child)
        historiographies = l_insert(structure.historiographies, note.index, child_historiography_at)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        new_t = len(t2s) - 1

        rhi = RecursiveHistoryInfo(new_t, child_per_step_info)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), False, rhi

    if not (0 <= note.index <= len(structure.children) - 1):  # For Delete/Replace the check is "inside bounds"
        return dissonant()  # "Out of bounds: %s" % note.index

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        historiographies = l_delete(structure.historiographies, note.index)

        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), False, None

    if isinstance(note, Replace):
        existing_historiography = structure.historiographies[note.index].historiography

        child, child_historiography_at, child_per_step_info = recurse(
            existing_historiography, note.nout_hash)

        children = l_replace(structure.children, note.index, child)
        historiographies = l_replace(structure.historiographies, note.index, child_historiography_at)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)

        rhi = RecursiveHistoryInfo(s2t[note.index], child_per_step_info)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), False, rhi

    raise Exception("Unknown Note")


def construct_y(tree_lookup, possible_timelines, historiography, edge_nout_hash):
    """
    construct_y constructs a structure that can be used to understand history (e.g. display it in a GUI to humans)

    In particular, it takes:
    * The historiography
    * An edge_nout_hash to advance to

    And it returns:
    * "Per step info": for each step that's required to advance: its hash and recursive information if it exists.
        (this can be used to draw recursive structures without knowledge of which notes have history-information)

    * The HistoriographyTreeNode, advanced to the edge_nout_hash.
    * The HistoriographyAt after advancing to the edge_nout_hash.

    The idea is that `construct_y` can be used in a special way while playing "Replace": by passing in the existing
    historiography of the to-be-replaced node, we can "connect the historiographic dots". (For Insert, and the
    construction of the root node, we simply pass in an empty historiography)

    For any given nout_hash, construct_y recursively constructs a single HistoriographyTreeNode with HistoriographyAt
    information for all descendants. Such a structure is useful if we want to provide insight about which notes from the
    past are sung in alternative histories.

    `construct_y` acts on both the linear historic level, and the historiographic level, but not at the same time. It is
    very important to keep seeing the distinction: [is it desirable to split these 2 levels into 2 functions?]

    1. the constructed Historiography is "historiographically aware" (how could it not be?)
    2. the constructed HistoriographyTreeNode, however, is not. By that we mean that it's constructed for a single
        linear history. Collary: the parameter `historiography` is not used to construct the treenode (the treenode is
        deduced fully from the last nout_hash, ignoring alternate (dead) histories.

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

    def recurse(h, enh):
        return construct_y(tree_lookup, possible_timelines, h, enh)

    historiography_at = historiography.x_append(edge_nout_hash)

    whats_new_pod = historiography_at.whats_new_pod()
    if whats_new_pod is None:
        # if there's _nothing_ you've seen before, start with an empty structure
        structure, dissonant = None, False
    else:
        # The below is by definition: the POD with "what's new", so you must have seen (and built and stored) it before
        assert whats_new_pod in tree_lookup
        structure, dissonant = tree_lookup[whats_new_pod]

    new_hashes = reversed(list(historiography_at.whats_new()))
    per_step_info = []

    for new_hash in new_hashes:
        new_nout = possible_timelines.get(new_hash)

        structure, dissonant, rhi = y_note_play(new_nout.note, structure, dissonant, recurse, possible_timelines)
        tree_lookup[new_hash] = structure, dissonant

        per_step_info.append((new_hash, dissonant, rhi))

    return structure, historiography_at, per_step_info


def y_origin(possible_timelines):
    return Historiography(possible_timelines)


def construct_y_from_scratch(possible_timelines, edge_nout_hash):
    tree_lookup = {}  # TODO pull the 'tree_lookup' to the calling location for caching between calls

    historiography = y_origin(possible_timelines)
    return construct_y(tree_lookup, possible_timelines, historiography, edge_nout_hash)
