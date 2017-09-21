from dsn.form_analysis.structure import (
    VariableForm,
    LambdaForm,
    IfForm,
    DefineForm,
    ApplicationForm,
    SequenceForm,
)

from dsn.form_analysis.somewhere import collect_definitions


def free_variables(form):
    # return type? let's start with python-lists of symbols.
    # Or rather: a set!

    if isinstance(form, VariableForm):
        return set([form.symbol.symbol])

    if isinstance(form, LambdaForm):
        a = set.union(*[free_variables(f) for f in form.body])
        b = set([d.symbol.symbol for d in collect_definitions(form)])
        c = set([p.symbol for p in form.parameters])
        return a - b - c

    # When considering a DefineForm, we might ask whether the form.symbol should be excluded from the result or not.
    # Arguments could be made for both decisions; which is unfortunate.

    # The confusion stems from the fact that choice of symbol influences the surrounding scope, but not the value of the
    # DefineForm itself (the value resulting from evaluating Define differs from implementation to implementation,
    # indicating that it's a non-central concept in the first place)

    # Consider e.g. this definition: "A variable, V, is 'free in an expression', E, if the meaning of E is _changed_ by
    # the uniform replacement of a variable, W, not occurring in E, for every occurrence of V in E."; note that the
    # definition doesn't help us very much, because it hinges on what the _meaning_ of the expression is... in the case
    # under consideration the expression will evaluate the same way when replacing the definition's symbol... but the
    # effects on the surrounding scope are _not_ the same.

    # Given that observation, it could be argued that the problem is simply to allow for "Define" as a separate form,
    # rather than as a property of a lambda or let. I'll take this as a datapoint for now, rather than banning define.

    # Rephrasing the question "is the variable free" as "is the variable bound to an enclosing scope" makes it easier:
    # in that case the answer is "form.symbol should not be excluded from the result", because if the symbol occurs on
    # the RHS it's bound to an enclosing scope (even though it's bound to that scope precisely by the LHS).

    # Another approach could be to consider "why are you interested in free variables". The answer is "to determine how
    # information from "the world" flows into the expression. Same answer, for the same reason.
    # Counterpoint: when doing an analysis for unused definitions, you actually want to ignore things that are defined
    # in terms of themselves (because that fact alone does not make it so that the defintion is used elsewhere).

    # In any case, I'm settling on "no special treatment of Define's LHS" for now.

    return general_means_of_collection(form, free_variables, lambda l: set.union(*l), set())


def general_means_of_collection(form, f, combine, identity):
    # Apply thing_to_do on all this form's child (but no lower descendants) forms.

    # The behavior for MalformedForm is TBD; in any case it has no child forms
    # VariableForm, ValueForm & QuoteForm have no child-forms

    if isinstance(form, IfForm):
        return combine([f(form.predicate), f(form.consequent), f(form.alternative)])

    if isinstance(form, DefineForm):
        return f(form.definition)

    if isinstance(form, LambdaForm):
        return combine([f(child) for child in form.body])

    if isinstance(form, ApplicationForm):
        return combine([f(form.procedure)] + [f(child) for child in form.arguments])

    if isinstance(form, SequenceForm):
        return combine([f(child) for child in form.sequence])

    return identity
