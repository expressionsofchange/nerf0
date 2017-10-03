# Lexical Addressing "X", because as of yet, we only do a very particular kind of addressing. Namely: we refer to a
# scope by "frames up", but we do not address within the scope (e.g.: memory-offset, or var-count-offset)

from dsn.form_analysis.free_variables import free_variables
from dsn.form_analysis.somewhere import collect_definitions
from dsn.form_analysis.utils import general_means_of_collection
from dsn.form_analysis.structure import (
    LambdaForm,
)


def set_union(l):
    return set.union(*l)


def dict_union(l):
    result = {}
    for d in l:
        result.update(d)
    return result


def add_lists(*args):
    result = []
    for arg in args:
        for elem in arg:
            result += elem
    return result


def lexical_addressing_x(surrounding_scope, lambda_form):
    """
    :: {symbol: scopes_up_count}, lambda_form -> {symbol: scopes_up_count}

    Note that this version (free-variable-driven) contains no keys for unused variables.
    (but I might change my mind once I get to the incremental analysis)
    """
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


def lexical_addressing_downwards(lambda_form):
    pass
    # * finding all scopes (lambda-expressions) in the tree; constructing a scope-tree out of that.
    #       gebleven bij: do it as a Tree!

    # HIER DAN
    # Eerste vraag is direct: wat is je beginpunt? Let's assume (and write that down): a lambda;
    # dan kunnen we dus de lambda-children van je body verzamelen.
    # and for each of those, the lambda-children of their bodies.

    # * following the scope-tree downwards, construct {symbol: scopes_up_count} ... this is the thing I already did.


def find_lambda_children(form):
    # recurse into the form, identifying subscopes, but don't recurse into any lambdas
    if isinstance(form, LambdaForm):
        return [form]

    return general_means_of_collection(form, find_lambda_children, add_lists, [])


class LambdaTree(object):
    def __init__(self, lambda_form, children):
        self.lambda_form = lambda_form
        self.children = children


def some_lambda_tree(lambda_form):
    lambda_children = add_lists([find_lambda_children(f) for f in lambda_form.body])
    children = [some_lambda_tree(c) for c in lambda_children]
    return LambdaTree(lambda_form, children)


class LambdaTreeWithLAStuff(object):
    def __init__(self, lambda_form, la_stuff, children):
        self.lambda_form = lambda_form
        self.la_stuff = la_stuff
        self.children = children


def construct_lexical_addresses_down_the_tree_initial(lambda_tree):
    return construct_lexical_addresses_down_the_tree(lambda_tree, {})


def construct_lexical_addresses_down_the_tree(lambda_tree, surrounding_scope):
    la = lexical_addressing_x(surrounding_scope, lambda_tree.lambda_form)

    constructed_children = [
        construct_lexical_addresses_down_the_tree(child, la)
        for child in lambda_tree.children
    ]

    return LambdaTreeWithLAStuff(
        lambda_tree.lambda_form,
        la,
        constructed_children,
    )


class LambdaTree4Prop(object):
    # alternatively: some mechanism of decoration.
    # alternatively: have a single point in your control-flow which applies all decorations at once.
    #     I like the above option... later though.

    def __init__(self, lambda_form, la_stuff, name_dependencies, children):
        self.lambda_form = lambda_form
        self.la_stuff = la_stuff
        self.name_dependencies = name_dependencies
        self.children = children


class MostCompleteScope(object):

    def __init__(self, parent, lambda_form, la_stuff, name_dependencies, children):
        self.parent = parent
        self.lambda_form = lambda_form
        self.la_stuff = la_stuff
        self.name_dependencies = name_dependencies
        self.children = children
