# coding=utf-8
from os.path import isfile

from datastructure import (
    BecomeNode,
    Delete,
    Insert,
    NoutBegin,
    NoutBlock,
    parse_nout,
    play,
    Replace,
    TextBecome,
    TreeNode,
)

from posacts import (
    Actuality,
    Possibility,
    parse_pos_acts,
)
from hashstore import (
    HashStore,
)


def edit_text(possible_timelines, text_node):
    print(text_node.unicode_)
    print('=' * 80)
    text = input(">>> ")

    # In the most basic version of the editor text has no history, which is why the editing of text spawns a new
    # (extremely brief) history
    # THE ABOVE IS A LIE
    # we could just as well choose to have history (just a history of full replaces) at the level of the text nodes
    # I have chosen against it for now, but we can always do it
    begin = possible_timelines.add(NoutBegin())
    return possible_timelines.add(NoutBlock(TextBecome(text), begin))


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


def edit_node(possible_timelines, present_nout, autosave):
    while True:
        present_tree = play(possible_timelines, possible_timelines.get(present_nout))
        print("AUTOSAVE", autosave)
        print('=' * 80)

        print("HISTORY")
        print(print_nouts_2(possible_timelines, present_nout, 0, set()))
        print('=' * 80)

        print(present_tree.pp_todo_numbered(0))
        print('=' * 80)

        choice = None
        while choice not in ['x', 'w', 'W', 'e', 'd', 'i', 'a', 's', '>', '<', '+', '-']:
            # DONE:
            # print "[E]dit"
            # print "[D]elete"
            # print "[I]nsert"
            # print "e[X]it without saving"
            # print "Exit and save (W)"

            # UNDO?
            # Save w/o exit?
            # Reload? (i.e. full undo?)

            # Simply "Add"
            # Create wrapping node
            # Collapse to index

            choice = getch()

        if choice == '+':
            autosave = True

        if choice == '-':
            autosave = False

        if choice in 'xwW':
            if choice == 'x':  # Exit w/out saving
                raise StopIteration
            if choice == 'w':  # write and continue
                yield present_nout
            if choice == 'W':
                yield present_nout
                raise StopIteration

        if choice == 'a':  # append node
            begin = possible_timelines.add(NoutBegin())
            inserted_nout = possible_timelines.add(NoutBlock(BecomeNode(), begin))
            present_nout = possible_timelines.add(
                NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))
            if autosave:
                yield present_nout

        if choice == 's':  # append text
            text = input(">>> ")
            begin = possible_timelines.add(NoutBegin())
            inserted_nout = possible_timelines.add(NoutBlock(TextBecome(text), begin))
            present_nout = possible_timelines.add(
                NoutBlock(Insert(len(present_tree.children), inserted_nout), present_nout))
            if autosave:
                yield present_nout

        if choice == '>':  # surround yourself with a new node
            begin = possible_timelines.add(NoutBegin())
            wrapping_nout = possible_timelines.add(NoutBlock(BecomeNode(), begin))
            present_nout = possible_timelines.add(NoutBlock(Insert(0, present_nout), wrapping_nout))
            if autosave:
                yield present_nout

        # Note (TODO): edit & delete presume an existing node; insertion can happen at the end too.
        # i.e. check indexes
        if choice in 'edi<':
            index = int(input("Index>>> "))

        if choice == '<':  # remove a node; make it's contents available as _your_ children
            to_be_removed = present_tree.children[index]
            for i, (child, child_history) in enumerate(zip(to_be_removed.children, to_be_removed.histories)):
                present_nout = possible_timelines.add(NoutBlock(Insert(index + i + 1, child_history), present_nout))

            present_nout = possible_timelines.add(NoutBlock(Delete(index), present_nout))
            if autosave:
                yield present_nout

        if choice in 'e':
            # Where do we distinguish the type? perhaps actually here, based on what we see.
            subject = present_tree.children[index]

            if isinstance(subject, TreeNode):
                old_nout = present_tree.histories[index]
                for new_nout in edit_node(possible_timelines, old_nout, autosave=autosave):
                    present_nout = possible_timelines.add(NoutBlock(Replace(index, new_nout), present_nout))
                    if autosave:
                        yield present_nout

            else:
                present_nout = possible_timelines.add(
                    NoutBlock(Replace(index, edit_text(possible_timelines, subject)), present_nout))
                if autosave:
                    yield present_nout

        if choice == 'i':
            type_choice = None
            while type_choice not in ['n', 't']:
                print("Choose type (n/t)")
                type_choice = getch()

            if type_choice == 't':
                text = input(">>> ")
                begin = possible_timelines.add(NoutBegin())
                inserted_nout = possible_timelines.add(NoutBlock(TextBecome(text), begin))

            else:  # type_choice == 'n'
                begin = possible_timelines.add(NoutBegin())
                inserted_nout = possible_timelines.add(NoutBlock(BecomeNode(), begin))

            present_nout = possible_timelines.add(NoutBlock(Insert(index, inserted_nout), present_nout))
            if autosave:
                yield present_nout

        if choice == 'd':
            present_nout = possible_timelines.add(NoutBlock(Delete(index), present_nout))
            if autosave:
                yield present_nout


def edit(filename):
    possible_timelines = HashStore(parse_nout)

    def set_current(f, nout):
        f.write(Actuality(nout).as_bytes())

    if isfile(filename):
        byte_stream = iter(open(filename, 'rb').read())
        for pos_act in parse_pos_acts(byte_stream):
            if isinstance(pos_act, Possibility):
                possible_timelines.add(pos_act.nout)
            else:  # Actuality
                # this can be depended on to happen at least once ... if the file is correct
                present_nout = pos_act.nout_hash

    else:
        with open(filename, 'wb') as initialize_f:
            possible_timelines.write_to = initialize_f

            begin = possible_timelines.add(NoutBegin())
            present_nout = possible_timelines.add(NoutBlock(BecomeNode(), begin))

            set_current(initialize_f, present_nout)  # write the 'new file

    with open(filename, 'ab') as f:
        possible_timelines.write_to = f
        for new_nout in edit_node(possible_timelines, present_nout, False):
            set_current(f, new_nout)


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
