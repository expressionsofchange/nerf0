import unittest
import doctest
import channel
import historiography


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(channel))
    tests.addTests(doctest.DocTestSuite(historiography))
    return tests


if __name__ == '__main__':
    unittest.main()
