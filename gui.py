from collections import namedtuple

from kivy.app import App
from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.text.markup import LabelBase
from kivy.metrics import pt
from kivy.uix.scrollview import ScrollView

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


BoxStructure = namedtuple('BoxStructure', ('node', 'top_left', 'bottom_right', 'children'))


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

        self.box_structure = self._render_node_as_todo_list(self._hack(), (0, self.size[1]))

    def on_touch_down(self, touch):
        # see https://kivy.org/docs/guide/inputs.html#touch-event-basics
        # Basically:
        # 1. Kivy (intentionally) does not limit its passing of touch events to widgets that it applies to, you
        #   need to do this youself
        # 2. You need to call super and return its value
        ret = super(MyFirstWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        clicked_item = self._from_xy(self.box_structure, touch.x, touch.y)
        print(clicked_item)

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

    def _render_text(self, text, pos):
        relative_x, relative_y = pos

        with self.canvas:
            text_texture = self._render_label(text)
            content_height = text_texture.height
            content_width = text_texture.width

            top_left = pos
            bottom_left = (top_left[0], top_left[1] - PADDING - MARGIN - content_height - MARGIN - PADDING)
            bottom_right = (bottom_left[0] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[1])

            Color(0.95, 0.95, 0.95, 1)  # Ad Hoc Grey
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                )

            Color(0, 115/255, 230/255, 1)  # Blue
            Rectangle(
                pos=(bottom_left[0] + PADDING + MARGIN, bottom_left[1] + PADDING + MARGIN),
                size=text_texture.size,
                texture=text_texture,
                )

        return BoxStructure(text, top_left, bottom_right, ())

    def _render_node_as_todo_list(self, node, pos):
        if isinstance(node, TreeText):
            return self._render_text(node.unicode_, pos)

        if len(node.children) < 1:
            return self._render_text("(...)", pos)

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        my_arg_0 = "" + node.children[0].pp_flat()
        rendered_arg_0 = self._render_text(my_arg_0, pos)
        children = [rendered_arg_0]
        rendered_bottom_right = rendered_arg_0.bottom_right
        max_x = rendered_bottom_right[X]

        my_indentation = pos[0]
        next_indentation = my_indentation + 50  # Magic number for indentation

        next_pos = (next_indentation, rendered_bottom_right[1])

        for child in node.children[1:]:
            rendered_arg_0 = self._render_node_as_todo_list(child, next_pos)
            rendered_bottom_right = rendered_arg_0.bottom_right
            max_x = max(max_x, rendered_bottom_right[X])
            children.append(rendered_arg_0)
            next_pos = (next_indentation, rendered_bottom_right[1])

        return BoxStructure(node, pos, (max_x, rendered_bottom_right[Y]), tuple(children))

    def _render_label(self, text):
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
        for child in bs.children:
            if (x >= child.top_left[X] and x <= child.bottom_right[X] and
                    y <= child.top_left[Y] and y >= child.bottom_right[Y]):
                return self._from_xy(child, x, y) + [bs.node]
        return [bs.node]


class TestApp(App):
    def build(self):
        widget = MyFirstWidget()
        widget.size_hint = (None, None)
        widget.height = 5000
        widget.width = 1000

        scrollview = ScrollView()
        scrollview.add_widget(widget)
        return scrollview

TestApp().run()
