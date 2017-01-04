from itertools import dropwhile
from copy import copy
from legato import follow_nouts
from spacetime import st_sanity


def riter(i):
    # TODO this is lazy; reveals problems elsewhwere
    return reversed(list(i))


class Historiograhpy(object):
    """
    >>> from legato import NoutBlock, NoutBegin, parse_nout
    >>> from clef import TextBecome
    >>> from hashstore import HashStore
    >>>
    >>> from historiography import Historiograhpy
    >>>
    >>> possible_timelines = HashStore(parse_nout)
    >>>
    >>> begin = NoutBegin()
    >>>
    >>> hash_begin = possible_timelines.add(begin)
    >>>
    >>> hash_a = possible_timelines.add(NoutBlock(TextBecome("a"), hash_begin))
    >>>
    >>> hash_ab = possible_timelines.add(NoutBlock(TextBecome("ab"), hash_a))
    >>> hash_abc = possible_timelines.add(NoutBlock(TextBecome("abc"), hash_ab))
    >>>
    >>> hash_ad = possible_timelines.add(NoutBlock(TextBecome("ad"), hash_a))
    >>>
    >>> historiography = Historiograhpy(possible_timelines)
    >>> historiography_abc = historiography.append(hash_abc)
    >>> historiography_ad = historiography_abc.append(hash_ad)
    >>>
    >>> list(historiography_abc.live_path())
    [6e340b9cffb3, 1f2cf5ca7d0d, a360f667d6fe, 6bd2fb15d352]
    >>> list(historiography_ad.live_path())
    [6e340b9cffb3, 1f2cf5ca7d0d, 30017b836d55]
    """

    def __init__(self, possible_timelines):
        self.possible_timelines = possible_timelines

        self.h2 = []

        # contains more & less information than h2:
        # * more: it contains all hashes back to "begin"
        # * less: it contains no duplicates
        self.l = []

        self.index_in_l = {}
        self.l_to_first_h2 = {}

        self.len_l_after_append = []

        # points of divergence is expressed as: index_in_h2 => hash
        self.points_of_divergence = []

        # TODO explain the idea of top/used
        self.top = -1
        self.used = False

    def append(self, nout_hash):
        if self.used:
            # better prose is required here.
            raise Exception("Each Historiograhpy can only be appended to once")

        copied = copy(self)
        self.used = True

        copied._do_append(nout_hash)
        copied.top += 1
        return copied

    def _do_append(self, nout_hash):
        self.h2.append(nout_hash)

        full_history = follow_nouts(self.possible_timelines, nout_hash)

        point_of_divergence = None  # when this is the first add, there is no point of divergence
        to_be_added = []

        # Note: handling of [pre-]BEGIN is not necessary; it's implied by full_history, and the special-case for
        # point_of_divergence

        for nout_hash in full_history:
            if nout_hash in self.index_in_l:
                # points of divergence are determined on _l_ (a divergence can occur at a more granular level than
                # 'actually appended to Historiograhpy)
                point_of_divergence = self.index_in_l[nout_hash]
                break

            to_be_added.append(nout_hash)
            # they must be collected, because we need to add in reverse order

        for nout_hash in reversed(to_be_added):
            self.l.append(nout_hash)
            self.index_in_l[nout_hash] = len(self.l) - 1
            self.l_to_first_h2[len(self.l) - 1] = len(self.h2) - 1

        self.len_l_after_append.append(len(self.l))
        self.points_of_divergence.append(point_of_divergence)

    def whats_new(self):
        if self.top == -1:
            raise Exception("Uninititalized yekyek")

        return self.r_whats_new(self.top)

    def r_whats_new(self, index):
        if index == 0:
            return self.l[0:self.len_l_after_append[index]]

        return self.l[self.len_l_after_append[index - 1]:self.len_l_after_append[index]]

    def live_path(self):
        if self.top == -1:
            raise Exception("Uninititalized yekyek")

        return self._r_live_path(self.h2[self.top])

    def _r_live_path(self, nout_hash):
        index_in_l = self.index_in_l[nout_hash]
        index_in_h2 = self.l_to_first_h2[index_in_l]

        # TODO Let's think about the ordering! In any case, the most logical thing is to do everything backwards, or
        # everything forwards.

        # If a point of divergence exists: recurse to it.
        pod = self.points_of_divergence[index_in_h2]
        if pod is not None:
            for x in self._r_live_path(self.l[pod]):
                yield x

        # * we use the index to yield the new items, but only from the nout_hash (each
        # until or from? depends on the ordering. The answer is "only those that are older than it"
        # which happens to be the same as "once seen, when the yielding is ant-chronological"
        for x in riter(dropwhile(lambda v: v != nout_hash, riter(self.r_whats_new(index_in_h2)))):
            yield x

    # possibly: _r_live_path... think about it as a datastructure that's modifiable in-place


class YetAnotherTreeNode(object):

    def __init__(self, children, historiographies, t2s, s2t):
        st_sanity(t2s, s2t)
        self.children = children
        self.historiographies = historiographies
        self.t2s = t2s
        self.s2t = s2t

    def __repr__(self):
        return "YATN"
