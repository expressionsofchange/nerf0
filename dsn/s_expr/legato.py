from legato import nout_factory
from dsn.s_expr.clef import Note

NoteNout, NoteCapo, NoteSlur = nout_factory(Note, "Note")
