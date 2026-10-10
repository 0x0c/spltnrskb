"""Thumbwheel encoder study on one sheet -> docs/img/encoder-study/sheet.jpg.

Run with the project venv:  .venv/bin/python gen/encoder_sheet.py
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMG = os.path.join(ROOT, 'docs', 'img', 'encoder-study')
ROWS = [
    [('section-left-current.png', '現在：AS5600＋磁石、ボールプランジャー（断面）'),
     ('section-left-encoder.png', '提案：Alps EC05E1220401、六角ピンで駆動（断面）')],
    [('exploded-left.png', '提案：分解図（トレイ、ホイール、エンコーダー、基板、角キャップとプレート）'),
     ('exterior-left.png', '提案：外観（左上の角）')],
]
CELL_W = 1400
CELL_H = CELL_W * 2 // 3
GAP, CAPTION = 24, 72
BG, INK = (246, 246, 244), (30, 32, 36)
FONT = next(iter(glob.glob('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc')), None)


def fit(im):
    im = im.convert('RGBA')
    s = min(CELL_W / im.width, CELL_H / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    cell = Image.new('RGBA', (CELL_W, CELL_H), (255, 255, 255, 255))
    cell.alpha_composite(im, ((CELL_W - im.width) // 2, (CELL_H - im.height) // 2))
    return cell.convert('RGB')


def main():
    font = ImageFont.truetype(FONT, 30) if FONT else ImageFont.load_default()
    cols = max(len(r) for r in ROWS)
    sheet = Image.new('RGB', (GAP + cols * (CELL_W + GAP), GAP + len(ROWS) * (CELL_H + CAPTION + GAP)), BG)
    d = ImageDraw.Draw(sheet)
    for ri, row in enumerate(ROWS):
        for ci, (name, caption) in enumerate(row):
            x, y = GAP + ci * (CELL_W + GAP), GAP + ri * (CELL_H + CAPTION + GAP)
            sheet.paste(fit(Image.open(os.path.join(IMG, name))), (x, y))
            d.text((x + 4, y + CELL_H + 18), caption, fill=INK, font=font)
    out = os.path.join(IMG, 'sheet.jpg')
    sheet.save(out, quality=88)
    print('wrote', out)


if __name__ == '__main__':
    main()
