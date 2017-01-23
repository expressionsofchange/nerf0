from hashstore import Hash
from legato import all_nhtups_for_nout_hash, NoutCapo
from posacts import Possibility, Actuality
from s_address import node_for_s_address

from dsn.s_expr.legato import NoutSlur
from dsn.s_expr.clef import (
    BecomeNode,
    Insert,
    Replace,
    TextBecome,
)


def calc_possibility(nout):
    # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
    # copy/pasted from the HashStore implementation; but we need it here again.

    bytes_ = nout.as_bytes()
    hash_ = Hash.for_bytes(bytes_)
    return Possibility(nout), hash_


def calc_actuality(nout_hash):
    return Actuality(nout_hash)


def some_cut_paste(possible_timelines, edge_nout_hash, cut_nout_hash, paste_point_hash):
    """Detaches the cut_nout from its parent, pasting the stuff from edge_nout_hash back to cut_nout onto the
    past_point. Returns chronological Notes."""

    todo = []
    for nh in all_nhtups_for_nout_hash(possible_timelines, edge_nout_hash):
        # potentially deal with edge cases (e.g. cut_nout_hash not in history) here.
        todo.append(nh)
        if nh.nout_hash == cut_nout_hash:
            break

    prev = paste_point_hash
    for nh in reversed(todo):
        nout = NoutSlur(nh.nout.note, prev)
        possibility, prev = calc_possibility(nout)
        yield possibility  # or: possibility.nout


def some_more_cut_paste(possible_timelines, edge_nout_hash, cut_nout_hash, paste_point_hash):
    """
    interpretation of cut_nout_hash is purely driven by how this is used in practice... do I like it? Not sure yet.

    the interpretation is:
    cut_nout_hash is the first thing that's _not_ included.
    """

    todo = []
    for nh in all_nhtups_for_nout_hash(possible_timelines, edge_nout_hash):
        # potentially deal with edge cases (e.g. cut_nout_hash not in history) here.
        if nh.nout_hash == cut_nout_hash:
            break

        todo.append(nh)

    prev = paste_point_hash
    for nh in reversed(todo):
        nout = NoutSlur(nh.nout.note, prev)
        possibility, prev = calc_possibility(nout)
        yield possibility  # or: possibility.nout


def bubble_history_up(hash_to_bubble, tree, s_address):
    """Recursively replace history to reflect a change (hash_to_bubble) at a lower level (s_address)"""

    posacts = []
    for i in reversed(range(len(s_address))):
        # We slide a window of size 2 over the s_address from right to left, like so:
        # [..., ..., ..., ..., ..., ..., ...]  <- s_address
        #                              ^  ^
        #                           [:i]  i
        # For each such i, the sliced array s_address[:i] gives you the s_address of a node in which a replacement
        # takes place, and s_address[i] gives you the index to replace at.
        #
        # Regarding the range (0, len(s_address)) the following:
        # * len(s_address) means the s_address itself is the first thing to be replaced.
        # * 0 means: the last replacement is _inside_ the root node (s_address=[]), at index s_address[0]
        replace_in = node_for_s_address(tree, s_address[:i])

        p, hash_to_bubble = calc_possibility(
            NoutSlur(Replace(s_address[i], hash_to_bubble), replace_in.metadata.nout_hash))

        posacts.append(p)

    # The root node (s_address=[]) itself cannot be replaced, its replacement is represented as "Actuality updated"
    posacts.append(calc_actuality(hash_to_bubble))
    return posacts


# TODO: insert_xxx_at: I see a pattern here!
def insert_text_at(tree, parent_s_address, index, text):
    parent_node = node_for_s_address(tree, parent_s_address)

    pa0, begin = calc_possibility(NoutCapo())
    pa1, to_be_inserted = calc_possibility(NoutSlur(TextBecome(text), begin))

    pa2, insertion = calc_possibility(
        NoutSlur(Insert(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, parent_s_address)
    return [pa0, pa1, pa2] + posacts


def insert_node_at(tree, parent_s_address, index):
    parent_node = node_for_s_address(tree, parent_s_address)

    pa0, begin = calc_possibility(NoutCapo())
    pa1, to_be_inserted = calc_possibility(NoutSlur(BecomeNode(), begin))

    pa2, insertion = calc_possibility(
        NoutSlur(Insert(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, parent_s_address)
    return [pa0, pa1, pa2] + posacts


def replace_text_at(tree, s_address, text):
    parent_node = node_for_s_address(tree, s_address[:-1])

    pa0, begin = calc_possibility(NoutCapo())
    pa1, to_be_inserted = calc_possibility(NoutSlur(TextBecome(text), begin))

    index = s_address[-1]

    pa2, insertion = calc_possibility(
        NoutSlur(Replace(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, s_address[:-1])
    return [pa0, pa1, pa2] + posacts
