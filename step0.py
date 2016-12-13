from hashlib import sha256
from vlq import to_vlq

# Type constructor codes
TREE_NODE = b'\x00'
TREE_TEXT = b'\x01'

NOUT_BEGIN = b'\x00'
NOUT_BLOCK = b'\x01'

NOTE_INSERT = b'\x00'
NOTE_DELETE = b'\x01'
NOTE_REPLACE = b'\x02'
# NOTE_COMBINE = b'\x03'

NOTE_TEXT_CREATE = b'\x03'


# Question: do I need to think so much yet of the binary encoding of the tree-structure?
def TreeNode(children):
    # children :: ???
    return TREE_NODE + b''.join(children)  # WE NEED LENGTH-ENCODING HERE (or cons/nill pairs)


def TreeText(text):
    # text :: bytes (utf8 encoded text)  ??? or use unicode here !
    # :: bytes
    return TREE_TEXT + text


# ## Binary encoding of nouts
def NoutBegin():
    # :: bytes
    return NOUT_BEGIN


def NoutBlock(payload, previous_hash):
    # payload :: bytes (any payload)
    # parent_hash :: bytes (hash of the parent)
    # :: bytes
    return NOUT_BLOCK + payload + previous_hash


# ##  Vocabulary of change  (AKA "Key")

# Potentially: explicitly reflect in the naming of Node-related nodes that they are just that.
# (As opposed to Text-related ones)

def Insert(index, nout_hash):
    # index :: VLQ (index to be inserted at in the list of children;
    # nout_hash: NoutHash of the history to be inserted
    return NOTE_INSERT + index + nout_hash


def Delete(index):
    # index :: VLQ (index to be deleted)
    return NOTE_DELETE + index


def Replace(index, nout_hash):
    # index :: VLQ (index to be inserted at in the list of children;
    # nout_hash: NoutHash of the history to be inserted
    return NOTE_REPLACE + index + nout_hash


# Text-related notes: I'm starting with just one
def TextCreate(utf8_encoded_unicode):
    return NOTE_TEXT_CREATE + utf8_encoded_unicode


# Here is some example usage:

def h(b):
    # :: bytes -> hash
    return sha256(b).digest()

that_happened = {}


def play(nout):
    hashed = h(nout)
    that_happened[hashed] = nout
    return hashed

hash_0 = play(NoutBegin())

hash_1 = play(Insert(to_vlq(0), hash_0))
hash_2 = play(Replace(to_vlq(0), hash_1))

# Next things to think about:
# serialize / unserialize functions (classes even?): where do they go?
# Similarly: pretty printing

# that_happend v.s. _a particular history_
# Stack-like behavior that exploits that difference

# Actually applying the changes on some structure :-D
