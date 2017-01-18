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


def y_note_play(note, structure, recurse, possible_timelines):
    if isinstance(note, BecomeNode):
        t2s, s2t = st_become()
        return HistoriographyTreeNode(l_become(), l_become(), t2s, s2t), None

    if isinstance(note, Insert):
        empty_structure, empty_historiography = y_origin(possible_timelines)

        child, child_historiography_at, child_per_step_info = recurse(
            empty_structure, empty_historiography, note.nout_hash)

        children = l_insert(structure.children, note.index, child)
        historiographies = l_insert(structure.historiographies, note.index, child_historiography_at)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        new_t = len(t2s) - 1

        rhi = RecursiveHistoryInfo(new_t, child_per_step_info)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), rhi

    if isinstance(note, Delete):
        children = l_delete(structure.children, note.index)
        historiographies = l_delete(structure.historiographies, note.index)

        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), None

    if isinstance(note, Replace):
        existing_structure = structure.children[note.index]
        existing_historiography = structure.historiographies[note.index].historiography

        child, child_historiography_at, child_per_step_info = recurse(
            existing_structure, existing_historiography, note.nout_hash)

        children = l_replace(structure.children, note.index, child)
        historiographies = l_replace(structure.historiographies, note.index, child_historiography_at)

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)

        rhi = RecursiveHistoryInfo(s2t[note.index], child_per_step_info)

        return HistoriographyTreeNode(children, historiographies, t2s, s2t), rhi

    if isinstance(note, TextBecome):
        # We're "misreusing" TextBecome here (it serves as the leaf of both TreeNode and HistoriographyTreeNode).
        return TreeText(note.unicode_, 'no metadata available'), None

    raise Exception("Unknown Note")


def construct_y(possible_timelines, structure, historiography, edge_nout_hash):
    """
    construct_y constructs a structure that can be used to understand history (e.g. display it in a GUI to humans)

    In particular, it takes:
    * A HistoriographyTreeNode
    * The historiography [mutable! insert notes about "use once"] TODO
    * An edge_nout_hash to advance to

    And it returns:
    * The HistoriographyTreeNode, advanced to the edge_nout_hash.
    * The HistoriographyAt after advancing to the edge_nout_hash.
    * "Per step info": for each step that's required to advance: its hash and recursive information if it exists.
        (this can be used to draw recursive structures without knowledge of which notes have history-information)

    The idea is that `construct_y` can be used in a special way while playing "Replace": by passing in the existing
    structure and historiography of the to-be-replaced node, we can "connect the historiographic dots". (For Insert,
    and the construction of the root node, we simply pass in an empty structure and historiography)

    For any given nout_hash, construct_y recursively constructs a single HistoriographyTreeNode with HistoriographyAt
    information for all descendants. Such a structure is useful if we want to provide insight about which notes from the
    past are sung in alternative histories.
    """

    def recurse(s, h, enh):
        return construct_y(possible_timelines, s, h, enh)

    historiography_at = historiography.x_append(edge_nout_hash)

    new_hashes = reversed(list(historiography_at.whats_new()))
    per_step_info = []

    for new_hash in new_hashes:
        new_nout = possible_timelines.get(new_hash)

        structure, rhi = y_note_play(new_nout.note, structure, recurse, possible_timelines)
        per_step_info.append((new_hash, rhi))

    return structure, historiography_at, per_step_info


def y_origin(possible_timelines):
    """We start `y` actions with no structure, and an empty historiography."""
    return None, Historiography(possible_timelines)


def construct_y_from_scratch(possible_timelines, edge_nout_hash):
    structure, historiography = y_origin(possible_timelines)
    return construct_y(possible_timelines, structure, historiography, edge_nout_hash)
