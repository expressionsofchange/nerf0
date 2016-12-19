from collections import namedtuple

from kivy.app import App
from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.text.markup import LabelBase
from kivy.metrics import pt
from kivy.uix.scrollview import ScrollView
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate

from step0 import TreeText, pp_test, HashStore, play, parse_nout, parse_pos_acts, Possibility

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


OffsetBS = namedtuple('OffsetBS', ('offset', 'item'))


def o(item):
    return OffsetBS((0, 0), item)

BSTerminal = namedtuple('BSTerminal', ('instructions', 'outer_dimensions', ))


class BSNonTerminal(object):
    def __init__(self, semantics, offset_nonterminals, offset_terminals):
        """The `offset_nonterminals` are ... the children

        I.e. the distinction is "is the node of semantics directly responsible for this, or only by virtue of its
        children?"

        (besides that distinction, one could argue for more folding of the concepts of terminals and non-terminals)
        """

        self.semantics = semantics
        self.offset_nonterminals = offset_nonterminals
        self.offset_terminals = offset_terminals

        self.outer_dimensions = self.calc_outer_dimensions()

    def get_all_terminals(self):
        result = self.offset_terminals
        for ((offset_x, offset_y), nt) in self.offset_nonterminals:
            for ((recursive_offset_x, recursive_offset_y), t) in nt.get_all_terminals:
                result.append(OffsetBS((offset_x + recursive_offset_x, offset_y + recursive_offset_y), t))
        return result

    def calc_outer_dimensions(self):
        max_x = max((obs.offset[X] + obs.item.outer_dimensions[X])
                    for obs in self.offset_terminals + self.offset_nonterminals)

        min_y = min((obs.offset[Y] + obs.item.outer_dimensions[Y])
                    for obs in self.offset_terminals + self.offset_nonterminals)

        return (max_x, min_y)


class MyFirstWidget(Widget):

    def __init__(self, **kwargs):
        super(MyFirstWidget, self).__init__(**kwargs)

        self.refresh()

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

    def refresh(self, *args):
        self.canvas.clear()

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        self.canvas.add(PushMatrix())
        self.canvas.add(Translate(0, self.size[Y]))

        self.box_structure = self._nt_for_node_as_todo_list(self._hack())
        self._render_bs(self.box_structure)

        self.canvas.add(PopMatrix())

    def on_touch_down(self, touch):
        # see https://kivy.org/docs/guide/inputs.html#touch-event-basics
        # Basically:
        # 1. Kivy (intentionally) does not limit its passing of touch events to widgets that it applies to, you
        #   need to do this youself
        # 2. You need to call super and return its value
        ret = super(MyFirstWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        clicked_item = self._from_xy(self.box_structure, touch.x, touch.y - self.height)
        print(repr(clicked_item))

        # TODO (potentially): grabbing, as documented here (including the caveats of that approach)
        # https://kivy.org/docs/guide/inputs.html#grabbing-touch-events

        return ret

    """
    def on_touch_move(self, touch):
        pass
        # print("M", touch.x, touch.y, touch.profile)

    def on_touch_up(self, touch):
        pass
        # print("U", touch.x, touch.y, touch.profile)
    """

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

    def _t_for_text(self, text):
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - PADDING - MARGIN - content_height - MARGIN - PADDING)
        bottom_right = (bottom_left[X] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[Y])

        instructions = [
            Color(0.95, 0.95, 0.95, 1),  # Ad Hoc Grey
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

        return BSTerminal(instructions, bottom_right)

    def _nt_for_node_as_todo_list(self, node):
        if isinstance(node, TreeText):
            return BSNonTerminal(node, [], [o(self._t_for_text(node.unicode_))])

        if len(node.children) == 0:
            return BSNonTerminal(node, [], [o(self._t_for_text("(...)"))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        flat_first_child = "" + node.children[0].pp_flat()
        t = self._t_for_text(flat_first_child)
        offset_nonterminals = [
            o(BSNonTerminal(node.children[0], [], [o(t)]))
        ]
        offset_down = t.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for child in node.children[1:]:
            nt = self._nt_for_node_as_todo_list(child)
            offset_nonterminals.append(OffsetBS((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BSNonTerminal(
            node,
            offset_nonterminals,
            [])

    def _render_bs(self, bs):
        for o, t in bs.offset_terminals:
            self.canvas.add(PushMatrix())
            self.canvas.add(Translate(*o))

            for instruction in t.instructions:
                self.canvas.add(instruction)

            self.canvas.add(PopMatrix())

        for o, nt in bs.offset_nonterminals:
            self.canvas.add(PushMatrix())
            self.canvas.add(Translate(*o))

            self._render_bs(nt)

            self.canvas.add(PopMatrix())

    def _texture_for_text(self, text):
        kw = {
            'font_size': pt(13),
            'font_name': 'DejaVuSans',
            'bold': True,
            'anchor_x': 'left',
            'anchor_y': 'top',
            'padding_x': 0,
            'padding_y': 0,
            'padding': (0, 0)}  # Hee... hier kan het ook direct.

        label = Label(text=text, **kw)
        label.refresh()
        return label.texture

        """
        # below is ill-understood copy/pasta; the explanation is inlcuded:
        # FIXME right now, we can't render very long line...
        # if we move on "VBO" version as fallback, we won't need to
        # do this. try to found the maximum text we can handle

        label = None
        label_len = len(text)
        ld = None

        while True:
            try:
                label = Label(text=text[:label_len], **kw)
                label.refresh()
                if ld is not None and ld > 2:
                    ld = int(ld / 2)
                    label_len += ld
                else:
                    break
            except Exception as e:
                # exception happen when we tried to render the text
                # reduce it...
                if ld is None:
                    ld = len(text)
                ld = int(ld / 2)
                if ld < 2 and label_len:
                    label_len -= 1
                label_len -= ld
                continue

        # ok, we found it.
        return label.texture
        """

    def _from_xy(self, bs, x, y):
        for o, t in bs.offset_terminals:
            if (x >= o[X] and x <= o[X] + t.outer_dimensions[X] and
                    y <= o[Y] and y >= o[Y] + t.outer_dimensions[Y]):
                return bs.semantics

        for o, nt in bs.offset_nonterminals:
            if (x >= o[X] and x <= o[X] + nt.outer_dimensions[X] and
                    y <= o[Y] and y >= o[Y] + nt.outer_dimensions[Y]):

                # it's within the outer bounds, and _may_ be a hit. recurse
                result = self._from_xy(nt, x - o[X], y - o[Y])
                if result is not None:
                    return result

        return None


class TestApp(App):
    def build(self):
        widget = MyFirstWidget()
        widget.size_hint = (None, None)
        widget.height = 500
        widget.width = 1000

        scrollview = ScrollView()
        scrollview.add_widget(widget)
        return scrollview

TestApp().run()
