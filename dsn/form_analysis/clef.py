"""
In the design of this Clef, the usual questions re-emerge. This time with a vengeneance though. Some highlights:

* Should we distinguish between BecomeX and SetX if X is a single-valued thing?
    TBD how this plays out; we'll start with TSTTCPW, which is to have only Become.

    Regarding an approach with both Become & Set, we can remark the following:

    * Pro: These are very different beasts. E.g. doing so allows us to express "this variable changed in name, but was
        present before that moment".

    * Cons: More types of notes.

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

This choice also has an implication on how we deal with FormLists (such as: the list of actual parameters of procedure
application and the list of elements of a sequence). Namely: those are a structure of their own, with their own clef, so
that we may express things such as "this sequence comes into being with the following history of its elements".
"""
from utils import pmts, rfs
from vlq import to_vlq, from_vlq


BECOME_MALFORMED = 0
BECOME_VARIABLE = 1
BECOME_VALUE = 2
BECOME_QUOTE = 3
CHANGE_QUOTE = 4
BECOME_IF = 5
BECOME_DEFINE = 6
DEFINE_CHANGE_SYMBOL = 7
BECOME_LAMBDA = 8
LAMBDA_CHANGE_PARAMETERS = 9
BECOME_APPLICATION = 10
APPLICATION_CHANGE_PARAMETERS = 11
BECOME_SEQUENCE = 12
CHANGE_SEQUENCE = 13
CHANGE_IF_PREDICATE = 14
CHANGE_IF_CONSEQUENT = 15
CHANGE_IF_ALTERNATIVE = 16
DEFINE_CHANGE_DEFINITION = 17
LAMBDA_CHANGE_BODY = 18
APPLICATION_CHANGE_PROCEDURE = 19


FORM_LIST_INSERT = 0
FORM_LIST_DELETE = 1
FORM_LIST_REPLACE = 2


BECOME_ATOM = 0
BECOME_MALFORMED_ATOM = 1


ATOM_LIST_INSERT = 0
ATOM_LIST_DELETE = 1
ATOM_LIST_REPLACE = 2


class FormNote(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            BECOME_MALFORMED: BecomeMalformed,
            BECOME_VARIABLE: BecomeVariable,
            BECOME_VALUE: BecomeValue,
            BECOME_QUOTE: BecomeQuote,
            CHANGE_QUOTE: ChangeQuote,
            BECOME_IF: BecomeIf,
            BECOME_DEFINE: BecomeDefine,
            DEFINE_CHANGE_SYMBOL: DefineChangeSymbol,
            BECOME_LAMBDA: BecomeLambda,
            LAMBDA_CHANGE_PARAMETERS: LambdaChangeParameters,
            BECOME_APPLICATION: BecomeApplication,
            APPLICATION_CHANGE_PARAMETERS: ApplicationChangeParameters,
            BECOME_SEQUENCE: BecomeSequence,
            CHANGE_SEQUENCE: ChangeSequence,
            CHANGE_IF_PREDICATE: ChangeIfPredicate,
            CHANGE_IF_CONSEQUENT: ChangeIfConsequent,
            CHANGE_IF_ALTERNATIVE: ChangeIfAlternative,
            DEFINE_CHANGE_DEFINITION: DefineChangeDefinition,
            LAMBDA_CHANGE_BODY: LambdaChangeBody,
            APPLICATION_CHANGE_PROCEDURE: ApplicationChangeProcedure

        }[byte0].from_stream(byte_stream)


class FormChangeNote(FormNote):
    """Abstract base class for Notes that represent, for some Form under consideration the change of a single subfield
    which is also of type Form. Hence, the subfield's change is represented as the replacing of that field with a full
    history of a replacement Form (hence: form_nout_hash)."""
    TYPE_CONSTANT = NotImplemented

    def __init__(self, form_nout_hash):
        # NOTE on a drawback of this field-name...
        self.form_nout_hash = form_nout_hash

    def as_bytes(self):
        return bytes([self.TYPE_CONSTANT]) + self.form_nout_hash.as_bytes()

    @classmethod
    def from_stream(cls, byte_stream):
        from dsn.form_analysis.legato import FormNoteNoutHash  # Avoids circular imports (just like in s_expr.clef)
        return cls(FormNoteNoutHash.from_stream(byte_stream))


# Malformed: Become only (to be Malformed is not to have any meaningful mechanisms for further change)
class BecomeMalformed(FormNote):

    def as_bytes(self):
        return bytes([BECOME_MALFORMED])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeMalformed()


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
        pmts(symbol, str)
        self.symbol = symbol

    def as_bytes(self):
        utf8 = self.symbol.encode('utf-8')
        return bytes([BECOME_VARIABLE]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return BecomeVariable(str(utf8, 'utf-8'))


# ValueForm:
class BecomeValue(FormNote):
    # TODO (potentially): factor out commonalities w/ BecomeVariable.
    # (that is, unless we diversify values to be more faithful to the underlying object's type)

    def __init__(self, value):
        pmts(value, str)
        self.value = value

    def as_bytes(self):
        utf8 = self.value.encode('utf-8')
        return bytes([BECOME_VALUE]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return BecomeValue(str(utf8, 'utf-8'))


# QuoteForm:
class BecomeQuote(FormNote):

    def __init__(self, s_expr_nout_hash):
        from dsn.s_expr.legato import NoteNoutHash
        pmts(s_expr_nout_hash, NoteNoutHash)
        self.s_expr_nout_hash = s_expr_nout_hash

    def as_bytes(self):
        return bytes([BECOME_QUOTE]) + self.s_expr_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.s_expr.legato import NoteNoutHash
        return BecomeQuote(NoteNoutHash.from_stream(byte_stream))


class ChangeQuote(FormNote):
    # NOTE: commonalities w/ BecomeQuote might be factored out. (That is... if they don't diverge)

    def __init__(self, s_expr_nout_hash):
        from dsn.s_expr.legato import NoteNoutHash
        pmts(s_expr_nout_hash, NoteNoutHash)
        self.s_expr_nout_hash = s_expr_nout_hash

    def as_bytes(self):
        return bytes([CHANGE_QUOTE]) + self.s_expr_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.s_expr.legato import NoteNoutHash
        return ChangeQuote(NoteNoutHash.from_stream(byte_stream))


# IfForm
class BecomeIf(FormNote):
    # Note on some "showerthoughts":
    # Once we introduce case statements, the question arises how If and Case relate to one another. SICP answers this
    # by implementing Case as a bunch of nested If statements. From the perspective of history-tracing this is not a
    # satisfactory answer, which points to: implementing If as a special case of a Case statement, namely that one in
    # which only one case is checked and there is one "otherwise" guard.

    def __init__(self, predicate, consequent, alternative):
        from dsn.form_analysis.legato import FormNoteNoutHash
        for t in [predicate, consequent, alternative]:
            pmts(t, FormNoteNoutHash)

        self.predicate = predicate
        self.consequent = consequent
        self.alternative = alternative

    def as_bytes(self):
        return (bytes([BECOME_IF]) +
                self.predicate.as_bytes() +
                self.consequent.as_bytes() +
                self.alternative.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormNoteNoutHash
        return BecomeIf(FormNoteNoutHash.from_stream(byte_stream), FormNoteNoutHash.from_stream(byte_stream),
                        FormNoteNoutHash.from_stream(byte_stream))


class ChangeIfPredicate(FormChangeNote):
    TYPE_CONSTANT = CHANGE_IF_PREDICATE


class ChangeIfConsequent(FormChangeNote):
    TYPE_CONSTANT = CHANGE_IF_CONSEQUENT


class ChangeIfAlternative(FormChangeNote):
    TYPE_CONSTANT = CHANGE_IF_ALTERNATIVE


# Define:
class BecomeDefine(FormNote):
    def __init__(self, symbol, definition):
        from dsn.form_analysis.legato import AtomNoteNoutHash, FormNoteNoutHash

        pmts(symbol, AtomNoteNoutHash)
        pmts(definition, FormNoteNoutHash)

        self.symbol = symbol
        self.definition = definition

    def as_bytes(self):
        return (bytes([BECOME_DEFINE]) + self.symbol.as_bytes() + self.definition.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomNoteNoutHash, FormNoteNoutHash
        return BecomeDefine(AtomNoteNoutHash.from_stream(byte_stream), FormNoteNoutHash.from_stream(byte_stream))


class DefineChangeSymbol(FormNote):
    def __init__(self, symbol):
        from dsn.form_analysis.legato import AtomNoteNoutHash
        pmts(symbol, AtomNoteNoutHash)

        self.symbol = symbol

    def as_bytes(self):
        return (bytes([DEFINE_CHANGE_SYMBOL]) + self.symbol.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomNoteNoutHash
        return DefineChangeSymbol(AtomNoteNoutHash.from_stream(byte_stream))


class DefineChangeDefinition(FormChangeNote):
    TYPE_CONSTANT = DEFINE_CHANGE_DEFINITION


# Lambda:
class BecomeLambda(FormNote):
    def __init__(self, parameters, body):
        from dsn.form_analysis.legato import AtomListNoteNoutHash, FormListNoteNoutHash

        pmts(parameters, AtomListNoteNoutHash)
        pmts(body, FormListNoteNoutHash)

        self.parameters = parameters
        self.body = body

    def as_bytes(self):
        return (bytes([BECOME_LAMBDA]) + self.parameters.as_bytes() + self.body.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomListNoteNoutHash, FormListNoteNoutHash
        return BecomeLambda(
            AtomListNoteNoutHash.from_stream(byte_stream), FormListNoteNoutHash.from_stream(byte_stream))


class LambdaChangeBody(FormNote):

    def __init__(self, body):
        self.body = body
        from dsn.form_analysis.legato import FormListNoteNoutHash
        pmts(body, FormListNoteNoutHash)

    def as_bytes(self):
        return (bytes([LAMBDA_CHANGE_BODY]) + self.body.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        return LambdaChangeBody(FormListNoteNoutHash.from_stream(byte_stream))


class LambdaChangeParameters(FormNote):
    def __init__(self, parameters):
        from dsn.form_analysis.legato import AtomListNoteNoutHash
        pmts(parameters, AtomListNoteNoutHash)
        self.parameters = parameters

    def as_bytes(self):
        return (bytes([LAMBDA_CHANGE_PARAMETERS]) + self.parameters.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomListNoteNoutHash
        return LambdaChangeParameters(AtomListNoteNoutHash.from_stream(byte_stream))


# Application
class BecomeApplication(FormNote):

    def __init__(self, procedure, parameters):
        from dsn.form_analysis.legato import FormNoteNoutHash, FormListNoteNoutHash

        pmts(procedure, FormNoteNoutHash)
        pmts(parameters, FormListNoteNoutHash)

        self.procedure = procedure
        self.parameters = parameters

    def as_bytes(self):
        return (bytes([BECOME_APPLICATION]) + self.procedure.as_bytes() + self.parameters.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormNoteNoutHash, FormListNoteNoutHash
        return BecomeApplication(
            FormNoteNoutHash.from_stream(byte_stream), FormListNoteNoutHash.from_stream(byte_stream))


class ApplicationChangeProcedure(FormChangeNote):
    TYPE_CONSTANT = APPLICATION_CHANGE_PROCEDURE


class ApplicationChangeParameters(FormNote):
    def __init__(self, parameters):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        pmts(parameters, FormListNoteNoutHash)
        self.parameters = parameters

    def as_bytes(self):
        return (bytes([APPLICATION_CHANGE_PARAMETERS]) + self.parameters.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        return ApplicationChangeParameters(FormListNoteNoutHash.from_stream(byte_stream))


# Sequence
class BecomeSequence(FormNote):
    def __init__(self, sequence):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        pmts(sequence, FormListNoteNoutHash)
        self.sequence = sequence

    def as_bytes(self):
        return (bytes([BECOME_SEQUENCE]) + self.sequence.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        return BecomeSequence(FormListNoteNoutHash.from_stream(byte_stream))


class ChangeSequence(FormNote):
    def __init__(self, sequence):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        pmts(sequence, FormListNoteNoutHash)
        self.sequence = sequence

    def as_bytes(self):
        return (bytes([CHANGE_SEQUENCE]) + self.sequence.as_bytes())

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormListNoteNoutHash
        return ChangeSequence(FormListNoteNoutHash.from_stream(byte_stream))


# Below this line: Notes that describe changes to _parts_ of the Forms (in particular: symbols and lists thereof):
class FormListNote(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            FORM_LIST_INSERT: FormListInsert,
            FORM_LIST_DELETE: FormListDelete,
            FORM_LIST_REPLACE: FormListReplace,
        }[byte0].from_stream(byte_stream)


# Not present here: BecomeFormList, because it is superfluous; whenever a FormList is used it is the only option for
# that field.

class FormListInsert(FormListNote):
    def __init__(self, index, form_nout_hash):
        from dsn.form_analysis.legato import FormNoteNoutHash

        pmts(index, int)
        pmts(form_nout_hash, FormNoteNoutHash)

        self.index = index
        self.form_nout_hash = form_nout_hash

    def as_bytes(self):
        return bytes([FORM_LIST_INSERT]) + to_vlq(self.index) + self.form_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormNoteNoutHash
        return FormListInsert(from_vlq(byte_stream), FormNoteNoutHash.from_stream(byte_stream))


class FormListDelete(FormListNote):
    def __init__(self, index):
        pmts(index, int)
        self.index = index

    def as_bytes(self):
        return bytes([FORM_LIST_DELETE]) + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return FormListDelete(from_vlq(byte_stream))


class FormListReplace(FormListNote):
    def __init__(self, index, form_nout_hash):
        from dsn.form_analysis.legato import FormNoteNoutHash

        pmts(index, int)
        pmts(form_nout_hash, FormNoteNoutHash)

        self.index = index
        self.form_nout_hash = form_nout_hash

    def as_bytes(self):
        return bytes([FORM_LIST_REPLACE]) + to_vlq(self.index) + self.form_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import FormNoteNoutHash
        return FormListReplace(from_vlq(byte_stream), FormNoteNoutHash.from_stream(byte_stream))


class AtomNote(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            BECOME_ATOM: BecomeAtom,
            BECOME_MALFORMED_ATOM: BecomeMalformedAtom,
        }[byte0].from_stream(byte_stream)


class BecomeAtom(AtomNote):

    def __init__(self, symbol):
        pmts(symbol, str)
        self.symbol = symbol

    def as_bytes(self):
        utf8 = self.symbol.encode('utf-8')
        return bytes([BECOME_ATOM]) + to_vlq(len(utf8)) + utf8

    @staticmethod
    def from_stream(byte_stream):
        length = from_vlq(byte_stream)
        utf8 = rfs(byte_stream, length)
        return BecomeAtom(str(utf8, 'utf-8'))


class BecomeMalformedAtom(AtomNote):

    def as_bytes(self):
        return bytes([BECOME_MALFORMED_ATOM])

    @staticmethod
    def from_stream(byte_stream):
        return BecomeMalformedAtom()


class AtomListNote(object):

    @staticmethod
    def from_stream(byte_stream):
        byte0 = next(byte_stream)
        return {
            ATOM_LIST_INSERT: AtomListInsert,
            ATOM_LIST_DELETE: AtomListDelete,
            ATOM_LIST_REPLACE: AtomListReplace,
        }[byte0].from_stream(byte_stream)


# Not present here: BecomeAtomList, because it is superfluous; the only actually AtomList is the param-list; when we
# have that, it can be nothing else than a list of atoms.


class AtomListInsert(AtomListNote):
    def __init__(self, index, atom_nout_hash):
        from dsn.form_analysis.legato import AtomNoteNoutHash

        pmts(index, int)
        pmts(atom_nout_hash, AtomNoteNoutHash)

        self.index = index
        self.atom_nout_hash = atom_nout_hash

    def as_bytes(self):
        return bytes([ATOM_LIST_INSERT]) + to_vlq(self.index) + self.atom_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomNoteNoutHash
        return AtomListInsert(from_vlq(byte_stream), AtomNoteNoutHash.from_stream(byte_stream))


class AtomListDelete(AtomListNote):
    def __init__(self, index):
        pmts(index, int)
        self.index = index

    def as_bytes(self):
        return bytes([ATOM_LIST_DELETE]) + to_vlq(self.index)

    @staticmethod
    def from_stream(byte_stream):
        return AtomListDelete(from_vlq(byte_stream))


class AtomListReplace(AtomListNote):
    def __init__(self, index, atom_nout_hash):
        from dsn.form_analysis.legato import AtomNoteNoutHash

        pmts(index, int)
        pmts(atom_nout_hash, AtomNoteNoutHash)

        self.index = index
        self.atom_nout_hash = atom_nout_hash

    def as_bytes(self):
        return bytes([ATOM_LIST_REPLACE]) + to_vlq(self.index) + self.atom_nout_hash.as_bytes()

    @staticmethod
    def from_stream(byte_stream):
        from dsn.form_analysis.legato import AtomNoteNoutHash
        return AtomListReplace(from_vlq(byte_stream), AtomNoteNoutHash.from_stream(byte_stream))
