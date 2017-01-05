import unittest
import doctest

import channel
import historiography
import spacetime
import vlq
import utils


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(utils))
    tests.addTests(doctest.DocTestSuite(channel))
    tests.addTests(doctest.DocTestSuite(historiography))
    tests.addTests(doctest.DocTestSuite(spacetime))
    tests.addTests(doctest.DocTestSuite(vlq))
    return tests


if __name__ == '__main__':
    unittest.main()
