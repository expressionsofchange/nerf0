from dsn.form_analysis.structure import (
    VariableForm,
    LambdaForm,
)
from dsn.form_analysis.utils import general_means_of_collection
from dsn.form_analysis.collect_definitions import collect_definitions


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


# ## Incremental analysis
#
# Here are some thoughts about an incremental analysis of both `collect_definitions` and `free_variables`.
#
# What do I mean by that? The idea that for those analyses we can come up with a version that has the following type:
#
# (previous_x_structure, form_note) ->  x_note (x ∈ {free_variables, definitions})
#
# Such an incremental analysis is useful for a number of reasons:
#
# 1. From the perspective of a human the analysis is useful to aid in the understanding of the evolution of the program.
# It's simply a direct expression of "this variable became free in this expression at this point in time" and similar
# such notions.
#
# 2. It may also serve as a starting point for further automated analyses. e.g. the coming into being of a free variable
# has a direct effect on analyses about undefined and unused variables.
#
# A few notes on the implementation of such an incremental analysis:
#
# The most naive implementation would be to _not_ base it directly in the original Clef (in this case: form-analysis)
# but to take deltas on the structures.  i.e. to simply do the analysis on the structure for both pre-note and
# post-note, and calculate the diff over the results.
#
# This is somewhat unsatisfying for a number of reasons:
#
# 1. A basic idea of the project is that incremental analyses are useful; the human intuition of changing programs often
# has a close match to this incremental analyses.  Having code that closely matches this intuition is a nice to have.
# 2. Performance of the non-naive approach might be better (would need to be proven though)
#
# However, as it stands it's not unsatisfying enough to actually take action on it and implement it as such. The naive
# approach also has a big advantage: simplicity of implementation (and future maintenance)
#
# Additionally: we'll probably need to implement the naive approach in any case (to support "Come into being Ex
# Machina"); so the non-naive approach is always in-addition-to, rather than a replacement. So: extra work.
#
# Also, the following usual remark applies: even when no satisfying connection between different Clefs can be found, the
# fact that we're working with meaningful (structural) changes on the lower level already puts us one step ahead of
# "just working on strings".
#
# Finally: I don't feel I'm painting myself in a corner by postponing this... it can always be done better later without
# implications on the rest of the project.
#
# ### Non-naive Incremental analysis; notes on implementation
#
# Despite the above remarks which basically state that a non-naive implementation of an incremental analysis is not
# currently a priority, some thoughts on such an implementation were already had. They are preserved below.
#
# One basic approach is to collect only sets of names (for both the collection of definitions and the
# free-variable-analysis).
#
# Note that the collection of defintions and free_variables have different incremental analyses (just as they have
# different non-incremental analyses), even though they share a common resulting data-structure. Let's briefly explore
# what they look like.
#
# #### Collecting definitions (is done on lambda notes only)
#
# * Become: do it from scratch * Change of body: * New defintion -> add to set... but only if not already in the
# pre-structure! Otherwise: a double-definiton (which must be somehow modelled in the structure!) * Remove definition ->
# remove from set... but only if not currently in broken (doubly-defined) state for that particular symbol; if currently
# doubly-defined, you must actually check how many times.  * Otherwise -> nothing * Change of params: no action.
#
# Note that in the above the amount of times you still have to reference structures is really quite high.  Even though
# we still need to reference the resulting structure in some cases, we gain efficiency w.r.t. a full reconstruction of
# the set: because we only need to look up a single value, rather than comparing two (potentially very large) sets.
#
# #### Free variables
#
# The free variables themselves are quite similar to the example of collecting definitions; the main difference is to be
# found in the fact that, at the level of the lambda, addition/removal of definitions and parameters has the effect of
# removal/addition on the set of free variables. There's also a similar amount of necessary checks on the resulting
# structure.
#
# Also important: free-vars goes down the full tree rather than scan only the direct children of a lambda.
#
# #### A note on counting (rather than having sets)
#
# An alternative approach to building up sets of names would be to actually count for each name a number of occurrences.
# I briefly considered this in an attempt to get better performance-characteristics... but I couldn't actually figure
# out a path to better performance there.  In particular: if you always count the exact number of occurrences, any
# effect will always propagate all the way up the tree; whereas when you only count set-membership, the propagation up
# the tree stops whenever you add to a set that already has the member.
#
# Finally, a note on how free-variables and collection of definitions differ: for free variables the case where a single
# variable is used many times is expected and normal; for definitions it's an error.  This might have consequences on
# the implementation of the algorithm too.
#
# #### A note on "multi-notes":
#
# We need to allow for arbitrary notes from the form-clef, including "Become" and any changing node which encodes
# multiples notes of lower-level history in a single higher-level-note; one way to do this is to have the notes from the
# analyses potentially encode multiple deletions and additions in a single note - such a setup also removes the need for
# Change notes. Alternatively, we could have explicit Composition-Notes. N.B. When multiple changes are combined into a
# single note, the above clef-to-clef approach ("Collecting definitions") must be reconsidered)
