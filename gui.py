from collections import namedtuple
from contextlib import contextmanager

from kivy.core.window import Window
from kivy.app import App
from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.text.markup import LabelBase
from kivy.metrics import pt
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate

from step0 import TreeText, HashStore, play, parse_nout, parse_pos_acts, Possibility

MARGIN = 5
PADDING = 3

X = 0
Y = 1

LabelBase.register(name="FreeSerif",
                   fn_regular="/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
                   fn_bold="/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
                   fn_italic="/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
                   fn_bolditalic="/usr/share/fonts/truetype/freefont/FreeSerifBoldItalic.ttf",)


LabelBase.register(name="Mono",
                   fn_regular="/usr/share/fonts/truetype/ttf-liberation/LiberationMono-Regular.ttf",
                   fn_bold="/usr/share/fonts/truetype/ttf-liberation/LiberationMono-Bold.ttf",
                   fn_italic="/usr/share/fonts/truetype/ttf-liberation/LiberationMono-Italic.ttf",
                   fn_bolditalic="/usr/share/fonts/truetype/ttf-liberation/LiberationMono-BoldItalic.ttf",)


LabelBase.register(name="DejaVu",
                   fn_regular="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   fn_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   fn_italic="/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
                   fn_bolditalic="/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",)


OffsetBox = namedtuple('OffsetBox', ('offset', 'item'))


@contextmanager
def apply_offset(canvas, offset):
    canvas.add(PushMatrix())
    canvas.add(Translate(*offset))
    yield
    canvas.add(PopMatrix())


def no_offset(item):
    return OffsetBox((0, 0), item)

BoxTerminal = namedtuple('BoxTerminal', ('instructions', 'outer_dimensions', ))


class BoxNonTerminal(object):
    def __init__(self, semantics, offset_nonterminals, offset_terminals):
        """The idea here is: draw tree-like structures using 'boxes', rectangular shapes that may contain other such
        shapes. Some details:

        * The direction of drawing is from top left to bottom right. Children may have (X, Y) offsets of respectively
            postive (including 0), and negative (including 0) values.

        * We tie some "semantics" to a node in the "box tree", by this we simply mean the underlying thing that's beign
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
        max_x = max((obs.offset[X] + obs.item.outer_dimensions[X])
                    for obs in self.offset_terminals + self.offset_nonterminals)

        # min_y, because we're moving _down_ which is negative in Kivy's coordinate system
        min_y = min((obs.offset[Y] + obs.item.outer_dimensions[Y])
                    for obs in self.offset_terminals + self.offset_nonterminals)

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


class TreeWidget(Widget):

    def __init__(self, **kwargs):
        super(TreeWidget, self).__init__(**kwargs)

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

        self._keyboard = Window.request_keyboard(self._keyboard_closed, self, 'text')
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

        self.tree = self._hack()
        self.s_cursor = []
        self._unpoke_all_cursors(self.tree)
        self._poke_s_cursor(self.tree, self.s_cursor)

        self.refresh()

    def _keyboard_closed(self):
        # LATER: think about further handling of this scenario. (probably: only once I get into Mobile territory)
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        # ......

        # Return True to accept the key. Otherwise, it will be used by the system.
        return True

    def refresh(self, *args):
        self.canvas.clear()

        self.offset = (0, self.size[Y])  # default offset: start on top_left

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self.box_structure = self._nt_for_node_as_lispy_layout(self.tree)
            self._render_box(self.box_structure)

    def on_touch_down(self, touch):
        # see https://kivy.org/docs/guide/inputs.html#touch-event-basics
        # Basically:
        # 1. Kivy (intentionally) does not limit its passing of touch events to widgets that it applies to, you
        #   need to do this youself
        # 2. You need to call super and return its value
        ret = super(TreeWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        clicked_item = self.box_structure.from_point(
            bring_into_offset(self.offset, (touch.x, touch.y)))

        print(repr(clicked_item.semantics) if clicked_item else None)

        # TODO (potentially): grabbing, as documented here (including the caveats of that approach)
        # https://kivy.org/docs/guide/inputs.html#grabbing-touch-events

        return ret

    def _hack(self):
        filename = 'test1'
        possible_timelines = HashStore(parse_nout)
        byte_stream = iter(open(filename, 'rb').read())
        for pos_act in parse_pos_acts(byte_stream):
            if isinstance(pos_act, Possibility):
                possible_timelines.add(pos_act.nout)
            else:  # Actuality
                # this can be depended on to happen at least once ... if the file is correct
                present_nout = pos_act.nout_hash
        present_tree = play(possible_timelines, possible_timelines.get(present_nout))
        return present_tree

    def _unpoke_all_cursors(self, node):
        node.is_cursor = False
        if hasattr(node, 'children'):
            for child in node.children:
                self._unpoke_all_cursors(child)

    def _poke_s_cursor(self, node, s_cursor):
        # poking... yuck; soonish a better solution will present itself
        if s_cursor == []:
            node.is_cursor = True
            return

        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                if i == s_cursor[0]:
                    self._poke_s_cursor(child, s_cursor[1:])
                    return

    def _t_for_text(self, text, is_cursor):
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - PADDING - MARGIN - content_height - MARGIN - PADDING)
        bottom_right = (bottom_left[X] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[Y])

        if is_cursor:
            box_color = Color(0.95, 0.95, 0.95, 1)  # Ad Hoc Grey
        else:
            box_color = Color(1, 1, 0.97, 1)  # Ad Hoc Light Yellow

        instructions = [
            box_color,
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                ),
            Color(0, 115/255, 230/255, 1),  # Blue
            Rectangle(
                pos=(bottom_left[0] + PADDING + MARGIN, bottom_left[1] + PADDING + MARGIN),
                size=text_texture.size,
                texture=text_texture,
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

    def _nt_for_node_as_todo_list(self, node):
        if isinstance(node, TreeText):
            return BoxNonTerminal(node, [], [no_offset(self._t_for_text(node.unicode_, node.is_cursor))])

        if len(node.children) == 0:
            return BoxNonTerminal(node, [], [no_offset(self._t_for_text("(...)", node.is_cursor))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        flat_child_0 = "" + node.children[0].pp_flat()
        t = self._t_for_text(flat_child_0, node.children[0].is_cursor)
        offset_nonterminals = [
            no_offset(BoxNonTerminal(node.children[0], [], [no_offset(t)]))
        ]
        offset_down = t.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for child in node.children[1:]:
            nt = self._nt_for_node_as_todo_list(child)
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BoxNonTerminal(
            node,
            offset_nonterminals,
            [])

    def _nt_for_node_as_lispy_layout(self, node):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz

        if isinstance(node, TreeText):
            return BoxNonTerminal(node, [], [no_offset(self._t_for_text(node.unicode_, node.is_cursor))])

        t = self._t_for_text("(", node.is_cursor)
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(node.children) > 0:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.
            flat_child_0 = "" + node.children[0].pp_flat()
            t = self._t_for_text(flat_child_0, node.children[0].is_cursor)

            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), BoxNonTerminal(node.children[0], [], [no_offset(t)]))
            )
            offset_right += t.outer_dimensions[X]

            if len(node.children) > 1:
                for i, child_x in enumerate(node.children[1:]):
                    nt = self._nt_for_node_as_lispy_layout(child_x)
                    offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
                    offset_down += nt.outer_dimensions[Y]

                # get the final drawn item to figure out where to put the closing ")"
                last_drawn = nt.get_all_terminals()[-1]
                offset_right += last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

                # go "one line" back up
                offset_down -= last_drawn.item.outer_dimensions[Y]

        else:
            offset_right = t.outer_dimensions[X]

        t = self._t_for_text(")", node.is_cursor)
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(
            node,
            offset_nonterminals,
            offset_terminals)

    def _render_box(self, box):
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    def _texture_for_text(self, text):
        kw = {
            'font_size': pt(13),
            'font_name': 'DejaVuSans',
            'bold': True,
            'anchor_x': 'left',
            'anchor_y': 'top',
            'padding_x': 0,
            'padding_y': 0,
            'padding': (0, 0)}

        label = Label(text=text, **kw)
        label.refresh()
        return label.texture


class TestApp(App):
    def build(self):
        widget = TreeWidget()
        return widget

TestApp().run()
