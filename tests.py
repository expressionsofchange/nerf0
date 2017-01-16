import unittest
import doctest

import channel
import historiography
import spacetime
import vlq
import utils
import s_address


def load_tests(loader, tests, ignore):
    # Test the docstrings inside our actual codebase
    tests.addTests(doctest.DocTestSuite(utils))
    tests.addTests(doctest.DocTestSuite(channel))
    tests.addTests(doctest.DocTestSuite(historiography))
    tests.addTests(doctest.DocTestSuite(spacetime))
    tests.addTests(doctest.DocTestSuite(vlq))
    tests.addTests(doctest.DocTestSuite(s_address))

    # Some tests in the doctests style are too large to nicely fit into a docstring; better to keep them separate:
    tests.addTests(doctest.DocFileSuite("doctests/construct_x.txt"))

    return tests


if __name__ == '__main__':
    unittest.main()
