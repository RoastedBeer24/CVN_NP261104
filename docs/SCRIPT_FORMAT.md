# 시나리오 스크립트 형식

시나리오는 `story/*.txt` 에 씁니다. 파일들은 **이름순으로 이어 붙여** 하나의 명령 목록이 됩니다.
그래서 파일 끝은 반드시 `@jump`, `@route`, `@ending`, `@title` 중 하나로 끝내야 합니다.
(그렇지 않으면 다음 파일 내용으로 그냥 흘러 들어갑니다.)

작성 후 검증: `python3 tools/build.py --check` / 빌드: `python3 tools/build.py`

## 기본 줄

| 형식 | 의미 |
|---|---|
| `# 메모` | 주석 (무시됨) |
| `*label_name` | 라벨 (영문·숫자·_ 만) |
| `텍스트` | 나레이션 (주인공 1인칭 독백 포함) |
| `린: 텍스트` | 대사. 화자 이름 + 콜론 |
| `린(smile): 텍스트` | 대사 + 그 캐릭터가 화면에 있으면 표정 변경 |
| `나: 텍스트` | 주인공 대사. 이름 칸에 플레이어가 정한 이름이 표시됨 |
| `점원: 텍스트` | 등록되지 않은 단역도 OK (이름만 표시, 스프라이트 없음) |

- 화자 이름에는 **공백 불가** (`역무원A` 처럼 붙여 쓰기). 12자 이내.
- 나레이션을 `단어: ...` 형태로 시작하지 말 것 (대사로 오인됨).
- 본문에서 `{name}` = 주인공 이름(기본 하루카), `{family}` = 주인공 성(기본 세오).
- 대사 본문에 따옴표는 쓰지 않습니다. 엔진이 이름 칸으로 구분합니다.
- 한 줄 = 한 번의 클릭. 모바일 화면을 생각해 **한 줄은 대략 80자 이내**, 길면 나눕니다.

등록 캐릭터(화자 이름 → ID): 린→rin, 유이→yui, 시오리→shiori, 노아→noa, 곤도→kondo, 마키→maki, 오카베→okabe

## 연출 명령

| 명령 | 설명 |
|---|---|
| `@chapter 제1장 실측` | 장 제목 카드 (세이브 화면에도 표시) |
| `@time 4월 3일 (토) 오후` | 화면 좌상단 시간 캡션 |
| `@bg 배경ID` / `@bg 배경ID cut` | 배경 변경 (기본 페이드, cut=즉시). 배경을 바꾸면 캐릭터는 자동으로 모두 퇴장 |
| `@show rin smile left` | 캐릭터 등장. 위치: left, left2, center, right2, right (생략 시 center) |
| `@hide rin` / `@hide all` | 캐릭터 퇴장 |
| `@cg 이벤트CG_ID` / `@cgoff` | 이벤트 CG 표시/해제 (본 CG는 갤러리에 등록) |
| `@bgm ID` / `@bgm stop` | 배경음악. ID: main, daily, cafe, night, sad, tension, romance, festival, ending, rain |
| `@se ID` | 효과음 (예: door, rain, phone, camera, train, fireworks, knock) |
| `@wait 1.5` | 초 단위 대기 |
| `@effect shake` | 효과: shake, flash, dark(암전), light(암전 해제), blur, unblur |
| `@msg on` / `@msg off` | 메시지(LINE) 모드. 켜면 대사가 휴대폰 메시지 말풍선처럼 표시됨 |

표정: normal, smile, laugh, sad, angry, surprised, shy, serious, tired, cry

## 변수와 분기

| 명령 | 설명 |
|---|---|
| `@set rin+1` | 변수 증가 (여러 개: `@set rin+1, yui-1, flag_x`) |
| `@set flag_x` | 플래그 = 1 |
| `@set rp=0` | 대입 |
| `@if rin>=5 && flag_x -> label` | 조건이 참이면 점프. 연산자: `>= <= > < == != && || !` 와 괄호 |
| `@jump label` | 무조건 점프 |
| `@route min=6 rin=rin_start yui=yui_start shiori=shiori_start noa=noa_start else=alone_start` | 호감도가 가장 높은(그리고 min 이상인) 히로인 루트로. 동점이면 적힌 순서 우선 |
| `@ending rin_true` | 엔딩 카드 표시 후 타이틀로. ID는 meta.json 의 엔딩 목록 |
| `@title` | 타이틀로 돌아감 |

정의되지 않은 변수는 0 으로 취급합니다.

### 선택지

```
@choice
- 커피를 주문한다 -> cafe_order {rin+1}
- [noa>=3] 노아에게 연락한다 -> call_noa {noa+2, called_noa}
- 그냥 지나친다
```

- `- 텍스트 -> 라벨 {변수식}` — 라벨과 `{}` 는 생략 가능.
- 라벨을 생략하면 선택 후 **선택지 블록 바로 다음 줄**로 진행 (분위기용 선택지).
- `[조건]` 을 앞에 붙이면 조건이 참일 때만 보임.
- 선택지 블록은 `-` 로 시작하는 줄이 끝나는 곳에서 끝납니다.

### 성인 장면

```
@adult
...노골적이지 않은 장면 (암전 처리, 감정 위주)...
@adultend
```

설정에서 성인 장면을 끄면 `@adult` ~ `@adultend` 사이를 통째로 건너뜁니다.
그러므로 블록 앞뒤 문장만으로도 이야기가 자연스럽게 이어지도록 씁니다.

## 패턴 예시

```
*ch1_cafe
@bg cafe_day
@bgm cafe
@show rin normal center
린: 주문.
나: …아메리카노.
린(smile): 여긴 그런 메뉴 없어.
@choice
- 추천을 부탁한다 {rin+1}
- 메뉴판을 다시 본다
린: 에티오피아로 줄게.
@hide rin
@jump ch1_next
```
