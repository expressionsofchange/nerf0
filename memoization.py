"""
"There are only two hard things in Computer Science: cache invalidation and naming things." Here are some notes about
one of those (caching).

In a "nerfy context", there are a few things that we can use to make it less hard; but not completely trivial.

In particular, we can use the fact that we can be precise about history to make the question of _cache invalidation_
less of an issue. The question of "cache invalidation" is one about time, and whether a cache is still valid at a
particular point in time. This is answered in the nerfy world including the "global clock" (some nout_note's hash) as a
component of the cache lookup (sometimes: as the only component).

Assuming that we don't have infinite storage space for our caches, this still leaves other cache-related questions open
though, such as the question "which caches must be kept around?" (Cache replacement policies) I currently have no such
policy (we use up as much space as we need).

There's also the following idea: if you can just make it faster, rather than caching stuff, that's always preferred.
Said differently: caching buys you some performance for storage space, but it's a cheap replacement for thinking hard
about the relevant algorithms yourself. Of course, because we are still in an experimental phase, this may in fact be
the correct choice!

And finally, the following observation: many (but not all) of the structures we build have a small incremental
(sometimes constant) cost per Note (unit of time). This means that memoization using the timely component (hash) is very
useful for those functions: it allows new steps to be made in O(1) time (basically: using dynamic programming). However,
we are not yet explicit about which functions rely on this fact for decent performance.

"""


class Stores(object):
    """Keep the various NoutHashStore objects in a single container"""

    def __init__(self, note_nout, historiography_note_nout):
        self.note_nout = note_nout
        self.historiography_note_nout = historiography_note_nout

        # TODO: the organization of construction of the various NoutHashStores is TBD. I've taken an ad hoc approach of
        # doing it inline for now
        from hashstore import NoutHashStore
        from dsn.form_analysis.legato import FormNoteNoutHash, FormNoteNout, FormNoteCapo
        self.form_note_nout = NoutHashStore(FormNoteNoutHash, FormNoteNout, FormNoteCapo)

        from dsn.form_analysis.legato import FormListNoteNoutHash, FormListNoteNout, FormListNoteCapo
        self.form_list_note_nout = NoutHashStore(FormListNoteNoutHash, FormListNoteNout, FormListNoteCapo)

        from dsn.form_analysis.legato import AtomNoteNoutHash, AtomNoteNout, AtomNoteCapo
        self.form_list_note_nout = NoutHashStore(AtomNoteNoutHash, AtomNoteNout, AtomNoteCapo)

        from dsn.form_analysis.legato import AtomListNoteNoutHash, AtomListNoteNout, AtomListNoteCapo
        self.form_list_note_nout = NoutHashStore(AtomListNoteNoutHash, AtomListNoteNout, AtomListNoteCapo)


class Memoization(object):
    """Single point of access for all memoized functions"""

    def __init__(self):
        self.construct_x = {}
        self.construct_y = {}
        self.construct_historiography = {}
        self.construct_historiography_treenode = {}
        self.view_past_from_present = {}
        self.texture_for_text = {}
        self.construct_form = {}
        self.construct_form_list = {}
        self.construct_atom = {}
        self.construct_atom_list = {}
