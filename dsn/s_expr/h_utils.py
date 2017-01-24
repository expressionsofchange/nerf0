from historiography import t_lookup
from legato import all_preceding_nout_hashes


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


def view_past_from_present(possible_timelines, present_root_htn, per_step_info, alive_at_my_level):
    return _view_past_from_present(
        possible_timelines, present_root_htn, ALIVE_AND_WELL, per_step_info, [], alive_at_my_level)


def _view_past_from_present(
        possible_timelines, present_root_htn, p_aliveness, per_step_info, t_path, alive_at_my_level):

    result = []

    for nout_hash, dissonant, (t, children_steps) in per_step_info:
        # Note: there is no passing of "dissonant" information to children. In the current version dissonents _never_
        # have children, as is explained in doctests/construct_y:
        # [..] notes that follow a broken action are still converted into steps, but not recursively explored. The
        # reasoning is: after breakage, all bets are off (but you still want to display as much info as possible)

        child_aliveness = aliveness = p_aliveness

        if aliveness == ALIVE_AND_WELL and nout_hash not in alive_at_my_level:
            child_aliveness = aliveness = DEAD

        if t is not None:
            if aliveness == ALIVE_AND_WELL:
                parent_htn = t_lookup(present_root_htn, t_path)

                child_s_address = parent_htn.t2s[t]
                if child_s_address is None:
                    child_aliveness = DELETED

                else:
                    child_historiography_in_present = parent_htn.historiographies[child_s_address]
                    alive_at_child_level = list(all_preceding_nout_hashes(
                        possible_timelines, child_historiography_in_present.nout_hash()))

            if child_aliveness != ALIVE_AND_WELL:
                alive_at_child_level = "_"

            recursive_result = _view_past_from_present(
                possible_timelines,
                present_root_htn,
                child_aliveness,
                children_steps,
                t_path + [t],
                alive_at_child_level,
                )

        else:
            recursive_result = []

        result.append((nout_hash, dissonant, aliveness, (t, recursive_result)))

    return result
