#!/usr/bin/env python3
"""이미지 생성 키트 데이터 생성.

docs/assets/*.md 의 CG·배경 프롬프트, story/meta.json 의 배경 목록,
빌드된 scenario.js 의 실제 사용 에셋을 모아 GPT 에 붙여넣을 배치 메시지로 묶는다.
결과: docs/assets/image_kit.json  (아티팩트 페이지가 이 데이터를 사용)
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "docs", "assets")

# ── 그림체 (사용자가 준 참고 그림의 '그림체만' 언어화) ──
STYLE = (
    "Soft painterly anime illustration. Thin, slightly uneven dark brown-black lineart with a hand-drawn, "
    "lightly sketchy quality. Flat cel shading with a subtle gouache / watercolor-like texture inside the color "
    "fills and soft visible brush grain. Muted, slightly desaturated palette with rich deep darks and one clear "
    "accent color per image. Minimal gradients, simple clean shapes, gentle soft shadows, no heavy glow, no bloom, "
    "no glossy 3D rendering. Faces: delicate features, large expressive eyes with soft highlights, light natural "
    "blush, calm subtle expressions. Overall mood: calm, elegant, slightly melancholic."
)

START_MSG = f"""지금부터 비주얼 노벨 「블루 아워」에 들어갈 이미지를 여러 장 연속으로 만들 거야.
모든 이미지에 아래 그림체를 똑같이 적용해 줘.

[그림체 — STYLE]
{STYLE}

[작품 설정]
- 현대 일본 도쿄 기요스미시라카와(운하가 있는 조용한 동네)가 배경인 현대 연애물.
- 판타지 요소 없음. 마녀 모자·로브·지팡이 같은 소재는 절대 넣지 마.
- 등장인물은 모두 성인. 노출 없음.
- 이미지 안에 글자·로고·워터마크·말풍선 넣지 마 (따로 지시한 경우 제외).

[참고 그림을 첨부했다면]
첨부 그림에서는 선·채색·질감 같은 그림체만 참고하고, 캐릭터 얼굴·머리색·의상·소품은 가져오지 마.

[진행 방식]
이후 내가 「배치」 메시지를 보내면, 그 안의 이미지를 번호 순서대로 한 장씩 끝까지 연속으로 생성해 줘.
중간에 확인 질문은 하지 말고, 각 이미지 바로 위에 지정된 파일명을 한 줄로 적어 줘.
이해했으면 "준비됨"이라고만 답해 줘."""

ZIP_MSG = """지금까지 이 대화에서 만든 이미지를 각각 위에 적힌 파일명(.png)으로 저장해서 ZIP 파일 하나로 묶어 줘.
파일명이 겹치면 마지막에 만든 것을 사용해 줘."""

LAND = "Landscape 3:2 (1536x1024), wide cinematic composition, safe to crop to 16:9."
PORT = ("Portrait 2:3 (1024x1536), fully TRANSPARENT background PNG, single character only, standing sprite framed "
        "from the top of the head to mid-thigh, centered, facing slightly toward the viewer, relaxed natural pose, "
        "even soft lighting, no shadow on the ground.")

# ── 기본 배경 영어 프롬프트 (meta.json 설명 기반) ──
BG = {
    "ext_aono_day": "Exterior of a six-story 1968 Japanese modernist reinforced-concrete apartment building beside a calm canal in daytime, horizontal ribbon windows with a long tilted clerestory band on each floor, weathered grey concrete with board-marked texture, small balconies with potted plants, a low bridge and cherry trees along the canal promenade, clear spring sky.",
    "ext_aono_dusk": "Exterior of a six-story 1968 Japanese modernist concrete apartment with horizontal ribbon windows and a tilted clerestory band on each floor, beside a canal, at blue hour just after sunset, sky deep blue, windows lighting up one by one in warm amber, canal water reflecting the blue sky and the windows.",
    "ext_aono_night": "Exterior of a six-story 1968 Japanese modernist concrete apartment with horizontal ribbon windows, beside a canal, at night, a few windows lit warm, streetlights reflected on dark canal water, quiet residential night.",
    "rooftop_day": "Flat rooftop of an old six-story concrete apartment in daytime, low concrete parapet, a rusty water tank on legs, a small dusty steel-and-glass greenhouse with a padlocked door in the corner, laundry poles, view over low Tokyo rooftops and a canal, soft clear sky.",
    "rooftop_dusk": "Flat rooftop of an old six-story concrete apartment at blue hour, low concrete parapet, rusty water tank and the small locked glass greenhouse, the city and canal below sinking into deep blue, first windows lighting up, distant Tokyo Skytree silhouette.",
    "rooftop_night": "Flat rooftop of an old six-story concrete apartment at night, rusty water tank and locked glass greenhouse in silhouette, distant Tokyo Skytree lit up, scattered city lights, dark navy sky.",
    "stairwell": "A spiral staircase inside a 1960s modernist apartment winding around a small open courtyard, terrazzo treads, slim steel handrail, a skylight at the top dropping a column of soft daylight, grey concrete walls.",
    "stairwell_night": "A spiral concrete staircase inside a 1960s modernist apartment winding around a small courtyard, at night lit by bare incandescent bulbs on each landing, warm pools of light and deep shadows, terrazzo treads.",
    "hallway": "Open-air exterior corridor of an old Japanese apartment building, a row of identical painted steel doors with small nameplates, concrete parapet on one side overlooking a canal, afternoon light.",
    "room601_day": "Almost empty apartment room in a 1960s modernist building in daytime, a wooden drafting table, a few cardboard moving boxes, worn oak flooring, white plaster walls, a large window facing a canal with a long tilted clerestory window above it.",
    "room601_dusk": "Almost empty room in a 1960s modernist apartment at blue hour, large canal-facing window with a tilted clerestory above, rippling blue light reflected from the canal dancing across the pale ceiling, drafting table in silhouette, deep blue atmosphere.",
    "room601_night": "Almost empty room in a 1960s modernist apartment at night, a desk lamp on the drafting table lighting rolled drawings and a scale ruler, dark window, cardboard boxes, quiet late-night work mood.",
    "room601_rain": "Almost empty room in a 1960s modernist apartment on a rainy day, rain streaking the large window, grey diffuse light, drafting table and boxes, quiet melancholic mood.",
    "kondo_office": "Small caretaker's office on the ground floor of an old apartment building, a wooden go board with stones, an old wall cabinet full of numbered keys on hooks, a transistor radio, a kettle, faded calendar, warm cluttered nostalgic feel.",
    "cafe_day": "A small specialty coffee cafe on the ground floor of a 1960s concrete building in daytime, exposed board-marked concrete ceiling, long solid wood counter, a compact drum coffee roaster, pour-over kettles, a few stools, large window facing a canal, calm natural light.",
    "cafe_night": "A small cafe on the ground floor of a 1960s concrete building, turned into a whisky bar at night, warm amber pendant lights over the wooden counter, shelves of whisky bottles, exposed concrete ceiling, dark canal outside the window, intimate quiet mood.",
    "yui_room": "A small apartment illustrator's studio at night, two glowing monitors and a drawing tablet on a desk, walls covered with pinned sketches of lit windows, blackout curtains with one window uncovered, scattered ink bottles, purple-blue night palette.",
    "room302": "An empty old apartment room in afternoon light, bare wooden floor with four small dents from piano casters, a paler rectangle on the wallpaper where a piano once stood, a worn wooden door frame with faint pencil height marks.",
    "canal_day": "A canal promenade in Kiyosumi-Shirakawa Tokyo in daytime, calm water, a low concrete bridge, cherry trees along a paved walkway, low-rise houses and a small roastery cafe across the water, gentle spring light.",
    "canal_night": "A canal promenade in Kiyosumi-Shirakawa Tokyo at night, streetlights reflected as long trembling lines on dark water, low bridge in silhouette, quiet residential night.",
    "street_kiyosumi": "A quiet backstreet in Kiyosumi-Shirakawa Tokyo, small coffee roasteries and galleries in renovated old buildings, low wooden houses with potted plants, utility poles and wires, soft afternoon light.",
    "garden_kiyosumi": "Kiyosumi Japanese landscape garden, a large pond with stepping stones, pine trees, a traditional wooden pavilion, carp in the water, calm overcast light.",
    "museum": "Lobby of a large contemporary art museum in Tokyo, very high ceiling, long glass curtain wall, polished stone floor, minimal benches, bright diffuse daylight.",
    "office_minato": "A high-floor corporate meeting room of a real estate developer, long white table with chairs, floor-to-ceiling glass windows overlooking central Tokyo towers, cool corporate lighting, a projector screen.",
    "shiori_apartment": "Minimal high-rise apartment living room at night, floor-to-ceiling window with Tokyo Bay night view, low sofa, an upright piano covered with a grey cloth, warm floor lamp, very tidy.",
    "university": "University architecture department studio, long tables with white foam-board models, cutting mats, rolled drawings, pin-up walls with plans and sections, large windows with daylight.",
    "station": "Platform of Kiyosumi-Shirakawa subway station in Tokyo, tiled walls, platform screen doors, station signs without readable text, fluorescent lighting, nearly empty.",
    "izakaya": "A tiny izakaya in Monzen-Nakacho Tokyo, narrow wooden counter with a few stools, menu strips on the wall without readable text, red paper lantern, yakitori grill smoke, warm amber light.",
    "park_rain": "A small Tokyo neighborhood park in June rain, clusters of blue and purple hydrangeas, wet benches, puddles reflecting the grey sky, soft rain lines.",
    "festival": "Fukagawa summer festival street at dusk in old downtown Tokyo, rows of red paper lanterns, food stalls with warm incandescent light, festive yet nostalgic mood.",
    "fireworks_river": "Sumida river summer fireworks at night, large colorful fireworks blooming over the river, reflections on the water, distant crowd silhouettes along the embankment.",
    "beach_kamakura": "Yuigahama beach in Kamakura on a summer afternoon, gentle waves, wide sand, a few distant beach umbrellas, green hills at the end of the bay, bright sea glitter.",
    "shibuya_night": "Shibuya street at night, neon signs without readable text, crowds as soft blurred silhouettes, wet asphalt reflecting colored light.",
    "gallery_space": "A small white cube art gallery, white walls, polished concrete floor, track lighting, a few framed small canvases on the walls, quiet minimal space.",
    "hospital": "A clean hospital corridor in Tokyo, pale walls, handrails, a bench, soft fluorescent light, a window at the end, quiet tense mood.",
    "christmas_street": "Marunouchi avenue in Tokyo at Christmas, rows of trees wrapped in warm golden illumination lights, elegant stone buildings, people as soft silhouettes, cold winter night.",
    "winter_canal": "The canal promenade in Kiyosumi-Shirakawa on a snowy winter evening, light snow falling, bare cherry trees, streetlights glowing, snow on the bridge railings, blue-grey dusk.",
    "demolition": "An old six-story modernist concrete apartment building wrapped in white construction hoarding panels and scaffolding nets just before demolition, canal in front, overcast sky, quiet ending mood.",
    "light_room": "Interior of a small dusty steel-and-glass greenhouse on a rooftop at blue hour, old glass panes tilted toward a canal, a worn wooden drafting table, empty clay pots, dried soil, the sky glowing deep blue through the glass.",
}
SKIP_BG = {"black", "white"}

EXPR = {
    "normal": "neutral calm default expression",
    "smile": "gentle small smile",
    "laugh": "laughing openly, eyes narrowed with joy",
    "sad": "sad expression, eyes lowered",
    "angry": "frowning, visibly irritated",
    "surprised": "surprised, eyes widened, lips slightly parted",
    "shy": "shy and embarrassed, light blush, eyes glancing away",
    "serious": "serious focused expression",
    "tired": "tired, heavy eyelids, faint fatigue",
    "cry": "crying quietly, tears on the cheeks",
}

CHARS = [
    ("rin", "사에키 린", "27세 · 카페&바 사장",
     "27-year-old Japanese woman, short black bob with sharp ends, narrow sharp dark grey eyes, slim build, white button-up shirt with sleeves rolled to the elbows, dark charcoal apron, small faint burn scar on the back of her left hand, a thin silver ear cuff, cool dry demeanor"),
    ("yui", "츠키시마 유이", "24세 · 일러스트레이터",
     "24-year-old Japanese woman, shoulder-length slightly messy light brown hair, soft drowsy eyes, round thin-frame glasses, oversized lavender-grey hoodie with sleeves covering her hands, deep indigo ink stains on her fingertips, slightly hunched shy posture"),
    ("shiori", "카미야 시오리", "30세 · 디벨로퍼 PM",
     "30-year-old Japanese woman, long straight black hair in a low ponytail, calm intelligent dark eyes, slender build, navy tailored business suit with a white blouse, small men's wristwatch with a large second hand on her left wrist, upright composed posture"),
    ("noa", "하야세 노아", "22세 · 사진학과 4학년",
     "22-year-old Japanese woman, orange-tinted brown hair in a short shoulder-length bob, bright big eyes, slim energetic build, denim jacket over a white t-shirt, a worn black-and-brass vintage film SLR camera hanging from a neck strap, open cheerful posture"),
    ("kondo", "곤도 겐조", "74세 · 관리인",
     "74-year-old Japanese man, short grey hair, kind wrinkled face, small round glasses, beige work jacket over a cardigan, slightly bent posture"),
    ("maki", "마키 요코", "58세 · 대학 교수",
     "58-year-old Japanese woman, short silver-streaked hair, sharp intelligent eyes, bold geometric glasses, black turtleneck under a long grey coat, confident posture"),
    ("okabe", "오카베 신지", "42세 · 전 직장 상사",
     "42-year-old Japanese man, neatly combed black hair, tired but sharp eyes, dark grey suit without a tie, an ID card on a lanyard, professional posture"),
]

PART_FILES = [("common_a.md", "공통 · 프롤로그~1장"), ("common_b.md", "공통 · 2~3장"), ("rin.md", "린 루트"),
              ("yui.md", "유이 루트"), ("shiori.md", "시오리 루트"), ("noa.md", "노아 루트"), ("hidden.md", "히든 에필로그")]

STRIP = re.compile(r"^anime style visual novel (?:event CG|background),\s*16:9,\s*(?:no people,\s*)?", re.I)


def parse_md(path):
    cgs, bgs = {}, {}
    lines = open(path, encoding="utf-8").read().splitlines()
    for i, ln in enumerate(lines):
        m = re.match(r"^- \*\*([a-z0-9_]+)\*\* — (.*)$", ln)
        if not m:
            continue
        cid, rest = m.group(1), m.group(2)
        pm = re.search(r"`([^`]*anime style[^`]*)`\s*$", rest)
        if pm:
            desc = rest[: pm.start()].rstrip(" —")
            cgs[cid] = (desc, pm.group(1))
        else:
            # 배경: 다음 줄에 프롬프트
            desc = re.sub(r"\s*권장 색:.*$", "", rest)
            for j in range(i + 1, min(i + 4, len(lines))):
                pm2 = re.search(r"프롬프트:\s*`([^`]*)`", lines[j])
                if pm2:
                    bgs[cid] = (desc, pm2.group(1))
                    break
    return cgs, bgs


def clean(p):
    p = STRIP.sub("", p.strip())
    p = re.sub(r",?\s*no text\s*$", "", p)
    return p[0].upper() + p[1:] if p else p


def main():
    txt = open(os.path.join(ROOT, "game", "js", "scenario.js"), encoding="utf-8").read()
    data = json.loads(txt[txt.index("=") + 1:].rstrip().rstrip(";"))
    used = data["assets"]
    meta = data["meta"]

    part_cg, part_bg, cg_part = {}, {}, {}
    for fn, label in PART_FILES:
        c, b = parse_md(os.path.join(A, fn))
        for k, v in c.items():
            part_cg[k] = v
            cg_part[k] = label
        part_bg.update(b)

    batches = []
    items = []

    # 1) 캐릭터 — 캐릭터당 배치 1개 (기본 표정 → 같은 그림에서 표정만 변경)
    used_sprites = {}
    for sp in used["sprite"]:
        ch, ex = sp.split("_", 1)
        used_sprites.setdefault(ch, set()).add(ex)
    for cid, name, sub, look in CHARS:
        exs = ["normal"] + [e for e in meta["expressions"] if e != "normal" and e in used_sprites.get(cid, set())]
        hero = cid in ("rin", "yui", "shiori", "noa")
        lines = [f"[블루 아워 · 캐릭터 배치 — {name} ({sub}) · {len(exs)}장]",
                 f"아래 {len(exs)}장을 번호 순서대로 끝까지 연속 생성해 줘. 각 이미지 위에 파일명을 적어 줘.",
                 "", f"공통: 앞에서 정한 그림체 / {PORT}", "",
                 f"CHARACTER: {look}.", ""]
        its = []
        for n, ex in enumerate(exs, 1):
            fn = f"{cid}_{ex}.png"
            if ex == "normal":
                pr = f"{look}. Expression: {EXPR[ex]}. This is the base sprite; keep this exact design for all following images."
            else:
                pr = f"Same character as image 1 with the identical outfit, hairstyle, pose, framing and scale. Change ONLY the facial expression to: {EXPR[ex]}."
            lines += [f"{n}) {fn}", pr, ""]
            its.append({"file": fn, "folder": "game/assets/ch/", "ko": f"{name} — {ex}", "prompt": pr,
                        "prio": 1 if (hero and ex == "normal") else 2 if hero else 3})
        batches.append({"id": f"ch_{cid}", "group": "캐릭터", "title": f"{name}", "sub": f"{sub} · 스탠딩 {len(exs)}장",
                        "text": "\n".join(lines).strip(), "items": its})
        items += its

    # 2) 배경 — 6장씩
    bg_list = []
    for b in used["bg"]:
        if b in SKIP_BG:
            continue
        desc_ko = meta["bgs"].get(b, {}).get("desc", "")
        if b in BG:
            pr = BG[b]
        elif b in part_bg:
            pr = clean(part_bg[b][1])
        else:
            pr = desc_ko
        core = {"ext_aono_day", "ext_aono_dusk", "rooftop_dusk", "room601_day", "room601_dusk", "room601_night",
                "cafe_day", "cafe_night", "stairwell", "canal_day", "rooftop_night", "yui_room", "office_minato"}
        bg_list.append({"file": f"{b}.png", "folder": "game/assets/bg/", "ko": desc_ko,
                        "prompt": pr + " No people.", "prio": 1 if b in core else 2})
    bg_list.sort(key=lambda x: (x["prio"], x["file"]))
    for k in range(0, len(bg_list), 6):
        chunk = bg_list[k:k + 6]
        n0 = k // 6 + 1
        lines = [f"[블루 아워 · 배경 배치 {n0:02d} · {len(chunk)}장]",
                 f"아래 {len(chunk)}장을 번호 순서대로 끝까지 연속 생성해 줘. 각 이미지 위에 파일명을 적어 줘.",
                 "", f"공통: 앞에서 정한 그림체 / {LAND} / 배경 전용 — 사람 없음, 글자 없음.", ""]
        for n, it in enumerate(chunk, 1):
            lines += [f"{n}) {it['file']}", it["prompt"], ""]
        batches.append({"id": f"bg_{n0:02d}", "group": "배경", "title": f"배경 {n0:02d}",
                        "sub": ("핵심 배경 · " if chunk[0]["prio"] == 1 else "") + f"{len(chunk)}장",
                        "text": "\n".join(lines).strip(), "items": chunk})
        items += chunk

    # 3) 이벤트 CG — 파트별, 최대 6장
    by_part = {}
    for c in used["cg"]:
        if c not in part_cg:
            continue
        by_part.setdefault(cg_part[c], []).append(c)
    for fn_, label in PART_FILES:
        ids = by_part.get(label, [])
        for k in range(0, len(ids), 6):
            chunk = ids[k:k + 6]
            its = []
            lines = [f"[블루 아워 · 이벤트 CG 배치 — {label}{' ' + str(k // 6 + 1) if len(ids) > 6 else ''} · {len(chunk)}장]",
                     f"아래 {len(chunk)}장을 번호 순서대로 끝까지 연속 생성해 줘. 각 이미지 위에 파일명을 적어 줘.",
                     "", f"공통: 앞에서 정한 그림체 / {LAND} / 등장인물은 모두 성인 / 글자 없음.",
                     "주인공은 27세 여성 건축가(어깨에 닿는 짙은 갈색 머리를 목덜미에서 느슨하게 묶음, 키가 큰 편, 흰 셔츠나 회색 카디건). 얼굴은 거의 보이지 않게(뒷모습·화면 가장자리·손만).", ""]
            for n, c in enumerate(chunk, 1):
                desc, pr = part_cg[c]
                p = clean(pr)
                it = {"file": f"{c}.png", "folder": "game/assets/cg/", "ko": re.sub(r"\s+", " ", desc)[:140],
                      "prompt": p, "prio": 2}
                its.append(it)
                lines += [f"{n}) {it['file']}", p, ""]
            batches.append({"id": f"cg_{fn_[:-3]}_{k // 6 + 1}", "group": "이벤트 CG",
                            "title": label + (f" {k // 6 + 1}" if len(ids) > 6 else ""), "sub": f"{len(chunk)}장",
                            "text": "\n".join(lines).strip(), "items": its})
            items += its

    received = sorted(os.path.basename(f) for f in __import__("glob").glob(os.path.join(ROOT, "game", "assets", "*", "*.*")))
    out = {"received": received, "style": STYLE, "start": START_MSG, "zip": ZIP_MSG, "batches": batches,
           "counts": {"total": len(items), "ch": sum(1 for i in items if "/ch/" in i["folder"]),
                      "bg": sum(1 for i in items if "/bg/" in i["folder"]),
                      "cg": sum(1 for i in items if "/cg/" in i["folder"])}}
    path = os.path.join(A, "image_kit.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    tpl = open(os.path.join(ROOT, "tools", "image_kit_template.html"), encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(out, ensure_ascii=False).replace("</", "<\\/"))
    with open(os.path.join(ROOT, "docs", "image_kit.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("배치", len(batches), "개 / 이미지", out["counts"], "→ docs/image_kit.html")
    missing = [c for c in used["cg"] if c not in part_cg]
    if missing:
        print("프롬프트 없는 CG:", missing)


if __name__ == "__main__":
    main()
