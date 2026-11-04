#!/usr/bin/env python3
"""Drive MCP 다운로드 결과(JSON, base64)를 원본 바이트 그대로 게임 에셋 폴더에 저장."""
import base64, json, sys, os, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in sys.argv[1:]:
    d = json.load(open(path))
    title = d["title"]
    stem = title.rsplit(".", 1)[0]
    ch = stem.split("_")[0] in ("rin", "yui", "shiori", "noa", "kondo", "maki", "okabe") and stem.split("_", 1)[1] in (
        "normal", "smile", "laugh", "sad", "angry", "surprised", "shy", "serious", "tired", "cry")
    sub = "ch" if ch else "bg"
    out = os.path.join(ROOT, "game", "assets", sub, title)
    raw = base64.b64decode(d["content"])
    open(out, "wb").write(raw)
    print(f"{sub}/{title} {len(raw):,} bytes md5={hashlib.md5(raw).hexdigest()[:8]}")
