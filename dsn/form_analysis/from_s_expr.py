"""
Debug only: a mechanism to construct Form-structures i.e. directly out of s-expressions.

Implemented by concocting a history for the s-expression, and sending that through the usual pipeline.

Some reasons this is debug-only:
* fundamentally, the idea that we work on structures directly, while ignoring their histories
* the fact that we use other debug-only mechanisms, i.e. concoct_history
* the ad hoc, non-shard, introduction of memoization and stores.

At some point in the future we might implement a direct mechanism, which entirely skips the historical view.
Disadvantage: having to duplicate the effort; however, this disadvantage might double as an advantage (the redundant
effort may serve as a reference-implementation for comparison in tests)"""

from dsn.s_expr.concoct import concoct_history

from hashstore import NoutHashStore
from memoization import Stores, Memoization

from dsn.s_expr.legato import NoteNout, NoteCapo, NoteNoutHash

from dsn.historiography.legato import HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo
from dsn.form_analysis.into import construct_form_note
from dsn.form_analysis.construct import construct_form


def from_s_expr(s_expr):
    m = Memoization()
    p = NoutHashStore(NoteNoutHash, NoteNout, NoteCapo)
    historiography_note_nout_store = NoutHashStore(
        HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo)
    stores = Stores(p, historiography_note_nout_store)

    nout_and_hash_list = concoct_history(m, stores, s_expr)

    form_note, form_note_nout_hash = construct_form_note(m, stores, nout_and_hash_list[-1].nout_hash)
    form = construct_form(m, stores, form_note_nout_hash)
    return form
