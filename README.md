# 블루 아워 (青の時間)

도쿄 기요스미시라카와, 1년 뒤 철거될 1968년의 모더니즘 맨션 「아오노 하우스」.
번아웃으로 회사를 그만둔 스물일곱 살 건축가가 그 건물을 기록하며 보내는 1년.

- 장르: 현대 순애 비주얼 노벨 (성인 대상, 노골적이지 않음, 설정에서 성인 장면 끄기 가능)
- 분량: 본문 약 17만 자 (전체 약 6시간, 한 번 플레이 약 1시간 40분~2시간) / 히로인 4명 / 엔딩 15개 (히든 엔딩 포함)
- 플랫폼: 웹 브라우저 (PC·모바일)

## 실행

`game/index.html` 을 웹 서버로 열면 됩니다. GitHub Pages 를 켜면 저장소 루트의 `index.html` 이 게임으로 이동합니다.

```bash
cd game && python3 -m http.server 8000
```

브라우저에서 `http://localhost:8000` 을 엽니다. 파일을 직접 더블클릭해서 열어도 대부분 동작합니다.

## 조작

| 동작 | PC | 모바일 |
|---|---|---|
| 다음 | 클릭 / Enter / Space / 휠 아래 | 탭 |
| 로그 | 휠 위 / ↑ | 하단 「로그」 |
| 스킵 | Ctrl 누르고 있기 / 「스킵」 | 「스킵」 |
| 자동 | A / 「자동」 | 「자동」 |
| 저장·불러오기 | S / L | 하단 메뉴 |
| UI 숨기기 | 우클릭 / H | — |
| 설정 | Esc | 「설정」 |

## 이미지·음악 교체

지금은 모든 그림이 **자리표시자**(색 그라데이션과 캐릭터 실루엣)로 나옵니다.
정해진 파일명으로 이미지를 넣으면 코드 수정 없이 자동으로 바뀝니다.

| 종류 | 폴더 | 파일명 |
|---|---|---|
| 배경 | `game/assets/bg/` | `<배경ID>.png` (jpg/webp 가능) |
| 캐릭터 | `game/assets/ch/` | `<캐릭터ID>_<표정>.png` — `_normal` 하나만 있어도 됨 |
| 이벤트 CG | `game/assets/cg/` | `<CG_ID>.png` |
| 배경음악 | `game/assets/bgm/` | `<ID>.mp3` (main, daily, cafe, night, sad, tension, romance, festival, ending, rain) |
| 효과음 | `game/assets/se/` | `<ID>.mp3` |

이미지 생성용 프롬프트는 `docs/assets/` 에 있습니다.
- `ASSET_LIST.md`: 필요한 모든 이미지 ID 목록 (빌드 시 자동 생성)
- `characters.md`: 캐릭터 스탠딩
- `common_*.md`, `rin.md`, `yui.md`, `shiori.md`, `noa.md`, `hidden.md`: 이벤트 CG와 추가 배경

## 시나리오 수정

- 시나리오: `story/*.txt` (형식은 `docs/SCRIPT_FORMAT.md`)
- 설정: `docs/STORY_BIBLE.md`
- 수정 후 빌드:

```bash
python3 tools/build.py
```

빌드하면 `game/js/scenario.js` 와 `docs/assets/ASSET_LIST.md` 가 갱신됩니다.

분기 검사(무작위 플레이 3만 회로 모든 엔딩 도달·막힌 경로 확인):

```bash
python3 tools/simulate.py
```
