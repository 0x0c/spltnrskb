"""Three-view drawings (third-angle projection, JIS) of the printed case parts: case/drawings/<name>.pdf.

make_case.write_stl calls draw() for every STL it writes into a print/ directory, so make_case.py, foot_coupon.py,
pin_coupon.py and make_enctest.py keep the drawings next to it (<dir>/drawings/) up to date; run this script by
hand to redraw without regenerating the STLs. A drawing is skipped when nothing it depends on changed: each PDF
records a hash of its STL, this script and the options (a "%source" comment), and a matching hash leaves it as is
(--force redraws anyway).

Each STL in case/print/ (or the STLs given on the command line) is drawn as a top view, a front view and a right
side view on an A3 sheet, at the largest standard scale that fits, with the overall dimensions and a title block.
Visible edges are solid lines and hidden edges dashed: the edges are the sharp edges of the mesh (faces meeting at
more than FEATURE_DEG) and the silhouettes, and a depth buffer of the projected triangles decides which parts of
them are seen. Needs numpy only.

Model axes as in make_case.py: x to the right, y to the back (away from the typist), z up. The parts are drawn as
they lie in the STL (stands in their print pose, the printed plate top side up).

    python3 gen/case_drawings.py                      # every STL in case/print/
    python3 gen/case_drawings.py case/print/left-tray.stl --no-hidden
"""
import argparse, glob, hashlib, math, os, re, sys, zlib
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'case', 'drawings')

FEATURE_DEG = 35.0            # faces meeting at a larger angle make a drawn edge (finer tessellation stays smooth)
STEP = 0.4                    # mm: an edge between two faces narrower than this is a step of a stacked-slice fillet
PX = 0.05                     # depth-buffer pixel, mm on the part
DEPTH_EPS = 0.05              # mm: an edge this close behind the nearest surface still counts as seen
SHEET = (420.0, 297.0)        # A3 landscape, mm
MARGIN = 10.0
GAP = 22.0                    # between views (room for the dimensions)
TITLE = (150.0, 32.0)         # title block, bottom right
SCALES = [(10, 1), (5, 1), (2, 1), (1, 1), (1, 2), (1, 5)]

# view name -> (u axis, v axis, viewing direction into the scene); u to the right, v up on the sheet
VIEWS = {
    'top': (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, -1.0])),
    'front': (np.array([1.0, 0, 0]), np.array([0, 0, 1.0]), np.array([0, 1.0, 0])),
    'right': (np.array([0, 1.0, 0]), np.array([0, 0, 1.0]), np.array([-1.0, 0, 0])),
}
LABELS = {'top': '平面図', 'front': '正面図', 'right': '右側面図'}


# --- mesh --------------------------------------------------------------------------
def read_stl(path):
    b = open(path, 'rb').read()
    if b[:5] == b'solid' and b'facet' in b[:400]:          # ASCII STL
        v = [list(map(float, ln.split()[1:4])) for ln in b.decode().splitlines() if ln.strip().startswith('vertex')]
        return np.array(v, dtype=np.float64).reshape(-1, 3, 3)
    n = int.from_bytes(b[80:84], 'little')
    rec = np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')])
    return np.frombuffer(b, dtype=rec, count=n, offset=84)['v'].astype(np.float64).reshape(-1, 3, 3)


def edges_of(tris):
    """Welded mesh -> vertices, (edges, normals of their two faces, step flag) of the manifold edges, other edges.
    The step flag marks an edge whose two faces are both narrow across it (a step of the fillets make_case.py builds
    from stacked slices): drawing those would turn a fillet into a black band, so the fillet shows by its two ends."""
    q = np.round(tris.reshape(-1, 3) / 1e-4).astype(np.int64)
    _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
    verts = tris.reshape(-1, 3)[first]
    f = inv.reshape(-1, 3)
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(nrm, axis=1)
    ok = ln > 1e-12
    f, nrm, ln = f[ok], nrm[ok] / ln[ok, None], ln[ok]
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    fi = np.tile(np.arange(len(f)), 3)
    width = ln[fi] / np.maximum(np.linalg.norm(verts[e[:, 0]] - verts[e[:, 1]], axis=1), 1e-12)   # face height over the edge
    e.sort(axis=1)
    live = e[:, 0] != e[:, 1]       # faces collapsed by the welding
    e, fi, width = e[live], fi[live], width[live]
    key = e[:, 0] * (len(verts) + 1) + e[:, 1]
    order = np.argsort(key, kind='stable')
    key, e, fi, width = key[order], e[order], fi[order], width[order]
    uniq, start, count = np.unique(key, return_index=True, return_counts=True)
    two = count == 2
    s0, s1 = start[two], start[two] + 1
    pairs = e[s0], nrm[fi[s0]], nrm[fi[s1]], (width[s0] < STEP) & (width[s1] < STEP)
    other = e[start[~two]]
    return verts, pairs, other


# --- projection --------------------------------------------------------------------
def zbuffer(p, box):
    """Nearest depth per pixel of the projected triangles p (n, 3, 3: u, v, depth); inf where nothing is."""
    u0, v0, w, h = box
    z = np.full(w * h, np.inf)
    a, b, c = p[:, 0], p[:, 1], p[:, 2]
    area = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    keep = np.abs(area) > 1e-9
    p, a, b, c, area = p[keep], a[keep], b[keep], c[keep], area[keep]
    # depth plane of each triangle: depth = gu * u + gv * v + g0
    gu = ((b[:, 2] - a[:, 2]) * (c[:, 1] - a[:, 1]) - (c[:, 2] - a[:, 2]) * (b[:, 1] - a[:, 1])) / area
    gv = ((c[:, 2] - a[:, 2]) * (b[:, 0] - a[:, 0]) - (b[:, 2] - a[:, 2]) * (c[:, 0] - a[:, 0])) / area
    g0 = a[:, 2] - gu * a[:, 0] - gv * a[:, 1]
    dmin, dmax = p[:, :, 2].min(axis=1), p[:, :, 2].max(axis=1)
    # scanlines: one span per triangle and pixel row it covers
    r0 = np.ceil((p[:, :, 1].min(axis=1) - v0) / PX - 0.5).astype(int)
    r1 = np.floor((p[:, :, 1].max(axis=1) - v0) / PX - 0.5).astype(int)
    rows = np.maximum(r1 - r0 + 1, 0)
    t = np.repeat(np.arange(len(p)), rows)
    iy = np.repeat(r0, rows) + np.arange(rows.sum()) - np.repeat(np.cumsum(rows) - rows, rows)
    y = v0 + (iy + 0.5) * PX
    xl, xr = np.full(len(t), np.inf), np.full(len(t), -np.inf)
    for i, j in ((0, 1), (1, 2), (2, 0)):
        pa, pb = p[t, i], p[t, j]
        lo_, hi_ = np.minimum(pa[:, 1], pb[:, 1]), np.maximum(pa[:, 1], pb[:, 1])
        on = (y >= lo_) & (y <= hi_) & (hi_ > lo_)
        x = pa[:, 0] + (y - pa[:, 1]) * (pb[:, 0] - pa[:, 0]) / np.where(hi_ > lo_, pb[:, 1] - pa[:, 1], 1.0)
        xl = np.where(on, np.minimum(xl, x), xl)
        xr = np.where(on, np.maximum(xr, x), xr)
    c0 = np.ceil((xl - u0) / PX - 0.5)
    c1 = np.floor((xr - u0) / PX - 0.5)
    ok = np.isfinite(c0) & np.isfinite(c1) & (c1 >= c0) & (iy >= 0) & (iy < h)
    t, iy, c0, c1 = t[ok], iy[ok], np.clip(c0[ok], 0, w - 1).astype(int), np.clip(c1[ok], 0, w - 1).astype(int)
    n = c1 - c0 + 1
    # expand the spans to pixels, a few million at a time
    ends = np.cumsum(n)
    step = 4_000_000
    s = 0
    while s < len(n):
        e = int(np.searchsorted(ends, ends[s] - n[s] + step, side='right'))
        e = max(e, s + 1)
        nn = n[s:e]
        tt = np.repeat(t[s:e], nn)
        yy = np.repeat(iy[s:e], nn)
        xx = np.repeat(c0[s:e], nn) + np.arange(nn.sum()) - np.repeat(np.cumsum(nn) - nn, nn)
        d = gu[tt] * (u0 + (xx + 0.5) * PX) + gv[tt] * (v0 + (yy + 0.5) * PX) + g0[tt]
        d = np.clip(d, dmin[tt], dmax[tt])
        np.minimum.at(z, yy * w + xx, d)
        s = e
    z = z.reshape(h, w)
    # farthest surface around each pixel: an edge on a crease is compared with its own faces, not a neighbour's
    pad = np.pad(z, 1, constant_values=np.inf)
    zmax = z.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            np.maximum(zmax, pad[1 + dy:h + 1 + dy, 1 + dx:w + 1 + dx], out=zmax)
    return zmax


def view_lines(tris, verts, pairs, other, view):
    """Visible and hidden segments (lists of ((u, v), (u, v))) of one view."""
    U, V, D = VIEWS[view]
    pv = np.stack([verts @ U, verts @ V, verts @ D], axis=1)
    p = np.stack([tris @ U, tris @ V, tris @ D], axis=2)
    u0, v0 = pv[:, 0].min() - 2 * PX, pv[:, 1].min() - 2 * PX
    w = int(math.ceil((pv[:, 0].max() - u0) / PX)) + 3
    h = int(math.ceil((pv[:, 1].max() - v0) / PX)) + 3
    zmax = zbuffer(p, (u0, v0, w, h))
    e, n1, n2, step = pairs
    d1, d2 = n1 @ D, n2 @ D
    sil = ((d1 < -1e-9) & (d2 > 1e-9)) | ((d1 > 1e-9) & (d2 < -1e-9))   # front face against a back face
    sharp = np.einsum('ij,ij->i', n1, n2) < math.cos(math.radians(FEATURE_DEG))
    sel = e[(sharp | sil) & ~step]
    sel = np.concatenate([sel, other]) if len(other) else sel
    vis, hid = [], []
    for i, j in sel:
        a, b = pv[i], pv[j]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 1e-6:
            continue
        k = max(2, int(math.ceil(L / PX)) + 1)
        t = np.linspace(0, 1, k)
        q = a[None] + t[:, None] * (b - a)[None]
        ix = np.clip(((q[:, 0] - u0) / PX).astype(int), 0, w - 1)
        iy = np.clip(((q[:, 1] - v0) / PX).astype(int), 0, h - 1)
        seen = q[:, 2] <= zmax[iy, ix] + DEPTH_EPS
        # runs of seen / hidden samples; a run of one sample is noise at a crossing and joins its neighbours
        cut = np.nonzero(np.diff(seen.astype(int)))[0]
        bounds = [0, *(cut + 1), k]
        runs = [(bounds[r], bounds[r + 1], bool(seen[bounds[r]])) for r in range(len(bounds) - 1)]
        merged = []
        for r in runs:
            if merged and (r[1] - r[0] < 3 or merged[-1][2] == r[2]):
                merged[-1] = (merged[-1][0], r[1], merged[-1][2])
            else:
                merged.append(r)
        for s0, s1, sn in merged:
            ta, tb = t[s0], t[min(s1, k - 1)] if s1 < k else 1.0
            seg = (tuple(a[:2] + ta * (b - a)[:2]), tuple(a[:2] + tb * (b - a)[:2]))
            (vis if sn else hid).append(seg)
    lo = pv[:, :2].min(axis=0)
    hi = pv[:, :2].max(axis=0)
    return vis, hid, lo, hi


def chain(segs, nd=3):
    """Join segments that share end points into polylines (smaller file, cleaner dashes)."""
    def key(p):
        return (round(p[0], nd), round(p[1], nd))
    at = {}
    for i, (a, b) in enumerate(segs):
        at.setdefault(key(a), []).append(i)
        at.setdefault(key(b), []).append(i)
    used = [False] * len(segs)
    lines = []
    for i in range(len(segs)):
        if used[i]:
            continue
        used[i] = True
        line = [segs[i][0], segs[i][1]]
        for end in (1, 0):
            while True:
                tip = key(line[-1] if end else line[0])
                nxt = next((j for j in at.get(tip, ()) if not used[j]), None)
                if nxt is None:
                    break
                used[nxt] = True
                a, b = segs[nxt]
                p = b if key(a) == tip else a
                line.append(p) if end else line.insert(0, p)
        lines.append(line)
    return lines


# --- sheet ---------------------------------------------------------------------------
def fmt(x):
    s = f'{x:.1f}'
    return s[:-2] if s.endswith('.0') else s


def scale_text(s):
    n, d = s
    return f'{n}:{d}'


def layout(size):
    """Scale and the sheet positions (lower left corner of each view, sheet mm, y up) for part extents (x, y, z)."""
    sx, sy, sz = size
    W, H = SHEET
    left, top = 14.0, 14.0         # room for the dimensions left of and above the views
    for n, d in SCALES:
        k = n / d
        bw, bh = sx * k + GAP + sy * k, sy * k + GAP + sz * k     # block of views
        if left + bw + 4 <= W - 2 * MARGIN and top + bh + GAP + TITLE[1] <= H - 2 * MARGIN:
            break
    # centred in the sheet, above the title block (the labels under the bottom views sit in the GAP below)
    x0 = MARGIN + left + (W - 2 * MARGIN - left - 4 - bw) / 2
    y0 = MARGIN + TITLE[1] + GAP + (H - 2 * MARGIN - TITLE[1] - GAP - top - bh) / 2
    pos = {'front': (x0, y0), 'top': (x0, y0 + sz * k + GAP), 'right': (x0 + sx * k + GAP, y0)}
    return (n, d), k, pos


# Helvetica advance widths (1/1000 em) of ASCII 32..126, for placing centred and right-aligned text
HELV = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556,
        556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667,
        556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556,
        556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722,
        500, 500, 500, 334, 260, 334, 584]
MM = 72 / 25.4                # PDF points per mm
# line styles: width (mm), dash pattern (mm), round caps and joins
STYLES = {'v': (0.35, [], True), 'h': (0.18, [1.5, 0.8], False), 'dim': (0.18, [], False), 'fr': (0.5, [], False),
          'ctr': (0.18, [4, 0.8, 0.8, 0.8], False)}


def runs(s):
    """Split text into (font, text) runs: Latin in Helvetica (F1), Japanese in the CID font (F2)."""
    out = []
    for ch in s:
        f = 'F1' if 32 <= ord(ch) < 127 or ch == '×' else 'F2'
        if out and out[-1][0] == f:
            out[-1][1] += ch
        else:
            out.append([f, ch])
    return out


def run_width(f, t):
    if f == 'F2':
        return 1000 * len(t)          # full-width
    return sum(584 if ch == '×' else HELV[ord(ch) - 32] for ch in t)


def pdf_string(f, t):
    if f == 'F2':
        return '<' + t.encode('utf-16-be').hex().upper() + '>'
    b = t.encode('cp1252').replace(b'\\', b'\\\\').replace(b'(', b'\\(').replace(b')', b'\\)')
    return '(' + ''.join(chr(c) if 32 <= c < 127 else f'\\{c:03o}' for c in b) + ')'


class Sheet:
    """One A3 page in sheet mm (origin lower left, y up), written out as a PDF."""
    def __init__(self):
        self.ops = []
        self.style = None

    def _stroke_style(self, cls):
        if self.style != cls:
            w, dash, rnd = STYLES[cls]
            self.ops.append(f'{w} w {1 if rnd else 0} J {1 if rnd else 0} j [{" ".join(map(str, dash))}] 0 d')
            self.style = cls

    def paths(self, lines, cls):
        lines = [ln for ln in lines if len(ln) > 1]
        if not lines:
            return
        self._stroke_style(cls)
        for ln in lines:
            self.ops.append(f'{ln[0][0]:.2f} {ln[0][1]:.2f} m ' + ' '.join(f'{x:.2f} {y:.2f} l' for x, y in ln[1:]))
        self.ops.append('S')

    def poly(self, pts, cls):
        self.paths([pts], cls)

    def text(self, x, y, s, size=3.5, anchor='middle', rot=0):
        """Text with its baseline at (x, y); rot=-90 reads from bottom to top."""
        rs = runs(s)
        w = sum(run_width(f, t) for f, t in rs) * size / 1000
        dx = {'start': 0, 'middle': -w / 2, 'end': -w}[anchor]
        c, sn = (0, 1) if rot else (1, 0)
        ox, oy = x + dx * c, y + dx * sn
        body = ' '.join(f'/{f} {size} Tf {pdf_string(f, t)} Tj' for f, t in rs)
        self.ops.append(f'BT {c} {sn} {-sn} {c} {ox:.2f} {oy:.2f} Tm {body} ET')

    def arrow(self, tip, direction):
        ux, uy = direction
        L, w = 3.0, 0.9
        bx, by = tip[0] - ux * L, tip[1] - uy * L
        self.ops.append(f'{tip[0]:.2f} {tip[1]:.2f} m {bx - uy * w:.2f} {by + ux * w:.2f} l '
                        f'{bx + uy * w:.2f} {by - ux * w:.2f} l f')

    def dim_h(self, xa, xb, y_edge, y_line, value):
        """Horizontal dimension between xa and xb, drawn at y_line, extension lines from y_edge."""
        g = math.copysign(1.5, y_line - y_edge)
        for x in (xa, xb):
            self.poly([(x, y_edge + g * 0.66), (x, y_line + g)], 'dim')
        out = abs(xb - xa) < 8              # short: arrows outside, pointing in
        e = 5 if out else 0
        self.poly([(xa - e, y_line), (xb + e, y_line)], 'dim')
        self.arrow((xa, y_line), (1, 0) if out else (-1, 0))
        self.arrow((xb, y_line), (-1, 0) if out else (1, 0))
        self.text((xa + xb) / 2, y_line + 1.2, fmt(value))

    def dim_v(self, ya, yb, x_edge, x_line, value):
        g = math.copysign(1.5, x_line - x_edge)
        for y in (ya, yb):
            self.poly([(x_edge + g * 0.66, y), (x_line + g, y)], 'dim')
        out = abs(yb - ya) < 8
        e = 5 if out else 0
        self.poly([(x_line, ya - e), (x_line, yb + e)], 'dim')
        self.arrow((x_line, ya), (0, 1) if out else (0, -1))
        self.arrow((x_line, yb), (0, -1) if out else (0, 1))
        if out:                             # beside the line, clear of the arrows
            self.text(x_line - 1.5, (ya + yb) / 2 - 1.2, fmt(value), anchor='end')
        else:
            self.text(x_line - 1.2, (ya + yb) / 2, fmt(value), rot=-90)

    def projection_symbol(self, x, y):
        """Third-angle projection symbol, centred on (x, y)."""
        self.poly([(x - 7, y - 2.5), (x - 7, y + 2.5), (x - 1, y + 4), (x - 1, y - 4), (x - 7, y - 2.5)], 'fr')
        self.poly([(x - 8, y), (x, y)], 'ctr')
        r1, r2 = 4.0, 2.0
        cx = x + 6
        for r in (r1, r2):
            pts = [(cx + r * math.cos(a), y + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 49)]
            self.poly(pts, 'fr')
        self.poly([(cx - 5, y), (cx + 5, y)], 'ctr')
        self.poly([(cx, y - 5), (cx, y + 5)], 'ctr')

    def pdf(self, title, source):
        """The page as PDF bytes. Japanese text uses the standard Adobe-Japan1 font HeiseiKakuGo-W5, not embedded:
        the viewer substitutes its own Japanese gothic font. source goes into a comment for the up-to-date check."""
        W, H = SHEET
        content = f'{MM:.6f} 0 0 {MM:.6f} 0 0 cm 0 G 0 g\n' + '\n'.join(self.ops) + '\n'
        stream = zlib.compress(content.encode('ascii'), 9)
        title_hex = (b'\xfe\xff' + title.encode('utf-16-be')).hex().upper()
        objs = [
            '<< /Type /Catalog /Pages 2 0 R >>',
            '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W * MM:.2f} {H * MM:.2f}] '
            '/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>',
            None,     # content stream
            '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
            '<< /Type /Font /Subtype /Type0 /BaseFont /HeiseiKakuGo-W5-UniJIS-UCS2-H /Encoding /UniJIS-UCS2-H '
            '/DescendantFonts [7 0 R] >>',
            '<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HeiseiKakuGo-W5 '
            '/CIDSystemInfo << /Registry (Adobe) /Ordering (Japan1) /Supplement 2 >> /FontDescriptor 8 0 R /DW 1000 >>',
            '<< /Type /FontDescriptor /FontName /HeiseiKakuGo-W5 /Flags 4 /FontBBox [-92 -250 1010 922] '
            '/ItalicAngle 0 /Ascent 752 /Descent -221 /CapHeight 737 /StemV 114 >>',
            f'<< /Title <{title_hex}> /Producer (gen/case_drawings.py) >>',
        ]
        out = bytearray(f'%PDF-1.4\n%source {source}\n%\xe2\xe3\xcf\xd3\n'.encode('latin-1'))
        offsets = []
        for i, o in enumerate(objs, 1):
            offsets.append(len(out))
            if o is None:
                out += f'{i} 0 obj\n<< /Length {len(stream)} /Filter /FlateDecode >>\nstream\n'.encode() + stream + b'\nendstream\nendobj\n'
            else:
                out += f'{i} 0 obj\n{o}\nendobj\n'.encode()
        xref = len(out)
        out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode()
        out += ''.join(f'{off:010d} 00000 n \n' for off in offsets).encode()
        out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info {len(objs)} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()
        return bytes(out)


def source_hash(path, hidden):
    """Hash of everything a drawing depends on: the STL, this script and the options."""
    h = hashlib.sha256()
    for f in (path, os.path.abspath(__file__)):
        h.update(open(f, 'rb').read())
    h.update(f'{os.path.relpath(path, ROOT)} hidden={hidden}'.encode())
    return h.hexdigest()[:16]


def draw(path, out_dir, hidden=True, force=False):
    """Draw path into out_dir/<name>.pdf; returns (pdf path, scale), the scale None when it was up to date."""
    name = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(out_dir, f'{name}.pdf')
    source = source_hash(path, hidden)
    if not force and os.path.exists(dst):
        m = re.search(rb'%source (\w+)', open(dst, 'rb').read(100))
        if m and m.group(1).decode() == source:
            return dst, None
    tris = read_stl(path)
    verts, pairs, other = edges_of(tris)
    lo, hi = verts.min(axis=0), verts.max(axis=0)
    size = hi - lo
    sc, k, pos = layout(size)
    sh = Sheet()
    W, H = SHEET
    sh.poly([(MARGIN, MARGIN), (W - MARGIN, MARGIN), (W - MARGIN, H - MARGIN), (MARGIN, H - MARGIN), (MARGIN, MARGIN)], 'fr')
    boxes = {}
    for view in ('top', 'front', 'right'):
        vis, hid, vlo, vhi = view_lines(tris, verts, pairs, other, view)
        ox, oy = pos[view]

        def tx(p):
            return (ox + (p[0] - vlo[0]) * k, oy + (p[1] - vlo[1]) * k)
        if hidden:
            sh.paths([[tx(p) for p in ln] for ln in chain(hid)], 'h')
        sh.paths([[tx(p) for p in ln] for ln in chain(vis)], 'v')
        bx0, by0 = ox, oy
        bx1, by1 = ox + (vhi[0] - vlo[0]) * k, oy + (vhi[1] - vlo[1]) * k
        boxes[view] = (bx0, by0, bx1, by1)
        sh.text((bx0 + bx1) / 2, by0 - (GAP - 6 if view != 'top' else 9), LABELS[view], size=3.5)
    # overall dimensions: width and depth on the top view, height on the front view
    x0, y0, x1, y1 = boxes['top']
    sh.dim_h(x0, x1, y1, y1 + 8, size[0])
    sh.dim_v(y0, y1, x0, x0 - 8, size[1])
    fx0, fy0, fx1, fy1 = boxes['front']
    sh.dim_v(fy0, fy1, fx0, fx0 - 8, size[2])
    # title block
    tw, th = TITLE
    X, Y = W - MARGIN - tw, MARGIN
    sh.poly([(X, Y), (X, Y + th), (X + tw, Y + th)], 'fr')
    for yy in (Y + th / 2,):
        sh.poly([(X, yy), (X + tw, yy)], 'dim')
    sh.poly([(X + 95, Y), (X + 95, Y + th / 2)], 'dim')
    sh.poly([(X + 120, Y), (X + 120, Y + th / 2)], 'dim')
    project = 'nrsk エンコーダー検証基板 筐体' if 'enctest' in os.path.relpath(path, ROOT).split(os.sep) else 'nrsk 分割キーボード v2 筐体'
    sh.text(X + 3, Y + th - 6.5, project, size=3.2, anchor='start')
    sh.text(X + 3, Y + th / 2 + 3.5, f'部品：{name}', size=4.2, anchor='start')
    sh.text(X + 3, Y + 9.5, f'{os.path.relpath(path, ROOT)}', size=2.6, anchor='start')
    sh.text(X + 3, Y + 4, f'外形 {fmt(size[0])} × {fmt(size[1])} × {fmt(size[2])}　単位 mm', size=2.6, anchor='start')
    sh.text(X + 107.5, Y + 9.5, '尺度', size=2.6)
    sh.text(X + 107.5, Y + 3.5, scale_text(sc), size=3.8)
    sh.projection_symbol(X + 135, Y + 10)
    sh.text(X + 135, Y + 2.5, '第三角法', size=2.4)
    os.makedirs(out_dir, exist_ok=True)
    open(dst, 'wb').write(sh.pdf(f'{name} 三面図', source))
    return dst, sc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stl', nargs='*', help='STL files (default: case/print/*.stl)')
    ap.add_argument('-o', '--out', default=OUT, help='output directory (default: case/drawings)')
    ap.add_argument('--no-hidden', action='store_true', help='leave out the hidden (dashed) lines')
    ap.add_argument('--force', action='store_true', help='redraw even when the drawing is up to date')
    a = ap.parse_args()
    paths = a.stl or sorted(glob.glob(os.path.join(ROOT, 'case', 'print', '*.stl')))
    for p in paths:
        dst, sc = draw(os.path.abspath(p), a.out, hidden=not a.no_hidden, force=a.force)
        print(f'{os.path.relpath(dst, ROOT)}  {scale_text(sc) if sc else "up to date"}')


if __name__ == '__main__':
    sys.exit(main())
