from trees import TreeText
from historiography import Historiograhpy, YetAnotherTreeNode

from clef import BecomeNode, TextBecome, Insert, Replace, Delete
from spacetime import st_become, st_insert, st_replace, st_delete
from collections import namedtuple


# A tuple containing information about histories at a lower level
RecursiveHistoryInfo = namedtuple('RecursiveHistory', (
    't_address',  # the history at the lower level takes place at a certain t_address
    'children_steps'))


def y_note_play(possible_timelines, structure, note, recurse):
    # whether we do hash-to-note here or below is of less importance

    if isinstance(note, BecomeNode):
        t2s, s2t = st_become()
        return YetAnotherTreeNode([], [], t2s, s2t), None

    if isinstance(note, Insert):
        empty_structure = None
        empty_historiography = Historiograhpy(possible_timelines)

        child, child_historiography_at, child_per_step_info = recurse(empty_structure, empty_historiography, note.nout_hash)

        children = structure.children[:]
        children.insert(note.index, child)

        historiographies = structure.historiographies[:]
        historiographies.insert(note.index, child_historiography_at)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        new_t = len(t2s) - 1

        rhi = RecursiveHistoryInfo(new_t, child_per_step_info)

        return YetAnotherTreeNode(children, historiographies, t2s, s2t), rhi

    if isinstance(note, Delete):
        children = structure.children[:]
        del children[note.index]

        historiographies = structure.historiographies[:]
        del historiographies[note.index]

        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)

        return YetAnotherTreeNode(children, historiographies, t2s, s2t), None

    if isinstance(note, Replace):
        existing_structure = structure.children[note.index]
        existing_historiography = structure.historiographies[note.index].historiography

        child, child_historiography_at, child_per_step_info = recurse(existing_structure, existing_historiography, note.nout_hash)

        children = structure.children[:]
        historiographies = structure.historiographies[:]

        children[note.index] = child
        historiographies[note.index] = child_historiography_at

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)

        rhi = RecursiveHistoryInfo(s2t[note.index], child_per_step_info)

        return YetAnotherTreeNode(children, historiographies, t2s, s2t), rhi

    if isinstance(note, TextBecome):
        return TreeText(note.unicode_, 'no metadata available'), None

    raise Exception("Unknown Note")


def construct_y(possible_timelines, existing_structure, existing_historiography, edge_nout_hash):
    def recurse(s, h, enh):
        return construct_y(possible_timelines, s, h, enh)

    historiography_at = existing_historiography.x_append(edge_nout_hash)

    new_hashes = reversed(list(historiography_at.whats_new()))
    per_step_info = []

    for new_hash in new_hashes:
        new_nout = possible_timelines.get(new_hash)

        existing_structure, rhi = y_note_play(possible_timelines, existing_structure, new_nout.note, recurse)
        per_step_info.append((new_hash, rhi))

    return existing_structure, historiography_at, per_step_info


def xxx_construct_y(possible_timelines, edge_nout_hash):
    return construct_y(possible_timelines, None, Historiograhpy(possible_timelines), edge_nout_hash)
