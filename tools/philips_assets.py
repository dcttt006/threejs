# Makes the pictures tools/philips_build.py needs for the Philips Stadion:
#   tools/philips/philips.png  PHILIPS in the second ring of the north stand,
#   tools/philips/oost.png     OOST in the first ring of the east end, PSV in
#   tools/philips/psv.png      the first ring of the main stand: one pixel a
#                              seat, one row a row; 255 the letter, 110 its
#                              black shadow (one seat to the right, one row
#                              down, as on the photos), 0 a plain red seat
#   tools/philips/boards.png   the LED boards round the pitch, 0.9 m tall
#   tools/philips/band.png     the LED band on the front of the second ring
#   tools/philips/tunnel.png   the side of the players' tunnel: red, the
#                              crest and 1913 in big white figures
#   tools/philips/crest.png    the club's logo (img/psvlogo.svg, rasterised
#                              to tools/philips/psvlogo.png), also media/hud/psv.png
#   tools/philips/sign.png     'philips stadion' over the main entrance
#   tools/philips/facade.png   the white panels of the outside, a band of
#                              windows a floor
#   tools/philips/shops.png    the ground floor of the main stand: glass,
#                              red columns
#   tools/philips/flags.png    the flags on the main stand's roof terrace
#   tools/philips/ground.png   the ground round the stadium from OpenStreetMap
# No sponsors: the boards carry the club's, the stadium's and the city's own
# words.
#   python3 tools/philips_assets.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'philips')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)
SUP = '/System/Library/Fonts/Supplemental/'
ARIAL_B = SUP + 'Arial Bold.ttf' if os.path.exists(SUP + 'Arial Bold.ttf') else os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
ARIAL_BLK = SUP + 'Arial Black.ttf' if os.path.exists(SUP + 'Arial Black.ttf') else ARIAL_B
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')
MONT = os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
RED, WHITE, INK, GOLD = (218, 26, 36), (246, 244, 240), (20, 20, 24), (201, 162, 74)
rng = np.random.default_rng(1913)


# ---------------------------------------------------------------- the letters in the seats
def letter_cells(ch, rows, per_row, font, thin=1.0):
    # one letter as seats: `rows` rows tall; a row is per_row seats long up
    # the slope (its depth and rise over the 0.5 m seat), so a letter is drawn
    # that many seats wide for every row of its height
    f = ImageFont.truetype(font, 400)
    im = Image.new('L', (700, 600), 0)
    ImageDraw.Draw(im).text((60, 40), ch, font=f, fill=255)
    im = im.crop(im.getbbox())
    cols = max(3, round(im.width / im.height * rows * per_row * thin))
    a = np.asarray(im.resize((cols * 8, rows * 8), Image.LANCZOS), 'f') / 255.0
    return a.reshape(rows, 8, cols, 8).mean(axis=(1, 3)) > 0.45


def word_mask(letters, rows, per_row, font, cell, name, thin=1.0):
    # each letter centred in its own block of `cell` seats (the blocks are
    # the sections between the stairs); its shadow one seat to the right and
    # one row down; row 0 of the picture is the top row of the letters
    out = np.zeros((rows + 1, cell * len(letters) + 1), np.uint8)
    for k, ch in enumerate(letters):
        m = letter_cells(ch, rows, per_row, font, thin)
        c0 = k * cell + (cell - m.shape[1]) // 2
        sh = np.zeros_like(out, bool)
        sh[1:rows + 1, c0 + 1:c0 + 1 + m.shape[1]] |= m
        lt = np.zeros_like(out, bool)
        lt[0:rows, c0:c0 + m.shape[1]] |= m
        out[sh & ~lt & (out == 0)] = 110
        out[lt] = 255
    Image.fromarray(out).save(os.path.join(OUT, name))
    for r in range(out.shape[0]):
        print(''.join('#' if v == 255 else ('x' if v == 110 else '.') for v in out[r]))
    print(name, out.shape[1], 'seats wide,', out.shape[0], 'rows')


# the north stand's second ring: 18 rows 0.8 deep and 0.56 up (0.98 m up the
# slope, 1.95 seats); its sections between the stairs 13.49 m (27 seats)
word_mask('PHILIPS', 13, 1.95, ARIAL_B, 27, 'philips.png', thin=0.92)
# the east end's first ring, the block under its walkway: 0.8 deep, 0.42 up
# (0.90 m, 1.8 seats); its sections 11.98 m (24 seats)
word_mask('OOST', 9, 1.8, ARIAL_B, 24, 'oost.png')
# the main stand's first ring, behind the dugouts: sections 13.49 m
word_mask('PSV', 9, 1.8, ARIAL_B, 27, 'psv.png', thin=1.05)


# ---------------------------------------------------------------- the crest
def crest(size):
    S = size / 512.0
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size / 2
    R = 250 * S
    d.ellipse([c - R, c - R, c + R, c + R], fill=GOLD + (255,))
    d.ellipse([c - R + 5 * S, c - R + 5 * S, c + R - 5 * S, c + R - 5 * S], outline=(150, 112, 40, 255), width=max(1, int(3 * S)))
    # the laurel: leaves round the golden ring
    for k in range(48):
        a = 2 * math.pi * k / 48
        r0 = 222 * S
        for side in (-1, 1):
            p = (c + math.cos(a) * r0, c + math.sin(a) * r0)
            q = (c + math.cos(a + side * 0.05) * (r0 + 22 * S), c + math.sin(a + side * 0.05) * (r0 + 22 * S))
            d.line([p, q], fill=(150, 112, 40, 255), width=max(1, int(4 * S)))
    Ri = 212 * S
    d.ellipse([c - Ri, c - Ri, c + Ri, c + Ri], fill=WHITE + (255,))
    stripes = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ds = ImageDraw.Draw(stripes)
    sw = 2 * Ri / 9
    for k in range(9):
        if k % 2 == 0:
            ds.rectangle([c - Ri + k * sw, 0, c - Ri + (k + 1) * sw, size], fill=RED + (255,))
    mask = Image.new('L', (size, size), 0)
    ImageDraw.Draw(mask).ellipse([c - Ri, c - Ri, c + Ri, c + Ri], fill=255)
    im.paste(stripes, (0, 0), Image.composite(stripes.split()[3], Image.new('L', (size, size), 0), mask))
    d = ImageDraw.Draw(im)
    # the pole, golden, a ball on top
    px = c - 150 * S
    d.rectangle([px - 8 * S, c - 150 * S, px + 8 * S, c + 175 * S], fill=GOLD + (255,), outline=(120, 90, 30, 255))
    d.ellipse([px - 18 * S, c - 186 * S, px + 18 * S, c - 150 * S], fill=GOLD + (255,), outline=(120, 90, 30, 255))
    # the pennant: white, black edged, PSV on its broad end, red stripes in its tail
    top, bot, tip = (px + 8 * S, c - 112 * S), (px + 8 * S, c + 52 * S), (c + 205 * S, c - 30 * S)
    d.polygon([top, tip, bot], fill=WHITE + (255,), outline=INK + (255,))
    for k in range(4):
        t0, t1 = 0.60 + k * 0.1, 0.65 + k * 0.1
        a0 = (top[0] + (tip[0] - top[0]) * t0, top[1] + (tip[1] - top[1]) * t0)
        a1 = (top[0] + (tip[0] - top[0]) * t1, top[1] + (tip[1] - top[1]) * t1)
        b0 = (bot[0] + (tip[0] - bot[0]) * t0, bot[1] + (tip[1] - bot[1]) * t0)
        b1 = (bot[0] + (tip[0] - bot[0]) * t1, bot[1] + (tip[1] - bot[1]) * t1)
        d.polygon([a0, a1, b1, b0], fill=RED + (255,))
    d.polygon([top, tip, bot], outline=INK + (255,), width=max(1, int(5 * S)))
    f = ImageFont.truetype(ARIAL_BLK, int(96 * S))
    d.text((px + 118 * S, c - 32 * S), 'PSV', font=f, fill=INK + (255,), anchor='mm')
    return im


# the club's own logo (img/psvlogo.svg, turned into tools/philips/psvlogo.png
# in a browser): it replaces the drawn crest everywhere
LOGO = Image.open(os.path.join(OUT, 'psvlogo.png')).convert('RGBA')
LOGO = LOGO.crop(LOGO.getbbox())


def crest(size):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    k = size / max(LOGO.size)
    lg = LOGO.resize((max(1, int(LOGO.width * k)), max(1, int(LOGO.height * k))), Image.LANCZOS)
    im.paste(lg, ((size - lg.width) // 2, (size - lg.height) // 2), lg)
    return im


crest(512).save(os.path.join(OUT, 'crest.png'))
crest(512).save(os.path.join(ROOT, 'media', 'hud', 'psv.png'))
print('crest.png, media/hud/psv.png')


# ---------------------------------------------------------------- the boards and the band
PXM = 128


def stripes(d, x0, w, h, a, b, n=10, slant=0.6):
    for k in range(-2, n + 2):
        xa = x0 + k * w / n
        d.polygon([(xa, 0), (xa + w / n / 2, 0), (xa + w / n / 2 - slant * h, h), (xa - slant * h, h)], fill=b)


CREST_SMALL = crest(256)


def panel(full, x0, w, kind):
    # drawn on its own piece, then put in its place: nothing runs over into the next
    h = full.height
    im = Image.new('RGB', (int(w), h), WHITE)
    full_x0, x0 = x0, 0
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(BARLOW, int(h * 0.70))
    logo = None
    if kind == 'foundation':
        d.rectangle([x0, 0, x0 + w, h], fill=RED)
        txt, col, logo = 'PSV FOUNDATION SUPPORTS', WHITE, 'left'
    elif kind == 'stadium':
        d.rectangle([x0, 0, x0 + w, h], fill=WHITE)
        d.rectangle([x0, h * 0.86, x0 + w, h], fill=RED)
        txt, col = 'PHILIPS STADION', RED
    elif kind == 'psv':
        d.rectangle([x0, 0, x0 + w, h], fill=RED)
        stripes(d, x0, w * 0.2, h, RED, WHITE, 4)
        stripes(d, x0 + w * 0.8, w * 0.2, h, RED, WHITE, 4)
        d.rectangle([x0 + w * 0.2, 0, x0 + w * 0.8, h], fill=RED)
        txt, col = 'PSV EINDHOVEN', WHITE
    elif kind == 'city':
        d.rectangle([x0, 0, x0 + w, h], fill=INK)
        txt, col = 'EINDHOVEN', WHITE
    elif kind == 'year':
        d.rectangle([x0, 0, x0 + w, h], fill=WHITE)
        txt, col, logo = 'SINDS 1913', RED, 'left'
    else:
        d.rectangle([x0, 0, x0 + w, h], fill=RED)
        txt, col = 'BOERENBENDE', WHITE
    room = w * (0.72 if logo else 0.84)
    tw = d.textlength(txt, font=big)
    f = big if tw < room else ImageFont.truetype(BARLOW, int(h * 0.70 * room / tw))
    tw = d.textlength(txt, font=f)
    cx = x0 + w / 2 + (h * 0.5 if logo else 0)
    d.text((cx - tw / 2, h * 0.52), txt, font=f, fill=col, anchor='lm')
    if logo:
        cr = CREST_SMALL.resize((int(h * 0.82), int(h * 0.82)), Image.LANCZOS)
        im.paste(cr, (int(cx - tw / 2 - h * 0.98), int(h * 0.09)), cr)
    d.line([(0, 0), (0, h)], fill=(40, 10, 12), width=3)
    full.paste(im, (int(full_x0), 0))


def strip(name, kinds, panel_m, h_px):
    w = int(PXM * panel_m * len(kinds))
    im = Image.new('RGB', (w, h_px), WHITE)
    for k, kind in enumerate(kinds):
        panel(im, k * panel_m * PXM, panel_m * PXM, kind)
    im.save(os.path.join(OUT, name))
    print(name, im.size)


strip('boards.png', ['foundation', 'stadium', 'psv', 'foundation', 'city', 'year'], 8.0, 115)
strip('band.png', ['foundation', 'psv', 'foundation', 'stadium', 'foundation', 'other'], 8.0, 115)


# ---------------------------------------------------------------- the tunnel's sides (6 x 2.6 m, 128 px a metre)
TW, TH = 768, 333
im = Image.new('RGB', (TW, TH), RED)
d = ImageDraw.Draw(im)
for k in range(5):                                  # faint stars along the bottom, as on the photo
    x = 300 + k * 90
    d.regular_polygon((x, TH - 40, 14), 5, fill=(178, 18, 26))
f = ImageFont.truetype(ARIAL_BLK, 200)
while d.textlength('1913', font=f) > 430:
    f = ImageFont.truetype(ARIAL_BLK, f.size - 6)
for dx, dy, col in ((9, 9, (52, 10, 14)), (0, 0, (250, 240, 226))):
    d.text((316 + dx, TH * 0.52 + dy), '1913', font=f, fill=col, anchor='lm')
d.polygon([(0, 0), (250, 0), (292, 82), (250, 164), (0, 164)], fill=WHITE)
cr = crest(156)
im.paste(cr, (62, 4), cr)
im.save(os.path.join(OUT, 'tunnel.png'))
print('tunnel.png', im.size)


# ---------------------------------------------------------------- the sign over the main entrance (16 x 2.2 m)
SW_, SH_ = 1024, 141
im = Image.new('RGBA', (SW_, SH_), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
f = ImageFont.truetype(SUP + 'Arial Rounded Bold.ttf' if os.path.exists(SUP + 'Arial Rounded Bold.ttf') else MONT, 104)
navy = (22, 40, 82, 255)
d.ellipse([12, 18, 112, 118], outline=navy, width=10)
for a in (0.3, 2.4, 4.4):
    d.line([(62 + 50 * math.cos(a), 68 + 50 * math.sin(a)), (62 + 18 * math.cos(a + 1), 68 + 18 * math.sin(a + 1))], fill=navy, width=9)
d.text((134, 70), 'philips stadion', font=f, fill=navy, anchor='lm')
im.save(os.path.join(OUT, 'sign.png'))
print('sign.png', im.size)


# ---------------------------------------------------------------- the outside: white panels, windows
# facade.png: 12 m wide, 3.6 m a floor, 64 px a metre: a band of dark windows
# with white mullions on each floor over a band of white panels
FW, FH = 768, 230
a = np.ones((FH, FW, 3), 'f') * np.array((228, 228, 224), 'f')
a *= (1 + 0.02 * rng.normal(0, 1, (FH, 1, 1))).astype('f')
y0, y1 = int(0.30 * FH), int(0.80 * FH)
a[y0:y1] = np.array((44, 56, 68), 'f') * np.linspace(1.25, 0.8, y1 - y0)[:, None, None]
for x in range(0, FW, 96):
    a[y0:y1, x:x + 5] = (226, 226, 222)
a[y0 - 3:y0] = (180, 180, 178); a[y1:y1 + 3] = (200, 200, 198)
for x in range(0, FW, 192):                          # the joints of the panels
    a[:y0, x:x + 2] *= 0.85; a[y1:, x:x + 2] *= 0.85
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'facade.png'))
# shops.png: the ground floor, 12 m wide, 4.2 m tall: glass with doors, red columns, a dark fascia
SW2, SH2 = 768, 269
im = Image.new('RGB', (SW2, SH2), (40, 46, 52))
d = ImageDraw.Draw(im)
d.rectangle([0, 0, SW2, 46], fill=(28, 28, 32))
for x in range(0, SW2, 192):
    d.rectangle([x, 46, x + 26, SH2], fill=RED)
    for k in range(1, 4):
        xx = x + 26 + k * 41
        d.line([(xx, 60), (xx, SH2)], fill=(150, 150, 150), width=3)
    d.rectangle([x + 70, 120, x + 150, SH2], fill=(70, 80, 88))
d.rectangle([0, 46, SW2, 56], fill=(200, 200, 198))
im.save(os.path.join(OUT, 'shops.png'))
print('facade.png, shops.png')


# ---------------------------------------------------------------- the flags (five in a row, 3 x 2 m each)
FLW, FLH = 128, 86
im = Image.new('RGB', (FLW * 5, FLH), WHITE)
d = ImageDraw.Draw(im)
for k in range(5):
    x0 = k * FLW
    if k in (0, 2, 4):                                   # PSV: red and white stripes
        for s in range(8):
            if s % 2 == 0:
                d.rectangle([x0 + s * FLW / 8, 0, x0 + (s + 1) * FLW / 8, FLH], fill=RED)
    elif k == 1:                                         # the Netherlands
        d.rectangle([x0, 0, x0 + FLW, FLH / 3], fill=(174, 28, 40))
        d.rectangle([x0, FLH * 2 / 3, x0 + FLW, FLH], fill=(33, 70, 139))
    else:                                                # Eindhoven: red and white halves
        d.rectangle([x0, 0, x0 + FLW / 2, FLH], fill=RED)
im.save(os.path.join(OUT, 'flags.png'))
print('flags.png', im.size)


# ---------------------------------------------------------------- the ground round the stadium
# from OpenStreetMap (tools/philips/osm.json, metres with the pitch on the
# axes: x towards the west end, y towards the main stand; data ©
# OpenStreetMap contributors, ODbL): 640 x 640 m, 2048 px, row 0 at y = +320
G_HALF, G_PX = 320.0, 2048
osm = json.load(open(os.path.join(OUT, 'osm.json')))
S = G_PX / (2 * G_HALF)
T = lambda q: ((q[0] + G_HALF) * S, (G_HALF - q[1]) * S)
noise = rng.normal(0, 1, (G_PX // 8, G_PX // 8, 1))
base = np.ones((G_PX, G_PX, 3)) * np.array((138, 134, 126))       # the town: pavements and yards
base *= 1 + 0.05 * np.kron(noise, np.ones((8, 8, 1)))
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for g in osm['residential']:
    d.polygon([T(q) for q in g], fill=(122, 126, 98))            # gardens between the houses
for g in osm['grass'] + osm['park']:
    d.polygon([T(q) for q in g], fill=(86, 116, 58))
for p in osm['pitches']:
    pts = p['pts']
    d.polygon([T(q) for q in pts], fill=(70, 120, 52) if p.get('surface') in (None, 'grass') else (120, 70, 60))
for g in osm['parking']:
    d.polygon([T(q) for q in g], fill=(86, 86, 88))
# the railway: a bed of ballast under the tracks, the rails as dark lines
for r in osm['rail']:
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=(112, 100, 88), width=max(1, int(4.2 * S)), joint='curve')
for r in osm['rail']:
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=(64, 58, 54), width=max(1, int(1.6 * S)), joint='curve')
for g in osm['platforms']:
    d.polygon([T(q) for q in g], fill=(160, 158, 150))
ROAD_W = {'primary': 12, 'secondary': 11, 'tertiary': 8, 'residential': 6.0, 'unclassified': 6, 'service': 4.5, 'living_street': 5,
          'pedestrian': 5, 'footway': 2.4, 'cycleway': 2.6, 'path': 2.0, 'steps': 2.4, 'busway': 7}
for r in sorted(osm['roads'], key=lambda r: ROAD_W.get(r['type'], 3)):
    if r.get('tunnel'):
        continue
    w = ROAD_W.get(r['type'], 3)
    col = (164, 160, 152) if r['type'] in ('footway', 'path', 'steps', 'pedestrian') else (118, 62, 56) if r['type'] == 'cycleway' else (66, 66, 70)
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=col, width=max(1, int(w * S)), joint='curve')
    for q in pts:
        rr = w * S / 2
        d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=col)
# the stadium's own apron: light paving right round it
st = [T(q) for q in osm['stadium']]
d.line(st + [st[0]], fill=(170, 166, 158), width=int(9 * S))
d.polygon(st, fill=(150, 148, 142))
for b in osm['buildings']:
    d.polygon([T(q) for q in b['pts']], fill=(58, 58, 60))
im = im.filter(ImageFilter.GaussianBlur(0.6))
im.save(os.path.join(OUT, 'ground.png'))
print('ground.png', im.size)
