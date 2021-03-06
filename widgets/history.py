from collections import namedtuple

from kivy.clock import Clock
from kivy.core.text import Label
from kivy.graphics import Color, Rectangle
from kivy.metrics import pt
from kivy.uix.behaviors.focus import FocusBehavior
from kivy.uix.widget import Widget

from dsn.historiography.legato import (
    HistoriographyNoteNoutHash,
    HistoriographyNoteSlur,
    HistoriographyNoteCapo,
)
from dsn.historiography.clef import SetNoteNoutHash

from dsn.history.clef import (
    EHDelete,
    EHCursorSet,
    EHCursorChild,
    EHCursorDFS,
    EHCursorParent,
)
from dsn.history.construct import eh_note_play
from dsn.history.structure import EHStructure

from dsn.s_expr.clef import (
    BecomeNode,
    Delete,
    Insert,
    Replace,
    TextBecome,
)
from dsn.s_expr.h_utils import view_past_from_present, DEAD, DELETED

from posacts import Actuality

from widgets.utils import (
    annotate_boxes_with_s_addresses,
    apply_offset,
    BoxNonTerminal,
    BoxTerminal,
    bring_into_offset,
    cursor_dimensions,
    from_point,
    OffsetBox,
    X,
    Y,
)
from colorscheme import (
    BLACK,
    CERISE,
    CUTTY_SARK,
    GUARDSMAN_RED,
    WHITE,
)
from widgets.layout_constants import (
    get_font_size,
    MARGIN,
    PADDING,
)

from dsn.viewports.structure import ViewportStructure, VRTC, ViewportContext
from dsn.viewports.construct import play_viewport_note
from dsn.viewports.clef import (
    ViewportContextChange,
    MoveViewportRelativeToCursor,
    CURSOR_TO_BOTTOM,
    CURSOR_TO_CENTER,
    CURSOR_TO_TOP,
    VIEWPORT_LINE_DOWN,
    VIEWPORT_LINE_UP,
)

ColWidths = namedtuple('ColWidths', ('my_hash', 'prev_hash', 'note', 'payload'))


# steps: annotated hash w/ ...

def get_annotated_hash_for_s_address(annotated_hashses, s_address, default=None):
    # Copy/pasta of get_node_for_s_address; but adapted for the "annotated_hashses" interface
    # A similar Ad Hoc function (which returns a list)

    if len(s_address) == 0:
        return default

    i = s_address[0]

    if i >= len(annotated_hashses) - 1:
        return default

    if len(s_address) == 1:
        return annotated_hashses[i]

    return get_annotated_hash_for_s_address(
        annotated_hashses[i].recursive_information.children_steps,
        s_address[1:],
        default)


class HistoryWidget(FocusBehavior, Widget):

    def __init__(self, **kwargs):
        self._invalidated = False

        self.m = kwargs.pop('m')
        self.stores = kwargs.pop('stores')

        self.display_mode = 's'

        # Not the best name ever, but at least it clearly indicates we're talking about the channel which contains
        # information on "data" changes (as opposed to "cursor" changes)
        self.data_channel = None

        super(HistoryWidget, self).__init__(**kwargs)

        # In __init__ we don't have any information available yet on our state. Which means we cannot draw ourselves.
        # This gets fixed the moment we get some data from e.g. our parent. In practice this happens before we get to
        # refresh from e.g. the size/pos bindings, but I'd like to make that flow a bit more explicit.
        #
        # AFAIU:
        # 1. We could basically set any value below.

        self.ds = EHStructure([], [0])

        self.z_pressed = False
        self.viewport_ds = ViewportStructure(
            ViewportContext(0, 0, 0, 0),
            VRTC(0),
        )

        self.bind(pos=self.invalidate)
        self.bind(size=self.invalidate)

    def parent_cursor_update(self, data):
        do_create = data

        if self.data_channel is not None:
            self.close_channel()

        self.data_channel, do_kickoff = do_create()
        self.send_to_channel, self.close_channel = self.data_channel.connect(self.receive_from_parent)

        # If we're bound to a different s_cursor in the parent tree, we unconditionally reset our own cursor:
        self.ds = EHStructure(
            self.ds.annotated_hashes,
            [0],
        )

        do_kickoff()

    def receive_from_parent(self, data):
        # data :: Possibility | Actuality
        # there is no else branch: we take no interest in any Possibilities that might be broadcast on the channel
        if isinstance(data, Actuality):
            self.update_nout_hash(data.nout_hash)

    def update_nout_hash(self, nout_hash):
        new_annotated_hashes = self._trees(nout_hash)

        # For each "tree cursor" change, we reset our own cursor to the end (most recent item)
        # (because the final item may actually contain subitems, this does not necessarily put the viewport at the
        # lowest possible position; this is something to be aware of because it might cause some confusion). At some
        # point this may be automatically solved, e.g. if we change the behavior of cursor-following to be "follow the
        # cursor, making sure it is in-view including the recursive subparts).
        s_cursor = [len(new_annotated_hashes) - 1]

        self.ds = EHStructure(
            new_annotated_hashes,
            s_cursor,
        )

        self._construct_box_structure()

        # If nout_hash update results in a cursor-reset, the desirable behavior is: follow the cursor; if the cursor
        # remains the same, the value of user_moved_cursor doesn't matter. Hence: user_moved_cursor=True
        self._update_viewport_for_change(user_moved_cursor=True)
        self.invalidate()

    def _handle_eh_note(self, eh_note):
        new_s_cursor, posacts, error = eh_note_play(self.stores.note_nout, self.ds, eh_note)
        self._update_internal_state_for_posacts(posacts, new_s_cursor)

    def _update_internal_state_for_posacts(self, posacts, new_s_cursor):
        # Strongly inspired by the equivalent method on TreeWidget
        # Once we start doing this more often, patterns will emerge and we can push for a refactoring
        last_actuality = None

        for posact in posacts:
            # Note: if we don't want to autosave, we should make Actuality-sending conditional here.
            self.send_to_channel(posact)

            if isinstance(posact, Actuality):
                last_actuality = posact

        if last_actuality is None:
            new_annotated_hashes = self.ds.annotated_hashes
        else:
            new_annotated_hashes = self._trees(last_actuality.nout_hash)

        self.ds = EHStructure(
            new_annotated_hashes,
            new_s_cursor,
        )

        self._construct_box_structure()
        self._update_viewport_for_change(user_moved_cursor=True)
        self.invalidate()

    def _trees(self, nout_hash):
        historiography_note_nout = HistoriographyNoteSlur(
            SetNoteNoutHash(nout_hash),
            HistoriographyNoteNoutHash.for_object(HistoriographyNoteCapo()),
        )

        liveness_annotated_hashes = view_past_from_present(
            self.m,
            self.stores,
            historiography_note_nout,
            nout_hash,
            )

        return liveness_annotated_hashes

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        FocusBehavior.keyboard_on_key_down(self, window, keycode, text, modifiers)

        code, textual_code = keycode

        if modifiers == ['ctrl'] and textual_code in ['e', 'y']:
            # For now, these are the only ctrl-key keys we handle; once we get more of those, they should get a better
            # home.
            note = MoveViewportRelativeToCursor({'e': VIEWPORT_LINE_UP, 'y': VIEWPORT_LINE_DOWN}[textual_code])
            self.viewport_ds = play_viewport_note(note, self.viewport_ds)
            self.invalidate()

        elif self.z_pressed:
            self.z_pressed = False
            if textual_code in ['z', 'b', 't']:
                lookup = {
                    'z': CURSOR_TO_CENTER,
                    'b': CURSOR_TO_BOTTOM,
                    't': CURSOR_TO_TOP,
                }
                note = MoveViewportRelativeToCursor(lookup[textual_code])
                self.viewport_ds = play_viewport_note(note, self.viewport_ds)
                self.invalidate()

        elif textual_code in ['z']:
            self.z_pressed = True

        elif textual_code in ['left', 'h']:
            self._handle_eh_note(EHCursorParent())

        elif textual_code in ['right', 'l']:
            self._handle_eh_note(EHCursorChild())

        elif textual_code in ['up', 'k']:
            self._handle_eh_note(EHCursorDFS(-1))

        elif textual_code in ['down', 'j']:
            self._handle_eh_note(EHCursorDFS(1))

        elif textual_code in ['t', 's']:
            # For now I've decided not to put these actions into the EH clef, because they are display-only.
            self.display_mode = textual_code
            self._construct_box_structure()
            self.invalidate()

        elif textual_code in ['x', 'del']:
            self._handle_eh_note(EHDelete())

        return True

    def invalidate(self, *args):
        if not self._invalidated:
            Clock.schedule_once(self.refresh, -1)
            self._invalidated = True

    def _update_viewport_for_change(self, user_moved_cursor):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        cursor_position, cursor_size = cursor_dimensions(self.box_structure, self.ds.s_cursor)

        # In the below, all sizes and positions are brought into the positive integers; there is a mirroring `+` in the
        # offset calculation when we actually apply the viewport.
        context = ViewportContext(
            document_size=self.box_structure.underlying_node.outer_dimensions[Y] * -1,
            viewport_size=self.size[Y],
            cursor_size=cursor_size * -1,
            cursor_position=cursor_position * -1)

        note = ViewportContextChange(
            context=context,
            user_moved_cursor=user_moved_cursor,
        )
        self.viewport_ds = play_viewport_note(note, self.viewport_ds)

    def _construct_box_structure(self):
        offset_nonterminals = self.draw_past_from_present(self.ds.annotated_hashes, ColWidths(0, 0, 30, 250), [])
        self.box_structure = annotate_boxes_with_s_addresses(BoxNonTerminal(offset_nonterminals, []), [])

    def refresh(self, *args):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y] + self.viewport_ds.get_position())

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            self._render_box(self.box_structure.underlying_node)

        self._invalidated = False

    NOTES_T = {
        BecomeNode: 'N',
        TextBecome: 'T',
        Insert: 'I',
        Replace: 'R',
        Delete: 'D',
    }

    def draw_past_from_present(self, steps_with_aliveness, col_widths, s_path):
        per_step_offset_non_terminals = []
        offset_y = 0

        for i, (nout_hash, dissonant, aliveness, rhi) in enumerate(steps_with_aliveness):
            this_s_path = s_path + [i]

            if aliveness == DELETED:
                fg, bg = (WHITE, GUARDSMAN_RED)
            elif aliveness == DEAD:
                fg, bg = (WHITE, CUTTY_SARK)
            elif dissonant:
                # I now understand that aliveness & being in dissonant state are orthogonal concerns. We _could_ express
                # that by using another UI element than a color (e.g. strike-through). For now, we'l just stick with
                # pink (with lower priority than RED/GREY)
                fg, bg = (BLACK, CERISE)
            else:
                fg, bg = (BLACK, WHITE)

            if this_s_path == self.ds.s_cursor:
                fg, bg = (WHITE, BLACK)

            nout = self.stores.note_nout.get(nout_hash)

            offset_x = 0
            terminals = []

            cols = [
                (repr(nout_hash), col_widths.my_hash),
                (repr(nout.previous_hash), col_widths.prev_hash),
                (self.NOTES_T[type(nout.note)], col_widths.note),
            ]

            if hasattr(nout.note, 'unicode_'):
                cols.append((nout.note.unicode_, col_widths.payload))
            else:
                if self.display_mode == 't':
                    if rhi.t_address is not None:
                        cols.append(("T: " + repr(rhi.t_address), col_widths.payload))
                if self.display_mode == 's':
                    if hasattr(nout.note, 'index'):
                        cols.append(("S: " + repr(nout.note.index), col_widths.payload))

            for col_text, col_width in cols:
                if col_width > 0:
                    terminals.append(OffsetBox((offset_x, 0), self._t_for_text(col_text, (fg, bg), col_width)))
                    offset_x += col_width

            if rhi.t_address is not None:
                recursive_result = self.draw_past_from_present(rhi.children_steps, col_widths, this_s_path)
                non_terminals = [OffsetBox((offset_x, o[Y]), nt) for (o, nt) in recursive_result]
            else:
                non_terminals = []

            per_step_result = BoxNonTerminal(non_terminals, terminals)
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

    def _t_for_text(self, text, colors, max_width):
        # copy/pasta with adaptations; we'll factor out the commonalities once they're' known
        # max_width is defined as "max inner width" (arbitrarily; we'll see how that works out; alternatives are
        # outer_width or between margin & padding
        fg, bg = colors

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
            Color(*bg),
            Rectangle(
                pos=(bottom_left[0] + PADDING, bottom_left[1] + PADDING),
                size=(content_width + 2 * MARGIN, content_height + 2 * MARGIN),
                ),
            Color(*fg),

            Rectangle(
                pos=(bottom_left[0] + PADDING + MARGIN, bottom_left[1] + PADDING + MARGIN),
                size=(content_width, text_texture.height),
                texture=text_texture,
                tex_coords=(0.0, 1.0, horizontal_scaling, 1.0, horizontal_scaling, 0.0, 0.0, 0.0),
                ),
        ]

        return BoxTerminal(instructions, bottom_right)

    def _texture_for_text(self, text):
        if text in self.m.texture_for_text:
            return self.m.texture_for_text[text]

        kw = {
            'font_size': pt(get_font_size()),
            # 'font_name': 'Oxygen',
            'bold': False,
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

        self.m.texture_for_text[text] = label.texture
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

        clicked_item = from_point(self.box_structure, bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            # THIS IS THE ONLY DIFFERENCE WHILE COPY/PASTING
            self._handle_eh_note(EHCursorSet(clicked_item.annotation))

        return True
