# Builds El Campín (Estadio Nemesio Camacho, Bogotá) from nothing and exports
# it for the game, the way the Philips Stadion and the Estadio Centenario are
# built; on a dry-season afternoon, the sun in the west behind the Tribuna
# Occidental, the Oriental with IDRD BOGOTÁ in its seats in full light and the
# hills of Monserrate behind it.
#   blender -b --factory-startup --python tools/campin_build.py -- <out.blend> <out.glb> <texture dir> [quick [shot ...]]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/campin_assets.py, the plan from
# tools/campin_osm.py.
#
# The facts and the plan (the photos on Wikimedia Commons, 2011-2025):
#   - opened in 1938 for the Bolivarian Games, rebuilt for the U-20 World Cup
#     of 2011 (the Occidental new, the roof over it), home of Millonarios and
#     Santa Fe; 39.512 places: the Oriental with its curved ends 19.740, the
#     Occidental 9.969, Sur 5.213, Norte 4.802
#   - the plan is OpenStreetMap's (way 24020167 the stadium, 336679692 the
#     front of its stands, 226327160 the pitch; data © OpenStreetMap
#     contributors, ODbL), turned 6.57 degrees so the pitch lies on the axes:
#     one bowl round the old athletics track, 180 x 104 m at the front of the
#     stands, 29 m deep, the Occidental 37
#   - the bowl as on the photo of the empty stadium (2019): a front wall with
#     a yellow rail, a first ring of 24 rows, a walkway with the vomitories, a
#     second ring of 10 rows under a narrow roof with the floodlights along its
#     edge; the stairways painted yellow; the Oriental's first ring red in its
#     six front rows (blue in the two middle sections), yellow above with
#     IDRD BOGOTÁ in red seats, one letter a section; its second ring grey,
#     blue in the middle; the ends yellow, blue in the corners by the Oriental
#   - the Occidental: its first ring red, the boxes over it behind glass, a
#     second ring of yellow seats, the big roof over both on radial beams;
#     outside the concrete base, the stairs, the glass lift tower
#   - round the pitch the green turf, the grey asphalt of the old track in the
#     curves behind the goals, the dugouts as blue tubes on the Occidental's side
#   - the outside: the raked underside of the stands painted cream, the grey
#     frames and V-struts, the balcony round the middle, the brown fence at
#     the foot; four lattice towers with the floodlights, the LED screen on the
#     north end's roof (game.screen.js, style 'campin'), the scoreboard tower
#   - round it the brick-red plaza, Avenida NQS with TransMilenio and the
#     canal, the brick town of Galerías and Nicolás de Federmán, the hills of
#     the Cerros Orientales in the east
# No sponsors: the boards carry the stadium's, the city's and the country's words.
#
# The helpers, the goals and the export are those of tools/philips_build.py;
# units are metres, x along the pitch towards the north end, y towards the
# Occidental (the match camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'campin')
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
SEAT_W, AISLE_W = 0.46, 1.1                 # the narrow plastic seats of 2011
GAIN = 2.0                                   # the game draws the model unlit at this gain (catalog: look.gain)
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))
_ring = lambda p: p[:-1] if p[0] == p[-1] else p
INNER = _ring(OSM['ways']['stadium_inner'])
OUTLINE = _ring(OSM['ways']['stadium_outer'])
# the bowl's section: a walk behind the front wall, 24 rows, the walkway with
# the vomitories, 10 rows under the roof, the walk along the top
FRONT_Z = 2.0
LOW_ROWS = [(0.0, 1.0, FRONT_Z, 'walk')]
LOW_ROWS += [(1.0 + 0.75 * k, 1.75 + 0.75 * k, 2.35 + 0.38 * k, 'seat') for k in range(24)]
LOW_ROWS += [(19.0, 20.8, 11.5, 'walk')]
UP_ROWS = [(20.8 + 0.75 * k, 21.55 + 0.75 * k, 12.2 + 0.42 * k, 'seat') for k in range(10)]
UP_ROWS += [(28.3, 29.0, 16.4, 'walk')]
BACK_D, TOP_Z = 29.0, 16.4
CAN_D0, CAN_D1, CAN_Z0, CAN_Z1 = 20.6, 29.8, 19.6, 19.0     # the roof over the second ring: its front edge, its back
# the Occidental over its first ring: the boxes, the second ring, the roof
BOX_D0, BOX_D1, BOX_Z0, BOX_Z1 = 20.4, 23.2, 11.5, 14.6
W_ROWS = [(23.2 + 0.8 * k, 24.0 + 0.8 * k, 15.1 + 0.48 * k, 'seat') for k in range(14)]
W_ROWS += [(34.4, 35.4, 21.9, 'walk')]
W_BACK, W_TOP = 35.4, 21.9
WR_D0, WR_D1, WR_Z0, WR_Z1 = 3.5, 40.5, 27.6, 25.2          # its roof: the front edge high, the back low
SCR_W, SCR_H = 18.0, 9.0                     # the LED screen on the north end's roof (drawn 2:1, game.screen.js 'campin')
MAST_H = 50.0
# the sun: a February afternoon in the west, 42 degrees up, a little south:
# behind the Occidental, full on the Oriental and the hills
SUN_AZ, SUN_EL = math.radians(100.0), math.radians(42.0)     # from the plan's x, towards y
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()


# ---------------------------------------------------------------- helpers (as in the Philips Stadion script)
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
    # a picture from tools/campin as floats, row 0 at the top
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



# ---------------------------------------------------------------- the plan: the front of the stands as one path
# A path is a row of nodes along the front of the stands (OSM's line, made
# symmetric about both axes and smoothed), each with its outward direction;
# a point at offset d (metres back from the front) lies on the same line out
# at every d. Piece i runs from node i to node i + 1; node 0 is the middle of
# the Oriental (-y), the path runs north (+x) round the north end, along the
# Occidental, round the south end and back. Three pieces a section between
# the stairways.
def ray_hit(poly, ox, oy, dx, dy):
    # the nearest t > 0 where the ray o + t d crosses the polygon
    best = None
    n = len(poly)
    for k in range(n):
        (ax, ay), (bx, by) = poly[k], poly[(k + 1) % n]
        ex, ey = bx - ax, by - ay
        den = dx * ey - dy * ex
        if abs(den) < 1e-9:
            continue
        t = ((ax - ox) * ey - (ay - oy) * ex) / den
        u = ((ax - ox) * dy - (ay - oy) * dx) / den
        if t > 1e-6 and -1e-9 <= u <= 1 + 1e-9 and (best is None or t < best):
            best = t
    return best


R_IN = []
for a in range(360):
    th = math.radians(a)
    rs = [ray_hit(INNER, 0.0, 0.0, math.cos(t_), math.sin(t_)) for t_ in (th, -th, math.pi - th, math.pi + th)]
    R_IN.append(sum(rs) / 4)
R_IN = [sum(R_IN[(a + k) % 360] for k in range(-5, 6)) / 11 for a in range(360)]


def r_front(deg):
    a0 = math.floor(deg) % 360
    f_ = deg - math.floor(deg)
    return R_IN[a0] * (1 - f_) + R_IN[(a0 + 1) % 360] * f_


_dense = []
for k in range(1440):
    deg = -90.0 + k * 0.25
    r = r_front(deg)
    _dense.append(Vector((r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), 0)))
_cum = [0.0]
for k in range(1440):
    _cum.append(_cum[-1] + (_dense[(k + 1) % 1440] - _dense[k]).length)
PERIM = _cum[-1]
NP = 144
_pts = []
for j in range(NP):
    s_ = PERIM * j / NP
    k = max(0, min(1439, next(kk for kk in range(1441) if _cum[kk] >= s_) - 1))
    f_ = (s_ - _cum[k]) / max(1e-9, _cum[k + 1] - _cum[k])
    _pts.append(_dense[k].lerp(_dense[(k + 1) % 1440], f_))
NODES = []
for j in range(NP):
    t_ = (_pts[(j + 1) % NP] - _pts[j - 1]).normalized()
    NODES.append((_pts[j].copy(), Vector((t_.y, -t_.x, 0))))
NODES.append((NODES[0][0].copy(), NODES[0][1].copy()))
print('FRONT %.1f m round, %d pieces of %.2f m' % (PERIM, NP, PERIM / NP))


def P(i, u, d):
    (Fa, Na), (Fb, Nb) = NODES[i % NP], NODES[i % NP + 1]
    return (Fa + Na * d).lerp(Fb + Nb * d, u)


def cumlen(d):
    c = [0.0]
    for i in range(NP):
        c.append(c[-1] + (P(i, 1, d) - P(i, 0, d)).length)
    return c


def is_aisle(i):
    return i % 3 == 0


def section(i):
    # the section a piece is in: 0 the first north of the Oriental's middle, -1 the first south
    s_ = (i % NP) // 3
    return s_ if s_ < NP // 6 else s_ - NP // 3


# how deep the stand is behind each node (OSM's outline), the Occidental's reach
D_OUT = []
for j in range(NP):
    p_, n_ = NODES[j]
    D_OUT.append(ray_hit(OUTLINE, p_.x, p_.y, n_.x, n_.y) or BACK_D)
_west = [j for j in range(NP) if NODES[j][0].y > 0 and D_OUT[j] > 32.5]
W_I0, W_I1 = min(_west), max(_west)               # the Occidental: pieces W_I0 .. W_I1 - 1
_mid = (W_I0 + W_I1) / 2.0
_half = max(W_I1 - _mid, _mid - W_I0)
W_I0, W_I1 = int(round(NP / 2 - _half)), int(round(NP / 2 + _half))   # made symmetric about the Occidental's middle (node 72)
is_west = lambda i: W_I0 <= (i % NP) < W_I1
print('OCCIDENTAL pieces %d-%d, depth %.1f m' % (W_I0, W_I1, max(D_OUT)))


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


def d_of(x, y):
    # how far a point of the plan lies out from the front of the stands
    r = math.hypot(x, y)
    return r - r_front(math.degrees(math.atan2(y, x)) % 360)


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1938)


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
    t[:, :2] *= 0.45; t[:, -2:] *= 0.45
    t[-2:] *= 1.06
    return t


def glazing_tex():
    # the boxes' glass: dark, white frames every 1.5 m (u: 6 m)
    w, h = 384, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.035, 0.045, 0.055), 'f')
    t *= np.linspace(0.7, 1.5, h)[:, None, None]
    t[:, (np.arange(w) % 96) < 4] = (0.70, 0.70, 0.69)
    t[:6] = (0.70, 0.70, 0.69); t[-6:] = (0.70, 0.70, 0.69)
    return t


def soffit_tex():
    # the stands' underside seen from outside: the cream-painted steps, a
    # darker line at every row (u: 4 m, v: 8 rows)
    w, h = 128, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.70, 0.53, 0.17), 'f')
    t *= (1 + 0.04 * vnoise(h, w, 16, 16))[..., None]
    y = np.arange(h)
    t[(y % 32) < 9] *= 0.62
    t[(y % 32) == 9] *= 0.85
    return t


def roof_under_tex():
    # the Occidental's roof from below: pale grey ribbed sheeting (u: 4 m)
    w, h = 128, 32
    t = np.ones((h, w, 3), 'f') * np.array((0.56, 0.57, 0.57), 'f')
    t[:, (np.arange(w) % 16) < 3] *= 0.74
    return t


def foliage_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.05, 0.085, 0.03), 'f')
    t *= (1 + 0.35 * vnoise(h, w, 6, 6) + 0.2 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


def hills_tex():
    # the Cerros Orientales: dark eucalyptus and native forest, a few paler
    # clearings, the town climbing their foot in brick and pale render
    # (u: 320 m, v: the slope, the foot at v 0)
    w, h = 1024, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.032, 0.058, 0.026), 'f')
    t *= (1 + 0.30 * vnoise(h, w, 12, 20) + 0.22 * vnoise(h, w, 4, 4) + 0.12 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    light = vnoise(h, w, 24, 60) > 0.95
    t[light] = t[light] * 0.6 + np.array((0.10, 0.11, 0.06), 'f') * 0.4
    y = np.arange(h)[:, None]
    edge = 34 + 18 * vnoise(h, w, 50, 70)
    town = (y < edge) & (rng.random((h, w)) < 0.9 - 0.6 * np.clip(y / np.maximum(edge, 1), 0, 1))
    tc = np.where(rng.random((h, w, 1)) < 0.7, np.array((0.27, 0.13, 0.08), 'f'), np.array((0.45, 0.42, 0.38), 'f'))
    tc = tc * (1 + 0.25 * rng.normal(0, 1, (h, w, 1)).astype('f'))
    t = np.where(town[..., None], tc, t)
    return np.clip(t, 0, 1)


def windows_tex():
    # the brick blocks of the town: red-brown brick, a window every 3 m on every floor (u: 12 m, v: 12 m, four floors)
    w, h = 256, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.30, 0.13, 0.075), 'f')
    t *= (1 + 0.05 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    for fy in range(4):
        y0 = fy * 64 + 20
        for fx in range(4):
            x0 = fx * 64 + 12
            t[y0:y0 + 28, x0:x0 + 40] = (0.08, 0.09, 0.10)
            t[y0 + 28:y0 + 31, x0 - 2:x0 + 42] = (0.55, 0.52, 0.46)
    return np.clip(t, 0, 1)


# the seats: plastic buckets in the colours of the photos
SEATS = [(0.80, 0.52, 0.015),                 # 0: yellow
         (0.62, 0.035, 0.025),                # 1: red
         (0.030, 0.075, 0.33),                # 2: blue
         (0.30, 0.32, 0.34),                  # 3: grey (the Oriental's second ring)
         (0.74, 0.20, 0.03)]                  # 4: orange (the north end's front, faded red)
YEL, RED, BLU, GRY, ORA = range(5)
seat_cols = [image_material('M_Seat%d' % i, painted('ec_seat%d' % i, seat_tile(c)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.40, 0.395, 0.38), 0.9)                 # the treads
concrete_dark = principled('M_ConcreteDark', (0.29, 0.285, 0.275), 0.9)       # the risers
concrete_light = principled('M_ConcreteLight', (0.52, 0.515, 0.50), 0.85)     # walls, the base outside
yellow_paint = principled('M_YellowPaint', (0.80, 0.55, 0.02), 0.6)           # the stairways, the rails
taupe = principled('M_Taupe', (0.34, 0.31, 0.27), 0.85)                       # the frames outside
portal = principled('M_Portal', (0.012, 0.012, 0.014), 0.95)
white_paint = principled('M_WhitePaint', (0.76, 0.76, 0.74), 0.7)
galv = principled('M_Galvanised', (0.44, 0.45, 0.46), 0.5)
steel_dark = principled('M_SteelDark', (0.035, 0.037, 0.04), 0.6)
steel_grey = principled('M_SteelGrey', (0.34, 0.35, 0.36), 0.5)
fence_brown = principled('M_FenceBrown', (0.15, 0.095, 0.06), 0.8)
roof_metal = principled('M_RoofMetal', (0.33, 0.34, 0.34), 0.6)
blue_tube = principled('M_DugoutBlue', (0.02, 0.17, 0.55), 0.4)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
lamp_glass = principled('M_LampGlass', (0.90, 0.90, 0.86), 0.2)
glazing = image_material('M_Glazing', painted('ec_glazing', glazing_tex()), 0.2)
soffit = image_material('M_Soffit', painted('ec_soffit', soffit_tex()), 0.85)
roof_under_mat = image_material('M_RoofUnder', painted('ec_roofunder', roof_under_tex()), 0.7)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
foliage = image_material('M_Foliage', painted('ec_foliage', foliage_tex()), 0.95)
hills_mat = image_material('M_Hills', painted('ec_hills', hills_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
brick = principled('M_Brick', (0.26, 0.095, 0.055), 0.9)                      # Bogotá: red brick
brick_light = principled('M_BrickLight', (0.38, 0.17, 0.09), 0.9)
plaster = principled('M_Plaster', (0.56, 0.53, 0.48), 0.9)
tiles = principled('M_Tiles', (0.24, 0.08, 0.045), 0.8)
tiles_dark = principled('M_TilesDark', (0.06, 0.06, 0.065), 0.7)
flat_roof = principled('M_FlatRoof', (0.16, 0.15, 0.15), 0.9)
office_wall = principled('M_OfficeWall', (0.50, 0.49, 0.47), 0.7)
tower_block = image_material('M_TowerBlock', painted('ec_windows', windows_tex()), 0.8)


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
net_img = D.images.new('ec_net', 32 * NET_N, 32 * NET_N, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/ec_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
FX0, FX1, FY0, FY1 = -93.0, 93.0, -56.0, 56.0
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
f = bm.faces.new([bm.verts.new((x, y, FLOOR_Z)) for x, y in ((FX0, FY0), (FX1, FY0), (FX1, FY1), (FX0, FY1))])
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.30, 0.30, 0.29), 0.9)])


# ================================================================ the stands
# The seats' colours as on the photos: the Oriental (sections -9 to 6 round
# its middle) red in its six front rows, blue in the two middle sections,
# yellow above with IDRD BOGOTA in red, one letter a section, read from the
# Occidental (the path runs north, the reader's left); its second ring grey,
# blue in the middle; the corners by it blue up to the twelfth row; the
# ends yellow, red in the front rows on the Occidental's half; the
# Occidental's first ring red, its second yellow
LET = asset_pixels('letters.png')[..., 0] > 0.5            # (9, 150), row 0 the top
LW_, LH_, LET_TOP = 15, 9, 14
LETTER_SEC = {4: 0, 3: 1, 2: 2, 1: 3, -2: 4, -3: 5, -4: 6, -5: 7, -6: 8, -7: 9}


def zone(i):
    s_ = section(i)
    if is_west(i):
        return 'W'
    if -9 <= s_ <= 6:
        return 'E'
    if 7 <= s_ <= 9 or -12 <= s_ <= -10:
        return 'EC'
    return 'END'


def seat_colour(i, tier, row, m_sec, sec_len):
    zn, s_ = zone(i), section(i)
    if tier == 'up':
        if zn == 'E':
            return BLU if -4 <= s_ <= 2 else GRY
        return YEL
    if tier == 'west':
        return YEL
    if zn == 'W':
        return RED
    if zn == 'E':
        if row <= 5:
            return BLU if s_ in (0, -1) else RED
        k = LETTER_SEC.get(s_)
        r = LET_TOP - row
        if k is not None and 0 <= r < LH_:
            c = LW_ - 1 - int(math.floor((m_sec - (sec_len - LW_ * SEAT_W) / 2) / SEAT_W))
            if 0 <= c < LW_ and LET[r, k * LW_ + c]:
                return RED
        return YEL
    if zn == 'EC':
        return BLU if row <= 11 else YEL
    if row <= 5:
        return ORA if NODES[i % NP][0].y > 0 else YEL
    return YEL


def mouth_at(i, tier, d, m_sec, sec_len):
    # the vomitories: through the first ring's front rows in every third
    # section, through the second ring's first rows in every second; not in the Occidental
    if is_west(i):
        return False
    s_ = section(i)
    if abs(m_sec - sec_len / 2) > 1.25:
        return False
    if tier == 'low':
        return s_ % 3 == 1 and 1.0 <= d < 4.75
    if tier == 'up':
        return s_ % 2 == 0 and d < UP_ROWS[2][1]
    return False


def seat_geo(bm, pa, pb, back, m, q, q1, cush=0.40, top=0.80, fwd=0.40):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(fwd, cush, 0), at(fwd, cush, 1), at(0.74, cush, 1), at(0.74, cush, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.74, cush, 0), at(0.74, cush, 1), at(0.80, top, 1), at(0.80, top, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 1.0), (q, 1.0)])


SEAT_COUNT = {}


def build_tier(name, rows, tier, keep, z_before):
    steps, seats, stairs, mouths = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    row_no = -1
    count = 0
    for k, (d0, d1, z, kind) in enumerate(rows):
        zp = rows[k - 1][2] if k else z_before
        if kind == 'seat':
            row_no += 1
        dm = (d0 + d1) / 2
        cum = cumlen(dm)
        for i in range(NP):
            if not keep(i):
                continue
            A0, A1, B0, B1 = P(i, 0, d0), P(i, 1, d0), P(i, 0, d1), P(i, 1, d1)
            L = (A1 - A0).length
            back = ((B0 + B1) / 2 - (A0 + A1) / 2).normalized()
            s0 = (i // 3) * 3
            sec_start, sec_len = cum[s0], cum[s0 + 3] - cum[s0]
            m_at = lambda u: cum[i] + (cum[i + 1] - cum[i]) * u - sec_start
            n = max(1, math.ceil(max(L, (B1 - B0).length) / 3.0))
            for s in range(n):
                t0, t1 = s / n, (s + 1) / n
                if mouth_at(i, tier, d0, m_at((t0 + t1) / 2), sec_len):
                    continue
                a0, a1, b0, b1 = A0.lerp(A1, t0), A0.lerp(A1, t1), B0.lerp(B1, t0), B0.lerp(B1, t1)
                face(steps, [(a0.x, a0.y, z), (a1.x, a1.y, z), (b1.x, b1.y, z), (b0.x, b0.y, z)], UPV, 0)
                if z > zp + 0.01:
                    face(steps, [(a0.x, a0.y, zp), (a1.x, a1.y, zp), (a1.x, a1.y, z), (a0.x, a0.y, z)], -back, 1)
            if kind != 'seat':
                continue
            # the stairway at the start of the piece where a section begins: painted yellow, a half step
            cut0 = AISLE_W / 2 if is_aisle(i) else 0.0
            cut1 = AISLE_W / 2 if is_aisle(i + 1) else 0.0
            rise = z - zp
            for u0, u1 in ([(0.0, cut0 / L)] if cut0 else []) + ([(1 - cut1 / L, 1.0)] if cut1 else []):
                f0, f1, g0, g1 = A0.lerp(A1, u0), A0.lerp(A1, u1), B0.lerp(B1, u0), B0.lerp(B1, u1)
                m0, m1 = f0.lerp(g0, 0.5), f1.lerp(g1, 0.5)
                F0, F1, G0, G1, M0, M1 = (Vector((v_.x, v_.y, z)) + lift for v_ in (f0, f1, g0, g1, m0, m1))
                face(stairs, [F0, F1, M1, M0], UPV, 0)
                hs = Vector((0, 0, min(0.2, rise / 2) if rise > 0.05 else 0.0))
                face(stairs, [M0 + hs, M1 + hs, G1 + hs, G0 + hs], UPV, 0)
                if hs.z > 0:
                    face(stairs, [M0, M1, M1 + hs, M0 + hs], -back, 0)
            c0, c1 = cut0 / L, 1 - cut1 / L
            usable = (c1 - c0) * L
            if usable < SEAT_W:
                continue
            nseat = int(usable / SEAT_W)
            pad = (usable - nseat * SEAT_W) / 2 / L
            for q in range(nseat):
                u = c0 + pad + (q + 0.5) * SEAT_W / L
                ms = m_at(u)
                if mouth_at(i, tier, d0, ms, sec_len):
                    continue
                us = [c0 + pad + qq * SEAT_W / L for qq in (q, q + 1)]
                pa = [A0.lerp(A1, uu) + Vector((0, 0, z)) for uu in us]
                pb = [B0.lerp(B1, uu) + Vector((0, 0, z)) for uu in us]
                seat_geo(seats, pa, pb, back, seat_colour(i, tier, row_no, ms, sec_len), q, q + 1)
                count += 1
    # the vomitories' mouths: a dark way in under the rows, a yellow lintel
    if tier in ('low', 'up'):
        for i in range(NP):
            if not keep(i) or not is_aisle(i):
                continue
            cum = cumlen(rows[1][0])
            sec_len = cum[i + 3] - cum[i]
            if not mouth_at(i, tier, rows[1][0], sec_len / 2, sec_len):
                continue
            j = i + 1                                    # the mouth sits in the section's middle piece
            dA = rows[1][0] if tier == 'low' else rows[0][0]
            dB = 4.75 if tier == 'low' else UP_ROWS[2][1]
            zf = rows[0][2] if tier == 'low' else LOW_ROWS[-1][2]
            zt = (rows[6][2] if tier == 'low' else UP_ROWS[3][2]) - 0.1
            u0, u1 = 0.5 - 1.25 / (P(j, 1, dA) - P(j, 0, dA)).length, 0.5 + 1.25 / (P(j, 1, dA) - P(j, 0, dA)).length
            a0, a1, b0, b1 = P(j, u0, dA), P(j, u1, dA), P(j, u0, dB), P(j, u1, dB)
            out = (NODES[j][1] + NODES[j + 1][1]).normalized()
            face(mouths, [(a0.x, a0.y, zf), (a1.x, a1.y, zf), (b1.x, b1.y, zf), (b0.x, b0.y, zf)], UPV, 0)
            face(mouths, [(b0.x, b0.y, zf), (b1.x, b1.y, zf), (b1.x, b1.y, zt), (b0.x, b0.y, zt)], -out, 0)
            for pa_, pb_ in ((a0, b0), (a1, b1)):
                face(mouths, [(pa_.x, pa_.y, zf), (pb_.x, pb_.y, zf), (pb_.x, pb_.y, zt + 0.6), (pa_.x, pa_.y, zt + 0.6)], None, 2)
            hi = zt + 0.05
            face(mouths, [(a0.x, a0.y, hi), (a1.x, a1.y, hi), (b1.x, b1.y, hi), (b0.x, b0.y, hi)], -UPV, 0)
            # the yellow lintel with SALIDA over it
            la, lb = P(j, u0 - 0.05, dA - 0.05), P(j, u1 + 0.05, dA - 0.05)
            face(mouths, [(la.x, la.y, zt), (lb.x, lb.y, zt), (lb.x, lb.y, zt + 0.55), (la.x, la.y, zt + 0.55)], -out, 1)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Stairs_' + name, stairs, '02_Bowl', [yellow_paint])
    new_obj('Mouths_' + name, mouths, '02_Bowl', [portal, yellow_paint, concrete_light])
    SEAT_COUNT[name] = count


t0 = time.time()
build_tier('Lower', LOW_ROWS, 'low', lambda i: True, FRONT_Z)
build_tier('Upper', UP_ROWS, 'up', lambda i: not is_west(i), LOW_ROWS[-1][2])
build_tier('West', W_ROWS, 'west', is_west, BOX_Z1)
print('STANDS %.0fs, seats %s, %d' % (time.time() - t0, SEAT_COUNT, sum(SEAT_COUNT.values())))

# the walls: the front wall round the pitch with its yellow rail, the rail
# along the walkway, the parapet and the black fence along the top
bm, rails = bmesh.new(), bmesh.new()
ring(bm, 0.0, 0.0, 0.0, FRONT_Z, 0, want='in')
ring(bm, LOW_ROWS[-1][0], LOW_ROWS[-2][2], LOW_ROWS[-1][0], LOW_ROWS[-1][2] + 0.25, 1, want='in', keep=lambda i: not is_west(i))
ring(bm, BACK_D, TOP_Z, BACK_D, TOP_Z + 1.05, 0, want='in', keep=lambda i: not is_west(i))
ring(bm, BACK_D + 0.25, TOP_Z - 0.8, BACK_D + 0.25, TOP_Z + 1.05, 2, want='out', keep=lambda i: not is_west(i))
ring(bm, BACK_D, TOP_Z + 1.05, BACK_D + 0.25, TOP_Z + 1.05, 2, want='up', keep=lambda i: not is_west(i))
for i in range(NP):
    for d_, z_, keep_ in ((0.12, FRONT_Z + 1.0, True), (LOW_ROWS[-1][0] + 0.1, LOW_ROWS[-1][2] + 1.0, not is_west(i))):
        if not keep_:
            continue
        a_, b_ = P(i, 0, d_), P(i, 1, d_)
        tube(rails, Vector((a_.x, a_.y, z_)), Vector((b_.x, b_.y, z_)), 0.035, 0, 6, step=4.0)
        tube(rails, Vector((a_.x, a_.y, z_ - 1.0)), Vector((a_.x, a_.y, z_)), 0.03, 0, 5)
new_obj('Walls', bm, '02_Bowl', [concrete, concrete_dark, taupe])
new_obj('Rails', rails, '02_Bowl', [yellow_paint])
# the fence along the top: black bars 2 m tall
FB = 64
fb_px = np.zeros((FB, FB, 4), 'f'); fb_px[..., :3] = 0.03
fb_px[:, (np.arange(FB) % 8) < 2, 3] = 1.0; fb_px[:4, :, 3] = 1.0; fb_px[-4:, :, 3] = 1.0
fimg = D.images.new('ec_fence', FB, FB, alpha=True); fimg.pixels.foreach_set(fb_px.ravel())
fimg.filepath_raw = TEX_DIR + '/ec_fence.png'; fimg.file_format = 'PNG'; fimg.save(); fimg.pack()
fence_mat = alpha_material('M_FenceBars', fimg, 0.6)
bm = bmesh.new()
ring(bm, BACK_D + 0.2, TOP_Z + 1.05, BACK_D + 0.2, TOP_Z + 3.0, 0, want='out', u_len=1.0, keep=lambda i: not is_west(i))
new_obj('Top_Fence', bm, '02_Bowl', [fence_mat])

# ================================================================ the roof over the second ring
# a narrow flat roof right round the north end, the Oriental and the south
# end on posts at the back, the floodlights along its front edge
bm, lamps = bmesh.new(), bmesh.new()
keep_c = lambda i: not is_west(i)
can_z = lambda d: CAN_Z0 + (CAN_Z1 - CAN_Z0) * (d - CAN_D0) / (CAN_D1 - CAN_D0)
for i in range(NP):
    if not keep_c(i):
        continue
    for s in range(2):
        t0, t1 = s / 2, (s + 1) / 2
        p0, p1, q0, q1 = P(i, t0, CAN_D0), P(i, t1, CAN_D0), P(i, t0, CAN_D1), P(i, t1, CAN_D1)
        face(bm, [(p0.x, p0.y, CAN_Z0), (p1.x, p1.y, CAN_Z0), (q1.x, q1.y, CAN_Z1), (q0.x, q0.y, CAN_Z1)], UPV, 0)
        face(bm, [(p0.x, p0.y, CAN_Z0 - 0.35), (p1.x, p1.y, CAN_Z0 - 0.35), (q1.x, q1.y, CAN_Z1 - 0.35), (q0.x, q0.y, CAN_Z1 - 0.35)], -UPV, 1)
ring(bm, CAN_D0, CAN_Z0 - 0.9, CAN_D0, CAN_Z0 + 0.15, 2, want='in', keep=keep_c)
ring(bm, CAN_D1, CAN_Z1 - 0.5, CAN_D1, CAN_Z1 + 0.1, 2, want='out', keep=keep_c)
for i in range(NP):
    if not keep_c(i):
        continue
    if is_aisle(i) and keep_c(i - 1):
        pb_ = P(i, 0, BACK_D + 0.1)
        tube(bm, Vector((pb_.x, pb_.y, TOP_Z)), Vector((pb_.x, pb_.y, CAN_Z1 - 0.35)), 0.16, 3, 8)
        pf = P(i, 0, CAN_D0 + 0.5)
        tube(bm, Vector((pb_.x, pb_.y, TOP_Z + 1.2)), Vector((pf.x, pf.y, CAN_Z0 - 0.4)), 0.08, 3, 6)
    # the lamps on the front edge, aimed at the pitch
    out = (NODES[i][1] + NODES[i + 1][1]).normalized()
    tg = (P(i, 1, CAN_D0) - P(i, 0, CAN_D0)).normalized()
    for u_ in (0.25, 0.75):
        c = P(i, u_, CAN_D0 - 0.4) + Vector((0, 0, CAN_Z0 - 0.55))
        fwd = (-out * math.cos(math.radians(35)) - UPV * math.sin(math.radians(35))).normalized()
        upl = tg.cross(fwd).normalized()
        if upl.z < 0:
            upl = -upl
        obox(lamps, c, fwd, tg, upl, 0.22, 0.32, 0.26, 0)
        cc = c + fwd * 0.23
        face(lamps, [cc - tg * 0.27 - upl * 0.21, cc + tg * 0.27 - upl * 0.21, cc + tg * 0.27 + upl * 0.21, cc - tg * 0.27 + upl * 0.21], fwd, 1)
new_obj('Roof_Ring', bm, '04_Roof', [roof_metal, roof_under_mat, white_paint, steel_grey])

# ================================================================ the Occidental
# over its first ring the boxes behind glass, its second ring, the roof
bm = bmesh.new()
ring(bm, BOX_D0, BOX_Z0, BOX_D0, BOX_Z1, 3, want='in', keep=is_west, u_len=6.0)
ring(bm, BOX_D0 - 0.6, BOX_Z1, BOX_D1, BOX_Z1, 2, want='up', keep=is_west)
ring(bm, BOX_D0 - 0.6, BOX_Z1 - 0.3, BOX_D0 - 0.6, BOX_Z1 + 0.5, 2, want='in', keep=is_west)
ring(bm, BOX_D0, BOX_Z1 - 0.05, BOX_D1, BOX_Z1 - 0.05, 2, want='down', keep=is_west)
ring(bm, BOX_D1, BOX_Z0, BOX_D1, BOX_Z1, 4, want='in', keep=is_west)
for i in range(W_I0, W_I1 + 1):
    out = NODES[i][1]
    tg = Vector((-out.y, out.x, 0))
    a_, b_ = P(i, 0, BOX_D0), P(i, 0, BOX_D1)
    box(bm, (a_ + b_) / 2, out, (BOX_D1 - BOX_D0) / 2, tg, 0.1, BOX_Z0, BOX_Z1, 2)
# the back of the second ring, the end walls where it meets the bowl
ring(bm, W_BACK, W_TOP, W_BACK, W_TOP + 2.0, 0, want='in', keep=is_west)
ring(bm, W_BACK + 0.3, 6.0, W_BACK + 0.3, W_TOP + 2.0, 1, want='out', keep=is_west, zstep=4.0)
ring(bm, W_BACK, W_TOP + 2.0, W_BACK + 0.3, W_TOP + 2.0, 0, want='up', keep=is_west)


def west_top(d):
    # the Occidental's profile top at d: the boxes, then its second ring
    if d < BOX_D1:
        return BOX_Z1 + 0.5
    for d0, d1, z, kind in W_ROWS:
        if d0 <= d < d1:
            return z
    return W_TOP + 2.0


def bowl_top(d):
    for d0, d1, z, kind in LOW_ROWS + UP_ROWS:
        if d0 <= d < d1:
            return z
    return TOP_Z + 1.05


for i_, sgn in ((W_I0, -1), (W_I1, 1)):
    out = NODES[i_][1]
    tg = Vector((-out.y, out.x, 0)) * sgn
    ds = [BOX_D0 - 0.6] + [r[0] for r in W_ROWS] + [W_BACK + 0.3]
    for da, db in zip(ds, ds[1:]):
        pa, pb = P(i_, 0, da), P(i_, 0, db)
        za, zb = bowl_top(da), bowl_top(db - 0.01)
        ta, tb = west_top(da) + 1.1, west_top(db - 0.01) + 1.1
        if ta > za and tb > zb:
            face(bm, [(pa.x, pa.y, za), (pb.x, pb.y, zb), (pb.x, pb.y, tb), (pa.x, pa.y, ta)], tg, 0)
new_obj('Occidental', bm, '02_Bowl', [concrete_light, concrete_dark, white_paint, glazing, portal])

# its roof: flat sheeting falling gently to the back, a white fascia with
# the floodlights at the front, radial beams under it on posts at the back,
# reaching out over the street behind
bm, lamps2 = bmesh.new(), bmesh.new()
wr_z = lambda d: WR_Z0 + (WR_Z1 - WR_Z0) * (d - WR_D0) / (WR_D1 - WR_D0)
for i in range(W_I0, W_I1):
    for b0, b1 in ((WR_D0, 12.0), (12.0, 22.0), (22.0, 32.0), (32.0, WR_D1)):
        p0, p1, q0, q1 = P(i, 0, b0), P(i, 1, b0), P(i, 0, b1), P(i, 1, b1)
        face(bm, [(p0.x, p0.y, wr_z(b0)), (p1.x, p1.y, wr_z(b0)), (q1.x, q1.y, wr_z(b1)), (q0.x, q0.y, wr_z(b1))], UPV, 0)
        Lp = (p1 - p0).length
        face(bm, [(p0.x, p0.y, wr_z(b0) - 0.4), (p1.x, p1.y, wr_z(b0) - 0.4), (q1.x, q1.y, wr_z(b1) - 0.4), (q0.x, q0.y, wr_z(b1) - 0.4)], -UPV, 1,
             [(i * Lp / 4.0, b0 / 4.0), ((i + 1) * Lp / 4.0, b0 / 4.0), ((i + 1) * Lp / 4.0, b1 / 4.0), (i * Lp / 4.0, b1 / 4.0)])
ring(bm, WR_D0, WR_Z0 - 1.4, WR_D0, WR_Z0 + 0.2, 2, want='in', keep=is_west)
ring(bm, WR_D1, WR_Z1 - 0.9, WR_D1, WR_Z1 + 0.15, 2, want='out', keep=is_west)
for i_, sgn in ((W_I0, -1), (W_I1, 1)):
    out = NODES[i_][1]
    tg = Vector((-out.y, out.x, 0)) * sgn
    pa, pb = P(i_, 0, WR_D0), P(i_, 0, WR_D1)
    face(bm, [(pa.x, pa.y, WR_Z0 - 1.4), (pb.x, pb.y, WR_Z1 - 0.9), (pb.x, pb.y, WR_Z1 + 0.15), (pa.x, pa.y, WR_Z0 + 0.2)], tg, 2)
for i in range(W_I0, W_I1 + 1):
    if (i - W_I0) % 2:
        continue
    # a radial beam: deep at the posts, thin at both tips
    pa, pb = P(i, 0, WR_D0 + 0.3), P(i, 0, WR_D1 - 0.3)
    prism(bm, pa, pb, 0.5, lambda t: wr_z(WR_D0 + (WR_D1 - WR_D0) * t) - 0.4,
          lambda t: wr_z(WR_D0 + (WR_D1 - WR_D0) * t) - 0.4 - (0.6 + 2.2 * max(0.0, 1 - abs((WR_D0 + (WR_D1 - WR_D0) * t) - W_BACK) / 26.0)), 3)
    pc = P(i, 0, W_BACK - 0.2)
    tube(bm, Vector((pc.x, pc.y, W_TOP + 2.0)), Vector((pc.x, pc.y, wr_z(W_BACK) - 2.5)), 0.35, 3, 8)
for i in range(W_I0, W_I1):
    out = (NODES[i][1] + NODES[i + 1][1]).normalized()
    tg = (P(i, 1, WR_D0) - P(i, 0, WR_D0)).normalized()
    for u_ in (0.2, 0.5, 0.8):
        c = P(i, u_, WR_D0 + 0.6) + Vector((0, 0, WR_Z0 - 1.75))
        fwd = (-out * math.cos(math.radians(38)) - UPV * math.sin(math.radians(38))).normalized()
        upl = tg.cross(fwd).normalized()
        if upl.z < 0:
            upl = -upl
        obox(lamps2, c, fwd, tg, upl, 0.22, 0.32, 0.26, 0)
        cc = c + fwd * 0.23
        face(lamps2, [cc - tg * 0.27 - upl * 0.21, cc + tg * 0.27 - upl * 0.21, cc + tg * 0.27 + upl * 0.21, cc - tg * 0.27 + upl * 0.21], fwd, 1)
new_obj('Occidental_Roof', bm, '04_Roof', [roof_metal, roof_under_mat, white_paint, steel_grey])
new_obj('Lamps_Ring', lamps, '04_Roof', [lamp, lamp_glass])
new_obj('Lamps_Occidental', lamps2, '04_Roof', [lamp, lamp_glass])

# ================================================================ the LED screen on the north end's roof
# east of the end's middle, standing on the roof ring on a black frame,
# facing the pitch (the photos of 2024)
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
bm, fb = bmesh.new(), bmesh.new()
i_s = min(range(NP), key=lambda j: abs(math.degrees(math.atan2(NODES[j][0].y, NODES[j][0].x)) - (-17.0)))
out_s = NODES[i_s][1]
right = out_s.cross(UPV).normalized()                # the viewer's right, looking at the screen from the pitch
c_s = P(i_s, 0, 25.2) + Vector((0, 0, can_z(25.2) + 0.7 + SCR_H / 2))
obox(bm, c_s + out_s * 0.5, out_s, right, UPV, 0.45, SCR_W / 2 + 0.25, SCR_H / 2 + 0.25, 0)
for lx in (-1, 1):
    for dd in (0.2, 2.6):
        pl = c_s + right * lx * (SCR_W / 2 - 1.5) + out_s * (0.6 + dd)
        tube(bm, Vector((pl.x, pl.y, can_z(25.2 + dd))), Vector((pl.x, pl.y, c_s.z - SCR_H / 2)), 0.14, 1, 6)
    pl = c_s + right * lx * (SCR_W / 2 - 1.5)
    tube(bm, pl + out_s * 0.9 + Vector((0, 0, -SCR_H / 2)), pl + out_s * 3.2 + Vector((0, 0, SCR_H / 2 - 0.5)), 0.1, 1, 6)
c0 = c_s - out_s * 0.03
face(fb, [c0 - right * SCR_W / 2 - UPV * SCR_H / 2, c0 + right * SCR_W / 2 - UPV * SCR_H / 2,
          c0 + right * SCR_W / 2 + UPV * SCR_H / 2, c0 - right * SCR_W / 2 + UPV * SCR_H / 2], -out_s, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
new_obj('Screen_Frame', bm, '04_Roof', [steel_dark, steel_grey])
screen_face = new_obj('ScreenFace_0', fb, '04_Roof', [live])

# ================================================================ round the pitch: the boards, the dugouts
bm = bmesh.new()
BH = 0.9
BOARD_X, BOARD_Y = PW / 2 + 5.0, PL / 2 + 5.0
V = lambda x, y, z: Vector((x, y, z))


def board_run(a, b, nrm, u0):
    # a row of boards from a to b, facing nrm; u runs with the reading direction
    L = (b - a).length
    n = max(1, math.ceil(L / 4.0))
    o = nrm * 0.15
    for k in range(n):
        p0, p1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        ua, ub = (u0 + L * k / n) / 56.0, (u0 + L * (k + 1) / n) / 56.0
        face(bm, [p0 + o, p1 + o, p1 + o + Vector((0, 0, BH)), p0 + o + Vector((0, 0, BH))], nrm, 0, [(ua, 0), (ub, 0), (ub, 1), (ua, 1)])
        face(bm, [p0 - o, p1 - o, p1 - o + Vector((0, 0, BH)), p0 - o + Vector((0, 0, BH))], -nrm, 1)
        face(bm, [p0 - o + Vector((0, 0, BH)), p1 - o + Vector((0, 0, BH)), p1 + o + Vector((0, 0, BH)), p0 + o + Vector((0, 0, BH))], UPV, 1)
    return u0 + L


u = 0.0
u = board_run(V(BOARD_X - 1.0, -BOARD_Y, 0), V(-BOARD_X + 1.0, -BOARD_Y, 0), V(0, 1, 0), u)          # the Oriental's side, read from the pitch
u = board_run(V(-BOARD_X, -BOARD_Y + 1.0, 0), V(-BOARD_X, BOARD_Y - 1.0, 0), V(1, 0, 0), u)         # the south end
u = board_run(V(BOARD_X, BOARD_Y - 1.0, 0), V(BOARD_X, -BOARD_Y + 1.0, 0), V(-1, 0, 0), u)          # the north end
u = board_run(V(-BOARD_X + 1.0, BOARD_Y, 0), V(-22.0, BOARD_Y, 0), V(0, -1, 0), u)                  # the Occidental's side, either side of the dugouts
u = board_run(V(22.0, BOARD_Y, 0), V(BOARD_X - 1.0, BOARD_Y, 0), V(0, -1, 0), u)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_dark])

# the dugouts: two long blue tubes on the Occidental's side, open to the
# pitch, a silver box for the fourth official between them (2019, 2023)
bm = bmesh.new()
DUG_Y, DUG_L, DUG_R = PL / 2 + 6.5, 13.0, 1.25
for xc in (-11.0, 11.0):
    x0_, x1_ = xc - DUG_L / 2, xc + DUG_L / 2
    angs = [math.radians(a) for a in range(-80, 141, 20)]          # from the bottom at the back round over the top to the front lip
    ring_pts = lambda x, a: Vector((x, DUG_Y + DUG_R * math.cos(a) * 1.0, 0.3 + DUG_R + DUG_R * math.sin(a)))
    for a0, a1 in zip(angs, angs[1:]):
        for xa, xb in ((x0_, xc), (xc, x1_)):
            q = [ring_pts(xa, a0), ring_pts(xb, a0), ring_pts(xb, a1), ring_pts(xa, a1)]
            cen = Vector((xa / 2 + xb / 2, DUG_Y, 0.3 + DUG_R))
            face(bm, q, (q[0] + q[2]) / 2 - cen, 0)
            face(bm, q[::-1], cen - (q[0] + q[2]) / 2, 0)
    for xe in (x0_, x1_):
        pts_ = [Vector((xe, DUG_Y - DUG_R * 0.2, 0.3))] + [ring_pts(xe, a) for a in angs]
        face(bm, pts_, Vector((1 if xe > xc else -1, 0, 0)), 0)
    abox(bm, x0_, x1_, DUG_Y - DUG_R, DUG_Y + DUG_R, 0.0, 0.3, 1, top=True)
    # the seats inside
    for k in range(int(DUG_L / 0.6)):
        xs_ = x0_ + 0.3 + k * 0.6
        seat_geo(bm, [V(xs_, DUG_Y - 0.2, 0.3), V(xs_ + 0.5, DUG_Y - 0.2, 0.3)], [V(xs_, DUG_Y + 0.75, 0.3), V(xs_ + 0.5, DUG_Y + 0.75, 0.3)],
                 Vector((0, 1, 0)), 2, 0, 1, cush=0.45, top=1.05, fwd=0.2)
abox(bm, -1.0, 1.0, DUG_Y - 0.6, DUG_Y + 0.6, 0.0, 2.1, 3, top=True)
new_obj('Dugouts', bm, '02_Bowl', [blue_tube, concrete_dark, seat_cols[GRY], galv])

# the players' way out under the Occidental's middle
bm = bmesh.new()
i_t = NP // 2
pa = P(i_t, 0, -0.03)
out = NODES[i_t][1]
tg = Vector((-out.y, out.x, 0))
face(bm, [tuple(pa - tg * 2.2), tuple(pa + tg * 2.2), tuple(pa + tg * 2.2 + Vector((0, 0, FRONT_Z - 0.05))), tuple(pa - tg * 2.2 + Vector((0, 0, FRONT_Z - 0.05)))], -out, 0)
pb = P(i_t, 0, -0.06)
face(bm, [tuple(pb - tg * 2.5 + Vector((0, 0, FRONT_Z - 0.3))), tuple(pb + tg * 2.5 + Vector((0, 0, FRONT_Z - 0.3))), tuple(pb + tg * 2.5 + Vector((0, 0, FRONT_Z))), tuple(pb - tg * 2.5 + Vector((0, 0, FRONT_Z)))], -out, 1)
new_obj('Tunnel', bm, '02_Bowl', [portal, yellow_paint])

# ================================================================ outside the bowl
# the stands' underside painted cream, raked from the front wall to the top;
# the grey frames under it every section with their V-struts; the balcony
# round the middle; the brown fence at the foot; not under the Occidental
bm = bmesh.new()
SOF_D0, SOF_Z0, SOF_Z1 = 1.0, 1.4, TOP_Z - 0.55
sof_z = lambda d: SOF_Z0 + (SOF_Z1 - SOF_Z0) * (d - SOF_D0) / (BACK_D - SOF_D0)
cum_s = cumlen(BACK_D)
slope = math.hypot(BACK_D - SOF_D0, SOF_Z1 - SOF_Z0)
for i in range(NP):
    if is_west(i):
        continue
    p0, p1, q0, q1 = P(i, 0, SOF_D0), P(i, 1, SOF_D0), P(i, 0, BACK_D), P(i, 1, BACK_D)
    ua, ub = cum_s[i] / 4.0, cum_s[i + 1] / 4.0
    face(bm, [(p0.x, p0.y, SOF_Z0), (p1.x, p1.y, SOF_Z0), (q1.x, q1.y, SOF_Z1), (q0.x, q0.y, SOF_Z1)], -UPV, 0,
         [(ua, 0), (ub, 0), (ub, slope / 6.7), (ua, slope / 6.7)])
ring(bm, BACK_D + 0.25, SOF_Z1, BACK_D + 0.25, TOP_Z - 0.8, 1, want='out', keep=lambda i: not is_west(i))
# the balcony: 7.2 m up, from under the stands out past their back, a parapet and a rail
BAL_Z, BAL_D0, BAL_D1 = 7.2, 22.5, 30.6
ring(bm, BAL_D0, BAL_Z, BAL_D1, BAL_Z, 1, want='up', keep=lambda i: not is_west(i))
ring(bm, BAL_D0, BAL_Z - 0.45, BAL_D1, BAL_Z - 0.45, 1, want='down', keep=lambda i: not is_west(i))
ring(bm, BAL_D1, BAL_Z - 0.45, BAL_D1, BAL_Z + 1.1, 1, want='out', keep=lambda i: not is_west(i))
ring(bm, BAL_D1 - 0.2, BAL_Z, BAL_D1 - 0.2, BAL_Z + 1.1, 1, want='in', keep=lambda i: not is_west(i))
# the fence at the foot: brown panels, dark doors in every third section
FENCE_D = 27.0
ring(bm, FENCE_D, 0.0, FENCE_D, 3.0, 2, want='out', keep=lambda i: not is_west(i))
for i in range(NP):
    if is_west(i):
        continue
    out = (NODES[i][1] + NODES[i + 1][1]).normalized()
    if section(i) % 3 == 0 and i % 3 == 1:
        a_, b_ = P(i, 0.3, FENCE_D + 0.04), P(i, 0.7, FENCE_D + 0.04)
        face(bm, [(a_.x, a_.y, 0.0), (b_.x, b_.y, 0.0), (b_.x, b_.y, 2.4), (a_.x, a_.y, 2.4)], out, 3)
    if not is_aisle(i):
        continue
    # the frame: a raker under the steps, a post at the back, a V of struts
    pa, pb = P(i, 0, 3.0), P(i, 0, BACK_D - 0.2)
    prism(bm, pa, pb, 0.55, lambda t: sof_z(3.0 + (BACK_D - 3.2) * t) - 0.02, lambda t: sof_z(3.0 + (BACK_D - 3.2) * t) - 1.1, 4)
    pc = P(i, 0, BACK_D - 0.6)
    box(bm, pc, out, 0.35, Vector((-out.y, out.x, 0)), 0.3, 0.0, SOF_Z1 - 0.3, 4)
    top_v = P(i, 0, 21.0) + Vector((0, 0, sof_z(21.0) - 1.0))
    for dg in (14.0, 26.5):
        g_ = P(i, 0, dg)
        tube(bm, Vector((g_.x, g_.y, 0.0)), top_v, 0.3, 4, 6, step=3.0)
    # the balcony's bracket
    pk = P(i, 0, BAL_D1 - 0.3)
    tube(bm, Vector((pk.x, pk.y, BAL_Z - 0.45)), P(i, 0, 26.8) + Vector((0, 0, 3.0)), 0.18, 4, 6)
new_obj('Outside_Bowl', bm, '05_Outside', [soffit, taupe, fence_brown, portal, taupe])
bm = bmesh.new()
for i in range(NP):
    if is_west(i):
        continue
    a_, b_ = P(i, 0, BAL_D1 - 0.1), P(i, 1, BAL_D1 - 0.1)
    tube(bm, Vector((a_.x, a_.y, BAL_Z + 1.6)), Vector((b_.x, b_.y, BAL_Z + 1.6)), 0.03, 0, 5, step=4.0)
    tube(bm, Vector((a_.x, a_.y, BAL_Z + 1.1)), Vector((a_.x, a_.y, BAL_Z + 1.6)), 0.025, 0, 4)
new_obj('Balcony_Rail', bm, '05_Outside', [galv])

# the Occidental outside: the concrete base with its grey doors, the steel
# balcony along the boxes' level on V-struts, the big stairs, the glass lift
# tower at its south end, the glass box at its north end (2011, 2024)
bm = bmesh.new()
BASE_D, BASE_Z = W_BACK + 0.4, 6.0
ring(bm, BASE_D, 0.0, BASE_D, BASE_Z, 0, want='out', keep=is_west, zstep=3.0)
ring(bm, W_BACK, BASE_Z, BASE_D + 3.5, BASE_Z, 0, want='up', keep=is_west)
ring(bm, BASE_D + 3.5, BASE_Z - 0.4, BASE_D + 3.5, BASE_Z + 1.1, 2, want='out', keep=is_west)
ring(bm, W_BACK + 0.3, BOX_Z0, BASE_D + 2.4, BOX_Z0, 1, want='up', keep=is_west)
ring(bm, W_BACK + 0.3, BOX_Z0 - 0.4, BASE_D + 2.4, BOX_Z0 - 0.4, 1, want='down', keep=is_west)
for i in range(W_I0, W_I1):
    out = (NODES[i][1] + NODES[i + 1][1]).normalized()
    tg = (P(i, 1, BASE_D) - P(i, 0, BASE_D)).normalized()
    if i % 2 == 0:
        a_, b_ = P(i, 0.25, BASE_D + 0.04), P(i, 0.75, BASE_D + 0.04)
        face(bm, [(a_.x, a_.y, 0.0), (b_.x, b_.y, 0.0), (b_.x, b_.y, 3.4), (a_.x, a_.y, 3.4)], out, 3)
    # the balcony's truss rail and its struts
    ea, eb = P(i, 0, BASE_D + 2.3), P(i, 1, BASE_D + 2.3)
    for zz in (BOX_Z0 + 0.1, BOX_Z0 + 1.15):
        tube(bm, Vector((ea.x, ea.y, zz)), Vector((eb.x, eb.y, zz)), 0.06, 4, 6, step=4.0)
    tube(bm, Vector((ea.x, ea.y, BOX_Z0 + 0.1)), Vector((eb.x, eb.y, BOX_Z0 + 1.15)), 0.04, 4, 5)
    if i % 2 == 0:
        g_ = P(i, 0, BASE_D + 1.0)
        tube(bm, Vector((g_.x, g_.y, BASE_Z)), Vector((ea.x, ea.y, BOX_Z0 - 0.4)) - tg * 1.5, 0.22, 4, 6)
        tube(bm, Vector((g_.x, g_.y, BASE_Z)), Vector((ea.x, ea.y, BOX_Z0 - 0.4)) + tg * 1.5, 0.22, 4, 6)
# the stairs up to the base's top, two in the middle third
for i in (W_I0 + (W_I1 - W_I0) // 3, W_I0 + 2 * (W_I1 - W_I0) // 3):
    out = NODES[i][1]
    tg = Vector((-out.y, out.x, 0))
    n_st = 20
    for k in range(n_st):
        dd = BASE_D + 3.5 + (n_st - k) * 0.4
        zz = BASE_Z * (k + 1) / n_st
        p_ = P(i, 0, dd)
        box(bm, p_, out, 0.2, tg, 2.6, 0.0, zz, 0)
# the lift tower at the south end, the glass box at the north
for i_, kind in ((W_I0 + 1, 'lift'), (W_I1 - 2, 'box')):
    out = NODES[i_][1]
    tg = Vector((-out.y, out.x, 0))
    if kind == 'lift':
        c_ = P(i_, 0, BASE_D + 2.2)
        box(bm, c_, out, 1.6, tg, 1.6, 0.0, W_TOP + 4.0, 5, top=True)
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            q_ = c_ + out * 1.65 * sx + tg * 1.65 * sy
            tube(bm, Vector((q_.x, q_.y, 0.0)), Vector((q_.x, q_.y, W_TOP + 4.0)), 0.12, 4, 6)
        for zz in range(0, int(W_TOP + 4), 3):
            for a_, b_ in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
                pa_ = c_ + out * 1.65 * a_[0] + tg * 1.65 * a_[1]; pb_ = c_ + out * 1.65 * b_[0] + tg * 1.65 * b_[1]
                tube(bm, Vector((pa_.x, pa_.y, zz)), Vector((pb_.x, pb_.y, zz + 3.0)), 0.05, 4, 4)
    else:
        c_ = P(i_, 0, BASE_D + 3.0)
        box(bm, c_, out, 3.0, tg, 6.0, BOX_Z0, BOX_Z0 + 3.6, 5, top=True)
        box(bm, c_, out, 3.2, tg, 6.2, BOX_Z0 + 3.6, BOX_Z0 + 4.0, 2, top=True)
        for sy in (-1, 1):
            q_ = c_ + tg * 5.0 * sy + out * 2.0
            tube(bm, Vector((q_.x, q_.y, 0.0)), Vector((q_.x, q_.y, BOX_Z0)), 0.3, 4, 8)
glass_lift = image_material('M_LiftGlass', painted('ec_liftglass', glazing_tex() * 0.6 + 0.08), 0.2)
new_obj('Occidental_Outside', bm, '05_Outside', [concrete_light, concrete_dark, white_paint, steel_grey, steel_grey, glass_lift])

# ================================================================ the floodlight towers and the scoreboard tower
# four lattice towers behind the corners, 50 m, a frame of lamps on top
# aimed at the middle of the pitch; the old scoreboard tower by the south-west
bm = bmesh.new()


def lattice_tower(bm, base, h, w0, w1, mat):
    k_n = int(h / 4.0)
    pts_at = lambda z: [base + Vector((sx * (w0 + (w1 - w0) * z / h) / 2, sy * (w0 + (w1 - w0) * z / h) / 2, z)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k in range(4):
        a_ = pts_at(0)[k]; b_ = pts_at(h)[k]
        tube(bm, a_, b_, 0.12, mat, 6, step=6.0)
    for j in range(k_n):
        za, zb = h * j / k_n, h * (j + 1) / k_n
        pa_, pb_ = pts_at(za), pts_at(zb)
        for k in range(4):
            tube(bm, pa_[k], pb_[(k + 1) % 4], 0.05, mat, 4)
            tube(bm, pb_[k], pb_[(k + 1) % 4], 0.05, mat, 4)


for deg in (40.0, 140.0, 220.0, 320.0):
    i_m = min(range(NP), key=lambda j: abs(((math.degrees(math.atan2(NODES[j][0].y, NODES[j][0].x)) - deg + 180) % 360) - 180))
    base = P(i_m, 0, D_OUT[i_m] + 7.0)
    lattice_tower(bm, base, MAST_H, 2.6, 1.4, 0)
    to_c = Vector((-base.x, -base.y, 0)).normalized()
    side = Vector((-to_c.y, to_c.x, 0))
    top = base + Vector((0, 0, MAST_H))
    fwd = (to_c * math.cos(math.radians(28)) - UPV * math.sin(math.radians(28))).normalized()
    upl = side.cross(fwd).normalized()
    if upl.z < 0:
        upl = -upl
    fc = top + upl * 2.6 + to_c * 0.6
    obox(bm, fc - fwd * 0.3, fwd, side, upl, 0.15, 4.6, 2.6, 0)
    for r_ in range(4):
        for c_ in range(7):
            lc = fc + side * (c_ - 3) * 1.25 + upl * (r_ - 1.5) * 1.2
            obox(bm, lc, fwd, side, upl, 0.25, 0.5, 0.45, 1)
            cc = lc + fwd * 0.26
            face(bm, [cc - side * 0.42 - upl * 0.36, cc + side * 0.42 - upl * 0.36, cc + side * 0.42 + upl * 0.36, cc - side * 0.42 + upl * 0.36], fwd, 2)
# the scoreboard tower: a concrete pylon with a black face, a lattice mast on top
i_b = min(range(NP), key=lambda j: abs(((math.degrees(math.atan2(NODES[j][0].y, NODES[j][0].x)) - 150.0 + 180) % 360) - 180))
cb = P(i_b, 0, D_OUT[i_b] + 16.0)
to_c = Vector((-cb.x, -cb.y, 0)).normalized()
side = Vector((-to_c.y, to_c.x, 0))
box(bm, cb, to_c, 1.6, side, 2.2, 0.0, 22.0, 3, top=True)
box(bm, cb - to_c * 1.75, to_c, 0.2, side, 2.0, 9.0, 21.0, 4, top=True)
lattice_tower(bm, cb + Vector((0, 0, 22.0)), 9.0, 1.4, 1.2, 0)
for k in range(3):
    obox(bm, cb + Vector((0, 0, 22.0 + 7.5 + k * 0.01)) + side * (k - 1) * 1.0, -to_c, side, UPV, 0.3, 0.45, 0.6, 1)
new_obj('Masts', bm, '05_Outside', [galv, lamp, lamp_glass, concrete_light, steel_dark])


# ================================================================ outside: the plaza round the stadium, trees
G_HALF = 320.0                   # tools/campin/ground.png covers 640 x 640 m
AP_X0, AP_X1, AP_Y0, AP_Y1 = -180.0, 180.0, -170.0, 180.0     # on the backdrop's 10 m grid: no overlap, no dark seam
G_Z = -0.12
COMPLEX = _ring(OSM['ways']['complex'])
HY0 = -235.0                     # the foot of the hills in the east


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


def inside_bowl(xa, xb, ya, yb):
    # every corner of the cell inside the stadium's outline: the bowl, not the plaza
    return all(inside_poly(x, y, OUTLINE) for x, y in ((xa, ya), (xb, ya), (xb, yb), (xa, yb)))


bm = bmesh.new()
ground_cells(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 5.0, inside_bowl)
new_obj('Ground', bm, '05_Outside', [ground_mat])

trng = random.Random(1938)


def tree(bm, x, y, h, r):
    tube(bm, Vector((x, y, G_Z)), Vector((x, y, G_Z + h * 0.6)), 0.24, 0, 5, step=4.0)
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector((r, r * trng.uniform(0.85, 1.1), h * 0.32)), verts=res['verts'])
    bmesh.ops.translate(bm, vec=Vector((x, y, G_Z + h * 0.7)), verts=res['verts'])
    uvl = bm.loops.layers.uv.verify()
    for f_ in {f_ for v_ in res['verts'] for f_ in v_.link_faces}:
        f_.material_index = 1
        for l in f_.loops:
            l[uvl].uv = (l.vert.co.x / 6.0, (l.vert.co.y + l.vert.co.z) / 6.0)


ROAD_HALF = {'trunk': 13.0, 'trunk_link': 5.0, 'primary': 9.0, 'primary_link': 5.0, 'secondary': 6.5, 'tertiary': 5.5, 'tertiary_link': 4.0,
             'residential': 4.5, 'service': 3.0, 'unclassified': 4.5, 'living_street': 3.5}


def near_road(x, y, margin):
    for r in OSM['roads'] + OSM['busway']:
        pts = r['pts']
        if r['type'] in ('footway', 'path', 'cycleway', 'steps', 'pedestrian', 'corridor', 'construction', 'proposed'):
            continue
        w = ROAD_HALF.get(r['type'], 3.0)
        if r.get('name') == 'TransMilenio':
            w = 5.0
        for k in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            if min(ax, bx) - 25 > x or max(ax, bx) + 25 < x or min(ay, by) - 25 > y or max(ay, by) + 25 < y:
                continue
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-6, dx * dx + dy * dy)))
            if math.hypot(x - ax - t * dx, y - ay - t * dy) < w + margin:
                return True
    return False


# the new stadium's site north-east of the old one: works begun in September 2026, bare ground
SITE = (75.0, 300.0, -255.0, -70.0)
in_site = lambda x, y: SITE[0] < x < SITE[1] and SITE[2] < y < SITE[3]


def clear_spot(x, y, margin=2.5):
    if inside_poly(x, y, COMPLEX) or inside_poly(x, y, OUTLINE) or in_site(x, y):
        return False
    for b in OSM['buildings']:
        bx, by = b['pts'][0]
        if abs(bx - x) < 80 and abs(by - y) < 80 and inside_poly(x, y, b['pts']):
            return False
    for g in OSM['parking'] + OSM['water'] + OSM['squares']:
        if inside_poly(x, y, g):
            return False
    return not near_road(x, y, margin)


def green(x, y):
    return any(inside_poly(x, y, g) for g in OSM['park'] + OSM['grass'])


def park_trees(bm, x0, x1, y0, y1, step, keep):
    for ix in range(int((x1 - x0) / step)):
        for iy in range(int((y1 - y0) / step)):
            x = x0 + (ix + trng.random()) * step
            y = y0 + (iy + trng.random()) * step
            if not keep(x, y):
                continue
            if trng.random() < (0.7 if green(x, y) else 0.06) and clear_spot(x, y):
                tree(bm, x, y, trng.uniform(9, 16), trng.uniform(2.8, 4.6))


bm = bmesh.new()
for x_, y_ in OSM['trees']:
    if AP_X0 < x_ < AP_X1 and AP_Y0 < y_ < AP_Y1 and not inside_poly(x_, y_, OUTLINE):
        tree(bm, x_, y_, trng.uniform(8, 13), trng.uniform(2.4, 3.8))
park_trees(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 9.0, lambda x, y: True)
# the palms and the young trees along the plaza's edge by Avenida NQS (the photos of the outside)
for k in range(26):
    x_ = -140.0 + k * 11.0
    y_ = 100.0 + trng.uniform(-2, 2)
    if not inside_poly(x_, y_ - 4, OUTLINE):
        tree(bm, x_, y_, trng.uniform(6, 9), trng.uniform(1.8, 2.6))
near_trees = new_obj('Trees', bm, '05_Outside', [trunk, foliage])


# ================================================================ the backdrop: the town from OpenStreetMap
bm = bmesh.new()
ground_cells(bm, -G_HALF, G_HALF, -G_HALF, G_HALF, 10.0, lambda xa, xb, ya, yb: AP_X0 <= xa and xb <= AP_X1 and AP_Y0 <= ya and yb <= AP_Y1)
far_ground = new_obj('Ground_Far', bm, '06_Backdrop', [ground_mat])

bm = bmesh.new()
HEIGHT = {'house': 7.0, 'detached': 7.0, 'residential': 12.0, 'terrace': 7.0, 'garage': 2.8, 'garages': 2.8,
          'shed': 2.6, 'roof': 5.0, 'canopy': 4.0, 'apartments': 18.0, 'school': 10.0, 'office': 18.0, 'commercial': 9.0,
          'retail': 7.0, 'church': 15.0, 'service': 4.0, 'construction': 12.0}


def extrude(bm, pts, h, wall_m, roof_m, tall):
    sa = 0.5 * sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    ucum = 0.0
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sa > 0 else -1)
        Lw = math.hypot(c_[0] - a_[0], c_[1] - a_[1])
        nz = max(1, math.ceil(h / 3.2))
        for q in range(nz):
            za, zb = G_Z + h * q / nz, G_Z + h * (q + 1) / nz
            if tall:
                face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, 7,
                     [(ucum / 12.0, za / 12.0), ((ucum + Lw) / 12.0, za / 12.0), ((ucum + Lw) / 12.0, zb / 12.0), (ucum / 12.0, zb / 12.0)])
            else:
                face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, wall_m)
        ucum += Lw
    try:
        rf = bm.faces.new([bm.verts.new((x, y, G_Z + h)) for x, y in pts])
    except ValueError:
        return
    rf.material_index = roof_m
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')


for b in OSM['buildings']:
    pts = b['pts'][:-1] if b['pts'][0] == b['pts'][-1] else b['pts']
    if len(pts) < 3 or max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4:
        continue
    if b['type'] == 'stadium' or any(in_site(x, y) for x, y in pts):
        continue
    area = abs(0.5 * sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts))))
    if area < 5:
        continue
    h = HEIGHT.get(b['type'], 12.0 if area > 400 else 8.0)
    if b.get('height'):
        try:
            h = float(b['height'])
        except ValueError:
            pass
    elif b.get('levels'):
        try:
            h = float(b['levels']) * 3.0 + 1.0
        except ValueError:
            pass
    if b.get('name') == 'El Campín':
        extrude(bm, pts, 4.6, 8, 3, False)                  # the TransMilenio station El Campín in the avenue's middle: glass
        continue
    tall = h > 14.0
    extrude(bm, pts, h, 1 if trng.random() < 0.7 else 2, 3, tall)

# the brick town OSM leaves out: blocks of three to six floors of red brick
# between the streets of Galerías, Nicolás de Federmán and Teusaquillo,
# a tower of flats here and there (the photos over the Oriental)
STEP_B = 14.0
n_blocks = 0
for ix in range(int(-G_HALF / STEP_B) + 1, int(G_HALF / STEP_B) - 1):
    for iy in range(int(-G_HALF / STEP_B) + 1, int(G_HALF / STEP_B) - 1):
        cx_, cy_ = (ix + 0.5) * STEP_B, (iy + 0.5) * STEP_B
        if max(abs(cx_), abs(cy_)) > G_HALF - 10 or cy_ < HY0 - 15:
            continue
        if inside_poly(cx_, cy_, COMPLEX) or d_of(cx_, cy_) < 45 or in_site(cx_, cy_) or green(cx_, cy_):
            continue
        for hw, hd in ((trng.uniform(5.0, 6.6), trng.uniform(5.0, 6.6)), (3.6, 3.6)):
            corners = [(cx_ - hw, cy_ - hd), (cx_ + hw, cy_ - hd), (cx_ + hw, cy_ + hd), (cx_ - hw, cy_ + hd)]
            if all(clear_spot(x, y, 0.5) for x, y in corners + [(cx_, cy_)]):
                break
        else:
            continue
        n_blocks += 1
        r_ = trng.random()
        h = trng.choice((9.5, 12.5, 12.5, 15.5, 18.5)) if r_ > 0.08 else trng.uniform(28.0, 48.0)
        extrude(bm, corners, h, 1 if trng.random() < 0.6 else (2 if trng.random() < 0.7 else 5), 3, h > 14.0 and trng.random() < 0.8)
print('TOWN BLOCKS', n_blocks)
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, brick_light, flat_roof, office_wall, plaster, tiles_dark, tower_block,
                                                     principled('M_StationGlass', (0.10, 0.12, 0.13), 0.2)])

# the Cerros Orientales: the foot of the hills at the eastern edge, rising
# out of the town, so they stand over the Oriental as on the photos
bm = bmesh.new()
def hz(x, y):
    f_ = max(0.0, min(1.0, (HY0 - y) / (HY0 + G_HALF)))
    ridge = 1 + 0.18 * math.sin(x / 61.0 + 0.4) + 0.10 * math.sin(x / 23.0 + 1.3) + 0.05 * math.sin(x / 9.0 + 2.1)
    gully = 0.08 * math.sin(x / 13.0) * f_
    return G_Z + 78.0 * (ridge + gully) * f_ ** 1.6


for ix in range(64):
    for iy in range(10):
        xa, xb = -G_HALF + ix * 10.0, -G_HALF + (ix + 1) * 10.0
        ya, yb = HY0 - iy * (G_HALF + HY0) / 10, HY0 - (iy + 1) * (G_HALF + HY0) / 10
        q = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
        face(bm, [(x, y, hz(x, y)) for x, y in q], UPV, 0, [((x + G_HALF) / 320.0, (HY0 - y) / (HY0 + G_HALF)) for x, y in q])
hills = new_obj('Hills', bm, '06_Backdrop', [hills_mat])
bm = bmesh.new()
park_trees(bm, -G_HALF + 8, G_HALF - 8, -G_HALF + 8, G_HALF - 8, 15.0, lambda x, y: not (AP_X0 < x < AP_X1 and AP_Y0 < y < AP_Y1) and y > HY0 + 10)
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
        'match': ((0, 62.0, 34.0), (0, -40.0, 8.0), 54),
        'east': ((0.0, 50.0, 14.0), (0.0, -90.0, 14.0), 66),            # the empty stadium (2019): the Oriental, IDRD BOGOTA, the hills
        'north': ((-40.0, 46.0, 4.0), (90.0, -10.0, 14.0), 62),          # towards the north end and the screen (2024)
        'west': ((0.0, -60.0, 12.0), (0.0, 80.0, 18.0), 66),             # the Occidental from the Oriental
        'south': ((60.0, -30.0, 14.0), (-95.0, 10.0, 12.0), 62),         # the south end and its curve
        'out_w': ((-30.0, 150.0, 1.7), (-10.0, 80.0, 16.0), 62),         # the Occidental from Avenida NQS
        'out_e': ((-60.0, -150.0, 1.7), (-20.0, -80.0, 10.0), 62),       # the bowl's outside from the east
        'out_sw': ((-150.0, 120.0, 1.7), (-90.0, 60.0, 14.0), 62),       # the scoreboard tower and the Occidental's end
        'air': ((-300.0, 230.0, 200.0), (0.0, 0.0, 0.0), 34),
        'air2': ((260.0, -200.0, 180.0), (0.0, 0.0, 10.0), 34),
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
floor_light = bake_lightmap(floor, 1000, 602)
grass.hide_render = False
inner = grass_light[int(464 * 0.25):int(464 * 0.75), int(704 * 0.25):int(704 * 0.75)]
lum_px = (inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1)
lum = float(np.percentile(lum_px, 80))  # the sunlit grass
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
    # El Campín's pitch as on the photos: broad bands across it, light
    # and dark, 20 over its length, wear in the goalmouths
    bands = np.tanh(np.sin(np.pi * X / (PW / 20)) * 6)
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
pitch_img = finish('ec_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: inside the stands' front the artificial turf round the
# pitch, the grey asphalt of the old track in the curves behind the goals and
# along the walls, a white line between them (2019, 2023)
H, W = 1204, 2000
X = (FX0 + (np.arange(W, dtype='f') + 0.5) / W * (FX1 - FX0))[None, :]
Y = (FY0 + (np.arange(H, dtype='f') + 0.5) / H * (FY1 - FY0))[:, None]
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
TURF_X, TURF_Y, TURF_R = 63.0, 49.6, 16.0
qx, qy = np.maximum(np.abs(X) - (TURF_X - TURF_R), 0), np.maximum(np.abs(Y) - (TURF_Y - TURF_R), 0)
dt = np.hypot(qx, qy) - TURF_R                        # out from the turf's edge (negative inside)
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.115, 0.115, 0.12)
alb *= (1 + 0.05 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 30, 30))[..., None]
turf = np.array((0.035, 0.105, 0.035), 'f') * (1 + 0.07 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 40, 40))[..., None]
alb = np.where((dt < 0)[..., None], turf, alb)
px = (FX1 - FX0) / W
edge = np.clip(1 - np.abs(dt - 0.1) / (0.12 + px), 0, 1)[..., None]
alb = alb * (1 - edge) + np.array((0.72, 0.72, 0.70), 'f') * edge
alb = np.where(((np.abs(X) < PITCH_X) & (np.abs(Y) < PITCH_Y))[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('ec_floor', alb, floor_light, H, W)
del alb, X, Y
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

skip = ('Pitch_Lines', 'StadiumGoals', 'Ground_Far', 'Buildings', 'Trees_', 'ScreenFace_', 'Hills')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, far_ground, buildings, far_trees, hills, screen_face]:
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
target.name = 'ElCampin'
select_only([far_ground, buildings, far_trees, hills], far_ground)
bpy.ops.object.join()
backdrop = far_ground
backdrop.name = 'StadiumBackdrop'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor'}
FIXED_LIGHT = {}


def bake_light(obj, samples=96, fill=0.0):
    # the sun into the vertex colours, at the pitch's exposure; the pitch and
    # the floor carry their own light in their pictures. `fill`: the light
    # thrown back by the sunlit pitch and stands into the shade under the
    # roofs, which the bake leaves far too dark
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
    c[:, :3] = c[:, :3] + fill * (1 - c[:, :3])
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


bake_light(target, fill=0.08)
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

