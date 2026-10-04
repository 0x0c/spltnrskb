"""All renders so far on one numbered grid -> docs/img/render-grid.png.

Run with the project venv:  .venv/bin/python gen/render_grid.py
"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMG = os.path.join(ROOT, 'docs', 'img')
# grouped by how the OLED is mounted; each group is a list of rows (None = empty cell)
GROUPS = [
    ('基板に直付け・プレートの窓から見せる', 'OLED は基板のコネクタに直接半田付け。プレートに窓を開ける', [
        [('render-hero.png', '完成イメージ（全体）'), ('render-detail.png', '完成イメージ（寄り）'),
         ('render-oled.png', '現在の設計：カバーをプレート上に載せる')],
        [('oled-study/user-0.png', 'A  ツライチ 0 mm・目線'), ('oled-study/close-0.png', 'A  ツライチ 0 mm・寄り'), None],
    ]),
    ('外寄せの水平台座', '壁の上に台座を立て、OLED は基板のコネクタから配線で接続', [
        [('oled-study/user-3.5.png', 'B  台座 3.5 mm・目線'), ('oled-study/user-6.5.png', 'C  台座 6.5 mm・目線'),
         ('oled-study/user-13.png', 'D  キートップ高 13 mm・目線')],
        [('oled-study/close-3.5.png', 'B  台座 3.5 mm・寄り'), ('oled-study/close-6.5.png', 'C  台座 6.5 mm・寄り'),
         ('oled-study/close-13.png', 'D  キートップ高 13 mm・寄り')],
    ]),
    ('傾斜台座', 'くさび形の台座で表示面を手前に向ける。配線で接続', [
        [('oled-study/user-tilt-v.png', 'E  縦置き 17° 傾斜・目線'), ('oled-study/user-tilt-h.png', 'F  横置き 50° 傾斜・目線'), None],
        [('oled-study/close-tilt-v.png', 'E  縦置き 17° 傾斜・寄り'), ('oled-study/close-tilt-h.png', 'F  横置き 50° 傾斜・寄り'), None],
    ]),
]
COLS = 3
CELL_W, CELL_H = 1600, 1067        # every image is fitted into a 3:2 cell
GAP, CAPTION = 24, 84
BG, INK, BADGE, MUTED = (246, 246, 244), (30, 32, 36), (242, 77, 0), (110, 114, 120)
FONT = next((f for f in glob.glob('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc') +
             glob.glob('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc')), None)


def font(size):
    return ImageFont.truetype(FONT, size) if FONT else ImageFont.load_default()


def main():
    W = COLS * CELL_W + (COLS + 1) * GAP
    HEAD, GROUP_HEAD = 130, 140
    n_rows = sum(len(rows) for _, _, rows in GROUPS)
    H = HEAD + len(GROUPS) * (GROUP_HEAD + GAP) + n_rows * (CELL_H + CAPTION + GAP) + GAP
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    d.text((GAP, 36), 'nrsk  レンダリング一覧（OLED の取り付け方式別）', font=font(64), fill=INK)
    y = HEAD
    n = 0
    for gi, (title, note, rows) in enumerate(GROUPS, 1):
        y += GAP
        d.rectangle((GAP, y, W - GAP, y + GROUP_HEAD - 12), fill=(232, 233, 230))
        d.rectangle((GAP, y, GAP + 14, y + GROUP_HEAD - 12), fill=BADGE)
        d.text((GAP + 40, y + 14), f'グループ {gi}　{title}', font=font(54), fill=INK)
        d.text((GAP + 40, y + 82), note, font=font(34), fill=MUTED)
        y += GROUP_HEAD
        for row in rows:
            for c, item in enumerate(row):
                if item is None:
                    continue
                path, caption = item
                n += 1
                x = GAP + c * (CELL_W + GAP)
                im = Image.open(os.path.join(IMG, path)).convert('RGB')
                im.thumbnail((CELL_W, CELL_H), Image.LANCZOS)
                cell = Image.new('RGB', (CELL_W, CELL_H), (255, 255, 255))
                cell.paste(im, ((CELL_W - im.width) // 2, (CELL_H - im.height) // 2))
                sheet.paste(cell, (x, y))
                label = str(n)
                d.rounded_rectangle((x, y + CELL_H + 14, x + 72, y + CELL_H + 72), radius=12, fill=BADGE)
                tw = d.textlength(label, font=font(42))
                d.text((x + 36 - tw / 2, y + CELL_H + 18), label, font=font(42), fill=(255, 255, 255))
                d.text((x + 90, y + CELL_H + 20), caption, font=font(42), fill=INK)
            y += CELL_H + CAPTION + GAP
    out = os.path.join(IMG, 'render-grid.png')
    sheet.save(out, optimize=True)
    sheet.save(out.replace('.png', '.jpg'), quality=93, subsampling=0)
    print('wrote', out, sheet.size, n, 'images')


if __name__ == '__main__':
    main()
