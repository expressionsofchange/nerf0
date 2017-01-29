from dsn.s_expr.legato import NoteNoutHash


class HistoriographyNote(object):

    @staticmethod
    def from_stream(byte_stream):
        # because there is only a single kind of HistoriograhyNote, we don't need a subtype-distinguisher here.
        return SetNoteNoutHash.from_stream(byte_stream)


class SetNoteNoutHash(HistoriographyNote):

    def __init__(self, note_nout_hash):
        self.note_nout_hash = note_nout_hash

    @staticmethod
    def from_stream(byte_stream):
        return SetNoteNoutHash(NoteNoutHash.from_stream(byte_stream))

    def as_bytes(self):
        return self.note_nout_hash.as_bytes()
