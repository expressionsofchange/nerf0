import unittest
import doctest
import channel


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(channel))
    return tests


if __name__ == '__main__':
    unittest.main()
