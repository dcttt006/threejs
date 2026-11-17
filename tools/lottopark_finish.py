# Finishes the Lotto Park model and exports it for the game.
#   blender -b lottopark.blend --python lottopark_finish.py -- <out.blend> <out.glb> <texture dir>
import bpy, bmesh, math, random, sys, time
import numpy as np
from mathutils import Vector, Matrix

OUT_BLEND, OUT_GLB, TEX_DIR = sys.argv[sys.argv.index('--') + 1:][:3]
D = bpy.data
sc = bpy.context.scene

# pitch size inside the bowl (the bowl floor is 110 x 73): leaves the run-off
# the game needs for its boards and goals, so no stand is cut away in a match
PW, PL = 88.0, 56.0
K = PW / 105.0                 # scale of the markings against a real 105 m pitch
LINE = 0.14
FLOOR_X, FLOOR_Y = 56.0, 37.5  # half size of the grass, just under the front wall

# the bowl is a rounded rectangle: an 86 x 49 core (CX, CY half sizes) and
# everything else at a distance r from it. Front wall r = 12, outer wall r = 45.5
CX, CY = 43.0, 24.5
SEG = 12                                   # segments per corner
N_RING = 4 * (SEG + 1)
NE, NW, SW, SE = (set(range(k * (SEG + 1), k * (SEG + 1) + SEG)) for k in range(4))   # corner segments
N_SIDE, W_SIDE, S_SIDE, E_SIDE = (k * (SEG + 1) + SEG for k in range(4))              # straight segments
# the office block: far left when you face the RSC ANDERLECHT end (west), and at
# the end of the dugout side (south), as on the photos
CORNER, CSX, CSY = SW, -1, -1

LOW = dict(r=12.0, z=1.3, rows=15, depth=0.8, rise=0.36)        # lower ring
LODGE_R, LODGE_Z0, LODGE_Z1 = 24.0, 6.34, 8.8                   # glass boxes behind it
UP = dict(r=23.6, z=9.8, rows=27, depth=0.8, rise=0.45)         # upper ring
SEAT_W = 0.5
ROOF_Z = 26.34                  # top of the roof
GAIN = 2.0                      # the game draws the model unlit at this gain (catalog: look.gain)


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
    # arr: (h, w, 3) linear colours, row 0 at the bottom
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


def remove(o):
    D.objects.remove(o, do_unlink=True)


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
    # a closed box around c, with half sizes hx_/hy_ along the horizontal axes ax/ay
    ax, ay = Vector((ax[0], ax[1], 0)), Vector((ay[0], ay[1], 0))
    if ax.x * ay.y - ax.y * ay.x < 0:      # keep the faces pointing outwards whichever way the box runs
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
    # the rounded rectangle at distance r from the core, as (x, y, outward angle)
    pts = []
    for sx, sy, a0 in ((1, 1, 0), (-1, 1, math.pi / 2), (-1, -1, math.pi), (1, -1, 1.5 * math.pi)):
        for i in range(SEG + 1):
            a = a0 + math.pi / 2 * i / SEG
            pts.append((sx * CX + r * math.cos(a), sy * CY + r * math.sin(a), a))
    return pts


def ring(bm, r0, z0, r1, z1, mat=0, skip=(), only=None, want=None, step=4.0, u_len=None):
    # a band of quads all the way round, from (r0, z0) to (r1, z1). Long
    # stretches are split, so light baked into the corners can vary along them.
    p0, p1 = ring_path(r0), ring_path(r1)
    cum = [0.0]                                             # distance along the ring, for window UVs
    for i in range(N_RING):
        cum.append(cum[-1] + math.dist(p0[i][:2], p0[(i + 1) % N_RING][:2]))
    for i in range(N_RING):
        if i in skip or (only is not None and i not in only):
            continue
        j = (i + 1) % N_RING
        A0, A1 = Vector((p0[i][0], p0[i][1], 0)), Vector((p0[j][0], p0[j][1], 0))
        B0, B1 = Vector((p1[i][0], p1[i][1], 0)), Vector((p1[j][0], p1[j][1], 0))
        t = (A1 - A0) if (A1 - A0).length > 1e-6 else (B1 - B0)
        out = Vector((t.y, -t.x, 0)).normalized()          # the path runs anticlockwise
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
                uvs = [(u0, 0), (u1, 0), (u1, 1), (u0, 1)]
            face(bm, [(a0.x, a0.y, z0), (a1.x, a1.y, z0), (b1.x, b1.y, z1), (b0.x, b0.y, z1)], w, mat, uvs)


def ring_points(r, step):
    # points about `step` apart along the ring at distance r: (x, y, outward angle)
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


def box_uv(o, tw, th):
    me = o.data
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = p.normal
        for li in p.loop_indices:
            co = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            if abs(n.z) > 0.7:
                uvl.data[li].uv = (co.x / tw, co.y / th)
            elif abs(n.y) > abs(n.x):
                uvl.data[li].uv = (co.x / tw, co.z / th)
            else:
                uvl.data[li].uv = (co.y / tw, co.z / th)


# ================================================================ textures
rng = np.random.default_rng(1908)


def seat_tile(color):
    # one seat: darker towards the bottom, a dark slit on either side
    t = np.zeros((32, 32, 3), 'f')
    t[:] = np.array(color, 'f') * np.linspace(0.62, 1.0, 32)[:, None, None]
    t[:, :2] *= 0.22; t[:, -2:] *= 0.22
    t[-2:] *= 1.12
    return t


def brick_tile():
    t = np.zeros((256, 256, 3), 'f')
    t[:] = np.array((0.50, 0.47, 0.43), 'f')          # mortar
    base = np.array((0.42, 0.27, 0.19), 'f')
    rows, cols = 8, 4
    rh, cw = 256 // rows, 256 // cols
    for r in range(rows):
        off = (cw // 2) if r % 2 else 0
        for c in range(cols):
            col = base * rng.uniform(0.78, 1.15) * np.array((1, rng.uniform(0.92, 1.06), rng.uniform(0.9, 1.05)), 'f')
            x0 = c * cw + off
            for x in range(x0 + 2, x0 + cw - 1):
                t[r * rh + 2:(r + 1) * rh - 1, x % 256] = col
    t *= rng.normal(1, 0.04, (256, 256, 1)).astype('f')
    return t


seat_mat = image_material('M_Seat', painted('lottopark_seat_purple', seat_tile((0.20, 0.10, 0.42))), 0.55)
seat_white = image_material('M_SeatWhite', painted('lottopark_seat_white', seat_tile((0.84, 0.84, 0.87))), 0.55)
rail_seat = image_material('M_RailSeat', painted('lottopark_seat_rail', seat_tile((0.17, 0.18, 0.20))), 0.6)      # folded-up seats of the standing rows
brick = image_material('M_BrickTex', painted('lottopark_brick', brick_tile()), 0.9)
concrete = principled('M_TerraceTread', (0.50, 0.49, 0.47), 0.9)
concrete_dark = principled('M_TerraceRiser', (0.33, 0.32, 0.31), 0.9)
concrete_light = principled('M_ConcreteLight', (0.66, 0.65, 0.62), 0.85)
glass = principled('M_Glass', (0.05, 0.07, 0.10), 0.12)
PANES = 16                       # panes in one repeat of the window texture
PANE_W = 2.0                     # metres per pane


def windows_tex():
    # rooms seen through glass at night: most lit warm (bright ceiling, darker
    # furniture and people below), some dark, thin frames between the panes
    pw, h = 64, 128
    t = np.zeros((h, pw * PANES, 3), 'f')
    v = np.linspace(0, 1, h)[:, None]
    for k in range(PANES):
        x0 = k * pw
        if rng.random() < 0.78:
            warm = np.array((1.0, 0.74, 0.48), 'f') * rng.uniform(0.35, 0.75)
            prof = 0.55 + 0.45 * np.clip((v - 0.55) / 0.3, 0, 1) ** 1.5      # brighter towards the ceiling
            prof = np.where(v > 0.86, 1.25, prof)                            # the ceiling lights
            prof = np.where(v < 0.32, 0.30, prof)                            # tables, seats, backs of heads
            pane = warm * prof[..., None] * np.ones((1, pw, 1), 'f')
            for _ in range(rng.integers(1, 4)):                              # a few figures against the light
                cx, wd = rng.integers(6, pw - 6), rng.integers(4, 9)
                top = rng.uniform(0.45, 0.62)
                m = (v < top) & (v > 0.05)
                pane[:, max(0, cx - wd // 2):cx + wd // 2][m[:, 0]] *= 0.35
        else:
            pane = np.array((0.03, 0.035, 0.05), 'f') * (1 + 0.6 * v)[..., None] * np.ones((1, pw, 1), 'f')
        pane[:, :2] = 0.02; pane[:, -2:] = 0.02; pane[:3] = 0.02; pane[-3:] = 0.02     # frames
        t[:, x0:x0 + pw] = pane
    return t


glass_lit = image_material('M_GlassLit', painted('lottopark_windows', windows_tex()), 0.2)
corner_wall = principled('M_CornerWall', (0.80, 0.80, 0.84), 0.85)
dark_band = principled('M_DarkBand', (0.10, 0.10, 0.11), 0.7)        # lit rooms behind the glass
led_purple = principled('M_LED', (0.21, 0.065, 0.60), 0.4, (0.21, 0.065, 0.60), 4.0)          # boards and bands
light_white = principled('M_FasciaText', (0.90, 0.90, 0.92), 0.4, (0.90, 0.90, 0.92), 2.0)   # lettering
steel = principled('M_Steel', (0.42, 0.43, 0.45), 0.5, metallic=0.3)
beam = principled('M_RoofBeam', (0.20, 0.20, 0.22), 0.7)
build_purple = principled('M_BuildPurple', (0.22, 0.07, 0.62), 0.5, (0.22, 0.07, 0.62), 3.0)   # the lit bands of the office block

# ================================================================ pitch
for n in ['Bottom', 'CenterCircle', 'Left', 'Mid', 'Right', 'Top']:      # the oversized attempt
    if n in D.objects:
        remove(D.objects[n])
for o in list(D.collections['01_Pitch'].objects):
    if o.name.startswith(('Line_', 'GA_', 'PB_', 'CenterSpot', 'PenaltySpot')):
        remove(o)

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
hline(hy, -hx - e, hx + e); hline(-hy, -hx - e, hx + e)          # touchlines
vline(hx, -hy, hy); vline(-hx, -hy, hy); vline(0, -hy, hy)       # goal lines, halfway line
arc(0, 0, 9.15 * K, 0, 2 * math.pi, 96); disc(0, 0, 0.22)        # centre circle and spot
for s in (-1, 1):
    gx = s * hx
    for depth, half in ((16.5 * K, 20.16 * K), (5.5 * K, 9.16 * K)):   # penalty area, goal area
        x = gx - s * depth
        vline(x, -half - e, half + e)
        hline(half, min(gx, x), max(gx, x)); hline(-half, min(gx, x), max(gx, x))
    spot = gx - s * 11 * K
    disc(spot, 0, 0.22)
    a = math.acos((16.5 - 11) / 9.15)                              # the D outside the box
    mid = math.pi if s > 0 else 0
    arc(spot, 0, 9.15 * K, mid - a, mid + a, 32)
    for t in (-1, 1):                                              # corner arcs
        a0 = {(1, 1): math.pi, (1, -1): math.pi / 2, (-1, 1): 1.5 * math.pi, (-1, -1): 0}[(s, t)]
        arc(gx, t * hy, 1.0 * K, a0, a0 + math.pi / 2, 10)
lines = new_obj('Pitch_Lines', bm, '01_Pitch', [D.materials['M_Lines']])

# two real goals on the goal lines. The game takes them out (it has its own,
# sized for play); in the picker, the test page and Blender they stand there.
for o in [o for o in D.collections['01_Pitch'].objects if o.name.startswith(('GoalPost', 'Crossbar', 'GoalNet'))]:
    remove(o)
net_tile = np.zeros((32, 32, 4), 'f')
net_tile[..., :3] = 0.92
net_tile[:3, :, 3] = 1.0; net_tile[:, :3, 3] = 1.0
net_img = D.images.new('lottopark_net', 32, 32, alpha=True)
net_img.pixels.foreach_set(net_tile.ravel())
net_img.filepath_raw = TEX_DIR + '/lottopark_net.png'; net_img.file_format = 'PNG'; net_img.save(); net_img.pack()
net_mat = image_material('M_Net', net_img, 0.8)
nn = net_mat.node_tree
tex_n = next(n for n in nn.nodes if n.type == 'TEX_IMAGE')
nn.links.new(tex_n.outputs['Alpha'], next(n for n in nn.nodes if n.type == 'BSDF_PRINCIPLED').inputs['Alpha'])
for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
    try:
        setattr(net_mat, attr, val)
    except Exception:
        pass
net_mat.use_backface_culling = False
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
for s in (-1, 1):
    gx = s * hx
    V = lambda x, y, z: Vector((x, y, z))
    for y in (-GOAL_HW, GOAL_HW):
        tube(bm, V(gx, y, 0), V(gx, y, GOAL_H + POST_R), POST_R, 0)                         # posts
        tube(bm, V(gx + s * 1.0, y, GOAL_H), V(gx + s * 2.0, y, 0.03), 0.025, 0)           # back stanchions
        tube(bm, V(gx, y, 0.03), V(gx + s * 2.0, y, 0.03), 0.025, 0)                       # ground frame
        tube(bm, V(gx, y, GOAL_H), V(gx + s * 1.0, y, GOAL_H), 0.025, 0)                   # top supports
    tube(bm, V(gx, -GOAL_HW - POST_R, GOAL_H), V(gx, GOAL_HW + POST_R, GOAL_H), POST_R, 0)    # crossbar
    tube(bm, V(gx + s * 2.0, -GOAL_HW, 0.03), V(gx + s * 2.0, GOAL_HW, 0.03), 0.025, 0)
    m = 1.0 / MESH
    w2 = 2 * GOAL_HW
    face(bm, [V(gx, -GOAL_HW, GOAL_H), V(gx + s, -GOAL_HW, GOAL_H), V(gx + s, GOAL_HW, GOAL_H), V(gx, GOAL_HW, GOAL_H)], None, 1,
         [(0, 0), (m, 0), (m, w2 * m), (0, w2 * m)])                                          # roof of the net
    slope = math.hypot(1.0, GOAL_H) * m
    face(bm, [V(gx + s, -GOAL_HW, GOAL_H), V(gx + 2 * s, -GOAL_HW, 0), V(gx + 2 * s, GOAL_HW, 0), V(gx + s, GOAL_HW, GOAL_H)], None, 1,
         [(0, 0), (slope, 0), (slope, w2 * m), (0, w2 * m)])                                  # back
    for y in (-GOAL_HW, GOAL_HW):
        face(bm, [V(gx, y, 0), V(gx, y, GOAL_H), V(gx + s, y, GOAL_H), V(gx + 2 * s, y, 0)], None, 1,
             [(0, 0), (0, GOAL_H * m), (m, GOAL_H * m), (2 * m, 0)])                          # sides
goals = new_obj('StadiumGoals', bm, '01_Pitch', [post_mat, net_mat])

# grass: the whole bowl floor, mown in a 5.5 m checkerboard
grass = D.objects['Pitch_Grass']
bm = bmesh.new()
f = bm.faces.new([bm.verts.new((x, y, 0)) for x, y in ((-FLOOR_X, -FLOOR_Y), (FLOOR_X, -FLOOR_Y), (FLOOR_X, FLOOR_Y), (-FLOOR_X, FLOOR_Y))])
uv = bm.loops.layers.uv.new('UVMap')
for l, c in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
    l[uv].uv = c
bm.to_mesh(grass.data)
bm.free()
grass.location = (0, 0, 0); grass.rotation_euler = (0, 0, 0); grass.scale = (1, 1, 1)

nt = D.materials['M_Grass'].node_tree
nt.nodes.clear()
out = nt.nodes.new('ShaderNodeOutputMaterial')
b = nt.nodes.new('ShaderNodeBsdfPrincipled'); b.inputs['Roughness'].default_value = 0.85
tc = nt.nodes.new('ShaderNodeTexCoord')
sep = nt.nodes.new('ShaderNodeSeparateXYZ')
L = nt.links.new
L(tc.outputs['Object'], sep.inputs[0])


def band(axis):
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 1 / 11.0
    fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = 0.5
    L(sep.outputs[axis], mul.inputs[0]); L(mul.outputs[0], fr.inputs[0]); L(fr.outputs[0], gt.inputs[0])
    return gt


dif = nt.nodes.new('ShaderNodeMath'); dif.operation = 'SUBTRACT'      # where the two bands differ: the checkerboard
xor = nt.nodes.new('ShaderNodeMath'); xor.operation = 'ABSOLUTE'
mix = nt.nodes.new('ShaderNodeMixRGB')
mix.inputs['Color1'].default_value = (0.060, 0.30, 0.060, 1)
mix.inputs['Color2'].default_value = (0.082, 0.37, 0.078, 1)
L(band('X').outputs[0], dif.inputs[0]); L(band('Y').outputs[0], dif.inputs[1]); L(dif.outputs[0], xor.inputs[0])
L(xor.outputs[0], mix.inputs['Fac']); L(mix.outputs['Color'], b.inputs['Base Color'])
L(b.outputs['BSDF'], out.inputs['Surface'])

# the purple artificial strip between the grass and the stands
bm = bmesh.new()
Z = 0.01
ix, iy = hx + 2.5, hy + 2.5
rect(-FLOOR_X, iy, FLOOR_X, FLOOR_Y); rect(-FLOOR_X, -FLOOR_Y, FLOOR_X, -iy)
rect(-FLOOR_X, -iy, -ix, iy); rect(ix, -iy, FLOOR_X, iy)
surround = new_obj('Pitch_Surround', bm, '01_Pitch', [principled('M_PitchSurround', (0.20, 0.09, 0.36), 0.9)])

# ================================================================ ground pad
pad = D.objects['Ground_Pad']
dg = bpy.context.evaluated_depsgraph_get()
bm = bmesh.new()
bm.from_object(pad, dg)
bmesh.ops.scale(bm, vec=(0.66, 0.66, 1), verts=bm.verts[:])     # an apron around the stadium, not a field twice its size
pad.location.x = pad.location.y = 0
for co, no in (((70, 0, 0), (1, 0, 0)), ((-70, 0, 0), (1, 0, 0)), ((0, 50, 0), (0, 1, 0)), ((0, -50, 0), (0, 1, 0))):
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], dist=1e-4, plane_co=co, plane_no=no)
inner = [f for f in bm.faces if abs(f.calc_center_median().x) < 70 and abs(f.calc_center_median().y) < 50]
bmesh.ops.delete(bm, geom=inner, context='FACES')      # the stadium stands on the hole
pad.modifiers.clear()
bm.to_mesh(pad.data)
bm.free()
pad.location.z = -0.15                                  # under the pitch, not over it

# ================================================================ stands
# The old terraces were one steep 6 m step and one shallow slab. Rebuilt as the
# real stadium has them: a shallow lower ring, a row of glass boxes, a steeper
# upper ring that starts above the boxes.
for n in ('Bowl_LowerTerraces', 'Bowl_UpperTerraces', 'Bowl_VomWall'):
    remove(D.objects[n])

AISLE_EVERY, AISLE_W, BLOCK_SEATS = 16.0, 1.3, 4
_heights = {}


def white_rows(key):
    # how many rows of white seats a column has, counted from the front: the
    # ragged white-into-purple pattern of the upper ring
    if key not in _heights:
        _heights[key] = random.Random(str(key)).choice((3, 4, 5, 6, 6, 7, 8, 9, 10, 12, 14))
    return _heights[key]


def column_key(p):
    if abs(p.x) <= CX:
        return ('N' if p.y > 0 else 'S', int(p.x // 2))
    if abs(p.y) <= CY:
        return ('E' if p.x > 0 else 'W', int(p.y // 2))
    return (p.x > 0, p.y > 0, int(math.atan2(abs(p.y) - CY, abs(p.x) - CX) / 0.2))


UP_V = Vector((0, 0, 1))


def seat_row(bm, a, b, row, pattern):
    # a: the two front corners of a tread, b: the two back corners
    length = (a[1] - a[0]).length
    spans = [(0.0, length)]
    if length > 20:          # a straight: stairs every 16 m
        cuts = [length / 2 + j * AISLE_EVERY for j in range(-6, 7)]
        edges = [0.0] + [c + d for c in cuts if AISLE_W < c < length - AISLE_W for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
        spans = [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]
    back = (b[0] - a[0]).normalized()
    for s0, s1 in spans:
        seats = max(1, round((s1 - s0) / SEAT_W))
        for k in range(0, seats, BLOCK_SEATS):
            k1 = min(k + BLOCK_SEATS, seats)
            u = [(s0 + (s1 - s0) * q / seats) / length for q in (k, k1)]
            pa = [a[0].lerp(a[1], t) for t in u]; pb = [b[0].lerp(b[1], t) for t in u]

            def at(t, h, i):
                return pa[i].lerp(pb[i], t) + Vector((0, 0, h))
            mat = 0
            if pattern:
                mat = 1 if row < white_rows(column_key((pa[0] + pa[1]) / 2)) else 0
            # seat, backrest, top edge of the backrest; one texture tile per seat
            face(bm, [at(0.34, 0.42, 0), at(0.34, 0.42, 1), at(0.72, 0.42, 1), at(0.72, 0.42, 0)], UP_V, mat, [(k, 0.0), (k1, 0.0), (k1, 0.45), (k, 0.45)])
            face(bm, [at(0.72, 0.42, 0), at(0.72, 0.42, 1), at(0.78, 0.84, 1), at(0.78, 0.84, 0)], -back, mat, [(k, 0.45), (k1, 0.45), (k1, 0.95), (k, 0.95)])
            face(bm, [at(0.78, 0.84, 0), at(0.78, 0.84, 1), at(0.84, 0.84, 1), at(0.84, 0.84, 0)], UP_V, mat, [(k, 0.95), (k1, 0.95), (k1, 1.0), (k, 1.0)])


def build_tier(name, t, base_z, skip=(), standing=(), pattern=False):
    steps, seats = bmesh.new(), bmesh.new()
    for k in range(t['rows']):
        r0, z = t['r'] + t['depth'] * k, t['z'] + t['rise'] * k
        ring(steps, r0, base_z if k == 0 else z - t['rise'], r0, z, 1, skip)          # riser
        ring(steps, r0, z, r0 + t['depth'], z, 0, skip)                               # tread
        p0, p1 = ring_path(r0), ring_path(r0 + t['depth'])
        for i in range(N_RING):
            if i in skip or i in standing:
                continue
            j = (i + 1) % N_RING
            seat_row(seats, [Vector((p0[i][0], p0[i][1], z)), Vector((p0[j][0], p0[j][1], z))],
                     [Vector((p1[i][0], p1[i][1], z)), Vector((p1[j][0], p1[j][1], z))], k, pattern)
    new_obj('Bowl_' + name + 'Terraces', steps, '02_Bowl', [concrete, concrete_dark])
    new_obj('Seats_' + name, seats, '03_Seats', [seat_mat, seat_white])


# The lower ring behind both goals is safe standing, as on the photos from
# there: a steel rail on posts in front of every row, grey seats folded up
# beneath it. The long sides and the corners have seats.
STANDING = {W_SIDE, E_SIDE}          # behind the goals; the long sides and the corners have seats


def spans_of(length):
    if length <= 20:
        return [(0.0, length)]
    cuts = [length / 2 + j * AISLE_EVERY for j in range(-6, 7)]
    edges = [0.0] + [c + d for c in cuts if AISLE_W < c < length - AISLE_W for d in (-AISLE_W / 2, AISLE_W / 2)] + [length]
    return [(edges[i], edges[i + 1]) for i in range(0, len(edges), 2)]


def rail_row(bm, a, b, z):
    # a: the two front corners of a tread, b: the two back corners
    length = (a[1] - a[0]).length
    along = (a[1] - a[0]).normalized()
    back = (b[0] - a[0]).normalized()
    al, bk_ = (along.x, along.y), (back.x, back.y)

    def at(s_, t):                     # s_ along the row, t back from its front edge
        q = a[0] + along * s_ + back * t
        return (q.x, q.y)
    for s0, s1 in spans_of(length):
        s0 += 0.05; s1 -= 0.05
        mid = (s0 + s1) / 2; half = (s1 - s0) / 2
        n_posts = max(1, round((s1 - s0) / 2.0))
        posts = [s0 + 0.2 + (s1 - s0 - 0.4) * k / n_posts for k in range(n_posts + 1)]
        for q in posts:
            box(bm, at(q, 0.11), al, 0.025, bk_, 0.025, z, z + 0.99, 0)
        # rail and bar run from post to post, each piece with its own corners,
        # so none of them sits inside a post (that baked the whole rail black)
        ends = [s0] + posts + [s1]
        for q0, q1 in zip(ends[:-1], ends[1:]):
            q0 += 0.04 if q0 in posts else 0.0
            q1 -= 0.04 if q1 in posts else 0.0
            if q1 - q0 < 0.05:
                continue
            m_, h_ = (q0 + q1) / 2, (q1 - q0) / 2
            box(bm, at(m_, 0.10), al, h_, bk_, 0.03, z + 1.00, z + 1.06, 0)            # the rail
            box(bm, at(m_, 0.12), al, h_, bk_, 0.015, z + 0.84, z + 0.88, 0)           # the bar under it
        seats = max(1, round((s1 - s0) / SEAT_W))
        for k in range(0, seats, BLOCK_SEATS):                                         # the folded seats
            k1 = min(k + BLOCK_SEATS, seats)
            u0, u1 = s0 + (s1 - s0) * k / seats, s0 + (s1 - s0) * k1 / seats
            p0, p1 = at(u0, 0.17), at(u1, 0.17)
            face(bm, [(p0[0], p0[1], z + 0.30), (p1[0], p1[1], z + 0.30), (p1[0], p1[1], z + 0.80), (p0[0], p0[1], z + 0.80)],
                 -back, 1, [(k, 0.0), (k1, 0.0), (k1, 1.0), (k, 1.0)])


build_tier('Lower', LOW, 1.2, standing=STANDING)
build_tier('Upper', UP, LODGE_Z1, skip=CORNER, pattern=True)
bm = bmesh.new()
for k in range(LOW['rows']):
    r0, z = LOW['r'] + LOW['depth'] * k, LOW['z'] + LOW['rise'] * k
    p0, p1 = ring_path(r0), ring_path(r0 + LOW['depth'])
    for i in STANDING:
        j = (i + 1) % N_RING
        rail_row(bm, [Vector((p0[i][0], p0[i][1], 0)), Vector((p0[j][0], p0[j][1], 0))],
                 [Vector((p1[i][0], p1[i][1], 0)), Vector((p1[j][0], p1[j][1], 0))], z)
new_obj('Standing_Rails', bm, '03_Seats', [principled('M_Galvanised', (0.38, 0.39, 0.41), 0.5), rail_seat])

# the dugouts and the players' tunnel, at pitch level in front of the south
# stand (the side with the office block), as on the photos from the stands
plexi = principled('M_Plexi', (0.70, 0.75, 0.82), 0.2)
bm, sb = bmesh.new(), bmesh.new()
YB, YF = -(CY + 11.85), -(CY + 9.35)            # back (in front of the boards) and front
for x0, x1 in ((-17.5, -3.2), (3.2, 17.5)):
    face(bm, [(x0, YB, 0), (x1, YB, 0), (x1, YB, 2.35), (x0, YB, 2.35)], Vector((0, 1, 0)), 0)      # white back
    for zz, nrm in ((2.36, (0, 0, 1)), (2.34, (0, 0, -1))):                                       # plexi roof
        face(bm, [(x0, YB, zz), (x1, YB, zz), (x1, YF, zz - 0.3), (x0, YF, zz - 0.3)], Vector(nrm), 1)
    for xx, nx in ((x0, -1), (x1, 1)):                                                            # plexi ends
        for off in (0.0, 0.02):
            face(bm, [(xx + off * nx, YB, 0), (xx + off * nx, YF, 0), (xx + off * nx, YF, 2.04), (xx + off * nx, YB, 2.34)], Vector((nx if off else -nx, 0, 0)), 1)
    box(bm, ((x0 + x1) / 2, YB + 0.75), (1, 0), (x1 - x0) / 2 - 0.1, (0, 1), 0.7, 0, 0.35, 2)     # step for the back row
    for yf, zz in ((YB + 1.45, 0.35), (YB + 2.35, 0.0)):
        seat_row(sb, [Vector((x0 + 0.2, yf, zz)), Vector((x1 - 0.2, yf, zz))],
                 [Vector((x0 + 0.2, yf - 0.8, zz)), Vector((x1 - 0.2, yf - 0.8, zz))], 0, False)
box(bm, (0, YB + 1.5), (1, 0), 1.6, (0, 1), 1.5, 0, 2.5, 0)                                      # tunnel
box(bm, (0, YB + 1.5), (1, 0), 1.65, (0, 1), 1.55, 1.7, 2.05, 3)
new_obj('Dugouts', bm, '02_Bowl', [corner_wall, plexi, concrete_dark, led_purple])
new_obj('Dugout_Seats', sb, '03_Seats', [seat_mat, seat_white])

# the boxes between the rings: concrete sill, glass, concrete head, mullions
bm = bmesh.new()
ring(bm, LODGE_R, LODGE_Z0, LODGE_R, 6.7, 0, CORNER)
ring(bm, LODGE_R, 6.7, LODGE_R, 8.6, 1, CORNER, u_len=PANE_W * PANES)
ring(bm, LODGE_R, 8.6, LODGE_R, LODGE_Z1, 0, CORNER)
ring(bm, UP['r'], LODGE_Z1, LODGE_R, LODGE_Z1, 0, CORNER)
new_obj('Lodges', bm, '02_Bowl', [concrete_light, glass_lit])
bm = bmesh.new()
for sy in (1, -1):
    for x in range(-40, 41, 4):
        box(bm, (x, sy * (CY + LODGE_R - 0.07)), (1, 0), 0.07, (0, 1), 0.07, 6.7, 8.6)
for sx in (1, -1):
    for y in range(-24, 25, 4):
        box(bm, (sx * (CX + LODGE_R - 0.07), y), (1, 0), 0.07, (0, 1), 0.07, 6.7, 8.6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
new_obj('Lodge_Mullions', bm, '02_Bowl', [concrete_light])

# the advertising band on the front of the upper ring
bm = bmesh.new()
ring(bm, UP['r'] - 0.1, 8.82, UP['r'] - 0.1, 9.78, 0, CORNER)
new_obj('Ribbon', bm, '02_Bowl', [led_purple])


def wall_text(name, body, loc, outward, size, coll, mat='M_FasciaText'):
    cu = D.curves.new(name, 'FONT')
    cu.body = body; cu.size = size; cu.align_x = 'CENTER'; cu.extrude = 0.01
    cu.offset = size * 0.022                                         # a little bolder
    cu.materials.append(D.materials[mat])
    t = D.objects.new(name, cu)
    t.location = loc
    t.rotation_euler = (math.pi / 2, 0, outward - math.pi / 2)      # stands up, faces the pitch
    D.collections[coll].objects.link(t)
    return t


n = 0
rr = UP['r'] - 0.16
for sy in (1, -1):
    for x in range(-40, 41, 10):
        if sy < 0 and x == 0:
            continue                          # the score panel sits there
        wall_text('Ribbon_RSCA_%d' % n, 'RSCA', (x, sy * (CY + rr), 8.98), sy * math.pi / 2, 0.92, '02_Bowl'); n += 1
for sx in (1, -1):
    for y in (-18, -6, 6, 18):
        wall_text('Ribbon_RSCA_%d' % n, 'RSCA', (sx * (CX + rr), y, 8.98), 0 if sx > 0 else math.pi, 0.92, '02_Bowl'); n += 1

# the little scoreboard in the band on the south stand (the side with the
# stars the game camera looks at), as in the real stadium: score and clock,
# drawn live by the game (game.screen.js) on its own node 'StadiumRibbonScore'
RS_X, RS_W = 0.0, 4.2                         # in the middle of the band, under the three stars
rs_y = -(CY + UP['r'] - 0.1) + 0.04
bm = bmesh.new()
face(bm, [(RS_X + RS_W / 2, rs_y, 8.82), (RS_X - RS_W / 2, rs_y, 8.82), (RS_X - RS_W / 2, rs_y, 9.78), (RS_X + RS_W / 2, rs_y, 9.78)],
     Vector((0, 1, 0)), 0, [(0, 0), (1, 0), (1, 1), (0, 1)])           # u runs left to right as seen from the pitch
ribbon_score = new_obj('StadiumRibbonScore', bm, '02_Bowl', [principled('M_RibbonScore', (1.0, 1.0, 1.0), 0.4, (0.13, 0.05, 0.28), 2.0)])

# LED boards along the front of the lower ring (where the game keeps them)
for o in ('AdvertBoardRing',):
    if o in D.objects:
        remove(D.objects[o])
bm = bmesh.new()
ring(bm, 11.9, 0.12, 11.9, 1.02, 0)
new_obj('LED_Boards', bm, '02_Bowl', [led_purple])
n = 0
for sy in (1, -1):
    for x in range(-42, 43, 7):
        wall_text('Board_RSCA_%d' % n, 'RSCA', (x, sy * (CY + 11.88), 0.36), sy * math.pi / 2, 0.62, '02_Bowl'); n += 1
for sx in (1, -1):
    for y in range(-21, 22, 7):
        wall_text('Board_RSCA_%d' % n, 'RSCA', (sx * (CX + 11.88), y, 0.36), 0 if sx > 0 else math.pi, 0.62, '02_Bowl'); n += 1

# ---------------------------------------------------------------- the corner block
# far left when you face the RSC ANDERLECHT end: an open concrete deck with
# the office block on it, and blank end walls where the upper ring stops
bm = bmesh.new()
ring(bm, LODGE_R, LODGE_Z0, 45.5, LODGE_Z0, 0, only=CORNER)
top = UP['z'] + UP['rise'] * UP['rows']
diag = Vector((CSX, CSY, 0)).normalized()
for d in ((CSX, 0), (0, CSY)):
    p = [Vector((CSX * CX + d[0] * r, CSY * CY + d[1] * r, z)) for r, z in ((UP['r'], LODGE_Z0), (45.5, LODGE_Z0), (45.5, top), (UP['r'], LODGE_Z1))]
    face(bm, p, diag - Vector((d[0], d[1], 0)), 1)
new_obj('Corner_Deck', bm, '02_Bowl', [concrete, concrete_light])

# The corner between the two stands is closed by a building up to the roof,
# as on the photos: plain white concrete walls slant in from the ends of the
# stands to a glass front, floors of lit rooms between purple bands, the lotto
# Park sign on one of them, and small windows in the white top under the roof.
tn = Vector((-diag.y, diag.x, 0))                       # along the front
C0 = Vector((CSX * CX, CSY * CY, 0))
F, WH, Z_TOP = 24.6, 7.0, 25.7
O = C0 + diag * F
ends = [C0 + Vector((0, CSY, 0)) * UP['r'], C0 + Vector((CSX, 0, 0)) * UP['r']]
CORNER_WALLS = []
bm = bmesh.new()
for E in (O + tn * WH, O - tn * WH):
    A = min(ends, key=lambda q: (q - E).length)
    # a grid with shared corners, so the uplight fades smoothly up the wall
    nu, nv = max(1, round((E - A).length / 1.5)), 14
    grid = [[bm.verts.new(A.lerp(E, iu / nu) + Vector((0, 0, LODGE_Z0 + (Z_TOP - LODGE_Z0) * iv / nv))) for iv in range(nv + 1)] for iu in range(nu + 1)]
    for iu in range(nu):
        for iv in range(nv):
            f = bm.faces.new((grid[iu][iv], grid[iu + 1][iv], grid[iu + 1][iv + 1], grid[iu][iv + 1]))
            f.normal_update()
            if f.normal.dot(-diag) < 0:
                f.normal_flip()
    CORNER_WALLS.append((A.copy(), E.copy()))
new_obj('Corner_Walls', bm, '02_Bowl', [corner_wall])


def P(t, z, off):
    return O + tn * t + diag * off + Vector((0, 0, z))


def front_quad(bm, t0, t1, z0, z1, off, mat, uvs=None):
    face(bm, [P(t0, z0, off), P(t1, z0, off), P(t1, z1, off), P(t0, z1, off)], -diag, mat, uvs)


def front_box(bm, t0, t1, z0, z1, o0, o1, mat):
    c = O + tn * ((t0 + t1) / 2) + diag * ((o0 + o1) / 2)
    box(bm, (c.x, c.y), (tn.x, tn.y), (t1 - t0) / 2, (diag.x, diag.y), (o1 - o0) / 2, z0, z1, mat)


# materials: 0 white concrete, 1 lit rooms, 2 purple band, 3 dark band
bm = bmesh.new()
RECESS = 0.6
FLOORS = [(LODGE_Z0, 8.8, 'glass'), (8.8, 9.8, 'band'), (9.8, 13.0, 'glass'), (13.0, 14.4, 'band'),
          (14.4, 16.6, 'glass'), (16.6, 17.6, 'band'), (17.6, 20.6, 'glass'), (20.6, 21.5, 'dark'), (21.5, Z_TOP, 'top')]
for z0, z1, kind in FLOORS:
    if kind == 'glass':
        u0 = rng.integers(0, PANES)                     # each floor shows other rooms
        front_quad(bm, -WH, WH, z0, z1, RECESS, 1, [(u0 / PANES, 0), ((u0 + 2 * WH / PANE_W) / PANES, 0),
                                                    ((u0 + 2 * WH / PANE_W) / PANES, 1), (u0 / PANES, 1)])
        for k in range(1, int(2 * WH / PANE_W)):       # mullions
            t = -WH + k * PANE_W
            front_box(bm, t - 0.05, t + 0.05, z0, z1, RECESS - 0.18, RECESS, 3)
        for t, sgn in ((-WH, 1), (WH, -1)):            # the sides of the recess
            face(bm, [P(t, z0, 0), P(t, z0, RECESS), P(t, z1, RECESS), P(t, z1, 0)], tn * sgn, 0)
    elif kind == 'band':
        front_box(bm, -WH - 0.2, WH + 0.2, z0, z1, -0.3, RECESS, 2)
    elif kind == 'dark':
        front_box(bm, -WH - 0.1, WH + 0.1, z0, z1, -0.12, RECESS, 3)
    else:
        front_quad(bm, -WH, WH, z0, z1, 0, 0)
        for t in np.arange(-WH + 1.1, WH - 1.4, 2.5):  # small windows in the top
            u0 = int(rng.integers(0, PANES))
            front_quad(bm, t, t + 1.5, 22.3, 23.5, -0.03, 1, [((u0 + 0.1) / PANES, 0.1), ((u0 + 0.9) / PANES, 0.1), ((u0 + 0.9) / PANES, 0.9), ((u0 + 0.1) / PANES, 0.9)])
for t in (-WH - 0.45, WH + 0.45):                       # white piers framing the glass front
    front_box(bm, t - 0.45, t + 0.45, LODGE_Z0, Z_TOP, -0.45, 0.3, 0)
new_obj('Corner_Front', bm, '02_Bowl', [corner_wall, glass_lit, build_purple, dark_band])
sign = P(0, 13.27, -0.33)
wall_text('Corner_Sign', 'lotto Park', (sign.x, sign.y, sign.z), math.atan2(diag.y, diag.x), 0.95, '02_Bowl')

# ---------------------------------------------------------------- roof
# The roof edge was a 3 m slab of colour. On the real stands it is a slim
# blue-violet band on the nose of a roof that tapers towards the pitch, with
# a pale trim on top and the lamps tucked under it.
FASCIA_R, FASCIA_Z0, FASCIA_Z1 = 15.5, 24.38, ROOF_Z - 0.16
SCREEN_DROP = 4.9          # the screens hang this far below their old place, into the game camera's view
D.materials['M_FasciaDark'].node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.10, 0.14, 0.56, 1)
fascia = D.objects['Roof_InnerFascia']
bm = bmesh.new()
ring(bm, FASCIA_R, FASCIA_Z0, FASCIA_R, FASCIA_Z1, 0)                        # the band
ring(bm, FASCIA_R - 0.04, FASCIA_Z1, FASCIA_R - 0.04, FASCIA_Z1 + 0.16, 1)   # pale trim along the top
ring(bm, FASCIA_R - 0.04, FASCIA_Z1 + 0.16, FASCIA_R + 0.5, FASCIA_Z1 + 0.16, 1)
ring(bm, FASCIA_R, FASCIA_Z0, FASCIA_R + 4.2, 25.7, 2)                       # the underside of the tapering nose
bm.to_mesh(fascia.data)
bm.free()
fascia.location = (0, 0, 0); fascia.rotation_euler = (0, 0, 0); fascia.scale = (1, 1, 1)
fascia.data.materials.append(concrete_light)
fascia.data.materials.append(principled('M_RoofSoffit', (0.60, 0.61, 0.63), 0.8))
for n in ('Fascia_RSCText', 'Fascia_SinceText'):                              # lettering sized to the slim band
    t = D.objects[n]
    t.data.size = 1.55
    t.data.offset = 1.55 * 0.022
    t.location.z = FASCIA_Z0 + 0.34
D.objects['Fascia_RSCText'].data.body, D.objects['Fascia_SinceText'].data.body = 'SINCE 1908', 'RSC ANDERLECHT'
stars_s = [o for o in D.objects if o.name.startswith('Fascia_Star_')]
for o in stars_s:
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    c = sum(bb, Vector()) / 8
    cx_all = 0.0                                                             # the three stars sit around x = 0
    k = 0.6
    o.matrix_world = Matrix.Translation(Vector((cx_all + (c.x - cx_all) * k, c.y, (FASCIA_Z0 + FASCIA_Z1) / 2))) @ Matrix.Scale(k, 4) @ Matrix.Translation(-c) @ o.matrix_world

bpy.context.view_layer.update()
for k, o in enumerate(stars_s):                 # the three stars on the north side too
    n_ = o.copy()
    n_.name = 'Fascia_StarN_%d' % k
    n_.matrix_world = Matrix.Rotation(math.pi, 4, 'Z') @ o.matrix_world
    o.users_collection[0].objects.link(n_)

# lamps under the nose, in pairs of four-lamp clusters, on a dark carrier
bm = bmesh.new()
LAMP_R = 17.7


def lamp_group(cx, cy, along, outward):  # along: unit vector of the roof edge; outward: away from the pitch
    z0 = 24.42
    for i in range(4):
        c = (i - 1.5) * 0.62
        p = [(cx + along[0] * (c + d), cy + along[1] * (c + d)) for d in (-0.24, 0.24)]
        face(bm, [(p[0][0], p[0][1], z0), (p[1][0], p[1][1], z0), (p[1][0], p[1][1], z0 + 0.46), (p[0][0], p[0][1], z0 + 0.46)], None, 0)
    box(bm, (cx + outward[0] * 0.12, cy + outward[1] * 0.12), along, 1.35, outward, 0.08, z0 - 0.08, z0 + 0.6, 1)      # carrier, behind the lamps


for sy in (1, -1):
    for x in (-36, -31, -13, -8, 8, 13, 31, 36):
        lamp_group(x, sy * (CY + LAMP_R), (1, 0), (0, sy))
for sx in (1, -1):
    for y in (-16, -11, 11, 16):
        lamp_group(sx * (CX + LAMP_R), y, (0, 1), (sx, 0))
new_obj('Roof_Lamps', bm, '04_Roof', [D.materials['M_FloodLight'], beam])

# the underside of the roof (the old slab was far too coarse to hold light)
remove(D.objects['Roof_Slab'])
bm = bmesh.new()
r = FASCIA_R + 4.2
while r < 45.5 - 1e-6:
    r2 = min(45.5, r + 2.0)
    ring(bm, r, 25.7, r2, 25.7, 0, want='down')
    r = r2
ring(bm, 45.5, 25.7, 45.5, ROOF_Z, 0, want='out')
new_obj('Roof_Soffit', bm, '04_Roof', [D.materials['M_RoofSoffit']])

# purlins along the roof, across the rafters
bm = bmesh.new()
for r in (21.0, 27.0, 33.0, 39.0):
    ring(bm, r, 25.3, r, 25.7, 0)
new_obj('Roof_Purlins', bm, '04_Roof', [beam])

# rafters under the roof, from the edge back to the outer wall
bm = bmesh.new()
for sy in (1, -1):
    for x in range(-40, 41, 8):
        box(bm, (x, sy * (CY + 30.4)), (1, 0), 0.18, (0, 1), 14.6, 24.85, 25.7)
for sx in (1, -1):
    for y in range(-24, 25, 8):
        box(bm, (sx * (CX + 30.4), y), (0, 1), 0.18, (1, 0), 14.6, 24.85, 25.7)
for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
    for a in (math.pi / 8, math.pi / 4, 3 * math.pi / 8):
        d = (sx * math.cos(a), sy * math.sin(a))
        box(bm, (sx * CX + d[0] * 30.4, sy * CY + d[1] * 30.4), (-d[1], d[0]), 0.18, d, 14.6, 24.85, 25.7)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
new_obj('Roof_Rafters', bm, '04_Roof', [beam])

# ---------------------------------------------------------------- roof, seen from above
# As on the aerial photo: a pale membrane roof with blocks of solar panels over
# the two long stands and the east end, dark bitumen without panels over the
# west end and three of the corners (the south-east corner stays pale).
for o in [o for o in D.objects if o.name.startswith('Roof_Panels_')]:
    remove(o)
MEMBRANE = (0.80, 0.81, 0.83)


def solar_tile():
    # one block of panels with half a walkway of bare roof around it
    t = np.zeros((96, 128, 3), 'f')
    t[:] = np.array(MEMBRANE, 'f')
    t[7:89, 7:121] = np.array((0.10, 0.13, 0.24), 'f')                 # frame lines
    for r in range(4):
        for c in range(6):
            y0, x0 = 8 + r * 20.25, 8 + c * 18.83
            t[int(y0) + 1:int(y0 + 20.25) - 1, int(x0) + 1:int(x0 + 18.83) - 1] = np.array((0.035, 0.05, 0.13), 'f') * rng.uniform(0.85, 1.2)
    return t


roof_white = principled('M_RoofMembrane', MEMBRANE, 0.7)
roof_dark = principled('M_RoofBitumen', (0.13, 0.13, 0.14), 0.95)
solar = image_material('M_SolarPanel', painted('lottopark_solar', solar_tile()), 0.3, 0.2)
R_IN, R_OUT = 16.0, 45.5
dark = SW | SE | NE | {E_SIDE}
bm = bmesh.new()
ring(bm, R_IN, ROOF_Z, R_OUT, ROOF_Z, 0, skip=dark)
ring(bm, R_IN, ROOF_Z, R_OUT, ROOF_Z, 1, only=dark)
z = ROOF_Z + 0.05
for sy in (1, -1):                                                     # long stands: two rows of nine blocks
    y0, y1 = sy * (CY + 18.5), sy * (CY + 43.5)
    face(bm, [(-CX, y0, z), (CX, y0, z), (CX, y1, z), (-CX, y1, z)], UP_V, 2, [(0, 0), (9, 0), (9, 2), (0, 2)])
x0, x1 = -(CX + 43.5), -(CX + 18.5)                                   # west end: three rows of five
face(bm, [(x0, -CY, z), (x1, -CY, z), (x1, CY, z), (x0, CY, z)], UP_V, 2, [(0, 0), (0, 3), (5, 3), (5, 0)])
new_obj('Roof_Top', bm, '04_Roof', [roof_white, roof_dark, solar])

# ================================================================ outside
# brick on the wall, raked concrete fins over every pillar
wall = D.objects['Exterior_BrickWall']
wall.data.materials.clear(); wall.data.materials.append(brick)
box_uv(wall, 2.4, 1.2)
bm = bmesh.new()
for o in [o for o in D.objects if o.name.startswith('Exterior_Pillar_')]:
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    p = sum(bb, Vector()) / 8
    out_v = Vector((p.x - max(-CX, min(CX, p.x)), p.y - max(-CY, min(CY, p.y)), 0)).normalized()
    side = Vector((-out_v.y, out_v.x, 0))
    base = Vector((p.x, p.y, 0))
    prof = [(0.0, 12.0), (0.0, 24.6), (3.4, 24.6), (3.4, 21.6)]
    for s in (-0.25, 0.25):
        face(bm, [base + out_v * r + side * s + Vector((0, 0, z)) for r, z in prof], side * s)
    for i in range(4):
        (r0, z0), (r1, z1) = prof[i], prof[(i + 1) % 4]
        face(bm, [base + out_v * r0 + side * -0.25 + Vector((0, 0, z0)), base + out_v * r0 + side * 0.25 + Vector((0, 0, z0)),
                  base + out_v * r1 + side * 0.25 + Vector((0, 0, z1)), base + out_v * r1 + side * -0.25 + Vector((0, 0, z1))])
new_obj('Exterior_Fins', bm, '06_Exterior', [D.materials['M_ConcretePillar']])

# entrance: it was hidden from renders, and its lettering faced the wall
for o in D.collections['09_Entrance'].objects:
    o.hide_render = False; o.hide_viewport = False
D.objects['Entrance_WText'].rotation_euler.z += math.pi
remove(D.objects['Entrance_LogoBG'])
tower = D.objects['Entrance_Tower_Brick']
tower.data.materials.clear(); tower.data.materials.append(brick)
box_uv(tower, 2.4, 1.2)

# vertical lettering, read bottom to top from the street (as on the real towers)
UPRIGHT = Matrix(((0, 1, 0), (0, 0, 1), (1, 0, 0))).to_4x4()
principled('M_EntLogo', (0.33, 0.12, 0.66), 0.5)
logo = D.objects['Entrance_LogoText']
logo.data.body = 'lotto Park'; logo.data.size = 2.5; logo.data.align_x = 'CENTER'
logo.matrix_world = Matrix.Translation((-13.0, 76.58, 10.5)) @ UPRIGHT
bm = bmesh.new()
box(bm, (-9.3, 76.55), (1, 0), 0.9, (0, 1), 0.06, 2.0, 19.0, 0)                 # dark strip beside it
box(bm, (29.5, 73.85), (1, 0), 3.5, (0, 1), 2.65, 0.0, 19.0, 1)                 # the second tower
box(bm, (29.5, 73.95), (1, 0), 3.7, (0, 1), 2.75, 19.0, 22.5, 0)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
t2 = new_obj('Entrance_Tower_2', bm, '09_Entrance', [D.materials['M_EntDark'], brick])
box_uv(t2, 2.4, 1.2)
rsca = wall_text('Entrance_RSCA', 'RSCA', (0, 0, 0), 0, 1.5, '09_Entrance', 'M_EntWhite')
rsca.matrix_world = Matrix.Translation((-9.75, 76.63, 12.0)) @ UPRIGHT

# ================================================================ screens
screen = principled('M_ScreenFace', (0.07, 0.04, 0.15), 0.5)
principled('M_ScreenWhiteText', (0.95, 0.93, 0.97), 0.5, (0.95, 0.93, 0.97), 1.0)
principled('M_ScreenDarkText', (0.95, 0.93, 0.97), 0.5, (0.95, 0.93, 0.97), 1.0)   # the score: was dark on dark
for n in ('LEDScreen_NorthWest', 'LEDScreen_SouthEast'):
    me = D.objects[n].data
    me.materials.clear(); me.materials.append(screen)
screen.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.13, 0.05, 0.28, 1)
for side in ('NorthWest', 'SouthEast'):
    c = D.objects['LEDScreen_' + side].matrix_world.translation.copy()
    sx, sy = (1 if c.x > 0 else -1), (1 if c.y > 0 else -1)
    off = Vector((c.x - sx * CX, c.y - sy * CY, 0))
    move = off.normalized() * (16.4 - off.length) + Vector((0, 0, -SCREEN_DROP))      # low enough for the game camera to see it
    for o in [o for o in D.objects if o.name.startswith('LEDScreen_' + side)]:
        o.location += move
    bpy.context.view_layer.update()
    for o in [o for o in D.objects if o.name.startswith('LEDScreen_' + side + '_Hanger')]:
        inv = o.matrix_world.inverted()
        ztop = max((o.matrix_world @ v.co).z for v in o.data.vertices)
        for v in o.data.vertices:                     # the hangers run up to the roof nose
            w = o.matrix_world @ v.co
            if w.z > ztop - 1e-4:
                w.z = 24.85
            v.co = inv @ w
# the screens show the live match (drawn by the game, game.screen.js): the
# fixed lettering goes, the faces get UVs across their width and height and
# their own material, and are exported as their own node 'StadiumScreens'
for o in [o for o in D.objects if o.type == 'FONT' and o.name.startswith('LEDScreen_')]:
    remove(o)
live = principled('M_LiveScreen', (1.0, 1.0, 1.0), 0.4, (0.13, 0.05, 0.28), 2.0)
SCREENS = []
bpy.context.view_layer.update()
for side in ('NorthWest', 'SouthEast'):
    o = D.objects['LEDScreen_' + side]
    me = o.data
    pts = [o.matrix_world @ v.co for v in me.vertices]
    c = sum(pts, Vector()) / len(pts)
    n = Vector((-c.x, -c.y, 0)).normalized()                  # towards the pitch
    right = (-n).cross(Vector((0, 0, 1))).normalized()        # as seen by someone facing the screen
    us = [(p - c).dot(right) for p in pts]; zs = [p.z for p in pts]
    uvl = me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap')
    for l in me.loops:
        p = pts[l.vertex_index]
        uvl.data[l.index].uv = (((p - c).dot(right) - min(us)) / (max(us) - min(us)), (p.z - min(zs)) / (max(zs) - min(zs)))
    me.materials.clear(); me.materials.append(live)
    print('SCREEN', side, 'width %.2f height %.2f' % (max(us) - min(us), max(zs) - min(zs)))
    SCREENS.append(o)
principled('M_EntLogo', (0.45, 0.20, 0.90), 0.5, (0.45, 0.20, 0.90), 2.0)

bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, copy=True)
print('SAVED', OUT_BLEND)

# ================================================================ game export
# (everything below only shapes the .glb; the saved .blend keeps the editable version)
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


# pitch: grass + lines baked into one texture (lines as loose geometry would
# flicker against the grass once the game presses the pitch flat)
PW_PX, PH_PX = 4096, 2744
pimg = D.images.new('lottopark_pitch', PW_PX, PH_PX)
target = grass.copy(); target.data = grass.data.copy(); target.name = 'Pitch'
D.collections['01_Pitch'].objects.link(target)
target.data.materials.clear(); target.data.materials.append(image_material('M_Pitch', pimg, 0.9))
grass.location.z = -0.01
bk.use_selected_to_active = True; bk.cage_extrusion = 0.1; bk.max_ray_distance = 0.5
select_only([grass, lines, surround, target], target)
bpy.ops.object.bake(type='DIFFUSE')
# The bake only tells us where the markings and the purple surround are; the
# turf itself is painted here, the way a real pitch looks from the stands:
# soft-edged mowing bands both ways, blade streaks along the mower's path,
# patchy colour, worn goal mouths, and chalk lines that are not pure white.
H, W = PH_PX, PW_PX
px = np.empty(W * H * 4, 'f'); pimg.pixels.foreach_get(px); px = px.reshape(H, W, 4)
rgb = px[..., :3]
line_m = np.clip((rgb.min(axis=2) - 0.45) / 0.4, 0, 1)
purple_m = (rgb[..., 2] > rgb[..., 1]) & (line_m < 0.3)
X = ((np.arange(W, dtype='f') + 0.5) / W * 2 - 1)[None, :] * FLOOR_X          # metres
Y = ((np.arange(H, dtype='f') + 0.5) / H * 2 - 1)[:, None] * FLOOR_Y


def vnoise(cy, cx):
    # smooth noise with features of about cy x cx pixels
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


bands_x = np.tanh(np.sin(np.pi * X / 5.5) * 6)                 # across the pitch: the strong mowing bands
bands_y = np.tanh(np.sin(np.pi * Y / 5.6) * 6)                 # along it: the faint second pass
fine = rng.normal(0, 1, (H, W)).astype('f')
shade = (1 + 0.105 * bands_x + 0.045 * bands_y
         + 0.055 * vnoise(420, 420) + 0.035 * vnoise(48, 48)   # slow patches, smaller mottling
         + 0.05 * vnoise(16, 1) * (0.6 + 0.4 * bands_x)        # blade streaks along the mower's path
         + 0.04 * fine)
grass_px = np.array((0.078, 0.185, 0.040), 'f') * shade[..., None]
grass_px[..., 0] *= 1 + 0.10 * vnoise(300, 300)                # some areas a little yellower
wear = sum(np.exp(-(((X - gx) / 3.2) ** 2 + (Y / 5.5) ** 2)) for gx in (-(hx - 2.8), hx - 2.8)) + 0.5 * np.exp(-((X / 1.6) ** 2 + (Y / 1.6) ** 2))
wear = (0.24 * wear * (0.55 + 0.45 * np.clip(vnoise(36, 36) + 0.5, 0, 1)))[..., None]
grass_px = grass_px * (1 - wear) + np.array((0.150, 0.190, 0.070), 'f') * wear
purple_px = np.array((0.150, 0.070, 0.280), 'f') * (1 + 0.05 * vnoise(64, 64) + 0.03 * fine)[..., None]
out_px = np.where(purple_m[..., None], purple_px, grass_px)
alpha = (np.clip(blur(line_m, 0.8), 0, 1) * np.clip(0.82 + 0.12 * vnoise(90, 90), 0.6, 1))[..., None]
out_px = np.clip(out_px * (1 - alpha) + np.array((0.78, 0.80, 0.76), 'f') * alpha, 0, 1)
del fine, shade, bands_x, bands_y, wear, purple_px, grass_px, alpha, rgb

# ---------------------------------------------------------------- night
# The match is played under floodlights, as on the photos from the stands. The
# light is worked out here once (Cycles) and stored in the model: in the pitch
# texture and in vertex colours. The game then draws the stadium unlit
# (catalog: look.baked, look.gain), so it looks the same on every device.
# Only the light is baked, not the colours: the textures keep their detail.


def light(coll, kind, loc, energy, color, target=None, size=60, blend=0.35, radius=0.3, area=None, rot=None):
    ld = D.lights.new('L', kind)
    ld.energy = energy; ld.color = color
    if kind == 'SPOT':
        ld.spot_size = math.radians(size); ld.spot_blend = blend; ld.shadow_soft_size = radius
    elif kind == 'POINT':
        ld.shadow_soft_size = radius
    elif kind == 'AREA':
        ld.shape = 'RECTANGLE'; ld.size, ld.size_y = area
    o = D.objects.new('Night_' + kind, ld)
    coll.objects.link(o)
    o.location = loc
    if target is not None:
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    if rot is not None:
        o.rotation_euler = rot
    return o


def setup_night():
    for o in [o for o in sc.objects if o.type == 'LIGHT']:
        remove(o)
    w = sc.world or D.worlds.new('World')
    sc.world = w
    w.use_nodes = True
    bgn = next((n for n in w.node_tree.nodes if n.type == 'BACKGROUND'), None)
    if bgn is None:
        bgn = w.node_tree.nodes.new('ShaderNodeBackground')
        outn = next((n for n in w.node_tree.nodes if n.type == 'OUTPUT_WORLD'), None) or w.node_tree.nodes.new('ShaderNodeOutputWorld')
        w.node_tree.links.new(bgn.outputs[0], outn.inputs['Surface'])
    for l in list(bgn.inputs['Color'].links):
        w.node_tree.links.remove(l)
    bgn.inputs['Color'].default_value = (0.0035, 0.006, 0.014, 1)      # the game's night sky
    bgn.inputs['Strength'].default_value = 1.0
    coll = D.collections.new('10_NightLights')
    sc.collection.children.link(coll)
    FLOOD = (1.0, 0.97, 0.92)
    # floodlights under the roof edge, aimed across the pitch
    for sy in (1, -1):
        for x in (-36, -31, -13, -8, 8, 13, 31, 36):
            light(coll, 'SPOT', (x, sy * (CY + LAMP_R), 24.5), NIGHT['roof'], FLOOD, target=(x * 0.55, -sy * 12, 0), size=75)
    for sx in (1, -1):
        for y in (-16, -11, 11, 16):
            light(coll, 'SPOT', (sx * (CX + LAMP_R), y, 24.5), NIGHT['roof'], FLOOD, target=(-sx * 24, y * 0.5, 0), size=75)
    # the four masts
    for sx in (1, -1):
        for sy in (1, -1):
            light(coll, 'SPOT', (sx * 80.0, sy * 61.5, 44.5), NIGHT['mast'], FLOOD, target=(sx * 12, sy * 6, 0), size=55)
    # the seats: down-lights under the roof
    for r in (30.0, 39.0):
        for x, y, a in ring_points(r, 9.0):
            light(coll, 'SPOT', (x, y, 24.7), NIGHT['stand'], (1.0, 0.96, 0.9), target=(x, y, 10), size=110, blend=0.6, radius=0.6)
    # blue-violet LEDs washing the underside of the roof (panels facing up)
    for r, drop in ((17.6, 0.8), (25.0, 1.6), (33.0, 1.6), (41.0, 1.6)):
        zs = 25.7 if r >= FASCIA_R + 4.2 else FASCIA_Z0 + (r - FASCIA_R) / 4.2 * (25.7 - FASCIA_Z0)
        for x, y, a in ring_points(r, 6.0):
            light(coll, 'AREA', (x, y, zs - drop), NIGHT['blue'] * (0.5 if drop < 1 else 1.0), (0.16, 0.12, 1.0), area=(5.5, 2.0), rot=(math.pi, 0, a + math.pi / 2))
    # violet uplights on the white corner walls
    for A, E in CORNER_WALLS:
        d = (E - A); n = Vector((-d.y, d.x, 0)).normalized()
        if n.dot(-diag) < 0:
            n = -n
        for f in (0.25, 0.7):
            q = A.lerp(E, f)
            light(coll, 'SPOT', (q + n * 2.5 + Vector((0, 0, LODGE_Z0 + 0.4)))[:], NIGHT['corner'], (0.50, 0.30, 1.0),
                  target=(q + Vector((0, 0, 19)))[:], size=75, blend=0.9, radius=1.5)
    light(coll, 'SPOT', (O - diag * 9 + Vector((0, 0, 4)))[:], NIGHT['corner'] * 0.6, (0.55, 0.38, 1.0),
          target=(O + Vector((0, 0, 22)))[:], size=40, blend=0.5)
    # outside: warm light on the facade
    for x, y, a in ring_points(51.5, 26.0):
        light(coll, 'SPOT', (x, y, 0.4), NIGHT['facade'], (1.0, 0.78, 0.5), target=(x - 5 * math.cos(a), y - 5 * math.sin(a), 13), size=75, blend=0.5)


NIGHT = dict(roof=14000, mast=45000, stand=900, blue=55, facade=2500, corner=2600)
setup_night()
for o in (grass, lines, surround, goals):          # no shadows of things the game does not show
    o.hide_render = True
sc.cycles.max_bounces = 4
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 0
sc.cycles.transmission_bounces = 0
sc.cycles.transparent_max_bounces = 2
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


# the light on the pitch, into a small light map
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
lmap = (lmap + np.roll(lmap, 1, 0) + np.roll(lmap, -1, 0) + np.roll(lmap, 1, 1) + np.roll(lmap, -1, 1)) / 5      # take the grain out
pm.node_tree.nodes.remove(lnode)
inner = lmap[int(LM_H * 0.2):int(LM_H * 0.8), int(LM_W * 0.2):int(LM_W * 0.8)]
lum = float((inner * np.array((0.2126, 0.7152, 0.0722), 'f')).sum(-1).mean())
EXPOSE = 0.8 / max(lum, 1e-6)          # the grass comes out at 1.6 x its own colour
print('PITCH LIGHT %.3f  EXPOSE %.4f' % (lum, EXPOSE))
out_px = np.clip(out_px * upsample(lmap, H, W) * (EXPOSE * GAIN), 0, 1)
px[..., :3] = np.where(out_px <= 0.0031308, 12.92 * out_px, 1.055 * out_px ** (1 / 2.4) - 0.055)
pimg.pixels.foreach_set(px.ravel())
del out_px, px
# noisy grass does not compress as PNG (20 MB): stored as JPEG instead
sc.render.image_settings.file_format = 'JPEG'; sc.render.image_settings.quality = 88
sc.view_settings.view_transform = 'Standard'
pimg.save_render(TEX_DIR + '/lottopark_pitch.jpg')
pjpg = D.images.load(TEX_DIR + '/lottopark_pitch.jpg')
target.data.materials.clear(); target.data.materials.append(image_material('M_Pitch', pjpg, 0.9))

bk.use_selected_to_active = False

# text -> mesh
dg = bpy.context.evaluated_depsgraph_get()
for o in [o for o in D.objects if o.type == 'FONT']:
    me = D.meshes.new_from_object(o.evaluated_get(dg))
    n = D.objects.new(o.name + '_mesh', me)
    n.matrix_world = o.matrix_world.copy()
    o.users_collection[0].objects.link(n)
    remove(o)
bpy.context.view_layer.update()

skip = ('Pitch_Grass', 'Pitch_Lines', 'Pitch_Surround', 'StadiumGoals', 'LEDScreen_NorthWest', 'LEDScreen_SouthEast', 'StadiumRibbonScore')
export = [o for o in sc.objects if o.type == 'MESH' and not o.name.startswith(skip)]
for o in export + [goals]:
    o.hide_set(False)
    if not o.data.uv_layers:
        o.data.uv_layers.new(name='UVMap')
    else:
        o.data.uv_layers[0].name = 'UVMap'
select_only(SCREENS, SCREENS[0])
bpy.ops.object.join()
screens = SCREENS[0]
screens.name = 'StadiumScreens'
select_only(export, target)
bpy.ops.object.join()
target.name = 'LottoPark'
bpy.context.view_layer.update()

# light on everything else, into vertex colours
me = target.data
me.color_attributes.active_color = me.color_attributes.new('Light', 'FLOAT_COLOR', 'POINT')      # per vertex: shared corners blend smoothly
bk.target = 'VERTEX_COLORS'
sc.cycles.samples = 192
select_only([target], target)
t0 = time.time()
bpy.ops.object.bake(type='DIFFUSE')
print('MODEL BAKE %.0fs' % (time.time() - t0))
fc = me.color_attributes['Light']
c = np.empty(len(fc.data) * 4, 'f'); fc.data.foreach_get('color', c); c = c.reshape(-1, 4)
c[:, :3] = np.clip(c[:, :3] * EXPOSE, 0, 1)
# what gives its own light (boards, lettering, lamps, lit windows) and the pitch
# (its light is in its texture) is drawn at its own colour
SELF_LIT = {'M_Pitch', 'M_LED', 'M_FasciaText', 'M_GlassLit', 'M_BuildPurple', 'M_FloodLight', 'M_ScreenFace',
            'M_ScreenWhiteText', 'M_ScreenDarkText', 'M_EntLogo', 'M_EntWhite'}
mi = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('material_index', mi)
ls = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_start', ls)
lt = np.empty(len(me.polygons), 'i'); me.polygons.foreach_get('loop_total', lt)
own = np.array([m is not None and m.name.split('.')[0] in SELF_LIT for m in me.materials])
order = np.argsort(ls)
loop_own = np.repeat(own[mi][order], lt[order])
lv = np.empty(len(me.loops), 'i'); me.loops.foreach_get('vertex_index', lv)
vert_own = np.zeros(len(me.vertices), bool); vert_own[lv[loop_own]] = True
lit_mask = ~vert_own
print('LIGHT p10/p50/p90', [round(float(v), 3) for v in np.percentile(c[lit_mask, :3].mean(1), (10, 50, 90))])
c[~lit_mask, :3] = 1.0 / GAIN
c[:, 3] = 1
me.color_attributes.new('Col', 'BYTE_COLOR', 'POINT').data.foreach_set('color', c.ravel())
me.color_attributes.remove(me.color_attributes['Light'])
ci = me.color_attributes.find('Col')
me.color_attributes.active_color_index = ci
me.color_attributes.render_color_index = ci
print('COLOR ATTRS', [(x.name, x.data_type) for x in me.color_attributes], ci)
gc = goals.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
gc.data.foreach_set('color', [0.45, 0.45, 0.45, 1.0] * len(gc.data))
goals.data.color_attributes.active_color = gc
goals.data.color_attributes.render_color_index = goals.data.color_attributes.find('Col')
scc = screens.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')     # self-lit: shown at its own colour
scc.data.foreach_set('color', [1.0 / GAIN, 1.0 / GAIN, 1.0 / GAIN, 1.0] * len(scc.data))
screens.data.color_attributes.active_color = scc
screens.data.color_attributes.render_color_index = screens.data.color_attributes.find('Col')
if not screens.data.uv_layers:
    screens.data.uv_layers.new(name='UVMap')
rsc = ribbon_score.data.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
rsc.data.foreach_set('color', [1.0 / GAIN, 1.0 / GAIN, 1.0 / GAIN, 1.0] * len(rsc.data))
ribbon_score.data.color_attributes.active_color = rsc
ribbon_score.data.color_attributes.render_color_index = ribbon_score.data.color_attributes.find('Col')
ribbon_score.data.uv_layers[0].name = 'UVMap'

# the light is in the model now: no emission in the file
for m in D.materials:
    if m.node_tree:
        for nd in m.node_tree.nodes:
            if nd.type == 'BSDF_PRINCIPLED':
                nd.inputs['Emission Strength'].default_value = 0.0

bb = [target.matrix_world @ Vector(c) for c in target.bound_box]
mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
s = 264 / max(mx[0] - mn[0], mx[1] - mn[1])
cx, cy = (mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2
print('BOUNDS', mn, mx)
print('PITCH x=%.2f z=%.2f w=%.2f l=%.2f y=%.2f' % (-cx * s, cy * s, PW * s, PL * s, -mn[2] * s))
print('TRIS', sum(len(p.vertices) - 2 for p in target.data.polygons), 'MATS', len(target.data.materials))

select_only([target, goals, screens, ribbon_score], target)
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
extra = {}
if 'export_vertex_color' in props: extra['export_vertex_color'] = 'ACTIVE'
if 'export_all_vertex_colors' in props: extra['export_all_vertex_colors'] = False
if 'export_active_vertex_color_when_no_material' in props: extra['export_active_vertex_color_when_no_material'] = True
print('VCOL', extra)
bpy.ops.export_scene.gltf(filepath=OUT_GLB, export_format='GLB', use_selection=True, export_apply=True, export_yup=True, **extra)
print('EXPORTED', OUT_GLB)
