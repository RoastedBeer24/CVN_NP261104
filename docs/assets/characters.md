# 캐릭터 스탠딩 이미지 프롬프트

## 파일 규칙
- 위치: `game/assets/ch/`
- 파일명: `<캐릭터ID>_<표정>.png` (예: `rin_smile.png`). webp/jpg 도 가능.
- **`<ID>_normal.png` 하나만 있어도 됩니다.** 다른 표정 파일이 없으면 normal 로 대체됩니다.
- 권장: 배경 투명 PNG, 세로 1024×2048 전후, 무릎 위~머리 위까지(또는 전신), 발끝/아래쪽이 이미지 하단에 닿게.
- 같은 캐릭터의 모든 표정은 **같은 구도·크기·위치**로 뽑아야 표정 전환이 자연스럽습니다.
  GPT에서 normal 을 먼저 만들고, 그 이미지를 첨부해 "같은 그림에서 표정만 ○○로 바꿔줘"라고 요청하는 방식을 추천.

표정 ID: normal(기본), smile(미소), laugh(웃음), sad(슬픔), angry(화남), surprised(놀람), shy(부끄러움), serious(진지), tired(지침), cry(울음)

## 공통 스타일 문구 (모든 프롬프트 앞에 붙이기)
```
Japanese visual novel character standing sprite, modern anime illustration, soft cel shading,
clean lineart, muted sophisticated color palette, full transparent background, waist-up to knees,
facing slightly toward viewer, consistent proportions, adult character,
```

## 사에키 린 (rin) — 27세, 카페&바 사장
```
27-year-old Japanese woman, short black bob haircut with sharp ends, narrow sharp eyes, dark grey eyes,
slim build, white button-up shirt with sleeves rolled to elbows, dark charcoal apron,
small faint burn scar on back of left hand, cool and dry expression, minimal silver ear cuff
```
- 표정 예: normal=무표정에 가까운 담담함 / smile=입꼬리만 살짝 / laugh=고개 살짝 숙여 웃음 / shy=시선 회피, 귀 붉어짐

## 츠키시마 유이 (yui) — 24세, 일러스트레이터
```
24-year-old Japanese woman, shoulder-length slightly messy light brown hair, soft drowsy eyes,
round thin-frame glasses, oversized lavender-grey hoodie with sleeves covering hands,
ink stains on fingertips, slightly hunched shy posture, gentle quiet expression
```
- 안경 없는 버전이 필요하면 `yui_normal` 등과 별도로 만들지 말고 안경 쓴 상태로 통일 권장.

## 카미야 시오리 (shiori) — 30세, 디벨로퍼 PM
```
30-year-old Japanese woman, long straight black hair in a low ponytail, elegant composed face,
calm dark eyes, navy tailored business suit, white blouse, thin wristwatch,
upright confident posture, professional and slightly cold expression
```
- 사복 버전이 필요하면 추후 `shiori_casual_*` 처럼 추가 가능(엔진 확장 필요 시 요청).

## 하야세 노아 (noa) — 22세, 사진학과 4학년
```
22-year-old Japanese woman, orange-tinted brown hair in a short shoulder-length cut, bright big eyes,
denim jacket over white t-shirt, vintage film camera hanging from neck strap,
energetic open posture, cheerful wide smile
```

## 곤도 겐조 (kondo) — 74세, 관리인
```
74-year-old Japanese man, short grey hair, kind wrinkled face, small round glasses,
beige work jacket over cardigan, slightly bent posture, gentle smile
```

## 마키 요코 (maki) — 58세, 대학 교수
```
58-year-old Japanese woman, short silver-streaked hair, sharp intelligent eyes, black turtleneck,
long grey coat, bold geometric glasses, confident expression
```

## 오카베 신지 (okabe) — 42세, 전 직장 상사
```
42-year-old Japanese man, neatly combed black hair, tired but sharp eyes, dark grey suit, no tie,
lanyard ID card, professional smile
```
