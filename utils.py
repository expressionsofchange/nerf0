def pmts(v, type_):
    """Poor man's type system"""
    assert isinstance(v, type_), "Expected value of type '%s' but is type '%s'" % (type_.__name__, type(v).__name__)


def rfs(byte_stream, n):
    # read n bytes from stream
    return bytes((next(byte_stream) for i in range(n)))


def i_flat_zip_longest(*iterators):
    """Yields from all iterators in a flat zipped manner, until the longest is fully consumed.

    >>> list(i_flat_zip_longest(iter(['a', 'b', 'c']), iter([1, 2]), iter('FOOBAR')))
    ['a', 1, 'F', 'b', 2, 'O', 'c', 'O', 'B', 'A', 'R']
    """

    live = list(iterators)
    while len(live) > 0:
        for it in live:
            try:
                v = next(it)
                yield v
            except StopIteration:
                live.remove(it)
