from s_address import node_for_s_address, s_dfs
from hashstore import Hash
from posacts import Possibility, Actuality
from legato import NoutBegin, NoutBlock
from clef import Replace

from clef import (
    BecomeNode,
    Delete,
    Insert,
    TextBecome,
)
from trees import TreeNode

from dsn.editor.clef import (
    CursorChild,
    CursorDFS,
    CursorParent,
    CursorSet,
    EDelete,
    InsertNodeChild,
    InsertNodeSibbling,
    TextInsert,
    TextReplace,
)


def calc_possibility(nout):
    # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
    # copy/pasted from the HashStore implementation; but we need it here again.

    bytes_ = nout.as_bytes()
    hash_ = Hash.for_bytes(bytes_)
    return Possibility(nout), hash_


def calc_actuality(nout_hash):
    return Actuality(nout_hash)


def bubble_history_up(hash_to_bubble, tree, s_address):
    """Recursively replace history to reflect a change (hash_to_bubble) at a lower level (s_address)"""

    posacts = []
    for i in reversed(range(len(s_address))):
        # We slide a window of size 2 over the s_address from right to left, like so:
        # [..., ..., ..., ..., ..., ..., ...]  <- s_address
        #                              ^  ^
        #                           [:i]  i
        # For each such i, the sliced array s_address[:i] gives you the s_address of a node in which a replacement
        # takes place, and s_address[i] gives you the index to replace at.
        #
        # Regarding the range (0, len(s_address)) the following:
        # * len(s_address) means the s_address itself is the first thing to be replaced.
        # * 0 means: the last replacement is _inside_ the root node (s_address=[]), at index s_address[0]
        replace_in = node_for_s_address(tree, s_address[:i])

        p, hash_to_bubble = calc_possibility(
            NoutBlock(Replace(s_address[i], hash_to_bubble), replace_in.metadata.nout_hash))

        posacts.append(p)

    # The root node (s_address=[]) itself cannot be replaced, its replacement is represented as "Actuality updated"
    posacts.append(calc_actuality(hash_to_bubble))
    return posacts


# TODO: insert_xxx_at: I see a pattern here!
def insert_text_at(tree, parent_s_address, index, text):
    parent_node = node_for_s_address(tree, parent_s_address)

    pa0, begin = calc_possibility(NoutBegin())
    pa1, to_be_inserted = calc_possibility(NoutBlock(TextBecome(text), begin))

    pa2, insertion = calc_possibility(
        NoutBlock(Insert(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, parent_s_address)
    return [pa0, pa1, pa2] + posacts


def insert_node_at(tree, parent_s_address, index):
    parent_node = node_for_s_address(tree, parent_s_address)

    pa0, begin = calc_possibility(NoutBegin())
    pa1, to_be_inserted = calc_possibility(NoutBlock(BecomeNode(), begin))

    pa2, insertion = calc_possibility(
        NoutBlock(Insert(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, parent_s_address)
    return [pa0, pa1, pa2] + posacts


def replace_text_at(tree, s_address, text):
    parent_node = node_for_s_address(tree, s_address[:-1])

    pa0, begin = calc_possibility(NoutBegin())
    pa1, to_be_inserted = calc_possibility(NoutBlock(TextBecome(text), begin))

    index = s_address[-1]

    pa2, insertion = calc_possibility(
        NoutBlock(Replace(index, to_be_inserted), parent_node.metadata.nout_hash))

    posacts = bubble_history_up(insertion, tree, s_address[:-1])
    return [pa0, pa1, pa2] + posacts


def edit_note_play(structure, edit_note):
    # :: EditStructure, EditNote => (new) s_cursor, posacts, error
    def an_error():
        return structure.s_cursor, [], True

    if isinstance(edit_note, TextInsert):
        posacts = insert_text_at(structure.tree, edit_note.parent_s_address, edit_note.index, edit_note.text)
        new_s_cursor = edit_note.parent_s_address + [edit_note.index]
        return new_s_cursor, posacts, False

    if isinstance(edit_note, TextReplace):
        posacts = replace_text_at(structure.tree, edit_note.s_address, edit_note.text)
        return edit_note.s_address, posacts, False

    if isinstance(edit_note, InsertNodeSibbling):
        if structure.s_cursor == []:
            return an_error()  # adding sibblings to the root is not possible (it would lead to a forest)

        # because direction is in [0, 1]... no need to minimize/maximize (PROVE!)
        # (Of course, that _does_ depend on the direction being in the 0, 1 range :-P )
        index = structure.s_cursor[-1] + edit_note.direction

        posacts = insert_node_at(structure.tree, structure.s_cursor[:-1], index)
        new_s_cursor = structure.s_cursor[:-1] + [index]

        return new_s_cursor, posacts, False

    if isinstance(edit_note, InsertNodeChild):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not isinstance(cursor_node, TreeNode):
            # for now... we just silently ignore the user's request when they ask to add a child node to a non-node
            return an_error()

        index = len(cursor_node.children)
        posacts = insert_node_at(structure.tree, structure.s_cursor, index)
        new_s_cursor = structure.s_cursor + [index]

        return new_s_cursor, posacts, False

    if isinstance(edit_note, EDelete):
        if structure.s_cursor == []:
            # silently ignored ('delete root' is not defined, because the root is assumed to exist.)
            return an_error()

        delete_from = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]
        delete_from_hash = node_for_s_address(structure.tree, delete_from).metadata.nout_hash

        p, h = calc_possibility(NoutBlock(Delete(delete_at_index), delete_from_hash))

        if delete_at_index == len(node_for_s_address(structure.tree, delete_from).children) - 1:
            # deletion makes cursor pos invalid: up to parent (alternative: sibbling-up first, until no more sibblings)
            new_s_cursor = delete_from
        else:
            new_s_cursor = structure.s_cursor  # "stay in place (although new contents slide into the cursor position)

        posacts = [p] + bubble_history_up(h, structure.tree, delete_from)

        return new_s_cursor, posacts, False

    def move_cursor(new_cursor):
        return new_cursor, [], False

    if isinstance(edit_note, CursorDFS):
        dfs = s_dfs(structure.tree, [])
        dfs_index = dfs.index(structure.s_cursor) + edit_note.direction
        if not (0 <= dfs_index <= len(dfs) - 1):
            return an_error()
        return move_cursor(dfs[dfs_index])

    """At some point I had "regular sibbling" (as opposed to DFS sibbling) in the edit_clef. It looks like this:

        if structure.s_cursor == []:
            return an_error() # root has no sibblings

        parent = node_for_s_address(structure.tree, s_cursor[:-1])
        index = s_cursor[-1] + direction

        if not (0 <= index <= len(parent.children) - 1):
            return an_error()
        return move_cursor(s_cursor[:-1] + [index])
    """
    if isinstance(edit_note, CursorSet):
        return move_cursor(edit_note.s_address)

    if isinstance(edit_note, CursorParent):
        if structure.s_cursor == []:
            return an_error()
        return move_cursor(structure.s_cursor[:-1])

    if isinstance(edit_note, CursorChild):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not hasattr(cursor_node, 'children') or len(cursor_node.children) == 0:
            return an_error()
        return move_cursor(structure.s_cursor + [0])

    raise Exception("Unknown Note")
