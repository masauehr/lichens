"""写真のEXIF(GPS・撮影日時)を読み、地図ページ用のデータと縮小画像を生成する。

使い方（HEICを読むため lichens/.venv の Python で実行）:
    .venv/bin/python scripts/build_map.py [--src images/raw] [--out map]
    # 全件版（手元用）:
    .venv/bin/python scripts/build_map.py --src images/originals --out map_local --kinds work/kinds.json

出力:
    {out}/photos.json    ... 位置・日時・種別・画像パスの一覧
    {out}/thumbs/*.jpg   ... サムネイル（長辺 --thumb-size）
    {out}/photos/*.jpg   ... 表示用（長辺 --photo-size）
    {out}/index.html     ... map/index.html のコピー（--out が map 以外のとき）

--exclude-circle は「緯度,経度,半径m」。その円内の写真は、画像も作らず photos.json にも含めない（公開版で自宅周辺を除く用。座標はコマンド引数でのみ渡し、ファイルに残さない）。
--est-loc は GPSのない写真の推定位置（scripts/estimate_locations.py で作成）。該当写真には "est": true を付ける。
--kinds は {ファイル名の語幹: "main"|"maybe"|"context"} のJSON（scripts/make_kinds.py で作成）。
"""
import argparse
import json
import math
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

try:  # HEIC対応（未導入ならJPEGのみ）
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


def read_exif(src: Path) -> list[dict]:
    """exiftoolでGPS・撮影日時を一括取得する（数値形式）"""
    cmd = ["exiftool", "-json", "-n", "-q", "-GPSLatitude", "-GPSLongitude", "-DateTimeOriginal"]
    for ext in ("jpg", "jpeg", "heic"):
        cmd += ["-ext", ext]
    out = subprocess.run(cmd + [str(src)], capture_output=True, text=True, check=True).stdout
    return json.loads(out) if out.strip() else []


def make_images(args: tuple) -> None:
    """EXIFの向きを反映して、サムネイルと表示用を1回の読み込みで作る"""
    src_file, thumb, photo, tsize, psize = args
    if thumb.exists() and (psize == 0 or photo.exists()):
        return
    with Image.open(src_file) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        for dst, size in ((thumb, tsize), (photo, psize)):
            if size and not dst.exists():
                c = im.copy()
                c.thumbnail((size, size))
                c.save(dst, "JPEG", quality=82)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="images/raw")
    ap.add_argument("--out", default="map")
    ap.add_argument("--kinds", default=None)
    ap.add_argument("--est-loc", default=None)
    ap.add_argument("--exclude-circle", default=None, help="緯度,経度,半径m")
    ap.add_argument("--thumb-size", type=int, default=320)
    ap.add_argument("--photo-size", type=int, default=1200, help="0で表示用画像を作らない")
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    (out / "thumbs").mkdir(parents=True, exist_ok=True)
    if args.photo_size:
        (out / "photos").mkdir(parents=True, exist_ok=True)
    kinds = json.loads(Path(args.kinds).read_text(encoding="utf-8")) if args.kinds else {}
    est = json.loads(Path(args.est_loc).read_text(encoding="utf-8")) if args.est_loc else {}

    ex_lat = ex_lon = ex_r = None
    if args.exclude_circle:
        ex_lat, ex_lon, ex_r = (float(v) for v in args.exclude_circle.split(","))
    excluded = 0
    items, skipped, jobs = [], [], []
    for row in sorted(read_exif(src), key=lambda r: r["SourceFile"]):
        f = Path(row["SourceFile"])
        base = re.sub(r" \(\d+\)$", "", f.stem)  # 重複ファイル「名前 (1)」は元の名前で引き当てる
        e = est.get(f.stem) or est.get(base)
        if "GPSLatitude" in row and "GPSLongitude" in row:
            lat, lon, estimated = row["GPSLatitude"], row["GPSLongitude"], False
        elif e:  # GPSなし → 撮影時刻からの推定位置
            lat, lon, estimated = e["lat"], e["lon"], True
        else:  # 位置不明: 地図のピンにはならず、ページ内の「位置不明」一覧に出る
            lat = lon = None
            estimated = False
            skipped.append(f.name)
        if ex_r is not None and lat is not None:
            dy = (lat - ex_lat) * 111000
            dx = (lon - ex_lon) * 111000 * math.cos(math.radians(ex_lat))
            if math.hypot(dx, dy) <= ex_r:
                excluded += 1
                continue
        taken = None
        if row.get("DateTimeOriginal"):
            taken = datetime.strptime(row["DateTimeOriginal"][:19], "%Y:%m:%d %H:%M:%S").isoformat()
        name = f.stem + ".jpg"
        jobs.append((f, out / "thumbs" / name, out / "photos" / name,
                     args.thumb_size, args.photo_size))
        item = {
            "id": f.stem,
            "lat": None if lat is None else round(lat, 6),
            "lon": None if lon is None else round(lon, 6),
            "taken": taken,
            "thumb": f"thumbs/{name}",
        }
        if args.photo_size:
            item["photo"] = f"photos/{name}"
        if estimated:
            item["est"] = True
        if kinds:
            item["kind"] = kinds.get(f.stem) or kinds.get(base, "context")
        items.append(item)

    with ProcessPoolExecutor() as ex:
        list(ex.map(make_images, jobs, chunksize=16))

    (out / "photos.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    if out.resolve() != Path("map").resolve():
        shutil.copy("map/index.html", out / "index.html")
    print(f"地図用データ: {len(items)}枚（うち位置不明 {len(skipped)}枚は一覧に掲載）/ 範囲除外 {excluded}枚")


if __name__ == "__main__":
    main()
