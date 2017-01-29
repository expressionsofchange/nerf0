from channel import ClosableChannel
from posacts import HashStoreChannelListener, LatestActualityListener
from hashstore import NoutHashStore

from filehandler import read_from_file

from dsn.s_expr.construct_y import construct_y_from_scratch
from dsn.s_expr.h_utils import view_past_from_present
from dsn.historiography.legato import HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo

from time import clock


class Timer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = clock()
        return self

    def __exit__(self, *args):
        self.end = clock()
        print(self.name, self.end - self.start)


filename = 'bigfile'
very_particular_cache = {}
construct_y_cache = {}
historiography_cache = {}

historiography_note_nout_store = NoutHashStore(
    HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo)

historiography_note_nout_store.add(HistoriographyNoteCapo())  # TODO where to really put this??!

# This is the main channel of PosActs for our application.
history_channel = ClosableChannel()
possible_timelines = HashStoreChannelListener(history_channel).possible_timelines
lnh = LatestActualityListener(history_channel)

read_from_file(filename, history_channel)

nout_hash = lnh.nout_hash

for i in range(2):
    # this is what the HistoryWidget would do
    with Timer('1'):
        new_htn, h2, new_annotated_hashes = construct_y_from_scratch(
            construct_y_cache,
            possible_timelines,

            construct_y_cache,
            historiography_cache,
            historiography_note_nout_store,

            nout_hash)

    edge_nout_hash, _, _ = new_annotated_hashes[-1]

    with Timer('2'):
        liveness_annotated_hashes = view_past_from_present(
            possible_timelines=possible_timelines,
            historiography_note_nout_store=historiography_note_nout_store,

            present_root_htn=new_htn,
            annotated_hashes=new_annotated_hashes,

            # Alternatively, we use the knowledge that at the top_level "everything is live"
            alive_at_my_level=list(possible_timelines.all_preceding_nout_hashes(edge_nout_hash)),
            )
