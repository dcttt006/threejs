# Builds the Stade Joseph Marien (Royale Union Saint-Gilloise, Duden Park,
# Vorst/Forest, Brussels) from nothing and exports it for the game, the way
# the Jan Breydelstadion is built; on an early June evening, the sun low
# behind the main stand, the park's trees bright behind the far stand, as on
# the photo of the cup final rematch against Club Brugge (June 2023).
#   blender -b --factory-startup --python tools/marien_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/marien_assets.py.
#
# The facts and the plan:
#   - built 1915-19 at the foot of the Duden Park, the main stand rebuilt in
#     1926 by Albert Callewaert (art deco, a listed building), named after
#     the club's president Joseph Marien in 1933; about 9.400 places
#   - the plan is OpenStreetMap's (ways 817807086, 230673443, 17379423; data
#     © OpenStreetMap contributors, ODbL), turned 55.5 degrees so the pitch
#     lies on the axes: the main stand along the street on the north-west
#     side (+y), its street front 101 m long, the park on the other three
#   - the main stand as on the photos: one covered tier of 13 rows, grey
#     seats with a dark blue middle, a light blue front wall, a row of
#     windows at the back, a flat roof on dark trusses with a blue edge, four
#     bars of floodlights on poles over it; its street front of red brick
#     with stone bays, reliefs of players and UNION SAINT-GILLOISE in the
#     middle (photos, CC0), the end towers with the crest
#   - the away section: the south-west terrace, fenced in green (the
#     visitors stand there on the photos)
#   - the park side: an open stand of blue seats on a steel frame up the
#     slope, the club's band along its top, four tall green floodlight poles
#     among the trees behind it; behind both goals open concrete terraces
#     with crush barriers on banks of grass; the wooded hill of the park all
#     round, the houses of the town across the street
# No sponsors: the boards carry the club's and the city's own words.
#
# The helpers, the goals and the export are those of tools/jan_breydel_build.py;
# units are metres, x along the pitch (north-east), y towards the main stand
# (the camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time
import numpy as np
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'marien')
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
MAIN_Y, PARK_Y, END_X = 37.6, -40.0, 58.4     # the fronts: the main stand, the park stand, the terraces behind the goals
MAIN_X0, MAIN_X1 = -47.9, 47.3                # the main stand's seats run between its end towers
BLD_X0, BLD_X1, BLD_Y0, BLD_Y1 = -50.9, 50.3, 41.9, 51.8      # the 1926 building (OSM)
FACADE_H = 13.6
MAIN = dict(r=0.3, z=1.2, rows=13, depth=0.80, rise=0.40)     # to d 10.7, z 6.0
PARK = dict(r=0.5, z=0.9, rows=18, depth=0.85, rise=0.52)     # to d 15.8, z 9.7
TERR = dict(r=0.5, z=0.7, rows=20, depth=0.55, rise=0.32)     # to d 11.5, z 6.8
MAIN_BACK = MAIN['r'] + MAIN['depth'] * MAIN['rows']
MAIN_TOP = MAIN['z'] + MAIN['rise'] * (MAIN['rows'] - 1)
ROOF_D0, ROOF_D1 = -1.2, BLD_Y1 - 0.6 - MAIN_Y               # the roof: from over the front wall to the building's parapet
ROOF_U0, ROOF_U1 = 11.0, 12.3
ROOF_TH = 0.6
GAIN = 2.0
SEAT_W, AISLE_W = 0.5, 1.1
SUN_AZ, SUN_EL = math.radians(109.5), math.radians(24)        # a June evening: the sun in the west-north-west, behind the main stand
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))
BOARD_Y, BOARD_X = PL / 2 + 2.8, PW / 2 + 3.2


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



rng = np.random.default_rng(1926)


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


def glazing_tex():
    w, h = 384, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.05, 0.065, 0.08), 'f')
    t *= np.linspace(0.7, 1.3, h)[:, None, None]
    t[:, (np.arange(w) % 48) < 4] = (0.80, 0.81, 0.80)
    t[:6] = (0.80, 0.81, 0.80); t[-6:] = (0.80, 0.81, 0.80)
    return t


def foliage_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.05, 0.10, 0.03), 'f')
    t *= (1 + 0.35 * vnoise(h, w, 6, 6) + 0.2 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


def grass_bank_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.07, 0.13, 0.04), 'f')
    t *= (1 + 0.15 * vnoise(h, w, 16, 16) + 0.12 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


SEATS = [(0.30, 0.31, 0.32), (0.27, 0.28, 0.29), (0.025, 0.05, 0.16), (0.02, 0.09, 0.40), (0.018, 0.075, 0.34)]
SEAT_GREY, SEAT_NAVY, SEAT_BLUE = 0, 2, 3
seat_cols = [image_material('M_Seat%d' % i, painted('jm_seat%d' % i, seat_tile(c)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.25, 0.245, 0.235), 0.9)              # weathered, as on the photos
concrete_dark = principled('M_ConcreteDark', (0.16, 0.155, 0.15), 0.9)
concrete_light = principled('M_ConcreteLight', (0.44, 0.43, 0.40), 0.85)
alu = principled('M_Alu', (0.46, 0.47, 0.48), 0.5, metallic=0.2)
alu_dark = principled('M_AluDark', (0.10, 0.10, 0.11), 0.6)
galv = principled('M_Galvanised', (0.40, 0.41, 0.42), 0.5)
light_blue = principled('M_LightBlue', (0.30, 0.50, 0.78), 0.7)
white_paint = principled('M_WhitePaint', (0.80, 0.80, 0.78), 0.7)
roof_blue = principled('M_RoofBlue', (0.02, 0.10, 0.42), 0.5)
roof_under = principled('M_RoofUnder', (0.08, 0.085, 0.09), 0.8)
roof_top = principled('M_RoofTop', (0.20, 0.21, 0.22), 0.8)
truss_mat = principled('M_Truss', (0.06, 0.065, 0.07), 0.6)
pole_green = principled('M_PoleGreen', (0.05, 0.16, 0.08), 0.6)
steel_grey = principled('M_SteelGrey', (0.30, 0.31, 0.32), 0.5)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
glazing = image_material('M_Glazing', painted('jm_glazing', glazing_tex()), 0.2)
facade_mat = image_material('M_Facade', load_asset('facade.png'), 0.85)
endface_mat = image_material('M_EndFace', load_asset('endface.png'), 0.85)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
banner_mat = image_material('M_Banner', load_asset('banner.png'), 0.7)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
bank_mat = image_material('M_Bank', painted('jm_bank', grass_bank_tex()), 0.95)
foliage = image_material('M_Foliage', painted('jm_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
brick = principled('M_Brick', (0.24, 0.10, 0.06), 0.9)
plaster = principled('M_Plaster', (0.52, 0.49, 0.44), 0.9)
stone_house = principled('M_StoneHouse', (0.44, 0.40, 0.33), 0.9)
tiles = principled('M_Tiles', (0.12, 0.06, 0.045), 0.8)
slate = principled('M_Slate', (0.07, 0.075, 0.085), 0.7)
dark_glass = principled('M_DarkGlass', (0.03, 0.035, 0.04), 0.15)


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

net_tile = np.zeros((32, 32, 4), 'f')
net_tile[..., :3] = 0.92
net_tile[:3, :, 3] = 1.0; net_tile[:, :3, 3] = 1.0
net_img = D.images.new('jm_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/jm_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
PITCH_X, PITCH_Y = 55.5, 36.6
FLOOR_X, FLOOR_Y = END_X + 0.2, -PARK_Y + 0.2
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
def stand_frame(a, b, nrm):
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    return a, b, Vector((nrm[0], nrm[1], 0)).normalized()


def build_stand(name, a, b, nrm, t, base_z, kind, colour=None, bay=13.0, step_mat=(0, 1), barrier_every=4):
    # a straight stand from a to b, its rows stepping back along nrm: treads
    # and risers, a stairway every `bay` metres, seats (or, on a terrace,
    # staggered crush barriers), a handrail up each stairway
    a, b, nrm = stand_frame(a, b, nrm)
    L = (b - a).length
    tang = (b - a) / L
    nb = max(1, round(L / bay))
    steps, seats, rails = bmesh.new(), bmesh.new(), bmesh.new()
    lift = Vector((0, 0, 0.012))
    for k in range(t['rows']):
        r0, r1, z = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1), t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        n = max(1, math.ceil(L / 3.0))
        for s in range(n):
            p0, p1 = a.lerp(b, s / n), a.lerp(b, (s + 1) / n)
            A0, A1, B0, B1 = p0 + nrm * r0, p1 + nrm * r0, p0 + nrm * r1, p1 + nrm * r1
            face(steps, [(A0.x, A0.y, z), (A1.x, A1.y, z), (B1.x, B1.y, z), (B0.x, B0.y, z)], UPV, step_mat[0])
            face(steps, [(A0.x, A0.y, z_prev), (A1.x, A1.y, z_prev), (A1.x, A1.y, z), (A0.x, A0.y, z)], -nrm, step_mat[1])
        for i in range(nb):
            u0, u1 = i / nb, (i + 1) / nb
            c0 = u0 + (AISLE_W / 2 / L if i > 0 else 0.3 / L)
            c1 = u1 - (AISLE_W / 2 / L if i < nb - 1 else 0.3 / L)
            if kind == 'seats':
                usable = (c1 - c0) * L
                ns = max(1, round(usable / SEAT_W))
                q = 0
                while q < ns:
                    q1 = min(ns, q + 2)
                    us = [c0 + (c1 - c0) * qq / ns for qq in (q, q1)]
                    mid = a.lerp(b, (us[0] + us[1]) / 2)
                    m = colour(i, k, mid)
                    pa = [a.lerp(b, uu) + nrm * r0 + Vector((0, 0, z)) for uu in us]
                    pb = [a.lerp(b, uu) + nrm * r1 + Vector((0, 0, z)) for uu in us]
                    def at(tt, hgt, kk):
                        return pa[kk].lerp(pb[kk], tt) + Vector((0, 0, hgt))
                    face(seats, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
                    face(seats, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -nrm, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
                    face(seats, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UPV, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])
                    q = q1
            elif kind == 'terrace' and k % barrier_every == (i % 2) * 2 and 0 < k < t['rows'] - 1:
                # a crush barrier along this bay, its posts every 2.5 m
                pa, pb = a.lerp(b, c0 + 0.05) + nrm * (r0 + 0.1), a.lerp(b, c1 - 0.05) + nrm * (r0 + 0.1)
                tube(rails, pa + Vector((0, 0, z + 1.05)), pb + Vector((0, 0, z + 1.05)), 0.04, 0, 6, step=3.0)
                npst = max(2, round((pb - pa).length / 2.5))
                for j in range(npst + 1):
                    pp = pa.lerp(pb, j / npst)
                    tube(rails, pp + Vector((0, 0, z)), pp + Vector((0, 0, z + 1.05)), 0.035, 0, 5)
    # the handrails up the stairways
    for i in range(1, nb):
        p = a.lerp(b, i / nb)
        pa_, pb_ = p + nrm * (t['r'] + t['depth'] * 1.5), p + nrm * (t['r'] + t['depth'] * (t['rows'] - 0.5))
        za, zb = t['z'] + t['rise'] * 1 + 0.95, t['z'] + t['rise'] * (t['rows'] - 1) + 0.95
        tube(rails, pa_ + Vector((0, 0, za)), pb_ + Vector((0, 0, zb)), 0.035, 0, 6, step=3.0)
        for k in range(1, t['rows'], 4):
            pp = p + nrm * (t['r'] + t['depth'] * (k + 0.5))
            zz = t['z'] + t['rise'] * k
            tube(rails, pp + Vector((0, 0, zz)), pp + Vector((0, 0, zz + 0.95)), 0.03, 0, 5)
    return steps, seats, rails


def main_colour(i, k, p):
    if abs(p.x) < 11.0 and k >= 2:
        return SEAT_NAVY                            # the middle of the main stand: dark blue
    return SEAT_GREY if (k + i) % 5 else 1


def park_colour(i, k, p):
    return SEAT_BLUE if (k // 3 + i) % 4 else 4


t0 = time.time()
# the main stand: from the north-east tower to the south-west one, its rows back towards the street
st, se, ra = build_stand('Main', (MAIN_X1, MAIN_Y), (MAIN_X0, MAIN_Y), (0, 1), MAIN, 1.2, 'seats', main_colour, bay=11.9)
new_obj('Steps_Main', st, '02_Bowl', [concrete, light_blue])
new_obj('Seats_Main', se, '03_Seats', seat_cols)
new_obj('Rails_Main', ra, '02_Bowl', [steel_grey])
# the park stand: blue seats on an aluminium frame up the slope
st, se, ra = build_stand('Park', (-52.0, PARK_Y), (52.0, PARK_Y), (0, -1), PARK, 0.9, 'seats', park_colour, bay=13.0)
new_obj('Steps_Park', st, '02_Bowl', [alu, alu_dark])
new_obj('Seats_Park', se, '03_Seats', seat_cols)
new_obj('Rails_Park', ra, '02_Bowl', [alu])
# the terraces behind the goals: the south-west one on the park side of the
# end only, the north-east one right across
st, se, ra = build_stand('SW', (-END_X, 20.0), (-END_X, -36.0), (-1, 0), TERR, 0.7, 'terrace', bay=14.0)
new_obj('Steps_SW', st, '02_Bowl', [concrete, concrete_dark])
se.free()
new_obj('Barriers_SW', ra, '02_Bowl', [galv])
st, se, ra = build_stand('NE', (END_X, -36.0), (END_X, 32.0), (1, 0), TERR, 0.7, 'terrace', bay=13.6)
new_obj('Steps_NE', st, '02_Bowl', [concrete, concrete_dark])
se.free()
new_obj('Barriers_NE', ra, '02_Bowl', [galv])
print('STANDS %.0fs' % (time.time() - t0))


def strip(bm, a, b, d0, z0, d1, z1, nrm, mat, want=None, step=3.0, uv=None):
    # a strip along a straight stand from (offset d0, z0) to (d1, z1)
    a, b, nrm = stand_frame(a, b, nrm)
    n = max(1, math.ceil((b - a).length / step))
    for s in range(n):
        p0, p1 = a.lerp(b, s / n), a.lerp(b, (s + 1) / n)
        q = [p0 + nrm * d0, p1 + nrm * d0, p1 + nrm * d1, p0 + nrm * d1]
        w = {'up': UPV, 'down': -UPV, 'in': -nrm, 'out': nrm}.get(want, want)
        uvs = uv(s / n, (s + 1) / n) if uv else None
        face(bm, [(q[0].x, q[0].y, z0), (q[1].x, q[1].y, z0), (q[2].x, q[2].y, z1), (q[3].x, q[3].y, z1)], w, mat, uvs)


# the main stand's front wall (light blue, a white top), the walkway behind
# the last row and the back with its windows up to the roof
bm = bmesh.new()
MA, MB = (MAIN_X1, MAIN_Y), (MAIN_X0, MAIN_Y)
strip(bm, MA, MB, 0.0, 0.0, 0.0, 0.95, (0, 1), 0, 'in')
strip(bm, MA, MB, 0.0, 0.95, 0.0, 1.2, (0, 1), 1, 'in')
strip(bm, MA, MB, 0.0, 1.2, MAIN['r'], 1.2, (0, 1), 1, 'up')
strip(bm, MA, MB, MAIN_BACK, MAIN_TOP, MAIN_BACK + 0.6, MAIN_TOP, (0, 1), 2, 'up')
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP, MAIN_BACK + 0.6, MAIN_TOP + 0.5, (0, 1), 1, 'in')
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP + 0.5, MAIN_BACK + 0.6, MAIN_TOP + 3.4, (0, 1), 3, 'in',
      uv=lambda u0, u1: [(u0 * 95.2 / 6, 0), (u1 * 95.2 / 6, 0), (u1 * 95.2 / 6, 1), (u0 * 95.2 / 6, 1)])
roof_at = lambda d: ROOF_U0 + (ROOF_U1 - ROOF_U0) * (d - ROOF_D0) / (ROOF_D1 - ROOF_D0)
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP + 3.4, MAIN_BACK + 0.6, roof_at(MAIN_BACK + 0.6), (0, 1), 0, 'in')
# the stand's two ends between the front and the towers: closed walls, light blue
for x_, sgn in ((MAIN_X1, 1), (MAIN_X0, -1)):
    prof = [(0.0, 0.0), (0.0, 2.2)] + [(MAIN['r'] + MAIN['depth'] * k, MAIN['z'] + MAIN['rise'] * k + 1.0) for k in range(MAIN['rows'])]
    prof += [(BLD_Y0 - MAIN_Y, roof_at(BLD_Y0 - MAIN_Y)), (BLD_Y0 - MAIN_Y, 0.0)]
    for j in range(len(prof) - 1):
        (da, za), (db, zb) = prof[j], prof[j + 1]
        if j == 0 or j == len(prof) - 2:
            continue
        face(bm, [(x_, MAIN_Y + da, 0.0), (x_, MAIN_Y + db, 0.0), (x_, MAIN_Y + db, zb), (x_, MAIN_Y + da, za)], Vector((sgn, 0, 0)), 0)
        face(bm, [(x_, MAIN_Y + da, 0.0), (x_, MAIN_Y + db, 0.0), (x_, MAIN_Y + db, zb), (x_, MAIN_Y + da, za)], Vector((-sgn, 0, 0)), 0)
    face(bm, [(x_, MAIN_Y, 0.0), (x_, MAIN_Y + MAIN['r'], 0.0), (x_, MAIN_Y + MAIN['r'], 2.2), (x_, MAIN_Y, 2.2)], Vector((sgn, 0, 0)), 0)
new_obj('Main_Walls', bm, '02_Bowl', [light_blue, white_paint, concrete, glazing])

# the 1926 building behind the seats: its street front (facade.png, u from
# east to west so it reads from the street), the parapet, the two end towers
# with the crest
bm = bmesh.new()
face_w = BLD_X1 - BLD_X0
nseg = 34
for s in range(nseg):
    x0_, x1_ = BLD_X1 - face_w * s / nseg, BLD_X1 - face_w * (s + 1) / nseg
    for q in range(4):
        z0_, z1_ = FACADE_H * q / 4, FACADE_H * (q + 1) / 4
        face(bm, [(x0_, BLD_Y1, z0_), (x1_, BLD_Y1, z0_), (x1_, BLD_Y1, z1_), (x0_, BLD_Y1, z1_)], Vector((0, 1, 0)), 0,
             [(s / nseg, q / 4), ((s + 1) / nseg, q / 4), ((s + 1) / nseg, (q + 1) / 4), (s / nseg, (q + 1) / 4)])
abox(bm, BLD_X0, BLD_X1, BLD_Y1 - 0.6, BLD_Y1, FACADE_H - 0.01, FACADE_H + 0.05, 2, True, False)
face(bm, [(BLD_X1, BLD_Y1 - 0.6, roof_at(ROOF_D1) - 0.2), (BLD_X0, BLD_Y1 - 0.6, roof_at(ROOF_D1) - 0.2),
          (BLD_X0, BLD_Y1 - 0.6, FACADE_H), (BLD_X1, BLD_Y1 - 0.6, FACADE_H)], Vector((0, -1, 0)), 2)
TOWER_W, TOWER_H = 3.0, 15.0
for xo, xi, sgn in ((BLD_X1, BLD_X1 - TOWER_W, 1), (BLD_X0, BLD_X0 + TOWER_W, -1)):
    # the end face with the crest (endface.png)
    for q in range(5):
        z0_, z1_ = TOWER_H * q / 5, TOWER_H * (q + 1) / 5
        ya, yb = (BLD_Y0, BLD_Y1) if sgn > 0 else (BLD_Y1, BLD_Y0)          # u left to right as seen from outside
        face(bm, [(xo, ya, z0_), (xo, yb, z0_), (xo, yb, z1_), (xo, ya, z1_)], Vector((sgn, 0, 0)), 1,
             [(0, q / 5), (1, q / 5), (1, (q + 1) / 5), (0, (q + 1) / 5)])
    xa, xb = min(xo, xi), max(xo, xi)
    for q in range(5):
        z0_, z1_ = TOWER_H * q / 5, TOWER_H * (q + 1) / 5
        face(bm, [(xa, BLD_Y0, z0_), (xb, BLD_Y0, z0_), (xb, BLD_Y0, z1_), (xa, BLD_Y0, z1_)], Vector((0, -1, 0)), 3)
        face(bm, [(xi, BLD_Y0, z0_), (xi, BLD_Y1, z0_), (xi, BLD_Y1, z1_), (xi, BLD_Y0, z1_)], Vector((-sgn, 0, 0)), 3)
    face(bm, [(xa, BLD_Y1, FACADE_H), (xb, BLD_Y1, FACADE_H), (xb, BLD_Y1, TOWER_H), (xa, BLD_Y1, TOWER_H)], Vector((0, 1, 0)), 3)
    abox(bm, xa, xb, BLD_Y0, BLD_Y1, TOWER_H - 0.01, TOWER_H + 0.4, 2, True, False)
# under the stand, behind its front, the space up to the building is closed
face(bm, [(MAIN_X1, BLD_Y0, 0.0), (MAIN_X0, BLD_Y0, 0.0), (MAIN_X0, BLD_Y0, MAIN['z']), (MAIN_X1, BLD_Y0, MAIN['z'])], Vector((0, -1, 0)), 3)
new_obj('Building', bm, '02_Bowl', [facade_mat, endface_mat, concrete_light, brick])

# the roof over the main stand: dark underneath on dark trusses, the blue
# edge along its front, grey on top; four bars of floodlights on poles
bm, tb = bmesh.new(), bmesh.new()
RA, RB = (MAIN_X1 + 0.4, MAIN_Y), (MAIN_X0 - 0.4, MAIN_Y)
BANDS = [ROOF_D0, ROOF_D0 + 4, ROOF_D0 + 8, ROOF_D0 + 12, ROOF_D1]
for j in range(len(BANDS) - 1):
    strip(bm, RA, RB, BANDS[j], roof_at(BANDS[j]), BANDS[j + 1], roof_at(BANDS[j + 1]), (0, 1), 0, 'down')
    strip(bm, RA, RB, BANDS[j], roof_at(BANDS[j]) + ROOF_TH, BANDS[j + 1], roof_at(BANDS[j + 1]) + ROOF_TH, (0, 1), 1, 'up')
strip(bm, RA, RB, ROOF_D0, roof_at(ROOF_D0) - 0.5, ROOF_D0, roof_at(ROOF_D0) + ROOF_TH + 0.1, (0, 1), 2, 'in')
strip(bm, RA, RB, ROOF_D0, roof_at(ROOF_D0) - 0.5, ROOF_D0 + 0.3, roof_at(ROOF_D0) - 0.5, (0, 1), 2, 'down')
for xe, sgn in ((RA[0], 1), (RB[0], -1)):
    face(bm, [(xe, MAIN_Y + ROOF_D0, roof_at(ROOF_D0) - 0.5), (xe, MAIN_Y + ROOF_D1, roof_at(ROOF_D1)),
              (xe, MAIN_Y + ROOF_D1, roof_at(ROOF_D1) + ROOF_TH), (xe, MAIN_Y + ROOF_D0, roof_at(ROOF_D0) + ROOF_TH + 0.1)], Vector((sgn, 0, 0)), 2)
nt = 16
for k in range(nt + 1):
    x_ = RA[0] + (RB[0] - RA[0]) * k / nt
    a_, b_ = Vector((x_, MAIN_Y + ROOF_D0 + 0.4, 0)), Vector((x_, MAIN_Y + ROOF_D1 - 0.3, 0))
    span_ = ROOF_D1 - ROOF_D0 - 0.7
    top_ = lambda t: roof_at(ROOF_D0 + 0.4 + span_ * t) + 0.02
    prism(tb, a_, b_, 0.3, top_, lambda t: top_(t) - 0.35 - 0.9 * t, 0)
    # the lattice: diagonals between the top and the bottom chord
    for j in range(6):
        t0_, t1_ = j / 6, (j + 1) / 6
        pa = a_.lerp(b_, t0_) + Vector((0, 0, top_(t0_) - 0.35 - 0.9 * t0_))
        pb = a_.lerp(b_, t1_) + Vector((0, 0, top_(t1_) - 0.1))
        tube(tb, pa, pb, 0.05, 0, 4, trim=0.05)
new_obj('Roof', bm, '04_Roof', [roof_under, roof_top, roof_blue])
new_obj('Roof_Trusses', tb, '04_Roof', [truss_mat])
bm = bmesh.new()
for x_ in (-36.0, -12.0, 12.0, 36.0):
    base = Vector((x_, MAIN_Y + 9.5, roof_at(9.5) + ROOF_TH))
    top = base + Vector((0, 0, 7.5))
    tube(bm, base, top, 0.14, 0, 6, step=3.0)
    tube(bm, base + Vector((0, 3.0, 0)), top - Vector((0, 0, 1.0)), 0.06, 0, 5)
    fwd = Vector((0, -math.cos(math.radians(32)), -math.sin(math.radians(32))))
    side = Vector((1, 0, 0))
    upl = side.cross(fwd).normalized()
    if upl.z < 0:
        upl = -upl
    tube(bm, top - side * 4.0, top + side * 4.0, 0.12, 0, 6)
    for j in range(8):
        c = top + side * (-3.5 + j) + Vector((0, -0.35, 0.25))
        obox(bm, c, fwd, side, upl, 0.25, 0.38, 0.32, 0)
        cc = c + fwd * 0.26
        face(bm, [cc - side * 0.32 - upl * 0.26, cc + side * 0.32 - upl * 0.26, cc + side * 0.32 + upl * 0.26, cc - side * 0.32 + upl * 0.26], fwd, 1)
# the tall green poles among the trees behind the park stand
POLES_PARK = [(-40.0, -59.5), (-13.0, -59.5), (13.0, -59.5), (40.0, -59.5)]
for px, py in POLES_PARK:
    zb_ = 0.0
    tube(bm, Vector((px, py, zb_)), Vector((px, py, 27.0)), 0.25, 2, 8, step=4.0)
    fwd = Vector((0, 0.86, -0.5)).normalized()
    side = Vector((1, 0, 0))
    upl = side.cross(fwd).normalized()
    if upl.z < 0:
        upl = -upl
    for j in range(4):
        c = Vector((px - 1.2 + 0.8 * j, py + 0.6, 27.2))
        obox(bm, c, fwd, side, upl, 0.25, 0.36, 0.3, 0)
        cc = c + fwd * 0.26
        face(bm, [cc - side * 0.3 - upl * 0.24, cc + side * 0.3 - upl * 0.24, cc + side * 0.3 + upl * 0.24, cc - side * 0.3 + upl * 0.24], fwd, 1)
new_obj('Floodlights', bm, '04_Roof', [steel_grey, lamp, pole_green])

# the park stand's top: a walkway, a fence and the club's band along it
bm = bmesh.new()
PA, PB = (-52.0, PARK_Y), (52.0, PARK_Y)
PBACK = PARK['r'] + PARK['depth'] * PARK['rows']
PTOP = PARK['z'] + PARK['rise'] * (PARK['rows'] - 1)
strip(bm, PA, PB, PBACK, PTOP, PBACK + 1.5, PTOP, (0, -1), 0, 'up')
strip(bm, PA, PB, PBACK + 1.5, PTOP + 0.1, PBACK + 1.5, PTOP + 1.3, (0, -1), 1, 'in',
      uv=lambda u0, u1: [((1 - u0) * 104 / 96, 0), ((1 - u1) * 104 / 96, 0), ((1 - u1) * 104 / 96, 1), ((1 - u0) * 104 / 96, 1)])   # u against x: it reads from the pitch
strip(bm, PA, PB, PBACK + 1.55, PTOP + 0.1, PBACK + 1.55, PTOP + 1.3, (0, -1), 0, 'out')
strip(bm, PA, PB, 0.0, 0.0, 0.0, PARK['z'] - 0.1, (0, -1), 2, 'in')
new_obj('Park_Top', bm, '02_Bowl', [alu, banner_mat, concrete])
bm = bmesh.new()
for x_ in np.arange(-52.0, 52.01, 2.6):
    tube(bm, Vector((x_, PARK_Y - PBACK - 1.5, PTOP)), Vector((x_, PARK_Y - PBACK - 1.5, PTOP + 1.4)), 0.035, 0, 5)
tube(bm, Vector((-52, PARK_Y - PBACK - 1.5, PTOP + 1.4)), Vector((52, PARK_Y - PBACK - 1.5, PTOP + 1.4)), 0.04, 0, 6, step=3.0)
new_obj('Park_Fence', bm, '02_Bowl', [alu])

# the away section: the south-west terrace, behind tall green fences along
# its front and up both its ends, as on the photos of the visitors there
fence_green = principled('M_FenceGreen', (0.03, 0.12, 0.06), 0.6)
bm = bmesh.new()
def fence(pa, pb, za, zb, h=2.6, every=2.4):
    pa, pb = Vector((pa[0], pa[1], 0)), Vector((pb[0], pb[1], 0))
    L = (pb - pa).length
    n = max(1, math.ceil(L / every))
    for k in range(n + 1):
        q = pa.lerp(pb, k / n); zq = za + (zb - za) * k / n
        tube(bm, Vector((q.x, q.y, zq)), Vector((q.x, q.y, zq + h)), 0.05, 0, 5)
    for hh in (0.15, 1.3, h):
        tube(bm, Vector((pa.x, pa.y, za + hh)), Vector((pb.x, pb.y, zb + hh)), 0.04, 0, 5, step=3.0)
    m = max(1, int(L / 0.2))
    for k in range(m):
        q = pa.lerp(pb, (k + 0.5) / m); zq = za + (zb - za) * (k + 0.5) / m
        tube(bm, Vector((q.x, q.y, zq + 0.15)), Vector((q.x, q.y, zq + h)), 0.012, 0, 3, step=4.0)
TBACK = TERR['r'] + TERR['depth'] * TERR['rows']
TTOP = TERR['z'] + TERR['rise'] * (TERR['rows'] - 1)
fence((-END_X - 0.15, 20.0), (-END_X - 0.15, -36.0), TERR['z'] - 0.1, TERR['z'] - 0.1, h=3.0)       # along its front
for y_ in (20.0, -36.0):
    fence((-END_X - 0.3, y_), (-END_X - TBACK, y_), TERR['z'], TTOP, h=2.6)                     # up both its ends
fence((-END_X - TBACK - 0.3, 20.0), (-END_X - TBACK - 0.3, -36.0), TTOP, TTOP, h=2.6)           # and along its back
new_obj('Away_Fences', bm, '02_Bowl', [fence_green])

# the boards round the pitch and the dugouts in front of the main stand
BOARD_LINES = [
    (Vector((52.0, -BOARD_Y, 0)), Vector((-52.0, -BOARD_Y, 0)), -math.pi / 2),
    (Vector((-52.0, BOARD_Y, 0)), Vector((-15.0, BOARD_Y, 0)), math.pi / 2),
    (Vector((15.0, BOARD_Y, 0)), Vector((52.0, BOARD_Y, 0)), math.pi / 2),
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
for x0, x1 in ((-13.5, -4.0), (4.0, 13.5)):
    yb = MAIN_Y - 0.2
    face(bm, [(x0, yb - 2.0, 2.0), (x1, yb - 2.0, 2.0), (x1, yb, 2.3), (x0, yb, 2.3)], UPV, 3)
    face(bm, [(x0, yb - 2.0, 1.98), (x1, yb - 2.0, 1.98), (x1, yb, 2.28), (x0, yb, 2.28)], -UPV, 3)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.3), (x0, yb, 2.3)], Vector((0, -1, 0)), 2)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.0, 0.0), (x, yb, 0.0), (x, yb, 2.3), (x, yb - 2.0, 2.0)], Vector((1 if x == x0 else -1, 0, 0)), 3)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_grey, white_paint, dark_glass])

# ================================================================ the ground: banks, the park's hill, the town
G_HALF = 320.0                   # tools/marien/ground.png covers 640 x 640 m
G_Z = -0.12
AP = 80.0                        # the stadium's own ground reaches this far; beyond it, and all the trees, the backdrop


def hz(x, y):
    # the ground: flat on the town's side, the banks under the park stand and
    # the terraces, the park's hill rising behind them
    z = 0.0
    if y < PARK_Y:
        d = PARK_Y - y
        z = max(z, min(d, 16.3) * 0.548 + max(0.0, d - 55.0) * 0.20)        # a level walk behind the stand, then the hill
    for s in (-1, 1):
        d = s * x - END_X
        if d > 0:
            ze = min(d, 11.5) * 0.548 + max(0.0, d - 40.0) * 0.12
            if s < 0 and y > 22.0:
                ze *= max(0.0, 1 - (y - 22.0) / 10.0)            # the south-west corner on the town's side stays low
            z = max(z, ze)
    if y > 30.0:
        z *= max(0.0, 1 - (y - 30.0) / 16.0)
    return min(z, 34.0) + G_Z


def ground_grid(bm, x0, x1, y0, y1, step, skip, mat_of=lambda x, y: 0):
    nx, ny = round((x1 - x0) / step), round((y1 - y0) / step)
    for ix in range(nx):
        for iy in range(ny):
            xa, xb = x0 + ix * step, x0 + (ix + 1) * step
            ya, yb = y0 + iy * step, y0 + (iy + 1) * step
            if skip(xa, xb, ya, yb):
                continue
            q = [(xa, ya), (xb, ya), (xb, yb), (xa, yb)]
            face(bm, [(x, y, hz(x, y)) for x, y in q], UPV, mat_of((xa + xb) / 2, (ya + yb) / 2),
                 [((x + G_HALF) / (2 * G_HALF), (y + G_HALF) / (2 * G_HALF)) for x, y in q])


inside_floor = lambda xa, xb, ya, yb: -END_X + 0.5 <= xa and xb <= END_X - 0.5 and PARK_Y + 0.5 <= ya and yb <= MAIN_Y - 0.5
bank = lambda x, y: 1 if (y < PARK_Y - 0.5 or abs(x) > END_X + 0.5) and y < 44 else 0
bm = bmesh.new()
ground_grid(bm, -AP, AP, -AP, 60.0, 2.5, inside_floor, bank)
new_obj('Ground', bm, '05_Outside', [ground_mat, bank_mat])

trng = random.Random(1926)


def tree(bm, x, y, h, r, subdiv=1):
    z0 = hz(x, y)
    tube(bm, Vector((x, y, z0)), Vector((x, y, z0 + h * 0.6)), 0.3, 0, 5, step=5.0)
    res = bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bmesh.ops.scale(bm, vec=Vector((r, r * trng.uniform(0.85, 1.1), h * 0.32)), verts=res['verts'])
    bmesh.ops.translate(bm, vec=Vector((x, y, z0 + h * 0.70)), verts=res['verts'])
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


PATHS_W = [r['pts'] for r in OSM['roads'] if r['type'] in ('footway', 'path', 'steps', 'service', 'cycleway', 'track')]


def near_path(x, y, m):
    for pts in PATHS_W:
        for k in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-6, dx * dx + dy * dy)))
            if math.hypot(x - ax - t * dx, y - ay - t * dy) < m:
                return True
    return False


def in_stadium(x, y):
    return (abs(x) < END_X + TERR['r'] + TERR['depth'] * TERR['rows'] + 1.5 and PARK_Y - PBACK - 3.5 < y < BLD_Y1 + 1.0)


def forest(bm, x0, x1, y0, y1, step, keep):
    # the park's trees: big beeches and oaks, on the park's ground only
    for gx in np.arange(x0, x1, step):
        for gy in np.arange(y0, y1, step):
            x, y = gx + trng.uniform(-0.4, 0.4) * step, gy + trng.uniform(-0.4, 0.4) * step
            if not keep(x, y) or in_stadium(x, y):
                continue
            if not any(inside_poly(x, y, g) for g in OSM['park']) and not any(inside_poly(x, y, g) for g in OSM['forest']):
                continue
            if near_path(x, y, 3.0):
                continue
            tree(bm, x, y, trng.uniform(17, 27), trng.uniform(4.5, 7.5), 2 if math.hypot(x, y) < 110 else 1)


bm = bmesh.new()
forest(bm, -130.0, 130.0, -130.0, 50.0, 9.0, lambda x, y: abs(x) < 130 and -130 < y < 50)
near_trees = new_obj('Trees_Near', bm, '06_Backdrop', [trunk, foliage])

# ================================================================ the backdrop: the park beyond and the town
bm = bmesh.new()
ground_grid(bm, -G_HALF, G_HALF, -G_HALF, G_HALF, 10.0, lambda xa, xb, ya, yb: -AP <= xa and xb <= AP and -AP <= ya and yb <= 60.0)
far_ground = new_obj('Ground_Far', bm, '06_Backdrop', [ground_mat])
bm = bmesh.new()
for b in OSM['buildings']:
    pts = b['pts'][:-1] if b['pts'][0] == b['pts'][-1] else b['pts']
    if len(pts) < 3 or max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4:
        continue
    sarea = 0.5 * sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
    area = abs(sarea)
    if area < 6:
        continue
    cx_ = sum(p[0] for p in pts) / len(pts); cy_ = sum(p[1] for p in pts) / len(pts)
    if in_stadium(cx_, cy_):
        continue
    h = {'garage': 3.0, 'garages': 3.0, 'shed': 2.6, 'kiosk': 3.0, 'roof': 4.0}.get(b['type'], 13.0 if area < 400 else 16.0)
    if cy_ < 44.0 or any(inside_poly(cx_, cy_, g) for g in OSM['park']):
        h = min(h, 4.0)                              # the club's huts round the stadium and the park's pavilions: low
    if b['levels'] and h > 4.0:
        try:
            h = float(b['levels']) * 3.2 + 1.8
        except ValueError:
            pass
    z0 = min(hz(x, y) for x, y in pts)
    wall_m = trng.choice((1, 1, 2, 3))
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
        nz = max(1, math.ceil(h / 3.2))
        for q in range(nz):
            za, zb = z0 + h * q / nz, z0 + h * (q + 1) / nz
            face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, wall_m)
    try:
        rf = bm.faces.new([bm.verts.new((x, y, z0 + h)) for x, y in pts])
    except ValueError:
        continue
    rf.material_index = 0 if trng.random() < 0.6 else 4
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, plaster, stone_house, slate])
bm = bmesh.new()
forest(bm, -G_HALF + 10, G_HALF - 10, -G_HALF + 10, G_HALF - 10, 14.0, lambda x, y: not (abs(x) < 130 and -130 < y < 50))
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
    preview('match', (0, 46.0, 13.0), (0, -18.0, 0), 50)
    preview('photo2023', (-8.0, 46.0, 14.0), (0.0, -50.0, 8.0), 58)
    preview('photo2010', (40.0, -46.0, 6.0), (-40.0, 30.0, 6.0), 60)
    preview('patro', (-55.0, -10.0, 2.0), (20.0, 45.0, 8.0), 60)
    preview('street', (-14.0, 58.5, 1.7), (6.0, 51.0, 8.0), 70)
    preview('tower', (70.0, 66.0, 2.0), (50.0, 46.0, 9.0), 58)
    preview('air', (-210.0, 190.0, 150.0), (0.0, 0.0, 5.0), 32)
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
floor_light = bake_lightmap(floor, 840, 576)
grass.hide_render = False
inner = grass_light[int(464 * 0.25):int(464 * 0.75), int(704 * 0.25):int(704 * 0.75)]
lum_px = (inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1)
lum = float(np.percentile(lum_px, 75))  # the sunlit grass, not the shadow of the west stand
EXPOSE = 0.66 / max(lum, 1e-6)          # a little lower than at noon: the low sun lights the slopes facing it far more than the pitch
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


# the pitch picture: 4096 x 2702 over 111 x 73 m
H, W = 2702, 4096
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * PITCH_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * PITCH_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = grass_albedo(X, Y, H, W)
cov = line_alpha(X, Y, 2 * PITCH_X / W)[..., None] * np.clip(0.85 + 0.1 * vnoise(H, W, 90, 90), 0.7, 1)[..., None]
alb = alb * (1 - cov) + np.array((0.80, 0.81, 0.78), 'f') * cov
pitch_img = finish('jm_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: 2048 x 1454 over the ground inside the stands: grass up
# to the boards, tarmac behind them
H, W = 1405, 2048
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.052, 0.052, 0.056)
alb *= (1 + 0.06 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 30, 30))[..., None]
infield = (np.abs(X) < BOARD_X) & (np.abs(Y) < BOARD_Y)
alb = np.where(infield[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('jm_floor', alb, floor_light, H, W)
del alb, X, Y
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

skip = ('Pitch_Lines', 'StadiumGoals', 'Ground_Far', 'Buildings', 'Trees_', 'ScreenFace_')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, far_ground, buildings, far_trees, near_trees]:
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    else:
        o.data.uv_layers[0].name = 'UVMap'
target = grass
select_only(export, target)
bpy.ops.object.join()
target.name = 'StadeJosephMarien'
select_only([far_ground, buildings, far_trees, near_trees], far_ground)
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

objs = [target, goals, backdrop]
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

