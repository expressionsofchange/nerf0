class Stores(object):
    """Keep the various NoutHashStore objects in a single container"""

    def __init__(self, note_nout, historiography_note_nout):
        self.note_nout = note_nout
        self.historiography_note_nout = historiography_note_nout


class Memoization(object):
    """Single point of access for all memoized functions"""

    def __init__(self):
        self.construct_x = {}
        self.construct_y = {}
        self.construct_historiography = {}
        self.construct_historiography_treenode = {}
