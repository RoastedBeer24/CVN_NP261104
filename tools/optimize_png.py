#!/usr/bin/env python3
"""game/assets 의 PNG 를 무손실 최적화. 픽셀이 원본과 완전히 같을 때만 교체한다."""
import glob, os, sys
import numpy as np
import oxipng
from PIL import Image
from concurrent.futures import ProcessPoolExecutor

def one(p):
    tmp = p + ".opt"
    oxipng.optimize(p, tmp, level=4, strip=oxipng.StripChunks.safe())
    a, b = Image.open(p), Image.open(tmp)
    same = a.size == b.size and np.array_equal(np.array(a.convert("RGBA")), np.array(b.convert("RGBA")))
    s0, s1 = os.path.getsize(p), os.path.getsize(tmp)
    if same and s1 < s0:
        os.replace(tmp, p)
        return p, s0, s1, "ok"
    os.remove(tmp)
    return p, s0, s0, "kept" if same else "MISMATCH"

if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game", "assets")
    files = sorted(glob.glob(os.path.join(root, "*", "*.png")))
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(one, files))
    t0 = sum(r[1] for r in res); t1 = sum(r[2] for r in res)
    bad = [r[0] for r in res if r[3] == "MISMATCH"]
    print(f"{len(res)}개: {t0/1e6:.1f}MB → {t1/1e6:.1f}MB ({(1-t1/t0)*100:.1f}% 감소), 픽셀 불일치 {len(bad)}")
    for b in bad: print("불일치(원본 유지):", b)
