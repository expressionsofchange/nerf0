"""
Vim-like interface for single-line editing.

This is not supposed to be have feature-parity with Vim; rather it's supposed to have just those features that I
personally have come to depend on.

For the interface/type of 'sent keys' we use `generalized_key_press`, i.e. "Kivy with some changes".

"""


MOVE_TO_CHAR_KEYS = ['f', 'F', 't', 'T']
MOTION_KEYS = MOVE_TO_CHAR_KEYS + ['h', 'l']


class vim(object):
    def __init__(self, text, cursor_pos):
        self.text = text
        self.cursor_pos = cursor_pos
        self.v = normal_mode_loop(text, cursor_pos)
        next(self.v)

    def send(self, key):
        result = self.v.send(key)

        # Debug-only: raise at the problematic point; once this stops happening, we can get rid of it:
        if result is None:
            self.v.throw(Exception("Please don't yield None"))

        self.text, self.cursor_pos = result


def normal_mode_loop(text, cursor_pos):
    while True:
        text, cursor_pos = yield from normal_mode(text, cursor_pos)


def normal_mode(text, cursor_pos):
    count = 1
    key = yield text, cursor_pos

    if key.isdigit():
        key, count = yield from numeral(key)

    if key in MOTION_KEYS:
        motion_result = yield from motion(text, cursor_pos, key, count)
        if motion_result is None:
            return text, cursor_pos

        cursor_pos, inclusive = motion_result
        return text, cursor_pos

    if key in ['i', 'a', 'I', 'A']:
        if key == 'a':
            # append (but don't but the cursor outside the text)
            cursor_pos = min(cursor_pos + 1, len(text))
        elif key == 'I':
            cursor_pos = 0
        elif key == 'A':
            cursor_pos = len(text)

        text, cursor_pos = yield from insert_mode(text, cursor_pos)
        return text, cursor_pos

    if key in ['d', 'c']:
        motion_key = yield text, cursor_pos

        motion_result = yield from motion(text, cursor_pos, motion_key, count)
        if motion_result is None:
            return text, cursor_pos

        delete_to_cursor_pos, delete_inclusive = motion_result

        # AFAIU, inclusive=True can be simply translated into ibeam-curosr +=1. (This is slightly surprising for the
        # deletions in leftward direction, because in that case "inclusive" means "don't delete", but it's per spec).
        # We just have to make sure to do this only for deletions, not regular movement.
        delete_to_cursor_pos += (1 if delete_inclusive else 0)

        text, cursor_pos = ibeam_delete(text, cursor_pos, delete_to_cursor_pos)

        if key == 'c':
            text, cursor_pos = yield from insert_mode(text, cursor_pos)

        return text, cursor_pos

    if key in ['x']:
        text, cursor_pos = ibeam_delete(text, cursor_pos, cursor_pos + 1)
        return text, cursor_pos

    return text, cursor_pos


def insert_mode(text, cursor_pos):
    key = yield text, cursor_pos

    while True:
        if key == 'escape':
            # the -1 here is simply reflective of how my reference implementation of Vim works (on exiting insert mode,
            # the cursor jumps to the left). Such a behavior makes sense if you see it as exiting append mode, and also
            # has the advantage of guaranteeing to put the cursor in-bounds for normal mode (there is 1 more
            # cursor-position available, at the end, in insert-mode). It has the disadvantage of being asymmetric for
            # 'i'/'escape'.
            return text, max(cursor_pos - 1, 0)

        if key == 'backspace':
            text, cursor_pos = ibeam_delete(text, cursor_pos, cursor_pos - 1)
            key = yield text, cursor_pos
            continue

        text = text[:cursor_pos] + key + text[cursor_pos:]
        cursor_pos += 1

        key = yield text, cursor_pos


def numeral(key):
    count = 0
    while key.isdigit():
        count *= 10
        count += int(key)
        key = yield
    return key, count


def motion(text, cursor_pos, key, count):
    # TODO Once we implement '0' to mean "beginning of line", we don't need this case anymore.
    if count == 0:
        return None

    if key == 'h':
        cursor_pos = max(cursor_pos - count, 0)
        return cursor_pos, False

    if key == 'l':
        # In normal mode there are as many positions as characters, hence `len(text) - 1`
        cursor_pos = min(cursor_pos + count, len(text) - 1)
        return cursor_pos, False

    if key in MOVE_TO_CHAR_KEYS:
        char = yield text, cursor_pos

        for i in range(count):
            result = ftFT(key, char, text, cursor_pos)
            if result is None:
                return result
            cursor_pos, inclusive = result

    return cursor_pos, inclusive


def ftFT(key, char, text, cursor_pos):
    """
    >>> s = 'some text as an example'
    >>> check = lambda *args: (ftFT(*args), s[ftFT(*args)[0]])

    From beginning to first 'a'
    >>> check('f', 'a', s, 0)
    ((10, True), 'a')

    From beginning to right before first 'a'
    >>> check('t', 'a', s, 0)
    ((9, True), ' ')

    From first 'a' to next 'a'
    >>> check('f', 'a', s, 10)
    ((13, True), 'a')

    Back to previous 'a'
    >>> check('F', 'a', s, 13)
    ((10, False), 'a')

    Back to right after previous 'a'
    >>> check('T', 'a', s, 13)
    ((11, False), 's')
    """
    find = text.find if key in ['f', 't'] else text.rfind  # forwards or backwards
    bounds = (cursor_pos + 1, len(text) - 1) if key in ['f', 't'] else (0, cursor_pos)  # first half or second half
    correction = {
        'f': 0,
        'F': 0,
        't': -1,  # 'till
        'T': 1,  # 'till after
    }[key]
    found = find(char, *bounds)

    # TBH, I personally think that the concept of inclusive/exclusive motions is a kludge; an equal amount of
    # expressiveness in a simpler interface can be achieved by simply have a cursor in between characters (i.e. ibeam
    # rather than block) and slightly different choices in the meaning of 'f' and 't' (i.e. to be able to
    # delete-including, 'f' needs to jump to right _after_ the character

    # However, I want the exact same behavior as Vim for this part to lower my own (and other peoples) switching costs,
    # so I'll just reimplement the kludge as well as I understand it)

    # Short example of why 'inclusive' motions are required is the behavior of 'f' and 'F': both of them jump _to_ the
    # indicated character; 'f' puts the ibeam-like cursor that's implicit in the deletion on the right of that
    # character, and 'F' puts it on the left.

    inclusive = key in ['f', 't']

    if found == -1:
        return None

    return found + correction, inclusive


def ibeam_delete(s, i0, i1):
    """
    Returns

    A] a string `s` with the bit between i0 and i1 deleted, treating both indices as 'ibeams', i.e. points in
    between characters, like so:

     0 1 2 3 4 5 6    | string indices
    |a|b|c|d|e|f|g|
    ^ ^ ^ ^ ^ ^ ^ ^
    0 1 2 3 4 5 6 7   | ibeam cursors

    B] The single index i´ representing an ibeam sitting in the now-deleted part.

    Single ibeam represents a no-op:
    >>> ibeam_delete('abcdefg', 5, 5)
    ('abcdefg', 5)

    >>> ibeam_delete('abcdefg', 0, 3)
    ('defg', 0)

    >>> ibeam_delete('abcdefg', 1, 3)
    ('adefg', 1)

    >>> ibeam_delete('abcdefg', 1, 7)
    ('a', 1)

    Order of the cursors does not matter:
    >>> ibeam_delete('abcdefg', 7, 1)
    ('a', 1)

    Bounds are checked (allows for lazy usage of this function; arguably we should raise an error instead)
    >>> ibeam_delete('abcdefg', -1, 99)
    ('', 0)
    """
    lo, hi = tuple(sorted([i0, i1]))
    lo = max(0, lo)
    hi = min(len(s), hi)

    # We need to copy right up to the lo ibeam; right up to the ibeam 'n' means up to and including string-index n-1.
    # Because python slice-notation's RHS excludes its index, this is written as s[0:lo]

    # We need to copy from right after the hi ibeam; right after the ibeam 'n' means from string-index n onwards.
    # Because python slice-notation's LHS includes its index, this is written as s[hi:]

    s = s[0:lo] + s[hi:]
    return s, lo
