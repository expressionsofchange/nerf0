from hashstore import Hash
from posacts import Possibility
from legato import all_nhtups_for_nout_hash

from dsn.s_expr.legato import NoutSlur


def calc_possibility(nout):
    # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
    # copy/pasted from the HashStore implementation; but we need it here again.

    bytes_ = nout.as_bytes()
    hash_ = Hash.for_bytes(bytes_)
    return Possibility(nout), hash_


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
