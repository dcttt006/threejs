# Makes the picture tools/bernabeu_build.py needs for the Santiago Bernabéu:
#   tools/bernabeu/realmadrid.png  REAL MADRID in white seats in the first ring of
#                                  the east stand: one pixel a seat, one row a row
#   python3 tools/bernabeu_assets.py
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'bernabeu')
FONTS = os.path.join(HERE, 'fonts')
os.makedirs(OUT, exist_ok=True)


def letters(text="REAL MADRID", rows=18, gap=2, word_gap=10):
    # wide, round, heavy capitals, as in the seats on the photos (the club's
    # lettering is a geometric sans: Montserrat ExtraBold comes close)
    f = ImageFont.truetype(os.path.join(FONTS, 'Montserrat-ExtraBold.ttf'), 400)

    def letter(ch):
        im = Image.new('L', (700, 600), 0)
        ImageDraw.Draw(im).text((50, 50), ch, font=f, fill=255)
        im = im.crop(im.getbbox())
        cols = max(1, round(im.width / im.height * rows * 0.78))
        a = np.asarray(im.resize((cols * 8, rows * 8), Image.LANCZOS), 'f') / 255.0
        return a.reshape(rows, 8, cols, 8).mean(axis=(1, 3)) > 0.45
    parts = []
    for w, word in enumerate(text.split(' ')):
        if w:
            parts.append(np.zeros((rows, word_gap), bool))
        for k, ch in enumerate(word):
            if k:
                parts.append(np.zeros((rows, gap), bool))
            parts.append(letter(ch))
    cells = np.hstack(parts)
    Image.fromarray((cells * 255).astype(np.uint8)).save(os.path.join(OUT, 'realmadrid.png'))
    for r in range(rows):
        print(''.join('#' if v else '.' for v in cells[r]))
    print(cells.shape[1], 'seats wide')


letters()
print('written to', OUT)
