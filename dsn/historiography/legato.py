from type_factories import nout_factory

from dsn.historiography.clef import HistoriographyNote

HistoriographyNoteNout, HistoriographyNoteCapo, HistoriographyNoteSlur, HistoriographyNoteNoutHash = \
    nout_factory(HistoriographyNote, "HistoriographyNote")
