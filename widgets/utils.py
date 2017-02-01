from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate
from contextlib import contextmanager
from collections import namedtuple

from annotated_tree import annotated_node_factory


X = 0
Y = 1

OffsetBox = namedtuple('OffsetBox', ('offset', 'item'))


def no_offset(item):
    return OffsetBox((0, 0), item)

BoxTerminal = namedtuple('BoxTerminal', ('instructions', 'outer_dimensions', ))


class BoxNonTerminal(object):
    def __init__(self, offset_nonterminals, offset_terminals):
        """The idea here is: draw tree-like structures using 'boxes', rectangular shapes that may contain other such
        shapes. Some details:

        * The direction of drawing is from top left to bottom right. Children may have (X, Y) offsets of respectively
            postive (including 0), and negative (including 0) values.

        * The current box may have some child-boxes

        * There outer_dimensions of represent the smallest box that can be drawn around this entire node. This is useful
            to quickly decide whether the current box needs to be considered at all in e.g. collision checks.
        """

        self.offset_nonterminals = offset_nonterminals
        self.offset_terminals = offset_terminals

        self.outer_dimensions = self.calc_outer_dimensions()

    def calc_outer_dimensions(self):
        max_x = max([0] + [(obs.offset[X] + obs.item.outer_dimensions[X])
                    for obs in self.offset_terminals + self.offset_nonterminals])

        # min_y, because we're moving _down_ which is negative in Kivy's coordinate system
        min_y = min([0] + [(obs.offset[Y] + obs.item.outer_dimensions[Y])
                    for obs in self.offset_terminals + self.offset_nonterminals])

        return (max_x, min_y)

    def get_all_terminals(self):
        def k(ob):
            return ob.offset[Y] * -1, ob.offset[X]

        result = self.offset_terminals[:]
        for ((offset_x, offset_y), nt) in self.offset_nonterminals:
            for ((recursive_offset_x, recursive_offset_y), t) in nt.get_all_terminals():
                result.append(OffsetBox((offset_x + recursive_offset_x, offset_y + recursive_offset_y), t))

        # sorting here is a bit of a hack. We need it to be able to access the "last added item" while throwing
        # terminals and non-terminals on a single big pile during construction time. Better solution: simply remember in
        # which order items were constructed in the first place.
        return sorted(result, key=k)


def bring_into_offset(offset, point):
    """The _inverse_ of applying to offset on the point"""
    return point[X] - offset[X], point[Y] - offset[Y]


@contextmanager
def apply_offset(canvas, offset):
    canvas.add(PushMatrix())
    canvas.add(Translate(*offset))
    yield
    canvas.add(PopMatrix())


SAddress = list  # the most basic expression of an SAddress' type; we can do something more powerful if needed

SAddressAnnotatedBoxNonTerminal = annotated_node_factory('SAddressAnnotatedBoxNonTerminal', BoxNonTerminal, SAddress)


def annotate_boxes_with_s_addresses(nt, path):
    children = [
        annotate_boxes_with_s_addresses(offset_box.item, path + [i])
        for (i, offset_box) in enumerate(nt.offset_nonterminals)]

    return SAddressAnnotatedBoxNonTerminal(
        underlying_node=nt,
        annotation=path,
        children=children
    )


def from_point(nt_with_s_address, point):
    """X & Y in the reference frame of `nt_with_s_address`"""

    nt = nt_with_s_address.underlying_node

    # If any of our terminals matches, we match
    for o, t in nt.offset_terminals:
        if (point[X] >= o[X] and point[X] <= o[X] + t.outer_dimensions[X] and
                point[Y] <= o[Y] and point[Y] >= o[Y] + t.outer_dimensions[Y]):

            return nt_with_s_address

    # Otherwise, recursively check our children
    for child_with_s_address, (o, nt) in zip(nt_with_s_address.children, nt.offset_nonterminals):
        if (point[X] >= o[X] and point[X] <= o[X] + nt.outer_dimensions[X] and
                point[Y] <= o[Y] and point[Y] >= o[Y] + nt.outer_dimensions[Y]):

            # it's within the outer bounds, and _might_ be a hit. recurse to check:
            result = from_point(child_with_s_address, bring_into_offset(o, point))
            if result is not None:
                return result

    return None
