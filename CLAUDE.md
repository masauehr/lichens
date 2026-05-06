# CLAUDE.md — lichens プロジェクト固有ルール

## プロジェクト概要
地衣類写真の整理・データベース化プロジェクト。
家族写真管理システムのプロトタイプを兼ねる。

## 新規記録追加時のルール

### 1. 種ID の採番
- `database.md` の末尾の番号 + 1 を使う
- 形式: `L{番号:03d}_{属名（小文字）}` 例: `L001_umbilicaria`
- 同定不明の場合は属名部分を `unknown` にする（例: `L005_unknown`）

### 2. ファイル作成手順
```bash
# カタログフォルダを作成
mkdir -p catalog/{種ID}/images

# テンプレートをコピー
cp catalog/template.md catalog/{種ID}/record.md
```

### 3. database.md の更新（必須）
新規記録を追加したら `database.md` の一覧テーブルに必ず1行追加すること。

### 4. GitHub へのコミット（必須）
```bash
git add catalog/{種ID}/ database.md
git commit -m "地衣類記録追加: {和名または学名}（{種ID}）

- 撮影地: {場所}
- 撮影日: {日付}
- 同定確度: {確定/暫定/不明}

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
git push origin main
```

## 画像ファイルの取り扱い

- **原本**: `images/raw/` に保管（撮影日_連番.jpg 形式）
- **カタログ用**: `catalog/{種ID}/images/` にリサイズ版を配置
- **Git管理**: 10MB未満の画像は通常コミット可。それ以上は Git LFS を検討
- macOS 写真アプリからのエクスポート手順は `docs/workflow.md` を参照

## 分類・タグ体系

詳細は `docs/taxonomy.md` を参照。
同定確度は必ず以下3段階で記録する:
- `確定` — 文献・専門家確認済み
- `暫定` — 形態から判断、要確認
- `不明` — 同定できていない

## 家族写真プロトタイプとしての注意点

このプロジェクトで確立したワークフローは家族写真管理に横展開する予定。
以下の点を意識して設計すること:
- メタデータ項目の汎用性（撮影日・場所・タグは共通で使える）
- `template.md` の構造を汎用的に保つ
- スクリプト類は引数でカテゴリを切り替えられるよう設計する
