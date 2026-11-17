# Builds De Kuip (Stadion Feyenoord, Rotterdam) from nothing and exports it for
# the game, the way MetLife is built: the pitch lines on the game's pitch, the
# night light baked into the model.
#   blender -b --factory-startup --python tools/dekuip_build.py -- <out.blend> <out.glb> <texture dir>
#
# As on the photos: a steep bowl of two rings close to the pitch, blue seats with
# red stairs. The upper ring hangs out over the lower one, with a row of glass
# boxes under it and a red band on its front; the two live scoreboards hang in
# that band behind the goals, as in the stadium. One roof over
# all the stands: silver on top, steel trusses underneath, floodlights along its
# edge. Outside: white steel columns with cross bracing, red stair towers, blue
# and grey cladding, "stadion feyenoord" over the front, and the four lattice
# floodlight masts at the corners. No club or sponsor logos.
#
# The helpers, the pitch and the export are the ones of tools/metlife_build.py.
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

# the pitch the game plays on (88 x 56, as in the other stadiums), and the bowl
# as a rounded rectangle round an 86 x 48 core: everything at a distance r from
# it. The front wall at r = 12 keeps every stand out of the block the game cuts
# away towards the camera (|x| < 51.2, y > -32.4 in these units).
PW, PL = 88.0, 56.0
K = PW / 105.0
LINE = 0.14
FLOOR_X, FLOOR_Y = 56.0, 37.0
CX, CY = 43.0, 24.0
SEG = 12
N_RING = 4 * (SEG + 1)
GAIN = 2.0                      # the game draws the model unlit at this gain (catalog: look.gain)
SEAT_W = 0.5

WALL_R, WALL_Z = 12.0, 2.6                                          # the wall round the pitch
LOW = dict(r=12.3, z=2.0, rows=24, depth=0.78, rise=0.40)           # lower ring: to r 31.0, z 11.2
SKY_R = LOW['r'] + LOW['depth'] * LOW['rows']                       # the glass boxes at its back
SKY_Z0 = LOW['z'] + LOW['rise'] * (LOW['rows'] - 1)
BAND_R, BAND_Z0, BAND_Z1 = 26.6, 14.8, 16.9                         # front of the upper ring, out over the lower one
SKY_Z1 = BAND_Z0
UP = dict(r=26.9, z=16.5, rows=22, depth=0.82, rise=0.60)           # upper ring: to r 44.9, z 29.1
UP_BACK = UP['r'] + UP['depth'] * UP['rows']
UP_TOP = UP['z'] + UP['rise'] * (UP['rows'] - 1)
FACADE_R = 47.5
ROOF_IN, ROOF_OUT = 14.0, 50.5                                      # the roof reaches almost to the pitch
ROOF_TOP = [(14.0, 39.4), (20.0, 39.4), (26.0, 39.3), (32.0, 39.0), (38.0, 38.3), (43.0, 37.0), (47.5, 35.0), (50.5, 32.2)]   # a cap with a steep flank: seen from the street over the facade
UNDER_IN, UNDER_OUT = 37.5, 31.9                                    # its underside, straight from the edge to the facade
MAST_R, MAST_H = 60.0, 56.0


def under_z(r):
    return UNDER_IN + (UNDER_OUT - UNDER_IN) * (min(r, FACADE_R) - ROOF_IN) / (FACADE_R - ROOF_IN)


# ---------------------------------------------------------------- helpers (as in the MetLife script)
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
rng = np.random.default_rng(1937)


def seat_tile(color):
    t = np.zeros((32, 32, 3), 'f')
    t[:] = np.array(color, 'f') * np.linspace(0.62, 1.0, 32)[:, None, None]
    t[:, :2] *= 0.22; t[:, -2:] *= 0.22
    t[-2:] *= 1.12
    return t


PANES, PANE_W = 16, 2.0


def windows_tex():
    pw, h = 64, 128
    t = np.zeros((h, pw * PANES, 3), 'f')
    v = np.linspace(0, 1, h)[:, None]
    for k in range(PANES):
        x0 = k * pw
        if rng.random() < 0.8:
            warm = np.array((1.0, 0.80, 0.58), 'f') * rng.uniform(0.35, 0.7)
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


def ribs_tex():
    # the roof: corrugated aluminium, the ribs running from the edge outwards
    w, h = 128, 16
    x = np.arange(w) / w
    rib = 0.80 + 0.20 * np.cos(x * 2 * np.pi * 8)
    return np.ones((h, w, 3), 'f') * np.array((0.74, 0.75, 0.77), 'f') * rib[None, :, None]


CLAD_U, CLAD_Z0, CLAD_Z1 = 12.0, 17.0, 29.6


def cladding_tex():
    # the back of the upper ring: grey panels with seams, a row of small windows
    w, h = 256, 256
    mx, mz = CLAD_U / w, (CLAD_Z1 - CLAD_Z0) / h
    t = np.ones((h, w, 3), 'f') * np.array((0.30, 0.31, 0.33), 'f')
    t *= (1 + 0.03 * rng.normal(0, 1, (1, w, 1))).astype('f')
    yy, xx = np.arange(h) * mz, np.arange(w) * mx
    t[(yy % 1.4) < mz * 1.5] *= 0.6
    t[:, (xx % 3.0) < mx * 1.5] *= 0.7
    win = ((yy > 7.0) & (yy < 8.3))[:, None] & ((xx % 3.0 > 0.5) & (xx % 3.0 < 2.5))[None, :]
    t[win] = np.array((0.06, 0.07, 0.09), 'f')
    return t[::-1]


seat_blues = [image_material('M_Seat%d' % i, painted('kuip_seat%d' % i, seat_tile(c)), 0.6)
              for i, c in enumerate(((0.025, 0.05, 0.40), (0.02, 0.04, 0.33), (0.03, 0.06, 0.46)))]
concrete = principled('M_Concrete', (0.46, 0.46, 0.47), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.20, 0.20, 0.21), 0.9)
concrete_light = principled('M_ConcreteLight', (0.62, 0.62, 0.63), 0.85)
red = principled('M_Red', (0.55, 0.03, 0.03), 0.6)
led_red = principled('M_LEDRed', (0.70, 0.04, 0.04), 0.4, (0.70, 0.04, 0.04), 3.0)      # the red bands
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
glass_lit = image_material('M_GlassLit', painted('kuip_windows', windows_tex()), 0.2)
steel_white = principled('M_SteelWhite', (0.80, 0.81, 0.83), 0.5)
steel = principled('M_Steel', (0.36, 0.37, 0.40), 0.5, metallic=0.3)
steel_dark = principled('M_SteelDark', (0.08, 0.08, 0.09), 0.6)
roof_top = image_material('M_RoofTop', painted('kuip_roof', ribs_tex()), 0.45, 0.2)
roof_under = principled('M_RoofUnder', (0.30, 0.31, 0.33), 0.8)
roof_clear = principled('M_RoofClear', (0.55, 0.57, 0.60), 0.5)                         # the translucent front part
blue_panel = principled('M_BluePanel', (0.03, 0.08, 0.30), 0.6)
dark_panel = principled('M_DarkPanel', (0.08, 0.08, 0.09), 0.8)
cladding = image_material('M_Cladding', painted('kuip_cladding', cladding_tex()), 0.7)
fascia = principled('M_Fascia', (0.80, 0.81, 0.83), 0.5)
lamp = principled('M_FloodLight', (1.0, 1.0, 0.96), 0.3, (1.0, 1.0, 0.95), 3.0)
asphalt = principled('M_Asphalt', (0.05, 0.05, 0.055), 0.95)
lawn = principled('M_Lawn', (0.05, 0.13, 0.05), 0.95)
plaza = principled('M_Plaza', (0.30, 0.30, 0.31), 0.9)
flag_green = principled('M_FlagGreen', (0.0, 0.30, 0.10), 0.8)
flag_white = principled('M_FlagWhite', (0.85, 0.85, 0.85), 0.8)
flag_red = principled('M_FlagRed', (0.70, 0.03, 0.03), 0.8)

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
net_img = D.images.new('kuip_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/kuip_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
AISLE_EVERY, AISLE_W, BLOCK_SEATS = 13.0, 1.2, 4
UP_V = Vector((0, 0, 1))
V3 = lambda p, z: Vector((p[0], p[1], z))


def seat_row(bm, aisles, a, b, block, rise):
    # one row of seats on a tread; a: its front corners, b: its back corners.
    # Seats come in blocks of `block`, each block one of three blues; the stairs
    # between the blocks are painted red, as in the stadium.
    length = (a[1] - a[0]).length
    spans = [(0.0, length)]
    back = (b[0] - a[0]).normalized()
    if length > 16:
        cuts = [c for c in (length / 2 + j * AISLE_EVERY for j in range(-10, 11)) if AISLE_W < c < length - AISLE_W]
        edges = [0.0] + [c + d for c in cuts for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        lift = Vector((0, 0, 0.012))
        for c in cuts:
            u0, u1 = (c - AISLE_W / 2) / length, (c + AISLE_W / 2) / length
            f0, f1 = a[0].lerp(a[1], u0), a[0].lerp(a[1], u1)
            face(aisles, [f0 + lift, f1 + lift, b[0].lerp(b[1], u1) + lift, b[0].lerp(b[1], u0) + lift], UP_V, 0)
            if rise:
                down, out = Vector((0, 0, -rise)), -back * 0.012
                face(aisles, [f0 + down + out, f1 + down + out, f1 + out, f0 + out], -back, 0)
    for s0, s1 in spans:
        seats = max(1, round((s1 - s0) / SEAT_W))
        for k in range(0, seats, block):
            k1 = min(k + block, seats)
            u = [(s0 + (s1 - s0) * q / seats) / length for q in (k, k1)]
            pa = [a[0].lerp(a[1], t) for t in u]; pb = [b[0].lerp(b[1], t) for t in u]

            def at(t, h, i):
                return pa[i].lerp(pb[i], t) + Vector((0, 0, h))
            mat = random.choice((0, 0, 1, 2))
            face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UP_V, mat, [(k, 0.0), (k1, 0.0), (k1, 0.45), (k, 0.45)])
            face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, mat, [(k, 0.45), (k1, 0.45), (k1, 0.95), (k, 0.95)])
            face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UP_V, mat, [(k, 0.95), (k1, 0.95), (k1, 1.0), (k, 1.0)])


def build_tier(name, t, base_z, block=BLOCK_SEATS):
    steps, seats, aisles = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, z = t['r'] + t['depth'] * k, t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        ring(steps, r0, z_prev, r0, z, 1)
        ring(steps, r0, z, r0 + t['depth'], z, 0)
        p0, p1 = ring_path(r0), ring_path(r0 + t['depth'])
        for i in range(N_RING):
            j = (i + 1) % N_RING
            seat_row(seats, aisles, [V3(p0[i], z), V3(p0[j], z)], [V3(p1[i], z), V3(p1[j], z)], block, t['rise'] if k else 0)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_blues)
    new_obj('Aisles_' + name, aisles, '02_Bowl', [red])


def band_text(name, r, z0, z1, texts, step):
    for i, (x, y, a) in enumerate(ring_points(r, step)):
        wall_text('%s_T%d' % (name, i), texts[i % len(texts)], (x, y, z0 + (z1 - z0) * 0.2), a, (z1 - z0) * 0.62, '02_Bowl', letters_white)


random.seed(1937)
build_tier('Lower', LOW, 0.0)
build_tier('Upper', UP, BAND_Z0, block=6)

# the wall round the pitch, the walkway along it, the red LED boards on it
bm = bmesh.new()
ring(bm, WALL_R, 0.0, WALL_R, WALL_Z, 0)
ring(bm, WALL_R, WALL_Z, LOW['r'], WALL_Z, 0, want='up')
ring(bm, LOW['r'], WALL_Z, LOW['r'], LOW['z'], 0, want='out')
ring(bm, 10.6, 0.03, WALL_R, 0.03, 1, want='up')
new_obj('Pitch_Wall', bm, '02_Bowl', [concrete_dark, concrete])
bm = bmesh.new()
ring(bm, WALL_R - 0.06, 0.15, WALL_R - 0.06, 1.05, 0)
new_obj('LED_Boards', bm, '02_Bowl', [led_red])
band_text('Boards', WALL_R - 0.1, 0.15, 1.05, ['FEYENOORD', 'DE KUIP', 'ROTTERDAM'], 11.0)

# the glass boxes at the back of the lower ring, under the overhang
bm = bmesh.new()
ring(bm, SKY_R, SKY_Z0, SKY_R, SKY_Z0 + 0.6, 0)
ring(bm, SKY_R, SKY_Z0 + 0.6, SKY_R, SKY_Z1 - 0.8, 1, u_len=PANE_W * PANES)
ring(bm, SKY_R, SKY_Z1 - 0.8, SKY_R, SKY_Z1, 2)                     # the red rail over them
ring(bm, BAND_R, BAND_Z0, SKY_R, BAND_Z0, 0, want='down')           # the underside of the overhang
new_obj('Skyboxes', bm, '02_Bowl', [concrete_light, glass_lit, red])
bm = bmesh.new()
for x, y, a in ring_points(SKY_R - 0.07, 3.0):
    box(bm, (x, y), (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.06, (math.cos(a), math.sin(a)), 0.06, SKY_Z0 + 0.6, SKY_Z1 - 0.8, 0)
new_obj('Skyboxes_Mullions', bm, '02_Bowl', [concrete_light])

# the red band on the front of the upper ring
bm = bmesh.new()
ring(bm, BAND_R, BAND_Z0, BAND_R, BAND_Z1, 0)
ring(bm, BAND_R, BAND_Z1, UP['r'], BAND_Z1, 1, want='up')
ring(bm, UP['r'], BAND_Z1, UP['r'], UP['z'], 1, want='out')
new_obj('Band', bm, '02_Bowl', [led_red, concrete])
band_text('Band', BAND_R - 0.06, BAND_Z0, BAND_Z1, ['STADION FEYENOORD', 'DE KUIP', 'ROTTERDAM', 'SINDS 1937'], 19.0)

# the back of the upper ring: a wall up to the roof, red framed doorways in it
bm = bmesh.new()
ring(bm, UP_BACK, UP_TOP, UP_BACK, under_z(UP_BACK), 0)
new_obj('Upper_Back', bm, '02_Bowl', [concrete_dark])
bm = bmesh.new()
for x, y, a in ring_points(UP_BACK - 0.3, 14.0):
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    c = Vector((x, y, 0))
    for s in (-1, 1):
        p = c + t * s * 1.6
        box(bm, (p.x, p.y), (t.x, t.y), 0.2, (n.x, n.y), 0.3, UP_TOP, UP_TOP + 2.2, 0)
    box(bm, (c.x, c.y), (t.x, t.y), 1.8, (n.x, n.y), 0.3, UP_TOP + 2.2, UP_TOP + 2.6, 0)
    q = c + n * 0.25
    face(bm, [q - t * 1.4 + Vector((0, 0, UP_TOP)), q + t * 1.4 + Vector((0, 0, UP_TOP)),
              q + t * 1.4 + Vector((0, 0, UP_TOP + 2.2)), q - t * 1.4 + Vector((0, 0, UP_TOP + 2.2))], -n, 1)
new_obj('Upper_Doors', bm, '02_Bowl', [red, steel_dark])

# the two live scoreboards (game.screen.js, style 'kuip'): in the band behind
# both goals, as in the stadium. Exported together as 'StadiumScreens'.
SCREEN_W, SCREEN_H = 17.0, 3.4
SCREEN_Z = BAND_Z0 - 0.4
SCREEN_R = BAND_R - 0.35
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.6, 0.05, 0.05), 2.0)
SCREEN_FACES = []
for sx in (1, -1):
    d = Vector((sx, 0, 0))                                          # out from the middle of the end
    tn = Vector((-d.y, d.x, 0))
    c = Vector((sx * CX, 0, 0)) + d * SCREEN_R
    bm = bmesh.new()
    box(bm, (c.x + d.x * 0.18, c.y + d.y * 0.18), (tn.x, tn.y), SCREEN_W / 2 + 0.35, (d.x, d.y), 0.15, SCREEN_Z - 0.35, SCREEN_Z + SCREEN_H + 0.35, 0)
    new_obj('Scoreboard_%d' % sx, bm, '02_Bowl', [steel_dark])
    fb = bmesh.new()
    face(fb, [c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)), c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)),
              c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H)), c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H))],
         -d, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])                  # u left to right as seen from the pitch
    SCREEN_FACES.append(new_obj('ScreenFace_%d' % sx, fb, '02_Bowl', [live]))

# ================================================================ the roof
bm = bmesh.new()
for (r0, z0), (r1, z1) in zip(ROOF_TOP, ROOF_TOP[1:]):
    ring(bm, r0, z0, r1, z1, 0, want='up', u_len=6.0, v_range=(0, (r1 - r0) / 6.0))
ring(bm, ROOF_IN, UNDER_IN, ROOF_IN, ROOF_TOP[0][1], 1)                      # the white inner edge
ring(bm, ROOF_OUT, UNDER_OUT, ROOF_OUT, ROOF_TOP[-1][1], 1, want='out')      # and the outer one
ring(bm, ROOF_IN, UNDER_IN, 26.0, under_z(26.0), 2, want='down')             # translucent front part
ring(bm, 26.0, under_z(26.0), FACADE_R, UNDER_OUT, 3, want='down')
ring(bm, FACADE_R, UNDER_OUT, ROOF_OUT, UNDER_OUT, 3, want='down')
new_obj('Roof', bm, '04_Roof', [roof_top, fascia, roof_clear, roof_under])

# the steel trusses under it: a top and a bottom chord out from the edge,
# verticals, diagonals across to the next truss, four ring beams
bm = bmesh.new()
TRUSS = ring_points(30.0, 6.0)


def under(p, r, dz):
    x, y, a = p
    q = Vector((x, y, 0)) + Vector((math.cos(a), math.sin(a), 0)) * (r - 30.0)
    return Vector((q.x, q.y, under_z(r) - dz))


for i, p in enumerate(TRUSS):
    q = TRUSS[(i + 1) % len(TRUSS)]
    tube(bm, under(p, ROOF_IN + 0.6, 0.15), under(p, FACADE_R - 0.3, 0.15), 0.16, 0, seg=4)
    tube(bm, under(p, ROOF_IN + 2.0, 1.3), under(p, FACADE_R - 2.0, 1.3), 0.12, 0, seg=4)
    for r in (18.0, 26.0, 34.0, 42.0):
        tube(bm, under(p, r, 1.3), under(p, r, 0.15), 0.08, 0, seg=4)
    for r0, r1 in ((18.0, 26.0), (26.0, 34.0), (34.0, 42.0)):
        tube(bm, under(p, r0, 1.3), under(q, r1, 0.15), 0.07, 0, seg=4)
for r in (18.0, 26.0, 34.0, 42.0):
    ring(bm, r, under_z(r) - 0.9, r, under_z(r) - 0.15, 0, step=6)
new_obj('Roof_Trusses', bm, '04_Roof', [steel_white])

# floodlights all along the inner edge, facing the pitch
bm = bmesh.new()
for x, y, a in ring_points(ROOF_IN + 0.4, 2.4):
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    c = Vector((x, y, UNDER_IN - 0.45))
    lo, hi = Vector((0, 0, -0.3)), Vector((0, 0, 0.3))
    face(bm, [c - t * 0.7 + lo, c + t * 0.7 + lo, c + t * 0.7 + hi, c - t * 0.7 + hi], -n, 0)
new_obj('Roof_Lamps', bm, '04_Roof', [lamp])

# ================================================================ outside
# From the ground up, as on the photo of the front: a dark ground floor, a lit
# concourse, the blue cladding of the lower ring, an open gallery, the lit
# upper concourse, the grey back of the upper ring, a white band under the roof.
bm = bmesh.new()
ring(bm, FACADE_R, 0.0, FACADE_R, 3.0, 0, want='out')
ring(bm, FACADE_R, 3.0, FACADE_R, 6.2, 1, want='out', u_len=PANE_W * PANES)
ring(bm, FACADE_R, 6.2, FACADE_R, 12.8, 2, want='out')
ring(bm, FACADE_R, 12.8, FACADE_R, CLAD_Z0, 1, want='out', u_len=PANE_W * PANES * 1.2)
ring(bm, FACADE_R, CLAD_Z0, FACADE_R, CLAD_Z1, 3, want='out', u_len=CLAD_U)
ring(bm, FACADE_R, CLAD_Z1, FACADE_R, UNDER_OUT, 4, want='out')
for z in (6.2, 12.8):                                                # the two open galleries with their rails
    ring(bm, FACADE_R, z, FACADE_R + 1.8, z, 5, want='up')
    ring(bm, FACADE_R, z - 0.3, FACADE_R + 1.8, z - 0.3, 5, want='down')
    ring(bm, FACADE_R + 1.8, z - 0.3, FACADE_R + 1.8, z, 5, want='out')
    ring(bm, FACADE_R + 1.75, z + 0.95, FACADE_R + 1.75, z + 1.1, 6, want='out')
    ring(bm, FACADE_R + 1.75, z + 0.45, FACADE_R + 1.75, z + 0.53, 6, want='out')
new_obj('Facade', bm, '05_Outside', [dark_panel, glass_lit, blue_panel, cladding, fascia, concrete, steel_white])

# the white steel frame under the roof edge: columns, cross bracing in every
# third bay, a beam along the top
bm = bmesh.new()
COLS = ring_points(ROOF_OUT - 0.9, 11.0)
cp = lambda p, z: Vector((p[0], p[1], z))
for x, y, a in COLS:
    box(bm, (x, y), (math.cos(a), math.sin(a)), 0.45, (-math.sin(a), math.cos(a)), 0.45, 0.0, UNDER_OUT, 0)
for i in range(0, len(COLS), 3):
    p, q = COLS[i], COLS[(i + 1) % len(COLS)]
    for z0, z1 in ((0.0, UNDER_OUT / 2), (UNDER_OUT / 2, UNDER_OUT)):
        tube(bm, cp(p, z0), cp(q, z1), 0.13, 0, seg=4)
        tube(bm, cp(q, z0), cp(p, z1), 0.13, 0, seg=4)
for p, q in zip(COLS, COLS[1:] + COLS[:1]):
    tube(bm, cp(p, UNDER_OUT - 0.3), cp(q, UNDER_OUT - 0.3), 0.25, 0, seg=4)
new_obj('Facade_Steel', bm, '05_Outside', [steel_white])

# ten red stair towers, zigzag flights up to the upper gallery
bm = bmesh.new()
for x, y, a in ring_points(FACADE_R + 0.9, ring_len(FACADE_R + 0.9) / 10):
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    c = Vector((x, y, 0))
    rise = 12.8 / 4
    for k in range(4):
        s = 1 if k % 2 == 0 else -1
        p0 = c - t * 2.6 * s + Vector((0, 0, rise * k))
        p1 = c + t * 2.6 * s + Vector((0, 0, rise * (k + 1)))
        slab(bm, p0, p1, n, 1.2, 0.22, 0)
        tube(bm, p0 + n * 0.6 + Vector((0, 0, 1.0)), p1 + n * 0.6 + Vector((0, 0, 1.0)), 0.05, 0, seg=4)
        slab(bm, p1 - t * 0.5 * s, p1 + t * 0.5 * s, n, 1.2, 0.22, 0)     # the landing
    for sa in (-1, 1):
        for sb in (-1, 1):
            p = c + t * 3.1 * sa + n * 0.6 * sb
            tube(bm, Vector((p.x, p.y, 0)), Vector((p.x, p.y, 13.9)), 0.09, 0, seg=4)
new_obj('Stair_Towers', bm, '05_Outside', [red])

# "stadion feyenoord" over the front, in front of the columns
FRONT_Y = CY + ROOF_OUT + 0.5
wall_text('Facade_Name', 'stadion feyenoord', (0, FRONT_Y, 4.2), 3 * math.pi / 2, 5.0, '05_Outside', letters_white, font=NAME_FONT, extrude=0.12)

# flags in front of it: Rotterdam (green white green) and red | white
bm = bmesh.new()
for i, x in enumerate((-33.0, -22.0, -11.0, 11.0, 22.0, 33.0)):
    y = FRONT_Y + 7.0
    tube(bm, Vector((x, y, 0)), Vector((x, y, 15.0)), 0.12, 0, seg=6)
    if i % 2 == 0:
        parts = [((0.0, 3.2), (12.2, 13.0), 1), ((0.0, 3.2), (13.0, 13.8), 2), ((0.0, 3.2), (13.8, 14.6), 1)]
    else:
        parts = [((0.0, 1.6), (12.2, 14.6), 3), ((1.6, 3.2), (12.2, 14.6), 2)]
    for (u0, u1), (z0, z1), m in parts:
        for side in (1, -1):
            dy = 0.02 * side
            face(bm, [(x + 0.1 + u0, y + dy, z0), (x + 0.1 + u1, y + dy, z0), (x + 0.1 + u1, y + dy, z1), (x + 0.1 + u0, y + dy, z1)],
                 Vector((0, side, 0)), m)
new_obj('Flags', bm, '05_Outside', [steel_white, flag_green, flag_white, flag_red])

# the four lattice floodlight masts at the corners
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
    base = Vector((sx * CX, sy * CY, 0)) + Vector((sx, sy, 0)).normalized() * MAST_R
    bm = bmesh.new()

    def leg(k, z):
        hw = 2.4 - 1.4 * z / MAST_H
        ox, oy = ((1, 1), (-1, 1), (-1, -1), (1, -1))[k]
        return Vector((base.x + ox * hw, base.y + oy * hw, z))
    for k in range(4):
        tube(bm, leg(k, 0), leg(k, MAST_H), 0.18, 0, seg=4)
    LEVELS = 14
    for lv in range(LEVELS):
        z0, z1 = MAST_H * lv / LEVELS, MAST_H * (lv + 1) / LEVELS
        for k in range(4):
            k2 = (k + 1) % 4
            tube(bm, leg(k, z1), leg(k2, z1), 0.08, 0, seg=4)
            if lv % 2:
                tube(bm, leg(k, z0), leg(k2, z1), 0.07, 0, seg=4)
            else:
                tube(bm, leg(k2, z0), leg(k, z1), 0.07, 0, seg=4)
    # the head: a frame tilted towards the centre spot, rows of lamps on it
    top = Vector((base.x, base.y, MAST_H + 3.0))
    f = (Vector((0, 0, 0)) - top).normalized()
    right = f.cross(Vector((0, 0, 1))).normalized()
    upv = right.cross(f).normalized()
    quad = lambda cx, cy, w, h, off: [top + right * (cx + w * a) + upv * (cy + h * b) + f * off for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    face(bm, quad(0, 0, 4.6, 3.3, -0.25), -f, 0)
    face(bm, quad(0, 0, 4.6, 3.3, 0.0), f, 1)
    for i in range(6):
        for j in range(4):
            face(bm, quad(-3.75 + 1.5 * i, -2.4 + 1.6 * j, 0.6, 0.6, 0.06), f, 2)
    tube(bm, Vector((base.x, base.y, MAST_H)), top - f * 0.3, 0.35, 0, seg=6)
    new_obj('Mast_%d%d' % (sx, sy), bm, '05_Outside', [steel, steel_dark, lamp])

bm = bmesh.new()
for r0, r1, m in ((-2, 24, 2), (24, 44, 0), (44, 60, 1)):                     # a paved square, roads and car parks, grass
    n = math.ceil((r1 - r0) / 4)                                                  # in narrow rings, so the baked light stays smooth
    for k in range(n):
        ring(bm, FACADE_R + r0 + (r1 - r0) * k / n, -0.05, FACADE_R + r0 + (r1 - r0) * (k + 1) / n, -0.05, m, want='up', step=4)
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
pimg = D.images.new('kuip_pitch', PW_PX, PH_PX)
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


# De Kuip's pitch: mown in squares, a checkerboard of 16 x 10, a dark run-off
bands_x = np.tanh(np.sin(np.pi * X / 5.5) * 6) * np.tanh(np.sin(np.pi * Y / 5.6) * 6)
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = (1 + 0.11 * bands_x + 0.055 * vnoise(420, 420) + 0.035 * vnoise(48, 48)
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


NIGHT = dict(flood=5000, stand=4000, roof=1500, facade=15000, moon=0.7)   # the masts only glow: the roof lights the pitch
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)
coll = D.collections.new('10_NightLights'); sc.collection.children.link(coll)
FLOOD = (1.0, 0.98, 0.94)
for x, y, a in ring_points(ROOF_IN + 0.6, 4.0):                     # the floodlights along the roof edge
    light(coll, 'SPOT', (x, y, UNDER_IN - 0.8), NIGHT['flood'], FLOOD, target=(x * 0.15, y * 0.15, 0), size=70)
for x, y, a in ring_points(ROOF_IN + 0.6, 8.0):                     # and some across onto the stands
    light(coll, 'SPOT', (x, y, UNDER_IN - 0.8), NIGHT['stand'], FLOOD, target=(-x * 0.75, -y * 0.75, 10), size=80, blend=0.6)
for x, y, a in ring_points(36.0, 10.0):                             # lights under the roof, over the upper ring
    light(coll, 'POINT', (x, y, under_z(36.0) - 1.2), NIGHT['roof'], (1.0, 0.95, 0.88))
light(coll, 'SUN', (0, 0, 120), NIGHT['moon'], (0.80, 0.86, 1.0), target=(30, 20, 0))   # a soft light from the sky: the silver roof reads at night
for x, y, a in ring_points(FACADE_R + 14, 14.0):                    # the facade
    light(coll, 'SPOT', (x, y, 0.5), NIGHT['facade'], (0.86, 0.90, 1.0), target=(x - 14 * math.cos(a), y - 14 * math.sin(a), 16), size=75, blend=0.6)
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
pimg.save_render(TEX_DIR + '/kuip_pitch.jpg')
pjpg = D.images.load(TEX_DIR + '/kuip_pitch.jpg')
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

skip = ('Pitch_Grass', 'Pitch_Lines', 'Pitch_Surround', 'StadiumGoals', 'ScreenFace_')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals]:
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
target.name = 'DeKuip'
bpy.context.view_layer.update()

me = target.data
me.color_attributes.active_color = me.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')
bk.target = 'VERTEX_COLORS'
sc.cycles.samples = 128
select_only([target], target)
t0 = time.time()
bpy.ops.object.bake(type='DIFFUSE')
print('MODEL BAKE %.0fs' % (time.time() - t0))
fc = me.color_attributes['Light']
c = np.empty(len(fc.data) * 4, 'f'); fc.data.foreach_get('color', c); c = c.reshape(-1, 4)
c[:, :3] = np.clip(c[:, :3] * EXPOSE, 0, 1)
SELF_LIT = {'M_Pitch', 'M_LEDRed', 'M_Lettering', 'M_FloodLight', 'M_GlassLit'}
mi = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('material_index', mi)
ls = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_start', ls)
lt = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_total', lt)
own = np.array([m is not None and m.name.split('.')[0] in SELF_LIT for m in me.materials])
order = np.argsort(ls)
loop_own = np.repeat(own[mi][order], lt[order])
lv = np.empty(len(me.loops), 'i'); me.loops.foreach_get('vertex_index', lv)
vert_own = np.zeros(len(me.vertices), bool); vert_own[lv[loop_own]] = True
print('LIGHT p10/p50/p90', [round(float(v), 3) for v in np.percentile(c[~vert_own, :3].mean(1), (10, 50, 90))])
c[vert_own, :3] = 1.0 / GAIN
c[:, 3] = 1
me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT').data.foreach_set('color', c.ravel())
me.color_attributes.remove(me.color_attributes['Light'])
ci = me.color_attributes.find('Col')
me.color_attributes.active_color_index = ci
me.color_attributes.render_color_index = ci
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
select_only([target, goals, screens], target)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
extra = {}
if 'export_vertex_color' in props: extra['export_vertex_color'] = 'ACTIVE'
if 'export_all_vertex_colors' in props: extra['export_all_vertex_colors'] = False
if 'export_active_vertex_color_when_no_material' in props: extra['export_active_vertex_color_when_no_material'] = True
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, **extra)
print('EXPORTED', OUT_GLB)
