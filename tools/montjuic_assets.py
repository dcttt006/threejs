# Makes the pictures tools/montjuic_build.py needs for the Estadi Olímpic
# Lluís Companys (Montjuïc), as on the photos of FC Barcelona's seasons there
# (2023-2025):
#   tools/montjuic/cloth.png   the big cloth on the grass in each curve: broad
#                              swathes of coral red and violet, the club crest
#                              in the middle, its top towards the stand
#   tools/montjuic/tarp.png    the blaugrana covers over the first rows of seats
#   tools/montjuic/band.png    the red banners on the front of the upper tier:
#                              FC BARCELONA in white, MÉS QUE UN CLUB in yellow
#   tools/montjuic/clock.png   the clock over the Marathon Gate
#   tools/montjuic/arms.png    the round arms of Barcelona under the clock
#   tools/montjuic/relief.png  the stone frieze over the arch, outside
#   python3 tools/montjuic_assets.py
import os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'montjuic')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1929)

# the cloth's colours, read off the photo of the north curve in the sun
CORAL = (226, 98, 96)
VIOLET = (138, 110, 168)
GOLD = (234, 197, 120)
INK = (50, 46, 78)
WHITE = (241, 238, 233)
SEN_Y, SEN_R = (238, 196, 60), (214, 52, 52)


def crest(size, red=CORAL, blue=VIOLET, gold=GOLD, ink=INK, white=WHITE, cross=(214, 50, 56)):
    # the club crest, upright, `size` px wide (and a little taller). Drawn from
    # its parts: the top edge rising to a point in the middle, sharp corners at
    # the ends of the FCB band, the cross of Sant Jordi on the left, the four
    # red bars on yellow on the right, the band with FCB, under it the stripes
    # with the ball, the bottom round to a point; a gold edge round it all
    S = 4                                            # drawn big, shrunk smooth
    W = size * S
    H = int(W * 1.08)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * W, y * H)

    def top_edge(inset):
        # from the left corner up to the point in the middle and down to the right corner
        pts = []
        for i in range(41):
            t = i / 40
            x = inset + (1 - 2 * inset) * t
            u = abs(t - 0.5) * 2                      # 1 at the corners, 0 in the middle
            y = 0.02 + inset * 0.9 + 0.13 * u ** 1.6
            pts.append(P(x, y))
        return pts

    def bottom(inset):
        # the lower half: from the band's ends down and round to the point
        pts = []
        for i in range(61):
            t = i / 60
            a = math.pi * t
            x = 0.5 - (0.5 - 0.035 - inset) * math.cos(a)
            sag = math.sin(a)
            y = 0.40 + (0.58 - inset) * (sag ** 0.62) + 0.03 * math.sin(a) ** 8
            pts.append(P(x, y))
        return pts

    BAND0, BAND1 = 0.285, 0.395
    outline = top_edge(0.0)[::-1] + [P(0.0, BAND0 - 0.02), P(-0.01, (BAND0 + BAND1) / 2), P(0.0, BAND1 + 0.02)] + \
        bottom(0.0) + [P(1.0, BAND1 + 0.02), P(1.01, (BAND0 + BAND1) / 2), P(1.0, BAND0 - 0.02)]
    # a thin dark line round the gold, as on the cloth
    d.polygon(outline, fill=(70, 60, 60, 255))
    shrink = lambda pts, k: [((x - W / 2) * k + W / 2, (y - H * 0.5) * k + H * 0.5) for x, y in pts]
    d.polygon(shrink(outline, 0.985), fill=gold + (255,))
    # the top two quarters
    g = 0.045
    top = top_edge(g)
    left_q = [p for p in top if p[0] <= W / 2] + [P(0.5 - 0.008, BAND0), P(g, BAND0)]
    right_q = [p for p in top if p[0] >= W / 2] + [P(1 - g, BAND0), P(0.5 + 0.008, BAND0)]
    d.polygon(left_q, fill=white + (255,))
    # the cross of Sant Jordi: wide red bars, the white left as four squares
    cx0, cx1 = 0.215, 0.315
    q = Image.new('L', (W, H), 0)
    ImageDraw.Draw(q).polygon(left_q, fill=255)
    bars = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bars)
    bd.rectangle((cx0 * W, 0, cx1 * W, BAND0 * H), fill=cross + (255,))
    bd.rectangle((0, 0.150 * H, 0.5 * W, 0.215 * H), fill=cross + (255,))
    im.paste(bars, (0, 0), Image.composite(bars, Image.new('RGBA', (W, H)), q).split()[3])
    # the four red bars on yellow
    q = Image.new('L', (W, H), 0)
    ImageDraw.Draw(q).polygon(right_q, fill=255)
    sen = Image.new('RGBA', (W, H), SEN_Y + (255,))
    sd = ImageDraw.Draw(sen)
    x0, x1 = 0.5 + 0.008, 1 - g
    for k in range(9):
        if k % 2:
            sd.rectangle((W * (x0 + (x1 - x0) * k / 9), 0, W * (x0 + (x1 - x0) * (k + 1) / 9), H), fill=SEN_R + (255,))
    im.paste(sen, (0, 0), q)
    # the lower half: violet and red stripes, five of them
    low = bottom(g)
    lowpoly = [P(g + 0.01, BAND1 + 0.02)] + low + [P(1 - g - 0.01, BAND1 + 0.02)]
    q = Image.new('L', (W, H), 0)
    ImageDraw.Draw(q).polygon(lowpoly, fill=255)
    st = Image.new('RGBA', (W, H), blue + (255,))
    sd = ImageDraw.Draw(st)
    for k in range(5):
        if k % 2:
            sd.rectangle((W * (0.05 + 0.9 * k / 5), 0, W * (0.05 + 0.9 * (k + 1) / 5), H), fill=red + (255,))
    im.paste(st, (0, 0), q)
    # the ball, in gold with its seams (kept inside the ball)
    bx, by, br = 0.5 * W, 0.535 * H, 0.10 * W
    ball = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(ball)
    box_ = (bx - br, by - br * 0.85, bx + br, by + br * 0.85)
    bd.ellipse(box_, fill=gold + (255,))
    lw = max(2, int(W * 0.006))
    bd.arc((bx - br * 1.6, by - br * 0.5, bx + br * 0.2, by + br * 1.9), 270, 360, fill=ink + (255,), width=lw)
    bd.arc((bx - br * 0.2, by - br * 0.5, bx + br * 1.6, by + br * 1.9), 180, 270, fill=ink + (255,), width=lw)
    bd.arc((bx - br * 0.9, by - br * 1.5, bx + br * 0.9, by + br * 0.1), 20, 160, fill=ink + (255,), width=lw)
    bd.arc((bx - br * 0.7, by + br * 0.05, bx + br * 0.7, by + br * 1.4), 200, 340, fill=ink + (255,), width=lw)
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).ellipse(box_, fill=255)
    im.paste(ball, (0, 0), Image.fromarray(np.minimum(np.asarray(m), np.asarray(ball.split()[3]))))
    d.ellipse(box_, outline=ink + (255,), width=max(1, lw // 2))
    # the band with FCB
    d.polygon([P(0.0, BAND0), P(1.0, BAND0), P(1.0, BAND1), P(0.0, BAND1)], fill=gold + (255,))
    f = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), int(H * 0.115))
    for ch, x in (('F', 0.31), ('C', 0.5), ('B', 0.69)):
        d.text(P(x, (BAND0 + BAND1) / 2 + 0.004), ch, font=f, fill=ink + (255,), anchor='mm')
    # the gold edge lines between the parts
    ew = max(3, int(W * 0.012))
    d.line([P(0.5, 0.04), P(0.5, BAND0)], fill=gold + (255,), width=ew)
    d.line([P(0.0, BAND0), P(1.0, BAND0)], fill=gold + (255,), width=ew)
    d.line([P(0.0, BAND1), P(1.0, BAND1)], fill=gold + (255,), width=ew)
    return im.resize((size, int(size * 1.08)), Image.LANCZOS)


def cloth():
    # the cloth in a curve, flat: u across the curve (71 m, from one side to the
    # other as seen from the stand), v from the edge at the pitch (top) to the
    # far end of the curve (bottom, 25.7 m). The crest stands in the middle with
    # its top towards the stand, as on the photos (it reads from the pitch).
    CW, CH = 71.0, 25.7
    PXM = 30
    W, H = int(CW * PXM), int(CH * PXM)
    y, x = np.mgrid[0:H, 0:W].astype('f')
    X, Y = x / PXM - CW / 2, y / PXM                  # metres: X across, Y from the pitch edge
    # broad swathes of violet over coral, curving across the cloth
    a = np.radians(32)
    s = X * math.cos(a) + Y * math.sin(a) + 2.4 * np.sin(X / 9.0) + 1.5 * np.sin(Y / 5.0 + 1.0)
    s = s + 4.0 * np.sin(X / 17.0 + Y / 11.0)
    band = np.sin(s / 15.0 * 2 * np.pi) > 0.1
    base = np.empty((H, W, 3), 'f')
    base[:] = CORAL
    base[band] = VIOLET
    # the cloth lies loose: soft folds and wrinkles, brighter and darker
    def noise(cy, cx):
        g = rng.normal(0, 1, (H // cy + 3, W // cx + 3)).astype('f')
        yy, xx = np.arange(H, dtype='f') / cy, np.arange(W, dtype='f') / cx
        y0, x0 = yy.astype(int), xx.astype(int)
        fy, fx = (yy - y0)[:, None], (xx - x0)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        return (g[y0][:, x0] * (1 - fy) * (1 - fx) + g[y0 + 1][:, x0] * fy * (1 - fx)
                + g[y0][:, x0 + 1] * (1 - fy) * fx + g[y0 + 1][:, x0 + 1] * fy * fx)
    folds = 0.05 * noise(60, 260) + 0.03 * noise(14, 90) + 0.02 * noise(4, 30)
    base *= (1 + folds)[..., None]
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert('RGBA')
    # the crest: 22 m wide, upside down on the image (its top towards the stand)
    cw = int(22.0 * PXM)
    c = crest(cw).rotate(180)
    cx, cy = W // 2, int(13.1 * PXM)
    shade = Image.fromarray(np.clip(255 * (1 + folds[cy - c.height // 2:cy - c.height // 2 + c.height, cx - cw // 2:cx - cw // 2 + cw]), 0, 255).astype(np.uint8))
    cr = np.asarray(c, 'f')
    cr[..., :3] *= (np.asarray(shade, 'f') / 255.0)[..., None]
    c = Image.fromarray(np.clip(cr, 0, 255).astype(np.uint8))
    im.alpha_composite(c, (cx - cw // 2, cy - c.height // 2))
    im.convert('RGB').save(os.path.join(OUT, 'cloth.png'))


def tarp():
    # the covers over the first rows: wide waves of blue and garnet with a pink
    # edge, as on the photo of the north end; u along the rows (12 m), v up
    # the slope (four rows, 3.2 m). Tiles along u.
    W, H = 768, 192
    y, x = np.mgrid[0:H, 0:W].astype('f')
    u, v = x / W * 12.0, y / H * 3.2
    s = v * 1.6 + 0.55 * np.sin(u / 12.0 * 2 * np.pi * 2) + 0.25 * np.sin(u / 12.0 * 2 * np.pi * 5 + 1)
    k = np.floor(s / 0.62).astype(int) % 3
    col = np.array([(38, 48, 128), (160, 30, 62), (54, 46, 136)], 'f')[k]
    edge = (np.abs((s / 0.62) % 1 - 0.5) > 0.44) & (k == 1)
    col[edge] = (196, 82, 110)
    col *= (1 + 0.06 * np.sin(u * 7.0 + v * 3.0))[..., None]
    Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'tarp.png'))


def band():
    # the banners on the front of the upper tier: red, FC BARCELONA in white
    # with the crest before it, MÉS QUE UN CLUB in yellow; 48 m of band
    # (1.4 m high) in one picture, tiling along the ring
    PXM = 64
    W, H = 48 * PXM, int(1.4 * PXM)
    im = Image.new('RGB', (W, H), (196, 18, 48))
    d = ImageDraw.Draw(im)
    big = ImageFont.truetype(os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf'), int(H * 0.62))
    ic = crest(int(H * 0.68), red=(178, 24, 52), blue=(30, 52, 140), gold=(236, 190, 40), ink=(20, 30, 70), cross=(200, 30, 40))
    for k in range(4):
        x0 = k * 12 * PXM
        d.line([(x0, 0), (x0, H)], fill=(120, 10, 30), width=4)    # the seam between two banners
        if k % 2 == 0:
            tw = d.textlength('FC BARCELONA', font=big)
            tx = x0 + 6 * PXM - tw / 2 + H * 0.45
            im.paste(ic, (int(tx - H * 0.9), int(H * 0.13)), ic)
            d.text((tx, H / 2), 'FC BARCELONA', font=big, fill=(250, 250, 250), anchor='lm')
        else:
            d.text((x0 + 6 * PXM, H / 2), 'MÉS QUE UN CLUB', font=big, fill=(246, 206, 40), anchor='mm')
    im.save(os.path.join(OUT, 'band.png'))


def clock():
    # the clock over the Marathon Gate: a white face, black figures 1 to 12,
    # the minutes marked round the edge, two black hands (half past two)
    S = 512
    im = Image.new('RGB', (S, S), (225, 214, 192))
    d = ImageDraw.Draw(im)
    c, r = S / 2, S / 2 - 6
    d.ellipse((c - r, c - r, c + r, c + r), fill=(46, 40, 36))
    r2 = r - 14
    d.ellipse((c - r2, c - r2, c + r2, c + r2), fill=(246, 244, 238))
    for m in range(60):
        a = math.radians(m * 6 - 90)
        l = 22 if m % 5 == 0 else 10
        d.line([(c + (r2 - 6) * math.cos(a), c + (r2 - 6) * math.sin(a)), (c + (r2 - 6 - l) * math.cos(a), c + (r2 - 6 - l) * math.sin(a))],
               fill=(30, 30, 30), width=6 if m % 5 == 0 else 3)
    f = ImageFont.truetype(os.path.join(FONTS, 'BarlowCondensed-ExtraBold.ttf'), 62)
    for h in range(1, 13):
        a = math.radians(h * 30 - 90)
        d.text((c + (r2 - 66) * math.cos(a), c + (r2 - 66) * math.sin(a)), str(h), font=f, fill=(24, 24, 24), anchor='mm')
    def hand(ang, length, width):
        a = math.radians(ang - 90)
        d.line([(c - 0.15 * length * math.cos(a), c - 0.15 * length * math.sin(a)), (c + length * math.cos(a), c + length * math.sin(a))], fill=(16, 16, 16), width=width)
    hand(2.5 * 30, r2 * 0.52, 16)
    hand(30 * 6, r2 * 0.80, 10)
    d.ellipse((c - 12, c - 12, c + 12, c + 12), fill=(16, 16, 16))
    im.save(os.path.join(OUT, 'clock.png'))


def arms():
    # the arms of Barcelona in a round stone frame, under the clock: the cross
    # of Sant Jordi in the first and fourth quarters, the four bars in the
    # second and third, on a lozenge; the frame dark red as on the photo
    S = 256
    im = Image.new('RGB', (S, S), (214, 200, 176))
    d = ImageDraw.Draw(im)
    c = S / 2
    d.ellipse((6, 6, S - 6, S - 6), fill=(120, 34, 38))
    d.ellipse((26, 26, S - 26, S - 26), fill=(236, 230, 220))
    L = 78
    q = [(c, c - L), (c + L, c), (c, c + L), (c - L, c)]
    d.polygon(q, fill=(240, 240, 236))
    for (sx, sy, kind) in ((-1, -1, 'cross'), (1, -1, 'bars'), (-1, 1, 'bars'), (1, 1, 'cross')):
        cx, cy = c + sx * L / 2, c + sy * L / 2
        tri = [(c, c), (c + sx * L, c), (c, c + sy * L)]
        m = Image.new('L', (S, S), 0)
        ImageDraw.Draw(m).polygon(tri, fill=255)
        layer = Image.new('RGB', (S, S), (240, 240, 236) if kind == 'cross' else SEN_Y)
        ld = ImageDraw.Draw(layer)
        if kind == 'cross':
            ld.rectangle((cx - 8, cy - 40, cx + 8, cy + 40), fill=(200, 30, 40))
            ld.rectangle((cx - 40, cy - 8, cx + 40, cy + 8), fill=(200, 30, 40))
        else:
            for k in range(9):
                if k % 2:
                    ld.rectangle((c - L + 2 * L * k / 9, 0, c - L + 2 * L * (k + 1) / 9, S), fill=SEN_R)
        im.paste(layer, (0, 0), m)
    d.polygon(q, outline=(120, 34, 38), width=4)
    im.save(os.path.join(OUT, 'arms.png'))


def relief():
    # the frieze over the arch on the outside: athletes carved in the stone,
    # lighter on top where the sun catches them, a shadow under each
    W, H = 1024, 256
    a = np.full((H, W), 0.80, 'f')
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    x = 20
    while x < W - 40:
        w = rng.integers(40, 70)
        h0 = rng.integers(150, 215)
        d.ellipse((x + w * 0.3, H - h0 - 30, x + w * 0.3 + 26, H - h0 - 4), fill=255)                       # head
        d.polygon([(x + w * 0.2, H - h0), (x + w * 0.8, H - h0 + 8), (x + w, H - 30), (x + w * 0.65, H - 22),
                   (x + w * 0.5, H - h0 * 0.45), (x + w * 0.3, H - 22), (x, H - 30)], fill=255)                # body and legs
        d.line([(x + w * 0.4, H - h0 + 14), (x + w * 1.1, H - h0 - 30 + rng.integers(0, 40))], fill=255, width=12)   # an arm
        x += w + rng.integers(4, 18)
    m = np.asarray(im.filter(ImageFilter.GaussianBlur(2)), 'f') / 255.0
    lit = np.roll(m, 3, axis=0)
    a = a + 0.05 * m - 0.07 * np.clip(lit - m, 0, 1) + 0.03 * rng.normal(0, 1, (H, W)).astype('f')
    rgb = np.clip(a[..., None] * np.array((236, 222, 196), 'f'), 0, 255).astype(np.uint8)
    Image.fromarray(rgb).save(os.path.join(OUT, 'relief.png'))


cloth()
tarp()
band()
clock()
arms()
relief()
crest(512).save(os.path.join(OUT, 'crest.png'))
print('written to', OUT)
