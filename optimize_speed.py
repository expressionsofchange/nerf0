from channel import ClosableChannel
from posacts import HashStoreChannelListener, LatestActualityListener
from hashstore import NoutHashStore
from memoization import Stores, Memoization

from filehandler import read_from_file

from dsn.s_expr.h_utils import view_past_from_present
from dsn.historiography.legato import (
    HistoriographyNoteNoutHash,
    HistoriographyNoteNout,
    HistoriographyNoteSlur,
    HistoriographyNoteCapo,
)

from dsn.historiography.clef import SetNoteNoutHash

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

historiography_note_nout_store = NoutHashStore(
    HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo)

# This is the main channel of PosActs for our application.
history_channel = ClosableChannel()
possible_timelines = HashStoreChannelListener(history_channel).possible_timelines
lnh = LatestActualityListener(history_channel)

read_from_file(filename, history_channel)

nout_hash = lnh.nout_hash

stores = Stores(
    possible_timelines,
    historiography_note_nout_store,
)
m = Memoization()

for i in range(2):
    # this is what the HistoryWidget would do

    historiography_note_nout = HistoriographyNoteSlur(
        SetNoteNoutHash(nout_hash),
        HistoriographyNoteNoutHash.for_object(HistoriographyNoteCapo()),
    )

    with Timer('2'):
        liveness_annotated_hashes = view_past_from_present(
            m,
            stores,
            historiography_note_nout,
            nout_hash,
            )
