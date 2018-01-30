# NOTE: a number of methods and classes from this file are copy/pasted and adapted from lexical_addressing_x.py; at some
# point that file may become entirely redundant, i.e. when we do all analyses in a loosely coupled way.

from dsn.s_expr.structure import TreeText
from dsn.form_analysis.structure import Form, LambdaForm
from dsn.form_analysis.utils import transform_children
from dsn.form_analysis.lexical_addressing_x import find_lambda_children, add_lists


class ConsolidatedLambdaForm(Form):
    """
    Using the class `Scope` below, we model our program as a tree of scopes, where each node in the tree corresponds to
    a newly introduced scope. In this setup, each node maintains a reference to its own corresponding form, with one
    important modification: any part of the form that corresponds to one of the children-scopes is not reproduced for
    the simple reason that their analysis is the responsibility of said child-scopes.

    This Replacing is modelled with the present class.

    As it stands, the modelling is somewhat ad hoc and subject to future improvements - i.e.  ConsolidatedLambdaForm is
    the only existing `Form` that doesn't actually correspond to something in the original program.
    """

    def __init__(self, index_in_scoped_children):
        """
        ConsolidatedLambdaForm is (exclusively) expected to be used as part of of a Scope.form; when it is the
        index_in_scoped_children points to the child scope which contains the replaced/occluded lambda.
        """
        self.index_in_scoped_children = index_in_scoped_children

    def __eq__(self, other):
        return isinstance(other, ConsolidatedLambdaForm) and (
            self.index_in_scoped_children == other.index_in_scoped_children)

    def as_s_expr(self):
        return TreeText("CONSOLIDATED-LAMBDA-%s" % self.index_in_scoped_children, None)


class Scope(object):
    """
    The idea is that many interesting analyses take place precisely at the level of a scope, and also that the
    interesting data-flows happen between scopes. (More precisely: that scopes form a level at which certain changes to
    the outcomes of analyses _stop propagating_, and form therefore a useful level to restrict the effects of such
    changes)
    """

    def __init__(self, form, children):
        # Note: currently the only "scoped form" is the lambda; future options are e.g. let-bindings, module-like
        # constructs (hence the name 'form')

        self.form = form
        self.children = children  # :: [Scope]

    def __repr__(self):
        return "(L " + repr(self.children) + ")"


def consolidated_form(lambda_form):
    i = -1

    def consolidate_or_not(form):
        if isinstance(form, LambdaForm):
            nonlocal i
            i += 1
            return ConsolidatedLambdaForm(i)

        return transform_children(form, consolidate_or_not)

    return transform_children(lambda_form, consolidate_or_not)


def construct_scope(lambda_form):
    children_scopes = add_lists([find_lambda_children(f) for f in lambda_form.body])
    children = [construct_scope(c) for c in children_scopes]
    return Scope(consolidated_form(lambda_form), children)


def something_else(lambda_form):
    """
    Mijn algo gaat uit van een zekere statefullness tussen 2 stappen.
    Namelijk: dat de analyses beschikbaar zijn.

    Die statefulness is de volgende uitdaging... dreigt ons trouwens toch snel weer bij iets meer dan zuiver
    deltas-tussen-forms te brengen; maar dat zien we dan wel weer...

    Sterker nog... is het uberhaupt doenlijk zonder zo'n continuiteit?
    ja, dat is uberhaupt doenlijk, maar dan moet je gaan cachen op de hash van de scope-structuur.... lastig.....

    Het gevoel begint me te bekruipen dat een incrementeel mechanisme directer is.... met daarbij wel de vraag hoe we
    de gezamenlijkheden met normale form-construction kunnen uitfactoren....
    EN... hoe die "state" er in een opvolgende stap "op wordt geplakt"
    EN.... de gebruikelijke vraag rond non-incremental en multi-step changes at lower levels.... die vraag is ditmaal
    echter prangender, omdat de "klok" globaal wordt geteld.
       (een eerste antwoord zou kunnen zijn: voorlopig beide verboden; single step at top is also single step all the
       way down)
       maar laat ik vast wat vooruit proberen te denken...

    Een achtergrondvraag is/blijft: bij het doen van performance-technisch gezien domme dingen, schilder je jezelf niet
    in een hoekje?
    Voor construct_scope is m'n antwoord vooralsnog "nee, geen hoekje" - het mechanisme om dat incrementeel te doen zou
    op basis van de form-construction zeer makkelijk te vinden moeten zijn. (het lastige is eerder nog: hoe factor je de
    gezamenlijkheden uit?)

    Een andere algemene achtergrondvraag is: die serializations/memoizations/stores die ik de hele tijd doe, kan dat op
    een algemenere manier tot uitdrukking worden gebracht in een Python API?

    How to?
    1. construct as usual... i.e. "into... construct_form" of iets dergelijks.
    2. [X] construct_lambda_tree... harvest for parts. in particular: it should look very similar, but w/
            ConsolidatedLambdaForm.
    3.

    op een zeker moment zal ik moeten in staat zijn om stapsgewijs te werken.
    Echter: de grote stappenteller is nog een apart iets denk ik?!

    Laat ik nu al even over dat "zekere moment" nadenken.
    in het boekje schreef ik (of hintte ik zwaar aan): dit gaat uit van 2 structuren, ipv van een clef-note.

    hoe speel je "zoek de verschillen" dan?
        * wel... het gaat er dus om of

    er is dus ook een "moment 0"; dat zal uitgaan van een lege scope ofzo? of simpelweg: de delta tussen de eerste 2...
    meh. liever expliciet. Lege lambdaform is een aardige stap echter.

    Scope equality is simply: form-equality (waarbij de ConsolidatedLambdaForm ook van een __eq__ is voorzien) en
    children-equality. Het is echter niet zo heel relevant, het gaat juist om de form-equality.

    N.B. .... door dat subsumen krijg je dus veel meer equality. Dit is ook een belangrijke reden om het te doen. (en
    zou ik in de relevante class ev. nog even kunnen noteren)

    The central point of making a loosly coupled scope-based algo is: de SOURCE van the-algo vaart niet op
    Scope-changes, maar op (Form w/ consolidation)-changes. If, for any given analysis, lower-level form-changes are
    relevant, this must be made explicit by making it an upflowing analysis.

    let's briefly review the_algo, to see how the notes on structural changes (below) might be incorporated
    This is automatic... the depended-on analysis will have a note "some descendant of me was changed on the present
    clock-tick"... which means the depending analysis will descend to (at least) that node to do a caculation for a new
    value.

    TODO note somewhere: the relationship between the 2 kinds of trees, namely scope-based and form-based, still feels a
    bit ad hoc to me; let's see where we end up.
    """
    pass

    # TODO nog in het boekje te schrijven: iets over onderstaande:
    # Dat een wijziging aan de scope-structuur altijd een wijziging in de form-structuur impliceert
    # hoe relevant dat is weet ik niet :-D

    # tot nu toe wist ik nog niet goed hoe wijzigingen in de scope-structuur door "the_algo" opgepakt zouden worden.
    # Volgens mij is het echter vrij simpel:
    # Verdwijnende scopes: daarover zijn geen analyses meer te doen. Up-propagating analyses must be rerun, starting at
    # the parent of the removed scope. Down-propagating analyses need not be rerun.
    # Newly created scopes: mark as "no analysis yet" for all analyses; do the analysis for all analyses and propagate
    # as required.
    pass
