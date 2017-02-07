"""
Vim-like interface for single-line editing.

This is not supposed to be have feature-parity with Vim; rather it's supposed to have just those features that I
personally have come to depend on.

# Python Generators

The below is implemented using Python generators/coroutines.

Some hints as to how this works:

`yield from` may be used to decompose generators; The passed parameters and returned value may be of any type that's
useful to you in the process of decomposition. This may contain `(text, cursor_pos)` info, but only if useful.

`yield` forms a direct interface between "the I/O" (screen, keyboard) and the yielding location. The yielding location
knows the latest state to be _output_ and communicates this; it yields control waiting for new _inputs_.

This is independent of choices made in the decomposition of the functions. From the perspective of the "yielding
location" this interface looks like this:

* You must always yield the current state `(text, cursor_pos)`.
* a `key` will be sent to you once control returns. (For the interface/type of 'sent keys' we use
    `generalized_key_press`, i.e. "Kivy with some changes".)


Are generators the right abstraction here? I think so: they allow for a linear-style of writing "I will wait until a new
keypress", without resorting to multi-threading.  A single-thread rewrite without generators would need extensive
callbacks, which hinders understanding. Of course, you do need to understand generators to be able to understand the
current version.
"""


MOVE_TO_CHAR_KEYS = ['f', 'F', 't', 'T']
MOTION_KEYS = MOVE_TO_CHAR_KEYS + ['h', 'l']


class Vim(object):
    """
    >>> vim = Vim('some text to edit', 0)
    >>> vim.send('2')
    >>> vim.send('d')
    >>> vim.send('f')
    >>> vim.send('e')
    >>> vim.text
    'xt to edit'
    """

    def __init__(self, text, cursor_pos):
        self.v = normal_mode_loop(text, cursor_pos)
        self.send(None)

    def send(self, key):
        self.text, self.cursor_pos = self.v.send(key)


def normal_mode_loop(text, cursor_pos):
    while True:
        text, cursor_pos = yield from normal_mode(text, cursor_pos)


def normal_mode(text, cursor_pos):
    """
    Performs 1 normal_mode action.

    The return type is: (text, cursor_pos). This is a necessary consequence of the requirement to chain operations: i.e.
    we need a value to pass into the next call.  It is _not_ a necessary consequence of the 'yield interface' (receive
    keyspresses by yielding the current state), despite being the same.
    """

    count = 1
    key = yield text, cursor_pos

    if key.isdigit():
        key, count = yield from numeral(text, cursor_pos, key)

    if key in MOTION_KEYS:
        motion_result = yield from motion(text, cursor_pos, key, count)
        if motion_result is None:
            return text, cursor_pos

        cursor_pos, inclusive_ = motion_result
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
        text, cursor_pos = ibeam_delete(text, cursor_pos, cursor_pos + count)
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


def numeral(text, cursor_pos, key):
    """Parses a 'count' value; returns that count and the first unusable key (to be consumed by some place that _does_
    know what to do with it).

    Note that we don't actually need the state (text, cursor_pos) to do such parsing, nor do we have anything new to say
    about that state. However, in our current `yield` interface we must _always_ yield the current state if we want to
    get a key; which means we need to know it. A simplification could be: codifying the fact that there is no output
    information as a possible yieldable value (and dealing with it on the receiving end). Because `numeral` is the only
    example of this, I have not yet done that.
    """

    count = 0
    while key.isdigit():
        count *= 10
        count += int(key)
        key = yield text, cursor_pos

    return key, count


def motion(text, cursor_pos, key, count):
    """
    >>> from test_utils import Generator
    >>>
    >>> text = 'some text as an example'

    h & l return immediately, no further info required
    >>> g = Generator(motion(text, 0, 'l', 5))
    ('R', (5, False))

    Findable text
    >>> g = Generator(motion(text, 0, 'f', 1))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', (3, True))

    nth occurence using 'count'
    >>> g = Generator(motion(text, 0, 'f', 2))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', (6, True))

    Unfindable text returns None
    >>> g = Generator(motion(text, 0, 'f', 1))
    ('Y', ('some text as an example', 0))
    >>> g.send('Q')
    ('R', None)

    Not enough occurrences returns None:
    >>> g = Generator(motion(text, 0, 'f', 5))
    ('Y', ('some text as an example', 0))
    >>> g.send('e')
    ('R', None)
    """

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
