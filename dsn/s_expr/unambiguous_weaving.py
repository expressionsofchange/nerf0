"""
unambiguous_weaving provides various tools to "weave together" (aka merge, aka relinearize) 2 separate histories, if
this is possible to do in an unambiguous way.
"""

from posacts import Actuality
from collections import namedtuple
from itertools import takewhile

from dsn.s_expr.construct_x import construct_x
from dsn.s_expr.clef import Insert, Delete, Replace
from dsn.s_expr.legato import NoteSlur
from dsn.s_expr.utils import calc_possibility


RelevantTAddresses = namedtuple('RelevantTAddresses', (
    'insertion_edges',
    'deletions',
    'replacements',
    ))


def collect_t_addresses(m, stores, tree, note_nout_hashes):
    insertion_edges = []
    deletions = []
    replacements = []

    for note_nout_hash in note_nout_hashes:
        note = stores.note_nout.get(note_nout_hash).note

        if isinstance(note, Insert):
            # An Insert happens between the point of insertion and the item to the left of it:
            left = 'begin' if note.index == 0 else tree.s2t[note.index - 1]
            right = 'end' if note.index == len(tree.s2t) else tree.s2t[note.index]

            insertion_edges.append((left, right))

        elif isinstance(note, Delete):
            deletions.append(tree.s2t[note.index])

        elif isinstance(note, Replace):
            replacements.append(tree.s2t[note.index])

        else:
            # Note: "Become*" is not to be expected: you can only become once at the beginning, which means that
            # Becoming cannot happen in divergent histories.
            # TODO: check whether this is still the case once we implement the recursive version w/ Replace
            raise Exception("Unexpected note: %s" % type(note))

        # we look at the pre-note_play tree for our addressess (in particular required to be able to deal with Delete);
        # hence we fetch tree at the end of the loop.
        tree = construct_x(m, stores, note_nout_hash)

    return RelevantTAddresses(insertion_edges, deletions, replacements)


def hashes_between(stores, new_hash, older_hash_not_included):
    return reversed(list(takewhile(
        lambda v: v != older_hash_not_included,
        stores.note_nout.all_preceding_nout_hashes(new_hash))))


def is_valid_double_edge(m, stores, pod, nout_hash_0, nout_hash_1):
    # TODO the copy/pasta with the main function `uw_double_edge`; I should find something for that.

    problems = set()

    tree_at_pod = construct_x(m, stores, pod)

    # max_t_at_pod is relevant, because anything happening at or in relation to a t_address greater than it is unique to
    # that timeline by definition, and hence never causes a collision.
    max_t_at_pod = len(tree_at_pod.t2s) - 1

    timeline_0 = list(hashes_between(stores, nout_hash_0, pod))
    timeline_1 = list(hashes_between(stores, nout_hash_1, pod))

    c0 = collect_t_addresses(m, stores, tree_at_pod, timeline_0)
    c1 = collect_t_addresses(m, stores, tree_at_pod, timeline_1)

    for one, other in [(c0, c1), (c1, c0)]:
        for left, right in one.insertion_edges:
            if left in ['begin', 'end'] or left <= max_t_at_pod:
                if left in other.deletions:
                    problems.add("Left edge w/ t_address=%s was deleted in the other history" % left)

                if left in [l for (l, r) in other.insertion_edges]:
                    problems.add("Left-edge w/ t_address=%s is used in both histories" % left)

            if right in ['begin', 'end'] or right <= max_t_at_pod:
                if right in other.deletions:
                    problems.add("Right edge w/ t_address=%s was deleted in the other history" % right)

                if right in [r for (l, r) in other.insertion_edges]:
                    problems.add("Right edge w/ t_address=%s is used in both histories" % right)

    if problems:
        return False, ", ".join(sorted(problems))

    return True, ""


def uw_double_edge(m, stores, pod, nout_hash_0, nout_hash_1, ordering_mechanism):
    """Unabiguous weaving ("uw"), where the insert operations must have 2 "edges" (points of reference) that are either
    uniquely used as left/right edge in their history or were already in the joint (pre-'branch') history, and insertion
    edges are never deleted in the other history.

    Deletions must also be unique across the 2 timelines.

    This is a generator that yields posacts:

    * Any yielded Possibilities must be made known to the note_nout store immediately, the algorithm depends on any
        announced possibility to later be available for getting.
    * A final Actuality represents the weaved endpoint.

    The pod (point of divergence) is explicitly passed, rather than calculated. This is the more general solution,
    because it allows us to handle the scenario where 2 actors act upon a history independently, but happen to act on
    the history in the same way, in an explicit manner (the manner happens to be: such histories cannot be unambiguously
    woven together, i.e. an exception).

    If you want to automatically determine the pod, you may do this as such:

    ```
    from historiography import find_point_of_divergence
    pod = find_point_of_divergence(
        stores.note_nout.all_preceding_nout_hashes(nout_hash_0),
        stores.note_nout.all_preceding_nout_hashes(nout_hash_1),
        )
    ```

    An `ordering_mechanism` is passed as a list of 0's and 1's, denoting the picking order of the final relinearization.
    It must contain as many 0's as there are nouts between nout_hash_0 and the pod, and similarly for 1's.

    (The picking order must be explict: precisly because weaving is unambiguously possible with the same same result for
    any picking order, any picking order is fine, but any picking order will still give a distinct result.)
    """

    # NOTE: we don't check whether pod is actually in both histories (yet?)

    tree_at_pod = construct_x(m, stores, pod)

    # max_t_at_pod is relevant, because anything happening at or in relation to a t_address greater than it is unique to
    # that timeline by definition, and hence never causes a collision.
    max_t_at_pod = len(tree_at_pod.t2s) - 1

    timeline_0 = list(hashes_between(stores, nout_hash_0, pod))
    timeline_1 = list(hashes_between(stores, nout_hash_1, pod))

    ok, msg = is_valid_double_edge(m, stores, pod, nout_hash_0, nout_hash_1)
    if not ok:
        raise Exception(msg)

    assert len(timeline_0) == len([x for x in ordering_mechanism if x == 0])
    assert len(timeline_1) == len([x for x in ordering_mechanism if x == 1])

    i_timeline_0 = iter(timeline_0)
    i_timeline_1 = iter(timeline_1)

    # Any t_address that precedes the divergence of histories can be mapped to itself
    t0_to_t_in_joint_history = {t: t for t in range(max_t_at_pod + 1)}
    t1_to_t_in_joint_history = {t: t for t in range(max_t_at_pod + 1)}

    tree_0, tree_1, joint_tree = tree_at_pod, tree_at_pod, tree_at_pod

    joint_note_nout_hash = pod

    for which_timeline in ordering_mechanism:
        timeline = (i_timeline_0, i_timeline_1)[which_timeline]
        tree = (tree_0, tree_1)[which_timeline]
        t_in_joint_history = (t0_to_t_in_joint_history, t1_to_t_in_joint_history)[which_timeline]
        note_nout_hash = next(timeline)

        note = stores.note_nout.get(note_nout_hash).note

        if isinstance(note, Insert):
            # The general idea for mapping insertions to the joint history is: in the separate timeline find the 2
            # reference edges as t_addresses, look up the associated t_addresses in the joint history and map back to
            # space. 'begin' and 'end' are special cases: they simply map directly to space in the target (by looking at
            # the target's length)

            # Note that there is some duplication in the below with the validation mechanism; we might factor it out.

            source_left = 'begin' if note.index == 0 else tree.s2t[note.index - 1]
            source_right = 'end' if note.index == len(tree.s2t) else tree.s2t[note.index]

            if source_left == 'begin':
                target_left_s = -1  # i.e. just left of the insertion-point 0
            else:
                target_left_s = joint_tree.t2s[t_in_joint_history[source_left]]

            if source_right == 'end':
                target_right_s = len(joint_tree.children)  # i.e. just right of the last existing index, "appending"
            else:
                target_right_s = joint_tree.t2s[t_in_joint_history[source_right]]

            # The mapped targets in space are consecutive. This is always so because of the rather strict validations
            # above (a formal proof is left as an excercise to the reader)
            assert target_left_s == target_right_s - 1

            # The right edge is the insertion point (this flows from the used definition of insertion, which is "insert
            # before"). Note that this matches with using `-1` and `len(...)` in the above for 'begin' and 'end'.
            joint_note = Insert(target_right_s, note.nout_hash)

            # We update the mapping to reflect where the insertion ends up in the joint history. len(t2s), before
            # updating the tree, is a shorthand for "what t_address will be used next?"
            t_in_joint_history[len(tree.t2s)] = len(joint_tree.t2s)

        elif isinstance(note, Delete):
            # Simply look up the t_address in the mapping, and the s_address for that t_address. Rewrite as such.
            # That this will "just work" follows directly from the fact that deletions occur on one side of the history
            # only due to the checks above.
            joint_note = Delete(joint_tree.t2s[t_in_joint_history[tree.s2t[note.index]]])

        elif isinstance(note, Replace):
            raise NotImplemented()  # TODO

        # Advance the relevant tree with the loop.
        if which_timeline == 0:
            tree_0 = construct_x(m, stores, note_nout_hash)
        else:
            tree_1 = construct_x(m, stores, note_nout_hash)

        joint_note_nout = NoteSlur(joint_note, joint_note_nout_hash)
        possibility, joint_note_nout_hash = calc_possibility(joint_note_nout)

        # As noted above: the yielded possibility must be added to the stores by the user of this function; which allows
        # us to call construct in the next line.
        yield possibility
        joint_tree = construct_x(m, stores, joint_note_nout_hash)

    yield Actuality(joint_note_nout_hash)
