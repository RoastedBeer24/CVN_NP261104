#!/usr/bin/env python3
"""블루 아워 시나리오 빌드 도구.

story/*.txt 시나리오와 story/meta.json 을 읽어 검증한 뒤
game/js/scenario.js 로 묶는다.

사용법:
    python3 tools/build.py            # 빌드 + 검증
    python3 tools/build.py --check    # 검증만 (파일 쓰지 않음)
    python3 tools/build.py --stats    # 파일별 글자 수 / 예상 플레이 시간
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORY = os.environ.get("BH_STORY", os.path.join(ROOT, "story"))
OUT = os.environ.get("BH_OUT", os.path.join(ROOT, "game", "js", "scenario.js"))

# 읽기 속도 가정: 분당 약 450자 (클릭 포함)
CHARS_PER_MIN = 450

SAY_RE = re.compile(r"^([^\s:：()（）\[\]@#*\-]{1,12})(?:\(([a-z_]+)\))?\s*[:：]\s*(.+)$")
COND_RE = re.compile(r"^[A-Za-z0-9_\s<>=!&|()+\-]+$")
SET_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(=|\+|-)?\s*(-?\d+)?$")
CHOICE_RE = re.compile(r"^-\s*(?:\[([^\]]+)\]\s*)?(.+?)\s*(?:->\s*([A-Za-z0-9_]+))?\s*(?:\{([^}]*)\})?\s*$")

COMMANDS = {
    "chapter", "time", "bg", "show", "hide", "cg", "cgoff", "bgm", "se", "wait",
    "effect", "set", "if", "jump", "choice", "route", "ending", "adult", "adultend",
    "title", "msg",
}
EFFECTS = {"shake", "flash", "dark", "light", "blur", "unblur"}


class BuildError(Exception):
    pass


def parse_set(expr, where, errors):
    out = []
    for part in [p.strip() for p in expr.split(",") if p.strip()]:
        m = SET_RE.match(part)
        if not m:
            errors.append(f"{where}: 잘못된 @set 식 '{part}'")
            continue
        var, op, num = m.group(1), m.group(2), m.group(3)
        if op is None and num is None:
            out.append([var, "=", 1])
        elif op is None or num is None:
            errors.append(f"{where}: 잘못된 @set 식 '{part}'")
        else:
            out.append([var, op, int(num)])
    return out


def check_cond(cond, where, errors):
    if not COND_RE.match(cond):
        errors.append(f"{where}: 조건식에 허용되지 않는 문자 '{cond}'")
    return cond.strip()


def parse_file(path, meta, cmds, labels, errors, warnings, stats):
    fname = os.path.basename(path)
    chars = set(meta["characters"].keys())
    speakers = {v["name"]: k for k, v in meta["characters"].items()}
    exprs = set(meta["expressions"])
    positions = set(meta["positions"])
    text_chars = 0
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    i = 0
    adult_stack = []
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        lineno = i + 1
        where = f"{fname}:{lineno}"
        i += 1
        if not line or line.startswith("#"):
            continue

        if line.startswith("*"):
            name = line[1:].strip()
            if not re.match(r"^[A-Za-z0-9_]+$", name):
                errors.append(f"{where}: 라벨 이름은 영문/숫자/_ 만 가능 '{name}'")
                continue
            if name in labels:
                errors.append(f"{where}: 라벨 중복 '{name}'")
            labels[name] = len(cmds)
            continue

        if line.startswith("@"):
            parts = line[1:].split(None, 1)
            op = parts[0]
            arg = parts[1].strip() if len(parts) > 1 else ""
            if op not in COMMANDS:
                errors.append(f"{where}: 알 수 없는 명령 '@{op}'")
                continue
            c = {"t": op, "src": where}
            if op in ("chapter", "time"):
                c["text"] = arg
                text_chars += len(arg)
            elif op == "bg":
                a = arg.split()
                if not a:
                    errors.append(f"{where}: @bg 에 배경 ID 필요")
                    continue
                c["id"] = a[0]
                c["tr"] = a[1] if len(a) > 1 else "fade"
                stats["bg"].add(a[0])
                if a[0] not in meta["bgs"]:
                    warnings.append(f"{where}: meta.json 에 없는 배경 '{a[0]}' (자리표시자로 표시됨)")
            elif op == "show":
                a = arg.split()
                if len(a) < 1 or a[0] not in chars:
                    errors.append(f"{where}: @show 캐릭터 ID 오류 '{arg}'")
                    continue
                c["ch"] = a[0]
                c["ex"] = a[1] if len(a) > 1 else "normal"
                c["pos"] = a[2] if len(a) > 2 else "center"
                if c["ex"] not in exprs:
                    errors.append(f"{where}: 표정 '{c['ex']}' 없음 (허용: {', '.join(sorted(exprs))})")
                if c["pos"] not in positions:
                    errors.append(f"{where}: 위치 '{c['pos']}' 없음 (허용: {', '.join(meta['positions'])})")
                stats["sprite"].add(f"{c['ch']}_{c['ex']}")
            elif op == "hide":
                if arg != "all" and arg not in chars:
                    errors.append(f"{where}: @hide 대상 오류 '{arg}'")
                c["ch"] = arg or "all"
            elif op == "cg":
                if not arg:
                    errors.append(f"{where}: @cg 에 ID 필요")
                c["id"] = arg
                stats["cg"].add(arg)
            elif op in ("bgm", "se"):
                c["id"] = arg
                if arg and arg != "stop":
                    stats[op].add(arg)
            elif op == "wait":
                try:
                    c["sec"] = float(arg or "1")
                except ValueError:
                    errors.append(f"{where}: @wait 숫자 오류")
            elif op == "effect":
                if arg not in EFFECTS:
                    errors.append(f"{where}: 효과 '{arg}' 없음 (허용: {', '.join(sorted(EFFECTS))})")
                c["id"] = arg
            elif op == "msg":
                if arg not in ("on", "off"):
                    errors.append(f"{where}: @msg 는 on/off")
                c["on"] = arg == "on"
            elif op == "set":
                c["ops"] = parse_set(arg, where, errors)
            elif op == "if":
                m = re.match(r"^(.+?)\s*->\s*([A-Za-z0-9_]+)$", arg)
                if not m:
                    errors.append(f"{where}: @if 형식은 '@if 조건 -> 라벨'")
                    continue
                c["cond"] = check_cond(m.group(1), where, errors)
                c["to"] = m.group(2)
            elif op == "jump":
                c["to"] = arg
            elif op == "route":
                kv = dict(p.split("=", 1) for p in arg.split() if "=" in p)
                c["min"] = int(kv.pop("min", "0"))
                c["else"] = kv.pop("else", None)
                c["map"] = kv
                if not c["else"]:
                    errors.append(f"{where}: @route 에 else= 필요")
            elif op == "ending":
                ids = {e["id"] for e in meta["endings"]}
                if arg not in ids:
                    errors.append(f"{where}: meta.json 에 없는 엔딩 '{arg}'")
                c["id"] = arg
                stats["endings"].add(arg)
            elif op == "adult":
                adult_stack.append(len(cmds))
            elif op == "adultend":
                if not adult_stack:
                    errors.append(f"{where}: 짝 없는 @adultend")
                else:
                    start = adult_stack.pop()
                    cmds[start]["end"] = len(cmds) + 1
            elif op == "choice":
                opts = []
                while i < len(lines) and lines[i].strip().startswith("-"):
                    ol = lines[i].strip()
                    owhere = f"{fname}:{i + 1}"
                    i += 1
                    m = CHOICE_RE.match(ol)
                    if not m:
                        errors.append(f"{owhere}: 선택지 형식 오류")
                        continue
                    o = {"text": m.group(2).strip()}
                    if m.group(1):
                        o["cond"] = check_cond(m.group(1), owhere, errors)
                    if m.group(3):
                        o["to"] = m.group(3)
                    if m.group(4):
                        o["set"] = parse_set(m.group(4), owhere, errors)
                    text_chars += len(o["text"])
                    opts.append(o)
                if len(opts) < 1:
                    errors.append(f"{where}: @choice 다음 줄에 '- 선택지' 가 없음")
                c["opts"] = opts
            cmds.append(c)
            continue

        # 대사 또는 나레이션
        m = SAY_RE.match(line)
        if m and (m.group(1) in speakers or m.group(1) == "나" or m.group(2) or len(m.group(1)) <= 8):
            who, ex, text = m.group(1), m.group(2), m.group(3).strip()
            c = {"t": "say", "who": who, "text": text, "src": where}
            if who in speakers:
                c["ch"] = speakers[who]
            if ex:
                if ex not in exprs:
                    errors.append(f"{where}: 표정 '{ex}' 없음")
                c["ex"] = ex
                if "ch" in c:
                    stats["sprite"].add(f"{c['ch']}_{ex}")
            text_chars += len(text)
        else:
            c = {"t": "say", "text": line, "src": where}
            text_chars += len(line)
        cmds.append(c)

    if adult_stack:
        errors.append(f"{fname}: 닫히지 않은 @adult")
    stats["files"][fname] = text_chars


def main():
    check_only = "--check" in sys.argv
    show_stats = "--stats" in sys.argv
    with open(os.path.join(STORY, "meta.json"), encoding="utf-8") as f:
        meta = json.load(f)

    files = sorted(fn for fn in os.listdir(STORY) if fn.endswith(".txt"))
    cmds, labels, errors, warnings = [], {}, [], []
    stats = {"files": {}, "bg": set(), "cg": set(), "sprite": set(), "bgm": set(), "se": set(), "endings": set()}
    for fn in files:
        parse_file(os.path.join(STORY, fn), meta, cmds, labels, errors, warnings, stats)

    # 라벨 참조 확인
    for c in cmds:
        targets = []
        if c["t"] in ("jump", "if"):
            targets.append(c.get("to"))
        elif c["t"] == "route":
            targets += list(c["map"].values()) + [c["else"]]
        elif c["t"] == "choice":
            targets += [o["to"] for o in c["opts"] if "to" in o]
        for t in targets:
            if t and t not in labels:
                errors.append(f"{c['src']}: 존재하지 않는 라벨 '{t}'")
    if "start" not in labels:
        warnings.append("시작 라벨 '*start' 가 없음")

    total = sum(stats["files"].values())
    if show_stats or not check_only:
        print("== 파일별 글자 수 ==")
        for fn, n in stats["files"].items():
            print(f"  {fn:28s} {n:7,d}자  ~{n / CHARS_PER_MIN:5.1f}분")
        print(f"  {'합계':26s} {total:7,d}자  ~{total / CHARS_PER_MIN / 60:4.2f}시간")
        print(f"  명령 {len(cmds)}개, 라벨 {len(labels)}개")
        missing = [e["id"] for e in meta["endings"] if e["id"] not in stats["endings"]]
        if missing:
            print(f"  아직 연결 안 된 엔딩: {', '.join(missing)}")

    for w in warnings:
        print("경고:", w)
    if errors:
        for e in errors:
            print("오류:", e)
        print(f"\n빌드 실패: 오류 {len(errors)}개")
        sys.exit(1)

    if check_only:
        print("검증 통과")
        return

    for c in cmds:
        c.pop("src", None)
    data = {
        "meta": meta,
        "labels": labels,
        "cmds": cmds,
        "assets": {k: sorted(stats[k]) for k in ("bg", "cg", "sprite", "bgm", "se")},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 자동 생성 파일 — tools/build.py 로 만듦. 직접 수정하지 말 것 */\n")
        f.write("window.SCENARIO = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"빌드 완료 → {os.path.relpath(OUT, ROOT)}")


if __name__ == "__main__":
    main()
