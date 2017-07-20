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

"""


class FormNote(object):
    pass


# Malformed: Become only (to be Malformed is not to have any meaningful mechanisms for further change)
class BecomeMalformed(FormNote):
    pass


# Reference:
class BecomeReference(FormNote):
    def __init__(self, symbol):
        self.symbol = symbol


# Value:
class BecomeValue(FormNote):
    def __init__(self, value):
        self.value = value


# Quote:
class BecomeQuote(FormNote):
    def __init__(self, data):
        # Design: we intentionally allow for Become to have a whole s-expr as given: at any point an s-expression could
        # be turned into a quote expression, giving rise to a payload of quoted data "ex machina" (from the perspective
        # of the Quote Form at least)

        # (TBH, the above basically applies symmetrically for all types of notes: whenever they become, underlying notes
        # may be arbitrary complex structures already)

        self.data = data  # :: SExpr


class QuoteChange(FormNote):
    # Changes to quoted data are expressed precisely so: as changes to their underlying s-expr.

    def __init__(self, sexpr_note):
        self.sexpr_note = sexpr_note


# If
class BecomeIf(FormNote):

    def __init__(self, predicate, consequent, alternative):
        self.predicate = predicate  # :: Form
        self.consequent = consequent  # :: Form
        self.alternative = alternative  # :: Form

# Changes to either of the 3 parts: how to model?
# thoughts:
# Either as 3 special classes, or as 1 class that takes as a parameter the (predicate, consequent, alterative)
# Or even more radically: just a single class across all notes, (meh)
# The best way to discover what a proper model is is to create the current analysis, and any further static analyses,
# first and then see which models are a good fit.


# Define:
class BecomeDefine(FormNote):

    def __init__(self, symbol, definition):
        self.symbol = symbol
        self.definition = definition


class DefineChangeSymbol(FormNote):
    def __init__(self, symbol):
        # TBD: or, via a separate symbol history
        self.symbol = symbol


class DefineChangeDefinition(FormNote):
    def __init__(self, note):
        self.note = note  # :: FormNote


# Lambda:
class BecomeLambda(FormNote):

    def __init__(self, parameters, body):
        self.parameters = parameters
        self.body = body


class LambdaChangeBody(FormNote):
    def __init__(self, note):
        self.note = note  # :: FormNote


class LambdaChangeParameters(FormNote):
    def __init__(self, note):
        self.note = note  # :: SymbolListNote


# Application
class ApplicationBecome(FormNote):

    def __init__(self, procedure, arguments):
        self.procedure_note = procedure
        self.arguments = arguments


class ApplicationChangeProcedure(FormNote):
    def __init__(self, note):
        self.note = note  # :: FormNote


class ApplicationChangeParameters(FormNote):
    def __init__(self, note):
        self.note = note  # FormListNote


# Below this line: Notes that describe changes to _parts_ of the Forms (in particular: symbols and lists thereof):
"""To be done still
Manipulation of FormList.

Insert. Delete. Replace.

Open question: model as single-note; or as "full history"?
... if we stay symmetric with the approach for s-expressions, the answer is "nout hash (i.e. full history)"

In either case, the notes passed are FormNotes

More modelling choices are:
We could even say: FormList manipulation is not a separate concern; the notes are simply on Application directly (since
application is the only type of Form that takes a list of Forms). Potato Potahto, we'll see.

"""


class SymbolBecome(object):
    def __init__(self, symbol):
        self.symbol = symbol

    # arguably SymbolBecome is also superfluous; we could just say at the level of "Define" we can change the symbol


# SymbolListBecome: I think that's superfluous; symbol-list manipulation only happens in contexts where the fact that
# we're dealing with a symbollist is implied, so it needs not be made further explicit.


class SymbolListNote(object):
    pass


class SymbolInsert(SymbolListNote):
    def __init__(self, index, symbol):
        self.index = index
        self.symbol = symbol


class SymbolDelete(SymbolListNote):
    def __init__(self, index):
        self.index = index


# How to model SymbolReplace? Recursively using the Symbol class? Or just directly? We'll see what's a good description;
# no need to go overboard in any case.
