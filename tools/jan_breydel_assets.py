# Makes the pictures tools/jan_breydel_build.py needs for the Jan Breydelstadion:
#   tools/jan_breydel/jan_breydel.png  JAN BREYDEL in light seats in the second ring
#   tools/jan_breydel/stadion.png      of the south stand, STADION under it: one
#                                      pixel a seat, one row a row
#   tools/jan_breydel/boards.png       the boards round the pitch (32 m a repeat)
#   tools/jan_breydel/band.png         the band on the front of the second ring
# No sponsors: the boards carry the clubs' and the city's own words.
#   python3 tools/jan_breydel_assets.py
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'jan_breydel')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)
ARIAL = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')


def seats(text, rows, name, gap=3, word_gap=9, wide=1.0):
    # plain bold capitals as on the photos of the south stand, each letter
    # `rows` rows tall; a seat is 0.5 m wide, a row 0.8 m deep and 0.58 m up
    # the slope, so a letter is drawn about twice as many seats wide as tall
    f = ImageFont.truetype(ARIAL if os.path.exists(ARIAL) else os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 400)

    def letter(ch):
        im = Image.new('L', (700, 600), 0)
        ImageDraw.Draw(im).text((50, 50), ch, font=f, fill=255)
        im = im.crop(im.getbbox())
        cols = max(2, round(im.width / im.height * rows * 1.55 * wide))
        a = np.asarray(im.resize((cols * 8, rows * 8), Image.LANCZOS), 'f') / 255.0
        return a.reshape(rows, 8, cols, 8).mean(axis=(1, 3)) > 0.42
    parts = []
    for w, word in enumerate(text.split(' ')):
        if w:
            parts.append(np.zeros((rows, word_gap), bool))
        for k, ch in enumerate(word):
            if k:
                parts.append(np.zeros((rows, gap), bool))
            parts.append(letter(ch))
    cells = np.hstack(parts)
    Image.fromarray((cells * 255).astype(np.uint8)).save(os.path.join(OUT, name))
    for r in range(rows):
        print(''.join('#' if v else '.' for v in cells[r]))
    print(name, cells.shape[1], 'seats wide')


# the boards: 128 px a metre, 0.9 m tall; panels of 8 m
PXM = 128
BLUE, BLACK, GREEN, WHITE = (0, 84, 166), (12, 12, 14), (0, 122, 72), (238, 238, 236)


def stripes(d, x0, w, h, a, b, n=10, slant=0.6):
    for k in range(-2, n + 2):
        xa = x0 + k * w / n
        d.polygon([(xa, 0), (xa + w / n / 2, 0), (xa + w / n / 2 - slant * h, h), (xa - slant * h, h)], fill=b)


def panel(im, x0, w, kind):
    d = ImageDraw.Draw(im)
    h = im.height
    big = ImageFont.truetype(BARLOW, int(h * 0.74))
    if kind == 'club':
        d.rectangle([x0, 0, x0 + w, h], fill=BLACK)
        stripes(d, x0, w * 0.22, h, BLACK, BLUE, 4)
        stripes(d, x0 + w * 0.78, w * 0.22, h, BLACK, BLUE, 4)
        txt, col = 'CLUB BRUGGE', WHITE
    elif kind == 'cercle':
        d.rectangle([x0, 0, x0 + w, h], fill=GREEN)
        d.rectangle([x0, 0, x0 + w, h * 0.12], fill=BLACK)
        d.rectangle([x0, h * 0.88, x0 + w, h], fill=BLACK)
        txt, col = 'CERCLE BRUGGE', WHITE
    elif kind == 'stadium':
        d.rectangle([x0, 0, x0 + w, h], fill=WHITE)
        d.rectangle([x0, h * 0.86, x0 + w, h], fill=BLUE)
        txt, col = 'JAN BREYDELSTADION', BLUE
    elif kind == 'city':
        d.rectangle([x0, 0, x0 + w, h], fill=BLUE)
        txt, col = 'BRUGGE', WHITE
    elif kind == 'motto':
        d.rectangle([x0, 0, x0 + w, h], fill=BLACK)
        txt, col = 'NO SWEAT NO GLORY', (120, 170, 235)
    else:
        d.rectangle([x0, 0, x0 + w, h], fill=WHITE)
        txt, col = 'OLYMPIAPARK', BLACK
    tw = d.textlength(txt, font=big)
    f = big if tw < w * 0.8 else ImageFont.truetype(BARLOW, int(h * 0.74 * w * 0.8 / tw))
    tw = d.textlength(txt, font=f)
    d.text((x0 + (w - tw) / 2, h * 0.5), txt, font=f, fill=col, anchor='lm')
    d.line([(x0, 0), (x0, h)], fill=(30, 30, 30), width=3)


def strip(name, kinds, panel_m, h_px):
    w = int(PXM * panel_m * len(kinds))
    im = Image.new('RGB', (w, h_px), WHITE)
    for k, kind in enumerate(kinds):
        panel(im, k * panel_m * PXM, panel_m * PXM, kind)
    im.save(os.path.join(OUT, name))
    print(name, im.size)


seats('JAN BREYDEL', 8, 'jan_breydel.png')
seats('STADION', 8, 'stadion.png', wide=1.08)
strip('boards.png', ['club', 'stadium', 'cercle', 'city'], 8.0, 115)
strip('band.png', ['club', 'motto', 'city', 'cercle', 'stadium', 'other'], 8.0, 128)


# the ground round the stadium from OpenStreetMap (tools/jan_breydel/osm.json,
# metres with the pitch on the axes: x north, y west; data © OpenStreetMap
# contributors, ODbL): 640 x 640 m, 2048 px, row 0 at y = +320
import json, math
G_HALF, G_PX = 320.0, 2048
osm = json.load(open(os.path.join(OUT, 'osm.json')))
S = G_PX / (2 * G_HALF)
T = lambda q: ((q[0] + G_HALF) * S, (G_HALF - q[1]) * S)
rng = np.random.default_rng(7)
noise = rng.normal(0, 1, (G_PX // 8, G_PX // 8, 1))
base = np.ones((G_PX, G_PX, 3)) * np.array((88, 112, 62))
base *= 1 + 0.06 * np.kron(noise, np.ones((8, 8, 1)))
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for g in osm['residential']:
    d.polygon([T(q) for q in g], fill=(96, 108, 70))
for g in osm['grass']:
    d.polygon([T(q) for q in g], fill=(84, 118, 60))
for g in osm['water']:
    d.polygon([T(q) for q in g], fill=(52, 70, 82))
# paving round the stadium and between it and the training pitches
st = [T(q) for q in osm['stadium']]
d.polygon(st, fill=(146, 144, 138))
d.line(st + [st[0]], fill=(146, 144, 138), width=int(30 * S))
w_ = [T(q) for q in osm['west']]
d.polygon(w_, fill=(146, 144, 138))
d.line(w_ + [w_[0]], fill=(146, 144, 138), width=int(26 * S))
for g in osm['parking']:
    d.polygon([T(q) for q in g], fill=(84, 84, 86))
for p in osm['pitches']:
    pts = p['pts'][:-1] if p['pts'][0] == p['pts'][-1] else p['pts']
    poly = [T(q) for q in pts]
    d.polygon(poly, fill=(66, 122, 50))
    if len(pts) == 4:
        # the markings: the outline, the halfway line and the centre circle
        a, b, c, e = [np.array(q) for q in pts]
        d.line(poly + [poly[0]], fill=(214, 220, 206), width=2)
        m1, m2 = (a + b) / 2, (c + e) / 2
        if np.linalg.norm(b - a) > np.linalg.norm(e - a):
            m1, m2 = (a + e) / 2, (b + c) / 2
        d.line([T(m1), T(m2)], fill=(214, 220, 206), width=2)
        cx, cy = T((a + c) / 2)
        r = 9.15 * S
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(214, 220, 206), width=2)
ROAD_W = {'secondary': 11, 'tertiary': 8, 'residential': 6.5, 'unclassified': 6, 'service': 4.5, 'pedestrian': 5,
          'footway': 2.4, 'cycleway': 2.4, 'path': 2.0, 'steps': 2.4}
for r in sorted(osm['roads'], key=lambda r: ROAD_W.get(r['type'], 3)):
    w = ROAD_W.get(r['type'], 3)
    col = (150, 146, 140) if r['type'] in ('footway', 'path', 'steps', 'pedestrian') else (66, 66, 68) if r['type'] != 'cycleway' else (110, 64, 56)
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=col, width=max(1, int(w * S)), joint='curve')
    for q in pts:
        rr = w * S / 2
        d.ellipse([q[0] - rr, q[1] - rr, q[0] + rr, q[1] + rr], fill=col)
for b in osm['buildings']:
    d.polygon([T(q) for q in b['pts']], fill=(58, 58, 60))
im.save(os.path.join(OUT, 'ground.png'))
print('ground.png', im.size)


# the four flags in the north-east corner, as on the photos of the Blue Army's
# end (left to right from the main stand): Brugge, Europe, Belgium, Flanders;
# 384 x 256 each
LION = [(18, 22), (13, 18), (21, 10), (31, 5), (42, 9), (48, 19), (56, 29), (62, 43), (66, 57), (70, 61),
        (78, 51), (83, 36), (81, 23), (86, 15), (93, 19), (90, 28), (86, 37), (80, 55), (72, 68), (71, 75),
        (77, 86), (83, 96), (72, 96), (65, 86), (59, 80), (55, 82), (52, 90), (49, 98), (37, 98), (42, 90),
        (45, 80), (43, 70), (40, 61), (33, 57), (21, 61), (11, 59), (13, 52), (25, 50), (33, 47), (35, 43),
        (27, 38), (15, 35), (7, 31), (9, 26), (21, 28), (31, 30), (29, 26), (21, 26)]


def lion(d, x0, y0, s, col, claws=None, crown=None):
    # a rampant lion facing the hoist (heraldic dexter), in a box of s x s
    P = lambda x, y: (x0 + x * s / 100, y0 + y * s / 100)
    d.polygon([P(x, y) for x, y in LION], fill=col)
    if claws:
        for (x, y), (dx, dy) in (((8, 29), (-4, 0)), ((12, 56), (-4, 0)), ((82, 96), (2, 2)), ((38, 98), (-2, 2))):
            d.polygon([P(x, y - 2), P(x + dx, y + dy), P(x, y + 2)], fill=claws)
        d.polygon([P(15, 21), P(8, 22), P(15, 23)], fill=claws)                      # the tongue
    if crown:
        d.polygon([P(24, 9), P(26, 1), P(29, 6), P(32, 0), P(35, 5), P(38, 0), P(40, 8)], fill=crown)


FW_, FH_ = 384, 256
im = Image.new('RGB', (FW_ * 5, FH_), (255, 255, 255))
d = ImageDraw.Draw(im)
# Brugge: eight stripes of white and red, a blue lion with a golden crown
for k in range(8):
    d.rectangle([0, k * FH_ / 8, FW_, (k + 1) * FH_ / 8], fill=(255, 255, 255) if k % 2 == 0 else (200, 16, 46))
lion(d, 92, 18, 220, (0, 56, 150), claws=(240, 190, 20), crown=(240, 190, 20))
# Europe: twelve gold stars on blue
x0 = FW_
d.rectangle([x0, 0, x0 + FW_, FH_], fill=(0, 51, 153))
for k in range(12):
    a = k / 12 * 2 * math.pi
    cx, cy = x0 + FW_ / 2 + math.sin(a) * 82, FH_ / 2 - math.cos(a) * 82
    pts = []
    for j in range(10):
        r = 13 if j % 2 == 0 else 5.2
        b = j / 10 * 2 * math.pi
        pts.append((cx + math.sin(b) * r, cy - math.cos(b) * r))
    d.polygon(pts, fill=(255, 204, 0))
# Belgium: black, yellow, red
x0 = 2 * FW_
for k, col in enumerate(((20, 20, 20), (253, 218, 36), (239, 51, 64))):
    d.rectangle([x0 + k * FW_ / 3, 0, x0 + (k + 1) * FW_ / 3, FH_], fill=col)
# Flanders: a black lion on yellow, red claws and tongue
x0 = 3 * FW_
d.rectangle([x0, 0, x0 + FW_, FH_], fill=(255, 221, 0))
lion(d, x0 + 80, 16, 224, (12, 12, 12), claws=(220, 30, 40))
# Club Brugge: blue and black stripes, the badge in the middle (the badge:
# media/hud/clubbrugge.png, CC BY 4.0, football-logos.cc via Wikimedia Commons)
x0 = 4 * FW_
for k in range(6):
    d.rectangle([x0, k * FH_ / 6, x0 + FW_, (k + 1) * FH_ / 6], fill=(0, 92, 175) if k % 2 == 0 else (15, 15, 18))
badge = Image.open(os.path.join(HERE, '..', 'media', 'hud', 'clubbrugge.png')).convert('RGBA').resize((190, 190), Image.LANCZOS)
im.paste(badge, (x0 + (FW_ - 190) // 2, (FH_ - 190) // 2), badge)
im.save(os.path.join(OUT, 'flags.png'))
print('flags.png', im.size)


# the main entrance of the west stand, as on the photo of it: the blue banner
# BLUVN GOAN over the doors, the signs WELKOM and FCB KAFFEE over them and the
# Jan Breydel plaque on the pier beside them; 1024 x 512
im = Image.new('RGB', (1024, 512), (40, 40, 44))
d = ImageDraw.Draw(im)
big = ImageFont.truetype(BARLOW, 150)
d.rectangle([0, 0, 1024, 200], fill=(58, 64, 76))
d.rectangle([0, 0, 600, 200], fill=(40, 150, 225))
d.text((300, 100), 'BLUVN', font=big, fill=(18, 40, 70), anchor='mm')
d.text((800, 100), 'GOAN', font=big, fill=(140, 205, 250), anchor='mm')
sm = ImageFont.truetype(BARLOW, 70)
for x0_, txt, bg, fg in ((0, 'FCB KAFFEE', (30, 34, 48), (230, 232, 236)), (512, 'WELKOM', (30, 34, 48), (230, 232, 236))):
    d.rectangle([x0_ + 6, 210, x0_ + 506, 330], fill=bg, outline=(200, 200, 205), width=4)
    d.text((x0_ + 256, 270), txt, font=sm, fill=fg, anchor='mm')
d.rectangle([0, 340, 512, 512], fill=(238, 238, 234))
d.text((256, 400), 'Jan', font=sm, fill=(20, 60, 140), anchor='mm')
d.text((256, 465), 'Breydel', font=sm, fill=(20, 60, 140), anchor='mm')
d.rectangle([512, 340, 1024, 512], fill=(40, 40, 44))
im.save(os.path.join(OUT, 'entrance.png'))
print('entrance.png', im.size)


# the dark cloth hung under the scoreboard: a sponsor's wave and word, five times
im = Image.new('RGB', (1024, 768), (30, 36, 58))
d = ImageDraw.Draw(im)
f = ImageFont.truetype(BARLOW, 110)
for k in range(5):
    y = 80 + k * 150
    d.arc([180, y - 40, 420, y + 40], 200, 340, fill=(120, 170, 200), width=14)
    d.arc([200, y - 20, 440, y + 60], 200, 340, fill=(90, 130, 170), width=12)
    d.text((470, y), 'BRUGGE', font=f, fill=(220, 225, 235), anchor='lm')
im.save(os.path.join(OUT, 'cloth.png'))
print('cloth.png', im.size)
