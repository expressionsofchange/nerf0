# coding=utf-8
from os.path import isfile

from channel import Channel
from datastructure import (
    BecomeNode,
    Delete,
    Insert,
    NoutBegin,
    NoutBlock,
    construct_x,
    Replace,
    TextBecome,
    TreeNode,
)

from posacts import (
    Actuality,
    Possibility,
)
from hashstore import (
    Hash,
)

from filehandler import (
    FileWriter,
    RealmOfThePossible,
    initialize_history,
    read_from_file
)


def print_nouts(possible_timelines, present_nout_hash):
    # Shows how the Nouts ref, but does not go inside notes
    present_nout = possible_timelines.get(present_nout_hash)
    prev_nout = possible_timelines.get(present_nout.previous_hash)

    if prev_nout == NoutBegin():
        result = ""
    else:
        result = print_nouts(possible_timelines, present_nout.previous_hash) + "\n"

    return result + repr(present_nout_hash) + ': ' + repr(present_nout)


def print_nouts_2(possible_timelines, present_nout_hash, indentation, seen):
    # Shows how the Nouts ref recursively
    if present_nout_hash.as_bytes() in seen:
        return (indentation * " ") + repr(present_nout_hash) + ":..."

    seen.add(present_nout_hash.as_bytes())
    present_nout = possible_timelines.get(present_nout_hash)

    if present_nout == NoutBegin():
        result = ""
    else:
        result = print_nouts_2(possible_timelines, present_nout.previous_hash, indentation, seen) + "\n\n"

    if hasattr(present_nout, 'note') and hasattr(present_nout.note, 'nout_hash'):
        horizontal_recursion = "\n" + print_nouts_2(possible_timelines, present_nout.note.nout_hash, indentation + 4,
                                                    seen)
    else:
        horizontal_recursion = ""

    return result + (indentation * " ") + repr(present_nout_hash) + ': ' + repr(present_nout) + horizontal_recursion


class CLI(object):
    def __init__(self, parent_channel, possible_timelines, autosave):
        self._send_to_parent = parent_channel.connect(self.receive_from_parent)
        self.autosave = autosave
        self.present_nout_hash = None  # expected to be received from parent

        # possible_timelines is modelled as a global variable;
        # * reads can be done straight from the variable
        # * writes are expected to channeled, by passing Possibility up the parent-chain
        self.possible_timelines = possible_timelines

    def receive_from_parent(self, data):
        # there is no else branch: Possibility only travels up
        if isinstance(data, Actuality):
            # LATER: now that TreeNode has nouth_hash in its metadata, we can get rid of self.present_nout_hash in favor
            # of simply self.present_nout_hash.metadata.nout_hash
            self.present_nout_hash = data.nout_hash
            self._present_nout_updated()

    def receive_from_child(self, data):
        if isinstance(data, Possibility):
            self._send_to_parent(data)
        else:  # Actuality
            # Not sure: too much Possibility objects being sent up (I think so...) (TODO): check in practice
            self.set_present_nout(NoutBlock(Replace(self.child_s_address, data.nout_hash), self.present_nout_hash))

    def main_keyboard_loop(self):
        keep_going = True
        while keep_going:
            self.print_stuff_on_screen()

            choice = getch()
            keep_going = self.on_keyboard_choice(choice)

    def send_possibility_up(self, nout):
        # Note: the're some duplication here of logic that's also elsewhere, e.g. the calculation of the hash was
        # copy/pasted from the HashStore implementation; but we need it here again.

        bytes_ = nout.as_bytes()
        hash_ = Hash.for_bytes(bytes_)
        self._send_to_parent(Possibility(nout))
        return hash_

    def send_actuality_up(self, nout_hash):
        self._send_to_parent(Actuality(nout_hash))

    def set_present_nout(self, nout):
        """Call only_from inside_ ! don't call this in response to parent updates, because this moves data in the
        direction of the parent!"""
        present_nout_hash = self.send_possibility_up(nout)
        self.present_nout_hash = present_nout_hash
        if self.autosave:
            self.send_actuality_up(present_nout_hash)
        self._present_nout_updated()

    def _present_nout_updated(self):
        """invalidation of any local caches that may depend on present_nout; must be called in response to _any_
        update"""
        self.present_tree = construct_x(
            {}, self.possible_timelines, self.present_nout_hash)

    def on_keyboard_choice(self, choice):
        if choice not in ['x', 'w', 'W', 'e', 'd', 'i', 'a', 's', '>', '<', '+', '-']:
            return True

        if choice == '+':
            self.autosave = True

        if choice == '-':
            self.autosave = False

        if choice in 'xwW':
            if choice == 'x':  # Exit w/out saving
                return False
            if choice == 'w':  # write and continue
                self.send_actuality_up(self.present_nout_hash)
            if choice == 'W':  # Save & exit
                self.send_actuality_up(self.present_nout_hash)
                return False

        if choice == 'a':  # append node
            begin = self.send_possibility_up(NoutBegin())
            to_be_inserted = self.send_possibility_up(NoutBlock(BecomeNode(), begin))
            self.set_present_nout(
                NoutBlock(Insert(len(self.present_tree.children), to_be_inserted), self.present_nout_hash))

        if choice == 's':  # append text
            text = input(">>> ")
            begin = self.send_possibility_up(NoutBegin())
            to_be_inserted = self.send_possibility_up(NoutBlock(TextBecome(text), begin))
            self.set_present_nout(
                NoutBlock(Insert(len(self.present_tree.children), to_be_inserted), self.present_nout_hash))

        if choice == '>':  # surround yourself with a new node
            begin = self.send_possibility_up(NoutBegin())
            wrapping_nout = self.send_possibility_up(NoutBlock(BecomeNode(), begin))
            self.self.present_nout(NoutBlock(Insert(0, self.present_nout_hash), wrapping_nout))

        # Note (TODO): edit & delete presume an existing node; insertion can happen at the end too.
        # i.e. check indexes
        if choice in 'edi<':
            index = int(input("Index>>> "))

        if choice == '<':  # remove a node; make it's contents available as _your_ children
            to_be_removed = self.present_tree.children[index]
            for i, child in enumerate(to_be_removed.children):
                self.set_present_nout(
                    NoutBlock(Insert(index + i + 1, child.metadata.nout_hash), self.present_nout_hash))

            self.set_present_nout(NoutBlock(Delete(index), self.present_nout_hash))

        if choice in 'e':
            # Where do we distinguish the type? perhaps actually here, based on what we see.
            subject = self.present_tree.children[index]

            if isinstance(subject, TreeNode):
                self.child_s_address = index
                current_child_nout_hash = self.present_tree.children[index].metadata.nout_hash

                self.child_comms = Channel()
                send_to_child = self.child_comms.connect(self.receive_from_child)
                self.child = CLI(self.child_comms, self.possible_timelines, self.autosave)
                send_to_child(Actuality(current_child_nout_hash))
                self.child.main_keyboard_loop()

            else:
                print(subject.unicode_)
                print('=' * 80)
                text = input(">>> ")

                # In the most basic version of the editor, we have not thought extensively about the Clef for Text
                # nodes, having only TextBecome; even in that scenario we can choose between "every text edit spawns a
                # history from the beginning of time" and "every text edit is adds a piece of history". We chose the
                # first, but the second is probably better.
                begin = self.send_possibility_up(NoutBegin())
                text_nout = self.send_possibility_up(NoutBlock(TextBecome(text), begin))
                self.set_present_nout(NoutBlock(Replace(index, text_nout), self.present_nout_hash))

        if choice == 'i':
            type_choice = None
            while type_choice not in ['n', 't']:
                print("Choose type (n/t)")
                type_choice = getch()

            if type_choice == 't':
                text = input(">>> ")
                begin = self.send_possibility_up(NoutBegin())
                to_be_inserted = self.send_possibility_up(NoutBlock(TextBecome(text), begin))

            else:  # type_choice == 'n'
                begin = self.send_possibility_up(NoutBegin())
                to_be_inserted = self.send_possibility_up(NoutBlock(BecomeNode(), begin))

            self.set_present_nout(NoutBlock(Insert(index, to_be_inserted), self.present_nout_hash))

        if choice == 'd':
            self.set_present_nout(NoutBlock(Delete(index), self.present_nout_hash))

        return True

    def print_stuff_on_screen(self):
        # print("AUTOSAVE", self.autosave)
        # print('=' * 80)

        # print("HISTORY")
        # print(print_nouts_2(possible_timelines, self.present_nout_hash, 0, set()))
        # print('=' * 80)

        print(self.present_tree.pp_todo_numbered(0))
        print('=' * 80)


def edit(filename):
    channel = Channel()

    possible_timelines = RealmOfThePossible(channel).possible_timelines
    cli = CLI(channel, possible_timelines, False)

    if isfile(filename):
        read_from_file(filename, channel)
        FileWriter(channel, filename)
    else:
        # FileWriter first to ensure that the initialization becomes part of the file.
        FileWriter(channel, filename)
        initialize_history(channel)

    cli.main_keyboard_loop()


# The abilitiy to read a single character
# http://stackoverflow.com/a/21659588/339144
def _find_getch():
    try:
        import termios
    except ImportError:
        # Non-POSIX. Return msvcrt's (Windows') getch.
        import msvcrt
        return msvcrt.getch

    # POSIX system. Create and return a getch that manipulates the tty.
    import sys
    import tty

    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return _getch

getch = _find_getch()
