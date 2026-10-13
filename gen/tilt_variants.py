"""Tilt-leg study (case/preview/tilt-variants/, docs/specs/case-feet-tilt.md step 2).

The back of each half is raised to 3, 6 or 9 degrees on legs under the tray, three mechanisms side by side:
  M  magnet   : a printed leg caps a rubber foot of the tray (a cup over it) and is held by a pair of 6 x 3 mm
                magnets beside the foot
  F  folding  : legs lie in a pocket under the tray and swing down on an M2 pivot; two legs share the pocket
  S  screw-in : a leg caps a foot as in M and is held by an M3 flat-head screw into a heat-set insert beside it
M and S legs stand right under the tray's feet, so the support is that of the five feet; a leg seated beside a foot
stands farther in, and the corner key by the wheel falls outside.
Every mechanism has three seats per half, each slid from a foot along an edge until it fits: one on the back edge
past the wheel, one at the inner back corner (the back edge, else the inner side edge: the ports and the corner foot
fill the back edge there) and one on the outer side edge next to the wheel, as the fifth foot: with the wheel in the
corner, two back legs alone leave the corner keys outside the support. Seats that reach past the wall's inner face
stand on a pad raised from the floor.

Tray frame (as make_case.py): x as the board, y = -board y, z up from the tray bottom. A leg's contact point sits
FOOT_PROUD + (y_front - y) tan(angle) below the tray bottom, y_front being the front feet's board y, so the front
feet and every leg tip lie on one plane at the angle.

Writes, per mechanism <m> and half <side>, under case/preview/tilt-variants/<m>/:
  <side>-tray.stl                      tray with the seats (and pads)
  <side>-leg-<seat>-<deg>.stl          leg attached to its seat (tray frame); F: unfolded
  <side>-legfoot-<seat>-<deg>.stl      rubber foot on that leg's tip (M, S)
  <side>-folded-<seat>.stl             F: both legs folded into the pocket
and variants.json (seats, contact points, leg heights, checks) for the renders; prints the comparison table.
Run with the project venv:  .venv/bin/python gen/tilt_variants.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifold3d import CrossSection, JoinType, Manifold  # noqa: E402
from make_case import (BOSS_D, FLOOR, FOOT_D, FOOT_DEPTH, OUT, STANDOFF, TRAY_FILLET, Half, hull, hull_margin,  # noqa: E402
                       write_stl)

DIR = os.path.join(OUT, 'preview', 'tilt-variants')
ANGLES = (3, 6, 9)
FOOT_H = 3.8                  # 3M CS-02
FOOT_PROUD = FOOT_H - FOOT_DEPTH
KEEP = 1.0                    # seat cuts to every other cut, and to the bottom fillet
EDGE_KEEP = TRAY_FILLET + KEEP   # seat cuts this far in from the outline (the fillet eats the first 2 mm)
PAD_TOP = 5.5                 # pad under a seat that reaches past the wall: 3.5 mm below the PCB back
PAD_WALL = 1.6
SEARCH = 70.0                 # a seat slides at most this far along its edge from its foot
HEIGHT_STEP = 0.1             # leg heights are rounded to this
ANGLE_TOL = 0.2
# M and S: the leg caps the tray's rubber foot (a cup over it locates the leg) and is held next to it, so the leg's
# own foot lands right under the tray's: the support stays that of the five feet
CUP = (FOOT_D + 0.4, FOOT_PROUD + 0.2)   # cup over the tray's foot: d, depth
CUP_WALL = 1.6
HW_SEARCH = 15.0              # magnet / insert: at most this far along the edge from the foot
LEG_FLOOR = 0.8               # leg material between its cup and its own foot recess
# M: magnet
MAG = (6.0, 3.0)              # magnet d, h (N35); holes 0.2 / 0.1 larger, press fit
# S: screw-in
S_INSERT = (4.0, 6.0)         # M3 heat-set insert hole d, depth
S_SCREW = (3.4, 6.0, 1.8)     # M3 flat head: clearance hole, head counterbore d, depth (from the leg's bottom)
S_MIN = 1.5                   # leg body left over the head
# F: folding legs
F_T = 3.0                     # leg bar: thickness across the edge and height when folded
F_GAP = 0.3
F_DEPTH = 4.0                 # pocket depth (pivot axis at half of it)
F_PIVOT_D = 2.2               # M2 pivot
F_END = 2.0                   # pocket beyond the pivot
F_ANGLES = (3, 9)             # two legs side by side in one pocket: short and long


def frame_matrix(o, a, b):
    """Local (u along the edge, v inward, z) -> tray frame; right-handed."""
    return [[a[0], b[0], 0.0, o[0]], [a[1], b[1], 0.0, o[1]], [0.0, 0.0, 1.0, 0.0]]


def cs_frame(cs, o, a, b):
    return cs.transform([[a[0], b[0], o[0]], [a[1], b[1], o[1]]])


def rrect(u0, v0, u1, v1, r):
    return CrossSection.square((u1 - u0 - 2 * r, v1 - v0 - 2 * r)).translate((u0 + r, v0 + r)).offset(r, JoinType.Round)


class Study:
    def __init__(self, side):
        self.hf = hf = Half(side)
        self.side = side
        ox0, oy0, ox1, oy1, _ = hf.outer_box
        feet = hf.feet()
        (wx, _), _ = hf.wheel_xy()
        wheel_left = wx < (ox0 + ox1) / 2
        bo, bi = (feet[0], feet[1]) if wheel_left else (feet[1], feet[0])
        self.front_y = feet[2][1]
        self.front = [feet[2], feet[3]]
        # edges, tray frame: param -> point on the outline, a (along), b (inward); u = x on the back edge, tray y
        # on a side edge
        back = (lambda u: (u, -oy0), (-1.0, 0.0), (0.0, -1.0))
        west = (lambda u: (ox0, u), (0.0, -1.0), (1.0, 0.0))
        east = (lambda u: (ox1, u), (0.0, 1.0), (-1.0, 0.0))
        # seat -> (foot it starts from, edges to try in order)
        self.edges = {
            'outer': (bo, [back]),
            'inner': (bi, [back, east if wheel_left else west]),
            'side': (feet[4], [west if wheel_left else east]),
        }
        self.mid = ((ox0 + ox1) / 2, -(oy0 + oy1) / 2)
        keep = hf.foot_keepout() + hf.holes(feet, FOOT_D)
        self.keep_cut = keep
        tunnels = CrossSection()
        for s in hf.slots:
            tunnels = tunnels + s['chan'] + hf.port_hole(s, FLOOR + STANDOFF).project()
        self.tunnels = tunnels
        conn = CrossSection()
        for c in hf.d['connectors'].values():
            conn = conn + rect_board(c['box'])
        self.keep_pad = hf.holes(hf.d['holes'], BOSS_D) + conn + hf.wheel_cut()
        self.tunnel_z = min(hf.port_z(s, FLOOR + STANDOFF)[0] for s in hf.slots) - 0.2
        self.edge_ok = hf.outer.offset(-EDGE_KEEP, JoinType.Round)
        self.wall_in = hf.inner


    def fits(self, cut, pad, top):
        """cut: footprint of everything cut into the tray (tray frame); pad: footprint of the pad (or empty);
        top: highest z any cut reaches."""
        if (cut - self.edge_ok).area() > 1e-6:
            return False
        if (cut.offset(KEEP, JoinType.Round) ^ self.keep_cut).area() > 1e-6:
            return False
        if top > self.tunnel_z - KEEP and (cut.offset(KEEP, JoinType.Round) ^ self.tunnels).area() > 1e-6:
            return False
        return pad.is_empty() or (pad.offset(KEEP, JoinType.Round) ^ self.keep_pad).area() < 1e-6

    def edges_foot_t(self, o, a):
        """The tray foot a capping seat belongs to: the foot nearest to o (tray frame)."""
        return min(((f[0], -f[1]) for f in self.hf.feet()), key=lambda f: math.dist(f, o))

    def candidates(self, name, shape, search=SEARCH):
        """Every place a seat fits, sliding along its edges up to SEARCH from its foot.
        shape(o, a, b) -> (cut, pad, top, (contact in the tray frame, ...))."""
        foot, edges = self.edges[name]
        steps = [0.0] + [s * 0.5 * i for i in range(1, int(search / 0.5) + 1) for s in (1, -1)]
        out = []
        for origin, a, b in edges:
            u0 = foot[0] if a[1] == 0 else -foot[1]
            for du in steps:
                o = origin(u0 + du)
                if not inside_box(o, self.hf.outer_box):
                    continue
                res = shape(o, a, b)
                for r in (res if isinstance(res, list) else [res]):    # a shape may offer several layouts
                    if self.fits(*r[:3]):
                        out.append(dict(origin=o, a=a, b=b, du=du, res=r))
        return out

    def margin(self, contacts):
        """Worst key: distance in from the edge of the support (front feet + leg contacts, tray frame)."""
        poly = hull(list(self.front) + [(c[0], -c[1]) for c in contacts])
        return min(hull_margin(poly, (k['cx'], k['cy'])) for k in self.hf.d['keys'])

    def select(self, shape, search=SEARCH):
        """One place per seat: the combination that keeps the keys farthest inside the support (a few rounds of
        improving one seat at a time). Seats with nowhere to go come back as None."""
        cands = {n: self.candidates(n, shape, search) for n in self.edges}
        pick = {n: (c[0] if c else None) for n, c in cands.items()}

        def score(choice):
            ps = [p for p in choice.values() if p is not None]
            for i, p in enumerate(ps):          # two seats' cuts must keep KEEP apart too
                for q in ps[i + 1:]:
                    if (p['res'][0].offset(KEEP, JoinType.Round) ^ q['res'][0]).area() > 1e-6:
                        return -math.inf
            return self.margin([p['res'][3][0] for p in ps])
        for _ in range(3):
            for n, cs in cands.items():
                if cs:
                    pick[n] = max(cs, key=lambda p: score({**pick, n: p}))
        return pick

    def contact_h(self, y_tray, deg):
        """Contact point below the tray bottom, for a tray-frame y."""
        h = FOOT_PROUD + (self.front_y + y_tray) * math.tan(math.radians(deg))   # y_tray = -board y
        return round(h / HEIGHT_STEP) * HEIGHT_STEP

    def pad_of(self, cut):
        pad = cut.offset(PAD_WALL, JoinType.Round) ^ self.wall_in.offset(-0.01)
        return pad if pad.area() > 1e-3 else CrossSection()


def inside_box(p, box):
    """Tray-frame point within the straight part of an edge of the outline box (board coordinates)."""
    ox0, oy0, ox1, oy1, r = box
    return ox0 - 1e-6 <= p[0] <= ox1 + 1e-6 and -oy1 - 1e-6 <= p[1] <= -oy0 + 1e-6


def rect_board(box):
    x0, y0, x1, y1 = box
    return CrossSection.square((x1 - x0, y1 - y0)).translate((x0, -y1))


# --- mechanisms -------------------------------------------------------------------------------------------------
def capped(st, hw_d, hw_depth, v_hw, leg_hw):
    """Seats for legs that cap a tray foot (M, S). hw_d, hw_depth: hole for the magnet / insert in the tray, its centre
    v_hw in from the outline; leg_hw(leg, h) cuts the leg's side of the hardware (leg in the local frame, hardware at
    the origin). Returns seats, tray cut and legs as the other mechanisms."""
    def shape(o, a, b):
        c = (o[0] + b[0] * v_hw, o[1] + b[1] * v_hw)
        cut = CrossSection.circle(hw_d / 2).translate(c)
        return cut, st.pad_of(cut), hw_depth, (st.edges_foot_t(o, a), c)
    seats, tray_cut, legs = {}, Manifold(), {}
    for name, p in st.select(shape, HW_SEARCH).items():
        if p is None:
            seats[name] = None
            continue
        cut, pad, top, (f, c) = p['res']
        seats[name] = dict(xy=f, hw=c, pad=pad, cut=cut)
        m = frame_matrix(c, p['a'], p['b'])
        tray_cut = tray_cut + Manifold.cylinder(hw_depth + 0.01, hw_d / 2, hw_d / 2, 48).translate((0, 0, -0.01)).transform(m)
        # foot in the hardware's local frame
        df = (f[0] - c[0], f[1] - c[1])
        fl = (df[0] * p['a'][0] + df[1] * p['a'][1], df[0] * p['b'][0] + df[1] * p['b'][1])
        r_leg = CUP[0] / 2 + CUP_WALL
        outline = hull_cs([(fl[0], fl[1], r_leg), (0.0, 0.0, max(hw_d / 2 + CUP_WALL, 4.0))])
        for deg in ANGLES:
            h = st.contact_h(f[1], deg)
            body = h - FOOT_PROUD                       # top on the tray bottom, bottom FOOT_PROUD above the contact
            leg = Manifold.extrude(outline, body).translate((0, 0, -body))
            leg = leg - Manifold.cylinder(CUP[1] + 0.01, CUP[0] / 2, CUP[0] / 2, 64).translate((fl[0], fl[1], -CUP[1]))
            leg = leg - Manifold.cylinder(FOOT_DEPTH + 0.01, FOOT_D / 2, FOOT_D / 2, 64).translate((fl[0], fl[1], -body - 0.01))
            leg, ok = leg_hw(leg, body)
            foot = Manifold.cylinder(FOOT_H, 9.5 / 2, 9.5 / 2, 64).translate((fl[0], fl[1], -h))
            legs[(name, deg)] = dict(leg=leg.transform(m), foot=foot.transform(m), h=h, body=body, contact=f,
                                     ok_body=ok and body >= CUP[1] + LEG_FLOOR + FOOT_DEPTH)
    return seats, tray_cut, legs


def hull_cs(circles):
    """Convex hull of circles (x, y, r) as a CrossSection."""
    cs = CrossSection()
    for x, y, r in circles:
        cs = cs + CrossSection.circle(r).translate((x, y))
    return cs.hull()


def magnet(st):
    def leg_hw(leg, body):
        hole = Manifold.cylinder(MAG[1] + 0.11, MAG[0] / 2 + 0.1, MAG[0] / 2 + 0.1, 48).translate((0, 0, -MAG[1] - 0.1))
        return leg - hole, body >= MAG[1] + 0.1 + 0.8
    return capped(st, MAG[0] + 0.2, MAG[1] + 0.1, EDGE_KEEP + MAG[0] / 2 + 0.1, leg_hw)


def screw(st):
    def leg_hw(leg, body):
        leg = leg - Manifold.cylinder(body + 0.02, S_SCREW[0] / 2, S_SCREW[0] / 2, 32).translate((0, 0, -body - 0.01))
        leg = leg - Manifold.cylinder(S_SCREW[2] + 0.01, S_SCREW[1] / 2, S_SCREW[1] / 2, 32).translate((0, 0, -body - 0.01))
        return leg, body >= S_MIN + S_SCREW[2]
    return capped(st, S_INSERT[0], S_INSERT[1], EDGE_KEEP + S_INSERT[0] / 2, leg_hw)


def folding(st):
    w = 2 * F_T + 3 * F_GAP
    v0 = EDGE_KEEP + w / 2
    zp = F_DEPTH / 2
    # the longest leg (back seats at the steepest angle) sets the pocket length on every seat
    l_max = st.contact_h(-st.hf.outer_box[1] - 6.0, max(F_ANGLES)) + zp

    def shape(o, a, b):
        c = (o[0] + b[0] * v0, o[1] + b[1] * v0)
        out = []
        for d in (1.0, -1.0):                 # the legs fold either way along the edge from the pivot
            u0, u1 = sorted((-d * F_END, d * (l_max + 0.5)))
            cut = cs_frame(rrect(u0, -w / 2, u1, w / 2, 1.0), c, a, b)
            out.append((cut, st.pad_of(cut), F_DEPTH, (c, d)))
        return out
    seats, tray_cut, legs = {}, Manifold(), {}
    for name, p in st.select(shape).items():
        if p is None:
            seats[name] = None
            continue
        cut, pad, top, (c, d) = p['res']
        seats[name] = dict(xy=c, pad=pad, cut=cut)
        m = frame_matrix(c, p['a'], p['b'])
        u0, u1 = sorted((-d * F_END, d * (l_max + 0.5)))
        pocket = Manifold.extrude(rrect(u0, -w / 2, u1, w / 2, 1.0), F_DEPTH + 0.01).translate((0, 0, -0.01))
        pivot = Manifold.cylinder(w + 2 * 2.0 + PAD_WALL + 2, F_PIVOT_D / 2, F_PIVOT_D / 2, 24).rotate((-90, 0, 0)).translate(
            (0, -w / 2 - 2.0, zp))
        tray_cut = tray_cut + (pocket + pivot).transform(m)
        folded = Manifold()
        for i, deg in enumerate(F_ANGLES):
            h = st.contact_h(c[1], deg)
            ln = h + zp                                   # pivot to tip
            v_off = -w / 2 + F_GAP + i * (F_T + F_GAP)
            bar = Manifold.cube((ln + F_T / 2, F_T, F_T)).translate((-F_T / 2, v_off, -F_T / 2))
            bar = bar - Manifold.cylinder(F_T + 0.02, F_PIVOT_D / 2, F_PIVOT_D / 2, 24).rotate((-90, 0, 0)).translate(
                (0, v_off - 0.01, 0))
            if d < 0:
                bar = bar.mirror((1, 0, 0))
            folded = folded + bar.translate((0, 0, zp))
            down = bar.rotate((0, 90 * d, 0)).translate((0, 0, zp))       # tip straight down
            legs[(name, deg)] = dict(leg=down.transform(m), foot=None, h=h, body=ln, contact=c,
                                     ok_body=ln + F_T / 2 <= l_max + 0.5 + F_END)
        seats[name]['folded'] = folded.transform(m)
    return seats, tray_cut, legs


MECHS = {'M': ('磁石式', magnet), 'F': ('折りたたみ式', folding), 'S': ('ねじ込み式', screw)}


def plug_boxes(hf):
    """USB-C plugs in the back-edge ports (tray frame): 12.5 x 7 mm, 25 mm out of the wall."""
    ox0, oy0, ox1, oy1, _ = hf.outer_box
    z = FLOOR + STANDOFF - 1.7
    out = []
    for c in hf.d['connectors'].values():
        if c.get('edge') == 'top':
            x = c['center'][0]
            out.append(Manifold.cube((12.5, 25.0, 7.0)).translate((x - 6.25, -oy0 - 2.0, z - 3.5)))
    return out


def run(side, key):
    st = Study(side)
    hf = st.hf
    label, fn = MECHS[key]
    seats, tray_cut, legs = fn(st)
    out = os.path.join(DIR, key)
    os.makedirs(out, exist_ok=True)
    tray = hf.tray()
    pads = CrossSection()
    for s in seats.values():
        if s and not s['pad'].is_empty():
            pads = pads + s['pad']
    if not pads.is_empty():
        tray = tray + Manifold.extrude(pads, PAD_TOP - FLOOR + 0.01).translate((0, 0, FLOOR - 0.005))
    tray = tray - tray_cut
    write_stl(os.path.join(out, f'{side}-tray.stl'), tray)
    rep = dict(label=label, seats={n: (None if s is None else [round(s['xy'][0], 2), round(-s['xy'][1], 2)])
                                   for n, s in seats.items()},
               pads=round(pads.area(), 1), legs={}, angles={}, notes=[])
    plugs = plug_boxes(hf)
    angles = F_ANGLES if key == 'F' else ANGLES
    for deg in angles:
        parts = [(n, legs[(n, deg)]) for n in seats if seats[n] is not None]
        contacts = list(st.front) + [(L['contact'][0], -L['contact'][1]) for _, L in parts]
        poly = hull(contacts)
        margin = min(hull_margin(poly, (k['cx'], k['cy'])) for k in hf.d['keys'])
        err = max(abs(math.degrees(math.atan((L['h'] - FOOT_PROUD) / (st.front_y + L['contact'][1]))) - deg)
                  for _, L in parts)
        plug_hit = sum((pl ^ L['leg']).volume() for pl in plugs for _, L in parts)
        # plug's lowest point above the desk: the desk lies FOOT_PROUD + (front_y + y) tan below the tray bottom
        t = math.tan(math.radians(deg))
        plug_low = min(FLOOR + STANDOFF - 1.7 - 3.5 + FOOT_PROUD + (st.front_y + (-hf.outer_box[1] + 25.0)) * t
                       for _ in plugs) if plugs else None
        overlap = sum((L['leg'] ^ tray).volume() for _, L in parts)
        rep['angles'][deg] = dict(margin=round(margin, 2), angle_err=round(err, 3), plug_hit=round(plug_hit, 3),
                                  plug_above_desk=round(plug_low, 1) if plug_low is not None else None,
                                  leg_in_tray=round(overlap, 3), seats_found=len(parts) == 3,
                                  bodies_ok=all(L['ok_body'] for _, L in parts))
        for n, L in parts:
            write_stl(os.path.join(out, f'{side}-leg-{n}-{deg}.stl'), L['leg'])
            if L['foot'] is not None:
                write_stl(os.path.join(out, f'{side}-legfoot-{n}-{deg}.stl'), L['foot'])
            rep['legs'][f'{n}-{deg}'] = dict(h=round(L['h'], 1), body=round(L['body'], 1),
                                            contact=[round(L['contact'][0], 2), round(-L['contact'][1], 2)])
    if key == 'F':
        for n, s in seats.items():
            if s is not None:
                write_stl(os.path.join(out, f'{side}-folded-{n}.stl'), s['folded'])
        rep['folded_in_tray'] = round(sum((s['folded'] ^ tray).volume() for s in seats.values() if s), 3)
    rep['tray_status'] = str(tray.status())
    rep['tray_genus'] = tray.genus()
    return rep


def check(rep, key):
    """Pass / fail of each item of the spec's check_tilt for one half of one mechanism."""
    a = rep['angles'].values()
    return dict(
        seats=all(s is not None for s in rep['seats'].values()),
        angle=all(v['angle_err'] <= ANGLE_TOL for v in a),
        support=all(v['margin'] > 0 for v in a),
        ribs=all(v['seats_found'] for v in a),          # seats only stand where every cut keeps KEEP
        plug=all(v['plug_hit'] < 1e-3 and (v['plug_above_desk'] or 1) > 0 for v in a),
        legs=all(v['bodies_ok'] and v['leg_in_tray'] < 1e-3 for v in a) and rep.get('folded_in_tray', 0) < 1e-3,
        steps=len(rep['angles']),
    )


def main():
    os.makedirs(DIR, exist_ok=True)
    out = {}
    for key in MECHS:
        out[key] = {}
        for side in ('left', 'right'):
            rep = run(side, key)
            rep['check'] = check(rep, key)
            out[key][side] = rep
    json.dump(out, open(os.path.join(DIR, 'variants.json'), 'w'), indent=1, ensure_ascii=False)
    head = ['案', '半分', '段', '座', '角度', '支持の余裕 mm', 'プラグ', '脚の形', 'tray']
    print(' | '.join(head))
    for key, sides in out.items():
        for side, rep in sides.items():
            c = rep['check']
            print(' | '.join(str(v) for v in (
                rep['label'], side, c['steps'], 'OK' if c['seats'] and c['ribs'] else 'NG',
                'OK' if c['angle'] else 'NG',
                '/'.join(f"{v['margin']:.1f}" for v in rep['angles'].values()),
                'OK' if c['plug'] else 'NG', 'OK' if c['legs'] else 'NG', rep['tray_status'])))


if __name__ == '__main__':
    main()
