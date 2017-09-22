from dsn.form_analysis.free_variables import free_variables
from dsn.form_analysis.somewhere import collect_definitions


def set_union(l):
    return set.union(*l)


def unused_definitions(lambda_form):
    """Structural (non-incremental) analysis"""

    defined = {f.symbol.symbol for f in collect_definitions(lambda_form)}
    free_vars = set_union([free_variables(f) for f in lambda_form.body])
    return defined - free_vars


def unused_parameters(lambda_form):
    parameters = {p.symbol for p in lambda_form.parameters}
    free_vars = set_union([free_variables(f) for f in lambda_form.body])

    return parameters - free_vars
