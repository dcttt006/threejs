# Makes the pictures tools/campin_build.py needs for El Campín (Bogotá):
#   tools/campin/letters.png  IDRD BOGOTA in the Tribuna Oriental's first
#                             ring: one letter for each section between the
#                             yellow stairways, 15 seats wide and 9 rows tall,
#                             one pixel a seat, one row a row (row 0 the
#                             top); 255 the letter's red seats, 0 the yellow
#   tools/campin/boards.png   the boards round the pitch, 0.9 m tall: the
#                             white boards with IDRD and BOGOTÁ in red as on
#                             the photos of 2025, EL CAMPÍN, ESTADIO NEMESIO
#                             CAMACHO, the colours of Colombia
#   tools/campin/ground.png   the ground round the stadium from OpenStreetMap:
#                             the brick-red plaza, Avenida NQS with the
#                             TransMilenio lanes and the canal beside it, the
#                             streets of Galerías and Nicolás de Federmán
# No sponsors: the boards carry the stadium's, the city's and the country's words.
#   python3 tools/campin_assets.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'campin')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)
SUP = '/System/Library/Fonts/Supplemental/'
ARIAL_B = SUP + 'Arial Bold.ttf' if os.path.exists(SUP + 'Arial Bold.ttf') else os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')
MONT = os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
rng = np.random.default_rng(1938)

# ---------------------------------------------------------------- the letters in the seats
# Square block letters as on the photo of the empty stadium (2019): strokes
# two to three seats wide, the letter filling most of its section
LW, LH = 15, 9
WORD = 'IDRDBOGOTA'


def letter_cells(ch):
    if ch == 'I':                                  # the I with its bars top and bottom, as in the seats
        out = np.zeros((LH, LW), bool)
        out[:2, 3:12] = True; out[-2:, 3:12] = True; out[:, 6:9] = True
        return out
    f = ImageFont.truetype(ARIAL_B, 400)
    im = Image.new('L', (700, 600), 0)
    ImageDraw.Draw(im).text((60, 40), ch, font=f, fill=255)
    im = im.crop(im.getbbox())
    cols = 5 if ch == 'I' else 11
    a = np.asarray(im.resize((cols * 8, LH * 8), Image.LANCZOS), 'f') / 255.0
    cells = a.reshape(LH, 8, cols, 8).mean(axis=(1, 3)) > 0.42
    out = np.zeros((LH, LW), bool)
    x0 = (LW - cols) // 2
    out[:, x0:x0 + cols] = cells
    return out


mask = np.zeros((LH, LW * len(WORD)), np.uint8)
for k, ch in enumerate(WORD):
    mask[:, k * LW:(k + 1) * LW] = np.where(letter_cells(ch), 255, 0)
Image.fromarray(mask).save(os.path.join(OUT, 'letters.png'))
for r in mask[:, :LW * 4]:
    print(''.join('#' if v else '.' for v in r))
print('letters.png', mask.shape)

# ---------------------------------------------------------------- the boards
BPX = 128
RED, WHITE, NAVY, YELLOW, BLUE = (206, 24, 36), (244, 244, 240), (20, 34, 78), (250, 204, 20), (0, 56, 147)


def panel(full, x0, w, kind):
    h = full.height
    im = Image.new('RGB', (int(w), h), WHITE)
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(BARLOW, int(h * 0.74))
    if kind == 'idrd':
        txt, col = 'IDRD', RED
    elif kind == 'bogota':
        txt, col = 'BOGOTÁ', RED
    elif kind == 'campin':
        d.rectangle([0, 0, w, h], fill=NAVY); txt, col = 'EL CAMPÍN', WHITE
    elif kind == 'nemesio':
        d.rectangle([0, 0, w, h], fill=YELLOW); txt, col = 'ESTADIO NEMESIO CAMACHO', NAVY
    else:
        d.rectangle([0, 0, w, h * 0.5], fill=YELLOW); d.rectangle([0, h * 0.5, w, h * 0.75], fill=BLUE); d.rectangle([0, h * 0.75, w, h], fill=RED)
        txt, col = 'COLOMBIA', None
    room = w * 0.84
    tw = d.textlength(txt, font=big)
    f = big if tw < room else ImageFont.truetype(BARLOW, int(h * 0.74 * room / tw))
    tw = d.textlength(txt, font=f)
    if col is None:
        d.rectangle([w / 2 - tw / 2 - 24, h * 0.1, w / 2 + tw / 2 + 24, h * 0.9], fill=WHITE)
        col = NAVY
    d.text((w / 2 - tw / 2, h * 0.53), txt, font=f, fill=col, anchor='lm')
    d.line([(0, 0), (0, h)], fill=(30, 30, 34), width=3)
    full.paste(im, (int(x0), 0))


kinds = ['idrd', 'bogota', 'campin', 'idrd', 'bogota', 'nemesio', 'colombia']
im = Image.new('RGB', (BPX * 8 * len(kinds), 115), WHITE)
for k, kind in enumerate(kinds):
    panel(im, k * 8 * BPX, 8 * BPX, kind)
im.save(os.path.join(OUT, 'boards.png'))
print('boards.png', im.size)

# ---------------------------------------------------------------- the ground round the stadium
# from OpenStreetMap (tools/campin/osm.json, metres with the pitch on the
# axes: x towards the north end, y towards the Occidental; data ©
# OpenStreetMap contributors, ODbL): 640 x 640 m, 2048 px, row 0 at y = +320
G_HALF, G_PX = 320.0, 2048
osm = json.load(open(os.path.join(OUT, 'osm.json')))
S = G_PX / (2 * G_HALF)
T = lambda q: ((q[0] + G_HALF) * S, (G_HALF - q[1]) * S)
noise = rng.normal(0, 1, (G_PX // 8, G_PX // 8, 1))
base = np.ones((G_PX, G_PX, 3)) * np.array((128, 118, 106))          # the town: pavements, yards, roofs between
base *= 1 + 0.06 * np.kron(noise, np.ones((8, 8, 1)))
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for g in osm['residential']:
    d.polygon([T(q) for q in g], fill=(132, 120, 108))
for g in osm['grass'] + osm['park']:
    d.polygon([T(q) for q in g], fill=(84, 112, 56))
for g in osm['parking']:
    d.polygon([T(q) for q in g], fill=(92, 92, 94))
for g in osm['water']:
    d.polygon([T(q) for q in g], fill=(70, 84, 76))
# the plaza round the stadium: brick-red paving with grey bands (the photos of the outside)
PLAZA = (136, 88, 68)
# the new stadium's site north-east of the old one: works begun in September 2026, bare earth
d.rectangle([T((75, -70))[0], T((75, -70))[1], T((300, -255))[0], T((300, -255))[1]], fill=(118, 96, 74))
for g in osm['squares']:
    d.polygon([T(q) for q in g], fill=PLAZA)
cx_ = osm['ways']['complex']
lay = Image.new('RGB', im.size, PLAZA)
dl = ImageDraw.Draw(lay)
for k in range(-12, 13):
    a = math.radians(k * 15)
    dl.line([T((0, 0)), T((300 * math.cos(a), 300 * math.sin(a)))], fill=(150, 146, 138), width=int(1.6 * S))
mk = Image.new('L', im.size, 0)
ImageDraw.Draw(mk).polygon([T(q) for q in cx_], fill=255)
im.paste(lay, (0, 0), mk)
d = ImageDraw.Draw(im)
d.polygon([T(q) for q in osm['ways']['stadium_outer']], fill=PLAZA)
ROAD_W = {'trunk': 24, 'trunk_link': 8, 'primary': 16, 'primary_link': 7, 'secondary': 12, 'tertiary': 10, 'tertiary_link': 6,
          'residential': 8, 'service': 5, 'unclassified': 7, 'living_street': 6,
          'footway': 3.0, 'cycleway': 2.6, 'path': 2.4, 'steps': 3.0, 'pedestrian': 5}
for r in sorted(osm['roads'], key=lambda r: ROAD_W.get(r['type'], 3)):
    w = ROAD_W.get(r['type'], 3)
    if r.get('layer') and r['layer'].startswith('-'):
        continue
    col = (176, 170, 158) if r['type'] in ('footway', 'path', 'steps', 'pedestrian') else (128, 54, 46) if r['type'] == 'cycleway' else (66, 66, 70)
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=col, width=max(1, int(w * S)), joint='curve')
    for q in pts:
        rr = w * S / 2
        d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=col)
for r in osm['busway']:
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=(150, 146, 136), width=int(7.5 * S), joint='curve')       # the TransMilenio lanes: pale concrete
for b in osm['buildings']:
    d.polygon([T(q) for q in b['pts']], fill=(70, 66, 64))
im = im.filter(ImageFilter.GaussianBlur(0.6))
im.save(os.path.join(OUT, 'ground.png'))
print('ground.png', im.size)
