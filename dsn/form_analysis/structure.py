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

from utils import pmts
from dsn.s_expr.structure import TreeText, TreeNode


class Form(object):

    def __init__(self):
        pass

    def __repr__(self):
        return repr(self.as_s_expr())

    def as_s_expr(self):
        """(At least for now): for debugging purposes, i.e. not thoroughly implemented.

        Prime example: The returned s_expr has no historic awareness (no nout_hash in the metadata).
        """
        raise NotImplemented()

# TODO Open question: will we store any history in these Forms too? In the end: Probably we will. Compare what's done
# with the s-expressions themselves (which also do this)


class MalformedForm(Form):
    # Potentially: also add various _specific_ malformednesses, like "Lambda with non-3 params", or "Lambda of which the
    # parameter list is not a list of symbols.

    # For now, the only actual malformed s-expression I can think of is: the empty list. One could also say: that's
    # simply a case of an application without either a procedure nor any arguments. I.e. a non-3-lambda.

    def as_s_expr(self):
        # Note: the introduction of the `as_s_expr` method raises the following question: should the MalformedForm know
        # what the underlying (malformed) s_expr is, so that it may reproduce that when asked? If we want Malformed
        # s_expressions to be returned unchanged from as_s_expr(to_form(...)) we indeed need to store. For now, this
        # isn't done.
        return TreeText("MALFORMED", None)

    def __eq__(self, other):
        return isinstance(other, MalformedForm)


class VariableForm(Form):

    def __init__(self, symbol):
        pmts(symbol, Symbol)
        self.symbol = symbol

    def as_s_expr(self):
        return TreeText(self.symbol.symbol, metadata=None)

    def __eq__(self, other):
        return isinstance(other, VariableForm) and self.symbol == other.symbol


class ValueForm(Form):
    def __init__(self, type_, value):
        self.type_ = type_
        self.value = value

    def as_s_expr(self):
        return TreeText(repr(self.value), metadata=None)

    def __eq__(self, other):
        return isinstance(other, ValueForm) and self.type_ == other.type_ and self.value == other.value


class QuoteForm(Form):
    def __init__(self, data):
        self.data = data  # :: SExpr

    def as_s_expr(self):
        return TreeNode([TreeText("quote", None), self.data])

    def __eq__(self, other):
        return isinstance(other, QuoteForm) and self.data == other.data


class IfForm(Form):

    def __init__(self, predicate, consequent, alternative):
        self.predicate = predicate  # :: Form
        self.consequent = consequent  # :: Form
        self.alternative = alternative  # :: Form

    def as_s_expr(self):
        return TreeNode([
            TreeText("if", None),
            self.predicate.as_s_expr(),
            self.consequent.as_s_expr(),
            self.alternative.as_s_expr(), ])

    def __eq__(self, other):
        return isinstance(other, IfForm) and (
            self.predicate == other.predicate and
            self.consequent == other.consequent and
            self.alternative == other.alternative)


class DefineForm(Form):

    def __init__(self, symbol, definition):
        self.symbol = symbol  # :: Symbol
        self.definition = definition  # :: Form

    def as_s_expr(self):
        return TreeNode([
            TreeText("define", None),
            TreeText(self.symbol.symbol, None),
            self.definition.as_s_expr(),
            ])

    def __eq__(self, other):
        return isinstance(other, DefineForm) and (
            self.symbol == other.symbol and
            self.definition == other.definition)


class LambdaForm(Form):
    def __init__(self, parameters, body):
        self.parameters = parameters  # :: AtomList
        self.body = body  # :: FormList

    def as_s_expr(self):
        return TreeNode([
            TreeText("lambda", None),
            TreeNode([TreeText(s.symbol, None) for s in self.parameters]),
            ] + [f.as_s_expr() for f in self.body])

    def __eq__(self, other):
        return isinstance(other, LambdaForm) and (
            self.parameters == other.parameters and
            self.body == other.body)


class ApplicationForm(Form):
    def __init__(self, procedure, arguments):
        self.procedure = procedure  # :: Form
        self.arguments = arguments  # :: FormList

    def as_s_expr(self):
        return TreeNode([
            self.procedure.as_s_expr(),
            ] + [a.as_s_expr() for a in self.arguments])

    def __eq__(self, other):
        return isinstance(other, ApplicationForm) and (
            self.procedure == other.procedure and
            self.arguments == other.arguments)


class SequenceForm(Form):
    def __init__(self, sequence):
        self.sequence = sequence  # :: FormList

    def as_s_expr(self):
        return TreeNode([
            TreeText("begin", None),
            ] + [e.as_s_expr() for e in self.sequence])

    def __eq__(self, other):
        return isinstance(other, SequenceForm) and self.sequence == other.sequence


# Below this line: _not_ Form, but used as a part of a Form. May still have its own independent history.
class FormList(object):
    def __init__(self, the_list, metadata=None):
        pmts(the_list, list)
        self.the_list = the_list
        self.metadata = metadata

    def __iter__(self):
        return self.the_list.__iter__()

    def __eq__(self, other):
        return isinstance(other, FormList) and len(self.the_list) == len(other.the_list) and all(
            a == b for (a, b) in zip(self.the_list, other.the_list))


class Symbol(object):

    def __init__(self, symbol):
        self.symbol = symbol  # :: string (or None, which has the special meaning "a malformed symbol")

    def __repr__(self):
        if self.symbol is None:
            return "<Symbol of malformed type>"
        return "<Symbol %s>" % self.symbol

    def __eq__(self, other):
        return isinstance(other, Symbol) and self.symbol == other.symbol


class SymbolList(object):
    def __init__(self, the_list, metadata=None):
        pmts(the_list, list)
        self.the_list = the_list
        self.metadata = metadata

    def __iter__(self):
        return self.the_list.__iter__()

    def __eq__(self, other):
        #  TBD: should metadata be part of equality-test?
        return isinstance(other, SymbolList) and len(self.the_list) == len(other.the_list) and all(
            a == b for (a, b) in zip(self.the_list, other.the_list))
