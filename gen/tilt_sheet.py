"""Comparison sheet and table of the tilt-leg study -> docs/img/tilt-study/sheet.jpg and table.md.

Reads the renders of gen/render_tilt.py and case/preview/tilt-variants/variants.json (gen/tilt_variants.py).
"""
import json
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.gridspec import GridSpec  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'docs', 'img', 'tilt-study')
VAR = json.load(open(os.path.join(ROOT, 'case', 'preview', 'tilt-variants', 'variants.json')))
# what the model does not say: hardware per seat and per leg, switching, storage
MECHS = {
    'M': dict(per_seat='磁石 1', per_leg='磁石 1、ゴム足 1', switch='引き抜いて別の脚をかぶせる（工具なし）',
              store='要る（片側 9 本）'),
    'F': dict(per_seat='M2 ネジとナット 1 組', per_leg='—', switch='脚を起こす（工具なし）', store='要らない'),
    'S': dict(per_seat='M3 インサート 1、M3 皿ネジ 1', per_leg='ゴム足 1',
              switch='皿ネジを外して別の脚を留める（ドライバー）', store='要る（片側 9 本）'),
}
ITEMS = [('seats', '脚の座'), ('angle', '角度'), ('support', '支持多角形'), ('plug', 'プラグ'), ('legs', '脚の形')]


def rows():
    out = []
    for key, info in MECHS.items():
        L, R = VAR[key]['left'], VAR[key]['right']
        angles = sorted(int(a) for a in L['angles'])
        seats = sum(s is not None for s in L['seats'].values())
        margin = [min(v['margin'] for v in r['angles'].values()) for r in (L, R)]
        err = max(v['angle_err'] for r in (L, R) for v in r['angles'].values())
        failed = [name for item, name in ITEMS if not (L['check'][item] and R['check'][item])]
        out.append(dict(
            key=key, label=L['label'], steps='、'.join(f'{a}°' for a in angles),
            parts=f"脚の座 {seats} か所（{info['per_seat']}）、印刷の脚 {seats * len(angles)} 本"
                  + (f"（1 本ごとに {info['per_leg']}）" if info['per_leg'] != '—' else ''),
            margin=f'左 {margin[0]:.1f} mm、右 {margin[1]:.1f} mm', err=f'{err:.2f}°',
            checks='すべて通る' if not failed else '通らない：' + '、'.join(failed),
            switch=info['switch'], store=info['store']))
    return out


def table(rs):
    head = ['案', '角度の段', '片側の部品', '支持の余裕（全キーの最小）', '角度の誤差', '検査', '切り替え', '外した脚の保管']
    lines = ['| ' + ' | '.join(head) + ' |', '| ' + ' | '.join('---' for _ in head) + ' |']
    for r in rs:
        lines.append('| ' + ' | '.join([f"{r['label']}（{r['key']}）", r['steps'], r['parts'], r['margin'], r['err'],
                                          r['checks'], r['switch'], r['store']]) + ' |')
    note = ('支持の余裕は、もっとも外側のキーの中心から支持多角形の辺までの距離（負は外）。'
            '印刷のサポート材は 3 案とも要らない（底面から開く穴と溝の天井は、ブリッジで印刷できる幅）。')
    open(os.path.join(D, 'table.md'), 'w').write('\n'.join(lines) + '\n\n' + note + '\n')
    print('wrote', os.path.join(D, 'table.md'))


def sheet(rs):
    plt.rcParams['font.family'] = ['Hiragino Sans', 'sans-serif']
    fig = plt.figure(figsize=(18, 10.5 * len(rs)))
    gs = GridSpec(3 * len(rs), 12, figure=fig, height_ratios=[0.6, 1.55, 2.0] * len(rs), hspace=0.25, wspace=0.08,
                  top=0.975, bottom=0.01, left=0.01, right=0.99)
    blank = None
    for i, r in enumerate(rs):
        title = fig.add_subplot(gs[3 * i, :])
        title.axis('off')
        title.text(0, 0.65, f"{r['key']}  {r['label']}", fontsize=20, weight='bold', va='center')
        title.text(0, 0.05, f"段 {r['steps']}　／　{r['parts']}　／　支持の余裕 {r['margin']}　／　{r['checks']}",
                   fontsize=12, color='#444', va='center')
        for j, deg in enumerate((0, 3, 6, 9)):
            ax = fig.add_subplot(gs[3 * i + 1, 3 * j:3 * j + 3])
            path = os.path.join(D, f"{r['key']}-side-{deg}.jpg")
            if os.path.exists(path):
                img = plt.imread(path)
                blank = img * 0 + 255
                ax.imshow(img)
            else:                     # same frame as the other views, so the row stays aligned
                ax.imshow(blank if blank is not None else [[[255, 255, 255]]])
                ax.text(0.5, 0.5, 'この段はない', ha='center', va='center', fontsize=14, color='#999',
                        transform=ax.transAxes)
            ax.set_title(f'{deg}°（外側から）', loc='left', fontsize=11, color='#555')
            ax.axis('off')
        for j, (shot, label) in enumerate((('bottom-0', '底面：脚なし'), ('bottom-legs', '底面：脚あり'),
                                           ('back', f"奥の寄り：{r['steps'].split('、')[-1]}"))):
            ax = fig.add_subplot(gs[3 * i + 2, 4 * j:4 * j + 4])
            ax.imshow(plt.imread(os.path.join(D, f"{r['key']}-{shot}.jpg")))
            ax.set_title(label, loc='left', fontsize=11, color='#555')
            ax.axis('off')
    fig.suptitle('チルト脚の 3 案（左半分）', fontsize=24, y=0.995)
    fig.savefig(os.path.join(D, 'sheet.jpg'), dpi=70, bbox_inches='tight', pil_kwargs=dict(quality=85))
    print('wrote', os.path.join(D, 'sheet.jpg'))


if __name__ == '__main__':
    rs = rows()
    table(rs)
    sheet(rs)
