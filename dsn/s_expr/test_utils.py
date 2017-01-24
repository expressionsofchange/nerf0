"""
These are utils for testing (not: the testing of said utils).

If they turn out to be more generally useful, we can always move them elsewhere.

There is no reason for the funny names, other than "obviously similar but distinct".
"""

from dsn.s_expr.clef import Insert, Replace
from dsn.s_expr.utils import nouts_for_notes_da_capo


def iinsert(possible_timelines, index, notes):
    """Returns a hash"""

    assert notes, "You must iinsert at least _something_"

    nhs = nouts_for_notes_da_capo(notes)

    for nh in nhs:
        possible_timelines.add(nh.nout)

    return Insert(index, nh.nout_hash)


def rreplace(possible_timelines, index, notes):
    """Returns a hash"""

    assert notes, "You must rreplace at least _something_"

    nhs = nouts_for_notes_da_capo(notes)

    for nh in nhs:
        possible_timelines.add(nh.nout)

    return Replace(index, nh.nout_hash)
