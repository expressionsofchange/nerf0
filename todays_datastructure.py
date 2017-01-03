from datastructure import (
    NoutBegin,
    Hash,
    TextBecome,
    BecomeNode,
    Insert,
    Replace,
    Delete,
)


class MultiHistory(object):

    def __init__(self, possible_timelines):
        self.possible_timelines = possible_timelines

        self.list_ = []
        self.set_ = set([])

        # In a multi-history, a particular item is either "alive" (included in the most recent update) or "alternate"
        self.alive = []

    def update(self, nout_hash):
        to_be_added = []
        consider_for_deadness_index = len(self.list_) - 1

        # Collect history until you run into familiar territory:
        while nout_hash not in self.set_:
            to_be_added.append(nout_hash)

            nout = self.possible_timelines.get(nout_hash)
            if nout == NoutBegin():
                break
            nout_hash = nout.previous_hash

        # Add the collected history in reversed order (oldest first)
        for nh in reversed(to_be_added):
            self.list_.append(nh)
            self.set_.add(nh)
            self.alive.append(True)  # Whatever we just collected is alive by default

        # nout_hash is now either the first already-seen value, or is the begin-hash
        while consider_for_deadness_index >= 0 and nout_hash != self.list_[consider_for_deadness_index]:
            self.alive[consider_for_deadness_index] = False
            consider_for_deadness_index -= 1

    def make_copy(self):
        # The funny name ("make") is because I don't want to think about Python's copy/deepcopy and whatever the magic
        # predefined behavior is, but rather to simply do this myself.

        # In the future we should rethink how to optimize this. In particular list_ and set_ are "grow only"
        # datastructures (for which copying could be cheaply implemented when using singly linked lists); however, alive
        # is treated (at least in the current version) as a mutable datastructure, so we need a full copy for that.

        # In fact, another possible way forward is "copy and update" mixed into a single oparation.
        result = MultiHistory()
        result.list_ = self.list_[:]
        result.set_ = self.set_.copy()
        result.alive = self.alive[:]
        return result


class YetAnotherTreeNode(object):

    def __init__(self, multi_history, t_children, s_to_t):
        self.multi_history = multi_history
        self.t_children = t_children
        self.s_to_t = s_to_t

    def __repr__(self):
        return "YATN"


# I think I'll need to get rid of the idea that Notes take care of their own playing... we'll see if that's indeed so
# generally. For starters, I will not replicate that idea here, but rather imlement it in a single function.


def y_note_play(possible_timelines, note, structure, recurse, nout_hash):
    if isinstance(note, BecomeNode):  # or ... TextBecome (which is also a structure-spawning note)
        mh = MultiHistory()

    else:
        mh = structure.multi_history.make_copy()

    mh.update(nout_hash)

    if isinstance(note, BecomeNode) or isinstance(note, TextBecome):
        return YetAnotherTreeNode([], [], mh)

    if isinstance(note, Insert):
        t_children = structure.t_children[:]
        t_children.append(recurse(MultiHistory(), note.nout_hash))

        s_to_t = structure.s_to_t[:]
        s_to_t.insert(note.index, len(t_children) - 1)

        return YetAnotherTreeNode(t_children, s_to_t, mh)

    if isinstance(note, Delete):
        t_children = structure.t_children[:]
        s_to_t = structure.s_to_t[:]
        del s_to_t[note.index]
        return YetAnotherTreeNode(t_children, s_to_t, mh)

    if isinstance(note, Replace):
        i = structure.s_to_t[note.index]

        t_children = structure.t_children[:]
        t_children[i] = recurse(t_children[i].multi_history.make_copy(), note.nout_hash)

        return YetAnotherTreeNode(t_children, s_to_t, mh)

    # TODO TextBecome

    raise Exception("adsfasdfas")

# TWijfel: in een multi-history kunnen dingen ook opnieuw verschijnen; hoe ga ik dan om met de t_addresses daarvan?
# Komt vanzelf nog wel goed.


def construct_y(possible_timelines, previous_history, edge_nout_hash):
    # results_lookup was removed: in a multi-history world the multi_history cannot simply be looked up using the
    # nout_hash of the latest history.

    # Copy/pasta starting point: construct_x

    def recurse(inner_previous_history, nout_hash):
        return construct_y(possible_timelines, inner_previous_history, nout_hash)

    edge_nout = possible_timelines.get(edge_nout_hash)

    if edge_nout == NoutBegin():
        # Does it make sense to allow for the "playing" of "begin only"?
        # Only if you think "nothing" is a thing; let's build a version which doesn't do that first.
        raise Exception("In this version, I don't think playing empty history makes sense")

    last_nout_hash = edge_nout.previous_hash
    last_nout = possible_timelines.get(last_nout_hash)
    if last_nout == NoutBegin():
        tree_before_edge = None  # in theory: ignored, because the first note should always be a "Become" note
    else:
        # TODO I think the current recursive definition breaks down... because we construct adfsadfsadfs
        tree_before_edge = construct_y(possible_timelines, previous_history_REAALY, last_nout_hash)

    note = edge_nout.note

    def hash_for(nout):
        # copy/pasta... e.g. from cli.py (at the time of copy/pasting)
        bytes_ = nout.as_bytes()
        return Hash.for_bytes(bytes_)

    result = y_note_play(possible_timelines, note, tree_before_edge, recurse, hash_for(edge_nout))
    return result
