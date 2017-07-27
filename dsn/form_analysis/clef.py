"""
In the design of this Clef, the usual questions re-emerge. This time with a vengeneance though. Some highlights:

* Should we distinguish between BecomeX and SetX if X is a single-valued thing?
    TBD how this plays out; we'll start with TSTTCPW

    * Pros: These are very different beasts. E.g. doing so allows us to express "this variable changed in name, but was
        present before that moment".

    * Cons: More notes.

    * Cons: If changing the value generally has the meaning "re-analyse this thing completely" anyway, distinguishing is
        meaningless anyway.

* How can we express that BecomeX can only be followed by SetX operations?
    We might actually be able to do this using a grammar of notes (which can be mapped to datatypes, and hence types)
    Like so:

    History = [TypedFormNote]

    TypedFormNote ::=
        BecomeX XSet* |
        BecomeY YSet* |

    XSet ::=
        XSetOperation0
        XSetOperation1

    ...

    This is just another way of saying "The Setters must be put inside their relevant Become operations". The
    disadvantage of such is a notation is that SetX operations get grouped inside their associated Become operation;
    On the other hand: you don't actually need to store it as such, you could just use the grammar as a means to
    determine correctness only, and still store the stream of notes as a single stream. Compared with Grammars &
    Parsers: CST vs. AST. Grammars are also able to express such things as "There may only be a single Become in this
    history (at the beginning)"


Thoughts on 27/07/2017 about BecomeNotes, and their parameters:
The most recent idea is: let's have the Become* notes take, for all fields of the Structure to become, a full history.
This is contrasted with the alternative of having Become* notes take no parameters at all, and always building up the
actual structures' contents only after creation.

The reason I'm (currently) settling on this approach of "create with history" is that it enables to express the scenario
of becoming a certain form only after the contents already exist, e.g. by correcting (laambda (x) x) to (lambda (x) x)
In such a scenario it's nice to be able to express that on the moment of creation of lambda the body & parameters
already existed (which would not be possible when you don't have 'create with history') but also what their histories
were on that moment of becoming lambda.
"""


class FormNote(object):
    pass


class FormChangeNote(FormNote):
    """Abstract base class for Notes that represent, for some Form under consideration the change of a single subfield
    which is also of type Form. Hence, the subfield's change is represented as the replacing of that field with a full
    history of a replacement Form (hence: form_nout_hash)."""

    def __init__(self, form_nout_hash):
        self.form_nout_hash = form_nout_hash


# Malformed: Become only (to be Malformed is not to have any meaningful mechanisms for further change)
class BecomeMalformed(FormNote):
    pass


# VariableForm:
class BecomeVariable(FormNote):
    def __init__(self, symbol):
        # Note: BecomeVariable (and BecomeValue) are not expressed using a symbol_nout_hash as their parameter, but
        # instead take a single `atom`.

        # This is in contrast with all other notes; e.g. DefineChangeSymbol takes a full history for symbol, similarly
        # ApplicationChangeParameters (although in that case the operation is on a _list_ of symbols). The reason for
        # this apparent inconsistancy is that the present Form is nothing other than its only field, whereas the other
        # examples are all multi-field forms. It is therefore not useful to have a separate history for the form and its
        # only field. (Insert joke about "splitting the atom" here).
        self.symbol = symbol  # :: unicode


# ValueForm:
class BecomeValue(FormNote):
    def __init__(self, value):
        self.value = value  # :: unicode


# QuoteForm:
class BecomeQuote(FormNote):
    pass


class ChangeQuote(FormNote):
    def __init__(self, s_expr_nout_hash):
        self.s_expr_nout_hash = s_expr_nout_hash


# IfForm
class BecomeIf(FormNote):
    def __init__(self, predicate, consequent, alternative):
        # All parameters are of type: form_nout_hash
        self.predicate = predicate
        self.consequent = consequent
        self.alternative = alternative


class ChangeIfPredicate(FormChangeNote):
    pass


class ChangeIfConsequent(FormChangeNote):
    pass


class ChangeIfAlternative(FormChangeNote):
    pass


# Define:
class BecomeDefine(FormNote):
    def __init__(self, symbol, definition):
        self.symbol = symbol  # :: symbol_nout_hash
        self.definition = definition  # :: form_nout_hash


class DefineChangeSymbol(FormNote):
    def __init__(self, symbol):
        self.symbol = symbol  # :: symbol_nout_hash


class DefineChangeDefinition(FormChangeNote):
    pass


# Lambda:
class BecomeLambda(FormNote):
    def __init__(self, parameters, body):
        self.parameters = parameters
        self.body = body


class LambdaChangeBody(FormChangeNote):
    pass


class LambdaChangeParameters(FormNote):
    def __init__(self, parameters):
        self.parameters = parameters  # :: atom_list_nout_hash


# Application
class BecomeApplication(FormNote):

    def __init__(self, procedure, arguments):
        self.procedure_note = procedure
        self.arguments = arguments


class ApplicationChangeProcedure(FormChangeNote):
    pass


class ApplicationChangeParameters(FormNote):
    def __init__(self, formlist_nout_hash):
        self.formlist_nout_hash = formlist_nout_hash


class ApplicationParameterInsert(FormNote):
    def __init__(self, index, form_nout_hash):
        self.index = index
        self.form_nout_hash = form_nout_hash


class ApplicationParameterDelete(FormNote):
    def __init__(self, index):
        self.index = index


class ApplicationParameterReplace(FormNote):
    def __init__(self, index, form_nout_hash):
        self.index = index
        self.form_nout_hash = form_nout_hash


# Sequence
class BecomeSequence(FormNote):
    pass


class SequenceInsert(FormNote):
    def __init__(self, index, form_nout_hash):
        self.index = index
        self.form_nout_hash = form_nout_hash


class SequenceDelete(FormNote):
    def __init__(self, index):
        self.index = index


class SequenceReplace(FormNote):
    def __init__(self, index, form_nout_hash):
        self.index = index
        self.form_nout_hash = form_nout_hash


# Below this line: Notes that describe changes to _parts_ of the Forms (in particular: symbols and lists thereof):



# Not present here: FormListNote, because we have ApplicationParameter* and Sequence* instead. (Application parameters
# and Sequence's sequence are the 2 examples of [Form]. I've chosen (for now) to express manipulations of those directly
# as Form notes.

class SetAtomNote(object):

    def __init__(self, unicode_):
        self.unicode_ = unicode_


# Not present here: BecomeAtomList, because it is superfluous; the only actually AtomList is the param-list; when we
# have that, it can be nothing else than a list of atoms.

class AtomListNote(object):
    pass


class AtomInsert(AtomListNote):
    def __init__(self, index, atom_nout_hash):
        self.index = index
        self.atom_nout_hash = atom_nout_hash


class AtomDelete(AtomListNote):
    def __init__(self, index):
        self.index = index


class AtomReplace(AtomListNote):
    def __init__(self, index, atom_nout_hash):
        self.index = index
        self.atom_nout_hash = atom_nout_hash
