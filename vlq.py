r"""
From wikipedia:
https://en.wikipedia.org/wiki/Variable-length_quantity

The encoding assumes an octet (an eight-bit byte) where the most significant bit (MSB), also commonly known as the sign
bit, is reserved to indicate whether another VLQ octet follows.

If the MSB is 0, then this is the last VLQ octet of the integer. If A is 1, then another VLQ octet follows.  B is a
7-bit number [0x00, 0x7F] and n is the position of the VLQ octet where B0 is the least significant. The VLQ octets are
arranged most significant first in a stream.


## Klaas' spin on this:

I've taken the opposite approach from the Wiki definition, putting the least significant byte first.

Implementation seems to be much more straightforward if the least significant bits are first.  Perhaps this is simply a
rehashing of the old war of little and big endianness.  In any case... this is perhaps simply my lazyness, I might
reconsider.

>>> interesting = [0, 1, 42, 127, 128, 128 * 128 - 1, 128 * 128, 1234567890]
>>> for i in interesting:
...     print("%12d: %s" % (i, to_vlq(i)))
...     assert from_vlq(iter(to_vlq(i))) == i
...
           0: b'\x00'
           1: b'\x01'
          42: b'*'
         127: b'\x7f'
         128: b'\x80\x01'
       16383: b'\xff\x7f'
       16384: b'\x80\x80\x01'
  1234567890: b'\xd2\x85\xd8\xcc\x04'
"""


def to_vlq(i):
    result = b''

    while True:
        result += bytes([(i % 128) + (128 if i >= 128 else 0)])
        i = i // 128
        if i == 0:
            return result


def from_vlq(bytes_stream):
    # bytes_stream is a bytes_stream of bytes, on which next(...) can be called which yields a byte
    result = 0
    base = 1

    while True:
        b = next(bytes_stream)

        result += (b % 128) * base
        base *= 128

        if b < 128:
            return result
