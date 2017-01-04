from trees import TreeText
from historiography import Historiograhpy, YetAnotherTreeNode

from clef import BecomeNode, TextBecome, Insert, Replace, Delete
from legato import NoutBegin
from spacetime import st_become, st_insert, st_replace, st_delete


def y_note_play(possible_timelines, structure, note, recurse):
    # whether we do hash-to-note here or below is of less importance

    if isinstance(note, BecomeNode):
        t2s, s2t = st_become()
        return YetAnotherTreeNode([], [], t2s, s2t), None

    if isinstance(note, Insert):
        empty_structure = "Nothing"  # unused variable b/c Begin is never reached.
        empty_historiography = Historiograhpy(possible_timelines)

        child, child_historiography, xxx_b = recurse(empty_structure, empty_historiography, note.nout_hash)

        children = structure.children[:]
        children.insert(note.index, child)

        historiography = structure.historiographies[:]
        historiography.insert(note.index, child_historiography)

        t2s, s2t = st_insert(structure.t2s, structure.s2t, note.index)
        new_t = len(t2s) - 1

        return YetAnotherTreeNode(children, historiography, t2s, s2t), (new_t, child_historiography.top, xxx_b)

    if isinstance(note, Delete):
        children = structure.children[:]
        del children[note.index]

        historiography = structure.historiographies[:]
        del historiography[note.index]

        t2s, s2t = st_delete(structure.t2s, structure.s2t, note.index)

        return YetAnotherTreeNode(children, historiography, t2s, s2t), None

    if isinstance(note, Replace):
        existing_structure = structure.children[note.index]
        existing_historiography = structure.historiographies[note.index]

        child, child_historiography, xxx_b = recurse(existing_structure, existing_historiography, note.nout_hash)

        children = structure.children[:]
        historiographies = structure.historiographies[:]

        children[note.index] = child
        historiographies[note.index] = child_historiography

        t2s, s2t = st_replace(structure.t2s, structure.s2t, note.index)

        xxx = (s2t[note.index], child_historiography.top, xxx_b)
        return YetAnotherTreeNode(children, historiographies, t2s, s2t), xxx

    if isinstance(note, TextBecome):
        return TreeText(note.unicode_, 'no metadata available'), None

    raise Exception("Unknown Note")


def construct_y(possible_timelines, existing_structure, existing_h2, edge_nout_hash):
    def recurse(s, h, enh):
        return construct_y(possible_timelines, s, h, enh)

    existing_h2 = existing_h2.append(edge_nout_hash)

    new_hashes = existing_h2.whats_new()
    xxx_b = []

    for new_hash in new_hashes:
        new_nout = possible_timelines.get(new_hash)
        if new_nout == NoutBegin():
            # this assymmetry is present elsewhere too... up for consideration
            continue

        # Note: y_note_play does _not_ operate on historiographies; it only knows about them in the sense that it
        # calls construct_y using the already-present historiography for the Replace note.
        existing_structure, xxx = y_note_play(possible_timelines, existing_structure, new_nout.note, recurse)
        xxx_b.append((new_hash, xxx))

    return existing_structure, existing_h2, xxx_b


def xxx_construct_y(possible_timelines, edge_nout_hash):
    return construct_y(possible_timelines, "ignored... b/c begi", Historiograhpy(possible_timelines), edge_nout_hash)
