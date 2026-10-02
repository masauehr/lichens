"""写真のEXIF(GPS・撮影日時)を読み、地図ページ用のデータと縮小画像を生成する。

使い方:
    python3 scripts/build_map.py [--src images/raw] [--out map]

出力:
    map/photos.json    ... 位置・日時・画像パスの一覧
    map/thumbs/*.jpg   ... サムネイル（長辺320px）
    map/photos/*.jpg   ... 表示用（長辺1200px）
"""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

THUMB_SIZE = 320
PHOTO_SIZE = 1200


def read_exif(src: Path) -> list[dict]:
    """exiftoolでGPS・撮影日時を一括取得する（数値形式）"""
    out = subprocess.run(
        ["exiftool", "-json", "-n", "-q", "-GPSLatitude", "-GPSLongitude",
         "-DateTimeOriginal", "-ext", "jpg", "-ext", "jpeg", str(src)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out) if out.strip() else []


def resize(src_file: Path, dst_file: Path, size: int) -> None:
    """EXIFの向きを反映して長辺sizeに縮小保存する"""
    if dst_file.exists():
        return
    with Image.open(src_file) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((size, size))
        im.convert("RGB").save(dst_file, "JPEG", quality=82)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="images/raw")
    ap.add_argument("--out", default="map")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    (out / "photos").mkdir(parents=True, exist_ok=True)

    items, skipped = [], []
    for row in sorted(read_exif(src), key=lambda r: r["SourceFile"]):
        f = Path(row["SourceFile"])
        if "GPSLatitude" not in row or "GPSLongitude" not in row:
            skipped.append(f.name)
            continue
        taken = None
        if row.get("DateTimeOriginal"):
            taken = datetime.strptime(row["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S").isoformat()
        name = f.stem + ".jpg"
        resize(f, out / "thumbs" / name, THUMB_SIZE)
        resize(f, out / "photos" / name, PHOTO_SIZE)
        items.append({
            "id": f.stem,
            "lat": round(row["GPSLatitude"], 6),
            "lon": round(row["GPSLongitude"], 6),
            "taken": taken,
            "thumb": f"thumbs/{name}",
            "photo": f"photos/{name}",
        })

    (out / "photos.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"地図用データ: {len(items)}枚 / GPSなしでスキップ: {len(skipped)}枚")
    for n in skipped:
        print("  skip:", n)


if __name__ == "__main__":
    main()
