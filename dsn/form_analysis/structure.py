"""
The structure described in the present file is the result of the very first phase of static analysis of an s-expression.

Staying true to the nature of this project, this analysis is done in terms of expressions of change on a given
s-expression. For simplicity's sake, let's however first consider what the analysis is in terms of a given (unchanging)
s-expression.

Given an s-expression which represents the whole program, we proceed in a top-down fashion and turn this s-expression
into a tree of lisp forms. In other words: we assign to the s-expression the meaning of a Lisp program. This must be
done in a top down fashion, because the meaning of lower s-expressions is fully determined by the meaning of their
ancestors. I.e. a list expression can be either the list of formal parameters of a lambda definition a list or a
function application, depending on whether it respectively appears as the first child of a lambda, inside a quote
expression or elsewhere.

As an example, consider how to evaulate the following s-expression, as it appears in a program:

(....... (a b) .........)

What is the meaning of (a b) in this expression? It depends on what's on the dots. Examples:

(lambda (a b) (* a b))  - it's the parameter-list part of a lambda-form
(quote (a b))  - it's a list of symbols
(a b)  - it's the application of the procedure which is referenced by the symbol a on the symbol b.

So far we've talked about analysing given a given fixed s-expression.  However, in actuality (and staying true to the
nature of the current project) this analysis is done in terms of changes to s-expressions. More precisely: in terms of
the result of a previous analysis and a change to an s-expression.

The change to a s-expression (the input to the present analysis) is described in the usual way: as an Insert / Delete /
Replace with relevant information about effects on children recursively expressed.

We note that a change to our children may affect the present form; as a particular example: the first child of a list
expression determines the form. If it's "lambda", "define", or "if" this affects the currently examined form. For such
form-changing changes, we do a full structural analysis of the subtree inasmuch as required.

E.g. if the first child becomes the symbol "lambda" we become a Lambda and consider the second child as a parameter list
and the third as a procedure body. If the change to the currently considered s-expression's does not change the
associated form, we simply recurse.

In principle this means that a single change can result in a full reanalysis of the program, e.g. by adding "quote" as
the first symbol of the root node program. In practice, most changes will result in a single traversal from the top of
the tree down to the affected leaf.

Finally, a few words about the chosen terminlogy.

In Lisp Forms are "any Lisp object that is intended to be evaluated". In the present set of files we additionally mean
"containing the relevant information on how this evaluation may take place given the object's position in the full
program tree".

We specifically did not choose "Abstract Syntax Tree", because that phrase does not tell us whether it's the abstract
syntax of s-expressions (the previous step of analysis) or the abstract syntax of forms (the current step). The phrase
"Intermediate Representation" was rejected as being too general.

Some people mean "Lisp Form" to be an implication of static correctness of the form. We don't do that, and instead say
that incorrect forms are a subset of forms. In other words: "those lisp objects that are intended to be evaluated, but
malformed".

We call the present phase "Static Form Analysis". This is more precise than the considered alternatives: "static
analysis" or "semantic analysis", of which the present phase is a part.
"""


class Form(object):

    def __init__(self):
        pass


# TODO Open question: will we store any history in these Forms too? In the end: Probably we will. Compare what's done
# with the s-expressions themselves (which also do this)


class MalformedForm(Form):
    # Potentially: also add various _specific_ malformednesses, like "Lambda with non-3 params", or "Lambda of which the
    # parameter list is not a list of symbols.

    # For now, the only actual malformed s-expression I can think of is: the empty list. One could also say: that's
    # simply a case of an application without either a procedure nor any arguments. I.e. a non-3-lambda.
    pass


class VariableForm(Form):

    def __init__(self, symbol):
        self.symbol = symbol  # :: Symbol


class ValueForm(Form):
    def __init__(self, value):
        # Type: TBD (any of: underlying 's-expr' text atom or something more close to the actual value. Whether we
        # attempt to already make the step from pieces of text to e.g. numbers is TBD (probably not))
        self.value = value


class QuoteForm(Form):
    def __init__(self, data):
        self.data = data  # :: SExpr


class IfForm(Form):

    def __init__(self, predicate, consequent, alternative):
        self.predicate = predicate  # :: Form
        self.consequent = consequent  # :: Form
        self.alternative = alternative  # :: Form


class DefineForm(Form):

    def __init__(self, symbol, definition):
        self.symbol = symbol  # :: Symbol
        self.definition = definition  # :: Form


class LambdaForm(Form):
    def __init__(self, parameters, body):
        self.parameters = parameters  # :: AtomList
        self.body = body  # :: Form


class ApplicationForm(Form):
    def __init__(self, procedure, arguments):
        self.procedure = procedure  # :: Form
        self.arguments = arguments  # :: FormList


class SequenceForm(Form):
    def __init__(self, sequence):
        self.sequence = sequence  # :: FormList


# Below this line: _not_ Form, but used as a part of a Form. May still have its own independent history.
class FormList(object):
    def __init__(self, the_list, metadata):
        self.the_list = the_list
        self.metadata = metadata


class Symbol(object):
    # A single symbol,

    def __init__(self, symbol):
        # Type: TBD (any of: underlying 's-expr' text atom or something more close to the actual value)
        # In the end it doesn't matter much what we choose here.
        self.symbol = symbol


class SymbolList(object):
    def __init__(self, the_list, metadata):
        self.the_list = the_list
        self.metadata = metadata
