# lichens — 地衣類写真データベース

地図表示機能・写真アプリからの自動抽出・公開版の作り方・座標周辺の枚数確認（`?probe=1`）は [MAP_MANUAL.md](MAP_MANUAL.md) を参照。
公開地図: https://masauehr.github.io/lichens/

MacBookの写真アプリから抽出した地衣類画像を整理・データベース化するプロジェクト。
家族写真管理ワークフローのプロトタイプを兼ねる。

## プロジェクトの目的

- 撮影した地衣類の写真を種ごとに整理・同定記録
- 撮影場所・日時・生育環境のメタデータを構造化
- 閲覧性の高いカタログを構築（GitHub上でのMarkdown表示）
- 将来の家族写真管理システムへの横展開

## ディレクトリ構成

```
lichens/
├── README.md            # このファイル
├── CLAUDE.md            # Claude向けプロジェクトルール
├── database.md          # 全記録一覧（マスターDB）
├── docs/
│   ├── workflow.md      # 写真取り込み〜整理のワークフロー
│   ├── taxonomy.md      # 分類・タグ体系
│   └── management.md   # 管理方式（PDF vs GitHub）の検討メモ
├── catalog/
│   ├── README.md        # カタログの使い方
│   ├── template.md     # 個別記録テンプレート
│   └── {種ID}/          # 種ごとのフォルダ（例: L001_umbilicaria/）
│       ├── record.md   # 種の記録（同定情報・観察メモ）
│       └── images/     # その種の写真（シンボリックリンクまたはコピー）
├── images/
│   └── README.md        # 原本画像の管理方針
└── scripts/
    └── README.md        # 自動化スクリプト（将来用）
```

## 管理方式

詳細は [docs/management.md](docs/management.md) を参照。

| 方式 | 利点 | 課題 |
|------|------|------|
| **GitHub管理（Markdown）** | バージョン管理・検索性・Webブラウズ | 画像容量（Git LFS検討） |
| **PDF化** | 印刷・配布が容易 | 更新コストが高い |
| **ハイブリッド** | 両方の利点を活かせる | 二重管理 |

→ 現状は **GitHub管理をメイン** とし、印刷用PDFを必要に応じて生成する方針。

## 種ID体系

```
L{番号:03d}_{属名}_{種小名（略）}/
例: L001_umbilicaria / L002_parmotrema / L003_usnea
```

## クイックスタート

1. 写真アプリからエクスポート → `images/raw/` に配置
2. `catalog/template.md` をコピーして `catalog/{種ID}/record.md` を作成
3. `database.md` の一覧テーブルに1行追加
4. `git add . && git commit && git push`

## 登録一覧（database.md へのショートカット）

→ [database.md](database.md) で全件を確認

| 種ID | 和名 / 学名 | 撮影地 | 撮影日 | 同定確度 |
|------|------------|--------|--------|---------|
| （記録追加時に記入） | | | | |
