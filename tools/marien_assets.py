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
#   tools/marien/banner.png   the band along the top of the park stand
#   tools/marien/ground.png   the ground round the stadium from OpenStreetMap
# No sponsors: the boards carry the club's and the city's own words.
#   python3 tools/marien_assets.py
import json, math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'marien')
FONTS = os.path.join(HERE, 'fonts')
BARLOW = os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf')
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


board_strip('boards.png', [('UNION SAINT-GILLOISE', YELLOW, BLUE), ('BRUXELLES · BRUSSEL', BLUE, WHITE),
                           ('PARC DUDEN', WHITE, NAVY), ('ALLEZ UNION', BLUE, YELLOW)])
board_strip('banner.png', [('ROYALE UNION SAINT-GILLOISE', BLUE, WHITE), ('BE.UNION', YELLOW, BLUE),
                           ('STADE JOSEPH MARIEN', BLUE, WHITE), ('BE.UNION', YELLOW, BLUE)], h=128, panel=12.0)

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
