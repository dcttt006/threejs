# Builds the Philips Stadion (PSV, Eindhoven) from nothing and exports it for
# the game, the way the Jan Breydelstadion and the Stade Joseph Marien are
# built; on a June afternoon, the sun behind the main stand, the north stand
# with PHILIPS in its seats in full light.
#   blender -b --factory-startup --python tools/philips_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/philips_assets.py, the plan from
# tools/philips_osm.py.
#
# The facts and the plan:
#   - PSV's ground since 1913 on Frederiklaan, between Philipsdorp and the
#     railway; four stands of two rings each, every seat covered, 35.119
#     places; the main stand (Zuidtribune) on Frederiklaan, the north stand on
#     the railway, the ends east (Oost, the home fans, its first ring safe
#     standing) and west; the four open corners closed in 2000-2002 (Toon van
#     Aken) with the corner pods: the corners' second rings in shells of
#     louvres, a dome on each, hung from two white pylons by cables
#   - the plan is OpenStreetMap's (way 270383267, the stadium; 185034347, the
#     pitch; data © OpenStreetMap contributors, ODbL), turned 36.96 degrees
#     so the pitch lies on the axes: the inner edge of the stands 14.2 m
#     behind the goal lines, 7.4 m from the north touchline and 8.5 m from
#     the main stand's
#   - every stand as on the photos: the first ring in two blocks with a
#     walkway and a white wall between them, two rows of business seats in
#     front of the glass of the lounges under the second ring, the front of
#     the second ring a red LED band, the second ring up to the roof; red
#     seats everywhere; PHILIPS in cream seats with a black shadow in the
#     north stand's second ring, OOST in white in the east end's first ring,
#     PSV behind the dugouts in the main stand's first ring
#   - the dugouts in the main stand's first rows either side of the tunnel
#     (1913 on its red sides), the four LED screens of 8 x 4.5 m at the ends
#     of both long stands' second rings (game.screen.js, style 'philips': the
#     orange-red board with the clock in a white box, the crests and the
#     score), the away section in the north-west corner behind fences and a
#     net, its footbridge from the station Eindhoven Stadion
#   - the roofs: over the north stand white trusses on top of pale sheeting
#     and down its back, the main stand's roof of glass on white trusses, the
#     ends white; a deep white girder along every front with clusters of
#     floodlights on it; eight white pylons, two at each pod
#   - outside: a base of white offices round the whole ground, a band of
#     windows a floor, red columns at the ground floor; the main stand's
#     front with 'philips stadion', a red band and flags, the red steel
#     crosses on its back; the north side's colonnade and red stair towers;
#     round it Frederiklaan, Philipsdorp's gabled houses, the railway and the
#     station's platform, the towers of the Hartje
# No sponsors: the boards carry the club's, the stadium's and the city's own
# words.
#
# The helpers, the goals and the export are those of tools/jan_breydel_build.py;
# units are metres, x along the pitch towards the west end, y towards the
# main stand (the match camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'philips')
os.makedirs(TEX_DIR, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data
sc = bpy.context.scene
for name in ('01_Pitch', '02_Bowl', '03_Seats', '04_Roof', '05_Outside', '06_Backdrop'):
    c = D.collections.new(name)
    sc.collection.children.link(c)

# ---------------------------------------------------------------- dimensions (metres)
PW, PL = 105.0, 68.0
LINE = 0.12
UPV = Vector((0, 0, 1))
XW, XE, YN, YS = 66.7, -66.7, -41.4, 42.5     # the fronts: the west end, the east end, the north stand, the main stand (OSM)
RC = 6.0                                      # the corners at the front (they grow with every row)
N_LONG, N_END, N_CORN = 18, 12, 12            # pieces: a long side, an end, a corner
WALL_Z = 1.1                                  # the wall round the pitch
SEAT_W, AISLE_W = 0.5, 1.1
# the first ring: 13 rows, a walkway with a white wall, 5 rows; the walkway
# behind them, two rows of business seats in front of the lounges' glass
LOW_ROWS = [(0.0, 0.5, WALL_Z, 'walk')]
LOW_ROWS += [(0.5 + 0.8 * k, 1.3 + 0.8 * k, 1.45 + 0.42 * k, 'seat') for k in range(13)]
LOW_ROWS += [(10.9, 12.5, 6.64, 'walk')]
LOW_ROWS += [(12.5 + 0.8 * j, 13.3 + 0.8 * j, 7.70 + 0.42 * j, 'seat') for j in range(5)]
LOW_ROWS += [(16.5, 17.3, 9.78, 'walk'), (17.3, 18.3, 10.10, 'biz'), (18.3, 19.5, 10.45, 'biz')]
GLASS_D = 19.5                                # the lounges' glass
BAL_D, FASCIA_Z0, FASCIA_Z1 = 16.9, 12.6, 14.0   # the front of the second ring: its LED band
UP_ROWS = [(17.0 + 0.8 * k, 17.8 + 0.8 * k, 14.25 + 0.56 * k, 'seat') for k in range(18)]
UP_ROWS += [(31.4, 32.4, 24.2, 'walk')]
UP_TOP = 24.2
BACK_D = 32.4                                 # the back wall of the second ring
BASE_H = 12.5                                 # the white offices round the ground
ROOF_D0, ROOF_D1 = -1.0, 34.0                 # the roof: the front of its girder, its eave
GIRDER_Z0, GIRDER_Z1, GIRDER_D = 26.6, 29.6, 1.0
ROOF_T0, ROOF_T1 = 29.4, 28.2                 # the sheeting's top at the girder and at the eave
SCR_W, SCR_H = 8.0, 4.5                       # the four LED screens (PPDS, 2025)
SCR_X = 56.1                                  # at both ends of both long stands
SCR_Z0, SCR_DF = 15.35, 18.15                 # their bottom edge, their face's offset
PYLON_H = 46.0
GAIN = 2.0                                    # the game draws the model unlit at this gain (catalog: look.gain)
# the sun: a June afternoon, south-south-west, 56 degrees up: behind the main
# stand, full on the north stand; the main stand's shadow over the near touchline
SUN_AZ, SUN_EL = math.radians(102.0), math.radians(56)       # from the plan's x, towards y
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))
OUTLINE = OSM['stadium'][:-1] if OSM['stadium'][0] == OSM['stadium'][-1] else OSM['stadium']
BOARD_X, BOARD_Y = PW / 2 + 5.0, PL / 2 + 4.2


# ---------------------------------------------------------------- helpers (as in the Jan Breydel script)
def principled(name, color, rough=0.8, emission=None, strength=1.0, metallic=0.0):
    m = D.materials.get(name) or D.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    if emission:
        b.inputs['Emission Color'].default_value = (*emission, 1)
        b.inputs['Emission Strength'].default_value = strength
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    return m


def image_material(name, img, rough, metallic=0.0):
    m = D.materials.get(name) or D.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    b = nt.nodes.new('ShaderNodeBsdfPrincipled')
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metallic
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    nt.links.new(b.outputs['BSDF'], out.inputs['Surface'])
    nt.nodes.active = t
    return m


def alpha_material(name, img, rough=0.8):
    # a picture with holes (nets): its alpha cuts through
    m = image_material(name, img, rough)
    nt = m.node_tree
    nt.links.new(next(n for n in nt.nodes if n.type == 'TEX_IMAGE').outputs['Alpha'], next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Alpha'])
    for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
        try:
            setattr(m, attr, val)
        except Exception:
            pass
    return m


def save_img(img, name):
    img.filepath_raw = TEX_DIR + '/' + name + '.png'; img.file_format = 'PNG'; img.save()


def to_srgb(a):
    a = np.clip(a, 0, 1)
    return np.where(a <= 0.0031308, 12.92 * a, 1.055 * a ** (1 / 2.4) - 0.055)


def painted(name, arr):
    # a picture from a (h, w, 3) array of linear colours, row 0 at the bottom
    h, w, _ = arr.shape
    img = D.images.new(name, w, h)
    px = np.ones((h, w, 4), 'f')
    px[..., :3] = to_srgb(arr)
    img.pixels.foreach_set(px.ravel())
    save_img(img, name)
    img.pack()
    return img


def load_asset(name):
    img = D.images.load(os.path.join(ASSETS, name))
    img.pack()
    return img


def asset_pixels(name):
    # a picture from tools/philips as floats, row 0 at the top
    img = D.images.load(os.path.join(ASSETS, name))
    w, h = img.size
    a = np.empty(w * h * 4, 'f'); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1].copy()
    D.images.remove(img)
    return a


def new_obj(name, bm, coll, mats):
    me = D.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    o = D.objects.new(name, me)
    D.collections[coll].objects.link(o)
    return o


def face(bm, pts, want=None, mat=0, uvs=None):
    verts = [bm.verts.new(p) for p in pts]
    f = bm.faces.new(verts)
    f.material_index = mat
    if uvs:
        uv = bm.loops.layers.uv.verify()
        by_vert = dict(zip(verts, uvs))
        for l in f.loops:
            l[uv].uv = by_vert[l.vert]
    if want is not None:
        f.normal_update()
        if f.normal.dot(want) < 0:
            f.normal_flip()
    return f


def box(bm, c, ax, hx_, ay, hy_, z0, z1, mat=0, top=True, bottom=True):
    # an upright box: centre c (plan), half sizes along ax and ay, from z0 to z1
    ax, ay = Vector((ax[0], ax[1], 0)).normalized(), Vector((ay[0], ay[1], 0)).normalized()
    if ax.x * ay.y - ax.y * ay.x < 0:
        ay = -ay
    c = Vector((c[0], c[1], 0))
    lo = [c + ax * sx * hx_ + ay * sy * hy_ + Vector((0, 0, z0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    hi = [v + Vector((0, 0, z1 - z0)) for v in lo]
    mid = c + Vector((0, 0, (z0 + z1) / 2))
    if bottom:
        face(bm, lo, -UPV, mat)
    if top:
        face(bm, hi, UPV, mat)
    for i in range(4):
        j = (i + 1) % 4
        face(bm, [lo[i], lo[j], hi[j], hi[i]], (lo[i] + lo[j]) / 2 - Vector((mid.x, mid.y, z0)), mat)


def abox(bm, x0, x1, y0, y1, z0, z1, mat=0, top=True, bottom=False):
    box(bm, ((x0 + x1) / 2, (y0 + y1) / 2), (1, 0), abs(x1 - x0) / 2, (0, 1), abs(y1 - y0) / 2, z0, z1, mat, top, bottom)


def obox(bm, c, ax, ay, az, hx_, hy_, hz_, mat=0):
    # a box turned any way: centre c, three axes at right angles, half sizes
    for axis, half, o1, h1, o2, h2 in ((ax, hx_, ay, hy_, az, hz_), (ay, hy_, az, hz_, ax, hx_), (az, hz_, ax, hx_, ay, hy_)):
        for s in (-1, 1):
            cc = c + axis * (s * half)
            face(bm, [cc - o1 * h1 - o2 * h2, cc + o1 * h1 - o2 * h2, cc + o1 * h1 + o2 * h2, cc - o1 * h1 + o2 * h2], axis * s, mat)


def tube(bm, p0, p1, r, mat, seg=8, trim=0.0, step=2.5):
    # a round bar from p0 to p1, a ring of points every `step` (the baked
    # light follows it); `trim` pulls both ends in
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    u = d / L
    if trim and L > 2.5 * trim:
        p0, p1, L = p0 + u * trim, p1 - u * trim, L - 2 * trim
    q = u.to_track_quat('Z', 'Y').to_matrix()
    ax, ay = q @ Vector((1, 0, 0)), q @ Vector((0, 1, 0))
    n = max(1, math.ceil(L / step))
    rings = []
    for k in range(n + 1):
        c = p0 + u * (L * k / n)
        rings.append([bm.verts.new(c + (ax * math.cos(2 * math.pi * j / seg) + ay * math.sin(2 * math.pi * j / seg)) * r) for j in range(seg)])
    for k in range(n):
        for j in range(seg):
            f = bm.faces.new((rings[k][j], rings[k][(j + 1) % seg], rings[k + 1][(j + 1) % seg], rings[k + 1][j]))
            f.material_index = mat
    for ring_, flip in ((rings[0], True), (rings[-1], False)):
        f = bm.faces.new(ring_[::-1] if flip else ring_)
        f.material_index = mat


def prism(bm, a, b, w, z_top, z_bot, mat, step=2.0):
    # a beam of width w under a line from a to b (plan); z_top(t), z_bot(t)
    # for t from 0 at a to 1 at b; in pieces so the baked light follows it
    a, b = Vector((a.x, a.y, 0)), Vector((b.x, b.y, 0))
    L = (b - a).length
    side = Vector((-(b - a).y, (b - a).x, 0)).normalized() * (w / 2)
    n = max(1, math.ceil(L / step))
    for k in range(n):
        t0, t1 = k / n, (k + 1) / n
        p0, p1 = a.lerp(b, t0), a.lerp(b, t1)
        for s in (-1, 1):
            o = side * s
            face(bm, [p0 + o + Vector((0, 0, z_bot(t0))), p1 + o + Vector((0, 0, z_bot(t1))),
                      p1 + o + Vector((0, 0, z_top(t1))), p0 + o + Vector((0, 0, z_top(t0)))], o, mat)
        face(bm, [p0 - side + Vector((0, 0, z_bot(t0))), p1 - side + Vector((0, 0, z_bot(t1))),
                  p1 + side + Vector((0, 0, z_bot(t1))), p0 + side + Vector((0, 0, z_bot(t0)))], -UPV, mat)
        face(bm, [p0 - side + Vector((0, 0, z_top(t0))), p1 - side + Vector((0, 0, z_top(t1))),
                  p1 + side + Vector((0, 0, z_top(t1))), p0 + side + Vector((0, 0, z_top(t0)))], UPV, mat)
    for t, p, sg in ((0.0, a, -1), (1.0, b, 1)):
        face(bm, [p - side + Vector((0, 0, z_bot(t))), p + side + Vector((0, 0, z_bot(t))),
                  p + side + Vector((0, 0, z_top(t))), p - side + Vector((0, 0, z_top(t)))], (b - a) * sg, mat)


def inside_poly(x, y, poly):
    c = False
    n = len(poly)
    for k in range(n):
        (ax, ay), (bx, by) = poly[k], poly[(k + 1) % n]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            c = not c
    return c


# ---------------------------------------------------------------- the plan: the bowl as one path
# A path is a row of nodes along the front of the stands, each with its
# outward direction; a point at offset d (metres back from the front) lies on
# the same line out at every d. Piece i runs from node i to node i + 1; the
# path runs right round: the north stand (east to west), the north-west
# corner, the west end, the south-west corner, the main stand (west to east),
# the south-east corner, the east end, the north-east corner.
V2 = lambda x, y: Vector((x, y, 0))


def make_path(segs):
    nodes, info = [], []
    for side, kind, prm, n in segs:
        for k in range(n):
            t = k / n
            if kind == 'line':
                a, b, nrm = prm
                nodes.append((a.lerp(b, t), nrm.copy()))
            else:
                c, r, a0, a1 = prm
                ang = a0 + (a1 - a0) * t
                N = Vector((math.cos(ang), math.sin(ang), 0))
                nodes.append((c + N * r, N))
            info.append((side, k, n))
    nodes.append((nodes[0][0].copy(), nodes[0][1].copy()))
    return nodes, info


NODES, INFO = make_path([
    ('N', 'line', (V2(XE + RC, YN), V2(XW - RC, YN), V2(0, -1)), N_LONG),
    ('cNW', 'arc', (V2(XW - RC, YN + RC), RC, -math.pi / 2, 0.0), N_CORN),
    ('W', 'line', (V2(XW, YN + RC), V2(XW, YS - RC), V2(1, 0)), N_END),
    ('cSW', 'arc', (V2(XW - RC, YS - RC), RC, 0.0, math.pi / 2), N_CORN),
    ('S', 'line', (V2(XW - RC, YS), V2(XE + RC, YS), V2(0, 1)), N_LONG),
    ('cSE', 'arc', (V2(XE + RC, YS - RC), RC, math.pi / 2, math.pi), N_CORN),
    ('E', 'line', (V2(XE, YS - RC), V2(XE, YN + RC), V2(-1, 0)), N_END),
    ('cNE', 'arc', (V2(XE + RC, YN + RC), RC, math.pi, 1.5 * math.pi), N_CORN),
])
NP = len(INFO)
SIDE_RANGE = {}
for i, (side, k, n) in enumerate(INFO):
    if k == 0:
        SIDE_RANGE[side] = (i, i + n)
CORNERS = ('cNW', 'cSW', 'cSE', 'cNE')
is_corner = lambda i: INFO[i % NP][0].startswith('c')
is_straight = lambda i: not is_corner(i)


def P(i, u, d):
    (Fa, Na), (Fb, Nb) = NODES[i], NODES[i + 1]
    return (Fa + Na * d).lerp(Fb + Nb * d, u)


def corner_t(i, u):
    # how far along its corner a point of a corner piece lies, 0 to 1
    side, k, n = INFO[i]
    return (k + u) / n


def cumlen(d):
    c = [0.0]
    for i in range(NP):
        c.append(c[-1] + (P(i, 1, d) - P(i, 0, d)).length)
    return c


def is_aisle(i):
    # a stairway at node i: where a stand meets a corner, every second piece
    # of a straight (sections of 13.5 m on the long sides, 12 m at the ends),
    # every fourth of a corner
    side, k, n = INFO[i % NP]
    if k == 0:
        return True
    return k % (4 if side.startswith('c') else 2) == 0


def ring(bm, d0, z0, d1, z1, mat, want=None, step=3.0, zstep=None, u_len=None, v=(0, 1), keep=None):
    # a strip from offset d0 at height z0 to d1 at z1 right round the bowl;
    # when d0 == d1 a wall, cut in bands of `zstep`
    cum = cumlen(d0)
    for i in range(NP):
        if keep and not keep(i):
            continue
        p0_, p1_ = P(i, 0, d0), P(i, 1, d0)
        Lf = cum[i + 1] - cum[i]
        out = (NODES[i][1] + NODES[i + 1][1]).normalized()
        w = {'up': UPV, 'down': -UPV, 'out': out, 'in': -out}.get(want) if isinstance(want, str) else want
        if w is None:
            w = UPV if abs(z1 - z0) < 1e-6 else -out
        n = max(1, math.ceil(max(Lf, (P(i, 1, d1) - P(i, 0, d1)).length) / step))
        bands = [(z0, z1, v[0], v[1])]
        if zstep and abs(d1 - d0) < 1e-6 and abs(z1 - z0) > zstep:
            m = math.ceil(abs(z1 - z0) / zstep)
            bands = [(z0 + (z1 - z0) * j / m, z0 + (z1 - z0) * (j + 1) / m,
                      v[0] + (v[1] - v[0]) * j / m, v[0] + (v[1] - v[0]) * (j + 1) / m) for j in range(m)]
        for s in range(n):
            t0, t1 = s / n, (s + 1) / n
            p0, p1 = P(i, t0, d0), P(i, t1, d0)
            q0, q1 = P(i, t0, d1), P(i, t1, d1)
            for za, zb, v0, v1 in bands:
                uvs = None
                if u_len:
                    c0_, c1_ = (cum[i] + Lf * t0) / u_len, (cum[i] + Lf * t1) / u_len
                    uvs = [(c0_, v0), (c1_, v0), (c1_, v1), (c0_, v1)]
                face(bm, [(p0.x, p0.y, za), (p1.x, p1.y, za), (q1.x, q1.y, zb), (q0.x, q0.y, zb)], w, mat, uvs)


HX, HY, CY0 = XW - RC, (YS - YN) / 2 - RC, (YS + YN) / 2


def d_front(x, y):
    # how far a point of the plan lies out from the front of the stands
    ax, ay = abs(x) - HX, abs(y - CY0) - HY
    if ax > 0 and ay > 0:
        return math.hypot(ax, ay) - RC
    return max(ax, ay) - RC


def roof_top(d): return ROOF_T0 + (ROOF_T1 - ROOF_T0) * (d - GIRDER_D) / (ROOF_D1 - GIRDER_D)
def roof_under(d): return roof_top(d) - 0.35


# the corner pods: how round each is at t (0 at its ends, 1 in its middle)
def pod_s(t): return math.sin(math.pi * max(0.0, min(1.0, t)))


POD_TOP_Z = 31.4
POD_PROFILE = [(12.5, 30.0), (14.5, 33.4), (17.0, 35.9), (20.0, 37.6), (23.0, 38.5), (26.0, 38.4), (28.4, 37.6), (29.9, 36.4), (30.9, 35.1), (POD_TOP_Z, 33.5)]


def pod_top(t):
    s = pod_s(t)
    return roof_top(ROOF_D1) * (1 - s) + POD_TOP_Z * s, ROOF_D1 * (1 - s) + 33.5 * s


def pod_point(t, j):
    # point j of the shell's profile at t: (d, z); the lens: its bottom rises
    # towards the pylons, its bulge flattens onto the stands' back walls
    s = pod_s(t)
    zb = BASE_H + 11.0 * (1 - s) ** 1.5
    zt, dt = pod_top(t)
    zp, dp = POD_PROFILE[j]
    z = zb + (zp - BASE_H) * (zt - zb) / (POD_TOP_Z - BASE_H)
    d = BACK_D + (dp - BACK_D) * s ** 0.4
    if j == len(POD_PROFILE) - 1:
        d = dt
    return d, z


def dome_z(d, t):
    # the corner roofs: flat where they meet the straight ones, a dome in the middle
    s = pod_s(t)
    zt, dt = pod_top(t)
    f = max(0.0, min(1.0, (d - GIRDER_D) / (dt - GIRDER_D)))
    mid = GIRDER_Z1 + (POD_TOP_Z - GIRDER_Z1) * f + 3.4 * math.sin(math.pi * f) ** 0.7
    return roof_top(d) * (1 - s) + mid * s


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1913)


def vnoise(h, w, cy, cx):
    g = rng.normal(0, 1, (h // cy + 3, w // cx + 3)).astype('f')
    yy, xx = np.arange(h, dtype='f') / cy, np.arange(w, dtype='f') / cx
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    return (g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0 + 1][:, x0] * fy * (1 - fx)
            + g[y0][:, x0 + 1] * (1 - fy) * fx + g[y0 + 1][:, x0 + 1] * fy * fx)


def seat_tile(color, stripes=False):
    t = np.zeros((32, 32, 3), 'f')
    t[:] = np.array(color, 'f') * np.linspace(0.80, 1.0, 32)[:, None, None]
    if stripes:                                   # the dugouts' seats: red and white stripes up the back
        t[14:, 5:9] = t[14:, 13:17] = t[14:, 21:25] = (0.80, 0.80, 0.78)
    t[:, :2] *= 0.35; t[:, -2:] *= 0.35
    t[-2:] *= 1.08
    return t


def glazing_tex():
    # the lounges' glass: dark, white mullions every 1.5 m (u: 6 m)
    w, h = 384, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.035, 0.045, 0.055), 'f')
    t *= np.linspace(0.7, 1.4, h)[:, None, None]
    t[:, (np.arange(w) % 96) < 4] = (0.70, 0.70, 0.69)
    t[:5] = (0.70, 0.70, 0.69); t[-5:] = (0.70, 0.70, 0.69)
    return t


def louvre_tex():
    # the pods' louvres: pale metal fins, 0.5 m apart, the dark inside between
    # them and the steel of the stand behind (u: 8 m, v: the whole height)
    w, h = 512, 256
    x = np.arange(w)
    fin = ((x % 32) < 13).astype('f')
    t = np.ones((h, w, 3), 'f') * np.array((0.035, 0.037, 0.04), 'f')
    shade = np.linspace(0.55, 1.0, 13)
    col = np.zeros((w,), 'f')
    col[(x % 32) < 13] = shade[(x % 32)[(x % 32) < 13]]
    metal = np.array((0.42, 0.43, 0.44), 'f')
    t = t * (1 - fin)[None, :, None] + (metal * col[:, None])[None, :, :] * fin[None, :, None]
    # the raking steel seen between the fins
    yy, xx = np.mgrid[0:h, 0:w]
    diag = (((xx + yy * 0.9) % 256) < 6) | (((xx - yy * 0.9) % 256) < 6)
    t[diag & (fin[None, :] < 0.5)] = (0.10, 0.10, 0.11)
    return t


def roof_under_tex():
    # the sheeting under the roofs: white ribbed panels (u: 4 m)
    w, h = 128, 32
    t = np.ones((h, w, 3), 'f') * np.array((0.62, 0.63, 0.62), 'f')
    t[:, (np.arange(w) % 16) < 3] *= 0.72
    return t


def glass_roof_tex():
    # the main stand's glass roof from above: grey-blue panes, white glazing bars (u: 6 m, v: 6 m)
    w, h = 192, 192
    t = np.ones((h, w, 3), 'f') * np.array((0.16, 0.19, 0.22), 'f')
    t *= (1 + 0.15 * vnoise(h, w, 48, 48))[..., None]
    t[:, (np.arange(w) % 48) < 3] = (0.70, 0.71, 0.70)
    t[(np.arange(h) % 96) < 3, :] = (0.70, 0.71, 0.70)
    return t


def sheet_tex():
    # the north roof's sheeting from above: pale ribbed panels (u: 6 m)
    w, h = 192, 64
    t = np.ones((h, w, 3), 'f') * np.array((0.64, 0.64, 0.61), 'f')
    t[:, (np.arange(w) % 12) < 2] *= 0.86
    t *= (1 + 0.04 * vnoise(h, w, 16, 16))[..., None]
    return t


def foliage_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.045, 0.09, 0.03), 'f')
    t *= (1 + 0.35 * vnoise(h, w, 6, 6) + 0.2 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


def graffiti_tex():
    # the noise wall along the station's platform, sprayed all over (u: 24 m)
    w, h = 768, 48
    t = np.ones((h, w, 3), 'f') * np.array((0.10, 0.12, 0.11), 'f')
    cols = [(0.6, 0.3, 0.5), (0.2, 0.5, 0.6), (0.7, 0.6, 0.2), (0.3, 0.6, 0.3), (0.7, 0.7, 0.7), (0.6, 0.2, 0.15), (0.25, 0.25, 0.6)]
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(60):
        cx, cy, r = rng.uniform(0, w), rng.uniform(5, h - 5), rng.uniform(6, 26)
        m = ((xx - cx) / (r * 1.6)) ** 2 + ((yy - cy) / r) ** 2 < 1
        t[m] = np.array(cols[rng.integers(len(cols))], 'f') * rng.uniform(0.7, 1.1)
    return t


SEATS = [(0.62, 0.018, 0.022),                 # 0: PSV red
         (0.53, 0.014, 0.019),                 # 1: a shade darker
         (0.80, 0.70, 0.50),                   # 2: PHILIPS: cream
         (0.80, 0.80, 0.78),                   # 3: OOST, PSV: white
         (0.020, 0.020, 0.022),                # 4: their shadows: black
         (0.42, 0.012, 0.018),                 # 5: the business seats: deep red, padded
         (0.60, 0.02, 0.025)]                  # 6: the dugouts: red, white stripes
RED, RED2, CREAM, WHITE_S, BLACK_S, BIZ, DUG = range(7)
seat_cols = [image_material('M_Seat%d' % i, painted('ps_seat%d' % i, seat_tile(c, i == DUG)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.40, 0.40, 0.385), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.28, 0.28, 0.27), 0.9)
concrete_light = principled('M_ConcreteLight', (0.52, 0.52, 0.50), 0.85)
white_paint = principled('M_WhitePaint', (0.80, 0.80, 0.78), 0.7)
truss_white = principled('M_TrussWhite', (0.80, 0.80, 0.78), 0.5)
roof_white = principled('M_RoofWhite', (0.76, 0.76, 0.73), 0.7)
pod_metal = principled('M_PodMetal', (0.62, 0.60, 0.55), 0.5)
pylon_mat = principled('M_Pylon', (0.74, 0.75, 0.76), 0.4)
cable_mat = principled('M_Cable', (0.10, 0.10, 0.11), 0.5)
steel_dark = principled('M_SteelDark', (0.042, 0.044, 0.048), 0.6)
steel_grey = principled('M_SteelGrey', (0.34, 0.35, 0.36), 0.5)
galv = principled('M_Galvanised', (0.46, 0.47, 0.48), 0.5)
red_steel = principled('M_RedSteel', (0.58, 0.025, 0.03), 0.5)
fascia_white = principled('M_FasciaWhite', (0.78, 0.78, 0.76), 0.6)
portal = principled('M_Portal', (0.015, 0.015, 0.018), 0.95)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
lamp_glass = principled('M_LampGlass', (0.90, 0.90, 0.86), 0.2)
base_roof = principled('M_BaseRoof', (0.30, 0.30, 0.295), 0.9)
glazing = image_material('M_Glazing', painted('ps_glazing', glazing_tex()), 0.2)
louvres = image_material('M_Louvres', painted('ps_louvres', louvre_tex()), 0.5)
roof_under_mat = image_material('M_RoofUnder', painted('ps_roofunder', roof_under_tex()), 0.7)
glass_roof = image_material('M_GlassRoof', painted('ps_glassroof', glass_roof_tex()), 0.3)
_gu = glass_roof_tex() * 0.0 + np.array((0.62, 0.66, 0.70), 'f')
_gu[:, (np.arange(192) % 48) < 3] = (0.80, 0.80, 0.78); _gu[(np.arange(192) % 96) < 3, :] = (0.80, 0.80, 0.78)
glass_under = image_material('M_GlassUnder', painted('ps_glassunder', _gu), 0.3)        # the glass from under it: the sky through it
sheet_mat = image_material('M_Sheet', painted('ps_sheet', sheet_tex()), 0.6)
graffiti = image_material('M_Graffiti', painted('ps_graffiti', graffiti_tex()), 0.8)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
band_mat = image_material('M_Band', load_asset('band.png'), 0.6)
tunnel_mat = image_material('M_Tunnel', load_asset('tunnel.png'), 0.7)
facade_mat = image_material('M_Facade', load_asset('facade.png'), 0.7)
shops_mat = image_material('M_Shops', load_asset('shops.png'), 0.6)
flags_mat = image_material('M_Flags', load_asset('flags.png'), 0.8)
sign_mat = alpha_material('M_Sign', load_asset('sign.png'), 0.6)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
foliage = image_material('M_Foliage', painted('ps_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
brick = principled('M_Brick', (0.22, 0.085, 0.05), 0.9)           # Philipsdorp: dark red brick
brick_light = principled('M_BrickLight', (0.36, 0.20, 0.12), 0.9)
plaster = principled('M_Plaster', (0.56, 0.54, 0.50), 0.9)
tiles = principled('M_Tiles', (0.22, 0.065, 0.035), 0.8)          # red-brown pantiles
tiles_dark = principled('M_TilesDark', (0.05, 0.05, 0.055), 0.7)
flat_roof = principled('M_FlatRoof', (0.13, 0.13, 0.135), 0.9)
office_wall = principled('M_OfficeWall', (0.48, 0.49, 0.50), 0.7)
platform_mat = principled('M_Platform', (0.40, 0.39, 0.37), 0.9)


# ================================================================ the pitch lines, the goals (as in the Jan Breydel script)
bm = bmesh.new()
Z = 0.02


def rect(x0, y0, x1, y1):
    bm.faces.new([bm.verts.new((x, y, Z)) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])


def hline(y, x0, x1): rect(x0, y - LINE / 2, x1, y + LINE / 2)
def vline(x, y0, y1): rect(x - LINE / 2, y0, x + LINE / 2, y1)


def arc(cx, cy, r, a0, a1, seg=48):
    ri, ro = r - LINE / 2, r + LINE / 2
    prev = None
    for i in range(seg + 1):
        a = a0 + (a1 - a0) * i / seg
        c, s = math.cos(a), math.sin(a)
        cur = (bm.verts.new((cx + ri * c, cy + ri * s, Z)), bm.verts.new((cx + ro * c, cy + ro * s, Z)))
        if prev:
            bm.faces.new((prev[0], prev[1], cur[1], cur[0]))
        prev = cur


def disc(cx, cy, r, seg=24):
    bm.faces.new([bm.verts.new((cx + r * math.cos(2 * math.pi * i / seg), cy + r * math.sin(2 * math.pi * i / seg), Z)) for i in range(seg)])


hx, hy, e = PW / 2, PL / 2, LINE / 2
hline(hy, -hx - e, hx + e); hline(-hy, -hx - e, hx + e)
vline(hx, -hy, hy); vline(-hx, -hy, hy); vline(0, -hy, hy)
arc(0, 0, 9.15, 0, 2 * math.pi, 96); disc(0, 0, 0.2)
for s in (-1, 1):
    gx = s * hx
    for depth, half in ((16.5, 20.16), (5.5, 9.16)):
        x = gx - s * depth
        vline(x, -half - e, half + e)
        hline(half, min(gx, x), max(gx, x)); hline(-half, min(gx, x), max(gx, x))
    spot = gx - s * 11
    disc(spot, 0, 0.2)
    a = math.acos((16.5 - 11) / 9.15)
    mid = math.pi if s > 0 else 0
    arc(spot, 0, 9.15, mid - a, mid + a, 32)
    for t in (-1, 1):
        a0 = {(1, 1): math.pi, (1, -1): math.pi / 2, (-1, 1): 1.5 * math.pi, (-1, -1): 0}[(s, t)]
        arc(gx, t * hy, 1.0, a0, a0 + math.pi / 2, 10)
lines = new_obj('Pitch_Lines', bm, '01_Pitch', [principled('M_Lines', (0.95, 0.95, 0.95), 0.6)])

# the nets: white cord, as on the photos; one picture covers 16 x 16 meshes (1.9 m)
NET_N = 16
net_tile = np.zeros((32 * NET_N, 32 * NET_N, 4), 'f')
net_tile[..., :3] = 0.92
_line = ((np.arange(32 * NET_N) % 32) < 3)
net_tile[_line, :, 3] = 1.0; net_tile[:, _line, 3] = 1.0
net_img = D.images.new('ps_net', 32 * NET_N, 32 * NET_N, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/ps_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
net_mat = alpha_material('M_Net', net_img, 0.8)
post_mat = principled('M_GoalPost', (0.92, 0.92, 0.92), 0.4)
GOAL_HW, GOAL_H, POST_R, MESH = 7.32 / 2, 2.44, 0.06, 0.12
bm = bmesh.new()
V = lambda x, y, z: Vector((x, y, z))
for s in (-1, 1):
    gx = s * hx
    for y in (-GOAL_HW, GOAL_HW):
        tube(bm, V(gx, y, 0), V(gx, y, GOAL_H + POST_R), POST_R, 0, 12)
        tube(bm, V(gx + s * 1.0, y, GOAL_H), V(gx + s * 2.0, y, 0.03), 0.025, 0)
        tube(bm, V(gx, y, 0.03), V(gx + s * 2.0, y, 0.03), 0.025, 0)
        tube(bm, V(gx, y, GOAL_H), V(gx + s * 1.0, y, GOAL_H), 0.025, 0)
    tube(bm, V(gx, -GOAL_HW - POST_R, GOAL_H), V(gx, GOAL_HW + POST_R, GOAL_H), POST_R, 0, 12)
    tube(bm, V(gx + s * 2.0, -GOAL_HW, 0.03), V(gx + s * 2.0, GOAL_HW, 0.03), 0.025, 0)
    m = 1.0 / MESH / NET_N
    w2 = 2 * GOAL_HW
    face(bm, [V(gx, -GOAL_HW, GOAL_H), V(gx + s, -GOAL_HW, GOAL_H), V(gx + s, GOAL_HW, GOAL_H), V(gx, GOAL_HW, GOAL_H)], None, 1,
         [(0, 0), (m, 0), (m, w2 * m), (0, w2 * m)])
    slope = math.hypot(1.0, GOAL_H) * m
    face(bm, [V(gx + s, -GOAL_HW, GOAL_H), V(gx + 2 * s, -GOAL_HW, 0), V(gx + 2 * s, GOAL_HW, 0), V(gx + s, GOAL_HW, GOAL_H)], None, 1,
         [(0, 0), (slope, 0), (slope, w2 * m), (0, w2 * m)])
    for y in (-GOAL_HW, GOAL_HW):
        face(bm, [V(gx, y, 0), V(gx, y, GOAL_H), V(gx + s, y, GOAL_H), V(gx + 2 * s, y, 0)], None, 1,
             [(0, 0), (0, GOAL_H * m), (m, GOAL_H * m), (2 * m, 0)])
goals = new_obj('StadiumGoals', bm, '01_Pitch', [post_mat, net_mat])

# the two floors the game sees: the pitch (grass, lines, up to the boards)
# and, under it, the ground inside the stands (the grass up to the boards,
# the walkway round them); each gets its own picture with the sun baked in
PITCH_X, PITCH_Y = 55.5, 36.6
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-PITCH_X, -PITCH_Y), (PITCH_X, -PITCH_Y), (PITCH_X, PITCH_Y), (-PITCH_X, PITCH_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.06, 0.20, 0.045), 0.85)])
FLOOR_Z = -0.05
FX0, FX1, FY0, FY1 = XE - 0.3, XW + 0.3, YN - 0.3, YS + 0.3
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
f = bm.faces.new([bm.verts.new((x, y, FLOOR_Z)) for x, y in ((FX0, FY0), (FX1, FY0), (FX1, FY1), (FX0, FY1))])
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.30, 0.30, 0.29), 0.9)])


# ================================================================ the stands
def mask_of(name):
    a = asset_pixels(name)[..., 0]
    return np.where(a > 0.8, 2, np.where(a > 0.3, 1, 0))       # 2 the letter, 1 its shadow


M_PHILIPS, M_OOST, M_PSV = mask_of('philips.png'), mask_of('oost.png'), mask_of('psv.png')
SEC_LONG = (2 * HX) / 9                    # the long sides' sections between the stairs: 13.49 m
SEC_END = (2 * HY) / 6                     # the ends': 11.98 m
LETTERS = {
    # side, tier: (mask, top row, the start of the word along the stand, a seat's width in the mask, the direction read from the pitch)
    ('N', 'up'): (M_PHILIPS, 15, 3.5 * SEC_LONG, SEC_LONG / 27, Vector((-1, 0, 0))),
    ('E', 'low'): (M_OOST, 11, CY0 - 2 * SEC_END, SEC_END / 24, Vector((0, 1, 0))),
    ('S', 'low'): (M_PSV, 12, -1.5 * SEC_LONG, SEC_LONG / 27, Vector((1, 0, 0))),
}


def letter_at(side, tier, row, p):
    spec = LETTERS.get((side, tier))
    if not spec:
        return 0
    m, top, start, sw, dirn = spec
    r = top - row
    if not 0 <= r < m.shape[0]:
        return 0
    along = (p.x * dirn.x + p.y * dirn.y) - (start * (dirn.x + dirn.y))
    c = int(math.floor(along / sw))
    if not 0 <= c < m.shape[1]:
        return 0
    return int(m[r, c])


def dugout(side, tier, row, p):
    return side == 'S' and tier == 'low' and row <= 3 and 2.6 < abs(p.x) < 13.5


def hole(side, tier, d, p):
    # the players' tunnel through the main stand's first rows
    return side == 'S' and tier == 'low' and d < 6.1 and abs(p.x) < 2.1


def no_seat(side, tier, d, p):
    # the tunnel, and the rows hidden behind the four screens in the second rings
    if hole(side, tier, d, p):
        return True
    return side in ('N', 'S') and tier == 'up' and 17.4 < d < 25.5 and any(abs(p.x - sx) < 4.4 for sx in (-SCR_X, SCR_X))


def seat_colour(side, tier, row, p, h):
    lt = letter_at(side, tier, row, p)
    if lt:
        if lt == 1:
            return BLACK_S
        return CREAM if side == 'N' else WHITE_S
    return RED if h % 5 else RED2


def seat_geo(bm, pa, pb, back, m, q, q1, cush=0.42, top=0.84, fwd=0.34):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(fwd, cush, 0), at(fwd, cush, 1), at(0.72, cush, 1), at(0.72, cush, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.72, cush, 0), at(0.72, cush, 1), at(0.78, top, 1), at(0.78, top, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
    face(bm, [at(0.78, top, 0), at(0.78, top, 1), at(0.84, top, 1), at(0.84, top, 0)], UPV, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])


SEAT_COUNT = [0]


def build_tier(name, rows, tier):
    steps, seats, stairs, rails = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    row_no = -1
    for k, (d0, d1, z, kind) in enumerate(rows):
        zp = rows[k - 1][2] if k else (z if tier == 'low' else FASCIA_Z1)
        white_riser = k > 0 and rows[k - 1][3] == 'walk' and tier == 'low' and k > 1 and kind == 'seat'
        if kind == 'seat':
            row_no += 1
        for i in range(NP):
            side = INFO[i][0]
            A0, A1, B0, B1 = P(i, 0, d0), P(i, 1, d0), P(i, 0, d1), P(i, 1, d1)
            L = (A1 - A0).length
            back = ((B0 + B1) / 2 - (A0 + A1) / 2).normalized()
            n = max(1, math.ceil(max(L, (B1 - B0).length) / 3.0))
            for s in range(n):
                t0, t1 = s / n, (s + 1) / n
                a0, a1, b0, b1 = A0.lerp(A1, t0), A0.lerp(A1, t1), B0.lerp(B1, t0), B0.lerp(B1, t1)
                mid = (a0 + a1 + b0 + b1) / 4
                if hole(side, tier, d0, mid):
                    continue
                face(steps, [(a0.x, a0.y, z), (a1.x, a1.y, z), (b1.x, b1.y, z), (b0.x, b0.y, z)], UPV, 0)
                if z > zp + 0.01:
                    face(steps, [(a0.x, a0.y, zp), (a1.x, a1.y, zp), (a1.x, a1.y, z), (a0.x, a0.y, z)], -back, 2 if white_riser else 1)
            if kind not in ('seat', 'biz'):
                continue
            # the stairs at the ends of the piece: a half step on the back
            # half of each tread, light concrete
            cut0 = AISLE_W / 2 if (kind == 'seat' and is_aisle(i) and L > 2.4) else 0.0
            cut1 = AISLE_W / 2 if (kind == 'seat' and is_aisle(i + 1) and L > 2.4) else 0.0
            rise = z - zp
            for u0, u1 in ([(0.0, cut0 / L)] if cut0 else []) + ([(1 - cut1 / L, 1.0)] if cut1 else []):
                f0, f1, g0, g1 = A0.lerp(A1, u0), A0.lerp(A1, u1), B0.lerp(B1, u0), B0.lerp(B1, u1)
                if hole(side, tier, d0, (f0 + f1 + g0 + g1) / 4):
                    continue
                m0, m1 = f0.lerp(g0, 0.5), f1.lerp(g1, 0.5)
                F0, F1, G0, G1, M0, M1 = (Vector((v_.x, v_.y, z)) + lift for v_ in (f0, f1, g0, g1, m0, m1))
                face(stairs, [F0, F1, M1, M0], UPV, 0)
                hs = Vector((0, 0, min(0.2, rise / 2) if rise > 0.05 else 0.0))
                face(stairs, [M0 + hs, M1 + hs, G1 + hs, G0 + hs], UPV, 0)
                if hs.z > 0:
                    face(stairs, [M0, M1, M1 + hs, M0 + hs], -back, 1)
            # the seats
            c0, c1 = cut0 / L, 1 - cut1 / L
            usable = (c1 - c0) * L
            sw = 0.56 if kind == 'biz' else SEAT_W
            if usable < sw:
                continue
            nseat = int(usable / sw)
            pad = (usable - nseat * sw) / 2 / L
            mats = []
            for q in range(nseat):
                u = c0 + pad + (q + 0.5) * sw / L
                p = A0.lerp(A1, u).lerp(B0.lerp(B1, u), 0.5)
                if no_seat(side, tier, d0, p):
                    mats.append(None)
                    continue
                if kind == 'biz':
                    mats.append(BIZ if is_straight(i) else RED)
                elif dugout(side, tier, row_no, p):
                    mats.append(DUG)
                else:
                    h = (row_no * 73856093) ^ (i * 19349663) ^ ((q // 3) * 83492791)
                    mats.append(seat_colour(side, tier, row_no, p, h))
            q = 0
            while q < nseat:
                m = mats[q]
                if m is None:
                    q += 1
                    continue
                q1 = q + 2 if q + 1 < nseat and mats[q + 1] == m and m != DUG else q + 1
                us = [c0 + pad + qq * sw / L for qq in (q, q1)]
                pa = [A0.lerp(A1, uu) + Vector((0, 0, z)) for uu in us]
                pb = [B0.lerp(B1, uu) + Vector((0, 0, z)) for uu in us]
                if m == DUG:
                    seat_geo(seats, pa, pb, back, m, q, q1, cush=0.5, top=1.25, fwd=0.2)
                elif kind == 'biz':
                    seat_geo(seats, pa, pb, back, m, q, q1, cush=0.46, top=0.98, fwd=0.3)
                else:
                    seat_geo(seats, pa, pb, back, m, q, q1)
                SEAT_COUNT[0] += q1 - q
                q = q1
            # safe standing in the east end's first ring: a rail along every row
            if side == 'E' and tier == 'low' and kind == 'seat':
                ra, rb = A0.lerp(B0, 0.9) + Vector((0, 0, z + 1.0)), A1.lerp(B1, 0.9) + Vector((0, 0, z + 1.0))
                tube(rails, ra.lerp(rb, c0), ra.lerp(rb, c1), 0.025, 0, 5, step=6.0)
    # the handrails up the middle of every stairway of the straights
    for i in range(NP):
        if not (is_aisle(i) and is_straight(i) and is_straight(i - 1)):
            continue
        seat_rows = [r for r in rows if r[3] == 'seat']
        blocks = [seat_rows] if tier == 'up' else [seat_rows[:13], seat_rows[13:]]
        for blk in blocks:
            if len(blk) < 3:
                continue
            ra, rb = blk[1], blk[-1]
            pa_, pb_ = P(i, 0, (ra[0] + ra[1]) / 2), P(i, 0, (rb[0] + rb[1]) / 2)
            if hole(INFO[i][0], tier, ra[0], pa_):
                continue
            tube(rails, pa_ + Vector((0, 0, ra[2] + 0.95)), pb_ + Vector((0, 0, rb[2] + 0.95)), 0.03, 0, 6, step=3.0)
            for r_ in blk[1::4]:
                pp = P(i, 0, (r_[0] + r_[1]) / 2)
                tube(rails, pp + Vector((0, 0, r_[2])), pp + Vector((0, 0, r_[2] + 0.95)), 0.025, 0, 5)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark, white_paint])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Stairs_' + name, stairs, '02_Bowl', [concrete_light, concrete_dark])
    new_obj('Rails_' + name, rails, '02_Bowl', [galv])


t0 = time.time()
build_tier('Lower', LOW_ROWS, 'low')
build_tier('Upper', UP_ROWS, 'up')
print('STANDS %.0fs, %d seats' % (time.time() - t0, SEAT_COUNT[0]))

# the wall round the pitch; the lounges' glass under the second ring (the
# corners: a plain wall); the front of the second ring: white, the LED band,
# white, its underside; the back wall over the last row
bm = bmesh.new()
tunnel_piece = lambda i: INFO[i][0] == 'S' and INFO[i][1] in (N_LONG // 2 - 1, N_LONG // 2)
ring(bm, 0.0, 0.0, 0.0, WALL_Z, 0, want='in', keep=lambda i: not tunnel_piece(i))
for i in range(NP):
    if tunnel_piece(i):
        a_, b_ = P(i, 0, 0.0), P(i, 1, 0.0)
        xs_ = sorted([a_.x, b_.x])
        for xa, xb in ((xs_[0], -2.1), (2.1, xs_[1])):
            if xb > xa:
                face(bm, [(xa, YS, 0.0), (xb, YS, 0.0), (xb, YS, WALL_Z), (xa, YS, WALL_Z)], Vector((0, -1, 0)), 0)
ring(bm, GLASS_D, LOW_ROWS[-1][2], GLASS_D, FASCIA_Z0 + 0.3, 3, want='in', keep=is_straight, u_len=6.0)
ring(bm, GLASS_D, LOW_ROWS[-1][2], GLASS_D, FASCIA_Z0 + 0.3, 1, want='in', keep=is_corner)
ring(bm, BAL_D, FASCIA_Z0, BAL_D, FASCIA_Z0 + 0.15, 2, want='in')
ring(bm, BAL_D, FASCIA_Z0 + 0.15, BAL_D, FASCIA_Z0 + 1.05, 4, want='in', u_len=-48.0)      # u against the path: the words read from the pitch
ring(bm, BAL_D, FASCIA_Z0 + 1.05, BAL_D, FASCIA_Z1, 2, want='in')
ring(bm, BAL_D, FASCIA_Z1, UP_ROWS[0][0], FASCIA_Z1, 2, want='up')
ring(bm, BAL_D, FASCIA_Z0, GLASS_D, FASCIA_Z0 + 0.3, 2, want='down')
ring(bm, BACK_D, UP_TOP, BACK_D, roof_under(BACK_D), 1, want='in', zstep=1.5)
new_obj('Fronts', bm, '02_Bowl', [concrete_light, concrete, white_paint, glazing, band_mat])

# the glass balustrade on the front of the second ring: posts and a top rail
bm = bmesh.new()
cum = cumlen(BAL_D + 0.05)
for i in range(NP):
    a_, b_ = P(i, 0, BAL_D + 0.05), P(i, 1, BAL_D + 0.05)
    tube(bm, a_ + Vector((0, 0, FASCIA_Z1 + 1.0)), b_ + Vector((0, 0, FASCIA_Z1 + 1.0)), 0.035, 0, 6, step=3.5)
    L = (b_ - a_).length
    for j in range(max(1, int(L / 1.6))):
        p = a_.lerp(b_, j / max(1, int(L / 1.6)))
        tube(bm, p + Vector((0, 0, FASCIA_Z1)), p + Vector((0, 0, FASCIA_Z1 + 1.0)), 0.02, 0, 4)
new_obj('Balustrade', bm, '02_Bowl', [galv])

# the business level's partitions: white walls every second piece of the straights
bm = bmesh.new()
for i in range(NP):
    if not (is_straight(i) and is_straight(i - 1)) or INFO[i][1] % 2:
        continue
    out = NODES[i][1]
    tg = Vector((-out.y, out.x, 0))
    a_, b_ = P(i, 0, 16.6), P(i, 0, GLASS_D)
    box(bm, (a_ + b_) / 2, out, (GLASS_D - 16.6) / 2, tg, 0.12, LOW_ROWS[-3][2], FASCIA_Z0, 0)
new_obj('Partitions', bm, '02_Bowl', [white_paint])

# ---------------------------------------------------------------- the tunnel and the dugouts in the main stand
bm = bmesh.new()
for sx in (-1, 1):
    x_ = sx * 2.1
    # its red side, stepping up with the rows, the crest and 1913 on it
    for k in range(1, 8):
        d0, d1, z = LOW_ROWS[k][0], LOW_ROWS[k][1], LOW_ROWS[k][2]
        u0, u1 = d0 / 6.1, min(1.0, d1 / 6.1)
        face(bm, [(x_, YS + d0, 0.0), (x_, YS + d1, 0.0), (x_, YS + d1, z), (x_, YS + d0, z)], Vector((-sx, 0, 0)), 0,
             [(u0 if sx < 0 else 1 - u0, 0), (u1 if sx < 0 else 1 - u1, 0), (u1 if sx < 0 else 1 - u1, z / 4.4), (u0 if sx < 0 else 1 - u0, z / 4.4)])
    face(bm, [(x_, YS, 0.0), (x_, YS, WALL_Z), (x_, YS + 0.5, WALL_Z), (x_, YS + 0.5, 0.0)], Vector((-sx, 0, 0)), 0, [(0, 0), (0, 0.25), (0.08, 0.25), (0.08, 0)])
face(bm, [(-2.1, YS + 6.1, 0.0), (2.1, YS + 6.1, 0.0), (2.1, YS + 6.1, LOW_ROWS[8][2]), (-2.1, YS + 6.1, LOW_ROWS[8][2])], Vector((0, -1, 0)), 1)
face(bm, [(-2.1, YS, 0.01), (2.1, YS, 0.01), (2.1, YS + 6.1, 0.01), (-2.1, YS + 6.1, 0.01)], UPV, 2)
new_obj('Tunnel', bm, '02_Bowl', [tunnel_mat, portal, concrete_dark])

# ---------------------------------------------------------------- the four screens, at the ends of both long stands' second rings
# a black box on the second ring, its face the live screen (game.screen.js,
# style 'philips'), seen from the pitch the left edge of each picture on the left
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
bm, fb = bmesh.new(), bmesh.new()
for side, ny in (('N', -1), ('S', 1)):
    yf = (YN if side == 'N' else YS) + ny * SCR_DF
    nrm = Vector((0, -ny, 0))                     # it faces the pitch
    right = Vector((ny, 0, 0))                    # the viewer's right
    for sx in (-SCR_X, SCR_X):
        c = Vector((sx, yf, SCR_Z0 + SCR_H / 2))
        hb = c - nrm * 0.35
        obox(bm, hb, nrm, right, UPV, 0.35, SCR_W / 2 + 0.2, SCR_H / 2 + 0.2, 0)
        # its legs down to the treads
        for lx in (-1, 1):
            for dd in (0.0, 1.6, 3.2):
                p = hb + right * lx * (SCR_W / 2 - 0.4) - nrm * (0.3 + dd)
                k = int(max(0, (abs(p.y - (YN if side == 'N' else YS)) - 17.0) / 0.8))
                zt = UP_ROWS[min(k, len(UP_ROWS) - 2)][2]
                tube(bm, Vector((p.x, p.y, zt)), Vector((p.x, p.y, c.z - SCR_H / 2 - 0.2)), 0.07, 1, 6)
        c0 = c + nrm * 0.02
        face(fb, [c0 - right * SCR_W / 2 - UPV * SCR_H / 2, c0 + right * SCR_W / 2 - UPV * SCR_H / 2,
                  c0 + right * SCR_W / 2 + UPV * SCR_H / 2, c0 - right * SCR_W / 2 + UPV * SCR_H / 2], nrm, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
new_obj('Screen_Frames', bm, '04_Roof', [steel_dark, steel_grey])
screen_face = new_obj('ScreenFace_0', fb, '04_Roof', [live])

# ---------------------------------------------------------------- the away section: the north-west corner's second ring
# tall fences up both its sides and along its front, a dark net from the
# front of the second ring up to the roof's girder (as on the photo from it)
i_aw0, i_aw1 = SIDE_RANGE['cNW']
bm = bmesh.new()


def fence(pa, pb, za, zb, h=2.6, every=2.2, mesh=True):
    L = (pb - pa).length
    n = max(1, math.ceil(L / every))
    for k in range(n + 1):
        q = pa.lerp(pb, k / n); zq = za + (zb - za) * k / n
        tube(bm, Vector((q.x, q.y, zq)), Vector((q.x, q.y, zq + h)), 0.05, 0, 5)
    for hh in (0.9, h):
        tube(bm, Vector((pa.x, pa.y, za + hh)), Vector((pb.x, pb.y, zb + hh)), 0.04, 0, 5, step=3.0)
    if mesh:
        m = max(1, int(L / 0.3))
        for k in range(m):
            q = pa.lerp(pb, (k + 0.5) / m); zq = za + (zb - za) * (k + 0.5) / m
            tube(bm, Vector((q.x, q.y, zq + 0.1)), Vector((q.x, q.y, zq + h)), 0.012, 0, 3, step=4.0)


for i in (i_aw0, i_aw1):
    for k in range(len(UP_ROWS) - 1):
        d0, d1, z, _ = UP_ROWS[k]
        fence(P(i, 0, d0), P(i, 0, d1), z, z, h=2.6, every=0.8, mesh=False)
new_obj('Away_Fences', bm, '02_Bowl', [galv])
NET2 = 64
dn = np.zeros((NET2, NET2, 4), 'f'); dn[..., :3] = 0.03
dl = (np.arange(NET2) % 16) < 2
dn[dl, :, 3] = 0.9; dn[:, dl, 3] = 0.9
dimg = D.images.new('ps_awaynet', NET2, NET2, alpha=True)
dimg.pixels.foreach_set(dn.ravel())
dimg.filepath_raw = TEX_DIR + '/ps_awaynet.png'; dimg.file_format = 'PNG'; dimg.save(); dimg.pack()
away_net = alpha_material('M_AwayNet', dimg, 0.9)
bm = bmesh.new()
for i in range(i_aw0, i_aw1):
    a_, b_ = P(i, 0, BAL_D + 0.1), P(i, 1, BAL_D + 0.1)
    L = (b_ - a_).length
    for zz in range(4):
        za, zb = FASCIA_Z1 + (GIRDER_Z0 - FASCIA_Z1) * zz / 4, FASCIA_Z1 + (GIRDER_Z0 - FASCIA_Z1) * (zz + 1) / 4
        face(bm, [(a_.x, a_.y, za), (b_.x, b_.y, za), (b_.x, b_.y, zb), (a_.x, a_.y, zb)], -NODES[i][1], 0,
             [(0, za / 0.5), (L / 0.5, za / 0.5), (L / 0.5, zb / 0.5), (0, zb / 0.5)])
new_obj('Away_Net', bm, '02_Bowl', [away_net])


# ================================================================ the roofs
# the deep white girder right round the front; the sheeting behind it: the
# north stand pale with white trusses on top, the main stand glass on white
# trusses under it, the ends white on trusses; the corners domed over the pods
bm = bmesh.new()
ring(bm, ROOF_D0, GIRDER_Z0, ROOF_D0, GIRDER_Z1, 0, want='in')
ring(bm, ROOF_D0, GIRDER_Z0, GIRDER_D, GIRDER_Z0, 0, want='down')
ring(bm, ROOF_D0, GIRDER_Z1, GIRDER_D, GIRDER_Z1, 0, want='up')
ring(bm, GIRDER_D, GIRDER_Z0, GIRDER_D, roof_under(GIRDER_D), 0, want='out')
new_obj('Roof_Girder', bm, '04_Roof', [fascia_white])

BANDS = [GIRDER_D, 6.0, 12.0, 18.0, 24.0, 30.0, ROOF_D1]
top_n, top_s, top_e, under, domes, eave = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
cum1 = cumlen(GIRDER_D)
for i in range(NP):
    side = INFO[i][0]
    corner = is_corner(i)
    nsub = 4 if corner else max(1, math.ceil((P(i, 1, ROOF_D1) - P(i, 0, ROOF_D1)).length / 3.0))
    for s in range(nsub):
        t0, t1 = s / nsub, (s + 1) / nsub
        if corner:
            ta, tb = corner_t(i, t0), corner_t(i, t1)
            dts = [GIRDER_D] + [GIRDER_D + (pod_top(0.5 * (ta + tb))[1] - GIRDER_D) * j / 8 for j in range(1, 8)]
            da_end, db_end = pod_top(ta)[1], pod_top(tb)[1]
            for j in range(8):
                fa, fb_ = j / 8, (j + 1) / 8
                pa0 = P(i, t0, GIRDER_D + (da_end - GIRDER_D) * fa); pa1 = P(i, t1, GIRDER_D + (db_end - GIRDER_D) * fa)
                pb0 = P(i, t0, GIRDER_D + (da_end - GIRDER_D) * fb_); pb1 = P(i, t1, GIRDER_D + (db_end - GIRDER_D) * fb_)
                za0 = dome_z(GIRDER_D + (da_end - GIRDER_D) * fa, ta); za1 = dome_z(GIRDER_D + (db_end - GIRDER_D) * fa, tb)
                zb0 = dome_z(GIRDER_D + (da_end - GIRDER_D) * fb_, ta); zb1 = dome_z(GIRDER_D + (db_end - GIRDER_D) * fb_, tb)
                face(domes, [(pa0.x, pa0.y, za0), (pa1.x, pa1.y, za1), (pb1.x, pb1.y, zb1), (pb0.x, pb0.y, zb0)], UPV, 0)
                face(domes, [(pa0.x, pa0.y, za0 - 0.4), (pa1.x, pa1.y, za1 - 0.4), (pb1.x, pb1.y, zb1 - 0.4), (pb0.x, pb0.y, zb0 - 0.4)], -UPV, 1)
            continue
        for b in range(len(BANDS) - 1):
            da, db = BANDS[b], BANDS[b + 1]
            p0, p1, q0, q1 = P(i, t0, da), P(i, t1, da), P(i, t0, db), P(i, t1, db)
            pts = lambda za, zb: [(p0.x, p0.y, za), (p1.x, p1.y, za), (q1.x, q1.y, zb), (q0.x, q0.y, zb)]
            L1 = cum1[i] + (cum1[i + 1] - cum1[i]) * t0, cum1[i] + (cum1[i + 1] - cum1[i]) * t1
            uvs = [(L1[0] / 6.0, da / 6.0), (L1[1] / 6.0, da / 6.0), (L1[1] / 6.0, db / 6.0), (L1[0] / 6.0, db / 6.0)]
            tgt = top_n if side == 'N' else top_s if side == 'S' else top_e
            face(tgt, pts(roof_top(da), roof_top(db)), UPV, 0, uvs)
            uvu = [(L1[0] / 4.0, 0), (L1[1] / 4.0, 0), (L1[1] / 4.0, 1), (L1[0] / 4.0, 1)]
            face(under, pts(roof_under(da), roof_under(db)), -UPV, 1 if side == 'S' else 0, uvs if side == 'S' else uvu)
        # the eave over the back wall, white
        e0, e1 = P(i, t0, ROOF_D1), P(i, t1, ROOF_D1)
        out = (NODES[i][1] + NODES[i + 1][1]).normalized()
        face(eave, [(e0.x, e0.y, roof_under(ROOF_D1) - 0.4), (e1.x, e1.y, roof_under(ROOF_D1) - 0.4),
                    (e1.x, e1.y, roof_top(ROOF_D1)), (e0.x, e0.y, roof_top(ROOF_D1))], out, 0)
new_obj('Roof_North', top_n, '04_Roof', [sheet_mat])
new_obj('Roof_Main', top_s, '04_Roof', [glass_roof])
new_obj('Roof_Ends', top_e, '04_Roof', [roof_white])
new_obj('Roof_Under', under, '04_Roof', [roof_under_mat, glass_under])
new_obj('Roof_Domes', domes, '04_Roof', [pod_metal, roof_under_mat])
new_obj('Roof_Eaves', eave, '04_Roof', [fascia_white])


# the trusses: over the north stand standing on its sheeting, rising to a
# peak over its back and down its back wall; under the others, fish-bellied
def truss(bm, top, bot, r_chord=0.13, r_web=0.07):
    # a planar Warren truss between two polylines of the same number of points
    for pts in (top, bot):
        for a_, b_ in zip(pts, pts[1:]):
            tube(bm, a_, b_, r_chord, 0, 6, step=3.0)
    for k in range(len(top) - 1):
        tube(bm, bot[k], top[k + 1] if k % 2 == 0 else top[k], r_web, 0, 5, step=3.0)
        tube(bm, top[k + 1] if k % 2 == 0 else top[k], bot[k + 1], r_web, 0, 5, step=3.0)


def lerp_path(pts, n):
    # n + 1 points evenly along a polyline of (d, z)
    segs = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    tot = sum(segs)
    out = []
    for k in range(n + 1):
        s = tot * k / n
        for (a, b), L in zip(zip(pts, pts[1:]), segs):
            if s <= L + 1e-9:
                f_ = s / L if L else 0
                out.append((a[0] + (b[0] - a[0]) * f_, a[1] + (b[1] - a[1]) * f_))
                break
            s -= L
    return out


bm = bmesh.new()
i0, i1 = SIDE_RANGE['N']
N_TOP = lerp_path([(ROOF_D0 + 0.4, GIRDER_Z1 + 0.8), (29.0, 34.2), (37.6, 21.0), (36.6, 13.4)], 18)
N_BOT = lerp_path([(GIRDER_D, roof_top(GIRDER_D) + 0.1), (26.5, roof_top(26.5) + 0.1), (ROOF_D1, roof_top(ROOF_D1) + 0.1), (34.6, 21.0), (33.8, 13.4)], 18)
for i in range(i0, i1 + 1):
    base_ = NODES[i][0]; out = NODES[i][1]
    to3 = lambda dz: Vector((base_.x + out.x * dz[0], base_.y + out.y * dz[0], dz[1]))
    truss(bm, [to3(q) for q in N_TOP], [to3(q) for q in N_BOT], 0.2, 0.1)
    if i < i1:
        nb_ = NODES[i + 1][0]
        for q in (N_TOP[0], N_TOP[7], N_TOP[10]):
            tube(bm, to3(q), Vector((nb_.x + out.x * q[0], nb_.y + out.y * q[0], q[1])), 0.09, 0, 5, step=3.5)
for side in ('S', 'E', 'W'):
    i0, i1 = SIDE_RANGE[side]
    for i in range(i0, i1 + 1):
        if side != 'S' and (i - i0) % 2:
            continue
        base_ = NODES[i][0]; out = NODES[i][1]
        to3 = lambda dz: Vector((base_.x + out.x * dz[0], base_.y + out.y * dz[0], dz[1]))
        top_ = lerp_path([(GIRDER_D, roof_under(GIRDER_D) - 0.1), (BACK_D, roof_under(BACK_D) - 0.1)], 10)
        bot_ = [(d_, roof_under(d_) - 0.1 - 2.4 * math.sin(math.pi * (d_ - GIRDER_D) / (BACK_D - GIRDER_D))) for d_, _ in top_]
        truss(bm, [to3(q) for q in top_], [to3(q) for q in bot_], 0.11, 0.06)
new_obj('Roof_Trusses', bm, '04_Roof', [truss_white])

# the floodlights: clusters on top of the girder, aimed at the pitch
bm = bmesh.new()
cum_l = cumlen(ROOF_D0 + 0.8)


def lamp_cluster(i, u, n=7, gap=0.8):
    p = P(i, u, ROOF_D0 + 0.8)
    out = (NODES[i][1] + NODES[i + 1][1]).normalized()
    tg = Vector((-out.y, out.x, 0))
    zb = GIRDER_Z1
    tube(bm, p - tg * (n * gap / 2) + Vector((0, 0, zb + 0.9)), p + tg * (n * gap / 2) + Vector((0, 0, zb + 0.9)), 0.07, 0, 6)
    for lx in (-1, 1):
        q = p + tg * lx * (n * gap / 2 - 0.2)
        tube(bm, q + Vector((0, 0, zb)), q + Vector((0, 0, zb + 0.9)), 0.06, 0, 5)
    fwd = (-out * math.cos(math.radians(40)) - UPV * math.sin(math.radians(40))).normalized()
    upl = tg.cross(fwd).normalized()
    if upl.z < 0:
        upl = -upl
    for k in range(n):
        c = p + tg * ((k + 0.5) * gap - n * gap / 2) + Vector((0, 0, zb + 1.25)) - out * 0.15
        obox(bm, c, fwd, tg, upl, 0.2, 0.3, 0.26, 0)
        cc = c + fwd * 0.21
        face(bm, [cc - tg * 0.26 - upl * 0.2, cc + tg * 0.26 - upl * 0.2, cc + tg * 0.26 + upl * 0.2, cc - tg * 0.26 + upl * 0.2], fwd, 1)


for side, count in (('N', 8), ('S', 8), ('W', 4), ('E', 4)):
    i0, i1 = SIDE_RANGE[side]
    for k in range(count):
        s_ = (k + 0.5) / count * (i1 - i0)
        i = i0 + int(s_)
        lamp_cluster(i, s_ - int(s_))
new_obj('Floodlights', bm, '04_Roof', [lamp, lamp_glass])


# ================================================================ the corner pods
# the corners' second rings in shells of louvres, bulging out over the
# offices, their bottoms rising towards the pylons, a rounded rim and the dome
bm = bmesh.new()
for c_side in CORNERS:
    i0, i1 = SIDE_RANGE[c_side]
    cum_c = cumlen(36.0)
    for i in range(i0, i1):
        for s in range(3):
            u0, u1 = s / 3, (s + 1) / 3
            ta, tb = corner_t(i, u0), corner_t(i, u1)
            for j in range(len(POD_PROFILE) - 1):
                (da0, za0), (db0, zb0) = pod_point(ta, j), pod_point(ta, j + 1)
                (da1, za1), (db1, zb1) = pod_point(tb, j), pod_point(tb, j + 1)
                pa0, pb0 = P(i, u0, da0), P(i, u0, db0)
                pa1, pb1 = P(i, u1, da1), P(i, u1, db1)
                out = (NODES[i][1] + NODES[i + 1][1]).normalized()
                rim = j >= len(POD_PROFILE) - 4
                L0 = (cum_c[i] + (cum_c[i + 1] - cum_c[i]) * u0) / 8.0
                L1 = (cum_c[i] + (cum_c[i + 1] - cum_c[i]) * u1) / 8.0
                uvs = [(L0, j / 6.0), (L1, j / 6.0), (L1, (j + 1) / 6.0), (L0, (j + 1) / 6.0)]
                face(bm, [(pa0.x, pa0.y, za0), (pa1.x, pa1.y, za1), (pb1.x, pb1.y, zb1), (pb0.x, pb0.y, zb0)], out + UPV * (1.5 if rim else 0.0),
                     1 if rim else 0, None if rim else uvs)
            # its underside: from the bottom of the shell in to the back wall
            (da0, za0), (da1, za1) = pod_point(ta, 0), pod_point(tb, 0)
            pa0, pa1 = P(i, u0, da0), P(i, u1, da1)
            qa0, qa1 = P(i, u0, BACK_D - 4.0), P(i, u1, BACK_D - 4.0)
            face(bm, [(pa0.x, pa0.y, za0), (pa1.x, pa1.y, za1), (qa1.x, qa1.y, za1), (qa0.x, qa0.y, za0)], -UPV, 2)
new_obj('Pods', bm, '05_Outside', [louvres, pod_metal, steel_dark])


# ================================================================ the pylons and their cables
# two at each pod, where it meets the straight stands, just outside the
# offices (OSM), 46 m tall: a tapering white blade with a sharp edge outward,
# leaning out a little; two cables from the top down to the pod's rim
def outline_dist(x, y):
    best = 1e9
    n = len(OUTLINE)
    for k in range(n):
        (ax, ay), (bx, by) = OUTLINE[k], OUTLINE[(k + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


PYLONS = []
for c_side in CORNERS:
    i0, i1 = SIDE_RANGE[c_side]
    for i, t_end in ((i0, 0.0), (i1 % NP, 1.0)):
        nrm = NODES[i][1]
        d = BACK_D + 2.0
        while inside_poly(P(i, 0, d).x, P(i, 0, d).y, OUTLINE) or outline_dist(P(i, 0, d).x, P(i, 0, d).y) < 2.2:
            d += 0.5
        PYLONS.append((P(i, 0, d), nrm, c_side, t_end))
bm, cb = bmesh.new(), bmesh.new()
for base_, nrm, c_side, t_end in PYLONS:
    tg = Vector((-nrm.y, nrm.x, 0))
    lean = nrm * 2.2
    n_seg = 12
    rings_ = []
    for k in range(n_seg + 1):
        f_ = k / n_seg
        z = PYLON_H * f_
        w_ = 2.1 * (1 - f_) + 0.45 * f_           # half the width along the stand
        dp = 2.8 * (1 - f_) + 0.7 * f_             # the depth, edge outward
        c = base_ + lean * f_ ** 1.6 + Vector((0, 0, z))
        rings_.append([c + nrm * dp * 0.6, c - nrm * dp * 0.4 + tg * w_, c - nrm * dp * 0.4 - tg * w_])
    ctr = lambda r: (r[0] + r[1] + r[2]) / 3
    for k in range(n_seg):
        for j in range(3):
            q = [rings_[k][j], rings_[k][(j + 1) % 3], rings_[k + 1][(j + 1) % 3], rings_[k + 1][j]]
            out_ = (q[0] + q[1] + q[2] + q[3]) / 4 - (ctr(rings_[k]) + ctr(rings_[k + 1])) / 2
            face(bm, q, out_, 0)
    tip = base_ + lean + Vector((0, 0, PYLON_H + 2.5))
    for j in range(3):
        q = [rings_[-1][j], rings_[-1][(j + 1) % 3], tip]
        face(bm, q, (q[0] + q[1]) / 2 - ctr(rings_[-1]) + UPV * 0.3, 0)
    face(bm, rings_[0], -UPV, 0)
    # the cables to the rim of the pod
    i0, i1 = SIDE_RANGE[c_side]
    top = base_ + lean * 0.98 + Vector((0, 0, PYLON_H - 1.5))
    for tc in ((0.16, 0.30) if t_end == 0.0 else (0.84, 0.70)):
        pos = tc * (i1 - i0)
        ii = i0 + min(i1 - i0 - 1, int(pos))
        zt, dt = pod_top(tc)
        rp = P(ii, pos - int(pos), dt - 0.6)
        tube(cb, top, Vector((rp.x, rp.y, zt + 0.1)), 0.06, 0, 5, step=4.0)
new_obj('Pylons', bm, '05_Outside', [pylon_mat])
new_obj('Cables', cb, '05_Outside', [cable_mat])


# ================================================================ round the pitch: the LED boards
bm = bmesh.new()
BH = 0.9


def board_run(a, b, nrm, u0):
    # a row of boards from a to b, facing nrm; u runs with the reading direction
    L = (b - a).length
    n = max(1, math.ceil(L / 4.0))
    o = nrm * 0.15
    for k in range(n):
        p0, p1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        ua, ub = (u0 + L * k / n) / 48.0, (u0 + L * (k + 1) / n) / 48.0
        face(bm, [p0 + o, p1 + o, p1 + o + Vector((0, 0, BH)), p0 + o + Vector((0, 0, BH))], nrm, 0, [(ua, 0), (ub, 0), (ub, 1), (ua, 1)])
        face(bm, [p0 - o, p1 - o, p1 - o + Vector((0, 0, BH)), p0 - o + Vector((0, 0, BH))], -nrm, 1)
        face(bm, [p0 - o + Vector((0, 0, BH)), p1 - o + Vector((0, 0, BH)), p1 + o + Vector((0, 0, BH)), p0 + o + Vector((0, 0, BH))], UPV, 1)
    return u0 + L


u = 0.0
u = board_run(V(BOARD_X - 1.0, -BOARD_Y, 0), V(-BOARD_X + 1.0, -BOARD_Y, 0), V(0, 1, 0), u)          # the north side, read from the pitch: west to east
u = board_run(V(-BOARD_X, -BOARD_Y + 1.0, 0), V(-BOARD_X, BOARD_Y - 1.0, 0), V(1, 0, 0), u)         # the east end
u = board_run(V(BOARD_X, BOARD_Y - 1.0, 0), V(BOARD_X, -BOARD_Y + 1.0, 0), V(-1, 0, 0), u)          # the west end
u = board_run(V(-BOARD_X + 1.0, BOARD_Y, 0), V(-15.0, BOARD_Y, 0), V(0, -1, 0), u)                  # the main stand's side, either side of the dugouts
u = board_run(V(15.0, BOARD_Y, 0), V(BOARD_X - 1.0, BOARD_Y, 0), V(0, -1, 0), u)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_dark])

# the photographers' and the TV's spots behind the goals: low benches and cameras
bm = bmesh.new()
for sx in (-1, 1):
    for y_ in (-24.0, -15.0, 15.0, 24.0):
        x_ = sx * (BOARD_X + 2.4)
        box(bm, (x_, y_), (1, 0), 0.35, (0, 1), 0.6, 0.0, 0.5, 0)
        tube(bm, Vector((x_, y_ + 0.4, 0.0)), Vector((x_, y_ + 0.4, 1.4)), 0.03, 1, 5)
        box(bm, (x_, y_ + 0.4), (1, 0), 0.3, (0, 1), 0.14, 1.4, 1.65, 0)
new_obj('Pitchside', bm, '02_Bowl', [steel_dark, steel_grey])


# ================================================================ outside: the back walls, the offices, the pods' feet
# the second ring's back wall seen from outside, white panels and a band of
# windows a floor, from the offices' roof up to the eave
bm = bmesh.new()
OUT_D = BACK_D + 0.2
ring(bm, OUT_D, BASE_H, OUT_D, roof_under(OUT_D) - 0.4, 0, want='out', zstep=3.6, u_len=12.0, v=(0, (roof_under(OUT_D) - 0.4 - BASE_H) / 3.6), keep=is_straight)
ring(bm, OUT_D, BASE_H + 3.0, OUT_D, roof_under(OUT_D) - 0.4, 1, want='out', zstep=3.0, keep=is_corner)
new_obj('Back_Walls', bm, '05_Outside', [facade_mat, concrete_dark])

# the offices round the ground (the stadium's outline in OSM): the ground
# floor's glass between red columns, white panels and windows over it; the
# north side's round red stair towers; a parapet on top
bm = bmesh.new()
n_o = len(OUTLINE)
sarea = sum(OUTLINE[k][0] * OUTLINE[(k + 1) % n_o][1] - OUTLINE[(k + 1) % n_o][0] * OUTLINE[k][1] for k in range(n_o))
ucum = 0.0
for k in range(n_o):
    a_, c_ = OUTLINE[k], OUTLINE[(k + 1) % n_o]
    L = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
    if L < 0.05:
        continue
    outv = Vector((c_[1] - a_[1], -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
    tower = a_[1] < -69.8 and c_[1] < -69.8 and abs(a_[0]) < 70        # the round stair towers on the north side
    for za, zb, mat, v0, v1 in ((0.0, 4.2, 1, 0.0, 1.0), (4.2, 8.35, 0, 0.0, 1.15), (8.35, BASE_H, 0, 0.0, 1.15)):
        face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, 3 if tower else mat,
             None if tower else [(ucum / 12.0, v0), ((ucum + L) / 12.0, v0), ((ucum + L) / 12.0, v1), (ucum / 12.0, v1)])
    face(bm, [(a_[0], a_[1], BASE_H), (c_[0], c_[1], BASE_H), (c_[0], c_[1], BASE_H + 0.7), (a_[0], a_[1], BASE_H + 0.7)], outv, 2)
    ucum += L
new_obj('Offices', bm, '05_Outside', [facade_mat, shops_mat, white_paint, red_steel])

# their flat roof between the outline and the back walls; where the outline
# lies inside the back wall (the north side) the second ring overhangs it on
# white columns
bm = bmesh.new()
STEP = 2.0
for ix in range(int(-112 / STEP), int(112 / STEP)):
    for iy in range(int(-90 / STEP), int(95 / STEP)):
        x0_, y0_ = ix * STEP, iy * STEP
        cx_, cy_ = x0_ + STEP / 2, y0_ + STEP / 2
        if d_front(cx_, cy_) < BACK_D + 0.1 or not inside_poly(cx_, cy_, OUTLINE):
            continue
        face(bm, [(x0_, y0_, BASE_H), (x0_ + STEP, y0_, BASE_H), (x0_ + STEP, y0_ + STEP, BASE_H), (x0_, y0_ + STEP, BASE_H)], UPV, 0)
for i in range(NP):
    if not is_straight(i):
        continue
    for s in range(3):
        u_ = (s + 0.5) / 3
        p_in = P(i, u_, BACK_D)
        if inside_poly(p_in.x, p_in.y, OUTLINE):
            continue
        dd = BACK_D
        while dd > 20 and not inside_poly(P(i, u_, dd).x, P(i, u_, dd).y, OUTLINE):
            dd -= 0.25
        a0_, a1_ = P(i, s / 3, dd), P(i, (s + 1) / 3, dd)
        b0_, b1_ = P(i, s / 3, OUT_D), P(i, (s + 1) / 3, OUT_D)
        face(bm, [(a0_.x, a0_.y, BASE_H), (a1_.x, a1_.y, BASE_H), (b1_.x, b1_.y, BASE_H), (b0_.x, b0_.y, BASE_H)], -UPV, 1)
        face(bm, [(b0_.x, b0_.y, BASE_H), (b1_.x, b1_.y, BASE_H), (b1_.x, b1_.y, BASE_H + 0.9), (b0_.x, b0_.y, BASE_H + 0.9)],
             (NODES[i][1] + NODES[i + 1][1]), 1)
        if s == 1:
            pc = P(i, 0.0, OUT_D - 0.8)
            tube(bm, Vector((pc.x, pc.y, 0.0)), Vector((pc.x, pc.y, BASE_H)), 0.42, 1, 12, step=4.0)
new_obj('Office_Roofs', bm, '05_Outside', [base_roof, white_paint])

# the main stand's front (OSM: its offices reach out to Frederiklaan): the
# red band along the top, 'philips stadion' over the entrance, the flags on
# the terrace; the red steel crosses on the second ring's back wall
bm = bmesh.new()
for k in range(n_o):
    a_, c_ = OUTLINE[k], OUTLINE[(k + 1) % n_o]
    if a_[1] < 70 or c_[1] < 70 or abs(c_[0] - a_[0]) < 0.5:
        continue
    outv = Vector((c_[1] - a_[1], -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
    o = outv.normalized() * 0.08
    face(bm, [(a_[0] + o.x, a_[1] + o.y, 10.9), (c_[0] + o.x, c_[1] + o.y, 10.9), (c_[0] + o.x, c_[1] + o.y, 11.9), (a_[0] + o.x, a_[1] + o.y, 11.9)], outv, 0)
new_obj('Main_Band', bm, '05_Outside', [red_steel])
y_sign = max(p[1] for p in OUTLINE if -47.0 < p[0] < -4.0) + 0.12
bm = bmesh.new()
face(bm, [(-17.0, y_sign, 8.1), (-33.0, y_sign, 8.1), (-33.0, y_sign, 10.3), (-17.0, y_sign, 10.3)], Vector((0, 1, 0)), 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
new_obj('Main_Sign', bm, '05_Outside', [sign_mat])
bm = bmesh.new()
yb = YS + OUT_D + 1.3
for x_ in (34.0, 22.0, 10.0, -2.0, -14.0, -26.0, -38.0):
    tube(bm, Vector((x_, yb, BASE_H)), Vector((x_, yb, 26.4)), 0.32, 0, 8, step=3.0)
    for s in (-1, 1):
        tube(bm, Vector((x_ - 3.2 * s, yb, BASE_H + 0.8)), Vector((x_ + 3.2 * s, yb, 25.6)), 0.24, 0, 8, step=3.0)
    tube(bm, Vector((x_ - 3.2, yb, 19.2)), Vector((x_ + 3.2, yb, 19.2)), 0.2, 0, 8)
    for zz in (BASE_H + 1.0, 25.4):
        tube(bm, Vector((x_, yb, zz)), Vector((x_, YS + OUT_D, zz)), 0.18, 0, 6)
new_obj('Main_Crosses', bm, '05_Outside', [red_steel])
bm = bmesh.new()
WIND = Vector((0.55, -0.83, 0)).normalized()
SIDEW = Vector((-WIND.y, WIND.x, 0))
fl_pts = [p for p in OUTLINE if p[1] > 78.0]
x_min, x_max = min(p[0] for p in fl_pts), max(p[0] for p in fl_pts)
for n_, x_ in enumerate(np.arange(x_min + 3.0, x_max - 3.0, 6.0)):
    ys_ = []
    for k in range(n_o):
        (ax_, ay_), (bx_, by_) = OUTLINE[k], OUTLINE[(k + 1) % n_o]
        if min(ax_, bx_) <= x_ <= max(ax_, bx_) and abs(bx_ - ax_) > 1e-6 and min(ay_, by_) > 70:
            ys_.append(ay_ + (by_ - ay_) * (x_ - ax_) / (bx_ - ax_))
    if not ys_:
        continue
    y_top = max(ys_) - 0.6
    base_ = Vector((float(x_), y_top, BASE_H + 0.7))
    top = base_ + Vector((0, 0, 6.5))
    tube(bm, base_, top, 0.06, 0, 6, step=3.0)
    FLW, FLH, NU, NV = 2.4, 1.6, 6, 2
    def fp(uu, vv, ph=n_ * 1.7):
        wave = 0.18 * math.sin(uu * 5.0 + ph) * uu
        return top + Vector((0, 0, -0.2 - FLH * (1 - vv))) + WIND * (0.08 + FLW * uu) + SIDEW * wave
    for i_ in range(NU):
        for j_ in range(NV):
            q = [(i_, j_), (i_ + 1, j_), (i_ + 1, j_ + 1), (i_, j_ + 1)]
            pts = [fp(a / NU, b / NV) for a, b in q]
            uvs = [(((n_ % 5) + a / NU) / 5, b / NV) for a, b in q]
            face(bm, pts, SIDEW, 1, uvs)
            face(bm, pts[::-1], -SIDEW, 1, uvs[::-1])
new_obj('Flags', bm, '05_Outside', [white_paint, flags_mat])

# the footbridge from the station's platform to the away section (OSM)
bm = bmesh.new()
br = next((r for r in OSM['roads'] if r.get('bridge') and r['type'] == 'footway' and len(r['pts']) >= 3 and r['pts'][-1][1] > -70), None)
if br:
    pts = [Vector((p[0], p[1], 0)) for p in br['pts']]
    BZ = 5.8
    for a_, b_ in zip(pts, pts[1:]):
        dv = (b_ - a_)
        if dv.length < 1.0:
            continue
        sd = Vector((-dv.y, dv.x, 0)).normalized() * 1.8
        n_ = max(1, math.ceil(dv.length / 3.0))
        for k in range(n_):
            p0, p1 = a_.lerp(b_, k / n_), a_.lerp(b_, (k + 1) / n_)
            face(bm, [p0 - sd + Vector((0, 0, BZ)), p1 - sd + Vector((0, 0, BZ)), p1 + sd + Vector((0, 0, BZ)), p0 + sd + Vector((0, 0, BZ))], UPV, 0)
            face(bm, [p0 - sd + Vector((0, 0, BZ - 0.8)), p1 - sd + Vector((0, 0, BZ - 0.8)), p1 + sd + Vector((0, 0, BZ - 0.8)), p0 + sd + Vector((0, 0, BZ - 0.8))], -UPV, 0)
            for s in (-1, 1):
                face(bm, [p0 + sd * s + Vector((0, 0, BZ - 0.8)), p1 + sd * s + Vector((0, 0, BZ - 0.8)), p1 + sd * s + Vector((0, 0, BZ)), p0 + sd * s + Vector((0, 0, BZ))], sd * s, 0)
        for s in (-1, 1):
            tube(bm, a_ + sd * s + Vector((0, 0, BZ + 1.2)), b_ + sd * s + Vector((0, 0, BZ + 1.2)), 0.05, 1, 6, step=4.0)
            for k in range(int(dv.length / 2.0) + 1):
                p = a_.lerp(b_, k / max(1, int(dv.length / 2.0))) + sd * s
                tube(bm, p + Vector((0, 0, BZ)), p + Vector((0, 0, BZ + 1.2)), 0.03, 1, 4)
        for k in range(int(dv.length / 10.0) + 1):
            p = a_.lerp(b_, k / max(1, int(dv.length / 10.0)))
            box(bm, p, dv, 0.35, sd, 0.35, 0.0, BZ - 0.8, 2)
new_obj('Footbridge', bm, '05_Outside', [concrete_light, galv, white_paint])


# ================================================================ outside: the stadium's own ground, the railway, trees
# The ground round the stadium up to the streets belongs to it (it is seen in
# Stadion kiezen); the town beyond is the backdrop
G_HALF = 320.0                   # tools/philips/ground.png covers 640 x 640 m
AP_X0, AP_X1, AP_Y0, AP_Y1 = -160.0, 160.0, -165.0, 130.0
G_Z = -0.12


def ground_cells(bm, x0, x1, y0, y1, step, skip):
    nx, ny = round((x1 - x0) / step), round((y1 - y0) / step)
    for ix in range(nx):
        for iy in range(ny):
            xa, xb = x0 + ix * step, x0 + (ix + 1) * step
            ya, yb = y0 + iy * step, y0 + (iy + 1) * step
            if skip(xa, xb, ya, yb):
                continue
            q = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
            face(bm, [(x, y, G_Z) for x, y in q], UPV, 0, [((x + G_HALF) / (2 * G_HALF), (y + G_HALF) / (2 * G_HALF)) for x, y in q])


bm = bmesh.new()
ground_cells(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 5.0, lambda xa, xb, ya, yb: XE <= xa and xb <= XW and YN <= ya and yb <= YS)
new_obj('Ground', bm, '05_Outside', [ground_mat])

# the station Eindhoven Stadion: its platform, the shelter on it, the sprayed
# noise wall behind it; the masts of the overhead lines along the tracks
bm = bmesh.new()
for g in OSM['platforms']:
    pts = g[:-1] if g[0] == g[-1] else g
    sa = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector((c_[1] - a_[1], -(c_[0] - a_[0]), 0)) * (1 if sa > 0 else -1)
        face(bm, [(a_[0], a_[1], G_Z), (c_[0], c_[1], G_Z), (c_[0], c_[1], 0.76), (a_[0], a_[1], 0.76)], outv, 0)
    try:
        rf = bm.faces.new([bm.verts.new((x, y, 0.76)) for x, y in pts])
        rf.material_index = 0
        rf.normal_update()
        if rf.normal.z < 0:
            rf.normal_flip()
        bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    except ValueError:
        pass
    # the shelter: a long low vault on posts near the footbridge
    xs_ = sorted(pts, key=lambda p: p[0])
    mid_line = [(x_, sum(p[1] for p in pts if abs(p[0] - x_) < 8) / max(1, sum(1 for p in pts if abs(p[0] - x_) < 8))) for x_ in np.arange(20.0, 125.0, 5.0)]
    for (xa, ya), (xb, yb) in zip(mid_line, mid_line[1:]):
        for k in range(6):
            a0, a1 = math.pi * k / 6, math.pi * (k + 1) / 6
            za, zb = 3.4 + 0.9 * math.sin(a0), 3.4 + 0.9 * math.sin(a1)
            oa, ob = 2.4 * math.cos(a0), 2.4 * math.cos(a1)
            face(bm, [(xa, ya + oa, za), (xb, yb + oa, za), (xb, yb + ob, zb), (xa, ya + ob, zb)], UPV, 1)
        for s in (-1, 1):
            tube(bm, Vector((xa, ya + s * 2.2, 0.76)), Vector((xa, ya + s * 2.2, 3.4)), 0.07, 2, 5)
for w_ in OSM['walls']:
    for a_, c_ in zip(w_, w_[1:]):
        L = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
        if L < 0.2 or not all(AP_X0 < q[0] < AP_X1 and AP_Y0 < q[1] < AP_Y1 for q in (a_, c_)):
            continue
        nrm = Vector((-(c_[1] - a_[1]), c_[0] - a_[0], 0))
        u_a = 0.0
        face(bm, [(a_[0], a_[1], G_Z), (c_[0], c_[1], G_Z), (c_[0], c_[1], 2.3), (a_[0], a_[1], 2.3)], nrm, 3, [(0, 0), (L / 24.0, 0), (L / 24.0, 1), (0, 1)])
        face(bm, [(a_[0], a_[1], G_Z), (c_[0], c_[1], G_Z), (c_[0], c_[1], 2.3), (a_[0], a_[1], 2.3)], -nrm, 3, [(0, 0), (L / 24.0, 0), (L / 24.0, 1), (0, 1)])
# the overhead line masts: along the outermost tracks, every 55 m
for r in OSM['rail']:
    pts = r['pts']
    run = 0.0
    for a_, c_ in zip(pts, pts[1:]):
        L = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
        if L < 0.1:
            continue
        while run < L:
            f_ = run / L
            x_, y_ = a_[0] + (c_[0] - a_[0]) * f_, a_[1] + (c_[1] - a_[1]) * f_
            nrm = Vector((-(c_[1] - a_[1]), c_[0] - a_[0], 0)).normalized()
            if nrm.y > 0:
                nrm = -nrm
            p = Vector((x_, y_, 0)) + nrm * 2.6
            if AP_X0 < p.x < AP_X1 and AP_Y0 < p.y < AP_Y1 and p.y < -95:
                tube(bm, Vector((p.x, p.y, G_Z)), Vector((p.x, p.y, 7.6)), 0.12, 2, 6, step=4.0)
                tube(bm, Vector((p.x, p.y, 6.9)), Vector((p.x, p.y, 6.9)) - nrm * 3.4, 0.05, 2, 5)
            run += 55.0
        run -= L
new_obj('Railway', bm, '05_Outside', [platform_mat, roof_white, galv, graffiti])

trng = random.Random(1913)


def tree(bm, x, y, h, r):
    tube(bm, Vector((x, y, G_Z)), Vector((x, y, G_Z + h * 0.62)), 0.22, 0, 5, step=4.0)
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector((r, r * trng.uniform(0.85, 1.1), h * 0.3)), verts=res['verts'])
    bmesh.ops.translate(bm, vec=Vector((x, y, G_Z + h * 0.72)), verts=res['verts'])
    uvl = bm.loops.layers.uv.verify()
    for f_ in {f_ for v_ in res['verts'] for f_ in v_.link_faces}:
        f_.material_index = 1
        for l in f_.loops:
            l[uvl].uv = (l.vert.co.x / 6.0, (l.vert.co.y + l.vert.co.z) / 6.0)


def clear_of(x, y, margin):
    if inside_poly(x, y, OUTLINE) or outline_dist(x, y) < 6.0:
        return False
    for b in OSM['buildings']:
        bx, by = b['pts'][0]
        if abs(bx - x) < 60 and abs(by - y) < 60 and inside_poly(x, y, b['pts']):
            return False
    for g in OSM['platforms']:
        if inside_poly(x, y, g):
            return False
    for r in OSM['roads'] + [{'type': 'rail', 'pts': rr['pts']} for rr in OSM['rail']]:
        if r['type'] in ('footway', 'path', 'cycleway', 'steps'):
            continue
        pts = r['pts']
        for k in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-6, dx * dx + dy * dy)))
            if math.hypot(x - ax - t * dx, y - ay - t * dy) < margin:
                return False
    return True


def road_trees(bm, every, in_apron):
    for r in OSM['roads']:
        if r['type'] not in ('residential', 'tertiary', 'secondary', 'primary', 'service', 'unclassified'):
            continue
        pts = r['pts']
        for k in range(len(pts) - 1):
            a, b = Vector((*pts[k], 0)), Vector((*pts[k + 1], 0))
            L = (b - a).length
            if L < 1:
                continue
            nrm = Vector((-(b - a).y, (b - a).x, 0)).normalized()
            nseg = max(1, int(L / every))
            for j in range(nseg):
                for sgn in (-1, 1):
                    if trng.random() < 0.45:
                        continue
                    p = a.lerp(b, (j + trng.random()) / nseg) + nrm * sgn * trng.uniform(6.0, 8.5)
                    ap = AP_X0 < p.x < AP_X1 and AP_Y0 < p.y < AP_Y1
                    if ap != in_apron or abs(p.x) > G_HALF - 10 or abs(p.y) > G_HALF - 10 or not clear_of(p.x, p.y, 4.5):
                        continue
                    tree(bm, p.x, p.y, trng.uniform(9, 15), trng.uniform(2.8, 4.4))


bm = bmesh.new()
for x_, y_ in OSM['trees']:
    if AP_X0 < x_ < AP_X1 and AP_Y0 < y_ < AP_Y1 and clear_of(x_, y_, 2.0):
        tree(bm, x_, y_, trng.uniform(9, 14), trng.uniform(2.6, 4.0))
road_trees(bm, 12.0, True)
near_trees = new_obj('Trees', bm, '05_Outside', [trunk, foliage])


# ================================================================ the backdrop: the town from OpenStreetMap
bm = bmesh.new()
ground_cells(bm, -G_HALF, G_HALF, -G_HALF, G_HALF, 10.0, lambda xa, xb, ya, yb: AP_X0 <= xa and xb <= AP_X1 and AP_Y0 <= ya and yb <= AP_Y1)
far_ground = new_obj('Ground_Far', bm, '06_Backdrop', [ground_mat])


def obb(pts):
    # the smallest box round a polygon: (centre, long axis, half long, half short)
    best = None
    n = len(pts)
    for k in range(n):
        (ax, ay), (bx, by) = pts[k], pts[(k + 1) % n]
        L = math.hypot(bx - ax, by - ay)
        if L < 0.5:
            continue
        ux, uy = (bx - ax) / L, (by - ay) / L
        us = [x * ux + y * uy for x, y in pts]
        vs = [-x * uy + y * ux for x, y in pts]
        area = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or area < best[0]:
            cu, cv = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (area, (cu * ux - cv * uy, cu * uy + cv * ux), (ux, uy), (max(us) - min(us)) / 2, (max(vs) - min(vs)) / 2)
    if best is None:
        return None
    area, c, u, hu, hv = best
    if hv > hu:
        u, hu, hv = (-u[1], u[0]), hv, hu
    return area, c, u, hu, hv


bm = bmesh.new()
HEIGHT = {'house': 6.0, 'detached': 6.5, 'residential': 8.0, 'semidetached_house': 6.0, 'terrace': 6.0, 'garage': 2.8, 'garages': 2.8,
          'shed': 2.6, 'roof': 4.0, 'canopy': 3.5, 'veranda': 3.0, 'apartments': 13.0, 'school': 10.0, 'office': 14.0, 'commercial': 12.0,
          'retail': 7.0, 'church': 15.0, 'service': 4.0}
for b in OSM['buildings']:
    pts = b['pts'][:-1] if b['pts'][0] == b['pts'][-1] else b['pts']
    if len(pts) < 3 or max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4:
        continue
    sa = 0.5 * sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    area = abs(sa)
    if area < 5:
        continue
    h = HEIGHT.get(b['type'], 9.0 if area > 500 else 6.0)
    if b.get('height'):
        try:
            h = float(b['height'])
        except ValueError:
            pass
    elif b['levels']:
        try:
            h = float(b['levels']) * 3.1 + (0.0 if b.get('roof') == 'gabled' else 1.2)
        except ValueError:
            pass
    big = area > 500 or b['type'] in ('school', 'office', 'apartments', 'commercial', 'church')
    gabled = b.get('roof') in ('gabled', 'gambrel') and not big
    ob = obb(pts) if gabled else None
    if ob and area / ob[0] < 0.82:
        ob = None
    if ob:
        # a house of Philipsdorp: brick under a pantiled gable, the ridge along its length
        _, c, u_, hu, hv = ob
        U, Vv = Vector((u_[0], u_[1], 0)), Vector((-u_[1], u_[0], 0))
        C = Vector((c[0], c[1], 0))
        ridge = h + min(4.5, hv * 0.95)
        corners = [C + U * su * hu + Vv * sv * hv for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        for k in range(4):
            a_, c2 = corners[k], corners[(k + 1) % 4]
            face(bm, [a_ + Vector((0, 0, G_Z)), c2 + Vector((0, 0, G_Z)), c2 + Vector((0, 0, h)), a_ + Vector((0, 0, h))], (a_ + c2) / 2 - C, 1)
        r0, r1 = C - U * hu + Vector((0, 0, ridge)), C + U * hu + Vector((0, 0, ridge))
        tile = 0 if trng.random() < 0.75 else 6
        face(bm, [corners[0] + Vector((0, 0, h)), corners[1] + Vector((0, 0, h)), r1, r0], -Vv + UPV, tile)
        face(bm, [corners[2] + Vector((0, 0, h)), corners[3] + Vector((0, 0, h)), r0, r1], Vv + UPV, tile)
        face(bm, [corners[1] + Vector((0, 0, h)), corners[2] + Vector((0, 0, h)), r1], U, 1)
        face(bm, [corners[3] + Vector((0, 0, h)), corners[0] + Vector((0, 0, h)), r0], -U, 1)
        continue
    wall_m = 4 if big else (1 if trng.random() < 0.7 else 2)
    if b['type'] in ('shed', 'garage', 'garages', 'canopy', 'veranda'):
        wall_m = 5
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sa > 0 else -1)
        nz = max(1, math.ceil(h / 3.2))
        for q in range(nz):
            za, zb = G_Z + h * q / nz, G_Z + h * (q + 1) / nz
            face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, wall_m)
    try:
        rf = bm.faces.new([bm.verts.new((x, y, G_Z + h)) for x, y in pts])
    except ValueError:
        continue
    rf.material_index = 3 if (big or not gabled) else 0
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
# the towers of the Hartje and their neighbours (OSM building parts)
for b in OSM['parts']:
    pts = b['pts'][:-1] if b['pts'][0] == b['pts'][-1] else b['pts']
    if len(pts) < 3 or max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4:
        continue
    try:
        lv = float(b['levels'] or 1); ml = float(b['min_level'] or 0)
    except ValueError:
        continue
    z0, z1 = G_Z + ml * 3.1, G_Z + lv * 3.1
    sa = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    mat = 4 if b.get('material') == 'glass' else 2 if b.get('material') == 'brick' else 4
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sa > 0 else -1)
        nz = max(1, math.ceil((z1 - z0) / 3.2))
        for q in range(nz):
            za, zb = z0 + (z1 - z0) * q / nz, z0 + (z1 - z0) * (q + 1) / nz
            face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, mat)
    try:
        rf = bm.faces.new([bm.verts.new((x, y, z1)) for x, y in pts])
        rf.material_index = 3
        rf.normal_update()
        if rf.normal.z < 0:
            rf.normal_flip()
        bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
    except ValueError:
        pass
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, brick_light, flat_roof, office_wall, plaster, tiles_dark])
bm = bmesh.new()
road_trees(bm, 14.0, False)
for x_, y_ in OSM['trees']:
    if not (AP_X0 < x_ < AP_X1 and AP_Y0 < y_ < AP_Y1) and abs(x_) < G_HALF - 8 and abs(y_) < G_HALF - 8 and clear_of(x_, y_, 2.0):
        tree(bm, x_, y_, trng.uniform(9, 14), trng.uniform(2.6, 4.0))
far_trees = new_obj('Trees_Far', bm, '06_Backdrop', [trunk, foliage])

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('SAVED', OUT_BLEND)


# ================================================================ the sun and the sky
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.36, 0.55, 0.95, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.75
ld = D.lights.new('Sun', 'SUN')
ld.energy = 5.0
ld.color = (1.0, 0.95, 0.86)
ld.angle = math.radians(0.6)
sun = D.objects.new('Sun', ld)
sc.collection.objects.link(sun)
sun.rotation_euler = (-TO_SUN).to_track_quat('-Z', 'Y').to_euler()

sc.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
    sc.cycles.device = 'GPU'
    print('CYCLES DEVICES', [(dv.name, dv.type) for dv in prefs.devices])
except Exception as ex:
    print('NO GPU', ex)
    sc.cycles.device = 'CPU'


def look(cam_obj, target):
    d = Vector(target) - cam_obj.location
    cam_obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def preview(name, loc, target, fov, clip=0.5, res=(1280, 720), samples=24):
    cd = D.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'
    cd.angle_y = math.radians(fov)
    cd.clip_start = clip
    cd.clip_end = 3000
    co = D.objects.new(name, cd)
    sc.collection.objects.link(co)
    co.location = loc
    look(co, target)
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 85
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = os.path.join(TEX_DIR, 'preview_' + name + '.jpg')
    bpy.ops.render.render(write_still=True)
    print('PREVIEW', sc.render.filepath)


if QUICK:
    sc.cycles.max_bounces = 3
    which = [a for a in ARGS[3:] if a != 'quick']
    shots = {
        'match': ((0, 38.0, 30.0), (0, -30.0, 3.0), 52),
        'photo2': ((0.0, 47.5, 5.5), (0.0, -60.0, 15.0), 62),             # 2.png: from behind the dugouts
        'photo1': ((58.0, 60.0, 22.0), (-40.0, -40.0, 6.0), 74),          # 1.png: from the south-west corner's second ring
        'photo7': ((-49.0, 30.0, 1.6), (-18.0, -45.0, 13.0), 58),         # 7.png: by the east goal, the north stand
        'photo6': ((-15.0, 58.0, 19.0), (-60.0, -44.0, 15.0), 32),        # 6.png: the north-east corner, its screen
        'photo3': ((45.0, 100.0, 1.7), (-40.0, 78.0, 16.0), 62),          # 3.png: the main stand's front and the south-east pod
        'photo4': ((300.0, -20.0, 190.0), (0.0, 0.0, 0.0), 34),           # 4.png: from over the west
        'photo5': ((-40.0, -300.0, 160.0), (0.0, 15.0, 0.0), 36),         # 5.png: from over the railway
        'train': ((55.0, -135.0, 4.0), (78.0, -62.0, 20.0), 62),          # from the train at the station: the north-west pod
        'corner': ((-135.0, 95.0, 1.7), (-85.0, 55.0, 20.0), 62),
        'photo8': ((9.0, 36.5, 1.6), (-6.0, 47.0, 4.0), 60),               # 8.png: the dugouts and the tunnel
        'away': ((40.0, 10.0, 12.0), (75.0, -55.0, 20.0), 50),             # the away section in the north-west corner        # the south-east corner from the crossroads
    }
    for nm in (which or list(shots)):
        loc, tgt, fov = shots[nm]
        preview(nm, loc, tgt, fov, res=(1280, 720))
    sys.exit(0)

# ================================================================ game export: the sun baked in
for m in D.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0
sc.cycles.samples = 24
bk = sc.render.bake
bk.margin = 4
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 0
sc.cycles.transmission_bounces = 0; sc.cycles.transparent_max_bounces = 2
bk.use_pass_direct = True; bk.use_pass_indirect = True; bk.use_pass_color = False
bk.use_selected_to_active = False


def select_only(objs, active):
    for o in sc.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def upsample(a, h2, w2):
    h, w_ = a.shape[:2]
    ys = np.clip((np.arange(h2) + 0.5) / h2 * h - 0.5, 0, h - 1)
    xs_ = np.clip((np.arange(w2) + 0.5) / w2 * w_ - 0.5, 0, w_ - 1)
    y0, x0 = ys.astype(int), xs_.astype(int)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w_ - 1)
    fy, fx = (ys - y0)[:, None, None].astype('f'), (xs_ - x0)[None, :, None].astype('f')
    return (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y1][:, x0] * fy * (1 - fx)
            + a[y0][:, x1] * (1 - fy) * fx + a[y1][:, x1] * fy * fx)


def bake_lightmap(obj, w_, h_, samples=160):
    lm = D.images.new(obj.name + '_light', w_, h_, float_buffer=True)
    m = obj.data.materials[0]
    node = m.node_tree.nodes.new('ShaderNodeTexImage'); node.image = lm
    m.node_tree.nodes.active = node
    bk.target = 'IMAGE_TEXTURES'
    sc.cycles.samples = samples
    select_only([obj], obj)
    t0 = time.time()
    bpy.ops.object.bake(type='DIFFUSE')
    print('LIGHTMAP %s %.0fs' % (obj.name, time.time() - t0))
    a = np.empty(w_ * h_ * 4, 'f'); lm.pixels.foreach_get(a)
    a = a.reshape(h_, w_, 4)[..., :3].copy()
    a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 5
    m.node_tree.nodes.remove(node)
    return a


for o in (lines, goals):
    o.hide_render = True
grass_light = bake_lightmap(grass, 704, 464)
grass.hide_render = True                 # the floor in full sun where the pitch lies on it
floor_light = bake_lightmap(floor, 840, 528)
grass.hide_render = False
inner = grass_light[int(464 * 0.25):int(464 * 0.75), int(704 * 0.25):int(704 * 0.75)]
lum_px = (inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1)
lum = float(np.percentile(lum_px, 80))  # the sunlit grass, not the main stand's shadow
EXPOSE = 0.70 / max(lum, 1e-6)
print('PITCH LIGHT %.3f  EXPOSE %.4f' % (lum, EXPOSE))


def line_alpha(X, Y, px):
    # the pitch markings as coverage, from their distance to each line (metres)
    d = np.full(X.shape, 1e3, 'f')
    def seg_h(y, x0, x1):
        nonlocal d
        dx = np.maximum(np.maximum(x0 - X, X - x1), 0)
        d = np.minimum(d, np.hypot(dx, Y - y))
    def seg_v(x, y0, y1):
        nonlocal d
        dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0)
        d = np.minimum(d, np.hypot(X - x, dy))
    def arc_(cx, cy, r, a0=None, a1=None):
        nonlocal d
        rr = np.hypot(X - cx, Y - cy)
        dd = np.abs(rr - r)
        if a0 is not None:
            ang = np.arctan2(Y - cy, X - cx)
            ok = ((ang - a0) % (2 * np.pi)) <= ((a1 - a0) % (2 * np.pi))
            dd = np.where(ok, dd, 1e3)
        d = np.minimum(d, dd)
    seg_h(hy, -hx, hx); seg_h(-hy, -hx, hx)
    seg_v(hx, -hy, hy); seg_v(-hx, -hy, hy); seg_v(0, -hy, hy)
    arc_(0, 0, 9.15)
    for s in (-1, 1):
        gx = s * hx
        for depth, half in ((16.5, 20.16), (5.5, 9.16)):
            x = gx - s * depth
            seg_v(x, -half, half)
            seg_h(half, min(gx, x), max(gx, x)); seg_h(-half, min(gx, x), max(gx, x))
        spot = gx - s * 11
        a = math.acos((16.5 - 11) / 9.15)
        mid = math.pi if s > 0 else 0
        arc_(spot, 0, 9.15, mid - a, mid + a)
        for t in (-1, 1):
            a0 = {(1, 1): math.pi, (1, -1): math.pi / 2, (-1, 1): 1.5 * math.pi, (-1, -1): 0}[(s, t)]
            arc_(gx, t * hy, 1.0, a0, a0 + math.pi / 2)
    cov = np.clip((LINE / 2 - d) / px + 0.5, 0, 1)
    for cx, cy, r in [(0, 0, 0.2), (hx - 11, 0, 0.2), (-hx + 11, 0, 0.2)]:
        cov = np.maximum(cov, np.clip((r - np.hypot(X - cx, Y - cy)) / px + 0.5, 0, 1))
    return cov


def grass_albedo(X, Y, H, W):
    # PSV's pitch as on the photos: broad bands across it, light and dark,
    # 18 over its length, wear in the goalmouths
    bands = np.tanh(np.sin(np.pi * X / (PW / 18)) * 6)
    fine = rng.normal(0, 1, (H, W)).astype('f')
    shade = (1 + 0.11 * bands + 0.04 * vnoise(H, W, 400, 400) + 0.025 * vnoise(H, W, 48, 48)
             + 0.03 * vnoise(H, W, 1, 14) * (0.6 + 0.4 * bands) + 0.03 * fine)
    g = np.array((0.060, 0.180, 0.040), 'f') * shade[..., None]
    g[..., 0] *= 1 + 0.08 * vnoise(H, W, 300, 300)
    wear = sum(np.exp(-(((X - gx) / 3.0) ** 2 + (Y / 5.0) ** 2)) for gx in (-(hx - 3.0), hx - 3.0))
    wear = (0.14 * wear * (0.55 + 0.45 * np.clip(vnoise(H, W, 36, 36) + 0.5, 0, 1)))[..., None]
    return g * (1 - wear) + np.array((0.14, 0.17, 0.07), 'f') * wear


def finish(name, albedo, light, H, W):
    out = np.clip(albedo * upsample(light, H, W) * (EXPOSE * GAIN), 0, 1)
    img = D.images.new(name, W, H)
    px = np.ones((H, W, 4), 'f')
    px[..., :3] = to_srgb(out)
    img.pixels.foreach_set(px.ravel())
    sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
    sc.view_settings.view_transform = 'Standard'
    img.save_render(TEX_DIR + '/' + name + '.jpg')
    D.images.remove(img)
    return D.images.load(TEX_DIR + '/' + name + '.jpg')


# the pitch picture: 4096 x 2702 over 111 x 73 m
H, W = 2702, 4096
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * PITCH_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * PITCH_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = grass_albedo(X, Y, H, W)
cov = line_alpha(X, Y, 2 * PITCH_X / W)[..., None] * np.clip(0.85 + 0.1 * vnoise(H, W, 90, 90), 0.7, 1)[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
pitch_img = finish('ps_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: the grass up to the boards, the grey walkway round them
H, W = 1312, 2048
X = (FX0 + (np.arange(W, dtype='f') + 0.5) / W * (FX1 - FX0))[None, :]
Y = (FY0 + (np.arange(H, dtype='f') + 0.5) / H * (FY1 - FY0))[:, None]
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.22, 0.22, 0.215)
alb *= (1 + 0.05 * rng.normal(0, 1, (H, W)).astype('f') + 0.04 * vnoise(H, W, 30, 30))[..., None]
tiles_ = ((np.floor(X / 0.6) + np.floor(Y / 0.6)) % 2 == 0)[..., None]
alb *= np.where(tiles_, 1.0, 0.94)
infield = (np.abs(X) < BOARD_X) & (np.abs(Y) < BOARD_Y)
alb = np.where(infield[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('ps_floor', alb, floor_light, H, W)
del alb, X, Y
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

skip = ('Pitch_Lines', 'StadiumGoals', 'Ground_Far', 'Buildings', 'Trees_', 'ScreenFace_')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, far_ground, buildings, far_trees, screen_face]:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    else:
        o.data.uv_layers[0].name = 'UVMap'
screens = screen_face
screens.name = 'StadiumScreens'
scc = screens.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
scc.data.foreach_set('color', [1.0 / GAIN, 1.0 / GAIN, 1.0 / GAIN, 1.0] * len(scc.data))
screens.data.color_attributes.active_color = scc
screens.data.color_attributes.render_color_index = screens.data.color_attributes.find('Col')
target = grass
select_only(export, target)
bpy.ops.object.join()
target.name = 'PhilipsStadion'
select_only([far_ground, buildings, far_trees], far_ground)
bpy.ops.object.join()
backdrop = far_ground
backdrop.name = 'StadiumBackdrop'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor'}
FIXED_LIGHT = {'M_GlassUnder': 0.62}       # the main stand's glass roof from under it: lit through it, not by the bake


def bake_light(obj, samples=96):
    # the sun into the vertex colours, at the pitch's exposure; the pitch and
    # the floor carry their own light in their pictures
    me = obj.data
    me.color_attributes.active_color = me.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')
    bk.target = 'VERTEX_COLORS'
    sc.cycles.samples = samples
    select_only([obj], obj)
    t0 = time.time()
    bpy.ops.object.bake(type='DIFFUSE')
    print('BAKE %s %.0fs' % (obj.name, time.time() - t0))
    fc = me.color_attributes['Light']
    c = np.empty(len(fc.data) * 4, 'f'); fc.data.foreach_get('color', c); c = c.reshape(-1, 4)
    c[:, :3] = np.clip(c[:, :3] * EXPOSE, 0, 1)
    mi = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('material_index', mi)
    ls = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_start', ls)
    lt = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_total', lt)
    own = np.array([m is not None and m.name.split('.')[0] in SELF_LIT for m in me.materials])
    order = np.argsort(ls)
    loop_own = np.repeat(own[mi][order], lt[order])
    lv = np.empty(len(me.loops), 'i'); me.loops.foreach_get('vertex_index', lv)
    vert_own = np.zeros(len(me.vertices), bool); vert_own[lv[loop_own]] = True
    if (~vert_own).any():
        print('LIGHT p10/p50/p90/p99', [round(float(v), 3) for v in np.percentile(c[~vert_own, :3].mean(1), (10, 50, 90, 99))])
    c[vert_own, :3] = 1.0 / GAIN
    for mname, val in FIXED_LIGHT.items():
        fx = np.array([m is not None and m.name.split('.')[0] == mname for m in me.materials])
        if fx.any():
            lfx = np.repeat(fx[mi][order], lt[order])
            c[lv[lfx], :3] = val / GAIN
    c[:, 3] = 1
    me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT').data.foreach_set('color', c.ravel())
    me.color_attributes.remove(me.color_attributes['Light'])
    ci = me.color_attributes.find('Col')
    me.color_attributes.active_color_index = ci
    me.color_attributes.render_color_index = ci


bake_light(target)
bake_light(backdrop, 32)
gc = goals.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
gc.data.foreach_set('color', [0.45, 0.45, 0.45, 1.0] * len(gc.data))
goals.data.color_attributes.active_color = gc
goals.data.color_attributes.render_color_index = goals.data.color_attributes.find('Col')

objs = [target, goals, screens, backdrop]
bb = [o.matrix_world @ Vector(cc) for o in objs for cc in o.bound_box]
mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
s = 264 / max(mx[0] - mn[0], mx[1] - mn[1])
cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
print('BOUNDS', mn, mx)
print('PITCH x=%.2f z=%.2f w=%.2f l=%.2f y=%.2f' % (-cx * s, cy * s, PW * s, PL * s, -mn[2] * s))
print('TRIS', sum(len(p.vertices) - 2 for p in target.data.polygons), 'MATS', len(target.data.materials))
select_only(objs, target)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
extra = {}
if 'export_vertex_color' in props: extra['export_vertex_color'] = 'ACTIVE'
if 'export_all_vertex_colors' in props: extra['export_all_vertex_colors'] = False
if 'export_active_vertex_color_when_no_material' in props: extra['export_active_vertex_color_when_no_material'] = True
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, **extra)
print('EXPORTED', OUT_GLB)
