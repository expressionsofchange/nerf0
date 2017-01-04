from legato import NoutBegin, NoutBlock, parse_nout
from clef import BecomeNode
from posacts import parse_pos_acts, Possibility, Actuality
from hashstore import HashStore, Hash


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


class RealmOfThePossible(object):
    """For lack of a better name;
    also: should probably be moved to another file.

    Listens to a channel; all Possibility objects are stored in a (presumable: globally readable) HashStore.

    In other words: it's the channel-listening HashStore thingie.
    """

    def __init__(self, channel):
        self.possible_timelines = HashStore(parse_nout)

        # receive-only connection: RealmOfThePossible's outwards communication goes via others reading
        # self.possible_timelines
        channel.connect(self.receive)

    def receive(self, data):
        # Receives: Possibility | Actuality; the former are stored, the latter ignored.
        if isinstance(data, Possibility):
            self.possible_timelines.add(data.nout)

'''
below is the copy/paste garbage of combining all filehandling in a single class

class FileHandler(object):
    """For lack of a better name.
    Handles the writing/reading of Possibility/Actuality objects to files."""

    def __init__(self, channel):
        self.send = channel.connect(self.receive)

    def open(self, filename):
        # read a bunch of data from the file; send those to the channel
        # ...
        pass

    def receive(self, data):
        # Receives: Possibility | Actuality; writes it to the connected file
        self.file_.write(data.as_bytes())

    def write_actuality(f, nout):
        # I doubt this belongs here too!
        f.write(Actuality(nout).as_bytes())

    def read_from_file(self, filename):
        # DD: actually, I wonder if there's _any_ relationship between the reading and writing modes of operation of the
        # FileHandler; if there turns out to be no such relationship, I could consider a split.
        # Hmmmm... I'm gonna do that straight away
        byte_stream = iter(open(filename, 'rb').read())
        for pos_act in parse_pos_acts(byte_stream):
            self.send(pos_act)

    def create_emtpy_ofzo(self, filename):
        # I'm quite sure this does _not_ belong in here.
        # At some point: 'possiblyActually' should become a function
        begin = NoutBegin()
        yield Possibility(begin)
        yield Actuality(begin)

        root_node_nout = NoutBlock(BecomeNode(), begin)
        yield Possibility(root_node_nout)
        yield Actuality(root_node_nout)

    def switch_to_writing_mode(self, filename):
        """Switches to file-writing (and channel-receiving) mode"""
        # LATER: add mechanisms for properly closing the file
        self.file_ = open(filename, 'ab')

    def cutpaste_elsewhere():
        for pos_act in parse_pos_acts(byte_stream):
            if isinstance(pos_act, Possibility):
                possible_timelines.add(pos_act.nout)
            else:  # Actuality
                # this can be depended on to happen at least once ... if the file is correct
                present_nout = pos_act.nout_hash
'''
