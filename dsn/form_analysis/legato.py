from type_factories import nout_factory
from dsn.form_analysis.clef import FormNote, FormListNote, AtomNote, AtomListNote

FormNoteNout, FormNoteCapo, FormNoteSlur, FormNoteNoutHash = nout_factory(FormNote, "FormNote")
FormListNoteNout, FormListNoteCapo, FormListNoteSlur, FormListNoteNoutHash = nout_factory(FormListNote, "FormListNote")
AtomNoteNout, AtomNoteCapo, AtomNoteSlur, AtomNoteNoutHash = nout_factory(AtomNote, "AtomNote")
AtomListNoteNout, AtomListNoteCapo, AtomListNoteSlur, AtomListNoteNoutHash = nout_factory(AtomListNote, "AtomListNote")
