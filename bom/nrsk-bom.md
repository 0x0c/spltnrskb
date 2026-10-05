> 単価・在庫は 2026-10-04 時点の参考値。リンク先はすべて開いて型番と仕様を確認済み。

| 分類 | 部品 | 仕様 | 左 | 右 | 合計 | メーカー型番・商品名 | 購入先 | 単価（参考） | URL | 備考 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MCU | マイコン RP2040 | Raspberry Pi RP2040、QFN-56 7×7 mm | 1 | 1 | 2 | Raspberry Pi RP2040 | LCSC C2040 | US$1.00 | [リンク](https://www.lcsc.com/product-detail/C2040.html) |  |
| MCU | QSPI フラッシュ 16 MB | Winbond W25Q128JVSIQ、SOIC-8 208 mil | 1 | 1 | 2 | Winbond W25Q128JVSIQ | LCSC C113767 | US$2.52 | [リンク](https://www.lcsc.com/product-detail/C113767.html) | よく使われる C97521 は同じ型番だが確認時に在庫切れ |
| MCU | 　└ 代替 |  |  |  |  | Winbond W25Q16JVSSIQ（2 MB、同じ 208 mil） | LCSC C82317 | US$1.07 | [リンク](https://www.lcsc.com/product-detail/C82317.html) | 容量は小さいがキーボードには十分 |
| 電源 | LDO 3.3 V | Diodes AP2112K-3.3TRG1（600 mA）、SOT-23-5 | 1 | 1 | 2 | Diodes AP2112K-3.3TRG1 | LCSC C51118 | US$0.17 | [リンク](https://www.lcsc.com/product-detail/C51118.html) |  |
| コネクタ | USB-C レセプタクル | HRO TYPE-C-31-M-12（16 ピン、USB 2.0） | 1 | 1 | 2 | Korean Hroparts TYPE-C-31-M-12 | LCSC C165948 | US$0.17 | [リンク](https://www.lcsc.com/product-detail/C165948.html) |  |
| コネクタ | TRRS ジャック 3.5 mm | PJ-320D（4 極、表面実装） | 1 | 1 | 2 | SHOU HAN PJ-320D | LCSC C431535 | US$0.05 | [リンク](https://www.lcsc.com/product-detail/C431535.html) | LCSC の EasyEDA フットプリントと照合済み：固定ピン間隔 7.0 mm が一致し、端子位置の差は 0.1 mm 以内で KiCad の PJ320D パッドに載る |
| コネクタ | 　└ 代替 |  |  |  |  | Korean Hroparts PJ-320D-4A | LCSC C95562 | US$0.11 | [リンク](https://www.lcsc.com/product-detail/C95562.html) | 代替。同じく固定ピン間隔 7.0 mm が一致し、端子位置の差は 0.1 mm 以内 |
| 保護 | USB ESD 保護 | STMicroelectronics USBLC6-2SC6, SOT-23-6 | 1 | 1 | 2 | STMicroelectronics USBLC6-2SC6 | LCSC C7519 | US$0.18 | [リンク](https://www.lcsc.com/product-detail/C7519.html) |  |
| クロック | 水晶振動子 12 MHz | 3225 4 パッド、負荷容量 10 pF 前後（15 pF のコンデンサと組み合わせる） | 1 | 1 | 2 | Abracon ABM8-272-T3（CL 10 pF） | LCSC C20625731 | US$0.63 | [リンク](https://www.lcsc.com/product-detail/C20625731.html) | Raspberry Pi のリファレンスと同じ部品。安価な YXC X322512MSB4SI（C9002）は CL 20 pF なので 15 pF のコンデンサとは合わない |
| 保護 | ポリスイッチ 500 mA | 1206（例: Bourns MF-NSMF050-2） | 1 | 1 | 2 | Bourns MF-NSMF050-2 | LCSC C75464 | US$0.04 | [リンク](https://www.lcsc.com/product-detail/C75464.html) |  |
| 保護 | ショットキーダイオード | B5819W（40 V 1 A）, SOD-123 | 1 | 1 | 2 | JSCJ B5819W SL | LCSC C8598 | US$0.03 | [リンク](https://www.lcsc.com/product-detail/C8598.html) |  |
| マトリクス | スイッチングダイオード | 1N4148W, SOD-123 | 44 | 48 | 92 | 1N4148W（SOD-123） | LCSC C81598 | US$0.012 | [リンク](https://www.lcsc.com/product-detail/C81598.html) |  |
| 受動部品 | コンデンサ 15 pF | 0805 C0G 50 V（水晶の負荷容量） | 2 | 2 | 4 | YAGEO CC0805JRNPO9BN150 | LCSC C107110 | US$0.0096 | [リンク](https://www.lcsc.com/product-detail/C107110.html) |  |
| 受動部品 | コンデンサ 0.1 µF | 0805 X7R 50 V | 12 | 12 | 24 | YAGEO CC0805KRX7R9BB104 | LCSC C49678 | US$0.019 | [リンク](https://www.lcsc.com/product-detail/C49678.html) |  |
| 受動部品 | コンデンサ 1 µF | 0805 X7R 25 V 以上（LDO、RP2040 の内蔵レギュレータ、AS5600） | 5 | 5 | 10 | Samsung CL21B105KBFNNNE（50 V） | LCSC C28323 | US$0.04 | [リンク](https://www.lcsc.com/product-detail/C28323.html) |  |
| 受動部品 | コンデンサ 10 µF | 0805 X5R 10 V 以上 | 1 | 1 | 2 | Samsung CL21A106KAYNNNE（X5R 25 V） | LCSC C15850 | US$0.066 | [リンク](https://www.lcsc.com/product-detail/C15850.html) |  |
| 受動部品 | 抵抗 10 kΩ | 0805 1% | 2 | 2 | 4 | UNI-ROYAL 0805W8F1002T5E | LCSC C17414 | US$0.0034 | [リンク](https://www.lcsc.com/product-detail/C17414.html) |  |
| 受動部品 | 抵抗 27 Ω | 0805 1%（USB D+/D−） | 2 | 2 | 4 | YAGEO RC0805FR-0727RL | LCSC C163408 | US$0.0078 | [リンク](https://www.lcsc.com/product-detail/C163408.html) | 確認時の在庫 4,900 |
| 受動部品 | 抵抗 1 kΩ | 0805 1%（水晶の XOUT 直列、BOOTSEL） | 2 | 2 | 4 | UNI-ROYAL 0805W8F1001T5E | LCSC C17513 | US$0.0041 | [リンク](https://www.lcsc.com/product-detail/C17513.html) |  |
| 受動部品 | 抵抗 5.1 kΩ | 0805 1%（USB-C CC） | 2 | 2 | 4 | UNI-ROYAL 0805W8F5101T5E | LCSC C27834 | US$0.0056 | [リンク](https://www.lcsc.com/product-detail/C27834.html) |  |
| 表示 | OLED モジュール 0.91 インチ | 128×32、SSD1306、I2C、3.3 V、ピン順 GND/VCC/SCL/SDA（ガラス上面を基板から 2.5 mm に） | 1 | 1 | 2 | OLED モジュール（0.91 インチ 128×32、SSD1306、ピンソケット付き） | 遊舎工房 | ¥825 | [リンク](https://shop.yushakobo.jp/products/oled) | 商品ページにピン順の記載なし。GND/VCC/SCL/SDA であることを現物のシルクで確認 |
| 入力 | 磁気角度センサー（サムホイール用） | ams OSRAM AS5600-ASOM、SOIC-8、I2C 0x36、3.3 V | 1 | 1 | 2 | ams OSRAM AS5600-ASOM | LCSC C79815 | US$1.77 | [リンク](https://www.lcsc.com/product-detail/C79815.html) |  |
| 受動部品 | 抵抗 4.7 kΩ | 0805 1%（I2C プルアップ） | 2 | 2 | 4 | UNI-ROYAL 0805W8F4701T5E | LCSC C17673 | US$0.0051 | [リンク](https://www.lcsc.com/product-detail/C17673.html) |  |
| スイッチ | タクトスイッチ（リセット） | C&K PTS810 SJM 250 SMTR LFS（2 回押しで書き込みモード） | 1 | 1 | 2 | C&K PTS810SJM250SMTRLFS | LCSC C116501 | US$0.58 | [リンク](https://www.lcsc.com/product-detail/C116501.html) |  |
| スイッチ | BOOTSEL パッド | 基板のはんだジャンパー（部品なし）。ピンセットで短絡しながら USB を挿すと書き込みモード | 1 | 1 | 2 | 部品なし（基板のはんだジャンパー） | — |  |  |  |
| キースイッチ | MX 互換キースイッチ | 3 ピン / 5 ピンどちらでも可 | 44 | 48 | 92 | Kailh Box V2 Red（リニア、5 ピン） | 遊舎工房 | ¥2,117 / 35 個 | [リンク](https://shop.yushakobo.jp/products/4264) | 92 個要るので 3 パック。確認時の在庫は 6 パックと少ない。遊舎工房の他の MX 互換スイッチでも可 |
| キースイッチ | 　└ 代替 |  |  |  |  | Kailh Super Speed Silver（リニア、3 ピン） | 遊舎工房 | ¥1,540 / 35 個 | [リンク](https://shop.yushakobo.jp/products/4280) | 在庫少 |
| キースイッチ | ホットスワップソケット | Kailh CPG151101S11（MX 用） | 44 | 48 | 92 | Kailh CPG151101S11-16（スイッチソケット MX 型） | 遊舎工房 | ¥187 / 10 個 | [リンク](https://shop.yushakobo.jp/products/a01ps) | 「MX 型」を選ぶ（Choc 型と取り違えない）。10 パック |
| キースイッチ | スタビライザ 2 u（PCB マウント） | ネジ止め式推奨 | 1 | 2 | 3 | GDK-02 Pre-lubed PCB Mount Stabilizer | 遊舎工房 | ¥770 / セット | [リンク](https://shop.yushakobo.jp/products/11952) | 左 Shift、右 Backspace、右 Enter；1 セットで 2 u が 4 個分。1 セットで足りる |
| 入力 | サムホイール | 直径 29.2 mm × 厚さ 4.1 mm、外周に 32 山のクリック用の歯（case/print/<side>-wheel.stl） | 1 | 1 | 2 | case/print/<side>-wheel.stl | 自作（3D プリント） |  |  | 3D プリントか、アルミ削り出しで外注 |
| 入力 | ネオジム磁石（径方向着磁） | 直径 6 mm × 厚さ 1.5 mm、ホイール上面のポケットに接着 | 1 | 1 | 2 | Radial Magnets 9042（φ6 × 2.5 mm、Diametric） | DigiKey | ¥105 | [リンク](https://www.digikey.jp/ja/products/detail/radial-magnets-inc/9042/5640338) | 必ず径方向（diametric）着磁のもの；厚さ 2.5 mm で、現在のポケット（深さ 1.6 mm）には入らない。国内で φ6 × 1.5 mm の径方向着磁品は在庫が見つからなかった |
| キーキャップ | キーキャップ 1 u |  |  |  | 81 | DSA 無刻印キーキャップ 1 u（PBT、22 色） | 遊舎工房 | ¥55 | [リンク](https://shop.yushakobo.jp/products/dsa-blank-keycaps) |  |
| キーキャップ | キーキャップ 1.25 u |  |  |  | 5 | Signature Plastics DSA 1.25 u | spkeyboards.com（米国） | US$3.50 | [リンク](https://spkeyboards.com/products/dsa-1-25-space) | 国内で DSA 1.25 u が見つからなかったため海外通販。輸入時に関税・消費税 |
| キーキャップ | キーキャップ 1.5 u |  |  |  | 2 | DSA 無刻印キーキャップ 1.5 u（白・黒・灰・緑・赤） | 遊舎工房 | ¥220 | [リンク](https://shop.yushakobo.jp/products/10731) |  |
| キーキャップ | キーキャップ 1.75 u |  |  |  | 1 | Signature Plastics DSA 1.75 u | spkeyboards.com（米国） | US$3.50 | [リンク](https://spkeyboards.com/collections/individual-keys/products/sp-dsa-1-75-space) |  |
| キーキャップ | キーキャップ 2 u |  |  |  | 1 | DSA 無刻印キーキャップ 2 u（白・黒） | 遊舎工房 | ¥220 | [リンク](https://shop.yushakobo.jp/products/11443) |  |
| キーキャップ | キーキャップ 2.25 u |  |  |  | 2 | Signature Plastics DSA 2.25 u（スタビ対応） | spkeyboards.com（米国） | US$4.00 | [リンク](https://spkeyboards.com/products/sp-dsa-2-25-space-single-keycap) |  |
| アクリル版 | M2 スペーサー 7 mm（メス-メス） | 六角 対辺 3.5〜4 mm、真鍮またはナイロン | 8 | 8 | 16 | 廣杉計器 ASB-2007E（黄銅、両メネジ） | MonotaRO | ¥1,978 / 50 個 | [リンク](https://www.monotaro.com/p/1111/2937/) | 基板と底板の間 |
| アクリル版 | 　└ 代替 |  |  |  |  | 黄銅スペーサー（六角）M2 7 mm | 遊舎工房 | ¥385 / 10 個 | [リンク](https://shop.yushakobo.jp/products/a0800r2?variant=37665434042529) | 少量向け |
| アクリル版 | M2 × 4 mm なべネジ | 基板の上からスペーサーへ | 8 | 8 | 16 | なべ小ねじ M2 × 4 | 遊舎工房 | ¥220 / 50 本 | [リンク](https://shop.yushakobo.jp/products/a0800n2?variant=37665432961185) |  |
| アクリル版 | 　└ 代替 |  |  |  |  | 大阪魂 ナベ頭小ねじ M2 × 4（ステンレス） | MonotaRO | ¥1,099 / 160 本 | [リンク](https://www.monotaro.com/p/0550/6907/) |  |
| 筐体共通 | ゴム足 | 直径 8〜10 mm、高さ 3 mm 以上 | 4 | 4 | 8 | 3M クッションゴム 丸形 CS-02（φ9.5 × 3.8 mm） | MonotaRO | ¥483 / 18 個 | [リンク](https://www.monotaro.com/p/4525/7232/) | 底面に出るネジ先・ナットより高いもの |
| 筐体共通 | 　└ 代替 |  |  |  |  | 栃木屋 クリアバンポン TM-180-303（φ11.2 × 5.1 mm） | MonotaRO | ¥48 / 個 | [リンク](https://www.monotaro.com/p/4262/7707/) |  |
| 筐体共通 | 透明アクリル板 1.5 mm（プレート） | <side>-plate、左 189.6×142.3 mm / 右 216.6×142.3 mm | 1 | 1 | 2 | アクリル板 DXF 切削（図面で WEB オーダー） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/estimate-drawing) | 3D プリント版もアクリル版もこのプレートを使う；透明 1.5 mm で注文。切断線どうしの間隔 3 mm 未満は不可 |
| アクリル版 | マットクリア アクリル板 3 mm（枠） | 同上の外形、片側 4 枚（frame1〜4） | 4 | 4 | 8 | アクリル板キャスト 片面マットクリア（パラグラス C1 P） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3481) | frame1〜3 は差込口の切り欠きあり、frame4 は切り欠きなし；2 / 3 / 5 mm。図面 WEB オーダー（https://www.hazaiya.co.jp/estimate-drawing）で DXF から切り出し |
| アクリル版 | マットクリア アクリル板 3 mm（底板） | 同上の外形 | 1 | 1 | 2 | アクリル板キャスト 片面マットクリア（パラグラス C1 P） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3481) | 2 / 3 / 5 mm。図面 WEB オーダー（https://www.hazaiya.co.jp/estimate-drawing）で DXF から切り出し |
| アクリル版 | M2 × 20 mm なべネジ | 外周（プレート〜底板を貫通、16.5 mm + ナット） | 10 | 12 | 22 | OHSATO ナベ頭小ねじ M2 × 20（ステンレス） | MonotaRO | ¥329 / 50 本 | [リンク](https://www.monotaro.com/p/1714/1900/) |  |
| アクリル版 | M2 ナット | 外周ネジ用 | 10 | 12 | 22 | 大阪魂 六角ナット 1 種 M2（SUS304） | MonotaRO | ¥164 / 20 個 | [リンク](https://www.monotaro.com/p/2876/3624/) |  |
| アクリル版 | 　└ 代替 |  |  |  |  | 廣杉計器 UNT-02 | MonotaRO | ¥1,428 / 50 個 | [リンク](https://www.monotaro.com/p/1148/5784/) |  |
| アクリル版 | M2 × 5 mm なべネジ | 底板の下からスペーサーへ | 8 | 8 | 16 | なべ小ねじ M2 × 5 | 遊舎工房 | ¥220 / 50 本 | [リンク](https://shop.yushakobo.jp/products/a0800n2?variant=37665432993953) |  |
| アクリル版 | 　└ 代替 |  |  |  |  | 大阪魂 ナベ頭小ねじ M2 × 5（ステンレス） | MonotaRO | ¥1,099 / 160 本 | [リンク](https://www.monotaro.com/p/0550/6916/) |  |
| OLED カバー | ハーフミラー アクリル板 2 mm | <side>-oled-cover（DXF/SVG）、プレートの窓にはめ込み、上面をプレートと面一 | 1 | 1 | 2 | アクリル板キャスト ハーフミラー 30%（三菱 MRH-001T-30） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3373) | OLED のガラス面に載せる。両方の筐体で共通；2 / 3 / 5 mm。図面 WEB オーダーで DXF から切り出し。1.5 mm のアクリル製ハーフミラーはメーカーにもない |
| OLED カバー | 　└ 代替 |  |  |  |  | アクリルハーフミラー板 フリーカット（2 mm、透過 30%） | アクリ屋ドットコム | 見積 | [リンク](https://www.acry-ya.com/products/detail/113/) | 最小 10 × 10 mm から |
| OLED カバー | 透明両面テープ 厚さ 0.5 mm | カバーと OLED のガラス面、カバーの縁が載る壁の上面に貼る |  |  |  | 3M スコッチ はがせる両面テープ 超透明 KRT-15（幅 15 × 1.5 m × 厚さ 0.5 mm） | カインズ |  | [リンク](https://www.cainz.com/g/4547452982974.html) | 少量；はがせるタイプなので OLED を交換できる |
| 3D プリント版 | M2 ヒートセットインサート | 外径 3.2 mm × 長さ 3 mm（壁上面の穴 φ3.2 × 4 mm） | 10 | 12 | 22 | 廣杉計器 HSB-203030 ビットインサート（M2 × 3、外径 3〜3.3） | MonotaRO | ¥2,198 / 50 個 | [リンク](https://www.monotaro.com/p/1138/6698/) | 熱圧入用かはページに記載なし。下穴は現物に合わせて調整 |
| 3D プリント版 | 　└ 代替 |  |  |  |  | Prusa Heat Set Inserts M2 short | Prusa Research | US$11.99 / 100 個 | [リンク](https://www.prusa3d.com/ja/product/heat-set-inserts-m2-short-100-pcs/) | 3D プリント用。寸法の記載なし |
| アクリル版 | M3 × 8 mm なべネジ | サムホイールの軸（底板の下から差し込む） | 1 | 1 | 2 | OHSATO ナベ頭小ねじ M3 × 8（ステンレス） | MonotaRO | ¥175 / 50 本 | [リンク](https://www.monotaro.com/p/1714/1988/) | 3D プリント版はトレイの軸を使う |
| 筐体共通 | M3 ボールプランジャー | M3 × 0.5、長さ 6 mm、ボール φ1.5、ストローク 0.5 mm、後端に六角穴 | 1 | 1 | 2 | NBK PAFS-3-L（ステンレス、L 6、1 → 2 N） | MonotaRO | ¥395 | [リンク](https://www.monotaro.com/p/2212/2932/) | ホイールのクリック。ねじ込み量でクリックの重さを調整；軽め。重くしたいときは PAFS-3-M（1.5 → 2.9 N） |
| 筐体共通 | 　└ 代替 |  |  |  |  | NBK PAFS-3-M（ステンレス、L 6、1.5 → 2.9 N） | MonotaRO | ¥395 | [リンク](https://www.monotaro.com/p/2212/2957/) |  |
| 筐体共通 | 　└ 代替 |  |  |  |  | MISUMI BPK3（ショートタイプ、L 5、ボール φ2、1 → 2 N） | MISUMI | ¥627 | [リンク](https://jp.misumi-ec.com/vona2/detail/110302018310/) | ブロックの穴はそのまま使える（長さが 1 mm 短い） |
| アクリル版 | プランジャーブロック | 3D プリント（case/print/<side>-detent.stl） | 1 | 1 | 2 | case/print/<side>-detent.stl | 自作（3D プリント） |  |  | 3D プリント版はトレイと一体；PETG 推奨。M3 の穴はタップを立てるか、プランジャーでねじを切りながら入れる |
| アクリル版 | M2 × 6 mm タッピングネジ（ブロック用） | 底板の下からプランジャーブロックへ | 2 | 2 | 4 | 大阪魂 ナベタッピンねじ 2 種 B-0 M2 × 6（ステンレス） | MonotaRO | ¥593 / 50 本 | [リンク](https://www.monotaro.com/p/4171/8022/) |  |
| アクリル版 | 　└ 代替 |  |  |  |  | エスコ EA949AL-103 | MonotaRO | ¥435 / 40 本 | [リンク](https://www.monotaro.com/p/5065/8362/) |  |
| 3D プリント版 | M2 × 5 mm スリムヘッド小ねじ（薄頭なべ） | 頭 φ4.0 × 高さ 0.5 mm、A・B のプレートをインサートへ固定 | 10 | 12 | 22 | 大阪魂 (+)スリムヘッド小ねじ ステンレス M2 × 5（φ4 × 0.5、注文コード 41746704） | MonotaRO | ¥593 / 7 本 | [リンク](https://www.monotaro.com/p/4174/6704/) |  |
| 3D プリント版 | 　└ 代替 |  |  |  |  | スリムヘッド小ねじ M2 × 5（鉄、三価ホワイト）A0800S2 | 遊舎工房 | ¥880 / 50 本 | [リンク](https://shop.yushakobo.jp/products/a0800s2) | 寸法の記載なし |
| 3D プリント版 | 　└ 代替 |  |  |  |  | MISUMI E-GCBSTSR2-5 超極低頭ボルト 六角穴（φ4 × 0.5、SUSXM7） | MISUMI | ¥88 / 本 | [リンク](https://jp.misumi-ec.com/vona2/detail/110311091879/?HissuCode=E-GCBSTSR2-5) | 六角穴 1.3 mm。推奨トルク 0.16 N·m |
| 3D プリント版 | M2 × 6 mm タッピングネジ | 基板をボス（下穴 φ1.6）へ固定 | 8 | 8 | 16 | 大阪魂 ナベタッピンねじ 2 種 B-0 M2 × 6（ステンレス） | MonotaRO | ¥593 / 50 本 | [リンク](https://www.monotaro.com/p/4171/8022/) |  |
| 3D プリント版 | 　└ 代替 |  |  |  |  | エスコ EA949AL-103 | MonotaRO | ¥435 / 40 本 | [リンク](https://www.monotaro.com/p/5065/8362/) |  |
| 3D プリント版 | ポートキャップ | 3D プリント（case/print/<side>-port-caps.stl、USB-C 用と TRRS 用の 2 個） | 2 | 2 | 4 | case/print/<side>-port-caps.stl | 自作（3D プリント） |  |  | トレイ、角キャップと同じ材料で印刷 |
| ケーブル | TRRS ケーブル（4 極、オス-オス） | 3.5 mm |  |  |  | TRRS ケーブル 0.3 m | 遊舎工房 | ¥330 | [リンク](https://shop.yushakobo.jp/products/8023) | 1 本 |
| ケーブル | 　└ 代替 |  |  |  |  | TRRS ケーブル 0.8 m（メタル） | 遊舎工房 | ¥1,100 | [リンク](https://shop.yushakobo.jp/products/8111) |  |
| ケーブル | USB-C ケーブル | USB 2.0 以上 |  |  |  | USB Type-C to C 1.0 m | 遊舎工房 | ¥440 | [リンク](https://shop.yushakobo.jp/products/11426) | 1 本 |
| ケーブル | 　└ 代替 |  |  |  |  | USB Type-A to C 1.0 m | 遊舎工房 | ¥330 | [リンク](https://shop.yushakobo.jp/products/8283) |  |
| 基板 | プリント基板（2 層、1.6 mm） | fab/<side>/nrsk-<side>-gerber.zip | 1 | 1 | 2 | Gerber から発注（実装サービスも可） | JLCPCB | 見積 | [リンク](https://cart.jlcpcb.com/quote) |  |
