# coding=utf-8

from legato import NoutBegin


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
    def short_repr_nout(nout):
        if hasattr(nout, 'note'):
            return repr(nout.note)
        return "BEGIN"

    # Shows how the Nouts ref recursively
    if present_nout_hash.as_bytes() in seen:
        return (indentation * " ") + ":..."

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

    return result + (indentation * " ") + short_repr_nout(present_nout) + horizontal_recursion
