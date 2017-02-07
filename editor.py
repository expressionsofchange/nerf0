from sys import argv
from os.path import isfile

from kivy.app import App
from kivy.core.text.markup import LabelBase
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.config import Config

from channel import ClosableChannel

from filehandler import (
    FileWriter,
    initialize_history,
    read_from_file
)

from posacts import Actuality, HashStoreChannelListener, LatestActualityListener

from widgets.tree import TreeWidget
from widgets.history import HistoryWidget

from dsn.historiography.legato import HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo
from hashstore import NoutHashStore
from memoization import Memoization, Stores

# How to tell Kivy about font locations; should be generalized
LabelBase.register(name="DejaVuSans",
                   fn_regular="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   fn_bold="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   fn_italic="/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
                   fn_bolditalic="/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",)

Config.set('kivy', 'exit_on_escape', '0')


class EditorGUI(App):

    def __init__(self, filename):
        super(EditorGUI, self).__init__()

        self.m = Memoization()

        self.historiography_note_nout_store = NoutHashStore(
            HistoriographyNoteNoutHash, HistoriographyNoteNout, HistoriographyNoteCapo)

        self.filename = filename

        self.setup_channels()

        self.stores = Stores(self.possible_timelines, self.historiography_note_nout_store)

        self.do_initial_file_read()

    def setup_channels(self):
        # This is the main channel of PosActs for our application.
        self.history_channel = ClosableChannel()  # Pun not intended
        self.possible_timelines = HashStoreChannelListener(self.history_channel).possible_timelines
        self.lnh = LatestActualityListener(self.history_channel)

    def do_initial_file_read(self):
        if isfile(self.filename):
            # ReadFromFile before connecting to the Writer to ensure that reading from the file does not write to it
            read_from_file(self.filename, self.history_channel)
            FileWriter(self.history_channel, self.filename)
        else:
            # FileWriter first to ensure that the initialization becomes part of the file.
            FileWriter(self.history_channel, self.filename)
            initialize_history(self.history_channel)

    def add_tree_and_stuff(self, history_channel):
        horizontal_layout = BoxLayout(spacing=10, orientation='horizontal')

        tree = TreeWidget(
            m=self.m,
            stores=self.stores,
            size_hint=(.5, 1),
            history_channel=history_channel,
            )

        history_widget = HistoryWidget(
            m=self.m,
            stores=self.stores,
            size_hint=(.5, 1),
            )
        horizontal_layout.add_widget(history_widget)
        horizontal_layout.add_widget(tree)

        self.vertical_layout.add_widget(horizontal_layout)

        tree.cursor_channel.connect(history_widget.parent_cursor_update)
        tree.focus = True
        return tree

    def build(self):
        self.vertical_layout = GridLayout(spacing=10, cols=1)

        tree = self.add_tree_and_stuff(self.history_channel)
        tree.report_new_tree_to_app = self.add_tree_and_stuff

        # we kick off with the state so far
        tree.receive_from_channel(Actuality(self.lnh.nout_hash))

        return self.vertical_layout


def main():
    if len(argv) != 2:
        print("Usage: ", argv[0], "FILENAME")
        exit()

    EditorGUI(argv[1]).run()


if __name__ == "__main__":
    main()
