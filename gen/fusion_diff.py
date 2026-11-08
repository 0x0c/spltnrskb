"""Compare the parts the Fusion designs exported (case/fusion/<side>/*.stl) with the ones make_case.py builds.

For every part with an exported STL: volumes, the symmetric difference, its ratio to the code part's volume and the
largest shift of the bounding box. A part over its threshold writes the difference to case/fusion/<side>/diff/ so the
place that differs can be looked at. docs/specs/fusion-case.md, "再現の検証".

Run with the project venv:  .venv/bin/python gen/fusion_diff.py [left] [right] [--part wheel ...]
Exit status 1 when a part is over its threshold.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_case import FUSION_DIR, FUSION_PARTS, ROOT, STAND_ANGLES, Half, write_stl  # noqa: E402

# per-part thresholds: (ratio of the symmetric difference to the volume, bounding-box shift in mm). The code builds
# circles from 96 segments and the fillets from 8 stacked slices, so an exact Fusion part differs by that much.
DEFAULT = (0.005, 0.05)
THRESHOLDS = {}


def parts(hf):
    """(name, code part) for every part this half has, in the frame the Fusion export uses."""
    out = [(name, getattr(hf, m)) for m, name in FUSION_PARTS.items()
           if not name.startswith('drum') or 'drum' in hf.d]
    out += [(f'stand-{deg}', lambda deg=deg: hf.stand(deg)[0]) for deg in STAND_ANGLES]
    return out


def compare(side, only=None):
    code, fusion = Half(side, source='code'), Half(side, source='fusion')
    rows, failed = [], False
    for name, build in parts(code):
        if only and name not in only:
            continue
        if not os.path.exists(os.path.join(FUSION_DIR, side, f'{name}.stl')):
            rows.append((name, None))
            continue
        a, b = build(), fusion.fusion_part(name)
        diff = a - b + (b - a)
        sym = diff.volume()
        ratio = sym / a.volume()
        bbox = max(abs(float(p) - float(q)) for p, q in zip(a.bounding_box(), b.bounding_box()))
        lim_r, lim_b = THRESHOLDS.get(name, DEFAULT)
        ok = ratio <= lim_r and bbox <= lim_b
        if not ok:
            failed = True
            os.makedirs(os.path.join(FUSION_DIR, side, 'diff'), exist_ok=True)
            write_stl(os.path.join(FUSION_DIR, side, 'diff', f'{name}.stl'), diff)
        rows.append((name, (a.volume(), b.volume(), sym, ratio, bbox, ok)))
    return rows, failed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sides', nargs='*', default=['left', 'right'])
    ap.add_argument('--part', action='append', help='compare only this part (repeatable)')
    args = ap.parse_args()
    failed = False
    print(f"{'side':6} {'part':11} {'vol_code':>10} {'vol_fusion':>10} {'sym_diff':>9} {'ratio':>8} {'bbox_dz':>8}")
    for side in args.sides:
        rows, f = compare(side, args.part)
        failed |= f
        for name, r in rows:
            if r is None:
                print(f'{side:6} {name:11} {"(no Fusion export)":>48}')
                continue
            vc, vf, sym, ratio, bbox, ok = r
            print(f"{side:6} {name:11} {vc:10.2f} {vf:10.2f} {sym:9.3f} {ratio * 100:7.3f}% {bbox:8.4f}"
                  f"{'' if ok else '  OVER -> ' + os.path.relpath(os.path.join(FUSION_DIR, side, 'diff', name + '.stl'), ROOT)}")
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
