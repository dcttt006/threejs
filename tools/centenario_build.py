# Builds the Estadio Centenario (Parque Batlle, Montevideo) from nothing and
# exports it for the game, the way the Philips Stadion and the Stade Joseph
# Marien are built; on an autumn afternoon, the sun low in the west-north-west
# behind the Tribuna América, the Olímpica and the Torre de los Homenajes in
# full light.
#   blender -b --factory-startup --python tools/centenario_build.py -- <out.blend> <out.glb> <texture dir> [quick [shot ...]]
#   quick: no light bakes and no export, only preview renders into <texture dir>
# The pictures it needs come from tools/centenario_assets.py, the plan from
# tools/centenario_osm.py.
#
# The facts and the plan:
#   - built for the first World Cup by Juan Antonio Scasso, opened on 18 July
#     1930; an elliptic bowl of four separate stands named after Uruguay's
#     triumphs: the Olímpica (east, three rings, the Torre de los Homenajes of
#     100 m at its back, the football museum under it), the América (west,
#     the lowest: two rings, in its middle the only roof, over the official
#     box, the VIP boxes and the press), the Colombes (north) and the
#     Amsterdam (south), three rings each, almost as tall as the Olímpica;
#     60.235 places
#   - the plan is OpenStreetMap's (relations 8725750, 8725752, 8725751,
#     8725754 for the stands, 8725748/8725749 for the plateas; way 179533172,
#     the pitch; data © OpenStreetMap contributors, ODbL), turned 59.11
#     degrees so the pitch lies on the axes. Every stand is an arc of a
#     circle: the long sides r 104 m about centres 23 m beyond the halfway
#     line, the ends r 77 and 71 m about centres 17 and 23 m beyond the goals,
#     each ending in a radial wall; their backs nearly one circle of 134 m,
#     the América's at 108 m
#   - in front of the long sides the plateas, straight rows of low seats down
#     to the walkway round the pitch: the Olímpica's dark grey, the América's
#     light blue, the players' tunnel through it; behind the goals the old
#     terraces of the taludes, closed since 1993, behind a fence
#   - the rings as on the photos of 2025: white seats on concrete steps whose
#     faces are painted in the blue and celeste chequerboard of 2021, sector
#     by sector, grey stairways between them, dark fronts with the mouths of
#     the vomitories; the América's official box in two blues, the press
#     boxes' dark band with ESTADIO CENTENARIO - 1930 and orange seats on its
#     balcony
#   - the Torre de los Homenajes: a concrete shaft with nine balconies
#     stepping in up both sides, the prow and the wings at its foot, the
#     bronze plaque MONTEVIDEO 1930 over the entrance, the flag on its mast
#   - the LED screen of 12.48 x 6.72 m (2021) on a steel table over the top
#     of the Colombes (game.screen.js, style 'centenario': MONUMENTO AL
#     FÚTBOL MUNDIAL - ESTADIO CENTENARIO, the crests, the score, the clock)
#   - four floodlight poles in the gaps between the stands
#   - the pitch 6 m below the park: the stands' backs rise 26 m over the
#     street, painted with the big murals of arcs in aqua, teal and slate, the
#     Olímpica's middle bare ribbed concrete round the tower, the América
#     light blue; round it Parque Batlle, the velodrome, the Hospital de Clínicas
# No sponsors: the boards carry the stadium's, the city's and the country's words.
#
# The helpers, the goals and the export are those of tools/philips_build.py;
# units are metres, x along the pitch towards the Colombes, y towards the
# América (the match camera's side), z up.
import bpy, bmesh, json, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

ARGS = sys.argv[sys.argv.index('--') + 1:]
OUT_BLEND, OUT_GLB, TEX_DIR = ARGS[:3]
QUICK = 'quick' in ARGS[3:]
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, 'centenario')
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
G_Z = 6.0                                   # the park round the stadium: the pitch lies 6 m below it
SEAT_W, AISLE_W = 0.48, 1.2
GAIN = 2.0                                  # the game draws the model unlit at this gain (catalog: look.gain)
OSM = json.load(open(os.path.join(ASSETS, 'osm.json')))
OUTLINE = OSM['stadium'][:-1] if OSM['stadium'][0] == OSM['stadium'][-1] else OSM['stadium']
FIELD = OSM['ways']['field'][:-1]           # the inner edge of the walkway round the pitch


def rows_of(rings, front_z, gap=2.2, step=1.3, top_walk=1.4):
    # a stand's section: a walk at its front, then the rings, each [rows,
    # first z, rise], a walkway between them whose next ring starts `step`
    # higher, the walk along the top; (d0, d1, z, kind, ring)
    out = [(0.0, 0.8, front_z, 'walk', 0)]
    d = 0.8
    for r, (n, z0, rise) in enumerate(rings):
        for k in range(n):
            out.append((d, d + 0.75, z0 + rise * k, 'seat', r + 1))
            d += 0.75
        last = z0 + rise * (n - 1)
        w = top_walk if r == len(rings) - 1 else gap
        out.append((d, d + w, last + 0.4, 'walk', r + 1))
        d += w
    return out


OLIM_ROWS = rows_of([(19, 6.4, 0.36), (19, 15.0, 0.40), (19, 23.9, 0.44)], 6.0)
END_ROWS = rows_of([(17, 5.2, 0.40), (16, 13.4, 0.45), (16, 21.95, 0.50)], 4.8)
AM_ROWS = rows_of([(13, 6.4, 0.40), (13, 13.0, 0.44)], 6.0, top_walk=1.6)
R_ = math.radians
STANDS = {
    'olimpica': dict(C=(0.0, 23.7), R0=104.3, a0=R_(-129.5), a1=R_(-51.1), rows=OLIM_ROWS, sectors=10, wall='olimpica'),
    'america': dict(C=(0.0, -22.6), R0=104.1, a0=R_(50.5), a1=R_(129.3), rows=AM_ROWS, wall='america',
                    bounds=[R_(a) for a in (50.5, 60.85, 71.2, 80.6, 90.0, 99.3, 108.7, 119.0, 129.3)]),
    'colombes': dict(C=(16.9, 0.0), R0=76.7, a0=R_(-45.3), a1=R_(45.1), rows=END_ROWS, sectors=8, wall='end'),
    'amsterdam': dict(C=(-23.3, 0.0), R0=71.0, a0=R_(131.4), a1=R_(228.0), rows=END_ROWS, sectors=8, wall='end'),
}
for _st in STANDS.values():
    if 'bounds' not in _st:
        _st['bounds'] = [_st['a0'] + (_st['a1'] - _st['a0']) * j / _st['sectors'] for j in range(_st['sectors'] + 1)]
    _st['d_end'] = _st['rows'][-1][1]
    _st['z_top'] = _st['rows'][-1][2]
PALCO = (R_(71.2), R_(108.7))               # the América's official box, VIP boxes and press, under the roof
TOWER = (0.0, -128.7)                       # the Torre de los Homenajes (OSM), at the Olímpica's back
SCR_W, SCR_H = 12.48, 6.72                  # the LED screen over the Colombes (Imply, 2021)
SCR_D, SCR_Z0 = 38.5, 33.4                  # its face's offset in the Colombes, its bottom edge
# the sun: an April afternoon in the west-north-west, 38 degrees up, behind
# the América and over the Colombes: the Olímpica and the tower in full sun,
# the pitch clear of shadow
SUN_AZ, SUN_EL = math.radians(39.1), math.radians(38)        # from the plan's x, towards y
TO_SUN = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL))).normalized()


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
    # a picture from tools/centenario as floats, row 0 at the top
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


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1930)


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
    t[:] = np.array(color, 'f') * np.linspace(0.82, 1.0, 32)[:, None, None]
    t[:, :2] *= 0.45; t[:, -2:] *= 0.45
    t[-2:] *= 1.06
    return t


def glazing_tex():
    # the VIP boxes' glass: dark, white frames every 1.5 m (u: 6 m)
    w, h = 384, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.03, 0.04, 0.05), 'f')
    t *= np.linspace(0.7, 1.5, h)[:, None, None]
    t[:, (np.arange(w) % 96) < 4] = (0.62, 0.63, 0.62)
    t[:6] = (0.62, 0.63, 0.62); t[-6:] = (0.62, 0.63, 0.62)
    return t


def ribbed_tex():
    # the Olímpica's back round the tower: bare concrete in panels between
    # pilasters every 6 m, a band of windows and doors at the street, the
    # merlons along the top (12 m wide, 28 m tall from the street; row 0 the bottom)
    w, h = 384, 896
    t = np.ones((h, w, 3), 'f') * np.array((0.42, 0.41, 0.385), 'f')
    t *= (1 + 0.05 * vnoise(h, w, 24, 24) + 0.03 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    x = np.arange(w)
    pil = ((x % 192) < 22)
    t[:, pil] *= 1.18
    t[:, ((x % 192) >= 22) & ((x % 192) < 26)] *= 0.62
    # the board marks of the formwork
    t[(np.arange(h) % 24) < 1] *= 0.9
    # the street floor: grey render, windows, red signs
    base = int(7.8 / 28 * h)
    t[:base] = (0.36, 0.36, 0.35)
    for xx in range(14, w, 48):
        t[int(0.10 * h):int(0.16 * h), xx:xx + 28] = (0.05, 0.06, 0.07)
    t[int(0.19 * h):int(0.22 * h), 60:180] = (0.62, 0.05, 0.05)
    t[int(0.19 * h):int(0.22 * h), 252:372] = (0.62, 0.05, 0.05)
    t[base:base + 6] = (0.30, 0.30, 0.29)
    return t


def foliage_tex():
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.05, 0.085, 0.03), 'f')
    t *= (1 + 0.35 * vnoise(h, w, 6, 6) + 0.2 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    return np.clip(t, 0, 1)


def terrace_tex():
    # the closed taludes: old weathered concrete, grass in the joints (u, v: 4 m)
    w, h = 128, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.30, 0.29, 0.26), 'f')
    t *= (1 + 0.12 * vnoise(h, w, 12, 12) + 0.06 * rng.normal(0, 1, (h, w)).astype('f'))[..., None]
    g = vnoise(h, w, 9, 9) > 0.55
    t[g] = t[g] * 0.5 + np.array((0.08, 0.13, 0.04), 'f') * 0.5
    return np.clip(t, 0, 1)


# the seats: white on the rings, the plateas' dark grey and light blue, the
# official box in two blues, the press balcony orange
SEATS = [(0.60, 0.66, 0.72), (0.52, 0.58, 0.64),          # 0, 1: white, weathered, a little blue in the shade
         (0.046, 0.052, 0.062),                           # 2: the Platea Olímpica: dark grey
         (0.11, 0.31, 0.62),                              # 3: the Platea América: light blue
         (0.022, 0.10, 0.40), (0.12, 0.33, 0.66),         # 4, 5: the official box: blue and light blue
         (0.70, 0.15, 0.03)]                              # 6: the press balcony: orange
WHITE1, WHITE2, PGREY, PBLUE, BOX1, BOX2, ORANGE = range(7)
seat_cols = [image_material('M_Seat%d' % i, painted('ce_seat%d' % i, seat_tile(c)), 0.6) for i, c in enumerate(SEATS)]
concrete = principled('M_Concrete', (0.36, 0.355, 0.34), 0.9)              # the treads
concrete_dark = principled('M_ConcreteDark', (0.25, 0.245, 0.235), 0.9)
concrete_light = principled('M_ConcreteLight', (0.50, 0.495, 0.47), 0.85)  # stairways, parapets, walls
celeste = principled('M_Celeste', (0.16, 0.42, 0.78), 0.8)                 # the chequerboard of 2021
azul = principled('M_Azul', (0.035, 0.13, 0.46), 0.8)
tread_cel = principled('M_TreadCeleste', (0.20, 0.42, 0.70), 0.85)           # the treads of the painted sectors
tread_azu = principled('M_TreadAzul', (0.06, 0.17, 0.46), 0.85)
front_dark = principled('M_FrontDark', (0.035, 0.037, 0.04), 0.8)          # the rings' fronts
portal = principled('M_Portal', (0.012, 0.012, 0.014), 0.95)
white_paint = principled('M_WhitePaint', (0.72, 0.72, 0.70), 0.7)
galv = principled('M_Galvanised', (0.44, 0.45, 0.46), 0.5)
steel_dark = principled('M_SteelDark', (0.03, 0.032, 0.036), 0.6)
steel_grey = principled('M_SteelGrey', (0.32, 0.33, 0.34), 0.5)
tower_mat = principled('M_Tower', (0.44, 0.43, 0.40), 0.85)
tower_dark = principled('M_TowerDark', (0.03, 0.03, 0.033), 0.9)
lamp = principled('M_FloodLight', (0.80, 0.81, 0.79), 0.3)
lamp_glass = principled('M_LampGlass', (0.90, 0.90, 0.86), 0.2)
brick_red = principled('M_BrickRed', (0.30, 0.09, 0.05), 0.9)
roof_mat = principled('M_RoofFlat', (0.20, 0.205, 0.21), 0.8)
glazing = image_material('M_Glazing', painted('ce_glazing', glazing_tex()), 0.2)
ribbed = image_material('M_Ribbed', painted('ce_ribbed', ribbed_tex()), 0.85)
terrace = image_material('M_Terrace', painted('ce_terrace', terrace_tex()), 0.95)
mural_mat = image_material('M_Mural', load_asset('mural.png'), 0.8)
mural_ends = image_material('M_MuralEnds', load_asset('mural_ends.png'), 0.8)
america_mat = image_material('M_AmericaWall', load_asset('america.png'), 0.8)
press_mat = image_material('M_Press', load_asset('press.png'), 0.6)
plaque_mat = image_material('M_Plaque', load_asset('plaque.png'), 0.5)
boards_mat = image_material('M_Boards', load_asset('boards.png'), 0.6)
flag_mat = image_material('M_Flag', load_asset('flag.png'), 0.8)
ground_mat = image_material('M_Ground', load_asset('ground.png'), 0.95)
foliage = image_material('M_Foliage', painted('ce_foliage', foliage_tex()), 0.95)
trunk = principled('M_Trunk', (0.10, 0.08, 0.06), 0.9)
plaster = principled('M_Plaster', (0.56, 0.53, 0.48), 0.9)
brick = principled('M_Brick', (0.24, 0.12, 0.08), 0.9)
tiles = principled('M_Tiles', (0.22, 0.08, 0.05), 0.8)
tiles_dark = principled('M_TilesDark', (0.06, 0.06, 0.065), 0.7)
flat_roof = principled('M_FlatRoof', (0.13, 0.13, 0.135), 0.9)
office_wall = principled('M_OfficeWall', (0.50, 0.48, 0.44), 0.7)


def windows_tex():
    # the tall buildings (the Hospital de Clínicas): beige concrete, a window
    # every 3 m on every floor (u: 12 m, v: 12 m, four floors)
    w, h = 256, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.50, 0.46, 0.38), 'f')
    for fy in range(4):
        y0 = fy * 64 + 22
        for fx in range(4):
            x0 = fx * 64 + 14
            t[y0:y0 + 26, x0:x0 + 36] = (0.07, 0.08, 0.09)
    return t


tower_block = image_material('M_TowerBlock', painted('ce_windows', windows_tex()), 0.8)
brick_light = principled('M_BrickLight', (0.40, 0.30, 0.22), 0.9)


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
net_img = D.images.new('ce_net', 32 * NET_N, 32 * NET_N, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/ce_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
# the two floors the game sees: the pitch (grass, lines, up to the boards)
# and, under it, the ground inside the bowl (the grass round the pitch, the
# walkway, the earth in front of the taludes); each gets its own picture
# with the sun baked in
PITCH_X, PITCH_Y = 55.5, 36.6
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-PITCH_X, -PITCH_Y), (PITCH_X, -PITCH_Y), (PITCH_X, PITCH_Y), (-PITCH_X, PITCH_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.06, 0.20, 0.045), 0.85)])
FLOOR_Z = -0.05
FX0, FX1, FY0, FY1 = -100.0, 100.0, -86.0, 86.0
bm = bmesh.new()
uv = bm.loops.layers.uv.new('UVMap')
f = bm.faces.new([bm.verts.new((x, y, FLOOR_Z)) for x, y in ((FX0, FY0), (FX1, FY0), (FX1, FY1), (FX0, FY1))])
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
floor = new_obj('Floor', bm, '01_Pitch', [principled('M_FloorBase', (0.30, 0.30, 0.29), 0.9)])


# ================================================================ the stands: four arcs
def AP(st, th, d, z=0.0):
    c, r = st['C'], st['R0'] + d
    return Vector((c[0] + r * math.cos(th), c[1] + r * math.sin(th), z))


def arc_steps(th0, th1, r, step=3.0):
    n = max(1, math.ceil(abs(th1 - th0) * r / step))
    return [th0 + (th1 - th0) * k / n for k in range(n + 1)]


def in_palco(th):
    return PALCO[0] - 1e-6 <= th <= PALCO[1] + 1e-6


def seat_geo(bm, pa, pb, back, m, q, q1, cush=0.36, top=0.50, fwd=0.44):
    def at(t, hgt, k):
        return pa[k].lerp(pb[k], t) + Vector((0, 0, hgt))
    face(bm, [at(fwd, cush, 0), at(fwd, cush, 1), at(0.72, cush, 1), at(0.72, cush, 0)], UPV, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
    face(bm, [at(0.72, cush, 0), at(0.72, cush, 1), at(0.78, top, 1), at(0.78, top, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])



SEAT_COUNT = {}
LEG_SPOTS = []                       # the scoreboard's legs: no seats there (filled below)


def no_seat(name, st, th, d, p):
    if name == 'olimpica' and abs(p.x - TOWER[0]) < 4.6 and d > 43.0:
        return True                  # the tower stands in the top rows
    if name == 'colombes' and any((p - q).length < 0.7 for q in LEG_SPOTS):
        return True
    return False


def build_stand(name, st):
    steps, seats, stairs, dark, rails = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    rows = st['rows']
    bounds = st['bounds']
    nsec = len(bounds) - 1
    lift = Vector((0, 0, 0.012))
    count = 0
    for k, (d0, d1, z, kind, ring) in enumerate(rows):
        zp = rows[k - 1][2] if k else z
        is_front = k > 1 and rows[k - 1][3] == 'walk' and kind == 'seat'      # the front of a ring over a walkway
        first_in_ring = kind == 'seat' and rows[k - 1][3] == 'walk'
        row_in_ring = 0
        kk = k
        while kk > 0 and rows[kk - 1][3] == 'seat':
            kk -= 1; row_in_ring += 1
        for j in range(nsec):
            th0, th1 = bounds[j], bounds[j + 1]
            mid_th = (th0 + th1) / 2
            if name == 'america' and ring >= 2 and in_palco(mid_th):
                continue                                    # the VIP boxes and the press building stand here
            r0 = st['R0'] + d0
            ha = (AISLE_W / 2) / r0                         # half the stairway, as an angle
            a_l = th0 + (ha if j > 0 else 0.0)
            a_r = th1 - (ha if j < nsec - 1 else 0.0)
            # the colour of the step faces: the chequerboard, sector by sector, ring by ring;
            # the ends' second ring bare concrete in its two corner sectors, without seats
            paint = 'cel' if (j + ring) % 2 == 0 else 'azu'
            bare = name in ('colombes', 'amsterdam') and ring == 2 and j in (0, nsec - 1)
            if bare:
                paint = 'bare'
            pieces = []
            if j > 0:
                pieces.append((th0, a_l, 'aisle'))
            pieces.append((a_l, a_r, 'body'))
            if j < nsec - 1:
                pieces.append((a_r, th1, 'aisle'))
            for pa_, pb_, what in pieces:
                ths = arc_steps(pa_, pb_, r0)
                for t0, t1 in zip(ths, ths[1:]):
                    A0, A1, B0, B1 = AP(st, t0, d0), AP(st, t1, d0), AP(st, t0, d1), AP(st, t1, d1)
                    out = (A0 + A1) / 2 - Vector((st['C'][0], st['C'][1], 0))
                    if what == 'aisle' and kind == 'seat':
                        # a stairway: a half step on the back half of each tread, light concrete
                        M0, M1 = A0.lerp(B0, 0.5), A1.lerp(B1, 0.5)
                        hs = min(0.2, (z - zp) / 2) if z > zp + 0.05 else 0.0
                        face(stairs, [A0 + Vector((0, 0, z)), A1 + Vector((0, 0, z)), M1 + Vector((0, 0, z)), M0 + Vector((0, 0, z))], UPV, 0)
                        face(stairs, [M0 + Vector((0, 0, z + hs)), M1 + Vector((0, 0, z + hs)), B1 + Vector((0, 0, z + hs)), B0 + Vector((0, 0, z + hs))], UPV, 0)
                        if hs:
                            face(stairs, [M0 + Vector((0, 0, z)), M1 + Vector((0, 0, z)), M1 + Vector((0, 0, z + hs)), M0 + Vector((0, 0, z + hs))], -out, 1)
                        if z > zp + 0.01:
                            face(stairs, [A0 + Vector((0, 0, zp)), A1 + Vector((0, 0, zp)), A1 + Vector((0, 0, z)), A0 + Vector((0, 0, z))], -out, 1)
                        continue
                    tmat = (6 if paint == 'cel' else 7 if paint == 'azu' else 0) if kind == 'seat' else 0
                    face(steps, [A0 + Vector((0, 0, z)), A1 + Vector((0, 0, z)), B1 + Vector((0, 0, z)), B0 + Vector((0, 0, z))], UPV, tmat)
                    if z > zp + 0.01:
                        mat = 3 if is_front else (4 if paint == 'cel' else 5 if paint == 'azu' else 1) if kind == 'seat' else 1
                        face(steps, [A0 + Vector((0, 0, zp)), A1 + Vector((0, 0, zp)), A1 + Vector((0, 0, z)), A0 + Vector((0, 0, z))], -out, mat)
            if kind != 'seat' or bare:
                continue
            # the mouths of the vomitories: the first two rows of the second
            # and third rings in the middle of every sector
            mouth = ring >= 2 and row_in_ring <= 1 and not (name == 'america' and in_palco(mid_th))
            hm = (1.1 / r0)
            # the seats
            arc_len = (a_r - a_l) * r0
            nseat = int(arc_len / SEAT_W)
            if nseat < 1:
                continue
            pad = (arc_len - nseat * SEAT_W) / 2 / r0
            back = None
            mats = []
            for q in range(nseat):
                th = a_l + pad + (q + 0.5) * SEAT_W / r0
                p = AP(st, th, (d0 + d1) / 2)
                if mouth and abs(th - mid_th) < hm:
                    mats.append('dark'); continue
                if no_seat(name, st, th, d0, p):
                    mats.append(None); continue
                h = (k * 73856093) ^ (j * 19349663) ^ (q * 83492791)
                if name == 'america' and ring == 1 and in_palco(th):
                    mats.append(BOX1 if h % 3 else BOX2)
                else:
                    mats.append(WHITE1 if h % 4 else WHITE2)
            # the dark mouths
            q = 0
            while q < nseat:
                if mats[q] != 'dark':
                    q += 1; continue
                q1 = q
                while q1 < nseat and mats[q1] == 'dark':
                    q1 += 1
                t0, t1 = a_l + pad + q * SEAT_W / r0, a_l + pad + q1 * SEAT_W / r0
                A0, A1, B0, B1 = (AP(st, t, dd) for t, dd in ((t0, d0), (t1, d0), (t0, d1), (t1, d1)))
                out = (A0 + A1) / 2 - Vector((st['C'][0], st['C'][1], 0))
                face(dark, [A0 + Vector((0, 0, z)) + lift, A1 + Vector((0, 0, z)) + lift, B1 + Vector((0, 0, z)) + lift, B0 + Vector((0, 0, z)) + lift], UPV, 0)
                face(dark, [A0 + Vector((0, 0, zp)) - out.normalized() * 0.01, A1 + Vector((0, 0, zp)) - out.normalized() * 0.01,
                            A1 + Vector((0, 0, z)) - out.normalized() * 0.01, A0 + Vector((0, 0, z)) - out.normalized() * 0.01], -out, 0)
                if row_in_ring == 1:
                    for t in (t0, t1):
                        g = AP(st, t, d1, z)
                        tube(rails, g, g + Vector((0, 0, 1.0)), 0.035, 0, 5)
                    tube(rails, AP(st, t0, d1, z + 1.0), AP(st, t1, d1, z + 1.0), 0.035, 0, 5)
                q = q1
            q = 0
            while q < nseat:
                m = mats[q]
                if m is None or m == 'dark':
                    q += 1; continue
                q1 = q + 2 if q + 1 < nseat and mats[q + 1] == m else q + 1
                ts = [a_l + pad + qq * SEAT_W / r0 for qq in (q, q1)]
                pa = [AP(st, t, d0, z) for t in ts]
                pb = [AP(st, t, d1, z) for t in ts]
                back = ((pb[0] + pb[1]) / 2 - (pa[0] + pa[1]) / 2).normalized()
                if m in (BOX1, BOX2):
                    seat_geo(seats, pa, pb, back, m, q, q1, cush=0.44, top=0.92, fwd=0.30)
                else:
                    seat_geo(seats, pa, pb, back, m, q, q1)
                count += q1 - q
                q = q1
    # the handrails down the middle of every stairway
    for j in range(1, nsec):
        th = bounds[j]
        for ring in range(1, 4):
            rr = [r for r in rows if r[3] == 'seat' and r[4] == ring]
            if len(rr) < 4 or (name == 'america' and ring >= 2 and in_palco(th)):
                continue
            a_, b_ = rr[1], rr[-1]
            pa_, pb_ = AP(st, th, (a_[0] + a_[1]) / 2, a_[2] + 0.95), AP(st, th, (b_[0] + b_[1]) / 2, b_[2] + 0.95)
            tube(rails, pa_, pb_, 0.03, 0, 6, step=3.0)
            for r_ in rr[1::5]:
                pp = AP(st, th, (r_[0] + r_[1]) / 2, r_[2])
                tube(rails, pp, pp + Vector((0, 0, 0.95)), 0.025, 0, 5)
    SEAT_COUNT[name] = count
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark, concrete_light, front_dark, celeste, azul, tread_cel, tread_azu])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Stairs_' + name, stairs, '02_Bowl', [concrete_light, concrete])
    new_obj('Mouths_' + name, dark, '02_Bowl', [portal])
    new_obj('Rails_' + name, rails, '02_Bowl', [galv])


def top_z(st, d):
    # the height of the stand's surface at offset d (its treads)
    zz = st['rows'][0][2]
    for d0, d1, z, kind, ring in st['rows']:
        if d0 - 1e-6 <= d:
            zz = z
    return zz


# the scoreboard's legs on the Colombes' top rows (they keep their spots free of seats)
for ly in (-5.8, 0.0, 5.8):
    for dd in (SCR_D + 0.4, SCR_D + 2.4):
        th = math.atan2(ly, STANDS['colombes']['R0'] + dd)
        LEG_SPOTS.append(AP(STANDS['colombes'], th, dd))

t0 = time.time()
for name, st in STANDS.items():
    build_stand(name, st)
print('STANDS %.0fs' % (time.time() - t0), SEAT_COUNT)

# the walls of every stand: its front over the platea or the talud, the
# parapet along its top, its two radial ends stepping with the rows, its back
# to the street (the murals; the Olímpica's ribbed concrete round the tower;
# the América light blue)
walls, outside = bmesh.new(), bmesh.new()
for name, st in STANDS.items():
    a0, a1, R0 = st['a0'], st['a1'], st['R0']
    zf = st['rows'][0][2]
    ths = arc_steps(a0, a1, R0)
    for t0, t1 in zip(ths, ths[1:]):
        A0, A1 = AP(st, t0, 0.0), AP(st, t1, 0.0)
        out = (A0 + A1) / 2 - Vector((st['C'][0], st['C'][1], 0))
        face(walls, [A0, A1, A1 + Vector((0, 0, zf + 1.05)), A0 + Vector((0, 0, zf + 1.05))], -out, 1)
        face(walls, [A0 + Vector((0, 0, zf + 1.05)), A1 + Vector((0, 0, zf + 1.05)), AP(st, t1, 0.25, zf + 1.05), AP(st, t0, 0.25, zf + 1.05)], UPV, 1)
    de = st['d_end']
    zt = st['z_top']
    ths = arc_steps(a0, a1, R0 + de)
    cum = 0.0
    for t0, t1 in zip(ths, ths[1:]):
        if name == 'america' and in_palco((t0 + t1) / 2):
            continue
        P0, P1 = AP(st, t0, de), AP(st, t1, de)
        out = (P0 + P1) / 2 - Vector((st['C'][0], st['C'][1], 0))
        face(walls, [P0 + Vector((0, 0, zt)), P1 + Vector((0, 0, zt)), P1 + Vector((0, 0, zt + 1.1)), P0 + Vector((0, 0, zt + 1.1))], -out, 1)
        Q0, Q1 = AP(st, t0, de + 0.3), AP(st, t1, de + 0.3)
        face(walls, [P0 + Vector((0, 0, zt + 1.1)), P1 + Vector((0, 0, zt + 1.1)), Q1 + Vector((0, 0, zt + 1.1)), Q0 + Vector((0, 0, zt + 1.1))], UPV, 1)
        L = (Q1 - Q0).length
        H = zt + 1.1
        mx = (Q0.x + Q1.x) / 2
        if st['wall'] == 'olimpica' and abs(mx) < 46.0:
            mat, uw, vh = 1, 12.0, 28.0
        elif st['wall'] == 'olimpica' or st['wall'] == 'end':
            mat, uw, vh = (2 if st['wall'] == 'olimpica' else 3), 48.0, 26.0
        else:
            mat, uw, vh = 4, 12.0, 20.0
        nz = max(1, math.ceil(H / 4.0))
        for q in range(nz):
            za, zb = H * q / nz, H * (q + 1) / nz
            face(outside, [Q0 + Vector((0, 0, za)), Q1 + Vector((0, 0, za)), Q1 + Vector((0, 0, zb)), Q0 + Vector((0, 0, zb))], out, mat,
                 [(cum / uw, (za - G_Z) / vh), ((cum + L) / uw, (za - G_Z) / vh), ((cum + L) / uw, (zb - G_Z) / vh), (cum / uw, (zb - G_Z) / vh)])
        cum += L
    # the radial ends: a wall stepping up with the rows, closed down to the ground
    for th, sg in ((a0, -1), (a1, 1)):
        tg = Vector((-math.sin(th), math.cos(th), 0)) * sg
        ds = [0.0]
        for d0, d1, z, kind, ring in st['rows']:
            ds += [d0, d1]
        ds = sorted(set(round(v, 3) for v in ds + [de + 0.3]))
        for da, db in zip(ds, ds[1:]):
            za, zb = top_z(st, da + 1e-4) + 1.05, top_z(st, da + 1e-4) + 1.05
            pa, pb = AP(st, th, da), AP(st, th, db)
            for s in (-1, 1):
                o = tg * 0.15 * s
                face(walls, [pa + o, pb + o, pb + o + Vector((0, 0, zb)), pa + o + Vector((0, 0, za))], o, 2)
            face(walls, [pa - tg * 0.15 + Vector((0, 0, za)), pb - tg * 0.15 + Vector((0, 0, zb)), pb + tg * 0.15 + Vector((0, 0, zb)), pa + tg * 0.15 + Vector((0, 0, za))], UPV, 2)
new_obj('Stand_Walls', walls, '02_Bowl', [concrete, concrete_light, white_paint])
new_obj('Outside_Walls', outside, '05_Outside', [concrete_dark, ribbed, mural_mat, mural_ends, america_mat])

# ---------------------------------------------------------------- the plateas
# straight rows of low seats in front of the long sides, from the walkway
# round the pitch back to the stands' fronts (their arcs cut them): the
# Olímpica's dark grey, the América's light blue; four blocks each, the
# middle stairway of the América the players' (brick, the tunnel's mouth)
def build_platea(name, st, y0, sgn, mat_seat):
    steps, seats, stairs = bmesh.new(), bmesh.new(), bmesh.new()
    cy, R0 = st['C'][1], st['R0']
    count = 0
    k = 0
    cuts = [(-1.2 if name == 'america' else -1.0, 1.2 if name == 'america' else 1.0), (-33.0, -31.8), (31.8, 33.0)]
    while True:
        ya, yb = y0 + sgn * 0.9 * k, y0 + sgn * 0.9 * (k + 1)
        lim = R0 * R0 - (yb - cy) ** 2
        if lim <= 0:
            break
        xm = min(64.5, math.sqrt(lim) - 0.4)
        if xm < 3.0:
            break
        z = 0.55 + 0.21 * k
        zp = 0.0 if k == 0 else z - 0.21
        nrm = Vector((0, sgn, 0))
        n = max(1, math.ceil(2 * xm / 3.0))
        for s in range(n):
            xa, xb = -xm + 2 * xm * s / n, -xm + 2 * xm * (s + 1) / n
            in_cut = any(c0 <= (xa + xb) / 2 <= c1 for c0, c1 in cuts)
            face(steps, [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)], UPV, 0)
            face(steps, [(xa, ya, zp), (xb, ya, zp), (xb, ya, z), (xa, ya, z)], -nrm, 1)
        # the stairways: the America's middle one brick red
        for c0, c1 in cuts:
            if c0 < -xm or c1 > xm:
                continue
            m = 2 if (name == 'america' and c0 < 0 < c1) else 0
            face(stairs, [(c0, ya, z + 0.01), (c1, ya, z + 0.01), (c1, yb, z + 0.01), (c0, yb, z + 0.01)], UPV, m)
        # the seats, block by block
        edges = [-xm] + [v for c in sorted(cuts) for v in c] + [xm]
        for xa, xb in zip(edges[0::2], edges[1::2]):
            if xb - xa < 0.6:
                continue
            ns = int((xb - xa - 0.4) / 0.52)
            for q in range(0, ns, 2):
                q1 = min(ns, q + 2)
                x0_, x1_ = xa + 0.2 + q * 0.52, xa + 0.2 + q1 * 0.52
                pa = [Vector((x0_, ya, z)), Vector((x1_, ya, z))]
                pb = [Vector((x0_, yb, z)), Vector((x1_, yb, z))]
                seat_geo(seats, pa, pb, nrm, mat_seat, q, q1, cush=0.42, top=0.80, fwd=0.30)
                count += q1 - q
        k += 1
    SEAT_COUNT['platea_' + name] = count
    new_obj('Platea_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('PlateaSeats_' + name, seats, '03_Seats', seat_cols)
    new_obj('PlateaStairs_' + name, stairs, '02_Bowl', [concrete_light, concrete, brick_red])
    return k


build_platea('olimpica', STANDS['olimpica'], -55.0, -1, PGREY)
build_platea('america', STANDS['america'], 56.5, 1, PBLUE)
# the players' tunnel: its mouth in the front of the Platea América, red brick round it
bm = bmesh.new()
face(bm, [(-1.6, 56.48, 0.0), (1.6, 56.48, 0.0), (1.6, 56.48, 0.55), (-1.6, 56.48, 0.55)], Vector((0, -1, 0)), 0)
box(bm, (0, 54.8), (1, 0), 2.2, (0, 1), 1.6, 0.0, 2.6, 1, True, False)
face(bm, [(-1.5, 53.18, 0.05), (1.5, 53.18, 0.05), (1.5, 53.18, 2.3), (-1.5, 53.18, 2.3)], Vector((0, -1, 0)), 0)
new_obj('Tunnel', bm, '02_Bowl', [portal, brick_red])

# ---------------------------------------------------------------- the taludes behind the goals
# old terraces from the ends' fronts down towards the pitch, closed since 1993:
# weathered concrete, grass in the joints, no seats, a fence at their foot
def dist_field(x, y):
    best = 1e9
    n = len(FIELD)
    for k in range(n):
        (ax, ay), (bx, by) = FIELD[k], FIELD[(k + 1) % n]
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-9, dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


bm = bmesh.new()
fence_pts = {}
for name in ('colombes', 'amsterdam'):
    st = STANDS[name]
    for k in range(20):
        r_out, r_in = -0.8 * k, -0.8 * (k + 1)
        z = 4.6 - 0.24 * k
        zp = z - 0.24
        if zp < 0.2:
            break
        ths = arc_steps(st['a0'], st['a1'], st['R0'] + r_in, 2.0)
        for t0, t1 in zip(ths, ths[1:]):
            mid = AP(st, (t0 + t1) / 2, (r_in + r_out) / 2)
            if inside_poly(mid.x, mid.y, FIELD) or dist_field(mid.x, mid.y) < 2.0 or abs(mid.y) > 50.0:
                continue
            A0, A1, B0, B1 = AP(st, t0, r_in), AP(st, t1, r_in), AP(st, t0, r_out), AP(st, t1, r_out)
            L = (A1 - A0).length
            uvs = [(t0 * (st['R0'] + r_in) / 4.0, r_in / 4.0), (t1 * (st['R0'] + r_in) / 4.0, r_in / 4.0),
                   (t1 * (st['R0'] + r_in) / 4.0, r_out / 4.0), (t0 * (st['R0'] + r_in) / 4.0, r_out / 4.0)]
            face(bm, [A0 + Vector((0, 0, z)), A1 + Vector((0, 0, z)), B1 + Vector((0, 0, z)), B0 + Vector((0, 0, z))], UPV, 0, uvs)
            out = (A0 + A1) / 2 - Vector((st['C'][0], st['C'][1], 0))
            face(bm, [A0 + Vector((0, 0, 0.0)), A1 + Vector((0, 0, 0.0)), A1 + Vector((0, 0, z)), A0 + Vector((0, 0, z))], -out, 0,
                 [(uvs[0][0], 0), (uvs[1][0], 0), (uvs[1][0], z / 4.0), (uvs[0][0], z / 4.0)])
new_obj('Taludes', bm, '02_Bowl', [terrace])

# the edge of the walkway round the pitch: a low dark wall along the long
# sides, tall fences behind the goals (since the 1990s)
bm = bmesh.new()
n = len(FIELD)
for k in range(n):
    (ax, ay), (bx, by) = FIELD[k], FIELD[(k + 1) % n]
    a_, b_ = Vector((ax, ay, 0)), Vector((bx, by, 0))
    L = (b_ - a_).length
    nrm = Vector((-(by - ay), bx - ax, 0)).normalized()
    if nrm.dot(-a_) < 0:
        nrm = -nrm                                           # towards the pitch
    end = abs(bx - ax) < abs(by - ay)
    if not end:
        ns = max(1, math.ceil(L / 3.0))
        for s in range(ns):
            p0, p1 = a_.lerp(b_, s / ns), a_.lerp(b_, (s + 1) / ns)
            face(bm, [p0, p1, p1 + Vector((0, 0, 1.0)), p0 + Vector((0, 0, 1.0))], nrm, 0)
            face(bm, [p0 - nrm * 0.25, p1 - nrm * 0.25, p1 - nrm * 0.25 + Vector((0, 0, 1.0)), p0 - nrm * 0.25 + Vector((0, 0, 1.0))], -nrm, 0)
            face(bm, [p0 + Vector((0, 0, 1.0)), p1 + Vector((0, 0, 1.0)), p1 - nrm * 0.25 + Vector((0, 0, 1.0)), p0 - nrm * 0.25 + Vector((0, 0, 1.0))], UPV, 0)
    else:
        npost = max(1, math.ceil(L / 2.5))
        for s in range(npost + 1):
            p = a_.lerp(b_, s / npost)
            tube(bm, p, p + Vector((0, 0, 2.8)), 0.05, 1, 5)
        for hh in (0.1, 1.4, 2.8):
            tube(bm, a_ + Vector((0, 0, hh)), b_ + Vector((0, 0, hh)), 0.035, 1, 5, step=3.0)
        m = max(1, int(L / 0.25))
        for s in range(m):
            p = a_.lerp(b_, (s + 0.5) / m)
            tube(bm, p + Vector((0, 0, 0.1)), p + Vector((0, 0, 2.8)), 0.012, 1, 3, step=4.0)
new_obj('Pitch_Edge', bm, '02_Bowl', [front_dark, galv])

# the boards round the pitch
bm = bmesh.new()
BH = 0.9


def board_run(a, b, nrm, u0):
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


V = lambda x, y, z: Vector((x, y, z))
BX, BY = PW / 2 + 6.0, PL / 2 + 4.5
u = 0.0
u = board_run(V(48.0, -BY, 0), V(-48.0, -BY, 0), V(0, 1, 0), u)            # in front of the Olímpica, read from the pitch
u = board_run(V(-BX, -24.0, 0), V(-BX, 24.0, 0), V(1, 0, 0), u)           # behind the Amsterdam goal
u = board_run(V(BX, 24.0, 0), V(BX, -24.0, 0), V(-1, 0, 0), u)            # behind the Colombes goal
u = board_run(V(-48.0, BY, 0), V(-14.0, BY, 0), V(0, -1, 0), u)           # the América's side, either side of the dugouts
u = board_run(V(14.0, BY, 0), V(48.0, BY, 0), V(0, -1, 0), u)
new_obj('Boards', bm, '02_Bowl', [boards_mat, steel_dark])
# the dugouts in front of the América: glass shelters on the grass, the fourth official's box between them
bm = bmesh.new()
for sx in (-1, 1):
    cx = sx * 9.5
    box(bm, (cx, BY + 1.2), (1, 0), 5.0, (0, 1), 0.9, 0.0, 0.5, 1)
    for xx in (cx - 5.0, cx + 5.0):
        face(bm, [(xx, BY + 0.3, 0.0), (xx, BY + 2.1, 0.0), (xx, BY + 2.1, 2.2), (xx, BY + 0.3, 2.2)], Vector((1, 0, 0)), 0)
    face(bm, [(cx - 5.0, BY + 2.1, 0.0), (cx + 5.0, BY + 2.1, 0.0), (cx + 5.0, BY + 2.1, 2.2), (cx - 5.0, BY + 2.1, 2.2)], Vector((0, 1, 0)), 0)
    face(bm, [(cx - 5.0, BY + 0.2, 2.2), (cx + 5.0, BY + 0.2, 2.2), (cx + 5.0, BY + 2.1, 2.3), (cx - 5.0, BY + 2.1, 2.3)], UPV, 0)
box(bm, (0, BY + 1.0), (1, 0), 1.2, (0, 1), 0.8, 0.0, 2.0, 0)
new_obj('Dugouts', bm, '02_Bowl', [glazing, seat_cols[BOX1]])

# ---------------------------------------------------------------- the gaps between the stands
# ramps from the walkway up to the park between the stands' radial ends
bm = bmesh.new()
order = [('olimpica', 'a1', 'colombes', 'a0'), ('colombes', 'a1', 'america', 'a0'), ('america', 'a1', 'amsterdam', 'a0'), ('amsterdam', 'a1', 'olimpica', 'a0')]
GAPS = []
for s1, e1, s2, e2 in order:
    A, B = STANDS[s1], STANDS[s2]
    ai, ao = AP(A, A[e1], 0.0), AP(A, A[e1], A['d_end'] + 0.3)
    bi, bo = AP(B, B[e2], 0.0), AP(B, B[e2], B['d_end'] + 0.3)
    GAPS.append(((ao + bo) / 2))
    n = 8
    for k in range(n):
        f0, f1 = k / n, (k + 1) / n
        p0, p1 = ai.lerp(ao, f0), ai.lerp(ao, f1)
        q0, q1 = bi.lerp(bo, f0), bi.lerp(bo, f1)
        z0, z1 = 0.3 + (G_Z - 0.3) * f0, 0.3 + (G_Z - 0.3) * f1
        face(bm, [p0 + Vector((0, 0, z0)), q0 + Vector((0, 0, z0)), q1 + Vector((0, 0, z1)), p1 + Vector((0, 0, z1))], UPV, 0)
new_obj('Gaps', bm, '02_Bowl', [concrete])

# ---------------------------------------------------------------- the official box, the VIP boxes and the press on the América
# over its first ring: the VIP boxes' glass, the balcony with the press's
# orange seats on their roof, the press boxes' dark band with ESTADIO
# CENTENARIO - 1930, the flat roof (the stadium's only one) over it all, the
# lift house on top; light blue walls behind
st = STANDS['america']
bm, sb = bmesh.new(), bmesh.new()
r1 = AM_ROWS[[r[4] for r in AM_ROWS].index(1) + 12][1]          # the back of the first ring
D_GLASS, D_PRESS, D_BACK = r1 + 0.6, r1 + 2.6, st['d_end']
Z_WALK, Z_GLASS, Z_PRESS, Z_ROOF = AM_ROWS[[r[4] for r in AM_ROWS].index(1) + 13][2], 14.8, 15.6, 19.6
ths = arc_steps(PALCO[0], PALCO[1], st['R0'] + D_PRESS, 2.5)
press_len = (PALCO[1] - PALCO[0]) * (st['R0'] + D_PRESS)
for t0, t1 in zip(ths, ths[1:]):
    o = AP(st, (t0 + t1) / 2, 0) - Vector((st['C'][0], st['C'][1], 0))
    u0, u1 = (PALCO[1] - t0) / (PALCO[1] - PALCO[0]), (PALCO[1] - t1) / (PALCO[1] - PALCO[0])     # read from the pitch: u from the left
    G0, G1 = AP(st, t0, D_GLASS), AP(st, t1, D_GLASS)
    L = (G1 - G0).length
    face(bm, [G0 + Vector((0, 0, Z_WALK)), G1 + Vector((0, 0, Z_WALK)), G1 + Vector((0, 0, Z_GLASS)), G0 + Vector((0, 0, Z_GLASS))], -o, 0,
         [(t0 * (st['R0'] + D_GLASS) / 6.0, 0), (t1 * (st['R0'] + D_GLASS) / 6.0, 0), (t1 * (st['R0'] + D_GLASS) / 6.0, 1), (t0 * (st['R0'] + D_GLASS) / 6.0, 1)])
    # the walk in front of the glass, the balcony slab
    face(bm, [AP(st, t0, r1, Z_WALK), AP(st, t1, r1, Z_WALK), G1 + Vector((0, 0, Z_WALK)), G0 + Vector((0, 0, Z_WALK))], UPV, 1)
    face(bm, [AP(st, t0, D_GLASS - 0.5, Z_GLASS), AP(st, t1, D_GLASS - 0.5, Z_GLASS), AP(st, t1, D_PRESS, Z_GLASS), AP(st, t0, D_PRESS, Z_GLASS)], UPV, 1)
    face(bm, [AP(st, t0, D_GLASS - 0.5, Z_GLASS - 0.35), AP(st, t1, D_GLASS - 0.5, Z_GLASS - 0.35), AP(st, t1, D_GLASS - 0.5, Z_GLASS), AP(st, t0, D_GLASS - 0.5, Z_GLASS)], -o, 2)
    # the press boxes' front
    P0, P1 = AP(st, t0, D_PRESS), AP(st, t1, D_PRESS)
    face(bm, [P0 + Vector((0, 0, Z_PRESS - 0.8)), P1 + Vector((0, 0, Z_PRESS - 0.8)), P1 + Vector((0, 0, Z_ROOF)), P0 + Vector((0, 0, Z_ROOF))], -o, 3,
         [(u0, 0), (u1, 0), (u1, 1), (u0, 1)])
    # the roof: over the balcony out to the back
    for d_a, d_b in ((D_GLASS - 1.2, D_PRESS), (D_PRESS, D_BACK)):
        face(bm, [AP(st, t0, d_a, Z_ROOF + 0.7), AP(st, t1, d_a, Z_ROOF + 0.7), AP(st, t1, d_b, Z_ROOF + 0.7), AP(st, t0, d_b, Z_ROOF + 0.7)], UPV, 4)
        face(bm, [AP(st, t0, d_a, Z_ROOF), AP(st, t1, d_a, Z_ROOF), AP(st, t1, d_b, Z_ROOF), AP(st, t0, d_b, Z_ROOF)], -UPV, 1)
    face(bm, [AP(st, t0, D_GLASS - 1.2, Z_ROOF), AP(st, t1, D_GLASS - 1.2, Z_ROOF), AP(st, t1, D_GLASS - 1.2, Z_ROOF + 0.7), AP(st, t0, D_GLASS - 1.2, Z_ROOF + 0.7)], -o, 2)
    # the back to the street, light blue
    Q0, Q1 = AP(st, t0, D_BACK + 0.3), AP(st, t1, D_BACK + 0.3)
    Lq = (Q1 - Q0).length
    cu = t0 * (st['R0'] + D_BACK)
    for za, zb in ((0.0, 7.0), (7.0, 14.0), (14.0, Z_ROOF + 0.7)):
        face(bm, [Q0 + Vector((0, 0, za)), Q1 + Vector((0, 0, za)), Q1 + Vector((0, 0, zb)), Q0 + Vector((0, 0, zb))], o, 5,
             [(cu / 12.0, (za - G_Z) / 20.0), ((cu + Lq) / 12.0, (za - G_Z) / 20.0), ((cu + Lq) / 12.0, (zb - G_Z) / 20.0), (cu / 12.0, (zb - G_Z) / 20.0)])
    # the press's orange seats on the balcony, two rows
    for rr, (da, zz) in enumerate(((D_GLASS - 0.3, Z_GLASS), (D_GLASS + 0.6, Z_GLASS + 0.3))):
        rmid = st['R0'] + da
        ns = int((t1 - t0) * rmid / 0.5)
        for q in range(0, ns, 2):
            ta, tb = t0 + (q + 0.1) * 0.5 / rmid, t0 + (min(ns, q + 2) - 0.1) * 0.5 / rmid
            pa, pb = [AP(st, ta, da, zz), AP(st, tb, da, zz)], [AP(st, ta, da + 0.9, zz), AP(st, tb, da + 0.9, zz)]
            seat_geo(sb, pa, pb, o.normalized(), ORANGE, 0, 1, cush=0.42, top=0.85)
for th, sg in ((PALCO[0], -1), (PALCO[1], 1)):
    tg = Vector((-math.sin(th), math.cos(th), 0)) * sg
    pa, pb = AP(st, th, D_GLASS - 1.2), AP(st, th, D_BACK + 0.3)
    face(bm, [pa + Vector((0, 0, Z_WALK)), pb + Vector((0, 0, Z_WALK)), pb + Vector((0, 0, Z_ROOF + 0.7)), pa + Vector((0, 0, Z_ROOF + 0.7))], tg, 1)
# the lift house and the aerials on the roof
c = AP(st, math.pi / 2, (D_PRESS + D_BACK) / 2)
box(bm, c, (1, 0), 4.0, (0, 1), 2.4, Z_ROOF + 0.7, Z_ROOF + 4.0, 1)
for dx in (-12.0, 9.0, 15.0):
    tube(bm, c + Vector((dx, 0, Z_ROOF + 0.7)), c + Vector((dx, 0, Z_ROOF + 9.0)), 0.06, 1, 5)
new_obj('Palco', bm, '04_Roof', [glazing, concrete_light, white_paint, press_mat, roof_mat, america_mat])
new_obj('Palco_Seats', sb, '03_Seats', seat_cols)

# ---------------------------------------------------------------- the Torre de los Homenajes
# at the Olímpica's back, its foot in the street: the shaft of bare
# concrete, the prow and the bronze plaque over the entrance on the street
# side, nine balconies stepping in up both sides, the wings at the top of
# the stand, the pulpit towards the pitch, the cap with its louvres, the mast
# and the flag; 100 m over the street
bm, tb = bmesh.new(), bmesh.new()
TX, TY = TOWER
ZB = G_Z
y_out, y_in = TY - 2.2, TY + 2.2                 # its street face, its face to the pitch
# the base, as OSM has it, and the shaft
abox(bm, TX - 2.7, TX + 2.7, y_out, y_in, 0.0, ZB + 26.0, 0, True, False)
abox(bm, TX - 1.7, TX + 1.7, y_out + 0.3, y_in - 0.3, ZB + 26.0, ZB + 86.0, 0, False, False)
abox(bm, TX - 2.1, TX + 2.1, y_out, y_in, ZB + 86.0, ZB + 92.5, 0, True, True)
abox(bm, TX - 1.2, TX + 1.2, y_out + 0.5, y_in - 0.5, ZB + 92.5, ZB + 94.5, 0, True, False)
# its louvres in the cap, the dark slits up the middle of both broad faces
for yy, sg in ((y_out - 0.01, -1), (y_in + 0.01, 1)):
    for k in range(5):
        x0 = TX - 1.4 + k * 0.7
        face(tb, [(x0, yy, ZB + 87.0), (x0 + 0.35, yy, ZB + 87.0), (x0 + 0.35, yy, ZB + 92.0), (x0, yy, ZB + 87.0 + 5.0)], Vector((0, sg, 0)), 0)
    face(tb, [(TX - 0.25, yy + sg * 0.3, ZB + 28.0), (TX + 0.25, yy + sg * 0.3, ZB + 28.0), (TX + 0.25, yy + sg * 0.3, ZB + 84.0), (TX - 0.25, yy + sg * 0.3, ZB + 84.0)], Vector((0, sg, 0)), 0)
# the vertical fins up the face towards the pitch (as from the stand)
for fx in (-1.2, -0.6, 0.6, 1.2):
    abox(bm, TX + fx - 0.09, TX + fx + 0.09, y_in - 0.3, y_in + 0.25, ZB + 30.0, ZB + 85.0, 0, True, True)
# nine balconies up both sides, each a block with its dark opening, smaller as they go up
for k in range(9):
    z0 = ZB + 27.0 + 6.4 * k
    wout = 1.7 - 0.13 * k
    for sx in (-1, 1):
        x0, x1 = (TX + 1.7, TX + 1.7 + wout) if sx > 0 else (TX - 1.7 - wout, TX - 1.7)
        abox(bm, x0, x1, y_out + 0.2, y_in - 0.2, z0, z0 + 4.6, 0, True, True)
        xo = x1 if sx > 0 else x0
        face(tb, [(xo + sx * 0.01, y_out + 1.2, z0 + 1.2), (xo + sx * 0.01, y_in - 1.2, z0 + 1.2), (xo + sx * 0.01, y_in - 1.2, z0 + 3.6), (xo + sx * 0.01, y_out + 1.2, z0 + 3.6)],
             Vector((sx, 0, 0)), 0)
        for yy, sg in ((y_out + 0.19, -1), (y_in - 0.19, 1)):
            xa, xb = (x0 + 0.25, x1 - 0.25)
            if xb > xa + 0.2:
                face(tb, [(xa, yy, z0 + 1.0), (xb, yy, z0 + 1.0), (xb, yy, z0 + 3.6), (xa, yy, z0 + 3.6)], Vector((0, sg, 0)), 0)
# the prow on the street face, rising to a point
pr = [Vector((TX - 2.4, y_out, ZB + 7.5)), Vector((TX + 2.4, y_out, ZB + 7.5)), Vector((TX, y_out - 2.4, ZB + 7.5))]
top_ = Vector((TX, y_out, ZB + 25.0))
for a_, b_ in zip(pr, pr[1:] + pr[:1]):
    face(bm, [a_, b_, top_], ((a_ + b_) / 2 - Vector((TX, TY, ZB + 7.5))) + UPV * 0.3, 0)
face(bm, pr, -UPV, 0)
# the plaque over the entrance, the dark band round it, the doors
face(tb, [(TX + 6.4, y_out - 0.32, ZB + 3.6), (TX - 6.4, y_out - 0.32, ZB + 3.6), (TX - 6.4, y_out - 0.32, ZB + 7.4), (TX + 6.4, y_out - 0.32, ZB + 7.4)], Vector((0, -1, 0)), 0)
face(tb, [(TX - 5.6, y_out - 0.36, ZB + 3.9), (TX + 5.6, y_out - 0.36, ZB + 3.9), (TX + 5.6, y_out - 0.36, ZB + 7.1), (TX - 5.6, y_out - 0.36, ZB + 7.1)], Vector((0, -1, 0)), 1,
     [(0, 0), (1, 0), (1, 1), (0, 1)])
face(tb, [(TX + 2.4, y_out - 0.33, ZB), (TX - 2.4, y_out - 0.33, ZB), (TX - 2.4, y_out - 0.33, ZB + 3.3), (TX + 2.4, y_out - 0.33, ZB + 3.3)], Vector((0, -1, 0)), 0)
abox(bm, TX - 6.6, TX + 6.6, y_out - 0.3, y_out + 1.0, ZB + 3.4, ZB + 7.6, 0, True, True)
# the low wings at the foot either side (OSM, 15 m)
abox(bm, TX + 2.7, TX + 10.4, y_out, y_out + 3.2, 0.0, ZB + 9.0, 0, True, False)
abox(bm, TX - 11.2, TX - 2.7, y_out, y_out + 3.2, 0.0, ZB + 9.0, 0, True, False)
# the wings at the top of the stand: thin slabs out either side
for sx in (-1, 1):
    x0 = TX + sx * 1.7
    x1 = TX + sx * 11.0
    zw = ZB + 30.5
    pts_t = [Vector((x0, y_out + 0.6, zw)), Vector((x1, y_out + 1.6, zw)), Vector((x1, y_in - 1.2, zw)), Vector((x0, y_in - 0.4, zw))]
    pts_b = [p - Vector((0, 0, 0.55 if abs(p.x - x0) < 0.1 else 0.2)) for p in pts_t]
    face(bm, pts_t, UPV, 0)
    face(bm, pts_b, -UPV, 0)
    for a_ in range(4):
        b_ = (a_ + 1) % 4
        face(bm, [pts_b[a_], pts_b[b_], pts_t[b_], pts_t[a_]], ((pts_t[a_] + pts_t[b_]) / 2 - Vector((TX + sx * 6, TY, zw))), 0)
# the pulpit towards the pitch, over the top of the stand
abox(bm, TX - 1.6, TX + 1.6, y_in, y_in + 3.0, ZB + 27.2, ZB + 27.8, 0, True, True)
for sx in (-1.5, 1.5):
    tube(bm, Vector((TX + sx, y_in + 2.9, ZB + 27.8)), Vector((TX + sx, y_in + 2.9, ZB + 28.8)), 0.04, 0, 5)
tube(bm, Vector((TX - 1.5, y_in + 2.9, ZB + 28.8)), Vector((TX + 1.5, y_in + 2.9, ZB + 28.8)), 0.04, 0, 5)
# the mast and the flag of Uruguay, flying east in the westerly
tube(bm, Vector((TX, TY, ZB + 94.5)), Vector((TX, TY, ZB + 101.0)), 0.09, 0, 6, step=3.0)
WIND = Vector((0.45, -0.89, 0)).normalized()
SIDEW = Vector((-WIND.y, WIND.x, 0))
FLW, FLH, NU, NV = 4.2, 2.8, 8, 3
ft = Vector((TX, TY, ZB + 100.6))
for i_ in range(NU):
    for j_ in range(NV):
        q = [(i_, j_), (i_ + 1, j_), (i_ + 1, j_ + 1), (i_, j_ + 1)]
        pts = [ft + Vector((0, 0, -FLH * (1 - b / NV))) + WIND * (0.1 + FLW * a / NU) + SIDEW * (0.25 * math.sin(a / NU * 5.0) * a / NU) for a, b in q]
        uvs = [(a / NU, b / NV) for a, b in q]
        face(tb, pts, SIDEW, 2, uvs)
        face(tb, pts[::-1], -SIDEW, 2, uvs[::-1])
new_obj('Torre', bm, '05_Outside', [tower_mat])
new_obj('Torre_Detail', tb, '05_Outside', [tower_dark, plaque_mat, flag_mat])

# ---------------------------------------------------------------- the TV cabins on the Olímpica's top, the flagpoles along the tops
bm = bmesh.new()
st = STANDS['olimpica']
for x_ in (-26.0, -20.0, -14.0, -8.0, 8.0, 14.0, 20.0, 26.0):
    th = math.atan2(-1.0, 0.0) + math.asin(max(-1, min(1, x_ / (st['R0'] + st['d_end'] - 1.0))))
    c = AP(st, th, st['d_end'] - 0.9)
    nrm = (c - Vector((st['C'][0], st['C'][1], 0))).normalized()
    box(bm, c, nrm, 0.8, (-nrm.y, nrm.x), 1.4, st['z_top'], st['z_top'] + 2.5, 0)
for name, st in STANDS.items():
    if name == 'america':
        continue
    ths = arc_steps(st['a0'], st['a1'], st['R0'] + st['d_end'], 13.0)
    for th in ths[1:-1]:
        p = AP(st, th, st['d_end'] + 0.15)
        if name == 'olimpica' and abs(p.x) < 12:
            continue
        tube(bm, p + Vector((0, 0, st['z_top'] + 1.1)), p + Vector((0, 0, st['z_top'] + 8.5)), 0.05, 1, 5, step=4.0)
new_obj('Top_Things', bm, '04_Roof', [white_paint, galv])

# ---------------------------------------------------------------- the LED screen on its table over the Colombes
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.12), 2.0)
st = STANDS['colombes']
bm, fb = bmesh.new(), bmesh.new()
xf = st['C'][0] + st['R0'] + SCR_D                 # its face, facing the Amsterdam
nrm = Vector((-1, 0, 0))
right = Vector((0, -1, 0))                         # the viewer's right, seen from the pitch
cz = SCR_Z0 + SCR_H / 2
obox(bm, Vector((xf + 0.45, 0.0, cz)), nrm, right, UPV, 0.42, SCR_W / 2 + 0.25, SCR_H / 2 + 0.25, 0)
obox(bm, Vector((xf + 1.4, 0.4, SCR_Z0 - 0.75)), nrm, right, UPV, 1.5, SCR_W / 2 + 2.2, 0.45, 0)        # the table's beam
for q in LEG_SPOTS:
    th = math.atan2(q.y - st['C'][1], q.x - st['C'][0])
    dd = math.hypot(q.x - st['C'][0], q.y - st['C'][1]) - st['R0']
    zt = top_z(st, dd)
    abox(bm, q.x - 0.22, q.x + 0.22, q.y - 0.22, q.y + 0.22, zt, SCR_Z0 - 1.2, 0, False, False)
for dd in (SCR_D + 0.4, SCR_D + 2.4):
    tube(bm, Vector((st['C'][0] + st['R0'] + dd, -5.8, SCR_Z0 - 4.0)), Vector((st['C'][0] + st['R0'] + dd, 5.8, SCR_Z0 - 4.0)), 0.12, 1, 6)
c0 = Vector((xf - 0.03, 0.0, cz))
face(fb, [c0 - right * SCR_W / 2 - UPV * SCR_H / 2, c0 + right * SCR_W / 2 - UPV * SCR_H / 2,
          c0 + right * SCR_W / 2 + UPV * SCR_H / 2, c0 - right * SCR_W / 2 + UPV * SCR_H / 2], nrm, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
new_obj('Screen_Frame', bm, '04_Roof', [steel_dark, steel_grey])
screen_face = new_obj('ScreenFace_0', fb, '04_Roof', [live])

# ---------------------------------------------------------------- the floodlights: four poles in the gaps between the stands
bm = bmesh.new()
POLE_H = 58.0
for g in GAPS:
    dirn = Vector((g.x, g.y, 0)).normalized()
    base_ = Vector((g.x, g.y, 0)) + dirn * 9.0
    tube(bm, base_ + Vector((0, 0, G_Z)), base_ + Vector((0, 0, POLE_H - 4.0)), 0.75, 0, 10, step=6.0)
    tube(bm, base_ + Vector((0, 0, G_Z)), base_ + Vector((0, 0, G_Z + 3.0)), 1.1, 0, 10)
    to_c = (-base_).normalized()
    tg = Vector((-to_c.y, to_c.x, 0))
    fwd = (to_c * math.cos(math.radians(28)) - UPV * math.sin(math.radians(28))).normalized()
    upl = tg.cross(fwd).normalized()
    if upl.z < 0:
        upl = -upl
    head = base_ + Vector((0, 0, POLE_H)) + to_c * 1.0
    obox(bm, head - fwd * 0.4, fwd, tg, upl, 0.25, 4.2, 3.4, 0)
    for i_ in range(6):
        for j_ in range(5):
            cc = head + tg * (-3.5 + 1.4 * i_) + upl * (-2.8 + 1.4 * j_)
            obox(bm, cc, fwd, tg, upl, 0.22, 0.55, 0.55, 0)
            fc = cc + fwd * 0.23
            face(bm, [fc - tg * 0.45 - upl * 0.45, fc + tg * 0.45 - upl * 0.45, fc + tg * 0.45 + upl * 0.45, fc - tg * 0.45 + upl * 0.45], fwd, 1)
new_obj('Floodlights', bm, '05_Outside', [lamp, lamp_glass])


# ================================================================ outside: the park round the stadium, trees
G_HALF = 320.0                   # tools/centenario/ground.png covers 640 x 640 m
AP_X0, AP_X1, AP_Y0, AP_Y1 = -175.0, 175.0, -175.0, 165.0


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
    # every corner of the cell inside the stadium's outline: the bowl, not the park
    return all(inside_poly(x, y, OUTLINE) for x, y in ((xa, ya), (xb, ya), (xb, yb), (xa, yb)))


bm = bmesh.new()
ground_cells(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 5.0, inside_bowl)
new_obj('Ground', bm, '05_Outside', [ground_mat])

trng = random.Random(1930)


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


def near_road(x, y, margin):
    for r in OSM['roads']:
        pts = r['pts']
        w = {'primary': 9.0, 'primary_link': 6.0, 'tertiary': 7.0, 'tertiary_link': 5.0, 'residential': 5.5, 'service': 4.0}.get(r['type'], 2.0)
        for k in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[k], pts[k + 1]
            if min(ax, bx) - 20 > x or max(ax, bx) + 20 < x or min(ay, by) - 20 > y or max(ay, by) + 20 < y:
                continue
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / max(1e-6, dx * dx + dy * dy)))
            if math.hypot(x - ax - t * dx, y - ay - t * dy) < w + margin:
                return True
    return False


def clear_spot(x, y):
    if math.hypot(x, y) < 152 or inside_poly(x, y, OUTLINE):
        return False                                         # the esplanade round the stadium
    for b in OSM['buildings']:
        bx, by = b['pts'][0]
        if abs(bx - x) < 80 and abs(by - y) < 80 and inside_poly(x, y, b['pts']):
            return False
    for g in OSM['pitches']:
        if inside_poly(x, y, g['pts']):
            return False
    for g in OSM['parking'] + OSM.get('tracks', []):
        if inside_poly(x, y, g):
            return False
    return not near_road(x, y, 2.5)


def park_trees(bm, x0, x1, y0, y1, step, keep):
    # Parque Batlle: eucalyptus and pines all round, thinner in the town
    for ix in range(int((x1 - x0) / step)):
        for iy in range(int((y1 - y0) / step)):
            x = x0 + (ix + trng.random()) * step
            y = y0 + (iy + trng.random()) * step
            if not keep(x, y):
                continue
            res_ = any(inside_poly(x, y, g) for g in OSM['residential'])
            if trng.random() < (0.25 if res_ else 0.62) and clear_spot(x, y):
                tree(bm, x, y, trng.uniform(12, 21), trng.uniform(3.4, 5.6))


bm = bmesh.new()
park_trees(bm, AP_X0, AP_X1, AP_Y0, AP_Y1, 11.0, lambda x, y: True)
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
    if len(pts) < 3 or (max(max(abs(x), abs(y)) for x, y in pts) > G_HALF - 4 and b['type'] != 'hospital'):
        continue
    if b['type'] == 'stadium':
        continue                                             # the tower: built above
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
        # a house: brick under a tiled gable, the ridge along its length
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
    tall = h > 18.0
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
buildings = new_obj('Buildings', bm, '06_Backdrop', [tiles, brick, brick_light, flat_roof, office_wall, plaster, tiles_dark, tower_block])
bm = bmesh.new()
park_trees(bm, -G_HALF + 8, G_HALF - 8, -G_HALF + 8, G_HALF - 8, 15.0, lambda x, y: not (AP_X0 < x < AP_X1 and AP_Y0 < y < AP_Y1))
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
        'match': ((0, 46.0, 30.0), (0, -40.0, 8.0), 54),
        'k10': ((6.0, 62.5, 4.6), (0.0, -120.0, 22.0), 70),                # from the Platea América: the Olímpica and the tower
        'k36': ((0.0, -119.0, 31.0), (0.0, 60.0, 8.0), 62),                # from the Olímpica's top: the América, the plateas
        'k04': ((90.0, -95.0, 33.0), (122.0, 30.0, 20.0), 60),             # from the Olímpica's corner: the Colombes and the screen
        'photo5': ((-40.0, -112.0, 28.0), (130.0, 10.0, 25.0), 62),         # towards the Colombes, the screen on its top
        'photo1': ((60.0, 0.0, 24.0), (132.0, 0.0, 36.0), 40),             # the screen on its table
        'm14': ((0.0, -205.0, 7.5), (0.0, -128.0, 45.0), 62),              # the tower from the street
        'air': ((-260.0, 230.0, 190.0), (0.0, 0.0, 0.0), 34),
        'air2': ((250.0, -190.0, 170.0), (0.0, 0.0, 10.0), 34),
        'k12': ((-205.0, 60.0, 8.0), (-130.0, 20.0, 18.0), 62),            # the Amsterdam's mural from the park
    }
    _unused = {
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
floor_light = bake_lightmap(floor, 1000, 860)
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
    # the Centenario's pitch as on the photos: broad bands across it, light
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
pitch_img = finish('ce_pitch', alb, grass_light, H, W)
del alb, cov, X, Y
grass.data.materials.clear(); grass.data.materials.append(image_material('M_Pitch', pitch_img, 0.9))

# the floor picture: the grass inside the walkway's edge, the grey walkway
# round it, the bare earth in front of the closed taludes
H, W = 1761, 2048
X = (FX0 + (np.arange(W, dtype='f') + 0.5) / W * (FX1 - FX0))[None, :]
Y = (FY0 + (np.arange(H, dtype='f') + 0.5) / H * (FY1 - FY0))[:, None]
X, Y = np.broadcast_to(X, (H, W)), np.broadcast_to(Y, (H, W))
def poly_mask(X, Y, poly):
    # inside a polygon, by counting the edges a ray to the right crosses
    m = np.zeros(X.shape, bool)
    n = len(poly)
    for k in range(n):
        (ax, ay), (bx, by) = poly[k], poly[(k + 1) % n]
        if ay == by:
            continue
        cross = ((ay > Y) != (by > Y)) & (X < ax + (Y - ay) * (bx - ax) / (by - ay))
        m ^= cross
    return m


inside = poly_mask(X, Y, FIELD)
alb = np.empty((H, W, 3), 'f')
alb[:] = (0.24, 0.235, 0.22)
alb *= (1 + 0.05 * rng.normal(0, 1, (H, W)).astype('f') + 0.05 * vnoise(H, W, 30, 30))[..., None]
earth = np.array((0.22, 0.16, 0.10), 'f') * (1 + 0.10 * vnoise(H, W, 20, 20) + 0.06 * rng.normal(0, 1, (H, W)).astype('f'))[..., None]
alb = np.where(((np.abs(X) > 66.0) & (np.abs(Y) < 46.0))[..., None], earth, alb)
alb = np.where(inside[..., None], grass_albedo(X, Y, H, W), alb)
floor_img = finish('ce_floor', alb, floor_light, H, W)
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
target.name = 'EstadioCentenario'
select_only([far_ground, buildings, far_trees], far_ground)
bpy.ops.object.join()
backdrop = far_ground
backdrop.name = 'StadiumBackdrop'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_Floor'}
FIXED_LIGHT = {}


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

