#!/usr/bin/env python3
"""Rasterize the chess piece set into compact sprites (src/sprites.h).

Pieces are described as signed distance fields and rendered with 8x8
supersampling into a 30x30 cell. Each pixel is quantized to one of eight
classes (3 bits):
  0 transparent   1 body          2 outline        3 outline 60% over background
  4 outline 30%   5 inner detail  6 outline/body   7 detail/body
Symmetric pieces only store their left half.

  python3 tools/pieces.py            # writes src/sprites.h
  python3 tools/pieces.py prev.png   # also writes a zoomed preview (docs/pieces.png)
"""
import math, struct, sys, zlib

N = 30          # cell size
SS = 8          # supersampling per axis
OUTLINE = 1.2  # outline width in pixels
DETAIL = 0.55   # half width of inner detail strokes


def length(x, y):
    return math.sqrt(x * x + y * y)


def circle(cx, cy, r):
    return lambda x, y: length(x - cx, y - cy) - r


def ellipse(cx, cy, rx, ry):
    m = min(rx, ry)
    return lambda x, y: (length((x - cx) / rx, (y - cy) / ry) - 1) * m


def box(x0, y0, x1, y1, r=0.0):
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2, (y1 - y0) / 2

    def f(x, y):
        qx, qy = abs(x - cx) - hx + r, abs(y - cy) - hy + r
        return length(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
    return f


def poly(pts):
    def f(x, y):
        d = 1e9
        s = 1
        n = len(pts)
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[i - 1]
            ex, ey = bx - ax, by - ay
            wx, wy = x - ax, y - ay
            t = max(0, min(1, (wx * ex + wy * ey) / (ex * ex + ey * ey)))
            d = min(d, length(wx - ex * t, wy - ey * t))
            c1, c2, c3 = y >= ay, y < by, ex * wy > ey * wx
            if (c1 and c2 and c3) or (not c1 and not c2 and not c3):
                s = -s
        return s * d
    return f


def seg(ax, ay, bx, by):
    def f(x, y):
        ex, ey, wx, wy = bx - ax, by - ay, x - ax, y - ay
        t = max(0, min(1, (wx * ex + wy * ey) / (ex * ex + ey * ey)))
        return length(wx - ex * t, wy - ey * t)
    return f


def union(*fs):
    return lambda x, y: min(f(x, y) for f in fs)


def smooth_union(k, *fs):
    def f(x, y):
        d = fs[0](x, y)
        for g in fs[1:]:
            e = g(x, y)
            h = max(0, min(1, 0.5 + 0.5 * (e - d) / k))
            d = e * (1 - h) + d * h - k * h * (1 - h)
        return d
    return f


def sub(a, b):
    return lambda x, y: max(a(x, y), -b(x, y))


def mirror(pts):
    """Close a left-half outline (top to bottom) into a symmetric polygon."""
    return pts + [(N - x, y) for x, y in reversed(pts)]


# ---------------------------------------------------------------- pieces
def pawn():
    body = smooth_union(1.2,
        circle(15, 8.9, 4.7),
        poly(mirror([(12.4, 13.2), (10.6, 16.2), (11.9, 16.6), (9.4, 22.8)])),
        box(7.0, 22.2, 23.0, 26.8, 1.6))
    return body, []


def rook():
    top = sub(box(8.2, 3.6, 21.8, 9.6, 0.6),
              union(box(11.4, 2, 13.4, 6.4), box(16.6, 2, 18.6, 6.4)))
    body = union(top,
                 poly(mirror([(10.2, 9), (10.6, 20.5)])),
                 box(8.6, 19.8, 21.4, 23.2, 0.6),
                 box(6.8, 22.6, 23.2, 26.8, 1.2))
    details = [seg(9.5, 9.6, 20.5, 9.6), seg(9.8, 20.2, 20.2, 20.2), seg(8, 23.2, 22, 23.2)]
    return body, details


def bishop():
    mitre = smooth_union(0.8,
        ellipse(15, 14.2, 5.9, 6.9),
        poly([(15, 6.0), (19.9, 12), (10.1, 12)]))
    body = union(
        circle(15, 4.6, 2.2),
        mitre,
        box(10.4, 19.6, 19.6, 22.6, 0.8),
        poly(mirror([(9.5, 22), (7.4, 26.8)])),
        box(7, 23.5, 23, 26.8, 1.2))
    details = [seg(16.6, 10.6, 14.2, 14.4), seg(11.4, 19.7, 18.6, 19.7), seg(9.6, 22.8, 20.4, 22.8)]
    return body, details


def queen():
    tips = [(5.6, 9.0), (10.2, 6.6), (15, 5.6), (19.8, 6.6), (24.4, 9.0)]
    crown = poly([(8.4, 22.6), (5.4, 10.6), (10.6, 15.0), (10.0, 8.2), (13.9, 14.2), (15, 7.2),
                  (16.1, 14.2), (20.0, 8.2), (19.4, 15.0), (24.6, 10.6), (21.6, 22.6)])
    body = union(crown, *[circle(x, y, 2.0) for x, y in tips],
                 box(8.0, 20.0, 22.0, 23.4, 0.8),
                 box(7, 23, 23, 26.8, 1.2))
    details = [seg(9.0, 20.2, 21.0, 20.2), seg(8.6, 23.3, 21.4, 23.3)]
    return body, details


def king():
    lobes = smooth_union(1.4,
        circle(10.6, 14.6, 4.6),
        circle(19.4, 14.6, 4.6),
        ellipse(15, 13.6, 3.2, 4.2),
        poly(mirror([(7.2, 15.5), (9.4, 22.6)])))
    cross = union(box(14, 2.4, 16, 10.2, 0.4), box(11.8, 4.2, 18.2, 6.2, 0.4))
    body = union(lobes, cross,
                 box(8.4, 20.4, 21.6, 23.4, 0.8),
                 box(7, 23, 23, 26.8, 1.2))
    details = [seg(15, 10.4, 15, 17.5), seg(9.4, 20.4, 20.6, 20.4), seg(8.6, 23.3, 21.4, 23.3)]
    return body, details


def knight():
    head = poly([
        (22.2, 23.2), (22.6, 18.5), (22.2, 13.8), (20.8, 9.8), (18.4, 6.6), (15.8, 5.2),
        (15.2, 2.8), (13.4, 4.8), (11.8, 3.6), (11.4, 6.4), (8.6, 9.6), (6.2, 13.6),
        (5.8, 15.6), (7.2, 17.0), (9.4, 16.2), (11.2, 15.2), (13.6, 14.2),
        (13.4, 16.4), (10.6, 19.6), (9.6, 23.2)])
    body = smooth_union(0.8, head, box(7, 22.6, 23.2, 26.8, 1.2))
    details = [seg(8.8, 23.2, 21.6, 23.2), seg(7.4, 14.4, 8.4, 13.8)]
    eye = circle(12.2, 9.2, 1.0)
    return body, details, eye


def render(shape):
    body, details = shape[0], shape[1]
    eye = shape[2] if len(shape) > 2 else None
    cls = []
    for py in range(N):
        row = []
        for px in range(N):
            inside = ink = det = 0
            for sy in range(SS):
                for sx in range(SS):
                    x = px + (sx + 0.5) / SS
                    y = py + (sy + 0.5) / SS
                    d = body(x, y)
                    if d < 0:
                        inside += 1
                        if d > -OUTLINE:
                            ink += 1
                        elif any(g(x, y) < DETAIL for g in details) or (eye and eye(x, y) < 0):
                            det += 1
            a = inside / (SS * SS)
            if a < 0.2:
                c = 0
            elif a < 0.5:
                c = 4
            elif a < 0.85:
                c = 3
            else:
                fi, fd = ink / inside, det / inside
                c = 2 if fi > 0.65 else 6 if fi > 0.3 else 5 if fd > 0.55 else 7 if fd > 0.2 else 1
            row.append(c)
        cls.append(row)
    return cls


PIECES = [('pawn', pawn), ('knight', knight), ('bishop', bishop),
          ('rook', rook), ('queen', queen), ('king', king)]


def bounds(img):
    ys = [y for y in range(N) if any(img[y])]
    xs = [x for x in range(N) if any(img[y][x] for y in range(N))]
    return min(xs), min(ys), max(xs), max(ys)


def symmetric(img):
    return all(img[y][x] == img[y][N - 1 - x] for y in range(N) for x in range(N))


def main():
    imgs = [(name, render(f())) for name, f in PIECES]
    out, bits, meta, off = [], [], [], 0
    for name, img in imgs:
        x0, y0, x1, y1 = bounds(img)
        sym = symmetric(img)
        if sym:
            x0 = min(x0, N - 1 - x1)
            w = N // 2 - x0
        else:
            w = x1 - x0 + 1
        h = y1 - y0 + 1
        px = [img[y][x] for y in range(y0, y1 + 1) for x in range(x0, x0 + w)]
        bits.extend(px)
        meta.append((off, x0, y0, w, h, sym))
        off += len(px)
    for i in range(0, len(bits), 8):
        v = 0
        for j, c in enumerate(bits[i:i + 8]):
            v |= c << (3 * j)
        out += [v & 255, (v >> 8) & 255, v >> 16]
    out.append(0)  # padding: the decoder reads two bytes at a time
    with open('src/sprites.h', 'w') as f:
        f.write('/* Generated by tools/pieces.py: 3 bits per pixel, 8 pixels per 3 bytes. */\n')
        f.write('static const struct { uint16_t off; uint8_t x, y, w, h; } SPR[6] = {\n')
        for off, x0, y0, w, h, sym in meta:
            f.write('  {%d, %d, %d, %d, %d},\n' % (off, x0, y0, w | (0x80 if sym else 0), h))
        f.write('};\nstatic const uint8_t SPRD[%d] = {\n' % len(out))
        for i in range(0, len(out), 20):
            f.write('  ' + ','.join(str(v) for v in out[i:i + 20]) + ',\n')
        f.write('};\n')
    print('sprite bytes:', len(out), file=sys.stderr)
    if len(sys.argv) > 1:
        preview(imgs, sys.argv[1])


def shade(c, bg, color):
    ink = (0x3A, 0x3A, 0x3A) if color == 0 else (0x14, 0x13, 0x12)
    body = (0xF8, 0xF8, 0xF6) if color == 0 else (0x52, 0x4F, 0x4D)
    det = ink if color == 0 else (0xA8, 0xA5, 0xA2)
    mix = lambda a, b, t: tuple(round(x * (1 - t) + y * t) for x, y in zip(a, b))
    return [bg, body, ink, mix(bg, ink, 0.6), mix(bg, ink, 0.3), det, mix(body, ink, 0.5), mix(body, det, 0.5)][c]


def preview(imgs, path, Z=4):
    """Both colors of the set on board squares, zoomed Z times."""
    light, dark = (0xEB, 0xEC, 0xD0), (0x77, 0x95, 0x56)
    W, Hh = 6 * N * Z, 2 * N * Z
    pix = [[None] * W for _ in range(Hh)]
    for color in range(2):
        for i, (name, img) in enumerate(imgs):
            bg = light if (i + color) % 2 == 0 else dark
            for y in range(N * Z):
                for x in range(N * Z):
                    pix[color * N * Z + y][i * N * Z + x] = shade(img[y // Z][x // Z], bg, color)
    raw = b''.join(b'\0' + bytes(v for p in row for v in p) for row in pix)

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, Hh, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b'')
    open(path, 'wb').write(png)


if __name__ == '__main__':
    main()
