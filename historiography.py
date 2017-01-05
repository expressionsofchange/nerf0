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

        # `set_values` model the consecutive "states" of the Historiograhpy.
        self.set_values = []

        # `all_nout_hashes` contains all nout_hashes that can be deduced from any set value, in double chronological
        # order (each history chronologically, and chronologically as flowing from the order of setting the values)
        self.all_nout_hashes = []

        # Reverse lookup: nout_hash => index in all_nout_hashes
        self.r_all_nout_hashes = {}

        #
        self.len_l_after = []

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
        self.set_values.append(nout_hash)

        to_be_added = []

        for nout_hash in follow_nouts(self.possible_timelines, nout_hash):
            if nout_hash in self.index_in_l:
                # this is also the point of divergence, which we could (re)consider storing for certain optimizations.
                break
            to_be_added.append(nout_hash)

        for nout_hash in reversed(to_be_added):
            self.all_nout_hashes.append(nout_hash)
            self.index_in_l[nout_hash] = len(self.all_nout_hashes) - 1

        self.len_l_after_append.append(len(self.all_nout_hashes))

    def whats_new(self):
        if self.top == -1:
            raise Exception("Uninititalized yekyek")

        return self.r_whats_new(self.top)

    def r_whats_new(self, index):
        if index == 0:
            return self.all_nout_hashes[0:self.len_l_after_append[index]]

        return self.all_nout_hashes[self.len_l_after_append[index - 1]:self.len_l_after_append[index]]

    def live_path(self):
        """
        At some point there was an implementation of a getter for the "live path" (both for the last value in
        self.latests_nouts, and for any nout) here. However, it was not more performant than simply calling
        follow_nouts, and much more complicated.

        Under certain very particular circumstances an optimization is useful though:

        * The Historiograhpy is kept in memory between updates; especially if related data (e.g. drawing instructions in
            a gui-context) are also kept in-memory between updates as much as possible.
        * The Historiograhpy is "long enough" (what that is should be measured empirically)

        * Updates to the latest_present are usually extensions of history.
        """
        raise NotImplemented()


class YetAnotherTreeNode(object):

    def __init__(self, children, historiographies, t2s, s2t):
        st_sanity(t2s, s2t)
        self.children = children
        self.historiographies = historiographies
        self.t2s = t2s
        self.s2t = s2t

    def __repr__(self):
        return "YATN"
