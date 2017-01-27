from spacetime import st_sanity
from itertools import takewhile
from utils import i_flat_zip_longest, pmts


class Historiography(object):
    """
    This module contains several equivalent approaches at dealing with a "Historiography" (for lack of a better word):
    An append-only list of nout-for-note hashes, that may or may not be somehow related.

    Another way of saying this is: it's a mutable (grow only) structure that allows you to keep track of the present,
    assigning a unique consecutive number to each version of the present.

    The need for this concept flows directly from a Clef with an operation Replace(index, any_nout_hash), as opposed to
    only being able to replace with consecutive hashes.

    The idea is: the nout-hashes are often related, and you want to be able to express how that's so.

    >>> from dsn.s_expr.legato import NoteNout, NoteCapo, NoteSlur
    >>> from dsn.s_expr.clef import TextBecome
    >>> from hashstore import HashStore
    >>>
    >>> from historiography import Historiography
    >>>
    >>> possible_timelines = HashStore(NoteNout, NoteCapo, NoteSlur)
    >>>
    >>> capo = NoteCapo()
    >>>
    >>> hash_capo = possible_timelines.add(capo)
    >>>
    >>> hash_a = possible_timelines.add(NoteSlur(TextBecome("a"), hash_capo))
    >>> hash_b = possible_timelines.add(NoteSlur(TextBecome("b"), hash_capo))
    >>> hash_ac = possible_timelines.add(NoteSlur(TextBecome("ac"), hash_a))
    >>> hash_acd = possible_timelines.add(NoteSlur(TextBecome("acd"), hash_ac))
    >>>
    >>> historiography = Historiography(possible_timelines)
    >>> a = historiography.append(hash_a)
    >>> b = historiography.append(hash_b)
    >>> ac = historiography.append(hash_ac)
    >>> acd = historiography.append(hash_acd)
    >>>
    >>> list(historiography.whats_new(a)) == [hash_a]
    True
    >>> historiography.point_of_divergence(a) is None
    True
    >>> list(historiography.whats_made_alive(a)) == [hash_a]
    True
    >>> list(historiography.whats_made_dead(a)) == []
    True
    >>> list(historiography.whats_new(b)) == [hash_b]
    True
    >>> historiography.point_of_divergence(b) is None
    True
    >>> list(historiography.whats_made_alive(b)) == [hash_b]
    True
    >>> list(historiography.whats_made_dead(b)) == [hash_a]
    True
    >>> list(historiography.whats_new(ac)) == [hash_ac]
    True
    >>> # N.B.: pod with _last state_, for which we must go back all the way to the beginning
    >>> historiography.point_of_divergence(ac) is None
    True
    >>> list(historiography.whats_made_alive(ac)) == [hash_ac, hash_a]
    True
    >>> list(historiography.whats_made_dead(ac)) == [hash_b]
    True
    >>> historiography.point_of_divergence(acd) == hash_ac
    True
    """

    def __init__(self, possible_timelines):
        self.possible_timelines = possible_timelines

        # `set_values` model the consecutive "states" of the Historiography.
        self.set_values = []

        # self.all_nouts & self.prev_seen_in_all_nouts are the internal bookkeeping structures.
        self.all_nouts = set([])
        self.prev_seen_in_all_nouts = []

        self.length = 0

        # When using Historiography to model a single historiography, a single grow-only datastructure is a nice
        # optimization: the objects produced by x_append are not affected by further append-actions.

        # Of course, Historiography is not always used to model a single historiography (especially now that we cache
        # multiple ones in a results_lookup)

        # I'm unwilling to let go of the optimization (I think it provides a nice hint on how to go forward) so I'm
        # leaving it in, but with the cludge "self.x_appended" which copies if x_append has already been called once.
        self.x_appended = False

    def x_append(self, nout_hash):
        if self.x_appended:
            use = Historiography(self.possible_timelines)
            use.set_values = self.set_values[:]
            use.all_nouts = self.all_nouts.copy()
            use.prev_seen_in_all_nouts = self.prev_seen_in_all_nouts[:]
            use.length = self.length
        else:
            self.x_appended = True
            use = self

        index = use.append(nout_hash)
        return HistoriographyAt(use, index)

    def append(self, nout_hash):
        self.set_values.append(nout_hash)

        prev_seen_in_all_nouts = None

        for nout_hash in self.possible_timelines.all_preceding_nout_hashes(nout_hash):
            if nout_hash in self.all_nouts:
                prev_seen_in_all_nouts = nout_hash
                break

            self.all_nouts.add(nout_hash)

        self.prev_seen_in_all_nouts.append(prev_seen_in_all_nouts)

        self.length += 1
        return self.length - 1

    def whats_new_pod(self, index):
        """what's the point of divergence with whats_new, i.e. what's the last thing you already saw?"""
        if index == 0:
            return None  # special value, indicating "nothing was seen before"

        return self.prev_seen_in_all_nouts[index]  # either a nout_hash, or None

    def whats_new(self, index):
        """in anti-chronological order"""
        return takewhile(
            lambda v: v != self.prev_seen_in_all_nouts[index],
            self.possible_timelines.all_preceding_nout_hashes(self.set_values[index]))

    def point_of_divergence(self, index):
        """Going back in time, what's the first nout_hash you already saw before?"""
        if index == 0:
            return None

        return find_point_of_divergence(
            self.possible_timelines.all_preceding_nout_hashes(self.set_values[index]),
            self.possible_timelines.all_preceding_nout_hashes(self.set_values[index - 1]))

    def whats_made_alive(self, index):
        """in anti-chronological order"""
        if index == 0:
            return self.whats_new(index)

        pod = self.point_of_divergence(index)
        return takewhile(
            lambda v: v != pod,
            self.possible_timelines.all_preceding_nout_hashes(self.set_values[index]))

    def whats_made_dead(self, index):
        if index == 0:
            return iter([])

        pod = self.point_of_divergence(index)
        return takewhile(
            lambda v: v != pod,
            self.possible_timelines.all_preceding_nout_hashes(self.set_values[index - 1]))


class HistoriographyAt(object):
    """Represents a particular point in time in the Historiography's life"""

    def __init__(self, historiography, index):
        pmts(index, int)
        self.historiography = historiography
        self.index = index

    def nout_hash(self):
        return self.historiography.set_values[self.index]

    def whats_new_pod(self):
        return self.historiography.whats_new_pod(self.index)

    def whats_new(self):
        return self.historiography.whats_new(self.index)

    def point_of_divergence(self):
        return self.historiography.point_of_divergence(self.index)

    def whats_made_alive(self):
        return self.historiography.made_alive(self.index)

    def whats_made_dead(self):
        return self.historiography.made_dead(self.index)


def find_point_of_divergence(history_a, history_b):
    seen = set([])

    for nout_hash in i_flat_zip_longest(history_a, history_b):
        if nout_hash in seen:
            return nout_hash
        seen.add(nout_hash)

    return None


class HistoriographyTreeNode(object):

    def __init__(self, children, historiographies, t2s, s2t):
        st_sanity(t2s, s2t)
        self.children = children
        self.historiographies = historiographies
        self.t2s = t2s
        self.s2t = s2t

    def __repr__(self):
        return "YATN"


def t_lookup(htn, t_path):
    if t_path == []:
        return htn

    s_addr = htn.t2s[t_path[0]]
    if s_addr is None:
        return None

    result = t_lookup(htn.children[s_addr], t_path[1:])
    return result
