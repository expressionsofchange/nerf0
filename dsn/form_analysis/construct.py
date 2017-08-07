from utils import pmts
from list_operations import l_insert, l_delete, l_replace

from dsn.s_expr.construct_x import construct_x
from dsn.s_expr.structure import YourOwnHash  # NOTE this appears to be more general than s_expr alone

from dsn.form_analysis.legato import (
    FormNoteNoutHash,
    FormListNoteNoutHash,
    AtomNoteNoutHash,
)

from dsn.form_analysis.structure import (
    ApplicationForm,
    DefineForm,
    FormList,
    IfForm,
    LambdaForm,
    QuoteForm,
    SequenceForm,
    ValueForm,
    VariableForm,
    MalformedForm,
    Symbol,
)

from dsn.form_analysis.clef import (
    ApplicationChangeProcedure,
    ApplicationChangeParameters,
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
from dsn.form_analysis.legato import (
    FormListNoteCapo,
)


def play_form_note(m, stores, structure, note, metadata_NOT_YET_USED):
    # How to write this? The principled approach is:
    # * start with construction from a structure/note pair. AKA 'play'.
    #
    # * memoization and such will be added after that. Perhaps never to this method at all!
    # * NOTE: part of 'and such' is: metadata (nout_hashes)

    if isinstance(note, BecomeMalformed):
        return MalformedForm()

    if isinstance(note, BecomeValue):
        return ValueForm(note.value)

    if isinstance(note, BecomeVariable):
        return VariableForm(note.symbol)

    if isinstance(note, BecomeQuote):
        s_expr = construct_x(m, stores, note.s_expr_nout_hash)
        return QuoteForm(s_expr)

    if isinstance(note, BecomeDefine):
        symbol = construct_atom(m, stores, note.symbol)
        definition = construct_form(m, stores, note.definition)

        return DefineForm(symbol, definition)

    if isinstance(note, BecomeApplication):
        procedure = construct_form(m, stores, note.procedure)
        parameters = construct_form_list(m, stores, note.parameters)

        return ApplicationForm(procedure, parameters)

    # More become...

    # In all of the below: # TODO CHECK EXISITNG

    if isinstance(note, DefineChangeDefinition):
        definition = construct_form(m, stores, note.form_nout_hash)
        return DefineForm(structure.symbol, definition)

    if isinstance(note, DefineChangeSymbol):
        symbol = construct_atom(m, stores, note.symbol)
        return DefineForm(symbol, structure.definition)

    if isinstance(note, ApplicationChangeParameters):
        parameters = construct_form_list(m, stores, note.parameters)
        return ApplicationForm(structure.procedure, parameters)

    if isinstance(note, ApplicationChangeProcedure):
        procedure = construct_form(m, stores, note.form_nout_hash)

        return ApplicationForm(procedure, structure.arguments)

    raise Exception("Not implemented type %s", type(note).__name__)

    BecomeIf,
    BecomeLambda,
    BecomeSequence,

    IfForm,
    LambdaForm,
    SequenceForm,

    ChangeIfPredicate,
    ChangeIfConsequent,
    ChangeIfAlternative,

    ChangeQuote,

    LambdaChangeBody,
    LambdaChangeParameters,


def play_atom_note(m, stores, structure, note, metadata_NOT_YET_USED):
    if isinstance(note, BecomeMalformedAtom):
        # First thoughts: either as a separate class, as a separate attribute, or by having the symbol None
        raise Exception("Modelling TBD")

    if isinstance(note, BecomeAtom):
        # NOTE the incongruency in naming here!
        # Also note: I'm not 100% sure in which direction to harmonize yet...
        # Arguments are: if it's really always just a symbol, that is a more precise name.
        # Otherwise, it should just be called Atom

        return Symbol(note.symbol)

    raise Exception("Unknown note: %s" % type(note).__name__)


def play_atom_list_note(*args):
    AtomListDelete,
    AtomListInsert,
    AtomListReplace,


def play_form_list_note(m, stores, structure, note, metadata):
    if isinstance(note, FormListInsert):
        if not (0 <= note.index <= len(structure.the_list)):  # Note: insert _at_ len(..) is ok (a.k.a. append)
            raise Exception("Out of bounds: %s" % note.index)

        element = construct_form(m, stores, note.form_nout_hash)
        return FormList(l_insert(structure.the_list, note.index, element), metadata)

    if not (0 <= note.index <= len(structure) - 1):  # For Delete/Replace the check is "inside bounds"
        raise Exception("Out of bounds: %s" % note.index)

    if isinstance(note, FormListDelete):
        return FormList(l_delete(structure.the_list, note.index), metadata)

    if isinstance(note, FormListReplace):
        element = construct_form(m, stores, note.form_nout_hash)
        return FormList(l_replace(structure.the_list, note.index, element), metadata)

    raise Exception("Unknown note %s" % type(note).__name__)


def construct(HashClass, empty_structure, memoization_key, store_key, play, m, stores, edge_nout_hash):
    """This provides a general mechanism for constructing structures by playing notes.

    Refactoring note: this mechanism is so general, that we may want to lift it out of the present module and use it
    elsewhere as well (e.g. "construct_x")
    """
    pmts(edge_nout_hash, HashClass)

    memoization = getattr(m, memoization_key)
    store = getattr(stores, store_key)

    structure = empty_structure

    todo = []
    for tup in store.all_nhtups_for_nout_hash(edge_nout_hash):
        if tup.nout_hash in memoization:
            structure = memoization[tup.nout_hash]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        structure = play(m, stores, structure, note, YourOwnHash(edge_nout_hash))
        memoization[edge_nout_hash] = structure

    return structure


def construct_form(m, stores, edge_nout_hash):
    return construct(
        FormNoteNoutHash, None, 'construct_form', 'form_note_nout', play_form_note,
        m, stores, edge_nout_hash)


def construct_form_list(m, stores, edge_nout_hash):
    # EXPLAIN: this is a trick that works
    capo_nh = stores.form_list_note_nout.add(FormListNoteCapo())

    return construct(
        FormListNoteNoutHash, FormList([], YourOwnHash(capo_nh)), 'construct_form_list', 'form_list_note_nout',
        play_form_list_note,
        m, stores, edge_nout_hash)


def construct_atom(m, stores, edge_nout_hash):
    return construct(
        AtomNoteNoutHash, None, 'construct_atom', 'atom_note_nout', play_atom_note,
        m, stores, edge_nout_hash)
