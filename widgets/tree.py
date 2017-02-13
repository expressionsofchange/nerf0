from collections import namedtuple

from kivy.clock import Clock
from kivy.core.text import Label
from kivy.graphics import Color, Rectangle
from kivy.uix.widget import Widget
from kivy.metrics import pt
from kivy.uix.behaviors.focus import FocusBehavior

from annotations import Annotation
from channel import Channel, ClosableChannel

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

from annotated_tree import annotated_node_factory
from posacts import Possibility, Actuality

from dsn.pp.structure import PPNone, PPSingleLine
from dsn.pp.clef import PPUnset, PPSetSingleLine, PPSetLispy
from dsn.pp.construct import construct_pp_tree

from s_address import node_for_s_address
from spacetime import t_address_for_s_address, best_s_address_for_t_address, get_s_address_for_t_address

from dsn.s_expr.structure import SExpr, TreeNode, TreeText
from dsn.s_expr.construct_x import construct_x

from vim import Vim, DONE_SAVE, DONE_CANCEL

from widgets.utils import (
    annotate_boxes_with_s_addresses,
    apply_offset,
    from_point,
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
)

from colorscheme import (
    AQUA_GREEN,
    BLACK,
    CERISE,
    WHITE,
)

# TSTTCPW for keeping track of the state of our single-line 'vim editor'
VimDS = namedtuple('VimDS', (
    'insert_or_replace',  # "I", "R"
    's_address',
    'vim'  # a vim.py object
    ))

# These are standard Python (and common sense); still... one might occasionally be tempted to think that 'before' is
# moddeled as -1 rather than 0, which is why I made the correct indexes constants
INSERT_BEFORE = 0
INSERT_AFTER = 1


# Multiline modes:
LISPY = 0
SINGLE_LINE = 1


class InheritedRenderingInformation(object):
    """When rendering trees, ancestors may affect how their descendants are rendered.

    Such information is formalized as InheritedRenderingInformation."""

    def __init__(self, multiline_mode):
        self.multiline_mode = multiline_mode


IriAnnotatedNode = annotated_node_factory("IriAnnotatedNode", SExpr, InheritedRenderingInformation)


def construct_lispy_iri_top_down(pp_annotated_node, inherited_information):
    """Constructs the InheritedRenderingInformation in a top-down fashion. Note the difference between the PP
    instructions and the InheritedRenderingInformation: the PP instructions must be viewed in the light of their
    ancestors, the InheritedRenderingInformation can be used without such lookups in the tree, and is therefore more
    easily used. Of course, we must construct it first, which is what we do in the present function.
    """

    # I attempted to write this more generally, as a generic map-over-trees function and a function that operates on a
    # single node; however: the fact that the index of a child is such an important piece of information (it determines
    # SINGLE_LINE mode) made this very unnatural, so I just wrote a single non-generic recursive function instead.

    children = getattr(pp_annotated_node, 'children', [])
    annotated_children = []

    my_information = inherited_information

    if type(pp_annotated_node.annotation) in [PPSingleLine, PPNone]:
        # "no hint" is currently interpreted as "Single line"; this might change in the future.
        my_information = InheritedRenderingInformation(SINGLE_LINE)

    for i, child in enumerate(children):
        if i == 0 or my_information.multiline_mode == SINGLE_LINE:
            # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that
            # we are robust for (we render it as flat text); but it's not the expected use-case.

            # If we were ever to make it a user-decision how to render that child (i.e. allow for a non-single-line
            # override), the below must also be updated (offset_down for child[n > 0] should be non-zero)
            child_information = InheritedRenderingInformation(SINGLE_LINE)
        else:
            child_information = InheritedRenderingInformation(LISPY)

        annotated_children.append(construct_lispy_iri_top_down(child, child_information))

    return IriAnnotatedNode(
        underlying_node=pp_annotated_node.underlying_node,
        annotation=my_information,
        children=annotated_children,
    )


class TreeWidget(FocusBehavior, Widget):

    def __init__(self, **kwargs):
        # The we keep track of whether we received a "closed" signal from the history_channel; if so we turn grey and
        # immutable. (the latter is implemented, for now, by simply no longer listening to the keyboard).
        #
        # Another option would be to stay mutable (though make it obvious that the changes will not propagate), but not
        # communicate any information back to the (closed) history_channel. A problem with that (in the current
        # architecture) is that "Possibilities" flow over the same channel. This is not possible once the channel is
        # closed, and we'll fail to fetch hashes back from the shared HashStoreChannelListener.
        self._invalidated = False
        self.closed = False

        self.m = kwargs.pop('m')
        self.stores = kwargs.pop('stores')
        self.history_channel = kwargs.pop('history_channel')

        super(TreeWidget, self).__init__(**kwargs)

        self.ds = EditStructure(None, [], [], None)
        self.vim_ds = None

        self.notify_children = {}
        self.next_channel_id = 0

        self.cursor_channel = Channel()

        self.send_to_channel, _ = self.history_channel.connect(self.receive_from_channel, self.channel_closed)

        self.bind(pos=self.invalidate)
        self.bind(size=self.invalidate)

    # ## Section for channel-communication
    def receive_from_channel(self, data):
        # data :: Possibility | Actuality
        # there is no else branch: Possibility only travels _to_ the channel;
        if isinstance(data, Actuality):
            t_cursor = t_address_for_s_address(self.ds.tree, self.ds.s_cursor)
            tree = construct_x(self.m, self.stores, data.nout_hash)

            s_cursor = best_s_address_for_t_address(tree, t_cursor)
            pp_annotations = self.ds.pp_annotations[:]

            self.ds = EditStructure(tree, s_cursor, pp_annotations, construct_pp_tree(tree, pp_annotations))

            # TODO we only really need to broadcast the new t_cursor if it has changed (e.g. because the previously
            # selected t_cursor is no longer valid)
            self.broadcast_cursor_update(t_address_for_s_address(self.ds.tree, self.ds.s_cursor))

            self.invalidate()

            for notify_child in self.notify_children.values():
                notify_child()  # (data.nout_hash)

    def channel_closed(self):
        self.closed = True
        self.invalidate()

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
            new_tree = construct_x(self.m, self.stores, last_actuality.nout_hash)

        self.ds = EditStructure(
            new_tree,
            new_s_cursor,
            self.ds.pp_annotations[:],
            construct_pp_tree(new_tree, self.ds.pp_annotations)
        )

        # TODO we only really need to broadcast the new t_cursor if it has changed.
        self.broadcast_cursor_update(t_address_for_s_address(self.ds.tree, self.ds.s_cursor))

        self.invalidate()

        if last_actuality is not None:
            for notify_child in self.notify_children.values():
                notify_child()  # (last_actuality.nout_hash)

    def keyboard_on_textinput(self, window, text):
        FocusBehavior.keyboard_on_textinput(self, window, text)
        self.generalized_key_press(text)
        return True

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        FocusBehavior.keyboard_on_key_down(self, window, keycode, text, modifiers)

        code, textual_code = keycode

        also_on_textinput = (
                [chr(ord('a') + i) for i in range(26)] +  # a-z
                [chr(ord('0') + i) for i in range(10)] +  # 0-9
                ['`', '-', '=',  ',', '.', '/', "'", ';', '\\', 'spacebar', 'tab'])

        # these are modifier-keys; we don't independently deal with them, so we ignore them explicitly.
        # on my system, right-alt and right-super are not recognized at present; they show up as '' here;
        # (their keycodes are respectively 1073741925 and 1073742055)
        modifiers = ['alt', 'alt-gr', 'lctrl', 'rctrl', 'rshift', 'shift', 'super', '']

        if textual_code not in modifiers + also_on_textinput:
            self.generalized_key_press(textual_code)

        return True

    def keyboard_on_key_up(self, window, keycode):
        """FocusBehavior automatically defocusses on 'escape'. This is undesirable, so we override without providing any
        behavior ourselves."""
        return True

    def generalized_key_press(self, textual_code):
        """
        Kivy's keyboard-handling is lacking in documentation (or I cannot find it).

        Some (partially) open questions are:

        Q: what are the possible values for keyboard_on_key_down's `keycode` parameter?
        A (partial): It's a tuple: code, textual_code = keycode; code is a number, textual_code is a textual
        representation of it (which, according to the source, is stolen from pygame, although I cannot find the
        original source)

        A (partial): as far as I understand it: the system's keycode gets passed straight to keyboard_on_key_down, via
        kivy.code.Window; Same for keyboard_on_textinput, but with text in that case.

        Q: What is the relationship between keyboard_on_textinput and keyboard_on_key_down?
        A (partial): https://groups.google.com/forum/#!topic/kivy-users/iYwK2uBOZPM

        I need at least the following:
        1. know when the alpha-numeric & interpunction keys are pressed.
        2. the combined effect of combining shift (sometimes this is .upper; but note that this is not so for digits)
            with such a key.
        3. know that "special keys" such as the cursor keys and escape are pressed.

        keyboard_on_key_down provides us with 1 & 3, but not 2; keyboard_on_textinput provides us with 1 & 2 but not 3.
        In cases where keyboard_on_key_down provides us with insufficient information, which has an equivalent in
        keyboard_on_textinput we ignore it. This is done by explicitly enumerating those cases.

        I have _no idea_ how this generalizes to any keyboard other than the one I happen to be typing on...  But for
        now I'm just going to push forward to something that I _do_ understand (and is documented) so that we can at
        least build on that.
        """

        if self.closed:
            # See the remarks in __init__
            return

        if self.vim_ds is not None:
            self.vim_ds.vim.send(textual_code)

            if self.vim_ds.vim.done == DONE_SAVE:
                self.apply_and_close_vim()

            elif self.vim_ds.vim.done == DONE_CANCEL:
                self.vim_ds = None

            self.invalidate()
            return

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

    def apply_and_close_vim(self):
        """apply the vim_ds, and close it:"""
        if self.vim_ds.insert_or_replace == "I":
            # At present, the editor's clef's TextInsert has an interface very similar to the s_expression's clef's
            # TextBecome, namely: (address, index, text). This means we're doing a split of the vim_ds.s_address at the
            # present point. Alternatively, we could change TextInsert to have a single s_address and apply the split at
            # the point of construction.
            self._handle_edit_note(
                TextInsert(self.vim_ds.s_address[:-1], self.vim_ds.s_address[-1], self.vim_ds.vim.text))
        else:
            self._handle_edit_note(TextReplace(self.vim_ds.s_address, self.vim_ds.vim.text))

        self.vim_ds = None

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

        self.invalidate()

    def _child_channel_for_t_address(self, t_address):
        child_channel = ClosableChannel()

        channel_id = self.next_channel_id
        self.next_channel_id += 1

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

    def invalidate(self, *args):
        if not self._invalidated:
            Clock.schedule_once(self.refresh, -1)
            self._invalidated = True

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
            self.box_structure = annotate_boxes_with_s_addresses(self._nts_for_pp_annotated_node(self.ds.pp_tree), [])
            self._render_box(self.box_structure.underlying_node)

        self._invalidated = False

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

        clicked_item = from_point(self.box_structure, bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            self._handle_edit_note(CursorSet(clicked_item.annotation))

        return True

    # ## Edit-actions that need further user input (i.e. Text-edits)
    def _add_child_text(self):
        cursor_node = node_for_s_address(self.ds.tree, self.ds.s_cursor)
        if not isinstance(cursor_node, TreeNode):
            # edit this text node
            self.vim_ds = VimDS("R", self.ds.s_cursor, Vim(cursor_node.unicode_, 0))
            self.invalidate()
            return

        # create a child node, and edit that
        index = len(cursor_node.children)
        self.vim_ds = VimDS("I", self.ds.s_cursor + [index], Vim("", 0))
        self.invalidate()

    def _add_sibbling_text(self, direction):
        if self.ds.s_cursor == []:
            return  # adding sibblings to the root is not possible (it would lead to a forest)

        # because direction is in [0, 1]... no need to minimize/maximize (PROVE!)
        self.vim_ds = VimDS("I", self.ds.s_cursor[:-1] + [self.ds.s_cursor[-1] + direction], Vim("", 0))
        self.invalidate()

    # ## Section for drawing boxes
    def _t_for_text(self, text, colors):
        fg, bg = colors
        text_texture = self._texture_for_text(text)
        content_height = text_texture.height
        content_width = text_texture.width

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - PADDING - MARGIN - content_height - MARGIN - PADDING)
        bottom_right = (bottom_left[X] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[Y])

        instructions = [
            Color(*bg),
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                ),
            Color(*fg),
            Rectangle(
                pos=(bottom_left[0] + PADDING + MARGIN, bottom_left[1] + PADDING + MARGIN),
                size=text_texture.size,
                texture=text_texture,
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

    def _t_for_vim(self, vim):
        # This was created as an ad hoc copy/pasta of _t_for_text. As it stands, it is not an obvious candidate for
        # factoring out commonalities (there aren't that many) but once the opportunity arises we should take it.

        texts = [
            vim.text[:vim.cursor_pos],
            vim.text[vim.cursor_pos:vim.cursor_pos + 1],
            vim.text[vim.cursor_pos + 1:]]

        if len(vim.text) == vim.cursor_pos:
            # if the cursor-position is to the right of the rightmost character (appending to the line), we need some
            # 'imaginary' (not actually drawn, but used for measurements) text as a placeholder.
            texts[1] = '▨'

        text_textures = [self._texture_for_text(text) for text in texts]

        content_height = max([text_texture.height for text_texture in text_textures])
        content_width = sum([text_texture.width for text_texture in text_textures])

        top_left = 0, 0
        bottom_left = (top_left[X], top_left[Y] - PADDING - MARGIN - content_height - MARGIN - PADDING)
        bottom_right = (bottom_left[X] + PADDING + MARGIN + content_width + MARGIN + PADDING, bottom_left[Y])

        instructions = [
            Color(*AQUA_GREEN),
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                ),
        ]

        offset_x = bottom_left[0] + PADDING + MARGIN
        offset_y = bottom_left[1] + PADDING + MARGIN

        for i, text_texture in enumerate(text_textures):
            if i == 1:  # i.e. the cursor
                instructions.extend([
                    Color(*WHITE),
                    Rectangle(
                        pos=(offset_x, offset_y),
                        size=text_texture.size,
                        ),
                ])

            # if this is the cursor, and the cursor is a fake character, don't actually draw it.
            is_cursor_eol = (i == 1 and len(vim.text) == vim.cursor_pos)

            if not is_cursor_eol:
                instructions.extend([
                    Color(*(BLACK if i == 1 else WHITE)),
                    Rectangle(
                        pos=(offset_x, offset_y),
                        size=text_texture.size,
                        texture=text_texture,
                        ),
                ])

            offset_x += text_texture.width

        return BoxTerminal(instructions, bottom_right)

    def colors_for_cursor(self, is_cursor, broken):
        if is_cursor:
            return WHITE, BLACK
        if broken:
            return BLACK, CERISE

        return BLACK, WHITE

    def _nts_for_pp_annotated_node(self, pp_annotated_node):
        iri_annotated_node = construct_lispy_iri_top_down(
            pp_annotated_node,

            # We start LISPY (but if the first PP node is annotated non-lispy, the result will still be a single line)
            InheritedRenderingInformation(LISPY),
        )

        if self.vim_ds is not None:
            vim_nt = BoxNonTerminal([], [no_offset(self._t_for_vim(self.vim_ds.vim))])
            exception = (self.vim_ds.s_address, self.vim_ds.insert_or_replace, vim_nt)
            return self.bottom_up_construct_with_exception(self._nt_for_iri, exception, iri_annotated_node, [])

        return self.bottom_up_construct(self._nt_for_iri, iri_annotated_node, [])

    def bottom_up_construct_with_exception(self, f, exception, node, s_address):
        exception_s_address, exception_type, exception_value = exception

        # If we're not on the exception's branch, we proceed as usual.
        if exception_s_address[len(s_address):] == s_address:
            return self.bottom_up_construct(f, node, s_address)

        constructed_children = []
        for i, child in enumerate(node.children):
            constructed_children.append(self.bottom_up_construct_with_exception(f, exception, child, s_address + [i]))

        if exception_s_address[:-1] == s_address:
            constructed_child = exception_value
            if exception_type == 'R':
                constructed_children[exception_s_address[-1]] = constructed_child
            else:
                constructed_children.insert(exception_s_address[-1], constructed_child)

        return f(node, constructed_children, s_address)

    def bottom_up_construct(self, f, node, s_address):
        children = [self.bottom_up_construct(f, child, s_address + [i]) for i, child in enumerate(node.children)]
        return f(node, children, s_address)

    def _nt_for_iri(self, iri_annotated_node, children_nts, s_address):
        # in some future version, rendering of `is_cursor` in a different color should not be part of the main drawing
        # mechanism, but as some separate "layer". The idea is: things that are likely to change should be drawn on top
        # of things that are very stable (and can therefore be cached).
        is_cursor = s_address == self.ds.s_cursor

        if iri_annotated_node.annotation.multiline_mode == LISPY:
            f = self._nt_for_node_as_lispy_layout
        else:  # SINGLE_LINE
            f = self._nt_for_node_single_line

        return f(iri_annotated_node, children_nts, is_cursor)

    def _nt_for_node_single_line(self, iri_annotated_node, children_nts, is_cursor):
        broken = iri_annotated_node.underlying_node.broken
        node = iri_annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal([], [no_offset(
                self._t_for_text(node.unicode_, self.colors_for_cursor(is_cursor, broken)))])

        t = self._t_for_text("(", self.colors_for_cursor(is_cursor, broken))
        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        offset_right = t.outer_dimensions[X]
        offset_down = 0

        for nt in children_nts:
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_right += nt.outer_dimensions[X]

        t = self._t_for_text(")", self.colors_for_cursor(is_cursor, broken))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _nt_for_node_as_todo_list(self, iri_annotated_node, children_nts, is_cursor):
        raise Exception("Not updated for the introduction of PP-annotations")
        broken = iri_annotated_node.underlying_node.broken

        node = iri_annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal([], [no_offset(self._t_for_text(
                node.unicode_, self.colors_for_cursor(is_cursor, broken)))])

        if len(children_nts) == 0:
            return BoxNonTerminal([], [no_offset(self._t_for_text(
                "(...)", self.colors_for_cursor(is_cursor, broken)))])

        # The fact that the first child may in fact _not_ be simply text, but any arbitrary tree, is a scenario that we
        # are robust for (we render it as flat text); but it's not the expected use-case.

        # WHEN_RESTORING: "first child is single line" should be pushed into the "top down" functionality
        nt = children_nts[0]
        offset_nonterminals = [
            no_offset(nt)
        ]
        offset_down = nt.outer_dimensions[Y]
        offset_right = 50  # Magic number for indentation

        for nt in children_nts[1:]:
            offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
            offset_down += nt.outer_dimensions[Y]

        return BoxNonTerminal(offset_nonterminals, [])

    def _nt_for_node_as_lispy_layout(self, iri_annotated_node, children_nts, is_cursor):
        # "Lisp Style indentation, i.e. xxx yyy
        #                                   zzz
        broken = iri_annotated_node.underlying_node.broken

        node = iri_annotated_node.underlying_node

        if isinstance(node, TreeText):
            return BoxNonTerminal([], [no_offset(self._t_for_text(
                node.unicode_, self.colors_for_cursor(is_cursor, broken)))])

        t = self._t_for_text("(", self.colors_for_cursor(is_cursor, broken))
        offset_right = t.outer_dimensions[X]
        offset_down = 0

        offset_terminals = [
            no_offset(t),
        ]
        offset_nonterminals = []

        if len(children_nts) > 0:
            nt = children_nts[0]

            offset_nonterminals.append(
                OffsetBox((offset_right, offset_down), nt)
            )
            offset_right += nt.outer_dimensions[X]

            if len(children_nts) > 1:
                for nt in children_nts[1:]:
                    offset_nonterminals.append(OffsetBox((offset_right, offset_down), nt))
                    offset_down += nt.outer_dimensions[Y]

                # get the final drawn item to figure out where to put the closing ")"
                last_drawn = nt.get_all_terminals()[-1]
                offset_right += last_drawn.item.outer_dimensions[X] + last_drawn.offset[X]

                # go "one line" back up
                offset_down -= last_drawn.item.outer_dimensions[Y]

        else:
            offset_right = t.outer_dimensions[X]

        t = self._t_for_text(")", self.colors_for_cursor(is_cursor, broken))
        offset_terminals.append(OffsetBox((offset_right, offset_down), t))

        return BoxNonTerminal(offset_nonterminals, offset_terminals)

    def _render_box(self, box):
        for o, t in box.offset_terminals:
            with apply_offset(self.canvas, o):
                for instruction in t.instructions:
                    self.canvas.add(instruction)

        for o, nt in box.offset_nonterminals:
            with apply_offset(self.canvas, o):
                self._render_box(nt)

    def _texture_for_text(self, text):
        if text in self.m.texture_for_text:
            return self.m.texture_for_text[text]

        kw = {
            'font_size': pt(14),
            'font_name': 'Oxygen',
            'bold': False,
            'anchor_x': 'left',
            'anchor_y': 'top',
            'padding_x': 0,
            'padding_y': 0,
            'padding': (0, 0)}

        label = Label(text=text, **kw)
        label.refresh()

        self.m.texture_for_text[text] = label.texture
        return label.texture
