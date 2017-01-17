from collections import namedtuple
from contextlib import contextmanager
from os.path import isfile

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
from kivy.uix.gridlayout import GridLayout
from kivy.uix.behaviors.focus import FocusBehavior

from clef import (
    BecomeNode,
    Delete,
    Insert,
    Replace,
    TextBecome,
)
from legato import (
    all_preceding_nout_hashes,
)
from construct_x import construct_x
from construct_pp import construct_pp_tree
from s_address import node_for_s_address
from edit_structure import EditStructure
from construct_edits import edit_note_play, bubble_history_up

from pp_annotations import PPNone, PPSingleLine, PPLispy

from annotations import Annotation
from trees import (
    TreeNode,
    TreeText,
)

from construct_y import xxx_construct_y
from historiography import t_lookup

from pp_clef import PPUnset, PPSetSingleLine, PPSetLispy

from posacts import Possibility, Actuality, HashStoreChannelListener, LatestActualityListener
from channel import Channel, ClosableChannel, ignore
from spacetime import t_address_for_s_address, best_s_address_for_t_address, get_s_address_for_t_address

from filehandler import (
    FileWriter,
    initialize_history,
    read_from_file
)

from edit_clef import (
    CursorChild,
    CursorDFS,
    CursorParent,
    CursorSet,
    EDelete,
    InsertNodeChild,
    InsertNodeSibbling,
    TextInsert,
    TextReplace,
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


class TreeWidget(Widget, FocusBehavior):

    def __init__(self, **kwargs):
        # The we keep track of whether we received a "closed" signal from the history_channel; if so we turn grey and
        # immutable. (the latter is implemented, for now, by simply no longer listening to the keyboard).
        #
        # Another option would be to stay mutable (though make it obvious that the changes will not propagate), but not
        # communicate any information back to the (closed) history_channel. A problem with that (in the current
        # architecture) is that "Possibilities" flow over the same channel. This is not possible once the channel is
        # closed, and we'll fail to fetch hashes back from the shared HashStoreChannelListener.
        self.closed = False

        self.history_channel = kwargs.pop('history_channel')
        self.possible_timelines = kwargs.pop('possible_timelines')

        super(TreeWidget, self).__init__(**kwargs)
        self.all_trees = {}

        self.ds = EditStructure(None, [], [], None)
        self.notify_children = []

        self.cursor_channel = Channel()

        self.send_to_channel, _ = self.history_channel.connect(self.receive_from_channel, self.channel_closed)

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

    # ## Section for channel-communication
    def receive_from_channel(self, data):
        # data :: Possibility | Actuality
        # there is no else branch: Possibility only travels _to_ the channel;
        if isinstance(data, Actuality):
            t_cursor = t_address_for_s_address(self.ds.tree, self.ds.s_cursor)
            tree, error = construct_x(self.all_trees, self.possible_timelines, data.nout_hash)
            assert error is False, "Tree-widget blah.. not expected to deal with incorrect histories.."

            s_cursor = best_s_address_for_t_address(tree, t_cursor)
            pp_annotations = self.ds.pp_annotations[:]

            self.ds = EditStructure(tree, s_cursor, pp_annotations, construct_pp_tree(tree, pp_annotations))

            self.cursor_channel.broadcast(node_for_s_address(self.ds.tree, self.ds.s_cursor).metadata.nout_hash)
            self.refresh()

            for notify_child in self.notify_children:
                notify_child()  # (data.nout_hash)

    def channel_closed(self):
        self.closed = True
        self.refresh()

    def _handle_edit_note(self, edit_note):
        new_s_cursor, posacts, error = edit_note_play(self.ds, edit_note)

        self._update_internal_state_for_posacts(posacts, new_s_cursor)

    def _update_internal_state_for_posacts(self, posacts, new_s_cursor):
        last_actuality = None

        for posact in posacts:
            # Note: if we don't want to autosave, we should make Actuality-sending conditional here.
            self.send_to_channel(posact)

            if isinstance(posact, Actuality):
                last_actuality = posact

        if last_actuality is None:
            new_tree = self.ds.tree
        else:
            new_tree, error = construct_x(self.all_trees, self.possible_timelines, last_actuality.nout_hash)
            assert error is False, "Tree-widget blah.. not expected to deal with incorrect histories.."

        self.ds = EditStructure(
            new_tree,
            new_s_cursor,
            self.ds.pp_annotations[:],
            construct_pp_tree(new_tree, self.ds.pp_annotations)
        )
        self.cursor_channel.broadcast(node_for_s_address(self.ds.tree, self.ds.s_cursor).metadata.nout_hash)
        self.refresh()

        if last_actuality is not None:
            for notify_child in self.notify_children:
                notify_child()  # (last_actuality.nout_hash)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if self.closed:
            # See the remarks in __init__
            return

        result = FocusBehavior.keyboard_on_key_down(self, window, keycode, text, modifiers)

        code, textual_code = keycode

        if textual_code in ['left', 'h']:
            self._handle_edit_note(CursorParent())

        elif textual_code in ['right', 'l']:
            self._handle_edit_note(CursorChild())

        elif textual_code in ['up', 'k']:
            self._handle_edit_note(CursorDFS(-1))

        elif textual_code in ['down', 'j']:
            self._handle_edit_note(CursorDFS(1))

        elif textual_code in ['q']:
            self._add_sibbling_text(INSERT_BEFORE)

        elif textual_code in ['w']:
            self._add_child_text()

        elif textual_code in ['e']:
            self._add_sibbling_text(INSERT_AFTER)

        elif textual_code in ['a']:
            self._handle_edit_note(InsertNodeSibbling(INSERT_BEFORE))

        elif textual_code in ['s']:
            self._handle_edit_note(InsertNodeChild())

        elif textual_code in ['d']:
            self._handle_edit_note(InsertNodeSibbling(INSERT_AFTER))

        elif textual_code in ['x', 'del']:
            self._handle_edit_note(EDelete())

        elif textual_code in ['u', 'i', 'o']:  # out of all the arbitrary keys, these are the most arbitrary :-)
            pp_map = {
                'u': PPUnset,
                'i': PPSetSingleLine,
                'o': PPSetLispy,
            }
            pp_note_type = pp_map[textual_code]
            self._change_pp_style(pp_note_type)

        elif textual_code in ['n']:
            self._create_child_window()

        return result

    def _change_pp_style(self, pp_note_type):
        t_address = t_address_for_s_address(self.ds.tree, self.ds.s_cursor)
        pp_note = pp_note_type(t_address)
        annotation = Annotation(self.ds.tree.metadata.nout_hash, pp_note)

        pp_annotations = self.ds.pp_annotations[:] + [annotation]

        pp_tree = construct_pp_tree(self.ds.tree, pp_annotations)

        self.ds = EditStructure(
            self.ds.tree,
            self.ds.s_cursor,
            pp_annotations,
            pp_tree,
        )

        self.refresh()

    def _create_child_window(self):
        child_channel = ClosableChannel()
        child_lives_at_t_address = t_address_for_s_address(self.ds.tree, self.ds.s_cursor)
        cursor_node = node_for_s_address(self.ds.tree, self.ds.s_cursor)

        def receive_from_child(data):
            # data :: Possibility | Actuality
            if isinstance(data, Possibility):
                self.send_to_channel(data)

            else:  # i.e. isinstance(data, Actuality):
                s_address = get_s_address_for_t_address(self.ds.tree, child_lives_at_t_address)
                if s_address is None:
                    # the child represents dead history; its updates are silently ignored.
                    # in practice this "shouldn't happen" in the current version, because closed children no longer
                    # communicate back to us.
                    return

                posacts = bubble_history_up(data.nout_hash, self.ds.tree, s_address)

                # TODO: new_s_cursor should be determined by looking at the pre-change tree, deducing a t_cursor and
                # then setting the new s_cursor based on the t_cursor and the new tree; this is made more
                # complicated because of the current choices in methods (s_cursor-setting integrated w/
                # tree-creation)
                self._update_internal_state_for_posacts(posacts, self.ds.s_cursor)

        # children don't close themselves (yet) so we don't have to listen for it
        send_to_child, close_child = child_channel.connect(receive_from_child, ignore)

        def notify_child():
            # Optimization (and: mental optimization) notes: The present version of notify_child takes no arguments.
            # It simply looks at the latest version of the tree, calculates the node where the child lives and sends
            # that node's hash to the child widget. This also means that we send information to the child when
            # really nothing changed.

            # However, in practice this function is called precisely when new information about the latest hash (for
            # the root node) is available. We could therefore:

            # a] figure out the differences between the 2 hashes (in terms of historiography's live & dead
            #       operations)
            # b] figure out which t_addresses are affected by these changes.
            # c] send the update-information only to children that listen those addresses.
            #       (because a change to a child node always affects all its ancesters, there is no need to be smart
            #       here, it's enough to send the precise match information)
            #
            # This has the additional advantage of being cleaner for the case of deletions: in the optimized
            # algorithm, the deletion is always automatically the last bit of information that happens at a
            # particular t_address (further changes cannot affect the address); [caveats may apply for deletions
            # that become dead because they are on a dead branch]

            s_address = get_s_address_for_t_address(self.ds.tree, child_lives_at_t_address)
            if s_address is None:
                # as it stands, it's possible to call close_child() multiple times (which we do). This is ugly but
                # it works (the calls are idempotent)
                close_child()

                # nothing to send to the child, the child represents dead history
                return

            node = node_for_s_address(self.ds.tree, s_address)
            send_to_child(Actuality(node.metadata.nout_hash))  # this kind of always-send behavior can be optimized

        self.notify_children.append(notify_child)

        new_widget = self.report_new_tree_to_app(child_channel)
        new_widget.receive_from_channel(Actuality(cursor_node.metadata.nout_hash))
        new_widget.report_new_tree_to_app = self.report_new_tree_to_app

    def refresh(self, *args):
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y])  # default offset: start on top_left

        with self.canvas:
            if self.closed:
                Color(0.5, 0.5, 0.5, 1)
            else:
                Color(1, 1, 1, 1)

            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self.box_structure = self._nt_for_node(self.ds.pp_tree, [])
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

        self.focus = True
        touch.grab(self)

        clicked_item = self.box_structure.from_point(bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._handle_edit_note(CursorSet(clicked_item.semantics))

        return ret

    def on_touch_up(self, touch):
        # Taken from the docs: https://kivy.org/docs/guide/inputs.html#grabbing-touch-events
        if touch.grab_current is self:
            self.focus = True
            touch.ungrab(self)
            return True

    # ## Edit-actions that need further user input (i.e. Text-edits)
    def _add_child_text(self):
        cursor_node = node_for_s_address(self.ds.tree, self.ds.s_cursor)
        if not isinstance(cursor_node, TreeNode):
            self._open_text_popup(cursor_node.unicode_, lambda text: self._handle_edit_note(
                TextReplace(self.ds.s_cursor, text)
            ))
            return

        index = len(cursor_node.children)
        self._open_text_popup("", lambda text: self._handle_edit_note(
            TextInsert(self.ds.s_cursor, index, text)
        ))

    def _add_sibbling_text(self, direction):
        if self.ds.s_cursor == []:
            return  # adding sibblings to the root is not possible (it would lead to a forest)

        # because direction is in [0, 1]... no need to minimize/maximize (PROVE!)
        self._open_text_popup("", lambda text: self._handle_edit_note(
            TextInsert(self.ds.s_cursor[:-1], self.ds.s_cursor[-1] + direction, text)
        ))

    def _open_text_popup(self, current_text, callback):
        layout = BoxLayout(spacing=10, orientation='vertical')
        ti = TextInput(text=current_text, size_hint=(1, .9))
        btn = Button(text='Close and save', size_hint=(1, .1,))
        layout.add_widget(ti)
        layout.add_widget(btn)

        popup = Popup(
            title='Edit text', content=layout
            )

        def popup_dismiss(*args):
            # (Tentative):
            # Because of the Modal nature of the popup, we can take the naive approach here and simply insert the
            # results of the popup, trigger the recalc etc. etc. as if this were sequential code.
            callback(ti.text)

        btn.bind(on_press=popup.dismiss)
        popup.bind(on_dismiss=popup_dismiss)

        popup.open()
        ti.focus = True

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

    def _nt_for_node(self, annotated_node, s_address):
        lookup = {
            PPNone: self._nt_for_node_single_line,
            PPSingleLine: self._nt_for_node_single_line,
            PPLispy: self._nt_for_node_as_lispy_layout,
        }
        pp_annotation = annotated_node.annotation
        m = lookup[type(pp_annotation)]
        return m(annotated_node, s_address)

    def _nt_for_node_single_line(self, annotated_node, s_address):
        is_cursor = s_address == self.ds.s_cursor
        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        t = self._t_for_text("(", is_cursor)
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for i, child in enumerate(annotated_node.children):
            nt = self._nt_for_node_single_line(child, s_address + [i])
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", is_cursor)
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            offset_terminals)

    def _nt_for_node_as_todo_list(self, annotated_node, s_address):
        raise Exception("Not updated for the introduction of PP-annotations")
        is_cursor = s_address == self.ds.s_cursor

        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        if len(annotated_node.children) == 0:
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text("(...)", is_cursor))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        nt = self._nt_for_node_single_line(annotated_node.children[0], s_address + [0])
        offset_nonterminals = [
            no_offset(nt)
        ]
        offset_down = nt.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for i, child in enumerate(annotated_node.children[1:]):
            nt = self._nt_for_node_as_todo_list(child, s_address + [i + 1])
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            [])

    def _nt_for_node_as_lispy_layout(self, annotated_node, s_address):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz
        is_cursor = s_address == self.ds.s_cursor

        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(node.unicode_, is_cursor))])

        t = self._t_for_text("(", is_cursor)
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(annotated_node.children) > 0:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.
            nt = self._nt_for_node(annotated_node.children[0], s_address + [0])  # CHECK! (and potentially remove the warning?)
            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), nt)
            )
            offset_right += nt.outer_dimensions[X]

            if len(annotated_node.children) > 1:
                for i, child_x in enumerate(annotated_node.children[1:]):
                    nt = self._nt_for_node(child_x, s_address + [i + 1])
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

GREY = (0.95, 0.95, 0.95, 1)  # Ad Hoc Grey
LIGHT_YELLOW = (1, 1, 0.97, 1)  # Ad Hoc Light Yellow
RED = (1, 0.8, 0.8, 1)  # ad hoc; fine-tune please
DARK_GREY = (0.5, 0.5, 0.5, 1)  # ad hoc; fine-tune please


class HistoryWidget(Widget):

    def __init__(self, **kwargs):
        self.possible_timelines = kwargs.pop('possible_timelines')
        self.all_trees = kwargs.pop('all_trees')

        super(HistoryWidget, self).__init__(**kwargs)

        self.s_cursor = None

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
            yatn, h2, per_step_info = xxx_construct_y(self.possible_timelines, self.nout_hash)
            offset_nonterminals = self.some_recursive_thing(
                yatn,
                per_step_info,
                [],
                list(all_preceding_nout_hashes(self.possible_timelines, self.nout_hash)),
                [],
                ColWidths(150, 150, 30, 100),
                )

            self.box_structure = BoxNonTerminal([], offset_nonterminals, [])
            self._render_box(self.box_structure)

    NOTES_T = {
        BecomeNode: 'N',
        TextBecome: 'T',
        Insert: 'I',
        Replace: 'R',
        Delete: 'D',
    }

    def some_recursive_thing(self, present_root_yatn, per_step_info, t_path, alive_at_my_level, s_path, col_widths):
        """
        s_path is an s_path at the level of the _history_
        t_path is a t_path on the underlying structure (tree)
        """

        per_step_offset_non_terminals = []
        offset_y = 0

        for i, (nout_hash, rhi) in enumerate(per_step_info):
            this_s_path = s_path + [i]

            box_color = Color(*LIGHT_YELLOW)

            if alive_at_my_level is None:
                box_color = Color(*RED)  # deleted b/c of parent
            else:
                if nout_hash not in alive_at_my_level:
                    box_color = Color(*DARK_GREY)  # dead branch

            if this_s_path == self.s_cursor:
                box_color = Color(*GREY)

            nout = self.possible_timelines.get(nout_hash)

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
                    terminals.append(OffsetBox((offset_x, 0), self._t_for_text(col_text, box_color, col_width)))
                    offset_x += col_width

            if rhi is not None:
                t_address, children_steps = rhi

                this_yatn = t_lookup(present_root_yatn, t_path)
                child_s_address = None if this_yatn is None else this_yatn.t2s[t_address]
                if child_s_address is not None:
                    child_historiography_in_present = this_yatn.historiographies[child_s_address]
                    alive_at_child_level = list(
                        all_preceding_nout_hashes(self.possible_timelines, child_historiography_in_present.nout_hash()))
                else:
                    alive_at_child_level = None

                recursive_result = self.some_recursive_thing(
                    present_root_yatn,
                    children_steps,
                    t_path + [t_address],
                    alive_at_child_level,
                    this_s_path,
                    col_widths,
                    )

                non_terminals = [OffsetBox((offset_x, o[Y]), nt) for (o, nt) in recursive_result]
            else:
                non_terminals = []

            per_step_result = BoxNonTerminal(this_s_path, non_terminals, terminals)
            per_step_offset_non_terminals.append(
                OffsetBox((0, offset_y), per_step_result))

            offset_y += per_step_result.outer_dimensions[Y]

        return per_step_offset_non_terminals

    def _render_box(self, box):
        # Pure copy/pasta.
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    def _t_for_text(self, text, box_color, max_width):
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

    # Mouse handling: PURE COPY/PASTA (for now) from TreeWidget

    def on_touch_down(self, touch):
        # see https://kivy.org/docs/guide/inputs.html#touch-event-basics
        # Basically:
        # 1. Kivy (intentionally) does not limit its passing of touch events to widgets that it applies to, you
        #   need to do this youself
        # 2. You need to call super and return its value
        ret = super(HistoryWidget, self).on_touch_down(touch)

        if not self.collide_point(*touch.pos):
            return ret

        self.focus = True
        touch.grab(self)

        clicked_item = self.box_structure.from_point(bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            # THIS IS THE ONLY DIFFERENCE WHILE COPY/PASTING
            self.s_cursor = clicked_item.semantics
            self.refresh()

        return ret

    def on_touch_up(self, touch):
        # Taken from the docs: https://kivy.org/docs/guide/inputs.html#grabbing-touch-events
        if touch.grab_current is self:
            self.focus = True
            touch.ungrab(self)
            return True


class TestApp(App):

    def __init__(self, *args, **kwargs):
        super(TestApp, self).__init__(*args, **kwargs)

        self.setup_channels()
        self.do_initial_file_read()

    def setup_channels(self):
        # This is the main channel of PosActs for our application.
        self.history_channel = ClosableChannel()  # Pun not intended
        self.possible_timelines = HashStoreChannelListener(self.history_channel).possible_timelines
        self.lnh = LatestActualityListener(self.history_channel)

    def do_initial_file_read(self):
        filename = 'test3'
        if isfile(filename):
            # ReadFromFile before connecting to the Writer to ensure that reading from the file does not write to it
            read_from_file(filename, self.history_channel)
            FileWriter(self.history_channel, filename)
        else:
            # FileWriter first to ensure that the initialization becomes part of the file.
            FileWriter(self.history_channel, filename)
            initialize_history(self.history_channel)

    def add_tree_and_stuff(self, history_channel):
        horizontal_layout = BoxLayout(spacing=10, orientation='horizontal')

        tree = TreeWidget(
            size_hint=(.2, 1),
            possible_timelines=self.possible_timelines,
            history_channel=history_channel,
            )

        history_widget = HistoryWidget(
            size_hint=(.8, 1),
            possible_timelines=tree.possible_timelines,
            all_trees=tree.all_trees,
            )
        horizontal_layout.add_widget(history_widget)
        horizontal_layout.add_widget(tree)

        self.vertical_layout.add_widget(horizontal_layout)

        tree.cursor_channel.connect(history_widget.update_nout_hash)
        tree.focus = True
        return tree

    def build(self):
        self.vertical_layout = GridLayout(spacing=10, cols=1)

        tree = self.add_tree_and_stuff(self.history_channel)
        tree.report_new_tree_to_app = self.add_tree_and_stuff

        # we kick off with the state so far
        tree.receive_from_channel(Actuality(self.lnh.nout_hash))

        return self.vertical_layout

TestApp().run()
