from historiography import Historiography, HistoriographyAt


def play_historiography_note(historiography_note, historiography_at):
    historiography_now_at = historiography_at.historiography.x_append(historiography_note.note_nout_hash)
    return historiography_now_at


def construct_historiography(
            historiography_cache,
            note_nout_store,
            historiography_note_nout_store,
            historiography_note_nout_hash,
            ):

    # In the beginning, there is the empty historiography
    historiography_at = HistoriographyAt(Historiography(note_nout_store), 0)

    todo = []
    for tup in historiography_note_nout_store.all_nhtups_for_nout_hash(historiography_note_nout_hash):
        if tup.nout_hash in historiography_cache:
            historiography_at = historiography_cache[tup.nout_hash]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        historiography_at = play_historiography_note(note, historiography_at)
        historiography_cache[edge_nout_hash] = historiography_at

    return historiography_at
