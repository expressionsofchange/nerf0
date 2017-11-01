# Lexical Addressing "X", because as of yet, we only do a very particular kind of addressing. Namely: we refer to a
# scope by "frames up", but we do not address within the scope (e.g.: memory-offset, or var-count-offset)

from utils import pmts

from dsn.form_analysis.free_variables import free_variables
from dsn.form_analysis.name_dependencies import name_dependencies
from dsn.form_analysis.collect_definitions import collect_definitions
from dsn.form_analysis.utils import general_means_of_collection
from dsn.form_analysis.structure import (
    LambdaForm,
)


def set_union(l):
    return set.union(*l)


def sdict(d, v_repr=None):
    if v_repr is None:
        v_repr = repr
    return "{" + ", ".join(["%s: %s" % (repr(k), v_repr(v)) for (k, v) in sorted(d.items())]) + "}"


def sset(s, e_repr=None):
    if e_repr is None:
        e_repr = repr
    return "{" + ", ".join([e_repr(e) for e in sorted(s)]) + "}"


def add_lists(*args):
    result = []
    for arg in args:
        for elem in arg:
            result += elem
    return result


def lexical_addressing_x(surrounding_scope, lambda_form):
    """
    :: {symbol: scopes_up_count}, lambda_form -> {symbol: scopes_up_count}

    In the present version of this function, the result will contain the lexical addresses of all free variables in the
    lambda_form, but will not contain any information on variables that are not used in the lambda_form's body (even
    when such information is available in the surrounding scope). This is a consequence of the present version being
    "driven" by the free variables in the lambda's body)

    Whether this is still the most useful answer once we implement the present analysis incrementally remains to be
    seen.
    """
    pmts(lambda_form, LambdaForm)
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


class LambdaTree(object):
    """
    ## LambdaTree

    LambdaTree represents a "tree of lambdas".

    Lambdas have special significance for all sorts of static analyses, because lambdas introduce new scopes (at present
    they are they only Form to do so).

    The LambdaTree respresents a view of a LambdaForm which allows for meaningful navigation through the scopes. Its
    children are all LambdaForms that exist as some descendant, but excluding those that are enclosed in another
    LambdaForm.

    ## A note on a number of closely related classes

    As is obvious from the below, a number of closely related classes exist, e.g. LexicallyAddressedLambdaTree and
    MostCompleteLambdaTree. These classes represent the same basic tree-structure, but with different information stored
    on each node. The usecase for each of these is implied by an associated analysis.

    How to arbitrarily decorate the same basic structure with different pieces of information, depending on the context
    of a given analysis, is at present not yet clear.

    One answer to this is "Aggregated Grammars", but this is not readily available in the present context. In any case,
    I'd prefer to ignore the question for now, and see what kind of modelling seems useful once we start examining the
    incremental analyses."""

    def __init__(self, lambda_form, children):
        self.lambda_form = lambda_form
        self.children = children

    def __repr__(self):
        return "(L " + repr(self.children) + ")"


class LexicallyAddressedLambdaTree(object):
    def __init__(self, lambda_form, lexical_addresses, children):
        self.lambda_form = lambda_form
        self.lexical_addresses = lexical_addresses
        self.children = children

    def __repr__(self):
        # To enable reproducable usage in tests, self.lexical_addresses is presented in ordered fashion
        return "(L " + sdict(self.lexical_addresses) + " " + repr(self.children) + ")"


class MostCompleteLambdaTree(object):
    """
    Represents a LambdaTree which contains attributes for all analyses that we do.  Because some of these analyses
    depend on information from enclosing scopes, this is modelled in doubly-linked fashion (links to both children and
    the parent).

    The set of its attributes is rather arbitrarily defined by being the complete set; The unsatisfactory naming prefix
    "MostComplete" reflects this. See the note on "Aggregated Grammars" above for more thoughts on this.
    """

    def __init__(self, parent, lambda_form, lexical_addresses, name_dependencies):
        self.parent = parent
        self.lambda_form = lambda_form
        self.lexical_addresses = lexical_addresses
        self.name_dependencies = name_dependencies

        # this datastructure has pointers in both directions (parent, children); one of them can be set at init, the
        # other can only be set once another datastructure has been created.
        self.children = "to be set later"

    def __repr__(self):
        # The present __repr__ is quite verbose; but at least it's useful in tests; in the future __repr__ is expected
        # to be changed into something more compact.

        # To enable reproducable usage in tests, various dicts are presented in ordered fashion
        la = sdict(self.lexical_addresses)
        nd = sdict(self.name_dependencies, v_repr=sset)
        return "(L " + la + " / " + nd + " " + repr(self.children) + ")"


def find_lambda_children(form):
    """Return a list of "lambda children" of the form: lambdas that are present as the forms descendant, but are not
    within another lambda."""

    if isinstance(form, LambdaForm):
        return [form]

    return general_means_of_collection(form, find_lambda_children, add_lists, [])


def construct_lambda_tree(lambda_form):
    """Constructs a (bare, i.e. no analyses) LambdaTree."""
    lambda_children = add_lists([find_lambda_children(f) for f in lambda_form.body])
    children = [construct_lambda_tree(c) for c in lambda_children]
    return LambdaTree(lambda_form, children)


def construct_lexically_addressed_lambda_tree(lambda_tree, surrounding_scope=None):
    """
    Out of a "bare" LambdaTree constructs a LexicallyAddressedLambdaTree, i.e. a tree of lambdas where the nodes are
    decorated with a dict like so:

    {symbol: scopes_up_count}

    It does this by going down the tree, calling lexical_addressing_x at each node (and passing down the surrounding
    node's info).
    """

    if surrounding_scope is None:
        surrounding_scope = {}

    pmts(surrounding_scope, dict)
    pmts(lambda_tree, LambdaTree)

    lexical_addresses = lexical_addressing_x(surrounding_scope, lambda_tree.lambda_form)

    constructed_children = [
        construct_lexically_addressed_lambda_tree(child, lexical_addresses)
        for child in lambda_tree.children
    ]

    return LexicallyAddressedLambdaTree(
        lambda_tree.lambda_form,
        lexical_addresses,
        constructed_children,
    )


def construct_most_complete_lambda_tree(lambda_tree, parent_scope=None):
    """constructs MostCompleteLambdaTree"""

    pmts(lambda_tree, LambdaTree)

    if parent_scope is None:
        lexical_addresses = {}
    else:
        pmts(parent_scope, MostCompleteLambdaTree)
        lexical_addresses = parent_scope.lexical_addresses

    lexical_addresses = lexical_addressing_x(lexical_addresses, lambda_tree.lambda_form)

    name_deps = name_dependencies(lambda_tree.lambda_form)

    result = MostCompleteLambdaTree(
        parent_scope,
        lambda_tree.lambda_form,
        lexical_addresses,
        name_deps,
    )

    constructed_children = [
        construct_most_complete_lambda_tree(child, result)
        for child in lambda_tree.children
    ]

    result.children = constructed_children
    return result


def follow_parents(thing_with_parent, nr_of_times):
    result = thing_with_parent
    for i in range(nr_of_times):
        result = result.parent
    return result


def calculate_name_closure(most_complete_scope, name, seen=None):
    # :: => set of (name, levels-up)
    # N.B. resist the temptation to convert into a dictionary: the set may contain more than one tuple for each name.

    if seen is None:
        seen = set()

    pmts(most_complete_scope, MostCompleteLambdaTree)

    if most_complete_scope.lexical_addresses.get(name) is None:
        # Undefined in one of two ways... (should I distinguish?)
        return set()  # or... be more explicit about this? we'll see about that later.

    levels_up = most_complete_scope.lexical_addresses[name]

    if (name, levels_up) in seen:
        # We pass around a set of variables we've already seen, and stop when re-encountering them. This allows for
        # analyses of (mutually) recursive dependencies.
        return set()

    result = set([(name, levels_up)])
    seen.add((name, levels_up))

    scope_where_name_is_defined = follow_parents(most_complete_scope, levels_up)

    # from the perspective of the scope where name is defined, the seen levels_up must be corrected;
    # The variables that were seen at lower levels than that scope (lu < levels_up) are unreachable.
    seen_from_recursive_perspective = {
        (n, lu - levels_up)
        for (n, lu) in seen
        if lu >= levels_up
    }

    dependencies = name_dependencies(scope_where_name_is_defined.lambda_form)[name]

    for depended_name in dependencies:
        recursive_result = calculate_name_closure(
            scope_where_name_is_defined, depended_name, seen_from_recursive_perspective)

        for (dependency_name, levels_up_wrt_recursive_scope) in recursive_result:
            # on-returning, add the appropriate depth to all names
            result.add((dependency_name, levels_up_wrt_recursive_scope + levels_up))

            # We add information about already-seen variable-name as soon as it comes available; this is not strictly
            # required for correctness but saves some double work. Here no correction for levels_up is required, because
            # both `seen_from_recursive_perspective` and the resulting dependencies have the same reference-scope.
            seen_from_recursive_perspective.add((dependency_name, levels_up_wrt_recursive_scope))

        # Note: if we were to use the inverted addressing scheme (levels-down, starting at root), we needed to do less
        # re-addressing; however, the present addressing scheme more clearly expresses how things might be depending on
        # each other, and hence is expected to be a better starting-point for the incremental analysis.

    return result
