from utils import pmts

from dsn.form_analysis.structure import (
    ApplicationForm,
    DefineForm,
    IfForm,
    LambdaForm,
    MalformedForm,
    QuoteForm,
    SequenceForm,
    ValueForm,
    VariableForm,
)


# ## Data model:
class Frame(object):
    def __init__(self, parent, data=None):
        self.parent = parent
        if data is None:
            data = {}
        self.data = data

    def lookup(self, symbol):
        if symbol is None:
            raise Exception("Malformed symbol cannot be looked up")
        pmts(symbol, str)

        if symbol in self.data:
            return self.data[symbol]

        if self.parent is None:
            raise KeyError("No such symbol: '%s'" % symbol)

        return self.parent.lookup(symbol)

    def set(self, symbol, value):
        if symbol is None:
            raise Exception("Malformed symbol cannot be set")
        pmts(symbol, str)

        self.data[symbol] = value


class Procedure(object):
    pass


class SpecialValue(object):
    def __init__(self, value):
        self.value = value


class BuiltinProcedure(object):
    def __init__(self, procedure):
        self.procedure = procedure


class CompoundProcedure(Procedure):
    def __init__(self, form, environment):
        self.form = form
        self.environment = environment


# ## Evaluation:
def evaluate(form, environment):
    if isinstance(form, MalformedForm):
        raise Exception("Cannot evaluate MalformedForm")

    if isinstance(form, ValueForm):
        return form.value

    if isinstance(form, VariableForm):
        return environment.lookup(form.symbol)

    if isinstance(form, QuoteForm):
        return form.data

    if isinstance(form, DefineForm):
        environment.set(form.symbol.symbol, evaluate(form.definition, environment))
        return SpecialValue("Definition")

    if isinstance(form, IfForm):
        if evaluate(form.predicate, environment):
            return evaluate(form.consequent, environment)
        return evaluate(form.alternative, environment)

    if isinstance(form, LambdaForm):
        return CompoundProcedure(form, environment)

    if isinstance(form, SequenceForm):
        for element in form.sequence:
            value = evaluate(element, environment)
        return value  # implicitly fails on empty lists.

    if isinstance(form, ApplicationForm):
        procedure = evaluate(form.procedure, environment)
        arguments = [evaluate(arg, environment) for arg in form.arguments]
        return apply(procedure, arguments)

    raise Exception("Case analysis fail %s" % type(form))


def apply(procedure, arguments):
    if isinstance(procedure, BuiltinProcedure):
        return procedure.procedure(*arguments)

    if isinstance(procedure, CompoundProcedure):
        assert len(arguments) == len(procedure.form.parameters.the_list)
        new_frame = {procedure.form.parameters.the_list[i].symbol: arguments[i] for i in range(len(arguments))}
        extended_environment = Frame(procedure.environment, new_frame)

        for body_element in procedure.form.body:
            value = evaluate(body_element, extended_environment)

        return value

    raise Exception("Case analysis fail %s" % type(procedure))
