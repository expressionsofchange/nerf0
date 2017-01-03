from collections import namedtuple
from contextlib import contextmanager
from os.path import isfile

from kivy.core.window import Window
from kivy.app import App
from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.core.text.markup import LabelBase
from kivy.metrics import pt
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Translate
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout

from datastructure import (
    BecomeNode,
    Delete,
    Insert,
    NoutBegin,
    NoutBlock,
    construct_x,
    Replace,
    TextBecome,
    TreeNode,
    TreeText,
)

from this_years_datastructure import xxx_construct_y

from hashstore import Hash
from posacts import Possibility, Actuality
from channel import Channel

from filehandler import (
    FileWriter,
    RealmOfThePossible,
    initialize_history,
    read_from_file
)

MARGIN = 5
PADDING = 3

X = 0
Y = 1

# These are standard Python (and common sense); still... one might occasionally be tempted to think that 'before' is
# moddeled as -1 rather than 0, which is why I made the correct indexes constants
INSERT_BEFORE = 0
INSERT_AFTER = 1

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


class TreeWidget(Widget):

    def __init__(self, **kwargs):
        super(TreeWidget, self).__init__(**kwargs)
        self.autosave = True

        self.all_trees = {}
        self.s_cursor = []

        # In this version the file-handling and history-channel are maintained by the GUI widget itself. I can imagine
        # they'll be moved out once we get multiple windows.

        filename = 'test2'
        history_channel = Channel()  # Pun not intended

        self.cursor_channel = Channel()

        self.possible_timelines = RealmOfThePossible(history_channel).possible_timelines
        self.send_to_channel = history_channel.connect(self.receive_from_channel)

        if isfile(filename):
            # ReadFromFile before connecting to the Writer to ensure that reading from the file does not write to it
            read_from_file(filename, history_channel)
            FileWriter(history_channel, filename)
        else:
            # FileWriter first to ensure that the initialization becomes part of the file.
            FileWriter(history_channel, filename)
            initialize_history(history_channel)

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

        self._keyboard = None
        self.initialize_keyboard()

    def initialize_keyboard(self):
        # not well-understood yet...
        if self._keyboard is None:
            self._keyboard = Window.request_keyboard(self._keyboard_closed, self, 'text')
            self._keyboard.bind(on_key_down=self._on_keyboard_down)

    # ## Section for channel-communication
    def receive_from_channel(self, data):
        # data :: Possibility | Actuality
        # there is no else branch: Possibility only travels _to_ the channel;
        if isinstance(data, Actuality):
            self.present_nout_hash = data.nout_hash
            self._present_nout_updated()

    def send_possibility_up(self, nout):
        # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
        # copy/pasted from the HashStore implementation; but we need it here again.

        bytes_ = nout.as_bytes()
        hash_ = Hash.for_bytes(bytes_)
        self.send_to_channel(Possibility(nout))
        return hash_

    def send_actuality_up(self, nout_hash):
        self.send_to_channel(Actuality(nout_hash))

    def set_present_nout(self, nout):
        """Call only_from inside_ ! don't call this in response to parent updates, because this moves data in the
        direction of the parent!"""
        present_nout_hash = self.send_possibility_up(nout)
        self.present_nout_hash = present_nout_hash
        if self.autosave:
            self.send_actuality_up(present_nout_hash)
        self._present_nout_updated()

    def _present_nout_updated(self):
        """invalidation of any local caches that may depend on present_nout; must be called in response to _any_
        update"""
        self.present_tree = construct_x(
            self.all_trees, self.possible_timelines, self.present_nout_hash)

        self.refresh()

    # ## Section for Keyboard / Mouse handling
    def _keyboard_closed(self):
        # LATER: think about further handling of this scenario. (probably: only once I get into Mobile territory)
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
        code, textual_code = keycode

        if textual_code in ['left', 'h']:
            self._set_s_cursor(self._parent_sc(self.s_cursor))
            self.refresh()
        elif textual_code in ['right', 'l']:
            self._set_s_cursor(self._child_sc(self.s_cursor))
            self.refresh()
        elif textual_code in ['up', 'k']:
            self._set_s_cursor(self._dfs_sibbling_sc(self.s_cursor, -1))
            self.refresh()
        elif textual_code in ['down', 'j']:
            self._set_s_cursor(self._dfs_sibbling_sc(self.s_cursor, 1))
            self.refresh()

        elif textual_code in ['q']:
            self._add_sibbling_text(INSERT_BEFORE)
        elif textual_code in ['w']:
            self._add_child_text()
        elif textual_code in ['e']:
            self._add_sibbling_text(INSERT_AFTER)
        elif textual_code in ['a']:
            self._add_sibbling_node(INSERT_BEFORE)
        elif textual_code in ['s']:
            self._add_child_node()
        elif textual_code in ['d']:
            self._add_sibbling_node(INSERT_AFTER)

        elif textual_code in ['x', 'del']:
            self._delete_current_node()

        # Return True to accept the key. Otherwise, it will be used by the system.
        return True

    def refresh(self, *args):
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y])  # default offset: start on top_left

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self.box_structure = self._nt_for_node_as_lispy_layout(self.present_tree, [])
            self._render_box(self.box_structure)

    def _set_s_cursor(self, s_cursor):
        self.s_cursor = s_cursor
        cursor_node = self._node_for_s_cursor(self.present_tree, self.s_cursor)
        self.cursor_channel.broadcast(cursor_node.metadata.nout_hash)

    def on_touch_down(self, touch):
        # see https://kivy.org/docs/guide/inputs.html#touch-event-basics
        # Basically:
        # 1. Kivy (intentionally) does not limit its passing of touch events to widgets that it applies to, you
        #   need to do this youself
        # 2. You need to call super and return its value
        ret = super(TreeWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        clicked_item = self.box_structure.from_point(bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._set_s_cursor(clicked_item.semantics)
            self.refresh()

        # TODO (potentially): grabbing, as documented here (including the caveats of that approach)
        # https://kivy.org/docs/guide/inputs.html#grabbing-touch-events

        return ret

    # ## Section for s_cursor navigation
    def _dfs(self, node, s_address):
        # returns the depth first search of all s_addresses
        result = [s_address]
        if hasattr(node, 'children'):
            for i, child in enumerate(node.children):
                result.extend(self._dfs(child, s_address + [i]))

        return result

    def _node_for_s_cursor(self, node, s_cursor):
        if s_cursor == []:
            return node

        if hasattr(node, 'children'):
            # no bounds checking (yet?)
            return self._node_for_s_cursor(node.children[s_cursor[0]], s_cursor[1:])

    def _node_path_for_s_cursor(self, node, s_cursor):
        if s_cursor == []:
            return [node]

        if hasattr(node, 'children'):
            # no bounds checking (yet?)
            return [node] + self._node_path_for_s_cursor(node.children[s_cursor[0]], s_cursor[1:])

    def _parent_sc(self, s_cursor):
        return s_cursor[:-1]

    def _child_sc(self, s_cursor):
        node = self._node_for_s_cursor(self.present_tree, s_cursor)
        if not hasattr(node, 'children') or len(node.children) == 0:
            return s_cursor  # the no-op
        return s_cursor + [0]

    def _sibbling_sc(self, s_cursor, direction):
        if s_cursor == []:
            return s_cursor  # root has no sibblings

        parent = self._node_for_s_cursor(self.present_tree, self._parent_sc(s_cursor))
        index = s_cursor[-1] + direction
        bounded_index = max(0, min(len(parent.children) - 1, index))
        return s_cursor[:-1] + [bounded_index]

    def _dfs_sibbling_sc(self, s_cursor, direction):
        dfs = self._dfs(self.present_tree, [])
        dfs_index = dfs.index(s_cursor) + direction
        bounded_index = max(0, min(len(dfs) - 1, dfs_index))
        return dfs[bounded_index]

    # ## Section for editing
    def _add_child_node(self):
        cursor_node = self._node_for_s_cursor(self.present_tree, self.s_cursor)
        if not isinstance(cursor_node, TreeNode):
            return  # for now... we just silently ignore the user's request when they ask to add a child to a non-node

        index = len(cursor_node.children)
        self._add_x_node(self.s_cursor, index)
        self._set_s_cursor(self.s_cursor + [index])
        self._present_nout_updated()

    def _add_sibbling_node(self, direction):
        if self.s_cursor == []:
            return  # adding sibblings to the root is not possible (it would lead to a forrest)

        # because direction is in [0, 1]... no need to minimize/maximize (PROVE!)
        index = self.s_cursor[-1] + direction
        self._add_x_node(self.s_cursor[:-1], index)
        self._set_s_cursor(self.s_cursor[:-1] + [index])
        self._present_nout_updated()

    def _add_x_node(self, s_cursor, index):
        cursor_node = self._node_for_s_cursor(self.present_tree, s_cursor)

        begin = self.send_possibility_up(NoutBegin())
        to_be_inserted = self.send_possibility_up(NoutBlock(BecomeNode(), begin))

        self._bubble_history_up(self.send_possibility_up(
            NoutBlock(Insert(index, to_be_inserted), cursor_node.metadata.nout_hash)), s_cursor)

    def _bubble_history_up(self, hash_to_bubble, s_address):
        """Recursively replace history to reflect a change (hash_to_bubble) at a lower level (s_address)"""

        for i in reversed(range(len(s_address))):
            # We slide a window of size 2 over the s_address from right to left, like so:
            # [..., ..., ..., ..., ..., ..., ...]  <- s_address
            #                              ^  ^
            #                           [:i]  i
            # For each such i, the sliced array s_address[:i] gives you the s_address of a node in which a replacement
            # takes place, and s_address[i] gives you the index to replace at.
            #
            # Regarding the range (0, len(s_address)) the following:
            # * len(s_address) means the s_address itself is the first thing to be replaced.
            # * 0 means: the last replacement is _inside_ the root node (s_address=[]), at index s_address[0]
            replace_in = self._node_for_s_cursor(self.present_tree, s_address[:i])

            hash_to_bubble = self.send_possibility_up(
                NoutBlock(Replace(s_address[i], hash_to_bubble), replace_in.metadata.nout_hash))

        # The root node (s_address=[]) itself cannot be replaced, its replacement is represented as "Actuality updated"
        self.present_nout_hash = hash_to_bubble
        self.send_actuality_up(hash_to_bubble)

    def _add_child_text(self):
        cursor_node = self._node_for_s_cursor(self.present_tree, self.s_cursor)
        if not isinstance(cursor_node, TreeNode):
            # Add child-text to text node is interpreted as "edit that text node"
            self._edit_x_text(cursor_node.unicode_, self.s_cursor[:-1], self.s_cursor[-1], self.s_cursor)
            return

        index = len(cursor_node.children)
        new_s_cursor = self.s_cursor + [index]
        self._add_x_text(self.s_cursor, index, new_s_cursor)

    def _add_sibbling_text(self, direction):
        if self.s_cursor == []:
            return  # adding sibblings to the root is not possible (it would lead to a forrest)

        # because direction is in [0, 1]... no need to minimize/maximize (PROVE!)
        index = self.s_cursor[-1] + direction
        new_s_cursor = self._set_s_cursor(self.s_cursor[:-1] + [index])
        self._add_x_text(self.s_cursor[:-1], index, new_s_cursor)

    def _add_x_text(self, s_cursor, index, new_s_cursor):
        layout = BoxLayout(spacing=10, orientation='vertical')
        ti = TextInput(text="", size_hint=(1, .9))
        btn = Button(text='Close and save', size_hint=(1, .1,))
        layout.add_widget(ti)
        layout.add_widget(btn)

        popup = Popup(
            title='Edit text', content=layout
            )

        def popup_dismiss(*args):
            # Because of the Modal nature of the popup, we can take the naive approach here and simply insert the
            # results of the popup, trigger the recalc etc. etc. as if this were sequential code.
            cursor_node = self._node_for_s_cursor(self.present_tree, s_cursor)

            begin = self.send_possibility_up(NoutBegin())
            to_be_inserted = self.send_possibility_up(NoutBlock(TextBecome(ti.text), begin))

            self._bubble_history_up(self.send_possibility_up(
                NoutBlock(Insert(index, to_be_inserted), cursor_node.metadata.nout_hash)), s_cursor)

            self._set_s_cursor(new_s_cursor)
            self._present_nout_updated()
            self.initialize_keyboard()

        btn.bind(on_press=popup.dismiss)
        popup.bind(on_dismiss=popup_dismiss)

        popup.open()
        ti.focus = True

    def _edit_x_text(self, current_text, s_cursor, index, new_s_cursor):
        layout = BoxLayout(spacing=10, orientation='vertical')
        ti = TextInput(text=current_text, size_hint=(1, .9))
        btn = Button(text='Close and save', size_hint=(1, .1,))
        layout.add_widget(ti)
        layout.add_widget(btn)

        popup = Popup(
            title='Edit text', content=layout
            )

        def popup_dismiss(*args):
            # Because of the Modal nature of the popup, we can take the naive approach here and simply insert the
            # results of the popup, trigger the recalc etc. etc. as if this were sequential code.
            cursor_node = self._node_for_s_cursor(self.present_tree, s_cursor)

            begin = self.send_possibility_up(NoutBegin())
            to_be_inserted = self.send_possibility_up(NoutBlock(TextBecome(ti.text), begin))

            self._bubble_history_up(self.send_possibility_up(
                NoutBlock(Replace(index, to_be_inserted), cursor_node.metadata.nout_hash)), s_cursor)

            self._set_s_cursor(new_s_cursor)
            self._present_nout_updated()
            self.initialize_keyboard()

        btn.bind(on_press=popup.dismiss)
        popup.bind(on_dismiss=popup_dismiss)

        popup.open()
        ti.focus = True

    def _delete_current_node(self):
        if self.s_cursor == []:
            # silently ignored ('delete root' is not defined, because the root is assumed to exist.)
            return

        delete_from = self.s_cursor[:-1]
        delete_at = self.s_cursor[-1]

        h = self.send_possibility_up(
            NoutBlock(Delete(delete_at), self._node_for_s_cursor(self.present_tree, delete_from).metadata.nout_hash))

        self._bubble_history_up(h, delete_from)
        self._present_nout_updated()

    # ## Section for drawing boxes
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

    def _nt_for_node_single_line(self, node, s_address):
        is_cursor = s_address == self.s_cursor
        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        t = self._t_for_text("(", is_cursor)
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for i, child in enumerate(node.children):
            nt = self._nt_for_node_single_line(child, s_address + [i])
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", is_cursor)
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            offset_terminals)

    def _nt_for_node_as_todo_list(self, node, s_address):
        is_cursor = s_address == self.s_cursor

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        if len(node.children) == 0:
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text("(...)", is_cursor))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        nt = self._nt_for_node_single_line(node.children[0], s_address + [0])
        offset_nonterminals = [
            no_offset(nt)
        ]
        offset_down = nt.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for i, child in enumerate(node.children[1:]):
            nt = self._nt_for_node_as_todo_list(child, s_address + [i + 1])
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            [])

    def _nt_for_node_as_lispy_layout(self, node, s_address):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz
        is_cursor = s_address == self.s_cursor

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        t = self._t_for_text("(", is_cursor)
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(node.children) > 0:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.
            nt = self._nt_for_node_single_line(node.children[0], s_address + [0])
            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), nt)
            )
            offset_right += nt.outer_dimensions[X]

            if len(node.children) > 1:
                for i, child_x in enumerate(node.children[1:]):
                    nt = self._nt_for_node_as_lispy_layout(child_x, s_address + [i + 1])
                    offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
                    offset_down += nt.outer_dimensions[Y]

                # get the final drawn item to figure out where to put the closing ")"
                last_drawn = nt.get_all_terminals()[-1]
                offset_right += last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

                # go "one line" back up
                offset_down -= last_drawn.item.outer_dimensions[Y]

        else:
            offset_right = t.outer_dimensions[X]

        t = self._t_for_text(")", is_cursor)
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(
            s_address,
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


ColWidths = namedtuple('ColWidths', ('my_hash', 'prev_hash', 'note', 'payload'))


class HistoryWidget(Widget):

    def __init__(self, **kwargs):
        self.possible_timelines = kwargs.pop('possible_timelines')
        self.all_trees = kwargs.pop('all_trees')

        super(HistoryWidget, self).__init__(**kwargs)

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

    def update_nout_hash(self, nout_hash):
        self.nout_hash = nout_hash
        self.refresh()

    def refresh(self, *args):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y])  # default offset: start on top_left

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        if not hasattr(self, 'nout_hash'):
            # This can happen if we call refresh() before being properly initialized... making sure that cannot happen
            # is something for a later date.
            return

        with apply_offset(self.canvas, self.offset):
            self.box_structure = self.some_recursive_thing(self.nout_hash, None, ColWidths(0, 0, 30, 100))
            self._render_box(self.box_structure)

    NOTES_T = {
        BecomeNode: 'N',
        TextBecome: 'T',
        Insert: 'I',
        Replace: 'R',
        Delete: 'D',
    }

    def some_recursive_thing(self, nout_hash, br_nout_hash, col_widths):
        nout = self.possible_timelines.get(nout_hash)
        if nout == NoutBegin():
            # in a later version, we could display BEGIN if that ever proves useful
            return BoxNonTerminal(nout, [], [])

        elif br_nout_hash == nout_hash:
            # we you've drawn this in another branch... stop here.
            # (later, we can draw this in a more fancy way)
            terminals = []  # [no_offset(self._t_for_text("^^^", False, 999))]
            return BoxNonTerminal(nout, [], terminals)

        else:
            recursive_result = self.some_recursive_thing(nout.previous_hash, br_nout_hash, col_widths)
            offset_y = recursive_result.outer_dimensions[Y]

            offset_x = 0
            terminals = []

            cols = [
                (repr(nout_hash), col_widths.my_hash),
                (repr(nout.previous_hash), col_widths.prev_hash),
                (self.NOTES_T[type(nout.note)], col_widths.note),
            ]

            if hasattr(nout.note, 'unicode_'):
                cols.append((nout.note.unicode_, col_widths.payload))
            elif hasattr(nout.note, 'index'):
                cols.append((repr(nout.note.index), col_widths.payload))

            for col_text, col_width in cols:
                if col_width > 0:
                    terminals.append(OffsetBox((offset_x, offset_y), self._t_for_text(col_text, False, col_width)))
                    offset_x += col_width

            non_terminals = [no_offset(recursive_result)]

        if hasattr(nout.note, 'nout_hash'):
            before_replacement = None
            if isinstance(nout.note, Replace):
                # rebuilding the tree for each of these is lazy programming; we'll fix it after the PoC;
                # (because we cache all trees anyway, it's not _that expensive_; but caching all trees is an underlying
                # lazyness)
                tree_before_r = construct_x(self.all_trees, self.possible_timelines, nout.previous_hash)
                before_replacement = tree_before_r.children[nout.note.index].metadata.nout_hash

            horizontal_recursion = self.some_recursive_thing(nout.note.nout_hash, before_replacement, col_widths)
            non_terminals.append(OffsetBox((offset_x, offset_y), horizontal_recursion))

        # TODO: continuation of history.
        # how to do it? not sure, we'll see in a sec

        return BoxNonTerminal(nout, non_terminals, terminals)

    def for_reference(self, possible_timelines, present_nout_hash, indentation, seen):
        # Shows how the Nouts ref recursively
        if present_nout_hash.as_bytes() in seen:
            return (indentation * " ") + ":..."

        seen.add(present_nout_hash.as_bytes())
        present_nout = possible_timelines.get(present_nout_hash)

        if present_nout == NoutBegin():
            result = ""
        else:
            result = self.for_reference(possible_timelines, present_nout.previous_hash, indentation, seen) + "\n\n"

        if hasattr(present_nout, 'note') and hasattr(present_nout.note, 'nout_hash'):
            horizontal_recursion = "\n" + self.for_reference(
                possible_timelines, present_nout.note.nout_hash, indentation + 4, seen)
        else:
            horizontal_recursion = ""

        return result + (indentation * " ") + repr(present_nout) + horizontal_recursion

    def _render_box(self, box):
        # Pure copy/pasta.
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    def _t_for_text(self, text, is_cursor, max_width):
        # copy/pasta with adaptations; we'll factor out the commonalities once they're' known
        # max_width is defined as "max inner width" (arbitrarily; we'll see how that works out; alternatives are
        # outer_width or between margin & padding

        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = min(text_texture.width, max_width)

        # I've found the correct formula for horizontal_scaling (and argument-order of tex_coords) by experimentation
        # rather than understanding. Which is why I'm documenting my findings here.

        # The problem to solve is: when drawing a smaller rectangle than the original (i.e. when cropping for max_width)
        # the original texture is simply scaled to fit the smaller rectangle. This is generally not what we want. As a
        # way around this I discovered tex_coords. The documentation says that the argument order is as such:
        # tex_coords = u, v, u + w, v, u + w, v + h, u, v + h; however, actually reading the value showed the following:
        # tex_coords=(0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0) (i.e. starting in the bottom right)
        # Seeing that the values are in the [0, 1] range, it's obvious that this is a relative expression of scale. In
        # other words: the sought value is the ratio of displayed texture, which is:
        horizontal_scaling = 1 if text_texture.width == 0 else content_width / text_texture.width

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
                size=(content_width, text_texture.height),
                texture=text_texture,
                tex_coords=(0.0, 1.0, horizontal_scaling, 1.0, horizontal_scaling, 0.0, 0.0, 0.0),
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

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

        # While researching max_width I ran into the following potential solution: add the below 3 parameters to the
        # `kw`.  In the end I didn't choose it, because I wanted something even simpler (and without '...' dots)
        # 'text_size': (some_width, None),
        # 'shorten': True,
        # 'shorten_from': 'right',

        label = Label(text=text, **kw)
        label.refresh()
        return label.texture


class TestApp(App):

    def build(self):
        layout = BoxLayout(spacing=10, orientation='horizontal')
        tree = TreeWidget(size_hint=(.2, 1))

        history_widget = HistoryWidget(
            size_hint=(.8, 1),
            possible_timelines=tree.possible_timelines,
            all_trees=tree.all_trees,
            )
        layout.add_widget(history_widget)
        layout.add_widget(tree)

        tree.cursor_channel.connect(history_widget.update_nout_hash)

        tree.focus = True

        return layout

TestApp().run()
