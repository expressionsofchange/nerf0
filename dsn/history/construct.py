from hashstore import Hash
from posacts import Possibility, Actuality
from cut_paste import some_more_cut_paste

from dsn.history.clef import (
    EHCursorChild,
    EHCursorDFS,
    EHCursorParent,
    EHCursorSet,
    EHDelete,
)


def ad_hoc_s_dfs(per_step_info, s_address):
    """Ad hoc rewrite of s_address for the Steps interface. The other option here is: make Steps confirm to the s_dfs
    interface (i.e. have nodes and children, rather than tuples of tuples)."""

    if s_address == []:
        result = []  # the rootlessness of per_step_info requires this special case.
    else:
        result = [s_address]

    for i, (nout_hash, dissonant, (t, children_steps)) in enumerate(per_step_info):
        result.extend(ad_hoc_s_dfs(children_steps, s_address + [i]))

    return result


def per_step_info_for_s_address(per_step_info, s_address):
    if s_address == []:
        return per_step_info

    for i, (nout_hash, dissonant, (t, children_steps)) in enumerate(per_step_info):
        if i == s_address[0]:
            return per_step_info_for_s_address(children_steps, s_address[1:])

    raise IndexError("s_address out of bounds")


def calc_possibility(nout):
    # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
    # copy/pasted from the HashStore implementation; but we need it here again.

    bytes_ = nout.as_bytes()
    hash_ = Hash.for_bytes(bytes_)
    return Possibility(nout), hash_


def eh_note_play(possible_timelines, structure, edit_note):
    # :: EHStructure, EHNote => (new) s_cursor, posacts, error
    def an_error():
        return structure.s_cursor, [], True

    if isinstance(edit_note, EHDelete):
        if len(structure.per_step_info) <= 1:
            # We don't allow the deletion of the final bit of history. This seems (though I'm not 100% sure) the
            # reasonable way forward, especially given the idea that "construct_x should always be able to construct
            # somethign valid". The reason I'm not sure: even the guarantee for non-empty histories alone is not enough
            # to guarantee histories that will have at least something non-None coming out of construct_x.
            return an_error()

        posacts = []

        top_index = structure.s_cursor[0]
        to_be_deleted, error, rhi = structure.per_step_info[top_index]

        edge_nout_hash, _, _ = structure.per_step_info[-1]

        if edge_nout_hash == to_be_deleted:
            # Alternative (equivalent) implementation
            # last_hash = self.possible_timelines.get(to_be_deleted).previous_hash

            penultimate_step = structure.per_step_info[-2]
            last_hash, dissonant, (t, children_steps) = penultimate_step

        else:
            results = some_more_cut_paste(
                possible_timelines,
                edge_nout_hash,
                to_be_deleted,
                possible_timelines.get(to_be_deleted).previous_hash)

            # AFAIU, cut_paste always leads to some results at least, so a fallback like the below is not necessary:
            # last_hash = edge_nout_hash

            for possibility in results:
                posacts.append(possibility)
                _, last_hash = calc_possibility(possibility.nout)

        # because we cut at the top level only, there's no need to bubble.
        # self.update_nout_hash(last_hash)  STILL NEEDS TO BE REPLACED, on the GUI side.

        posacts.append(Actuality(last_hash))

        # TODO Here we also need to update the cursor if we so desire. (At least: keep it inside the newly created
        # bounds)
        return structure.s_cursor, posacts, False

    # It seems a good idea to push for factoring out the commonalities between cursor movement in the HistoryWidget and
    # the TreeWidget.

    # In practice that's somewhat complicated by the fact that they don't both use trees with .children (in that case we
    # could just ducktype)

    # Besides that, there are some questions on how to model the shared Notes, and the shared playing of notes. For now,
    # the answer doesn't really matter... options are:
    # * Include certain Notes in both Clefs.
    # * Have a wrapper-note (ECursor / EHCursor) which refers to a Cursor note.

    # Given the above, I have just pushed forward by copy/pasting and editing; cleanup to follow later.

    def move_cursor(new_cursor):
        return new_cursor, [], False

    if isinstance(edit_note, EHCursorDFS):
        dfs = ad_hoc_s_dfs(structure.per_step_info, [])
        dfs_index = dfs.index(structure.s_cursor) + edit_note.direction
        if not (0 <= dfs_index <= len(dfs) - 1):
            return an_error()
        return move_cursor(dfs[dfs_index])

    if isinstance(edit_note, EHCursorSet):
        return move_cursor(edit_note.s_address)

    if isinstance(edit_note, EHCursorParent):
        # N.B.: different from the TreeWidget case: our root is a single list, rather than an actual root.
        if len(structure.s_cursor) == 1:
            return an_error()
        return move_cursor(structure.s_cursor[:-1])

    if isinstance(edit_note, EHCursorChild):
        per_step_infos = per_step_info_for_s_address(structure.per_step_info, structure.s_cursor)
        if len(per_step_infos) == 0:
            return an_error()
        return move_cursor(structure.s_cursor + [0])

    raise Exception("Unknown Note")
