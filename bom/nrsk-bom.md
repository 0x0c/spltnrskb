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
| 受動部品 | コンデンサ 0.1 µF | 0805 X7R 50 V | 11 | 11 | 22 | YAGEO CC0805KRX7R9BB104 | LCSC C49678 | US$0.019 | [リンク](https://www.lcsc.com/product-detail/C49678.html) |  |
| 受動部品 | コンデンサ 1 µF | 0805 X7R 25 V 以上（LDO、RP2040 の内蔵レギュレータ） | 4 | 4 | 8 | Samsung CL21B105KBFNNNE（50 V） | LCSC C28323 | US$0.04 | [リンク](https://www.lcsc.com/product-detail/C28323.html) |  |
| 受動部品 | コンデンサ 10 µF | 0805 X5R 10 V 以上 | 1 | 1 | 2 | Samsung CL21A106KAYNNNE（X5R 25 V） | LCSC C15850 | US$0.066 | [リンク](https://www.lcsc.com/product-detail/C15850.html) |  |
| 受動部品 | 抵抗 10 kΩ | 0805 1% | 2 | 2 | 4 | UNI-ROYAL 0805W8F1002T5E | LCSC C17414 | US$0.0034 | [リンク](https://www.lcsc.com/product-detail/C17414.html) |  |
| 受動部品 | 抵抗 27 Ω | 0805 1%（USB D+/D−） | 2 | 2 | 4 | UNI-ROYAL 0805W8F270JT5E | LCSC C17594 | US$0.0029（100 個単位） | [リンク](https://www.lcsc.com/product-detail/C17594.html) | 2026-10-10 に確認（在庫 195,300）。JLCPCB の部品実装の推奨部品（Preferred）で、在庫は約 4 万個 |
| 受動部品 | 　└ 代替 |  |  |  |  | YAGEO RC0805FR-0727RL | LCSC C163408 | US$0.0078 | [リンク](https://www.lcsc.com/product-detail/C163408.html) | 代替。JLCPCB の部品実装の在庫が 5 個しかない（2026-10-10、LCSC の在庫は別で 4,900） |
| 受動部品 | 抵抗 1 kΩ | 0805 1%（水晶の XOUT 直列、BOOTSEL） | 2 | 2 | 4 | UNI-ROYAL 0805W8F1001T5E | LCSC C17513 | US$0.0041 | [リンク](https://www.lcsc.com/product-detail/C17513.html) |  |
| 受動部品 | 抵抗 5.1 kΩ | 0805 1%（USB-C CC） | 2 | 2 | 4 | UNI-ROYAL 0805W8F5101T5E | LCSC C27834 | US$0.0056 | [リンク](https://www.lcsc.com/product-detail/C27834.html) |  |
| 表示 | OLED モジュール 0.91 インチ | 128×32、SSD1306、I2C、3.3 V、ピン順 GND/VCC/SCL/SDA（ガラス上面を基板から 2.5 mm に） | 1 | 1 | 2 | HS HS91L02W2C01（0.91 インチ 128×32、SSD1306、I2C） | LCSC C5248081 | US$2.26 | [リンク](https://www.lcsc.com/product-detail/C5248081.html) | 2026-10-10 に確認（在庫 3,017）。写真のピン順は GND/VCC/SCL/SDA。3.3 V で動くか、ピンヘッダが付くかはページに記載なし |
| 表示 | 　└ 代替 |  |  |  |  | OLED モジュール（0.91 インチ 128×32、SSD1306、ピンソケット付き） | 遊舎工房 | ¥825 | [リンク](https://shop.yushakobo.jp/products/oled) | 商品ページにピン順の記載なし。GND/VCC/SCL/SDA であることを現物のシルクで確認 |
| 入力 | ロータリーエンコーダー（サムホイール用） | Alps Alpine EC05E1220401、中空シャフト（六角穴 対辺 1.72 mm）、12 クリック / 12 パルス、表面実装、基板の裏に付ける | 1 | 1 | 2 | Alps Alpine EC05E1220401 | LCSC C116648 | US$1.08 | [リンク](https://www.lcsc.com/product-detail/C116648.html) | 2026-10-10 に確認（在庫 291 個） |
| 受動部品 | 抵抗 4.7 kΩ | 0805 1%（I2C プルアップ） | 2 | 2 | 4 | UNI-ROYAL 0805W8F4701T5E | LCSC C17673 | US$0.0051 | [リンク](https://www.lcsc.com/product-detail/C17673.html) |  |
| スイッチ | タクトスイッチ（リセット） | C&K PTS810 SJM 250 SMTR LFS（2 回押しで書き込みモード） | 1 | 1 | 2 | C&K PTS810SJM250SMTRLFS | LCSC C116501 | US$0.58 | [リンク](https://www.lcsc.com/product-detail/C116501.html) |  |
| スイッチ | BOOTSEL パッド | 基板のはんだジャンパー（部品なし）。ピンセットで短絡しながら USB を挿すと書き込みモード | 1 | 1 | 2 | 部品なし（基板のはんだジャンパー） | — |  |  |  |
| キースイッチ | MX 互換キースイッチ | 3 ピン / 5 ピンどちらでも可 | 44 | 48 | 92 | Kailh（HanElectricity）CPG151101D05 赤軸（リニア、45 gf） | LCSC C49234236 | US$0.108（5 個単位） | [リンク](https://www.lcsc.com/product-detail/C49234236.html) | 2026-10-10 に確認（在庫 1,210）。3 ピンか 5 ピンかはページに記載なし（どちらでも基板に付く） |
| キースイッチ | 　└ 代替 |  |  |  |  | Kailh Box V2 Red（リニア、5 ピン） | 遊舎工房 | ¥2,117 / 35 個 | [リンク](https://shop.yushakobo.jp/products/4264) | 92 個要るので 3 パック。確認時の在庫は 6 パックと少ない。遊舎工房の他の MX 互換スイッチでも可 |
| キースイッチ | 　└ 代替 |  |  |  |  | Kailh Super Speed Silver（リニア、3 ピン） | 遊舎工房 | ¥1,540 / 35 個 | [リンク](https://shop.yushakobo.jp/products/4280) | 在庫少 |
| キースイッチ | ホットスワップソケット | Kailh CPG151101S11（MX 用） | 44 | 48 | 92 | Kailh（HanElectricity）CPG151101S11-16 | LCSC C41430893 | US$0.043（10 個単位） | [リンク](https://www.lcsc.com/product-detail/C41430893.html) | 2026-10-10 に確認（在庫 217,980） |
| キースイッチ | スタビライザ 2 u（PCB マウント） | ネジ止め式推奨 | 1 | 2 | 3 | GDK-02 Pre-lubed PCB Mount Stabilizer | 遊舎工房 | ¥770 / セット | [リンク](https://shop.yushakobo.jp/products/11952) | 左 Shift、右 Backspace、右 Enter；LCSC に該当品なし；1 セットで 2 u が 4 個分。1 セットで足りる |
| 入力 | サムホイール | 直径 29.2 mm × 厚さ 4.1 mm、外周に 32 山のすべり止め、上面にエンコーダーを回す六角ピン（対辺 1.66 mm）（case/print/<side>-wheel.stl） | 1 | 1 | 2 | case/print/<side>-wheel.stl | 自作（3D プリント） |  |  | 六角ピンのはめあいは試し印刷で調整する；LCSC に該当品なし（自作の 3D プリント部品） |
| キーキャップ | キーキャップ 1 u |  |  |  | 81 | DSA 無刻印キーキャップ 1 u（PBT、22 色） | 遊舎工房 | ¥55 | [リンク](https://shop.yushakobo.jp/products/dsa-blank-keycaps) | LCSC に該当品なし |
| キーキャップ | キーキャップ 1.25 u |  |  |  | 5 | Signature Plastics DSA 1.25 u | spkeyboards.com（米国） | US$3.50 | [リンク](https://spkeyboards.com/products/dsa-1-25-space) | LCSC に該当品なし；国内で DSA 1.25 u が見つからなかったため海外通販。輸入時に関税・消費税 |
| キーキャップ | キーキャップ 1.5 u |  |  |  | 2 | DSA 無刻印キーキャップ 1.5 u（白・黒・灰・緑・赤） | 遊舎工房 | ¥220 | [リンク](https://shop.yushakobo.jp/products/10731) | LCSC に該当品なし |
| キーキャップ | キーキャップ 1.75 u |  |  |  | 1 | Signature Plastics DSA 1.75 u | spkeyboards.com（米国） | US$3.50 | [リンク](https://spkeyboards.com/collections/individual-keys/products/sp-dsa-1-75-space) | LCSC に該当品なし |
| キーキャップ | キーキャップ 2 u |  |  |  | 1 | DSA 無刻印キーキャップ 2 u（白・黒） | 遊舎工房 | ¥220 | [リンク](https://shop.yushakobo.jp/products/11443) | LCSC に該当品なし |
| キーキャップ | キーキャップ 2.25 u |  |  |  | 2 | Signature Plastics DSA 2.25 u（スタビ対応） | spkeyboards.com（米国） | US$4.00 | [リンク](https://spkeyboards.com/products/sp-dsa-2-25-space-single-keycap) | LCSC に該当品なし |
| アクリル版 | M2 スペーサー 7 mm（メス-メス） | 六角 対辺 3.5〜4 mm、真鍮、ステンレスまたはナイロン | 8 | 8 | 16 | XHHD 303HZ20007（ステンレス、対辺 4 mm） | LCSC C52976405 | US$0.28 / 10 個（10 個単位） | [リンク](https://www.lcsc.com/product-detail/C52976405.html) | 基板と底板の間；2026-10-10 に確認（在庫 500） |
| アクリル版 | 　└ 代替 |  |  |  |  | 廣杉計器 ASB-2007E（黄銅、両メネジ） | MonotaRO | ¥1,978 / 50 個 | [リンク](https://www.monotaro.com/p/1111/2937/) |  |
| アクリル版 | M2 × 4 mm なべネジ | 基板の上からスペーサーへ | 8 | 8 | 16 | Shuntian PM2X4nie（ニッケルめっき、頭 φ3.3 × 1.3） | LCSC C357393 | US$0.19 / 100 本（100 本単位） | [リンク](https://www.lcsc.com/product-detail/C357393.html) | 2026-10-10 に確認（在庫 11,700） |
| 筐体共通 | ゴム足 | 直径 8〜10 mm、高さ 3 mm 以上 | 4 | 4 | 8 | 3M クッションゴム 丸形 CS-02（φ9.5 × 3.8 mm） | MonotaRO | ¥483 / 18 個 | [リンク](https://www.monotaro.com/p/4525/7232/) | 底面に出るネジ先・ナットより高いもの；LCSC に該当品なし |
| 筐体共通 | 　└ 代替 |  |  |  |  | 栃木屋 クリアバンポン TM-180-303（φ11.2 × 5.1 mm） | MonotaRO | ¥48 / 個 | [リンク](https://www.monotaro.com/p/4262/7707/) |  |
| 筐体共通 | 透明アクリル板 1.5 mm（プレート） | <side>-plate、左 189.6×143.3 mm / 右 216.6×143.3 mm | 1 | 1 | 2 | アクリル板 DXF 切削（図面で WEB オーダー） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/estimate-drawing) | 3D プリント版もアクリル版もこのプレートを使う；LCSC に該当品なし；透明 1.5 mm で注文。切断線どうしの間隔 3 mm 未満は不可 |
| アクリル版 | マットクリア アクリル板 3 mm（枠） | 同上の外形、片側 4 枚（frame1〜4） | 4 | 4 | 8 | アクリル板キャスト 片面マットクリア（パラグラス C1 P） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3481) | frame1〜3 は差込口の切り欠きあり、frame4 は切り欠きなし；LCSC に該当品なし；2 / 3 / 5 mm。図面 WEB オーダー（https://www.hazaiya.co.jp/estimate-drawing）で DXF から切り出し |
| アクリル版 | マットクリア アクリル板 3 mm（底板） | 同上の外形 | 1 | 1 | 2 | アクリル板キャスト 片面マットクリア（パラグラス C1 P） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3481) | LCSC に該当品なし；2 / 3 / 5 mm。図面 WEB オーダー（https://www.hazaiya.co.jp/estimate-drawing）で DXF から切り出し |
| アクリル版 | M2 × 20 mm なべネジ | 外周：プレートの上から底板まで貫通（16.5 mm + ナット） | 10 | 11 | 21 | OHSATO ナベ頭小ねじ M2 × 20（ステンレス） | MonotaRO | ¥329 / 50 本 | [リンク](https://www.monotaro.com/p/1714/1900/) | LCSC に該当品なし |
| アクリル版 | M2 ナット | 外周ネジ用（底板の下） | 10 | 11 | 21 | 大阪魂 六角ナット 1 種 M2（SUS304、対辺 4 × 厚さ 1.6） | MonotaRO | ¥164 / 20 個 | [リンク](https://www.monotaro.com/p/2876/3624/) | LCSC に該当品なし |
| アクリル版 | 　└ 代替 |  |  |  |  | エスコ EA949LT-720 六角ナット M2（真鍮、ニッケルめっき） | MonotaRO | ¥798 / 80 個 | [リンク](https://www.monotaro.com/p/5052/3646/) |  |
| アクリル版 | M2 × 5 mm なべネジ | 底板の下からスペーサーへ | 8 | 8 | 16 | なべ小ねじ M2 × 5 | 遊舎工房 | ¥220 / 50 本 | [リンク](https://shop.yushakobo.jp/products/a0800n2?variant=37665432993953) | LCSC は在庫切れ（C357529） |
| アクリル版 | 　└ 代替 |  |  |  |  | 大阪魂 ナベ頭小ねじ M2 × 5（ステンレス） | MonotaRO | ¥1,099 / 160 本 | [リンク](https://www.monotaro.com/p/0550/6916/) |  |
| OLED カバー | ハーフミラー アクリル板 2 mm | <side>-oled-cover（DXF/SVG）、プレートの窓にはめ込み、上面をプレートと面一 | 1 | 1 | 2 | アクリル板キャスト ハーフミラー 30%（三菱 MRH-001T-30） | はざいや（菅原工芸） | 見積 | [リンク](https://www.hazaiya.co.jp/products/detail/3373) | OLED のガラス面に載せる。両方の筐体で共通；LCSC に該当品なし；2 / 3 / 5 mm。図面 WEB オーダーで DXF から切り出し。1.5 mm のアクリル製ハーフミラーはメーカーにもない |
| OLED カバー | 　└ 代替 |  |  |  |  | アクリルハーフミラー板 フリーカット（2 mm、透過 30%） | アクリ屋ドットコム | 見積 | [リンク](https://www.acry-ya.com/products/detail/113/) | 最小 10 × 10 mm から |
| OLED カバー | 透明両面テープ 厚さ 0.5 mm | カバーと OLED のガラス面、カバーの縁が載る壁の上面に貼る |  |  |  | 3M スコッチ はがせる両面テープ 超透明 KRT-15（幅 15 × 1.5 m × 厚さ 0.5 mm） | カインズ |  | [リンク](https://www.cainz.com/g/4547452982974.html) | 少量；LCSC に該当品なし；はがせるタイプなので OLED を交換できる |
| 3D プリント版 B | M2 ヒートセットインサート | 外径 3.2 mm × 長さ 3 mm、プレート裏のボスに入れる | 10 | 11 | 21 | XHHD SZTB1063（真鍮、両ローレット） | LCSC C51938879 | US$0.51 / 50 個（50 個単位） | [リンク](https://www.lcsc.com/product-detail/C51938879.html) | 2026-10-10 に確認（在庫 9,300）。寸法（M2、長さ 3 mm、外径 3.2 mm）は品名 M2*3*3.2 から読んだもの |
| 3D プリント版 B | 　└ 代替 |  |  |  |  | Prusa Heat Set Inserts M2 short | Prusa Research | US$11.99 / 100 個 | [リンク](https://www.prusa3d.com/ja/product/heat-set-inserts-m2-short-100-pcs/) | 3D プリント用。寸法の記載なし |
| 3D プリント版 A | M2 ナット（ナット受け用） | 壁上面のくぼみの下の六角穴に入れる | 10 | 11 | 21 | 大阪魂 六角ナット 1 種 M2（SUS304、対辺 4 × 厚さ 1.6） | MonotaRO | ¥164 / 20 個 | [リンク](https://www.monotaro.com/p/2876/3624/) | LCSC に該当品なし |
| 3D プリント版 A | 　└ 代替 |  |  |  |  | エスコ EA949LT-720 六角ナット M2（真鍮、ニッケルめっき） | MonotaRO | ¥798 / 80 個 | [リンク](https://www.monotaro.com/p/5052/3646/) |  |
| 3D プリント版 A | M2 × 6 mm スリムヘッド小ねじ | 頭 φ4.0 × 高さ 0.5 mm、透明アクリルのプレートを上から留める | 10 | 11 | 21 | 大阪魂 (+)スリムヘッド小ねじ ステンレス M2 × 6（φ4 × 0.5、注文コード 41746713） | MonotaRO | 7 本入り | [リンク](https://www.monotaro.com/p/4174/6713/) | LCSC に該当品なし（頭の低い M2 は皿ネジだけ） |
| アクリル版 | M3 × 8 mm なべネジ | サムホイールの軸（底板の下から差し込む） | 1 | 1 | 2 | Shuntian PM3X8（ニッケルめっき） | LCSC C357544 | US$0.23 / 100 本（100 本単位） | [リンク](https://www.lcsc.com/product-detail/C357544.html) | 3D プリント版はトレイの軸を使う；2026-10-10 に確認（在庫 27,500） |
| 3D プリント版 B | M2 × 12 mm なべネジ（底から） | トレイ底の座ぐりから壁を通してプレート裏のインサートへ | 10 | 11 | 21 | TRUSCO Y823-0212 ナベ頭小ねじ ステンレス M2 × 12 | MonotaRO | ¥395 / 20 本 | [リンク](https://www.monotaro.com/p/2498/0167/) | LCSC に該当品なし |
| 3D プリント版 B | 　└ 代替 |  |  |  |  | エスコ EA949NF-212 鍋頭小ねじ ステンレス M2 × 12 | MonotaRO | ¥275 / 16 本 | [リンク](https://www.monotaro.com/g/02450718/) |  |
| 3D プリント版 | M2 × 6 mm タッピングネジ | 基板をボス（下穴 φ1.6）へ固定 | 8 | 8 | 16 | Shuntian PA2X6nie（なべ、頭 φ3.5、ニッケルめっき） | LCSC C357360 | US$0.16 / 100 本（100 本単位） | [リンク](https://www.lcsc.com/product-detail/C357360.html) | 2026-10-10 に確認（在庫 2,900） |
| ケーブル | TRRS ケーブル（4 極、オス-オス） | 3.5 mm |  |  |  | TRRS ケーブル 0.3 m | 遊舎工房 | ¥330 | [リンク](https://shop.yushakobo.jp/products/8023) | 1 本；LCSC に該当品なし |
| ケーブル | 　└ 代替 |  |  |  |  | TRRS ケーブル 0.8 m（メタル） | 遊舎工房 | ¥1,100 | [リンク](https://shop.yushakobo.jp/products/8111) |  |
| ケーブル | USB-C ケーブル | USB 2.0 以上 |  |  |  | Ckmtw S100920007（USB-A to C、データ用、1 m） | LCSC C430908 | US$2.12 | [リンク](https://www.lcsc.com/product-detail/C430908.html) | 1 本；2026-10-10 に確認（在庫 110） |
| ケーブル | 　└ 代替 |  |  |  |  | USB Type-C to C 1.0 m | 遊舎工房 | ¥440 | [リンク](https://shop.yushakobo.jp/products/11426) |  |
| 基板 | プリント基板（2 層、1.6 mm） | fab/<side>/nrsk-<side>-gerber.zip | 1 | 1 | 2 | Gerber から発注（実装サービスも可） | JLCPCB | 見積 | [リンク](https://cart.jlcpcb.com/quote) |  |
