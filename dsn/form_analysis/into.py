"""
## On the funny (temporary) name 'into':

Constructing "into" this Clef, from the s-expr Clef.

I.e. from s-expr notes to form_analysis clef.

This is different from construct.py, which constructs from notes to structures.

Should this be part of the s-expr module or the current one? Object Oriented programmers would fight over this.
Functional programmers point out that you can't know; but this is also useless :-)
"""

from dsn.s_expr.structure import TreeText

from dsn.form_analyis.clef import BecomeMalformed, BecomeReference, BecomeValue


def some_analysis(previous_s_expr, sexpr_note, previous_form):
    # klein vraagje: tussenvorm construct_x en x_note_play?
    # hmmm. irritant.
    # we kunnen bovenstaande nog wel enigszins uitstellen, en het uitdrukken als:

    # previous_s_expr, current_s_expr, previous_form.... dat is ook zuiverder in lijn met wat er daadwerkelijk gebeurt!

    pass


def is_number(unicode_):
    # notes on ints-only.
    pass

def is_string(unicode_):
    # notes on a more simple impl: opening-quote only
    blah

def some_other_analysis(previous_s_expr, s_expr, previous_form):
    isinstance(s_expr, TreeText):
        # TODO Describe: Become v.s. Set plays up again; we'll go with "Become only" for now.

        if is_number(s_expr.unicode_):
            return BecomeValue(to_number(s_expr.unicode_))

        if is_string(s_expr.unicode_):
            return BecomeValue(to_string(s_expr.unicode_))

        # all other atoms are symbols
        return BecomeVariable(s_expr.unicode_)

    # implied else: TreeNode

    if len(s_expr.children) == 0:
        # Trying to interpret the empty list as a lisp form yields an error.
        # Alternatively one could say this is Procedure Application w/o specified a procedure to apply. (This would be
        # the behavior of the interpreter from SICP). However, I'm not sure the added specificity in that scenario
        # actually adds information rather than confusion.
        return BecomeMalformed()

    tagged_list_tag = s_expr.children[0].unicode_ if isinstance(s_expr.children[0], TreeText) else None

    if tagged_list_tag == "quote":
        # TODO Check: len == 2 (tag + data)
        # TODO What about Set v.s. become in this case? I'd like to think a Set is relevant, but I cannot prove it yet.
        # So we'll really stick with TSTTCPW

        # There are many ways we can arrive at the present point, not all of them being: a change to the data-s_expr. In
        # particular:
        # * tag-change
        # * param-count-change to the correct number of 2
        # * change to the data-s_expr.
        # If we ever distinguish between Set/Become, only the last of those should be a Set.

        return BecomeQuote(s_expr.children[1])

    if tagged_list_tag == "define":
        # TODO Check: len == 3 (tag, symbol, definition)
        #
        # First question now: how to determine whether there was even a change on LHS or RHS? I'd really like to be a
        # bit more smart here than to do this via a diffing trick.

        # In other words: just look at what happened. Which means: the s-expr note is still available here. Ok, no
        # biggie.

        # I think this is the first point where we really have to distinguish between Set & Become right from the very
        # first implementation? Why? First, because we distinguish between the 2 kinds of Set themselves! Which implies
        # that they are distinct from Become.

        # What are the ingredients to this soup?

        # * Current nr. of args (must be 3)
        #     if not: we're now malformed. with the usual notes about future improvements. (specificness of mlfrmness)

        # * Previous Form same?
        #     if not: become.

        # If we've past those 2 checks, we know that we're dealing with a change to child[1] or child[2]. Why?
        #     child[0] was & is define, because the previous change was the same too!
        #

        # (In fact, we're not 100% sure, e.g. child[0] might have changed to be the same... let's just note that then)
        # We're at least sure about: prev. arg-count was also 3 (otherwise: form would not have been valid previously)
        # Because we don't do swapping (yet), the only remaining possibilities are Replace at 1 or 2.

        # In any case: let's think about such changes.

        # How does brokenness bubble up? TSTTCPW for now is: if any error, just return an error at the present point.

        # Let's start with changes to the parameter-list. Such changes should be representable quite straight-forwardly
        # as a mapping between s-expr-notes and notes on a list of symbols.

        # So we get a single Replace on the child[1].
        # The first problem is: such a replace may [a] imply any number of changes on the parameter-list; [b] such
        # changes may even non-linear.
        # Let's ignore that problem for a short while though. And for now assume it's a single linear change. We'll
        # return to this shortly.

        # One level down, the following changes may occur:
        # * Replace. (Again: whole-history)
        #       Do we care about any non-end-history here?! I don't think we do. Reason: there is nothing meaningful to
        #       map it to in the target-clef anyway.
        #       In any case: we limit to "the end result is a single [symbol as opposed to variable? - is this a useful restriction?] atom"
        #
        # * Insert (Again: whole-history)
        #       We might restrict?! We just look
        #
        # * Delete.
        #       This removes a single symbol from the list.

        # Gebleven bij: nadenken over bovenstaande. Daarmee hangt samen: hoe veel moet je je best doen om op basis van
        # changes te werken, en in welke mate is "just look at the situation" voldoende (waarbij bij dat laatste dan wel
        # weer geldt: je kan dat dan heel lokaal doen, omdat de changes ook op structuren werken.)

        # Het voorlopige antwoord is: we doen een beetje ons best; maar het belangrijkste is: de doel-clef.
        # In feite is dit het zelfde antwoord als voor de huidige functie als geheel

        # Is het feit dat er geen 1-to-1 mapping is dan niet het bewijs dat clef-gebaseerd werken op de s-expressions
        # nutteloos is? nee, om een aantal redenen:
        # * De kleine stapjes aan de s-expr kant geven leiden tot slechts kleine delta-puzzeltjes
        # * localiteit blijft behouden in die puzzeltjes, d.w.z. de delta-puzzeltjes hoeven maar op kleine expressies
        #       uitgevoerd te worden
        # * de interpretatie idem (should we interpret the present thing as a form, parameter list, or ...?)

        # Een voordeel van de ignore-s-expr-clef in-analysis is: geen gevoeligheid voor nieuwe keuzes in de s-expr-clef.

        # Hoe zit het

        """
    * Definition.
        changes to LHS: check for correctness, apply as a note.
        changes to RHS: recurse.
            recurse how? current_s_expr!
            so, we need ways to point at s_expr easily - not really, we _could_ just use "nout_hash" for now.
                though the principled standpoint is: the hash that represents the things themselves is more precise!

            what about the result of recursing?
                this generates a new form note. this note is added to the present defintion's RHS history.
                which is then replaced with the addition of that.
                such note->nout stuff, do we have it already in some general form, or only for s_expr? Maybe in the editor's dsn?
    """


        return BecomeDefinition(s_expr.children[1])

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

    * quoted expression:
        BecomeQE v.s. SetQEValue v.s.
            What the precise answer will be here is as of yet unknown. Awaiting use cases. First thoughts:
                Analysis isn't going to be super-interesting: quoted expressions are "just a value"
                However, because such values might become arbitrarily large, a replace may be quite useful
                Yup.

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

            It analyses to: a ProcedureForm. Because the construction of the procedure only happens when the lambda is _evaluated_ (rather than analysed)

        ParamsChange.
            Params are much more limited. They are a list of symbols.
                InsertSymbol (position, symbol)
                DeleteSymbol (position)
                ReplaceSymbol (position, symbol)

    * Application:
        Paramcount (of the s-expr) is ≥ 1, of the Form ≥ 0

    """
