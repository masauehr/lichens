# scripts/ — 自動化スクリプト

## 将来実装予定のスクリプト

| スクリプト | 目的 | 状態 |
|-----------|------|------|
| `rename.sh` | 写真アプリからエクスポートした画像を命名規則に従ってリネーム | 未実装 |
| `resize.sh` | 原本から1200px幅JPGを生成してカタログ用に配置 | 未実装 |
| `new_record.sh` | 対話式で catalog/{種ID}/record.md を自動生成 | 未実装 |
| `export_pdf.sh` | database.md + カタログをPDFに出力（pandoc使用） | 未実装 |
| `import_photos.sh` | 写真アプリから一括エクスポート（AppleScript利用） | 未実装 |

## rename.sh の設計メモ

```bash
# 想定インターフェース
bash scripts/rename.sh --dir images/raw/
# → 撮影日EXIFを読んでリネーム（exiftool使用）
# exiftool のインストール: brew install exiftool
```

## export_pdf.sh の設計メモ

```bash
# pandoc でMarkdownをPDFに変換
# pandoc のインストール: brew install pandoc
bash scripts/export_pdf.sh --output lichens_catalog_2026.pdf
```

## 家族写真への横展開メモ

- `rename.sh` は撮影日・人物タグを引数で指定できるよう設計する
- `new_record.sh` はカテゴリ（lichens / family / travel など）を引数で切り替える
- `import_photos.sh` はアルバム名を引数で指定できるようにする
