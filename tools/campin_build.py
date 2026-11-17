# Builds El Campín (Estadio Nemesio Camacho, Bogotá) from nothing and exports
# it for the game, the way MetLife and De Kuip are built.
#   blender -b --factory-startup --python tools/campin_build.py -- <out.blend> <out.glb> <texture dir>
#
# As on the photos: an oval bowl of one big tier round a pitch with the grey
# track behind it, yellow seats with red and blue, IDRD BOGOTA in red seats on
# the east stand (the far side in the game), a white roof ring round the top.
# The west stand has a second tier and its own flat roof; outside it the beige
# tower with the black EL CAMPIN sign. Round the bowl the raked concrete
# underside, a steel truss gallery with white rooms, the concrete base with the
# stadium's name, silver fence panels with posters, a terracotta square. Four
# floodlight towers, a big screen over the north end (live, game.screen.js).
# No club, league or city logos: only lettering and plain shields.
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

# the pitch the game plays on (88 x 56), and the bowl as a rounded rectangle
# round a 71.4 x 27.4 core with a big corner radius: an oval. The front wall at
# r = 24 stays out of the block the game cuts away towards the camera
# (|x| < 51.2, y > -32.4), and leaves the track's wide D behind each goal.
PW, PL = 88.0, 56.0
K = PW / 105.0
LINE = 0.14
FLOOR_X, FLOOR_Y = 61.0, 39.0
CX, CY = 35.7, 13.7
SEG = 12
N_RING = 4 * (SEG + 1)
NE, NW, SW, SE = (set(range(k * (SEG + 1), k * (SEG + 1) + SEG)) for k in range(4))
N_SIDE, W_SIDE, S_SIDE, E_SIDE = (k * (SEG + 1) + SEG for k in range(4))
GAIN = 2.0
SEAT_W = 0.5

WALL_R, WALL_Z = 24.0, 2.6
TRACK_R0 = 17.0                                                    # the track: from here to the wall
BOWL = dict(r=24.3, z=2.1, rows=34, depth=0.8, rise=0.42)          # the one big tier: to r 51.5, z 16
BACK_R = BOWL['r'] + BOWL['depth'] * BOWL['rows']
TOP_Z = BOWL['z'] + BOWL['rise'] * (BOWL['rows'] - 1)
CAN_R0, CAN_R1, CAN_Z0, CAN_Z1 = 43.0, 56.0, 21.0, 20.0           # the roof ring: front edge high, back low
# the west stand (the near side): boxes, a second tier, a flat roof
MAIN = dict(r=52.0, z=18.6, rows=12, depth=0.85, rise=0.6)
MAIN_BACK = MAIN['r'] + MAIN['depth'] * MAIN['rows']
MAIN_TOP = MAIN['z'] + MAIN['rise'] * (MAIN['rows'] - 1)
MROOF_R0, MROOF_R1, MROOF_Z = 33.0, 65.0, 29.0
MAST_R, MAST_H = 64.0, 46.0
FENCE_R = 70.0


def soffit_z(r):
    # the underside of the big tier, a straight rake from the front wall to its back
    return 1.6 + (r - WALL_R) / (BACK_R - WALL_R) * (TOP_Z - 2.0)


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




NAME_FONT = D.fonts.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'Montserrat-ExtraBold.ttf'))


def ring_len(r):
    p = ring_path(r)
    return sum(math.dist(p[i][:2], p[(i + 1) % len(p)][:2]) for i in range(len(p)))


def text_out(name, body, loc, n, size, coll, mat, font=None, extrude=0.0):
    # lettering on an outside wall, facing along n
    return wall_text(name, body, loc, math.atan2(-n.y, -n.x), size, coll, mat, font=font, extrude=extrude)


# ---------------------------------------------------------------- materials and textures
rng = np.random.default_rng(1938)


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
        if rng.random() < 0.75:
            warm = np.array((1.0, 0.82, 0.60), 'f') * rng.uniform(0.35, 0.7)
            prof = 0.55 + 0.45 * np.clip((v - 0.55) / 0.3, 0, 1) ** 1.5
            prof = np.where(v > 0.86, 1.25, prof)
            prof = np.where(v < 0.32, 0.30, prof)
            pane = warm * prof[..., None] * np.ones((1, pw, 1), 'f')
        else:
            pane = np.array((0.03, 0.035, 0.05), 'f') * (1 + 0.6 * v)[..., None] * np.ones((1, pw, 1), 'f')
        pane[:, :2] = 0.02; pane[:, -2:] = 0.02; pane[:3] = 0.02; pane[-3:] = 0.02
        t[:, x0:x0 + pw] = pane
    return t


def ribs_tex():
    # the raked concrete underside: beams across it every 1.6 m
    w = 64
    y = np.arange(w) / w
    rib = 0.62 + 0.38 * np.clip(np.sin(y * 2 * np.pi) * 2.5, -1, 1) ** 2
    return np.ones((w, w, 3), 'f') * np.array((0.50, 0.50, 0.48), 'f') * rib[:, None, None]


def paving_tex():
    # the terracotta square: clay pavers in a herring of rows, 2 x 2 m
    w = 256
    yy, xx = np.mgrid[0:w, 0:w].astype('f') / w * 2.0
    row = np.floor(yy / 0.1)
    xs = xx + (row % 2) * 0.1
    col = np.floor(xs / 0.2)
    fy, fx = (yy / 0.1) % 1, (xs / 0.2) % 1
    gap = np.minimum(np.minimum(fy, 1 - fy) / 0.1, np.minimum(fx, 1 - fx) / 0.05)
    tone = (np.sin(row * 12.9898 + col * 78.233) * 43758.5453) % 1
    t = (0.85 + 0.25 * tone)[..., None] * np.array((0.34, 0.15, 0.10), 'f')
    return t * np.clip(0.6 + 0.4 * np.clip(gap, 0, 1), 0, 1)[..., None]


def concrete_tex():
    # weathered beige concrete panels, 2.4 x 2.4 m
    w = 128
    t = np.ones((w, w, 3), 'f') * np.array((0.52, 0.51, 0.44), 'f')
    t *= (1 + 0.05 * rng.normal(0, 1, (w, w, 1))).astype('f')
    streak = (0.92 + 0.08 * np.sin(np.arange(w) / w * 2 * np.pi * 7 + rng.uniform(0, 6)))[None, :, None]
    t *= streak
    t[:2] *= 0.7; t[:, :2] *= 0.7
    return t


seat_cols = [image_material('M_Seat%d' % i, painted('campin_seat%d' % i, seat_tile(c)), 0.6)
             for i, c in enumerate(((0.80, 0.55, 0.04), (0.62, 0.05, 0.04), (0.06, 0.13, 0.42)))]   # yellow, red, blue
concrete = principled('M_Concrete', (0.46, 0.46, 0.45), 0.9)
concrete_dark = principled('M_ConcreteDark', (0.26, 0.26, 0.26), 0.9)
beige = image_material('M_Beige', painted('campin_concrete', concrete_tex()), 0.85)
ribs = image_material('M_Ribs', painted('campin_ribs', ribs_tex()), 0.9)
stair_yellow = principled('M_StairYellow', (0.75, 0.52, 0.04), 0.7)
track = principled('M_Track', (0.11, 0.11, 0.12), 0.95)
roof_white = principled('M_RoofWhite', (0.80, 0.81, 0.82), 0.5)
roof_under = principled('M_RoofUnder', (0.30, 0.31, 0.32), 0.8)
steel = principled('M_Steel', (0.40, 0.41, 0.43), 0.5, metallic=0.3)
steel_dark = principled('M_SteelDark', (0.07, 0.07, 0.08), 0.6)
white_room = principled('M_WhiteRoom', (0.78, 0.78, 0.76), 0.7)
glass_lit = image_material('M_GlassLit', painted('campin_windows', windows_tex()), 0.2)
glass_dark = principled('M_GlassDark', (0.04, 0.05, 0.07), 0.15)
sign_black = principled('M_SignBlack', (0.025, 0.025, 0.03), 0.4)
letters_white = principled('M_Lettering', (0.92, 0.92, 0.94), 0.4, (0.92, 0.92, 0.94), 2.0)
letters_metal = principled('M_LetterMetal', (0.72, 0.72, 0.74), 0.4)
paint_white = principled('M_PaintWhite', (0.80, 0.80, 0.80), 0.8)
lamp = principled('M_FloodLight', (1.0, 1.0, 0.96), 0.3, (1.0, 1.0, 0.95), 3.0)
paving = image_material('M_Paving', painted('campin_paving', paving_tex()), 0.95)
lawn = principled('M_Lawn', (0.05, 0.13, 0.05), 0.95)
asphalt = principled('M_Asphalt', (0.06, 0.06, 0.065), 0.95)
fence_metal = principled('M_FenceMetal', (0.62, 0.63, 0.65), 0.4, metallic=0.4)
posters = [principled('M_Poster%d' % i, c, 0.7) for i, c in enumerate(((0.55, 0.70, 0.75), (0.85, 0.42, 0.12), (0.80, 0.80, 0.78), (0.20, 0.30, 0.55)))]

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
net_img = D.images.new('campin_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/campin_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
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
AISLE_EVERY, AISLE_W = 12.0, 1.0                      # every 12 m: two letters fit between two stairs
UP_V = Vector((0, 0, 1))
V3 = lambda p, z: Vector((p[0], p[1], z))

# IDRD BOGOTA in red seats on the east stand, as on the photos: a 5 x 7 letter
# grid, each square two seats wide and two rows high
GLYPHS = {
    'I': ('.###.', '..#..', '..#..', '..#..', '..#..', '..#..', '.###.'),
    'D': ('####.', '#...#', '#...#', '#...#', '#...#', '#...#', '####.'),
    'R': ('####.', '#...#', '#...#', '####.', '#.#..', '#..#.', '#...#'),
    'B': ('####.', '#...#', '#...#', '####.', '#...#', '#...#', '####.'),
    'O': ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    'G': ('.###.', '#...#', '#....', '#.###', '#...#', '#...#', '.###.'),
    'T': ('#####', '..#..', '..#..', '..#..', '..#..', '..#..', '..#..'),
    'A': ('.###.', '#...#', '#...#', '#####', '#...#', '#...#', '#...#'),
    ' ': ('.....',) * 7,
}
WORD = 'IDRD BOGOTA'
WORD_PX = len(WORD) * 6 - 1
LETTER_ROW0 = 12                                     # the bottom row of the letters


def letter_on(x, row):
    # seen from the pitch the east stand runs from +x (left) to -x (right); the
    # stairs (x = 0, +-12, ...) fall in the gaps between the letters
    px = math.floor(35.5 - x)                        # one square = 1 m = two seats
    pr = (LETTER_ROW0 + 13 - row) // 2
    if not (0 <= px < WORD_PX and 0 <= pr < 7):
        return False
    ch, cx = WORD[px // 6], px % 6
    return cx < 5 and GLYPHS[ch][pr][cx] == '#'


def seat_colour(tier, seg, row, x):
    # 0 yellow, 1 red, 2 blue
    if tier == 'main':
        return 0 if row < 9 else 2
    if seg == S_SIDE:                                # east: red front rows, IDRD BOGOTA, blue at the top
        if row < 6:
            return 1
        if row >= 30:
            return 2
        return 1 if letter_on(x, row) else 0
    if seg == N_SIDE:                                # west, lower tier
        return 1 if row < 5 else (2 if row >= 31 else 0)
    if row < 10 or row >= 30:                        # the ends and corners: blue low and at the top
        return 2
    return 1 if 10 <= row < 13 else 0


def seat_row(bm, aisles, a, b, row, tier, seg, rise):
    length = (a[1] - a[0]).length
    spans = [(0.0, length)]
    back = (b[0] - a[0]).normalized()
    if length > 16:
        cuts = [c for c in (length / 2 + j * AISLE_EVERY for j in range(-10, 11)) if AISLE_W < c < length - AISLE_W]
        edges = [0.0] + [c + d for c in cuts for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
        lift = Vector((0, 0, 0.012))
        for c in cuts:                               # the stairs, painted yellow at their edges as in the stadium
            for e0, e1 in ((c - AISLE_W / 2, c - AISLE_W / 2 + 0.12), (c + AISLE_W / 2 - 0.12, c + AISLE_W / 2)):
                u0, u1 = e0 / length, e1 / length
                f0, f1 = a[0].lerp(a[1], u0), a[0].lerp(a[1], u1)
                face(aisles, [f0 + lift, f1 + lift, b[0].lerp(b[1], u1) + lift, b[0].lerp(b[1], u0) + lift], UP_V, 0)
    for s0, s1 in spans:
        seats = max(1, round((s1 - s0) / SEAT_W))
        for k in range(0, seats, 2):
            k1 = min(k + 2, seats)
            u = [(s0 + (s1 - s0) * q / seats) / length for q in (k, k1)]
            pa = [a[0].lerp(a[1], t) for t in u]; pb = [b[0].lerp(b[1], t) for t in u]
            mid = (pa[0] + pa[1]) / 2
            mat = seat_colour(tier, seg, row, mid.x)

            def at(t, h, i):
                return pa[i].lerp(pb[i], t) + Vector((0, 0, h))
            face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UP_V, mat, [(k, 0.0), (k1, 0.0), (k1, 0.45), (k, 0.45)])
            face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, mat, [(k, 0.45), (k1, 0.45), (k1, 0.95), (k, 0.95)])
            face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UP_V, mat, [(k, 0.95), (k1, 0.95), (k1, 1.0), (k, 1.0)])


def build_tier(name, t, base_z, tier, only=None):
    steps, seats, aisles = bmesh.new(), bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, z = t['r'] + t['depth'] * k, t['z'] + t['rise'] * k
        z_prev = base_z if k == 0 else z - t['rise']
        ring(steps, r0, z_prev, r0, z, 1, only=only)
        ring(steps, r0, z, r0 + t['depth'], z, 0, only=only)
        p0, p1 = ring_path(r0), ring_path(r0 + t['depth'])
        for i in range(N_RING):
            if only is not None and i not in only:
                continue
            j = (i + 1) % N_RING
            seat_row(seats, aisles, [V3(p0[i], z), V3(p0[j], z)], [V3(p1[i], z), V3(p1[j], z)], k, tier, i, k > 0)
    new_obj('Bowl_' + name, steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', seat_cols)
    new_obj('Stairs_' + name, aisles, '02_Bowl', [stair_yellow])


random.seed(1938)
build_tier('Bowl', BOWL, 0.0, 'bowl')
build_tier('Main', MAIN, TOP_Z + 0.6, 'main', only={N_SIDE})

# the wall round the track, the track, IDRD painted on the grass in the corners
bm = bmesh.new()
ring(bm, WALL_R, 0.0, WALL_R, WALL_Z, 0)
ring(bm, WALL_R, WALL_Z, BOWL['r'], WALL_Z, 0, want='up')
ring(bm, BOWL['r'], WALL_Z, BOWL['r'], BOWL['z'], 0, want='out')
new_obj('Pitch_Wall', bm, '02_Bowl', [concrete_dark])
bm = bmesh.new()
for k in range(4):
    r0 = TRACK_R0 + (WALL_R - TRACK_R0) * k / 4
    ring(bm, r0, 0.015, TRACK_R0 + (WALL_R - TRACK_R0) * (k + 1) / 4, 0.015, 0, want='up')
new_obj('Track', bm, '02_Bowl', [track])
for i, (x, y, rot) in enumerate(((-38.0, -29.4, math.pi), (38.0, -29.4, math.pi), (-38.0, 29.4, math.pi), (38.0, 29.4, math.pi))):
    cu = D.curves.new('Grass_IDRD_%d' % i, 'FONT')
    cu.body = 'IDRD' if i % 2 == 0 else 'BOGOTÁ'
    cu.size = 1.2; cu.align_x = 'CENTER'; cu.font = LETTER_FONT; cu.resolution_u = 3
    cu.materials.append(paint_white)
    o = D.objects.new('Grass_IDRD_%d' % i, cu)
    o.location = (x, y, 0.03); o.rotation_euler = (0, 0, rot)
    D.collections['01_Pitch'].objects.link(o)

# the back of the bowl up to the roof ring; on the west the boxes, the upper
# tier's back wall and the flat roof
WEST = {N_SIDE}
bm = bmesh.new()
ring(bm, BACK_R, TOP_Z, BACK_R, CAN_Z1 - 0.3, 0, skip=WEST)
ring(bm, BACK_R, TOP_Z, BACK_R, TOP_Z + 0.6, 0, only=WEST)
ring(bm, BACK_R, TOP_Z + 0.6, MAIN['r'], TOP_Z + 0.6, 0, only=WEST, want='up')
ring(bm, MAIN_BACK, MAIN_TOP, MAIN_BACK, MROOF_Z - 0.4, 0, only=WEST)
new_obj('Bowl_Back', bm, '02_Bowl', [concrete_dark])

# the roof ring round the top: white on top, its front edge lit by floodlights
bm = bmesh.new()
ring(bm, CAN_R0, CAN_Z0, CAN_R1, CAN_Z1, 0, skip=WEST, want='up')
ring(bm, CAN_R0, CAN_Z0 - 0.7, CAN_R1, CAN_Z1 - 0.5, 1, skip=WEST, want='down')
ring(bm, CAN_R0, CAN_Z0 - 0.7, CAN_R0, CAN_Z0, 0, skip=WEST)
ring(bm, CAN_R1, CAN_Z1 - 0.5, CAN_R1, CAN_Z1, 0, skip=WEST, want='out')
# the west roof, flat and wide over both tiers
ring(bm, MROOF_R0, MROOF_Z, MROOF_R1, MROOF_Z, 0, only=WEST, want='up')
ring(bm, MROOF_R0, MROOF_Z - 0.9, MROOF_R1, MROOF_Z - 0.9, 1, only=WEST, want='down')
ring(bm, MROOF_R0, MROOF_Z - 0.9, MROOF_R0, MROOF_Z, 0, only=WEST)
ring(bm, MROOF_R1, MROOF_Z - 0.9, MROOF_R1, MROOF_Z, 0, only=WEST, want='out')
new_obj('Roof', bm, '04_Roof', [roof_white, roof_under])
bm = bmesh.new()                                      # the ends of the west roof
for sx in (1, -1):
    x = sx * CX
    for zz, nz in ((MROOF_Z, 1),):
        face(bm, [(x, CY + MROOF_R0, MROOF_Z - 0.9), (x, CY + MROOF_R1, MROOF_Z - 0.9), (x, CY + MROOF_R1, MROOF_Z), (x, CY + MROOF_R0, MROOF_Z)], Vector((sx, 0, 0)), 0)
    for r in (BACK_R + 0.2, MAIN_BACK + 0.6):         # posts carrying it
        box(bm, (x, CY + r), (1, 0), 0.3, (0, 1), 0.3, TOP_Z, MROOF_Z - 0.9, 1)
new_obj('Roof_West_Ends', bm, '04_Roof', [roof_white, concrete])
bm = bmesh.new()                                      # the glass boxes under the west upper tier
ring(bm, BACK_R + 0.1, TOP_Z + 0.6, BACK_R + 0.1, MAIN['z'] - 0.2, 0, only=WEST, u_len=PANE_W * PANES)
new_obj('Boxes_West', bm, '02_Bowl', [glass_lit])
bm = bmesh.new()
LAMPS = ring_points(CAN_R0 + 0.3, 3.0)
for x, y, a in LAMPS:
    if y > CY + 30 and abs(x) < CX:
        continue
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    c = Vector((x, y, CAN_Z0 - 1.1))
    face(bm, [c - t * 0.6 - Vector((0, 0, 0.25)), c + t * 0.6 - Vector((0, 0, 0.25)), c + t * 0.6 + Vector((0, 0, 0.25)), c - t * 0.6 + Vector((0, 0, 0.25))], -n, 0)
for x in np.arange(-CX + 2, CX - 1, 3.0):            # and under the west roof
    c = Vector((x, CY + MROOF_R0 + 0.4, MROOF_Z - 1.4))
    face(bm, [c + Vector((-0.6, 0, -0.25)), c + Vector((0.6, 0, -0.25)), c + Vector((0.6, 0, 0.25)), c + Vector((-0.6, 0, 0.25))], Vector((0, -1, 0)), 0)
new_obj('Roof_Lamps', bm, '04_Roof', [lamp])

# the big screen over the north end: live (game.screen.js, style 'campin'),
# exported on its own as 'StadiumScreens'
SCREEN_W, SCREEN_H, SCREEN_Z = 18.0, 9.0, CAN_Z1 + 1.6
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.05, 0.25, 0.55), 2.0)
d = Vector((1, 0, 0)); tn = Vector((0, 1, 0))
c = Vector((CX + BACK_R - 1.0, 0, 0))
bm = bmesh.new()
box(bm, (c.x + 0.66, c.y), (0, 1), SCREEN_W / 2 + 0.6, (1, 0), 0.6, SCREEN_Z - 0.6, SCREEN_Z + SCREEN_H + 0.6, 0)   # just behind the screen
box(bm, (c.x + 0.6, c.y), (0, 1), SCREEN_W / 2 + 0.7, (1, 0), 0.7, SCREEN_Z + SCREEN_H + 0.6, SCREEN_Z + SCREEN_H + 1.1, 1)
for s in (-1, 1):                                    # legs down to the back wall
    box(bm, (c.x + 0.6, s * (SCREEN_W / 2 - 1.5)), (0, 1), 0.35, (1, 0), 0.35, TOP_Z, SCREEN_Z - 0.6, 1)
new_obj('Screen_Frame', bm, '02_Bowl', [steel_dark, steel])
fb = bmesh.new()
face(fb, [c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)), c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z)),
          c - tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H)), c + tn * (SCREEN_W / 2) + Vector((0, 0, SCREEN_Z + SCREEN_H))],
     -d, 0, [(0, 0), (1, 0), (1, 1), (0, 1)])
SCREEN_FACES = [new_obj('ScreenFace_0', fb, '02_Bowl', [live])]

# ================================================================ outside
# The raked concrete underside of the tier, on columns and struts; a steel
# truss gallery round it with white rooms behind; the concrete base with the
# stadium's name; on the west the upper tier's underside and the beige tower
# with the EL CAMPIN sign; silver fence panels with posters; the square.
bm = bmesh.new()
for k in range(6):
    r0, r1 = WALL_R + 1 + (BACK_R - WALL_R - 1) * k / 6, WALL_R + 1 + (BACK_R - WALL_R - 1) * (k + 1) / 6
    ring(bm, r0, soffit_z(r0), r1, soffit_z(r1), 0, want='down', u_len=6.0, v_range=(k * (r1 - r0) / 1.6, (k + 1) * (r1 - r0) / 1.6))
for k in range(4):                                    # the west upper tier's underside
    r0, r1 = BACK_R + (MAIN_BACK - BACK_R) * k / 4, BACK_R + (MAIN_BACK - BACK_R) * (k + 1) / 4
    z0, z1 = [TOP_Z + 0.4 + (r - BACK_R) / (MAIN_BACK - BACK_R) * (MAIN_TOP - TOP_Z - 1.4) for r in (r0, r1)]
    ring(bm, r0, z0, r1, z1, 0, only=WEST, want='down', u_len=6.0, v_range=(k * (r1 - r0) / 1.6, (k + 1) * (r1 - r0) / 1.6))
new_obj('Underside', bm, '05_Outside', [ribs])

bm = bmesh.new()
COLS = ring_points(BACK_R - 1.6, 8.0)
for x, y, a in COLS:                                  # columns under the back of the tier, struts out to it
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    base = Vector((x, y, 0))
    box(bm, (x, y), (n.x, n.y), 0.35, (t.x, t.y), 0.35, 0.0, soffit_z(BACK_R - 1.6), 0)
    q = base - n * 9.0
    box(bm, (q.x, q.y), (n.x, n.y), 0.3, (t.x, t.y), 0.3, 0.0, soffit_z(BACK_R - 10.6), 0)
    tube(bm, base - n * 5.0 + Vector((0, 0, 0.0)), base + n * 1.0 + Vector((0, 0, soffit_z(BACK_R - 0.6) - 0.2)), 0.22, 0, seg=4)
for x, y, a in ring_points(MAIN_BACK - 1.0, 8.0):     # and under the west upper tier
    if y > CY + BACK_R and abs(x) < CX:
        box(bm, (x, y), (math.cos(a), math.sin(a)), 0.4, (-math.sin(a), math.cos(a)), 0.4, 0.0, MAIN_TOP - 1.4, 0)
new_obj('Columns', bm, '05_Outside', [concrete])

# the gallery: a slab with a steel truss for a railing, white rooms behind it
GAL_Z, GAL_R0, GAL_R1 = 7.4, 43.0, 49.5
bm, tr, wr = bmesh.new(), bmesh.new(), bmesh.new()
for rr0, rr1, zz, only_, skip_ in ((GAL_R0, GAL_R1, GAL_Z, None, WEST), (GAL_R0 + 9.0, GAL_R1 + 9.0, GAL_Z + 2.0, WEST, ())):
    ring(bm, rr0, zz, rr1, zz, 0, want='up', only=only_, skip=skip_)
    ring(bm, rr0, zz - 0.35, rr1, zz - 0.35, 0, want='down', only=only_, skip=skip_)
    ring(bm, rr1, zz - 0.35, rr1, zz, 0, want='out', only=only_, skip=skip_)
    for x, y, a in ring_points(rr1 - 0.1, 2.4):
        west = y > CY + 30 and abs(x) < CX
        if (only_ is not None) != west:
            continue
        n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        p = Vector((x, y, zz))
        tube(tr, p - t * 1.2 + Vector((0, 0, 1.3)), p + t * 1.2 + Vector((0, 0, 1.3)), 0.06, 0, seg=4)    # top chord
        tube(tr, p - t * 1.2 + Vector((0, 0, 0.1)), p + t * 1.2 + Vector((0, 0, 0.1)), 0.06, 0, seg=4)    # bottom chord
        tube(tr, p - t * 1.2 + Vector((0, 0, 0.1)), p + Vector((0, 0, 1.3)), 0.045, 0, seg=4)            # the triangles
        tube(tr, p + Vector((0, 0, 1.3)), p + t * 1.2 + Vector((0, 0, 0.1)), 0.045, 0, seg=4)
    for x, y, a in ring_points(rr0 + 1.4, 7.0):        # the white rooms, one in three places
        west = y > CY + 30 and abs(x) < CX
        if (only_ is not None) != west or rng.random() < 0.4:
            continue
        n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        box(wr, (x, y), (t.x, t.y), 2.6, (n.x, n.y), 1.3, zz, zz + 2.8, 0)
        q = Vector((x, y, 0)) + n * 1.32
        face(wr, [q - t * 0.5 + Vector((0, 0, zz)), q + t * 0.5 + Vector((0, 0, zz)), q + t * 0.5 + Vector((0, 0, zz + 2.1)), q - t * 0.5 + Vector((0, 0, zz + 2.1))], n, 1)
new_obj('Gallery', bm, '05_Outside', [concrete])
new_obj('Gallery_Truss', tr, '05_Outside', [steel])
new_obj('Gallery_Rooms', wr, '05_Outside', [white_room, steel_dark])

# the concrete base, with the stadium's name on the west; dark gates in it
BASE_R = 49.0
bm = bmesh.new()
ring(bm, BASE_R, 0.0, BASE_R, 3.0, 0, want='out', skip=WEST, u_len=2.4, v_range=(0, 1.25))
ring(bm, BASE_R, 3.0, BASE_R - 1.0, 3.0, 0, want='up', skip=WEST)
ring(bm, BASE_R + 9.0, 0.0, BASE_R + 9.0, 3.0, 0, want='out', only=WEST, u_len=2.4, v_range=(0, 1.25))
ring(bm, BASE_R + 9.0, 3.0, BASE_R + 8.0, 3.0, 0, want='up', only=WEST)
for x, y, a in ring_points(BASE_R + 0.05, 26.0):     # roller doors
    if y > CY + 30 and abs(x) < CX:
        continue
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    q = Vector((x, y, 0))
    face(bm, [q - t * 1.6, q + t * 1.6, q + t * 1.6 + Vector((0, 0, 2.4)), q - t * 1.6 + Vector((0, 0, 2.4))], n, 1)
WFRONT = CY + BASE_R + 9.0
for xx in (-24.0, -16.0, 16.0, 24.0):
    face(bm, [(xx - 1.6, WFRONT + 0.05, 0), (xx + 1.6, WFRONT + 0.05, 0), (xx + 1.6, WFRONT + 0.05, 2.4), (xx - 1.6, WFRONT + 0.05, 2.4)], Vector((0, 1, 0)), 1)
new_obj('Base', bm, '05_Outside', [beige, steel])
text_out('Base_Name', 'ESTADIO NEMESIO CAMACHO EL CAMPÍN', Vector((10.5, WFRONT + 0.06, 1.2)), Vector((0, 1, 0)), 0.55, '05_Outside', letters_metal, font=NAME_FONT)

# the west tower: a beige core up past the roof, glazed boxes either side, the
# black EL CAMPIN sign and under it a shield with the city hall's name
TF = CY + MROOF_R1 + 1.0                              # the tower's front
bm, gb = bmesh.new(), bmesh.new()
box(bm, (0, TF - 4.0), (1, 0), 3.0, (0, 1), 4.0, 0.0, MROOF_Z + 3.0, 0)                     # the core
box(bm, (0, TF - 4.5), (1, 0), 5.0, (0, 1), 3.5, 3.0, 11.2, 0)                               # its foot
for s in (-1, 1):                                                                            # the boxes
    cx_ = s * 6.6
    box(bm, (cx_, TF - 3.2), (1, 0), 3.6, (0, 1), 2.6, 11.2, 12.4, 0)
    box(bm, (cx_, TF - 3.2), (1, 0), 3.6, (0, 1), 2.6, 16.8, 18.0, 0)
    u0 = rng.integers(0, PANES)
    face(gb, [(cx_ - 3.5, TF - 0.62, 12.4), (cx_ + 3.5, TF - 0.62, 12.4), (cx_ + 3.5, TF - 0.62, 16.8), (cx_ - 3.5, TF - 0.62, 16.8)], Vector((0, 1, 0)), 0,
         [(u0 / PANES, 0), ((u0 + 3.5) / PANES, 0), ((u0 + 3.5) / PANES, 1), (u0 / PANES, 1)])
    face(gb, [(cx_ + s * 3.58, TF - 5.7, 12.4), (cx_ + s * 3.58, TF - 0.7, 12.4), (cx_ + s * 3.58, TF - 0.7, 16.8), (cx_ + s * 3.58, TF - 5.7, 16.8)], Vector((s, 0, 0)), 1)
box(bm, (0, TF - 1.9), (1, 0), 4.2, (0, 1), 2.0, 18.0, 21.0, 0)                               # the head over the sign, just proud of the core
bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=8, use_grid_fill=True)    # the baked light lives in the corners: give it many
tower = new_obj('Tower', bm, '05_Outside', [beige])
new_obj('Tower_Glass', gb, '05_Outside', [glass_lit, glass_dark])
bm = bmesh.new()
box(bm, (0, TF + 0.2), (1, 0), 4.9, (0, 1), 0.2, 16.6, 18.6, 0)                              # the sign
box(bm, (0, TF + 0.2), (1, 0), 1.7, (0, 1), 0.2, 13.0, 16.6, 0)                              # the shield's panel
sh = [(-0.75, 16.2), (0.75, 16.2), (0.75, 15.0), (0.0, 14.3), (-0.75, 15.0)]                # a plain shield
face(bm, [(x, TF + 0.42, z) for x, z in sh], Vector((0, 1, 0)), 1)
new_obj('Tower_Sign', bm, '05_Outside', [sign_black, letters_metal])
text_out('Tower_Name', 'EL CAMPÍN', Vector((0, TF + 0.42, 17.05)), Vector((0, 1, 0)), 1.45, '05_Outside', letters_white, font=NAME_FONT, extrude=0.06)
text_out('Tower_City1', 'ALCALDÍA MAYOR', Vector((0, TF + 0.42, 13.85)), Vector((0, 1, 0)), 0.3, '05_Outside', letters_metal, font=NAME_FONT)
text_out('Tower_City2', 'DE BOGOTÁ D.C.', Vector((0, TF + 0.42, 13.4)), Vector((0, 1, 0)), 0.3, '05_Outside', letters_metal, font=NAME_FONT)

# silver fence panels round the square, posters on some, a truss along the top
bm = bmesh.new()
pts = ring_points(FENCE_R, 2.4)
for i, (x, y, a) in enumerate(pts):
    n, t = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
    q = Vector((x, y, 0))
    box(bm, (x - t.x * 1.2, y - t.y * 1.2), (t.x, t.y), 0.06, (n.x, n.y), 0.06, 0.0, 2.6, 0)
    m = 0 if (i // 4) % 3 == 0 else 1 + (i // 4) % 4
    face(bm, [q - t * 1.12 + Vector((0, 0, 0.25)), q + t * 1.12 + Vector((0, 0, 0.25)), q + t * 1.12 + Vector((0, 0, 2.3)), q - t * 1.12 + Vector((0, 0, 2.3))], n, m)
    face(bm, [q + t * 1.12 + Vector((0, 0, 0.25)), q - t * 1.12 + Vector((0, 0, 0.25)), q - t * 1.12 + Vector((0, 0, 2.3)), q + t * 1.12 + Vector((0, 0, 2.3))], -n, 0)
ring(bm, FENCE_R + 0.02, 2.3, FENCE_R + 0.02, 2.6, 0, want='out')
ring(bm, FENCE_R - 0.02, 2.3, FENCE_R - 0.02, 2.6, 0)
new_obj('Fence', bm, '05_Outside', [fence_metal] + posters)

# four floodlight towers: a lattice up to a platform and a big frame of lamps
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
    base = Vector((sx * CX, sy * CY, 0)) + Vector((sx, sy, 0)).normalized() * MAST_R
    bm = bmesh.new()

    def leg(k, z):
        hw = 1.6 - 0.6 * z / MAST_H
        ox, oy = ((1, 1), (-1, 1), (-1, -1), (1, -1))[k]
        return Vector((base.x + ox * hw, base.y + oy * hw, z))
    for k in range(4):
        tube(bm, leg(k, 0), leg(k, MAST_H), 0.16, 0, seg=4)
    for lv in range(12):
        z0, z1 = MAST_H * lv / 12, MAST_H * (lv + 1) / 12
        for k in range(4):
            k2 = (k + 1) % 4
            tube(bm, leg(k, z1), leg(k2, z1), 0.07, 0, seg=4)
            tube(bm, leg(k, z0) if lv % 2 else leg(k2, z0), leg(k2, z1) if lv % 2 else leg(k, z1), 0.06, 0, seg=4)
        if lv in (5, 9):                                                  # platforms
            box(bm, (base.x, base.y), (1, 0), 2.0, (0, 1), 2.0, z1 - 0.15, z1, 0)
    top = Vector((base.x, base.y, MAST_H + 3.0))
    f = (Vector((0, 0, 0)) - top).normalized()
    right = f.cross(Vector((0, 0, 1))).normalized()
    upv = right.cross(f).normalized()
    quad = lambda cx, cy, w, h, off: [top + right * (cx + w * a) + upv * (cy + h * b) + f * off for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    face(bm, quad(0, 0, 3.6, 3.0, -0.25), -f, 0)
    face(bm, quad(0, 0, 3.6, 3.0, 0.0), f, 1)
    for i in range(5):
        for j in range(4):
            face(bm, quad(-2.8 + 1.4 * i, -2.2 + 1.47 * j, 0.55, 0.55, 0.06), f, 2)
    tube(bm, Vector((base.x, base.y, MAST_H)), top - f * 0.3, 0.3, 0, seg=6)
    new_obj('Mast_%d%d' % (sx, sy), bm, '05_Outside', [steel, steel_dark, lamp])

# the terracotta square, roads and grass round it
bm = bmesh.new()
for r0, r1, m, uv in ((BASE_R - 1.0, FENCE_R + 18.0, 0, True), (FENCE_R + 18.0, FENCE_R + 30.0, 1, False), (FENCE_R + 30.0, FENCE_R + 40.0, 2, False)):
    n = math.ceil((r1 - r0) / 4)
    for k in range(n):
        a0, a1 = r0 + (r1 - r0) * k / n, r0 + (r1 - r0) * (k + 1) / n
        if uv:
            ring(bm, a0, -0.05, a1, -0.05, m, want='up', step=4, u_len=2.0, v_range=((a0 - r0) / 2.0, (a1 - r0) / 2.0))
        else:
            ring(bm, a0, -0.05, a1, -0.05, m, want='up', step=4)
new_obj('Ground', bm, '05_Outside', [paving, asphalt, lawn])


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
pimg = D.images.new('campin_pitch', PW_PX, PH_PX)
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


# El Campin's pitch: broad mowing stripes across it, as on the photos
bands_x = np.tanh(np.sin(np.pi * X / 5.5) * 6)
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = (1 + 0.11 * bands_x + 0.055 * vnoise(420, 420) + 0.035 * vnoise(48, 48)
         + 0.05 * vnoise(16, 1) * (0.6 + 0.4 * bands_x) + 0.04 * fine)
grass_px = np.array((0.070, 0.175, 0.042), 'f') * shade[..., None]
grass_px[..., 0] *= 1 + 0.10 * vnoise(300, 300)
wear = sum(np.exp(-(((X - gx) / 3.2) ** 2 + (Y / 5.5) ** 2)) for gx in (-(hx - 2.8), hx - 2.8)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
wear = (0.2 * wear * (0.55 + 0.45 * np.clip(vnoise(36, 36) + 0.5, 0, 1)))[..., None]
grass_px = grass_px * (1 - wear) + np.array((0.150, 0.190, 0.070), 'f') * wear
runoff_px = np.array((0.045, 0.105, 0.035), 'f') * (1 + 0.05 * vnoise(64, 64) + 0.03 * fine)[..., None]
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


NIGHT = dict(flood=6000, stand=3500, mast=40000, under=1200, facade=5000, tower=12000, moon=0.5)
w = D.worlds.new('World'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)
coll = D.collections.new('10_NightLights'); sc.collection.children.link(coll)
FLOOD = (1.0, 0.98, 0.94)
west_at = lambda x, y: y > CY + 30 and abs(x) < CX
for x, y, a in ring_points(CAN_R0 + 0.6, 4.5):                     # floodlights under the roof edges
    z = MROOF_Z - 1.8 if west_at(x, y) else CAN_Z0 - 1.5
    light(coll, 'SPOT', (x, y, z), NIGHT['flood'], FLOOD, target=(x * 0.2, y * 0.2, 0), size=70)
for x, y, a in ring_points(CAN_R0 + 0.6, 9.0):                     # and across onto the stands
    z = MROOF_Z - 1.8 if west_at(x, y) else CAN_Z0 - 1.5
    light(coll, 'SPOT', (x, y, z), NIGHT['stand'], FLOOD, target=(-x * 0.7, -y * 0.7, 8), size=80, blend=0.6)
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):                 # the four towers
    head = Vector((sx * CX, sy * CY, 0)) + Vector((sx, sy, 0)).normalized() * MAST_R + Vector((0, 0, MAST_H + 3.0))
    head += (Vector((0, 0, 0)) - head).normalized() * 1.0
    light(coll, 'SPOT', tuple(head), NIGHT['mast'], FLOOD, target=(0, 0, 0), size=45, blend=0.4)
for x, y, a in ring_points(GAL_R0 - 1.0, 9.0):                     # lights under the tier, over the gallery
    light(coll, 'POINT', (x, y, GAL_Z + (5.0 if west_at(x, y) else 3.0)), NIGHT['under'], (1.0, 0.92, 0.80))
for x, y, a in ring_points(FENCE_R - 4.0, 12.0):                   # the outside
    light(coll, 'SPOT', (x, y, 0.5), NIGHT['facade'], (0.90, 0.92, 1.0), target=(x - 12 * math.cos(a), y - 12 * math.sin(a), 9), size=70, blend=0.6)
for s in (-1, 1):                                                   # the tower and its sign
    light(coll, 'SPOT', (s * 7.0, TF + 12.0, 1.0), NIGHT['tower'], (1.0, 0.95, 0.88), target=(0, TF - 2, 15), size=50, blend=0.5)
for x in (-28.0, -14.0, 14.0, 28.0):                                # the west front
    light(coll, 'SPOT', (x, TF + 3.0, 0.5), NIGHT['facade'] * 1.6, (1.0, 0.95, 0.88), target=(x, CY + BACK_R + 4, 14), size=70, blend=0.6)
light(coll, 'SUN', (0, 0, 120), NIGHT['moon'], (0.80, 0.86, 1.0), target=(30, 20, 0))
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
pimg.save_render(TEX_DIR + '/campin_pitch.jpg')
pjpg = D.images.load(TEX_DIR + '/campin_pitch.jpg')
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
target.name = 'ElCampin'
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
SELF_LIT = {'M_Pitch', 'M_Lettering', 'M_FloodLight', 'M_GlassLit'}
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
