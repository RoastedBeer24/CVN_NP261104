#!/usr/bin/env python3
"""분기 검사: 빌드된 game/js/scenario.js 의 모든 선택지 조합을 탐색해
- 각 엔딩에 도달 가능한지
- 엔딩 없이 끝나거나(파일 끝으로 빠짐) 무한 루프가 되는 경로가 없는지
확인한다.

사용법: python3 tools/simulate.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "game", "js", "scenario.js")


def load():
    txt = open(SRC, encoding="utf-8").read()
    return json.loads(txt[txt.index("=") + 1:].rstrip().rstrip(";"))


def make_cond(expr):
    py = expr.replace("&&", " and ").replace("||", " or ")
    py = re.sub(r"!(?!=)", " not ", py)
    py = re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: m.group(0) if m.group(0) in ("and", "or", "not") else f"v.get('{m.group(0)}',0)", py)
    code = compile(py.strip(), expr, "eval")
    return lambda v: bool(eval(code, {}, {"v": v}))


def main():
    data = load()
    cmds, labels, meta = data["cmds"], data["labels"], data["meta"]
    conds = {}

    def cond(expr, v):
        if expr not in conds:
            conds[expr] = make_cond(expr)
        return conds[expr](dict(v, truecount=4))

    def apply(ops, v):
        v = dict(v)
        for k, op, n in ops or []:
            cur = v.get(k, 0)
            v[k] = cur + n if op == "+" else cur - n if op == "-" else n
        return v

    import random
    rnd = random.Random(1)
    reached = {}
    problems = []
    runs = int(os.environ.get("BH_RUNS", "30000"))
    # 공통 루트부터 + 각 루트 시작점부터(호감도 무관하게 루트 내부 검사)
    starts = ["start"] * (runs // 2) + [s for s in ("rin_start", "yui_start", "shiori_start", "noa_start", "alone_start", "leave_start", "hidden_start") if s in labels] * (runs // 14)
    seen = starts
    for n, origin in enumerate(starts):
        adult = n % 2 == 0
        ptr, v, steps = labels[origin], {}, 0
        # 공통 루트에서 한 히로인에 몰아주는 플레이도 섞기
        favor = rnd.choice([None, "rin", "yui", "shiori", "noa"])
        while True:
            steps += 1
            if steps > 100000:
                problems.append(f"무한 루프 의심: {origin} 에서 ptr={ptr}")
                break
            if ptr >= len(cmds):
                problems.append(f"엔딩 없이 시나리오 끝에 도달 ({origin})")
                break
            c = cmds[ptr]
            t = c["t"]
            if t == "set":
                v = apply(c["ops"], v)
            elif t == "if":
                if cond(c["cond"], v):
                    ptr = labels[c["to"]]
                    continue
            elif t == "jump":
                ptr = labels[c["to"]]
                continue
            elif t == "route":
                best, bv = None, -10**9
                for k, lab in c["map"].items():
                    if v.get(k, 0) > bv:
                        best, bv = lab, v.get(k, 0)
                ptr = labels[best if best and bv >= c["min"] else c["else"]]
                continue
            elif t == "adult" and not adult:
                ptr = c["end"]
                continue
            elif t == "ending":
                reached[c["id"]] = reached.get(c["id"], 0) + 1
                break
            elif t == "title":
                break
            elif t == "choice":
                opts = [o for o in c["opts"] if "cond" not in o or cond(o["cond"], v)]
                if not opts:
                    problems.append(f"보이는 선택지가 없음: ptr={ptr} ({origin})")
                    break
                pref = [o for o in opts if favor and any(op[0] == favor and op[1] == "+" for op in o.get("set", []))]
                good = [o for o in opts if any(op[0] == "rp" and op[1] == "+" for op in o.get("set", []))]
                pool = pref if pref and rnd.random() < 0.8 else good if good and rnd.random() < 0.5 else opts
                o = rnd.choice(pool)
                v = apply(o.get("set"), v)
                ptr = labels[o["to"]] if "to" in o else ptr + 1
                continue
            ptr += 1

    print(f"무작위 플레이 {len(seen):,}회")
    ok = True
    for e in meta["endings"]:
        n = reached.get(e["id"], 0)
        mark = "OK " if n else "없음"
        if not n:
            ok = False
        print(f"  [{mark}] {e['no']:02d} {e['id']:14s} {e['title']}  (도달 경로 {n:,})")
    for p in sorted(set(problems))[:30]:
        print("문제:", p)
    if problems or not ok:
        sys.exit(1)
    print("모든 엔딩 도달 가능, 막힌 경로 없음")


if __name__ == "__main__":
    main()
