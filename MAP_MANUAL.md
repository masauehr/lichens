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

- **位置の推定**: 前後の両方に GPS 写真があれば（各30分以内）時刻で補間、片側のみなら10分以内の最寄り。それ以外は位置不明。GPS付き写真を隠した検証では、中央値1〜3m・90%点4〜11m。カメラの時計が iPhone とずれていると外れるが、TG-6 は位置が合っていることを確認済み。
- 推定位置の写真は、ポップアップに「※位置は推定」と表示。
- **位置不明の写真**は、ピンの代わりにページ内の「位置不明」ボタンから一覧で見られる。
- **除外円の座標はコマンド引数でのみ渡し、スクリプトやドキュメントに書かない。** 公開版では自宅から半径50m以内の写真を、データにも画像にも含めない（2026-10-05時点で669枚）。
- 画像はEXIFを付けずに保存するので、サムネイルから位置情報は漏れない。

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
| 公開版 | 6,143枚（位置あり4,960 / 位置不明1,183）、約160MB。種別 地衣類3,888 / 可能性1,441 / 全景814 |
| 手元用の全件版 | 6,812枚、約1.4GB |

## 6. 今後の取り込み（2回目以降）

AIは使わず、写真アプリで「地衣類（候補）」アルバムに足した写真だけを書き出す（3.の手順）。

## 更新履歴

- 2026-10-03: 地図ページ・生成スクリプトを新規作成。GitHub Pages で公開。
- 2026-10-05: 座標周辺の枚数確認機能（`?probe=1`）を追加。写真アプリからの自動抽出（機材＋ラベルで絞り、Claudeで判定）、TG-6 の位置推定、位置不明の一覧、種別の絞り込み、自宅周辺の除外を追加。公開版を110枚から6,143枚へ拡張。
