from datastructure import NoutBegin


def riter(i):
    return reversed(list(i))


def follow_nouts(possible_timelines, nout_hash):
    yield nout_hash

    nout = possible_timelines.get(nout_hash)
    if nout == NoutBegin():
        raise StopIteration()

    for x in follow_nouts(possible_timelines, nout.previous_hash):
        yield x


def once_seen(values, value):
    # TODO: use dropwhile (but with a false predicate please)
    seen = False
    for consider_me in values:
        if consider_me == value:
            seen = True

        if seen:
            yield consider_me


class H2(object):

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

    def append(self, nout_hash):
        self.h2.append(nout_hash)

        full_history = follow_nouts(self.possible_timelines, nout_hash)

        point_of_divergence = None  # when this is the first add, there is no point of divergence
        to_be_added = []

        # Note: handling of [pre-]BEGIN is not necessary; it's implied by full_history, and the special-case for
        # point_of_divergence

        for nout_hash in full_history:
            if nout_hash in self.index_in_l:
                # points of divergence are determined on _l_ (a divergence can occur at a more granular level than
                # 'actually appended to H2)
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

    def whats_new(self, index_in_h2):
        if index_in_h2 == 0:
            return self.l[0:self.len_l_after_append[index_in_h2]]

        return self.l[self.len_l_after_append[index_in_h2 - 1]:self.len_l_after_append[index_in_h2]]

    def live_path(self, nout_hash):
        index_in_l = self.index_in_l[nout_hash]
        index_in_h2 = self.l_to_first_h2[index_in_l]

        # TODO Let's think about the ordering! In any case, the most logical thing is to do everything backwards, or
        # everything forwards.

        # If a point of divergence exists: recurse to it.
        pod = self.points_of_divergence[index_in_h2]
        if pod is not None:
            for x in self.live_path(self.l[pod]):
                yield x

        # * we use the index to yield the new items, but only from the nout_hash (each
        # until or from? depends on the ordering. The answer is "only those that are older than it"
        # which happens to be the same as "once seen, when the yielding is ant-chronological"
        for x in riter(once_seen(riter(self.whats_new(index_in_h2)), nout_hash)):
            yield x

    # possibly: live_path... think about it as a datastructure that's modifiable in-place

"""
>>> from datastructure import NoutBlock, NoutBegin, parse_nout
>>> from datastructure import TextBecome
>>> from hashstore import HashStore
>>>
>>> from this_years_datastructure import H2
>>>
>>> pt = HashStore(parse_nout)
>>>
>>> nb = NoutBegin()
>>>
>>> h_nb = pt.add(nb)
>>>
>>> h_a = pt.add(NoutBlock(TextBecome("a"), h_nb))
>>>
>>> h_ab = pt.add(NoutBlock(TextBecome("ab"), h_a))
>>> h_abc = pt.add(NoutBlock(TextBecome("abc"), h_ab))
>>>
>>> h_ad = pt.add(NoutBlock(TextBecome("ad"), h_a))
>>>
>>> h2 = H2(pt)
>>> h2.append(h_abc)
>>> h2.append(h_ad)
>>>
>>> list(h2.live_path(h_ad))
[6e340b9cffb3, 1f2cf5ca7d0d, 30017b836d55]
>>> list(h2.live_path(h_abc))
[6e340b9cffb3, 1f2cf5ca7d0d, a360f667d6fe, 6bd2fb15d352]
"""
