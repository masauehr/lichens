# lichens — 地衣類フォトマップ

撮りためた地衣類の写真を、EXIF の GPS 情報から地図上にプロットして閲覧するプロジェクト。
（写真DB・カタログ管理は [lichens/README.md](README.md) を参照）

## 構成

| ファイル | 役割 |
|---|---|
| `scripts/build_map.py` | `images/raw/` の写真から GPS・撮影日時を抽出し、縮小画像と `photos.json` を生成 |
| `map/index.html` | Leaflet + markercluster の地図ページ（Vanilla JS） |
| `map/photos.json` | 位置・日時・画像パスの一覧（生成物） |
| `map/thumbs/`, `map/photos/` | サムネイル（320px）・表示用（1200px）（生成物） |

## 使い方

```bash
cd ~/projects/lichens
python3 scripts/build_map.py          # 写真を追加したら再実行（生成済み画像はスキップ）
cd map && python3 -m http.server 8765 # http://localhost:8765/ を開く
```

- `fetch` を使うため、`index.html` をダブルクリックで開くのではなく http サーバー経由で開く
- 背景地図は国土地理院（航空写真・標準地図）と OpenStreetMap を切替可能
- ピンは近接でクラスタ化。ピンをクリックでサムネイル+撮影日時、サムネイルをクリックで拡大

## 設計メモ

- 前提: exiftool（`brew install exiftool`）と Pillow
- 原本（`images/raw/`、約364MB）は Git 管理しない（`.gitignore`）。地図用の縮小版のみコミット
- GPS なしの写真は地図に出さずスキップし、件数と名前を表示する
- 公開可否: 自宅近くをほぼ撮っていないため公開OK（ユーザー判断 2026-10-03）
- 初回データ: 2026-05-03 撮影の 110 枚（全て GPS あり、半径約300mの範囲）

## 更新履歴

- 2026-10-03: 地図ページ・生成スクリプトを新規作成、動作確認済み（クラスタ・ポップアップ）
