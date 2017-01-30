from collections import namedtuple
from binascii import unhexlify
from utils import pmts

NoutAndHash = namedtuple('NoutAndHash', (
    'nout',
    'nout_hash'))


class HashStore(object):
    """A HashStore stores serializable objects, keyed by the Hash of that serialization."""

    def __init__(self, Hash, ObjClass):
        """"
        Hash & ObjClass are types that are used for dynamic type checks, and to reconstruct new objects from the
        serialization.
        """
        self.d = {}
        self.Hash = Hash
        self.ObjClass = ObjClass

    def __repr__(self):
        return "<HashStore of %s>" % type(self.Nout).__name__

    def add(self, serializable):
        pmts(serializable, self.ObjClass)

        bytes_ = serializable.as_bytes()
        hash_ = self.Hash._for_bytes(bytes_)

        # The fact that we store the bytes representation of the object, rather than the object itself isn't very
        # "Pythonic", I suppose. The reason I stuck with it is that it's a good fit for a design property I personally
        # like very much: "objects are not anything else than their layout in memory".

        # The ability to store as bytes is guaranteed by the interface of HashStore (it's implied by the fact that we
        # store serializable objects) so it does not impose new constraints on our design.
        self.d[hash_] = bytes_
        return hash_

    def get(self, hash_):
        if hash_ not in self.d:
            raise KeyError(repr(hash_))
        return self.ObjClass.from_stream(iter(self.d[hash_]))

    def guess(self, human_readable_hash):
        """.get() based on a hash formatted as a string. Debugging only! (naive implementation; abysmal performance)"""
        prefix = unhexlify(human_readable_hash)
        for k, v in list(self.d.items()):
            if k.startswith(prefix):
                return self.get(self.Hash(k))
        raise KeyError()


class NoutHashStore(HashStore):
    """HashStore to store Nouts."""

    def __init__(self, Hash, Nout, NoutCapo):
        super(NoutHashStore, self).__init__(Hash, Nout)
        self.NoutCapo = NoutCapo
        self.add(NoutCapo())

    def all_nhtups_for_nout_hash(self, nout_hash):
        while True:
            nout = self.get(nout_hash)
            if nout == self.NoutCapo():
                raise StopIteration()

            yield NoutAndHash(nout, nout_hash)
            nout_hash = nout.previous_hash

    def all_preceding_nout_hashes(self, nout_hash):
        return (t.nout_hash for t in self.all_nhtups_for_nout_hash(nout_hash))


class ReadOnlyHashStore(object):
    def __init__(self, delegate):
        self._delegate = delegate

    def __getattr__(self, attr_name):
        if attr_name in ['add']:
            raise AttributeError("Illegal operation on read-only store")
        return getattr(self._delegate, attr_name)
