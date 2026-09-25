#!/usr/bin/env python3
"""Render the home screen icon (src/icon.png, 55x56): a knight on a green tile."""
import struct, sys, zlib, os
sys.path.insert(0, os.path.dirname(__file__))
import pieces

W, H, SS = 55, 56, 6
GREEN, BODY, INK = (0x81, 0xB6, 0x4C), (0xF9, 0xF9, 0xF7), (0x3A, 0x3A, 0x3A)
tile = pieces.box(0, 0, W, H, 10)
body, details, eye = pieces.knight()
scale, ox, oy = 1.6, 3.5, 3.5  # icon px -> piece space


def px(x, y):
    acc = [0, 0, 0]
    for sy in range(SS):
        for sx in range(SS):
            X, Y = x + (sx + 0.5) / SS, y + (sy + 0.5) / SS
            c = (255, 255, 255)
            if tile(X, Y) < 0:
                c = GREEN
                u, v = (X - ox) / scale + 0.8, (Y - oy) / scale
                d = body(u, v)
                if d < 0:
                    ink = d > -1.0 or eye(u, v) < 0 or any(g(u, v) < 0.5 for g in details)
                    c = INK if ink else BODY
            acc = [a + b for a, b in zip(acc, c)]
    return tuple(round(a / SS / SS) for a in acc)


raw = b''.join(b'\0' + bytes(v for x in range(W) for v in px(x, y)) for y in range(H))


def chunk(t, d):
    return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))


open('src/icon.png', 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) +
                                 chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
