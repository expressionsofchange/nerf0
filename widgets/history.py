from collections import namedtuple

from kivy.core.text import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle
from kivy.metrics import pt
from kivy.uix.behaviors.focus import FocusBehavior


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
from dsn.s_expr.construct_y import construct_y_from_scratch
from dsn.s_expr.h_utils import view_past_from_present, DEAD, DELETED

from posacts import Actuality

from widgets.utils import (
    apply_offset,
    BoxTerminal,
    BoxNonTerminal,
    bring_into_offset,
    OffsetBox,
    X,
    Y,
)
from widgets.layout_constants import (
    DARK_GREY,
    GREY,
    LIGHT_YELLOW,
    MARGIN,
    PADDING,
    PINK,
    RED,
)


ColWidths = namedtuple('ColWidths', ('my_hash', 'prev_hash', 'note', 'payload'))


class HistoryWidget(FocusBehavior, Widget):

    def __init__(self, **kwargs):
        self.possible_timelines = kwargs.pop('possible_timelines')
        self.construct_y_cache = kwargs.pop('construct_y_cache')

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
        # 2. The exact same remarks apply for TreeWidget

        self.ds = EHStructure([], "htn", [0])

        self.bind(pos=self.refresh)
        self.bind(size=self.refresh)

    def parent_cursor_update(self, data):
        do_create = data

        if self.data_channel is not None:
            self.close_channel()

        self.data_channel, do_kickoff = do_create()
        self.send_to_channel, self.close_channel = self.data_channel.connect(self.receive_from_parent)

        do_kickoff()

    def receive_from_parent(self, data):
        # data :: Possibility | Actuality
        # there is no else branch: Possibility only travels _to_ the channel;
        if isinstance(data, Actuality):
            self.update_nout_hash(data.nout_hash)

    def update_nout_hash(self, nout_hash):
        new_htn, new_annotated_hashes = self._trees(nout_hash)

        # TODO here we can implement cursor_safe-guarding behaviors.

        self.ds = EHStructure(
            new_annotated_hashes,
            new_htn,
            self.ds.s_cursor,
        )

        self.refresh()

    def _handle_eh_note(self, eh_note):
        new_s_cursor, posacts, error = eh_note_play(self.possible_timelines, self.ds, eh_note)
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
            new_htn = self.ds.htn
        else:
            new_htn, new_annotated_hashes = self._trees(last_actuality.nout_hash)

        self.ds = EHStructure(
            new_annotated_hashes,
            new_htn,
            new_s_cursor,
        )

        self.refresh()

    def _trees(self, nout_hash):
        new_htn, h2, new_annotated_hashes = construct_y_from_scratch(
            self.construct_y_cache, self.possible_timelines, nout_hash)

        edge_nout_hash, _, _ = new_annotated_hashes[-1]
        liveness_annotated_hashes = view_past_from_present(
            possible_timelines=self.possible_timelines,
            present_root_htn=new_htn,
            annotated_hashes=new_annotated_hashes,

            # Alternatively, we use the knowledge that at the top_level "everything is live"
            alive_at_my_level=list(self.possible_timelines.all_preceding_nout_hashes(edge_nout_hash)),
            )

        return new_htn, liveness_annotated_hashes

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        result = FocusBehavior.keyboard_on_key_down(self, window, keycode, text, modifiers)

        code, textual_code = keycode

        if textual_code in ['left', 'h']:
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
            self.refresh()

        elif textual_code in ['x', 'del']:
            self._handle_eh_note(EHDelete())

        return result

    def refresh(self, *args):
        # As it stands: _PURE_ copy-pasta from TreeWidget;
        """refresh means: redraw (I suppose we could rename, but I believe it's "canonical Kivy" to use 'refresh'"""
        self.canvas.clear()

        self.offset = (self.pos[X], self.pos[Y] + self.size[Y])  # default offset: start on top_left

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size,)

        with apply_offset(self.canvas, self.offset):
            offset_nonterminals = self.draw_past_from_present(
                    self.ds.annotated_hashes, [], ColWidths(150, 150, 30, 100))

            self.box_structure = BoxNonTerminal([], offset_nonterminals, [])
            self._render_box(self.box_structure)

    NOTES_T = {
        BecomeNode: 'N',
        TextBecome: 'T',
        Insert: 'I',
        Replace: 'R',
        Delete: 'D',
    }

    def draw_past_from_present(self, steps_with_aliveness, s_path, col_widths):
        """
        s_path is an s_path at the level of the _history_
        t_path is a t_path on the underlying structure (tree)
        """

        per_step_offset_non_terminals = []
        offset_y = 0

        for i, (nout_hash, dissonant, aliveness, (t, children_steps)) in enumerate(steps_with_aliveness):
            this_s_path = s_path + [i]

            if aliveness == DELETED:
                box_color = Color(*RED)
            elif aliveness == DEAD:
                box_color = Color(*DARK_GREY)
            elif dissonant:
                # I now understand that aliveness & being in dissonant state are orthogonal concerns. We _could_ express
                # that by using another UI element than a color (e.g. strike-through). For now, we'l just stick with
                # pink (with lower priority than RED/GREY)
                box_color = Color(*PINK)
            else:
                box_color = Color(*LIGHT_YELLOW)

            if this_s_path == self.ds.s_cursor:
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
            else:
                if self.display_mode == 't':
                    if t is not None:
                        cols.append(("T: " + repr(t), col_widths.payload))
                if self.display_mode == 's':
                    if hasattr(nout.note, 'index'):
                        cols.append(("S: " + repr(nout.note.index), col_widths.payload))

            for col_text, col_width in cols:
                if col_width > 0:
                    terminals.append(OffsetBox((offset_x, 0), self._t_for_text(col_text, box_color, col_width)))
                    offset_x += col_width

            if t is not None:
                recursive_result = self.draw_past_from_present(children_steps, this_s_path, col_widths)
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

        clicked_item = self.box_structure.from_point(bring_into_offset(self.offset, (touch.x, touch.y)))

        if clicked_item is not None:
            # THIS IS THE ONLY DIFFERENCE WHILE COPY/PASTING
            self._handle_eh_note(EHCursorSet(clicked_item.semantics))
            self.refresh()

        return ret
