"""写真アプリから地衣類の候補を探し、Claudeで判定する（初回の網羅用）。

流れ:
    candidates ... 写真ライブラリから候補（iPhone 15 Pro・自然物ラベル/ラベルなし・人物書類除外）を抽出
    trial      ... 既知の地衣類と未知の候補を混ぜた試験セットでコンタクトシートを作り、判定精度を測る
    judge-trial... 試験シートをClaude CLIで判定し、正解（既知/未知）と照合して精度を出す
    album      ... 判定結果（あり/可能性あり）を写真アプリのアルバムに登録（既定はドライラン、--apply で実行）
    context    ... 「あり」写真の前後（時刻・距離が近い）の全景写真をアルバムへ追加（既定はドライラン）
    judge      ... 全候補をコンタクトシート化してClaudeに判定させ work/judged.json に保存（再開可）

使い方（lichens/ で実行。osxphotos は .venv に導入済み）:
    .venv/bin/python scripts/find_lichens.py candidates
    .venv/bin/python scripts/find_lichens.py trial --n 60

出力は work/（Git管理外）。写真は縮小して判定用に Anthropic へ送られる点に注意。
"""
import argparse
import bisect
import json
import math
import random
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import osxphotos
from PIL import Image, ImageDraw, ImageOps

WORK = Path("work")
CAMERA = "iPhone 15 Pro"
# 人物・書類系のラベルを持つ写真は除外
EXCLUDE = {"人々", "子ども", "書類", "印刷されたページ", "衣類"}
# 自然物系のラベル（地衣類は「動物」「フジツボ」等に誤分類されるため広めに取る）
NATURE = {"植物", "樹幹", "岩", "コケ", "葉", "枝", "草", "土壌", "ツリー", "動物",
          "節足動物", "フジツボ", "虫", "土地", "アウトドア", "クローズアップ", "小道", "壁"}
COLS, ROWS, CELL = 4, 3, 300  # 1枚のシートに12枚


def key(p) -> tuple:
    """既知写真との突き合わせ用キー（ファイル名は再利用されるため撮影日時も使う）"""
    return (Path(p.original_filename).stem, p.date.strftime("%Y-%m-%dT%H:%M"))


def known_keys() -> set:
    rows = json.loads(Path("map/photos.json").read_text(encoding="utf-8"))
    return {(r["id"], r["taken"][:16]) for r in rows}


def is_candidate(p) -> bool:
    if p.ismovie or not p.exif_info or CAMERA not in (p.exif_info.camera_model or ""):
        return False
    labels = set(p.labels)
    if labels & EXCLUDE:
        return False
    return not labels or bool(labels & NATURE)


def is_digicam_candidate(p) -> bool:
    """Apple以外のデジタルカメラで撮った横長写真（人物・書類系ラベルを除外、自然物ラベルかラベルなし）"""
    e = p.exif_info
    if p.ismovie or not e or not e.camera_model or "Apple" in (e.camera_make or ""):
        return False
    if p.width <= p.height:
        return False
    labels = set(p.labels)
    if labels & EXCLUDE:
        return False
    return not labels or bool(labels & NATURE)


def make_model_candidate(model: str, require: set | None = None):
    """指定機種（完全一致）で、人物・書類系を除き、自然物ラベルかラベルなしの写真。
    require を指定すると、そのラベルのいずれかを持つ写真に限る（低コストの取りこぼし確認用）"""
    def f(p) -> bool:
        e = p.exif_info
        if p.ismovie or not e or (e.camera_model or "").strip() != model:
            return False
        labels = set(p.labels)
        if labels & EXCLUDE:
            return False
        if require is not None:
            return bool(labels & require)
        return not labels or bool(labels & NATURE)
    return f


CORE_LABELS = {"樹幹", "コケ", "クローズアップ"}


SETS = {
    "iphone": (is_candidate, "judged.json"),
    "digicam": (is_digicam_candidate, "judged_digicam.json"),
    "se": (make_model_candidate("iPhone SE (3rd generation)"), "judged_se.json"),
    "i8p": (make_model_candidate("iPhone 8 Plus"), "judged_i8p.json"),
    "i6s": (make_model_candidate("iPhone 6s"), "judged_i6s.json"),
    "i8p_core": (make_model_candidate("iPhone 8 Plus", CORE_LABELS), "judged_i8p_core.json"),
    "i6s_core": (make_model_candidate("iPhone 6s", CORE_LABELS), "judged_i6s_core.json"),
}


def load_candidates(which: str = "iphone") -> list:
    db = osxphotos.PhotosDB()
    return [p for p in db.photos() if SETS[which][0](p)]


def thumb_path(p) -> Path | None:
    """判定用の縮小版（ライブラリ内のderivative。原本はiCloud上のことが多い）"""
    return Path(p.path_derivatives[0]) if p.path_derivatives else None


def make_sheet(items: list, out: Path) -> None:
    """items=[(番号, 画像パス)] を格子状に並べ、各コマに番号を描き込む"""
    sheet = Image.new("RGB", (COLS * CELL, ROWS * CELL), "white")
    d = ImageDraw.Draw(sheet)
    for i, (num, path) in enumerate(items):
        with Image.open(path) as im:
            im = ImageOps.fit(ImageOps.exif_transpose(im).convert("RGB"), (CELL - 4, CELL - 4))
        x, y = (i % COLS) * CELL + 2, (i // COLS) * CELL + 2
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 46, y + 30], fill="black")
        d.text((x + 8, y + 8), str(num), fill="yellow")
    sheet.save(out, "JPEG", quality=85)


def cmd_candidates(_args) -> None:
    WORK.mkdir(exist_ok=True)
    cands = load_candidates()
    known = known_keys()
    rows = [{"uuid": p.uuid, "name": p.original_filename, "date": p.date.isoformat(),
             "labels": list(p.labels), "known": key(p) in known} for p in cands]
    (WORK / "candidates.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"候補 {len(rows)}枚（既知の地衣類 {sum(r['known'] for r in rows)}枚を含む）")


def cmd_trial(args) -> None:
    """既知n枚＋未知n枚を混ぜ、正解を伏せたままシート化する"""
    WORK.mkdir(exist_ok=True)
    random.seed(args.seed)
    cands = load_candidates()
    known = known_keys()
    pos = [p for p in cands if key(p) in known and thumb_path(p)]
    neg = [p for p in cands if key(p) not in known and thumb_path(p)]
    sel = random.sample(pos, min(args.n, len(pos))) + random.sample(neg, args.n)
    random.shuffle(sel)
    per = COLS * ROWS
    answers = {}
    sheets = []
    for s in range(0, len(sel), per):
        chunk = sel[s:s + per]
        out = WORK / f"trial_{s // per:03d}.jpg"
        make_sheet([(i + 1, thumb_path(p)) for i, p in enumerate(chunk)], out)
        sheets.append(out.name)
        answers[out.name] = {str(i + 1): {"uuid": p.uuid, "known": key(p) in known}
                             for i, p in enumerate(chunk)}
    (WORK / "trial_answers.json").write_text(json.dumps(answers, indent=1), encoding="utf-8")
    print(f"シート {len(sheets)}枚（既知{args.n}＋未知{args.n}）を work/ に作成")


PROMPT = (
    "画像 {path} を Read ツールで読んでください。番号付きの12コマのコンタクトシートです。"
    "各コマについて、地衣類が写っているかを3段階で判定してください。"
    "2=地衣類が主な被写体、または樹幹・岩・壁に灰白色〜緑灰色の地衣類の被覆（粉状・痂状・葉状）が"
    "はっきり見える。1=地衣類かもしれない（樹皮・岩の模様や被覆が曖昧）。"
    "0=地衣類ではない（コケ・菌類・虫・風景・人工物・植物の葉や花など）。"
    "後で人が目視確認するので、迷う場合は 1 にしてください。"
    "出力は次のJSONのみ（説明文なし）: "
    '{{"1": 2, "2": 0, ...}}（キーはコマ番号1〜12）'
)


def ask_claude(sheet: Path, model: str) -> dict:
    """Claude Code CLI（サブスク）でシートを判定し、{番号: bool} を返す"""
    out = subprocess.run(
        ["claude", "-p", PROMPT.format(path=sheet.resolve()), "--model", model,
         "--allowedTools", "Read"],
        capture_output=True, text=True, timeout=300,
    ).stdout
    start, end = out.find("{"), out.rfind("}")
    return json.loads(out[start:end + 1])


def cmd_judge_trial(args) -> None:
    answers = json.loads((WORK / "trial_answers.json").read_text(encoding="utf-8"))
    tp = fp = fn = tn = 0
    misses, falses = [], []
    for name, cells in answers.items():
        try:
            got = ask_claude(WORK / name, args.model)
        except Exception as e:  # 判定失敗のシートは飛ばして続行
            print(f"  {name}: 判定失敗 ({e})")
            continue
        for num, info in cells.items():
            pred, truth = int(got.get(num, 0)) >= 1, info["known"]
            tp += pred and truth
            fn += (not pred) and truth
            fp += pred and (not truth)
            tn += (not pred) and (not truth)
            if truth and not pred:
                misses.append(f"{name}#{num}")
            if pred and not truth:
                falses.append(f"{name}#{num}")
        print(f"  {name}: 完了")
    print(f"既知の地衣類の検出 {tp}/{tp + fn}（再現率）、未知のうち『地衣類』判定 {fp}/{fp + tn}")
    print("見逃し:", misses)
    print("未知で地衣類判定（要目視。実は地衣類かもしれない）:", falses)


def cmd_judge(args) -> None:
    """全候補を12枚ずつシート化して判定。結果は {uuid: 0/1/2} で逐次保存（中断→再実行で続きから）"""
    WORK.mkdir(exist_ok=True)
    (WORK / "sheets").mkdir(exist_ok=True)
    out_file = WORK / SETS[args.set][1]
    judged = json.loads(out_file.read_text(encoding="utf-8")) if out_file.exists() else {}
    cands = sorted((p for p in load_candidates(args.set) if thumb_path(p)), key=lambda p: p.date)
    todo = [p for p in cands if p.uuid not in judged]
    if args.sample:  # 地衣類の含有率を見積もるための無作為抽出（結果は保存され、全件実行時に再利用）
        random.seed(0)
        todo = random.sample(todo, min(args.sample, len(todo)))
    per = COLS * ROWS
    chunks = [todo[i:i + per] for i in range(0, len(todo), per)]
    print(f"候補 {len(cands)}枚 / 判定済み {len(judged)} / 残り {len(todo)}枚 = {len(chunks)}シート")
    lock = threading.Lock()
    done = [0]

    def work(idx_chunk):
        idx, chunk = idx_chunk
        sheet = WORK / "sheets" / f"s_{chunk[0].uuid[:8]}.jpg"
        make_sheet([(i + 1, thumb_path(p)) for i, p in enumerate(chunk)], sheet)
        for attempt in range(2):  # 失敗時は1回だけ再試行
            try:
                got = ask_claude(sheet, args.model)
                break
            except Exception as e:
                got = None
                err = e
        with lock:
            if got is None:
                print(f"  シート{idx}: 判定失敗 ({err})", flush=True)
                return
            for i, p in enumerate(chunk):
                judged[p.uuid] = int(got.get(str(i + 1), 0))
            out_file.write_text(json.dumps(judged), encoding="utf-8")
            done[0] += 1
            print(f"  {done[0]}/{len(chunks)} 完了", flush=True)
        sheet.unlink(missing_ok=True)

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(work, enumerate(chunks)))
    vals = list(judged.values())
    print(f"結果: あり {vals.count(2)} / 可能性あり {vals.count(1)} / なし {vals.count(0)}"
          f"（未判定 {len([p for p in cands if p.uuid not in judged])}枚）")


def cmd_album(args) -> None:
    """judged.json の score>=min を写真アプリのアルバムへ登録する（ライブラリを書き換える）"""
    judged = json.loads((WORK / SETS[args.set][1]).read_text(encoding="utf-8"))
    uuids = [u for u, v in judged.items() if v >= args.min]
    db = osxphotos.PhotosDB()
    exists = any(a.title == args.name for a in db.album_info)
    print(f"対象 {len(uuids)}枚（score>={args.min}）→ アルバム「{args.name}」"
          f"（既存: {'あり' if exists else 'なし'}）")
    if not args.apply:
        print("ドライラン: ライブラリは変更していません。実行は --apply を付ける")
        return
    import photoscript
    lib = photoscript.PhotosLibrary()
    # 全アルバムの列挙は大規模ライブラリでタイムアウトするため、既存確認は osxphotos 側で済ませる
    album = lib.album(args.name) if exists else lib.create_album(args.name)
    # 写真アプリは追加命令ごとに確認を出すため、1回でまとめて追加する
    album.add([photoscript.Photo(u) for u in uuids])
    print("登録完了")


def find_context(db, judged: dict, in_album: set, sec: int, m: int) -> set:
    """判定「あり」(2)の写真の前後（sec秒・mメートル以内）にある、同じ機種の写真を返す。
    すでにアルバムにある写真・人物系は除く"""
    def model(p):
        e = p.exif_info
        return (e.camera_model or "").strip() if e else ""

    ps = sorted((p for p in db.photos() if not p.ismovie and model(p)), key=lambda p: p.date)
    times = [p.date.timestamp() for p in ps]

    def dist(a, b):
        (la, lo), (lb, lo2) = a.location, b.location
        if None in (la, lo, lb, lo2):
            return None
        return math.hypot((la - lb) * 111000, (lo - lo2) * 111000 * math.cos(math.radians(la)))

    found = set()
    for p in ps:
        if judged.get(p.uuid) != 2:  # 地衣類が主役の写真だけを起点にする
            continue
        t = p.date.timestamp()
        i = bisect.bisect_left(times, t - sec)
        while i < len(ps) and times[i] <= t + sec:
            q, i = ps[i], i + 1
            if q.uuid in in_album or set(q.labels) & EXCLUDE or model(q) != model(p):
                continue
            d = dist(p, q)
            if d is None or d <= m:
                found.add(q.uuid)
    return found


def cmd_context(args) -> None:
    """判定結果（--sets で複数指定可）の「あり/可能性あり」と、その前後の全景を、1回の追加命令でまとめて登録する"""
    db = osxphotos.PhotosDB()
    in_album = {p.uuid for x in db.album_info if x.title == args.name for p in x.photos}
    main_ids, ctx_ids = set(), set()
    for key in args.sets.split(","):
        judged = json.loads((WORK / SETS[key][1]).read_text(encoding="utf-8"))
        ids = {u for u, v in judged.items() if v >= args.min} - in_album
        ctx = find_context(db, judged, in_album | ids, args.sec, args.m)
        print(f"  [{key}] 判定分 {len(ids)}枚 / 全景 {len(ctx)}枚")
        main_ids |= ids
        ctx_ids |= ctx
    allids = sorted(main_ids | ctx_ids)
    print(f"合計 {len(allids)}枚（アルバム「{args.name}」へ。既に入っている分は除外済み）")
    if not args.apply:
        print("ドライラン: ライブラリは変更していません。実行は --apply を付ける")
        return
    import photoscript
    album = photoscript.PhotosLibrary().album(args.name)
    album.add([photoscript.Photo(u) for u in allids])  # 確認回数を減らすため1回でまとめて追加
    print("追加完了")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("candidates").set_defaults(func=cmd_candidates)
    t = sub.add_parser("trial")
    t.add_argument("--n", type=int, default=60)
    t.add_argument("--seed", type=int, default=0)
    t.set_defaults(func=cmd_trial)
    j = sub.add_parser("judge-trial")
    j.add_argument("--model", default="sonnet")
    j.set_defaults(func=cmd_judge_trial)
    a = sub.add_parser("judge")
    a.add_argument("--model", default="sonnet")
    a.add_argument("--workers", type=int, default=3)
    a.add_argument("--set", choices=list(SETS), default="iphone")
    a.add_argument("--sample", type=int, default=0, help="指定枚数だけ無作為に判定する")
    a.set_defaults(func=cmd_judge)
    b = sub.add_parser("album")
    b.add_argument("--name", default="地衣類（候補）")
    b.add_argument("--min", type=int, default=1, help="登録する最低スコア（2=あり, 1=可能性あり以上）")
    b.add_argument("--apply", action="store_true")
    b.add_argument("--set", choices=list(SETS), default="iphone")
    b.set_defaults(func=cmd_album)
    c = sub.add_parser("context")
    c.add_argument("--name", default="地衣類（候補）")
    c.add_argument("--sec", type=int, default=120)
    c.add_argument("--m", type=int, default=30)
    c.add_argument("--apply", action="store_true")
    c.add_argument("--sets", default="iphone", help="カンマ区切り（例: se,i8p_core,i6s_core）")
    c.add_argument("--min", type=int, default=1)
    c.set_defaults(func=cmd_context)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
