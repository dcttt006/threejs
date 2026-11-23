# Builds the Stade Joseph Marien (Royale Union Saint-Gilloise, Duden Park,
# Vorst/Forest, Brussels) from nothing and exports it for the game, the way
# the Jan Breydelstadion is built; on an early June evening, the sun low
# behind the main stand, the park's trees bright behind the far side.
#   blender -b --factory-startup --python tools/marien_build.py -- <out.blend> <out.glb> <texture dir> [quick]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/marien_assets.py.
#
# The facts and the plan:
#   - built 1915-19 at the foot of the Duden Park, the main stand rebuilt in
#     1926 by Albert Callewaert (art deco, a listed building), named after
#     the club's president Joseph Marien in 1933; about 9.400 places: the
#     covered main stand, the standing terrace on the park side (3.000) and
#     two half-round ends turned from terraces into seats in 2018
#   - the plan is OpenStreetMap's (ways 817807086, 230673443, 17379423; data
#     © OpenStreetMap contributors, ODbL), turned 55.5 degrees so the pitch
#     lies on the axes, and moved (DX, DY) so the pitch sits where the aerial
#     photo has its lines; the ends and the cloth on the bank are measured
#     on that photo
#   - the main stand as on the photos: 13 rows of grey seats under a flat roof
#     on columns, a block of blue seats right of the middle, a white front
#     with the dugouts; the roof green-grey on top with a blue edge, four
#     blue frames of floodlights on it, flags along the street front; its
#     street front of red brick with stone bays, reliefs of players and UNION
#     SAINT-GILLOISE in the middle (photos, CC0), the end towers with the crest
#   - the park side: a long standing terrace of concrete steps thick with
#     galvanised crush barriers, a black wall along its front with two yellow
#     gates, huts along its top under the club's band (yellow, blue, yellow,
#     players, be union be.brussels, the crest, ROYALE UNION SAINT-GILLOISE)
#     on yellow posts; four tall green floodlight poles among the trees behind
#   - the two ends: half-round stands of yellow seats with blue ones among
#     them, far from the goals behind a road and a bank of grass, radial
#     stairs with yellow edges; the south-west end (the town's side) holds
#     the away section, its park half behind green fences (the visitors sit
#     there on the photos of 2025), a TV scaffold and a cabin on its top; the
#     north-east end the scoreboard on a concrete base over its top row (0
#     00:00 0, the crest, VS, the other crest: game.screen.js, style 'marien')
#   - on the bank between the terrace and the south-west end the big cloth
#     Let's go hey!, the white villa on the hill above it; the wooded park all
#     round, the town across the street
#
# The helpers, the goals and the export are those of tools/jan_breydel_build.py;
# units are metres, x along the pitch (north-east), y towards the main stand
# (the camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time, bisect
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

# ---------------------------------------------------------------- the plan (metres)
PW, PL = 105.0, 68.0
LINE = 0.12
UPV = Vector((0, 0, 1))
DX, DY = -3.35, 4.75                # OpenStreetMap's plan moved so the pitch, as on the aerial photo, lies round the origin
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))
_sh = lambda pts: [[x + DX, y + DY] for x, y in pts]
OSM['stadium'] = _sh(OSM['stadium']); OSM['main'] = _sh(OSM['main'])
for _b in OSM['buildings'] + OSM['roads']:
    _b['pts'] = _sh(_b['pts'])
for _k in ('park', 'grass', 'forest'):
    OSM[_k] = [_sh(g) for g in OSM[_k]]

# the main stand and its 1926 building (OSM)
BLD_X0, BLD_X1, BLD_Y0, BLD_Y1 = -50.9 + DX, 50.3 + DX, 41.9 + DY, 51.8 + DY
MAIN_Y = 37.6 + DY                                   # the front of its seats
MAIN_X0, MAIN_X1 = -47.9 + DX, 47.3 + DX             # between the end towers
MAIN_C = (MAIN_X0 + MAIN_X1) / 2
FACADE_H = 13.6
MAIN = dict(r=0.3, z=1.2, rows=13, depth=0.80, rise=0.40)     # to d 10.7, z 6.0
MAIN_BACK = MAIN['r'] + MAIN['depth'] * MAIN['rows']
MAIN_TOP = MAIN['z'] + MAIN['rise'] * (MAIN['rows'] - 1)
ROOF_D0, ROOF_D1 = 2.6, BLD_Y1 - 0.6 - MAIN_Y        # the roof: its front edge over the third row (aerial photo), back to the parapet
ROOF_U0, ROOF_U1 = 11.0, 12.3
ROOF_TH = 0.6
# the standing terrace on the park side (aerial photo: its front 5.5 m from the line, 14 m deep)
PARK_Y, PX0, PX1 = -39.5, -52.0, 58.0
PARK = dict(r=0.6, z=1.3, rows=22, depth=0.62, rise=0.34)     # to d 14.2, z 8.4
PBACK = PARK['r'] + PARK['depth'] * PARK['rows']
PTOP = PARK['z'] + PARK['rise'] * (PARK['rows'] - 1)
PBACK_Y = PARK_Y - PBACK
BAND_X = 34.0                                        # the club's band over it: 68 m, round the halfway line
# the two half-round ends, seated: the fronts of their first rows (aerial photo)
CURVE = dict(r=0.5, z=1.0, rows=16, depth=0.82, rise=0.42)    # to d 13.6, z 7.3
CURVE_WZ = 0.6                                       # the walk along their fronts
CBACK = CURVE['r'] + CURVE['depth'] * CURVE['rows']
CTOP = CURVE['z'] + CURVE['rise'] * (CURVE['rows'] - 1)
SW_FRONT = [(-75.6, 22.0), (-75.0, 12.0), (-74.4, 2.0), (-73.6, -8.0), (-72.2, -17.0), (-69.8, -25.0), (-66.6, -30.3), (-63.6, -35.6)]   # its park end along the cloth's edge
NE_FRONT = [(60.6, 31.5), (61.8, 22.0), (62.5, 12.0), (62.8, 2.0), (62.6, -8.0), (62.0, -17.0), (61.0, -24.0), (59.8, -29.0)]
NE_DEPTH = [(31.5, 12.0), (14.0, 13.7), (4.0, 13.7), (-6.0, 12.4), (-15.0, 9.8), (-22.0, 8.0), (-29.0, 6.4)]   # how far back each part of it reaches, by y
AWAY_Y = -6.0                                        # the away section: the south-west end from here to the park
AISLE_W = 1.1
SEAT_W = 0.5
# the cloth on the bank between the terrace and the south-west end, as on the
# photos: its right edge along the end's last stair, from its first row to its
# top, as steep; 9.5 m wide (aerial photo). Low corners A, B (B on the left
# seen from the pitch), the high ones D over A, C over B
HEY = [Vector((-63.6, -35.6, 0.9)), Vector((-58.4, -43.5, 0.9)), Vector((-70.2, -50.2, 7.6)), Vector((-75.4, -42.3, 7.6))]
# the scoreboard over the top of the north-east end (13.png; the aerial photo has its base)
SCR_W, SCR_H = 8.0, 4.9
SCR_N = Vector((-1.0, -0.06, 0.0)).normalized()
SCR_C = Vector((77.7, 5.5, CTOP + 1.1 + SCR_H / 2))
# the floor the game sees inside the stands, and the stadium's own ground round it
FX0, FX1, FY0, FY1 = -77.0, 64.5, PARK_Y - 0.3, MAIN_Y + 0.3
GX0, GX1, GY0, GY1 = -112.5, 100.0, -92.5, 65.0
GAIN = 2.0
SUN_AZ, SUN_EL = math.radians(109.5), math.radians(24)        # a June evening: the sun in the west-north-west, behind the main stand
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()
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



# the seats as on the photos: the main stand light grey with a blue block;
# the ends Union yellow with blue among them, the north-east end's faded
SEATS = [(0.36, 0.38, 0.42), (0.31, 0.33, 0.37), (0.012, 0.08, 0.44),
         (0.85, 0.56, 0.02), (0.012, 0.09, 0.52), (0.74, 0.58, 0.18), (0.04, 0.14, 0.48)]
S_GREY, S_GREY2, S_MBLUE, S_YEL, S_BLUE, S_YEL_F, S_BLUE_F = range(7)
seat_cols = [image_material('M_Seat%d' % i, painted('jm_seat%d' % i, seat_tile(c)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.25, 0.245, 0.235), 0.9)              # weathered, as on the photos
concrete_dark = principled('M_ConcreteDark', (0.16, 0.155, 0.15), 0.9)
concrete_light = principled('M_ConcreteLight', (0.44, 0.43, 0.40), 0.85)
alu = principled('M_Alu', (0.46, 0.47, 0.48), 0.5, metallic=0.2)
galv = principled('M_Galvanised', (0.42, 0.43, 0.44), 0.5)
white_paint = principled('M_WhitePaint', (0.80, 0.80, 0.78), 0.7)
black_wall = principled('M_BlackWall', (0.025, 0.026, 0.028), 0.8)
yellow_paint = principled('M_YellowPaint', (0.88, 0.62, 0.02), 0.6)
roof_blue = principled('M_RoofBlue', (0.015, 0.11, 0.50), 0.5)
frame_blue = principled('M_FrameBlue', (0.03, 0.16, 0.52), 0.5)
roof_under_mat = principled('M_RoofUnder', (0.40, 0.41, 0.42), 0.8)
roof_top = principled('M_RoofTop', (0.17, 0.21, 0.15), 0.85)                # green-grey, as from the air
truss_mat = principled('M_Truss', (0.07, 0.08, 0.10), 0.6)
pole_green = principled('M_PoleGreen', (0.05, 0.16, 0.08), 0.6)
fence_green = principled('M_FenceGreen', (0.03, 0.12, 0.06), 0.6)
steel_grey = principled('M_SteelGrey', (0.30, 0.31, 0.32), 0.5)
steel_dark = principled('M_SteelDark', (0.05, 0.05, 0.055), 0.5)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
glazing = image_material('M_Glazing', painted('jm_glazing', glazing_tex()), 0.2)
facade_mat = image_material('M_Facade', load_asset('facade.png'), 0.85)
endface_mat = image_material('M_EndFace', load_asset('endface.png'), 0.85)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
topboards_mat = image_material('M_TopBoards', load_asset('topboards.png'), 0.6)
banner_mat = image_material('M_Banner', load_asset('banner.png'), 0.7)
hey_mat = image_material('M_Hey', load_asset('hey.png'), 0.8)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
bank_mat = image_material('M_Bank', painted('jm_bank', grass_bank_tex()), 0.95)
foliage = image_material('M_Foliage', painted('jm_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
brick = principled('M_Brick', (0.24, 0.10, 0.06), 0.9)
plaster = principled('M_Plaster', (0.52, 0.49, 0.44), 0.9)
villa_white = principled('M_VillaWhite', (0.72, 0.71, 0.67), 0.85)
stone_house = principled('M_StoneHouse', (0.44, 0.40, 0.33), 0.9)
tiles = principled('M_Tiles', (0.12, 0.06, 0.045), 0.8)
slate = principled('M_Slate', (0.07, 0.075, 0.085), 0.7)
dark_glass = principled('M_DarkGlass', (0.03, 0.035, 0.04), 0.15)
hut_beige = principled('M_HutBeige', (0.50, 0.45, 0.36), 0.85)
tarp_blue = principled('M_TarpBlue', (0.02, 0.10, 0.45), 0.7)
tent_red = principled('M_TentRed', (0.55, 0.03, 0.03), 0.7)
flag_yellow = principled('M_FlagYellow', (0.88, 0.62, 0.02), 0.8)
flag_blue = principled('M_FlagBlue', (0.012, 0.08, 0.50), 0.8)
CAR_COLS = [(0.75, 0.75, 0.74), (0.03, 0.03, 0.035), (0.25, 0.26, 0.28), (0.02, 0.05, 0.18), (0.45, 0.03, 0.02), (0.50, 0.50, 0.50)]
car_mats = [principled('M_Car%d' % i, c, 0.35) for i, c in enumerate(CAR_COLS)]


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

# the nets in Union's colours, as on the photos: broad slanting bands of
# yellow and blue cord; one picture covers 16 x 16 meshes (1.9 m)
NET_N = 16
net_tile = np.zeros((32 * NET_N, 32 * NET_N, 4), 'f')
_cy, _cx = np.mgrid[0:32 * NET_N, 0:32 * NET_N] // 32
_band = ((_cx + _cy) // 8) % 2 == 0
net_tile[..., :3] = np.where(_band[..., None], np.array((0.92, 0.70, 0.04), 'f'), np.array((0.03, 0.16, 0.62), 'f'))
_line = ((np.arange(32 * NET_N) % 32) < 3)
net_tile[_line, :, 3] = 1.0; net_tile[:, _line, 3] = 1.0
net_img = D.images.new('jm_net', 32 * NET_N, 32 * NET_N, alpha=True)
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
# and, under it, the ground inside the stands (tarmac, the roads behind the
# goals, the banks of grass in front of the ends); each gets its own picture
# with the sun baked in (below)
PITCH_X, PITCH_Y = 55.5, 36.6
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-PITCH_X, -PITCH_Y), (PITCH_X, -PITCH_Y), (PITCH_X, PITCH_Y), (-PITCH_X, PITCH_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.06, 0.20, 0.045), 0.85)])
FLOOR_Z = -0.05                  # under the pitch, far enough that the two never flicker
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
f = bm.faces.new([bm.verts.new((x, y, FLOOR_Z)) for x, y in ((FX0, FY0), (FX1, FY0), (FX1, FY1), (FX0, FY1))])
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.06, 0.06, 0.06), 0.9)])


# ================================================================ the straight stands
def stand_frame(a, b, nrm):
    a, b = Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0))
    return a, b, Vector((nrm[0], nrm[1], 0)).normalized()


def build_stand(name, a, b, nrm, t, base_z, kind, colour=None, bay=13.0, step_mat=(0, 1), ends=False):
    # a straight stand from a to b, its rows stepping back along nrm: treads
    # and risers, a stairway every `bay` metres (its step edges yellow),
    # seats, a handrail up each stairway
    a, b, nrm = stand_frame(a, b, nrm)
    L = (b - a).length
    tang = (b - a) / L
    nb = max(1, round(L / bay))
    steps, seats, rails, marks = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, r1, z = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1), t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        n = max(1, math.ceil(L / 3.0))
        for s in range(n):
            p0, p1 = a.lerp(b, s / n), a.lerp(b, (s + 1) / n)
            A0, A1, B0, B1 = p0 + nrm * r0, p1 + nrm * r0, p0 + nrm * r1, p1 + nrm * r1
            face(steps, [(A0.x, A0.y, z), (A1.x, A1.y, z), (B1.x, B1.y, z), (B0.x, B0.y, z)], UPV, step_mat[0])
            if z > z_prev + 0.01:
                face(steps, [(A0.x, A0.y, z_prev), (A1.x, A1.y, z_prev), (A1.x, A1.y, z), (A0.x, A0.y, z)], -nrm, step_mat[1])
        for i in range(1, nb):
            # the stairway's step edges, yellow
            c = a.lerp(b, i / nb)
            for dd, zz in ((r0, z), (r0 + t['depth'] / 2, z)):
                q0, q1 = c - tang * (AISLE_W / 2) + nrm * dd, c + tang * (AISLE_W / 2) + nrm * dd
                face(marks, [(q0.x, q0.y, zz + 0.006), (q1.x, q1.y, zz + 0.006), (q1.x + nrm.x * 0.07, q1.y + nrm.y * 0.07, zz + 0.006),
                             (q0.x + nrm.x * 0.07, q0.y + nrm.y * 0.07, zz + 0.006)], UPV, 0)
        if kind != 'seats':
            continue
        for i in range(nb):
            u0, u1 = i / nb, (i + 1) / nb
            c0 = u0 + (AISLE_W / 2 / L if i > 0 else 0.3 / L)
            c1 = u1 - (AISLE_W / 2 / L if i < nb - 1 else 0.3 / L)
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
    # the ends: walls down to the ground, stepping with the rows
    for p, sg in ((a, -1), (b, 1)) if ends else ():
        for k in range(t['rows']):
            r0, r1, z = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1), t['z'] + t['rise'] * k
            A, B = p + nrm * r0, p + nrm * r1
            face(steps, [(A.x, A.y, -0.1), (B.x, B.y, -0.1), (B.x, B.y, z), (A.x, A.y, z)], tang * sg, step_mat[1])
    return steps, seats, rails, marks


def main_colour(i, k, p):
    if MAIN_C + 2.0 < p.x < MAIN_C + 14.0 and 3 <= k <= 11:
        return S_MBLUE                               # the block of blue seats right of the middle
    if MAIN_C + 14.0 <= p.x < MAIN_C + 26.0 and k <= 2:
        return S_MBLUE
    return S_GREY if (k + i) % 6 else S_GREY2


t0 = time.time()
# the main stand: from the north-east tower to the south-west one, its rows back towards the street
st, se, ra, mk = build_stand('Main', (MAIN_X1, MAIN_Y), (MAIN_X0, MAIN_Y), (0, 1), MAIN, 1.2, 'seats', main_colour, bay=11.9)
new_obj('Steps_Main', st, '02_Bowl', [concrete, concrete_dark])
new_obj('Seats_Main', se, '03_Seats', seat_cols)
new_obj('Rails_Main', ra, '02_Bowl', [steel_grey])
new_obj('Marks_Main', mk, '02_Bowl', [yellow_paint])
# the park side: the standing terrace, its front walk level with the first step
st, se, ra, mk = build_stand('Park', (PX0, PARK_Y), (PX1, PARK_Y), (0, -1), PARK, PARK['z'], 'bare', bay=13.75, ends=True)
se.free()
new_obj('Steps_Park', st, '02_Bowl', [concrete, concrete_dark])
new_obj('Rails_Park', ra, '02_Bowl', [galv])
new_obj('Marks_Park', mk, '02_Bowl', [yellow_paint])
print('STRAIGHT STANDS %.0fs' % (time.time() - t0))


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


# ---------------------------------------------------------------- the main stand's walls, building, roof
# its white front (the dugouts' wall), the walkway behind the last row and the
# back with its windows up to the roof
bm = bmesh.new()
MA, MB = (MAIN_X1, MAIN_Y), (MAIN_X0, MAIN_Y)
strip(bm, MA, MB, 0.0, 0.0, 0.0, 1.2, (0, 1), 0, 'in')
strip(bm, MA, MB, 0.0, 1.2, MAIN['r'], 1.2, (0, 1), 0, 'up')
strip(bm, MA, MB, MAIN_BACK, MAIN_TOP, MAIN_BACK + 0.6, MAIN_TOP, (0, 1), 1, 'up')
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP, MAIN_BACK + 0.6, MAIN_TOP + 0.5, (0, 1), 0, 'in')
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP + 0.5, MAIN_BACK + 0.6, MAIN_TOP + 3.4, (0, 1), 2, 'in',
      uv=lambda u0, u1: [(u0 * 95.2 / 6, 0), (u1 * 95.2 / 6, 0), (u1 * 95.2 / 6, 1), (u0 * 95.2 / 6, 1)])
roof_at = lambda d: ROOF_U0 + (ROOF_U1 - ROOF_U0) * (d - ROOF_D0) / (ROOF_D1 - ROOF_D0)
strip(bm, MA, MB, MAIN_BACK + 0.6, MAIN_TOP + 3.4, MAIN_BACK + 0.6, roof_at(MAIN_BACK + 0.6), (0, 1), 1, 'in')
# the stand's two ends between the front and the towers: closed walls, white
for x_, sgn in ((MAIN_X1, 1), (MAIN_X0, -1)):
    prof = [(0.0, 0.0), (0.0, 2.2)] + [(MAIN['r'] + MAIN['depth'] * k, MAIN['z'] + MAIN['rise'] * k + 1.0) for k in range(MAIN['rows'])]
    prof += [(BLD_Y0 - MAIN_Y, roof_at(BLD_Y0 - MAIN_Y)), (BLD_Y0 - MAIN_Y, 0.0)]
    for j in range(1, len(prof) - 2):
        (da, za), (db, zb) = prof[j], prof[j + 1]
        for s_ in (sgn, -sgn):
            face(bm, [(x_, MAIN_Y + da, 0.0), (x_, MAIN_Y + db, 0.0), (x_, MAIN_Y + db, zb), (x_, MAIN_Y + da, za)], Vector((s_, 0, 0)), 0)
    face(bm, [(x_, MAIN_Y, 0.0), (x_, MAIN_Y + MAIN['r'], 0.0), (x_, MAIN_Y + MAIN['r'], 2.2), (x_, MAIN_Y, 2.2)], Vector((sgn, 0, 0)), 0)
new_obj('Main_Walls', bm, '02_Bowl', [white_paint, concrete, glazing])

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
face(bm, [(MAIN_X1, BLD_Y0, 0.0), (MAIN_X0, BLD_Y0, 0.0), (MAIN_X0, BLD_Y0, MAIN['z']), (MAIN_X1, BLD_Y0, MAIN['z'])], Vector((0, -1, 0)), 3)
new_obj('Building', bm, '02_Bowl', [facade_mat, endface_mat, concrete_light, brick])

# the roof: light underneath on dark trusses, green-grey on top, the blue
# edge along its front over the third row, on six columns among the seats
bm, tb = bmesh.new(), bmesh.new()
RA, RB = (MAIN_X1 + 0.4, MAIN_Y), (MAIN_X0 - 0.4, MAIN_Y)
BANDS = [ROOF_D0, ROOF_D0 + 3.6, ROOF_D0 + 7.2, ROOF_D1]
for j in range(len(BANDS) - 1):
    strip(bm, RA, RB, BANDS[j], roof_at(BANDS[j]), BANDS[j + 1], roof_at(BANDS[j + 1]), (0, 1), 0, 'down')
    strip(bm, RA, RB, BANDS[j], roof_at(BANDS[j]) + ROOF_TH, BANDS[j + 1], roof_at(BANDS[j + 1]) + ROOF_TH, (0, 1), 1, 'up')
strip(bm, RA, RB, ROOF_D0, roof_at(ROOF_D0) - 0.7, ROOF_D0, roof_at(ROOF_D0) + ROOF_TH + 0.1, (0, 1), 2, 'in')
strip(bm, RA, RB, ROOF_D0, roof_at(ROOF_D0) - 0.7, ROOF_D0 + 0.3, roof_at(ROOF_D0) - 0.7, (0, 1), 2, 'down')
for xe, sgn in ((RA[0], 1), (RB[0], -1)):
    face(bm, [(xe, MAIN_Y + ROOF_D0, roof_at(ROOF_D0) - 0.7), (xe, MAIN_Y + ROOF_D1, roof_at(ROOF_D1)),
              (xe, MAIN_Y + ROOF_D1, roof_at(ROOF_D1) + ROOF_TH), (xe, MAIN_Y + ROOF_D0, roof_at(ROOF_D0) + ROOF_TH + 0.1)], Vector((sgn, 0, 0)), 2)
nt = 16
for k in range(nt + 1):
    x_ = RA[0] + (RB[0] - RA[0]) * k / nt
    a_, b_ = Vector((x_, MAIN_Y + ROOF_D0 + 0.4, 0)), Vector((x_, MAIN_Y + ROOF_D1 - 0.3, 0))
    span_ = ROOF_D1 - ROOF_D0 - 0.7
    top_ = lambda t: roof_at(ROOF_D0 + 0.4 + span_ * t) + 0.02
    prism(tb, a_, b_, 0.3, top_, lambda t: top_(t) - 0.35 - 0.7 * t, 0)
    for j in range(5):
        t0_, t1_ = j / 5, (j + 1) / 5
        pa = a_.lerp(b_, t0_) + Vector((0, 0, top_(t0_) - 0.35 - 0.7 * t0_))
        pb = a_.lerp(b_, t1_) + Vector((0, 0, top_(t1_) - 0.1))
        tube(tb, pa, pb, 0.05, 0, 4, trim=0.05)
# the columns under its front edge
dcol = ROOF_D0 + 0.35
kcol = int((dcol - MAIN['r']) / MAIN['depth'])
zcol = MAIN['z'] + MAIN['rise'] * kcol
for j in range(1, 7):
    x_ = MAIN_X1 + (MAIN_X0 - MAIN_X1) * j / 7
    abox(tb, x_ - 0.17, x_ + 0.17, MAIN_Y + dcol - 0.17, MAIN_Y + dcol + 0.17, zcol, roof_at(dcol) - 0.05, 0, False, False)
new_obj('Roof', bm, '04_Roof', [roof_under_mat, roof_top, roof_blue])
new_obj('Roof_Trusses', tb, '04_Roof', [truss_mat])

# four blue frames of floodlights on the roof: two legs braced crosswise,
# stays back to the roof, a bar of lamps on top tilted at the pitch
bm = bmesh.new()
roof_top_at = lambda d: roof_at(d) + ROOF_TH
fwd = Vector((0, -math.cos(math.radians(34)), -math.sin(math.radians(34))))
side = Vector((1, 0, 0))
upl = side.cross(fwd).normalized()
if upl.z < 0:
    upl = -upl
for xc in (MAIN_C - 36.0, MAIN_C - 12.0, MAIN_C + 12.0, MAIN_C + 36.0):
    d_leg, h_ = 6.5, 8.5
    feet = [Vector((xc + s_ * 1.9, MAIN_Y + d_leg, roof_top_at(d_leg))) for s_ in (-1, 1)]
    tops = [Vector((xc + s_ * 1.6, MAIN_Y + d_leg - 0.8, roof_top_at(d_leg) + h_)) for s_ in (-1, 1)]
    for f_, t_ in zip(feet, tops):
        tube(bm, f_, t_, 0.11, 0, 6, step=3.0)
        tube(bm, t_, Vector((t_.x, MAIN_Y + d_leg + 5.5, roof_top_at(d_leg + 5.5))), 0.06, 0, 5)     # its stay
    for j in range(4):
        a1, a2 = feet[0].lerp(tops[0], j / 4), feet[1].lerp(tops[1], (j + 1) / 4)
        b1, b2 = feet[1].lerp(tops[1], j / 4), feet[0].lerp(tops[0], (j + 1) / 4)
        tube(bm, a1, a2, 0.04, 0, 4); tube(bm, b1, b2, 0.04, 0, 4)
    top = (tops[0] + tops[1]) / 2 + Vector((0, 0, 0.4))
    tube(bm, top - side * 3.4, top + side * 3.4, 0.10, 0, 6)
    for row_ in (0, 1):
        for j in range(7):
            c = top + side * (-3.0 + j) + Vector((0, -0.35, 0.3 + 0.62 * row_))
            obox(bm, c, fwd, side, upl, 0.24, 0.40, 0.29, 0)
            cc = c + fwd * 0.25
            face(bm, [cc - side * 0.34 - upl * 0.24, cc + side * 0.34 - upl * 0.24, cc + side * 0.34 + upl * 0.24, cc - side * 0.34 + upl * 0.24], fwd, 1)
# the tall green poles among the trees behind the terrace
POLES_PARK = [(-40.0, PBACK_Y - 7.0), (-14.0, PBACK_Y - 7.5), (14.0, PBACK_Y - 7.5), (42.0, PBACK_Y - 7.0)]
fwd2 = Vector((0, 0.86, -0.5)).normalized()
upl2 = side.cross(fwd2).normalized()
if upl2.z < 0:
    upl2 = -upl2
for px, py in POLES_PARK:
    tube(bm, Vector((px, py, 8.0)), Vector((px, py, 33.0)), 0.25, 2, 8, step=4.0)
    tube(bm, Vector((px - 1.0, py + 0.4, 33.2)), Vector((px + 1.0, py + 0.4, 33.2)), 0.08, 0, 5)
    for j in range(2):
        for r_ in range(4):
            c = Vector((px - 0.45 + 0.9 * j, py + 0.6, 30.6 + 0.75 * r_))
            obox(bm, c, fwd2, side, upl2, 0.25, 0.36, 0.3, 0)
            cc = c + fwd2 * 0.26
            face(bm, [cc - side * 0.3 - upl2 * 0.24, cc + side * 0.3 - upl2 * 0.24, cc + side * 0.3 + upl2 * 0.24, cc - side * 0.3 + upl2 * 0.24], fwd2, 1)
new_obj('Floodlights', bm, '04_Roof', [frame_blue, lamp, pole_green])
# flags along the street front, yellow and blue
bm = bmesh.new()
for j in range(9):
    x_ = BLD_X0 + 6.0 + (face_w - 12.0) * j / 8
    yp = BLD_Y1 - 0.3
    tube(bm, Vector((x_, yp, FACADE_H)), Vector((x_, yp, FACADE_H + 6.0)), 0.04, 0, 5)
    fl = [Vector((x_, yp, FACADE_H + 5.9)), Vector((x_ + 1.6, yp - 0.15, FACADE_H + 5.75)), Vector((x_ + 1.6, yp - 0.15, FACADE_H + 4.75)), Vector((x_, yp, FACADE_H + 4.9))]
    for sg in (1, -1):
        face(bm, fl if sg > 0 else fl[::-1], Vector((0, sg, 0)), 1 + j % 2)
new_obj('Flags', bm, '04_Roof', [steel_grey, flag_yellow, flag_blue])

# ---------------------------------------------------------------- the terrace on the park side
# its front: a black wall with two yellow gates and a steel cage in the middle,
# the walk behind it level with the first step
bm = bmesh.new()
PA, PB = (PX0, PARK_Y), (PX1, PARK_Y)
strip(bm, PA, PB, 0.0, -0.1, 0.0, PARK['z'] + 0.15, (0, -1), 0, 'in')
strip(bm, PA, PB, 0.0, PARK['z'] + 0.15, 0.25, PARK['z'] + 0.15, (0, -1), 0, 'up')
strip(bm, PA, PB, 0.25, PARK['z'], PARK['r'], PARK['z'], (0, -1), 1, 'up')
for xg in (-27.0, 27.0):
    # a yellow gate: its frame and its mesh
    yg = PARK_Y + 0.08
    for a, b in (((xg - 1.4, 0.0), (xg - 1.4, 2.3)), ((xg + 1.4, 0.0), (xg + 1.4, 2.3)), ((xg - 1.4, 2.3), (xg + 1.4, 2.3)), ((xg - 1.4, 0.9), (xg + 1.4, 0.9))):
        tube(bm, Vector((a[0], yg, a[1])), Vector((b[0], yg, b[1])), 0.05, 2, 5)
    for j in range(14):
        xw = xg - 1.4 + 2.8 * (j + 0.5) / 14
        tube(bm, Vector((xw, yg, 0.05)), Vector((xw, yg, 2.3)), 0.012, 3, 3)
abox(bm, -1.6, 1.6, PARK_Y - 0.1, PARK_Y + 1.6, 0.0, 2.4, 3, True, False)
# its top: a walk, the huts, the band on yellow posts, a green fence behind
strip(bm, PA, PB, PBACK, PTOP, PBACK + 3.4, PTOP, (0, -1), 1, 'up')
new_obj('Park_Front', bm, '02_Bowl', [black_wall, concrete, yellow_paint, galv])
bm = bmesh.new()
for k in range(2, PARK['rows'] - 1, 2):
    # the crush barriers: 3.6 m long, staggered every other row, posts at 1.8 m
    z = PARK['z'] + PARK['rise'] * k
    yb = PARK_Y - (PARK['r'] + PARK['depth'] * k + 0.12)
    nb = round((PX1 - PX0) / 13.75)
    aisles = [PX0 + (PX1 - PX0) * i / nb for i in range(1, nb)]
    x = PX0 + 0.6 + (2.5 if (k // 2) % 2 else 0.0)
    while x < PX1 - 1.0:
        x1 = min(x + 3.6, PX1 - 0.6)
        segs = [(x, x1)]
        for xa in aisles:
            segs = [piece for s0, s1 in segs for piece in ((s0, min(s1, xa - 0.8)), (max(s0, xa + 0.8), s1)) if piece[1] - piece[0] > 0.6]
        for s0, s1 in segs:
            tube(bm, Vector((s0, yb, z + 1.05)), Vector((s1, yb, z + 1.05)), 0.04, 0, 6, step=4.0)
            npst = max(1, round((s1 - s0) / 1.8))
            for j in range(npst + 1):
                xp = s0 + (s1 - s0) * j / npst
                tube(bm, Vector((xp, yb, z)), Vector((xp, yb, z + 1.05)), 0.03, 0, 5, step=4.0)
        x += 5.0
new_obj('Barriers_Park', bm, '02_Bowl', [galv])
bm = bmesh.new()
yband = PBACK_Y - 1.1
for j in range(17):
    x_ = -BAND_X + 2 * BAND_X * j / 16
    tube(bm, Vector((x_, yband - 0.15, PTOP)), Vector((x_, yband - 0.15, PTOP + 5.6)), 0.07, 0, 6, step=3.0)
tube(bm, Vector((-BAND_X, yband - 0.15, PTOP + 2.75)), Vector((BAND_X, yband - 0.15, PTOP + 2.75)), 0.05, 0, 5, step=4.0)
new_obj('Band_Posts', bm, '02_Bowl', [yellow_paint])
bm = bmesh.new()
nbs = 24
for s in range(nbs):
    x0_, x1_ = BAND_X - 2 * BAND_X * s / nbs, BAND_X - 2 * BAND_X * (s + 1) / nbs        # u against x: it reads from the pitch
    face(bm, [(x0_, yband, PTOP + 2.8), (x1_, yband, PTOP + 2.8), (x1_, yband, PTOP + 5.4), (x0_, yband, PTOP + 5.4)], Vector((0, 1, 0)), 0,
         [(s / nbs, 0), ((s + 1) / nbs, 0), ((s + 1) / nbs, 1), (s / nbs, 1)])
    face(bm, [(x0_, yband - 0.05, PTOP + 2.8), (x1_, yband - 0.05, PTOP + 2.8), (x1_, yband - 0.05, PTOP + 5.4), (x0_, yband - 0.05, PTOP + 5.4)], Vector((0, -1, 0)), 1)
new_obj('Band', bm, '02_Bowl', [banner_mat, steel_dark])
# the huts along the top, white and beige, two under blue tarpaulins
bm = bmesh.new()
HUTS = [(-31.5, 2.6, 0), (-28.2, 2.6, 0), (-17.0, 2.0, 1), (-12.6, 4.0, 2), (-8.2, 3.6, 2), (-3.4, 2.8, 1), (4.8, 1.8, 1), (13.0, 3.0, 0), (19.5, 2.2, 1), (27.0, 2.6, 0)]
for xh, wh, kind in HUTS:
    abox(bm, xh - wh / 2, xh + wh / 2, PBACK_Y - 3.2, PBACK_Y - 1.45, PTOP, PTOP + (2.0 if kind == 2 else 2.5), kind, True, False)
new_obj('Huts', bm, '02_Bowl', [hut_beige, white_paint, tarp_blue])
bm = bmesh.new()


def fence_line(bm, pts, h, every=2.4, wires=0.2, r=0.045):
    # a mesh fence on the feet `pts` (3D): posts, three rails, upright wires
    pts = [Vector(p) for p in pts]
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + (pts[i] - pts[i - 1]).length)
    L = cum[-1]
    if L < 0.3:
        return
    def P(u):
        j = max(1, min(len(pts) - 1, bisect.bisect_left(cum, u)))
        f_ = (u - cum[j - 1]) / max(1e-6, cum[j] - cum[j - 1])
        return pts[j - 1].lerp(pts[j], max(0.0, min(1.0, f_)))
    n = max(1, math.ceil(L / every))
    for k in range(n + 1):
        p = P(L * k / n)
        tube(bm, p, p + Vector((0, 0, h)), r, 0, 5, step=4.0)
    for hh in (0.15, h * 0.5, h):
        for i in range(len(pts) - 1):
            tube(bm, pts[i] + Vector((0, 0, hh)), pts[i + 1] + Vector((0, 0, hh)), 0.03, 0, 5, step=4.0)
    if wires:
        m = max(1, int(L / wires))
        for k in range(m):
            p = P(L * (k + 0.5) / m)
            tube(bm, p + Vector((0, 0, 0.15)), p + Vector((0, 0, h)), 0.011, 0, 3, step=5.0)


fence_line(bm, [(PX0 - 1.0, PBACK_Y - 3.4, PTOP), (PX1 + 1.0, PBACK_Y - 3.4, PTOP)], 1.8, wires=0.25)
new_obj('Park_Fence', bm, '02_Bowl', [fence_green])


# ================================================================ the half-round ends
def frame(pts, step=0.8):
    # a smooth line through the points (Catmull-Rom), a point every ~step m
    # with its tangent, its normal away from the pitch and its arc length
    P = [Vector((x, y, 0)) for x, y in pts]
    P = [P[0] * 2 - P[1]] + P + [P[-1] * 2 - P[-2]]
    Q = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        n = max(2, math.ceil((p2 - p1).length / step))
        for j in range(n):
            t = j / n
            Q.append(0.5 * ((2 * p1) + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (3 * p1 - p0 - 3 * p2 + p3) * t * t * t))
    Q.append(P[-2].copy())
    F, s = [], 0.0
    for i, q in enumerate(Q):
        a, b = Q[max(0, i - 1)], Q[min(len(Q) - 1, i + 1)]
        tg = (b - a).normalized()
        n = Vector((tg.y, -tg.x, 0))
        if n.dot(q) < 0:
            n = -n
        if i:
            s += (q - Q[i - 1]).length
        F.append((q, tg, n, s))
    return F


def curve_stand(F, t, wz, dlim, colour, aisles):
    # a seated end along the line F, its rows stepping out along the normals:
    # treads, risers, the ends and the back closed, seats one by one (each
    # its own colour), radial stairs at the arc lengths `aisles` with half
    # steps and yellow edges; dlim(point) is how far back the end reaches
    steps, seats, marks = bmesh.new(), bmesh.new(), bmesh.new()
    nF = len(F)
    rows_at = [max(0, min(t['rows'], int((dlim(F[i]) - t['r']) / t['depth'] + 1e-6))) for i in range(nF)]
    def at(i, d, z):
        q, _, n, _ = F[i]
        return (q.x + n.x * d, q.y + n.y * d, z)
    for i in range(nF - 1):
        nn = F[i][2] + F[i + 1][2]
        face(steps, [at(i, 0, -0.1), at(i + 1, 0, -0.1), at(i + 1, 0, wz), at(i, 0, wz)], -nn, 1)
        face(steps, [at(i, 0, wz), at(i + 1, 0, wz), at(i + 1, t['r'], wz), at(i, t['r'], wz)], UPV, 0)
    for i, sg in ((0, -1), (nF - 1, 1)):
        face(steps, [at(i, 0, -0.1), at(i, t['r'], -0.1), at(i, t['r'], wz), at(i, 0, wz)], F[i][1] * sg, 1)
    seat_n = 0
    for k in range(t['rows']):
        d0, d1 = t['r'] + t['depth'] * k, t['r'] + t['depth'] * (k + 1)
        z = t['z'] + t['rise'] * k
        zp = wz if k == 0 else z - t['rise']
        live = [rows_at[i] > k for i in range(nF)]
        nxt = [rows_at[i] > k + 1 for i in range(nF)]
        for i in range(nF - 1):
            if not (live[i] and live[i + 1]):
                continue
            nn = F[i][2] + F[i + 1][2]
            face(steps, [at(i, d0, z), at(i + 1, d0, z), at(i + 1, d1, z), at(i, d1, z)], UPV, 0)
            face(steps, [at(i, d0, zp), at(i + 1, d0, zp), at(i + 1, d0, z), at(i, d0, z)], -nn, 1)
            if not (nxt[i] and nxt[i + 1]):
                face(steps, [at(i, d1, z - 1.8), at(i + 1, d1, z - 1.8), at(i + 1, d1, z + 0.15), at(i, d1, z + 0.15)], nn, 1)
                face(steps, [at(i, d1 - 0.12, z + 0.15), at(i + 1, d1 - 0.12, z + 0.15), at(i + 1, d1, z + 0.15), at(i, d1, z + 0.15)], UPV, 1)
                face(steps, [at(i, d1 - 0.12, z), at(i + 1, d1 - 0.12, z), at(i + 1, d1 - 0.12, z + 0.15), at(i, d1 - 0.12, z + 0.15)], -nn, 1)
        for i in range(nF):
            if live[i] and (i == 0 or not live[i - 1]):
                face(steps, [at(i, d0, -0.1), at(i, d1, -0.1), at(i, d1, z), at(i, d0, z)], -F[i][1], 1)
            if live[i] and (i == nF - 1 or not live[i + 1]):
                face(steps, [at(i, d0, -0.1), at(i, d1, -0.1), at(i, d1, z), at(i, d0, z)], F[i][1], 1)
        idx = [i for i in range(nF) if live[i]]
        if len(idx) < 2:
            continue
        R0 = [Vector(at(i, d0, 0)) for i in idx]
        R1 = [Vector(at(i, d1, 0)) for i in idx]
        S = [F[i][3] for i in idx]
        cum = [0.0]
        for j in range(1, len(R0)):
            cum.append(cum[-1] + (R0[j] - R0[j - 1]).length)
        Lr = cum[-1]
        def along(u):
            j = max(1, min(len(cum) - 1, bisect.bisect_left(cum, u)))
            f_ = max(0.0, min(1.0, (u - cum[j - 1]) / max(1e-6, cum[j] - cum[j - 1])))
            return R0[j - 1].lerp(R0[j], f_), R1[j - 1].lerp(R1[j], f_), (R0[j] - R0[j - 1]).normalized()
        a_row = [float(np.interp(sa, S, cum)) for sa in aisles if S[0] + 1.0 < sa < S[-1] - 1.0]
        cuts = [0.2] + [v for a in a_row for v in (a - AISLE_W / 2, a + AISLE_W / 2)] + [Lr - 0.2]
        for u0, u1 in zip(cuts[0::2], cuts[1::2]):
            ns = int((u1 - u0) / SEAT_W)
            pad = ((u1 - u0) - ns * SEAT_W) / 2
            for q in range(ns):
                pf, pb, tg = along(u0 + pad + (q + 0.5) * SEAT_W)
                m = colour(k, seat_n, pf)
                seat_n += 1
                def A(tt, hh, sd):
                    p = pf.lerp(pb, tt) + tg * (sd * 0.22)
                    return (p.x, p.y, z + hh)
                back = pf - pb
                face(seats, [A(0.34, 0.42, -1), A(0.34, 0.42, 1), A(0.72, 0.42, 1), A(0.72, 0.42, -1)], UPV, m, [(0, 0.0), (1, 0.0), (1, 0.45), (0, 0.45)])
                face(seats, [A(0.72, 0.42, -1), A(0.72, 0.42, 1), A(0.78, 0.84, 1), A(0.78, 0.84, -1)], back, m, [(0, 0.45), (1, 0.45), (1, 0.95), (0, 0.95)])
                face(seats, [A(0.78, 0.84, -1), A(0.78, 0.84, 1), A(0.84, 0.84, 1), A(0.84, 0.84, -1)], UPV, m, [(0, 0.95), (1, 0.95), (1, 1.0), (0, 1.0)])
        for a in a_row:
            # the stair: a half step on the back half of the tread, both edges yellow
            pf, pb, tg = along(a)
            w = AISLE_W / 2 - 0.04
            def B(tt, hh, sd):
                p = pf.lerp(pb, tt) + tg * (sd * w)
                return (p.x, p.y, z + hh)
            hs = t['rise'] / 2
            face(steps, [B(0.5, hs, -1), B(0.5, hs, 1), B(1.0, hs, 1), B(1.0, hs, -1)], UPV, 0)
            face(steps, [B(0.5, 0, -1), B(0.5, 0, 1), B(0.5, hs, 1), B(0.5, hs, -1)], pf - pb, 1)
            for sd in (-1, 1):
                face(steps, [B(0.5, 0, sd), B(1.0, 0, sd), B(1.0, hs, sd), B(0.5, hs, sd)], tg * sd, 1)
            for tt, hh in ((0.0, 0.006), (0.5, hs + 0.006)):
                face(marks, [B(tt, hh, -1), B(tt, hh, 1), B(tt + 0.085, hh, 1), B(tt + 0.085, hh, -1)], UPV, 0)
    return steps, seats, marks, rows_at


def curve_colour(fade):
    yel, blu = (S_YEL_F, S_BLUE_F) if fade else (S_YEL, S_BLUE)
    def f(k, q, p):
        if k == 0:
            return blu                                # the front row blue, as on the photos
        h = (math.sin(p.x * 12.9898 + p.y * 78.233 + k * 37.719) * 43758.5453) % 1.0
        return blu if h < 0.24 else yel
    return f


t0 = time.time()
F_SW = frame(SW_FRONT)
F_NE = frame(NE_FRONT)
ne_dlim = lambda y: float(np.interp(-y, [-v[0] for v in NE_DEPTH], [v[1] for v in NE_DEPTH]))
CURVES = {}
for name, F_, dl, fade in (('SW', F_SW, lambda f_: CBACK + 0.01, False), ('NE', F_NE, lambda f_: ne_dlim(f_[0].y), True)):
    Ltot = F_[-1][3]
    na = max(2, round(Ltot / 11.0))
    aisles = [Ltot * (j + 0.5) / na for j in range(na)]
    st, se, mk, rows_at = curve_stand(F_, CURVE, CURVE_WZ, dl, curve_colour(fade), aisles)
    CURVES[name] = (F_, rows_at)
    new_obj('Steps_' + name, st, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, se, '03_Seats', seat_cols)
    new_obj('Marks_' + name, mk, '02_Bowl', [yellow_paint])
print('ENDS %.0fs' % (time.time() - t0))


def curve_back(F_, rows_at, i, extra=0.0):
    # the point at the top of an end behind its last row, and the height there
    q, _, n, _ = F_[i]
    k = rows_at[i]
    d = CURVE['r'] + CURVE['depth'] * k + extra
    return Vector((q.x + n.x * d, q.y + n.y * d, CURVE['z'] + CURVE['rise'] * (k - 1)))


# the away section: the park half of the south-west end, green fences along
# its front, up its side towards the home half and along its top
bm = bmesh.new()
F_, rows_at = CURVES['SW']
i_div = next(i for i, f_ in enumerate(F_) if f_[0].y < AWAY_Y)
fence_line(bm, [(f_[0].x + f_[2].x * 0.15, f_[0].y + f_[2].y * 0.15, CURVE_WZ) for f_ in F_[i_div::3]] +
           [(F_[-1][0].x + F_[-1][2].x * 0.15, F_[-1][0].y + F_[-1][2].y * 0.15, CURVE_WZ)], 2.5, every=2.5)
q, _, n, _ = F_[i_div]
side_pts = [(q.x + n.x * d, q.y + n.y * d, CURVE_WZ if d < CURVE['r'] else CURVE['z'] + CURVE['rise'] * min(CURVE['rows'] - 1, int((d - CURVE['r']) / CURVE['depth'])))
            for d in np.arange(0.2, CBACK, CURVE['depth'])]
fence_line(bm, side_pts, 2.6, every=1.64)
fence_line(bm, [tuple(curve_back(F_, rows_at, i, 0.9)) for i in range(i_div, len(F_), 3)], 2.4, every=2.5)
new_obj('Away_Fences', bm, '02_Bowl', [fence_green])

# the tops of both ends: a fence hung with boards; on the south-west one a
# TV scaffold and a grey cabin
bm, bb = bmesh.new(), bmesh.new()
for name in ('SW', 'NE'):
    F_, rows_at = CURVES[name]
    lo = i_div if name == 'SW' else 0
    pts = [tuple(curve_back(F_, rows_at, i, 2.2)) for i in range(0, len(F_), 3)]
    fence_line(bm, pts, 2.0, every=2.5, wires=0.3)
    if name == 'NE':
        pts = [p for p in pts if abs(p[1] - SCR_C.y) > SCR_W / 2 + 1.5]
    # boards on the fence, facing the pitch, 5 m each
    u = 0.0
    for j in range(len(pts) - 1):
        a, b = Vector(pts[j]), Vector(pts[j + 1])
        L = (b - a).length
        if L > 4.0:
            continue
        nrm = Vector((-(b - a).y, (b - a).x, 0)).normalized()
        if nrm.dot(-a) < 0:
            nrm = -nrm
        o = nrm * 0.08
        face(bb, [(a + o).to_tuple(), (b + o).to_tuple(), (b + o + Vector((0, 0, 1.2))).to_tuple(), (a + o + Vector((0, 0, 1.2))).to_tuple()], nrm, 0,
             [(u / 30.0, 0), ((u + L) / 30.0, 0), ((u + L) / 30.0, 1), (u / 30.0, 1)])
        u += L
new_obj('Top_Fences', bm, '02_Bowl', [galv])
new_obj('Top_Boards', bb, '02_Bowl', [topboards_mat])
bm = bmesh.new()
F_, rows_at = CURVES['SW']
i_tv = min(range(len(F_)), key=lambda i: abs(F_[i][0].y - 0.0))
p = curve_back(F_, rows_at, i_tv, 2.4)
n = F_[i_tv][2]; tg = F_[i_tv][1]
for sx in (-1, 1):
    for sd in (0, 1):
        c = p + tg * (sx * 1.2) + n * (sd * 2.2)
        tube(bm, c, c + Vector((0, 0, 4.2)), 0.05, 0, 5)
for hh in (1.4, 2.8, 4.2):
    for sd in (0, 1):
        c = p + n * (sd * 2.2) + Vector((0, 0, hh))
        tube(bm, c - tg * 1.2, c + tg * 1.2, 0.04, 0, 4)
box(bm, p + n * 1.1, tg, 1.45, n, 1.4, p.z + 4.2, p.z + 5.5, 1)
i_cab = min(range(len(F_)), key=lambda i: abs(F_[i][0].y + 14.0))
p = curve_back(F_, rows_at, i_cab, 3.0)
box(bm, p + F_[i_cab][2] * 1.3, F_[i_cab][1], 3.0, F_[i_cab][2], 1.3, p.z - 0.5, p.z + 2.6, 2)
new_obj('Top_Structures', bm, '02_Bowl', [galv, white_paint, principled('M_CabinGrey', (0.10, 0.11, 0.12), 0.7)])

# ---------------------------------------------------------------- the scoreboard over the north-east end
# a concrete base over the top row, the dark screen on it, its face the live
# screen (game.screen.js, style 'marien'); a camera pole beside it
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
right = (-SCR_N).cross(UPV).normalized()
bm = bmesh.new()
zb_ = SCR_C.z - SCR_H / 2
pc = SCR_C - SCR_N * 0.5
obox(bm, Vector((pc.x, pc.y, (CTOP - 1.0 + zb_ - 0.1) / 2)), SCR_N, right, UPV, 0.75, SCR_W / 2 + 0.9, (zb_ - 0.1 - CTOP + 1.0) / 2, 1)
obox(bm, SCR_C - SCR_N * 0.3, SCR_N, right, UPV, 0.28, SCR_W / 2 + 0.15, SCR_H / 2 + 0.15, 0)
for sx in (-1, 1):
    pp = SCR_C - SCR_N * 0.9 + right * sx * (SCR_W / 2 - 0.8)
    tube(bm, Vector((pp.x, pp.y, zb_ - 0.1)), Vector((pp.x, pp.y, SCR_C.z + SCR_H / 2 - 0.3)), 0.08, 2, 5)
    tube(bm, Vector((pp.x, pp.y, SCR_C.z + SCR_H / 2 - 0.3)), SCR_C - SCR_N * 0.45 + right * sx * (SCR_W / 2 - 0.8) + UPV * (SCR_H / 2 - 0.3), 0.06, 2, 5)
pole0 = SCR_C - SCR_N * 0.6 + right * (SCR_W / 2 + 1.6)
tube(bm, Vector((pole0.x, pole0.y, CTOP - 0.5)), Vector((pole0.x + 0.8, pole0.y, CTOP + 8.5)), 0.07, 2, 5)
box(bm, (pole0.x + 0.8, pole0.y), (1, 0), 0.25, (0, 1), 0.18, CTOP + 8.5, CTOP + 8.9, 3)
new_obj('Screen_Frame', bm, '04_Roof', [steel_dark, concrete_light, steel_grey, white_paint])
fb = bmesh.new()
c0 = SCR_C + SCR_N * 0.02
face(fb, [c0 - right * SCR_W / 2 - UPV * SCR_H / 2, c0 + right * SCR_W / 2 - UPV * SCR_H / 2,
          c0 + right * SCR_W / 2 + UPV * SCR_H / 2, c0 - right * SCR_W / 2 + UPV * SCR_H / 2], SCR_N, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
screen_face = new_obj('ScreenFace_0', fb, '04_Roof', [live])

# ---------------------------------------------------------------- the cloth on the bank: Let's go hey!
bm = bmesh.new()
A_, B_, C_, D_ = HEY
Q = lambda a, b: B_.lerp(A_, a).lerp(C_.lerp(D_, a), b)
want = (A_ - B_).cross(C_ - B_)
if want.z < 0:
    want = -want
for i in range(3):
    for j in range(8):
        face(bm, [Q(i / 3, j / 8), Q((i + 1) / 3, j / 8), Q((i + 1) / 3, (j + 1) / 8), Q(i / 3, (j + 1) / 8)], want, 0,
             [(i / 3, j / 8), ((i + 1) / 3, j / 8), ((i + 1) / 3, (j + 1) / 8), (i / 3, (j + 1) / 8)])
# its edge: a dark hem down into the bank
for a, b in ((B_, A_), (A_, D_), (D_, C_), (C_, B_)):
    o = ((a + b) / 2 - (A_ + B_ + C_ + D_) / 4)
    o.z = 0
    face(bm, [a, b, b - Vector((0, 0, 0.9)), a - Vector((0, 0, 0.9))], o, 1)
new_obj('Hey_Cloth', bm, '02_Bowl', [hey_mat, black_wall])

# ---------------------------------------------------------------- round the pitch: the boards, the dugouts, the low fences
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
    yb = MAIN_Y - 1.4
    face(bm, [(x0, yb - 2.0, 2.0), (x1, yb - 2.0, 2.0), (x1, yb, 2.3), (x0, yb, 2.3)], UPV, 3)
    face(bm, [(x0, yb - 2.0, 1.98), (x1, yb - 2.0, 1.98), (x1, yb, 2.28), (x0, yb, 2.28)], -UPV, 3)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.3), (x0, yb, 2.3)], Vector((0, -1, 0)), 2)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.0, 0.0), (x, yb, 0.0), (x, yb, 2.3), (x, yb - 2.0, 2.0)], Vector((1 if x == x0 else -1, 0, 0)), 3)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_grey, white_paint, dark_glass])
bm = bmesh.new()
# the low fences between the roads behind the goals and the banks of grass
fence_line(bm, [(-63.8, 26.0, 0.0), (-63.8, -33.0, 0.0), (-60.5, -38.6, 0.0)], 1.2, every=2.5, wires=0.25)
fence_line(bm, [(59.4, 33.0, 0.0), (59.4, -27.5, 0.0), (57.5, -38.6, 0.0)], 1.2, every=2.5, wires=0.25)
new_obj('Low_Fences', bm, '02_Bowl', [fence_green])
# cars parked on the south-west road, red tents on the north-east one, a blue skip
bm = bmesh.new()
crng = random.Random(7)
for j, yc in enumerate((-24.0, -17.5, 6.0, 18.5)):
    m = crng.randrange(len(CAR_COLS))
    xc = -61.6 + crng.uniform(-0.2, 0.2)
    box(bm, (xc, yc), (0, 1), 2.15, (1, 0), 0.88, 0.32, 0.92, m)
    box(bm, (xc, yc - 0.25), (0, 1), 1.15, (1, 0), 0.78, 0.92, 1.42, len(CAR_COLS))
    for wy in (-1.45, 1.35):
        for wx in (-0.8, 0.8):
            box(bm, (xc + wx, yc + wy), (0, 1), 0.33, (1, 0), 0.12, 0.0, 0.62, len(CAR_COLS))
for yc in (24.0, 28.0, 32.0):
    xc = 58.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            tube(bm, Vector((xc + sx * 1.45, yc + sy * 1.45, 0.0)), Vector((xc + sx * 1.45, yc + sy * 1.45, 2.1)), 0.03, len(CAR_COLS) + 1, 4)
    pk = Vector((xc, yc, 3.0))
    cn = [Vector((xc + sx * 1.5, yc + sy * 1.5, 2.1)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    for k in range(4):
        face(bm, [cn[k], cn[(k + 1) % 4], pk], (cn[k] + cn[(k + 1) % 4]) / 2 - Vector((xc, yc, 2.0)), len(CAR_COLS) + 2)
box(bm, (-60.0, -34.0), (1, 0), 1.9, (0, 1), 1.0, 0.0, 1.4, len(CAR_COLS) + 3)
new_obj('Cars_Tents', bm, '05_Outside', car_mats + [dark_glass, steel_grey, tent_red, tarp_blue])

# ================================================================ the ground: banks, the park's hill, the town
G_HALF = 320.0                   # tools/marien/ground.png covers 640 x 640 m round OpenStreetMap's origin
G_Z = -0.12


def curve_ground(F_, dl, x, y):
    # under an end a little below its rows, behind it level with its top for
    # a walk, then the park's slope; fading away past its ends
    best, bi = 1e18, 0
    for i in range(0, len(F_), 2):
        q = F_[i][0]
        dd = (x - q.x) ** 2 + (y - q.y) ** 2
        if dd < best:
            best, bi = dd, i
    q, tg, n, _ = F_[bi]
    d = (x - q.x) * n.x + (y - q.y) * n.y
    if d <= 0.0:
        return 0.0
    rows = max(1, min(CURVE['rows'], int((dl(F_[bi]) - CURVE['r']) / CURVE['depth'] + 1e-6)))
    back = CURVE['r'] + CURVE['depth'] * rows
    top = CURVE['z'] + CURVE['rise'] * (rows - 1)
    if d < back:
        z = CURVE['z'] + (d - CURVE['r']) / CURVE['depth'] * CURVE['rise'] - 1.3
    else:
        z = top - 0.12 + max(0.0, d - back - 4.0) * 0.16
    over = 0.0
    if bi in (0, len(F_) - 1) or bi >= len(F_) - 2:
        over = max(0.0, abs((x - q.x) * tg.x + (y - q.y) * tg.y) - 0.5)
    return max(0.0, z) * max(0.0, 1.0 - over / 10.0)


def park_ground(x, y):
    d = PARK_Y - y
    if d <= 0.0:
        return 0.0
    if d < PBACK:
        z = PARK['z'] + (d - PARK['r']) / PARK['depth'] * PARK['rise'] - 1.3
    else:
        z = PTOP - 0.12 + max(0.0, d - PBACK - 4.5) * 0.30
    over = max(0.0, x - PX1, PX0 - x)
    return max(0.0, z) * max(0.0, 1.0 - over / 30.0)


def hey_ground(x, y):
    # under the cloth just below it; round it falling away
    A_, B_, C_, D_ = HEY
    u, v = (A_ - B_), (C_ - B_)
    px, py = x - B_.x, y - B_.y
    det = u.x * v.y - u.y * v.x
    a = (px * v.y - py * v.x) / det
    b = (u.x * py - u.y * px) / det
    ac, bc = max(0.0, min(1.0, a)), max(0.0, min(1.0, b))
    z = B_.z + (C_.z - B_.z) * bc - 0.35
    out = math.hypot((a - ac) * u.length, (b - bc) * v.length)
    return max(0.0, z - out * 0.7)


def hey_under(x, y):
    # under the cloth: its height less a little, or None off it
    A_, B_, C_, D_ = HEY
    u, v = (A_ - B_), (C_ - B_)
    px, py = x - B_.x, y - B_.y
    det = u.x * v.y - u.y * v.x
    a = (px * v.y - py * v.x) / det
    b = (u.x * py - u.y * px) / det
    if -0.02 <= a <= 1.02 and -0.02 <= b <= 1.02:
        return B_.z + (C_.z - B_.z) * max(0.0, min(1.0, b)) - 0.35
    return None


def hz(x, y):
    if FX0 - 0.01 <= x <= FX1 + 0.01 and FY0 - 0.01 <= y <= FY1 + 0.01:
        return G_Z                                   # the floor's own
    hu = hey_under(x, y)
    if hu is not None:
        return max(0.0, hu) + G_Z
    z = max(park_ground(x, y), hey_ground(x, y),
            curve_ground(F_SW, lambda f_: CBACK + 0.01, x, y), curve_ground(F_NE, lambda f_: ne_dlim(f_[0].y), x, y))
    if y > 36.0:
        z *= max(0.0, 1 - (y - 36.0) / 10.0)        # the street side stays low
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
                 [((x - DX + G_HALF) / (2 * G_HALF), (y - DY + G_HALF) / (2 * G_HALF)) for x, y in q])


t0 = time.time()
inside_floor = lambda xa, xb, ya, yb: FX0 <= xa and xb <= FX1 and FY0 <= ya and yb <= FY1
bank = lambda x, y: 1 if hz(x, y) > 0.4 and y < 44 else 0
bm = bmesh.new()
ground_grid(bm, GX0, GX1, GY0, GY1, 2.5, inside_floor, bank)
new_obj('Ground', bm, '05_Outside', [ground_mat, bank_mat])
print('GROUND %.0fs' % (time.time() - t0))

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


VILLA = (-76.4, -65.2)                                # the white villa on the hill over the cloth


def in_stadium(x, y):
    if math.hypot(x - VILLA[0], y - VILLA[1]) < 12.0:
        return True
    return -93.0 < x < 82.0 and PBACK_Y - 4.5 < y < BLD_Y1 + 1.0


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


t0 = time.time()
bm = bmesh.new()
forest(bm, -135.0, 135.0, -135.0, 55.0, 9.0, lambda x, y: abs(x) < 135 and -135 < y < 55)
near_trees = new_obj('Trees_Near', bm, '06_Backdrop', [trunk, foliage])
print('TREES %.0fs' % (time.time() - t0))

# ================================================================ the backdrop: the park beyond and the town
bm = bmesh.new()
ground_grid(bm, -G_HALF, G_HALF, -G_HALF, G_HALF, 10.0, lambda xa, xb, ya, yb: GX0 <= xa and xb <= GX1 and GY0 <= ya and yb <= GY1)
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
    villa = math.hypot(cx_ - VILLA[0], cy_ - VILLA[1]) < 6.0
    if in_stadium(cx_, cy_) and not villa:
        continue
    h = {'garage': 3.0, 'garages': 3.0, 'shed': 2.6, 'kiosk': 3.0, 'roof': 4.0}.get(b['type'], 13.0 if area < 400 else 16.0)
    if cy_ < 44.0 + DY or any(inside_poly(cx_, cy_, g) for g in OSM['park']):
        h = min(h, 4.0)                              # the club's huts round the stadium and the park's pavilions: low
    if b['levels'] and h > 4.0:
        try:
            h = float(b['levels']) * 3.2 + 1.8
        except ValueError:
            pass
    if villa:
        h = 9.5
    z0 = min(hz(x, y) for x, y in pts)
    wall_m = 5 if villa else trng.choice((1, 1, 2, 3))
    for k in range(len(pts)):
        a_, c_ = pts[k], pts[(k + 1) % len(pts)]
        outv = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
        nz = max(1, math.ceil(h / 3.2))
        for q in range(nz):
            za, zb = z0 + h * q / nz, z0 + h * (q + 1) / nz
            face(bm, [(a_[0], a_[1], za), (c_[0], c_[1], za), (c_[0], c_[1], zb), (a_[0], a_[1], zb)], outv, wall_m)
    if villa:
        # its hipped roof of red tiles
        apex = Vector((cx_, cy_, z0 + h + 3.8))
        for k in range(len(pts)):
            a_, c_ = pts[k], pts[(k + 1) % len(pts)]
            ov = Vector(((c_[1] - a_[1]), -(c_[0] - a_[0]), 0)) * (1 if sarea > 0 else -1)
            face(bm, [(a_[0], a_[1], z0 + h), (c_[0], c_[1], z0 + h), apex.to_tuple()], ov.normalized() + UPV, 0)
        continue
    try:
        rf = bm.faces.new([bm.verts.new((x, y, z0 + h)) for x, y in pts])
    except ValueError:
        continue
    rf.material_index = 0 if trng.random() < 0.6 else 4
    rf.normal_update()
    if rf.normal.z < 0:
        rf.normal_flip()
    bmesh.ops.triangulate(bm, faces=[rf], quad_method='BEAUTY', ngon_method='EAR_CLIP')
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, plaster, stone_house, slate, villa_white])
bm = bmesh.new()
forest(bm, -G_HALF + 10, G_HALF - 10, -G_HALF + 10, G_HALF - 10, 14.0, lambda x, y: not (abs(x) < 135 and -135 < y < 55))
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
    preview('match', (0, 50.0, 13.0), (0, -18.0, 0), 50)
    preview('photo1', (-4.0, 37.0, 1.6), (-4.0, -45.0, 7.0), 56)            # 1.png: the terrace from the pitch
    preview('photo7', (-47.0, 38.5, 2.2), (-63.0, -40.0, 4.0), 42)          # 7.png: from the south-west corner, the cloth and the end
    preview('photo3', (-84.0, -4.0, 8.5), (30.0, 6.0, 0.0), 75)             # 3.png: from the top of the south-west end
    preview('north', (10.0, -44.0, 9.0), (75.0, 8.0, 8.0), 55)              # the north-east end and its scoreboard
    preview('street', (-14.0, BLD_Y1 + 6.7, 1.7), (6.0, BLD_Y1 - 0.8, 8.0), 70)
    preview('air', (-150.0, 230.0, 160.0), (-5.0, -5.0, 0.0), 34)          # 10.png: from over the town
    preview('air2', (190.0, 120.0, 120.0), (-20.0, -10.0, 0.0), 36)         # 2.png: from over the north-east corner
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
floor_light = bake_lightmap(floor, 840, 492)
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
    # Union's pitch as on the aerial photos: mown in squares of 8.75 x 8.5 m,
    # wear in the goalmouths and the centre
    bands_x = np.tanh(np.sin(np.pi * X / (PW / 12)) * 6)
    bands_y = np.tanh(np.sin(np.pi * Y / (PL / 8)) * 6)
    fine = rng.normal(0, 1, (H, W)).astype('f')
    shade = (1 + 0.13 * bands_x * bands_y + 0.03 * bands_x + 0.05 * vnoise(H, W, 400, 400) + 0.03 * vnoise(H, W, 48, 48)
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

# the floor picture: over the ground inside the stands: grass up to the
# boards, tarmac round it, behind the goals the roads and the banks of grass
# in front of the ends
H, W = 1198, 2048
X = (FX0 + (np.arange(W, dtype='f') + 0.5) / W * (FX1 - FX0))[None, :]
Y = (FY0 + (np.arange(H, dtype='f') + 0.5) / H * (FY1 - FY0))[:, None]
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.075, 0.075, 0.08)
alb *= (1 + 0.06 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 30, 30))[..., None]
sw_y = [p[1] for p in SW_FRONT][::-1]; sw_x = [p[0] for p in SW_FRONT][::-1]
ne_y = [p[1] for p in NE_FRONT][::-1]; ne_x = [p[0] for p in NE_FRONT][::-1]
x_sw = np.interp(Y, sw_y, sw_x)
x_ne = np.interp(Y, ne_y, ne_x)
green = np.array((0.055, 0.12, 0.035), 'f') * (1 + 0.10 * vnoise(H, W, 20, 20) + 0.08 * rng.normal(0, 1, (H, W)).astype('f'))[..., None]
road = np.array((0.10, 0.10, 0.105), 'f') * (1 + 0.05 * rng.normal(0, 1, (H, W)).astype('f'))[..., None]
bank_sw = (X < -63.8) & (X > x_sw - 0.2) & (Y < 26.0)
road_sw = (X >= -63.8) & (X < -57.4) & (Y < 30.0)
grass_sw = (X >= -57.4) & (X < -BOARD_X) & (np.abs(Y) < BOARD_Y)
bank_ne = (X > 59.4) & (X < x_ne + 0.2) & (Y < 33.0)
road_ne = (X <= 59.4) & (X > 56.6)
grass_ne = (X <= 56.6) & (X > BOARD_X) & (np.abs(Y) < BOARD_Y)
for m_, col in ((road_sw, road), (road_ne, road), (bank_sw, green), (bank_ne, green), (grass_sw, green), (grass_ne, green)):
    alb = np.where(m_[..., None], col, alb)
infield = (np.abs(X) < BOARD_X) & (np.abs(Y) < BOARD_Y)
alb = np.where(infield[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('jm_floor', alb, floor_light, H, W)
del alb, X, Y
floor.data.materials.clear(); floor.data.materials.append(image_material('M_Floor', floor_img, 0.9))

skip = ('Pitch_Lines', 'StadiumGoals', 'Ground_Far', 'Buildings', 'Trees_', 'ScreenFace_')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals, far_ground, buildings, far_trees, near_trees, screen_face]:
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
target.name = 'StadeJosephMarien'
select_only([far_ground, buildings, far_trees, near_trees], far_ground)
bpy.ops.object.join()
backdrop = far_ground
backdrop.name = 'StadiumBackdrop'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor', 'M_RoofLight'}


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
