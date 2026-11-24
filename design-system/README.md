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
| `extension/assets/tokens.css` | 확장 사이드 패널. `extension/assets/tailwind.css`가 `@import` | `@theme`: `--color-*`(바탕·글자·메인·알림 4색과 연한 바탕·확실도·`on-accent`), `--font-sans`, `--text-caption/body/lead/title/number` · `:root`: `--state-disabled-opacity`, `--focus-width/offset`, `--motion-*` |
| `extension/assets/overlay-tokens.css` | 광고 관리자 위 오버레이(shadow root). `overlay.css`가 `@import`, `Character.tsx`가 `var()`로 씀 | `--coach-*`, `--character-*` |

세 파일 모두 머리에 "자동 생성" 주석이 있어요. 직접 고치면 다음 빌드에서 덮어써요.
확장 이름(`--color-*`)과 의미 토큰의 짝은 `build.cjs`의 `EXTENSION_COLORS`에 있어요.

## 색 외 토큰

| 이름 | 값 | 쓰는 곳 |
|---|---|---|
| `semantic.text.family` | Pretendard → Noto Sans KR → system-ui | 두 앱·오버레이 공통 글꼴 |
| `primitive.font.size.*` | mark 10 · small 12 · caption 13 · label 14 · body 16 · lead 17 · title 20 · number 28 · hero 40 | 두 앱 모두 `text-caption`처럼 Tailwind 이름으로 써요. `text-[13px]`처럼 숫자를 직접 쓰지 않아요. `mark`는 알림·체크 모양 안 기호에만 써요 |
| `semantic.text.line-height` | 1.5 | 본문 줄 간격 |
| `semantic.motion.hover / expand / move / walk` | 150 / 250 / 350 / 500ms | 색 바뀜 / 펼치기 / 테두리 이동 / 캐릭터 걸음. 모두 `prefers-reduced-motion`이면 끔 |
| `semantic.state.disabled-opacity` | 0.4 | 못 누르는 버튼: `disabled:opacity-(--state-disabled-opacity)` + `disabled` 속성 |
| `component.focus.width / offset` | 2px / 2px | 초점 링 (`outline-2 outline-offset-2 outline-accent`) |

## 색 표

### 메인 (바이올렛)

| 이름 (semantic) | 값 | 쓰는 곳 | 대비 |
|---|---|---|---|
| `tone.accent` · 확장 `accent` | `#5B3FD9` | 현재 단계, 로고, 초점 링, 칸 테두리, 주 버튼(`tone.action`), 캐릭터 몸 | 흰 바탕 6.5:1 |
| `tone.accent-ink` · 확장 `accent-ink` | `#4528B0` | 메인 글자·링크, 버튼 눌림(`tone.action-hover`), 확실 배지 | 흰 바탕 9.5:1 |
| `tone.accent-soft` · 확장 `accent-soft` | `#EFEBFF` | 연한 바탕: 어시스턴트 패널, 말풍선, 선택 행, 확실 배지 바탕 | (바탕색) |
| `tone.accent-line` | `#B3A5F0` | 오버레이 보조 버튼 테두리 (장식) | — |

### 바탕·글자

| 이름 | 값 | 쓰는 곳 | 대비 |
|---|---|---|---|
| `tone.ink` · 확장 `ink` | `#16213A` | 본문, 숫자 | 15.7:1 |
| `tone.ink-soft` · 확장 `soft` | `#4A5568` | 보조 글자 | 7.4:1 |
| `tone.bg` · 확장 `cream` | `#F7F5F0` | 페이지 바탕 | — |
| `tone.surface` · 확장 `paper` | `#FFFDF8` | 카드 바탕, 주 버튼 글자 | — |
| `tone.surface-sunk` · 확장 `sunk` | `#EFEAE0` | 막대 빈 부분, 눌린 칸 | — |
| `tone.line` · 확장 `line` | `#E2DCD0` | 선 | — |
| `tone.hold` / `hold-bg` | `#5F6672` / `#F1F1EF` | 보류 배지 | 5.1:1 |
| `tone.series-a` | `#8A92A0` | 차트 비교 막대 | 3.1:1 (모양) |
| `tone.on-meta` | `#FFFFFF` | 메타 흰 화면 위 버튼 바탕, 알림 모양 안 기호 | — |

### 알림 4색 (고정)

| 단계 | 모양 색 | 글자 색 | 연한 바탕 | 쓰는 곳 |
|---|---|---|---|---|
| ■✕ 차단 | `block` `#D93025` | 흰 바탕 위: `block` (4.7:1) · 연한 바탕 위: **`block-ink` `#B3261E`** (5.6:1) | `block-bg` `#FCE8E6` | 게시하면 안 되는 문제 |
| ▲! 주의 | `warn-mark` `#E8710A` | `warn` `#B35300` (4.6:1) | `warn-bg` `#FEF3E6` | 고치면 좋은 문제 |
| ●i 참고 | `info` `#1A73E8` | `ink` (14.0:1) | `info-bg` `#E8F0FE` | 알아 두면 좋은 정보 |
| ✓ 정상 | `ok` `#1E8E3E` | `ink` (14.1:1) | `ok-bg` `#E6F4EA` | 문제 없음 |

알림 원색 네 개는 **모양(■▲●✓)에만** 써요. 연한 바탕 위 글자로 쓰면 4.5:1이 안 나와요(차단 4.05, 참고 3.93, 정상 3.70).
그래서 주의는 `warn`(진한 주황), 차단은 `block-ink`(진한 빨강), 참고·정상은 `ink`를 글자로 써요.

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
- 분석 페이지 구현: `web/src/ui/index.tsx`의 `AlertMark`·`Banner`.

## 확실도 표시

분석 결과가 얼마나 확실한지는 **메인 색의 진하기**로만 말해요. 알림 색을 쓰지 않아요.

| 단계 | 기준 | 글자 | 바탕 | 모양 |
|---|---|---|---|---|
| 확실 | 90% 이상 | `adopt` = 메인 진하게 `#4528B0` | `adopt-bg` `#EFEBFF` | 채운 배지 |
| 유력 | 70~90% | `likely` = 메인 `#5B3FD9` | `likely-bg` `#FFFDF8` | 테두리만 있는 배지 (연하게) |
| 보류 | 70% 미만 | `hold` = 회색 `#5F6672` | `hold-bg` `#F1F1EF` | 회색 배지 |

배지 안에는 "확실·유력·보류" 글자를 꼭 같이 써요 (색만으로 말하지 않기).

## 새 버전에서 가져다 쓰는 법

**웹 (Tailwind v4 아닌 곳 포함)** — `web/src/tokens.css`를 복사하거나 `@import` 하고 `var(--tone-accent)`처럼 써요.

**Tailwind v4** — 분석 페이지처럼 `tokens.css`를 불러온 뒤 `@theme inline { --color-accent: var(--tone-accent); }`로 연결해요 (`web/src/styles.css` 참고). 또는 확장처럼 `extension/assets/tokens.css`의 `@theme` 블록을 그대로 `@import` 해요.

**새 출력이 필요할 때 (예: 다른 앱, 발표 자료)** — `build.cjs`의 `outputs`에 파일을 하나 더해요. 이름 짝만 정하면 값은 `resolve("semantic.tone.accent")`로 원천에서 읽어요. 직접 hex를 적지 마세요.

**발표 자료·디자인 툴** — 아래 값을 쓰면 돼요.

```
메인 #5B3FD9 · 눌림 #4528B0 · 연한 바탕 #EFEBFF
글자 #16213A · 보조 글자 #4A5568 · 바탕 #F7F5F0 · 카드 #FFFDF8
차단 #D93025 · 주의 #E8710A(글자 #B35300) · 참고 #1A73E8 · 정상 #1E8E3E
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
| 본문 (페이지 바탕) | #16213A | #F7F5F0 | 14.68:1 | 4.5:1 | 통과 |
| 본문 (카드) | #16213A | #FFFDF8 | 15.74:1 | 4.5:1 | 통과 |
| 보조 글자 (카드) | #4A5568 | #FFFDF8 | 7.40:1 | 4.5:1 | 통과 |
| 보조 글자 (눌린 칸) | #4A5568 | #EFEAE0 | 6.28:1 | 4.5:1 | 통과 |
| 메인 글자·링크 | #4528B0 | #FFFDF8 | 9.46:1 | 4.5:1 | 통과 |
| 연한 바탕 위 메인 글자 | #4528B0 | #EFEBFF | 8.24:1 | 4.5:1 | 통과 |
| 말풍선 본문 | #16213A | #EFEBFF | 13.71:1 | 4.5:1 | 통과 |
| 주 버튼 글자 | #FFFDF8 | #5B3FD9 | 6.54:1 | 4.5:1 | 통과 |
| 주 버튼 글자 (눌림) | #FFFDF8 | #4528B0 | 9.46:1 | 4.5:1 | 통과 |
| 확실 배지 | #4528B0 | #EFEBFF | 8.24:1 | 4.5:1 | 통과 |
| 유력 배지 | #5B3FD9 | #FFFDF8 | 6.54:1 | 4.5:1 | 통과 |
| 보류 배지 | #5F6672 | #F1F1EF | 5.12:1 | 4.5:1 | 통과 |
| ▲ 주의 글자 | #B35300 | #FEF3E6 | 4.62:1 | 4.5:1 | 통과 |
| ■ 차단 상자 글자 | #B3261E | #FCE8E6 | 5.55:1 | 4.5:1 | 통과 |
| ■ 차단 오류 한 줄 (흰 바탕) | #D93025 | #FFFDF8 | 4.70:1 | 4.5:1 | 통과 |
| ● 참고 상자 글자 | #16213A | #E8F0FE | 13.96:1 | 4.5:1 | 통과 |
| ✓ 정상 상자 글자 | #16213A | #E6F4EA | 14.09:1 | 4.5:1 | 통과 |
| ■ 모양 안 ✕ | #FFFFFF | #D93025 | 4.77:1 | 4.5:1 | 통과 |
| ● 모양 안 i | #FFFFFF | #1A73E8 | 4.51:1 | 4.5:1 | 통과 |
| ■ 차단 모양 (연한 바탕) | #D93025 | #FCE8E6 | 4.05:1 | 3:1 | 통과 |
| ● 참고 모양 (연한 바탕) | #1A73E8 | #E8F0FE | 3.93:1 | 3:1 | 통과 |
| ✓ 정상 모양 (연한 바탕) | #1E8E3E | #E6F4EA | 3.70:1 | 3:1 | 통과 |
| ✓ 모양 안 체크 | #FFFFFF | #1E8E3E | 4.21:1 | 3:1 | 통과 |
| ▲ 모양 안 ! | #FFFFFF | #E8710A | 3.09:1 | 3:1 | 통과 |
| 오버레이 안내 글자 | #4A5568 | #EFEBFF | 6.45:1 | 4.5:1 | 통과 |
| 오버레이 보조 버튼 | #4528B0 | #FFFFFF | 9.62:1 | 4.5:1 | 통과 |
| 오버레이 주 버튼 | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| 메인 바탕 위 흰 글자 | #FFFFFF | #5B3FD9 | 6.65:1 | 4.5:1 | 통과 |
| 메인 진하게 위 흰 글자 | #FFFFFF | #4528B0 | 9.62:1 | 4.5:1 | 통과 |
| 보류 글자 (흰 바탕) | #5F6672 | #FFFDF8 | 5.69:1 | 4.5:1 | 통과 |
| 초점 링·현재 단계 테두리 | #5B3FD9 | #FFFDF8 | 6.54:1 | 3:1 | 통과 |
| 메타 화면 위 칸 테두리 | #5B3FD9 | #FFFFFF | 6.65:1 | 3:1 | 통과 |
| ▲ 주의 모양 | #E8710A | #FFFDF8 | 3.04:1 | 3:1 | 통과 |
| 차트 비교 막대 | #8A92A0 | #FFFDF8 | 3.08:1 | 3:1 | 통과 |

## 검토 기록 (2026-11-25, ui-ux-pro-max 기준)

| 항목 | 기준 | 상태 |
|---|---|---|
| 글자 대비 | 4.5:1 (`color-accessible-pairs`) | 34쌍 모두 통과. 차단 글자용 `block-ink` 추가, 분석 페이지 차단 배너에 적용 |
| 색만으로 말하지 않기 | WCAG 1.4.1 | 알림 모양·확실도 글자 규칙으로 지킴 |
| 화면 코드 hex 금지 | `color-semantic` | `web/src`·`extension/entrypoints`·`extension/assets` 위반 0. `text-white`/`bg-white` → `text-on-accent`/`bg-on-accent`, 입력칸 그림자의 rgba → `--color-ink` |
| 초점 링 | 2–4px, 늘 보이게 (`focus-states`) | 화면마다 2px·3px 섞여 있었음 → `focus.width` 2px, offset 2px로 통일 (`outline-3`·`outline-offset-1` 정리) |
| 못 누르는 상태 | 투명도 0.38–0.5 (`disabled-states`) | 화면마다 0.3·0.4·0.5 섞여 있었음 → 모든 버튼이 `state.disabled-opacity` 0.4 사용 |
| 움직임 | 같은 리듬 (`motion-consistency`) | 오버레이 0.35s·0.5s를 `motion.move/walk` 토큰으로 |
| 글꼴 | 한 서비스 한 글꼴 | 오버레이만 다른 글꼴 목록을 쓰던 것을 공통 글꼴로 |
| 확장 글자 크기 | 일정한 단계 (`font-size-scale`) | 사이드 패널이 9·10·12·13·14·15·16·17·20·26px를 직접 씀 → 모두 단계 이름으로 바꿈. 9px 기호는 10px(`text-mark`), 26px 이름은 28px(`text-number`)로 맞춤 |
| 누르는 칸 크기 | 웹 최소 24px (WCAG 2.5.8) | 주 버튼 48px, 오버레이 버튼 약 33px로 통과 |
| 본문 글자 크기 | 16px 이상 권장 (`readable-font-size`) | 15px → **16px로 올림** (2026-11-25). 분석 페이지는 `text-body`로 바로 반영. 확장 사이드 패널의 `text-[15px]` 11곳도 `text-body`로 바꿔 반영 |

예전 원천 `web/tokens.json`은 지웠어요 (2026-11-25). 색은 이제 `design-system/tokens.json`에만 있어요.
