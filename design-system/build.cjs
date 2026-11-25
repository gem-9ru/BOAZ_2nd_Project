#!/usr/bin/env node
/**
 * Ad assistant 디자인 시스템 빌드.
 * 원천 design-system/tokens.json 하나에서 아래 파일을 만든다.
 *   - web/src/tokens.css                  분석 페이지 (--primitive-*, --tone-*, 부품 변수)
 *   - extension/assets/tokens.css         확장 프로그램 Tailwind @theme 색 (--color-*)
 *   - extension/assets/overlay-tokens.css 광고 관리자 위 오버레이 (:host 의 --coach-*, --character-*)
 * 그리고 글자·모양 대비를 검사한다 (글자 4.5:1, 모양 3:1 미만이면 실패).
 *
 * 쓰는 법 (저장소 최상위에서):
 *   node design-system/build.cjs            파일을 새로 쓴다
 *   node design-system/build.cjs --check    파일이 원천과 같은지만 본다 (다르면 exit 1)
 *   node design-system/build.cjs --contrast 대비 표를 마크다운으로 찍는다
 */
const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const DS = __dirname;
const ROOT = path.resolve(DS, "..");
const SOURCE = path.join(DS, "tokens.json");
const tokens = JSON.parse(fs.readFileSync(SOURCE, "utf8"));
const args = new Set(process.argv.slice(2));

/** "{semantic.tone.accent}" 또는 "semantic.tone.accent" → 최종 값 */
function resolve(ref) {
  const key = ref.replace(/^\{|\}$/g, "");
  let node = tokens;
  for (const k of key.split(".")) {
    node = node?.[k];
    if (node === undefined) throw new Error(`없는 토큰: ${key}`);
  }
  const v = node.$value;
  if (v === undefined) throw new Error(`값이 아닌 그룹: ${key}`);
  return typeof v === "string" && v.startsWith("{") ? resolve(v) : v;
}

const HEADER = (what) =>
  `/* 자동 생성 파일: 직접 고치지 마세요. ${what}\n` +
  ` * 원천: design-system/tokens.json → 저장소 최상위에서 \`node design-system/build.cjs\` */\n`;

// ── 1. 분석 페이지: 스킬의 generate-tokens.cjs 출력을 그대로 쓰고 머리말만 바꾼다 ──
function buildWeb() {
  const css = execFileSync(process.execPath, [path.join(DS, "scripts/generate-tokens.cjs"), "--config", SOURCE], {
    encoding: "utf8",
  });
  const body = css.replace(/^\/\* Design Tokens - Auto-generated \*\/\n\/\* Do not edit directly[^\n]*\n/, "");
  return HEADER("분석 페이지(web) 토큰.") + body.trimEnd() + "\n";
}

// ── 2. 확장 프로그램: Tailwind @theme 색. 이름은 화면 코드가 쓰는 그대로 유지 ──
const EXTENSION_COLORS = [
  ["/* 바탕·글자 */"],
  ["ink", "semantic.tone.ink"],
  ["soft", "semantic.tone.ink-soft"],
  ["paper", "semantic.tone.surface"],
  ["cream", "semantic.tone.bg"],
  ["line", "semantic.tone.line"],
  ["sunk", "semantic.tone.surface-sunk"],
  ["/* 메인 바이올렛: 현재 단계·주 버튼·초점 링 */"],
  ["accent", "semantic.tone.accent"],
  ["accent-ink", "semantic.tone.accent-ink"],
  ["accent-soft", "semantic.tone.accent-soft"],
  ["/* 알림 4색 고정: 메인과 섞지 않고, 모양(■ ▲ ● ✓)과 함께만 쓴다 */"],
  ["block", "semantic.tone.block"],
  ["block-ink", "semantic.tone.block-ink"],
  ["warn","semantic.tone.warn"],
  ["warn-mark", "semantic.tone.warn-mark"],
  ["info", "semantic.tone.info"],
  ["ok", "semantic.tone.ok"],
  ["block-bg", "semantic.tone.block-bg"],
  ["warn-bg", "semantic.tone.warn-bg"],
  ["info-bg", "semantic.tone.info-bg"],
  ["ok-bg", "semantic.tone.ok-bg"],
  ["on-accent", "semantic.tone.on-accent"],
  ["/* 확실도: 확실 = 메인 진하게, 유력 = 메인 테두리, 보류 = 회색 */"],
  ["adopt", "semantic.tone.adopt"],
  ["adopt-bg", "semantic.tone.adopt-bg"],
  ["likely", "semantic.tone.likely"],
  ["likely-bg", "semantic.tone.likely-bg"],
  ["hold", "semantic.tone.hold"],
  ["hold-bg", "semantic.tone.hold-bg"],
];

// 색 외 @theme 값: [Tailwind 변수 이름, 토큰]
const EXTENSION_THEME = [
  ["/* 글꼴·글자 크기: text-mark 10 · small 12 · caption 13 · label 14 · body 16 · lead 17 · title 20 · number 28 */"],
  ["--font-sans", "primitive.font.family.sans"],
  ["--text-mark", "primitive.font.size.mark"],
  ["--text-small", "primitive.font.size.small"],
  ["--text-caption", "primitive.font.size.caption"],
  ["--text-label", "primitive.font.size.label"],
  ["--text-body", "primitive.font.size.body"],
  ["--text-lead", "primitive.font.size.lead"],
  ["--text-title", "primitive.font.size.title"],
  ["--text-number", "primitive.font.size.number"],
  ["/* 모서리: 분석 페이지와 같은 이름 (rounded-button · rounded-card · rounded-badge · rounded-mark) */"],
  ["--radius-button", "component.button.radius"],
  ["--radius-card", "component.card.radius"],
  ["--radius-badge", "component.badge.radius"],
  ["--radius-mark", "component.alert-mark.radius"],
  ["/* 움직임: transition 기본 시간 (hover 등 색 바뀜) */"],
  ["--default-transition-duration", "semantic.motion.hover"],
];

function buildExtensionTheme() {
  const lines = EXTENSION_COLORS.map(([name, ref]) =>
    ref ? `  --color-${name}: ${String(resolve(ref)).toLowerCase()};` : `  ${name}`,
  );
  for (const [name, ref] of EXTENSION_THEME) lines.push(ref ? `  ${name}: ${resolve(ref)};` : `  ${name}`);
  // 못 누르는 상태·초점 링은 Tailwind 이름공간이 없어 :root 변수로 둔다 (opacity-(--state-disabled-opacity))
  const root = [
    `  --state-disabled-opacity: ${resolve("semantic.state.disabled-opacity")};`,
    `  --focus-width: ${resolve("component.focus.width")};`,
    `  --focus-offset: ${resolve("component.focus.offset")};`,
    `  --motion-expand: ${resolve("semantic.motion.expand")};`,
    `  --motion-easing: ${resolve("semantic.motion.easing")};`,
    // 패널 제목 왼쪽 '캐릭터 집'도 광고 관리자 위 캐릭터와 같은 값으로 그린다
    ...Object.keys(tokens.component.character).filter((k) => !k.startsWith("$"))
      .map((k) => `  --character-${k}: ${resolve(`component.character.${k}`)};`),
  ];
  return (
    HEADER("확장 프로그램 Tailwind 테마 (색·글자·움직임).") +
    `@theme {\n${lines.join("\n")}\n}\n\n:root {\n${root.join("\n")}\n}\n`
  );
}

// ── 3. 오버레이: shadow root 안이라 Tailwind 없이 :host 변수로 넣는다 ──
function buildOverlay() {
  const vars = [];
  for (const name of ["coach", "character"]) {
    for (const [k, v] of Object.entries(tokens.component[name])) {
      if (k.startsWith("$")) continue;
      vars.push(`  --${name}-${k}: ${resolve(`component.${name}.${k}`)};`);
    }
  }
  return HEADER("광고 관리자 위 오버레이 변수.") + `:host {\n${vars.join("\n")}\n}\n`;
}

// ── 대비 검사 (WCAG 2.x 상대 휘도) ──
function luminance(hex) {
  const n = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255);
  const lin = (c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}
function ratio(a, b) {
  const [l1, l2] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

// [앞, 뒤, 종류(text 4.5 / ui 3), 쓰는 곳]
const PAIRS = [
  ["semantic.tone.ink", "semantic.tone.bg", "text", "본문 (페이지 바탕)"],
  ["semantic.tone.ink", "semantic.tone.surface", "text", "본문 (카드)"],
  ["semantic.tone.ink-soft", "semantic.tone.surface", "text", "보조 글자 (카드)"],
  ["semantic.tone.ink-soft", "semantic.tone.surface-sunk", "text", "보조 글자 (눌린 칸)"],
  ["semantic.tone.accent-ink", "semantic.tone.surface", "text", "메인 글자·링크"],
  ["semantic.tone.accent-ink", "semantic.tone.accent-soft", "text", "연한 바탕 위 메인 글자"],
  ["semantic.tone.ink", "semantic.tone.accent-soft", "text", "말풍선 본문"],
  ["semantic.tone.on-action", "semantic.tone.action", "text", "주 버튼 글자"],
  ["semantic.tone.on-action", "semantic.tone.action-hover", "text", "주 버튼 글자 (눌림)"],
  ["semantic.tone.adopt", "semantic.tone.adopt-bg", "text", "확실 배지"],
  ["semantic.tone.likely", "semantic.tone.likely-bg", "text", "유력 배지"],
  ["semantic.tone.hold", "semantic.tone.hold-bg", "text", "보류 배지"],
  ["semantic.tone.warn", "semantic.tone.warn-bg", "text", "▲ 주의 글자"],
  ["semantic.tone.block-ink", "semantic.tone.block-bg", "text", "■ 차단 상자 글자"],
  ["semantic.tone.block", "semantic.tone.surface", "text", "■ 차단 오류 한 줄 (흰 바탕)"],
  ["semantic.tone.ink", "semantic.tone.info-bg", "text", "● 참고 상자 글자"],
  ["semantic.tone.ink", "semantic.tone.ok-bg", "text", "✓ 정상 상자 글자"],
  ["semantic.tone.on-meta", "semantic.tone.block", "text", "■ 모양 안 ✕"],
  ["semantic.tone.on-meta", "semantic.tone.info", "text", "● 모양 안 i"],
  ["semantic.tone.block", "semantic.tone.block-bg", "ui", "■ 차단 모양 (연한 바탕)"],
  ["semantic.tone.info", "semantic.tone.info-bg", "ui", "● 참고 모양 (연한 바탕)"],
  ["semantic.tone.ok", "semantic.tone.ok-bg", "ui", "✓ 정상 모양 (연한 바탕)"],
  ["semantic.tone.on-meta", "semantic.tone.ok", "ui", "✓ 모양 안 체크"],
  ["semantic.tone.on-meta", "semantic.tone.warn-mark", "ui", "▲ 모양 안 !"],
  ["component.coach.note-fg", "component.coach.bubble-bg", "text", "오버레이 안내 글자"],
  ["component.coach.button-fg", "component.coach.button-bg", "text", "오버레이 보조 버튼"],
  ["component.coach.primary-fg", "component.coach.primary-bg", "text", "오버레이 주 버튼"],
  ["semantic.tone.on-accent", "semantic.tone.accent", "text", "메인 바탕 위 흰 글자"],
  ["semantic.tone.on-accent", "semantic.tone.accent-ink", "text", "메인 진하게 위 흰 글자"],
  ["semantic.tone.hold", "semantic.tone.surface", "text", "보류 글자 (흰 바탕)"],
  ["semantic.tone.accent", "semantic.tone.surface", "ui", "초점 링·현재 단계 테두리"],
  ["component.coach.ring", "semantic.tone.on-meta", "ui", "메타 화면 위 칸 테두리"],
  ["semantic.tone.warn-mark", "semantic.tone.surface", "ui", "▲ 주의 모양"],
  ["semantic.tone.series-a", "semantic.tone.surface", "ui", "차트 비교 막대"],
];

function contrast() {
  return PAIRS.map(([fg, bg, kind, use]) => {
    const f = resolve(fg);
    const b = resolve(bg);
    const r = ratio(f, b);
    const need = kind === "text" ? 4.5 : 3;
    return { fg, bg, f, b, kind, use, r, ok: r >= need, need };
  });
}

// ── 실행 ──
const outputs = [
  ["web/src/tokens.css", buildWeb()],
  ["extension/assets/tokens.css", buildExtensionTheme()],
  ["extension/assets/overlay-tokens.css", buildOverlay()],
];

let failed = false;
for (const [rel, text] of outputs) {
  const file = path.join(ROOT, rel);
  const old = fs.existsSync(file) ? fs.readFileSync(file, "utf8") : null;
  if (args.has("--check")) {
    if (old !== text) {
      console.error(`✗ ${rel} 가 원천과 다릅니다. node design-system/build.cjs 를 돌리세요.`);
      failed = true;
    } else console.log(`✓ ${rel}`);
  } else if (old !== text) {
    fs.writeFileSync(file, text);
    console.log(`썼음: ${rel}`);
  } else console.log(`같음: ${rel}`);
}

const results = contrast();
if (args.has("--contrast")) {
  console.log("\n| 쓰는 곳 | 글자/모양 | 바탕 | 대비 | 기준 | 결과 |\n|---|---|---|---|---|---|");
  for (const x of results)
    console.log(`| ${x.use} | ${x.f} | ${x.b} | ${x.r.toFixed(2)}:1 | ${x.need}:1 | ${x.ok ? "통과" : "미달"} |`);
}
const bad = results.filter((x) => !x.ok);
for (const x of bad) console.error(`✗ 대비 미달: ${x.use} ${x.f} / ${x.b} = ${x.r.toFixed(2)}:1 (기준 ${x.need}:1)`);
if (!bad.length) console.log(`대비 검사 ${results.length}쌍 모두 통과`);
process.exit(failed || bad.length ? 1 : 0);
