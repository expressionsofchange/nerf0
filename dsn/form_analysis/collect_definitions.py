# ## Define - restrictions on where it can appear:

# With respect to MIT Scheme, we restrict the locations where "define" is a legal form; in particular:
#
# * Define must be a direct child (not just any descendant) of a lambda.
# * Redefinitions are illegal.
# * Definitions must be at the start of a lambda's body. (not done yet)
# * Definitions must not rely on definitions from the same scope to be evaluated (not done yet)
#
# (As it stands, these restrictions are not yet checked; but the rest of the implementation already relies on it)
#
# I believe that the above restrictions are useful in the sense that they lead to less errors; they also happen to make
# implementation easier.
#
# In SICP, I could find the following notes that hint at the fact that the above restrictions are useful (although they
# are not part of the SICP implementation):
#
# * p. 241, footnote: "If there is already a binding for the variable in the current frame, then the binding is changed.
# [..] some people prefer redefinitions of existing symbols to signal errors" * p. 388, "4.1.6. Internal definitions"
# talks about the problems that arise when not having your definitions at the start of the lambda; especially when the
# definitions use other variables from the present scope, and when the value of the definitions is calculated before all
# variables of the scope are defined.
#
# W.R.T. non-top-level definitions I could not find an explicit discussion of the topic, however.
#
# However, it seems that I'm not the first one to think of the above restriction, e.g. from Racket (a Scheme)'s
# specification:
#
# "11.2  Definitions - Definitionsmay appear within a <top-level body>, at the top of a <library body>, or at the top of
# a <body>"
#
# A similar question (as of yet unresolved) is: will we allow define to redefine parameters from the same scope (i.e.
# name-collissions between paramters and defines in the same scope). In Racket, this is legal:
# ((lambda (foo) (define foo 1) foo) 2)


from dsn.form_analysis.structure import DefineForm


def collect_definitions(lambda_form):
    # :: [form]; this is subject to change though
    return [f for f in lambda_form.body if isinstance(f, DefineForm)]
