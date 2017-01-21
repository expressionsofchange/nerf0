from uuid import uuid4

from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import pt
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors.focus import FocusBehavior

from annotations import Annotation
from channel import Channel, ClosableChannel
from construct_x import construct_x

from dsn.editor.clef import (
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

from dsn.editor.construct import edit_note_play, bubble_history_up
from dsn.editor.structure import EditStructure

from posacts import Possibility, Actuality

from dsn.pp.structure import PPNone, PPSingleLine, PPLispy
from dsn.pp.clef import PPUnset, PPSetSingleLine, PPSetLispy
from dsn.pp.construct import construct_pp_tree

from s_address import node_for_s_address
from spacetime import t_address_for_s_address, best_s_address_for_t_address, get_s_address_for_t_address
from trees import TreeNode, TreeText

from widgets.utils import (
    apply_offset,
    no_offset,
    BoxNonTerminal,
    BoxTerminal,
    bring_into_offset,
    OffsetBox,
    X,
    Y,
)

from widgets.layout_constants import (
    MARGIN,
    PADDING,
    PINK,
)

# These are standard Python (and common sense); still... one might occasionally be tempted to think that 'before' is
# moddeled as -1 rather than 0, which is why I made the correct indexes constants
INSERT_BEFORE = 0
INSERT_AFTER = 1


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
        self.all_trees = {}  # TODO pull this to a single higher location for better performance

        self.ds = EditStructure(None, [], [], None)
        self.notify_children = {}

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
            tree = construct_x(self.all_trees, self.possible_timelines, data.nout_hash)

            s_cursor = best_s_address_for_t_address(tree, t_cursor)
            pp_annotations = self.ds.pp_annotations[:]

            self.ds = EditStructure(tree, s_cursor, pp_annotations, construct_pp_tree(tree, pp_annotations))

            # TODO we only really need to broadcast the new t_cursor if it has changed (e.g. because the previously
            # selected t_cursor is no longer valid)
            self.broadcast_cursor_update(t_address_for_s_address(self.ds.tree, self.ds.s_cursor))

            self.refresh()

            for notify_child in self.notify_children.values():
                notify_child()  # (data.nout_hash)

    def channel_closed(self):
        self.closed = True
        self.refresh()

    def broadcast_cursor_update(self, t_address):
        """
        The distinction between "somebody moved the cursor" and "the selected _data_ has changed" is relevant for other
        windows that show something "under the cursor". This is the more so if such windows do not communicate all their
        changes back to us directly (autosave=False).

        The offered choices / information to the user on what to do with the not yet saved stuff may differ in those 2
        cases.

        We don't want to expose our address space (t addresses) to our children, but still want to allow for such a
        distinction. Solution: we broadcast a mechanism `do_create` which may be used to create a data channel.
        """

        def do_create():
            channel, send_to_child, close_child = self._child_channel_for_t_address(t_address)

            def do_kickoff():
                """After the child has connected its listeners to the channel, it wants to know the latest state."""
                # the s_address is expected to exist (and correct): do_kickoff is assumed to be very quick after the
                # cursor move... and you cannot move the cursor to a non-existent place.
                # Regarding using do_kickoff() and do_create() with some time between them: YAGNI.
                s_address = get_s_address_for_t_address(self.ds.tree, t_address)

                assert s_address is not None

                cursor_node = node_for_s_address(self.ds.tree, s_address)
                send_to_child(Actuality(cursor_node.metadata.nout_hash))

            return channel, do_kickoff

        self.cursor_channel.broadcast(do_create)

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
            new_tree = construct_x(self.all_trees, self.possible_timelines, last_actuality.nout_hash)

        self.ds = EditStructure(
            new_tree,
            new_s_cursor,
            self.ds.pp_annotations[:],
            construct_pp_tree(new_tree, self.ds.pp_annotations)
        )

        # TODO we only really need to broadcast the new t_cursor if it has changed.
        self.broadcast_cursor_update(t_address_for_s_address(self.ds.tree, self.ds.s_cursor))

        self.refresh()

        if last_actuality is not None:
            for notify_child in self.notify_children.values():
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

    def _child_channel_for_t_address(self, t_address):
        child_channel = ClosableChannel()

        # more "nerfy" would be: create a chain of creation events; take the latest nout hash (you only need to store
        # the latest)
        channel_id = uuid4().bytes

        def receive_from_child(data):
            # data :: Possibility | Actuality
            if isinstance(data, Possibility):
                self.send_to_channel(data)

            else:  # i.e. isinstance(data, Actuality):
                s_address = get_s_address_for_t_address(self.ds.tree, t_address)
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

        def receive_close_from_child():
            del self.notify_children[channel_id]

        send_to_child, close_child = child_channel.connect(receive_from_child, receive_close_from_child)

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

            s_address = get_s_address_for_t_address(self.ds.tree, t_address)
            if s_address is None:
                # as it stands, it's possible to call close_child() multiple times (which we do). This is ugly but
                # it works (the calls are idempotent)
                close_child()

                # nothing to send to the child, the child represents dead history
                return

            node = node_for_s_address(self.ds.tree, s_address)
            send_to_child(Actuality(node.metadata.nout_hash))  # this kind of always-send behavior can be optimized

        self.notify_children[channel_id] = notify_child
        return child_channel, send_to_child, close_child

    def _create_child_window(self):
        child_lives_at_t_address = t_address_for_s_address(self.ds.tree, self.ds.s_cursor)
        child_channel, _, _ = self._child_channel_for_t_address(child_lives_at_t_address)
        cursor_node = node_for_s_address(self.ds.tree, self.ds.s_cursor)

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
            self.box_structure = self._nt_for_node(self.ds.pp_tree, [], self.ds.pp_tree.underlying_node.broken)
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
    def _t_for_text(self, text, box_color):
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

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
                size=text_texture.size,
                texture=text_texture,
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

    def color_for_cursor(self, is_cursor, broken):
        if is_cursor:
            return Color(0.95, 0.95, 0.95, 1)  # Ad Hoc Grey
        if broken:
            return Color(*PINK)
        return Color(1, 1, 0.97, 1)  # Ad Hoc Light Yellow

    def _nt_for_node(self, annotated_node, s_address, broken):
        lookup = {
            PPNone: self._nt_for_node_single_line,
            PPSingleLine: self._nt_for_node_single_line,
            PPLispy: self._nt_for_node_as_lispy_layout,
        }
        pp_annotation = annotated_node.annotation
        m = lookup[type(pp_annotation)]
        return m(annotated_node, s_address, broken or annotated_node.underlying_node.broken)

    def _nt_for_node_single_line(self, annotated_node, s_address, broken):
        is_cursor = s_address == self.ds.s_cursor
        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(
                self._t_for_text(node.unicode_, self.color_for_cursor(is_cursor, broken)))])

        t = self._t_for_text("(", self.color_for_cursor(is_cursor, broken))
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for i, child in enumerate(annotated_node.children):
            nt = self._nt_for_node_single_line(child, s_address + [i], broken or child.underlying_node.broken)
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", self.color_for_cursor(is_cursor, broken))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            offset_terminals)

    def _nt_for_node_as_todo_list(self, annotated_node, s_address, broken):
        raise Exception("Not updated for the introduction of PP-annotations")
        is_cursor = s_address == self.ds.s_cursor

        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(
                node.unicode_, self.color_for_cursor(is_cursor, broken)))])

        if len(annotated_node.children) == 0:
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(
                "(...)", self.color_for_cursor(is_cursor, broken)))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.
        nt = self._nt_for_node_single_line(
            annotated_node.children[0], s_address + [0], broken or annotated_node.children[0].underlying_node.broken)

        offset_nonterminals = [
            no_offset(nt)
        ]
        offset_down = nt.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for i, child in enumerate(annotated_node.children[1:]):
            nt = self._nt_for_node_as_todo_list(child, s_address + [i + 1], broken or child.underlying_node.broken)
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BoxNonTerminal(
            s_address,
            offset_nonterminals,
            [])

    def _nt_for_node_as_lispy_layout(self, annotated_node, s_address, broken):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz
        is_cursor = s_address == self.ds.s_cursor

        node = annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal(s_address, [], [no_offset(self._t_for_text(
                node.unicode_, self.color_for_cursor(is_cursor, broken)))])

        t = self._t_for_text("(", self.color_for_cursor(is_cursor, broken))
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(annotated_node.children) > 0:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.
            # CHECK! (and potentially remove the warning?)
            nt = self._nt_for_node(
                annotated_node.children[0], s_address + [0],
                broken or annotated_node.children[0].underlying_node.broken)

            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), nt)
            )
            offset_right += nt.outer_dimensions[X]

            if len(annotated_node.children) > 1:
                for i, child_x in enumerate(annotated_node.children[1:]):
                    nt = self._nt_for_node(child_x, s_address + [i + 1], broken or child_x.underlying_node.broken)
                    offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
                    offset_down += nt.outer_dimensions[Y]

                # get the final drawn item to figure out where to put the closing ")"
                last_drawn = nt.get_all_terminals()[-1]
                offset_right += last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

                # go "one line" back up
                offset_down -= last_drawn.item.outer_dimensions[Y]

        else:
            offset_right = t.outer_dimensions[X]

        t = self._t_for_text(")", self.color_for_cursor(is_cursor, broken))
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
