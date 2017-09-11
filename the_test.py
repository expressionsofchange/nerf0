from posacts import Possibility, Actuality
from hashstore import NoutHashStore
from memoization import Stores, Memoization

from dsn.s_expr.construct_x import construct_x
from dsn.s_expr.clef import BecomeNode, TextBecome, Delete
from dsn.s_expr.legato import NoteNout, NoteCapo, NoteNoutHash
from dsn.s_expr.test_utils import iinsert, rreplace
from dsn.s_expr.utils import nouts_for_notes, nouts_for_notes_da_capo
from dsn.historiography.legato import HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo

from dsn.s_expr.unambiguous_weaving import uw_double_edge, is_valid_double_edge


p = NoutHashStore(NoteNoutHash, NoteNout, NoteCapo)
historiography_note_nout_store = NoutHashStore(
    HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo)
stores = Stores(p, historiography_note_nout_store)
m = Memoization()

capo = NoteCapo()
hash_capo = p.add(capo)

# ## Shared History: the empty node
# Let's start with the empty node; note that no interesting weaving can be done on the empty node (deletions & replacing
# cannot be done on the empty node; insertions collide by definition)

shared_history = nouts_for_notes_da_capo([BecomeNode()])

for nh in shared_history:
    p.add(nh.nout)

last_shared_hash = nh.nout_hash

# history_0 is used twice for this example
history_0 = nouts_for_notes([
    iinsert(p, 0, [TextBecome("new")]),
    ], last_shared_hash)

for nh in history_0:
    p.add(nh.nout)

nout_hash_0 = nh.nout_hash

is_valid_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_0)

# ## Shared History: a single child

# Having a single child allows for some more interesting cases. Notably: add before and after the reference-child

shared_history = nouts_for_notes_da_capo([
    BecomeNode(),
    iinsert(p, 0, [TextBecome("reference")]),
    ])

for nh in shared_history:
    p.add(nh.nout)

last_shared_hash = nh.nout_hash

# history_0: Insert a new element _before_ the only already existing element
history_0 = nouts_for_notes([
    iinsert(p, 0, [TextBecome("before")]),
    ], last_shared_hash)

for nh in history_0:
    p.add(nh.nout)

nout_hash_0 = nh.nout_hash

# history_1: Insert a new element _after_ the only already existing element
history_1 = nouts_for_notes([
    iinsert(p, 1, [TextBecome("after")]),
    ], last_shared_hash)

for nh in history_1:
    p.add(nh.nout)

nout_hash_1 = nh.nout_hash

for posact in uw_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1, [0, 1]):
    if isinstance(posact, Possibility):
        p.add(posact.nout)
    if isinstance(posact, Actuality):
        print("Result", posact.nout_hash)

print(construct_x(m, stores, posact.nout_hash))

# history_1: Replace the only already existing element
history_1 = nouts_for_notes([
    rreplace(p, 0, [TextBecome("replaced")]),
    ], last_shared_hash)

for nh in history_1:
    p.add(nh.nout)

nout_hash_1 = nh.nout_hash

for posact in uw_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1, [0, 1]):
    if isinstance(posact, Possibility):
        p.add(posact.nout)
    if isinstance(posact, Actuality):
        print("Result", posact.nout_hash)

print(construct_x(m, stores, posact.nout_hash))


# if history_0 is a deletion, replacing in history_1 is illegal

history_0 = nouts_for_notes([Delete(0)], last_shared_hash)

for nh in history_0:
    p.add(nh.nout)

nout_hash_0 = nh.nout_hash

is_valid_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1)

# Blah extend-only-histories.
# Note about TextBecome...

history_0 = nouts_for_notes([
    rreplace(p, 0, [TextBecome("replaced differently")]),
    ], last_shared_hash)

for nh in history_0:
    p.add(nh.nout)

nout_hash_0 = nh.nout_hash

is_valid_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1)


# ## Shared History: a multiple children

# Having multiple children allows for some more interesting cases, such as combining deletions & insertions in different
# parts of the children-list, and deleting in one side of the list while inserting in the other.

shared_history = nouts_for_notes_da_capo([
    BecomeNode(),
    iinsert(p, 0, [TextBecome("0")]),
    iinsert(p, 1, [TextBecome("1")]),
    iinsert(p, 2, [TextBecome("2")]),
    iinsert(p, 3, [TextBecome("3")]),
    iinsert(p, 4, [TextBecome("4")]),
    ])

for nh in shared_history:
    p.add(nh.nout)

last_shared_hash = nh.nout_hash

# history_0: Deletions are in decreasing order here only for reasons of understandbility of the test.
history_0 = nouts_for_notes([
    Delete(3),
    Delete(0),
    ], last_shared_hash)

for nh in history_0:
    p.add(nh.nout)

nout_hash_0 = nh.nout_hash

# history_1: Deletions are in decreasing order here only for reasons of understandbility of the test.
history_1 = nouts_for_notes([
    Delete(2),
    Delete(1),
    ], last_shared_hash)

for nh in history_1:
    p.add(nh.nout)

nout_hash_1 = nh.nout_hash

for posact in uw_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1, [0, 0, 1, 1]):
    if isinstance(posact, Possibility):
        p.add(posact.nout)
    if isinstance(posact, Actuality):
        print("Result", posact.nout_hash)

print(construct_x(m, stores, posact.nout_hash))

# multiple children: insertions & deletions combined

# history_1: the insertion
history_1 = nouts_for_notes([
    iinsert(p, 2, [TextBecome("inserted")]),
    ], last_shared_hash)

for nh in history_1:
    p.add(nh.nout)

nout_hash_1 = nh.nout_hash

for posact in uw_double_edge(m, stores, last_shared_hash, nout_hash_0, nout_hash_1, [0, 1, 0]):
    if isinstance(posact, Possibility):
        p.add(posact.nout)
    if isinstance(posact, Actuality):
        print("Result", posact.nout_hash)

print(construct_x(m, stores, posact.nout_hash))
