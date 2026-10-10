"""Case variants A and B side by side (whole, OLED, wheel) -> docs/img/render-compare-ab.jpg.

The six renders come from gen/render_compare.sh. Run with the project venv:  .venv/bin/python gen/compare_ab.py
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMG = os.path.join(ROOT, 'docs', 'img')
COLUMNS = [('A  トレイ + 透明アクリルのプレート（上からスリムヘッド）', '-top-acrylic-lowpan'),
           ('B  全部 3D プリント（底からネジ止め）', '-top-print')]
SHOTS = ('hero', 'oled', 'wheel-left')
CELL_W, CELL_H = 1200, 800
GAP, HEADER = 24, 90
BG, INK = (246, 246, 244), (30, 32, 36)
FONT = next(iter(glob.glob('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc')), None)


def main():
    font = ImageFont.truetype(FONT, 40) if FONT else ImageFont.load_default()
    w = GAP + len(COLUMNS) * (CELL_W + GAP)
    h = HEADER + len(SHOTS) * (CELL_H + GAP)
    sheet = Image.new('RGB', (w, h), BG)
    d = ImageDraw.Draw(sheet)
    for c, (title, suffix) in enumerate(COLUMNS):
        x = GAP + c * (CELL_W + GAP)
        d.text((x, 28), title, font=font, fill=INK)
        for r, shot in enumerate(SHOTS):
            im = Image.open(os.path.join(IMG, f'render-{shot}{suffix}.png')).convert('RGB')
            sheet.paste(im.resize((CELL_W, CELL_H), Image.LANCZOS), (x, HEADER + r * (CELL_H + GAP)))
    out = os.path.join(IMG, 'render-compare-ab.jpg')
    sheet.save(out, quality=90)
    print('wrote', out, sheet.size)


if __name__ == '__main__':
    main()
