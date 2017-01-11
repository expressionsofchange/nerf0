"""
Come into being; add a first item
>>> t2s, s2t = st_become()
>>> t2s, s2t
([], [])
>>> t2s, s2t = st_insert(t2s, s2t, 0)
>>> t2s, s2t
([0], [0])

Insert at the beginning, after which s_address 0 maps to t_address 1
>>> t2s, s2t = st_insert(t2s, s2t, 0)
>>> t2s, s2t
([1, 0], [1, 0])

Delete the first item (s_address 0, t_address 1)
>>> t2s, s2t = st_delete(t2s, s2t, 0)
>>> t2s, s2t
([0, None], [0])

Insert a new (t_address: 2) item at the end (s_address: 1)
>>> t2s, s2t = st_insert(t2s, s2t, 1)
>>> t2s, s2t
([0, None, 1], [0, 2])

Delete the first item (s_address 0, t_address 0)
>>> t2s, s2t = st_delete(t2s, s2t, 0)
>>> t2s, s2t
([None, None, 0], [2])
"""


def st_sanity(t2s, s2t):
    for (t, s) in enumerate(t2s):
        assert s is None or (0 <= s <= len(t2s) - 1 and s2t[s] == t), "%s <X> %s" % (s2t, t2s)

    for (s, t) in enumerate(s2t):
        assert 0 <= t <= len(t2s) - 1 and t2s[t] == s, "%s <X> %s" % (s2t, t2s)


def st_become():
    # trivial; introduced here for reasons of symmetry
    return [], []


def st_insert(prev_t2s, prev_s2t, index):
    t2s = [(i if i is None or i < index else i + 1) for i in prev_t2s] + [index]
    s2t = prev_s2t[:]
    s2t.insert(index, len(t2s) - 1)
    return t2s, s2t


def st_delete(prev_t2s, prev_s2t, index):
    t2s = [(i if (i is None or i < index) else i - 1) for i in prev_t2s]
    t2s[prev_s2t[index]] = None

    s2t = prev_s2t[:]
    del s2t[index]
    return t2s, s2t


def st_replace(prev_t2s, prev_s2t, index):
    # trivial, introduced here for reasons of symmetry
    return prev_t2s[:], prev_s2t[:]


def t_address_for_s_address(node, s_address):
    result = get_t_address_for_s_address(node, s_address)
    if result is None:
        raise IndexError("s_address out of bounds: %s" % s_address)

    return result


def get_t_address_for_s_address(node, s_address, _collected=[], default=None):
    # `get` in analogy with {}.get(k, d), returns a default value for non-existing addresses

    if s_address == []:
        return _collected

    if not hasattr(node, 's2t'):
        return default

    if not (0 <= s_address[0] <= len(node.s2t) - 1):
        return default  # Index out of bounds

    _collected += [node.s2t[s_address[0]]]
    return get_t_address_for_s_address(node.children[s_address[0]], s_address[1:], _collected, default)


# TODO factor out commonalities
def s_address_for_t_address(node, t_address):
    result = get_s_address_for_t_address(node, t_address)
    if result is None:
        raise IndexError("s_address out of bounds: %s" % t_address)

    return result


def get_s_address_for_t_address(node, t_address, _collected=None, default=None):
    # `get` in analogy with {}.get(k, d), returns a default value for non-existing addresses
    if _collected is None:
        _collected = []

    if t_address == []:
        return _collected

    if not hasattr(node, 't2s'):
        return default

    if not (0 <= t_address[0] <= len(node.t2s) - 1):
        return default  # Index out of bounds

    s_index = node.t2s[t_address[0]]
    _collected += [s_index]
    return get_s_address_for_t_address(node.children[s_index], t_address[1:], _collected, default)


def best_s_address_for_t_address(node, t_address, _collected=None):
    # TODO explain "best"
    if _collected is None:
        _collected = []

    if t_address == []:
        return _collected

    if not hasattr(node, 't2s'):
        return _collected

    if not (0 <= t_address[0] <= len(node.t2s) - 1):
        return _collected  # Index out of bounds

    s_index = node.t2s[t_address[0]]
    if s_index is None:
        return _collected  # Removed in space

    _collected += [s_index]
    return best_s_address_for_t_address(node.children[s_index], t_address[1:], _collected)
