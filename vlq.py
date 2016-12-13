"""
From wikipedia:
https://en.wikipedia.org/wiki/Variable-length_quantity

The encoding assumes an octet (an eight-bit byte) where the most significant bit (MSB), also commonly known as the sign bit, is reserved to indicate whether another VLQ octet follows.

If the MSB is 0, then this is the last VLQ octet of the integer. If A is 1, then another VLQ octet follows.
B is a 7-bit number [0x00, 0x7F] and n is the position of the VLQ octet where B0 is the least significant. The VLQ octets are arranged most significant first in a stream.


-- Klaas' spin on this:
Whyyyyy are the most significant bits first in the stream? Implementation seems to be much more straightforward if the least significant bits are first.
Perhaps this is simply a rehashing of the old war of little and big endianness.
In any case... this is perhaps simply my lazyness, I might reconsider.

"""


def to_vlq(i):
    result = b''

    while True:
        result += chr((i % 128) + (128 if i >= 128 else 0))
        i = i / 128
        if i == 0:
            return result


def from_vlq(stream):
    # stream is a stream of bytes, on which .next() can be called
    result = 0
    base = 1

    while True:
        b = ord(stream.next())

        result += (b % 128) * base
        base *= 128

        if b < 128:
            return result

"""
>>> import vlq
>>> for i in range(1234567):
...   if vlq.from_vlq(iter(vlq.to_vlq(i))) != i:
...     print i
"""
