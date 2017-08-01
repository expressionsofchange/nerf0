"""
## On the funny (temporary) name 'into':

Constructing "into" this Clef, from the s-expr Clef.

I.e. from s-expr notes to form_analysis clef.

This is different from construct.py, which constructs from notes to structures.

Should this be part of the s-expr module or the current one? Object Oriented programmers would fight over this.
Functional programmers point out that you can't know; but this is also useless :-)
"""

from dsn.s_expr.clef import Insert, Replace, Delete
from dsn.s_expr.structure import TreeText
from dsn.s_expr.construct import construct_x

from dsn.form_analyis.clef import (
    BecomeAtom,
    BecomeDefine,
    BecomeLambda,
    BecomeMalformed,
    BecomeMalformedAtom,
    BecomeQuote,
    BecomeValue,
    BecomeVariable,
    ChangeQuote,
    DefineChangeSymbol,
    DefineChangeDefinition,
    FormListDelete,
    FormListInsert,
    FormListReplace,
    LambdaChangeParameters,
    LambdaChangeBody
)
from dsn.form_analyis.structure import QuoteForm, DefineForm, LambdaForm
from dsn.form_analysis.legato import AtomNoteCapo, FormNoteCapo, FormNoteSlur


def is_number(unicode_):
    """TSTTCPW implementation: integers only."""
    return unicode_.isdigit()


def is_string(unicode_):
    """We diverge from standard Lisp somewhat here: because we store our s-expressions and atoms as structured data
    there is no need for closing quotes, and hence no need for other escape mechanisms. We simply use the opening quote
    to mean "the rest of this atom is a string".
    """
    return unicode_[:1] == '"'


def parse_string(unicode_):
    return unicode_[1:]   # drop the opening quote


def play_form(m, stores, s_expr_note, previous_s_expr, s_expr, previous_form):
    if isinstance(s_expr, TreeText):
        # Because we don't distinguish between Become & Set yet, we don't have to consider the previous_form at this
        # point.

        if is_number(s_expr.unicode_):
            return BecomeValue(s_expr.unicode_)

        if is_string(s_expr.unicode_):
            return BecomeValue(parse_string(s_expr.unicode_))

        # All other atoms are considered to be symbols.
        return BecomeVariable(s_expr.unicode_)

    # implied else: isinstance(s_expr, TreeNode)

    if len(s_expr.children) == 0:
        # Trying to interpret the empty list as a lisp form yields an error.
        # Alternatively one could say this is Procedure Application w/o specified a procedure to apply. (This would be
        # the behavior of the interpreter from SICP). However, I'm not sure the added specificity in that scenario
        # actually adds information rather than confusion.
        return BecomeMalformed()

    tagged_list_tag = s_expr.children[0].unicode_ if isinstance(s_expr.children[0], TreeText) else None

    if tagged_list_tag == "quote":
        if len(s_expr.children) != 2:
            return BecomeMalformed()

        s_expr_nout_hash = s_expr.children[1].metadata.nout_hash

        if isinstance(previous_form, QuoteForm):
            return ChangeQuote(s_expr_nout_hash)

        return BecomeQuote(s_expr_nout_hash)

    if tagged_list_tag == "define":
        if len(s_expr.children) != 3:  # (tag, symbol, definition)
            return BecomeMalformed()

        # OK... HIER IS HET AL MIS; return-type of construct_* is a note as it stands, but for recursive constructions
        # we need a nout_hash. Let's take it from there.
        # VERGEET IK DAAR AL HOE DE CONSTRUCTED NOTES MET ELKAAR TE MAKEN HEBBEN? Ik denk het wel... Ik denk dat ik dat
        # gewoon niet zou moeten vergeten.
        # daarna door bij DAARNA_HIER_DOOR
        s = construct_atom(m, stores, s_expr.children[1].metadata.nout_hash)
        d = construct_form(m, stores, s_expr.children[2].metadata.nout_hash)

        # How does brokenness bubble up? TSTTCPW for now is: if any error, just return an error at the present point.
        # TODO TBD; or not... one might equally convincingly say: the present level is fine, it just happens to
        # _contain_ an error (rather than be one). I think I had similar design choices on error/brokennes propagation
        # when constructing malformed histories.

        if not isinstance(previous_form, DefineForm):
            return BecomeDefine(s, d)

        # At this point, we're "almost sure" that we're dealing with a Replace on either children[1] or children[2]:
        # Any length-changers would not have children's length be 3 both before and after the operation. Which leaves us
        # with the somewhat pathological case of Replacing the tag with the same tag, which we'll deal with without
        # crashing by using Become; All other cases point to an error in my thinking and will dynamically raise an
        # exception.

        assert isinstance(s_expr_note, Replace), "An error in Klaas' thinking has been exposed"

        if s_expr_note.index == 0:
            return BecomeDefine(s, d)

        if s_expr_note.index == 1:
            return DefineChangeSymbol(s)

        return DefineChangeDefinition(d)

    if tagged_list_tag == "lambda":
        if len(s_expr.children) < 3:  # (tag, parameters, «body-expressions»)
            return BecomeMalformed()

        parameters = construct_atom(m, stores, s_expr.children[1].metadata.nout_hash)

        if isinstance(s_expr_note, Replace) and s_expr_note.index == 1:
            return LambdaChangeParameters(parameters)

        if s_expr_note.note.index <= 1:
            # Any other change to a child <= 1 is interpreted as BecomeLambda. Such a change can either be a direct
            # tag-change, or some change that, at the level of s-expr-manipuliation, doesn't respect the natural
            # boundaries of meaning as they exist on the form-analyis.

            # This is a general property of clef-to-clef mappings: the fact that we have the following 5 valid elements
            # does not imply we have a meaningful Note on the questionmarks:

            #               Pre-Structure       Note        Post-Structure
            # Pre-Clef      Yes                 Yes         Yes
            # Post-Clef     Yes                 ???         Yes

            # NOTE: a more history-preserving way of concocting would be to look at s_expr's history through the window
            # of children[2:], but this is not entirely trivial (operations to children w/ index >= 2 may simply be
            # mapped by decrementing the index with 2, deletions on any index < 2 map to deletion of index=0, and
            # insertions to any index < 2 map to some new element (but not necessarily the inserted one) appearing at
            # index=0
            return BecomeLambda(parameters, concoct_form_list_history(s_expr.children[2:]))

        if not isinstance(previous_form, LambdaForm):
            return BecomeLambda(parameters, concoct_form_list_history(s_expr.children[2:]))

        # Once we've reached this point, we know there's a change to the lambda's body. The mapping is straightforward:
        # map the types, payload and indices.

        if isinstance(s_expr_note, Insert) or isinstance(s_expr_note, Replace):
            form_note = construct_form(m, stores, s_expr_note.nout_hash)

            # form_note_nout_hash = form_note MORE NEED
            # DAARNA_HIER_DOOR
            # NOTE: Adding to store!
            stores.form_note_nout.add(FormNoteSlur(form_note, prev_how_the_fuck_hash))

        index = s_expr_note.index - 2  # ignore lambda-tag & params

        if isinstance(s_expr_note, Replace):
            form_list_note = FormListReplace(index, form_nout_hash)

        elif isinstance(s_expr_note, Insert):
            form_list_note = FormListInsert(index, form_nout_hash)

        elif isinstance(s_expr_note, Delete):
            form_list_note = FormListDelete(index)

        else:
            raise Exception("Programming Error: Incomplete case-analysis")

        # GEBLVEN BIJ: 2 means of construction must be made.
        # Ik zit al meteen weer na te denken over een ander probleem dat ik al eens eerder had, nl: propagation of
        # "possibilities". In this case it's a bit hairier than normally though, because the possibilities could be of
        # any of the 4 types of Clef we're dealing with.
        # For now, I will just ignore that problem though. I can just write to the store, making a note about how dirty
        # that is.

        # Let's write down the basic idea;
        # note
        # nout (slur) takes: prev hash & the note ?! yes.
        # such a nout may then be added to the store; this yields the hash we're looking for.

        form_list_nout_hash = another_means_of_construction(form_list_note)
        return LambdaChangeBody(form_list_nout_hash)

    """
    # The below is worth preserving in some comment or notebook:

    (Road not taken: trying to be extremely faithful to the paradigm of incrementality, and analyse the s-expr-note
    itself to make statements about whether it might affect your form. I.e. for a list, replace at 0, insert at 0 and
    delete at 0 may change the present Form, but replace at 1 may not. For now we ignore this idea as it is more
    complicated than simply looking at the first element of the result, without actually yielding any better performance
    or clarity)


    Is het feit dat er geen 1-to-1 mapping is dan niet het bewijs dat clef-gebaseerd werken op de s-expressions
    nutteloos is? nee, om een aantal redenen (een aantal andere staat al in het notebook):

    * De kleine stapjes aan de s-expr kant geven leiden tot slechts kleine delta-puzzeltjes
    * localiteit blijft behouden in die puzzeltjes, d.w.z. de delta-puzzeltjes hoeven maar op kleine expressies
          uitgevoerd te worden
    * de interpretatie idem (should we interpret the present thing as a form, parameter list, or ...?)

    * If
        changes to parameter-count: (for now: go into malformed mode)
        changes to either of the 3: recurse

    * Application:
        Paramcount (of the s-expr) is ≥ 1, of the Form ≥ 0

    """

def concoct_form_list_history(s_expr_list):
    """'concocts' a form list history, given a list of s-expressions which have histories. Note that our input is a list
    of histories, and our output is the history of a list. This missing information is why the need to concoct exists.
    The implementation of concocting is simply to construct inserts in spatial order."""

    return TODO


def play_atom(m_, stores_, s_expr_note_, previous_s_expr_, s_expr, previous_atom_):
    if not isinstance(s_expr, TreeText):
        return BecomeMalformedAtom()

    return BecomeAtom(s_expr.unicode_)


def construct_analysis_note(m, stores, edge_nout_hash, memoization_key, play, Capo):
    """Generic mechanism to construct any of the 4 types of notes from the form-analysis Clef.

    edge_nout_hash :: NoutHash (i.e. s-expr)"""

    memoization = getattr(m, memoization_key)

    # In the beginning, there is nothing, which we model as `None`
    constructed = None

    todo = []
    for tup in stores.note_nout.all_nhtups_for_nout_hash(edge_nout_hash):
        if tup.nout_hash in memoization:
            constructed = memoization[tup.nout_hash]
            break

        todo.append(tup)

    # The first previous_s_expr is looked up once pre-loop; in the loop itself we simply use the previous loop's value
    if isinstance(tup.nout, Capo):
        previous_s_expr = None  # a more explicit means of modelling this might be desirable.
    else:
        previous_s_expr = construct_x(m, stores, tup.nout.previous_hash)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        s_expr = construct_x(m, stores, edge_nout)
        constructed = play(m, stores, note, previous_s_expr, s_expr, constructed)

        # A SIMILAR QUESTION TO EARLIER: will we be needing the metadata of the s_expr's notes in the 1-to-1-mapped
        # equivalents in the form world? For now: no need has been established. So we won't do it. But we'll leave it
        # here as a comment: YourOwnHash(edge_nout_hash))

        memoization[edge_nout_hash] = constructed

        previous_s_expr = s_expr

    return constructed

def construct_form(m, stores, edge_nout_hash):
    return construct_analysis_note(m, stores, edge_nout_hash, 'construct_form', play_form, FormNoteCapo)


def construct_atom(m, stores, edge_nout_hash):
    return construct_analysis_note(m, stores, edge_nout_hash, 'construct_atom', play_atom, AtomNoteCapo)
