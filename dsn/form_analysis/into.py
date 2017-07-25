"""
## On the funny (temporary) name 'into':

Constructing "into" this Clef, from the s-expr Clef.

I.e. from s-expr notes to form_analysis clef.

This is different from construct.py, which constructs from notes to structures.

Should this be part of the s-expr module or the current one? Object Oriented programmers would fight over this.
Functional programmers point out that you can't know; but this is also useless :-)
"""


def some_analysis(previous_form, sexpr_note):
    pass
    # OK, HERE WE GO...

    """
    SOME QUESTIONS:

    Open questions: sexpr_note in the form of a nout_hash? That takes care of any problems of "getting from histories to
    previous_structure" etc. So probably: yes.

    Hmkay.

    Previous Form, and how do we know whether to only do the last step on the sexpr_nout_hash? I dunno.. can we just
    assume?

    """


    """
    A: apply the sexpr_note; take a look at the resulting node and do a case analyis on its form to figure out what the
    resulting Form is.

    B: Compare the resulting type of Form with the previous Form; if they differ, Become the new type.
        (probably: from scratch?)

    C: Else: as a case analysis, determine how to create a form history.

    (Road not taken: trying to be extremely faithful to the paradigm of incrementality, and analyse the s-expr-note
    itself to make statements about whether it might affect your form. I.e. for a list, replace at 0, insert at 0 and
    delete at 0 may change the present Form, but replace at 1 may not. For now we ignore this idea as it is more
    complicated than simply looking at the first element of the result, without actually yielding any better performance
    or clarity)

    * what about the type of text nodes? Can they also change?
        Yes! Variable v.s. Value
        The differences, at least between variable and the other 2 are relevant for certain types of analyses.

    * if variable:
        BecomeVariable

    * if value:
        BecomeValue

    * quoted expression:
        BecomeQE v.s. SetQEValue v.s.
            What the precise answer will be here is as of yet unknown. Awaiting use cases. First thoughts:
                Analysis isn't going to be super-interesting: quoted expressions are "just a value"
                However, because such values might become arbitrarily large, a replace may be quite useful

    * Definition.
        changes to LHS: check for correctness, apply as a note.
        changes to RHS: recurse.

    * If
        changes to parameter-count: (for now: go into malformed mode)
        changes to either of the 3: recurse

    * Lambda
        Turn this into a comment:
            What about swapping the lambda's arguments 1 & 2?  TBH, the cases in which that is meaningful would seem rather limited to me?!
                I can't think of any meaningful such case even. In other words: this might as well be considered a new BecomeLambda
                (BTW: swapping isn't even supported yet in the s-expr clef)

        Then there is:
            getting more than the (lambda params body)... meh Question-88; I could just postpone answering this; the tentative answer is:
                MalformedForm

            (similiar for: less than (lambda params body)

            let's start with a solution that has little granularity in the reporting about brokenness, and slowly introduce more such granularity as we see fit.

            It analyses to: a ProcedureYek. Because the construction of the procedure only happens when the lambda is _evaluated_ (rather than analysed)

        ParamsChange.
            Params are much more limited. They are a list of symbols.
                InsertSymbol (position, symbol)
                DeleteSymbol (position)
                ReplaceSymbol (position, symbol)

    * Application:
        Paramcount (of the s-expr) is ≥ 1, of the Form ≥ 0

    """
