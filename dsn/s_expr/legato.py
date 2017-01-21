from legato import nout_factory
from dsn.s_expr.clef import Note, parse_note

NoutSlur, parse_nout = nout_factory(Note, parse_note)
