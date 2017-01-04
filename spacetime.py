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
