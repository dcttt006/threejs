# Makes the three pictures tools/arena_build.py needs for the Johan Cruijff ArenA:
#   tools/arena/portrait.png    the black and white portrait on the north tower
#   tools/arena/foundation.png  the yellow Johan Cruyff Foundation disc on the ground
#   tools/arena/ajax.png        AJAX in seats: one pixel a seat, one row a row of seats
#   tools/arena/banners.png     the championship banners under the roof: 8 x 4 in one picture
#   python3 tools/arena_assets.py [photo.jpg]
#
# The portrait: "Johan Cruijff (1974)", Rob Mieremet / Anefo, Nationaal Archief,
# CC0 (public domain): https://commons.wikimedia.org/wiki/File:Johan_Cruijff_(1974).jpg
# It is fetched from Wikimedia Commons when no photo is given. As on the facade:
# black and white, head and shoulders, on a light grey ground.
import os, sys, urllib.request
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'arena')
FONTS = os.path.join(HERE, 'fonts')
PHOTO_URL = 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/cb/Johan_Cruijff_%281974%29.jpg/960px-Johan_Cruijff_%281974%29.jpg'
os.makedirs(OUT, exist_ok=True)


def photo():
    if len(sys.argv) > 1:
        return cv2.imread(sys.argv[1])
    req = urllib.request.Request(PHOTO_URL, headers={'User-Agent': 'stadium-texture-script/1.0'})
    data = np.frombuffer(urllib.request.urlopen(req).read(), np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def portrait():
    img = photo()                                   # 960 x 1280, the face a little right of the middle
    h, w = img.shape[:2]
    s = w / 960.0
    # lift him off the blurred room behind him: a soft mask drawn round the
    # head (hair included), the neck and the shoulders of this photo
    fg = np.zeros((h, w), 'f')
    P = lambda pts: np.array([[int(x * s), int(y * s)] for x, y in pts], np.int32)
    cv2.ellipse(fg, (int(567 * s), int(405 * s)), (int(262 * s), int(330 * s)), 0, 0, 360, 1.0, -1)
    cv2.fillPoly(fg, [P([(470, 690), (800, 690), (870, 770), (960, 840), (960, 1280), (357, 1280),
                         (400, 1100), (440, 1000), (512, 878), (470, 800)]),
                     P([(420, 540), (600, 540), (640, 760), (520, 800), (440, 740), (415, 640)])], 1.0)     # the jaw and the chin
    fg = cv2.GaussianBlur(fg, (0, 0), 12 * s)
    # black and white, a little more contrast, as a print on the facade
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype('f') / 255.0
    lo, hi = np.percentile(g[fg > 0.5], (2, 99))
    g = np.clip((g - lo) / (hi - lo), 0, 1) ** 0.9
    ground = 0.86 + 0.05 * np.linspace(1, 0, h)[:, None]
    out = g * fg + ground * (1 - fg)
    # the panel is 10.4 x 14.6 m: head and shoulders, the face in the upper half
    cx, top = int(555 * s), 0
    ch = h - int(150 * s)
    cw = int(ch * 10.4 / 14.6)
    x0 = max(0, min(w - cw, cx - cw // 2))
    out = out[top:top + ch, x0:x0 + cw]
    im = Image.fromarray((out * 255).astype(np.uint8)).resize((512, 720), Image.LANCZOS)
    im.save(os.path.join(OUT, 'portrait.png'))


def foundation():
    # a yellow disc with the name round it and a big 14 in the middle
    S = 512
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    yellow, black = (247, 200, 20, 255), (20, 20, 20, 255)
    d.ellipse((4, 4, S - 4, S - 4), fill=yellow)
    d.ellipse((34, 34, S - 34, S - 34), outline=black, width=8)
    big = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 230)
    d.text((S / 2, S / 2 + 6), '14', font=big, fill=black, anchor='mm')
    small = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 40)

    def arc_text(text, radius, start, step, flip):
        for i, ch in enumerate(text):
            a = np.radians(start + i * step)
            g = Image.new('RGBA', (60, 60), (0, 0, 0, 0))
            ImageDraw.Draw(g).text((30, 30), ch, font=small, fill=black, anchor='mm')
            rot = -np.degrees(a) - 90 if not flip else -np.degrees(a) + 90
            g = g.rotate(rot, resample=Image.BICUBIC)
            x, y = S / 2 + radius * np.cos(a), S / 2 + radius * np.sin(a)
            im.alpha_composite(g, (int(x - 30), int(y - 30)))
    top, bottom = 'JOHAN CRUYFF', 'FOUNDATION'
    arc_text(top, 175, -90 - 6.5 * (len(top) - 1), 13, False)
    arc_text(bottom, 178, 90 + 7.5 * (len(bottom) - 1), -15, True)
    im.save(os.path.join(OUT, 'foundation.png'))


def ajax(rows=19, gap=2, mid_gap=4):
    # AJAX in Arial Black, bold and wide as in the seats: each letter
    # squeezed to `rows` rows, `gap` seats between letters and a wider gap
    # between J and A, which sits on the image's middle column: the stairs on
    # the halfway line run through there
    black = '/System/Library/Fonts/Supplemental/Arial Black.ttf'
    f = ImageFont.truetype(black if os.path.exists(black) else os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 400)

    def letter(ch):
        im = Image.new('L', (700, 600), 0)
        ImageDraw.Draw(im).text((50, 50), ch, font=f, fill=255)
        im = im.crop(im.getbbox())
        cols = max(1, round(im.width / im.height * rows * 0.75))   # rows look short from the camera: tall letters on the slope, as on the photos
        a = np.asarray(im.resize((cols * 8, rows * 8), Image.LANCZOS), 'f') / 255.0
        return a.reshape(rows, 8, cols, 8).mean(axis=(1, 3)) > 0.45
    A, J, X = letter('A'), letter('J'), letter('X')
    sp = np.zeros((rows, gap), bool)
    left = np.hstack([A, sp, J])
    right = np.hstack([A, sp, X])
    half = max(left.shape[1], right.shape[1]) + mid_gap // 2
    left = np.hstack([np.zeros((rows, half - mid_gap // 2 - left.shape[1]), bool), left, np.zeros((rows, mid_gap // 2), bool)])
    right = np.hstack([np.zeros((rows, mid_gap // 2), bool), right, np.zeros((rows, half - mid_gap // 2 - right.shape[1]), bool)])
    cells = np.hstack([left, right])
    Image.fromarray((cells * 255).astype(np.uint8)).save(os.path.join(OUT, 'ajax.png'))
    for r in range(rows):
        print(''.join('#' if v else '.' for v in cells[r]))
    print(cells.shape[1], 'seats wide')


def banners():
    # the championship banners hanging under the roof at both ends, as on the
    # photos: red, a thin white edge, what was won at the top, the trophy (a
    # plate for the title, a cup for the others) and the year at the bottom
    BW, BH, NC, NR = 128, 320, 8, 4
    sheet = Image.new('RGB', (BW * NC, BH * NR), (200, 16, 46))
    small = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 15)
    year_f = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 18)
    W = (245, 245, 245)
    title = lambda y: ('LANDS', 'KAMPIOEN', 'plate', y)
    beker = lambda y: ('NATIONALE', 'BEKER', 'cup', y)
    items = [title(2022), ('EUROPA', 'CUP I', 'ears', 1995), beker(2021), title(2021), ('WERELD', 'BEKER', 'world', 1995),
             title(2019), beker(2019), ('EUROPESE', 'SUPERCUP', 'super', 1995), title(2014), beker(2010), title(2013),
             ('UEFA', 'CUP', 'uefa', 1992), title(2012), beker(2007), title(2011), ('EUROPA', 'CUP II', 'cup', 1987),
             title(2004), beker(2006), ('EUROPA', 'CUP I', 'ears', 1973), title(2002), beker(2002), ('EUROPESE', 'SUPERCUP', 'super', 1973),
             title(1998), ('EUROPA', 'CUP I', 'ears', 1972), beker(1999), title(1996), ('WERELD', 'BEKER', 'world', 1972),
             title(1995), beker(1998), ('EUROPA', 'CUP I', 'ears', 1971), title(1994), title(1990)]
    for k, (l1, l2, kind, year) in enumerate(items):
        b = Image.new('RGB', (BW, BH), (200, 16, 46))
        d = ImageDraw.Draw(b)
        d.rectangle((7, 7, BW - 8, BH - 8), outline=W, width=3)
        d.text((BW / 2, 40), l1, font=small, fill=W, anchor='mm')
        d.text((BW / 2, 61), l2, font=small, fill=W, anchor='mm')
        cx, cy = BW / 2, 162
        if kind == 'plate':
            d.ellipse((cx - 40, cy - 40, cx + 40, cy + 40), fill=W)
            d.ellipse((cx - 30, cy - 30, cx + 30, cy + 30), outline=(200, 16, 46), width=3)
        else:
            top, bot = cy - 52, cy + 50
            if kind == 'ears':                                            # the big ears
                d.ellipse((cx - 50, top + 4, cx - 14, top + 62), outline=W, width=7)
                d.ellipse((cx + 14, top + 4, cx + 50, top + 62), outline=W, width=7)
            elif kind != 'super':
                d.arc((cx - 40, top + 8, cx - 10, top + 40), 90, 270, fill=W, width=6)
                d.arc((cx + 10, top + 8, cx + 40, top + 40), -90, 90, fill=W, width=6)
            if kind == 'world':
                d.ellipse((cx - 20, top, cx + 20, top + 40), fill=W)
                d.polygon([(cx - 8, top + 38), (cx + 8, top + 38), (cx + 13, bot - 14), (cx - 13, bot - 14)], fill=W)
            elif kind == 'super':
                d.ellipse((cx - 36, top + 6, cx + 36, top + 70), fill=W)
                d.polygon([(cx - 9, top + 66), (cx + 9, top + 66), (cx + 14, bot - 14), (cx - 14, bot - 14)], fill=W)
            else:
                tall = kind in ('cup', 'uefa')
                d.polygon([(cx - 26, top), (cx + 26, top), (cx + 18, top + 46), (cx + 6, top + 58), (cx - 6, top + 58), (cx - 18, top + 46)], fill=W)
                d.rectangle((cx - 5, top + 56, cx + 5, bot - 16 if tall else bot - 22), fill=W)
            d.rectangle((cx - 22, bot - 16, cx + 22, bot), fill=W)
        d.text((BW / 2, BH - 34), str(year), font=year_f, fill=W, anchor='mm')
        sheet.paste(b, ((k % NC) * BW, (k // NC) * BH))
    sheet.save(os.path.join(OUT, 'banners.png'))


portrait()
foundation()
ajax()
banners()
print('written to', OUT)
