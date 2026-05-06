# catalog/ — 種別カタログ

## このディレクトリについて

種（または形態グループ）ごとにフォルダを作成し、写真と観察記録を格納する。

## フォルダ構成

```
catalog/
├── README.md          # このファイル
├── template.md       # 記録テンプレート（コピーして使う）
├── L001_umbilicaria/ # 例: ウチワゴケ属
│   ├── record.md    # 観察記録・同定情報
│   └── images/      # カタログ用画像（JPG）
├── L002_usnea/
│   ├── record.md
│   └── images/
└── ...
```

## 種ID の命名規則

```
L{番号:03d}_{属名（小文字、スペースなし）}
```

- 番号は `database.md` の末尾番号 + 1
- 属名は確定していれば属名、不明なら `unknown`
- 同じ属の種が複数ある場合: `L003_usnea_a`, `L004_usnea_b` のように末尾で区別

## 新規記録の作成手順

```bash
# 1. 種IDを決める
SPECIES_ID="L001_umbilicaria"

# 2. フォルダ作成
mkdir -p catalog/${SPECIES_ID}/images

# 3. テンプレートをコピー
cp catalog/template.md catalog/${SPECIES_ID}/record.md

# 4. record.md を編集して情報を記入

# 5. 画像を配置
cp images/raw/20260412_001.jpg catalog/${SPECIES_ID}/images/

# 6. database.md に1行追加

# 7. コミット
git add catalog/${SPECIES_ID}/ database.md
git commit -m "地衣類記録追加: {種名}（${SPECIES_ID}）"
git push origin main
```
