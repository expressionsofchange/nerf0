from dsn.form_analysis.collect_definitions import collect_definitions
from dsn.form_analysis.free_variables import free_variables


def name_dependencies(lambda_form):
    """For a given lambda form, returns all defined names and the names they depend on.

    A (lambda) scope, being the place where definitions are tied to, would seem to be the perfect place to do this
    analysis.

    This analyis can be done without considering the surrounding scope.
    """

    # The lambda's parameters do not have dependencies on surrounding scope.
    result = {p.symbol: set() for p in lambda_form.parameters}

    # TODO in the below redefinitions are silently allowed (later occurrences overwriting previous ones), despite the
    # fact that they are generally a bad idea. Before implementing an error-mechanism, we need to choose a way of
    # representing errors though.
    for f in collect_definitions(lambda_form):
        result[f.symbol.symbol] = free_variables(f)

    return result
