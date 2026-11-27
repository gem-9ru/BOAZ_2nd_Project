# Ad assistant 디자인 시스템 (색)

Ad assistant의 색은 **`design-system/tokens.json` 한 곳**에만 적어요.
값을 바꾸고 아래 한 줄을 돌리면 분석 페이지와 확장 프로그램에 같이 반영돼요.

```bash
node design-system/build.cjs
```

| 명령 | 하는 일 |
|---|---|
| `node design-system/build.cjs` | 원천에서 CSS 3개를 새로 쓰고, 대비를 검사해요 |
| `node design-system/build.cjs --check` | 파일이 원천과 같은지만 봐요 (다르면 실패). 확장 테스트 `tests/tokens.test.ts`도 이걸 돌려요 |
| `node design-system/build.cjs --contrast` | 아래 대비 표를 다시 찍어요 |
| `node design-system/scripts/validate-tokens.cjs --dir <폴더>` | 화면 코드에 색·px이 하드코딩됐는지 찾아요 |

`scripts/`의 두 파일은 `/design-system` 스킬(claudekit, MIT)의 `generate-tokens.cjs`·`validate-tokens.cjs`를 그대로 복사한 거예요. 저장소만 받아도 돌아가게 하려고 넣었어요. 고치지 마세요.

## 구조: 3층

```
primitive (원시값, 예: violet.600 = #5B3FD9)
   ↓
semantic  (의미, 예: tone.accent = 메인)        ← 화면은 여기부터 써요
   ↓
component (부품, 예: button.bg, coach.ring)
```

형식은 W3C Design Tokens(`$value`·`$type`·`$description`)이고, 참조는 `{semantic.tone.accent}`처럼 써요.
**화면 코드는 원시값(hex)을 직접 쓰지 않아요.** 새 색이 필요하면 primitive에 넣고 semantic 이름을 붙여요.

## 만들어지는 파일

| 파일 | 누가 읽나 | 변수 이름 |
|---|---|---|
| `web/src/tokens.css` | 분석 페이지. `web/src/styles.css`의 `@theme inline`이 Tailwind 색으로 연결 | `--primitive-*`, `--tone-*`, `--card-*`·`--button-*` 등 |
| `extension/assets/tokens.css` | 확장 사이드 패널. `extension/assets/tailwind.css`가 `@import` | `@theme`: `--color-*`(바탕·글자·메인·뭉치 배·알림 4색과 연한 바탕·`reference`·판정·`on-accent`), `--font-sans`, `--text-*`, `--radius-*`, `--container-*`, `--shadow-raised/float/card/press/hero/press-sm/cta/selected`, `--radius-soft/bubble/sheet`, `--text-headline` · `:root`: `--state-disabled-opacity`, `--focus-width/offset`, `--motion-*`, `--character-*`, `--panel-*`(사이드 패널 머리·진행 막대) |
| `extension/assets/overlay-tokens.css` | 광고 관리자 위 오버레이(shadow root). `overlay.css`가 `@import`, `Character.tsx`가 `var()`로 씀 | `--coach-*`, `--character-*` |

세 파일 모두 머리에 "자동 생성" 주석이 있어요. 직접 고치면 다음 빌드에서 덮어써요.
확장 이름(`--color-*`)과 의미 토큰의 짝은 `build.cjs`의 `EXTENSION_COLORS`에 있어요.

## 색 외 토큰

| 이름 | 값 | 쓰는 곳 |
|---|---|---|
| `semantic.text.family` | Pretendard → Noto Sans KR → system-ui | 두 앱·오버레이 공통 글꼴 |
| `primitive.font.size.*` | mark 10 · small 12 · caption 13 · label 14 · body 16 · lead 17 · title 20 · headline 24 · number 28 · hero-sm 30 · hero 40 | 꾸미기안_뭉치 2026-11-26: 페이지 제목(`.h1`)은 `hero-sm` 30(예전 32), 결론 카드 제목·큰 숫자는 `headline` 24. 꾸미기안의 11.5·12.5·13.5·15.5px은 가장 가까운 단계로 써요(본문은 16 아래로 안 내려요) | 두 앱 모두 `text-caption`처럼 Tailwind 이름으로 써요. `text-[13px]`처럼 숫자를 직접 쓰지 않아요. `mark`는 알림·체크 모양 안 기호에만 써요 |
| `semantic.text.line-height` | 1.5 | 본문 줄 간격 |
| `semantic.motion.hover / expand / move / walk` | 150 / 250 / 350 / 500ms | 색 바뀜 / 펼치기 / 테두리 이동 / 캐릭터 걸음. 모두 `prefers-reduced-motion`이면 끔 |
| `semantic.state.disabled-opacity` | 0.4 | 작은 버튼·칸이 못 누를 때: `disabled:opacity-(--state-disabled-opacity)` + `disabled` 속성 |
| `tone.disabled-bg / disabled-line / disabled-fg` | `#EEECF3` / `#D6D0E6` / `#5E5880` | **큰 주 버튼**이 못 누를 때는 투명도 대신 회보라 상자로 보여요 (꾸미기안_뭉치 2026-11-26 `.cta-off` '분석 시작 ▶'). 옆에 '파일을 올리면 눌러져요'처럼 이유를 같이 써요. 글자 5.6:1 |
| `component.focus.width / offset` | 2px / 2px | 초점 링 (`outline-2 outline-offset-2 outline-accent`) |
| `component.button/card/badge/alert-mark.radius` | 16 / 22 / 9999 / 2px | 모서리. 두 앱 모두 `rounded-button` · `rounded-card` · `rounded-badge` · `rounded-mark`(■ 차단 모양)로 써요. `rounded-xl`처럼 Tailwind 기본 이름을 쓰지 않아요. 모서리 단계 (꾸미기안_뭉치 2026-11-26: '둥글고 말랑하게'): md 12 · soft 14(`rounded-soft`: 알림 상자·테두리 버튼) · lg 16(버튼) · bubble 18(`rounded-bubble`: 말풍선) · xl 22(카드) · 2xl 26(`rounded-sheet`: 파일 올리는 칸·패널 머리). 오버레이 말풍선은 `--coach-radius` 18, 말풍선 버튼은 `--coach-button-radius` 12 |
| `semantic.state.disabled-opacity` (잠긴 단계) | 0.4 | 아직 못 가는 단계 표시도 `text-soft opacity-(--state-disabled-opacity)`로 (`text-soft/50` 금지) |
| `semantic.layout.page / page-wide / measure` | 960px / 1040px / 60ch | 화면 너비. 두 앱 모두 `max-w-page` · `max-w-page-wide` · `max-w-measure`로 써요. `max-w-[960px]`처럼 숫자를 직접 쓰지 않아요. 말풍선 `max-w-[85%]`처럼 부모 대비 비율은 그대로 둬요 |
| `semantic.elevation.*` | raised · card · float · hero · selected · press · press-sm · cta · bubble · mascot | 꾸미기안_뭉치 2026-11-26에서 card·hero·selected·press·press-sm·cta·bubble·mascot을 더했어요. 높이: `shadow-raised` < `shadow-card` < `shadow-float` < `shadow-hero`. `shadow-selected`는 사이드 패널의 지금 칸. 눌림: `shadow-press`(말풍선 '다 했어요'), `shadow-press-sm`(선택된 단계 탭·칩), `shadow-cta`(큰 주 버튼, 눌림 + 보라 번짐). `elevation.bubble`은 광고 관리자 위 흰 말풍선 전용 검은 그림자, `elevation.mascot`은 뭉치 그림 `filter: drop-shadow`. `shadow-raised`는 스크롤 중 위에 붙는 칸(sticky), `shadow-card`는 보통 카드(살짝 뜸), `shadow-float`는 토스트·말풍선, `shadow-hero`는 결론 카드처럼 화면의 주인공 한 개. `shadow-press`(`0 4px 0` 진한 보라)는 높이가 아니라 주 버튼 아래 '눌리는 느낌' 그림자로, 주 버튼과 선택된 칩에만 써요. `shadow-sm`·`shadow-lg` 같은 Tailwind 기본 이름은 쓰지 않아요. 그림자 색은 회색 대신 `ink`·`accent-ink` 계열을 투명하게 써요 (예외: 메타 화면 위 말풍선 `bubble`은 꾸미기안대로 검정) |
| `component.ghost.*` | `surface` / `accent` / `accent` / 14 / 44px | 테두리 보조 버튼 ('왜 그런지 보기 ▶', '◀ 결론') (꾸미기안_뭉치 2026-11-26 `.ghost`) |
| `component.button.height / shadow` | 52px / `cta` | 큰 주 버튼 (꾸미기안_뭉치 2026-11-26 `.big` 52, 확장 `.cta` 50) |
| `component.meter.*` | track `sunk` · `#8D78F2`→메인 · 눈금 `belly-strong` | 예산 가능성 막대 (꾸미기안_뭉치 2026-11-26 `.meter`) |
| `component.drop.*` | 점선 `accent-line` · 26 | 파일 올리는 칸 (꾸미기안_뭉치 2026-11-26 `.drop`) |
| `component.field.border / bg / radius` | `field-line` / `surface` / 12px | 입력칸·선택칸: `rounded-button border border-field-line bg-surface`(확장은 `bg-paper`) |

## 색 표

아래 값은 꾸미기안_뭉치 2026-11-26 기준이에요 (뭉치 몸 색에서 가져옴: 보라 몸통 = 메인, 베이지 배 = 포인트, 아주 옅은 크림 = 바탕).

### 메인 (바이올렛)

| 이름 (semantic) | 값 | 쓰는 곳 | 대비 |
|---|---|---|---|
| `tone.accent` · 확장 `accent` | `#5B3FD9` | 현재 단계, 로고, 초점 링, 칸 테두리, 주 버튼(`tone.action`), 캐릭터 몸 | 흰 바탕 6.5:1 |
| `tone.accent-ink` · 확장 `accent-ink` | `#4528B0` | 메인 글자·링크, 버튼 눌림(`tone.action-hover`), 차트의 보통 값 점 ('확실해요' 배지는 이제 메인 `#5B3FD9` 채움) | 흰 바탕 9.5:1 |
| `tone.accent-soft` · 확장 `accent-soft` | `#EFEBFF` | 연한 바탕: 어시스턴트 패널, 선택 행, 단계 칩, 번호 동그라미, 페이지 오른쪽 위 번짐 | (바탕색) |
| `tone.accent-faint` · 확장 `accent-faint` | `#F7F4FF` | 아주 옅은 보라: 칸 경로 알약, 새 세트 카드 바탕, 열린 접기 칸 | (바탕색) |
| `tone.accent-line` · 확장 `accent-line` | `#B3A5F0` | 메인 계열 옅은 테두리 (장식) | — |

### 바탕·글자

| 이름 | 값 | 쓰는 곳 | 대비 |
|---|---|---|---|
| `tone.ink` · 확장 `ink` | `#2A1F5C` | 본문, 숫자 (보라 기운 남색) | 14.5:1 |
| `tone.ink-soft` · 확장 `soft` | `#6B6590` | 보조 글자 | 카드 5.4:1 · 눌린 칸 4.8:1 |
| `tone.bg` · 확장 `cream` | `#FFFAF2` | 페이지 바탕 (아주 옅은 크림) | — |
| `tone.surface` · 확장 `paper` | `#FFFFFF` | 카드 바탕, 주 버튼 글자 | — |
| `tone.surface-sunk` · 확장 `sunk` | `#F3F0FB` | 막대 빈 부분, 눌린 칸, 단계 탭 바탕, 말풍선 보조 버튼 바탕 | — |
| `tone.line` · 확장 `line` | `#E8E2F4` | 구분선·카드 테두리 (장식). **입력칸 테두리에는 쓰지 않아요** | 1.3:1 (장식이라 기준 없음) |
| `tone.field-line` · 확장 `field-line` | `#767E8C` | 입력칸·선택칸 테두리. 칸이 어디 있는지 보여야 해서 3:1 이상이 필요해요 (WCAG 1.4.11) | 카드 4.1:1 · 바탕 3.9:1 · 눌린 칸 3.6:1 |
| `tone.hold` / `hold-bg` | `#5E5880` / `#EEECF3` | '아직 몰라요' 배지 (회보라, 꾸미기안_뭉치 2026-11-26 `.t-dk`. 예전 회색 `#5F6672`/`#F1F1EF`). **'아직 몰라요'·못 누르는 버튼 말고는 이 색을 쓰지 않아요** (`field-line`은 테두리 전용) | 5.6:1 |
| `tone.series-a` | `#8A92A0` | 차트의 나머지 쪽 (회색, 값 글자 없는 차트) | 3.1:1 (모양) |
| `tone.series-soft` · 확장 `series-soft` | `#D9D2F2` | 막대 위에 값 글자가 붙는 작은 막대의 나머지 쪽 (꾸미기안_뭉치 2026-11-26 `.spark`) | 1.5:1 → **값 글자를 꼭 같이** 써요 |
| `tone.glow-warm` · 확장 `glow-warm` | `#FBEBD6` | 페이지 바탕 왼쪽 아래 따뜻한 번짐 (장식, 꾸미기안_뭉치 2026-11-26 `.scr::after`). 오른쪽 위 번짐은 `accent-soft` | — |
| `tone.series-b` | `#5B3FD9` | 차트의 추천 쪽 (메인) | 6.5:1 (모양) |
| `tone.on-meta` | `#FFFFFF` | 메타 흰 화면 위 버튼 바탕, 알림 모양 안 기호 | — |

### 뭉치 배 (장식 전용)

꾸미기안_뭉치 2026-11-26에서 더했어요. 뭉치의 베이지 배 색이에요. **장식 전용이라 상태 표시(알림·판정·정상/오류)에는 쓰지 않아요.** 부리·발의 빨강은 차단 빨강과 겹쳐서 화면에 쓰지 않아요.

| 이름 | 값 | 쓰는 곳 | 대비 |
|---|---|---|---|
| `tone.belly` · 확장 `belly` | `#F6E4CB` | 강조 밑줄(형광펜), 테스트 제안 태그 바탕, 뭉치 얼굴 동그라미 바탕 | (바탕색) |
| `tone.belly-strong` · 확장 `belly-strong` | `#D2AD81` | 진행 막대 끝 점(흰 테두리 3px), 차트 기준선 같은 장식 선 | 흰 바탕 2.1:1 → 글자·필수 모양에 쓰지 않아요 |
| `tone.belly-ink` · 확장 `belly-ink` | `#7A5320` | `belly` 위 글자 (테스트 제안 태그) | 5.5:1 |

### 알림 4색 (고정)

| 단계 | 모양 색 | 글자 색 | 연한 바탕 | 쓰는 곳 |
|---|---|---|---|---|
| ■✕ 차단 | `block` `#D93025` | 흰 바탕 위: `block` (4.7:1) · 연한 바탕 위: **`block-ink` `#B3261E`** (5.6:1) | `block-bg` `#FCE8E6` · 테두리 `block-line` `#F6AEA9` | 게시하면 안 되는 문제 |
| ▲! 주의 | `warn-mark` `#E8710A` | `warn` `#7A3D06` (7.6:1) | `warn-bg` `#FFF1E3` · 테두리 `warn-line` `#F7C99B` | 고치면 좋은 문제 |
| ●i 참고 | `info` `#1A73E8` | `info-ink` `#123B73` (9.8:1) | `info-bg` `#EAF2FE` · 테두리 `info-line` `#BCD5FA` | 알아 두면 좋은 정보 |
| ● 참고만 배지 | `reference` `#1A73E8` (= 참고 파랑) | 흰 글자 `on-accent` (4.5:1) | — | 보여진 횟수 100 미만 칸 (ALT-22) |
| ✓ 정상 | `ok` `#1E8E3E` | `ok-ink` `#1B5E2C` (7.0:1) | `ok-bg` `#E9F6EC` · 테두리 `ok-line` `#A9D9B5` | 문제 없음, '✓ 그대로' 태그 |

알림 원색 네 개는 **모양(■▲●✓)에만** 써요. 연한 바탕 위 글자로 쓰면 4.5:1이 안 나와요.
상자 글자는 같은 색 계열의 진한 글자(`warn`, `block-ink`, `info-ink`, `ok-ink`)를 쓰고, 상자에는 1.5px 테두리(`*-line`, 장식)와 모서리 `rounded-soft` 14를 줘요 (꾸미기안_뭉치 2026-11-26 `.alert`, `.note`). 차단 상자 테두리 `block-line` `#F6AEA9`는 꾸미기안에 없어서, 2026-11-27 사용자 요청('연하게')에 따라 다른 세 테두리와 같은 옅기(각 색의 200 단계)로 정했어요.
▲ 모양(`#E8710A`)은 주의 연한 바탕 위 2.8:1이라 혼자 뜻을 전하지 못해요. 그래서 '주의' 글자를 꼭 같이 써요.

## 색을 이렇게 고른 이유

1. **메타 위에서 구분되게.** 광고 관리자는 파랑(#0866FF 계열)이 주인공이에요. 우리 오버레이 테두리·버튼이 메타 버튼과 헷갈리면 사용자가 메타 버튼을 우리 안내로 착각해요. 그래서 메인을 파랑이 아닌 바이올렛 `#5B3FD9`로 정했어요. 메타 흰 화면 위에서 6.6:1로 또렷해요.
2. **알림 4색과 안 겹치게.** 빨강·주황·파랑·초록은 "차단·주의·참고·정상" 뜻으로만 써요. 메인이 이 중 하나와 같으면 "현재 단계"와 "문제 있음"이 같은 색이 돼요. 바이올렛은 넷 중 어느 것과도 색상(hue)이 멀어요. 특히 참고 파랑(`#1A73E8`)과도 구분돼요.
3. **확장과 분석 페이지가 같은 색.** 사이드 패널, 광고 관리자 위 캐릭터, 분석 페이지가 한 서비스로 보이게 같은 원천에서 만들어요. `extension/tests/tokens.test.ts`가 두 앱의 값이 같은지 검사해요.

## 알림 모양 규칙 (WCAG 1.4.1 색만으로 말하지 않기)

색을 못 구분하는 사람도 뜻을 알 수 있게 **모양 + 기호 + 이름**을 같이 보여 줘요.

| 단계 | 모양 | 기호 | 이름 (화면 낭독기용) |
|---|---|---|---|
| 차단 | ■ 네모 | ✕ | "차단" |
| 주의 | ▲ 세모 | ! | "주의" |
| 참고 | ● 동그라미 | i | "참고" |
| 정상 | ✓ (동그라미 안) | ✓ | "정상" |

- 모양 안 기호는 흰색(`on-meta`)이에요. 차단·참고 4.5:1 이상, 정상·주의 3:1 이상(기호는 모양의 일부).
- 알림 색은 메인 바이올렛과 섞지 않아요 (예: 바이올렛 배경 위 빨간 글자 금지).
- **▲는 주의 알림에만** 써요. 좋아짐·나빠짐은 ↑↓ 화살표에 문구를 붙여요 (예: "↓ 광고비 15% 싸요").
- **경고는 결론보다 먼저**: 알림 바는 카드 맨 위, 어시스턴트도 알림(주황) 말풍선을 먼저 보내요.
- **차트에 주황을 쓰지 않아요** (주황은 주의 색). 보통 값 같은 강조 표시는 진한 보라 점(`accent-ink`)으로 해요.
- 표·카드 안 고정 안내(예: "평균만 보고 끄지 마세요")는 알림이 아니에요. 알림 모양 없이 테두리 상자(`line`)에 넣어요.
- 분석 페이지 구현: `web/src/ui/index.tsx`의 `AlertMark`·`Banner`·`ReferenceBadge`.

### ● 참고만 배지 (v4.2, ALT-22)

보여진 횟수가 100 미만인 칸은 판정(90/70%)에 넣지 않고 **● 참고만** 배지를 달아요.

- 배지: 파랑 바탕(`reference`) + 흰 글자(`on-accent`) + ● 기호 + "참고만" 글자.
- 그 칸의 숫자는 `ink-soft`로 연하게 써요.
- 회색으로 칠하지 않아요. 회색은 '아직 몰라요'에만 써서 두 뜻이 섞이지 않게 해요.

## 판정 표시 (v4.2)

분석 결과가 얼마나 확실한지는 **메인 색의 진하기**로만 말해요. 알림 색을 쓰지 않아요.
사장님 화면에는 아래 **화면 글자 3개만** 써요. 근거 탭·개발 문서·코드 값은 예전 이름(확실/유력/보류, 코드 `채택/유력/보류`)을 그대로 써요. 기준(90% / 70%)은 같아요.

| 확률 | 화면 글자 | 근거 탭·개발 문서 | 기호 | 모양 (글자 / 바탕 / 테두리) |
|---|---|---|---|---|
| 90% 이상 | **확실해요** | 확실 | ● | 흰 글자 `on-accent` / **메인 보라 채움** `adopt` `#5B3FD9` / 없음 (꾸미기안_뭉치 2026-11-26 `.t-sure`) |
| 70~90% | **B 쪽이에요** (이긴 쪽 이름) | 유력 | ◐ | 보라 글자 `adopt` / **흰 바탕** `likely-bg` `#FFFFFF` / 보라 실선 `likely` `#5B3FD9` (꾸미기안_뭉치 2026-11-26 `.t-lean` 1.5px). 두 앱 같음. 화면은 `bg-likely-bg`를 써요 (`bg-adopt-bg` 아님) |
| 70% 미만 · 표본 부족 | **아직 몰라요** | 보류 | ○ | 회보라 글자 `hold` `#5E5880` / 연한 회보라 `hold-bg` `#EEECF3` / 없음 (꾸미기안_뭉치 2026-11-26 `.t-dk`) |

진하기가 ● 채움 → ◐ 흰 바탕 테두리 → ○ 회보라 순으로 옅어져서, 색을 못 구분해도 기호와 글자로 단계를 알 수 있어요.

- 배지 안에는 화면 글자를 꼭 같이 써요 (색만으로 말하지 않기).
- '확실히 차이 남', '우세', '유의미' 같은 다른 말은 쓰지 않아요.
- 판정을 낮추는 규칙(ALT-13 지출 쏠림, ALT-14 표본 부족)은 '확실해요 → B 쪽이에요 → 아직 몰라요' 순서로 한 단계씩 내려요.
- 구현: 분석 페이지 `web/src/ui/index.tsx`의 `VerdictBadge`(문구는 `web/src/steps/Certainty.tsx`), 확장 `extension/entrypoints/sidepanel/steps/PlanStep.tsx`(문구는 `ownerWord`).

### 테스트 제안 태그

돌려 본 적 없는 선택지(예: 세로 9:16 소재)에는 판정 배지를 달지 않고 **'테스트 제안' 태그**를 달아요. 판정 배지는 실측이 있는 카드에만 써요.

- 모양: **뭉치 배 바탕**(`belly`) + 갈색 글자(`belly-ink`), 테두리·기호 없음 (꾸미기안_뭉치 2026-11-26. 예전: 보라 점선 테두리).
- 판정 배지는 모두 보라·회색(● 채움 · ◐ 실선 테두리 · ○ 회색)이라, 베이지 태그는 판정과 헷갈리지 않아요. 태그 안에 '테스트 제안' 글자를 꼭 써요.
- 구현: 분석 페이지 `web/src/ui/index.tsx`의 `TestTag`, 확장 `extension/entrypoints/sidepanel/steps/PlanStep.tsx`의 태그.

### 테스트할 칸 표시

내 설정 표(AN-03)에서 테스트할 행은 **보라 왼쪽 테두리(`accent`) + '테스트' 배지**로 보여요. 노란 바탕은 쓰지 않아요 (주의 주황과 헷갈려요).

### 차트 색

- 추천 쪽 = 바이올렛(`series-b`), 나머지 = 회색(`series-a`). 누가 나은지는 문구로도 써요.
- 보통 값(가장 그럴듯한 값) = 진한 보라 점(`accent-ink`).
- 범위 기준선(70%·90%) = 뭉치 배 색 `belly-strong` 점선 (꾸미기안_뭉치 2026-11-26 `.spark .th`, 예전 `ink`). 선 옆에 '점선 = 70%' 글자를 꼭 써요 (흰 바탕 2.1:1).
- 값 글자가 붙은 작은 막대는 나머지 쪽을 연보라 `series-soft`로 써도 돼요.

## 새 버전에서 가져다 쓰는 법

**웹 (Tailwind v4 아닌 곳 포함)** — `web/src/tokens.css`를 복사하거나 `@import` 하고 `var(--tone-accent)`처럼 써요.

**Tailwind v4** — 분석 페이지처럼 `tokens.css`를 불러온 뒤 `@theme inline { --color-accent: var(--tone-accent); }`로 연결해요 (`web/src/styles.css` 참고). 또는 확장처럼 `extension/assets/tokens.css`의 `@theme` 블록을 그대로 `@import` 해요.

**새 출력이 필요할 때 (예: 다른 앱, 발표 자료)** — `build.cjs`의 `outputs`에 파일을 하나 더해요. 이름 짝만 정하면 값은 `resolve("semantic.tone.accent")`로 원천에서 읽어요. 직접 hex를 적지 마세요.

**발표 자료·디자인 툴** — 아래 값을 쓰면 돼요.

```
메인 #5B3FD9 · 눌림 #4528B0 · 연한 바탕 #EFEBFF · 아주 옅은 보라 #F7F4FF
글자 #2A1F5C · 보조 글자 #6B6590 · 바탕 #FFFAF2 · 카드 #FFFFFF · 선 #E8E2F4
뭉치 배(장식) #F6E4CB · #D2AD81 · 배 위 글자 #7A5320
차단 #D93025 · 주의 #E8710A(글자 #7A3D06) · 참고 #1A73E8(글자 #123B73) · 정상 #1E8E3E(글자 #1B5E2C)
확실해요 #5B3FD9 채움 · 아직 몰라요 #5E5880 / #EEECF3
```

**색을 바꿀 때 순서**
1. `design-system/tokens.json`의 primitive 값을 바꿔요 (의미 토큰 이름은 그대로).
2. `node design-system/build.cjs` — 대비가 기준 미만이면 실패하고 어느 쌍인지 알려 줘요.
3. `cd extension && npx vitest run`, `cd web && npx vitest run && npx vite build`.

## 대비 검사 결과

기준: 글자 4.5:1 (WCAG 1.4.3 AA), 모양·테두리 3:1 (WCAG 1.4.11). `build.cjs`가 매번 다시 계산하고, 하나라도 미달이면 실패해요.
쌍 목록은 `build.cjs`의 `PAIRS`에 있어요. 새 글자·바탕 조합을 쓰면 여기에 더해 주세요.

| 쓰는 곳 | 글자/모양 | 바탕 | 대비 | 기준 | 결과 |
|---|---|---|---|---|---|
| 본문 (페이지 바탕) | #2A1F5C | #FFFAF2 | 13.95:1 | 4.5:1 | 통과 |
| 본문 (카드) | #2A1F5C | #FFFFFF | 14.49:1 | 4.5:1 | 통과 |
| 보조 글자 (카드) | #6B6590 | #FFFFFF | 5.40:1 | 4.5:1 | 통과 |
| 보조 글자 (눌린 칸) | #6B6590 | #F3F0FB | 4.80:1 | 4.5:1 | 통과 |
| 메인 글자·링크 | #4528B0 | #FFFFFF | 9.62:1 | 4.5:1 | 통과 |
| 연한 바탕 위 메인 글자 | #4528B0 | #EFEBFF | 8.24:1 | 4.5:1 | 통과 |
| 말풍선 본문 | #2A1F5C | #EFEBFF | 12.42:1 | 4.5:1 | 통과 |
| 주 버튼 글자 | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| 주 버튼 글자 (눌림) | #FFFFFF | #4528B0 | 9.62:1 | 4.5:1 | 통과 |
| ● 확실해요 배지 (진한 보라 바탕 + 흰 글자) | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| ◐ ○ 쪽이에요 배지 글자 (흰 바탕) | #5B3FD9 | #FFFFFF | 6.65:1 | 4.5:1 | 통과 |
| ◐ ○ 쪽이에요 배지 테두리 | #5B3FD9 | #FFFFFF | 6.65:1 | 3:1 | 통과 |
| ○ 아직 몰라요 배지 (회색) | #5E5880 | #EEECF3 | 5.63:1 | 4.5:1 | 통과 |
| ▲ 주의 글자 | #7A3D06 | #FFF1E3 | 7.58:1 | 4.5:1 | 통과 |
| ■ 차단 상자 글자 | #B3261E | #FCE8E6 | 5.55:1 | 4.5:1 | 통과 |
| ■ 차단 오류 한 줄 (흰 바탕) | #D93025 | #FFFFFF | 4.77:1 | 4.5:1 | 통과 |
| ● 참고 상자 글자 | #123B73 | #EAF2FE | 9.81:1 | 4.5:1 | 통과 |
| ✓ 정상 상자 글자·'그대로' 태그 | #1B5E2C | #E9F6EC | 7.03:1 | 4.5:1 | 통과 |
| 참고 상자 안 본문 | #2A1F5C | #EAF2FE | 12.86:1 | 4.5:1 | 통과 |
| 못 누르는 큰 버튼 글자 | #5E5880 | #EEECF3 | 5.63:1 | 4.5:1 | 통과 |
| 아직 몰라요 글자 (흰 바탕) | #5E5880 | #FFFFFF | 6.60:1 | 4.5:1 | 통과 |
| ■ 모양 안 ✕ | #FFFFFF | #D93025 | 4.77:1 | 4.5:1 | 통과 |
| ● 모양 안 i | #FFFFFF | #1A73E8 | 4.51:1 | 4.5:1 | 통과 |
| ● 참고만 배지 글자 (ALT-22) | #FFFFFF | #1A73E8 | 4.51:1 | 4.5:1 | 통과 |
| ■ 차단 모양 (연한 바탕) | #D93025 | #FCE8E6 | 4.05:1 | 3:1 | 통과 |
| ● 참고 모양 (연한 바탕) | #1A73E8 | #EAF2FE | 4.00:1 | 3:1 | 통과 |
| ✓ 정상 모양 (연한 바탕) | #1E8E3E | #E9F6EC | 3.78:1 | 3:1 | 통과 |
| ✓ 모양 안 체크 | #FFFFFF | #1E8E3E | 4.21:1 | 3:1 | 통과 |
| ▲ 모양 안 ! | #FFFFFF | #E8710A | 3.09:1 | 3:1 | 통과 |
| 오버레이 안내 글자 | #6B6590 | #FFFFFF | 5.40:1 | 4.5:1 | 통과 |
| 오버레이 보조 버튼 | #6B6590 | #F3F0FB | 4.80:1 | 4.5:1 | 통과 |
| 오버레이 주 버튼 | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| 메인 바탕 위 흰 글자 | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| 메인 진하게 위 흰 글자 | #FFFFFF | #4528B0 | 9.62:1 | 4.5:1 | 통과 |
| 테스트 제안 태그 (배 색 바탕) | #7A5320 | #F6E4CB | 5.47:1 | 4.5:1 | 통과 |
| 보조 글자 (크림 바탕) | #6B6590 | #FFFAF2 | 5.20:1 | 4.5:1 | 통과 |
| 말풍선 단계 칩 | #5B3FD9 | #EFEBFF | 5.70:1 | 4.5:1 | 통과 |
| 말풍선 작은 보조 버튼 | #6B6590 | #F3F0FB | 4.80:1 | 4.5:1 | 통과 |
| 말풍선 안 굵은 값 | #5B3FD9 | #FFFFFF | 6.65:1 | 4.5:1 | 통과 |
| 굵은 값 (밑줄 위로 겹친 부분) | #5B3FD9 | #F6E4CB | 5.34:1 | 4.5:1 | 통과 |
| 테두리 보조 버튼 | #5B3FD9 | #FFFFFF | 6.65:1 | 4.5:1 | 통과 |
| 패널 머리 흰 글자 (그라데이션 밝은 쪽) | #FFFFFF | #6A4FE6 | 5.42:1 | 4.5:1 | 통과 |
| 패널 머리 흰 글자 (그라데이션 어두운 쪽) | #FFFFFF | #4A2FC4 | 8.42:1 | 4.5:1 | 통과 |
| 초점 링·현재 단계 테두리 | #5B3FD9 | #FFFFFF | 6.65:1 | 3:1 | 통과 |
| 메타 화면 위 칸 테두리 | #5B3FD9 | #FFFFFF | 6.65:1 | 3:1 | 통과 |
| ▲ 주의 모양 | #E8710A | #FFFFFF | 3.09:1 | 3:1 | 통과 |
| 차트 비교 막대 | #8A92A0 | #FFFFFF | 3.13:1 | 3:1 | 통과 |
| 입력칸 테두리 (카드) | #767E8C | #FFFFFF | 4.09:1 | 3:1 | 통과 |
| 입력칸 테두리 (페이지 바탕) | #767E8C | #FFFAF2 | 3.94:1 | 3:1 | 통과 |
| 입력칸 테두리 (눌린 칸) | #767E8C | #F3F0FB | 3.64:1 | 3:1 | 통과 |

## 검토 기록 (2026-11-25, ui-ux-pro-max 기준)

| 항목 | 기준 | 상태 |
|---|---|---|
| 글자 대비 | 4.5:1 (`color-accessible-pairs`) | 39쌍 모두 통과 (입력칸 테두리 3쌍 추가. v4.2 참고만 배지, 판정 배지를 실제 모양대로 다시 짝지음. '○ 쪽이에요' 배지는 두 앱 모두 연한 보라 바탕으로 통일). 차단 글자용 `block-ink` 추가, 분석 페이지 차단 배너에 적용 |
| 색만으로 말하지 않기 | WCAG 1.4.1 | 알림 모양·판정 글자 규칙으로 지킴 |
| 화면 코드 hex 금지 | `color-semantic` | `web/src`·`extension/entrypoints`·`extension/assets` 위반 0. `text-white`/`bg-white` → `text-on-accent`/`bg-on-accent`, 입력칸 그림자의 rgba → `--color-ink` |
| 초점 링 | 2–4px, 늘 보이게 (`focus-states`) | 화면마다 2px·3px 섞여 있었음 → `focus.width` 2px, offset 2px로 통일 (`outline-3`·`outline-offset-1` 정리). 분석 페이지 기본 초점 링(`styles.css`)도 3px 고정값이었던 것을 `--focus-width`·`--focus-offset`으로 바꿈 |
| 입력칸 테두리 | 3:1 (WCAG 1.4.11, `input-labels`) | 입력칸이 구분선 색 `line`(1.3:1)을 써서 칸이 잘 안 보였음 → `field-line` #767E8C(3.4–4.0:1) 추가. 화면 코드 적용은 아래 '보완' 참고 |
| 화면 너비·그림자 | 단계 이름으로 (`spacing-scale`, `elevation-consistent`) | `max-w-[960px]`·`[1040px]`·`[60ch]`, `shadow-sm`·`shadow-lg`, 오버레이 그림자 숫자를 직접 씀 → `layout.*`, `elevation.*` 토큰 추가 |
| 못 누르는 상태 | 투명도 0.38–0.5 (`disabled-states`) | 화면마다 0.3·0.4·0.5 섞여 있었음 → 모든 버튼이 `state.disabled-opacity` 0.4 사용 |
| 움직임 | 같은 리듬 (`motion-consistency`) | 오버레이 0.35s·0.5s를 `motion.move/walk` 토큰으로 |
| 글꼴 | 한 서비스 한 글꼴 | 오버레이만 다른 글꼴 목록을 쓰던 것을 공통 글꼴로 |
| 확장 글자 크기 | 일정한 단계 (`font-size-scale`) | 사이드 패널이 9·10·12·13·14·15·16·17·20·26px를 직접 씀 → 모두 단계 이름으로 바꿈. 9px 기호는 10px(`text-mark`), 26px 이름은 28px(`text-number`)로 맞춤 |
| 누르는 칸 크기 | 웹 최소 24px (WCAG 2.5.8) | 주 버튼 48px, 오버레이 버튼 약 33px로 통과 |
| 본문 글자 크기 | 16px 이상 권장 (`readable-font-size`) | 15px → **16px로 올림** (2026-11-25). 분석 페이지는 `text-body`로 바로 반영. 확장 사이드 패널의 `text-[15px]` 11곳도 `text-body`로 바꿔 반영 |

예전 원천 `web/tokens.json`은 지웠어요 (2026-11-25). 색은 이제 `design-system/tokens.json`에만 있어요.

## v4.2 반영 (2026-11-25)

화면설계서 v4.2의 '화면 표현 원칙'에 맞췄어요. 색 값은 그대로이고, 판정 화면 글자, ● 참고만 배지(`tone.reference`), ▲·↑↓ 기호 규칙, 테스트 제안 태그, 테스트 행 표시, 차트 보통 값 점을 더했어요.
숫자 표기(원 단위·범위·사람 수)와 용어 표기는 색·모양이 아니라 문구 규칙이라 화면설계서 AN-TXT에 있어요.

## 보완 (2026-11-25, 2차 검토)

ui-ux-pro-max 기준으로 다시 보고 빈 곳을 채웠어요. 색 값은 하나도 안 바꿨고, 토큰만 더했어요.

| 더한 것 | 왜 |
|---|---|
| `tone.field-line` #767E8C, `component.field.*` | 입력칸 테두리가 `line`(1.3:1)이라 흰 카드 위에서 칸이 거의 안 보였어요. 대비 검사 3쌍도 더했어요 |
| `layout.page / page-wide / measure` | 분석 페이지 너비가 숫자로만 있었어요 |
| `elevation.raised / float` | 그림자가 Tailwind 기본값과 오버레이 숫자로 따로 있었어요 |
| 분석 페이지 초점 링 2px | 토큰은 2px인데 `styles.css`만 3px였어요 |

**화면 코드 적용 (같은 날)**

- 입력칸 8곳 `border-line` → `border-field-line`:
  - 분석 페이지: `MySettings`, `Simulator`
  - 확장: `Chat`, `CodeStep`, `CopyStep`, `AnalysisAssistant`, `QuestionStep`, `FindStep` 상품 검색칸
  - 보조 버튼·카드·근거 태그의 `border-line`은 장식 테두리라 그대로 둬요. 버튼은 글자로 알아볼 수 있어요
- 너비: `App.tsx` → `max-w-page` · `max-w-page-wide`, `Start.tsx` → `max-w-measure`
- 그림자:
  - 토스트 → `shadow-float`
  - `PlanStep` sticky 칸 → `shadow-raised`
  - 오버레이 말풍선 → `--coach-shadow` = `primitive.shadow.bubble` (`0 10px 28px` 검정 28%). 바탕은 흰색(`coach.bubble-bg` = `tone.surface`), 테두리는 옅은 보라(`coach.bubble-border` = `tone.accent-line`): 메타 흰 화면 위에서 그림자로 떠 보이고, 보라 테두리로 우리 안내임을 알게 해요 (꾸미기안_뭉치, 사용자 확인 2026-11-27)

## 꾸미기안_뭉치 2026-11-26 반영

사용자가 준 꾸미기안 두 개(분석 페이지·확장 프로그램 `광고어시스턴트_*_꾸미기안_뭉치.html`)에 맞췄어요. 구조는 그대로, 분위기만 뭉치에 맞춰요.

| 바꾼 것 | 값 | 꾸미기안 근거 |
|---|---|---|
| 바탕·글자 색 | ink `#2A1F5C`, ink-soft `#6B6590`, bg `#FFFAF2`, surface `#FFFFFF`, sunk `#F3F0FB`, line `#E8E2F4` | `:root` 변수 `--ink` `--sub` `--cream` `--line` |
| 새 색 | `accent-faint` `#F7F4FF`, `belly` 3단계 | `--v-ll`, `--belly` `--tan`, 메모 '색은 뭉치 몸에서' |
| 모서리 | card 20 · button 16 · 말풍선 18(`radius.bubble`) · 말풍선 버튼 12 | 메모 '모서리 16~18px', `.card` 18, `.btns` 12 |
| 그림자 | `card` · `press` · `hero` 추가 (확장 `shadow-card/press/hero`) | `.card`, `.big`·`.btns .p`의 `0 4px 0 var(--v2)`, `.hero` |
| 오버레이 말풍선 | `--coach-chip-*`(단계 칩), `--coach-dot` `--coach-dot-on` `--coach-dot-height` `--coach-dot-gap`(14칸 진행 점), `--coach-primary-shadow`, `--coach-emphasis-fg` + `--coach-mark-bg`(굵은 값 + 배 색 밑줄), `--coach-ghost-bg/fg`(작은 보조 버튼), 보조 버튼은 회보라 바탕(`sunk`) + 보조 글자, 테두리 없음 | `.chip` `.dots` `.btns` `.tx b`, 메모 '다 했어요만 크게, 이전·멈추기는 작게' |
| 사이드 패널 | `--panel-head-from/to`(머리 135° 그라데이션 `#6A4FE6`→`#4A2FC4`), `--panel-head-radius` 26px, `--panel-progress-from/to`(`#7C63F0`→메인), `--panel-progress-dot`(배 색), `--panel-avatar-bg` | `.top` `.bar` `.bar .dot` `.brand .av` |

꾸미기안의 칩 글자 11.5px·말풍선 본문 15px·버튼 높이 40px는 최소 기준(글자 12px, 본문 16px, 누르는 곳 44px)에 맞춰 올려 썼어요. 꾸미기안의 `#ECE8F6`·`#EAE4F7` 같은 아주 비슷한 옅은 보라는 새 값을 만들지 않고 `line`으로 썼어요.

### 2차 꼼꼼 반영 (2026-11-27, 사용자: '꾸미기안 반영을 꼼꼼히')

1차에서 물어보려고 남겨 둔 값까지 꾸미기안대로 넣었어요.

| 바꾼 것 | 예전 → 지금 | 꾸미기안 근거 |
|---|---|---|
| 알림 상자 | 주의 바탕 `#FEF3E6`→`#FFF1E3`, 글자 `#B35300`→`#7A3D06` · 정상 바탕 `#E6F4EA`→`#E9F6EC`, 글자 `ink`→`#1B5E2C` · 참고 바탕 `#E8F0FE`→`#EAF2FE`, 글자 `ink`→`#123B73` · 테두리 `*-line` 3개 새로 (차단 `block-line`은 2026-11-27 사용자 요청으로 추가) | `.alert.w` `.alert.ok` `.note` |
| 판정 배지 | 확실해요 `#4528B0`→`#5B3FD9` · 쪽이에요 바탕 `#EFEBFF`→흰색 · 아직 몰라요 `#5F6672`/`#F1F1EF`→`#5E5880`/`#EEECF3` | `.t-sure` `.t-lean` `.t-dk` |
| 못 누르는 큰 버튼 | 투명도 0.4 → 회보라 상자 `disabled-*` | `.cta-off` |
| 말풍선 | 연보라 바탕 + 보라 테두리 + float 그림자 → 흰 바탕, 테두리 없음, 검은 그림자 `bubble`. 화면은 이미 22% 어둡게 덮여 있어서(scrim) 메타 흰 화면과 구분돼요. 사장님 차례는 보라 4px 테두리 그대로 | `.card` |
| 3D 캐릭터 배 | `#F7B77A` → `#D2AD81` (`belly-strong`) | 메모 '배 #D2AD81' |
| 모서리 | 카드 20→22, 새 soft 14 · 2xl 26 | `.card` 22, `.alert` `.ghost` 14, `.drop` `.top` 26 |
| 그림자 | press-sm · cta · selected · bubble · mascot 추가 | `.steps .cur` `.big` `.it.cur` `.card` `.headrow img` |
| 글자 | 페이지 제목 32→30(`hero-sm`), 새 `headline` 24 | `.h1` 30, `.what` 24 |
| 큰 버튼 | 높이 48→52, `ghost` 보조 버튼, `meter`·`drop` 부품 | `.big` `.ghost` `.meter` `.drop` |

**꾸미기안대로 하지 않은 것 (이유)**
- 체크리스트 네모 테두리 `#CFC6EC`: 흰 바탕 위 1.6:1이라 입력칸 기준 3:1(WCAG 1.4.11)에 못 미쳐요. `field-line`을 그대로 써요.
- 말풍선 본문 15px·칩 11.5px·버튼 높이 40px: 본문 16px, 글자 12px, 누르는 곳 44px 기준을 지켜요.
- 확장 14번 칸의 주의 색(`#FFF4E8`·`#F2B27A`·`#8A4A0E`)은 분석 페이지 주의 상자와 값이 조금 달라요. 한 서비스 한 색이라 분석 페이지 값(`warn-*`)으로 묶었어요.
- 패널 머리 위 흰 번짐·탭 바탕(흰색 14~22% 투명)은 흰색에 투명도를 준 장식이라 토큰을 만들지 않았어요 (`bg-on-accent/15`처럼 써요).

