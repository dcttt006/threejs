# Builds MetLife Stadium (New York New Jersey, the World Cup final) from
# nothing and exports it for the game, the way Lotto Park is finished:
# the pitch lines on the game's pitch, the night light baked into the model.
#   blender -b --factory-startup --python tools/metlife_build.py -- <out.blend> <out.glb> <texture dir>
#
# The stadium, as on the photos: a closed bowl without a roof, three tiers
# (a big lower ring, a middle ring with suites in front, a steep upper ring),
# dark grey seats, gold and navy LED bands between the tiers, gold walls round
# the pitch, a steel ring of floodlights over the rim, four big screens in the
# corners, WORLD CUP 26 over the far stand, and outside a facade of aluminium
# louvres with METLIFE STADIUM on it. No federation or sponsor logos.
import bpy, bmesh, math, os, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

OUT_BLEND, OUT_GLB, TEX_DIR = sys.argv[sys.argv.index('--') + 1:][:3]
bpy.ops.wm.read_factory_settings(use_empty=True)
D = bpy.data
sc = bpy.context.scene
for name in ('01_Pitch', '02_Bowl', '03_Seats', '04_Rim', '05_Outside'):
    c = D.collections.new(name)
    sc.collection.children.link(c)

# the pitch the game plays on, scaled like Lotto Park's (88 x 56), and the bowl
# as a rounded rectangle round an 86 x 49 core: everything at a distance r from
# it. The front wall stands at r = 12, so the game's cut-out never takes a stand.
PW, PL = 88.0, 56.0
K = PW / 105.0
LINE = 0.14
FLOOR_X, FLOOR_Y = 56.0, 37.5
CX, CY = 43.0, 24.5
SEG = 12
N_RING = 4 * (SEG + 1)
NE, NW, SW, SE = (set(range(k * (SEG + 1), k * (SEG + 1) + SEG)) for k in range(4))
N_SIDE, W_SIDE, S_SIDE, E_SIDE = (k * (SEG + 1) + SEG for k in range(4))
GAIN = 2.0                      # the game draws the model unlit at this gain (catalog: look.gain)
SEAT_W = 0.5

LOW = dict(r=12.0, z=1.4, rows=30, depth=0.82, rise=0.40)       # lower ring: up to r 36.6, z 13
CLUB_R, CLUB_Z0, CLUB_Z1 = 36.6, 13.0, 18.1                     # suites in front of the middle ring
MID = dict(r=37.9, z=19.1, rows=12, depth=0.86, rise=0.50)      # middle ring: up to r 48.2, z 24.6
SUITE_R, SUITE_Z0, SUITE_Z1 = 48.2, 24.6, 29.7                  # suites in front of the upper ring
UP = dict(r=49.5, z=30.7, rows=30, depth=0.86, rise=0.62)       # upper ring: up to r 75.3, z 48.7
RIM_R, RIM_Z = UP['r'] + UP['depth'] * UP['rows'], UP['z'] + UP['rise'] * (UP['rows'] - 1)
HALO_R0, HALO_R1, HALO_Z0, HALO_Z1 = 71.5, 78.0, 54.0, 55.6    # the floodlight ring over the rim
FACADE_R = 80.0


# ---------------------------------------------------------------- helpers (as in the Lotto Park script)
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


def wall_text(name, body, loc, outward, size, coll, mat):
    # a line of lettering standing up, facing away from `outward` (towards the pitch)
    cu = D.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.extrude = 0.0
    cu.font = LETTER_FONT
    cu.resolution_u = 2 if size < 2 else 4               # flat letters, few points on the curves: light for phones
    cu.offset = size * 0.022
    cu.materials.append(mat)
    t = D.objects.new(name, cu)
    t.location = loc
    t.rotation_euler = (math.pi / 2, 0, outward - math.pi / 2)
    D.collections[coll].objects.link(t)
    return t


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(2026)


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
            warm = np.array((1.0, 0.78, 0.55), 'f') * rng.uniform(0.35, 0.7)
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


LOUVRE_U, LOUVRE_Z0, LOUVRE_Z1 = 48.0, 5.5, 33.1


def louvre_tex():
    # the facade, as on the photo: bands of horizontal aluminium slats, panels
    # with thin seams, here and there the lit building showing through
    w, h = 1024, 512
    mx, mz = LOUVRE_U / w, (LOUVRE_Z1 - LOUVRE_Z0) / h          # metres per pixel
    y = np.arange(h, dtype='f')[:, None] * mz
    x = np.arange(w, dtype='f')[None, :] * mx
    slat = (np.sin(y / 0.42 * 2 * np.pi) * 0.5 + 0.5) ** 0.6     # a slat every 0.42 m: lit top, dark gap
    t = np.ones((h, w, 3), 'f') * np.array((0.60, 0.62, 0.66), 'f')
    t *= (0.55 + 0.45 * slat)[..., None]
    t *= (1 + 0.035 * rng.normal(0, 1, (h, 1, 1))).astype('f')
    t *= (1 + 0.06 * np.sign(np.sin(y / 1.35 * np.pi)))[..., None]   # the slats come in broad bands, as on the photo
    # through the slats: lit floors in places (stairs, concourses), dark elsewhere
    behind = np.zeros((h, w), 'f')
    for _ in range(9):                                            # long, low strips of light, faint
        x0, wd = rng.uniform(0, LOUVRE_U), rng.uniform(6, 14)
        z0, hd = rng.uniform(2, 22), rng.uniform(1.4, 2.4)
        xm = ((x - x0) % LOUVRE_U) < wd
        behind = np.maximum(behind, (xm & (y > z0) & (y < z0 + hd)).astype('f') * rng.uniform(0.10, 0.22))
    gap = (1 - slat)[..., None]
    t = t * (1 - 0.35 * gap) + np.array((1.0, 0.88, 0.70), 'f') * behind[..., None] * gap
    # panel seams: vertical every 6 m, a floor line every 6.9 m
    t[:, (np.arange(w) * mx % 6.0) < mx * 2] *= 0.55
    t[(np.arange(h) * mz % 6.9) < mz * 2] *= 0.6
    return t[::-1]                                                # row 0 is the top of the image


seat_greys = [image_material('M_Seat%d' % i, painted('metlife_seat%d' % i, seat_tile(c)), 0.6)
              for i, c in enumerate(((0.16, 0.17, 0.19), (0.12, 0.13, 0.15), (0.20, 0.21, 0.23)))]
concrete = principled('M_Concrete', (0.46, 0.46, 0.47), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.27, 0.27, 0.29), 0.9)
concrete_light = principled('M_ConcreteLight', (0.62, 0.62, 0.63), 0.85)
steel = principled('M_Steel', (0.36, 0.37, 0.40), 0.5, metallic=0.3)
steel_dark = principled('M_SteelDark', (0.12, 0.13, 0.15), 0.6)
navy = principled('M_Navy', (0.03, 0.04, 0.16), 0.5)
gold_wall = principled('M_GoldWall', (0.52, 0.40, 0.17), 0.6)
glass_lit = image_material('M_GlassLit', painted('metlife_windows', windows_tex()), 0.2)
led_band = principled('M_LED', (0.05, 0.06, 0.30), 0.4, (0.05, 0.06, 0.30), 4.0)            # the navy LED bands
led_gold = principled('M_LEDGold', (0.95, 0.70, 0.24), 0.4, (0.95, 0.70, 0.24), 3.0)        # their gold lettering
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
lamp = principled('M_FloodLight', (1.0, 1.0, 0.96), 0.3, (1.0, 1.0, 0.95), 3.0)
louvres = image_material('M_Louvres', painted('metlife_louvres', louvre_tex()), 0.5, 0.2)
fascia = principled('M_Fascia', (0.72, 0.74, 0.78), 0.45, metallic=0.2)
steel_white = principled('M_SteelWhite', (0.80, 0.81, 0.83), 0.5)
asphalt = principled('M_Asphalt', (0.05, 0.05, 0.055), 0.95)
lawn = principled('M_Lawn', (0.05, 0.13, 0.05), 0.95)

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
net_img = D.images.new('metlife_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/metlife_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
AISLE_EVERY, AISLE_W, BLOCK_SEATS = 16.0, 1.3, 4
UP_V = Vector((0, 0, 1))


def seat_row(bm, a, b, block):
    # one row of seats on a tread; a: its front corners, b: its back corners.
    # Seats come in blocks of `block`, each block one of three greys, like the
    # weathered mix of seats on the photos.
    length = (a[1] - a[0]).length
    spans = [(0.0, length)]
    if length > 20:
        cuts = [length / 2 + j * AISLE_EVERY for j in range(-8, 9)]
        edges = [0.0] + [c + d for c in cuts if AISLE_W < c < length - AISLE_W for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    back = (b[0] - a[0]).normalized()
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
    steps, seats = bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, z = t['r'] + t['depth'] * k, t['z'] + t['rise'] * k
        ring(steps, r0, base_z if k == 0 else z - t['rise'], r0, z, 1)
        ring(steps, r0, z, r0 + t['depth'], z, 0)
        p0, p1 = ring_path(r0), ring_path(r0 + t['depth'])
        for i in range(N_RING):
            j = (i + 1) % N_RING
            seat_row(seats, [Vector((p0[i][0], p0[i][1], z)), Vector((p0[j][0], p0[j][1], z))],
                     [Vector((p1[i][0], p1[i][1], z)), Vector((p1[j][0], p1[j][1], z))], block)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_greys)


random.seed(2026)
build_tier('Lower', LOW, 0.0)
build_tier('Middle', MID, CLUB_Z1)
build_tier('Upper', UP, SUITE_Z1, block=6)

# the gold wall round the pitch and the navy LED boards on it
bm = bmesh.new()
ring(bm, 12.0, 0.0, 12.0, LOW['z'], 0)
new_obj('Pitch_Wall', bm, '02_Bowl', [gold_wall])
bm = bmesh.new()
ring(bm, 11.9, 0.12, 11.9, 1.02, 0)
new_obj('LED_Boards', bm, '02_Bowl', [led_band])
n = 0
for sy in (1, -1):
    for x in range(-42, 43, 12):
        wall_text('Board_%d' % n, 'WORLD CUP 26', (x, sy * (CY + 11.88), 0.34), sy * math.pi / 2, 0.6, '02_Bowl', led_gold); n += 1
for sx in (1, -1):
    for y in range(-18, 19, 12):
        wall_text('Board_%d' % n, 'WORLD CUP 26', (sx * (CX + 11.88), y, 0.34), 0 if sx > 0 else math.pi, 0.6, '02_Bowl', led_gold); n += 1


def suites(name, r, z0, z1, top_r):
    # a band of suites: concrete sill, lit glass, concrete head, and the floor
    # over to the next tier; mullions every 4 m
    bm = bmesh.new()
    ring(bm, r, z0, r, z0 + 0.6, 0)
    ring(bm, r, z0 + 0.6, r, z1 - 1.6, 1, u_len=PANE_W * PANES)
    ring(bm, r, z1 - 1.6, r, z1, 0)
    ring(bm, r, z1, top_r, z1, 0)
    new_obj(name, bm, '02_Bowl', [concrete_light, glass_lit])
    bm = bmesh.new()
    for x, y, a in ring_points(r - 0.07, 4.0):
        box(bm, (x, y), (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.07, (math.cos(a), math.sin(a)), 0.07, z0 + 0.6, z1 - 1.6, 0)
    new_obj(name + '_Mullions', bm, '02_Bowl', [concrete_light])


def ribbon(name, r, z0, z1, text, repeat):
    # an LED band, navy with gold lettering, all the way round
    bm = bmesh.new()
    ring(bm, r, z0, r, z1, 0)
    new_obj(name, bm, '02_Bowl', [led_band])
    for i, (x, y, a) in enumerate(ring_points(r - 0.06, repeat)):
        body = text[i % len(text)]
        wall_text('%s_T%d' % (name, i), body, (x, y, z0 + (z1 - z0) * 0.18), a, (z1 - z0) * 0.66, '02_Bowl', led_gold)


suites('Suites_Club', CLUB_R, CLUB_Z0, CLUB_Z1 - 1.0, MID['r'])
ribbon('Ribbon_Club', MID['r'] - 0.1, CLUB_Z1 - 1.0, CLUB_Z1 + 0.9, ['WORLD CUP 26', 'NEW YORK NEW JERSEY'], 22)
suites('Suites_Upper', SUITE_R, SUITE_Z0, SUITE_Z1 - 1.0, UP['r'])
ribbon('Ribbon_Upper', UP['r'] - 0.1, SUITE_Z1 - 1.0, SUITE_Z1 + 0.9, ['METLIFE STADIUM', 'WORLD CUP 26'], 24)

# the rim: a parapet at the back of the upper ring and the concourse roof out to the facade
bm = bmesh.new()
ring(bm, RIM_R, RIM_Z, RIM_R, RIM_Z + 1.6, 0)
ring(bm, RIM_R, RIM_Z + 1.6, FACADE_R, RIM_Z + 1.6, 1)
new_obj('Rim', bm, '04_Rim', [concrete, steel_dark])

# the floodlight ring: posts from the rim, a box truss, the lamps on its inside
bm = bmesh.new()
for x, y, a in ring_points(HALO_R1 - 1.0, 11.0):
    box(bm, (x, y), (math.cos(a), math.sin(a)), 0.35, (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.35, RIM_Z + 1.6, HALO_Z0, 0)
ring(bm, HALO_R0, HALO_Z0, HALO_R1, HALO_Z0, 0, want='down')
ring(bm, HALO_R0, HALO_Z1, HALO_R1, HALO_Z1, 0, want='up')
ring(bm, HALO_R0, HALO_Z0, HALO_R0, HALO_Z1, 1)
ring(bm, HALO_R1, HALO_Z0, HALO_R1, HALO_Z1, 0, want='out')
new_obj('Halo', bm, '04_Rim', [steel, steel_dark])
bm = bmesh.new()
for x, y, a in ring_points(HALO_R0 - 0.05, 3.0):
    tx, ty = math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)
    for k in (-0.55, 0.55):
        cx, cy = x + tx * k, y + ty * k
        face(bm, [(cx - tx * 0.4, cy - ty * 0.4, HALO_Z0 + 0.25), (cx + tx * 0.4, cy + ty * 0.4, HALO_Z0 + 0.25),
                  (cx + tx * 0.4, cy + ty * 0.4, HALO_Z1 - 0.25), (cx - tx * 0.4, cy - ty * 0.4, HALO_Z1 - 0.25)],
             Vector((-math.cos(a), -math.sin(a), 0)), 0)
HALO_LAMPS = new_obj('Halo_Lamps', bm, '04_Rim', [lamp])

# WORLD CUP 26 over the far (south) stand, on the truss (THE FINAL only shows on the screens, in the final)
bm = bmesh.new()
fy = -(CY + HALO_R0) + 0.3
face(bm, [(-14, fy, HALO_Z0 - 4.0), (14, fy, HALO_Z0 - 4.0), (14, fy, HALO_Z1), (-14, fy, HALO_Z1)], Vector((0, 1, 0)), 0)
new_obj('Final_Sign', bm, '04_Rim', [navy])
wall_text('Final_Sign_T', 'WORLD CUP 26', (0, fy + 0.05, HALO_Z0 - 3.1), -math.pi / 2, 3.0, '04_Rim', led_gold)

# the four corner screens, above the middle ring. Their faces show the match
# live (game.screen.js, World Cup style): exported together as 'StadiumScreens'
# They hang low, on the band over the club suites, near the ends of the long
# sides: the game camera sees the far side only up to about 27 m (lookZ -17),
# and only so far sideways, so higher up in the very corners they'd be out of frame.
SCREEN_W, SCREEN_H, SCREEN_Z = 18.0, 6.5, CLUB_Z1 + 1.1
SCREEN_R, SCREEN_A = MID['r'] - 0.55, math.radians(62)
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.05, 0.08, 0.30), 2.0)
SCREEN_FACES = []
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
    d = Vector((sx * math.cos(SCREEN_A), sy * math.sin(SCREEN_A), 0))
    tn = Vector((-d.y, d.x, 0)) * (1 if sx * sy > 0 else 1)
    c = Vector((sx * CX, sy * CY, 0)) + d * SCREEN_R
    bm = bmesh.new()
    box(bm, (c.x + d.x * 0.25, c.y + d.y * 0.25), (tn.x, tn.y), SCREEN_W / 2 + 0.3, (d.x, d.y), 0.2, SCREEN_Z - 0.3, SCREEN_Z + SCREEN_H + 0.3, 0)
    new_obj('Screen_%d%d' % (sx, sy), bm, '04_Rim', [steel_dark])
    fb = bmesh.new()
    face(fb, [c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)), c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)),
              c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H)), c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H))],
         -d, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])                  # u left to right as seen from the pitch
    SCREEN_FACES.append(new_obj('ScreenFace_%d%d' % (sx, sy), fb, '04_Rim', [live]))

# ================================================================ outside
# As on photo 2.png, from the ground up: a lit glass ground floor set back under
# the facade, the silver louvres, the open concourse (two lit decks behind white
# steel columns), the light fascia on top. METLIFE STADIUM once, on the fascia
# over the main entrance in the middle of the front (the +y long side).
R_IN = FACADE_R - 3.5                                  # the back of the concourse
bm = bmesh.new()
ring(bm, FACADE_R - 1.2, 0.0, FACADE_R - 1.2, LOUVRE_Z0, 1, want='out', u_len=PANE_W * PANES)                # ground floor glass
ring(bm, FACADE_R - 1.2, LOUVRE_Z0, FACADE_R, LOUVRE_Z0, 2, want='down')                                    # its soffit
ring(bm, FACADE_R, LOUVRE_Z0, FACADE_R, LOUVRE_Z1, 0, want='out', u_len=LOUVRE_U)                           # the louvres
ring(bm, R_IN, 32.0, FACADE_R, 32.0, 2, want='up')                                                          # concourse floor
ring(bm, FACADE_R, LOUVRE_Z1, FACADE_R - 0.3, LOUVRE_Z1, 2, want='up')
ring(bm, R_IN, 32.0, R_IN, 38.3, 1, want='out', u_len=PANE_W * PANES)                                       # lower deck, lit
ring(bm, R_IN, 38.3, FACADE_R - 0.2, 38.3, 2, want='down')
ring(bm, FACADE_R - 0.2, 38.3, FACADE_R - 0.2, 39.1, 2, want='out')                                          # slab edge
ring(bm, R_IN, 39.1, FACADE_R - 0.2, 39.1, 2, want='up')
ring(bm, R_IN, 39.1, R_IN, 45.0, 1, want='out', u_len=PANE_W * PANES * 1.3)                                  # upper deck, lit
ring(bm, R_IN, 45.0, FACADE_R, 45.0, 2, want='down')                                                         # under the fascia
ring(bm, FACADE_R, 45.0, FACADE_R, RIM_Z + 1.6, 3, want='out')                                               # the fascia
new_obj('Facade', bm, '05_Outside', [louvres, glass_lit, concrete_light, fascia])
bm = bmesh.new()
for x, y, a in ring_points(FACADE_R - 0.45, 9.0):                                                            # the steel columns
    box(bm, (x, y), (math.cos(a), math.sin(a)), 0.3, (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.3, 32.0, 45.0, 0)
for x, y, a in ring_points(FACADE_R - 0.7, 9.0):                                                             # and under the glass floor
    box(bm, (x, y), (math.cos(a), math.sin(a)), 0.35, (math.cos(a + math.pi / 2), math.sin(a + math.pi / 2)), 0.35, 0.0, LOUVRE_Z0, 0)
new_obj('Facade_Columns', bm, '05_Outside', [steel_white])

# the main entrance: a tall lit opening in the louvres with a canopy over it
FRONT_Y = CY + FACADE_R
bm = bmesh.new()
face(bm, [(-16, FRONT_Y + 0.08, 0), (16, FRONT_Y + 0.08, 0), (16, FRONT_Y + 0.08, 12.0), (-16, FRONT_Y + 0.08, 12.0)], Vector((0, 1, 0)), 1,
     [(0, 0), (1.0, 0), (1.0, 1), (0, 1)])
box(bm, (0, FRONT_Y + 2.0), (1, 0), 18.0, (0, 1), 2.0, 12.0, 13.0, 0)
for gx in (-16.6, 16.6):
    box(bm, (gx, FRONT_Y + 0.5), (1, 0), 0.6, (0, 1), 0.5, 0.0, 12.0, 0)
new_obj('Entrance', bm, '05_Outside', [steel_white, glass_lit])
wall_text('Facade_Name', 'METLIFE STADIUM', (0, FRONT_Y + 0.12, 45.6), 3 * math.pi / 2, 6.6, '05_Outside', letters_white)

bm = bmesh.new()
ring(bm, FACADE_R - 4, -0.05, FACADE_R + 14, -0.05, 2, want='up', step=4)      # the paved plaza round it
ring(bm, FACADE_R + 14, -0.05, FACADE_R + 46, -0.05, 0, want='up', step=4)     # car parks
ring(bm, FACADE_R + 46, -0.05, FACADE_R + 70, -0.05, 1, want='up', step=6)
new_obj('Ground', bm, '05_Outside', [asphalt, lawn, principled('M_Plaza', (0.30, 0.30, 0.31), 0.9)])

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
pimg = D.images.new('metlife_pitch', PW_PX, PH_PX)
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


# the World Cup pitch: long mowing bands across it (no checkerboard), a darker
# artificial run-off
bands_x = np.tanh(np.sin(np.pi * X / 5.5) * 6)
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = (1 + 0.11 * bands_x + 0.055 * vnoise(420, 420) + 0.035 * vnoise(48, 48)
         + 0.05 * vnoise(16, 1) * (0.6 + 0.4 * bands_x) + 0.04 * fine)
grass_px = np.array((0.070, 0.175, 0.042), 'f') * shade[..., None]
grass_px[..., 0] *= 1 + 0.10 * vnoise(300, 300)
wear = sum(np.exp(-(((X - gx) / 3.2) ** 2 + (Y / 5.5) ** 2)) for gx in (-(hx - 2.8), hx - 2.8)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
wear = (0.2 * wear * (0.55 + 0.45 * np.clip(vnoise(36, 36) + 0.5, 0, 1)))[..., None]
grass_px = grass_px * (1 - wear) + np.array((0.150, 0.190, 0.070), 'f') * wear
runoff_px = np.array((0.045, 0.11, 0.035), 'f') * (1 + 0.05 * vnoise(64, 64) + 0.03 * fine)[..., None]
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


NIGHT = dict(flood=26000, stand=9000, facade=60000)
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)
coll = D.collections.new('10_NightLights'); sc.collection.children.link(coll)
FLOOD = (1.0, 0.98, 0.94)
for x, y, a in ring_points(HALO_R0, 9.0):
    light(coll, 'SPOT', (x, y, HALO_Z0 - 0.3), NIGHT['flood'], FLOOD, target=(x * 0.18, y * 0.18, 0), size=62)
for x, y, a in ring_points(HALO_R0, 14.0):
    light(coll, 'SPOT', (x, y, HALO_Z0 - 0.3), NIGHT['stand'], FLOOD, target=(-x * 0.55, -y * 0.55, 18), size=70, blend=0.6)
for x, y, a in ring_points(FACADE_R + 14, 16.0):          # floodlit silver facade, as at night on the photos
    light(coll, 'SPOT', (x, y, 0.5), NIGHT['facade'], (0.86, 0.90, 1.0), target=(x - 14 * math.cos(a), y - 14 * math.sin(a), 26), size=75, blend=0.6)
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
pimg.save_render(TEX_DIR + '/metlife_pitch.jpg')
pjpg = D.images.load(TEX_DIR + '/metlife_pitch.jpg')
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
target.name = 'MetLife'
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
SELF_LIT = {'M_Pitch', 'M_LED', 'M_LEDGold', 'M_Lettering', 'M_FloodLight', 'M_GlassLit', 'M_Navy'}
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
