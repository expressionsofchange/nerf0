from dsn.s_expr.structure import TreeNode, TreeText


def s_expr_from_python(python_obj):
    """
    Constructs an s-expression given a Python-modelling of s-expressions, as such:

    * Python tuples being interpreted as compound expressions (lists)
    * Python strings being interpreted as atoms

    This allows one to write s-expressions concisely in Python code, which aids in readability for humans. N.B. Python
    still mandates the items in its tuples to be comma-separated.

    `s_expr_from_python` is in the first place meant as glue-code for ad hoc situations; it's not supposed to take a
    central role in production systems. An important real-world use-case of such glue-like behavior are the
    testcases/doctests.

    Note that the resulting s_expressions are ahistoric.

    >>> s_expr_from_python(("foo", ("bar",)))
    (foo (bar))
    """

    if isinstance(python_obj, tuple):
        children = [s_expr_from_python(child) for child in python_obj]
        return TreeNode(children)

    if isinstance(python_obj, str):
        return TreeText(python_obj, None)

    raise Exception("Not an s_expression: %s" % type(python_obj))

