"""Pure's verified 12x12, 1bpp, interleaved-pair 18-byte glyph format.

This is a game format, not a claim that every NGP game uses it.
Bitmap bit 143 is the top-left pixel; bit 0 is the bottom-right pixel.
"""

def unpack(raw: bytes) -> int:
    if len(raw) != 18:
        raise ValueError("A Pure glyph must contain exactly 18 bytes")
    nibbles = []
    for value in raw:
        nibbles.extend([
            sum(((value >> (7 - 2*i)) & 1) << (3-i) for i in range(4)),
            sum(((value >> (6 - 2*i)) & 1) << (3-i) for i in range(4)),
        ])
    return sum(nibbles[i] << (140 - i*4) for i in range(36))


def pack(bits: int) -> bytes:
    if not isinstance(bits, int) or not 0 <= bits < (1 << 144):
        raise ValueError("Expected a nonnegative 144-bit bitmap")
    n = [(bits >> (140 - i*4)) & 15 for i in range(36)]
    return bytes(sum(((a >> (3-i)) & 1) << (7 - 2*i)
                     | ((b >> (3-i)) & 1) << (6 - 2*i)
                     for i in range(4)) for a, b in zip(n[::2], n[1::2]))
