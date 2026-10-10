"""Turn a KiCad GLB export into compact instanced meshes for the case viewer.

KiCad writes one primitive per CAD face and repeats identical part meshes, which is far too heavy for
a browser. Here every mesh's primitives are merged per material, identical meshes are shared, and
each node becomes an instance (4x4 matrix) in viewer space: mm, Z up, y = -board y.
Geometry goes into a pool shared by every board (switches, sockets, diodes... are stored once),
positions are quantised to int16 over the part's bounding box, and normals are left to the viewer.
"""
import base64
import hashlib
import json
import re
import struct

import numpy as np

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}
# glTF (metres, Y up, z = board y) -> viewer (mm, Z up, y = -board y)
TO_VIEW = np.array([[1000, 0, 0, 0], [0, 0, -1000, 0], [0, 1000, 0, 0], [0, 0, 0, 1]], dtype=np.float64)


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def trs(node):
    if 'matrix' in node:
        return np.array(node['matrix'], dtype=np.float64).reshape(4, 4).T
    t = np.eye(4)
    t[:3, 3] = node.get('translation', [0, 0, 0])
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    r = np.eye(4)
    r[:3, :3] = [[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                 [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                 [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]
    s = np.diag(list(node.get('scale', [1, 1, 1])) + [1])
    return t @ r @ s


def category(ref, mesh_name):
    """Assembly group of a KiCad part: what gets fitted together in one assembly step."""
    if 'Stabilizer' in mesh_name:
        return 'stab'
    if ref.startswith('SW'):
        return 'switch' if 'Cherry_MX' in mesh_name else 'socket'
    if re.fullmatch(r'D\d+', ref) and ref != 'D99':
        return 'diode'
    if ref in ('J1', 'J2'):
        return 'conn'
    if ref == 'J3':
        return 'oled'
    if ref == 'ENC1':
        return 'encoder'
    if '_PCB' in mesh_name or ref.endswith('_PCB') or ref.startswith(('left', 'right')):
        return 'board'
    return 'smd'


def load(path, pool):
    """Append new geometry to pool (list, plus pool_index dict) and return {category: [(pool id, instances)]}."""
    d = open(path, 'rb').read()
    jl = struct.unpack('<I', d[12:16])[0]
    j = json.loads(d[20:20 + jl])
    binary = d[20 + jl + 8:]

    def acc(i):
        a = j['accessors'][i]
        bv = j['bufferViews'][a['bufferView']]
        n = NCOMP[a['type']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        arr = np.frombuffer(binary, COMP[a['componentType']], a['count'] * n, off)
        return arr.reshape(-1, n) if n > 1 else arr

    mats = []
    for m in j.get('materials', []):
        p = m.get('pbrMetallicRoughness', {})
        c = p.get('baseColorFactor', [0.7, 0.7, 0.7, 1])
        mats.append(dict(c=[round(v, 4) for v in c], m=round(p.get('metallicFactor', 0), 3),
                         r=round(p.get('roughnessFactor', 0.6), 3)))
    index = pool.setdefault('index', {})
    items = pool.setdefault('items', [])

    # merge each mesh's primitives per material; share identical meshes
    mesh_parts = {}
    for mi, mesh in enumerate(j['meshes']):
        per = {}
        for p in mesh['primitives']:
            pos = acc(p['attributes']['POSITION'])
            idx = acc(p['indices']) if 'indices' in p else np.arange(len(pos))
            per.setdefault(p.get('material', 0), []).append((pos, idx))
        parts = []
        for mat, chunks in sorted(per.items()):
            off, P, I = 0, [], []
            for pos, idx in chunks:
                P.append(pos); I.append(idx.astype(np.uint32) + off); off += len(pos)
            P, I = np.concatenate(P).astype(np.float64), np.concatenate(I)
            lo, hi = P.min(0), P.max(0)
            sc = np.where(hi > lo, (hi - lo) / 65534, 1.0)
            q = np.round((P - lo) / sc - 32767).astype(np.int16)
            key = hashlib.sha1(q.tobytes() + I.tobytes() + json.dumps(mats[mat]).encode()).hexdigest()
            if key not in index:
                index[key] = len(items)
                items.append(dict(mat=mats[mat], v=b64(q), o=(lo + 32767 * sc).tolist(), s=sc.tolist(),
                                  i=b64(I.astype(np.uint16 if len(P) < 65536 else np.uint32)), big=bool(len(P) >= 65536)))
            parts.append(index[key])
        mesh_parts[mi] = parts

    # walk the scene graph for instance matrices
    inst = {}

    def walk(ni, parent, ref):
        node = j['nodes'][ni]
        m = parent @ trs(node)
        if 'mesh' in node:
            cat = category(ref or node.get('name', ''), j['meshes'][node['mesh']].get('name', ''))
            for g in mesh_parts[node['mesh']]:
                inst.setdefault((cat, g), []).append(m)
        for c in node.get('children', []):
            walk(c, m, ref or j['nodes'][c].get('name', ''))
    for root in j['scenes'][j.get('scene', 0)]['nodes']:
        walk(root, TO_VIEW, None)
    out = {}
    for (cat, g), ms in inst.items():
        out.setdefault(cat, []).append((g, b64(np.array([m.T.reshape(16) for m in ms], dtype=np.float32))))   # column-major
    return out
