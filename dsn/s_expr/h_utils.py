from collections import namedtuple

from dsn.s_expr.construct_y import RecursiveHistoryInfo, construct_y
from dsn.historiography.legato import HistoriographyNoteNoutHash


"""
These are the 3 liveness options (they form an enum; but there's no natural modelling for that in Python).

In the context of a particular historiography, you cannot be both deleted and dead at the same time. To be deleted means
to be deleted in the path that leads to the present. To have such a path means you're alive.

Recursively, such things can occur, i.e.:
* a deletion can happen inside a dead branch
* a deletion can happen inside a deletion
* a dead branch can happen inside a deletion
* a dead branch can happen inside a dead branch

However, from the user perspective none of that is very interesting. Most interesting is the point at which the branch
no longer was ALIVE_AND_WELL; the whole branch is then displayed in that color.
"""
ALIVE_AND_WELL = 0
DEAD = 1
DELETED = 2


AnnotatedWLIHash = namedtuple('AnnotatedHash', (
    'hash',
    'dissonant',
    'aliveness',
    'recursive_information',
))


def view_past_from_present(m, stores, historiography_note_nout, present_note_nout_hash):
    """Views the past through the eyes of the present, annotating dead and deleted hashes accordingly.
    view_past_from_present assumes an alive starting-point; use _view_past_from_present_for_aliveness if you're already
    in a dead/deleted state.

    The 2 parameters are interpreted as such:

    * historiography_note_nout: do the calculation for the (singular) last historiographic step (which may be multiple
        steps in history)

    * present_note_nout: "the present", represented as an end-point in history.

    Some thoughts about optimizing this: In general, the current approach (naive caching of previous results) has at
    least some properties of reuse "over time", but we can probably do better.

    Things that are interesting to think about are: can we reuse previous results when the present is updated?  The part
    that already works well is: because we cache, for each subtree, the `present_note_nout_hash` of that subtree, we at
    least don't have to recalculate history for other subtrees, when the history for a certain unrelated subtree is
    updated.

    However, when present_note_nout_hash gets updated in any way whatsover, we currently recalculate all
    live / deleted / dead information about any previous step, even though scenarios are imaginable (and often
    occurring) in which no such recalculations are needed. Example: any linear extension of an endpoint of history has
    the property of not making old stuff either dead or alive.
    """
    # Note: I don't like the asymmetry hash/no hash; I may want to reconsider.

    historiography_note_nout_hash = HistoriographyNoteNoutHash.for_object(historiography_note_nout)

    if (historiography_note_nout_hash, present_note_nout_hash) in m.view_past_from_present:
        return m.view_past_from_present[(historiography_note_nout_hash, present_note_nout_hash)]

    # In the below, past_htn is an unused variable. Although it's tempting to think of it as a good source of
    # information for e.g.  the children's historiography_note_nout parameter, such values are not available granularly
    # enough. Namely: we have a `past_htn` available for each "historiographic step" (call to Historiography.append_x),
    # but in general we're interested in such information for each AnnotatedHash (i.e. for each historic step).

    # The approach of reconstructing the whole past again and again (using construct_y) might seem very inefficient, but
    # because the results are memoized this is in fact not the case.
    past_htn, annotated_hashes = construct_y(m, stores, historiography_note_nout)

    # Note; I don't like using caches for application-logic. "but for now it works"
    present_htn, dissonant_ = m.construct_historiography_treenode[present_note_nout_hash]

    alive_at_my_level = list(stores.note_nout.all_preceding_nout_hashes(present_note_nout_hash))
    result = []

    for ah in annotated_hashes:
        # Note: there is no passing of "dissonant" information to children. In the current version dissonents _never_
        # have children, as is explained in doctests/construct_y:
        # [..] notes that follow a broken action are still converted into steps, but not recursively explored. The
        # reasoning is: after breakage, all bets are off (but you still want to display as much info as possible)

        child_aliveness = aliveness = ALIVE_AND_WELL

        if ah.hash not in alive_at_my_level:
            child_aliveness = aliveness = DEAD

        child_historiography_note_nout = ah.recursive_information.historiography_note_nout

        if ah.recursive_information.t_address is not None:
            if aliveness == ALIVE_AND_WELL:
                child_s_index = present_htn.t2s[ah.recursive_information.t_address]

                if child_s_index is None:
                    child_aliveness = DELETED

                else:
                    child_in_present_historiography_note_nout_hash = present_htn.historiographies[child_s_index]

                    child_in_present_historiography_note_nout = stores.historiography_note_nout.get(
                        child_in_present_historiography_note_nout_hash
                    )

                    child_in_present_nout_hash = child_in_present_historiography_note_nout.note.note_nout_hash

            if child_aliveness != ALIVE_AND_WELL:
                # the child is not ALIVE_AND_WELL, so it has no "present" either; we simply display it broken in the
                # same way as its ancestor.
                recursive_result = _view_past_from_present_for_aliveness(
                    m,
                    stores,
                    child_historiography_note_nout,
                    child_aliveness,
                    )

            else:
                recursive_result = view_past_from_present(
                    m,
                    stores,
                    child_historiography_note_nout,
                    child_in_present_nout_hash,
                    )

        else:
            recursive_result = []

        result.append(AnnotatedWLIHash(
            ah.hash,
            ah.dissonant,
            aliveness,
            RecursiveHistoryInfo(ah.recursive_information.t_address, child_historiography_note_nout, recursive_result)))

    m.view_past_from_present[(historiography_note_nout_hash, present_note_nout_hash)] = result
    return result


def _view_past_from_present_for_aliveness(m, stores, historiography_note_nout, aliveness):
    """From the moment a branch is marked dead/deleted, all its descendants are also dead/deleted.
    The present function simply assings a certain not-aliveness to all nodes in the tree.
    """
    past_htn, annotated_hashes = construct_y(m, stores, historiography_note_nout)

    result = []

    for ah in annotated_hashes:
        child_historiography_note_nout = ah.recursive_information.historiography_note_nout

        if ah.recursive_information.t_address is not None:
            recursive_result = _view_past_from_present_for_aliveness(
                m,
                stores,
                child_historiography_note_nout,
                aliveness,
                )
        else:
            recursive_result = []

        result.append(AnnotatedWLIHash(
            ah.hash,
            ah.dissonant,
            aliveness,
            RecursiveHistoryInfo(ah.recursive_information.t_address, child_historiography_note_nout, recursive_result)))

    return result
