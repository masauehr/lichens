# ワークフロー — 写真取り込みから整理まで

## 全体の流れ

```
MacBook 写真アプリ
    ↓ エクスポート
images/raw/        ← 原本を保管
    ↓ リサイズ・選定
catalog/{種ID}/images/   ← カタログ用画像
    ↓ 記録作成
catalog/{種ID}/record.md ← メタデータ・観察メモ
    ↓ 一覧更新
database.md              ← マスターDB
    ↓
git commit & push        ← GitHub公開
```

---

## STEP 1: 写真アプリからエクスポート

### 方法A — 手動エクスポート（基本）

1. 写真アプリを開く
2. 地衣類の写真を選択（複数選択可: Shift/Cmd クリック）
3. メニュー: **ファイル → 書き出す → 変更なしで元のファイルを書き出す**
4. 保存先: `lichens/images/raw/`
5. ファイル名はそのまま（HEIC / JPG）でOK

### 方法B — アルバムからまとめてエクスポート

写真アプリで「地衣類」アルバムを事前に作成しておくと効率的。

1. 写真アプリ → 左サイドバー「アルバム」→「地衣類」を選択
2. Cmd+A で全選択
3. 上記と同じ手順でエクスポート

### ファイル名の整理（推奨）

エクスポート後、以下の形式にリネームする（`scripts/rename.sh` で自動化予定）:

```
{撮影日YYYYMMDD}_{連番3桁}.jpg
例: 20260412_001.jpg
```

---

## STEP 2: 原本画像の保管

```
images/
├── raw/                  # 原本（変更しない）
│   ├── 20260412_001.jpg
│   └── 20260412_002.heic
└── README.md
```

- HEIC形式はそのまま保管可（GitHub表示用にJPG変換が必要な場合のみ変換）
- 削除禁止。リネームのみ許可。

---

## STEP 3: カタログ記録の作成

```bash
# 種IDを決める（database.md の末尾番号+1）
SPECIES_ID="L001_umbilicaria"

# フォルダ作成
mkdir -p catalog/${SPECIES_ID}/images

# テンプレートをコピー
cp catalog/template.md catalog/${SPECIES_ID}/record.md

# カタログ用画像をコピー（必要に応じてリサイズ）
cp images/raw/20260412_001.jpg catalog/${SPECIES_ID}/images/
```

`catalog/{種ID}/record.md` をエディタで開いて記入する。

---

## STEP 4: database.md の更新

`database.md` の「全記録テーブル」に1行追記し、統計欄も更新する。

---

## STEP 5: コミット＆プッシュ

```bash
cd /Users/masahiro/projects/lichens
git add catalog/${SPECIES_ID}/ database.md images/raw/
git commit -m "地衣類記録追加: {種名}（${SPECIES_ID}）

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin main
```

---

## 画像形式に関するメモ

| 形式 | GitHub表示 | 容量 | 推奨用途 |
|------|-----------|------|---------|
| HEIC | ❌ 非対応 | 小 | 原本保管のみ |
| JPG | ✅ 対応 | 中 | カタログ表示用 |
| WebP | ✅ 対応 | 最小 | 将来的に移行検討 |

→ カタログ用画像は JPG に変換して配置する。

---

## 将来の自動化候補

- [ ] `scripts/import.sh` — エクスポートフォルダを監視して自動リネーム
- [ ] `scripts/resize.sh` — 原本から1200px幅のJPGを生成
- [ ] `scripts/new_record.sh` — 対話式で record.md を自動生成
- [ ] `scripts/export_pdf.sh` — database.md からPDFカタログを生成
