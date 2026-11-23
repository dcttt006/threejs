# Makes the pictures tools/marien_build.py needs for the Stade Joseph Marien:
#   tools/marien/facade.png   the street front of the main stand (Albert
#                             Callewaert, 1926), 101.2 x 13.6 m: red brick,
#                             the stone bays with their reliefs of players
#                             and the middle with UNION SAINT-GILLOISE
#                             (tools/marien/bay.jpg and centre.jpg are cut from
#                             photos by karmakolle, CC0, Wikimedia Commons)
#   tools/marien/endface.png  the end towers of the main stand: brick, the
#                             club's crest (tools/marien/usg.png, CC BY 4.0)
#   tools/marien/boards.png   the boards round the pitch (32 m a repeat)
#   tools/marien/banner.png   the club's band over the top of the standing
#                             terrace on the park side, 68 x 2.6 m, as on the
#                             photos: yellow, royal blue, yellow, players
#                             running and heading, be union be.brussels, the
#                             crest and ROYALE UNION SAINT-GILLOISE
#   tools/marien/hey.png      the cloth laid over the bank between that
#                             terrace and the south-west end (Let's go hey!),
#                             9.2 m wide, 18.9 m up the slope: drawn twice as
#                             tall as it is meant to look, so that seen from
#                             the pitch, foreshortened, it reads as it does
#   tools/marien/topboards.png the boards along the fences over both ends
#   tools/marien/ground.png   the ground round the stadium from OpenStreetMap
# Also media/hud/union.png (the crest for the scoreboard, game.screen.js).
#   python3 tools/marien_assets.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'marien')
FONTS = os.path.join(HERE, 'fonts')
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')
MONT = os.path.join(FONTS, 'Montserrat-ExtraBold.ttf')
ROUND = '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf'      # macOS; the cloth's 'hey!'
if not os.path.exists(ROUND):
    ROUND = os.path.join(FONTS, 'Comfortaa-Bold.ttf')
rng = np.random.default_rng(1926)

# ---------------------------------------------------------------- the facade
FW_M, FH_M, PXM = 101.2, 13.6, 40          # metres, pixels a metre
W, H = int(FW_M * PXM), int(FH_M * PXM)
zpx = lambda z: int(H - z * PXM)            # height (m) to row
xpx = lambda x: int((x + 50.9) * PXM)       # plan x (m) to column, 0 at the west end... (u runs with x)
BRICK = np.array((124, 58, 42), 'f')
STONE = (196, 182, 156)


def brick_field(w, h):
    # red brick in stretcher bond, the joints a little lighter, each brick its own shade
    t = np.ones((h, w, 3), 'f') * BRICK
    bh, bw = 3, 9                                            # 7.5 x 22 cm at 40 px/m
    shade = rng.normal(0, 0.09, (h // bh + 2, w // bw + 3))
    for r in range(h):
        row = r // bh
        off = (bw // 2) if row % 2 else 0
        cols = (np.arange(w) + off) // bw
        t[r] *= (1 + shade[row, cols])[:, None]
        if r % bh == 0:
            t[r] = (150, 132, 118)
    t[:, ::bw] = t[:, ::bw] * 0.5 + np.array((150, 132, 118)) * 0.5
    return t


img = Image.fromarray(np.clip(brick_field(W, H), 0, 255).astype(np.uint8))
d = ImageDraw.Draw(img)
# the stone plinth along the bottom, blocks of 1 m, and the coping along the top
d.rectangle([0, zpx(2.6), W, H], fill=STONE)
for z in np.arange(0, 2.6, 0.55):
    d.line([(0, zpx(z)), (W, zpx(z))], fill=(160, 148, 126), width=1)
for x in range(0, W, PXM):
    for k, z in enumerate(np.arange(0, 2.6, 0.55)):
        xx = x + (PXM // 2 if k % 2 else 0)
        d.line([(xx, zpx(z)), (xx, zpx(min(2.6, z + 0.55)))], fill=(160, 148, 126), width=1)
d.rectangle([0, 0, W, zpx(13.0)], fill=STONE)
d.rectangle([0, zpx(11.4), W, zpx(11.0)], fill=STONE)        # a stone band under the basket-weave panels
# the basket-weave brick panels high up between the bays
for x0 in range(0, W, 8):
    for y0 in range(zpx(12.9), zpx(11.45), 8):
        if ((x0 // 8) + (y0 // 8)) % 2:
            d.line([(x0, y0 + 2), (x0 + 7, y0 + 2)], fill=(100, 46, 34)); d.line([(x0, y0 + 5), (x0 + 7, y0 + 5)], fill=(100, 46, 34))
        else:
            d.line([(x0 + 2, y0), (x0 + 2, y0 + 7)], fill=(100, 46, 34)); d.line([(x0 + 5, y0), (x0 + 5, y0 + 7)], fill=(100, 46, 34))
bay = Image.open(os.path.join(OUT, 'bay.jpg')).convert('RGB')
centre = Image.open(os.path.join(OUT, 'centre.jpg')).convert('RGB')
_c = np.asarray(centre).astype('f')
_sky = (_c[..., 2] > _c[..., 0] + 25) & (_c[..., 2] > 120)                 # the sky round the arch: stone instead
_c[_sky] = STONE
centre = Image.fromarray(_c.astype(np.uint8))
BAYS = [-41.5, -31.0, -20.5, -10.0, 10.0, 20.5, 31.0, 41.5]
DOORS = {-41.5: '6', -20.5: '5', 20.5: '4', 41.5: '3'}
for bx in BAYS:
    # the stone bay: from the plinth to the band, the photo of one, 4.6 m wide
    bw_, bh_ = int(4.6 * PXM), int((11.4 - 1.6) * PXM)
    img.paste(bay.resize((bw_, bh_), Image.LANCZOS), (xpx(bx) - bw_ // 2, zpx(11.4)))
    # its rounded stone top over the band
    d.pieslice([xpx(bx) - bw_ // 2, zpx(13.6), xpx(bx) + bw_ // 2, zpx(12.2)], 180, 360, fill=STONE)
    if bx in DOORS:
        # a blue door beside it, its number on a little plate
        dx = xpx(bx + 3.6)
        d.rectangle([dx - 46, zpx(2.5), dx + 46, zpx(0)], fill=(40, 90, 170))
        d.line([(dx, zpx(2.5)), (dx, zpx(0))], fill=(20, 50, 110), width=3)
        d.rectangle([dx - 40, zpx(2.5) + 8, dx + 40, zpx(2.5) + 16], fill=(70, 120, 200))
        d.rectangle([dx + 56, zpx(1.8), dx + 72, zpx(1.4)], fill=(30, 30, 34))
        d.text((dx + 64, zpx(1.6)), DOORS[bx], fill=(240, 240, 240), anchor='mm')
# the middle: the photo of it (UNION SAINT-GILLOISE, the relief, the window,
# the blue door's top), 11 m wide, from 2.6 m to the top
cw, ch = int(11.0 * PXM), int((FH_M - 2.4) * PXM)
img.paste(centre.resize((cw, ch), Image.LANCZOS), (xpx(0.0) - cw // 2, zpx(FH_M)))
d.rectangle([xpx(-1.3), zpx(2.6), xpx(1.3), zpx(0)], fill=(44, 96, 176))          # its blue double door
d.line([(xpx(0), zpx(2.6)), (xpx(0), zpx(0))], fill=(20, 50, 110), width=3)
# CLUB HOUSE at the east end
d.rectangle([xpx(46.0), zpx(3.3), xpx(49.4), zpx(2.75)], fill=(240, 240, 238))
d.text(((xpx(46.0) + xpx(49.4)) / 2, (zpx(3.3) + zpx(2.75)) / 2), 'CLUB HOUSE', fill=(20, 50, 130),
       font=ImageFont.truetype(BARLOW, 18), anchor='mm')
d.rectangle([xpx(46.6), zpx(2.6), xpx(48.8), zpx(0)], fill=(96, 70, 48))
img.save(os.path.join(OUT, 'facade.png'))
print('facade.png', img.size)

# ---------------------------------------------------------------- the end towers (10 x 15 m)
EW, EH = 400, 600
ef = Image.fromarray(np.clip(brick_field(EW, EH), 0, 255).astype(np.uint8))
d = ImageDraw.Draw(ef)
d.rectangle([0, EH - int(2.6 * 40), EW, EH], fill=STONE)
d.rectangle([0, 0, EW, int(1.0 * 40)], fill=STONE)
d.rectangle([0, int(2.2 * 40), EW, int(2.6 * 40)], fill=STONE)
crest = Image.open(os.path.join(OUT, 'usg.png')).convert('RGBA')
k = 150 / crest.width
crest = crest.resize((int(crest.width * k * 1.4), int(crest.height * k * 1.4)), Image.LANCZOS)
ef.paste(crest, (EW - crest.width - 50, int(4.5 * 40)), crest)
d.rectangle([60, EH - int(2.6 * 40) - 70, 160, EH - int(2.6 * 40) - 20], fill=(250, 250, 250))
d.text((110, EH - int(2.6 * 40) - 45), 'CLUB HOUSE', fill=(20, 50, 130), font=ImageFont.truetype(BARLOW, 16), anchor='mm')
d.rectangle([150, EH - int(2.5 * 40), 250, EH], fill=(40, 90, 170))
ef.save(os.path.join(OUT, 'endface.png'))
print('endface.png', ef.size)

# ---------------------------------------------------------------- the boards (128 px a metre, 0.9 m tall, panels of 8 m)
YELLOW, BLUE, WHITE, NAVY = (250, 205, 20), (16, 60, 170), (245, 245, 242), (10, 26, 80)
big = lambda h: ImageFont.truetype(BARLOW, h)


def board_strip(name, items, h=115, panel=8.0):
    w = int(128 * panel * len(items))
    im = Image.new('RGB', (w, h), WHITE)
    d = ImageDraw.Draw(im)
    for k, (txt, bg, fg) in enumerate(items):
        x0, x1 = int(k * panel * 128), int((k + 1) * panel * 128)
        d.rectangle([x0, 0, x1, h], fill=bg)
        f = big(int(h * 0.72))
        tw = d.textlength(txt, font=f)
        if tw > (x1 - x0) * 0.86:
            f = big(int(h * 0.72 * (x1 - x0) * 0.86 / tw))
        d.text(((x0 + x1) / 2, h * 0.52), txt, font=f, fill=fg, anchor='mm')
        d.line([(x0, 0), (x0, h)], fill=(40, 40, 40), width=3)
    im.save(os.path.join(OUT, name))
    print(name, im.size)


RED = (214, 36, 44)
board_strip('boards.png', [('be union', RED, WHITE), ('UNION SAINT-GILLOISE', YELLOW, BLUE),
                           ('be.brussels', WHITE, BLUE), ('PARC DUDEN · DUDENPARK', BLUE, WHITE)])
board_strip('topboards.png', [('be union', (40, 58, 160), WHITE), ('RÉGION DE BRUXELLES-CAPITALE', WHITE, (30, 40, 70)),
                              ('be.brussels', WHITE, (40, 58, 160)), ('UNION', (40, 58, 160), YELLOW),
                              ('FOREST · VORST', WHITE, (30, 40, 70)), ('be union', (40, 58, 160), WHITE)], h=128, panel=5.0)

# ---------------------------------------------------------------- the club's band over the park terrace (68 x 2.6 m)
BW_, BH_ = 4096, 160
PXB = BW_ / 68.0
BAND_Y, BAND_B = (246, 208, 22), (40, 58, 160)
band = Image.new('RGB', (BW_, BH_), BAND_Y)
d = ImageDraw.Draw(band)
X = lambda f: int(f * BW_)
# the blue middle, its ends slanting
d.polygon([(X(0.19), 0), (X(0.75) + 30, 0), (X(0.75) - 30, BH_), (X(0.19) - 60, BH_)], fill=BAND_B)
d.line([(X(0.19), 0), (X(0.19) - 60, BH_)], fill=(255, 255, 255), width=4)
d.line([(X(0.75) + 30, 0), (X(0.75) - 30, BH_)], fill=(255, 255, 255), width=4)


def player(d, x, h, pose, kit, shorts, skin=(232, 196, 160), flip=False):
    # a footballer in silhouette, h px tall, feet on the band's lower edge
    s = h / 100.0
    fx = (lambda v: x - v * s) if flip else (lambda v: x + v * s)
    fy = lambda v: BH_ - 12 - v * s
    P = lambda a, b: (fx(a), fy(b))
    lw = max(3, int(9 * s))
    if pose == 'run':
        hip, sh = (0, 50), (4, 80)
        legs = [((hip, (12, 28)), ((12, 28), (6, 2))), ((hip, (-10, 30)), ((-10, 30), (-24, 14)))]
        arms = [((sh, (16, 70)), ((16, 70), (22, 82))), ((sh, (-10, 66)), ((-10, 66), (-18, 56)))]
    elif pose == 'kick':
        hip, sh = (0, 50), (-6, 80)
        legs = [((hip, (2, 26)), ((2, 26), (0, 2))), ((hip, (20, 40)), ((20, 40), (36, 30)))]
        arms = [((sh, (-24, 82)), ((-24, 82), (-34, 92))), ((sh, (8, 74)), ((8, 74), (20, 70)))]
    elif pose == 'head':
        hip, sh = (0, 56), (2, 84)
        legs = [((hip, (8, 34)), ((8, 34), (2, 12))), ((hip, (-8, 34)), ((-8, 34), (-16, 14)))]
        arms = [((sh, (-16, 92)), ((-16, 92), (-24, 102))), ((sh, (16, 92)), ((16, 92), (22, 102)))]
    else:   # 'jump': arms up, knees bent
        hip, sh = (0, 54), (0, 82)
        legs = [((hip, (12, 36)), ((12, 36), (4, 18))), ((hip, (-10, 38)), ((-10, 38), (-20, 22)))]
        arms = [((sh, (14, 94)), ((14, 94), (12, 108))), ((sh, (-12, 94)), ((-12, 94), (-10, 108)))]
    for (a, b), (c, e) in legs:
        d.line([P(*a), P(*b)], fill=shorts, width=lw + 2)
        d.line([P(*c), P(*e)], fill=skin, width=lw)
        d.line([P(*e), P(e[0] + 6, e[1] - 2)], fill=(20, 20, 24), width=lw)
    d.polygon([P(hip[0] - 9, hip[1]), P(hip[0] + 9, hip[1]), P(sh[0] + 10, sh[1]), P(sh[0] - 10, sh[1])], fill=kit)
    d.polygon([P(hip[0] - 9, hip[1]), P(hip[0] + 9, hip[1]), P(hip[0] + 10, hip[1] - 12), P(hip[0] - 10, hip[1] - 12)], fill=shorts)
    for (a, b), (c, e) in arms:
        d.line([P(*a), P(*b)], fill=kit, width=lw)
        d.line([P(*c), P(*e)], fill=skin, width=lw - 1)
    hx_, hy_ = P(sh[0] + 2, sh[1] + 11)
    r = 8 * s
    d.ellipse([hx_ - r, hy_ - r, hx_ + r, hy_ + r], fill=skin)
    d.chord([hx_ - r, hy_ - r - 1, hx_ + r, hy_ + r * 0.2], 180, 360, fill=(40, 28, 20))


def be_union(d, cx, colour, h=BH_):
    # the city's mark as on the band: 'be union' over 'be.brussels'
    f1, f2 = ImageFont.truetype(MONT, int(h * 0.30)), ImageFont.truetype(MONT, int(h * 0.30))
    d.text((cx, h * 0.33), 'be union', font=f1, fill=colour, anchor='mm')
    d.text((cx, h * 0.68), 'be.brussels', font=f2, fill=colour, anchor='mm')
    w = d.textlength('be.brussels', font=f2)
    ex, ey, r = cx + w / 2 + h * 0.10, h * 0.68, h * 0.09
    d.ellipse([ex - r, ey - r, ex + r, ey + r], outline=colour, width=4)


be_union(d, X(0.045), BAND_B)
be_union(d, X(0.27), (255, 255, 255))
be_union(d, X(0.665), (255, 255, 255))
be_union(d, X(0.945), BAND_B)
POSES = ['run', 'kick', 'head', 'jump', 'run', 'kick']
k = 0
for a, b, kit, sh in ((0.09, 0.17, BAND_B, (250, 250, 250)), (0.32, 0.40, BAND_Y, BAND_B), (0.54, 0.63, BAND_Y, BAND_B),
                      (0.70, 0.74, BAND_Y, BAND_B), (0.78, 0.91, BAND_B, (250, 250, 250))):
    n = max(1, round((b - a) * 68 / 3.2))
    for j in range(n):
        x = X(a + (b - a) * (j + 0.5) / n)
        player(d, x, BH_ * (0.62 + 0.12 * ((k * 7) % 3) / 2), POSES[k % len(POSES)], kit, sh, flip=bool(k % 2))
        k += 1
    if a < 0.5 and b > 0.3:
        # a ball by the header
        bx_ = X(a + (b - a) * 0.5)
        d.ellipse([bx_ - 9, 18, bx_ + 9, 36], fill=(250, 250, 250), outline=(30, 30, 30), width=2)
crest_b = Image.open(os.path.join(OUT, 'usg.png')).convert('RGBA')
ch_ = int(BH_ * 0.52)
crest_b = crest_b.resize((int(crest_b.width * ch_ / crest_b.height), ch_), Image.LANCZOS)
band.paste(crest_b, (X(0.47) - crest_b.width // 2, 8), crest_b)
fnt = ImageFont.truetype(BARLOW, int(BH_ * 0.26))
d.text((X(0.47), BH_ * 0.78), 'ROYALE UNION SAINT-GILLOISE', font=fnt, fill=(255, 255, 255), anchor='mm')
d.rectangle([0, 0, BW_ - 1, BH_ - 1], outline=(20, 24, 40), width=3)
band.save(os.path.join(OUT, 'banner.png'))
print('banner.png', band.size)

# ---------------------------------------------------------------- the cloth on the bank: Let's go hey! (9.2 x 18.9 m)
# designed as it is seen from the pitch (a 512 x 512 square), then drawn twice
# as tall on the cloth
VW, VH = 512, 512
v = Image.new('RGB', (VW, VH), (230, 78, 52))
d = ImageDraw.Draw(v)
d.polygon([(0, VH * 0.43), (VW, VH * 0.33), (VW, VH * 0.58), (0, VH * 0.70)], fill=(44, 82, 200))    # the blue band across
d.polygon([(VW * 0.30, VH), (VW, VH * 0.62), (VW, VH)], fill=(84, 166, 232))                         # light blue, bottom right
d.polygon([(VW * 0.30, VH), (VW, VH * 0.62), (VW, VH * 0.58), (0, VH * 0.70), (0, VH * 0.74)], fill=(66, 120, 214))


def slanted(img, txt, font, fill, centre, shear=0.22, stroke=0):
    # italic: the text drawn on its own layer and sheared
    f = ImageFont.truetype(*font)
    w, h = int(f.getlength(txt) + 40 + 2 * stroke), int(font[1] * 1.4)
    lay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((20 + stroke, h * 0.5), txt, font=f, fill=fill, anchor='lm', stroke_width=stroke, stroke_fill=fill)
    lay = lay.transform(lay.size, Image.AFFINE, (1, shear, -shear * h * 0.5, 0, 1, 0), Image.BICUBIC)
    img.paste(lay, (int(centre[0] - w / 2), int(centre[1] - h / 2)), lay)


slanted(v, "Let's go", (MONT, 92), (250, 200, 30), (VW * 0.55, VH * 0.24))
slanted(v, 'hey!', (ROUND, 160), (255, 255, 255), (VW * 0.50, VH * 0.50), 0.10, 3)
slanted(v, 'heytelecom.be', (MONT, 40), (255, 255, 255), (VW * 0.50, VH * 0.70), 0.15)
for j in range(3):                                                                                    # the three strokes top right
    x0 = VW * 0.74 + j * 30
    d.polygon([(x0 + 14, 22), (x0 + 30, 22), (x0 + 14, 92), (x0 - 2, 92)], fill=(255, 255, 255))
v = v.resize((VW, VH * 2), Image.LANCZOS)
v.save(os.path.join(OUT, 'hey.png'))
print('hey.png', v.size)

# ---------------------------------------------------------------- the crest for the scoreboard
Image.open(os.path.join(OUT, 'usg.png')).convert('RGBA').save(os.path.join(HERE, '..', 'media', 'hud', 'union.png'))
print('media/hud/union.png')

# ---------------------------------------------------------------- the ground (640 x 640 m, 2048 px, row 0 at y = +320)
G_HALF, G_PX = 320.0, 2048
osm = json.load(open(os.path.join(OUT, 'osm.json')))
S = G_PX / (2 * G_HALF)
T = lambda q: ((q[0] + G_HALF) * S, (G_HALF - q[1]) * S)
noise = rng.normal(0, 1, (G_PX // 8, G_PX // 8, 1))
base = np.ones((G_PX, G_PX, 3)) * np.array((150, 146, 138))           # the town: pavements and yards
base *= 1 + 0.05 * np.kron(noise, np.ones((8, 8, 1)))
im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(im)
for g in osm['park']:
    d.polygon([T(q) for q in g], fill=(70, 92, 48))                    # the park's floor under the trees
for g in osm['forest']:
    d.polygon([T(q) for q in g], fill=(58, 78, 40))
for g in osm['grass']:
    d.polygon([T(q) for q in g], fill=(88, 120, 58))
ROAD_W = {'primary': 14, 'secondary': 12, 'tertiary': 10, 'residential': 8, 'unclassified': 7, 'service': 4.5,
          'pedestrian': 5, 'footway': 2.2, 'cycleway': 2.2, 'path': 2.0, 'steps': 2.2}
for r in sorted(osm['roads'], key=lambda r: ROAD_W.get(r['type'], 3)):
    w = ROAD_W.get(r['type'], 3)
    col = (128, 112, 90) if r['type'] in ('footway', 'path', 'steps') else (64, 64, 66)
    pts = [T(q) for q in r['pts']]
    d.line(pts, fill=col, width=max(1, int(w * S)), joint='curve')
for b in osm['buildings']:
    d.polygon([T(q) for q in b['pts']], fill=(60, 58, 56))
im.save(os.path.join(OUT, 'ground.png'))
print('ground.png', im.size)
