from dsn.s_expr.clef import BecomeNode, TextBecome, Insert
from dsn.s_expr.structure import TreeNode, TreeText
from dsn.s_expr.utils import stored_nouts_for_notes_da_capo


def concoct_history(m_, stores, s_expr):
    """Given an s_expression, concoct a history that produces the s_expression.

    The method of concocting is The Simplest Thing That Could Possibly Work, i.e. in the concocted history things are
    created in the order of (spatial) appearance; each child is added only once using a single Insert (which contains
    the child's entire history).

    The history is returned as a list of NoutAndHash (which have been added to the store, a.k.a. "seen")

    """

    if isinstance(s_expr, TreeNode):
        notes = [BecomeNode()]

        for i, child in enumerate(s_expr.children):
            child_history = concoct_history(m_, stores, child)
            notes.append(Insert(i, child_history[-1].nout_hash))

    if isinstance(s_expr, TreeText):
        notes = [TextBecome(s_expr.unicode_)]

    return list(stored_nouts_for_notes_da_capo(stores.note_nout, notes))  # wrapped in list to ensure it happens
