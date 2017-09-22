# Lexical Addressing "X", because as of yet, we only do a very particular kind of addressing. Namely: we refer to a
# scope by "frames up", but we do not address within the scope (e.g.: memory-offset, or var-count-offset)

from dsn.form_analysis.free_variables import free_variables
from dsn.form_analysis.somewhere import collect_definitions


def set_union(l):
    return set.union(*l)


def dict_union(l):
    result = {}
    for d in l:
        result.update(d)
    return result


def lexical_addressing_x(surrounding_scope, lambda_form):
    # Note that the present free-variable-driven form has no values for unused variables. This is considered useless
    # (but I might change my mind once I get to the incremental analysis)
    result = {}

    parameters = {p.symbol for p in lambda_form.parameters}
    defined = {f.symbol.symbol for f in collect_definitions(lambda_form)}

    this_scope = set.union(parameters, defined)

    for symbol in set_union([free_variables(f) for f in lambda_form.body]):
        if symbol in this_scope:
            result[symbol] = 0
            continue

        # The act of looking up always succeeds, though it may result in None for "not defined". This is because free
        # variables that are not defined at the present level will also be free variables of higher levels.
        looked_up = surrounding_scope[symbol]
        if looked_up is None:
            result[symbol] = None
        else:
            result[symbol] = looked_up + 1

    return result
