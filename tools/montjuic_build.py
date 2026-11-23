# Builds the Estadi Olímpic Lluís Companys (Montjuïc, Barcelona) from nothing
# and exports it for the game, the way MetLife, De Kuip, El Campín and the
# Johan Cruijff ArenA are built; this one in the afternoon sun, as on the
# photos of FC Barcelona's seasons there (2023-2025), not floodlit.
#   blender -b --factory-startup --python tools/montjuic_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#   quick: no light bakes and no export, only preview renders into <texture dir>
#
# The facts and the plan:
#   - built 1927-29 for the 1929 Exhibition (Pere Domènech i Roura), rebuilt
#     1985-89 for the 1992 Games (Vittorio Gregotti with Correa, Milà, Margarit
#     and Buxadé): the old facades kept, the pitch lowered by about 11 m, two
#     new rings of stands, a roof over the west stand of two 65 m beams
#   - the footprint, the roof, the pitch, the cauldron and two of the
#     floodlight masts are where OpenStreetMap has them (way 35764760, 126784791,
#     35743735; data © OpenStreetMap contributors, ODbL), turned 0.6 degrees so
#     the pitch lies on the axes: the pitch 104.9 x 67.1 m, the facade 275 m
#     long, the roof 130 m long and 40 m deep, four gate houses on the east
#     front, the Marathon Gate 29 m wide in the middle of the north end
#   - inside, as on the photos: a 400 m track round the pitch, for Barça
#     covered with artificial grass, a big cloth with the crest on the grass in
#     each curve (its top towards the stand); a first ring of light grey seats
#     with yellow stairs and blaugrana covers over its first rows, a walkway
#     with the red banners (FC BARCELONA, MÉS QUE UN CLUB) on the front of the
#     second ring; the gate houses and five floodlight masts behind the east
#     stand, the Montjuïc hill full of pines behind them
#   - the north end: the Marathon Gate, its arch open through the second ring,
#     the clock on top, the round arms of Barcelona under it, the two bronze
#     horsemen of Pau Gargallo either side, BARCELONA over the tunnel under the
#     arch; the Olympic cauldron on its column east of it and the platform on
#     two legs on the rim
#   - the south end: a tunnel through the first ring; over the second ring,
#     east of the middle, the screen in a grey frame on a cream concrete beam
#     and two round columns (game.screen.js, style 'montjuic': Barça's half
#     blue, the other red, the crests, the score and the minutes of the
#     goals), in the middle, lower, a plain black board with a white clock
#   - the west stand under Gregotti's roof: the press gallery behind the second
#     ring, the glass box of the royal box in the middle, three concrete piers,
#     the white truss on top and the stays down to the facade; outside the
#     main front with five arches, the dome with Gargallo's two charioteers and
#     the tower with its lantern north of it
# No sponsor names: the boards and banners carry the club's own words.
#
# The helpers, the goals and the export are those of tools/arena_build.py;
# units here are metres, x towards the north (the left of the match camera),
# y towards the west (the camera's side), z up.
import bpy, bmesh, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'montjuic')
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
XS = 42.195                      # half the straight of the track: the curves are round (±XS, 0)
R_KERB, LANE = 36.5, 1.22        # lane 1's inner edge; eight lanes
R_TRACK = R_KERB + 8 * LANE
R_WALL, WALL_Z = 49.5, 1.3       # the low wall in front of the first ring
LOW = dict(r=49.8, z=1.4, rows=26, depth=0.80, rise=0.40)            # to r 70.6, z 11.4
LOW_BACK = LOW['r'] + LOW['depth'] * LOW['rows']
LOW_TOP = LOW['z'] + LOW['rise'] * (LOW['rows'] - 1)
WALK_Z = LOW_TOP + 0.4           # the walkway between the rings: the old ground level
BAL_R, BAL_Z = 72.4, WALK_Z + 1.5                                    # the front of the second ring, with the banners
UP = dict(r=72.6, z=BAL_Z + 0.3, rows=17, depth=0.82, rise=0.56)    # to r 86.5, z 22.6
UP_BACK = UP['r'] + UP['depth'] * UP['rows']
UP_TOP = UP['z'] + UP['rise'] * (UP['rows'] - 1)
PARAPET_Z = UP_TOP + 1.45
GROUND_Z = 11.5                  # the streets round the stadium
CORNICE_Z = 25.4
ESPLANADE_Z, ESPLANADE_Y = 6.0, 104.0                               # the Olympic esplanade, lower, west of the stadium
GAIN = 2.0                       # the game draws the model unlit at this gain (catalog: look.gain)
SEAT_W, AISLE_W = 0.5, 1.1
N_STR, N_ARC = 14, 48            # pieces of each straight (6 m) and each curve (3.75 degrees)
NP = 2 * (N_STR + N_ARC)
I_S = N_STR + N_ARC // 2         # the point on the south axis
I_N = 2 * N_STR + N_ARC + N_ARC // 2
GATE_HW, GATE_X = 14.5, 139.2    # the Marathon Gate: half its width, its outer face
GATE_BAY = 5.6                   # half the width of its middle bay, the one with the arch
GATE_IN = XS + BAL_R             # the inner face of the middle bay, at the walkway
GATE_WING = XS + UP['r'] + 11 * UP['depth'] - 0.2                   # the wings stand behind row 11 of the second ring
TUNNEL_HW, TUNNEL_ROWS = 3.3, 8  # the south tunnel through the first ring
ROOF_X0, ROOF_X1 = -63.6, 66.2   # Gregotti's roof (OSM): 130 m along the west stand
ROOF_Y0, ROOF_Y1 = 54.0, 92.0    # from its front edge to the facade
ROOF_UNDER0, ROOF_UNDER1 = 36.4, 35.2     # its underside at the front and the back
ROOF_TOP0, ROOF_TOP1 = 39.4, 38.6
FACADE_W = 92.0                  # the west front under the roof
UPV = Vector((0, 0, 1))

# the footprint (OSM way 35764760, in these axes), counter-clockwise from the
# north-west; 'c' points lie on a curve and are smoothed, the others are corners.
# The east front is straightened (the gate houses are their own blocks), the
# Marathon Gate and the middle bay of the south front squared, the four steps
# at the ends of the long sides moved out 1-2 m so the back of the second ring
# stays inside.
OUTLINE = [
    (66.1, 85.2, 's'), (66.2, FACADE_W, 's'), (ROOF_X0, FACADE_W, 's'), (-63.6, 85.2, 's'),
    (-107.6, 80.7, 'c'), (-113.2, 73.3, 'c'), (-118.6, 63.9, 'c'), (-127.7, 43.3, 'c'), (-131.2, 30.6, 'c'), (-134.4, 10.0, 's'),
    (-135.8, 10.0, 's'), (-135.8, -10.0, 's'),
    (-134.4, -10.0, 's'), (-132.0, -28.1, 'c'), (-129.9, -36.0, 'c'), (-125.8, -48.5, 'c'), (-120.1, -61.9, 'c'), (-113.9, -72.9, 'c'), (-109.3, -79.3, 'c'),
    (-65.6, -85.2, 's'), (-65.5, -92.8, 's'), (65.0, -92.8, 's'), (64.9, -85.2, 's'),
    (109.3, -81.0, 'c'), (118.0, -67.9, 'c'), (124.4, -55.8, 'c'), (127.4, -47.9, 'c'), (131.6, -35.0, 'c'), (133.7, -26.2, 'c'), (135.4, -GATE_HW, 's'),
    (GATE_X, -GATE_HW, 's'), (GATE_X, GATE_HW, 's'),
    (135.5, GATE_HW, 's'), (133.8, 25.3, 'c'), (129.4, 42.1, 'c'), (126.6, 49.5, 'c'), (123.1, 57.7, 'c'), (117.4, 68.7, 'c'), (110.6, 79.5, 'c'), (92.5, 81.0, 'c'),
]
PAVILIONS = [-49.9, -16.7, 16.3, 49.5]          # the gate houses on the east front (OSM), 13.6 m wide
PAV_HW, PAV_Y0, PAV_Y1, PAV_TOP = 6.8, -87.6, -97.2, 28.6
MASTS = [(-70.5, -81.7), (-33.3, -88.6), (-0.2, -88.6), (32.9, -88.6), (78.1, -80.9)]   # the ends from OSM, the others between the gate houses
MAST_TOP = 62.0
CAULDRON = (137.4, -23.3)                       # OSM: the Olympic cauldron
TOWER_X, TOWER_Y0, TOWER_Y1 = 50.0, 90.5, 99.5  # the tower on the west front
SUN_AZ, SUN_EL = 200.0, 52.0                    # the sun: south-south-west, early afternoon


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


# ---------------------------------------------------------------- the bowl's plan: a 400 m track shape
def bowl_pts(r):
    # NP points counter-clockwise from the north end of the west straight;
    # point i lies on the same line out from the track at every r
    pts = []
    for k in range(N_STR):
        pts.append((XS - 2 * XS * k / N_STR, r))
    for k in range(N_ARC):
        a = math.pi / 2 + math.pi * k / N_ARC
        pts.append((-XS + r * math.cos(a), r * math.sin(a)))
    for k in range(N_STR):
        pts.append((-XS + 2 * XS * k / N_STR, -r))
    for k in range(N_ARC):
        a = -math.pi / 2 + math.pi * k / N_ARC
        pts.append((XS + r * math.cos(a), r * math.sin(a)))
    return [Vector((x, y, 0)) for x, y in pts]


def piece(i):
    # which part of the plan point i is on, and how far along it
    if i < N_STR: return 'W', i
    if i < N_STR + N_ARC: return 'S', i - N_STR
    if i < 2 * N_STR + N_ARC: return 'E', i - N_STR - N_ARC
    return 'N', i - 2 * N_STR - N_ARC


def is_aisle(i):
    s, k = piece(i % NP)
    return k % 2 == 0 if s in 'WE' else k % 4 == 0


def is_mid(i):
    s, k = piece(i % NP)
    return k % 2 == 1 if s in 'WE' else k % 4 == 2


def cumlen(p):
    c = [0.0]
    for i in range(NP):
        c.append(c[-1] + (p[(i + 1) % NP] - p[i]).length)
    return c


def outward(i, p):
    j = (i + 1) % NP
    t = p[j] - p[i]
    return Vector((t.y, -t.x, 0)).normalized()


def bring(bm, r0, z0, r1, z1, mat, keep=None, want=None, step=3.0, u_len=None, v=(0, 1)):
    # a band all round the bowl between the line at r0 (height z0) and r1 (z1)
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
    pts = [Vector((x, y, 0)) for x, y, _ in OUTLINE]
    sharp = [k == 's' for _, _, k in OUTLINE]
    n = len(pts)
    out = []
    for i in range(n):
        p1, p2 = pts[i], pts[(i + 1) % n]
        p0 = pts[i - 1] if not sharp[i] else p1 - (p2 - p1)
        p3 = pts[(i + 2) % n] if not sharp[(i + 1) % n] else p2 + (p2 - p1)
        m = max(1, math.ceil((p2 - p1).length / step))
        for k in range(m):
            t = k / m
            if sharp[i] and sharp[(i + 1) % n]:
                out.append(p1.lerp(p2, t))
                continue
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


FOOT = outline_path()


def inside_foot(x, y, poly=None):
    poly = poly or FOOT
    c = False
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if (a.y > y) != (b.y > y):
            if x < a.x + (y - a.y) * (b.x - a.x) / (b.y - a.y):
                c = not c
    return c


def ray_foot(o, d):
    # the first point where the ray from o along d meets the footprint
    best = None
    n = len(FOOT)
    for i in range(n):
        a, b = FOOT[i], FOOT[(i + 1) % n]
        e = b - a
        den = d.x * e.y - d.y * e.x
        if abs(den) < 1e-9:
            continue
        w = a - o
        t = (w.x * e.y - w.y * e.x) / den
        s = (w.x * d.y - w.y * d.x) / den
        if t > 0 and 0 <= s <= 1 and (best is None or t < best):
            best = t
    return o + d * best if best is not None else o


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1929)


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


STONE = np.array((0.62, 0.53, 0.40), 'f')       # the cream stone of the 1929 fronts
FRAME = np.array((0.26, 0.035, 0.035), 'f')     # the dark red window frames
GLASS = np.array((0.035, 0.04, 0.05), 'f')


def window(t, x0, x1, y0, y1, frame=3, arch=False, shutter=False):
    # a window on a facade picture: dark glass in a dark red frame (row 0 at the top)
    t[y0:y1, x0:x1] = FRAME
    gx0, gx1, gy0, gy1 = x0 + frame, x1 - frame, y0 + frame, y1 - frame
    t[gy0:gy1, gx0:gx1] = GLASS * (1 + 0.6 * np.linspace(0, 1, gy1 - gy0))[:, None, None]
    if shutter:
        t[gy0:gy1, gx0:gx1] = FRAME * 1.25
        t[gy0:gy1:4, gx0:gx1] *= 0.6
    else:
        t[gy0:gy1, (gx0 + gx1) // 2 - 1:(gx0 + gx1) // 2 + 1] = FRAME
    if arch:
        r = (x1 - x0) / 2
        yy, xx = np.mgrid[0:int(r) + 1, x0:x1]
        cx = (x0 + x1 - 1) / 2
        out = (xx - cx) ** 2 + (r - yy) ** 2 > r * r
        sub = t[y0 - int(r) - 1:y0, x0:x1]
        hh = sub.shape[0]
        m = ~out[-hh:]
        sub[m] = FRAME
        inner = (xx - cx) ** 2 + (r - yy) ** 2 < (r - frame) ** 2
        sub[inner[-hh:]] = GLASS


def stone_base(w, h, block=(32, 16)):
    t = np.ones((h, w, 3), 'f') * STONE
    t *= (1 + 0.035 * vnoise(h, w, 24, 24) + 0.02 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    yy, xx = np.arange(h), np.arange(w)
    t[(yy % block[1]) == 0] *= 0.86
    off = ((yy // block[1]) % 2) * (block[0] // 2)
    jx = ((xx[None, :] + off[:, None]) % block[0]) == 0
    t[jx] *= 0.90
    return t


def facade_tex():
    # the 1929 fronts, one bay of 12 m from the street (bottom) to the cornice
    # (top, 13.9 m): rusticated base with tall red doors, a string course,
    # two rows of windows (the lower with red shutters), pilasters, the cornice
    PXM = 24
    w, h = 12 * PXM, int(13.9 * PXM)
    t = stone_base(w, h)
    yy = np.arange(h)
    base = yy > h - 4.2 * PXM
    t[base & ((yy % 12) < 3)] *= 0.72                                          # the rustication
    t[int(h - 4.4 * PXM):int(h - 4.1 * PXM)] = STONE * 1.08                    # the string course
    t[:int(1.2 * PXM)] = STONE * 1.05                                          # the cornice
    t[int(1.2 * PXM):int(1.35 * PXM)] = STONE * 0.62                           # its shadow line
    for px in (0, w - int(0.9 * PXM)):                                         # pilasters at the bay ends
        t[int(1.35 * PXM):int(h - 4.4 * PXM), px:px + int(0.9 * PXM)] *= 1.07
    for cx in (3.2, 8.8):
        x0, x1 = int((cx - 0.7) * PXM), int((cx + 0.7) * PXM)
        window(t, x0, x1, int(h - 8.0 * PXM), int(h - 5.4 * PXM), shutter=True)
        window(t, x0, x1, int(h - 11.6 * PXM), int(h - 9.2 * PXM))
    window(t, int(5.4 * PXM), int(6.6 * PXM), int(h - 3.3 * PXM), h - 2, shutter=True)   # a red door in the base
    return t[::-1]


def east_tex():
    # the long east front: plainer, a row of high windows, stone joints
    PXM = 24
    w, h = 12 * PXM, int(13.9 * PXM)
    t = stone_base(w, h)
    t[:int(1.0 * PXM)] = STONE * 1.05
    t[int(1.0 * PXM):int(1.12 * PXM)] = STONE * 0.62
    t[int(h - 1.0 * PXM):] *= 0.9
    for cx in (2.0, 6.0, 10.0):
        window(t, int((cx - 0.5) * PXM), int((cx + 0.5) * PXM), int(h - 6.2 * PXM), int(h - 4.0 * PXM))
    return t[::-1]


def main_tex():
    # the west main front: a high arcade of round-headed windows over a base
    PXM = 24
    w, h = 9 * PXM, int(16.5 * PXM)
    t = stone_base(w, h)
    t[:int(1.3 * PXM)] = STONE * 1.06
    t[int(1.3 * PXM):int(1.45 * PXM)] = STONE * 0.6
    t[int(h - 4.6 * PXM):int(h - 4.3 * PXM)] = STONE * 1.1
    window(t, int(2.6 * PXM), int(6.4 * PXM), int(h - 11.5 * PXM), int(h - 5.6 * PXM), frame=5, arch=True)
    t[int(2.0 * PXM):int(h - 4.6 * PXM), :int(0.8 * PXM)] *= 1.08
    for cx in (2.2, 6.8):
        window(t, int((cx - 0.55) * PXM), int((cx + 0.55) * PXM), int(h - 3.6 * PXM), int(h - 1.2 * PXM), shutter=True)
    return t[::-1]


def gate_in_tex():
    # the Marathon Gate seen from the pitch: 29 m wide, from the walkway
    # (bottom) to the top of the attic (19.6 m above it). The arch is cut out
    # of the mesh; here the pilasters, the square windows of the attic, the two
    # square panels either side of the round arms (painted on afterwards)
    PXM = 20
    w, h = int(2 * GATE_HW * PXM), int(19.6 * PXM)
    t = stone_base(w, h, (40, 20))
    zz = lambda z: int(h - z * PXM)                                            # height over the walkway -> row
    xx = lambda y: int((y + GATE_HW) * PXM)
    t[zz(19.6):zz(18.8)] = STONE * 1.08                                        # the top cornice
    t[zz(18.8):zz(18.6)] = STONE * 0.6
    t[zz(14.3):zz(13.6)] = STONE * 1.08                                        # the cornice under the attic
    t[zz(13.6):zz(13.4)] = STONE * 0.6
    for y in (-GATE_HW + 0.3, -GATE_BAY - 0.9, GATE_BAY, GATE_HW - 1.2):      # pilasters
        t[zz(18.6):, xx(y):xx(y + 0.9)] *= 1.09
        t[zz(18.6):, xx(y + 0.9):xx(y + 1.0)] *= 0.75
    for c in np.linspace(-GATE_BAY + 1.3, GATE_BAY - 1.3, 5):                 # the attic: five windows over the arch
        window(t, xx(c - 0.55), xx(c + 0.55), zz(17.9), zz(15.0), frame=2)
    for s in (-1, 1):                                                          # four on each wing
        for c in np.linspace(GATE_BAY + 1.6, GATE_HW - 2.0, 4):
            window(t, xx(s * c - 0.5), xx(s * c + 0.5), zz(17.9), zz(15.0), frame=2)
    for c in (-3.4, 3.4):                                                      # the square panels beside the arms
        t[zz(13.0):zz(11.0), xx(c - 1.1):xx(c + 1.1)] *= 0.86
        t[zz(12.8):zz(11.2), xx(c - 0.9):xx(c + 0.9)] *= 1.12
    return t[::-1]


def gate_out_tex():
    # the gate from the street: 29 m wide, 20.6 m from the street to the attic
    # top: pilasters with capitals, two rows of windows on the wings, the frieze
    # over the arch (painted in), the loggia of small columns, the attic
    PXM = 20
    w, h = int(2 * GATE_HW * PXM), int(20.6 * PXM)
    t = stone_base(w, h, (40, 20))
    zz = lambda z: int(h - z * PXM)
    xx = lambda y: int((y + GATE_HW) * PXM)
    t[zz(20.6):zz(19.6)] = STONE * 1.07
    t[zz(15.6):zz(15.0)] = STONE * 1.08
    t[zz(15.0):zz(14.8)] = STONE * 0.62
    t[zz(1.2):] *= 0.9
    for y in np.linspace(-GATE_HW + 0.4, -GATE_BAY - 1.0, 4).tolist() + np.linspace(GATE_BAY, GATE_HW - 1.4, 4).tolist():
        t[zz(15.0):zz(0.0) - 1, xx(y):xx(y + 1.0)] *= 1.08
        t[zz(15.0):zz(14.2), xx(y - 0.2):xx(y + 1.2)] = STONE * 1.15         # the capitals
    for s in (-1, 1):
        for c in np.linspace(GATE_BAY + 1.6, GATE_HW - 2.1, 3):
            window(t, xx(s * c - 0.6), xx(s * c + 0.6), zz(12.8), zz(10.0))
            window(t, xx(s * c - 0.6), xx(s * c + 0.6), zz(7.6), zz(4.4))
    for c in np.linspace(-GATE_BAY + 0.8, GATE_BAY - 0.8, 7):                 # the loggia over the frieze
        t[zz(18.6):zz(16.2), xx(c - 0.45):xx(c + 0.45)] = GLASS * 2.0
    return t[::-1]


def tower_tex():
    # the tower's sides: plain stone with a slit window every few storeys
    PXM = 20
    w, h = int(9 * PXM), int(38.5 * PXM)
    t = stone_base(w, h, (40, 20))
    t[:, :int(0.8 * PXM)] *= 1.07
    t[:, -int(0.8 * PXM):] *= 1.07
    for z in (6.0, 14.0, 22.0, 30.0):
        window(t, int(3.9 * PXM), int(5.1 * PXM), int(h - (z + 2.2) * PXM), int(h - z * PXM), frame=2)
    return t[::-1]


def glass_tex(lit=0.25):
    # the press gallery and the royal box: dark glass, a few panes with a light on
    w, h = 256, 64
    t = np.ones((h, w, 3), 'f') * np.array((0.04, 0.05, 0.06), 'f')
    t *= (1 + 0.5 * np.linspace(0, 1, h))[:, None, None]
    for k in range(16):
        if rng.random() < lit:
            t[8:h - 8, k * 16 + 2:k * 16 + 14] = np.array((0.32, 0.30, 0.26), 'f') * rng.uniform(0.5, 1.0)
    t[:, (np.arange(w) % 16) < 2] = (0.55, 0.56, 0.57)
    t[:3] = (0.55, 0.56, 0.57); t[-3:] = (0.55, 0.56, 0.57)
    return t


def roof_under_tex():
    # under Gregotti's roof: light grey panels between the white beams that run front to back
    w, h = 128, 32
    t = np.ones((h, w, 3), 'f') * np.array((0.52, 0.53, 0.54), 'f')
    xx = np.arange(w)
    t[:, (xx % 32) < 3] = (0.78, 0.79, 0.80)
    t[:, (xx % 8) == 4] *= 0.85
    return t


def fascia_tex():
    # the front edge of the roof: the ends of the white beams, a row of
    # openings with the dark underside behind them, as on the photos
    w, h = 256, 64
    t = np.ones((h, w, 3), 'f') * np.array((0.80, 0.81, 0.82), 'f')
    xx, yy = np.arange(w), np.arange(h)
    hole = ((yy > 14) & (yy < 50))[:, None] & ((xx % 32) > 8)[None, :] & ((xx % 32) < 28)[None, :]
    t[hole] = (0.16, 0.17, 0.18)
    t[:4] *= 0.8
    return t


def turf_tex():
    # the artificial grass laid over the track: even, a faint seam every roll
    w, h = 64, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.055, 0.17, 0.045), 'f')
    t *= (1 + 0.05 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    t[(np.arange(h) % 128) < 2] *= 0.85
    return t


def foliage_tex():
    # pines and holm oaks on the hill, as on the photos: dark mottled greens
    w = h = 256
    a = 0.55 * vnoise(h, w, 10, 10) + 0.3 * vnoise(h, w, 4, 4) + 0.15 * rng.normal(0, 1, (h, w)).astype('f')
    t = np.ones((h, w, 3), 'f') * np.array((0.028, 0.052, 0.021), 'f')
    t *= (1 + 0.45 * a)[..., None]
    t[..., 0] *= 1 + 0.25 * vnoise(h, w, 30, 30)
    return np.clip(t, 0, 1)


def paving_tex():
    # the cream paving round the stadium
    w = h = 128
    t = np.ones((h, w, 3), 'f') * np.array((0.50, 0.44, 0.36), 'f')
    t *= (1 + 0.04 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    t[(np.arange(h) % 16) == 0] *= 0.85
    t[:, (np.arange(w) % 32) == 0] *= 0.85
    return t


def column_tex():
    # the yellow columns of the Olympic ring: gold-yellow with dark rings
    w, h = 32, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.52, 0.40, 0.10), 'f')
    t[(np.arange(h) % 24) < 2] = (0.08, 0.08, 0.07)
    return t


SEAT_GREY = [(0.31, 0.32, 0.33), (0.29, 0.30, 0.31), (0.33, 0.34, 0.35)]       # light grey plastic, as dark as on the photos in the sun
seat_cols = [image_material('M_Seat%d' % i, painted('mj_seat%d' % i, seat_tile(c)), 0.6)
             for i, c in enumerate(SEAT_GREY + [(0.07, 0.08, 0.10)])]               # 3: the dark seats of the main stand
concrete = principled('M_Concrete', (0.36, 0.35, 0.33), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.27, 0.26, 0.25), 0.9)
concrete_light = principled('M_ConcreteLight', (0.46, 0.45, 0.42), 0.85)
aisle_yellow = principled('M_AisleYellow', (0.50, 0.34, 0.045), 0.8)               # the stairs of the first ring
portal = principled('M_Portal', (0.015, 0.015, 0.018), 0.95)
steel_white = principled('M_SteelWhite', (0.80, 0.81, 0.82), 0.5)
steel_grey = principled('M_SteelGrey', (0.42, 0.43, 0.44), 0.5)
steel_dark = principled('M_SteelDark', (0.05, 0.05, 0.06), 0.6)
stone = image_material('M_Stone', painted('mj_stone', stone_base(128, 64)), 0.85)
stone_plain = principled('M_StonePlain', tuple(STONE * 1.02), 0.85)
facade = image_material('M_Facade', painted('mj_facade', facade_tex()), 0.85)
east_front = image_material('M_EastFront', painted('mj_east', east_tex()), 0.85)
main_front = image_material('M_MainFront', painted('mj_main', main_tex()), 0.85)
gate_in = image_material('M_GateIn', painted('mj_gate_in', gate_in_tex()), 0.85)
gate_out = image_material('M_GateOut', painted('mj_gate_out', gate_out_tex()), 0.85)
tower_side = image_material('M_Tower', painted('mj_tower', tower_tex()), 0.85)
glass = image_material('M_Glass', painted('mj_glass', glass_tex()), 0.2)
dark_glass = principled('M_DarkGlass', (0.02, 0.025, 0.03), 0.15)
roof_under = image_material('M_RoofUnder', painted('mj_roofunder', roof_under_tex()), 0.7)
roof_top = principled('M_RoofTop', (0.66, 0.67, 0.68), 0.5, metallic=0.1)
fascia = image_material('M_Fascia', painted('mj_fascia', fascia_tex()), 0.6)
roof_flat = principled('M_FlatRoof', (0.36, 0.35, 0.33), 0.95)                       # the concourse roofs behind the stands
tiles = principled('M_Tiles', (0.30, 0.27, 0.24), 0.8)                               # the low roofs of the gate houses
bronze = principled('M_Bronze', (0.07, 0.085, 0.065), 0.5, metallic=0.4)
cauldron_black = principled('M_CauldronBlack', (0.025, 0.025, 0.025), 0.5)
band_mat = image_material('M_Band', load_asset('band.png'), 0.8)
tarp_mat = image_material('M_Tarp', load_asset('tarp.png'), 0.9)
clock_mat = image_material('M_Clock', load_asset('clock.png'), 0.6)
arms_mat = image_material('M_Arms', load_asset('arms.png'), 0.8)
relief_mat = image_material('M_Relief', load_asset('relief.png'), 0.9)
led_blue = principled('M_LEDBlue', (0.012, 0.045, 0.24), 0.4, (0.012, 0.045, 0.24), 2.5)        # the boards round the pitch
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
lamp = principled('M_FloodLight', (0.85, 0.86, 0.84), 0.3)
sign_black = principled('M_SignBlack', (0.02, 0.02, 0.025), 0.6)
turf = image_material('M_Turf', painted('mj_turf', turf_tex()), 0.9)
foliage = image_material('M_Foliage', painted('mj_foliage', foliage_tex()), 0.95)
board_white = principled('M_BoardWhite', (0.82, 0.82, 0.80), 0.6)
board_red = principled('M_BoardRed', (0.50, 0.03, 0.07), 0.6)
board_blue = principled('M_BoardBlue', (0.02, 0.06, 0.26), 0.6)
paving = image_material('M_Paving', painted('mj_paving', paving_tex()), 0.9)
asphalt = principled('M_Asphalt', (0.06, 0.06, 0.065), 0.95)
lawn = principled('M_Lawn', (0.06, 0.13, 0.04), 0.95)
trunk = principled('M_Trunk', (0.12, 0.09, 0.07), 0.9)
gold_col = image_material('M_Column', painted('mj_column', column_tex()), 0.6)
white_paint = principled('M_WhitePaint', (0.82, 0.82, 0.80), 0.7)

# ================================================================ the pitch lines, the goals (as in the ArenA script)
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
net_img = D.images.new('mj_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/mj_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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

# the two floors the game sees: the pitch (grass, lines, the run-off) and,
# under it, the whole ground inside the stands (the covered track, the cloths
# in the curves); each gets its own picture with the sun baked in (below)
PITCH_X, PITCH_Y = 58.0, 40.0
FLOOR_X, FLOOR_Y = XS + R_WALL, R_WALL
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-PITCH_X, -PITCH_Y), (PITCH_X, -PITCH_Y), (PITCH_X, PITCH_Y), (-PITCH_X, PITCH_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.07, 0.25, 0.06), 0.85)])
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
ring_pts = bowl_pts(R_WALL)
FLOOR_Z = -0.05                  # under the pitch, far enough that the two never flicker
centre = bm.verts.new((0, 0, FLOOR_Z))
vs = [bm.verts.new((p.x, p.y, FLOOR_Z)) for p in ring_pts]
for i in range(NP):
    fc = bm.faces.new((centre, vs[i], vs[(i + 1) % NP]))
    for l in fc.loops:
        l[uv].uv = ((l.vert.co.x / FLOOR_X + 1) / 2, (l.vert.co.y / FLOOR_Y + 1) / 2)
    fc.normal_update()
    if fc.normal.z < 0:
        fc.normal_flip()
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.06, 0.18, 0.05), 0.9)])

# ================================================================ the stands
def in_gate(p, margin=0.3):
    # inside the Marathon Gate's block (plan)
    if abs(p.y) > GATE_HW + margin:
        return False
    if abs(p.y) <= GATE_BAY:
        return p.x > GATE_IN - margin
    return p.x > GATE_WING - margin


def hole(tier, row, p):
    # where a stand has no rows: the south tunnel, the gate, the royal box
    if tier == 'low' and row < TUNNEL_ROWS and p.x < -(XS + R_WALL - 1) and abs(p.y) < TUNNEL_HW:
        return True
    if tier == 'up' and in_gate(p):
        return True
    if tier == 'up' and row >= 13 and p.y > 0 and abs(p.x) < 9.6 and abs(p.x) < XS:
        return True
    return False


def dark_spot(tier, row, i, u, L):
    # the tunnel mouths in the seats: half way along each block of the second
    # ring, in its first three rows, as on the photos of the east stand; the
    # opening at the top of the first ring under the Marathon Gate
    if tier == 'low':
        return row >= LOW['rows'] - 8 and piece(i)[0] == 'N' and i in (I_N - 1, I_N)
    if row > 2:
        return False
    d = None
    if is_mid(i + 1):
        d = (1 - u) * L
    elif is_mid(i):
        d = u * L
    return d is not None and d < 1.4


def seat_colour(tier, side, row, p, h):
    if tier == 'low' and side == 'W' and abs(p.x) < 18.5 and row >= 6:
        return 3                                   # the dark seats in the middle of the main stand
    return h % 3


def seat_pair(bm, pa, pb, back, m, q, q1):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
    face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UPV, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])


def build_tier(name, t, base_z, tier):
    steps, seats, aisles, dark, cover = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    front_len = cumlen(bowl_pts(t['r']))
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
            # the tread and the riser in front of it, in pieces
            for s in range(n):
                a0, a1 = A0.lerp(A1, s / n), A0.lerp(A1, (s + 1) / n)
                b0, b1 = B0.lerp(B1, s / n), B0.lerp(B1, (s + 1) / n)
                mid = (a0 + a1 + b0 + b1) / 4
                if hole(tier, k, mid):
                    continue
                face(steps, [(a0.x, a0.y, z), (a1.x, a1.y, z), (b1.x, b1.y, z), (b0.x, b0.y, z)], UPV, 0)
                face(steps, [(a0.x, a0.y, z_prev), (a1.x, a1.y, z_prev), (a1.x, a1.y, z), (a0.x, a0.y, z)], -back, 1)
            # the stairs at the ends of the piece
            cut0 = AISLE_W / 2 if is_aisle(i) else 0.0
            cut1 = AISLE_W / 2 if is_aisle(j) else 0.0
            amat = 0
            for span in ([(0.0, cut0 / L)] if cut0 else []) + ([(1 - cut1 / L, 1.0)] if cut1 else []):
                u0, u1 = span
                f0, f1 = A0.lerp(A1, u0), A0.lerp(A1, u1)
                g0, g1 = B0.lerp(B1, u0), B0.lerp(B1, u1)
                if hole(tier, k, (f0 + f1 + g0 + g1) / 4):
                    continue
                F0, F1, G0, G1 = (Vector((v.x, v.y, z)) + lift for v in (f0, f1, g0, g1))
                face(aisles, [F0, F1, G1, G0], UPV, amat)
                if k:
                    down, out_ = Vector((0, 0, -t['rise'])), -back * 0.012
                    face(aisles, [F0 + down + out_, F1 + down + out_, F1 + out_, F0 + out_], -back, amat)
            # the covers over the first rows of the first ring
            if tier == 'low' and k == 0:
                rr = t['r'] + t['depth'] * 5
                q0, q1 = bowl_pts(rr)[i], bowl_pts(rr)[j]
                za, zb = z + 0.5, t['z'] + t['rise'] * 4 + 0.86
                u0, u1 = cut0 / L, 1 - cut1 / L
                nn_ = max(1, math.ceil(L / 3.0))
                for s in range(nn_):
                    ua, ub = u0 + (u1 - u0) * s / nn_, u0 + (u1 - u0) * (s + 1) / nn_
                    fa, fb = A0.lerp(A1, ua), A0.lerp(A1, ub)
                    ga, gb = q0.lerp(q1, ua), q0.lerp(q1, ub)
                    if hole(tier, 0, (fa + fb) / 2):
                        continue
                    ta, tb = (front_len[i] + L * ua) / 12.0, (front_len[i] + L * ub) / 12.0
                    face(cover, [(fa.x, fa.y, za), (fb.x, fb.y, za), (gb.x, gb.y, zb), (ga.x, ga.y, zb)], UPV - back * 0.3, 0,
                         [(ta, 0.0), (tb, 0.0), (tb, 1.0), (ta, 1.0)])
            if tier == 'low' and k < 5:
                continue                           # under the covers
            # the seats
            usable = L - cut0 - cut1
            nseat = max(1, round(usable / SEAT_W))
            mats = []
            for q in range(nseat):
                u = (cut0 + usable * (q + 0.5) / nseat) / L
                p = A0.lerp(A1, u).lerp(B0.lerp(B1, u), 0.5)
                if hole(tier, k, p):
                    mats.append(None)
                    continue
                if dark_spot(tier, k, i, u, L):
                    mats.append('dark')
                    continue
                h = (k * 73856093) ^ (i * 19349663) ^ ((q // 3) * 83492791)
                mats.append(seat_colour(tier, side, k, p, h))
            # the dark tunnel mouths
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
                if (tier == 'up' and k == 2) or (tier == 'low' and k == LOW['rows'] - 1):
                    for g in (G0, G1):                                   # the white rails round the opening
                        tube(dark, g + Vector((0, 0, 0.0)), g + Vector((0, 0, 1.0)), 0.03, 1, 4)
                    tube(dark, G0 + Vector((0, 0, 1.0)), G1 + Vector((0, 0, 1.0)), 0.03, 1, 4)
                q = q1
            q = 0
            while q < nseat:
                m = mats[q]
                if m is None or m == 'dark':
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
    new_obj('Aisles_' + name, aisles, '02_Bowl', [aisle_yellow if tier == 'low' else concrete_light])
    new_obj('Portals_' + name, dark, '02_Bowl', [portal, steel_white])
    if tier == 'low':
        new_obj('Covers', cover, '03_Seats', [tarp_mat])
    else:
        cover.free()


random.seed(1929)
t0 = time.time()
build_tier('Lower', LOW, WALL_Z, 'low')
build_tier('Upper', UP, BAL_Z, 'up')
print('STANDS %.0fs' % (time.time() - t0))

# the low wall in front of the first ring and its rail; the south tunnel
bm = bmesh.new()
south_tunnel = lambda i, p: not (p.x < -(XS + R_WALL - 1) and abs(p.y) < TUNNEL_HW)
bring(bm, R_WALL, 0.0, R_WALL, WALL_Z, 0, keep=south_tunnel)
bring(bm, R_WALL, WALL_Z, LOW['r'], WALL_Z, 0, keep=south_tunnel, want='up')
bring(bm, R_WALL - 0.05, WALL_Z + 0.95, R_WALL - 0.05, WALL_Z + 1.02, 1, step=6.0)
TZ = LOW['z'] + LOW['rise'] * (TUNNEL_ROWS - 1) + 0.3          # the tunnel's roof
tx0, tx1 = -(XS + R_WALL), -(XS + LOW['r'] + LOW['depth'] * TUNNEL_ROWS)
face(bm, [(tx0, -TUNNEL_HW, TZ), (tx0, TUNNEL_HW, TZ), (tx1, TUNNEL_HW, TZ), (tx1, -TUNNEL_HW, TZ)], UPV, 0)
for s in (-1, 1):
    face(bm, [(tx0, s * TUNNEL_HW, 0), (tx1, s * TUNNEL_HW, 0), (tx1, s * TUNNEL_HW, TZ), (tx0, s * TUNNEL_HW, TZ)], Vector((0, -s, 0)), 2)
face(bm, [(tx1, -TUNNEL_HW, 0), (tx1, TUNNEL_HW, 0), (tx1, TUNNEL_HW, TZ), (tx1, -TUNNEL_HW, TZ)], Vector((1, 0, 0)), 2)
face(bm, [(tx0, -TUNNEL_HW - 0.4, TZ - 0.6), (tx0, TUNNEL_HW + 0.4, TZ - 0.6), (tx0, TUNNEL_HW + 0.4, TZ + 0.2), (tx0, -TUNNEL_HW - 0.4, TZ + 0.2)], Vector((1, 0, 0)), 3)
new_obj('Pitch_Wall', bm, '02_Bowl', [concrete_dark, steel_white, portal, white_paint])

# the walkway between the rings and the front of the second ring with the banners
bm = bmesh.new()
not_bay = lambda i, p: not (p.x > XS and abs(p.y) < GATE_BAY + 0.2)
bring(bm, LOW_BACK, LOW_TOP, LOW_BACK, WALK_Z, 1)
bring(bm, LOW_BACK, WALK_Z, BAL_R, WALK_Z, 0, want='up')
bring(bm, BAL_R, WALK_Z, BAL_R, BAL_Z, 2, keep=not_bay, want='in', u_len=-48.0)     # u runs against the plan: the words read from the pitch
bring(bm, BAL_R, BAL_Z, UP['r'], BAL_Z, 0, keep=not_bay, want='up')
bring(bm, LOW_BACK - 0.05, WALK_Z + 0.95, LOW_BACK - 0.05, WALK_Z + 1.02, 3, step=6.0)
new_obj('Walkway', bm, '02_Bowl', [concrete_light, concrete, band_mat, steel_white])

# the back of the second ring: the parapet, and the flat roofs of the
# concourse between it and the facade
bm = bmesh.new()
keep_out_gate = lambda i, p: not in_gate(p, 0.0)
bring(bm, UP_BACK, UP_TOP, UP_BACK, PARAPET_Z, 0, keep=keep_out_gate)
bring(bm, UP_BACK, PARAPET_Z, UP_BACK + 0.5, PARAPET_Z, 0, keep=keep_out_gate, want='up')
bring(bm, UP_BACK - 0.05, PARAPET_Z + 0.9, UP_BACK - 0.05, PARAPET_Z + 1.0, 1, keep=keep_out_gate, step=6.0)
pb = bowl_pts(UP_BACK + 0.5)
edge = []
for i in range(NP):
    n_ = (outward((i - 1) % NP, pb) + outward(i, pb)).normalized()
    edge.append(ray_foot(pb[i], n_))
for i in range(NP):
    j = (i + 1) % NP
    a, b, c_, d_ = pb[i], pb[j], edge[j], edge[i]
    if in_gate((a + b) / 2, 1.0) or not inside_foot(a.x, a.y) or not inside_foot(b.x, b.y):
        continue
    if (c_ - b).length > 40 or (d_ - a).length > 40:
        continue
    face(bm, [(a.x, a.y, PARAPET_Z), (b.x, b.y, PARAPET_Z), (c_.x, c_.y, PARAPET_Z), (d_.x, d_.y, PARAPET_Z)], UPV, 2)
new_obj('Upper_Back', bm, '02_Bowl', [concrete, steel_white, roof_flat])

# the tunnel under the Marathon Gate: BARCELONA in white on a black sign over it
bm = bmesh.new()
sx_ = GATE_IN + 0.05
abox(bm, sx_, sx_ + 0.4, -3.4, 3.4, WALK_Z + 0.3, WALK_Z + 1.5, 0, True, True)
new_obj('Barcelona_Sign', bm, '02_Bowl', [sign_black])
wall_text('Barcelona_T', 'BARCELONA', (sx_ - 0.03, 0, WALK_Z + 0.55), 0.0, 0.85, '02_Bowl', letters_white)

# the boards round the pitch: blue LED, white lettering; along the far side and
# behind both goals (the near side too, for the look from the stands)
BOARD_Y, BOARD_X = PL / 2 + 4.5, PW / 2 + 3.5
BOARD_LINES = [
    (Vector((52.0, -BOARD_Y, 0)), Vector((-52.0, -BOARD_Y, 0)), -math.pi / 2),
    (Vector((-52.0, BOARD_Y, 0)), Vector((-8.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((8.0, BOARD_Y, 0)), Vector((52.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((-BOARD_X, -26.0, 0)), Vector((-BOARD_X, 26.0, 0)), math.pi),
    (Vector((BOARD_X, 26.0, 0)), Vector((BOARD_X, -26.0, 0)), 0.0),
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
new_obj('LED_Boards', bm, '02_Bowl', [led_blue, steel_dark])
BOARD_TEXT = ['FC BARCELONA', 'MÉS QUE UN CLUB', 'ESTADI OLÍMPIC LLUÍS COMPANYS']
ti = 0
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    n = max(1, round((b - a).length / 14.0))
    for k in range(n):
        p = a.lerp(b, (k + 0.5) / n) - out * 0.05
        wall_text('Boards_T%d' % ti, BOARD_TEXT[ti % 3], (p.x, p.y, 0.3), ang, 0.5, '02_Bowl', letters_white)
        ti += 1

# the dugouts on the near (west) side, either side of the halfway line
bm = bmesh.new()
yb = R_WALL - 0.4
for x0, x1 in ((-15.0, -5.0), (5.0, 15.0)):
    face(bm, [(x0, yb - 2.2, 2.0), (x1, yb - 2.2, 2.0), (x1, yb, 2.2), (x0, yb, 2.2)], UPV, 1)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.2), (x0, yb, 2.2)], Vector((0, -1, 0)), 0)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.2, 0.0), (x, yb, 0.0), (x, yb, 2.2), (x, yb - 2.2, 2.0)], Vector((1 if x == x0 else -1, 0, 0)), 1)
new_obj('Dugouts', bm, '02_Bowl', [concrete_dark, dark_glass])

# ================================================================ the west stand: Gregotti's roof
def roof_under_z(y):
    t = (y - ROOF_Y0) / (ROOF_Y1 - ROOF_Y0)
    return ROOF_UNDER0 + (ROOF_UNDER1 - ROOF_UNDER0) * t


def roof_top_z(y):
    t = (y - ROOF_Y0) / (ROOF_Y1 - ROOF_Y0)
    return ROOF_TOP0 + (ROOF_TOP1 - ROOF_TOP0) * t


bm = bmesh.new()
NX, NY = 26, 8
for a in range(NX):
    x0, x1 = ROOF_X0 + (ROOF_X1 - ROOF_X0) * a / NX, ROOF_X0 + (ROOF_X1 - ROOF_X0) * (a + 1) / NX
    for b in range(NY):
        y0, y1 = ROOF_Y0 + (ROOF_Y1 - ROOF_Y0) * b / NY, ROOF_Y0 + (ROOF_Y1 - ROOF_Y0) * (b + 1) / NY
        face(bm, [(x0, y0, roof_under_z(y0)), (x1, y0, roof_under_z(y0)), (x1, y1, roof_under_z(y1)), (x0, y1, roof_under_z(y1))], -UPV, 0,
             [(x0 / 12.0, (y0 - ROOF_Y0) / 12.0), (x1 / 12.0, (y0 - ROOF_Y0) / 12.0), (x1 / 12.0, (y1 - ROOF_Y0) / 12.0), (x0 / 12.0, (y1 - ROOF_Y0) / 12.0)])
        face(bm, [(x0, y0, roof_top_z(y0)), (x1, y0, roof_top_z(y0)), (x1, y1, roof_top_z(y1)), (x0, y1, roof_top_z(y1))], UPV, 1)
# the front edge: the ends of the beams, white with openings
L = wall(bm, (ROOF_X0, ROOF_Y0), (ROOF_X1, ROOF_Y0), ROOF_UNDER0, ROOF_TOP0, Vector((0, -1, 0)), 2, 4.0, 0.0, 8.0)
for x in (ROOF_X0, ROOF_X1):
    face(bm, [(x, ROOF_Y0, roof_under_z(ROOF_Y0)), (x, ROOF_Y1, roof_under_z(ROOF_Y1)), (x, ROOF_Y1, roof_top_z(ROOF_Y1)), (x, ROOF_Y0, roof_top_z(ROOF_Y0))],
         Vector((1 if x > 0 else -1, 0, 0)), 3)
face(bm, [(ROOF_X0, ROOF_Y1, roof_under_z(ROOF_Y1)), (ROOF_X1, ROOF_Y1, roof_under_z(ROOF_Y1)), (ROOF_X1, ROOF_Y1, roof_top_z(ROOF_Y1)), (ROOF_X0, ROOF_Y1, roof_top_z(ROOF_Y1))], Vector((0, 1, 0)), 3)
# the floodlights under the front edge
for x in np.arange(ROOF_X0 + 2.0, ROOF_X1 - 1.0, 4.0):
    abox(bm, x - 0.5, x + 0.5, ROOF_Y0 + 1.0, ROOF_Y0 + 1.8, ROOF_UNDER0 - 0.7, ROOF_UNDER0, 4, True, True)
new_obj('Roof', bm, '04_Roof', [roof_under, roof_top, fascia, steel_white, lamp])

# the truss on top along the back half, the stays down to the facade, the
# three concrete piers it stands on
bm = bmesh.new()
TR_Y0, TR_Y1, TR_Z = 76.0, 86.0, 47.5
TR_ZB = roof_top_z(81.0)
xs = np.linspace(ROOF_X0 + 1.0, ROOF_X1 - 1.0, 27)
for y in (TR_Y0, TR_Y1):
    tube(bm, Vector((xs[0], y, TR_ZB + 0.3)), Vector((xs[-1], y, TR_ZB + 0.3)), 0.35, 0, 6)
tube(bm, Vector((xs[0], (TR_Y0 + TR_Y1) / 2, TR_Z)), Vector((xs[-1], (TR_Y0 + TR_Y1) / 2, TR_Z)), 0.45, 0, 6)
apex = lambda x: Vector((x, (TR_Y0 + TR_Y1) / 2, TR_Z))
for k, x in enumerate(xs):
    for y in (TR_Y0, TR_Y1):
        tube(bm, Vector((x, y, TR_ZB + 0.3)), apex(x), 0.2, 0, 5, trim=0.55)
        if k + 1 < len(xs):
            tube(bm, Vector((x, y, TR_ZB + 0.3)), apex(xs[k + 1]), 0.14, 0, 4, trim=0.55)
    tube(bm, Vector((x, TR_Y0, TR_ZB + 0.3)), Vector((x, TR_Y1, TR_ZB + 0.3)), 0.16, 0, 4, trim=0.45)
for x in xs[::2]:                                                             # the stays, out over the facade
    tube(bm, apex(x), Vector((x, FACADE_W + 5.0, CORNICE_Z + 0.5)), 0.22, 0, 6, trim=0.6)
    tube(bm, apex(x), Vector((x, ROOF_Y0 + 2.0, ROOF_TOP0 + 0.2)), 0.16, 0, 5, trim=0.6)
for x in (-56.0, 2.0, 60.0):
    abox(bm, x - 1.6, x + 1.6, 86.6, FACADE_W - 0.3, GROUND_Z, roof_top_z(88.0) + 0.6, 1, True, False)
new_obj('Roof_Truss', bm, '04_Roof', [steel_white, concrete])

# the press gallery behind the second ring, the royal box, the stair towers
bm = bmesh.new()
GY0 = UP_BACK + 0.5
wall(bm, (ROOF_X0 + 2.5, GY0), (ROOF_X1 - 2.5, GY0), PARAPET_Z, ROOF_UNDER1 - 3.0, Vector((0, -1, 0)), 0, 4.0, 0.0, 16.0)
face(bm, [(ROOF_X0 + 2.5, GY0, ROOF_UNDER1 - 3.0), (ROOF_X1 - 2.5, GY0, ROOF_UNDER1 - 3.0), (ROOF_X1 - 2.5, FACADE_W, ROOF_UNDER1 - 3.0), (ROOF_X0 + 2.5, FACADE_W, ROOF_UNDER1 - 3.0)], UPV, 1)
wall(bm, (ROOF_X0 + 2.5, GY0), (ROOF_X1 - 2.5, GY0), ROOF_UNDER1 - 3.0, ROOF_UNDER1 - 2.2, Vector((0, -1, 0)), 1, 6.0)
VY0 = UP['r'] + UP['depth'] * 13
abox(bm, -9.6, 9.6, VY0, GY0, UP['z'] + UP['rise'] * 12 + 0.4, PARAPET_Z + 3.4, 1, True, False)
wall(bm, (9.6, VY0 - 0.05), (-9.6, VY0 - 0.05), UP['z'] + UP['rise'] * 13, PARAPET_Z + 2.8, Vector((0, -1, 0)), 2, 4.0)
for x in (ROOF_X0 + 6.0, ROOF_X1 - 6.0):                                      # the white stair towers at the ends (outside, under the roof)
    abox(bm, x - 2.2, x + 2.2, FACADE_W - 0.2, FACADE_W + 4.0, GROUND_Z, ROOF_UNDER1 - 1.0, 3, True, False)
new_obj('Press_Gallery', bm, '04_Roof', [glass, concrete_light, dark_glass, white_paint])

# ================================================================ the facades
bm = bmesh.new()
cum = 0.0
nF = len(FOOT)
for i in range(nF):
    a, b = FOOT[i], FOOT[(i + 1) % nF]
    mid = (a + b) / 2
    L = (b - a).length
    if L < 1e-6:
        continue
    out = Vector(((b - a).y, -(b - a).x, 0)).normalized()
    if mid.x > 134.5 and abs(mid.y) <= GATE_HW + 0.1:
        cum += L
        continue                                    # the gate is its own block
    if abs(mid.y - FACADE_W) < 0.2 and ROOF_X0 < mid.x < ROOF_X1:
        mat, u_len, z1 = 1, 9.0, GROUND_Z + 16.5    # the main front, under the roof
    elif mid.y < -92 and abs(mid.x) < 65.1:
        mat, u_len, z1 = 2, 12.0, CORNICE_Z
    else:
        mat, u_len, z1 = 0, 12.0, CORNICE_Z
    wall(bm, a, b, GROUND_Z, z1, out, mat, 3.0, cum, u_len)
    wall(bm, a - out * 0.45, b - out * 0.45, PARAPET_Z, z1, -out, 3, 3.0)      # the inner face of the parapet
    face(bm, [(a.x, a.y, z1), (b.x, b.y, z1), (b.x - out.x * 0.45, b.y - out.y * 0.45, z1), (a.x - out.x * 0.45, a.y - out.y * 0.45, z1)], UPV, 3)
    cum += L
new_obj('Facade', bm, '05_Outside', [facade, main_front, east_front, stone])

# the gate houses on the east front, rising over the back of the stand
bm = bmesh.new()
for cx in PAVILIONS:
    abox(bm, cx - PAV_HW, cx + PAV_HW, PAV_Y1, PAV_Y0, GROUND_Z, PAV_TOP, 0, False, False)
    # a low hipped roof
    ridge = PAV_TOP + 2.4
    c0, c1 = Vector((cx - PAV_HW - 0.4, PAV_Y1 - 0.4, PAV_TOP)), Vector((cx + PAV_HW + 0.4, PAV_Y0 + 0.4, PAV_TOP))
    r0, r1 = Vector((cx - PAV_HW * 0.45, (PAV_Y0 + PAV_Y1) / 2, ridge)), Vector((cx + PAV_HW * 0.45, (PAV_Y0 + PAV_Y1) / 2, ridge))
    face(bm, [(c0.x, c0.y, PAV_TOP), (c1.x, c0.y, PAV_TOP), r1, r0], Vector((0, -1, 1)), 1)
    face(bm, [(c0.x, c1.y, PAV_TOP), (c1.x, c1.y, PAV_TOP), r1, r0], Vector((0, 1, 1)), 1)
    face(bm, [(c0.x, c0.y, PAV_TOP), (c0.x, c1.y, PAV_TOP), r0], Vector((-1, 0, 1)), 1)
    face(bm, [(c1.x, c0.y, PAV_TOP), (c1.x, c1.y, PAV_TOP), r1], Vector((1, 0, 1)), 1)
    abox(bm, cx - PAV_HW - 0.4, cx + PAV_HW + 0.4, PAV_Y1 - 0.4, PAV_Y0 + 0.4, PAV_TOP - 0.6, PAV_TOP, 2, False, True)
    # windows: two small ones to the pitch, three over the doors to the street
    for wy in (-2.8, 2.8):
        abox(bm, cx + wy - 0.5, cx + wy + 0.5, PAV_Y0 + 0.02, PAV_Y0 + 0.08, PAV_TOP - 3.4, PAV_TOP - 1.6, 3, False, False)
    for wy in (-3.6, 0.0, 3.6):
        abox(bm, cx + wy - 0.6, cx + wy + 0.6, PAV_Y1 - 0.08, PAV_Y1 - 0.02, PAV_TOP - 4.2, PAV_TOP - 2.0, 3, False, False)
        abox(bm, cx + wy - 1.0, cx + wy + 1.0, PAV_Y1 - 0.08, PAV_Y1 - 0.02, GROUND_Z, GROUND_Z + 4.0, 3, False, False)
    for wy in (-1.8, 1.8):                                                    # the little columns of the entrance
        cone(bm, (cx + wy, PAV_Y1 - 0.8), 0.35, 0.35, GROUND_Z, GROUND_Z + 5.0, 2, 8)
new_obj('Gate_Houses', bm, '05_Outside', [stone, tiles, stone_plain, dark_glass])

# the boards on frames over the gate houses, as on the photos of Barça's
# seasons there; the club's words in place of the sponsors
BB = [('FC BARCELONA', 2, 0), ('MÉS QUE UN CLUB', 1, 0), ('ESTADI OLÍMPIC', 0, 2), ('LLUÍS COMPANYS', 0, 1)]
bm = bmesh.new()
for cx, (text, bg, fg) in zip(PAVILIONS, BB):
    yb_ = PAV_Y0 - 1.2
    z0b, z1b = PAV_TOP + 1.2, PAV_TOP + 3.6
    face(bm, [(cx + 6.2, yb_, z0b), (cx - 6.2, yb_, z0b), (cx - 6.2, yb_, z1b), (cx + 6.2, yb_, z1b)], Vector((0, 1, 0)), bg)
    face(bm, [(cx + 6.2, yb_ - 0.15, z0b), (cx - 6.2, yb_ - 0.15, z0b), (cx - 6.2, yb_ - 0.15, z1b), (cx + 6.2, yb_ - 0.15, z1b)], Vector((0, -1, 0)), 3)
    for dx in (-4.5, 0.0, 4.5):
        tube(bm, Vector((cx + dx, yb_ - 0.3, PAV_TOP + 0.3)), Vector((cx + dx, yb_ - 0.3, z0b + 0.2)), 0.08, 3, 4)
        tube(bm, Vector((cx + dx, yb_ - 0.3, z0b + 0.2)), Vector((cx + dx, yb_ - 2.4, PAV_TOP + 0.6)), 0.06, 3, 4)
    wall_text('Billboard_T%d' % int(cx), text, (cx, yb_ + 0.03, z0b + 0.55), -math.pi / 2, 1.5, '05_Outside', [board_white, board_red, board_blue][fg])
new_obj('Billboards', bm, '05_Outside', [board_white, board_red, board_blue, steel_grey])

# ---------------------------------------------------------------- the Marathon Gate
bm = bmesh.new()
GZ0 = WALK_Z
GTOP = WALK_Z + 19.6
ARCH_W, ARCH_SPRING = 8.4, WALK_Z + 6.0       # the arch: 8.4 m wide, round head from 6 m over the walkway
ARCH_TOP = ARCH_SPRING + ARCH_W / 2


def arch_profile(n=12):
    pts = [(-ARCH_W / 2, GZ0), (-ARCH_W / 2, ARCH_SPRING)]
    for k in range(1, n):
        a = math.pi - math.pi * k / n
        pts.append((ARCH_W / 2 * math.cos(a), ARCH_SPRING + ARCH_W / 2 * math.sin(a)))
    pts += [(ARCH_W / 2, ARCH_SPRING), (ARCH_W / 2, GZ0)]
    return pts


def facade_with_arch(bm, x, y0, y1, z0, z1, mat, normal_x, tex_y0, tex_w, tex_z0, tex_h):
    # a flat front at x from y0 to y1 with the arch cut out of its middle,
    # made of quads between the arch and the edges; uv from the plane position
    prof = arch_profile()
    def uvw(y, z):
        u = (y - tex_y0) / tex_w
        if normal_x < 0:
            u = 1 - u
        return (u, (z - tex_z0) / tex_h)
    def q(pts):
        face(bm, [(x, y, z) for y, z in pts], Vector((normal_x, 0, 0)), mat, [uvw(y, z) for y, z in pts])
    uvq = lambda x_, y, z: uvw(y, z)
    # left and right of the arch, full height, in a grid of points
    grid_quad(bm, (x, y0), (x, -ARCH_W / 2), z0, z1, Vector((normal_x, 0, 0)), mat, uvq)
    grid_quad(bm, (x, ARCH_W / 2), (x, y1), z0, z1, Vector((normal_x, 0, 0)), mat, uvq)
    # over the arch: a fan from the arch's edge up to the top, cut in two heights
    for k in range(len(prof) - 1):
        (ya, za), (yb, zb) = prof[k], prof[k + 1]
        if abs(ya - yb) < 1e-6:
            continue
        zm = (max(za, zb) + z1) / 2
        q([(ya, za), (yb, zb), (yb, zm), (ya, zm)])
        q([(ya, zm), (yb, zm), (yb, z1), (ya, z1)])


# the middle bay with the arch, the wings either side; from the walkway (inside)
# and from the street (outside) the same height
facade_with_arch(bm, GATE_IN, -GATE_BAY, GATE_BAY, GZ0, GTOP - 0.15, 0, -1.0, -GATE_HW, 2 * GATE_HW, GZ0, 19.6)
for s in (-1, 1):
    ya, yb = sorted((s * GATE_BAY, s * GATE_HW))
    grid_quad(bm, (GATE_WING, ya), (GATE_WING, yb), GZ0, GTOP - 0.15, Vector((-1, 0, 0)), 0,
              lambda x_, y, z: (1 - (y + GATE_HW) / (2 * GATE_HW), (z - GZ0) / 19.6))
    grid_quad(bm, (GATE_IN, s * GATE_BAY), (GATE_WING, s * GATE_BAY), GZ0, GTOP - 0.15, Vector((0, s, 0)), 2)
    grid_quad(bm, (GATE_WING, s * GATE_HW), (GATE_X, s * GATE_HW), GROUND_Z, GTOP - 0.15, Vector((0, s, 0)), 2)
GOUT_Z0 = GROUND_Z
facade_with_arch(bm, GATE_X, -GATE_HW, GATE_HW, GOUT_Z0, GTOP - 0.15, 1, 1.0, -GATE_HW, 2 * GATE_HW, GOUT_Z0, GTOP - 0.15 - GOUT_Z0)
face(bm, [(GATE_IN, -GATE_BAY, GTOP), (GATE_X, -GATE_BAY, GTOP), (GATE_X, GATE_BAY, GTOP), (GATE_IN, GATE_BAY, GTOP)], UPV, 2)
for s in (-1, 1):
    ya, yb = sorted((s * GATE_BAY, s * GATE_HW))
    face(bm, [(GATE_WING, ya, GTOP), (GATE_X, ya, GTOP), (GATE_X, yb, GTOP), (GATE_WING, yb, GTOP)], UPV, 2)
# the vault of the passage under the arch
prof = arch_profile()
for k in range(len(prof) - 1):
    (ya, za), (yb, zb) = prof[k], prof[k + 1]
    mid = Vector((0, (ya + yb) / 2, (za + zb) / 2 - ARCH_SPRING))
    face(bm, [(GATE_IN, ya, za), (GATE_X, ya, za), (GATE_X, yb, zb), (GATE_IN, yb, zb)], Vector((0, -mid.y, -max(mid.z, 0))), 3)
face(bm, [(GATE_IN, -ARCH_W / 2, GZ0), (GATE_X, -ARCH_W / 2, GZ0), (GATE_X, ARCH_W / 2, GZ0), (GATE_IN, ARCH_W / 2, GZ0)], UPV, 3)
# cornices standing out a little
abox(bm, GATE_IN - 0.25, GATE_X + 0.25, -GATE_BAY - 0.25, GATE_BAY + 0.25, GTOP - 0.1, GTOP + 0.5, 2, True, True)
for s in (-1, 1):
    ya, yb = sorted((s * (GATE_BAY + 0.25), s * (GATE_HW + 0.25)))
    abox(bm, GATE_WING - 0.25, GATE_X + 0.25, ya, yb, GTOP - 0.1, GTOP + 0.5, 2, True, True)
# the clock on top: a stone frame with a curved head, the white face, volutes either side
CL_X, CL_Z, CL_R = GATE_IN + 1.2, GTOP + 3.4, 2.1
frame = []
for k in range(25):
    a = math.pi * k / 24
    frame.append((-(CL_R + 1.3) * math.cos(a), CL_Z + (CL_R + 1.5) * math.sin(a)))
cap = [(-(CL_R + 2.6), GTOP + 0.5)] + [(-(CL_R + 1.3), CL_Z - 0.4)] + frame + [(CL_R + 1.3, CL_Z - 0.4), (CL_R + 2.6, GTOP + 0.5)]
for x_, nx in ((CL_X - 0.6, -1.0), (CL_X + 1.6, 1.0)):
    for k in range(len(cap) - 1):
        (ya, za), (yb, zb) = cap[k], cap[k + 1]
        face(bm, [(x_, ya, GTOP + 0.5), (x_, yb, GTOP + 0.5), (x_, yb, zb), (x_, ya, za)], Vector((nx, 0, 0)), 2)
for k in range(len(frame) - 1):
    (ya, za), (yb, zb) = frame[k], frame[k + 1]
    face(bm, [(CL_X - 0.6, ya, za), (CL_X + 1.6, ya, za), (CL_X + 1.6, yb, zb), (CL_X - 0.6, yb, zb)], Vector((0, ya + yb, (za + zb) / 2 - CL_Z)), 2)
cl = []
for k in range(32):
    a = 2 * math.pi * k / 32
    cl.append((CL_R * math.cos(a), CL_Z + CL_R * math.sin(a)))
face(bm, [(CL_X - 0.62, y, z) for y, z in cl], Vector((-1, 0, 0)), 4, [(0.5 - 0.5 * (y / CL_R), 0.5 + 0.5 * (z - CL_Z) / CL_R) for y, z in cl])
# the round arms under the attic, between the two panels
AR = 1.15
ar = [(AR * math.cos(2 * math.pi * k / 24), WALK_Z + 12.0 + AR * math.sin(2 * math.pi * k / 24)) for k in range(24)]
face(bm, [(GATE_IN - 0.04, y, z) for y, z in ar], Vector((-1, 0, 0)), 5, [(0.5 - 0.5 * y / AR, 0.5 + 0.5 * (z - WALK_Z - 12.0) / AR) for y, z in ar])
# the frieze over the arch, outside
fz0, fz1 = GOUT_Z0 + ARCH_TOP - GZ0 + 0.6, GOUT_Z0 + ARCH_TOP - GZ0 + 3.6
face(bm, [(GATE_X + 0.04, -GATE_BAY + 0.3, fz0), (GATE_X + 0.04, GATE_BAY - 0.3, fz0), (GATE_X + 0.04, GATE_BAY - 0.3, fz1), (GATE_X + 0.04, -GATE_BAY + 0.3, fz1)],
     Vector((1, 0, 0)), 6, [(1, 0), (0, 0), (0, 1), (1, 1)])
# the dome over the back of the clock, seen from the street
for k in range(12):
    a0, a1 = math.pi * k / 12, math.pi * (k + 1) / 12
    for m_ in range(5):
        b0, b1 = math.pi / 2 * m_ / 5, math.pi / 2 * (m_ + 1) / 5
        R = 4.4
        P = lambda a, b: (GATE_X - 9.0 + R * math.cos(b) * math.sin(a) * 0.8, -R * math.cos(a) * math.cos(b), GTOP + 0.5 + R * math.sin(b) * 0.9)
        face(bm, [P(a0, b0), P(a1, b0), P(a1, b1), P(a0, b1)], Vector((math.sin((a0 + a1) / 2), -math.cos((a0 + a1) / 2), 0.5)), 2)
new_obj('Marathon_Gate', bm, '05_Outside', [gate_in, gate_out, stone_plain, stone, clock_mat, arms_mat, relief_mat])

# the two horsemen (Els Genets, Pau Gargallo, 1929) on their piers either side
# of the arch, facing the pitch: a horse at a walk and its rider, in bronze
bm = bmesh.new()
for s in (-1, 1):
    py = s * (ARCH_W / 2 + 1.6)
    px = GATE_IN - 0.9
    abox(bm, px - 0.8, px + 0.8, py - 0.9, py + 0.9, WALK_Z, WALK_Z + 6.6, 1, True, False)
    z0 = WALK_Z + 6.6
    K_ = 1.55                                                                   # a little over life size, as on the photo
    def bx(cx, cy, hx_, hy_, za, zb):
        abox(bm, px + (cx - px) * K_ - hx_ * K_, px + (cx - px) * K_ + hx_ * K_, py + (cy - py) * K_ - hy_ * K_, py + (cy - py) * K_ + hy_ * K_,
             z0 + (za - z0) * K_, z0 + (zb - z0) * K_, 0, True, True)
    def tb(a, b, r):
        a = Vector((px + (a.x - px) * K_, py + (a.y - py) * K_, z0 + (a.z - z0) * K_))
        b = Vector((px + (b.x - px) * K_, py + (b.y - py) * K_, z0 + (b.z - z0) * K_))
        tube(bm, a, b, r * K_, 0, 6)
    bx(px, py, 1.2, 0.36, z0 + 1.2, z0 + 2.1)                                   # the body
    for dx in (-0.9, 0.9):                                                      # the legs
        for dy in (-0.22, 0.22):
            bx(px + dx, py + dy, 0.1, 0.09, z0, z0 + 1.25)
    tb(Vector((px - 1.0, py, z0 + 1.9)), Vector((px - 1.6, py, z0 + 2.9)), 0.24)  # the neck
    bx(px - 1.85, py, 0.38, 0.16, z0 + 2.65, z0 + 3.0)                          # the head
    tb(Vector((px + 1.15, py, z0 + 1.9)), Vector((px + 1.5, py, z0 + 0.9)), 0.08)   # the tail
    bx(px + 0.05, py, 0.22, 0.2, z0 + 2.1, z0 + 3.0)                            # the rider
    for dy in (-0.32, 0.32):
        tb(Vector((px, py + dy * 0.6, z0 + 2.2)), Vector((px - 0.2, py + dy, z0 + 1.5)), 0.08)
    bx(px + 0.05, py, 0.15, 0.14, z0 + 3.0, z0 + 3.38)                          # the head
new_obj('Horsemen', bm, '05_Outside', [bronze, stone_plain])

# the Olympic cauldron (1992) on its column, east of the gate, and the
# platform on two legs on the rim of the north-east curve
bm = bmesh.new()
cxo, cyo = CAULDRON
abox(bm, cxo - 0.8, cxo + 0.8, cyo - 0.8, cyo + 0.8, GROUND_Z, 37.6, 0, True, False)
cone(bm, (cxo, cyo), 0.9, 2.7, 37.6, 39.6, 1, 16)
cone(bm, (cxo, cyo), 2.7, 2.75, 39.6, 39.8, 1, 16)
PL_A = math.radians(38.0)
pc = Vector((XS + (UP_BACK + 3.0) * math.cos(PL_A), -(UP_BACK + 3.0) * math.sin(PL_A), 0))
tang = Vector((-math.sin(PL_A), -math.cos(PL_A), 0))
nrm = Vector((math.cos(PL_A), -math.sin(PL_A), 0))
box(bm, pc, tang, 7.5, nrm, 1.6, 30.2, 31.0, 0)
for s in (-4.5, 4.5):
    p = pc + tang * s
    box(bm, p, tang, 0.6, nrm, 0.6, PARAPET_Z, 30.2, 0)
for s in (-7.3, 7.3):
    p = pc + tang * s
    tube(bm, p + Vector((0, 0, 31.0)), p + Vector((0, 0, 32.1)), 0.05, 2, 4)
tube(bm, pc - tang * 7.3 + Vector((0, 0, 32.1)), pc + tang * 7.3 + Vector((0, 0, 32.1)), 0.05, 2, 4)
box(bm, pc - tang * 5.8, tang, 1.2, nrm, 1.2, 31.0, 33.2, 0)
new_obj('Cauldron', bm, '05_Outside', [concrete_light, cauldron_black, steel_white])

# the flagpoles along the rim of both ends
bm = bmesh.new()
for cxs, a0, a1 in ((XS, -82, -50), (XS, 18, 80), (-XS, 100, 172), (-XS, 202, 260)):
    for a in np.linspace(math.radians(a0), math.radians(a1), 6):
        p = Vector((cxs + (UP_BACK + 1.5) * math.cos(a), (UP_BACK + 1.5) * math.sin(a), 0))
        tube(bm, Vector((p.x, p.y, PARAPET_Z)), Vector((p.x, p.y, PARAPET_Z + 13.0)), 0.09, 0, 5)
new_obj('Flagpoles', bm, '05_Outside', [white_paint])

# the five floodlight masts behind the east stand: a grey pole and a frame of
# lamps leaning towards the pitch
bm = bmesh.new()
for mx, my in MASTS:
    tube(bm, Vector((mx, my, GROUND_Z)), Vector((mx, my, MAST_TOP - 2.0)), 0.55, 0, 10)
    to = (Vector((0, 0, 0)) - Vector((mx, my, 0))).normalized()
    side_ = Vector((-to.y, to.x, 0))
    c = Vector((mx, my, MAST_TOP)) + to * 0.6
    tilt = to * 0.8
    for row in range(4):
        z = MAST_TOP - 2.4 + row * 1.35
        for col in range(6):
            p = c + side_ * (col - 2.5) * 1.1 + Vector((0, 0, z - MAST_TOP)) - tilt * (row - 1.5) * 0.3
            box(bm, p, side_, 0.42, to, 0.3, p.z - 0.42, p.z + 0.42, 1)
    for row in (0, 3):
        z = MAST_TOP - 2.4 + row * 1.35 - 0.6
        tube(bm, c - side_ * 3.4 + Vector((0, 0, z - MAST_TOP)), c + side_ * 3.4 + Vector((0, 0, z - MAST_TOP)), 0.1, 0, 4)
    for s in (-1, 1):
        tube(bm, c + side_ * 3.4 * s + Vector((0, 0, -3.0)), c + side_ * 3.4 * s + Vector((0, 0, 2.6)), 0.1, 0, 4)
new_obj('Masts', bm, '05_Outside', [steel_grey, lamp])

# small light poles over the corners of the south end (none by the boards)
bm = bmesh.new()
for a in (130, 230):
    r_ = math.radians(a)
    p = Vector((-XS + (UP_BACK + 2.5) * math.cos(r_), (UP_BACK + 2.5) * math.sin(r_), 0))
    tube(bm, Vector((p.x, p.y, PARAPET_Z)), Vector((p.x, p.y, PARAPET_Z + 9.0)), 0.18, 0, 6)
    box(bm, Vector((p.x, p.y, 0)), (1, 0), 0.9, (0, 1), 0.5, PARAPET_Z + 9.0, PARAPET_Z + 9.9, 1)
new_obj('Light_Poles', bm, '05_Outside', [steel_grey, lamp])

# ---------------------------------------------------------------- the west front: the arcade, the dome, the charioteers, the tower
bm = bmesh.new()
MB_Y = FACADE_W + 7.5            # the middle of the main front stands out, the dome on it clear of the roof
MB_Z1 = GROUND_Z + 16.5
wall(bm, (-22.0, MB_Y), (22.0, MB_Y), GROUND_Z, MB_Z1, Vector((0, 1, 0)), 0, 3.0, 0.0, 9.0)
for x in (-22.0, 22.0):
    wall(bm, (x, FACADE_W), (x, MB_Y), GROUND_Z, MB_Z1, Vector((1 if x > 0 else -1, 0, 0)), 1, 3.0)
abox(bm, -22.6, 22.6, FACADE_W + 0.2, MB_Y + 0.6, MB_Z1, MB_Z1 + 0.8, 1, True, True)
face(bm, [(-22.0, FACADE_W + 0.2, MB_Z1), (22.0, FACADE_W + 0.2, MB_Z1), (22.0, MB_Y, MB_Z1), (-22.0, MB_Y, MB_Z1)], UPV, 1)
# the dome: an octagonal drum with arched windows, the dome, the lantern
DC = Vector((0.0, FACADE_W + 4.2, 0))
cone(bm, (DC.x, DC.y), 3.6, 3.6, MB_Z1 + 0.8, MB_Z1 + 2.0, 1, 8)
cone(bm, (DC.x, DC.y), 3.2, 3.2, MB_Z1 + 2.0, MB_Z1 + 6.2, 2, 8, False)
cone(bm, (DC.x, DC.y), 3.6, 3.6, MB_Z1 + 6.2, MB_Z1 + 6.9, 1, 8)
for k in range(5):
    za, zb = MB_Z1 + 6.9 + 3.0 * math.sin(math.pi / 2 * k / 5), MB_Z1 + 6.9 + 3.0 * math.sin(math.pi / 2 * (k + 1) / 5)
    cone(bm, (DC.x, DC.y), 3.3 * math.cos(math.pi / 2 * k / 5) + 0.05, 3.3 * math.cos(math.pi / 2 * (k + 1) / 5) + 0.05, za, zb, 1, 8, False)
cone(bm, (DC.x, DC.y), 1.1, 1.1, MB_Z1 + 9.9, MB_Z1 + 10.8, 1, 8)
cone(bm, (DC.x, DC.y), 0.25, 0.08, MB_Z1 + 10.8, MB_Z1 + 13.2, 1, 8)
# Gargallo's charioteers either side of the dome: two rearing horses and the driver
for s in (-1, 1):
    cx_ = s * 7.0
    Y0 = FACADE_W + 3.0
    abox(bm, cx_ - 2.4, cx_ + 2.4, Y0 - 0.6, Y0 + 2.4, MB_Z1 + 0.8, MB_Z1 + 1.6, 1, True, False)
    for dx in (-0.9, 0.9):
        x = cx_ + dx
        tube(bm, Vector((x, Y0 + 0.6, MB_Z1 + 1.6)), Vector((x, Y0 + 1.2, MB_Z1 + 3.6)), 0.38, 3, 6)       # the body, rearing
        tube(bm, Vector((x, Y0 + 1.2, MB_Z1 + 3.4)), Vector((x, Y0 + 1.9, MB_Z1 + 4.6)), 0.2, 3, 6)       # the neck and head
        for dy in (-0.25, 0.25):
            tube(bm, Vector((x + dy, Y0 + 1.2, MB_Z1 + 3.0)), Vector((x + dy, Y0 + 1.9, MB_Z1 + 2.8)), 0.07, 3, 4)   # the forelegs up
            tube(bm, Vector((x + dy, Y0 + 0.5, MB_Z1 + 1.8)), Vector((x + dy, Y0 + 0.5, MB_Z1 + 1.6)), 0.08, 3, 4)
    tube(bm, Vector((cx_, Y0 + 0.2, MB_Z1 + 1.6)), Vector((cx_, Y0 + 0.2, MB_Z1 + 3.4)), 0.22, 3, 6)          # the driver
    cone(bm, (cx_, Y0 + 0.2), 0.16, 0.14, MB_Z1 + 3.4, MB_Z1 + 3.8, 3, 6)
# the tower: a square shaft, the belfry with round windows and a cornice, the lantern of columns
T0, T1 = Vector((TOWER_X - 4.5, TOWER_Y0, 0)), Vector((TOWER_X + 4.5, TOWER_Y1, 0))
TZ1 = GROUND_Z + 38.5
for (a, b, n_) in (((T0.x, T0.y), (T1.x, T0.y), Vector((0, -1, 0))), ((T1.x, T0.y), (T1.x, T1.y), Vector((1, 0, 0))),
                   ((T1.x, T1.y), (T0.x, T1.y), Vector((0, 1, 0))), ((T0.x, T1.y), (T0.x, T0.y), Vector((-1, 0, 0)))):
    wall(bm, a, b, GROUND_Z, TZ1, n_, 4, 4.0, 0.0, 9.0)
abox(bm, T0.x - 0.4, T1.x + 0.4, T0.y - 0.4, T1.y + 0.4, TZ1, TZ1 + 0.7, 1, True, True)
abox(bm, T0.x + 0.6, T1.x - 0.6, T0.y + 0.6, T1.y - 0.6, TZ1 + 0.7, TZ1 + 6.2, 1, False, False)
for (yy_, n_) in ((T0.y + 0.58, -1), (T1.y - 0.58, 1)):
    ow = [(TOWER_X + 0.9 * math.cos(2 * math.pi * k / 16), TZ1 + 4.2 + 0.9 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    face(bm, [(x, yy_ + n_ * 0.03, z) for x, z in ow], Vector((0, n_, 0)), 5)
    abox(bm, TOWER_X - 0.6, TOWER_X + 0.6, yy_ + n_ * 0.01, yy_ + n_ * 0.05, TZ1 + 1.2, TZ1 + 2.9, 5, False, False)
abox(bm, T0.x + 0.2, T1.x - 0.2, T0.y + 0.2, T1.y - 0.2, TZ1 + 6.2, TZ1 + 7.0, 1, True, True)
abox(bm, T0.x + 2.0, T1.x - 2.0, T0.y + 2.0, T1.y - 2.0, TZ1 + 7.0, TZ1 + 9.0, 1, True, False)
LC = Vector((TOWER_X, (TOWER_Y0 + TOWER_Y1) / 2, 0))
cone(bm, (LC.x, LC.y), 2.0, 2.0, TZ1 + 9.0, TZ1 + 9.4, 1, 12)
for k in range(8):
    a = 2 * math.pi * k / 8
    p = LC + Vector((1.6 * math.cos(a), 1.6 * math.sin(a), 0))
    tube(bm, Vector((p.x, p.y, TZ1 + 9.4)), Vector((p.x, p.y, TZ1 + 12.0)), 0.16, 1, 6)
cone(bm, (LC.x, LC.y), 2.0, 2.0, TZ1 + 12.0, TZ1 + 12.6, 1, 12)
cone(bm, (LC.x, LC.y), 1.7, 0.4, TZ1 + 12.6, TZ1 + 13.6, 1, 12)
new_obj('West_Front', bm, '05_Outside', [main_front, stone_plain, dark_glass, bronze, tower_side, dark_glass])

# ---------------------------------------------------------------- the two boards over the south end
# as on the photos from the pitch and from the second ring: left of the middle
# (east) the screen in a grey steel frame on a cream concrete beam, the beam
# on two round concrete columns behind the top row, a ladder on its right, a
# loudspeaker under the beam; in the middle, lower, a plain black board with a
# white clock in its left top corner on a black steel frame, a red board
# along the rim under it
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
cream = principled('M_ConcreteCream', (0.80, 0.76, 0.67), 0.85)


def black_board_tex(W=1024, H=512, SS=2):
    # the middle board: black, the clock's white marks and hands at its top left
    w, h = W * SS, H * SS
    yy, xx = np.mgrid[0:h, 0:w].astype('f')
    img = np.full((h, w), 0.0, 'f')
    cx, cy, R = 0.135 * w, 0.24 * h, 0.19 * h

    def seg(x0, y0, x1, y1, r):
        dx, dy = x1 - x0, y1 - y0
        t = np.clip(((xx - x0) * dx + (yy - y0) * dy) / (dx * dx + dy * dy), 0, 1)
        return np.hypot(xx - x0 - t * dx, yy - y0 - t * dy) < r
    on = np.zeros((h, w), bool)
    for i in range(12):
        a = i / 12 * 2 * math.pi
        r0 = R * (0.70 if i % 3 == 0 else 0.78)
        on |= seg(cx + math.sin(a) * r0, cy - math.cos(a) * r0, cx + math.sin(a) * R, cy - math.cos(a) * R, R * (0.065 if i % 3 == 0 else 0.05))
    for frac, ln, wd in ((10.4 / 12, 0.52, 0.075), (22 / 60, 0.82, 0.055)):      # twenty past ten
        a = frac * 2 * math.pi
        on |= seg(cx - math.sin(a) * R * 0.12, cy + math.cos(a) * R * 0.12, cx + math.sin(a) * R * ln, cy - math.cos(a) * R * ln, R * wd)
    img[on] = 1.0
    img = img.reshape(H, SS, W, SS).mean((1, 3))
    img = np.maximum(img, 0.006)
    return np.repeat(img[::-1, :, None], 3, 2)        # row 0 at the bottom


board_black = image_material('M_BlackBoard', painted('mj_blackboard', black_board_tex()), 0.35)
SCREEN_FACES = []
bm = bmesh.new()
FACE_R = UP_BACK + 0.5 + 1.2                         # the faces, over the back of the top row, from the curve's centre
CC = Vector((-XS, 0.0, 0.0))

# the screen: turned to face the curve's centre, 17 degrees east of the middle
SCR_W, SCR_H = 11.0, 7.6
SCR_FR = 0.28                                       # the frame round the picture
BEAM_Z0, BEAM_H = PARAPET_Z + 2.2, 0.85
SCR_Z0 = BEAM_Z0 + BEAM_H + SCR_FR
PHI = math.radians(17.0)
O = Vector((-math.cos(PHI), -math.sin(PHI), 0.0))   # outwards, away from the pitch
T = Vector((-math.sin(PHI), math.cos(PHI), 0.0))    # left to right as seen from the pitch
F = CC + O * FACE_R
P = lambda u, d, z=0.0: F + T * u + O * d + Vector((0, 0, z))
ax, ay = (T.x, T.y), (O.x, O.y)
box(bm, P(0, 0.45).xy, ax, SCR_W / 2 + SCR_FR, ay, 0.45, SCR_Z0 - SCR_FR, SCR_Z0 + SCR_H + SCR_FR, 1)
box(bm, P(0, 0.9).xy, ax, SCR_W / 2 + SCR_FR + 0.08, ay, 1.0, BEAM_Z0 + 0.25, BEAM_Z0 + BEAM_H, 2)
box(bm, P(0, 1.05).xy, ax, SCR_W / 2 + SCR_FR, ay, 0.8, BEAM_Z0, BEAM_Z0 + 0.25, 2)
for u_ in (-0.155 * SCR_W, 0.145 * SCR_W):
    q = P(u_, 1.0)
    cone(bm, (q.x, q.y), 0.42, 0.42, PARAPET_Z - 1.45, BEAM_Z0, 2, 16)
box(bm, P(1.9, 0.35).xy, ax, 0.22, ay, 0.18, BEAM_Z0 - 0.4, BEAM_Z0, 1)          # the loudspeaker
lu = 0.33 * SCR_W                                                                 # the ladder
for s_ in (-0.25, 0.25):
    tube(bm, P(lu + s_, 2.2, PARAPET_Z - 1.45), P(lu + s_, 2.2, BEAM_Z0), 0.035, 3, 4)
for z_ in np.arange(PARAPET_Z - 1.1, BEAM_Z0, 0.35):
    tube(bm, P(lu - 0.25, 2.2, z_), P(lu + 0.25, 2.2, z_), 0.02, 3, 4)
for u_ in np.arange(-SCR_W / 2, SCR_W / 2 + 0.01, 1.83):                          # the rail behind the top row
    tube(bm, P(u_, 1.8, PARAPET_Z - 1.45), P(u_, 1.8, PARAPET_Z), 0.03, 3, 4)
tube(bm, P(-SCR_W / 2, 1.8, PARAPET_Z), P(SCR_W / 2, 1.8, PARAPET_Z), 0.035, 3, 4)
fb = bmesh.new()
face(fb, [P(-SCR_W / 2, -0.02, SCR_Z0), P(SCR_W / 2, -0.02, SCR_Z0), P(SCR_W / 2, -0.02, SCR_Z0 + SCR_H), P(-SCR_W / 2, -0.02, SCR_Z0 + SCR_H)],
     -O, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])                                     # u left to right as seen from the pitch
SCREEN_FACES.append(new_obj('ScreenFace_0', fb, '02_Bowl', [live]))

# the black board in the middle, lower, straight over the curve's end
BB_W, BB_H, BB_FR = 13.0, 6.4, 0.22
BB_Z0 = PARAPET_Z + 1.6
xb = -(XS + FACE_R)
box(bm, (xb - 0.4, 0.0), (0, 1), BB_W / 2 + BB_FR, (1, 0), 0.4, BB_Z0 - BB_FR, BB_Z0 + BB_H + BB_FR, 4)
face(bm, [(xb + 0.01, -BB_W / 2, BB_Z0), (xb + 0.01, BB_W / 2, BB_Z0), (xb + 0.01, BB_W / 2, BB_Z0 + BB_H), (xb + 0.01, -BB_W / 2, BB_Z0 + BB_H)],
     Vector((1, 0, 0)), 5, [(0, 0), (1, 0), (1, 1), (0, 1)])                     # u left to right as seen from the pitch (east, -y, on the left)
# its legs from the walk behind the top row, braced, and the frame they carry
for yl in (-BB_W / 2 + 0.6, -BB_W / 6, BB_W / 6, BB_W / 2 - 0.6):
    for dx in (0.5, 1.9):
        tube(bm, Vector((xb - dx, yl, PARAPET_Z - 1.45)), Vector((xb - dx, yl, BB_Z0 - BB_FR)), 0.11, 4, 6)
    tube(bm, Vector((xb - 0.5, yl, PARAPET_Z - 1.2)), Vector((xb - 1.9, yl, BB_Z0 - BB_FR)), 0.05, 4, 4)
tube(bm, Vector((xb - 0.5, -BB_W / 2, BB_Z0 - BB_FR - 0.1)), Vector((xb - 0.5, BB_W / 2, BB_Z0 - BB_FR - 0.1)), 0.1, 4, 4)
# the red board along the rim under it
box(bm, (xb + 0.15, 0.0), (0, 1), 0.29 * BB_W, (1, 0), 0.06, PARAPET_Z + 0.15, BB_Z0 - BB_FR - 0.25, 6)
new_obj('Scoreboards', bm, '02_Bowl', [portal, steel_grey, cream, steel_white, steel_dark, board_black, board_red])

# ================================================================ outside: the ground, the esplanade, the columns, trees, the hill
bm = bmesh.new()
STEP = 5.0
for gx in np.arange(-185.0, 190.0, STEP):
    for gy in np.arange(-126.0, 141.0, STEP):
        c4 = [(gx, gy), (gx + STEP, gy), (gx + STEP, gy + STEP), (gx, gy + STEP)]
        if all(inside_foot(x, y) for x, y in c4):
            continue
        west = gy >= ESPLANADE_Y
        z = ESPLANADE_Z if west else GROUND_Z
        near = any(inside_foot(x + dx, y + dy) for x, y in c4 for dx, dy in ((-18, 0), (18, 0), (0, -18), (0, 18)))
        road = (150.0 <= gx < 165.0) or (-126.0 <= gy < -116.0 and not west)
        mat = 1 if road else (0 if near or west else 2)
        uvs = [(x / 8.0, y / 8.0) for x, y in c4]
        face(bm, [(x, y, z) for x, y in c4], UPV, mat, uvs)
# the stone wall where the esplanade drops away to the west, and the steps down
wall(bm, (-185.0, ESPLANADE_Y), (190.0, ESPLANADE_Y), ESPLANADE_Z, GROUND_Z, Vector((0, 1, 0)), 3, 5.0)
for k in range(10):
    z = GROUND_Z - (GROUND_Z - ESPLANADE_Z) * (k + 1) / 10
    y = ESPLANADE_Y + k * 0.42
    face(bm, [(-30.0, y, z), (30.0, y, z), (30.0, y + 0.42, z), (-30.0, y + 0.42, z)], UPV, 0, [(-30 / 8, y / 8), (30 / 8, y / 8), (30 / 8, (y + .42) / 8), (-30 / 8, (y + .42) / 8)])
new_obj('Ground', bm, '05_Outside', [paving, asphalt, lawn, stone])

# the yellow columns of the Olympic ring along the east promenade and on the esplanade
bm = bmesh.new()
for x, y, z in ((-33.0, -106.0, GROUND_Z), (0.0, -106.0, GROUND_Z), (33.0, -106.0, GROUND_Z),
                (-28.0, 118.0, ESPLANADE_Z), (28.0, 118.0, ESPLANADE_Z)):
    abox(bm, x - 1.2, x + 1.2, y - 1.2, y + 1.2, z, z + 3.0, 1, True, False)
    res = bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.7, radius2=0.7, depth=19.0)
    bmesh.ops.translate(bm, vec=Vector((x, y, z + 3.0 + 9.5)), verts=res['verts'])
    uvl = bm.loops.layers.uv.verify()
    for f_ in {f_ for v in res['verts'] for f_ in v.link_faces}:
        f_.material_index = 0
        for l in f_.loops:
            l[uvl].uv = (math.atan2(l.vert.co.y - y, l.vert.co.x - x) / math.pi, (l.vert.co.z - z - 3.0) / 19.0)
new_obj('Columns', bm, '05_Outside', [gold_col, stone_plain])

# trees: umbrella pines and plane trees round the stadium
bm = bmesh.new()
trng = random.Random(7)
tree_spots = []
for x in np.arange(-150.0, 150.0, 11.0):
    tree_spots.append((x + trng.uniform(-3, 3), -111.5 + trng.uniform(-1.5, 1.5)))      # along the Passeig Olímpic
for y in np.arange(-90.0, 95.0, 12.0):
    if abs(y) > 18:
        tree_spots.append((168.0 + trng.uniform(-3, 3), y + trng.uniform(-3, 3)))       # past the Avinguda de l'Estadi
    tree_spots.append((-160.0 + trng.uniform(-4, 4), y + trng.uniform(-3, 3)))          # south of the stadium
for x in np.arange(170.0, 188.0, 8.0):
    for y in (-10.0, 0.0, 10.0):
        tree_spots.append((x + trng.uniform(-2, 2), y + trng.uniform(-2, 2)))           # seen through the arch
for x, y in tree_spots:
    if inside_foot(x, y):
        continue
    z = ESPLANADE_Z if y >= ESPLANADE_Y else GROUND_Z
    h = trng.uniform(9.0, 14.0)
    tube(bm, Vector((x, y, z)), Vector((x, y, z + h * 0.7)), 0.3, 0, 5)
    res = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    rx = trng.uniform(3.5, 5.5)
    bmesh.ops.scale(bm, vec=Vector((rx, rx * trng.uniform(0.8, 1.1), h * 0.28)), verts=res['verts'])
    bmesh.ops.translate(bm, vec=Vector((x, y, z + h * 0.78)), verts=res['verts'])
    uvl = bm.loops.layers.uv.verify()
    for f_ in {f_ for v in res['verts'] for f_ in v.link_faces}:
        f_.material_index = 1
        for l in f_.loops:
            l[uvl].uv = (l.vert.co.x / 6.0, (l.vert.co.y + l.vert.co.z) / 6.0)
new_obj('Trees', bm, '05_Outside', [trunk, foliage])

# the Montjuïc hill east of the stadium: a slope covered in pines, rising to the
# south-east, as seen over the east stand on every photo from the west stand
bm = bmesh.new()
HX = np.arange(-240.0, 216.0, 6.0)
HY = np.arange(-130.0, -250.0, -6.0)
hn = vnoise(len(HX), len(HY), 3, 3) * 0.8 + vnoise(len(HX), len(HY), 1, 1) * 0.25


def hill_z(ix, iy):
    x, y = HX[ix], HY[iy]
    t = min(1.0, (-130.0 - y) / 110.0)
    top = 47.0 + 10.0 * min(1.0, max(0.0, (60.0 - x) / 220.0))
    end = min(1.0, max(0.0, (216.0 - x) / 50.0)) * min(1.0, max(0.0, (x + 240.0) / 50.0))
    return GROUND_Z + 3.0 + (top - GROUND_Z) * (t ** 0.9) * end + 1.4 * hn[ix, iy] * (0.4 + t)


for ix in range(len(HX) - 1):
    for iy in range(len(HY) - 1):
        q = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
        face(bm, [(HX[a], HY[b], hill_z(a, b)) for a, b in q], UPV, 0, [(HX[a] / 14.0, HY[b] / 14.0) for a, b in q])
backdrop = new_obj('StadiumBackdrop', bm, '06_Backdrop', [foliage])

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('SAVED', OUT_BLEND)

# ================================================================ the sun and the sky
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.36, 0.55, 0.95, 1)
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.75
ld = D.lights.new('Sun', 'SUN')
ld.energy = 5.0
ld.color = (1.0, 0.96, 0.90)
ld.angle = math.radians(0.6)
sun = D.objects.new('Sun', ld)
sc.collection.objects.link(sun)
az, el = math.radians(SUN_AZ), math.radians(SUN_EL)
to_sun = Vector((math.cos(az) * math.cos(el), -math.sin(az) * math.cos(el), math.sin(el)))     # x north, y west
sun.rotation_euler = (-to_sun).to_track_quat('-Z', 'Y').to_euler()

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
    for o in (grass, floor):
        o.hide_render = False
    preview('match', (0, 71.2, 21.4), (0, -16.2, 0), 36, clip=30.0)
    preview('photo1', (115.4, -1.5, 20.6), (-60.0, 8.0, -6.0), 62, res=(1280, 960))
    preview('photo3', (14.0, -4.0, 1.6), (128.0, 0.0, 21.0), 30, res=(1280, 853))
    preview('east', (-24.0, 76.0, 17.5), (55.0, -70.0, 12.0), 50)
    preview('air', (-230.0, 210.0, 170.0), (0.0, 0.0, 10.0), 32)
    sys.exit(0)

# ================================================================ game export: the sun baked in
for m in D.materials:                    # nothing glows during the bakes: the LEDs and screens get their own light after
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
grass_light = bake_lightmap(grass, 640, 442)
grass.hide_render = True                 # the floor in full sun where the pitch lies on it
floor_light = bake_lightmap(floor, 920, 497)
grass.hide_render = False
inner = grass_light[int(442 * 0.25):int(442 * 0.75), int(640 * 0.25):int(640 * 0.75)]
lum = float((inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1).mean())
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
    def dot(cx, cy, r):
        nonlocal d
        d = np.minimum(d, np.maximum(np.hypot(X - cx, Y - cy) - r, 0) + LINE / 2 * 0)
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


def grass_albedo(X, Y, H, W, seed_scale=1.0):
    # the Montjuïc pitch in the sun: broad stripes across it (5.25 m), a
    # fainter lengthwise checker, wear in the goalmouths and the centre
    bands_x = np.tanh(np.sin(np.pi * X / (PW / 20)) * 6)
    bands_y = np.tanh(np.sin(np.pi * Y / (PL / 10)) * 4)
    fine = rng.normal(0, 1, (H, W)).astype('f')
    shade = (1 + 0.11 * bands_x + 0.035 * bands_y + 0.05 * vnoise(H, W, 400, 400) + 0.03 * vnoise(H, W, 48, 48)
             + 0.04 * vnoise(H, W, 14, 1) * (0.6 + 0.4 * bands_x) + 0.035 * fine)
    g = np.array((0.068, 0.170, 0.040), 'f') * shade[..., None]
    g[..., 0] *= 1 + 0.10 * vnoise(H, W, 300, 300)
    wear = sum(np.exp(-(((X - gx) / 3.0) ** 2 + (Y / 5.0) ** 2)) for gx in (-(hx - 3.0), hx - 3.0)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
    wear = (0.18 * wear * (0.55 + 0.45 * np.clip(vnoise(H, W, 36, 36) + 0.5, 0, 1)))[..., None]
    return g * (1 - wear) + np.array((0.14, 0.18, 0.07), 'f') * wear


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


# the pitch picture: 4096 x 2824 over 116 x 80 m
H, W = 2824, 4096
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * PITCH_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * PITCH_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = grass_albedo(X, Y, H, W)
# beyond the run-off the artificial grass of the track and, behind the goals, the cloths
turf_c = np.array((0.058, 0.165, 0.048), 'f')
track = (np.abs(Y) > R_KERB) | (np.abs(X) > PW / 2 + 1.0)
alb = np.where(track[..., None], turf_c * (1 + 0.04 * rng.normal(0, 1, (H, W)).astype('f'))[..., None], alb)
CLOTH = asset_pixels('cloth.png')
CL_H, CL_W = CLOTH.shape[:2]
CLOTH_X0, CLOTH_R, CLOTH_D, CLOTH_W = 53.5, 37.0, 25.7, 71.0


def cloth_over(alb, X, Y):
    # the two cloths: the picture's top edge along the pitch end, its middle
    # on the axis, the crest's top towards the stand; cut to the curve
    for s in (-1, 1):
        d = s * X - CLOTH_X0                       # metres out from the edge at the pitch
        inside = (d >= 0) & ((np.abs(X) - XS) ** 2 + Y ** 2 <= (CLOTH_R + 0.25 * np.sin(Y * 1.7) + 0.2 * np.sin(Y * 4.3)) ** 2)
        ys, xs_ = np.nonzero(inside)
        if not len(ys):
            continue
        u = s * Y[ys, xs_] / CLOTH_W + 0.5         # turned, not mirrored: seen from the stand the senyera is on the left
        u = np.clip(u * CL_W, 0, CL_W - 1).astype(int)
        v = np.clip(d[ys, xs_] / CLOTH_D * CL_H, 0, CL_H - 1).astype(int)
        alb[ys, xs_] = CLOTH[v, u, :3] * 0.92
    return alb


alb = cloth_over(alb, X, Y)
cov = line_alpha(X, Y, 2 * PITCH_X / W)[..., None] * np.clip(0.85 + 0.1 * vnoise(H, W, 90, 90), 0.7, 1)[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
pitch_img = finish('mj_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: 3072 x 1659 over the whole ground inside the stands
H, W = 1659, 3072
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = np.empty((H, W, 3), 'f')
alb[:] = turf_c
alb *= (1 + 0.04 * rng.normal(0, 1, (H, W)).astype('f') + 0.03 * vnoise(H, W, 40, 40))[..., None]
# the seams of the rolls of grass round the track
rr = np.where(np.abs(X) <= XS, np.abs(Y), np.hypot(np.abs(X) - XS, Y))
seam = (np.abs(((rr - R_KERB) / 4.1) % 1 - 0.5) > 0.47) & (rr > R_KERB) & (rr < R_TRACK + 2)
alb[seam] *= 0.88
infield = rr < R_KERB
alb = np.where(infield[..., None], grass_albedo(X, Y, H, W), alb)
alb = cloth_over(alb, X, Y)
cov = line_alpha(X, Y, 2 * FLOOR_X / W)[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
floor_img = finish('mj_floor', alb, floor_light, H, W)
del alb, X, Y, rr
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

# text -> mesh
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in D.objects if o.type == 'FONT']:
    me = D.meshes.new_from_object(o.evaluated_get(dg))
    nobj = D.objects.new(o.name + '_mesh', me)
    nobj.matrix_world = o.matrix_world.copy()
    o.users_collection[0].objects.link(nobj)
    D.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

skip = ('Pitch_Lines', 'StadiumGoals', 'ScreenFace_', 'StadiumBackdrop')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, backdrop]:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    else:
        o.data.uv_layers[0].name = 'UVMap'
select_only(SCREEN_FACES, SCREEN_FACES[0])
bpy.ops.object.join()
screens = SCREEN_FACES[0]
screens.name = 'StadiumScreens'
scc = screens.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
scc.data.foreach_set('color', [1.0 / GAIN, 1.0 / GAIN, 1.0 / GAIN, 1.0] * len(scc.data))
screens.data.color_attributes.active_color = scc
screens.data.color_attributes.render_color_index = screens.data.color_attributes.find('Col')
screens.data.uv_layers[0].name = 'UVMap'
target = grass
select_only(export, target)
bpy.ops.object.join()
target.name = 'EstadiOlimpic'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor', 'M_LEDBlue', 'M_Lettering'}


def bake_light(obj, samples=96):
    # the sun into the vertex colours, at the pitch's exposure; the pitch and
    # the floor carry their own light in their pictures, the LEDs light themselves
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
bake_light(backdrop, 48)
gc = goals.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
gc.data.foreach_set('color', [0.45, 0.45, 0.45, 1.0] * len(gc.data))
goals.data.color_attributes.active_color = gc
goals.data.color_attributes.render_color_index = goals.data.color_attributes.find('Col')
for m in D.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0

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
