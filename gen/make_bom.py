"""Whole-project BOM (both halves + enclosure) -> bom/nrsk-bom.csv and bom/nrsk-bom.md.

Electronics quantities come from the per-side KiCad BOMs (fab/<side>/nrsk-<side>-bom.csv),
enclosure quantities from case/case_report.json and <side>/case_data.json.
"""
import csv
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
SIDES = ('left', 'right')

# value/footprint -> (category, part, spec / suggested part number)
ELEC = {
    ('ATmega32U4-AU', 'Package_QFP:TQFP-44_10x10mm_P0.8mm'): ('MCU', 'マイコン ATmega32U4-AU', 'Microchip ATmega32U4-AU, TQFP-44'),
    ('USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12'): ('コネクタ', 'USB-C レセプタクル', 'HRO TYPE-C-31-M-12（16 ピン、USB 2.0）'),
    ('PJ-320D', 'Connector_Audio:Jack_3.5mm_PJ320D_Horizontal'): ('コネクタ', 'TRRS ジャック 3.5 mm', 'PJ-320D（4 極、表面実装）'),
    ('USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6'): ('保護', 'USB ESD 保護', 'STMicroelectronics USBLC6-2SC6, SOT-23-6'),
    ('16MHz', 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm_HandSoldering'): ('クロック', '水晶振動子 16 MHz', '3225 4 パッド、負荷容量 12〜20 pF'),
    ('500mA', 'Fuse:Fuse_1206_3216Metric'): ('保護', 'ポリスイッチ 500 mA', '1206（例: Bourns MF-NSMF050-2）'),
    ('B5819W', 'Diode_SMD:D_SOD-123'): ('保護', 'ショットキーダイオード', 'B5819W（40 V 1 A）, SOD-123'),
    ('1N4148W', 'Diode_SMD:D_SOD-123'): ('マトリクス', 'スイッチングダイオード', '1N4148W, SOD-123'),
    ('22pF', 'Capacitor_SMD:C_0805_2012Metric'): ('受動部品', 'コンデンサ 22 pF', '0805 C0G 50 V'),
    ('0.1uF', 'Capacitor_SMD:C_0805_2012Metric'): ('受動部品', 'コンデンサ 0.1 µF', '0805 X7R 50 V'),
    ('1uF', 'Capacitor_SMD:C_0805_2012Metric'): ('受動部品', 'コンデンサ 1 µF', '0805 X7R 25 V（UCAP 用）'),
    ('10uF', 'Capacitor_SMD:C_0805_2012Metric'): ('受動部品', 'コンデンサ 10 µF', '0805 X5R 10 V 以上'),
    ('10k', 'Resistor_SMD:R_0805_2012Metric'): ('受動部品', '抵抗 10 kΩ', '0805 1%'),
    ('22', 'Resistor_SMD:R_0805_2012Metric'): ('受動部品', '抵抗 22 Ω', '0805 1%（USB D+/D−）'),
    ('5.1k', 'Resistor_SMD:R_0805_2012Metric'): ('受動部品', '抵抗 5.1 kΩ', '0805 1%（USB-C CC）'),
    ('OLED 128x32', 'nrsk:OLED_0.91in_128x32_I2C'): ('表示', 'OLED モジュール 0.91 インチ', '128×32、SSD1306、I2C、ピン順 GND/VCC/SCL/SDA（基板から約 2 mm 浮かせて半田付け）'),
    ('AS5600-ASOM', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'):
        ('入力', '磁気角度センサー（サムホイール用）', 'ams OSRAM AS5600-ASOM、SOIC-8、I2C 0x36'),
    ('4.7k', 'Resistor_SMD:R_0805_2012Metric'): ('受動部品', '抵抗 4.7 kΩ', '0805 1%（I2C プルアップ）'),
    ('Reset', 'Button_Switch_SMD:SW_SPST_PTS810'): ('スイッチ', 'タクトスイッチ（リセット）', 'C&K PTS810 SJM 250 SMTR LFS'),
}


def read_side_bom(side):
    rows = list(csv.DictReader(open(os.path.join(ROOT, 'fab', side, f'nrsk-{side}-bom.csv'), encoding='utf-8')))
    elec, sockets, widths = Counter(), Counter(), Counter()
    for r in rows:
        q = int(r['Qty'])
        fp = r['Footprint']
        if fp.startswith('nrsk:SW_MX_Hotswap_'):
            w = float(fp.split('_')[-1].rstrip('u'))
            widths[w] += q
            sockets['sw'] += q
        else:
            elec[(r['Value'], fp)] += q
    return elec, sockets, widths


def main():
    out = []   # (category, part, spec, left, right, total, note)
    elec_tot = defaultdict(lambda: [0, 0])
    sw = [0, 0]
    widths = Counter()
    for i, side in enumerate(SIDES):
        e, s, w = read_side_bom(side)
        for k, q in e.items():
            elec_tot[k][i] += q
        sw[i] = s['sw']
        widths.update(w)
    for k, (l, r) in sorted(elec_tot.items(), key=lambda kv: list(ELEC).index(kv[0]) if kv[0] in ELEC else 99):
        cat, part, spec = ELEC.get(k, ('その他', k[0], k[1]))
        out.append((cat, part, spec, l, r, l + r, ''))

    out.append(('キースイッチ', 'MX 互換キースイッチ', '3 ピン / 5 ピンどちらでも可', sw[0], sw[1], sum(sw), ''))
    out.append(('キースイッチ', 'ホットスワップソケット', 'Kailh CPG151101S11（MX 用）', sw[0], sw[1], sum(sw), ''))
    stabs = [sum(1 for k in json.load(open(os.path.join(ROOT, s, 'case_data.json')))['keys'] if k['w'] >= 2) for s in SIDES]
    out.append(('キースイッチ', 'スタビライザ 2 u（PCB マウント）', 'ネジ止め式推奨', stabs[0], stabs[1], sum(stabs),
                '左 Shift、右 Backspace、右 Enter'))
    out.append(('入力', 'サムホイール', '直径 29.2 mm × 厚さ 4.1 mm（case/print/<side>-wheel.stl）', 1, 1, 2,
                '3D プリントか、アルミ削り出しで外注'))
    out.append(('入力', 'ネオジム磁石（径方向着磁）', '直径 6 mm × 厚さ 1.5 mm、ホイール上面のポケットに接着', 1, 1, 2,
                '必ず径方向（diametric）着磁のもの'))
    for w in sorted(widths):
        out.append(('キーキャップ', f'キーキャップ {w:g} u', '', '', '', widths[w], ''))

    rep = json.load(open(os.path.join(ROOT, 'case', 'case_report.json')))
    cov = [rep[s]['cover_screws'] for s in SIDES]
    scr = [rep[s]['screws'] - rep[s]['cover_screws'] for s in SIDES]
    std = [rep[s]['pcb_holes'] for s in SIDES]
    size = {s: '×'.join(f'{v:g}' for v in rep[s]['case_mm']) for s in SIDES}

    def add(cat, part, spec, l, r, note=''):
        out.append((cat, part, spec, l, r, l + r, note))

    add('アクリル版', 'M2 スペーサー 7 mm（メス-メス）', '六角 対辺 3.5〜4 mm、真鍮またはナイロン', std[0], std[1], '基板と底板の間')
    add('アクリル版', 'M2 × 4 mm なべネジ', '基板の上からスペーサーへ', std[0], std[1], '')
    add('筐体共通', 'ゴム足', '直径 8〜10 mm、高さ 3 mm 以上', 4, 4, '底面に出るネジ先・ナットより高いもの')
    add('アクリル版', 'アクリル板 1.5 mm（プレート）', f'左 {size["left"]} mm / 右 {size["right"]} mm', 1, 1,
        'FR4 1.6 mm やアルミ 1.5 mm でも可')
    add('アクリル版', 'アクリル板 3 mm（枠）', '同上の外形、片側 4 枚（frame1〜4）', 4, 4, 'frame1〜3 は差込口の切り欠きあり、frame4 は切り欠きなし')
    add('アクリル版', 'アクリル板 3 mm（底板）', '同上の外形', 1, 1, '')
    add('アクリル版', 'M2 × 20 mm なべネジ', '外周（プレート〜底板を貫通、16.5 mm + ナット）', scr[0], scr[1], '')
    add('アクリル版', 'M2 ナット', '外周ネジ用', scr[0], scr[1], '')
    add('アクリル版', 'M2 × 5 mm なべネジ', '底板の下からスペーサーへ', std[0], std[1], '')
    add('OLED カバー', '透明アクリル板 2 mm', '<side>-oled-cover（DXF/SVG）', 1, 1, 'プレートの上に直接載せる。両方の筐体で共通')
    add('アクリル版', 'M2 × 22 mm なべネジ', 'OLED カバー〜底板を貫通（18.5 mm + ナット）', cov[0], cov[1], '')
    add('アクリル版', 'M2 ナット（OLED カバー用）', '', cov[0], cov[1], '')
    add('3D プリント版', 'M2 ヒートセットインサート', '外径 3.2 mm × 長さ 3 mm（壁上面の穴 φ3.2 × 4 mm）', scr[0] + cov[0], scr[1] + cov[1], '外周と OLED カバーの両方')
    add('3D プリント版', 'M2 × 6 mm なべネジ', 'OLED カバーとプレートをインサートへ固定', cov[0], cov[1], '')
    add('アクリル版', 'M3 × 8 mm なべネジ', 'サムホイールの軸（底板の下から差し込む）', 1, 1, '3D プリント版はトレイの軸を使う')
    add('3D プリント版', 'M2 × 5 mm なべネジ', 'プレートをインサートへ固定', scr[0], scr[1], '')
    add('3D プリント版', 'M2 × 6 mm タッピングネジ', '基板をボス（下穴 φ1.6）へ固定', std[0], std[1], '')
    add('ケーブル', 'TRRS ケーブル（4 極、オス-オス）', '3.5 mm', '', '', '1 本')
    add('ケーブル', 'USB-C ケーブル', 'USB 2.0 以上', '', '', '1 本')
    add('基板', 'プリント基板（2 層、1.6 mm）', 'fab/<side>/nrsk-<side>-gerber.zip', 1, 1, '')

    os.makedirs(os.path.join(ROOT, 'bom'), exist_ok=True)
    head = ['分類', '部品', '仕様・型番の例', '左', '右', '合計', '備考']
    with open(os.path.join(ROOT, 'bom', 'nrsk-bom.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        wr = csv.writer(f)
        wr.writerow(head)
        wr.writerows(out)
    md = '| ' + ' | '.join(head) + ' |\n|' + ' --- |' * len(head) + '\n'
    for r in out:
        md += '| ' + ' | '.join(str(c) for c in r) + ' |\n'
    open(os.path.join(ROOT, 'bom', 'nrsk-bom.md'), 'w').write(md)
    print(md)


if __name__ == '__main__':
    main()
