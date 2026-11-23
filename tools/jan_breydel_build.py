# Builds the Jan Breydelstadion (Sint-Andries, Brugge) from nothing and
# exports it for the game, the way Montjuïc and the Bernabéu are built; this
# one on an autumn afternoon in the low sun, as on most photos of the ground.
#   blender -b --factory-startup --python tools/jan_breydel_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/jan_breydel_assets.py.
#
# The facts and the plan:
#   - opened in 1975 as the Olympiastadion of Club and Cercle Brugge, named
#     after Jan Breydel in 1998 and rebuilt for Euro 2000: all seats, every
#     stand roofed, 29.062 places
#   - the plan is OpenStreetMap's (ways 166521385, 166521388, 166522336; data
#     © OpenStreetMap contributors, ODbL), turned 107.4 degrees so the pitch
#     lies on the axes: the ends 7.5 m behind the goal lines, the long sides
#     7.5 and 9 m from the touchlines; the south end, the east stand and the
#     north end one U with filled, open-air corners, the west (main) stand on
#     its own with an open corner at either end, where the ends turn away in a
#     slanting wall
#   - every stand as on the photos: a first ring of grey seats, a walkway with
#     the tunnel mouths, the front of the second ring with a band of boards,
#     the second ring up to a row of windows under a flat roof on deep black
#     girders, light panels along its front, a black fascia with a green edge
#     and pale green sheeting on top; yellow rails everywhere
#   - the seats: the north end (the Blue Army's) blue with JAN BREYDEL
#     STADION in light seats and white flanks, the south end green and grey
#     (Cercle), the long sides blocks of orange, black and grey, the
#     south-east corner orange; which end is which follows from the sun and
#     the shadows on the photos and from the main stand standing free
#   - the scoreboard in the open south-west corner on a steel frame, a cloth
#     hung under it, as on the photos: adverts, under them a blue bar with
#     the badges, the score and the clock (game.screen.js, 'janbreydel');
#     next to it the away section behind tall yellow fences
#   - four flags on white poles in the north-east corner, as on the photos
#     from the main stand: Brugge, Europe, Belgium, Flanders
#   - four lattice floodlight masts in the corners, a row of lamps along the
#     front of both long roofs; the roofs' girders bare light concrete
#   - outside, as on the photo of the main entrance: bare concrete, the
#     stepped underside of the second ring open to the street on its raking
#     beams, square columns and stair piers, the roofs' raking arms rising
#     out over the back, under them the ground floor set back with its row
#     of windows, the gates and in the middle of the west stand the main
#     entrance (BLUVN GOAN, WELKOM, FCB KAFFEE) with two club flags
#   - round it the Olympiapark from OpenStreetMap: the training pitches, the
#     car parks, the roads, the sports halls and the houses
# No sponsors: the boards carry the clubs' and the city's own words.
#
# The helpers, the goals and the export are those of tools/montjuic_build.py;
# units are metres, x towards the north (the left of the match camera), y
# towards the west (the camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'jan_breydel')
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
XF, YE, YW = 60.0, -41.5, 43.0   # the fronts: both ends, the east stand, the west stand
RC = 4.0                         # the corners of the U at the front (they grow with every row)
S_TIP, N_TIP = 61.0, 70.0        # how far west the ends' straights run before the slanting walls cut them
WALL_Z = 1.2                     # the wall round the pitch
LOW = dict(r=0.3, z=1.6, rows=15, depth=0.80, rise=0.42)             # to d 12.3, z 7.5
LOW_BACK = LOW['r'] + LOW['depth'] * LOW['rows']
LOW_TOP = LOW['z'] + LOW['rise'] * (LOW['rows'] - 1)
WALK_Z = LOW_TOP + 0.4           # the walkway between the rings
BAL_D, BAL_Z = 14.0, WALK_Z + 2.3                                    # the front of the second ring
UP = dict(r=14.2, z=BAL_Z + 0.3, rows=21, depth=0.80, rise=0.58)    # to d 31.0, z 22.1
UP_BACK = UP['r'] + UP['depth'] * UP['rows']
UP_TOP = UP['z'] + UP['rise'] * (UP['rows'] - 1)
BACK_D = UP_BACK + 0.4           # the back wall
GF_ROW, SOFFIT = 3, 0.45         # outside: the ground floor's wall stands under the second ring's 4th row,
GF_D = UP['r'] + UP['depth'] * GF_ROW                                # the ring's underside steps up behind it, 0.45 m
GF_TOP = UP['z'] + UP['rise'] * GF_ROW - SOFFIT                      # under the treads, open to the street
SCR_W, SCR_H = 10.0, 6.8         # the scoreboard in the open south-west corner, between the south end and the main stand
SCR_C = Vector((-70.5, 60.0, 18.0))
SCR_N = Vector((0.8, -0.6, 0.0)).normalized()                        # it faces the pitch
AWAY_Y = 22.0                    # the away section: the south end west of this aisle, behind tall yellow fences
ROOF_D0, ROOF_D1 = 11.6, BACK_D + 0.9                                # the roof: its front edge, its eave
ROOF_U0, ROOF_U1 = 25.8, 25.0    # its underside at the front and the back
ROOF_T0, ROOF_T1 = 27.1, 27.6    # its top
PARAPET_Z = UP_TOP + 1.1         # the back of the open corners
GAIN = 2.0                       # the game draws the model unlit at this gain (catalog: look.gain)
SEAT_W, AISLE_W = 0.5, 1.1
N_SOUTH, N_CORNER, N_EAST, N_NORTH, N_WEST = 15, 12, 16, 16, 16
MASTS = [(-85.0, -67.0), (85.0, -67.0), (67.0, 63.0), (-80.0, 72.0)]  # the floodlight masts, in the corners
MAST_H = 42.0
# the sun: south-west, 33 degrees up, an October afternoon in Brugge (the
# plan's x is 17 degrees west of north): the west stand's shadow falls
# slanting over the near third of the pitch, as on the photos
SUN_AZ, SUN_EL = math.radians(128), math.radians(33)        # from the plan's x, towards y
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))


def ylim_s(d): return 42.5 + 0.5 * d      # the slanting wall of the south end (OSM)
def ylim_n(d): return 41.0 + 0.85 * d     # and of the north end


# ---------------------------------------------------------------- helpers (as in the Montjuïc script)
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
    # a picture from tools/jan_breydel as linear floats, row 0 at the top
    img = D.images.load(os.path.join(ASSETS, name))
    w, h = img.size
    a = np.empty(w * h * 4, 'f'); img.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1].copy()
    D.images.remove(img)
    a[..., :3] = np.where(a[..., :3] <= 0.04045, a[..., :3] / 12.92, ((a[..., :3] + 0.055) / 1.055) ** 2.4)
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
    for t, p, sg in ((0.0, a, -1), (1.0, b, 1)):
        face(bm, [p - side + Vector((0, 0, z_bot(t))), p + side + Vector((0, 0, z_bot(t))),
                  p + side + Vector((0, 0, z_top(t))), p - side + Vector((0, 0, z_top(t)))], (b - a) * sg, mat)


# ---------------------------------------------------------------- the plan: the stands as paths
# A path is a row of nodes along the front of a stand, each with its outward
# direction; a point at offset d (metres back from the front) lies on the same
# line out at every d. Piece i runs from node i to node i + 1.
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
    side, kind, prm, n = segs[-1]
    if kind == 'line':
        nodes.append((prm[1].copy(), prm[2].copy()))
    else:
        c, r, a0, a1 = prm
        N = Vector((math.cos(a1), math.sin(a1), 0))
        nodes.append((c + N * r, N))
    return nodes, info


# the U: the south end (west to east), its corner, the east stand (south to
# north), the north-east corner, the north end (east to west)
U_PATH = make_path([
    ('S', 'line', (V2(-XF, S_TIP), V2(-XF, YE + RC), V2(-1, 0)), N_SOUTH),
    ('cS', 'arc', (V2(-XF + RC, YE + RC), RC, math.pi, 1.5 * math.pi), N_CORNER),
    ('E', 'line', (V2(-XF + RC, YE), V2(XF - RC, YE), V2(0, -1)), N_EAST),
    ('cN', 'arc', (V2(XF - RC, YE + RC), RC, 1.5 * math.pi, 2 * math.pi), N_CORNER),
    ('N', 'line', (V2(XF, YE + RC), V2(XF, N_TIP), V2(1, 0)), N_NORTH),
])
# the west stand, north to south
W_PATH = make_path([('W', 'line', (V2(XF - RC, YW), V2(-XF + RC, YW), V2(0, 1)), N_WEST)])
PATHS = [U_PATH, W_PATH]
SIDE_RANGE = {}                  # the pieces of each part: (path, first, last + 1)
for path in PATHS:
    for i, (side, k, n) in enumerate(path[1]):
        if k == 0:
            SIDE_RANGE[side] = (path, i, i + n)


def P(path, i, u, d):
    (Fa, Na), (Fb, Nb) = path[0][i], path[0][i + 1]
    return (Fa + Na * d).lerp(Fb + Nb * d, u)


def span(path, i, d):
    # the part of piece i that stands at offset d: (u0, u1), or None; the ends
    # are cut by their slanting walls on the west
    side = path[1][i][0]
    if side == 'S':
        ya, yb = path[0][i][0].y, path[0][i + 1][0].y
        lim = ylim_s(d)
        if yb >= lim:
            return None
        return ((ya - lim) / (ya - yb) if ya > lim else 0.0, 1.0)
    if side == 'N':
        ya, yb = path[0][i][0].y, path[0][i + 1][0].y
        lim = ylim_n(d)
        if ya >= lim:
            return None
        return (0.0, (lim - ya) / (yb - ya) if yb > lim else 1.0)
    return (0.0, 1.0)


def is_aisle(path, i):
    # a stairway at node i: where one part of a stand meets the next, every
    # second piece of a straight (sections of 13-14 m), every third of a corner
    nodes, info = path
    if i <= 0 or i >= len(nodes) - 1:
        return False
    side, k, n = info[i]
    if k == 0:
        return True
    return k % (3 if side.startswith('c') else 2) == 0


def is_mid(path, i):
    nodes, info = path
    if i <= 0 or i >= len(nodes) - 1:
        return False
    side, k, n = info[i]
    return not side.startswith('c') and k % 2 == 1


def cumlen(path, d):
    c = [0.0]
    for i in range(len(path[1])):
        c.append(c[-1] + (P(path, i, 1, d) - P(path, i, 0, d)).length)
    return c


def ring(bm, d0, z0, d1, z1, mat, want=None, step=3.0, zstep=None, u_len=None, v=(0, 1), keep=None, paths=None):
    # a strip from offset d0 at height z0 to d1 at z1 along the stands; when
    # d0 == d1 a wall, cut in bands of `zstep`
    for path in (paths or PATHS):
        nodes, info = path
        cum = cumlen(path, d0)
        for i in range(len(info)):
            if keep and not keep(path, i):
                continue
            sa, sb = span(path, i, d0), span(path, i, d1)
            if sa is None or sb is None:
                continue
            Lf = cum[i + 1] - cum[i]
            out = (nodes[i][1] + nodes[i + 1][1]).normalized()
            w = {'up': UPV, 'down': -UPV, 'out': out, 'in': -out}.get(want) if isinstance(want, str) else want
            if w is None:
                w = UPV if abs(z1 - z0) < 1e-6 else -out
            la = (P(path, i, sa[1], d0) - P(path, i, sa[0], d0)).length
            lb = (P(path, i, sb[1], d1) - P(path, i, sb[0], d1)).length
            n = max(1, math.ceil(max(la, lb) / step))
            bands = [(z0, z1, v[0], v[1])]
            if zstep and abs(d1 - d0) < 1e-6 and abs(z1 - z0) > zstep:
                m = math.ceil(abs(z1 - z0) / zstep)
                bands = [(z0 + (z1 - z0) * j / m, z0 + (z1 - z0) * (j + 1) / m,
                          v[0] + (v[1] - v[0]) * j / m, v[0] + (v[1] - v[0]) * (j + 1) / m) for j in range(m)]
            for s in range(n):
                t0, t1 = s / n, (s + 1) / n
                ua, ub = sa[0] + (sa[1] - sa[0]) * t0, sa[0] + (sa[1] - sa[0]) * t1
                va, vb = sb[0] + (sb[1] - sb[0]) * t0, sb[0] + (sb[1] - sb[0]) * t1
                p0, p1 = P(path, i, ua, d0), P(path, i, ub, d0)
                q0, q1 = P(path, i, va, d1), P(path, i, vb, d1)
                for za, zb, v0, v1 in bands:
                    uvs = None
                    if u_len:
                        c0_, c1_ = (cum[i] + Lf * ua) / u_len, (cum[i] + Lf * ub) / u_len
                        uvs = [(c0_, v0), (c1_, v0), (c1_, v1), (c0_, v1)]
                    face(bm, [(p0.x, p0.y, za), (p1.x, p1.y, za), (q1.x, q1.y, zb), (q0.x, q0.y, zb)], w, mat, uvs)


def tread_z(d):
    if d < LOW['r']:
        return WALL_Z
    if d < LOW_BACK:
        return LOW['z'] + LOW['rise'] * min(LOW['rows'] - 1, int((d - LOW['r']) / LOW['depth']))
    if d < BAL_D:
        return WALK_Z
    if d < UP['r']:
        return BAL_Z
    if d < UP_BACK:
        return UP['z'] + UP['rise'] * min(UP['rows'] - 1, int((d - UP['r']) / UP['depth']))
    return UP_TOP


def roof_under(d): return ROOF_U0 + (ROOF_U1 - ROOF_U0) * (d - ROOF_D0) / (ROOF_D1 - ROOF_D0)
def roof_top(d): return ROOF_T0 + (ROOF_T1 - ROOF_T0) * (d - ROOF_D0) / (ROOF_D1 - ROOF_D0)


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1975)


def vnoise(h, w, cy, cx):
    g = rng.normal(0, 1, (h // cy + 3, w // cx + 3)).astype('f')
    yy, xx = np.arange(h, dtype='f') / cy, np.arange(w, dtype='f') / cx
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    return (g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0 + 1][:, x0] * fy * (1 - fx)
            + g[y0][:, x0 + 1] * (1 - fy) * fx + g[y0 + 1][:, x0 + 1] * fy * fx)


def seat_tile(color):
    t = np.zeros((32, 32, 3), 'f')
    t[:] = np.array(color, 'f') * np.linspace(0.80, 1.0, 32)[:, None, None]
    t[:, :2] *= 0.35; t[:, -2:] *= 0.35
    t[-2:] *= 1.08
    return t


def roof_under_tex():
    # the sheeting under the roof: dark ribbed panels (u along the stand, 8 m)
    w, h = 256, 64
    t = np.ones((h, w, 3), 'f') * np.array((0.16, 0.165, 0.17), 'f')
    t[:, (np.arange(w) % 8) < 2] *= 0.6
    t *= (1 + 0.05 * vnoise(h, w, 16, 16))[..., None]
    return t


def glazing_tex():
    # the row of windows at the back of the second ring (u: 6 m, v: the band)
    w, h = 384, 128
    t = np.ones((h, w, 3), 'f')
    yy = np.linspace(0, 1, h)[:, None, None]
    t[:] = np.array((0.045, 0.06, 0.075), 'f') * (0.7 + 0.6 * yy)
    t[:, (np.arange(w) % 64) < 4] = (0.55, 0.56, 0.56)
    t[:5] = (0.55, 0.56, 0.56)
    t[int(h * 0.62):int(h * 0.62) + 3] = (0.55, 0.56, 0.56)
    t[-5:] = (0.55, 0.56, 0.56)
    return t


def clad_tex():
    # the white cladding of the stands' ends: tall panels, 1.2 m apart (4.8 m a repeat)
    w, h = 128, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.60, 0.61, 0.62), 'f')
    t[:, (np.arange(w) % 32) < 2] *= 0.72
    t[(np.arange(h) % 128) < 2] *= 0.8
    t *= (1 + 0.03 * vnoise(h, w, 32, 32))[..., None]
    return t


def ground_floor_tex():
    # the ground floor under the second ring (u: 24 m, v: its wall, 0 to
    # GF_TOP): the gates and the concrete, the dark panels, the row of
    # windows of the concourse under the ring's underside
    w, h = 768, int(GF_TOP * 32)
    zpx = lambda z: int(z * 32)
    t = np.ones((h, w, 3), 'f') * np.array((0.31, 0.31, 0.30), 'f')
    t *= (1 + 0.05 * vnoise(h, w, 40, 40) + 0.02 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    for k in range(4):                                       # the gates and the dark panels between them, 6 m a bay
        x0 = int(k * 6 * 32)
        t[zpx(0.1):zpx(2.9), x0 + 20:x0 + 20 + 4 * 32] = (0.03, 0.035, 0.04)
        t[zpx(0.1):zpx(2.9), x0 + 20:x0 + 20 + 4 * 32][:, ::10] = (0.30, 0.25, 0.04)
        t[zpx(3.1):zpx(7.2), x0 + 30:x0 + 30 + 2 * 32] = (0.06, 0.05, 0.045)
    t[zpx(2.9):zpx(3.3)] *= 0.6
    t[zpx(7.4):zpx(10.4)] = (0.30, 0.34, 0.38)               # the windows: sky in the glass
    t[zpx(7.4):zpx(10.4)] *= np.linspace(0.85, 1.15, zpx(10.4) - zpx(7.4))[:, None, None]
    t[zpx(7.4):zpx(10.4), (np.arange(w) % 38) < 4] = (0.62, 0.63, 0.62)
    t[zpx(7.3):zpx(7.5)] = (0.62, 0.63, 0.62)
    t[zpx(10.3):zpx(10.5)] = (0.62, 0.63, 0.62)
    return t


def slats_tex():
    # the top of the back of the stands: dark horizontal slats (u: 8 m)
    w, h = 256, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.05, 0.052, 0.056), 'f')
    t[(np.arange(h) % 16) < 6] = (0.17, 0.17, 0.17)
    return t


def office_tex():
    # the back of the west stand: offices, five floors of windows (u: 24 m, v: 25 m)
    w, h = 768, 800
    t = np.ones((h, w, 3), 'f') * np.array((0.33, 0.33, 0.32), 'f')
    t *= (1 + 0.04 * vnoise(h, w, 40, 40))[..., None]
    for z0 in (1.0, 5.0, 9.0, 13.0, 17.0):
        y0, y1 = int(z0 / 25 * h), int((z0 + 2.2) / 25 * h)
        for k in range(16):
            x0 = int((k * 1.5 + 0.2) / 24 * w)
            t[y0:y1, x0:x0 + int(1.1 / 24 * w)] = (0.04, 0.05, 0.06)
    return t


def foliage_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.045, 0.085, 0.03), 'f')
    t *= (1 + 0.35 * vnoise(h, w, 6, 6) + 0.2 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


SEATS = [(0.13, 0.135, 0.14), (0.15, 0.155, 0.16), (0.17, 0.175, 0.18),      # 0-2: the grey first rings
         (0.36, 0.37, 0.38),                                                   # 3: light grey
         (0.025, 0.11, 0.46),                                                  # 4: Club blue
         (0.62, 0.68, 0.78),                                                   # 5: the letters: pale, almost white
         (0.015, 0.22, 0.13),                                                  # 6: Cercle green
         (0.58, 0.13, 0.025),                                                  # 7: orange
         (0.022, 0.023, 0.026),                                                # 8: black
         (0.50, 0.51, 0.52)]                                                   # 9: white
GREY, LGREY, BLUE, LETTER, GREEN, ORANGE, BLACK, WHITE = 0, 3, 4, 5, 6, 7, 8, 9
seat_cols = [image_material('M_Seat%d' % i, painted('jb_seat%d' % i, seat_tile(c)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.33, 0.33, 0.32), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.22, 0.22, 0.21), 0.9)
concrete_light = principled('M_ConcreteLight', (0.44, 0.44, 0.42), 0.85)
portal = principled('M_Portal', (0.015, 0.015, 0.018), 0.95)
rail_yellow = principled('M_RailYellow', (0.75, 0.50, 0.012), 0.5)
steel_dark = principled('M_SteelDark', (0.042, 0.044, 0.048), 0.6)
steel_grey = principled('M_SteelGrey', (0.30, 0.31, 0.32), 0.5)
girder_mat = principled('M_Girder', (0.34, 0.34, 0.33), 0.85)                     # the roofs' girders: bare concrete
fascia_mat = principled('M_Fascia', (0.09, 0.095, 0.10), 0.6)
flags_mat = image_material('M_Flags', load_asset('flags.png'), 0.8)
roof_green = principled('M_RoofGreen', (0.25, 0.40, 0.31), 0.6)
roof_under_mat = image_material('M_RoofUnder', painted('jb_roofunder', roof_under_tex()), 0.7)
roof_light = principled('M_RoofLight', (0.34, 0.36, 0.38), 0.5)                  # the light panels: lit by the sky through them
glazing = image_material('M_Glazing', painted('jb_glazing', glazing_tex()), 0.2)
clad = image_material('M_Clad', painted('jb_clad', clad_tex()), 0.6)
ground_floor = image_material('M_GroundFloor', painted('jb_groundfloor', ground_floor_tex()), 0.85)
slats = image_material('M_Slats', painted('jb_slats', slats_tex()), 0.7)
entrance_mat = image_material('M_Entrance', load_asset('entrance.png'), 0.6)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
band_mat = image_material('M_Band', load_asset('band.png'), 0.6)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
dark_glass = principled('M_DarkGlass', (0.03, 0.035, 0.04), 0.15)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
foliage = image_material('M_Foliage', painted('jb_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
brick = principled('M_Brick', (0.26, 0.12, 0.07), 0.9)
plaster = principled('M_Plaster', (0.50, 0.48, 0.44), 0.9)
tiles = principled('M_Tiles', (0.13, 0.07, 0.05), 0.8)
flat_roof = principled('M_FlatRoof', (0.12, 0.12, 0.125), 0.9)
hall_wall = principled('M_HallWall', (0.36, 0.37, 0.38), 0.8)
white_paint = principled('M_WhitePaint', (0.80, 0.80, 0.78), 0.7)

# ================================================================ the pitch lines, the goals (as in the Montjuïc script)
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

net_tile = np.zeros((32, 32, 4), 'f')
net_tile[..., :3] = 0.92
net_tile[:3, :, 3] = 1.0; net_tile[:, :3, 3] = 1.0
net_img = D.images.new('jb_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/jb_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
net_mat = image_material('M_Net', net_img, 0.8)
nn = net_mat.node_tree
nn.links.new(next(n for n in nn.nodes if n.type == 'TEX_IMAGE').outputs['Alpha'], next(n for n in nn.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Alpha'])
for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
    try:
        setattr(net_mat, attr, val)
    except Exception:
        pass
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
    m = 1.0 / MESH
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
# and, under it, the ground inside the stands (the tarmac behind the boards);
# each gets its own picture with the sun baked in (below)
PITCH_X, PITCH_Y = 56.0, 38.0
FLOOR_X, FLOOR_Y = XF + 0.6, YW + 0.6
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-PITCH_X, -PITCH_Y), (PITCH_X, -PITCH_Y), (PITCH_X, PITCH_Y), (-PITCH_X, PITCH_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.06, 0.20, 0.045), 0.85)])
FLOOR_Z = -0.05                  # under the pitch, far enough that the two never flicker
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
f = bm.faces.new([bm.verts.new((x, y, FLOOR_Z)) for x, y in ((-FLOOR_X, -FLOOR_Y), (FLOOR_X, -FLOOR_Y), (FLOOR_X, FLOOR_Y), (-FLOOR_X, FLOOR_Y))])
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.06, 0.06, 0.06), 0.9)])

# ================================================================ the stands
JB_MASK = asset_pixels('jan_breydel.png')[..., 0] > 0.5        # JAN BREYDEL, one pixel a seat
ST_MASK = asset_pixels('stadion.png')[..., 0] > 0.5            # STADION
LETTER_YC = 4.2                  # the middle of the lettering, on the north end
EAST_SEQ = [LGREY, ORANGE, BLACK, ORANGE, BLACK, ORANGE, BLACK, LGREY]     # the long sides, block by block
WEST_SEQ = [LGREY, BLACK, ORANGE, BLACK, BLACK, ORANGE, BLACK, LGREY]
SOUTH_SEQ = [GREEN, LGREY, GREEN, GREEN, LGREY, GREEN, GREEN, LGREY]     # Cercle's end, west to east


def letter_at(row, y):
    # JAN BREYDEL in the back half of the north end's second ring, STADION
    # under it; read from the pitch the words run from west to east (-y)
    if 12 <= row <= 19:
        m, g = JB_MASK, 19 - row
    elif 1 <= row <= 8:
        m, g = ST_MASK, 8 - row
    else:
        return False
    c = int(math.floor((LETTER_YC - y) / SEAT_W + m.shape[1] / 2))
    return 0 <= c < m.shape[1] and bool(m[g, c])


def seat_colour(tier, side, ks, ns, row, p, h):
    if tier == 'low':
        return h % 3
    if side == 'N':
        if p.y > 40.0:
            return WHITE                                   # the slanting west flank
        return LETTER if letter_at(row, p.y) else BLUE
    if side == 'S':
        return SOUTH_SEQ[min(7, ks // 2)]
    if side == 'E':
        return EAST_SEQ[min(7, ks // 2)]
    if side == 'W':
        return WEST_SEQ[min(7, ks // 2)]
    if side == 'cS':
        return ORANGE                                      # the south-east corner, orange from the air
    return WHITE                                           # the north-east corner, white next to the blue


def hole(path, tier, row, p):
    # the players' tunnel through the first ring of the west stand
    return path is W_PATH and tier == 'low' and row < 7 and abs(p.x) < 2.4


def screen_spot(path, tier, row, p):
    # no seats where the big screen stands on its frame
    return False


def dark_spot(path, tier, row, i, u, L):
    # the tunnel mouths: in the top rows of the first ring, every other
    # section; half way up the second ring, every section, between the two
    # lines of letters on the north end as on the photos
    if tier == 'low':
        if row < LOW['rows'] - 5:
            return False
        sel = lambda j: is_mid(path, j) and (path[1][j][1] // 2) % 2 == 0
    else:
        if not (9 <= row <= 11):
            return False
        sel = lambda j: is_mid(path, j)
    d = None
    if sel(i + 1):
        d = (1 - u) * L
    elif sel(i):
        d = u * L
    return d is not None and d < 1.4


def seat_pair(bm, pa, pb, back, m, q, q1):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
    face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UPV, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])


def build_tier(name, t, base_z, tier):
    steps, seats, aisles, dark, soffit = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    for path in PATHS:
        nodes, info = path
        for k in range(t['rows']):
            r0, r1, z = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1), t['z'] + t['rise'] * k
            z_prev = base_z if k == 0 else z - t['rise']
            for i in range(len(info)):
                side, ks, ns = info[i]
                sa, sb = span(path, i, r0), span(path, i, r1)
                if sa is None or sb is None:
                    continue
                A = lambda u: P(path, i, u, r0)
                B = lambda u: P(path, i, u, r1)
                L = (A(1.0) - A(0.0)).length
                back = (B(0.5) - A(0.5)).normalized()
                n = max(1, math.ceil(L * (sa[1] - sa[0]) / 3.0))
                # the tread and the riser in front of it, in pieces
                for s in range(n):
                    t0, t1 = s / n, (s + 1) / n
                    a0, a1 = A(sa[0] + (sa[1] - sa[0]) * t0), A(sa[0] + (sa[1] - sa[0]) * t1)
                    b0, b1 = B(sb[0] + (sb[1] - sb[0]) * t0), B(sb[0] + (sb[1] - sb[0]) * t1)
                    if hole(path, tier, k, (a0 + a1 + b0 + b1) / 4):
                        continue
                    face(steps, [(a0.x, a0.y, z), (a1.x, a1.y, z), (b1.x, b1.y, z), (b0.x, b0.y, z)], UPV, 0)
                    face(steps, [(a0.x, a0.y, z_prev), (a1.x, a1.y, z_prev), (a1.x, a1.y, z), (a0.x, a0.y, z)], -back, 1)
                    if tier == 'up' and k >= GF_ROW:
                        # the ring's underside, stepping up and out over the street
                        zs = z - SOFFIT
                        face(soffit, [(a0.x, a0.y, zs), (a1.x, a1.y, zs), (b1.x, b1.y, zs), (b0.x, b0.y, zs)], -UPV, 0)
                        if k < t['rows'] - 1:
                            face(soffit, [(b0.x, b0.y, zs), (b1.x, b1.y, zs), (b1.x, b1.y, zs + t['rise']), (b0.x, b0.y, zs + t['rise'])], back, 0)
                # the stairs at the ends of the piece
                cut0 = AISLE_W / 2 if (is_aisle(path, i) and sa[0] == 0.0) else 0.0
                cut1 = AISLE_W / 2 if (is_aisle(path, i + 1) and sa[1] == 1.0) else 0.0
                for u0, u1 in ([(0.0, cut0 / L)] if cut0 else []) + ([(1 - cut1 / L, 1.0)] if cut1 else []):
                    f0, f1, g0, g1 = A(u0), A(u1), B(u0), B(u1)
                    if hole(path, tier, k, (f0 + f1 + g0 + g1) / 4):
                        continue
                    F0, F1, G0, G1 = (Vector((v_.x, v_.y, z)) + lift for v_ in (f0, f1, g0, g1))
                    face(aisles, [F0, F1, G1, G0], UPV, 0)
                    if k:
                        down, out_ = Vector((0, 0, -t['rise'])), -back * 0.012
                        face(aisles, [F0 + down + out_, F1 + down + out_, F1 + out_, F0 + out_], -back, 0)
                # the seats
                us0, us1 = max(sa[0], sb[0]), min(sa[1], sb[1])
                c0 = cut0 / L if us0 == 0.0 else us0 + 0.3 / L
                c1 = 1 - cut1 / L if us1 == 1.0 else us1 - 0.3 / L
                usable = (c1 - c0) * L
                if usable < SEAT_W:
                    continue
                nseat = max(1, round(usable / SEAT_W))
                mats = []
                for q in range(nseat):
                    u = c0 + (c1 - c0) * (q + 0.5) / nseat
                    p = A(u).lerp(B(u), 0.5)
                    if hole(path, tier, k, p) or screen_spot(path, tier, k, p):
                        mats.append(None)
                        continue
                    if dark_spot(path, tier, k, i, u, L):
                        mats.append('dark')
                        continue
                    h = (k * 73856093) ^ (i * 19349663) ^ ((q // 3) * 83492791)
                    mats.append(seat_colour(tier, side, ks, ns, k, p, h))
                # the dark tunnel mouths, a yellow rail round each
                q = 0
                while q < nseat:
                    if mats[q] != 'dark':
                        q += 1
                        continue
                    q1 = q
                    while q1 < nseat and mats[q1] == 'dark':
                        q1 += 1
                    u0, u1 = c0 + (c1 - c0) * q / nseat, c0 + (c1 - c0) * q1 / nseat
                    f0, f1, g0, g1 = A(u0), A(u1), B(u0), B(u1)
                    F0, F1, G0, G1 = (Vector((v_.x, v_.y, z)) + lift for v_ in (f0, f1, g0, g1))
                    face(dark, [F0, F1, G1, G0], UPV, 0)
                    down, out_ = Vector((0, 0, -t['rise'])), -back * 0.012
                    face(dark, [F0 + down + out_, F1 + down + out_, F1 + out_, F0 + out_], -back, 0)
                    if (tier == 'up' and k == 11) or (tier == 'low' and k == LOW['rows'] - 1):
                        for g in (G0, G1):
                            tube(dark, g, g + Vector((0, 0, 1.0)), 0.035, 1, 5)
                        tube(dark, G0 + Vector((0, 0, 1.0)), G1 + Vector((0, 0, 1.0)), 0.035, 1, 5)
                    q = q1
                q = 0
                while q < nseat:
                    m = mats[q]
                    if m is None or m == 'dark':
                        q += 1
                        continue
                    q1 = q + 2 if q + 1 < nseat and mats[q + 1] == m else q + 1
                    us = [c0 + (c1 - c0) * qq / nseat for qq in (q, q1)]
                    pa = [A(uu) + Vector((0, 0, z)) for uu in us]
                    pb = [B(uu) + Vector((0, 0, z)) for uu in us]
                    seat_pair(seats, pa, pb, back, m, q, q1)
                    q = q1
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Aisles_' + name, aisles, '02_Bowl', [concrete_light])
    new_obj('Portals_' + name, dark, '02_Bowl', [portal, rail_yellow])
    if tier == 'up':
        new_obj('Soffit_' + name, soffit, '02_Bowl', [concrete])
    else:
        soffit.free()


random.seed(1975)
t0 = time.time()
build_tier('Lower', LOW, WALL_Z, 'low')
build_tier('Upper', UP, BAL_Z, 'up')
print('STANDS %.0fs' % (time.time() - t0))

# the wall round the pitch, the walkway, the front of the second ring with
# its band of boards, the back wall: the windows under the roof, the parapet
# of the open corners
straight = lambda path, i: not path[1][i][0].startswith('c')
corner = lambda path, i: path[1][i][0].startswith('c')
bm = bmesh.new()
ring(bm, 0.0, 0.0, 0.0, WALL_Z, 0, want='in')
ring(bm, 0.0, WALL_Z, LOW['r'], WALL_Z, 0, want='up')
ring(bm, LOW_BACK, LOW_TOP, LOW_BACK, WALK_Z, 1, want='in')
ring(bm, LOW_BACK, WALK_Z, BAL_D, WALK_Z, 2, want='up')
ring(bm, BAL_D, WALK_Z, BAL_D, WALK_Z + 1.1, 0, want='in')
ring(bm, BAL_D, WALK_Z + 1.1, BAL_D, WALK_Z + 2.1, 3, want='in', u_len=-48.0)   # u against the path: the words read from the pitch
ring(bm, BAL_D, WALK_Z + 2.1, BAL_D, BAL_Z, 0, want='in')
ring(bm, BAL_D, BAL_Z, UP['r'], BAL_Z, 2, want='up')
ring(bm, UP_BACK, UP_TOP, BACK_D, UP_TOP, 2, want='up')
ring(bm, BACK_D, UP_TOP, BACK_D, UP_TOP + 0.5, 0, want='in', keep=straight)
ring(bm, BACK_D, UP_TOP + 0.5, BACK_D, roof_under(BACK_D), 4, want='in', keep=straight, u_len=-6.0)
ring(bm, BACK_D, UP_TOP, BACK_D, PARAPET_Z, 0, want='in', keep=corner)
ring(bm, BACK_D, PARAPET_Z, BACK_D + 0.35, PARAPET_Z, 0, want='up', keep=corner)
new_obj('Fronts', bm, '02_Bowl', [concrete, concrete_dark, concrete_light, band_mat, glazing])

# the outside of the stands, as on the photo of the main entrance: the
# ground floor's wall set back under the second ring, whose underside steps
# up and out over the street to the back of the ring; on top the back wall
# with its dark slats (the open corners: their parapet)
bm = bmesh.new()
OUT_D = BACK_D + 0.3
ring(bm, GF_D, 0.0, GF_D, GF_TOP, 0, want='out', zstep=1.5, u_len=24.0)
ring(bm, UP_BACK, UP_TOP - SOFFIT, OUT_D, UP_TOP - SOFFIT, 2, want='down')
ring(bm, OUT_D, UP_TOP - SOFFIT, OUT_D, roof_under(OUT_D), 1, want='out', keep=straight, u_len=8.0)
ring(bm, OUT_D, UP_TOP - SOFFIT, OUT_D, PARAPET_Z, 2, want='out', keep=corner)
# the raking beams under the ring at every node (every third in the corners),
# a square column under every other one, a stair pier under every fourth of
# the straights, the roofs' raking arms over the back at every girder
soffit_line = lambda d: UP['z'] - SOFFIT + UP['rise'] / UP['depth'] * (d - UP['r']) + 0.05
for path in PATHS:
    nodes, info = path
    for i in range(1, len(nodes) - 1):
        side, k, n = info[i]
        if side.startswith('c') and k % 3:
            continue
        sp = span(path, i, GF_D)
        if sp is None or sp[0] > 0.0 or span(path, i - 1, GF_D) is None:
            continue
        a_, b_ = P(path, i, 0.0, GF_D - 0.3), P(path, i, 0.0, UP_BACK - 0.4)
        d0_, d1_ = GF_D - 0.3, UP_BACK - 0.4
        prism(bm, a_, b_, 0.7, (lambda d0, d1: (lambda t: soffit_line(d0 + (d1 - d0) * t)))(d0_, d1_),
              (lambda d0, d1: (lambda t: soffit_line(d0 + (d1 - d0) * t) - 1.2))(d0_, d1_), 3)
        out = nodes[i][1]
        entrance = path is W_PATH and abs(nodes[i][0].x) < 12.0          # keep the main entrance clear
        if is_aisle(path, i) and not entrance:
            pc = P(path, i, 0.0, 27.0)
            box(bm, pc, out, 0.38, (-out.y, out.x), 0.38, 0.0, soffit_line(27.0) - 1.1, 3, False, False)
        if not side.startswith('c') and k % 4 == 0 and not entrance:
            pa_, pb_ = P(path, i, 0.0, GF_D), P(path, i, 0.0, GF_D + 3.2)
            prism(bm, pa_, pb_, 2.6, (lambda t: soffit_line(GF_D + 3.2 * t)), (lambda t: 0.0), 3, step=1.6)
        if not side.startswith('c'):
            sp2 = span(path, i, OUT_D)
            if sp2 and sp2[0] == 0.0:
                pa_, pb_ = P(path, i, 0.0, OUT_D - 0.2), P(path, i, 0.0, OUT_D + 6.5)
                prism(bm, pa_, pb_, 1.15, (lambda t: ROOF_U1 + 0.9 + (ROOF_T1 + 3.4 - ROOF_U1 - 0.9) * t),
                      (lambda t: ROOF_U1 + 0.9 + (ROOF_T1 + 3.4 - ROOF_U1 - 0.9) * t - 2.1), 3)
# the main entrance in the middle of the west stand: the banner over the
# doors, WELKOM and FCB KAFFEE over them, the Jan Breydel plaque on a pier
ye = YW + GF_D + 0.25
def plate(x0, x1, z0, z1, u0, u1, v0, v1, y=ye):
    # u runs from east to west: read from the street (facing -y) left is +x
    face(bm, [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)], Vector((0, 1, 0)), 4,
         [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
plate(-8.0, 8.0, 6.0, 8.0, 0.0, 1.0, 1 - 200 / 512, 1.0)
plate(0.6, 4.6, 3.05, 3.9, 0.0, 0.5, 1 - 330 / 512, 1 - 210 / 512)
plate(-4.6, -0.6, 3.05, 3.9, 0.5, 1.0, 1 - 330 / 512, 1 - 210 / 512)
plate(9.3, 11.3, 4.0, 5.6, 0.0, 0.5, 0.0, 172 / 512, y=ye + 0.05)
abox(bm, -8.3, 8.3, ye - 0.25, ye - 0.02, 5.8, 8.2, 3, True, True)
new_obj('Outside', bm, '02_Bowl', [ground_floor, slats, concrete, girder_mat, entrance_mat])


# the ends of the stands that stand free: the slanting walls of both ends
# (towards the west stand) and the west stand's two ends; concrete low down,
# white panels high up, closed up to the roof
def top_right(d):
    return roof_under(d) if d >= ROOF_D0 else tread_z(d) + 1.05


def top_left(d):
    return roof_under(d) if d > ROOF_D0 + 1e-6 else tread_z(d - 1e-4) + 1.05


def side_wall(bm, pfun, nrm, th=0.3, step=0.4, zstep=1.6):
    ds = []
    d = 0.0
    while d < BACK_D - 1e-6:
        ds.append(d)
        nd = round(d + step, 4)
        if d < ROOF_D0 < nd:
            nd = ROOF_D0
        d = nd
    ds.append(BACK_D)
    o = Vector((nrm.x, nrm.y, 0)).normalized() * (th / 2)
    for j in range(len(ds) - 1):
        da, db = ds[j], ds[j + 1]
        ta, tb = top_right(da), top_left(db)
        pa, pb = pfun(da), pfun(db)
        m = max(1, math.ceil(max(ta, tb) / zstep))
        for s in (-1, 1):
            for q in range(m):
                za0, za1, zb0, zb1 = ta * q / m, ta * (q + 1) / m, tb * q / m, tb * (q + 1) / m
                mat = 1 if (za0 + za1) / 2 > BAL_Z + 0.5 else 0
                face(bm, [pa + o * s + Vector((0, 0, za0)), pb + o * s + Vector((0, 0, zb0)),
                          pb + o * s + Vector((0, 0, zb1)), pa + o * s + Vector((0, 0, za1))], o * s, mat,
                     [(da / 4.8 * s, za0 / 4.8), (db / 4.8 * s, zb0 / 4.8), (db / 4.8 * s, zb1 / 4.8), (da / 4.8 * s, za1 / 4.8)])
        face(bm, [pa - o + Vector((0, 0, ta)), pb - o + Vector((0, 0, tb)), pb + o + Vector((0, 0, tb)), pa + o + Vector((0, 0, ta))], UPV, 0)
    # the wall's front edge, and the step up to the roof where the roof begins
    fwd = pfun(0.0) - pfun(1.0)
    p0 = pfun(0.0)
    face(bm, [p0 - o, p0 + o, p0 + o + Vector((0, 0, top_right(0.0))), p0 - o + Vector((0, 0, top_right(0.0)))], fwd, 0)
    pr = pfun(ROOF_D0)
    zlo = top_left(ROOF_D0)
    face(bm, [pr - o + Vector((0, 0, zlo)), pr + o + Vector((0, 0, zlo)), pr + o + Vector((0, 0, ROOF_U0)), pr - o + Vector((0, 0, ROOF_U0))], fwd, 1)


bm = bmesh.new()
# the wing at the north end of the west stand (OSM): a block of offices and
# lifts at the north end in white panels, a stair tower at the south end
for poly, h, mat in (([(56.1, 46.5), (60.9, 45.9), (65.2, 52.8), (65.4, 68.9), (60.0, 68.7), (60.2, 72.0), (56.1, 72.0)], 21.0, 1),
):
    n_ = len(poly)
    sarea = sum(poly[k][0] * poly[(k + 1) % n_][1] - poly[(k + 1) % n_][0] * poly[k][1] for k in range(n_))
    for k in range(n_):
        a_, c_ = poly[k], poly[(k + 1) % n_]
        outv = Vector((c_[1] - a_[1], -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
        L_ = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
        for q in range(math.ceil(h / 1.75)):
            za, zb = h * q / math.ceil(h / 1.75), h * (q + 1) / math.ceil(h / 1.75)
            face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, mat,
                 [(0, za / 4.8), (L_ / 4.8, za / 4.8), (L_ / 4.8, zb / 4.8), (0, zb / 4.8)])
    rf = bm.faces.new([bm.verts.new((x, y, h)) for x, y in poly])
    rf.material_index = 0
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
for s, lim, slope in ((-1, ylim_s, 0.5), (1, ylim_n, 0.85)):
    pf = (lambda s_, l_: (lambda d: V2(s_ * (XF + d), l_(d))))(s, lim)
    dvec = V2(s, slope).normalized()
    nrm = V2(-dvec.y, dvec.x)
    if nrm.y < 0:
        nrm = -nrm
    side_wall(bm, pf, nrm)
for s in (-1, 1):
    side_wall(bm, (lambda s_: (lambda d: V2(s_ * (XF - RC), YW + d)))(s), V2(s, 0))
new_obj('Stand_Ends', bm, '02_Bowl', [concrete, clad])


# ================================================================ the roofs: one over each straight
def roof_over(side, lamps=False):
    path, i0, i1 = SIDE_RANGE[side]
    top, under, light, beams, fascia = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    BANDS = [ROOF_D0, ROOF_D0 + 0.7, ROOF_D0 + 6.5, ROOF_D0 + 12.0, ROOF_D0 + 17.0, ROOF_D1]
    cum = cumlen(path, ROOF_D0)
    inside = lambda p, i: i0 <= i < i1
    for i in range(i0, i1):
        for b in range(len(BANDS) - 1):
            da, db = BANDS[b], BANDS[b + 1]
            sa, sb = span(path, i, da), span(path, i, db)
            if sa is None or sb is None:
                continue
            for s in range(3):
                t0, t1 = s / 3, (s + 1) / 3
                p0, p1 = P(path, i, sa[0] + (sa[1] - sa[0]) * t0, da), P(path, i, sa[0] + (sa[1] - sa[0]) * t1, da)
                q0, q1 = P(path, i, sb[0] + (sb[1] - sb[0]) * t0, db), P(path, i, sb[0] + (sb[1] - sb[0]) * t1, db)
                pts = lambda za, zb: [(p0.x, p0.y, za), (p1.x, p1.y, za), (q1.x, q1.y, zb), (q0.x, q0.y, zb)]
                face(top, pts(roof_top(da), roof_top(db)), UPV, 0)
                cu = cum[i] / 8.0
                uvs = [(cu + t0, 0), (cu + t1, 0), (cu + t1, 1), (cu + t0, 1)]
                if b == 1:
                    face(light, pts(roof_under(da), roof_under(db)), -UPV, 0)
                else:
                    face(under, pts(roof_under(da), roof_under(db)), -UPV, 0, uvs)
    # the fascia: black, its green top edge; the eave at the back
    zf = roof_under(ROOF_D0) - 0.4
    ring(fascia, ROOF_D0, zf, ROOF_D0, ROOF_T0 - 0.28, 0, want='in', paths=[path], keep=inside)
    ring(fascia, ROOF_D0, ROOF_T0 - 0.28, ROOF_D0, ROOF_T0, 1, want='in', paths=[path], keep=inside)
    ring(fascia, ROOF_D0, zf, ROOF_D0 + 0.3, zf, 0, want='down', paths=[path], keep=inside)
    ring(fascia, ROOF_D0 + 0.3, zf, ROOF_D0 + 0.3, roof_under(ROOF_D0 + 0.3), 0, want='out', paths=[path], keep=inside)
    ring(fascia, ROOF_D1, roof_under(ROOF_D1), ROOF_D1, roof_top(ROOF_D1), 3, want='out', paths=[path], keep=inside)    # the white edge seen from outside
    # the roof's two ends, closed
    for b in range(len(BANDS) - 1):
        da, db = BANDS[b], BANDS[b + 1]
        ok = [i for i in range(i0, i1) if span(path, i, da) and span(path, i, db)]
        if not ok:
            continue
        for i, end in ((ok[0], 0), (ok[-1], 1)):
            pa, pb = P(path, i, span(path, i, da)[end], da), P(path, i, span(path, i, db)[end], db)
            tan = (P(path, i, 1, da) - P(path, i, 0, da)).normalized() * (1 if end else -1)
            zlo_a = roof_under(da) - (0.4 if b == 0 else 0.0)
            face(fascia, [(pa.x, pa.y, zlo_a), (pb.x, pb.y, roof_under(db)), (pb.x, pb.y, roof_top(db)), (pa.x, pa.y, roof_top(da))], tan, 0)
    # the girders, one at every node: deep at the back, slim at the front
    for i in range(i0, i1 + 1):
        j = min(i, i1 - 1)
        u = 0.0 if i < i1 else 1.0
        d_in = None
        for dd in np.linspace(ROOF_D0 + 0.3, BACK_D, 60):
            sp = span(path, j, dd)
            if sp and sp[0] - 1e-6 <= u <= sp[1] + 1e-6:
                d_in = float(dd)
                break
        if d_in is None or d_in > BACK_D - 3:
            continue
        a, b_ = P(path, j, u, d_in), P(path, j, u, BACK_D)
        span_d = BACK_D - d_in
        prism(beams, a, b_, 0.42, (lambda di, sd: (lambda t: roof_under(di + sd * t) + 0.02))(d_in, span_d),
              (lambda di, sd: (lambda t: roof_under(di + sd * t) - (0.45 + 1.9 * (di + sd * t - ROOF_D0) / (BACK_D - ROOF_D0))))(d_in, span_d), 0)
    if lamps:
        # a row of floodlights along the top of the fascia
        start, end = cum[i0], cum[i1]
        nl = int((end - start) / 4.4)
        for k in range(nl):
            sdist = start + (end - start) * (k + 0.5) / nl
            i = next(ii for ii in range(i0, i1) if cum[ii] <= sdist <= cum[ii + 1])
            u = (sdist - cum[i]) / (cum[i + 1] - cum[i])
            p = P(path, i, u, ROOF_D0 + 0.4)
            out = (path[0][i][1] + path[0][i + 1][1]).normalized()
            tan = Vector((-out.y, out.x, 0))
            tube(beams, p + Vector((0, 0, ROOF_T0)), p + Vector((0, 0, ROOF_T0 + 0.9)), 0.06, 0, 6)
            fwd = (-out * math.cos(math.radians(35)) - UPV * math.sin(math.radians(35))).normalized()
            upl = tan.cross(fwd).normalized()
            if upl.z < 0:
                upl = -upl
            c = p - out * 0.1 + Vector((0, 0, ROOF_T0 + 1.25))
            obox(fascia, c, fwd, tan, upl, 0.25, 0.42, 0.32, 0)
            cc = c + fwd * 0.26
            face(fascia, [cc - tan * 0.36 - upl * 0.26, cc + tan * 0.36 - upl * 0.26, cc + tan * 0.36 + upl * 0.26, cc - tan * 0.36 + upl * 0.26], fwd, 2)
    new_obj('Roof_' + side, top, '04_Roof', [roof_green])
    new_obj('RoofUnder_' + side, under, '04_Roof', [roof_under_mat])
    new_obj('RoofLight_' + side, light, '04_Roof', [roof_light])
    new_obj('Girders_' + side, beams, '04_Roof', [girder_mat])
    new_obj('Fascia_' + side, fascia, '04_Roof', [fascia_mat, roof_green, lamp, white_paint])


roof_over('S')
roof_over('E', lamps=True)
roof_over('N')
roof_over('W', lamps=True)

# the scoreboard in the open south-west corner, as on the photos: a black box
# on four steel legs between the south end and the main stand, facing the
# pitch, its face the live screen (game.screen.js, style 'janbreydel'); a
# dark cloth hung slanting under it down to the first ring
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
cloth_mat = image_material('M_Cloth', load_asset('cloth.png'), 0.9)
right = (-SCR_N).cross(UPV).normalized()
bm = bmesh.new()
hc = SCR_C - SCR_N * 0.45
obox(bm, hc, SCR_N, right, UPV, 0.42, SCR_W / 2 + 0.3, SCR_H / 2 + 0.3, 0)
zb_ = hc.z - SCR_H / 2 - 0.3
for sx in (-1, 1):
    for sd in (-1, 1):
        p = hc + right * sx * (SCR_W / 2 - 0.8) + SCR_N * sd * 0.3 - SCR_N * 0.6
        tube(bm, Vector((p.x, p.y, 0.0)), Vector((p.x, p.y, zb_)), 0.16, 1, 6, step=3.0)
    for h_ in (3.0, 7.0, 10.5):
        p0 = hc + right * sx * (SCR_W / 2 - 0.8) - SCR_N * 0.6
        tube(bm, Vector((p0.x, p0.y, h_)) + SCR_N * 0.3, Vector((p0.x, p0.y, h_)) - SCR_N * 0.3, 0.06, 1, 5)
for h_ in (3.0, 7.0, 10.5):
    tube(bm, hc - right * (SCR_W / 2 - 0.8) - SCR_N * 0.9 + Vector((0, 0, h_ - hc.z)), hc + right * (SCR_W / 2 - 0.8) - SCR_N * 0.9 + Vector((0, 0, h_ - hc.z)), 0.07, 1, 5)
new_obj('Screen_Frame', bm, '04_Roof', [steel_dark, steel_grey])
bm = bmesh.new()
c_top = SCR_C + SCR_N * 0.1 - UPV * (SCR_H / 2 + 0.3)
for sgn in (1, -1):
    pts = [c_top - right * SCR_W / 2 + SCR_N * 3.2 - UPV * (c_top.z - 3.0), c_top + right * SCR_W / 2 + SCR_N * 3.2 - UPV * (c_top.z - 3.0),
           c_top + right * SCR_W / 2, c_top - right * SCR_W / 2]
    uvs = [(0, 0), (1, 0), (1, 1), (0, 1)]
    if sgn < 0:
        pts, uvs = pts[::-1], uvs[::-1]
    face(bm, pts, SCR_N * sgn + UPV * 0.3 * sgn, 0, uvs)
new_obj('Screen_Cloth', bm, '04_Roof', [cloth_mat])
fb = bmesh.new()
c0 = SCR_C + SCR_N * 0.02
face(fb, [c0 - right * SCR_W / 2 - UPV * SCR_H / 2, c0 + right * SCR_W / 2 - UPV * SCR_H / 2,
          c0 + right * SCR_W / 2 + UPV * SCR_H / 2, c0 - right * SCR_W / 2 + UPV * SCR_H / 2], SCR_N, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
screen_face = new_obj('ScreenFace_0', fb, '04_Roof', [live])

# the away section in the west part of the south end: tall yellow fences
# up both rings along its aisle and along the front of its second ring
bm = bmesh.new()
def fence(pa, pb, za, zb, h=2.6, every=2.2):
    L = (pb - pa).length
    n = max(1, math.ceil(L / every))
    for k in range(n + 1):
        q = pa.lerp(pb, k / n); zq = za + (zb - za) * k / n
        tube(bm, Vector((q.x, q.y, zq)), Vector((q.x, q.y, zq + h)), 0.05, 0, 5)
    for hh in (0.9, 1.8, h):
        tube(bm, Vector((pa.x, pa.y, za + hh)), Vector((pb.x, pb.y, zb + hh)), 0.04, 0, 5, step=3.0)
    # the mesh: thin uprights every 0.25 m
    m = max(1, int(L / 0.25))
    for k in range(m):
        q = pa.lerp(pb, (k + 0.5) / m); zq = za + (zb - za) * (k + 0.5) / m
        tube(bm, Vector((q.x, q.y, zq + 0.1)), Vector((q.x, q.y, zq + h)), 0.012, 0, 3, step=4.0)
for t_ in (LOW, UP):
    d0, d1 = t_['r'] + 0.3, t_['r'] + t_['depth'] * (t_['rows'] - 0.5)
    pa, pb = V2(-XF - d0, AWAY_Y), V2(-XF - d1, AWAY_Y)
    fence(pa, pb, t_['z'], t_['z'] + t_['rise'] * (t_['rows'] - 1))
fence(V2(-XF - BAL_D - 0.1, AWAY_Y), V2(-XF - BAL_D - 0.1, ylim_s(BAL_D) - 0.5), BAL_Z, BAL_Z)
fence(V2(-XF - 0.1, AWAY_Y), V2(-XF - 0.1, ylim_s(0.0) - 0.5), WALL_Z, WALL_Z, h=2.2)
new_obj('Away_Fences', bm, '02_Bowl', [rail_yellow])

# the flags in the north-east corner, on white poles on the corner's back
# wall: Brugge, Europe, Belgium, Flanders from north to south (left to right
# from the main stand), flying east in a westerly breeze
bm = bmesh.new()
WIND = Vector((0.42, -0.91, 0)).normalized()
SIDEW = Vector((-WIND.y, WIND.x, 0))
POLES = []
for n, ang in enumerate((330.0, 320.0, 310.0, 300.0)):
    a_ = math.radians(ang)
    POLES.append((n, Vector((XF - RC + (RC + BACK_D + 0.17) * math.cos(a_), YE + RC + (RC + BACK_D + 0.17) * math.sin(a_), PARAPET_Z)), 11.0))
for x_ in (-12.5, 12.5):                         # two club flags before the main entrance
    POLES.append((4, Vector((x_, YW + OUT_D + 6.0, 0.0)), 10.0))
for n, base, hp in POLES:
    top = base + Vector((0, 0, hp))
    tube(bm, base, top, 0.08, 0, 8, step=3.0)
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.14, matrix=__import__('mathutils').Matrix.Translation(top + Vector((0, 0, 0.1))))
    FLW, FLH, NU, NV = 3.0, 2.0, 8, 3
    def fp(uu, vv, ph=n * 1.7 + base.x * 0.3):
        wave = 0.22 * math.sin(uu * 5.0 + ph) * uu
        return top + Vector((0, 0, -0.3 - FLH * (1 - vv))) + WIND * (0.1 + FLW * uu) + SIDEW * wave
    for i in range(NU):
        for j in range(NV):
            q = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            pts = [fp(a / NU, b / NV) for a, b in q]
            uvs = [((n + a / NU) / 5, b / NV) for a, b in q]
            face(bm, pts, SIDEW, 1, uvs)
            face(bm, pts[::-1], -SIDEW, 1, uvs[::-1])
for f_ in bm.faces:
    if f_.material_index not in (0, 1):
        f_.material_index = 0
new_obj('Flags', bm, '04_Roof', [white_paint, flags_mat])

# ================================================================ the rails: yellow, everywhere
bm = bmesh.new()


def rail_along(d, z, post_every=2.4):
    for path in PATHS:
        for i in range(len(path[1])):
            sp = span(path, i, d)
            if sp is None:
                continue
            a, b = P(path, i, sp[0], d), P(path, i, sp[1], d)
            L = (b - a).length
            if L < 0.3:
                continue
            tube(bm, a + Vector((0, 0, z + 1.0)), b + Vector((0, 0, z + 1.0)), 0.04, 0, 6, step=3.0)
            n = max(1, round(L / post_every))
            for k in range(n):
                p = a.lerp(b, (k + 0.5) / n)
                tube(bm, p + Vector((0, 0, z)), p + Vector((0, 0, z + 1.0)), 0.03, 0, 5)


rail_along(0.12, WALL_Z)
rail_along(LOW_BACK + 0.12, WALK_Z)
rail_along(BAL_D + 0.12, BAL_Z)
# a handrail up the middle of every stairway
for path in PATHS:
    for i in range(1, len(path[0]) - 1):
        if not is_aisle(path, i):
            continue
        for t, tier in ((LOW, 'low'), (UP, 'up')):
            ks = []
            for k in range(1, t['rows']):
                dk = t['r'] + t['depth'] * k
                a_, b_ = span(path, i, dk), span(path, i - 1, dk)
                if a_ and b_ and a_[0] == 0.0 and b_[1] == 1.0 and not hole(path, tier, k, P(path, i, 0.0, dk)):
                    ks.append(k)
            if len(ks) < 3:
                continue
            k0, k1 = ks[0], ks[-1]
            pa = P(path, i, 0.0, t['r'] + t['depth'] * (k0 + 0.5))
            pb = P(path, i, 0.0, t['r'] + t['depth'] * (k1 + 0.5))
            za, zb = t['z'] + t['rise'] * k0 + 0.95, t['z'] + t['rise'] * k1 + 0.95
            tube(bm, pa + Vector((0, 0, za)), pb + Vector((0, 0, zb)), 0.035, 0, 6, step=3.0)
            for k in range(k0, k1 + 1, 4):
                p = P(path, i, 0.0, t['r'] + t['depth'] * (k + 0.5))
                zz = t['z'] + t['rise'] * k
                tube(bm, p + Vector((0, 0, zz)), p + Vector((0, 0, zz + 0.95)), 0.03, 0, 5)
new_obj('Rails', bm, '02_Bowl', [rail_yellow])

# the players' tunnel under the west stand, the dugouts either side of it
bm = bmesh.new()
TZ = LOW['z'] + LOW['rise'] * 6 + 0.3
y0, y1 = YW, YW + LOW['r'] + LOW['depth'] * 7
face(bm, [(-2.4, y0, TZ), (2.4, y0, TZ), (2.4, y1, TZ), (-2.4, y1, TZ)], -UPV, 0)
face(bm, [(-2.4, y0, TZ + 0.02), (2.4, y0, TZ + 0.02), (2.4, y1, TZ + 0.02), (-2.4, y1, TZ + 0.02)], UPV, 0)
for sx in (-1, 1):
    face(bm, [(sx * 2.4, y0, 0), (sx * 2.4, y1, 0), (sx * 2.4, y1, TZ), (sx * 2.4, y0, TZ)], Vector((-sx, 0, 0)), 0)
face(bm, [(-2.4, y1, 0), (2.4, y1, 0), (2.4, y1, TZ), (-2.4, y1, TZ)], Vector((0, -1, 0)), 1)
for x0, x1 in ((-16.0, -5.0), (5.0, 16.0)):
    yb = YW - 0.6
    face(bm, [(x0, yb - 2.3, 2.0), (x1, yb - 2.3, 2.0), (x1, yb, 2.3), (x0, yb, 2.3)], UPV, 2)
    face(bm, [(x0, yb - 2.3, 1.98), (x1, yb - 2.3, 1.98), (x1, yb, 2.28), (x0, yb, 2.28)], -UPV, 2)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.3), (x0, yb, 2.3)], Vector((0, -1, 0)), 0)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.3, 0.0), (x, yb, 0.0), (x, yb, 2.3), (x, yb - 2.3, 2.0)], Vector((1 if x == x0 else -1, 0, 0)), 2)
    for k in range(int(x1 - x0)):                                          # the seats in them
        xx = x0 + 0.5 + k
        abox(bm, xx - 0.22, xx + 0.22, yb - 0.9, yb - 0.4, 0.0, 0.45, 3, True, False)
new_obj('Tunnel', bm, '02_Bowl', [concrete_dark, portal, dark_glass, seat_cols[BLACK]])

# the boards round the pitch: the clubs' and the city's words (tools/jan_breydel/boards.png)
BOARD_Y, BOARD_X = PL / 2 + 4.2, PW / 2 + 3.8
BOARD_LINES = [
    (Vector((52.0, -BOARD_Y, 0)), Vector((-52.0, -BOARD_Y, 0)), -math.pi / 2),
    (Vector((-52.0, BOARD_Y, 0)), Vector((-18.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((18.0, BOARD_Y, 0)), Vector((52.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((-BOARD_X, -30.0, 0)), Vector((-BOARD_X, 30.0, 0)), math.pi),
    (Vector((BOARD_X, 30.0, 0)), Vector((BOARD_X, -30.0, 0)), 0.0),
]
bm = bmesh.new()
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    L = (b - a).length
    n = max(1, math.ceil(L / 4.0))
    for k in range(n):
        p0, p1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        q0, q1 = p0 + out * 0.3, p1 + out * 0.3
        ua, ub = L * k / n / 32.0, L * (k + 1) / n / 32.0
        face(bm, [(p0.x, p0.y, 0.05), (p1.x, p1.y, 0.05), (p1.x, p1.y, 0.95), (p0.x, p0.y, 0.95)], -out, 0, [(ua, 0), (ub, 0), (ub, 1), (ua, 1)])
        face(bm, [(q0.x, q0.y, 0.0), (q1.x, q1.y, 0.0), (q1.x, q1.y, 0.95), (q0.x, q0.y, 0.95)], out, 1)
        face(bm, [(p0.x, p0.y, 0.95), (p1.x, p1.y, 0.95), (q1.x, q1.y, 0.95), (q0.x, q0.y, 0.95)], UPV, 1)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_dark])

# the corner flags
bm = bmesh.new()
for sx in (-1, 1):
    for sy in (-1, 1):
        b0 = Vector((sx * hx, sy * hy, 0))
        tube(bm, b0, b0 + Vector((0, 0, 1.55)), 0.018, 0, 6)
        face(bm, [b0 + Vector((0, 0, 1.15)), b0 + Vector((0, 0, 1.52)), b0 + Vector((-sx * 0.42, 0, 1.40)), b0 + Vector((-sx * 0.42, 0, 1.18))], None, 1)
new_obj('Corner_Flags', bm, '01_Pitch', [white_paint, principled('M_Flag', (0.85, 0.36, 0.02), 0.7)])

# ================================================================ the floodlight masts in the corners
bm = bmesh.new()
for mx, my in MASTS:
    base = Vector((mx, my, 0))
    to_c = Vector((-mx, -my * 0.6, 0)).normalized()                   # aimed at the pitch, a little towards its middle
    side_ = Vector((-to_c.y, to_c.x, 0))
    top_h = MAST_H - 6.0
    legs = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        legs.append((base + (to_c * sx + side_ * sy) * 2.1, base + (to_c * sx + side_ * sy) * 0.75 + Vector((0, 0, top_h))))
    for p0, p1 in legs:
        tube(bm, p0, p1, 0.16, 0, 6, step=3.0)
    nlev = 9
    for lv in range(nlev + 1):
        t = lv / nlev
        ring_pts = [p0.lerp(p1, t) for p0, p1 in legs]
        for q in range(4):
            tube(bm, ring_pts[q], ring_pts[(q + 1) % 4], 0.06, 0, 5, trim=0.15)
        if lv < nlev:
            nxt_pts = [p0.lerp(p1, (lv + 1) / nlev) for p0, p1 in legs]
            for q in range(4):
                tube(bm, ring_pts[q], nxt_pts[(q + 1) % 4], 0.05, 0, 5, trim=0.15)
    # the platform and the head: a frame of lamps, tilted down at the pitch
    ptop = base + Vector((0, 0, top_h))
    box(bm, ptop, to_c, 1.6, side_, 1.6, top_h - 0.25, top_h, 0)
    tilt = math.radians(28)
    fwd = (to_c * math.cos(tilt) - UPV * math.sin(tilt)).normalized()
    upv = side_.cross(fwd).normalized()
    if upv.z < 0:
        upv = -upv
    hc = ptop + Vector((0, 0, 3.4)) + to_c * 0.6
    W2, H2 = 4.6, 2.9
    for p0, p1 in ((hc - side_ * W2 - upv * H2, hc + side_ * W2 - upv * H2), (hc - side_ * W2 + upv * H2, hc + side_ * W2 + upv * H2),
                   (hc - side_ * W2 - upv * H2, hc - side_ * W2 + upv * H2), (hc + side_ * W2 - upv * H2, hc + side_ * W2 + upv * H2)):
        tube(bm, p0, p1, 0.09, 0, 5)
    for sx in (-1, 1):
        tube(bm, ptop + side_ * sx * 1.2, hc + side_ * sx * 1.2 - upv * H2, 0.08, 0, 5)
    for cx in range(7):
        for cy in range(4):
            c = hc + side_ * ((cx - 3) * 1.25) + upv * ((cy - 1.5) * 1.35)
            obox(bm, c - fwd * 0.25, fwd, side_, upv, 0.25, 0.52, 0.52, 0)
            cc = c + fwd * 0.01
            face(bm, [cc - side_ * 0.45 - upv * 0.45, cc + side_ * 0.45 - upv * 0.45, cc + side_ * 0.45 + upv * 0.45, cc - side_ * 0.45 + upv * 0.45], fwd, 1)
new_obj('Floodlights', bm, '04_Roof', [steel_grey, lamp])

# ================================================================ outside: the stadium's own ground, trees
# The ground inside the ring road belongs to the stadium (it is seen in
# Stadion kiezen); the Olympiapark beyond it is the backdrop
G_HALF = 320.0                   # tools/jan_breydel/ground.png covers 640 x 640 m
AP_X0, AP_X1, AP_Y0, AP_Y1 = -110.0, 110.0, -90.0, 100.0
G_Z = -0.15


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
ground_cells(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 5.0, lambda xa, xb, ya, yb: -60 <= xa and xb <= 60 and -40 <= ya and yb <= 40)
new_obj('Ground', bm, '05_Outside', [ground_mat])

trng = random.Random(1975)


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


def inside_poly(x, y, poly):
    c = False
    n = len(poly)
    for k in range(n):
        (ax, ay), (bx, by) = poly[k], poly[(k + 1) % n]
        if (ay > y) != (by > y) and x < ax + (y - ay) * (bx - ax) / (by - ay):
            c = not c
    return c


def clear_of(x, y, margin):
    # not on a building, a pitch, a car park, the stadium or a road
    if any(inside_poly(x, y, b['pts']) for b in OSM['buildings']):
        return False
    if any(inside_poly(x, y, p['pts']) for p in OSM['pitches']) or any(inside_poly(x, y, g) for g in OSM['parking']):
        return False
    if inside_poly(x, y, OSM['stadium']) or inside_poly(x, y, OSM['west']) or math.hypot(x, y) < 75:
        return False
    for r in OSM['roads']:
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
    # trees along the roads, a few metres off the edge
    for r in OSM['roads']:
        if r['type'] not in ('residential', 'tertiary', 'secondary', 'service', 'unclassified'):
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
                    if trng.random() < 0.35:
                        continue
                    p = a.lerp(b, (j + trng.random()) / nseg) + nrm * sgn * trng.uniform(6.5, 9.0)
                    ap = AP_X0 < p.x < AP_X1 and AP_Y0 < p.y < AP_Y1
                    if ap != in_apron or abs(p.x) > G_HALF - 10 or abs(p.y) > G_HALF - 10 or not clear_of(p.x, p.y, 5.0):
                        continue
                    tree(bm, p.x, p.y, trng.uniform(10, 16), trng.uniform(3.0, 4.6))


bm = bmesh.new()
road_trees(bm, 11.0, True)
new_obj('Trees', bm, '05_Outside', [trunk, foliage])

# ================================================================ the backdrop: the Olympiapark from OpenStreetMap
bm = bmesh.new()
ground_cells(bm, -G_HALF, G_HALF, -G_HALF, G_HALF, 10.0, lambda xa, xb, ya, yb: AP_X0 <= xa and xb <= AP_X1 and AP_Y0 <= ya and yb <= AP_Y1)
far_ground = new_obj('Ground_Far', bm, '06_Backdrop', [ground_mat])
bm = bmesh.new()
HEIGHT = {'house': 7.5, 'detached': 7.5, 'residential': 8.0, 'semidetached_house': 7.5, 'terrace': 8.0, 'garage': 3.0, 'garages': 3.0,
          'shed': 2.6, 'roof': 4.5, 'apartments': 13.0, 'school': 10.0, 'sports_centre': 11.0, 'office': 13.0, 'church': 15.0,
          'social_facility': 9.0, 'stadium': 0.0}
for b in OSM['buildings']:
    pts = b['pts'][:-1] if b['pts'][0] == b['pts'][-1] else b['pts']
    if len(pts) < 3 or max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4:
        continue
    sarea = 0.5 * sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    area = abs(sarea)
    if area < 4:
        continue
    h = HEIGHT.get(b['type'], 9.0 if area > 700 else 7.0)
    if b['levels']:
        try:
            h = float(b['levels']) * 3.2 + 1.5
        except ValueError:
            pass
    if h <= 0:
        continue
    big = area > 700 or b['type'] in ('school', 'sports_centre', 'office', 'apartments', 'church')
    wall_m = 4 if big else (1 if trng.random() < 0.7 else 2)
    for k in range(len(pts)):
        a, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a[1]), -(c_[0] - a[0]), 0)) * (1 if sarea > 0 else -1)
        nz = max(1, math.ceil(h / 3.0))
        for q in range(nz):
            za, zb = G_Z + h * q / nz, G_Z + h * (q + 1) / nz
            face(bm, [(a[0], a[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a[0], a[1], zb)], outv, wall_m)
    try:
        rf = bm.faces.new([bm.verts.new((x, y, G_Z + h)) for x, y in pts])
    except ValueError:
        continue
    rf.material_index = 3 if big else 0
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, plaster, flat_roof, hall_wall])
bm = bmesh.new()
road_trees(bm, 13.0, False)
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
    preview('match', (0, 78.0, 22.0), (0, -16.0, 0), 36, clip=30.0)
    preview('photo1', (-22.0, 64.0, 21.0), (72.0, -18.0, 4.0), 62, res=(1280, 960))
    preview('north', (-40.0, 2.0, 9.0), (70.0, 2.0, 15.0), 55, res=(1280, 853))
    preview('entrance', (-14.0, 112.0, 6.0), (4.0, 60.0, 13.0), 62)
    preview('outside_e', (40.0, -125.0, 8.0), (10.0, -60.0, 16.0), 60)
    preview('south_up', (-86.0, 0.0, 20.0), (60.0, 0.0, 4.0), 75, res=(1280, 853))
    preview('flags', (40.0, 10.0, 18.0), (85.0, -60.0, 28.0), 45)
    preview('corner', (-50.0, 30.0, 6.0), (60.0, -45.0, 12.0), 70)
    preview('air', (-230.0, 210.0, 170.0), (0.0, 0.0, 10.0), 32)
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
grass_light = bake_lightmap(grass, 704, 478)
grass.hide_render = True                 # the floor in full sun where the pitch lies on it
floor_light = bake_lightmap(floor, 840, 596)
grass.hide_render = False
inner = grass_light[int(478 * 0.25):int(478 * 0.75), int(704 * 0.25):int(704 * 0.75)]
lum_px = (inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1)
lum = float(np.percentile(lum_px, 75))  # the sunlit grass, not the shadow of the west stand
EXPOSE = 0.75 / max(lum, 1e-6)
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
    # the Jan Breydel pitch as on the photos: broad stripes across it, a
    # fainter lengthwise check, wear in the goalmouths and the centre
    bands_x = np.tanh(np.sin(np.pi * X / (PW / 18)) * 6)
    bands_y = np.tanh(np.sin(np.pi * Y / (PL / 8)) * 5)
    fine = rng.normal(0, 1, (H, W)).astype('f')
    shade = (1 + 0.14 * bands_x + 0.07 * bands_y + 0.05 * vnoise(H, W, 400, 400) + 0.03 * vnoise(H, W, 48, 48)
             + 0.035 * vnoise(H, W, 14, 1) * (0.6 + 0.4 * bands_x) + 0.035 * fine)
    g = np.array((0.058, 0.172, 0.040), 'f') * shade[..., None]
    g[..., 0] *= 1 + 0.10 * vnoise(H, W, 300, 300)
    wear = sum(np.exp(-(((X - gx) / 3.0) ** 2 + (Y / 5.0) ** 2)) for gx in (-(hx - 3.0), hx - 3.0)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
    wear = (0.18 * wear * (0.55 + 0.45 * np.clip(vnoise(H, W, 36, 36) + 0.5, 0, 1)))[..., None]
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


# the pitch picture: 4096 x 2780 over 112 x 76 m
H, W = 2780, 4096
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * PITCH_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * PITCH_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = grass_albedo(X, Y, H, W)
cov = line_alpha(X, Y, 2 * PITCH_X / W)[..., None] * np.clip(0.85 + 0.1 * vnoise(H, W, 90, 90), 0.7, 1)[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
pitch_img = finish('jb_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: 2048 x 1454 over the ground inside the stands: grass up
# to the boards, tarmac behind them
H, W = 1454, 2048
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.052, 0.052, 0.056)
alb *= (1 + 0.06 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 30, 30))[..., None]
infield = (np.abs(X) < BOARD_X) & (np.abs(Y) < BOARD_Y)
alb = np.where(infield[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('jb_floor', alb, floor_light, H, W)
del alb, X, Y
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

skip = ('Pitch_Lines', 'StadiumGoals', 'Ground_Far', 'Buildings', 'Trees_Far', 'ScreenFace_')
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
target.name = 'JanBreydelstadion'
select_only([far_ground, buildings, far_trees], far_ground)
bpy.ops.object.join()
backdrop = far_ground
backdrop.name = 'StadiumBackdrop'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor', 'M_RoofLight'}


def bake_light(obj, samples=96):
    # the sun into the vertex colours, at the pitch's exposure; the pitch and
    # the floor carry their own light in their pictures, the light panels
    # under the roofs are lit by the sky through them
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
