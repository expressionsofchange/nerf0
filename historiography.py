from legato import all_preceding_nout_hashes
from spacetime import st_sanity
from itertools import takewhile
from utils import i_flat_zip_longest, pmts


class Historiography(object):
    """
    This module contains several equivalent approaches at dealing with a "Historiography" (for lack of a better word):
    An append-only list of nout-for-note hashes, that may or may not be somehow related.

    Another way of saying this is: it's a mutable (grow only) structure that allows you to keep track of the present,
    assigning a unique consecutive number to each version of the present.

    The need for this concept flows directly from a Clef with an operation Replace(index, any_nout_hash)

    The idea is: the nout-hashes are often related, and you want to be able to express how that's so.

    >>> from legato import NoutBlock, NoutBegin, parse_nout
    >>> from clef import TextBecome
    >>> from hashstore import HashStore
    >>>
    >>> from historiography import Historiography
    >>>
    >>> possible_timelines = HashStore(parse_nout)
    >>>
    >>> begin = NoutBegin()
    >>>
    >>> hash_begin = possible_timelines.add(begin)
    >>>
    >>> hash_a = possible_timelines.add(NoutBlock(TextBecome("a"), hash_begin))
    >>> hash_b = possible_timelines.add(NoutBlock(TextBecome("b"), hash_begin))
    >>> hash_ac = possible_timelines.add(NoutBlock(TextBecome("ac"), hash_a))
    >>>
    >>> historiography = Historiography(possible_timelines)
    >>> a = historiography.append(hash_a)
    >>> b = historiography.append(hash_b)
    >>> ac = historiography.append(hash_ac)
    >>>
    >>> list(historiography.whats_new(a)) == [hash_a]
    True
    >>> list(historiography.whats_made_alive(a)) == [hash_a]
    True
    >>> list(historiography.whats_made_dead(a)) == []
    True
    >>>
    >>> list(historiography.whats_new(b)) == [hash_b]
    True
    >>> list(historiography.whats_made_alive(b)) == [hash_b]
    True
    >>> list(historiography.whats_made_dead(b)) == [hash_a]
    True
    >>>
    >>> list(historiography.whats_new(ac)) == [hash_ac]
    True
    >>> list(historiography.whats_made_alive(ac)) == [hash_ac, hash_a]
    True
    >>> list(historiography.whats_made_dead(ac)) == [hash_b]
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

    def x_append(self, nout_hash):
        index = self.append(nout_hash)
        return HistoriographyAt(self, index)

    def append(self, nout_hash):
        self.set_values.append(nout_hash)

        prev_seen_in_all_nouts = None

        for nout_hash in all_preceding_nout_hashes(self.possible_timelines, nout_hash):
            if nout_hash in self.all_nouts:
                prev_seen_in_all_nouts = nout_hash
                break

            self.all_nouts.add(nout_hash)

        self.prev_seen_in_all_nouts.append(prev_seen_in_all_nouts)

        self.length += 1
        return self.length - 1

    def whats_new(self, index):
        """in anti-chronological order"""
        return takewhile(
            lambda v: v != self.prev_seen_in_all_nouts[index],
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index]))

    def whats_made_alive(self, index):
        """in anti-chronological order"""
        if index == 0:
            return self.whats_new(index)

        pod = find_point_of_divergence(
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index]),
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index - 1]))

        return takewhile(
            lambda v: v != pod,
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index]))

    def whats_made_dead(self, index):
        if index == 0:
            return iter([])

        pod = find_point_of_divergence(
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index]),
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index - 1]))

        return takewhile(
            lambda v: v != pod,
            all_preceding_nout_hashes(self.possible_timelines, self.set_values[index - 1]))


class HistoriographyAt(object):
    """Represents a particular point in time in the Historiography's life"""

    def __init__(self, historiography, index):
        pmts(index, int)
        self.historiography = historiography
        self.index = index

    def nout_hash(self):
        return self.historiography.set_values[self.index]

    def whats_new(self):
        return self.historiography.whats_new(self.index)

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


def t_lookup(yatn, t_path):
    if t_path == []:
        return yatn

    s_addr = yatn.t2s[t_path[0]]
    if s_addr is None:
        return None

    result = t_lookup(yatn.children[s_addr], t_path[1:])
    return result
