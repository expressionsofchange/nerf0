from copy import copy

from datastructure import (
    NoutBegin,
    TextBecome,
    TreeText,
    BecomeNode,
    Insert,
    Replace,
    Delete,
)


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

        # TODO explain the idea of top/used
        self.top = -1
        self.used = False

    def append(self, nout_hash):
        if self.used:
            # better prose is required here.
            raise Exception("Each H2 can only be appended to once")

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

    def whats_new(self):
        if self.top == -1:
            raise Exception("Uninititalized yekyek")

        if self.top == 0:
            return self.l[0:self.len_l_after_append[self.top]]

        return self.l[self.len_l_after_append[self.top - 1]:self.len_l_after_append[self.top]]

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
        for x in riter(once_seen(riter(self.whats_new(index_in_h2)), nout_hash)):
            yield x

    # possibly: _r_live_path... think about it as a datastructure that's modifiable in-place


"""
NO LONGER WORKS; I've moved on from the initial playing around
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


class YetAnotherTreeNode(object):

    def __init__(self, children, historiographies, t_to_s, s_to_t):
        self.children = children
        self.historiographies = historiographies
        self.t_to_s = t_to_s
        self.s_to_t = s_to_t

    def __repr__(self):
        return "YATN"


# I think I'll need to get rid of the idea that Notes take care of their own playing... we'll see if that's indeed so
# generally. For starters, I will not replicate that idea here, but rather imlement it in a single function.


def y_note_play(possible_timelines, structure, note, recurse):
    # whether we do hash-to-note here or below is of less importance

    if isinstance(note, BecomeNode):
        return YetAnotherTreeNode([], [], [], []), None

    if isinstance(note, Insert):
        empty_structure = "Nothing"  # unused variable b/c Begin is never reached.
        empty_historiography = H2(possible_timelines)

        child, child_historiography, xxx_b = recurse(empty_structure, empty_historiography, note.nout_hash)

        children = structure.children[:]
        children.insert(note.index, child)

        historiography = structure.historiographies[:]
        historiography.insert(note.index, child_historiography)

        t_to_s = [(i if i is None or i < note.index else i + 1) for i in structure.t_to_s] + [note.index]

        new_t = len(t_to_s) - 1
        s_to_t = structure.s_to_t[:]
        s_to_t.insert(note.index, new_t)

        return YetAnotherTreeNode(children, historiography, t_to_s, s_to_t), (new_t, child_historiography.top, xxx_b)

    if isinstance(note, Delete):
        children = structure.children[:]
        del children[note.index]

        historiography = structure.historiographies[:]
        del historiography[note.index]

        t_to_s = structure.t_to_s[:]
        t_to_s[structure.s_to_t[note.index]] = None

        s_to_t = structure.s_to_t[:]
        del s_to_t[note.index]

        return YetAnotherTreeNode(children, historiography, t_to_s, s_to_t), None

    if isinstance(note, Replace):
        existing_structure = structure.children[note.index]
        existing_historiography = structure.historiographies[note.index]

        child, child_historiography, xxx_b = recurse(existing_structure, existing_historiography, note.nout_hash)

        children = structure.children[:]
        historiographies = structure.historiographies[:]

        children[note.index] = child
        historiographies[note.index] = child_historiography

        t_to_s = structure.t_to_s[:]
        s_to_t = structure.s_to_t[:]

        xxx = (s_to_t[note.index], child_historiography.top, xxx_b)
        return YetAnotherTreeNode(children, historiographies, t_to_s, s_to_t), xxx

    if isinstance(note, TextBecome):
        return TreeText(note.unicode_, 'no metadata available'), None

    raise Exception("Unknown Note")


def construct_y(possible_timelines, existing_structure, existing_h2, edge_nout_hash):
    def recurse(s, h, enh):
        return construct_y(possible_timelines, s, h, enh)

    existing_h2 = existing_h2.append(edge_nout_hash)

    new_hashes = existing_h2.whats_new()
    xxx_b = []

    for new_hash in new_hashes:
        new_nout = possible_timelines.get(new_hash)
        if new_nout == NoutBegin():
            # this assymmetry is present elsewhere too... up for consideration
            continue

        # Note: y_note_play does _not_ operate on historiographies; it only knows about them in the sense that it
        # calls construct_y using the already-present historiography for the Replace note.
        existing_structure, xxx = y_note_play(possible_timelines, existing_structure, new_nout.note, recurse)
        xxx_b.append((new_hash, xxx))

    return existing_structure, existing_h2, xxx_b


def xxx_construct_y(possible_timelines, edge_nout_hash):
    return construct_y(possible_timelines, "ignored... b/c begining is assumed", H2(possible_timelines), edge_nout_hash)
