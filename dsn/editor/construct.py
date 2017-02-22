from s_address import node_for_s_address, s_dfs

from dsn.s_expr.legato import NoteSlur, NoteCapo

from dsn.s_expr.utils import (
    bubble_history_up,
    calc_possibility,
    insert_text_at,
    insert_node_at,
    replace_text_at,
)

from dsn.s_expr.clef import Delete, Insert, Replace, BecomeNode

from dsn.s_expr.structure import TreeNode

from dsn.editor.clef import (
    CursorChild,
    CursorDFS,
    CursorParent,
    CursorSet,
    EDelete,
    EncloseWithParent,
    InsertNodeChild,
    InsertNodeSibbling,
    LeaveChildrenBehind,
    SwapSibbling,
    TextInsert,
    TextReplace,
)


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

        p, h = calc_possibility(NoteSlur(Delete(delete_at_index), delete_from_hash))

        if delete_at_index == len(node_for_s_address(structure.tree, delete_from).children) - 1:
            # deletion makes cursor pos invalid: up to parent (alternative: sibbling-up first, until no more sibblings)
            new_s_cursor = delete_from
        else:
            new_s_cursor = structure.s_cursor  # "stay in place (although new contents slide into the cursor position)

        posacts = [p] + bubble_history_up(h, structure.tree, delete_from)

        return new_s_cursor, posacts, False

    if isinstance(edit_note, SwapSibbling):
        if structure.s_cursor == []:
            return an_error()  # root has no sibblings

        parent = node_for_s_address(structure.tree, structure.s_cursor[:-1])
        index = structure.s_cursor[-1] + edit_note.direction

        if not (0 <= index <= len(parent.children) - 1):
            return an_error()

        # For now, SwapSibbling is simply implemented as a "delete and insert"; if (or when) we'll introduce "Move" into
        # the Clef, we should note the move here.

        parent_s_address = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]
        delete_from_hash = node_for_s_address(structure.tree, parent_s_address).metadata.nout_hash
        reinsert_later_hash = node_for_s_address(structure.tree, structure.s_cursor).metadata.nout_hash

        p0, hash_after_deletion = calc_possibility(NoteSlur(Delete(delete_at_index), delete_from_hash))
        p1, hash_after_insertion = calc_possibility(NoteSlur(Insert(index, reinsert_later_hash), hash_after_deletion))

        new_cursor = structure.s_cursor[:-1] + [index]
        posacts = [p0, p1] + bubble_history_up(hash_after_insertion, structure.tree, parent_s_address)
        return new_cursor, posacts, False

    if isinstance(edit_note, LeaveChildrenBehind):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)
        if not hasattr(cursor_node, 'children'):
            return an_error()  # Leave _children_ behind presupposes the existance of children

        if structure.s_cursor == []:
            return an_error()  # Root cannot die

        # For now, LeaveChildrenBehind is simply implemented as a "delete and insert"; if (or when) we'll introduce
        # "Move" into the Clef, we should note the move here.

        parent_s_address = structure.s_cursor[:-1]
        delete_at_index = structure.s_cursor[-1]
        delete_from_hash = node_for_s_address(structure.tree, parent_s_address).metadata.nout_hash

        p, hash_ = calc_possibility(NoteSlur(Delete(delete_at_index), delete_from_hash))
        posacts = [p]

        removed_node = node_for_s_address(structure.tree, structure.s_cursor)
        for i, child in enumerate(removed_node.children):
            p, hash_ = calc_possibility(NoteSlur(Insert(structure.s_cursor[-1] + i, child.metadata.nout_hash), hash_))
            posacts.append(p)

        # In general, leaving the cursor at the same s_address will be great: post-deletion you'll be in the right spot
        new_cursor = structure.s_cursor
        if len(removed_node.children) == 0:
            # ... however, if there are no children to leave behind... this "right spot" may be illegal
            parent_node = node_for_s_address(structure.tree, parent_s_address)
            if len(parent_node.children) == 1:
                # if the deleted node was the only node: fall back to the parent
                new_cursor = parent_s_address
            else:
                # otherwise, make sure to stay in bounds.
                new_cursor[len(new_cursor) - 1] = min(
                    len(parent_node.children) - 1 - 1,  # len - 1 idiom; -1 for deletion.
                    new_cursor[len(new_cursor) - 1])

        posacts += bubble_history_up(hash_, structure.tree, parent_s_address)

        return new_cursor, posacts, False

    if isinstance(edit_note, EncloseWithParent):
        cursor_node = node_for_s_address(structure.tree, structure.s_cursor)

        if structure.s_cursor == []:
            # I am not sure about this one yet: should we have the option to create a new root? I don't see any direct
            # objections (by which I mean: it's possible in terms of the math), but I still have a sense that it may
            # create some asymmetries. For now I'm disallowing it; we'll see whether a use case arises.
            return an_error()

        # For now, EncloseWithParent is simply implemented as a "replace with the parent"; if (or when) we'll introduce
        # "Move" (in particular: the MoveReplace) into the Clef, we should note the move here.

        parent_s_address = structure.s_cursor[:-1]
        replace_at_index = structure.s_cursor[-1]
        replace_on_hash = node_for_s_address(structure.tree, parent_s_address).metadata.nout_hash

        reinsert_later_hash = node_for_s_address(structure.tree, structure.s_cursor).metadata.nout_hash

        p_capo, hash_capo = calc_possibility(NoteCapo())
        p_create, hash_create = calc_possibility(NoteSlur(BecomeNode(), hash_capo))

        p_enclosure, hash_enclosure = calc_possibility(NoteSlur(Insert(0, reinsert_later_hash), hash_create))

        p_replace, hash_replace = calc_possibility(
            NoteSlur(Replace(replace_at_index, hash_enclosure), replace_on_hash))

        posacts = [p_capo, p_create, p_enclosure, p_replace] + bubble_history_up(
                hash_replace, structure.tree, parent_s_address)

        # We jump the cursor to the newly enclosed location:
        new_cursor = structure.s_cursor + [0]

        return new_cursor, posacts, False

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
            return an_error()  # root has no sibblings

        parent = node_for_s_address(structure.tree, s_cursor[:-1])
        index = s_cursor[-1] + edit_node.direction

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
