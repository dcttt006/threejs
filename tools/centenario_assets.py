# Makes the pictures tools/centenario_build.py needs for the Estadio Centenario:
#   tools/centenario/mural.png     the outside of the Olímpica and the ends:
#                                  the painted wall of big intersecting arcs and
#                                  triangles in aqua, teal, slate, blue and sand
#                                  (as on the photos of the outside), a band of
#                                  windows with deep reveals; 48 m a repeat
#   tools/centenario/america.png   the outside of the América: light blue
#                                  painted concrete, windows
#   tools/centenario/press.png     the front of the press boxes on the América:
#                                  ESTADIO CENTENARIO - 1930 in white over the
#                                  dark band, a row of windows
#   tools/centenario/plaque.png    the bronze plaque under the Torre de los
#                                  Homenajes (MONTEVIDEO 1930 campeonato mundial
#                                  de football URUGUAY CAMPEON), cut from the
#                                  user's photo img/16.png
#   tools/centenario/boards.png    the boards round the pitch, 0.9 m tall
#   tools/centenario/flag.png      the flag of Uruguay on the tower
#   tools/centenario/ground.png    Parque Batlle round the stadium from OpenStreetMap
# Also media/hud/boca.png and media/hud/millonarios.png for the scoreboard
# (img/bocalogo.png, img/milloslogo.png, trimmed).
# No sponsors: the boards carry the stadium's, the city's and the country's words.
#   python3 tools/centenario_assets.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'centenario')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)
SUP = '/System/Library/Fonts/Supplemental/'
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')
MONT = os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
COPPER = SUP + 'Copperplate.ttc' if os.path.exists(SUP + 'Copperplate.ttc') else MONT
rng = np.random.default_rng(1930)

# ---------------------------------------------------------------- the painted outside walls
# 40 px a metre; a repeat of 24 m, 26 m tall (the Olímpica's back is about
# 31 m over the street, the ends' a little less)
PXM = 40
MW, MH = 48 * PXM, 26 * PXM
PAL = [(120, 192, 182), (72, 152, 146), (108, 136, 152), (84, 112, 128), (172, 216, 202), (70, 112, 182),
       (42, 62, 112), (206, 186, 122), (216, 196, 160), (230, 226, 206), (96, 168, 160), (150, 190, 205)]


def mural(seed, w, h, bands):
    # half a repeat at random, then mirrored: the wall runs on without a seam.
    # Big circles and straight cuts across the wall, every piece its own colour
    r = np.random.default_rng(seed)
    weights = np.array([5, 5, 4, 4, 3, 1.5, 0.8, 1.2, 1.5, 1.5, 3, 2], 'f')
    weights /= weights.sum()
    hw = w // 2
    yy, xx = np.mgrid[0:h, 0:hw]
    code = np.zeros((h, hw), np.int64)
    for k in range(8):
        cx = r.uniform(-0.2, 1.2) * hw
        cy = r.uniform(-0.3, 1.3) * h
        rad = r.uniform(0.35, 0.95) * h
        code = code * 2 + (((xx - cx) ** 2 + (yy - cy) ** 2) < rad * rad)
    for k in range(4):
        x0, x1 = r.uniform(-0.2, 1.2) * hw, r.uniform(-0.2, 1.2) * hw
        code = code * 2 + (((x1 - x0) * (yy - 0) - (h - 0) * (xx - x0)) > 0)
    code = np.concatenate([code, code[:, ::-1]], axis=1)
    uniq = np.unique(code)
    a = np.zeros((h, w, 3), np.uint8)
    for u in uniq:
        a[code == u] = PAL[int(r.choice(len(PAL), p=weights))]
    edge = (np.abs(np.diff(code, axis=0, prepend=code[:1])) > 0) | (np.abs(np.diff(code, axis=1, prepend=code[:, -1:])) > 0)
    edge = np.asarray(Image.fromarray((edge * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    a[edge] = (a[edge] * 0.45).astype(np.uint8)
    im = Image.fromarray(a)
    # weathering
    n = rng.normal(0, 1, (h // 4, w // 4))
    nn = np.kron(n, np.ones((4, 4)))[:h, :w]
    a = np.asarray(im).astype('f') * (1 + 0.035 * nn[..., None])
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    # the windows: deep reveals, white frames, a mullion
    for y0 in bands:
        for x in range(int(1.2 * PXM), w, int(3.0 * PXM)):
            x0, x1 = x, x + int(1.9 * PXM)
            ya, yb = h - int((y0 + 1.1) * PXM), h - int(y0 * PXM)
            d.rectangle([x0 - 6, ya - 6, x1 + 6, yb + 8], fill=(200, 212, 206))
            d.rectangle([x0, ya, x1, yb], fill=(58, 70, 84))
            d.rectangle([x0 + 4, ya + 4, x1 - 4, yb - 4], fill=(150, 168, 182))
            d.line([((x0 + x1) // 2, ya), ((x0 + x1) // 2, yb)], fill=(40, 46, 52), width=4)
    return im


mural(11, MW, MH, [9.6, 14.2]).save(os.path.join(OUT, 'mural.png'))
mural(23, MW, MH, [10.4]).save(os.path.join(OUT, 'mural_ends.png'))
print('mural.png, mural_ends.png')

# the América: light blue paint, windows in pairs, joints of the panels (12 m, 20 m tall)
AW, AH = 12 * PXM, 20 * PXM
a = np.ones((AH, AW, 3), 'f') * np.array((112, 168, 214), 'f')
a *= (1 + 0.03 * rng.normal(0, 1, (AH, 1, 1))).astype('f')
im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for y0 in (6.0, 10.2):
    for x in (1.5, 4.5, 7.5, 10.5):
        x0, x1 = int((x - 0.8) * PXM), int((x + 0.8) * PXM)
        ya, yb = AH - int((y0 + 1.2) * PXM), AH - int(y0 * PXM)
        d.rectangle([x0, ya, x1, yb], fill=(54, 66, 80))
        d.rectangle([x0 + 4, ya + 4, x1 - 4, yb - 4], fill=(140, 160, 176))
for x in range(0, AW, 3 * PXM):
    d.line([(x, 0), (x, AH)], fill=(96, 148, 192), width=2)
d.rectangle([0, AH - int(4.2 * PXM), AW, AH], fill=(90, 132, 176))       # the ground floor a darker blue
im.save(os.path.join(OUT, 'america.png'))
print('america.png')

# ---------------------------------------------------------------- the press boxes' front (82 m, 3.6 m tall; 32 px a metre)
PW_, PH_ = 2624, 115
im = Image.new('RGB', (PW_, PH_), (26, 30, 36))
d = ImageDraw.Draw(im)
f = ImageFont.truetype(COPPER, 64)
txt = 'ESTADIO CENTENARIO - 1930'
tw = d.textlength(txt, font=f)
d.text(((PW_ - tw) / 2, 30), txt, font=f, fill=(238, 238, 232), anchor='lm')
for x in range(40, PW_, 120):
    if abs(x + 40 - PW_ / 2) < tw / 2 + 60:
        continue
    d.rectangle([x, 52, x + 80, 104], fill=(70, 86, 100))
    d.rectangle([x + 4, 56, x + 76, 100], fill=(110, 130, 146))
    d.line([(x + 40, 52), (x + 40, 104)], fill=(26, 30, 36), width=3)
d.rectangle([0, 0, PW_, 6], fill=(58, 62, 66))
im.save(os.path.join(OUT, 'press.png'))
print('press.png')

# ---------------------------------------------------------------- the plaque (the user's photo)
pl = Image.open(os.path.join(ROOT, 'img', '16.png')).convert('RGB').crop((40, 180, 545, 335))
pl = pl.resize((1024, int(1024 * pl.height / pl.width)), Image.LANCZOS)
pl.save(os.path.join(OUT, 'plaque.png'))
print('plaque.png', pl.size)

# ---------------------------------------------------------------- the boards
BPX = 128
BLUE, SKY, WHITE, NAVY, RED = (20, 70, 160), (110, 175, 225), (244, 244, 240), (18, 30, 70), (200, 30, 40)


def panel(full, x0, w, kind):
    h = full.height
    im = Image.new('RGB', (int(w), h), WHITE)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(BARLOW, int(h * 0.70))
    if kind == 'centenario':
        d.rectangle([0, 0, w, h], fill=NAVY); txt, col = 'ESTADIO CENTENARIO', WHITE
    elif kind == 'celeste':
        d.rectangle([0, 0, w, h], fill=SKY); txt, col = 'LA CELESTE', WHITE
    elif kind == 'montevideo':
        d.rectangle([0, 0, w, h], fill=WHITE); d.rectangle([0, h * 0.86, w, h], fill=BLUE); txt, col = 'MONTEVIDEO', BLUE
    elif kind == 'monumento':
        d.rectangle([0, 0, w, h], fill=BLUE); txt, col = 'MONUMENTO AL FÚTBOL MUNDIAL', WHITE
    elif kind == 'uruguay':
        d.rectangle([0, 0, w, h], fill=WHITE)
        for k in range(4):
            d.rectangle([0, h * (2 * k + 1) / 9, w, h * (2 * k + 2) / 9], fill=(60, 120, 210))
        txt, col = 'URUGUAY', NAVY
    else:
        d.rectangle([0, 0, w, h], fill=RED); txt, col = '1930', WHITE
    room = w * 0.86
    tw = d.textlength(txt, font=big)
    f = big if tw < room else ImageFont.truetype(BARLOW, int(h * 0.70 * room / tw))
    tw = d.textlength(txt, font=f)
    if kind == 'uruguay':
        d.rectangle([w / 2 - tw / 2 - 20, h * 0.12, w / 2 + tw / 2 + 20, h * 0.88], fill=WHITE)
    d.text((w / 2 - tw / 2, h * 0.52), txt, font=f, fill=col, anchor='lm')
    d.line([(0, 0), (0, h)], fill=(20, 20, 24), width=3)
    full.paste(im, (int(x0), 0))


kinds = ['centenario', 'celeste', 'montevideo', 'monumento', 'uruguay', 'year']
im = Image.new('RGB', (BPX * 8 * len(kinds), 115), WHITE)
for k, kind in enumerate(kinds):
    panel(im, k * 8 * BPX, 8 * BPX, kind)
im.save(os.path.join(OUT, 'boards.png'))
print('boards.png', im.size)

# ---------------------------------------------------------------- the flag of Uruguay (3:2)
FW, FH = 270, 180
im = Image.new('RGB', (FW, FH), WHITE)
d = ImageDraw.Draw(im)
for k in range(9):
    if k % 2:
        d.rectangle([0, FH * k / 9, FW, FH * (k + 1) / 9], fill=(0, 56, 168))
d.rectangle([0, 0, FW * 0.36, FH * 5 / 9], fill=WHITE)
cx, cy, r = FW * 0.18, FH * 5 / 18, FH * 0.11
for k in range(16):
    a0 = 2 * math.pi * k / 16
    d.polygon([(cx + math.cos(a0 - 0.12) * r, cy + math.sin(a0 - 0.12) * r), (cx + math.cos(a0) * r * 1.9, cy + math.sin(a0) * r * 1.9),
               (cx + math.cos(a0 + 0.12) * r, cy + math.sin(a0 + 0.12) * r)], fill=(252, 209, 22))
d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(252, 209, 22), outline=(125, 63, 22), width=2)
im.save(os.path.join(OUT, 'flag.png'))
print('flag.png')

# ---------------------------------------------------------------- the crests for the scoreboard
for src, dst in (('bocalogo.png', 'boca.png'), ('milloslogo.png', 'millonarios.png')):
    lg = Image.open(os.path.join(ROOT, 'img', src)).convert('RGBA')
    lg = lg.crop(lg.getbbox())
    k = 512 / max(lg.size)
    lg = lg.resize((int(lg.width * k), int(lg.height * k)), Image.LANCZOS)
    lg.save(os.path.join(ROOT, 'media', 'hud', dst))
    print('media/hud/' + dst, lg.size)

# ---------------------------------------------------------------- the ground round the stadium
# from OpenStreetMap (tools/centenario/osm.json, metres with the pitch on the
# axes: x towards the Colombes, y towards the América; data © OpenStreetMap
# contributors, ODbL): 640 x 640 m, 2048 px, row 0 at y = +320
G_HALF, G_PX = 320.0, 2048
osm = json.load(open(os.path.join(OUT, 'osm.json')))
S = G_PX / (2 * G_HALF)
T = lambda q: ((q[0] + G_HALF) * S, (G_HALF - q[1]) * S)
noise = rng.normal(0, 1, (G_PX // 8, G_PX // 8, 1))
base = np.ones((G_PX, G_PX, 3)) * np.array((92, 120, 64))           # Parque Batlle: grass under the trees
base *= 1 + 0.07 * np.kron(noise, np.ones((8, 8, 1)))
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for g in osm['residential']:
    d.polygon([T(q) for q in g], fill=(140, 134, 124))
for g in osm['grass'] + osm['park']:
    d.polygon([T(q) for q in g], fill=(88, 124, 60))
for g in osm.get('tracks', []):
    d.line([T(q) for q in g] + [T(g[0])], fill=(150, 110, 96), width=int(9 * S))
for p in osm['pitches']:
    d.polygon([T(q) for q in p['pts']], fill=(76, 128, 54) if p.get('surface') in (None, 'grass') else (150, 120, 90))
for g in osm['parking']:
    d.polygon([T(q) for q in g], fill=(96, 96, 98))
ROAD_W = {'primary': 14, 'primary_link': 7, 'secondary': 11, 'tertiary': 10, 'tertiary_link': 6, 'residential': 7, 'service': 5,
          'footway': 3.0, 'cycleway': 2.6, 'path': 2.4, 'steps': 3.0, 'pedestrian': 5}
for r in sorted(osm['roads'], key=lambda r: ROAD_W.get(r['type'], 3)):
    w = ROAD_W.get(r['type'], 3)
    col = (176, 170, 158) if r['type'] in ('footway', 'path', 'steps', 'pedestrian') else (120, 70, 60) if r['type'] == 'cycleway' else (70, 70, 74)
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=col, width=max(1, int(w * S)), joint='curve')
    for q in pts:
        rr = w * S / 2
        d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=col)
# the paved esplanade round the stadium
st = [T(q) for q in osm['stadium']]
d.line(st + [st[0]], fill=(168, 162, 150), width=int(16 * S))
d.polygon(st, fill=(150, 146, 138))
for b in osm['buildings']:
    d.polygon([T(q) for q in b['pts']], fill=(60, 60, 62))
im = im.filter(ImageFilter.GaussianBlur(0.6))
im.save(os.path.join(OUT, 'ground.png'))
print('ground.png', im.size)
