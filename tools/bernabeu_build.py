# Builds the Santiago Bernabéu (Madrid), as rebuilt 2019-2024, from nothing and
# exports it for the game, the way the other built stadiums are made: a
# floodlit night baked into the model. The retractable roof comes twice, open
# ('StadiumRoofOpen') and closed ('StadiumRoofClosed'); the game shows one of
# them (Stadion kiezen: Dak open / Dak dicht).
#   blender -b --factory-startup --python tools/bernabeu_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#
# As on the photos and the facts:
#   - the footprint and the pitch from OpenStreetMap (way 1507411898 and
#     1446479375, © OpenStreetMap contributors, ODbL), turned 4.2 degrees so the
#     pitch lies on the axes: a near-square of about 218 x 243 m with the
#     bulge of the east side, the stands close round the pitch (no track)
#   - inside: four rings of dark blue seats, steep and close; REAL MADRID in
#     white seats across the first ring of the east stand; white LED ribbons on
#     the front of the second and the top ring (BIENVENIDOS, WELCOME, ...);
#     two rows of glazed boxes; the 360-degree screen hanging round the edge of
#     the roof's opening, leaning to the pitch, with the floodlights under it
#     (game.screen.js, style 'bernabeu')
#   - the roof: fixed over all the stands, white steel lattice underneath,
#     floodlights along the edge of the opening; twelve big trusses across the
#     opening carry the retractable cover, 55 m over the pitch; open, its
#     panels stand folded at both ends of the opening
#   - outside: the skin of silver steel ribbons wrapped round the whole
#     building and carried over the roof in rings round the opening, lit at
#     night; the cover white; the streets round
#     it (Castellana to the west), trees
# No sponsor names; the crest is not drawn, the screens show the score.
#
# The helpers are those of tools/montjuic_build.py; metres, x towards the
# north (the left of the match camera), y towards the west (the camera's side).
import bpy, bmesh, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'bernabeu')
os.makedirs(TEX_DIR, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data
sc = bpy.context.scene
for name in ('01_Pitch', '02_Bowl', '03_Seats', '04_Roof', '05_Outside', '06_RoofOpen', '07_RoofClosed'):
    c = D.collections.new(name)
    sc.collection.children.link(c)
UPV = Vector((0, 0, 1))

# ---------------------------------------------------------------- helpers (as in the ArenA script)
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
    # a picture from tools/montjuic as linear floats, row 0 at the top
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


def tube(bm, p0, p1, r, mat, seg=8, trim=0.0, step=2.5):
    # a round bar from p0 to p1; `trim` pulls both ends in (members meeting a
    # thicker one stop at its skin, so none of their points lie inside it,
    # where the baked light would be black); a ring of points every `step`
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


def cone(bm, c, r0, r1, z0, z1, mat, seg=12, caps=True):
    res = bmesh.ops.create_cone(bm, cap_ends=caps, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=z1 - z0)
    bmesh.ops.translate(bm, vec=Vector((c[0], c[1], (z0 + z1) / 2)), verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat


def wall(bm, a, b, z0, z1, want, mat, step=3.0, u0=0.0, u_len=None, v=(0, 1)):
    # a vertical strip from a to b (2D), in pieces of `step` so the baked light follows it
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    L = (b - a).length
    n = max(1, math.ceil(L / step))
    for k in range(n):
        p, q = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        uvs = None
        if u_len:
            ua, ub = (u0 + L * k / n) / u_len, (u0 + L * (k + 1) / n) / u_len
            uvs = [(ua, v[0]), (ub, v[0]), (ub, v[1]), (ua, v[1])]
        face(bm, [(p.x, p.y, z0), (q.x, q.y, z0), (q.x, q.y, z1), (p.x, p.y, z1)], want, mat, uvs)
    return L


def grid_quad(bm, a, b, z0, z1, want, mat, uvf=None, step=2.5):
    # a vertical rectangle from a to b (2D) in a grid of points `step` apart
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    nu = max(1, math.ceil((b - a).length / step))
    nv = max(1, math.ceil((z1 - z0) / step))
    for i in range(nu):
        for j in range(nv):
            pts = []
            for (di, dj) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                p = a.lerp(b, (i + di) / nu)
                pts.append((p.x, p.y, z0 + (z1 - z0) * (j + dj) / nv))
            face(bm, pts, want, mat, [uvf(*p) for p in pts] if uvf else None)


# the lettering: Barlow Condensed ExtraBold
LETTER_FONT = D.fonts.load(os.path.join(HERE, 'fonts', 'BarlowCondensed-ExtraBold.ttf'))


def wall_text(name, body, loc, outward, size, coll, mat, extrude=0.0):
    # a line of lettering standing up, facing away from `outward` (towards the pitch)
    cu = D.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.extrude = extrude
    cu.font = LETTER_FONT
    cu.resolution_u = 2 if size < 2 else 4
    cu.offset = size * 0.022
    cu.materials.append(mat)
    t = D.objects.new(name, cu)
    t.location = loc
    t.rotation_euler = (math.pi / 2, 0, outward - math.pi / 2)
    D.collections[coll].objects.link(t)
    return t



# ---------------------------------------------------------------- dimensions (metres)
PW, PL = 105.0, 68.0
LINE = 0.12
CX, CY = 40.0, 22.0              # the core of the bowl's rounded rectangle; the stands lie round it at r
R_WALL, WALL_Z = 16.0, 1.2       # the wall in front of the first ring: 3.5 m behind the goal line, 5 m from the touchline
T1 = dict(r=16.3, z=1.4, rows=24, depth=0.80, rise=0.45)            # to r 35.5, z 11.75
T2 = dict(r=36.5, z=13.9, rows=14, depth=0.82, rise=0.60)           # to r 48.0, z 21.7
BOX_R0, BOX_R1, BOX_Z0, BOX_Z1 = 48.0, 50.0, 22.2, 26.4               # the band of glazed boxes
T3 = dict(r=50.3, z=26.8, rows=9, depth=0.82, rise=0.66)            # to r 57.7, z 32.1
T4 = dict(r=58.3, z=35.6, rows=13, depth=0.85, rise=0.74)           # to r 69.4, z 44.5
def back_r(t): return t['r'] + t['depth'] * t['rows']
def top_z(t): return t['z'] + t['rise'] * (t['rows'] - 1)
SCR_R, SCR_DR, SCR_Z0, SCR_Z1 = 18.0, 2.4, 44.0, 52.8              # the 360 screen: round the edge of the roof's opening, leaning out at the top
OX, OY, OR = 56.0, 38.5, 9.0     # the roof's opening: half its length and width, the corners' radius
ROOF_TOP0, ROOF_TOP1 = 52.5, 56.5     # the top of the fixed roof at the facade and at the opening
ROOF_TH0, ROOF_TH1 = 4.0, 2.0         # its thickness there
COVER_Z = 57.6                   # the retractable cover, 55 m and more over the pitch, on the trusses
FACADE_TOP = 52.5
GAIN = 2.0
SEAT_W, AISLE_W = 0.5, 1.1
N_LONG, N_SHORT, N_CORNER = 14, 8, 6      # pieces of each long side, each end, each corner
NP = 2 * (N_LONG + N_SHORT + 2 * N_CORNER)

# the footprint (OSM way 1507411898 in these axes), counter-clockwise from the north-west, all smooth
OUTLINE = [(66.9, 107.1), (42.5, 108.4), (19.3, 108.2), (-11.6, 107.6), (-42.8, 107.0), (-65.5, 106.4), (-80.8, 104.4),
           (-94.8, 96.0), (-102.6, 84.5), (-106.6, 68.0), (-108.0, 49.7), (-108.7, 19.7), (-109.2, -16.9), (-108.9, -73.1),
           (-104.5, -90.5), (-93.3, -101.4), (-77.9, -105.7), (-57.7, -108.5), (-43.1, -111.9), (-28.0, -117.5), (-15.3, -128.3),
           (-2.0, -132.4), (10.8, -134.1), (24.0, -130.5), (38.6, -124.0), (56.2, -115.4), (73.6, -107.1), (90.3, -98.9),
           (103.0, -91.6), (107.6, -82.0), (109.0, -66.0), (109.8, -18.6), (109.8, 4.7), (109.0, 31.6), (107.8, 52.5),
           (105.4, 71.5), (99.0, 86.9), (89.5, 97.5), (76.0, 105.0)]


# ---------------------------------------------------------------- the bowl's plan: a rounded rectangle
def bowl_pts(r):
    # NP points counter-clockwise from the north end of the west side; point i
    # lies on the same line out from the pitch at every r
    pts = []
    for k in range(N_LONG):                               # west side, north to south
        pts.append((CX - 2 * CX * k / N_LONG, CY + r))
    for k in range(N_CORNER):                             # south-west corner
        a = math.pi / 2 + math.pi / 2 * k / N_CORNER
        pts.append((-CX + r * math.cos(a), CY + r * math.sin(a)))
    for k in range(N_SHORT):                              # south end
        pts.append((-CX - r, CY - 2 * CY * k / N_SHORT))
    for k in range(N_CORNER):
        a = math.pi + math.pi / 2 * k / N_CORNER
        pts.append((-CX + r * math.cos(a), -CY + r * math.sin(a)))
    for k in range(N_LONG):                               # east side, south to north
        pts.append((-CX + 2 * CX * k / N_LONG, -CY - r))
    for k in range(N_CORNER):
        a = 1.5 * math.pi + math.pi / 2 * k / N_CORNER
        pts.append((CX + r * math.cos(a), -CY + r * math.sin(a)))
    for k in range(N_SHORT):                              # north end
        pts.append((CX + r, -CY + 2 * CY * k / N_SHORT))
    for k in range(N_CORNER):
        a = math.pi / 2 * k / N_CORNER
        pts.append((CX + r * math.cos(a), CY + r * math.sin(a)))
    return [Vector((x, y, 0)) for x, y in pts]


SEGS = [('W', N_LONG), ('c', N_CORNER), ('S', N_SHORT), ('c', N_CORNER), ('E', N_LONG), ('c', N_CORNER), ('N', N_SHORT), ('c', N_CORNER)]


def piece(i):
    i %= NP
    for s, n in SEGS:
        if i < n:
            return s, i
        i -= n


def is_aisle(i):
    s, k = piece(i)
    return k % 3 == 0 if s == 'c' else k % 2 == 0


def is_mid(i):
    s, k = piece(i)
    return False if s == 'c' else k % 2 == 1


def cumlen(p):
    c = [0.0]
    for i in range(NP):
        c.append(c[-1] + (p[(i + 1) % NP] - p[i]).length)
    return c


def outward(i, p):
    t = p[(i + 1) % NP] - p[i]
    return Vector((t.y, -t.x, 0)).normalized()


def bring(bm, r0, z0, r1, z1, mat, keep=None, want=None, step=3.0, u_len=None, v=(0, 1)):
    p0, p1 = bowl_pts(r0), bowl_pts(r1)
    c0 = cumlen(p0)
    for i in range(NP):
        j = (i + 1) % NP
        A0, A1, B0, B1 = p0[i], p0[j], p1[i], p1[j]
        out = outward(i, p0 if (A1 - A0).length > 1e-6 else p1)
        w = {'up': UPV, 'down': -UPV, 'out': out, 'in': -out}.get(want)
        if w is None:
            w = UPV if abs(z1 - z0) < 1e-6 else -out
        n = max(1, math.ceil(max((A1 - A0).length, (B1 - B0).length) / step))
        for k in range(n):
            a0, a1 = A0.lerp(A1, k / n), A0.lerp(A1, (k + 1) / n)
            b0, b1 = B0.lerp(B1, k / n), B0.lerp(B1, (k + 1) / n)
            if keep is not None and not keep(i, (a0 + a1 + b0 + b1) / 4):
                continue
            uvs = None
            if u_len:
                ua = (c0[i] + (c0[i + 1] - c0[i]) * k / n) / u_len
                ub = (c0[i] + (c0[i + 1] - c0[i]) * (k + 1) / n) / u_len
                uvs = [(ua, v[0]), (ub, v[0]), (ub, v[1]), (ua, v[1])]
            face(bm, [(a0.x, a0.y, z0), (a1.x, a1.y, z0), (b1.x, b1.y, z1), (b0.x, b0.y, z1)], w, mat, uvs)


# ---------------------------------------------------------------- the footprint, smoothed
def outline_path(step=3.0):
    pts = [Vector((x, y, 0)) for x, y in OUTLINE]
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        m = max(1, math.ceil((p2 - p1).length / step))
        for k in range(m):
            t = k / m
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


FOOT = outline_path()


def inside_foot(x, y):
    c = False
    n = len(FOOT)
    for i in range(n):
        a, b = FOOT[i], FOOT[(i + 1) % n]
        if (a.y > y) != (b.y > y):
            if x < a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y):
                c = not c
    return c


def opening_sdf(x, y):
    qx, qy = abs(x) - (OX - OR), abs(y) - (OY - OR)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - OR


def to_opening(p):
    # the point of the opening's edge on the line from the centre through p
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m = (lo + hi) / 2
        if opening_sdf(p.x * m, p.y * m) < 0:
            lo = m
        else:
            hi = m
    return Vector((p.x * lo, p.y * lo, 0))


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1947)


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
    t[-2:] *= 1.15
    return t


def skin_tex():
    # the steel skin: silver ribbons a metre apart with dark gaps between them,
    # each ribbon catching a little more light on its lower edge (u: 8 m, v: 52.5 m)
    w, h = 64, 1024
    yy = np.arange(h) / h * 52.5
    f = (yy % 1.05) / 1.05
    band = np.where(f < 0.16, 0.10, 0.55 + 0.25 * np.clip((f - 0.16) / 0.84, 0, 1) ** 0.6)
    t = np.ones((h, w, 3), 'f') * band[:, None, None] * np.array((0.78, 0.80, 0.84), 'f')
    t *= (1 + 0.05 * vnoise(h, w, 64, 16))[..., None]
    t[:, (np.arange(w) % 32) == 0] *= 0.8                                       # the joints between the panels
    return t[::-1]


def lattice_tex():
    # under the roof: white steel trusses close together against the dark deck
    w = h = 128
    t = np.ones((h, w, 3), 'f') * np.array((0.10, 0.11, 0.12), 'f')
    yy, xx = np.mgrid[0:h, 0:w]
    steel = np.array((0.82, 0.83, 0.84), 'f')
    t[(xx % 32) < 3] = steel
    t[(yy % 32) < 2] = steel * 0.9
    t[((xx + yy) % 32) < 2] = steel * 0.8
    t[((xx - yy) % 32) < 2] = steel * 0.8
    return t


def boxes_tex():
    # the glazed boxes between the second and third rings: lit rooms behind glass
    pw, h, n = 64, 96, 16
    t = np.zeros((h, pw * n, 3), 'f')
    v = np.linspace(0, 1, h)[:, None]
    for k in range(n):
        warm = np.array((1.0, 0.86, 0.66), 'f') * rng.uniform(0.35, 0.7)
        pane = warm * (0.55 + 0.45 * v)[..., None] * np.ones((1, pw, 1), 'f')
        for _ in range(rng.integers(1, 4)):
            cx, wd = rng.integers(8, pw - 8), rng.integers(4, 9)
            m = (v[:, 0] > 0.15) & (v[:, 0] < 0.55)
            pane[m, max(0, cx - wd // 2):cx + wd // 2] *= 0.35
        pane[:, :2] = 0.05; pane[:3] = 0.05; pane[-3:] = 0.05
        t[:, k * pw:(k + 1) * pw] = pane
    return t


def cover_tex():
    # the retractable cover: light panels with darker seams across
    w, h = 64, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.86, 0.87, 0.88), 'f')
    t[(np.arange(h) % 32) < 2] *= 0.6
    t[:, (np.arange(w) % 64) < 2] *= 0.7
    return t


def paving_tex():
    w = h = 128
    t = np.ones((h, w, 3), 'f') * np.array((0.30, 0.30, 0.31), 'f')
    t *= (1 + 0.04 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    t[(np.arange(h) % 32) == 0] *= 0.8
    t[:, (np.arange(w) % 32) == 0] *= 0.8
    return t


def foliage_tex():
    w = h = 128
    a = 0.6 * vnoise(h, w, 8, 8) + 0.4 * rng.normal(0, 1, (h, w)).astype('f')
    return np.clip(np.ones((h, w, 3), 'f') * np.array((0.03, 0.06, 0.025), 'f') * (1 + 0.45 * a)[..., None], 0, 1)


NAVY = [(0.020, 0.045, 0.140), (0.017, 0.040, 0.125), (0.024, 0.052, 0.155)]
seat_cols = [image_material('M_Seat%d' % i, painted('rm_seat%d' % i, seat_tile(c)), 0.6)
             for i, c in enumerate(NAVY + [(0.86, 0.87, 0.89)])]             # 3: the white seats of REAL MADRID
concrete = principled('M_Concrete', (0.30, 0.30, 0.31), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.14, 0.14, 0.15), 0.9)
concrete_light = principled('M_ConcreteLight', (0.42, 0.42, 0.43), 0.85)
portal = principled('M_Portal', (0.012, 0.012, 0.016), 0.95)
steel_white = principled('M_SteelWhite', (0.80, 0.81, 0.82), 0.5)
steel_dark = principled('M_SteelDark', (0.05, 0.05, 0.06), 0.6)
skin = image_material('M_Skin', painted('rm_skin', skin_tex()), 0.35, 0.2)
lattice = image_material('M_Lattice', painted('rm_lattice', lattice_tex()), 0.7)
roof_top_m = principled('M_RoofTop', (0.36, 0.37, 0.39), 0.4, metallic=0.2)
cover_m = image_material('M_Cover', painted('rm_cover', cover_tex()), 0.5)
boxes_m = image_material('M_Boxes', painted('rm_boxes', boxes_tex()), 0.2)
led_purple = principled('M_LEDBand', (0.80, 0.80, 0.86), 0.4, (0.80, 0.80, 0.86), 2.2)     # the white LED ribbons between the rings
led_board = principled('M_LEDBoard', (0.03, 0.06, 0.30), 0.4, (0.03, 0.06, 0.30), 2.5)
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
letters_navy = principled('M_LetteringDark', (0.03, 0.05, 0.24), 0.4, (0.03, 0.05, 0.24), 2.0)
lamp = principled('M_FloodLight', (1.0, 1.0, 0.97), 0.3, (1.0, 1.0, 0.96), 3.0)
glass_dark = principled('M_GlassDark', (0.02, 0.025, 0.03), 0.15)
paving = image_material('M_Paving', painted('rm_paving', paving_tex()), 0.9)
asphalt = principled('M_Asphalt', (0.045, 0.045, 0.05), 0.95)
road_line = principled('M_RoadLine', (0.70, 0.70, 0.68), 0.8)
lawn = principled('M_Lawn', (0.04, 0.10, 0.035), 0.95)
foliage = image_material('M_Foliage', painted('rm_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)

# ================================================================ the pitch lines, the goals
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
net_img = D.images.new('rm_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/rm_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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

# the ground inside the stands: one picture with the night light baked in
FLOOR_X, FLOOR_Y = CX + R_WALL, CY + R_WALL
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-FLOOR_X, -FLOOR_Y), (FLOOR_X, -FLOOR_Y), (FLOOR_X, FLOOR_Y), (-FLOOR_X, FLOOR_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.06, 0.22, 0.05), 0.85)])

# ================================================================ the stands
_rm = D.images.load(os.path.join(ASSETS, 'realmadrid.png'))
RM_W, RM_H = _rm.size
_px = np.empty(RM_W * RM_H * 4, 'f'); _rm.pixels.foreach_get(_px)
RM_MASK = _px.reshape(RM_H, RM_W, 4)[::-1, :, 0] > 0.5      # row 0 at the top
D.images.remove(_rm)
RM_ROW0 = 3                                                # the bottom row of the letters, in the first ring


def letters_on(x, row):
    # REAL MADRID across the first ring of the east stand, read from the west:
    # its first letter at the north (+x, the camera's left)
    col = math.floor((RM_W * SEAT_W / 2 - x) / SEAT_W)
    pr = RM_ROW0 + RM_H - 1 - row
    return 0 <= col < RM_W and 0 <= pr < RM_H and bool(RM_MASK[pr, col])


def dark_spot(tier, row, i, u, L):
    # a tunnel mouth half way along every block of the second and the top ring, in its first rows
    if tier not in ('t2', 't4') or row > 2:
        return False
    d = None
    if is_mid(i + 1):
        d = (1 - u) * L
    elif is_mid(i):
        d = u * L
    return d is not None and d < 1.3


def seat_colour(tier, side, row, p, h):
    if tier == 't1' and side == 'E' and letters_on(p.x, row):
        return 3
    return h % 3


def seat_pair(bm, pa, pb, back, m, q, q1):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
    face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UPV, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])


def build_tier(name, t, base_z, tier):
    steps, seats, aisles, dark = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    for k in range(t['rows']):
        r0, r1, z = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1), t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        p0, p1 = bowl_pts(r0), bowl_pts(r1)
        for i in range(NP):
            j = (i + 1) % NP
            side = piece(i)[0]
            A0, A1, B0, B1 = p0[i], p0[j], p1[i], p1[j]
            L = (A1 - A0).length
            back = (B0 - A0).normalized()
            n = max(1, math.ceil(max(L, (B1 - B0).length) / 3.0))
            for s in range(n):
                a0, a1 = A0.lerp(A1, s / n), A0.lerp(A1, (s + 1) / n)
                b0, b1 = B0.lerp(B1, s / n), B0.lerp(B1, (s + 1) / n)
                face(steps, [(a0.x, a0.y, z), (a1.x, a1.y, z), (b1.x, b1.y, z), (b0.x, b0.y, z)], UPV, 0)
                face(steps, [(a0.x, a0.y, z_prev), (a1.x, a1.y, z_prev), (a1.x, a1.y, z), (a0.x, a0.y, z)], -back, 1)
            cut0 = AISLE_W / 2 if is_aisle(i) else 0.0
            cut1 = AISLE_W / 2 if is_aisle(j) else 0.0
            for u0, u1 in ([(0.0, cut0 / L)] if cut0 else []) + ([(1 - cut1 / L, 1.0)] if cut1 else []):
                f0, f1 = A0.lerp(A1, u0), A0.lerp(A1, u1)
                g0, g1 = B0.lerp(B1, u0), B0.lerp(B1, u1)
                F0, F1, G0, G1 = (Vector((v.x, v.y, z)) + lift for v in (f0, f1, g0, g1))
                face(aisles, [F0, F1, G1, G0], UPV, 0)
                if k:
                    down, out_ = Vector((0, 0, -t['rise'])), -back * 0.012
                    face(aisles, [F0 + down + out_, F1 + down + out_, F1 + out_, F0 + out_], -back, 0)
            usable = L - cut0 - cut1
            nseat = max(1, round(usable / SEAT_W))
            mats = []
            for q in range(nseat):
                u = (cut0 + usable * (q + 0.5) / nseat) / L
                p = A0.lerp(A1, u).lerp(B0.lerp(B1, u), 0.5)
                if dark_spot(tier, k, i, u, L):
                    mats.append('dark')
                    continue
                h = (k * 73856093) ^ (i * 19349663) ^ ((q // 3) * 83492791)
                mats.append(seat_colour(tier, side, k, p, h))
            q = 0
            while q < nseat:
                if mats[q] != 'dark':
                    q += 1
                    continue
                q1 = q
                while q1 < nseat and mats[q1] == 'dark':
                    q1 += 1
                u0, u1 = (cut0 + usable * q / nseat) / L, (cut0 + usable * q1 / nseat) / L
                f0, f1 = A0.lerp(A1, u0), A0.lerp(A1, u1)
                g0, g1 = B0.lerp(B1, u0), B0.lerp(B1, u1)
                F0, F1, G0, G1 = (Vector((v.x, v.y, z)) + lift for v in (f0, f1, g0, g1))
                face(dark, [F0, F1, G1, G0], UPV, 0)
                down, out_ = Vector((0, 0, -t['rise'])), -back * 0.012
                face(dark, [F0 + down + out_, F1 + down + out_, F1 + out_, F0 + out_], -back, 0)
                if k == 2:
                    for g in (G0, G1):
                        tube(dark, g, g + Vector((0, 0, 1.0)), 0.03, 1, 4)
                    tube(dark, G0 + Vector((0, 0, 1.0)), G1 + Vector((0, 0, 1.0)), 0.03, 1, 4)
                q = q1
            q = 0
            while q < nseat:
                m = mats[q]
                if m == 'dark':
                    q += 1
                    continue
                q1 = q + 2 if q + 1 < nseat and mats[q + 1] == m else q + 1
                u = [(cut0 + usable * qq / nseat) / L for qq in (q, q1)]
                pa = [A0.lerp(A1, uu) + Vector((0, 0, z)) for uu in u]
                pb = [B0.lerp(B1, uu) + Vector((0, 0, z)) for uu in u]
                seat_pair(seats, pa, pb, back, m, q, q1)
                q = q1
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Aisles_' + name, aisles, '02_Bowl', [concrete_light])
    new_obj('Portals_' + name, dark, '02_Bowl', [portal, steel_white])


t0 = time.time()
build_tier('T1', T1, WALL_Z, 't1')
build_tier('T2', T2, top_z(T1) + 0.4, 't2')
build_tier('T3', T3, BOX_Z1, 't3')
build_tier('T4', T4, top_z(T3) + 0.4, 't4')
print('STANDS %.0fs' % (time.time() - t0))

# the fronts between the rings: the wall round the pitch, the LED ribbon on the
# second ring, the glazed boxes, the walkways and the back wall into the roof
bm = bmesh.new()
bring(bm, R_WALL, 0.0, R_WALL, WALL_Z, 0)
bring(bm, R_WALL, WALL_Z, T1['r'], WALL_Z, 0, want='up')
bring(bm, R_WALL - 0.05, WALL_Z + 0.95, R_WALL - 0.05, WALL_Z + 1.02, 1, step=6.0)
B1 = back_r(T1)
bring(bm, B1, top_z(T1), B1, top_z(T1) + 0.4, 0)
bring(bm, B1, top_z(T1) + 0.4, T2['r'] - 0.05, top_z(T1) + 0.4, 0, want='up')
bring(bm, T2['r'] - 0.05, top_z(T1) + 0.4, T2['r'] - 0.05, T2['z'] - 0.3, 2, want='in')          # the LED ribbon
bring(bm, T2['r'] - 0.05, T2['z'] - 0.3, T2['r'], T2['z'] - 0.3, 0, want='up')
B2 = back_r(T2)
bring(bm, B2, top_z(T2), B2, BOX_Z0, 0)
bring(bm, BOX_R0, BOX_Z0, BOX_R0, BOX_Z1 - 0.5, 3, want='in', u_len=32.0)                          # the boxes' glass
bring(bm, BOX_R0, BOX_Z1 - 0.5, BOX_R0, BOX_Z1, 0, want='in')
bring(bm, BOX_R0 - 0.6, BOX_Z1, T3['r'], BOX_Z1, 0, want='up')
bring(bm, BOX_R0 - 0.6, BOX_Z1 - 0.1, BOX_R0 - 0.6, BOX_Z1, 0, want='in')
B3 = back_r(T3)
bring(bm, B3, top_z(T3), B3, top_z(T3) + 0.4, 0)
bring(bm, B3, top_z(T3) + 0.4, T4['r'] - 0.4, top_z(T3) + 0.4, 0, want='up')
bring(bm, T4['r'] - 0.4, top_z(T3) + 0.4, T4['r'] - 0.4, top_z(T3) + 1.0, 2, want='in')                 # the second, thin ribbon
bring(bm, T4['r'] - 0.4, top_z(T3) + 1.0, T4['r'] - 0.4, T4['z'] - 0.3, 3, want='in', u_len=32.0)      # the second row of boxes
bring(bm, T4['r'] - 0.4, T4['z'] - 0.3, T4['r'], T4['z'] - 0.3, 0, want='up')
B4 = back_r(T4)
bring(bm, B4, top_z(T4), B4, ROOF_TOP0 - ROOF_TH0 + 1.0, 1)
new_obj('Fronts', bm, '02_Bowl', [concrete, steel_white, led_purple, boxes_m])
for side, (loc, out) in {'E': ((0, -(CY + T2['r'] - 0.09), 0), -math.pi / 2), 'N': ((CX + T2['r'] - 0.09, 0, 0), 0.0),
                         'S': ((-(CX + T2['r'] - 0.09), 0, 0), math.pi), 'W': ((0, CY + T2['r'] - 0.09, 0), math.pi / 2)}.items():
    for k, s_ in enumerate((-30.0, -10.0, 10.0, 30.0) if side in 'EW' else (-12.0, 12.0)):
        p = Vector(loc) + (Vector((s_, 0, 0)) if side in 'EW' else Vector((0, s_, 0)))
        word = ['BIENVENIDOS', 'WELCOME', 'WILLKOMMEN', 'BEM-VINDOS', 'HOŞ GELDIN'][(k + len(side) * 3 + 'ENSW'.index(side)) % 5]
        wall_text('Ribbon_%s%d' % (side, k), word, (p.x, p.y, top_z(T1) + 0.62), out, 0.72, '02_Bowl', letters_navy)

# the LED boards round the pitch
BOARD_Y, BOARD_X = PL / 2 + 3.6, PW / 2 + 2.8
BOARD_LINES = [
    (Vector((50.0, -BOARD_Y, 0)), Vector((-50.0, -BOARD_Y, 0)), -math.pi / 2),
    (Vector((-50.0, BOARD_Y, 0)), Vector((-8.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((8.0, BOARD_Y, 0)), Vector((50.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((-BOARD_X, -24.0, 0)), Vector((-BOARD_X, 24.0, 0)), math.pi),
    (Vector((BOARD_X, 24.0, 0)), Vector((BOARD_X, -24.0, 0)), 0.0),
]
bm = bmesh.new()
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    n = max(1, math.ceil((b - a).length / 4.0))
    for k in range(n):
        p0, p1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        q0, q1 = p0 + out * 0.25, p1 + out * 0.25
        face(bm, [(p0.x, p0.y, 0.1), (p1.x, p1.y, 0.1), (p1.x, p1.y, 1.0), (p0.x, p0.y, 1.0)], -out, 0)
        face(bm, [(q0.x, q0.y, 0.0), (q1.x, q1.y, 0.0), (q1.x, q1.y, 1.0), (q0.x, q0.y, 1.0)], out, 1)
        face(bm, [(p0.x, p0.y, 1.0), (p1.x, p1.y, 1.0), (q1.x, q1.y, 1.0), (q0.x, q0.y, 1.0)], UPV, 1)
new_obj('LED_Boards', bm, '02_Bowl', [led_board, steel_dark])
BOARD_TEXT = ['REAL MADRID', 'HALA MADRID', 'SANTIAGO BERNABÉU']
ti = 0
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    n = max(1, round((b - a).length / 14.0))
    for k in range(n):
        p = a.lerp(b, (k + 0.5) / n) - out * 0.05
        wall_text('Boards_T%d' % ti, BOARD_TEXT[ti % 3], (p.x, p.y, 0.3), ang, 0.5, '02_Bowl', letters_white)
        ti += 1

# the dugouts on the west side, either side of the halfway line
bm = bmesh.new()
yb = CY + R_WALL - 0.4
for x0, x1 in ((-14.0, -4.0), (4.0, 14.0)):
    face(bm, [(x0, yb - 2.2, 2.0), (x1, yb - 2.2, 2.0), (x1, yb, 2.2), (x0, yb, 2.2)], UPV, 1)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.2), (x0, yb, 2.2)], Vector((0, -1, 0)), 0)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.2, 0.0), (x, yb, 0.0), (x, yb, 2.2), (x, yb - 2.2, 2.0)], Vector((1 if x == x0 else -1, 0, 0)), 1)
new_obj('Dugouts', bm, '02_Bowl', [concrete_dark, glass_dark])

# ================================================================ the 360 screen, round under the roof
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.14), 2.0)
fb = bmesh.new()
bring(fb, SCR_R, SCR_Z0, SCR_R + SCR_DR, SCR_Z1, 0, want='in', step=4.0, u_len=-64.0)      # the picture repeats every 64 m, reading from the pitch
screen_face = new_obj('ScreenFace_0', fb, '02_Bowl', [live])
bm = bmesh.new()
bring(bm, SCR_R + 0.7, SCR_Z0 - 0.5, SCR_R + SCR_DR + 0.7, SCR_Z1 + 0.5, 0, want='out', step=6.0)         # the back of the screen
bring(bm, SCR_R - 0.1, SCR_Z0 - 0.5, SCR_R + 0.7, SCR_Z0 - 0.5, 0, want='down', step=6.0)
bring(bm, SCR_R + SCR_DR - 0.1, SCR_Z1 + 0.5, SCR_R + SCR_DR + 0.7, SCR_Z1 + 0.5, 0, want='up', step=6.0)
bring(bm, SCR_R - 0.1, SCR_Z0 - 0.5, SCR_R - 0.02, SCR_Z0, 0, want='in', step=6.0)
bring(bm, SCR_R + SCR_DR - 0.02, SCR_Z1, SCR_R + SCR_DR - 0.1, SCR_Z1 + 0.5, 0, want='in', step=6.0)
bring(bm, SCR_R + 0.4, SCR_Z0 - 1.9, SCR_R + 2.2, SCR_Z0 - 1.9, 1, want='down', step=6.0)                   # the gantry of floodlights under it
for p in bowl_pts(SCR_R + SCR_DR + 0.4)[::2]:                                 # the hangers up into the roof's trusses
    tube(bm, Vector((p.x, p.y, SCR_Z1 + 0.5)), Vector((p.x, p.y, 56.0)), 0.14, 1, 5)
for p in bowl_pts(SCR_R + 1.3)[::1]:
    box(bm, (p.x, p.y), (1, 0), 0.4, (0, 1), 0.4, SCR_Z0 - 2.6, SCR_Z0 - 1.9, 2)
new_obj('Screen_Frame', bm, '02_Bowl', [portal, steel_white, lamp])

# ================================================================ the roof
OUT_PTS = FOOT
NR = len(OUT_PTS)
INNER = [to_opening(p) for p in OUT_PTS]
T_STEPS = [0.0, 0.05, 0.12, 0.22, 0.34, 0.46, 0.58, 0.70, 0.82, 0.92, 1.0]


def rz_top(t): return ROOF_TOP0 + (ROOF_TOP1 - ROOF_TOP0) * math.sin(min(1.0, t * 1.25) * math.pi / 2) ** 0.8
def rz_under(t): return rz_top(t) - (ROOF_TH0 + (ROOF_TH1 - ROOF_TH0) * t)


def rp(i, t, z):
    p = OUT_PTS[i % NR].lerp(INNER[i % NR], t)
    return (p.x, p.y, z)


bm = bmesh.new()
for i in range(NR):
    j = i + 1
    for t0_, t1_ in zip(T_STEPS, T_STEPS[1:]):
        face(bm, [rp(i, t0_, rz_top(t0_)), rp(j, t0_, rz_top(t0_)), rp(j, t1_, rz_top(t1_)), rp(i, t1_, rz_top(t1_))], UPV, 4,
             [(i * 3.0 / 8.0, t0_ * 0.95), (j * 3.0 / 8.0, t0_ * 0.95), (j * 3.0 / 8.0, t1_ * 0.95), (i * 3.0 / 8.0, t1_ * 0.95)])     # ribbons parallel to the edge
        uvs = [(rp(k, tt, 0)[0] / 16.0, rp(k, tt, 0)[1] / 16.0) for k, tt in ((i, t0_), (j, t0_), (j, t1_), (i, t1_))]
        face(bm, [rp(i, t0_, rz_under(t0_)), rp(j, t0_, rz_under(t0_)), rp(j, t1_, rz_under(t1_)), rp(i, t1_, rz_under(t1_))], -UPV, 0, uvs)
    # the edge of the opening, with the floodlights under it
    a, b = INNER[i % NR], INNER[j % NR]
    face(bm, [(a.x, a.y, rz_under(1)), (b.x, b.y, rz_under(1)), (b.x, b.y, rz_top(1)), (a.x, a.y, rz_top(1))], Vector((-a.x, -a.y, 0)), 2)
for i in range(0, NR, 2):
    p = INNER[i]
    d = Vector((p.x, p.y, 0)).normalized()
    c = p + d * 1.6
    box(bm, (c.x, c.y), (d.y, -d.x), 0.55, (d.x, d.y), 0.35, rz_under(1) - 0.8, rz_under(1), 3)
new_obj('Roof', bm, '04_Roof', [lattice, roof_top_m, steel_white, lamp, skin])

# the twelve trusses across the opening that carry the retractable cover
bm = bmesh.new()
TR_X = np.linspace(-OX + 5.0, OX - 5.0, 12)
TR_Y = OY + 10.0
for x in TR_X:
    zb, zt = rz_top(1) - 1.2, COVER_Z - 0.4
    for z in (zb, zt):
        tube(bm, Vector((x, -TR_Y, z)), Vector((x, TR_Y, z)), 0.38, 0, 6)
    ys = np.linspace(-TR_Y, TR_Y, 21)
    for k in range(len(ys) - 1):
        tube(bm, Vector((x, ys[k], zb)), Vector((x, ys[k + 1], zt)), 0.16, 0, 4, trim=0.5)
        tube(bm, Vector((x, ys[k], zb)), Vector((x, ys[k], zt)), 0.14, 0, 4, trim=0.5)
for y in (-OY + 2.0, 0.0, OY - 2.0):                                         # the rails the cover runs on
    tube(bm, Vector((-OX - 2.0, y, COVER_Z - 0.1)), Vector((OX + 2.0, y, COVER_Z - 0.1)), 0.2, 0, 4)
new_obj('Roof_Trusses', bm, '04_Roof', [steel_white])


def cover_panel(bm, x0, x1, z, mat_top=0, mat_under=1):
    y0, y1 = -OY - 1.0, OY + 1.0
    face(bm, [(x0, y0, z + 0.3), (x1, y0, z + 0.3), (x1, y1, z + 0.3), (x0, y1, z + 0.3)], UPV, mat_top,
         [(x0 / 8.0, y0 / 8.0), (x1 / 8.0, y0 / 8.0), (x1 / 8.0, y1 / 8.0), (x0 / 8.0, y1 / 8.0)])
    face(bm, [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)], -UPV, mat_under,
         [(x0 / 16.0, y0 / 16.0), (x1 / 16.0, y0 / 16.0), (x1 / 16.0, y1 / 16.0), (x0 / 16.0, y1 / 16.0)])
    for x in (x0, x1):
        face(bm, [(x, y0, z), (x, y1, z), (x, y1, z + 0.3), (x, y0, z + 0.3)], Vector((1 if x == x1 else -1, 0, 0)), mat_top)


# closed: the panels side by side over the whole opening; open: folded up at both ends
PANEL_W = 2 * OX / 11
bm = bmesh.new()
for k in range(11):
    x0 = -OX + PANEL_W * k
    cover_panel(bm, x0 - 0.15, x0 + PANEL_W + 0.15, COVER_Z + (0.35 if k % 2 else 0.0))
roof_closed = new_obj('StadiumRoofClosed', bm, '07_RoofClosed', [cover_m, cover_m])
bm = bmesh.new()
for s in (-1, 1):
    for k in range(6 if s > 0 else 5):
        xc = s * (OX - 2.2 - k * 0.9)
        cover_panel(bm, xc - PANEL_W / 2, xc + PANEL_W / 2, COVER_Z + k * 0.35)
roof_open = new_obj('StadiumRoofOpen', bm, '06_RoofOpen', [cover_m, cover_m])

# ================================================================ the steel skin round the building
bm = bmesh.new()
cum = 0.0
nF = len(FOOT)
for i in range(nF):
    a, b = FOOT[i], FOOT[(i + 1) % nF]
    L = (b - a).length
    if L < 1e-6:
        continue
    out = Vector(((b - a).y, -(b - a).x, 0)).normalized()
    wall(bm, a, b, 0.0, FACADE_TOP - 1.5, out, 0, 3.0, cum, 8.0, (0.0, (FACADE_TOP - 1.5) / 52.5))
    # the skin rounds over onto the roof
    for k in range(3):
        z0, z1 = FACADE_TOP - 1.5 + k * 0.6, FACADE_TOP - 1.5 + (k + 1) * 0.6
        i0, i1 = 0.25 * k * k, 0.25 * (k + 1) * (k + 1)
        A0, B0 = a - out * i0, b - out * i0
        A1, B1 = a - out * i1, b - out * i1
        face(bm, [(A0.x, A0.y, z0), (B0.x, B0.y, z0), (B1.x, B1.y, z1), (A1.x, A1.y, z1)], out + UPV * (0.5 + k * 0.6), 0,
             [(cum / 8.0, z0 / 52.5), ((cum + L) / 8.0, z0 / 52.5), ((cum + L) / 8.0, z1 / 52.5), (cum / 8.0, z1 / 52.5)])
    cum += L
new_obj('Skin', bm, '05_Outside', [skin])

# ================================================================ outside: the streets, trees
bm = bmesh.new()
STEP = 5.0
for gx in np.arange(-175.0, 180.0, STEP):
    for gy in np.arange(-195.0, 185.0, STEP):
        c4 = [(gx, gy), (gx + STEP, gy), (gx + STEP, gy + STEP), (gx, gy + STEP)]
        if all(inside_foot(x, y) for x, y in c4):
            continue
        road = (125.0 <= gy < 150.0) or (-145.0 <= gx < -125.0) or (125.0 <= gx < 140.0) or (-170.0 <= gy < -155.0)
        mat = 1 if road else 0
        face(bm, [(x, y, 0.0) for x, y in c4], UPV, mat, [(x / 8.0, y / 8.0) for x, y in c4])
for y in (130.0, 137.5, 145.0):                                               # the lanes of the Castellana
    for x in np.arange(-170.0, 175.0, 9.0):
        face(bm, [(x, y - 0.08, 0.02), (x + 4.5, y - 0.08, 0.02), (x + 4.5, y + 0.08, 0.02), (x, y + 0.08, 0.02)], UPV, 2)
new_obj('Ground', bm, '05_Outside', [paving, asphalt, road_line])
bm = bmesh.new()
trng = random.Random(1947)
spots = [(x, 121.0) for x in np.arange(-165.0, 170.0, 10.0)] + [(x, 154.0) for x in np.arange(-165.0, 170.0, 10.0)]
spots += [(-150.0, y) for y in np.arange(-120.0, 120.0, 12.0)] + [(145.0, y) for y in np.arange(-120.0, 120.0, 12.0)]
for x, y in spots:
    if inside_foot(x, y):
        continue
    h = trng.uniform(8.0, 12.0)
    tube(bm, Vector((x, y, 0)), Vector((x, y, h * 0.6)), 0.25, 0, 5)
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    rx = trng.uniform(2.8, 4.2)
    bmesh.ops.scale(bm, vec=Vector((rx, rx, h * 0.3)), verts=res['verts'])
    bmesh.ops.translate(bm, vec=Vector((x, y, h * 0.72)), verts=res['verts'])
    uvl = bm.loops.layers.uv.verify()
    for f_ in {f_ for v in res['verts'] for f_ in v.link_faces}:
        f_.material_index = 1
        for l in f_.loops:
            l[uvl].uv = (l.vert.co.x / 5.0, (l.vert.co.y + l.vert.co.z) / 5.0)
new_obj('Trees', bm, '05_Outside', [trunk, foliage])

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('SAVED', OUT_BLEND)

# ================================================================ night: floodlights from the roof
def light(coll, kind, loc, energy, color, target=None, size=60, blend=0.35, radius=0.3):
    ld = D.lights.new('L', kind)
    ld.energy = energy; ld.color = color
    if kind == 'SPOT':
        ld.spot_size = math.radians(size); ld.spot_blend = blend; ld.shadow_soft_size = radius
    o = D.objects.new('Night_' + kind, ld)
    coll.objects.link(o)
    o.location = loc
    if target is not None:
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o


w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)
coll = D.collections.new('10_NightLights'); sc.collection.children.link(coll)
FLOOD = (1.0, 0.99, 0.96)
EDGE_Z = SCR_Z0 - 2.8
for i in range(0, NR, 2):                                                     # all round the opening, onto the pitch
    p = INNER[i] + Vector((INNER[i].x, INNER[i].y, 0)).normalized() * 3.0
    light(coll, 'SPOT', (p.x, p.y, EDGE_Z), 6500, FLOOD, target=(p.x * 0.25, p.y * 0.25, 0), size=70)
for i in range(1, NR, 2):                                                     # and out onto the stands
    p = INNER[i] + Vector((INNER[i].x, INNER[i].y, 0)).normalized() * 3.0
    light(coll, 'SPOT', (p.x, p.y, EDGE_Z), 9000, FLOOD, target=(p.x * 1.7, p.y * 1.7, 18), size=85, blend=0.6)
for p in bowl_pts(B4 - 4.0)[::2]:                                             # lights under the roof, over the top ring
    light(coll, 'POINT', (p.x, p.y, rz_under(0.05) - 1.5), 4500, (1.0, 0.95, 0.88))
for p in bowl_pts(B2 + 0.5)[::3]:                                             # and over the second ring, from under the boxes
    light(coll, 'POINT', (p.x, p.y, BOX_Z0 - 0.6), 1400, (1.0, 0.93, 0.84))
light(coll, 'SUN', (0, 0, 120), 1.6, (0.80, 0.86, 1.0), target=(30, 20, 0))
for i in range(0, nF, 5):                                                     # the skin, lit from the street
    a, b = FOOT[i], FOOT[(i + 1) % nF]
    out = Vector(((b - a).y, -(b - a).x, 0)).normalized()
    p = a + out * 9.0
    light(coll, 'SPOT', (p.x, p.y, 0.6), 65000, (0.88, 0.92, 1.0), target=(a.x, a.y, 34.0), size=75, blend=0.6)
for o in (lines, goals, screen_face):
    o.hide_render = True
for m in D.materials:                    # the LEDs, the boxes and the screen glow, the rest does not
    if m.node_tree and m.name not in ('M_LEDBand', 'M_LEDBoard', 'M_Lettering', 'M_LetteringDark', 'M_FloodLight'):
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0
sc.render.engine = 'CYCLES'
try:
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    for dv in prefs.devices:
        dv.use = True
    sc.cycles.device = 'GPU'
except Exception as ex:
    print('NO GPU', ex)
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 0
sc.cycles.transmission_bounces = 0; sc.cycles.transparent_max_bounces = 2


def look(cam_obj, target):
    cam_obj.rotation_euler = (Vector(target) - cam_obj.location).to_track_quat('-Z', 'Y').to_euler()


def preview(name, loc, target, fov, clip=0.5, res=(1280, 720), samples=32):
    cd = D.cameras.new(name)
    cd.sensor_fit = 'VERTICAL'; cd.angle_y = math.radians(fov); cd.clip_start = clip; cd.clip_end = 3000
    co = D.objects.new(name, cd)
    sc.collection.objects.link(co)
    co.location = loc
    look(co, target)
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    sc.render.image_settings.file_format = 'JPEG'
    sc.view_settings.view_transform = 'Standard'
    sc.render.filepath = os.path.join(TEX_DIR, 'preview_' + name + '.jpg')
    bpy.ops.render.render(write_still=True)


if QUICK:
    lines.hide_render = False
    roof_closed.hide_render = True
    preview('match', (0, 71.2, 21.4), (0, -16.2, 0), 36, clip=30.0)
    preview('far', (0, 40.0, 30.0), (0, -60.0, 28.0), 60, clip=8.0)
    preview('air', (-230.0, 210.0, 190.0), (0.0, 0.0, 20.0), 32)
    roof_closed.hide_render = False; roof_open.hide_render = True
    preview('air_closed', (-230.0, 210.0, 190.0), (0.0, 0.0, 20.0), 32)
    sys.exit(0)

# ================================================================ game export
bk = sc.render.bake
bk.margin = 4
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


# the pitch's light, with the roof open
roof_closed.hide_render = True
LM_W, LM_H = 560, 380
lm = D.images.new('pitch_light', LM_W, LM_H, float_buffer=True)
pm = grass.data.materials[0]
lnode = pm.node_tree.nodes.new('ShaderNodeTexImage'); lnode.image = lm
pm.node_tree.nodes.active = lnode
bk.target = 'IMAGE_TEXTURES'
sc.cycles.samples = 160
select_only([grass], grass)
bpy.ops.object.bake(type='DIFFUSE')
lmap = np.empty(LM_W * LM_H * 4, 'f'); lm.pixels.foreach_get(lmap)
lmap = lmap.reshape(LM_H, LM_W, 4)[..., :3].copy()
lmap = (lmap + np.roll(lmap, 1, 0) + np.roll(lmap, -1, 0) + np.roll(lmap, 1, 1) + np.roll(lmap, -1, 1)) / 5
pm.node_tree.nodes.remove(lnode)
inner = lmap[int(LM_H * 0.25):int(LM_H * 0.75), int(LM_W * 0.25):int(LM_W * 0.75)]
lum = float((inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1).mean())
EXPOSE = 0.8 / max(lum, 1e-6)
print('PITCH LIGHT %.3f  EXPOSE %.4f' % (lum, EXPOSE))

# the Bernabéu's grass: broad stripes across it and a fainter checker
H, W = 2776, 4096
X = np.broadcast_to(((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X, (H, W))
Y = np.broadcast_to(((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y, (H, W))
bands_x = np.tanh(np.sin(np.pi * X / (PW / 18)) * 6)
bands_y = np.tanh(np.sin(np.pi * Y / (PL / 8)) * 4)
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = 1 + 0.12 * bands_x + 0.04 * bands_y + 0.05 * vnoise(H, W, 400, 400) + 0.03 * vnoise(H, W, 48, 48) + 0.035 * fine
alb = np.array((0.060, 0.165, 0.040), 'f') * shade[..., None]
wear = sum(np.exp(-(((X - gx) / 3.0) ** 2 + (Y / 5.0) ** 2)) for gx in (-(hx - 3.0), hx - 3.0))
wear = (0.15 * wear)[..., None]
alb = alb * (1 - wear) + np.array((0.13, 0.17, 0.07), 'f') * wear
d = np.full((H, W), 1e3, 'f')
def seg_h(y, x0, x1):
    global d
    d = np.minimum(d, np.hypot(np.maximum(np.maximum(x0 - X, X - x1), 0), Y - y))
def seg_v(x, y0, y1):
    global d
    d = np.minimum(d, np.hypot(X - x, np.maximum(np.maximum(y0 - Y, Y - y1), 0)))
def arc_(cx, cy, r, a0=None, a1=None):
    global d
    dd = np.abs(np.hypot(X - cx, Y - cy) - r)
    if a0 is not None:
        ang = np.arctan2(Y - cy, X - cx)
        dd = np.where(((ang - a0) % (2 * np.pi)) <= ((a1 - a0) % (2 * np.pi)), dd, 1e3)
    d = np.minimum(d, dd)
seg_h(hy, -hx, hx); seg_h(-hy, -hx, hx); seg_v(hx, -hy, hy); seg_v(-hx, -hy, hy); seg_v(0, -hy, hy); arc_(0, 0, 9.15)
for s in (-1, 1):
    gx = s * hx
    for depth, half in ((16.5, 20.16), (5.5, 9.16)):
        x = gx - s * depth
        seg_v(x, -half, half); seg_h(half, min(gx, x), max(gx, x)); seg_h(-half, min(gx, x), max(gx, x))
    a = math.acos((16.5 - 11) / 9.15)
    mid = math.pi if s > 0 else 0
    arc_(gx - s * 11, 0, 9.15, mid - a, mid + a)
    for t in (-1, 1):
        a0 = {(1, 1): math.pi, (1, -1): math.pi / 2, (-1, 1): 1.5 * math.pi, (-1, -1): 0}[(s, t)]
        arc_(gx, t * hy, 1.0, a0, a0 + math.pi / 2)
px_m = 2 * FLOOR_X / W
cov = np.clip((LINE / 2 - d) / px_m + 0.5, 0, 1)
for cx_, cy_ in ((0, 0), (hx - 11, 0), (-hx + 11, 0)):
    cov = np.maximum(cov, np.clip((0.2 - np.hypot(X - cx_, Y - cy_)) / px_m + 0.5, 0, 1))
cov = cov[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
out_px = np.clip(alb * upsample(lmap, H, W) * (EXPOSE * GAIN), 0, 1)
img = D.images.new('rm_pitch', W, H)
px = np.ones((H, W, 4), 'f'); px[..., :3] = to_srgb(out_px)
img.pixels.foreach_set(px.ravel())
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
img.save_render(TEX_DIR + '/rm_pitch.jpg')
D.images.remove(img)
del alb, out_px, px, d, cov, X, Y, shade, fine, bands_x, bands_y, wear
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', D.images.load(TEX_DIR + '/rm_pitch.jpg'), 0.9))

# text -> mesh
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in D.objects if o.type == 'FONT']:
    me = D.meshes.new_from_object(o.evaluated_get(dg))
    nobj = D.objects.new(o.name + '_mesh', me)
    nobj.matrix_world = o.matrix_world.copy()
    o.users_collection[0].objects.link(nobj)
    D.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

skip = ('Pitch_Lines', 'StadiumGoals', 'ScreenFace_', 'StadiumRoof')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, screen_face, roof_open, roof_closed]:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    else:
        o.data.uv_layers[0].name = 'UVMap'
screen_face.name = 'StadiumScreens'
scc = screen_face.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
scc.data.foreach_set('color', [1.0 / GAIN, 1.0 / GAIN, 1.0 / GAIN, 1.0] * len(scc.data))
screen_face.data.color_attributes.active_color = scc
screen_face.data.color_attributes.render_color_index = screen_face.data.color_attributes.find('Col')
target = grass
select_only(export, target)
bpy.ops.object.join()
target.name = 'SantiagoBernabeu'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_LEDBand', 'M_LEDBoard', 'M_Lettering', 'M_LetteringDark', 'M_FloodLight', 'M_Boxes'}


def bake_light(obj, samples=128):
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
        print('LIGHT p10/p50/p90', [round(float(v), 3) for v in np.percentile(c[~vert_own, :3].mean(1), (10, 50, 90))])
    c[vert_own, :3] = 1.0 / GAIN
    c[:, 3] = 1
    me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT').data.foreach_set('color', c.ravel())
    me.color_attributes.remove(me.color_attributes['Light'])
    ci = me.color_attributes.find('Col')
    me.color_attributes.active_color_index = ci
    me.color_attributes.render_color_index = ci


roof_closed.hide_render = True
bake_light(target)
bake_light(roof_open, 64)
roof_open.hide_render = True; roof_closed.hide_render = False
bake_light(roof_closed, 64)
gc = goals.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
gc.data.foreach_set('color', [0.45, 0.45, 0.45, 1.0] * len(gc.data))
goals.data.color_attributes.active_color = gc
goals.data.color_attributes.render_color_index = goals.data.color_attributes.find('Col')
for m in D.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0

objs = [target, goals, screen_face, roof_open, roof_closed]
bb = [o.matrix_world @ Vector(cc) for o in objs for cc in o.bound_box]
mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
s = 264 / max(mx[0] - mn[0], mx[1] - mn[1])
cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
print('BOUNDS', mn, mx)
print('PITCH x=%.2f z=%.2f w=%.2f l=%.2f y=%.2f' % (-cx * s, cy * s, PW * s, PL * s, -mn[2] * s))
print('TRIS', sum(len(p.vertices) - 2 for p in target.data.polygons), 'MATS', len(target.data.materials))
roof_open.hide_render = False
select_only(objs, target)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
extra = {}
if 'export_vertex_color' in props: extra['export_vertex_color'] = 'ACTIVE'
if 'export_all_vertex_colors' in props: extra['export_all_vertex_colors'] = False
if 'export_active_vertex_color_when_no_material' in props: extra['export_active_vertex_color_when_no_material'] = True
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, **extra)
print('EXPORTED', OUT_GLB)
