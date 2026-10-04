"""書き出した写真の「種別」を、判定結果から作る（地図の絞り込み用）。

    main    ... 判定「あり」（地衣類が主役）
    maybe   ... 判定「可能性あり」
    context ... 上記以外（前後の全景など）

使い方: .venv/bin/python scripts/make_kinds.py   → work/kinds.json
キーは書き出しファイル名の語幹（撮影日時_元ファイル名、拡張子なし）。
"""
import json
from pathlib import Path

import osxphotos

SETS = ["judged.json", "judged_digicam.json", "judged_se.json",
        "judged_i8p_core.json", "judged_i6s_core.json"]
ALBUM = "地衣類（候補）"


def main() -> None:
    score: dict[str, int] = {}
    for f in SETS:
        p = Path("work") / f
        if p.exists():
            for u, v in json.loads(p.read_text(encoding="utf-8")).items():
                score[u] = max(score.get(u, 0), v)
    db = osxphotos.PhotosDB()
    album = next(a for a in db.album_info if a.title == ALBUM)
    kinds = {}
    for p in album.photos:
        stem = f"{p.date.strftime('%Y%m%d_%H%M%S')}_{Path(p.original_filename).stem}"
        kinds[stem] = {2: "main", 1: "maybe"}.get(score.get(p.uuid, 0), "context")
    Path("work/kinds.json").write_text(json.dumps(kinds, ensure_ascii=False), encoding="utf-8")
    vals = list(kinds.values())
    print(f"種別: main {vals.count('main')} / maybe {vals.count('maybe')} / context {vals.count('context')}")


if __name__ == "__main__":
    main()
