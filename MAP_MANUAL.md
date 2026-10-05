# lichens — 地衣類フォトマップと写真アプリからの自動抽出

撮りためた地衣類の写真を、写真アプリから自動で拾い出し、地図に紐付けて閲覧するプロジェクト。
（写真DB・カタログ管理は [lichens/README.md](README.md) を参照）

公開URL: https://masauehr.github.io/lichens/ （GitHub Pages。`.github/workflows/pages.yml` で `map/` のみ公開）

## 全体の流れ

```
写真アプリ ─(1)候補抽出─▶ (2)Claudeで判定 ─▶ (3)「地衣類（候補）」アルバム ─(4)人が確認─▶
(5)原本を書き出し ─▶ (6)GPS推定 ─▶ (7)地図生成（手元用の全件版 / 公開用の絞り込み版）
```

## 構成

| ファイル | 役割 |
|---|---|
| `scripts/find_lichens.py` | 候補抽出・Claude判定・アルバム登録・前後の全景追加 |
| `scripts/make_kinds.py` | 判定結果から写真ごとの種別（main/maybe/context）を作る |
| `scripts/estimate_locations.py` | GPSのない写真の位置を、撮影時刻の近いGPS写真から推定 |
| `scripts/build_map.py` | EXIFから地図データ・サムネイルを生成（`--exclude-circle` で範囲除外） |
| `map/index.html` | Leaflet + markercluster の地図ページ（種別絞り込み・位置不明一覧付き） |
| `map/photos.json`, `map/thumbs/` | 公開用データ（サムネイルのみ） |

実行は `lichens/.venv`（osxphotos・pillow・pillow-heif）の Python で行う。

## 1. 写真アプリから地衣類を拾う（初回の網羅）

候補条件（iPhone 15 Pro・自然物ラベル/ラベルなし・人物書類を除外）を機材ごとに用意してある（`SETS`）。

```bash
.venv/bin/python scripts/find_lichens.py judge --set iphone    # Claudeで判定（12枚/シートのコンタクトシート）
.venv/bin/python scripts/find_lichens.py judge --set digicam   # Apple以外・横長（TG-6など）
.venv/bin/python scripts/find_lichens.py judge --set se --sample 36   # 一部だけ試す
.venv/bin/python scripts/find_lichens.py context --sets iphone,digicam,se --apply   # 判定結果＋前後の全景を1回でアルバムへ
```

- 判定は3段階（2=あり / 1=可能性あり / 0=なし）。結果は `work/judged*.json`（再開可）。
- 試験結果: 既知の地衣類の検出率 97%（2段階だと82%）。「未知」側の誤検出率は自動では測れず、アルバムでの目視確認が必要。
- 機材が強い手がかり: 既知の地衣類は iPhone 15 Pro の超広角（マクロ）が9割。TG-6 の写真は、ほぼ地衣類の接写。8 Plus・6s にはほとんどない。
- 「前後の全景」は、「あり」写真の前後120秒・30m以内で同じ機種の写真（木の全景など）。
- 縮小した写真が判定のために Anthropic へ送られる（人物ラベル付きは除外）。

## 2. 写真アプリのアルバム登録時の注意

- 写真アプリは**追加命令ごとに確認ダイアログ**を出す。必ず1回にまとめて追加する（枚数は関係ない）。
- AppleScript の許可は、システム設定 → プライバシーとセキュリティ → オートメーション。
- 全アルバムの列挙は大規模ライブラリでタイムアウトするため避ける。
- 「オリジナルに戻す」は編集の取り消し。**ダウンロードの機能ではない**ので押さない。

## 3. 原本の書き出し

```bash
.venv/bin/osxphotos export images/originals --album "地衣類（候補）" --only-photos --skip-edited --skip-live \
  --download-missing --use-photokit --filename "{created.strftime,%Y%m%d_%H%M%S}_{original_name}" \
  --update --retry 3 --report work/export_report.csv
```

- 原本の多くは iCloud 上にあり、ダウンロードに6〜7時間（約20GB）かかった。**ターミナル/iTermから実行**（このセッション内からは PhotoKit の許可が通らない）。
- 初回は写真アプリへのアクセス許可が必要（ターミナルまたは iTerm が対象）。`--update` で再実行すると続きから。
- 書き出せなかった写真が34枚あった（iCloud側の問題）。再取得しても失敗。

## 4. 地図の生成

```bash
.venv/bin/python scripts/make_kinds.py            # → work/kinds.json
.venv/bin/python scripts/estimate_locations.py    # → work/est_loc.json
# 手元用の全件版（Git管理外 map_local/・大きい画像つき）
.venv/bin/python scripts/build_map.py --src images/originals --out map_local --kinds work/kinds.json --est-loc work/est_loc.json
# 公開用（サムネイルのみ・自宅周辺を除外）→ 内容を確認してから map/ へコピー
.venv/bin/python scripts/build_map.py --src images/originals --out map_public --kinds work/kinds.json --est-loc work/est_loc.json --photo-size 0 --exclude-circle 緯度,経度,半径m
cd map_local && python3 -m http.server 8766        # http://localhost:8766/ （周辺の枚数確認は ?probe=1）
```

- **位置の推定**（`estimate_locations.py`。GPSのない写真が対象）:
  1. 前後の両方にGPS写真があれば（各30分以内）時刻で**補間**
  2. 片側のみなら10分以内の**最寄り**の写真の位置
  3. どちらでもなければ、**直前のGPS写真から1日（`--carry 86400`）以内なら、その写真と同じ場所**（デジカメの写真を翌日ごろに写真アプリへ取り込むことがあるため。間にGPS写真が無いことが前提）
  4. それ以外は位置不明
  - GPS付き写真を隠した検証では、補間は中央値1m・90%点4m、最寄りは中央値3m・90%点11m（連続撮影の条件。TG-6は時計のずれがなく位置が合うことを確認済み）。引き継ぎは精度が低い（同じ場所とみなすだけ）。
- 推定位置の写真は、ポップアップに「※位置は推定」と表示。
- 名前が「名前 (1)」の重複ファイルは、元の名前で推定位置・種別を引き当てる。
- **位置不明の写真**は、ピンの代わりにページ内の「位置不明」ボタンから一覧で見られる。
- **除外円の座標はコマンド引数でのみ渡し、スクリプトやドキュメントに書かない。** 公開版では自宅から半径50m以内の写真を、データにも画像にも含めない（2026-10-05時点で829枚）。位置の引き継ぎで自宅の写真と同じ場所になった写真も除外される。
- 画像はEXIFを付けずに保存するので、サムネイルから位置情報は漏れない。

## 標高の地図

- 左上の背景地図の選択に、国土地理院の**色別標高図**と**陰影起伏図**を追加（航空写真・標準地図・OSM と切替）。
- ピンのポップアップに**標高（m）**を表示（国土地理院の標高API。日本国内のみ。取得できないときは「取得できず」）。推定位置の写真の標高は目安。
- **地図の何もない場所をクリックすると、その地点の緯度・経度・標高を表示**する（ピンやクラスタのクリックは対象外。海上・範囲外は「データなし」）。`?probe=1` のときは、さらに周辺の枚数も出る。

## 初期表示の範囲

- 地図を動かす・拡大すると、中心とズームを閲覧者のブラウザ（localStorage）に記憶し、次に開いたときは**前回と同じ範囲**から始める。
- 初めて開くとき（記憶がないとき）は、全写真が収まる範囲。記憶できない環境（プライベートブラウズなど）でも、動作はそのまま。
- 記憶は端末ごと。リセットは、ブラウザのサイトデータ削除か、開発者ツールで `localStorage.removeItem('lichens_map_view')`。

## 座標周辺の枚数確認機能（`?probe=1`）

公開したくない場所（自宅など）の写真が何枚あるか、除外範囲をどう決めるかを、地図上で確認する機能。**残すこと**（`map/index.html` に実装済み）。

- 使い方: 地図ページのURLの末尾に `?probe=1` を付けて開く（例: `http://localhost:8766/?probe=1`）。
- 地図をクリックすると、その地点を中心に赤い円が出て、左下に「座標 / 半径N m以内の枚数（地衣類・可能性・全景の内訳）」が表示される。
- 左下の「半径」欄で距離を変えられる（初期値500m）。
- 手元用の全件版（`map_local/`）で使う。表示された座標と半径を、公開版の除外円（`--exclude-circle`）に使う。
- 通常のURL（`?probe=1` なし）では表示されない。

## 5. 規模（2026-10-05時点）

| 項目 | 内容 |
|---|---|
| 「地衣類（候補）」アルバム | 約6,800枚（人が確認して不要分を除外済み） |
| 公開版 | 5,983枚（位置あり5,778 / 位置不明205）、約160MB。種別 地衣類3,874 / 可能性1,421 / 全景688。推定位置は1,856枚 |
| 手元用の全件版 | 6,812枚、約1.4GB |

## 6. 今後の取り込み（2回目以降）

AIは使わず、写真アプリで「地衣類（候補）」アルバムに足した写真だけを書き出す（3.の手順）。

## 更新履歴

- 2026-10-03: 地図ページ・生成スクリプトを新規作成。GitHub Pages で公開。
- 2026-10-05: 初期表示を前回の範囲にする。地図クリックで緯度経度・標高を表示。位置の引き継ぎ（直前のGPS写真から1日以内）、標高の地図・ポップアップの標高を追加。公開版を5,983枚に更新し、旧名の画像220ファイルを削除。座標周辺の枚数確認機能（`?probe=1`）を追加。写真アプリからの自動抽出（機材＋ラベルで絞り、Claudeで判定）、TG-6 の位置推定、位置不明の一覧、種別の絞り込み、自宅周辺の除外を追加。公開版を110枚から6,143枚へ拡張。
