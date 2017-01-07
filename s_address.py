"""
>>> from trees import TreeNode
>>>
>>> node = TreeNode(children=[
...     TreeNode(children=[
...         TreeNode(children=[], metadata=[0, 0]),
...         TreeNode(children=[], metadata=[0, 1]),
...     ], metadata=[0]),
... ], metadata=[])
>>>
>>> node_for_s_address(node, []).metadata
[]
>>> node_for_s_address(node, [0]).metadata
[0]
>>> node_for_s_address(node, [0, 1]).metadata
[0, 1]
>>> node_for_s_address(node, [0, 1, 4]).metadata
Traceback (most recent call last):
IndexError: s_address out of bounds: [0, 1, 4]
>>> get_node_for_s_address(node, [0, 1, 4], 'sentinel value')
'sentinel value'
"""


def node_for_s_address(node, s_address):
    result = get_node_for_s_address(node, s_address)
    if result is None:
        raise IndexError("s_address out of bounds: %s" % s_address)

    return result


def get_node_for_s_address(node, s_address, default=None):
    # `get` in analogy with {}.get(k, d), returns a default value for non-existing addresses

    if s_address == []:
        return node

    if not hasattr(node, 'children'):
        return default

    if not (0 <= s_address[0] <= len(node.children) - 1):
        return default  # Index out of bounds

    return get_node_for_s_address(node.children[s_address[0]], s_address[1:], default)
