from spacetime import get_s_address_for_t_address
from s_address import node_for_s_address

from dsn.s_expr.structure import TreeText

from dsn.pp.structure import PPNone, PPSingleLine, PPLispy, PPAnnotatedSExpr
from dsn.pp.clef import PPUnset, PPSetSingleLine, PPSetLispy


def build_annotated_tree(node, default_annotation):
    if isinstance(node, TreeText):
        annotated_children = []
    else:
        annotated_children = [build_annotated_tree(child, default_annotation) for child in node.children]

    return PPAnnotatedSExpr(
        node,
        default_annotation,
        annotated_children,
    )


def construct_pp_tree(tree, pp_annotations):
    """Because pp notes take a t_address, they can be applied on future trees (i.e. the current tree).

    The better (more general, more elegant and more performant) solution is to build the pp_tree in sync with the
    general tree, and have construct_pp_tree be a function over notes from those clefs rather than on trees.
    """
    annotated_tree = build_annotated_tree(tree, PPNone())

    for annotation in pp_annotations:
        pp_note = annotation.annotation

        s_address = get_s_address_for_t_address(tree, pp_note.t_address)
        if s_address is None:
            continue  # the node no longer exists

        annotated_node = node_for_s_address(annotated_tree, s_address)
        if isinstance(pp_note, PPUnset):
            new_value = PPNone()
        elif isinstance(pp_note, PPSetSingleLine):
            new_value = PPSingleLine()
        elif isinstance(pp_note, PPSetLispy):
            new_value = PPLispy()
        else:
            raise Exception("Unknown PP Note")

        # let's just do this mutably first... this is the lazy approach (but that fits with the caveats mentioned at the
        # top of this method)
        annotated_node.annotation = new_value

    return annotated_tree
