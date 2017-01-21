from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate
from contextlib import contextmanager
from collections import namedtuple

X = 0
Y = 1

OffsetBox = namedtuple('OffsetBox', ('offset', 'item'))


def no_offset(item):
    return OffsetBox((0, 0), item)

BoxTerminal = namedtuple('BoxTerminal', ('instructions', 'outer_dimensions', ))


class BoxNonTerminal(object):
    def __init__(self, semantics, offset_nonterminals, offset_terminals):
        """The idea here is: draw tree-like structures using 'boxes', rectangular shapes that may contain other such
        shapes. Some details:

        * The direction of drawing is from top left to bottom right. Children may have (X, Y) offsets of respectively
            postive (including 0), and negative (including 0) values.

        * We tie some "semantics" to a node in the "box tree", by this we simply mean the underlying thing that's being
            drawn. Any actual drawing related to the present semantics is represented in the terminals.

        * The current box may have some child-boxes, which have underlying semantics.

        * There outer_dimensions of represent the smallest box that can be drawn around this entire node. This is useful
            to quickly decide whether the current box needs to be considered at all in e.g. collision checks.
        """

        self.semantics = semantics
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

    def from_point(self, point):
        """X & Y in the reference frame of `self`"""

        # If any of our terminals matches, we match
        for o, t in self.offset_terminals:
            if (point[X] >= o[X] and point[X] <= o[X] + t.outer_dimensions[X] and
                    point[Y] <= o[Y] and point[Y] >= o[Y] + t.outer_dimensions[Y]):
                return self

        # Otherwise, recursively check our children
        for o, nt in self.offset_nonterminals:
            if (point[X] >= o[X] and point[X] <= o[X] + nt.outer_dimensions[X] and
                    point[Y] <= o[Y] and point[Y] >= o[Y] + nt.outer_dimensions[Y]):

                # it's within the outer bounds, and _might_ be a hit. recurse to check:
                result = nt.from_point(bring_into_offset(o, point))
                if result is not None:
                    return result

        return None

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
