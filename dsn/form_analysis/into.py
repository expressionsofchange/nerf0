"""
## On the funny (temporary) name 'into':

Constructing "into" this Clef, from the s-expr Clef.

I.e. from s-expr notes to form_analysis clef.

This is different from construct.py, which constructs from notes to structures.

Should this be part of the s-expr module or the current one? Object Oriented programmers would fight over this.
Functional programmers point out that you can't know... which is true but not useful in actually making a decision.
"""
from utils import pmts

from dsn.s_expr.clef import BecomeNode, Insert, Replace, Delete
from dsn.s_expr.structure import TreeText, YourOwnHash
from dsn.s_expr.construct_x import construct_x
from dsn.s_expr.legato import NoteCapo, NoteNoutHash

from dsn.form_analysis.constants import VT_INTEGER, VT_STRING
from dsn.form_analysis.clef import (
    ApplicationChangeProcedure,
    ApplicationChangeParameters,
    AtomListBecome,
    AtomListDelete,
    AtomListInsert,
    AtomListReplace,
    BecomeApplication,
    BecomeAtom,
    BecomeDefine,
    BecomeIf,
    BecomeLambda,
    BecomeMalformed,
    BecomeMalformedAtom,
    BecomeQuote,
    BecomeValue,
    BecomeVariable,
    BecomeSequence,
    ChangeSequence,
    ChangeIfPredicate,
    ChangeIfConsequent,
    ChangeIfAlternative,
    ChangeQuote,
    DefineChangeDefinition,
    DefineChangeSymbol,
    FormListDelete,
    FormListInsert,
    FormListReplace,
    LambdaChangeBody,
    LambdaChangeParameters,
)

from dsn.form_analysis.construct import (
    play_form_note,
    play_atom_note,
    play_atom_list_note,
    # play_form_list_note, NOTE why assymmetriccally not imported here...

    construct_form,
    construct_atom,
    construct_atom_list,
)
from dsn.form_analysis.structure import (
    ApplicationForm,
    DefineForm,
    Form,
    FormList,
    IfForm,
    LambdaForm,
    QuoteForm,
    SequenceForm,
)
from dsn.form_analysis.legato import (
    AtomNoteCapo,
    AtomNoteSlur,
    AtomListNoteCapo,
    AtomListNoteSlur,
    FormListNoteCapo,
    FormListNoteSlur,
    FormNoteCapo,
    FormNoteSlur,
)


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


def not_quite_play_form_list(m, stores, s_expr_note, previous_form_list, index_shift):
    """
    This looks somewhat similar to e.g. play_form, but it's not quite symmetric with the other play* functions. The
    differences are described below; once these are more thoroughly understood, a better name for the present function
    may arise as well.

    The regular play* functions take an s-expr note, and translate it into a note in another clef (the one indicated by
    what's in the place of the "*").
    The assumption is that each note instance in the s-expr side will be translated into a note in the other clef; we
    build on this assumption in the construct_*_note functions, which send each consecutive s-expr note to the play*
    functions, and construct a nout-connected equivalent on the other side out of it.

    The translation of s-expr notes into form_list_notes has a slightly different shape.

    As far as I can see this is not a fundamental property of form_lists, but a somewhat coincidental consequence of
    where they are used in practice. Namely: as part of 'begin', 'lambda' and function application. In all 3 cases, the
    created formlists do not have a 1-to-1 correspondance to a single s-expr, but rather are just one of the parts of a
    form. I.e. (begin «the list»), (lambda (params) «the list») and so on.

    In other words: at the places where the present function is called, we check whether the s-expr note's index is
    greater than a certain threshold. If it isn't, it is treated specially (e.g. lambda's params). Only if it is, the
    present function is called, and the threshold (index_shift) is passed. Which means that the present function is not
    always called for each not in the s-expr (no 1-to-1 correspondance)

    This lack of 1-to-1 correspondance is further reflected in the fact that the connecting of resulting notes into
    nouts is done in the present function, as opposed to automatically in a construct* function. That in turn is
    reflected in the type-signature: we don't return a Note, but rather return a hash here.
    """

    pmts(previous_form_list, FormList)

    if isinstance(s_expr_note, Insert) or isinstance(s_expr_note, Replace):
        _, form_note_nh = construct_form_note(m, stores, s_expr_note.nout_hash)

    assert s_expr_note.index >= index_shift, "function may only be called on s_expr_note with index >= index_shift"
    index = s_expr_note.index - index_shift

    if isinstance(s_expr_note, Replace):
        form_list_note = FormListReplace(index, form_note_nh)

    elif isinstance(s_expr_note, Insert):
        form_list_note = FormListInsert(index, form_note_nh)

    elif isinstance(s_expr_note, Delete):
        form_list_note = FormListDelete(index)

    else:
        raise Exception("Programming Error: Incomplete case-analysis: %s" % type(s_expr_note))

    # NOTE: this assumes that we'll store metadata on all 4 types of analysis-[sub]structures.
    previous_form_list_nh = previous_form_list.metadata.nout_hash

    return stores.form_list_note_nout.add(FormListNoteSlur(form_list_note, previous_form_list_nh))


def play_form(m, stores, s_expr_note, previous_s_expr, s_expr, previous_form):
    previous_form is None or pmts(previous_form, Form)

    if isinstance(s_expr, TreeText):
        # Because we don't distinguish between Become & Set yet, we don't have to consider the previous_form at this
        # point: we always Become anyway.

        if is_number(s_expr.unicode_):
            return BecomeValue(VT_INTEGER, int(s_expr.unicode_))

        if is_string(s_expr.unicode_):
            return BecomeValue(VT_STRING, parse_string(s_expr.unicode_))

        # All other atoms are considered to be variables.
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

        _, s = construct_atom_note(m, stores, s_expr.children[1].metadata.nout_hash)
        _, d = construct_form_note(m, stores, s_expr.children[2].metadata.nout_hash)

        # TODO The note below should be lifted to a more general design-document when this is available:
        # A note on the bubbling up of brokenness: we take the most general approach, of doing as little "automatic"
        # bubbling up as possible. Particularly: if any given level of the s-expr tree appears to be well-formed, the
        # mapping to the appropriate form is made, regardless of whether the children of the s-expression are
        # well-formed.
        # This allows for as much preservation of meaningful history as possible, while retaining the possibility of (in
        # an independent, potentially incrementally implemented, phase) determining whether a form and any of its
        # descendendants is well-formed.

        if not isinstance(previous_form, DefineForm):
            return BecomeDefine(s, d)

        # At this point, we're "almost sure" that we're dealing with a Replace on either children[1] or children[2]:
        # Any length-changers would not have children's length be 3 both before and after the operation. Which leaves us
        # with the somewhat pathological case of Replacing the list-tag with the same tag, which we'll deal with without
        # crashing by using Become; All other cases point to an error in my thinking and will dynamically raise an
        # exception.
        assert isinstance(s_expr_note, Replace), "An error in Klaas' thinking has been exposed"

        if s_expr_note.index == 0:
            # The pathological case mentioned above.
            return BecomeDefine(s, d)

        if s_expr_note.index == 1:
            return DefineChangeSymbol(s)

        return DefineChangeDefinition(d)

    if tagged_list_tag == "lambda":
        if len(s_expr.children) < 3:  # (tag, parameters, «body-expressions»)
            return BecomeMalformed()

        _, parameters = construct_atom_list_note(m, stores, s_expr.children[1].metadata.nout_hash)

        if not isinstance(previous_form, LambdaForm):
            return BecomeLambda(parameters, concoct_form_list_history(m, stores, s_expr.children[2:]))

        if isinstance(s_expr_note, Replace) and s_expr_note.index == 1:
            return LambdaChangeParameters(parameters)

        if s_expr_note.index <= 1:
            # Any other change to a child <= 1 is interpreted as BecomeLambda. Such a change can either be a direct
            # tag-change, or some change that, at the level of s-expr-manipuliation, doesn't respect the natural
            # boundaries of meaning as they exist on the form-analysis. (i.e. delete/insert at position or 1)

            # This is a general property of clef-to-clef mappings: the fact that we have the following 5 valid elements
            # does not imply we have a meaningful interpretation of the 6th (the "?")

            #               Pre-Structure       Note        Post-Structure
            # Pre-Clef      Yes                 Yes         Yes
            # Post-Clef     Yes                  ?          Yes

            # NOTE: a more history-preserving way of concocting would be to look at s_expr's history through the window
            # of children[2:], but this is not entirely trivial. Here's a sketch anyway:
            # * operations to children w/ index >= 2 may be mapped by decrementing the index with 2
            # * deletions on any index < 2 map to deletion of index=0
            # * insertions to any index < 2 map to some new element (but not always the inserted one) at index=0)
            return BecomeLambda(parameters, concoct_form_list_history(m, stores, s_expr.children[2:]))

        index_shift = 2  # ignore lambda-tag & params
        form_list_nout_hash = not_quite_play_form_list(m, stores, s_expr_note, previous_form.body, index_shift)

        return LambdaChangeBody(form_list_nout_hash)

    if tagged_list_tag == "begin":
        if len(s_expr.children) < 2:  # (tag, «sequence-expressions»)  # i.e. we don't allow for empty sequences
            return BecomeMalformed()

        if not isinstance(previous_form, SequenceForm):
            # Note that this implies: a change to index=0 of some sort (this is true for all similar checks... we may
            # want to lift this comment)
            # see notes on BecomeLambda's usage of concoct_form_list_history for some reservations.
            return BecomeSequence(concoct_form_list_history(m, stores, s_expr.children[1:]))

        # Once we've reached this point, we know there's a change to the actual sequence.
        index_shift = 1  # we ignore the tag 'begin'
        form_list_nout_hash = not_quite_play_form_list(m, stores, s_expr_note, previous_form.sequence, index_shift)

        return ChangeSequence(form_list_nout_hash)

    if tagged_list_tag == "if":
        if len(s_expr.children) != 4:  # (tag, predicate, consequent, alternative)
            # Note: arguably, the alternative is not required, so a more minimal check here is that the length is either
            # 3 or 4. (The use case for this is in the imperative context; in the functional context there is no
            # sensible meaning of an else-less if)
            return BecomeMalformed()

        note_type_for_child_index = {
            1: ChangeIfPredicate,
            2: ChangeIfConsequent,
            3: ChangeIfAlternative,
        }

        if not isinstance(previous_form, IfForm):
            HASH = 1

            args = [
                construct_form_note(m, stores, s_expr.children[i].metadata.nout_hash)[HASH]
                for i in note_type_for_child_index.keys()
                ]

            return BecomeIf(*args)

        # (similar thinking as in "define")
        assert isinstance(s_expr_note, Replace), "An error in Klaas' thinking has been exposed"

        Note = note_type_for_child_index[s_expr_note.index]

        _, child_change = construct_form_note(m, stores, s_expr.children[s_expr_note.index].metadata.nout_hash)

        return Note(child_change)

    # implied else: if no tag is recognized we assume procedure application

    # if len(s_expr.children) == 0 ... is already guarded above (and documented there)

    _, procedure = construct_form_note(m, stores, s_expr.children[0].metadata.nout_hash)

    if not isinstance(previous_form, ApplicationForm):
        # see notes on BecomeLambda's usage of concoct_form_list_history for some reservations.
        return BecomeApplication(
            procedure,
            concoct_form_list_history(m, stores, s_expr.children[1:]))

    if isinstance(s_expr_note, Replace) and s_expr_note.index == 0:
        return ApplicationChangeProcedure(procedure)

    if s_expr_note.index == 0:
        # Similar case as for lambda: too much shifting around to make any sense
        return BecomeApplication(
            procedure,
            concoct_form_list_history(m, stores, s_expr.children[1:]))

    index_shift = 1  # ignore the procedure
    form_list_nout_hash = not_quite_play_form_list(m, stores, s_expr_note, previous_form.arguments, index_shift)

    return ApplicationChangeParameters(form_list_nout_hash)

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

    """


def concoct_form_list_history(m, stores, s_expr_list):
    """'concocts' a form list history, given a list of s-expressions which have histories. Note that our input is a list
    of histories, and our output is the history of a list. This missing information is why the need to concoct exists.
    The implementation of concocting is simply to construct inserts in spatial order."""

    form_list_nh = stores.form_list_note_nout.add(FormListNoteCapo())

    for i, s_expr in enumerate(s_expr_list):
        form_note, form_nh = construct_form_note(m, stores, s_expr.metadata.nout_hash)

        form_list_note = FormListInsert(i, form_nh)

        # NOTE: side-effects through adding to the store
        form_list_nh = stores.form_list_note_nout.add(FormListNoteSlur(form_list_note, form_list_nh))

    return form_list_nh


def play_atom(m_, stores_, s_expr_note_, previous_s_expr_, s_expr, previous_atom_):
    if not isinstance(s_expr, TreeText):
        return BecomeMalformedAtom()

    return BecomeAtom(s_expr.unicode_)


def play_atom_list(m, stores, s_expr_note, previous_s_expr_, s_expr, previous_atom_list_):
    if isinstance(s_expr_note, BecomeNode):
        return AtomListBecome()

    # STEAL FROM CONSTRUCT_X !
    if isinstance(s_expr_note, Delete):
        return AtomListDelete(s_expr_note.index)

    if isinstance(s_expr_note, Delete):
        return AtomListDelete(s_expr_note.index)

    a, a_nh = construct_atom_note(m, stores, s_expr.children[s_expr_note.index].metadata.nout_hash)

    if isinstance(s_expr_note, Replace):
        return AtomListReplace(s_expr_note.index, a_nh)

    if isinstance(s_expr_note, Insert):
        return AtomListInsert(s_expr_note.index, a_nh)

    # By the way: perhaps there's an issue w/ BecomeNode existing in the s-expression Clef, but not here? If so, it will
    # show up soon enough.

    # Indeed there is :-D
    # I will think of a solution over coffee

    # Related question: I haven't yet seen the similar problem on the form list.
    #

    # Something must give.... let's enumerate the options.
    # Not having a 1-to-1 correspondence between the s_expr clef and the atom-list-clef. Meh, for many reasons
    #       1-to-1 correspondence useful everywhere. e.g. in the UI later on
    #       assymmetry is always bad, spreads like an olievlek

    raise Exception("Case analysis fail %s" % type(s_expr_note))


def construct_analysis_note(
        m, stores, edge_nout_hash, memoization_key, store_key, play, play_note, construct_structure, empty_structure,
        Capo, Slur):
    """Generic mechanism to construct any of the 4 types of notes from the form-analysis Clef.

    * play: the mechanism of constructing analysis* notes out of s_expr notes
    * play_note: the mechanism of constructing, for analysis* notes, the associated structure.

    returns :: (note, nout_hash) (both of these are of 1 of the 4 analysis clefs)

    we do this for convenience (i.e. to avoid unnecessary lookups)
    """
    pmts(edge_nout_hash, NoteNoutHash)

    memoization = getattr(m, memoization_key)
    store = getattr(stores, store_key)

    # In the beginning, there is nothing, which we model as `None`
    constructed_note = None
    constructed_structure = empty_structure

    # the below is just a quick & dirty way of constructing the first nout_hash. Because any NoutHashStore contains the
    # Capo, this is actually a side-effect-free operation.
    constructed_nout_hash = store.add(Capo())

    todo = []
    for tup in stores.note_nout.all_nhtups_for_nout_hash(edge_nout_hash):
        if tup.nout_hash in memoization:
            constructed_note, constructed_nout_hash = memoization[tup.nout_hash]

            # NOTE on why we need to construct from first principles.... rather than taking a single step using "play".
            constructed_structure = construct_structure(m, stores, constructed_nout_hash)
            break

        todo.append(tup)

    # The first previous_s_expr is looked up once pre-loop; in the loop itself we simply use the previous loop's value
    if isinstance(tup.nout, NoteCapo):
        previous_s_expr = None  # a more explicit means of modelling this might be desirable.
    else:
        previous_s_expr = construct_x(m, stores, tup.nout.previous_hash)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        s_expr = construct_x(m, stores, edge_nout_hash)

        constructed_note = play(m, stores, note, previous_s_expr, s_expr, constructed_structure)

        # Will we be needing the metadata of the s_expr's notes in the 1-to-1-mapped equivalents in the form world? For
        # now: no need has been established. So we won't do it. But we'll leave it here as a comment:
        # YourOwnHash(edge_nout_hash))
        # The above remark still stands, but since then we _did_ in fact find a usage for YourOwnHash in the present
        # function.

        constructed_nout = Slur(constructed_note, constructed_nout_hash)

        # NOTE: We _add_ to the store here! i.e. we have some side-effects (albeit of a rather constrained sort)
        constructed_nout_hash = store.add(constructed_nout)

        constructed_structure = play_note(
            m, stores, constructed_structure, constructed_note, YourOwnHash(constructed_nout_hash))

        memoization[edge_nout_hash] = constructed_note, constructed_nout_hash

        previous_s_expr = s_expr

    return constructed_note, constructed_nout_hash


def construct_form_note(m, stores, edge_nout_hash):
    return construct_analysis_note(
        m, stores, edge_nout_hash, 'construct_form_note', 'form_note_nout', play_form, play_form_note,
        construct_form, None, FormNoteCapo, FormNoteSlur)


def construct_atom_note(m, stores, edge_nout_hash):
    return construct_analysis_note(
        m, stores, edge_nout_hash, 'construct_atom_note', 'atom_note_nout', play_atom, play_atom_note,
        construct_atom, None, AtomNoteCapo, AtomNoteSlur)


def construct_atom_list_note(m, stores, edge_nout_hash):
    return construct_analysis_note(
        m, stores, edge_nout_hash, 'construct_atom_list_note', 'atom_list_note_nout', play_atom_list,
        play_atom_list_note, construct_atom_list, None, AtomListNoteCapo, AtomListNoteSlur)
