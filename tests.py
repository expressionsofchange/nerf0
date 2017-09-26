import unittest
import doctest

import channel
import historiography
import spacetime
import vlq
import utils
import s_address
import vim

from dsn.s_expr import utils as s_expr_utils
from dsn.s_expr import from_python as s_expr_from_python
from dsn.viewports import utils as viewports_utils


def load_tests(loader, tests, ignore):
    # Test the docstrings inside our actual codebase
    tests.addTests(doctest.DocTestSuite(utils))
    tests.addTests(doctest.DocTestSuite(channel))
    tests.addTests(doctest.DocTestSuite(historiography))
    tests.addTests(doctest.DocTestSuite(spacetime))
    tests.addTests(doctest.DocTestSuite(vlq))
    tests.addTests(doctest.DocTestSuite(s_address))
    tests.addTests(doctest.DocTestSuite(s_expr_utils))
    tests.addTests(doctest.DocTestSuite(vim))
    tests.addTests(doctest.DocTestSuite(viewports_utils))
    tests.addTests(doctest.DocTestSuite(s_expr_from_python))

    # Some tests in the doctests style are too large to nicely fit into a docstring; better to keep them separate:
    tests.addTests(doctest.DocFileSuite("doctests/construct_x.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/construct_y.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/h_utils.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/unambiguous_weaving.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/form_analysis_into.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/form_analysis_construct.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/evaluator.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/free_variables.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/unused_definitions.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/name_dependencies.txt"))
    tests.addTests(doctest.DocFileSuite("doctests/lexical_addressing_x.txt"))

    return tests


if __name__ == '__main__':
    unittest.main()
