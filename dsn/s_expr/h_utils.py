from collections import namedtuple

from historiography import t_lookup
from dsn.s_expr.construct_y import RecursiveHistoryInfo


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


def view_past_from_present(m, stores, present_root_htn, annotated_hashes, alive_at_my_level):
    return _view_past_from_present(m, stores, present_root_htn, ALIVE_AND_WELL, annotated_hashes, [], alive_at_my_level)


def _view_past_from_present(m, stores, present_root_htn, p_aliveness, annotated_hashes, t_path, alive_at_my_level):
    result = []

    for nout_hash, dissonant, recursive_information in annotated_hashes:
        # Note: there is no passing of "dissonant" information to children. In the current version dissonents _never_
        # have children, as is explained in doctests/construct_y:
        # [..] notes that follow a broken action are still converted into steps, but not recursively explored. The
        # reasoning is: after breakage, all bets are off (but you still want to display as much info as possible)

        child_aliveness = aliveness = p_aliveness

        if aliveness == ALIVE_AND_WELL and nout_hash not in alive_at_my_level:
            child_aliveness = aliveness = DEAD

        if recursive_information.t_address is not None:
            if aliveness == ALIVE_AND_WELL:
                parent_htn = t_lookup(present_root_htn, t_path)

                child_s_address = parent_htn.t2s[recursive_information.t_address]
                if child_s_address is None:
                    child_aliveness = DELETED

                else:
                    child_historiography_in_present_something = parent_htn.historiographies[child_s_address]

                    historiography_note_nout = stores.historiography_note_nout.get(
                        child_historiography_in_present_something
                    )

                    alive_at_child_level = list(stores.note_nout.all_preceding_nout_hashes(
                        historiography_note_nout.note.note_nout_hash))

            if child_aliveness != ALIVE_AND_WELL:
                alive_at_child_level = "_"

            recursive_result = _view_past_from_present(
                m,
                stores,
                present_root_htn,
                child_aliveness,
                recursive_information.children_steps,
                t_path + [recursive_information.t_address],
                alive_at_child_level,
                )

        else:
            recursive_result = []

        result.append(AnnotatedWLIHash(
            nout_hash, dissonant, aliveness, RecursiveHistoryInfo(recursive_information.t_address, recursive_result)))

    return result
