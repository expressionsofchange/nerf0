from historiography import Historiography, HistoriographyAt


def play_historiography_note(historiography_note, historiography_at):
    historiography_now_at = historiography_at.historiography.x_append(historiography_note.note_nout_hash)
    return historiography_now_at


def construct_historiography(m, stores, historiography_note_nout_hash):
    # In the beginning, there is the empty historiography
    historiography_at = HistoriographyAt(Historiography(stores.note_nout), 0)

    todo = []
    for tup in stores.historiography_note_nout.all_nhtups_for_nout_hash(historiography_note_nout_hash):
        if tup.nout_hash in m.construct_historiography:
            historiography_at = m.construct_historiography[tup.nout_hash]
            break
        todo.append(tup)

    for tup in reversed(todo):
        edge_nout = tup.nout
        edge_nout_hash = tup.nout_hash

        note = edge_nout.note

        historiography_at = play_historiography_note(note, historiography_at)
        m.construct_historiography[edge_nout_hash] = historiography_at

    return historiography_at
