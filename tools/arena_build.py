# Builds the Johan Cruijff ArenA (Amsterdam) from nothing and exports it for the
# game, the way MetLife, De Kuip and El Campín are built: the pitch lines on
# the game's pitch, the night light baked into the model.
#   blender -b --factory-startup --python tools/arena_build.py -- <out.blend> <out.glb> <texture dir>
#
# As on the photos and the facts (opened 14 August 1996, 56,120 seats since
# 2022, architect Rob Schuurman with Sjoerd Soeters; stands at 37 degrees; a
# sliding roof of two parts of 37 x 120 m; built on a deck 8.40 m over the
# Burgemeester Stramanweg and the parking garage):
#   - inside, a rectangle with rounded corners: two rings of red seats, the
#     second ring steep and close, a ring of lit skyboxes between them; AJAX in
#     white seats filling the first ring of the far long side, on the halfway
#     line, the XXX of Amsterdam (three white crosses on black) in two narrow
#     strips in the second ring at the ends of that side; dark skybox glass
#     between the rings; a
#     red LED band on the front of the second ring: AMSTERDAMSCHE FOOTBALL CLUB
#     AJAX SINDS 18 MAART 1900 over AJAX, AJAX F-SIDE SINDS 1976 and the
#     European cups over the south goal (the F-side); red LED boards along the
#     sides and close behind the goals, grass and a concrete walk behind them,
#     the yellow disc of the Johan Cruyff Foundation on the grass behind the
#     north goal; a red sign over every tunnel mouth
#   - the roof: fixed over all the stands, grey with solar panels on top and
#     a lattice of white steel underneath, floodlights along the edge of the
#     opening, a row of red championship banners across each end of it with
#     the live screen hanging under the middle; the opening is open, its two
#     translucent panels parked over the ends; two big white steel arches
#     along the long sides carry them, from four corner towers with round caps
#   - two live screens (game.screen.js, style 'arena') under the banners, as
#     on the photos of the screen in a match; the Ajax logo on it is img/logo3.png
#   - outside, the "flying saucer": a grey roof rim with red stripes over a
#     slatted underside, the white upper concourse with red accents bulging out
#     (the 2018 renovation), raked grey concrete struts all round, round glass
#     stair towers at the corners, two glass escalator tubes, at each end a
#     white stair tower with six round windows; on the north one the portrait
#     of Johan Cruijff in black and white over the red JOHAN CRUIJFF ARENA
#     banner, the glass doors of gate B under it, the escalators climbing to
#     it from the right; the deck, the garage under it and the road passing
#     beneath the stadium
# No sponsor logos. The portrait, the Foundation disc, AJAX in the seats and
# the banners are pictures made by tools/arena_assets.py (the portrait: Rob
# Mieremet / Anefo, Nationaal Archief, 1974, CC0) and read from tools/arena/.
#
# The helpers, the pitch and the export are the ones of tools/dekuip_build.py.
import bpy, bmesh, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

OUT_BLEND, OUT_GLB, TEX_DIR = sys.argv[sys.argv.index('--') + 1:][:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data
sc = bpy.context.scene
for name in ('01_Pitch', '02_Bowl', '03_Seats', '04_Roof', '05_Outside'):
    c = D.collections.new(name)
    sc.collection.children.link(c)

# the pitch the game plays on (88 x 56, as in the other stadiums: 105 x 68 m at
# K units a metre) and the bowl as a rounded rectangle round an 84 x 48 core.
# The front wall at r = 13 keeps every stand out of the block the game cuts
# away towards the camera (|x| < 51.2, y > -32.4 in these units).
# +x is the south end (the F-side), -x the north end (the Johan Cruijff
# facade), -y the far long side in the game (AJAX in the seats).
PW, PL = 88.0, 56.0
K = PW / 105.0
LINE = 0.14
FLOOR_X, FLOOR_Y = 56.0, 37.0
CX, CY = 42.0, 24.0
SEG = 12
N_RING = 4 * (SEG + 1)
N_SIDE, W_SIDE, S_SIDE, E_SIDE = (k * (SEG + 1) + SEG for k in range(4))   # +y side, -x end, -y side, +x end
GAIN = 2.0                      # the game draws the model unlit at this gain (catalog: look.gain)
SEAT_W = 0.5

BOARD_R = 9.0                                                       # the LED boards along the long sides (from the core)
BOARD_X = PW / 2 + 3.6                                              # and behind the goals, close to the line as on the photos
WALL_R, WALL_Z = 13.0, 1.3                                          # the low wall in front of the first ring
LOW = dict(r=13.3, z=1.3, rows=26, depth=0.80, rise=0.40)           # first ring: to r 34.1, z 11.3
SKY_R = LOW['r'] + LOW['depth'] * LOW['rows']                       # the skyboxes at its back
SKY_Z0 = LOW['z'] + LOW['rise'] * (LOW['rows'] - 1)
BAND_R, BAND_Z0, BAND_Z1 = 33.0, 15.4, 16.4                         # the LED band on the front of the second ring
UP = dict(r=33.3, z=16.8, rows=26, depth=0.80, rise=0.60)           # second ring, 37 degrees: to r 54.1, z 31.8
UP_BACK = UP['r'] + UP['depth'] * UP['rows']
UP_TOP = UP['z'] + UP['rise'] * (UP['rows'] - 1)
WALL_TOP = 37.6                                                     # the back wall of the second ring, up into the roof

# the roof: from the rim round the outside to the edge of the opening, a
# rectangle of 62 x 92 (74 x 110 m) over the pitch; the two sliding panels are
# parked over the ends. The arches run along the long sides, over the edges of
# the opening, from towers at the four corners.
ROOF_OUT = 60.0
RIM_Z0, RIM_Z1 = 35.0, 38.5
ROOF_RISE = 8.0                                                     # the top climbs from the rim to the opening
OPEN_X, OPEN_Y = 31.0, 46.0
ARCH_Y, ARCH_X = 47.5, 102.0                                        # the arches' line and their towers
ARCH_Z0, ARCH_Z1 = 45.0, 56.0                                       # at the towers and at the top
PANEL_D = 37.0 * K                                                  # a sliding panel, along the length

# outside
CONC_R = 48.0                                                       # the wall of the lower concourse
DECK_R = 70.0                                                       # the deck round the stadium, at pitch level
GROUND_Z = -8.4 * K                                                 # the street, 8.40 m under the deck


def roof_t_z(t):
    return RIM_Z1 + ROOF_RISE * math.sin(t * math.pi / 2)


def roof_thick(t):
    return 2.2 + 1.8 * t


def arch_z(x):
    return ARCH_Z0 + (ARCH_Z1 - ARCH_Z0) * (1 - (x / ARCH_X) ** 2)


def to_opening(x, y):
    # the point where the line from the centre through (x, y) meets the edge of the opening
    s = min(OPEN_X / max(abs(x), 1e-6), OPEN_Y / max(abs(y), 1e-6))
    return x * s, y * s


# ---------------------------------------------------------------- helpers (as in the MetLife and De Kuip scripts)
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


def painted(name, arr):
    h, w, _ = arr.shape
    img = D.images.new(name, w, h)
    px = np.ones((h, w, 4), 'f')
    a = np.clip(arr, 0, 1)
    px[..., :3] = np.where(a <= 0.0031308, 12.92 * a, 1.055 * a ** (1 / 2.4) - 0.055)
    img.pixels.foreach_set(px.ravel())
    save_img(img, name)
    img.pack()
    return img


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


def box(bm, c, ax, hx_, ay, hy_, z0, z1, mat=0):
    ax, ay = Vector((ax[0], ax[1], 0)), Vector((ay[0], ay[1], 0))
    if ax.x * ay.y - ax.y * ay.x < 0:
        ay = -ay
    c = Vector((c[0], c[1], 0))
    lo = [bm.verts.new(c + ax * sx * hx_ + ay * sy * hy_ + Vector((0, 0, z0))) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    hi = [bm.verts.new(v.co + Vector((0, 0, z1 - z0))) for v in lo]
    fs = [bm.faces.new(lo[::-1]), bm.faces.new(hi)]
    fs += [bm.faces.new((lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i])) for i in range(4)]
    for f in fs:
        f.material_index = mat
    return fs


def ring_path(r):
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, math.pi / 2), (-1, -1, math.pi), (1, -1, 1.5 * math.pi)):
        for i in range(SEG + 1):
            a = a0 + math.pi / 2 * i / SEG
            pts.append((sx * CX + r * math.cos(a), sy * CY + r * math.sin(a), a))
    return pts


def ring(bm, r0, z0, r1, z1, mat=0, skip=(), only=None, want=None, step=4.0, u_len=None, v_range=(0, 1)):
    p0, p1 = ring_path(r0), ring_path(r1)
    cum = [0.0]
    for i in range(N_RING):
        cum.append(cum[-1] + math.dist(p0[i][:2], p0[(i + 1) % N_RING][:2]))
    for i in range(N_RING):
        if i in skip or (only is not None and i not in only):
            continue
        j = (i + 1) % N_RING
        A0, A1 = Vector((p0[i][0], p0[i][1], 0)), Vector((p0[j][0], p0[j][1], 0))
        B0, B1 = Vector((p1[i][0], p1[i][1], 0)), Vector((p1[j][0], p1[j][1], 0))
        t = (A1 - A0) if (A1 - A0).length > 1e-6 else (B1 - B0)
        out = Vector((t.y, -t.x, 0)).normalized()
        w = {'up': Vector((0, 0, 1)), 'down': Vector((0, 0, -1)), 'out': out}.get(want)
        if w is None:
            w = Vector((0, 0, 1)) if abs(z1 - z0) < 1e-6 else -out
        n = max(1, math.ceil(max((A1 - A0).length, (B1 - B0).length) / step))
        for k in range(n):
            a0, a1 = A0.lerp(A1, k / n), A0.lerp(A1, (k + 1) / n)
            b0, b1 = B0.lerp(B1, k / n), B0.lerp(B1, (k + 1) / n)
            uvs = None
            if u_len:
                u0 = (cum[i] + (cum[i + 1] - cum[i]) * k / n) / u_len
                u1 = (cum[i] + (cum[i + 1] - cum[i]) * (k + 1) / n) / u_len
                uvs = [(u0, v_range[0]), (u1, v_range[0]), (u1, v_range[1]), (u0, v_range[1])]
            face(bm, [(a0.x, a0.y, z0), (a1.x, a1.y, z0), (b1.x, b1.y, z1), (b0.x, b0.y, z1)], w, mat, uvs)


def ring_points(r, step):
    p = [Vector((x, y, 0)) for x, y, _ in ring_path(r)]
    segs = [(p[i], p[(i + 1) % len(p)]) for i in range(len(p))]
    total = sum((q1 - q0).length for q0, q1 in segs)
    n = max(4, round(total / step))
    pts, acc, k = [], 0.0, 0
    for q0, q1 in segs:
        L = (q1 - q0).length
        if L < 1e-6:
            continue
        d = (q1 - q0) / L
        while k < n and (k + 0.5) * total / n <= acc + L:
            q = q0.lerp(q1, ((k + 0.5) * total / n - acc) / L)
            pts.append((q.x, q.y, math.atan2(-d.x, d.y)))
            k += 1
        acc += L
    return pts


# the lettering: Barlow Condensed ExtraBold, close to the letters on the stadium
LETTER_FONT = D.fonts.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'BarlowCondensed-ExtraBold.ttf'))


def wall_text(name, body, loc, outward, size, coll, mat, font=None, extrude=0.0):
    # a line of lettering standing up, facing away from `outward` (towards the pitch)
    cu = D.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.extrude = extrude
    cu.font = font or LETTER_FONT
    cu.resolution_u = 2 if size < 2 else 4               # flat letters, few points on the curves: light for phones
    cu.offset = size * 0.022
    cu.materials.append(mat)
    t = D.objects.new(name, cu)
    t.location = loc
    t.rotation_euler = (math.pi / 2, 0, outward - math.pi / 2)
    D.collections[coll].objects.link(t)
    return t



NAME_FONT = D.fonts.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Comfortaa-Bold.ttf'))


def ring_len(r):
    p = ring_path(r)
    return sum(math.dist(p[i][:2], p[(i + 1) % len(p)][:2]) for i in range(len(p)))


def slab(bm, p0, p1, side, width, thick, mat):
    # a flat bar from p0 to p1, `width` wide along `side`, `thick` thick
    s = side * (width / 2)
    h = Vector((0, 0, thick / 2))
    c = [p0 - s, p1 - s, p1 + s, p0 + s]
    top, bot = [q + h for q in c], [q - h for q in c]
    face(bm, top, Vector((0, 0, 1)), mat)
    face(bm, bot, Vector((0, 0, -1)), mat)
    mid = (p0 + p1) / 2
    for i in range(4):
        j = (i + 1) % 4
        face(bm, [bot[i], bot[j], top[j], top[i]], (c[i] + c[j]) / 2 - mid, mat)


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1996)


def seat_tile(color):
    t = np.zeros((32, 32, 3), 'f')
    t[:] = np.array(color, 'f') * np.linspace(0.80, 1.0, 32)[:, None, None]
    t[:, :2] *= 0.22; t[:, -2:] *= 0.22
    t[-2:] *= 1.12
    return t


PANES, PANE_W = 16, 2.0


def windows_tex(warmth=(1.0, 0.80, 0.58), lit=0.8):
    pw, h = 64, 128
    t = np.zeros((h, pw * PANES, 3), 'f')
    v = np.linspace(0, 1, h)[:, None]
    for k in range(PANES):
        x0 = k * pw
        if rng.random() < lit:
            warm = np.array(warmth, 'f') * rng.uniform(0.35, 0.7)
            prof = 0.55 + 0.45 * np.clip((v - 0.55) / 0.3, 0, 1) ** 1.5
            prof = np.where(v > 0.86, 1.25, prof)
            prof = np.where(v < 0.32, 0.30, prof)
            pane = warm * prof[..., None] * np.ones((1, pw, 1), 'f')
            for _ in range(rng.integers(1, 4)):
                cx, wd = rng.integers(6, pw - 6), rng.integers(4, 9)
                top = rng.uniform(0.45, 0.62)
                m = (v < top) & (v > 0.05)
                pane[:, max(0, cx - wd // 2):cx + wd // 2][m[:, 0]] *= 0.35
        else:
            pane = np.array((0.03, 0.035, 0.05), 'f') * (1 + 0.6 * v)[..., None] * np.ones((1, pw, 1), 'f')
        pane[:, :2] = 0.02; pane[:, -2:] = 0.02; pane[:3] = 0.02; pane[-3:] = 0.02
        t[:, x0:x0 + pw] = pane
    return t


def roof_tex():
    # the fixed roof: grey sheet with standing seams running out from the opening
    w, h = 128, 32
    x = np.arange(w) / w
    rib = 0.86 + 0.14 * np.cos(x * 2 * np.pi * 8)
    return np.ones((h, w, 3), 'f') * np.array((0.50, 0.51, 0.53), 'f') * rib[None, :, None]


def solar_tex():
    # rows of solar panels: dark blue cells in a light frame
    w, h = 256, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.035, 0.05, 0.10), 'f')
    t *= (1 + 0.15 * rng.random((1, w, 1))).astype('f')
    t[:, (np.arange(w) % 32) < 2] = (0.55, 0.56, 0.58)
    t[(np.arange(h) % 32) < 2] = (0.55, 0.56, 0.58)
    t[:, (np.arange(w) % 8) == 4] *= 0.75
    return t


def roof_under_tex():
    # under the roof, as on the photos: a close lattice of white steel against the dark deck
    w = h = 128
    t = np.ones((h, w, 3), 'f') * np.array((0.20, 0.21, 0.22), 'f')
    yy, xx = np.mgrid[0:h, 0:w]
    steel = np.array((0.80, 0.81, 0.82), 'f')
    t[(xx % 32) < 3] = steel
    t[(yy % 64) < 3] = steel
    t[((xx + yy) % 64) < 2] = steel * 0.85
    t[((xx - yy) % 64) < 2] = steel * 0.85
    return t


def slats_tex():
    # the underside of the "saucer" outside: warm grey horizontal slats
    w, h = 64, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.60, 0.56, 0.50), 'f')
    yy = np.arange(h)
    t[(yy % 16) < 4] *= 0.55
    t[(yy % 16) == 4] *= 1.15
    return t


def concourse_tex():
    # the white upper concourse of the 2018 facade: white slats, a band of
    # windows, red panels at the frames (u: 16 m, v: from the bottom to the top)
    w, h = 512, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.86, 0.86, 0.85), 'f')
    yy, xx = np.arange(h), np.arange(w)
    t[(yy % 12) < 2] *= 0.82
    win = ((yy > 150) & (yy < 190))[:, None] & ((xx % 64) > 6)[None, :]
    t[win] = (0.06, 0.07, 0.09)
    lit = win & (((xx // 64) % 3) != 1)[None, :]
    t[lit] = np.array((0.95, 0.78, 0.55), 'f') * 0.6
    red_ = ((xx % 256) > 96) & ((xx % 256) < 116)
    t[(yy > 30)[:, None] & (yy < 140)[:, None] & red_[None, :]] = (0.62, 0.04, 0.05)
    return t[::-1]


def plinth_tex():
    # the deck's dark concrete side, the garage behind it in openings
    w, h = 512, 128
    t = np.ones((h, w, 3), 'f') * np.array((0.27, 0.27, 0.28), 'f')
    t *= (1 + 0.04 * rng.normal(0, 1, (h, w, 1))).astype('f')
    yy, xx = np.arange(h), np.arange(w)
    hole = ((yy > 22) & (yy < 96))[:, None] & ((xx % 128) > 12)[None, :]
    t[hole] = (0.02, 0.02, 0.025)
    t[(yy > 92) & (yy < 96)] = (0.55, 0.55, 0.55)
    return t[::-1]


def concwall_tex():
    # the lower concourse: grey concrete, doors and lit windows, red gate signs
    w, h = 512, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.55, 0.55, 0.56), 'f')
    t *= (1 + 0.03 * rng.normal(0, 1, (h, w, 1))).astype('f')
    yy, xx = np.arange(h), np.arange(w)
    t[(yy % 64) < 2] *= 0.7
    door = ((yy > 4) & (yy < 70))[:, None] & ((xx % 128) > 30)[None, :] & ((xx % 128) < 98)[None, :]
    t[door] = np.array((0.95, 0.85, 0.65), 'f') * 0.55
    win = ((yy > 120) & (yy < 160))[:, None] & ((xx % 32) > 4)[None, :]
    t[win] = (0.07, 0.08, 0.10)
    sign = ((yy > 76) & (yy < 92))[:, None] & ((xx % 128) > 44)[None, :] & ((xx % 128) < 84)[None, :]
    t[sign] = (0.70, 0.05, 0.06)
    return t[::-1]


def tower_glass_tex():
    # a round glass stair tower at night: the flights behind the glass, lit
    w, h = 128, 256
    t = np.ones((h, w, 3), 'f') * np.array((0.10, 0.13, 0.15), 'f')
    yy, xx = np.arange(h), np.arange(w)
    t[(yy % 32) < 3] = np.array((0.95, 0.90, 0.80), 'f') * 0.7
    t[:, (xx % 16) < 1] *= 0.5
    diag = ((yy[:, None] + xx[None, :] // 2) % 32) < 3
    t[diag] = np.array((0.95, 0.90, 0.80), 'f') * 0.45
    return t


seat_cols = [image_material('M_Seat%d' % i, painted('arena_seat%d' % i, seat_tile(c)), 0.6)
             for i, c in enumerate(((0.74, 0.035, 0.045), (0.70, 0.032, 0.042), (0.77, 0.04, 0.05),
                                    (0.90, 0.90, 0.90), (0.035, 0.035, 0.04)))]
concrete = principled('M_Concrete', (0.46, 0.46, 0.47), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.22, 0.22, 0.23), 0.9)
concrete_light = principled('M_ConcreteLight', (0.66, 0.66, 0.65), 0.85)
portal = principled('M_Portal', (0.015, 0.015, 0.018), 0.95)
red = principled('M_Red', (0.60, 0.035, 0.045), 0.6)
led_red = principled('M_LEDRed', (0.55, 0.03, 0.04), 0.4, (0.55, 0.03, 0.04), 3.0)           # the LED band and boards
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
glass_lit = image_material('M_GlassLit', painted('arena_windows', windows_tex()), 0.2)
steel_white = principled('M_SteelWhite', (0.80, 0.81, 0.82), 0.5)
steel_dark = principled('M_SteelDark', (0.07, 0.07, 0.08), 0.6)
roof_top = image_material('M_RoofTop', painted('arena_roof', roof_tex()), 0.5, 0.15)
solar = image_material('M_Solar', painted('arena_solar', solar_tex()), 0.3)
roof_under = image_material('M_RoofUnder', painted('arena_roofunder', roof_under_tex()), 0.8)        # white steel lattice
sky_glass = image_material('M_SkyGlass', painted('arena_skyglass', windows_tex(lit=0.15)), 0.2)     # the skyboxes: dark glass, as on the photos
_bimg = D.images.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arena', 'banners.png'))
_bimg.pack()
banner_tex = image_material('M_Banners', _bimg, 0.9)                                           # the championship banners (tools/arena_assets.py)
roof_clear = principled('M_RoofClear', (0.80, 0.82, 0.84), 0.5)                            # the translucent sliding panels
fascia = principled('M_Fascia', (0.52, 0.52, 0.53), 0.6)                                   # the grey rim of the saucer
slats = image_material('M_Slats', painted('arena_slats', slats_tex()), 0.8)
concourse = image_material('M_Concourse', painted('arena_concourse', concourse_tex()), 0.7)
plinth = image_material('M_Plinth', painted('arena_plinth', plinth_tex()), 0.9)
concwall = image_material('M_ConcWall', painted('arena_concwall', concwall_tex()), 0.85)
tower_glass = image_material('M_TowerGlass', painted('arena_towerglass', tower_glass_tex()), 0.2)
escalator = principled('M_Escalator', (0.10, 0.22, 0.17), 0.2, (0.16, 0.34, 0.26), 1.0)    # the green glass tubes, lit inside
white_wall = principled('M_WhiteWall', (0.84, 0.84, 0.83), 0.8)
_pimg = D.images.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arena', 'portrait.png'))
_pimg.pack()
portrait = image_material('M_Portrait', _pimg, 0.8)                                         # Johan Cruijff, 1974 (tools/arena_assets.py)
banner_red = principled('M_BannerRed', (0.62, 0.03, 0.04), 0.9)
banner_white = principled('M_BannerWhite', (0.90, 0.90, 0.90), 0.9)
lamp = principled('M_FloodLight', (1.0, 1.0, 0.97), 0.3, (1.0, 1.0, 0.96), 3.0)
asphalt = principled('M_Asphalt', (0.05, 0.05, 0.055), 0.95)
road_line = principled('M_RoadLine', (0.75, 0.75, 0.72), 0.8)
lawn = principled('M_Lawn', (0.05, 0.13, 0.05), 0.95)
plaza = principled('M_Plaza', (0.36, 0.35, 0.34), 0.9)

# ================================================================ pitch
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
arc(0, 0, 9.15 * K, 0, 2 * math.pi, 96); disc(0, 0, 0.22)
for s in (-1, 1):
    gx = s * hx
    for depth, half in ((16.5 * K, 20.16 * K), (5.5 * K, 9.16 * K)):
        x = gx - s * depth
        vline(x, -half - e, half + e)
        hline(half, min(gx, x), max(gx, x)); hline(-half, min(gx, x), max(gx, x))
    spot = gx - s * 11 * K
    disc(spot, 0, 0.22)
    a = math.acos((16.5 - 11) / 9.15)
    mid = math.pi if s > 0 else 0
    arc(spot, 0, 9.15 * K, mid - a, mid + a, 32)
    for t in (-1, 1):
        a0 = {(1, 1): math.pi, (1, -1): math.pi / 2, (-1, 1): 1.5 * math.pi, (-1, -1): 0}[(s, t)]
        arc(gx, t * hy, 1.0 * K, a0, a0 + math.pi / 2, 10)
lines = new_obj('Pitch_Lines', bm, '01_Pitch', [principled('M_Lines', (0.95, 0.95, 0.95), 0.6)])

# two real goals (the game takes them out and uses its own)
net_tile = np.zeros((32, 32, 4), 'f')
net_tile[..., :3] = 0.92
net_tile[:3, :, 3] = 1.0; net_tile[:, :3, 3] = 1.0
net_img = D.images.new('arena_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/arena_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
net_mat = image_material('M_Net', net_img, 0.8)
nn = net_mat.node_tree
nn.links.new(next(n for n in nn.nodes if n.type == 'TEX_IMAGE').outputs['Alpha'], next(n for n in nn.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Alpha'])
for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
    try:
        setattr(net_mat, attr, val)
    except Exception:
        pass
post_mat = principled('M_GoalPost', (0.92, 0.92, 0.92), 0.4)
GOAL_HW, GOAL_H, POST_R, MESH = 7.32 * K / 2, 2.44, 0.06, 0.12


def tube(bm, p0, p1, r, mat, seg=12):
    d = p1 - p0
    res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=d.length)
    rot = d.to_track_quat('Z', 'Y').to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((p0 + p1) / 2) @ rot, verts=res['verts'])
    for f in {f for v in res['verts'] for f in v.link_faces}:
        f.material_index = mat


bm = bmesh.new()
V = lambda x, y, z: Vector((x, y, z))
for s in (-1, 1):
    gx = s * hx
    for y in (-GOAL_HW, GOAL_HW):
        tube(bm, V(gx, y, 0), V(gx, y, GOAL_H + POST_R), POST_R, 0)
        tube(bm, V(gx + s * 1.0, y, GOAL_H), V(gx + s * 2.0, y, 0.03), 0.025, 0)
        tube(bm, V(gx, y, 0.03), V(gx + s * 2.0, y, 0.03), 0.025, 0)
        tube(bm, V(gx, y, GOAL_H), V(gx + s * 1.0, y, GOAL_H), 0.025, 0)
    tube(bm, V(gx, -GOAL_HW - POST_R, GOAL_H), V(gx, GOAL_HW + POST_R, GOAL_H), POST_R, 0)
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

# the grass and the darker artificial run-off round it
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-FLOOR_X, -FLOOR_Y), (FLOOR_X, -FLOOR_Y), (FLOOR_X, FLOOR_Y), (-FLOOR_X, FLOOR_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
grass = new_obj('Pitch_Grass', bm, '01_Pitch', [principled('M_Grass', (0.07, 0.33, 0.07), 0.85)])
bm = bmesh.new()
Z = 0.01
ix, iy = hx + 2.5, hy + 2.5
rect(-FLOOR_X, iy, FLOOR_X, FLOOR_Y); rect(-FLOOR_X, -FLOOR_Y, FLOOR_X, -iy)
rect(-FLOOR_X, -iy, -ix, iy); rect(ix, -iy, FLOOR_X, iy)
surround = new_obj('Pitch_Surround', bm, '01_Pitch', [principled('M_PitchSurround', (0.30, 0.09, 0.30), 0.9)])   # marked, painted green below


# ================================================================ the bowl
AISLE_EVERY, AISLE_W = 12.0, 1.0
UP_V = Vector((0, 0, 1))
V3 = lambda p, z: Vector((p[0], p[1], z))

# AJAX in white seats in the first ring of the far long side (-y), centred on
# the halfway line, as on the photos: tools/arena/ajax.png, one pixel a seat
# and one row a row of seats; the stairs on the halfway line run between J and A
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arena')
_aj = D.images.load(os.path.join(ASSETS, 'ajax.png'))
AJ_W, AJ_H = _aj.size
_px = np.empty(AJ_W * AJ_H * 4, 'f'); _aj.pixels.foreach_get(_px)
AJ_MASK = _px.reshape(AJ_H, AJ_W, 4)[::-1, :, 0] > 0.5      # row 0 at the top
D.images.remove(_aj)
LETTER_ROW0 = 2                                      # the bottom row: the letters fill most of the ring, as on the photos


def ajax_on(x, row):
    # seen from the pitch the far side runs from +x (left) to -x (right)
    col = math.floor((AJ_W * SEAT_W / 2 - x) / SEAT_W)
    pr = LETTER_ROW0 + AJ_H - 1 - row
    return 0 <= col < AJ_W and 0 <= pr < AJ_H and bool(AJ_MASK[pr, col])


# the XXX of Amsterdam in the second ring: a strip of black seats nine seats
# wide from the bottom to the top, three white crosses in it, one over the
# other; as on the photos only two, on the far long side, out at its ends
STRIP_W = 4.5
STRIPS = {S_SIDE: (-39.25, 39.25)}



def strip_at(seg, x, y):
    if seg not in STRIPS:
        return None
    s = x if seg in (N_SIDE, S_SIDE) else y
    for c in STRIPS[seg]:
        if abs(s - c) < STRIP_W / 2:
            return s - (c - STRIP_W / 2)             # 0 .. STRIP_W across the strip
    return None


def cross_on(u, row):
    if not 1 <= row <= 24:
        return False
    rr = (row - 1) % 8                               # three cells of eight rows: a cross of six, a black row above and below
    if not 1 <= rr <= 6:
        return False
    r = rr - 1
    col = u / STRIP_W * 12                           # 0 .. 12 across the strip
    return abs(col - (2 * r + 1)) <= 1.3 or abs(col - (11 - 2 * r)) <= 1.3


def seat_colour(tier, seg, row, x, y, h):
    # 0, 1, 2 reds; 3 white; 4 black
    if tier == 'low' and seg == S_SIDE and ajax_on(x, row):
        return 3
    if tier == 'up':
        u = strip_at(seg, x, y)
        if u is not None:
            return 3 if cross_on(u, row) else 4
    return (0, 0, 1, 2)[h % 4]


def portal_rows(tier):
    # the dark tunnel mouths: half way up the second ring, at the back of the first
    return (10, 11, 12) if tier == 'up' else (21, 22, 23)


def seat_row(bm, aisles, dark, a, b, row, tier, seg, rise):
    # one row of seats on a tread; a: its front corners, b: its back corners
    length = (a[1] - a[0]).length
    spans = [(0.0, length)]
    back = (b[0] - a[0]).normalized()
    lift = Vector((0, 0, 0.012))
    if length > 16:
        cuts = [c for c in (length / 2 + j * AISLE_EVERY for j in range(-10, 11)) if AISLE_W < c < length - AISLE_W]
        edges = [0.0] + [c + d for c in cuts for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        for c in cuts:                               # the stairs: plain grey concrete, as in the stadium
            u0, u1 = (c - AISLE_W / 2) / length, (c + AISLE_W / 2) / length
            f0, f1 = a[0].lerp(a[1], u0), a[0].lerp(a[1], u1)
            face(aisles, [f0 + lift, f1 + lift, b[0].lerp(b[1], u1) + lift, b[0].lerp(b[1], u0) + lift], UP_V, 0)
            if rise:
                down, out = Vector((0, 0, -rise)), -back * 0.012
                face(aisles, [f0 + down + out, f1 + down + out, f1 + out, f0 + out], -back, 0)
    for si, (s0, s1) in enumerate(spans):
        seats = max(1, round((s1 - s0) / SEAT_W))
        mats = []
        for q in range(seats):
            p = a[0].lerp(a[1], (s0 + (s1 - s0) * (q + 0.5) / seats) / length)
            h = (row * 73856093) ^ (seg * 19349663) ^ ((q // 2 + si * 131) * 83492791)
            mats.append(seat_colour(tier, seg, row, p.x, p.y, h))
        # a tunnel mouth in every other block between two stairs, not in the letters or the crosses
        if len(spans) > 2 and row in portal_rows(tier) and si % 2 == (1 if tier == 'up' else 0) and 3 not in mats and 4 not in mats:
            half = 1.3 / (s1 - s0) * seats
            zone = [q for q in range(seats) if abs(q + 0.5 - seats / 2) < half]
            if zone:
                for q in zone:
                    mats[q] = None
                u0 = (s0 + (s1 - s0) * zone[0] / seats) / length
                u1 = (s0 + (s1 - s0) * (zone[-1] + 1) / seats) / length
                f0, f1 = a[0].lerp(a[1], u0), a[0].lerp(a[1], u1)
                g0, g1 = b[0].lerp(b[1], u0), b[0].lerp(b[1], u1)
                face(dark, [f0 + lift, f1 + lift, g1 + lift, g0 + lift], UP_V, 0)
                if rise:
                    down, out = Vector((0, 0, -rise)), -back * 0.012
                    face(dark, [f0 + down + out, f1 + down + out, f1 + out, f0 + out], -back, 0)
                if row == max(portal_rows(tier)):
                    sg = [g0.lerp(g1, 0.18), g0.lerp(g1, 0.82)]
                    face(dark, [sg[0] + Vector((0, 0, 0.95)), sg[1] + Vector((0, 0, 0.95)), sg[1] + Vector((0, 0, 1.45)), sg[0] + Vector((0, 0, 1.45))], -back, 1)
        q = 0
        while q < seats:
            m = mats[q]
            if m is None:
                q += 1
                continue
            q1 = q + 2 if q + 1 < seats and mats[q + 1] == m else q + 1
            u = [(s0 + (s1 - s0) * qq / seats) / length for qq in (q, q1)]
            pa = [a[0].lerp(a[1], t) for t in u]; pb = [b[0].lerp(b[1], t) for t in u]

            def at(t, hgt, i):
                return pa[i].lerp(pb[i], t) + Vector((0, 0, hgt))
            face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UP_V, m, [(q, 0.0), (q1, 0.0), (q1, 0.45), (q, 0.45)])
            face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, m, [(q, 0.45), (q1, 0.45), (q1, 0.95), (q, 0.95)])
            face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UP_V, m, [(q, 0.95), (q1, 0.95), (q1, 1.0), (q, 1.0)])
            q = q1


def build_tier(name, t, base_z, tier):
    steps, seats, aisles, dark = bmesh.new(), bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, z = t['r'] + t['depth'] * k, t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        ring(steps, r0, z_prev, r0, z, 1)
        ring(steps, r0, z, r0 + t['depth'], z, 0)
        p0, p1 = ring_path(r0), ring_path(r0 + t['depth'])
        for i in range(N_RING):
            j = (i + 1) % N_RING
            seat_row(seats, aisles, dark, [V3(p0[i], z), V3(p0[j], z)], [V3(p1[i], z), V3(p1[j], z)], k, tier, i, t['rise'] if k else 0)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Aisles_' + name, aisles, '02_Bowl', [concrete_light])
    new_obj('Portals_' + name, dark, '02_Bowl', [portal, led_red])


random.seed(1996)
build_tier('Lower', LOW, 0.0, 'low')
build_tier('Upper', UP, BAND_Z1, 'up')

# the low wall in front of the first ring, the walkway on it, the red LED boards round the pitch
bm = bmesh.new()
ring(bm, WALL_R, 0.0, WALL_R, WALL_Z, 0)
ring(bm, WALL_R, WALL_Z, LOW['r'], WALL_Z, 0, want='up')
ring(bm, WALL_R - 0.05, WALL_Z + 0.9, WALL_R - 0.05, WALL_Z + 1.0, 1)          # the rail on the wall
new_obj('Pitch_Wall', bm, '02_Bowl', [concrete_dark, steel_white])
BY_ = CY + BOARD_R
BOARD_LINES = [  # (start, end, outward angle): the far side, the near side, the south end, the north end
    (Vector((BOARD_X, -BY_, 0)), Vector((-BOARD_X, -BY_, 0)), -math.pi / 2),
    (Vector((-BOARD_X, BY_, 0)), Vector((BOARD_X, BY_, 0)), math.pi / 2),
    (Vector((BOARD_X, BY_, 0)), Vector((BOARD_X, -BY_, 0)), 0.0),
    (Vector((-BOARD_X, -BY_, 0)), Vector((-BOARD_X, BY_, 0)), math.pi),
]
bm = bmesh.new()
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    n = max(1, math.ceil((b - a).length / 4.0))
    for k in range(n):
        p0, p1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        q0, q1 = p0 + out * 0.25, p1 + out * 0.25
        face(bm, [(p0.x, p0.y, 0.1), (p1.x, p1.y, 0.1), (p1.x, p1.y, 1.0), (p0.x, p0.y, 1.0)], -out, 0)
        face(bm, [(q0.x, q0.y, 0.1), (q1.x, q1.y, 0.1), (q1.x, q1.y, 1.0), (q0.x, q0.y, 1.0)], out, 1)
        face(bm, [(p0.x, p0.y, 1.0), (p1.x, p1.y, 1.0), (q1.x, q1.y, 1.0), (q0.x, q0.y, 1.0)], UP_V, 1)
new_obj('LED_Boards', bm, '02_Bowl', [led_red, steel_dark])
BOARD_TEXT = ['AJAX', 'JOHAN CRUIJFF ARENA', 'AMSTERDAM']
ti = 0
for a, b, ang in BOARD_LINES:
    out = Vector((math.cos(ang), math.sin(ang), 0))
    n = max(1, round((b - a).length / 12.0))
    for k in range(n):
        p = a.lerp(b, (k + 0.5) / n) - out * 0.05
        wall_text('Boards_T%d' % ti, BOARD_TEXT[ti % 3], (p.x, p.y, 0.28), ang, 0.56, '02_Bowl', letters_white)
        ti += 1

# the skyboxes at the back of the first ring, under the second
bm = bmesh.new()
ring(bm, SKY_R, SKY_Z0, SKY_R, SKY_Z0 + 0.6, 0)
ring(bm, SKY_R, SKY_Z0 + 0.6, SKY_R, BAND_Z0 - 0.7, 1, u_len=PANE_W * PANES)
ring(bm, SKY_R, BAND_Z0 - 0.7, SKY_R, BAND_Z0, 2)
ring(bm, BAND_R, BAND_Z0, SKY_R, BAND_Z0, 0, want='down')           # the underside of the overhang
ring(bm, SKY_R - 0.05, SKY_Z0 + 0.95, SKY_R - 0.05, SKY_Z0 + 1.05, 3)   # the glass balustrade's rail
new_obj('Skyboxes', bm, '02_Bowl', [concrete_light, sky_glass, concrete_dark, steel_white])
bm = bmesh.new()
for x, y, a in ring_points(SKY_R - 0.07, 4.0):
    box(bm, (x, y), (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.06, (math.cos(a), math.sin(a)), 0.06, SKY_Z0 + 0.6, BAND_Z0 - 0.7, 0)
new_obj('Skyboxes_Mullions', bm, '02_Bowl', [concrete_light])

# the red LED band on the front of the second ring
bm = bmesh.new()
ring(bm, BAND_R, BAND_Z0, BAND_R, BAND_Z1, 0)
ring(bm, BAND_R, BAND_Z1, UP['r'], BAND_Z1, 1, want='up')
new_obj('Band', bm, '02_Bowl', [led_red, concrete])
BAND_TEXT = {
    # side: [(position along it, text)]; over the south goal as on the photo of
    # the F-side: AJAX F-SIDE SINDS 1976 with the cups to the left and the right
    S_SIDE: [(31.0, 'WERELDBEKERS'), (0.0, 'AMSTERDAMSCHE FOOTBALL CLUB AJAX SINDS 18 MAART 1900'), (-31.0, 'LANDSKAMPIOENEN')],
    N_SIDE: [(-26.0, 'AMSTERDAM'), (0.0, 'JOHAN CRUIJFF ARENA'), (26.0, 'AMSTERDAM')],
    E_SIDE: [(15.0, 'EUROPA CUP II  1987'), (0.0, 'AJAX F-SIDE SINDS 1976'), (-15.0, 'EUROPA CUP I  1971 1972 1973 1995')],
    W_SIDE: [(-12.0, 'EUROPA CUP II'), (12.0, 'UEFA CUP')],
}
bh = BAND_Z1 - BAND_Z0
for side, items in BAND_TEXT.items():
    for i, (s, text) in enumerate(items):
        if side == S_SIDE:
            loc, out = (s, -(CY + BAND_R - 0.06)), -math.pi / 2
        elif side == N_SIDE:
            loc, out = (s, CY + BAND_R - 0.06), math.pi / 2
        elif side == E_SIDE:
            loc, out = (CX + BAND_R - 0.06, s), 0.0
        else:
            loc, out = (-(CX + BAND_R - 0.06), s), math.pi
        wall_text('Band_T%d_%d' % (side, i), text, (loc[0], loc[1], BAND_Z0 + bh * 0.2), out, bh * 0.62, '02_Bowl', letters_white)

# the back of the second ring: a wall up into the roof
bm = bmesh.new()
ring(bm, UP_BACK, UP_TOP, UP_BACK, WALL_TOP, 0)
new_obj('Upper_Back', bm, '02_Bowl', [concrete_dark])


def ray_to_ring(x, y, r):
    # how far out along the line from the centre through (x, y) the ring at r lies (a factor)
    d = math.hypot(x, y)
    lo, hi = 0.0, 4.0 * (CX + CY + r) / max(d, 1e-6)
    for _ in range(48):
        m = (lo + hi) / 2
        px, py = abs(x * m), abs(y * m)
        if math.hypot(max(px - CX, 0), max(py - CY, 0)) < r:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def roof_t_at(x, y):
    # where (x, y) lies between the rim (0) and the edge of the opening (1)
    m = ray_to_ring(x, y, ROOF_OUT)
    ox, oy = to_opening(x, y)
    full = math.hypot(x * m - ox, y * m - oy)
    return max(0.0, min(1.0, math.hypot(x * m - x, y * m - y) / max(full, 1e-6)))


def roof_under_at(x, y):
    t = roof_t_at(x, y)
    return roof_t_z(t) - roof_thick(t)


# the two live screens (game.screen.js, style 'arena'), as on the photos from
# the ends: hanging from the roof at both ends of the opening, right under the
# row of championship banners. Exported together as 'StadiumScreens'.
EDGE_Z = roof_t_z(1) - roof_thick(1)                               # the underside of the roof at the opening
BANNER_TOP, BANNER_H, BANNER_W = EDGE_Z - 5.6, 5.8, 2.5
SCREEN_W, SCREEN_H = 14.5, 7.7
SCREEN_Z = BANNER_TOP - BANNER_H - 0.8 - SCREEN_H
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.10, 0.10, 0.16), 2.0)
SCREEN_FACES = []
for sx in (1, -1):
    d = Vector((sx, 0, 0))                                          # out from the middle of the end
    tn = Vector((-d.y, d.x, 0))
    c = Vector((sx * (OPEN_X - 2.2), 0, 0))
    bm = bmesh.new()
    box(bm, (c.x + d.x * 0.3, c.y), (tn.x, tn.y), SCREEN_W / 2 + 0.4, (d.x, d.y), 0.25, SCREEN_Z - 0.4, SCREEN_Z + SCREEN_H + 0.4, 0)
    top = EDGE_Z - 1.6 + 0.8
    for s in (-1, 1):                                               # the hangers up to the truss at the edge, between two banners
        p = c + tn * s * (SCREEN_W / 2 - 0.6) + d * 0.3
        tube(bm, Vector((p.x, p.y, SCREEN_Z + SCREEN_H + 0.4)), Vector((p.x, p.y, top - 0.8)), 0.12, 1, seg=6)
    tube(bm, Vector((c.x + d.x * 0.6, c.y - SCREEN_W / 2, SCREEN_Z + SCREEN_H + 1.2)), Vector((c.x + d.x * 0.6, c.y + SCREEN_W / 2, SCREEN_Z + SCREEN_H + 1.2)), 0.25, 1, seg=6)
    new_obj('Scoreboard_%d' % sx, bm, '02_Bowl', [portal, steel_white])                 # the box black, as on the photo from behind it
    fb = bmesh.new()
    face(fb, [c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)), c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)),
              c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H)), c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H))],
         -d, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])                  # u left to right as seen from the pitch
    SCREEN_FACES.append(new_obj('ScreenFace_%d' % sx, fb, '02_Bowl', [live]))

# the dugouts on the near side, either side of the halfway line
bm = bmesh.new()
yb = CY + WALL_R - 0.2
for x0, x1 in ((-14.0, -4.0), (4.0, 14.0)):
    face(bm, [(x0, yb - 2.2, 1.8), (x1, yb - 2.2, 1.8), (x1, yb, 2.0), (x0, yb, 2.0)], UP_V, 1)
    face(bm, [(x0, yb, 0.0), (x1, yb, 0.0), (x1, yb, 2.0), (x0, yb, 2.0)], Vector((0, -1, 0)), 0)
    for x in (x0, x1):
        face(bm, [(x, yb - 2.2, 0.0), (x, yb, 0.0), (x, yb, 2.0), (x, yb - 2.2, 1.8)], Vector((1 if x == x0 else -1, 0, 0)), 1)
new_obj('Dugouts', bm, '02_Bowl', [concrete_dark, roof_clear])

# ================================================================ the roof
# The fixed roof as a grid between the rim (t = 0) and the edge of the opening
# (t = 1): every point of the rim joined to the point of the opening on the same
# line from the centre. The top climbs to the opening, its underside follows.
OUT_PTS = [Vector((x, y, 0)) for x, y, _ in ring_points(ROOF_OUT, 3.0)]
NP = len(OUT_PTS)
T_STEPS = [0.0, 0.06, 0.14, 0.24, 0.34, 0.44, 0.54, 0.64, 0.74, 0.84, 0.92, 1.0]
INNER = [Vector((*to_opening(p.x, p.y), 0)) for p in OUT_PTS]
CUM = [0.0]
for i in range(NP):
    CUM.append(CUM[-1] + (OUT_PTS[(i + 1) % NP] - OUT_PTS[i]).length)


def rp(i, t, z):
    p = OUT_PTS[i % NP].lerp(INNER[i % NP], t)
    return Vector((p.x, p.y, z))


bm = bmesh.new()
for i in range(NP):
    j = i + 1
    for t0, t1 in zip(T_STEPS, T_STEPS[1:]):
        tm = (t0 + t1) / 2
        # solar panels in blocks on the middle of the roof, as on the photo from the air
        m = 1 if 0.2 <= tm <= 0.72 and i % 8 != 7 else 0
        uvs = [(CUM[i] / 8, t0 * 5), (CUM[i + 1] / 8, t0 * 5), (CUM[i + 1] / 8, t1 * 5), (CUM[i] / 8, t1 * 5)]
        face(bm, [rp(i, t0, roof_t_z(t0)), rp(j, t0, roof_t_z(t0)), rp(j, t1, roof_t_z(t1)), rp(i, t1, roof_t_z(t1))], UP_V, m, uvs)
        face(bm, [rp(i, t0, roof_t_z(t0) - roof_thick(t0)), rp(j, t0, roof_t_z(t0) - roof_thick(t0)),
                  rp(j, t1, roof_t_z(t1) - roof_thick(t1)), rp(i, t1, roof_t_z(t1) - roof_thick(t1))], -UP_V, 2,
             [(CUM[i] / 6, t0 * 6), (CUM[i + 1] / 6, t0 * 6), (CUM[i + 1] / 6, t1 * 6), (CUM[i] / 6, t1 * 6)])
    # the edge of the opening: a white face from the underside to the top
    face(bm, [rp(i, 1.0, roof_t_z(1) - roof_thick(1)), rp(j, 1.0, roof_t_z(1) - roof_thick(1)), rp(j, 1.0, roof_t_z(1)), rp(i, 1.0, roof_t_z(1))],
         -(OUT_PTS[i % NP]).normalized(), 3)
ring(bm, ROOF_OUT, RIM_Z0, ROOF_OUT, RIM_Z1, 4, want='out')                  # the grey rim of the saucer
ring(bm, ROOF_OUT - 2.5, RIM_Z0, ROOF_OUT, RIM_Z0, 4, want='down')
new_obj('Roof', bm, '04_Roof', [roof_top, solar, roof_under, steel_white, fascia])

# the red stripes on the rim, all the way round
bm = bmesh.new()
for x, y, a in ring_points(ROOF_OUT + 0.05, 16.0):
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    c = Vector((x, y, 0))
    face(bm, [c - t * 0.8 + Vector((0, 0, RIM_Z0 + 0.25)), c + t * 0.8 + Vector((0, 0, RIM_Z0 + 0.25)),
              c + t * 0.8 + Vector((0, 0, RIM_Z1 - 0.25)), c - t * 0.8 + Vector((0, 0, RIM_Z1 - 0.25))], n, 0)
new_obj('Roof_Stripes', bm, '04_Roof', [red])

# white steel trusses under the roof, from the back of the second ring to the
# opening: a top and a bottom chord, verticals and diagonals
bm = bmesh.new()
for x, y, a in ring_points(ROOF_OUT, 8.0):
    m = ray_to_ring(x, y, UP_BACK)
    t_w = roof_t_at(x * m, y * m)
    ox, oy = to_opening(x, y)
    P, Q = Vector((x, y, 0)), Vector((ox, oy, 0))
    st = [t_w + (0.995 - t_w) * k / 6 for k in range(7)]
    pt = lambda t, dz: Vector((*(P.lerp(Q, t)).xy, roof_t_z(t) - roof_thick(t) - dz))
    depth = lambda t: 2.4 - 1.2 * t
    for t0, t1 in zip(st, st[1:]):
        tube(bm, pt(t0, 0.15), pt(t1, 0.15), 0.13, 0, seg=4)
        tube(bm, pt(t0, depth(t0)), pt(t1, depth(t1)), 0.11, 0, seg=4)
        tube(bm, pt(t0, depth(t0)), pt(t1, 0.15), 0.07, 0, seg=4)
    for t in st:
        tube(bm, pt(t, depth(t)), pt(t, 0.15), 0.07, 0, seg=4)
new_obj('Roof_Trusses', bm, '04_Roof', [steel_white])

# round the opening: a white truss under the edge, floodlights on it all the
# way round, black loudspeaker clusters hanging from it
RECT = [Vector((OPEN_X, OPEN_Y, 0)), Vector((-OPEN_X, OPEN_Y, 0)), Vector((-OPEN_X, -OPEN_Y, 0)), Vector((OPEN_X, -OPEN_Y, 0))]


def rect_points(step, inset=0.0):
    pts = []
    for k in range(4):
        a, b = RECT[k], RECT[(k + 1) % 4]
        n = max(1, round((b - a).length / step))
        inward = Vector((-(a.x + b.x) / 2, -(a.y + b.y) / 2, 0)).normalized()
        for i in range(n):
            p = a.lerp(b, (i + 0.5) / n) + inward * inset
            pts.append((p, inward))
    return pts


bm = bmesh.new()
for k in range(4):
    a, b = RECT[k], RECT[(k + 1) % 4]
    for dz in (0.2, 1.6):
        tube(bm, Vector((a.x, a.y, EDGE_Z - dz)), Vector((b.x, b.y, EDGE_Z - dz)), 0.22, 0, seg=4)
for p, n in rect_points(4.0, 0.3):
    tube(bm, Vector((p.x, p.y, EDGE_Z - 1.6)), Vector((p.x, p.y, EDGE_Z - 0.2)), 0.08, 0, seg=4)
for p, n in rect_points(18.0, 0.6):                                  # loudspeakers
    box(bm, (p.x, p.y), (n.x, n.y), 0.6, (-n.y, n.x), 0.7, EDGE_Z - 5.2, EDGE_Z - 2.4, 1)
    tube(bm, Vector((p.x, p.y, EDGE_Z - 2.4)), Vector((p.x, p.y, EDGE_Z - 1.6)), 0.05, 1, seg=4)
new_obj('Roof_Edge', bm, '04_Roof', [steel_white, steel_dark])
bm = bmesh.new()
for p, n in rect_points(2.2, 0.5):
    t = Vector((-n.y, n.x, 0))
    c = Vector((p.x, p.y, EDGE_Z - 1.9))
    nrm = (n * 0.6 + Vector((0, 0, -0.8))).normalized()
    up = nrm.cross(t).normalized()
    face(bm, [c - t * 0.7 - up * 0.35, c + t * 0.7 - up * 0.35, c + t * 0.7 + up * 0.35, c - t * 0.7 + up * 0.35], nrm, 0)
new_obj('Roof_Lamps', bm, '04_Roof', [lamp])

# the championship banners, as on the photos from the ends: a row across each
# end of the opening, hanging on wires from the truss at the edge, the screen
# under the middle of it. Red, a white edge, the trophy and the year
# (tools/arena/banners.png: 8 x 4 banners, read the same from both sides)
bm = bmesh.new()
NB, BSPAN = 22, 72.0
for sx in (1, -1):
    xb = sx * (OPEN_X - 0.7)
    for k in range(NB):
        y = -BSPAN / 2 + BSPAN * (k + 0.5) / NB
        cell = (k + (0 if sx > 0 else NB)) % 32
        u0, u1 = (cell % 8) / 8, (cell % 8 + 1) / 8
        v1 = 1 - (cell // 8) / 4; v0 = v1 - 0.25
        y0, y1 = y - BANNER_W / 2, y + BANNER_W / 2
        z0, z1 = BANNER_TOP - BANNER_H, BANNER_TOP
        for side in (-1, 1):                                          # the face towards the pitch, and the back
            xf = xb + side * 0.03
            n = Vector((side, 0, 0))
            # seen from its own side, the banner's left is +y when facing +x and -y when facing -x
            l, r = (y1, y0) if side < 0 else (y0, y1)
            face(bm, [(xf, l, z0), (xf, r, z0), (xf, r, z1), (xf, l, z1)], n, 0, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
        tube(bm, Vector((xb, y0 - 0.1, z1 + 0.09)), Vector((xb, y1 + 0.1, z1 + 0.09)), 0.05, 1, seg=4)     # clear of the cloth: its corners take the baked light
        tube(bm, Vector((xb, y0, z0 - 0.07)), Vector((xb, y1, z0 - 0.07)), 0.035, 1, seg=4)
        for yy in (y0 + 0.15, y1 - 0.15):                             # the wires up to the truss
            tube(bm, Vector((xb, yy, z1 + 0.09)), Vector((xb, yy, EDGE_Z - 1.6)), 0.02, 1, seg=3)
new_obj('Banners', bm, '04_Roof', [banner_tex, steel_white])

# the two sliding panels, parked over the ends: translucent, a little crowned,
# hanging under the arches
bm = bmesh.new()
for sx in (1, -1):
    xs = [sx * (OPEN_X + PANEL_D * i / 8) for i in range(9)]
    ys = [-(ARCH_Y - 2.2) + 2 * (ARCH_Y - 2.2) * j / 16 for j in range(17)]
    pz = lambda x, y: arch_z(x) - 1.6 + 1.4 * (1 - (y / ARCH_Y) ** 2)
    for i in range(8):
        for j in range(16):
            q = [(xs[i], ys[j]), (xs[i + 1], ys[j]), (xs[i + 1], ys[j + 1]), (xs[i], ys[j + 1])]
            face(bm, [(x, y, pz(x, y)) for x, y in q], UP_V, 0)
            face(bm, [(x, y, pz(x, y) - 0.05) for x, y in q], -UP_V, 0)
    for x in (xs[0], xs[4], xs[8]):                                   # the panel's trusses across
        for j in range(16):
            tube(bm, Vector((x, ys[j], pz(x, ys[j]) - 0.6)), Vector((x, ys[j + 1], pz(x, ys[j + 1]) - 0.6)), 0.2, 1, seg=4)
    for y in (ys[0], ys[16]):
        for i in range(8):
            tube(bm, Vector((xs[i], y, pz(xs[i], y) - 0.4)), Vector((xs[i + 1], y, pz(xs[i + 1], y) - 0.4)), 0.25, 1, seg=4)
new_obj('Roof_Panels', bm, '04_Roof', [roof_clear, steel_white])

# the two arches along the long sides: triangular steel trusses from tower to tower
for sy in (1, -1):
    y0 = sy * ARCH_Y
    bm = bmesh.new()
    xs = [-ARCH_X + 2 * ARCH_X * i / 50 for i in range(51)]
    B1 = [Vector((x, y0 - 2.2, arch_z(x))) for x in xs]
    B2 = [Vector((x, y0 + 2.2, arch_z(x))) for x in xs]
    T = [Vector((x, y0, arch_z(x) + 4.6 - 2.0 * (x / ARCH_X) ** 2)) for x in xs]
    for i in range(len(xs)):
        tube(bm, B1[i], T[i], 0.14, 0, seg=4)
        tube(bm, B2[i], T[i], 0.14, 0, seg=4)
        tube(bm, B1[i], B2[i], 0.12, 0, seg=4)
        if i + 1 < len(xs):
            for chord in (B1, B2, T):
                tube(bm, chord[i], chord[i + 1], 0.38, 0, seg=6)
            a, b = (B1, B2) if i % 2 else (B2, B1)
            tube(bm, a[i], T[i + 1], 0.12, 0, seg=4)
            tube(bm, b[i], b[i + 1].lerp(T[i + 1], 0.5), 0.10, 0, seg=4)
    new_obj('Arch_%d' % (1 if sy > 0 else 0), bm, '04_Roof', [steel_white])

# ================================================================ outside
def beam(bm, p0, p1, side, w, h, mat, step=3.0):
    # a straight beam from p0 to p1, w wide along `side`, h deep across it; cut
    # into pieces of `step`, so the baked light (per corner) follows it
    ax = (p1 - p0).normalized()
    s = (side - ax * side.dot(ax)).normalized() * (w / 2)
    u = ax.cross(s).normalized() * (h / 2)
    corners = [s * a + u * b for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    n = max(1, math.ceil((p1 - p0).length / step))
    face(bm, [p0 + c for c in corners][::-1], -ax, mat)
    face(bm, [p1 + c for c in corners], ax, mat)
    for k in range(n):
        q0, q1 = p0.lerp(p1, k / n), p0.lerp(p1, (k + 1) / n)
        for i in range(4):
            j = (i + 1) % 4
            face(bm, [q0 + corners[i], q0 + corners[j], q1 + corners[j], q1 + corners[i]], corners[i] + corners[j], mat)


def gridbox(bm, x0, x1, y0, y1, z0, z1, mat, step=2.0):
    # an upright box with its sides and top cut into a grid of `step`
    def grid(p, du, dv, want):
        nu, nv = max(1, math.ceil(du.length / step)), max(1, math.ceil(dv.length / step))
        for a in range(nu):
            for b in range(nv):
                q = p + du * (a / nu) + dv * (b / nv)
                face(bm, [q, q + du / nu, q + du / nu + dv / nv, q + dv / nv], want, mat)
    X, Y, Zv = Vector((x1 - x0, 0, 0)), Vector((0, y1 - y0, 0)), Vector((0, 0, z1 - z0))
    grid(Vector((x0, y0, z0)), Y, Zv, Vector((-1, 0, 0)))
    grid(Vector((x1, y0, z0)), Y, Zv, Vector((1, 0, 0)))
    grid(Vector((x0, y0, z0)), X, Zv, Vector((0, -1, 0)))
    grid(Vector((x0, y1, z0)), X, Zv, Vector((0, 1, 0)))
    grid(Vector((x0, y0, z1)), X, Y, Vector((0, 0, 1)))


# the four corner towers that carry the arches: concrete, a white column, a round cap
for sx in (1, -1):
    for sy in (1, -1):
        cx_, cy_ = sx * ARCH_X, sy * ARCH_Y
        bm = bmesh.new()
        gridbox(bm, cx_ - 3.4, cx_ + 3.4, cy_ - 3.4, cy_ + 3.4, GROUND_Z, ARCH_Z0 - 7.0, 0)
        tube(bm, Vector((cx_, cy_, ARCH_Z0 - 7.0)), Vector((cx_, cy_, ARCH_Z0 - 1.0)), 2.1, 1, seg=16)
        tube(bm, Vector((cx_, cy_, ARCH_Z0 - 1.0)), Vector((cx_, cy_, ARCH_Z0)), 4.6, 1, seg=24)
        new_obj('Tower_%d%d' % (sx, sy), bm, '04_Roof', [concrete_light, steel_white])

# From the deck up, as on the photo of the north front: the grey lower
# concourse with its doors, the white upper concourse bulging out (the 2018
# facade) with red panels and a band of windows, the slatted underside of the
# saucer, the grey rim with its red stripes (the roof).
SHELL0, SHELL1, SHELL2 = (52.0, 14.6), (56.0, 20.5), (55.5, 27.5)
bm = bmesh.new()
ring(bm, CONC_R, 0.0, CONC_R, SHELL0[1], 0, want='out', u_len=16.0)
ring(bm, CONC_R, SHELL0[1], SHELL0[0], SHELL0[1], 1, want='down')
vmid = (SHELL1[1] - SHELL0[1]) / (SHELL2[1] - SHELL0[1])
ring(bm, SHELL0[0], SHELL0[1], SHELL1[0], SHELL1[1], 2, want='out', u_len=16.0, v_range=(0, vmid))
ring(bm, SHELL1[0], SHELL1[1], SHELL2[0], SHELL2[1], 2, want='out', u_len=16.0, v_range=(vmid, 1))
ring(bm, SHELL2[0], SHELL2[1], ROOF_OUT, RIM_Z0, 3, want='out', u_len=4.0)
new_obj('Facade', bm, '05_Outside', [concwall, concrete, concourse, slats])

# the raked grey concrete struts all round, from the deck out to the rim
bm = bmesh.new()
for x, y, a in ring_points(51.0, 16.0):
    if abs(y) < 16.0 and abs(x) > CX:                     # the stair towers at the ends stand there
        continue
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    p0 = Vector((x, y, 0.0))
    p1 = p0 + n * 10.0 + Vector((0, 0, RIM_Z0 + 0.8))
    beam(bm, p0, p1, t, 1.3, 1.7, 0)
new_obj('Struts', bm, '05_Outside', [concrete_light])

# the deck round the stadium at pitch level, its edge down to the street with
# the garage behind it, a rail along it
bm = bmesh.new()
n = math.ceil((DECK_R - CONC_R) / 4)
for k in range(n):
    ring(bm, CONC_R + (DECK_R - CONC_R) * k / n, 0.0, CONC_R + (DECK_R - CONC_R) * (k + 1) / n, 0.0, 0, want='up', step=4)
ring(bm, DECK_R, GROUND_Z, DECK_R, 0.0, 1, want='out', u_len=16.0)
ring(bm, DECK_R - 0.15, 1.0, DECK_R - 0.15, 1.1, 2, want='out')
ring(bm, DECK_R - 0.15, 0.0, DECK_R - 0.15, 1.0, 3, want='out')
new_obj('Deck', bm, '05_Outside', [plaza, plinth, steel_white, roof_clear])

# the Burgemeester Stramanweg, under the deck from one side to the other
bm = bmesh.new()
RY = CY + DECK_R + 60.0
face(bm, [(-7.0, -RY, GROUND_Z + 0.04), (7.0, -RY, GROUND_Z + 0.04), (7.0, RY, GROUND_Z + 0.04), (-7.0, RY, GROUND_Z + 0.04)], UP_V, 0)
y = -RY
while y < RY:
    face(bm, [(-0.08, y, GROUND_Z + 0.05), (0.08, y, GROUND_Z + 0.05), (0.08, y + 3.0, GROUND_Z + 0.05), (-0.08, y + 3.0, GROUND_Z + 0.05)], UP_V, 1)
    y += 9.0
for sy in (1, -1):                                         # the dark mouths of the passage under the stadium
    yy = sy * (CY + DECK_R + 0.05)
    face(bm, [(-7.0, yy, GROUND_Z), (7.0, yy, GROUND_Z), (7.0, yy, GROUND_Z + 5.5), (-7.0, yy, GROUND_Z + 5.5)], Vector((0, sy, 0)), 2)
new_obj('Road', bm, '05_Outside', [asphalt, road_line, portal])

# stairs from the street up to the deck at both ends
bm = bmesh.new()
for sx in (1, -1):
    for sy in (1, -1):
        x0, y0 = sx * (CX + DECK_R), sy * 30.0
        steps = 14
        for k in range(steps):
            z1 = -GROUND_Z * (1 - k / steps) + GROUND_Z
            xa = x0 + sx * 0.7 * k
            box(bm, (xa + sx * 0.35, y0), (1, 0), 0.35, (0, 1), 3.0, GROUND_Z, z1, 0)
new_obj('Deck_Stairs', bm, '05_Outside', [concrete_light])

# round glass stair towers at the corners, the flights lit behind the glass
for sx in (1, -1):
    for sy in (1, -1):
        c = Vector((sx * CX, sy * CY, 0)) + Vector((sx, sy, 0)).normalized() * 63.0
        bm = bmesh.new()
        R, NSEG, TOP = 3.8, 24, 24.0
        for k in range(NSEG):
            a0, a1 = 2 * math.pi * k / NSEG, 2 * math.pi * (k + 1) / NSEG
            p0 = c + Vector((math.cos(a0), math.sin(a0), 0)) * R
            p1 = c + Vector((math.cos(a1), math.sin(a1), 0)) * R
            face(bm, [(p0.x, p0.y, GROUND_Z), (p1.x, p1.y, GROUND_Z), (p1.x, p1.y, TOP), (p0.x, p0.y, TOP)],
                 (p0 + p1) / 2 - c, 0, [(2 * k / NSEG, 0), (2 * (k + 1) / NSEG, 0), (2 * (k + 1) / NSEG, 1), (2 * k / NSEG, 1)])
        face(bm, [(c.x + math.cos(2 * math.pi * k / NSEG) * (R + 0.4), c.y + math.sin(2 * math.pi * k / NSEG) * (R + 0.4), TOP) for k in range(NSEG)], UP_V, 1)
        tube(bm, Vector((c.x, c.y, TOP)), Vector((c.x, c.y, TOP + 0.6)), R + 0.4, 1, seg=NSEG)
        new_obj('GlassTower_%d%d' % (sx, sy), bm, '05_Outside', [tower_glass, white_wall])

# two glass escalator tubes up the north front, side by side: as on the photo
# from the deck on the right (-y, seen from the front) up to the upper
# concourse beside the tower
bm = bmesh.new()
A, B = Vector((-(CX + 66.0), -42.0, 0.6)), Vector((-(CX + 57.5), -15.5, 20.0))
hd = Vector(((B - A).x, (B - A).y, 0)).normalized()
perp = Vector((-hd.y, hd.x, 0))
for off in (0.0, 3.0):
    a, b = A + perp * off, B + perp * off
    tube(bm, a, b, 1.35, 0, seg=14)
    beam(bm, a - Vector((0, 0, 1.2)), b - Vector((0, 0, 1.2)), perp, 1.6, 0.5, 1)        # the truss under it
    for f in (0.3, 0.62):
        p = a.lerp(b, f)
        tube(bm, Vector((p.x, p.y, 0.0)), Vector((p.x, p.y, p.z - 1.4)), 0.3, 1, seg=8)
new_obj('Escalators', bm, '05_Outside', [escalator, concrete_light])

# at each end a white stair tower with big round holes; on the north one the
# red banner with the stadium's name, and the doors of gate B under it
for sx in (1, -1):
    xo = sx * (CX + 66.0)
    bm = bmesh.new()
    gridbox(bm, sx * (CX + 61.0) - 5.0, sx * (CX + 61.0) + 5.0, -14.0, 14.0, GROUND_Z, 31.0, 0, step=1.5)
    out = Vector((sx, 0, 0))
    # as on the photo of the north front: two columns of three round windows,
    # dark glass with two crossed bars in a grey frame; between them the
    # portrait from the top down, the red banner under it, and the glass doors
    # of gate B across the whole foot of the tower
    WR = 2.6
    for yy in (-8.6, 8.6):
        for zz in (8.6, 16.4, 24.2):
            pts = [(xo + sx * 0.06, yy + math.cos(2 * math.pi * k / 28) * WR, zz + math.sin(2 * math.pi * k / 28) * WR) for k in range(28)]
            face(bm, pts, out, 1)
            for k in range(28):
                a0, a1 = 2 * math.pi * k / 28, 2 * math.pi * (k + 1) / 28
                face(bm, [(xo + sx * 0.08, yy + math.cos(a0) * WR, zz + math.sin(a0) * WR), (xo + sx * 0.08, yy + math.cos(a1) * WR, zz + math.sin(a1) * WR),
                          (xo + sx * 0.08, yy + math.cos(a1) * (WR + 0.35), zz + math.sin(a1) * (WR + 0.35)), (xo + sx * 0.08, yy + math.cos(a0) * (WR + 0.35), zz + math.sin(a0) * (WR + 0.35))], out, 2)
            for a in (math.pi / 4, -math.pi / 4):                                   # the two bars across
                d, n = Vector((0, math.cos(a), math.sin(a))), Vector((0, -math.sin(a), math.cos(a))) * 0.16
                c0, c1 = Vector((xo + sx * 0.1, yy, zz)) - d * WR, Vector((xo + sx * 0.1, yy, zz)) + d * WR
                face(bm, [c0 - n, c1 - n, c1 + n, c0 + n], out, 2)
    face(bm, [(xo + sx * 0.07, -12.5, 0.0), (xo + sx * 0.07, 12.5, 0.0), (xo + sx * 0.07, 12.5, 4.6), (xo + sx * 0.07, -12.5, 4.6)], out, 3,
         [(0, 0), (6.25, 0), (6.25, 1), (0, 1)])
    if sx < 0:
        face(bm, [(xo - 0.08, -5.2, 16.4), (xo - 0.08, 5.2, 16.4), (xo - 0.08, 5.2, 30.6), (xo - 0.08, -5.2, 30.6)], out, 4, [(1, 0), (0, 0), (0, 1), (1, 1)])
        face(bm, [(xo - 0.08, -5.2, 6.6), (xo - 0.08, 5.2, 6.6), (xo - 0.08, 5.2, 16.4), (xo - 0.08, -5.2, 16.4)], out, 5)
        face(bm, [(xo - 0.1, -2.6, 4.85), (xo - 0.1, 2.6, 4.85), (xo - 0.1, 2.6, 5.75), (xo - 0.1, -2.6, 5.75)], out, 5)   # the sign of gate B
    new_obj('EndTower_%d' % sx, bm, '05_Outside', [white_wall, portal, concrete_light, glass_lit, portrait, red])
NX = -(CX + 66.0) - 0.14
wall_text('Banner_Name1', 'JOHAN CRUIJFF', (NX, 0.0, 14.1), 0.0, 1.4, '05_Outside', letters_white)
wall_text('Banner_Name2', 'ARENA', (NX, 0.0, 10.6), 0.0, 3.6, '05_Outside', letters_white)
wall_text('Banner_Tag', '#JohanCruijffArenA', (NX, 0.0, 8.8), 0.0, 0.7, '05_Outside', letters_white)
wall_text('Gate_B', 'NOORD B', (NX - 0.02, 0.0, 5.05), 0.0, 0.55, '05_Outside', letters_white)

# the gate signs of NOORD A and NOORD C on posts on the deck
bm = bmesh.new()
for yy in (22.0, -22.0):
    x = -(CX + DECK_R) + 3.0
    face(bm, [(x - 0.05, yy - 1.8, 2.2), (x - 0.05, yy + 1.8, 2.2), (x - 0.05, yy + 1.8, 3.1), (x - 0.05, yy - 1.8, 3.1)], Vector((-1, 0, 0)), 0)
    for s in (-1.5, 1.5):
        tube(bm, Vector((x, yy + s, 0.0)), Vector((x, yy + s, 2.2)), 0.06, 1, seg=6)
new_obj('Gate_Signs', bm, '05_Outside', [red, steel_white])
wall_text('Gate_A', 'NOORD A', (-(CX + DECK_R) + 2.9, 22.0, 2.35), 0.0, 0.6, '05_Outside', letters_white)
wall_text('Gate_C', 'NOORD C', (-(CX + DECK_R) + 2.9, -22.0, 2.35), 0.0, 0.6, '05_Outside', letters_white)

# the street round the deck: paving, roads, grass
bm = bmesh.new()
for r0, r1, m in ((0, 20, 2), (20, 32, 0), (32, 48, 1)):
    n = math.ceil((r1 - r0) / 4)
    for k in range(n):
        ring(bm, DECK_R + r0 + (r1 - r0) * k / n, GROUND_Z, DECK_R + r0 + (r1 - r0) * (k + 1) / n, GROUND_Z, m, want='up', step=4)
new_obj('Ground', bm, '05_Outside', [asphalt, lawn, plaza])

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
print('SAVED', OUT_BLEND)

# ================================================================ game export
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 24
bk = sc.render.bake
bk.use_pass_direct = False; bk.use_pass_indirect = False; bk.use_pass_color = True
bk.margin = 4


def select_only(objs, active):
    for o in sc.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


# pitch: lines and run-off baked into one texture, the turf painted over it
PW_PX, PH_PX = 4096, 2744
pimg = D.images.new('arena_pitch', PW_PX, PH_PX)
target = grass.copy(); target.data = grass.data.copy(); target.name = 'Pitch'
D.collections['01_Pitch'].objects.link(target)
target.data.materials.clear(); target.data.materials.append(image_material('M_Pitch', pimg, 0.9))
grass.location.z = -0.01
bk.use_selected_to_active = True; bk.cage_extrusion = 0.1; bk.max_ray_distance = 0.5
select_only([grass, lines, surround, target], target)
bpy.ops.object.bake(type='DIFFUSE')
H, W = PH_PX, PW_PX
px = np.empty(W * H * 4, 'f'); pimg.pixels.foreach_get(px); px = px.reshape(H, W, 4)
rgb = px[..., :3]
line_m = np.clip((rgb.min(axis=2) - 0.45) / 0.4, 0, 1)
runoff_m = (rgb[..., 2] > rgb[..., 1]) & (line_m < 0.3)
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y


def vnoise(cy, cx):
    g = rng.normal(0, 1, (H // cy + 3, W // cx + 3)).astype('f')
    yy, xx = np.arange(H, dtype='f') / cy, np.arange(W, dtype='f') / cx
    y0, x0 = yy.astype(int), xx.astype(int)
    fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    return (g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0 + 1][:, x0] * fy * (1 - fx)
            + g[y0][:, x0 + 1] * (1 - fy) * fx + g[y0 + 1][:, x0 + 1] * fy * fx)


def blur(a, sigma):
    fy, fx = np.fft.fftfreq(H)[:, None], np.fft.rfftfreq(W)[None, :]
    return np.fft.irfft2(np.fft.rfft2(a) * np.exp(-2 * np.pi ** 2 * sigma ** 2 * (fx ** 2 + fy ** 2)), s=(H, W)).astype('f')


# the ArenA's pitch: twenty broad stripes across it, light and dark, as on the
# photos (5.25 m each, the halfway line on a seam); a dark artificial run-off
bands_x = np.tanh(np.sin(np.pi * X / (PW / 20)) * 6)
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = (1 + 0.13 * bands_x + 0.055 * vnoise(420, 420) + 0.035 * vnoise(48, 48)
         + 0.05 * vnoise(16, 1) * (0.6 + 0.4 * bands_x) + 0.04 * fine)
grass_px = np.array((0.070, 0.175, 0.042), 'f') * shade[..., None]
grass_px[..., 0] *= 1 + 0.10 * vnoise(300, 300)
wear = sum(np.exp(-(((X - gx) / 3.2) ** 2 + (Y / 5.5) ** 2)) for gx in (-(hx - 2.8), hx - 2.8)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
wear = (0.2 * wear * (0.55 + 0.45 * np.clip(vnoise(36, 36) + 0.5, 0, 1)))[..., None]
grass_px = grass_px * (1 - wear) + np.array((0.150, 0.190, 0.070), 'f') * wear
runoff_px = np.array((0.030, 0.075, 0.025), 'f') * (1 + 0.05 * vnoise(64, 64) + 0.03 * fine)[..., None]
out_px = np.where(runoff_m[..., None], runoff_px, grass_px)
alpha = (np.clip(blur(line_m, 0.8), 0, 1) * np.clip(0.82 + 0.12 * vnoise(90, 90), 0.6, 1))[..., None]
out_px = np.clip(out_px * (1 - alpha) + np.array((0.78, 0.80, 0.76), 'f') * alpha, 0, 1)
del fine, shade, bands_x, wear, runoff_px, grass_px, alpha, rgb

# behind the boards at the ends, as on the photos from there: grass in the
# middle, a concrete walk along the stand and to the corners
behind = np.abs(X) > BOARD_X + 0.25
walk = behind & ((np.abs(X) > CX + WALL_R - 1.3) | (np.abs(Y) > 22.0))
lawn_px = np.array((0.068, 0.165, 0.040), 'f') * (1 + 0.06 * vnoise(64, 64) + 0.03 * rng.normal(0, 1, (H, W)).astype('f'))[..., None]
out_px = np.where((behind & ~walk)[..., None], lawn_px, out_px)
out_px = np.where(walk[..., None], np.array((0.22, 0.22, 0.21), 'f') * (1 + 0.04 * vnoise(32, 32))[..., None], out_px)
del lawn_px

# the yellow disc of the Johan Cruyff Foundation on that grass behind the north
# goal, as on the photos from that end; read from the camera (tools/arena/foundation.png)
FD_R = 2.6
FD_X, FD_Y = -(BOARD_X + 0.25 + (CX + WALL_R - 1.3 - BOARD_X - 0.25) / 2), -3.0
_fd = D.images.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'arena', 'foundation.png'))
FS = _fd.size[0]
_f = np.empty(FS * FS * 4, 'f'); _fd.pixels.foreach_get(_f)
_f = _f.reshape(FS, FS, 4)[::-1]                                     # row 0 at the top
D.images.remove(_fd)
_f[..., :3] = np.where(_f[..., :3] <= 0.04045, _f[..., :3] / 12.92, ((_f[..., :3] + 0.055) / 1.055) ** 2.4)
_f[..., :3] *= 1.0                                                   # bright paint: the pitch light still darkens it
ys, xs = np.nonzero((np.abs(X - FD_X) < FD_R) & (np.abs(Y - FD_Y) < FD_R))
iu = np.clip(((FD_X - X[0, xs]) / (2 * FD_R) + 0.5) * FS, 0, FS - 1).astype(int)      # the camera's left is +x
iv = np.clip(((Y[ys, 0] - FD_Y) / (2 * FD_R) + 0.5) * FS, 0, FS - 1).astype(int)      # its top the far side, -y
src = _f[iv, iu]
out_px[ys, xs] = out_px[ys, xs] * (1 - src[:, 3:4]) + src[:, :3] * src[:, 3:4]
del _f, src


# ---------------------------------------------------------------- night: floodlights from the ring
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


NIGHT = dict(flood=5500, stand=3500, under=1100, arch=2500, facade=22000, tower=30000, banner=9000, moon=0.6)
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)
coll = D.collections.new('10_NightLights'); sc.collection.children.link(coll)
FLOOD = (1.0, 0.99, 0.96)                                           # LED floodlights: cool white
for p, n in rect_points(4.0, 0.6):                                  # all round the edge of the opening, onto the pitch
    light(coll, 'SPOT', (p.x, p.y, EDGE_Z - 2.2), NIGHT['flood'], FLOOD, target=(p.x * 0.2, p.y * 0.2, 0), size=70)
for p, n in rect_points(8.0, 0.6):                                  # and across onto the stands
    light(coll, 'SPOT', (p.x, p.y, EDGE_Z - 2.2), NIGHT['stand'], FLOOD, target=(-p.x * 1.4, -p.y * 1.4, 12), size=80, blend=0.6)
for x, y, a in ring_points(46.0, 10.0):                             # lights under the roof, over the second ring
    light(coll, 'POINT', (x, y, roof_under_at(x, y) - 1.5), NIGHT['under'], (1.0, 0.95, 0.88))
for sy in (1, -1):                                                  # the white arches, lit from the roof
    for x in (-70.0, -42.0, -14.0, 14.0, 42.0, 70.0):
        light(coll, 'POINT', (x, sy * (ARCH_Y + 6.0), arch_z(x) - 3.0), NIGHT['arch'], (0.95, 0.96, 1.0))
light(coll, 'SUN', (0, 0, 120), NIGHT['moon'], (0.80, 0.86, 1.0), target=(30, 20, 0))
for x, y, a in ring_points(DECK_R - 3.0, 14.0):                     # the facade, from the deck
    light(coll, 'SPOT', (x, y, 0.6), NIGHT['facade'], (0.92, 0.94, 1.0), target=(x - 14 * math.cos(a), y - 14 * math.sin(a), 22), size=75, blend=0.6)
for sx in (1, -1):                                                  # the white stair towers at the ends
    for s in (-1, 1):
        light(coll, 'SPOT', (sx * (CX + DECK_R + 14.0), s * 20.0, 9.0), NIGHT['tower'], (1.0, 0.97, 0.92), target=(sx * (CX + 66.0), s * 4.0, 14), size=50, blend=0.5)
for sx in (1, -1):                                                  # the corner towers of the arches
    for sy in (1, -1):
        light(coll, 'SPOT', (sx * (ARCH_X + 14.0), sy * (ARCH_Y + 14.0), 8.0), NIGHT['tower'] * 0.6, (0.95, 0.96, 1.0), target=(sx * ARCH_X, sy * ARCH_Y, 30), size=35, blend=0.5)
for sx in (1, -1):                                                  # the championship banners and the screens at both ends
    for y in (-32.0, -16.0, 0.0, 16.0, 32.0):
        light(coll, 'SPOT', (sx * (OPEN_X - 15.0), y, BANNER_TOP - 1.0), 3200, FLOOD,
              target=(sx * (OPEN_X - 0.7), y, BANNER_TOP - BANNER_H / 2), size=55, blend=0.5)
for s in (-1, 1):                                                   # the banner on the north tower
    light(coll, 'SPOT', (-(CX + DECK_R) - 10.0, s * 7.0, 8.0), NIGHT['banner'], (1.0, 0.97, 0.92), target=(-(CX + 66.0), 0, 16), size=45, blend=0.5)
for o in (grass, lines, surround, goals):
    o.hide_render = True
sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 0
sc.cycles.transmission_bounces = 0; sc.cycles.transparent_max_bounces = 2
bk.use_pass_direct = True; bk.use_pass_indirect = True; bk.use_pass_color = False
bk.use_selected_to_active = False


def upsample(a, h2, w2):
    h, w = a.shape[:2]
    ys = np.clip((np.arange(h2) + 0.5) / h2 * h - 0.5, 0, h - 1)
    xs = np.clip((np.arange(w2) + 0.5) / w2 * w - 0.5, 0, w - 1)
    y0, x0 = ys.astype(int), xs.astype(int)
    y1, x1 = np.minimum(y0 + 1, h - 1), np.minimum(x0 + 1, w - 1)
    fy, fx = (ys - y0)[:, None, None].astype('f'), (xs - x0)[None, :, None].astype('f')
    return (a[y0][:, x0] * (1 - fy) * (1 - fx) + a[y1][:, x0] * fy * (1 - fx)
            + a[y0][:, x1] * (1 - fy) * fx + a[y1][:, x1] * fy * fx)


LM_W, LM_H = 448, 300
lm = D.images.new('pitch_light', LM_W, LM_H, float_buffer=True)
pm = target.data.materials[0]
lnode = pm.node_tree.nodes.new('ShaderNodeTexImage'); lnode.image = lm
pm.node_tree.nodes.active = lnode
bk.target = 'IMAGE_TEXTURES'
sc.cycles.samples = 160
select_only([target], target)
t0 = time.time()
bpy.ops.object.bake(type='DIFFUSE')
print('PITCH BAKE %.0fs' % (time.time() - t0))
lmap = np.empty(LM_W * LM_H * 4, 'f'); lm.pixels.foreach_get(lmap)
lmap = lmap.reshape(LM_H, LM_W, 4)[..., :3].copy()
lmap = (lmap + np.roll(lmap, 1, 0) + np.roll(lmap, -1, 0) + np.roll(lmap, 1, 1) + np.roll(lmap, -1, 1)) / 5
pm.node_tree.nodes.remove(lnode)
inner = lmap[int(LM_H * 0.2):int(LM_H * 0.8), int(LM_W * 0.2):int(LM_W * 0.8)]
lum = float((inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1).mean())
EXPOSE = 0.8 / max(lum, 1e-6)
print('PITCH LIGHT %.3f  EXPOSE %.4f' % (lum, EXPOSE))
out_px = np.clip(out_px * upsample(lmap, H, W) * (EXPOSE * GAIN), 0, 1)
px[..., :3] = np.where(out_px <= 0.0031308, 12.92 * out_px, 1.055 * out_px ** (1 / 2.4) - 0.055)
pimg.pixels.foreach_set(px.ravel())
del out_px, px
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
sc.view_settings.view_transform = 'Standard'
pimg.save_render(TEX_DIR + '/arena_pitch.jpg')
pjpg = D.images.load(TEX_DIR + '/arena_pitch.jpg')
target.data.materials.clear(); target.data.materials.append(image_material('M_Pitch', pjpg, 0.9))

# text -> mesh
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in D.objects if o.type == 'FONT']:
    me = D.meshes.new_from_object(o.evaluated_get(dg))
    nobj = D.objects.new(o.name + '_mesh', me)
    nobj.matrix_world = o.matrix_world.copy()
    o.users_collection[0].objects.link(nobj)
    D.objects.remove(o, do_unlink=True)
bpy.context.view_layer.update()

skip = ('Pitch_Grass', 'Pitch_Lines', 'Pitch_Surround', 'StadiumGoals', 'ScreenFace_', 'Scoreboard_', 'Banners')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
# what hangs over the pitch (the screens' boxes and the banners) is its own
# object, 'StadiumHang': the game cuts everything over the pitch away except
# this and the screens (game.stadium.js: dressStadium)
HANG = [o for o in sc.objects if o.type == 'MESH' and o.name.startswith(('Scoreboard_', 'Banners'))]
for o in export + HANG + [goals]:
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
select_only(export, target)
bpy.ops.object.join()
target.name = 'JohanCruijffArena'
select_only(HANG, HANG[0])
bpy.ops.object.join()
hang = HANG[0]
hang.name = 'StadiumHang'
bpy.context.view_layer.update()

SELF_LIT = {'M_Pitch', 'M_LEDRed', 'M_Lettering', 'M_FloodLight', 'M_GlassLit', 'M_Escalator', 'M_TowerGlass'}


def bake_light(obj):
    # the night light into the vertex colours, at the pitch's exposure; what
    # lights itself (LEDs, lettering, lamps) stays at full strength
    me = obj.data
    me.color_attributes.active_color = me.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')
    bk.target = 'VERTEX_COLORS'
    sc.cycles.samples = 128
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


bake_light(target)
bake_light(hang)
gc = goals.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
gc.data.foreach_set('color', [0.45, 0.45, 0.45, 1.0] * len(gc.data))
goals.data.color_attributes.active_color = gc
goals.data.color_attributes.render_color_index = goals.data.color_attributes.find('Col')
for m in D.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0

bb = [target.matrix_world @ Vector(cc) for cc in target.bound_box]
mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
s = 264 / max(mx[0] - mn[0], mx[1] - mn[1])
cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
print('BOUNDS', mn, mx)
print('PITCH x=%.2f z=%.2f w=%.2f l=%.2f y=%.2f' % (-cx * s, cy * s, PW * s, PL * s, -mn[2] * s))
print('TRIS', sum(len(p.vertices) - 2 for p in target.data.polygons), 'MATS', len(target.data.materials))
select_only([target, hang, goals, screens], target)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
extra = {}
if 'export_vertex_color' in props: extra['export_vertex_color'] = 'ACTIVE'
if 'export_all_vertex_colors' in props: extra['export_all_vertex_colors'] = False
if 'export_active_vertex_color_when_no_material' in props: extra['export_active_vertex_color_when_no_material'] = True
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, **extra)
print('EXPORTED', OUT_GLB)
