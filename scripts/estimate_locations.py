"""GPSのない写真（TG-6など）の位置を、撮影時刻の近い GPS付き写真から推定する。

規則:
    interp  ... 前後の両方にGPS写真があり、どちらも --both 秒以内 → 時刻で直線補間
    nearest ... 片側のみ、--one 秒以内 → 最寄りの写真の位置
    carry   ... 上記に当てはまらない場合、直前のGPS写真から --carry 秒以内 → その写真と同じ場所
                （デジカメの写真を翌日ごろに写真アプリへ取り込むことがあるため。間にGPS写真が無いことが前提）
    上記以外は位置なし（地図に載せない）

使い方: .venv/bin/python scripts/estimate_locations.py   → work/est_loc.json
キーは書き出しファイル名の語幹（撮影日時_元ファイル名、拡張子なし）。値に推定方法と時間差を持つ。
前提: カメラの時計が iPhone と大きくずれていないこと（ずれがあると位置が外れる）。
"""
import argparse
import bisect
import json
from pathlib import Path

import osxphotos

ALBUM = "地衣類（候補）"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--both", type=int, default=1800)
    ap.add_argument("--one", type=int, default=600)
    ap.add_argument("--carry", type=int, default=86400, help="直前のGPS写真の場所を引き継ぐ最大秒数（既定1日）")
    args = ap.parse_args()

    db = osxphotos.PhotosDB()
    ref = sorted((p for p in db.photos() if not p.ismovie and p.location[0] is not None),
                 key=lambda p: p.date)
    rt = [p.date.timestamp() for p in ref]
    album = next(a for a in db.album_info if a.title == ALBUM)

    out, stat = {}, {"interp": 0, "nearest": 0, "carry": 0, "none": 0}
    for p in album.photos:
        if p.location[0] is not None:
            continue
        t = p.date.timestamp()
        i = bisect.bisect_left(rt, t)
        prev = ref[i - 1] if i > 0 else None
        nxt = ref[i] if i < len(ref) else None
        gp = t - rt[i - 1] if prev else None
        gn = rt[i] - t if nxt else None
        stem = f"{p.date.strftime('%Y%m%d_%H%M%S')}_{Path(p.original_filename).stem}"
        if prev and nxt and gp <= args.both and gn <= args.both:
            w = gp / (gp + gn) if (gp + gn) else 0.0
            lat = prev.location[0] + (nxt.location[0] - prev.location[0]) * w
            lon = prev.location[1] + (nxt.location[1] - prev.location[1]) * w
            out[stem] = {"lat": lat, "lon": lon, "method": "interp", "gap": int(min(gp, gn))}
            stat["interp"] += 1
        else:
            cands = [(g, q) for g, q in ((gp, prev), (gn, nxt)) if q is not None and g <= args.one]
            if cands:
                g, q = min(cands, key=lambda c: c[0])
                out[stem] = {"lat": q.location[0], "lon": q.location[1], "method": "nearest", "gap": int(g)}
                stat["nearest"] += 1
            elif prev and gp <= args.carry:  # 直前のGPS写真から1日以内: 同じ場所とみなす
                out[stem] = {"lat": prev.location[0], "lon": prev.location[1], "method": "carry", "gap": int(gp)}
                stat["carry"] += 1
            else:
                stat["none"] += 1
    Path("work/est_loc.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"推定: 補間 {stat['interp']} / 最寄り {stat['nearest']} / 引き継ぎ {stat['carry']} / 位置なし {stat['none']}")


if __name__ == "__main__":
    main()
