"""Comparison sheet of the OLED study renders -> docs/img/oled-study/sheet.png."""
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'docs', 'img', 'oled-study')
VARIANTS = [
    ('0', 'A  ツライチ（0 mm）', '今の位置。窓にレンズをはめ込む'),
    ('3.5', 'B  台座 3.5 mm', '壁の上へ外寄せ、配線で接続'),
    ('6.5', 'C  台座 6.5 mm', '壁の上へ外寄せ、配線で接続'),
    ('13', 'D  キートップと同じ（13 mm）', '壁の上へ外寄せ、配線で接続'),
    ('tilt-v', 'E  縦置き・17° 傾斜', '内側上の角。手前 1.5 mm → 奥 12.6 mm'),
    ('tilt-h', 'F  横置き・50° 傾斜', 'Fキー列の奥。横書き表示'),
]
plt.rcParams['font.family'] = ['Hiragino Sans', 'Hiragino Kaku Gothic ProN', 'sans-serif']
fig, axes = plt.subplots(len(VARIANTS), 2, figsize=(14, 4.1 * len(VARIANTS)))
for row, (tag, title, note) in zip(axes, VARIANTS):
    for ax, kind in zip(row, ('user', 'close')):
        ax.imshow(plt.imread(os.path.join(D, f'{kind}-{tag}.png')))
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(False)
    row[0].set_title(f'{title}   —   {note}', loc='left', fontsize=13, pad=8)
    row[1].set_title('寄り', loc='left', fontsize=11, color='#666', pad=8)
fig.suptitle('OLED の高さ・角度の比較（左: 座った目線、右: 寄り）', fontsize=16, y=0.997)
plt.tight_layout(rect=(0, 0, 1, 0.99))
fig.savefig(os.path.join(D, 'sheet.png'), dpi=90)
print('wrote', os.path.join(D, 'sheet.png'))
