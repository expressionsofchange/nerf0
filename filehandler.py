from legato import NoutBegin, NoutBlock
from clef import BecomeNode
from posacts import parse_pos_acts, Possibility, Actuality
from hashstore import Hash


class FileWriter(object):
    """For lack of a better name: Handles the writing of Possibility/Actuality objects to files."""

    def __init__(self, channel, filename):
        self.file_ = open(filename, 'ab')  # LATER: proper file-closing too!
        channel.connect(self.receive)  # receive-only connection: FileWriters are ChannelReaders

    def receive(self, data):
        # Receives: Possibility | Actuality; writes it to the connected file
        self.file_.write(data.as_bytes())
        self.file_.flush()


def read_from_file(filename, channel):
    byte_stream = iter(open(filename, 'rb').read())
    for pos_act in parse_pos_acts(byte_stream):
        channel.broadcast(pos_act)


def initialize_history(channel):
    def hash_for(nout):
        # copy/pasta... e.g. from cli.py (at the time of copy/pasting)
        bytes_ = nout.as_bytes()
        return Hash.for_bytes(bytes_)

    def as_iter():
        begin = NoutBegin()
        yield Possibility(begin)

        root_node_nout = NoutBlock(BecomeNode(), hash_for(begin))
        yield Possibility(root_node_nout)
        yield Actuality(hash_for(root_node_nout))

    for item in as_iter():
        channel.broadcast(item)
