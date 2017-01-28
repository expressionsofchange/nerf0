from dsn.s_expr.legato import NoteCapo, NoteSlur, NoteNoutHash

from dsn.s_expr.clef import BecomeNode
from posacts import PosAct, Possibility, Actuality


class FileWriter(object):
    """For lack of a better name: Handles the writing of Possibility/Actuality objects to files."""

    def __init__(self, channel, filename):
        # LATER: proper file-closing too! In the status quo there's 2 (related) open ends:
        # 1] we don't do any file closing ourselves at any point
        # 2] we don't have an implementation for closing channels yet
        self.file_ = open(filename, 'ab')

        # receive-only connection: FileWriters are ChannelReaders
        channel.connect(self.receive)

    def receive(self, data):
        # Receives: Possibility | Actuality; writes it to the connected file
        self.file_.write(data.as_bytes())
        self.file_.flush()


def read_from_file(filename, channel):
    byte_stream = iter(open(filename, 'rb').read())
    for pos_act in PosAct.all_from_stream(byte_stream):
        channel.broadcast(pos_act)


def initialize_history(channel):
    def as_iter():
        capo = NoteCapo()
        yield Possibility(capo)

        root_node_nout = NoteSlur(BecomeNode(), NoteNoutHash.for_object(capo))
        yield Possibility(root_node_nout)
        yield Actuality(NoteNoutHash.for_object(root_node_nout))

    for item in as_iter():
        channel.broadcast(item)
