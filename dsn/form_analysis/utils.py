from dsn.form_analysis.structure import (
    LambdaForm,
    IfForm,
    DefineForm,
    ApplicationForm,
    SequenceForm,
)


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
