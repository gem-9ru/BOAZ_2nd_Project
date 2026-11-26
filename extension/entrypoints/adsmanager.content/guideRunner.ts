// 안내 진행 (DOM만 다루고 그리기는 Character.tsx). 테스트할 수 있게 화면 그리기와 나눴다.
import type { GuideStepItem } from "../../lib/guide";
import { checkLocation, moneyProblems, setAgeGender, setEndDate, setLifetimeBudget, setStartDate, useAdsetBudget, type Pace, currentAdsetId } from "./actions";
import { shownDates, type Level, type MoneyKind } from "../../lib/guide";
import { currentLevel, goToLevel, hasValue, openDialog, isChecked, isChoice, isKorean, isPublishLike, isTextField, locateWith, mainScroller, typeInto } from "./locate";

export const MAX_TRIES = 3;
const MONEY = new Set<string>(["campaignBudget", "lifetimeBudget", "moneyCheck"]);
/** 돈 칸을 대신 못 했을 때 말풍선 (moneyCheck는 무엇이 다른지 하나씩) */
const MONEY_FAIL: Record<MoneyKind, string> = {
  campaignBudget: "'예산 전략'을 '광고 세트 예산'으로 바꾸고 '예산 일부를 다른 광고 세트와 공유하기'를 끄지 못했어요 → 캠페인 화면 '예산'에서 직접 맞춰 주세요",
  lifetimeBudget: "총예산을 넣지 못했어요 → '예산 및 일정'에서 종류를 '총예산'으로 고르고 금액을 직접 넣어 주세요",
  moneyCheck: "돈 설정을 확인하지 못했어요",
};
const LANGUAGE_TEXT = "화면 언어를 한국어로 바꿔 주세요. (메뉴 › 설정 › 언어) 바꾼 뒤 '다음 칸'을 눌러 주세요.";

export interface GuideView {
  index: number;
  total: number;
  found: boolean;
  text: string;
  copy?: string;
  image?: string;
  target?: HTMLElement;
  publish?: boolean;
  /** 진짜 칸이 아니라 그 칸으로 가는 준비 안내("'+ 만들기'를 누르세요")를 짚는 중 */
  hint?: boolean;
  /** 자동 진행 중인지 */
  auto?: boolean;
  /** 자동 진행이 멈춰 기다리는 이유: owner = 사장님이 직접 맞출 칸, publish = 게시는 직접 */
  waiting?: "owner" | "publish";
  /** 사장님 차례 (직접 할 칸·사장님 단계·뭉치가 못 해서 넘긴 칸): 말풍선 맨 위에 '직접 눌러 주세요' */
  owner?: boolean;
}

// 사장님이 눈으로 따라올 수 있게 천천히 (2026-11-25 요청): 뭉치가 걸어가 가리키고, 말풍선을 읽을 시간을 둔다
const PACE = 1 / 1.5;     // 기다리는 시간 배율 (2026-11-25 사장님 요청으로 1.5배 빠르게)
const ACT_GAP = Math.round(3800 * PACE);    // 한 번 대신 한 뒤 다음 동작까지
const HINT_GAP = Math.round(4500 * PACE);   // 창을 넘긴 뒤
const SCAN_GAP = Math.round(1500 * PACE);   // 스크롤 한 번 뒤
const LOOK_FIRST = Math.round(2200 * PACE); // 칸을 찾으면 바로 하지 않고 가리킨 채 잠깐 보여 준다
const SURVEY_LEVEL_WAIT = Math.round(1500 * PACE);  // 둘러보기: 화면을 바꾼 뒤 그려질 때까지
const SURVEY_SCROLL_WAIT = Math.round(700 * PACE);  // 둘러보기: 한 번 내린 뒤
// 하위 단계(사진 고르기 등): 칸 하나 안에서 버튼 → 메뉴 → 창이 차례로 늦게 뜬다
const STAGE_LOOK = Math.round(1200 * PACE);   // 하위 단계 버튼을 가리킨 뒤 누르기까지 (첫 칸보다 짧게)
const STAGE_PRESS_WAIT = Math.round(4500 * PACE);   // 누른 뒤 다음 요소가 뜰 때까지 기다리는 시간 (그 전엔 다시 누르지 않음)
const ARRIVE_LOOK = Math.round(600 * PACE);    // 뭉치가 칸에 도착해 가리킨 뒤 누르거나 넣기까지
const ARRIVE_TIMEOUT = Math.round(9000 * PACE);   // 뭉치가 끝내 도착 신호를 못 보내면(칸이 화면 밖 등) 이만큼 뒤엔 그대로 진행
const ARRIVE_POLL = 250;   // 도착을 기다리는 동안 다시 보는 간격
/** 창 안 칸을 다 마친 뒤 창을 닫는 단추 ('완료'가 보이면 '완료', 아니면 '다음'으로 끝까지 넘긴다) */
const FINISH_DIALOG = [{ role: "button", text: "완료" }, { role: "button", text: "다음" }];
const FINISH_PRESSES = 6;   // 창 마무리 단추를 이만큼 눌러도 안 닫히면 사장님께
const STAGE_PRESSES = 2;   // 한 하위 단계 버튼을 누르는 최대 횟수
const STAGE_HOLD = 3;   // 뒤 단계 요소가 이만큼(확인 횟수) 연달아 안 보여야 정말 사라진 것으로 본다 (다시 그리는 중엔 그대로)

export class Guide {
  private tries = 0;
  private target: HTMLElement | null = null;
  private matched = 0;   // 찾은 방법의 순서 (0보다 크면 더 앞의 진짜 칸이 나타나는지 계속 본다)
  private languageOk: boolean;
  private detach: (() => void) | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private auto = false;
  private waiting: GuideView["waiting"];
  private nextAt = 0;
  private scan = { wrapped: false, done: false };
  private busy = false;   // 복잡한 칸을 대신 맞추는 중 (여러 번 눌러야 해서 시간이 걸림)
  /** 칸 위치 지도: 칸 id → 어느 편집 화면의 어느 높이에 있었는지 (처음 편집 화면에 들어올 때 한 번 훑어 만든다) */
  private map: Record<string, { level: Level; scrollTop: number }> = {};
  private surveyed = false;
  /** 끝까지 훑어 본 편집 화면. 여기서 못 찾은 칸은 접힌 구역 안에 있다 (예: 연령은 '타겟 추천' › '설정 표시' 안) */
  private surveyedLevels = new Set<Level>();
  private surveying: string | null = null;
  private jumped = -1;   // 지도로 점프한 단계 (한 단계에 한 번만)
  private shown = -1;   // 이 단계 칸을 이미 가리켜 보여 줬는지
  private hintPresses = 0;   // 이 단계에서 자동으로 누른 준비 버튼 수 (끝없이 누르지 않게)
  /** 찾는 칸이 열린 창 뒤에 가려져 있음 (창을 먼저 마쳐야 함) */
  private behindDialog = false;
  /** 돈 확인을 통과한 광고 세트 id (다음 테스트의 두 세트가 같은 세트를 두 번 읽지 않게) */
  private checkedSets: string[] = [];
  private dialogWait = false;   // 칸이 창 뒤라서 기다리는 중 (창이 닫히면 저절로 풀린다)
  /** 창 밖 칸(웹사이트 URL)인데 창이 열려 있음 → 뭉치가 누를 창 마무리 단추('다음'·'완료') */
  private finishBtn: HTMLElement | null = null;
  private finishPresses = 0;
  /** 뭉치(화면 캐릭터)를 따라가는지: 켜면 뭉치가 칸에 도착한 뒤에만 누르고 넣는다 */
  private buddy = false;
  private arrivedAt: HTMLElement | null = null;
  private arrivedTime = 0;
  private waitFor: HTMLElement | null = null;   // 도착을 기다리기 시작한 칸
  private waitSince = 0;
  /** 뭉치가 넣는 칸인데 준비 버튼을 눌러도 칸이 안 생겨 사장님을 기다리는 중 (진짜 칸이 나타나면 이어서 넣는다) */
  private hintWait = false;
  /** 그때 사장님이 [다 했어요]를 누른 횟수 (첫 번째 = 준비를 마침 → 다시 찾기, 두 번째 = 이 칸은 넘어가기) */
  private hintDone = 0;
  /** 문구를 칸에 넣지 못해 복사해 두고 붙여넣기를 부탁하는 중 */
  private pasteAsk = false;
  /** 돈 칸: 화면에서 다시 읽었더니 다른 것 (있으면 다음 칸으로 가지 않는다) */
  private money: string | null = null;
  /** 하위 단계가 있는 칸: 지금 하위 단계(-1 = 아직), 안 보인 횟수, 가리켜 보여 준 단계, 사장님이 되돌아갔는지 */
  private stage = -1;
  private stageMiss = 0;
  private stageShown = -1;
  private stageBack = false;

  constructor(
    private doc: Document,
    private steps: GuideStepItem[],
    private index: number,
    private onProgress: (index: number) => void,
    private retryMs = 2000,
  ) {
    this.languageOk = isKorean(doc);
    this.seek();
  }

  view(): GuideView {
    const item = this.steps[this.index];
    const ownerTurn = Boolean(item && !item.entry.publish && this.languageOk
      && (item.entry.auto === "owner" || this.waiting === "owner" || (item.entry.stages && item.entry.stages[this.stage]?.by === "owner")));
    const v = { ...this.baseView(), ...(ownerTurn ? { owner: true } : {}) };
    if (this.money && this.waiting === "owner") return { ...v, auto: this.auto, waiting: this.waiting,
      text: `▲ 돈 확인: ${this.money}. 고친 뒤 '다 했어요'를 누르면 다시 확인할게요 (맞을 때만 넘어가요).` };
    if (this.pasteAsk && this.waiting === "owner") return { ...v, auto: this.auto, waiting: this.waiting,
      text: "문구를 칸에 넣지 못했어요. 복사해 두었으니 칸을 누르고 붙여 넣어(⌘V) 주세요. 다 했으면 '다 했어요'." };
    if (this.behindDialog) return { ...v, auto: this.auto, waiting: this.waiting,
      text: this.finishBtn && this.auto && this.waiting !== "owner"
        ? "창 안 칸은 다 넣었어요. 창 오른쪽 아래 '다음'으로 끝까지 넘기고 '완료'로 창을 닫을게요. 창이 닫히면 다음 칸을 짚을게요."
        : "열린 창 안의 남은 단계는 그대로 두고 오른쪽 아래 '다음'으로 끝까지 넘긴 뒤 '완료'를 눌러 창을 닫아 주세요. 창이 닫히면 이 칸을 짚을게요." };
    if (this.surveying) return { ...v, found: false, target: undefined, auto: this.auto, text: `화면을 먼저 둘러보고 칸 위치를 적어 둘게요 (${this.surveying})` };
    return { ...v, auto: this.auto, waiting: this.waiting,
      text: this.waiting === "owner" ? `${v.text} 다 맞췄으면 '다 했어요'를 누르세요.`
        : this.waiting === "publish" ? "여기까지 왔어요. 게시는 내용을 확인하고 사장님이 직접 눌러 주세요." : v.text };
  }

  setAuto(on: boolean): void {
    this.auto = on;
    if (on) { this.waiting = this.waiting === "owner" ? "owner" : undefined; this.nextAt = 0; }
  }

  /** 뭉치를 따라간다: 이후 자동 진행은 뭉치가 칸에 도착한 뒤에 누르거나 넣는다 (콘텐츠 스크립트가 켠다). */
  followBuddy(): void {
    this.buddy = true;
  }

  /** 뭉치가 el 옆에 도착해 가리킴 (el = null: 다시 걷기 시작). now = ms (autoStep과 같은 시계) */
  arrived(el: HTMLElement | null, now: number): void {
    this.arrivedAt = el;
    this.arrivedTime = now;
  }

  /** 지금 칸(el)에 뭉치가 도착해 잠깐 가리켰는지. 뭉치를 안 따라가면 늘 true.
   *  도착 신호가 끝내 안 오면(칸이 화면 밖 등) ARRIVE_TIMEOUT 뒤엔 true로 멈추지 않게 한다. */
  private atTarget(el: HTMLElement, now: number): boolean {
    if (!this.buddy) return true;
    if (this.arrivedAt === el && now - this.arrivedTime >= ARRIVE_LOOK) return true;
    if (this.waitFor !== el) { this.waitFor = el; this.waitSince = now; }
    return now - this.waitSince >= ARRIVE_TIMEOUT;
  }

  /** 자동 진행 한 걸음 (콘텐츠 스크립트가 tick 뒤에 부른다). now = ms */
  autoStep(now: number): void {
    // 준비 단계에서 기다리다가 진짜 칸이 나타났다 → 사장님 [다 했어요] 없이 이어서 넣는다
    if (this.hintWait && this.waiting === "owner" && this.target && !this.steps[this.index]?.entry.find[this.matched]?.say) {
      this.hintWait = false;
      this.waiting = undefined;
      this.shown = -1;
    }
    if (!this.auto || this.waiting || this.busy || now < this.nextAt || !this.languageOk) return;
    const item = this.steps[this.index];
    if (!item) { this.auto = false; return; }
    const kind = item.entry.publish ? "stop" : (item.entry.auto ?? "owner");
    if (kind === "stop") { this.waiting = "publish"; this.auto = false; return; }
    if (item.entry.stages) return this.autoStage(now);
    const dialog = openDialog(this.doc);
    if (dialog && this.behindDialog) {
      // 창 밖 칸(웹사이트 URL): 창 안 칸은 이미 마쳤다 → 뭉치가 '다음'으로 끝까지 넘기고 '완료'로 창을 닫는다
      const btn = this.finishBtn;
      if (btn && !isPublishLike(btn) && this.finishPresses < FINISH_PRESSES) {
        if (!this.atTarget(btn, now)) { this.nextAt = now + ARRIVE_POLL; return; }
        this.finishPresses += 1;
        btn.click();
        this.nextAt = now + HINT_GAP;
        this.recheck();
        return;
      }
      this.waiting = "owner"; this.dialogWait = true; return;   // 칸이 창 뒤 → 창을 마칠 때까지 기다림
    }
    const hint = this.target ? Boolean(item.entry.find[this.matched]?.say) : false;
    if (this.target && !hint) {
      if (kind === "owner") { this.waiting = "owner"; return; }
      if (this.shown !== this.index) { this.shown = this.index; this.nextAt = now + LOOK_FIRST; return; }   // 먼저 가리켜 보여 주고
      if (!this.atTarget(this.target, now)) { this.nextAt = now + ARRIVE_POLL; return; }   // 뭉치가 도착한 뒤에 넣는다
      this.apply();
      this.nextAt = now + ACT_GAP;
      return;
    }
    // 진짜 칸이 아직 없다 → 다른 편집 화면에 있는 칸이면 그 화면으로, 아니면 끝까지 내려 보며 찾고, 그래도 없으면 준비 안내(만들기·계속·다음)를 누른다
    if (this.walkToField(now, dialog)) return;
    if (this.target && hint) {
      if (isPublishLike(this.target)) { this.waiting = "publish"; this.auto = false; return; }
      // 사장님이 직접 할 칸(사진 등)은 준비 버튼을 한 번만 열어 주고 기다린다. 어떤 칸이든 3번 눌러도 그대로면 멈춘다.
      if ((kind === "owner" && this.hintPresses >= 1) || this.hintPresses >= 3) { this.waiting = "owner"; this.hintWait = kind !== "owner"; return; }
      if (!this.atTarget(this.target, now)) { this.nextAt = now + ARRIVE_POLL; return; }   // 뭉치가 도착한 뒤에 누른다
      this.hintPresses += 1;
      this.apply();
      this.scan = { wrapped: false, done: false };
      this.nextAt = now + HINT_GAP;
      return;
    }
    this.waiting = "owner";   // 화면 어디에도 없다 → 대신 그림과 함께 사장님을 기다린다
  }

  /** 칸이 화면에 아직 없을 때 한 걸음: 처음이면 세 화면을 훑어 지도 만들기 → 다른 편집 화면으로 → 지도 높이로 점프 → 내려 보며 찾기.
   *  한 걸음 했으면 true (다음 걸음 시각도 정함), 더 할 게 없으면 false. */
  private walkToField(now: number, dialog: HTMLElement | null): boolean {
    if (!this.surveyed && !dialog && currentLevel(this.doc) !== "list") {
      // 편집 화면에 처음 들어왔다 → 세 화면을 훑어 칸 위치 지도를 만든다 (그동안 다른 동작은 쉼)
      this.busy = true;
      void this.survey().finally(() => { this.busy = false; this.nextAt = 0; });
      return true;
    }
    if (!dialog && this.ensureLevel()) { this.nextAt = now + HINT_GAP; return true; }
    if (!dialog && this.jumpFromMap()) { this.nextAt = now + SCAN_GAP; return true; }
    if (!dialog && this.foldedField()) return false;   // 훑어 봐도 없던 칸 + 여는 버튼이 보임 → 또 끝까지 내려 보지 않고 그 버튼부터
    if (!this.scan.done) { this.scanStep(); this.nextAt = now + SCAN_GAP; return true; }
    return false;
  }

  /** 이 화면을 끝까지 훑었는데도 칸이 지도에 없고, 지금 여는 버튼(힌트)이 보이면 true: 칸이 접힌 구역 안에 있다 */
  private foldedField(): boolean {
    const item = this.steps[this.index];
    const level = item?.entry.level;
    if (!item || !level || !this.surveyedLevels.has(level) || this.map[item.entry.id] || currentLevel(this.doc) !== level) return false;
    return Boolean(this.target && item.entry.find[this.matched]?.say);
  }

  /** 칸이 다른 편집 화면(캠페인·광고 세트·광고)에 있으면 왼쪽 목록으로 그 화면에 간다. 갔으면 true.
   *  캠페인 목록(아직 초안이 없음)에서는 넘나들 수 없어 '만들기·계속' 안내를 따른다. */
  private ensureLevel(): boolean {
    const want = this.steps[this.index]?.entry.level;
    const now = currentLevel(this.doc);
    if (!want || want === "list" || now === "list" || now === want) return false;
    if (!goToLevel(this.doc, want)) return false;
    this.scan = { wrapped: false, done: false };
    const mainSc = mainScroller(this.doc);
    if (mainSc) mainSc.scrollTop = 0;
    this.recheck();
    return true;
  }

  /** 지도 없이 바로 시작 (이미 둘러봤거나, 테스트) */
  skipSurvey(): void {
    this.surveyed = true;
  }

  /** 지도에 이 칸의 높이가 있으면 그 높이로 바로 점프 (한 단계에 한 번). */
  private jumpFromMap(): boolean {
    const item = this.steps[this.index];
    const spot = item && this.map[item.entry.id];
    const sc = mainScroller(this.doc);
    if (!spot || !sc || this.jumped === this.index || spot.level !== currentLevel(this.doc)) return false;
    this.jumped = this.index;
    sc.scrollTop = spot.scrollTop;
    sc.dispatchEvent(new Event("scroll"));
    this.recheck();
    return true;
  }

  /** 칸 위치 지도 만들기: 캠페인 → 광고 세트 → 광고 화면을 차례로 열고 끝까지 내려 보며, 이 안내의 칸이 처음 보인 높이를 적는다.
   *  다 훑고 나면 원래 화면으로 돌아간다. 눌러야만 생기는 창(크리에이티브 설정 등) 안의 칸은 지도에 없고, 그 자리에서 찾는다. */
  async survey(pace: Pace = { wait: (ms) => new Promise((r) => setTimeout(r, ms)) }): Promise<Record<string, { level: Level; scrollTop: number }>> {
    this.surveyed = true;
    const start = currentLevel(this.doc);
    if (start === "list") return this.map;
    const NAMES: Record<string, string> = { campaign: "캠페인", adset: "광고 세트", ad: "광고" };
    for (const level of ["campaign", "adset", "ad"] as const) {
      const items = this.steps.filter((s) => s.entry.level === level && !s.entry.publish);
      if (!items.length || !goToLevel(this.doc, level)) continue;
      this.surveyedLevels.add(level);
      this.surveying = NAMES[level]!;
      await pace.wait(SURVEY_LEVEL_WAIT);
      const sc = mainScroller(this.doc);
      const look = (top: number) => {
        for (const s of items) {
          if (this.map[s.entry.id]) continue;
          const real = s.entry.stages?.[0]?.find ?? s.entry.find.filter((f) => !f.say);
          if (real.length && locateWith(this.doc, real)) this.map[s.entry.id] = { level, scrollTop: top };
        }
      };
      look(0);
      if (sc) {
        for (let y = 0; y < sc.scrollHeight; y += Math.round(sc.clientHeight * 0.6)) {
          sc.scrollTop = y;
          sc.dispatchEvent(new Event("scroll"));
          await pace.wait(SURVEY_SCROLL_WAIT);
          look(sc.scrollTop);
          if (sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 4) break;
        }
        sc.scrollTop = 0;
      }
    }
    this.surveying = null;
    if (start !== currentLevel(this.doc)) goToLevel(this.doc, start);
    this.recheck();
    return this.map;
  }

  /** 편집 화면을 한 화면의 60%씩 내려 본다. 끝에 닿으면 맨 위로 한 번 돌아가 훑고, 두 번째 끝에서 멈춘다. */
  private scanStep(): void {
    const dialog = openDialog(this.doc);
    const sc = dialog ? (mainScroller(this.doc, dialog) ?? null) : mainScroller(this.doc);
    if (!sc) { this.scan.done = true; return; }
    const atEnd = sc.scrollTop + sc.clientHeight >= sc.scrollHeight - 4;
    if (atEnd) {
      if (this.scan.wrapped) { this.scan.done = true; return; }
      this.scan.wrapped = true;
      sc.scrollTop = 0;
    } else {
      sc.scrollTop = Math.min(sc.scrollHeight - sc.clientHeight, sc.scrollTop + Math.round(sc.clientHeight * 0.6));
    }
    this.recheck();
  }

  private baseView(): GuideView {
    const total = this.steps.length;
    const item = this.steps[this.index];
    if (!item) return { index: this.index, total, found: false, text: "안내를 모두 마쳤어요." };
    if (!this.languageOk) return { index: this.index, total, found: false, text: LANGUAGE_TEXT };
    const stages = item.entry.stages;
    if (stages && this.stage >= 0) {
      const st = stages[this.stage]!;
      const say = (this.target ? st.find[this.matched]?.say : undefined) ?? st.say;
      const text = `${this.stage + 1}/${stages.length} · ${say.replace("{value}", shownDates(item.value ?? "")).replace(" ()", "")}`;
      return { index: this.index, total, found: Boolean(this.target), target: this.target ?? undefined, hint: st.by === "buddy", text };
    }
    if (this.target) {
      const hint = item.entry.find[this.matched]?.say;
      return { index: this.index, total, found: true, target: this.target, publish: item.entry.publish, hint: Boolean(hint),
               text: (hint ?? item.entry.say).replace("{value}", shownDates(item.value ?? "")), copy: hint ? undefined : item.value };
    }
    if (this.tries >= MAX_TRIES) {
      return { index: this.index, total, found: false, text: item.entry.fallback.text, image: item.entry.fallback.image, copy: item.value };
    }
    return { index: this.index, total, found: false, text: "칸을 찾는 중이에요…" };
  }

  /** [다음 칸]: 언어를 바꿨거나, 못 찾은 칸을 직접 채웠거나, 수동 단계를 마침. 게시 버튼은 절대 누르지 않는다. */
  markDone(): void {
    if (!this.languageOk) {
      this.languageOk = true;
      this.seek();
      return;
    }
    this.advance();
  }

  /** [다음 칸]: 지금 칸을 페이지에서 대신 해 준다. 게시 버튼은 어떤 경우에도 누르지 않는다.
   *  - 준비 안내('+ 만들기', '계속')면 그 버튼을 누르고, 같은 단계에서 진짜 칸을 다시 찾는다
   *  - 고르는 칸이면 고르고, 글자 칸이면 값을 넣고 다음 단계로
   *  - 그 밖(날짜·지역처럼 복잡한 칸, 못 찾은 칸)은 사장님이 한 것으로 보고 다음 단계로 */
  apply(): void {
    const item = this.steps[this.index];
    const el = this.target;
    if (this.behindDialog) {
      // 칸이 아직 창 뒤: [다 했어요]로 건너뛰지 않는다. 사장님이 창 안을 고쳤을 수 있으니 창 마무리([다음]·[완료])를 처음부터 다시 해 본다
      this.finishPresses = 0;
      this.dialogWait = false;
      if (this.waiting === "owner") this.waiting = undefined;
      this.nextAt = 0;
      this.seek();
      return;
    }
    // 돈 칸: [다 했어요]·[다음 칸]도 화면에서 다시 읽어 맞을 때만 넘어간다 (칸이 다른 편집 화면이면 먼저 그 화면으로)
    if (this.languageOk && item && MONEY.has(item.entry.auto ?? "")) {
      if (!el && this.ensureLevel()) return;
      return this.checkMoney(item.entry.auto as MoneyKind, item.value ?? "");
    }
    const ownerDone = this.waiting === "owner";   // [다 했어요]: 사장님이 직접 맞췄다 → 다시 하지 않고 다음 칸
    this.waiting = undefined;
    if (this.languageOk && item?.entry.publish) return this.advance();   // [게시했어요]: 사장님이 직접 게시했다 → 다음 (게시 버튼은 누르지 않음)
    if (this.languageOk && item?.entry.stages) {
      if (!el && this.ensureLevel()) return;
      const st = item.entry.stages[this.stage];
      if (ownerDone || !el || !st || st.by === "owner") return this.advance();   // 사장님 차례(사진)에서 누르면 = 다 했어요
      if (isPublishLike(el)) return;
      this.hintPresses += 1;
      el.click();
      this.timer = setTimeout(() => this.recheck(), 600);
      return;
    }
    if (this.languageOk && item && (!el || item.entry.find[this.matched]?.say) && this.ensureLevel()) return;   // 다른 화면의 칸 → 그 화면으로
    if (!this.languageOk || !item || !el) return this.markDone();
    if (item.entry.publish || isPublishLike(el)) return;   // 게시는 사장님이 직접
    const hint = Boolean(item.entry.find[this.matched]?.say);
    // 뭉치가 넣는 칸의 준비 단계에서 [다 했어요] = 준비를 마쳤다 → 칸을 건너뛰지 않고 다시 찾아 넣는다 (두 번째 누르면 넘어감)
    if (ownerDone && this.hintWait && this.hintDone < 1) {
      this.hintDone += 1;
      this.hintPresses = 0;
      this.nextAt = 0;
      this.recheck();
      return;
    }
    if (ownerDone) return this.advance();
    if (hint) {
      // 이미 고른 준비 선택지('수동 트래픽 캠페인' ✓)면 그 뒤의 준비 버튼('계속')을 누른다
      if (isChoice(el) && isChecked(el)) {
        const later = locateWith(openDialog(this.doc) ?? this.doc, item.entry.find.slice(this.matched + 1).filter((f) => f.say));
        if (later && !isPublishLike(later.el)) later.el.click();
        this.timer = setTimeout(() => this.recheck(), 600);
        return;
      }
      el.click();
      this.timer = setTimeout(() => this.recheck(), 600);
      return;
    }
    // 값이 바뀌면 seek()의 change 리스너가 이미 넘겼을 수 있다 → 아직 같은 단계일 때만 넘긴다
    const at = this.index;
    const next = () => { if (this.index === at) this.advance(); };
    const kind = item.entry.auto;
    if (kind === "skip" || kind === "owner") return next();   // 그대로 두는 칸 / 사장님이 맞춘 칸
    if (kind === "startDate" || kind === "endDate" || kind === "ageGender" || kind === "location") {
      // 여러 번 눌러야 하는 칸: 끝나면 다음, 못 하면 사장님께 (자동 진행은 기다림)
      const value = item.value ?? "";
      const run = kind === "startDate" ? setStartDate(this.doc, value)
        : kind === "endDate" ? setEndDate(this.doc, value)
        : kind === "ageGender" ? setAgeGender(this.doc, value)
        : Promise.resolve(checkLocation(this.doc, value));
      this.busy = true;
      void run.then((ok) => {
        this.busy = false;
        if (ok) next();
        else if (this.index === at) this.waiting = "owner";
      }, () => { this.busy = false; this.waiting = "owner"; });
      return;
    }
    if (isChoice(el)) {
      if (item.entry.doneWhen) {
        // 끝 신호가 따로 있는 칸(캠페인 만들기 창): 고른 뒤 넘어가지 않고 창의 다음 준비 버튼('계속')을 누른다 → 끝 신호가 보이면 다음 칸
        if (!isChecked(el)) el.click();
        else {
          const later = locateWith(openDialog(this.doc) ?? this.doc, item.entry.find.slice(this.matched + 1).filter((f) => f.say));
          if (later && !isPublishLike(later.el)) later.el.click();
        }
        this.timer = setTimeout(() => this.recheck(), 600);
        return;
      }
      if (!isChecked(el)) el.click();
      return next();
    }
    if (isTextField(el) && item.value) {
      // 넣은 뒤 정말 들어갔는지 확인하고 넘어간다. 안 들어갔으면 복사해 두고 붙여넣기를 부탁한다.
      const value = item.value;
      typeInto(el, value);
      this.busy = true;
      setTimeout(() => {
        this.busy = false;
        if (this.index !== at) return;
        if (hasValue(el, value)) return next();
        this.pasteAsk = true;
        this.waiting = "owner";
        void navigator.clipboard?.writeText(value).catch(() => {});
      }, 700);
      return;
    }
    next();
  }

  /** 돈 칸 대신 하기 + 다시 읽기. 맞으면 다음 칸, 아니면 무엇이 다른지 말풍선에 두고 사장님을 기다린다. */
  private checkMoney(kind: MoneyKind, value: string): void {
    if (this.busy) return;
    const at = this.index;
    this.busy = true;
    this.waiting = undefined;
    const set = kind === "moneyCheck" ? currentAdsetId(this.doc) : null;
    const run: Promise<string[]> = kind === "moneyCheck" && set && this.checkedSets.includes(set)
      ? Promise.resolve(["아까 확인한 세트예요 → 복제한 다른 세트('그대로' 세트)를 열고 '다 했어요'를 눌러 주세요"])
      : kind === "moneyCheck" ? moneyProblems(this.doc, value)
      : (kind === "campaignBudget" ? useAdsetBudget(this.doc) : setLifetimeBudget(this.doc, value)).then((ok) => (ok ? [] : [MONEY_FAIL[kind]]));
    void run.then((problems) => {
      this.busy = false;
      if (this.index !== at) return;
      if (!problems.length) { if (set) this.checkedSets.push(set); this.money = null; return this.advance(); }
      this.money = problems.join(" · ");
      this.waiting = "owner";
    }, () => { this.busy = false; if (this.index === at) { this.money = MONEY_FAIL[kind]; this.waiting = "owner"; } });
  }

  /** 준비 안내대로 눌렀으니 진짜 칸을 바로 다시 찾는다 (단계는 넘기지 않음). */
  recheck(): void {
    const tries = this.tries;
    this.seek();
    this.tries = tries;
  }

  /** 못 찾았을 때 다시 찾기 (콘텐츠 스크립트는 retryMs마다 부르고, 테스트는 직접 부른다). */
  retryNow(): void {
    if (this.target || !this.steps[this.index]) return;
    this.tries += 1;
    this.seek();
  }

  /** 화면이 바뀌었을 수 있으니 다시 본다: 아직 못 찾았거나, 찾았던 칸이 다시 그려져 사라졌으면 다시 찾는다. */
  tick(): void {
    if (!this.steps[this.index] || !this.languageOk) return;
    const item = this.steps[this.index]!;
    if (item.entry.stages) return this.seekStage();
    const better = this.matched > 0 && locateWith(openDialog(this.doc) ?? this.doc, item.entry.find.slice(0, this.matched)) !== null;
    if (!this.target || !this.target.isConnected || better || this.behindDialog || (openDialog(this.doc) && !openDialog(this.doc)!.contains(this.target))) {
      const tries = this.tries;
      this.seek();
      this.tries = tries;
    }
  }

  stop(): void {
    this.detach?.();
    if (this.timer) clearTimeout(this.timer);
  }

  /** [이전 칸]: 한 칸 뒤로 (첫 칸이면 그대로). */
  back(): void {
    if (this.index === 0) return;
    this.moveTo(this.index - 1);
    if (!this.ensureLevel()) this.seek();
  }

  private advance(): void {
    this.moveTo(this.index + 1);
    this.seek();
  }

  /** 다른 칸으로: 칸마다 새로 세는 값(스크롤·기다림·누른 횟수·하위 단계)을 모두 비운다 */
  private moveTo(index: number): void {
    this.stop();
    this.scan = { wrapped: false, done: false };
    this.waiting = undefined;
    this.hintPresses = 0;
    this.finishPresses = 0;
    this.dialogWait = false;
    this.pasteAsk = false;
    this.hintWait = false;
    this.hintDone = 0;
    this.money = null;
    this.resetStage();
    this.index = index;
    this.tries = 0;
    this.onProgress(this.index);
  }

  private seek(): void {
    this.detach?.();
    this.detach = null;
    const item = this.steps[this.index];
    if (item?.entry.stages && this.languageOk) {
      this.seekStage();
      if (!this.target && this.stage < 0 && this.retryMs > 0 && this.tries < MAX_TRIES) this.timer = setTimeout(() => this.retryNow(), this.retryMs);
      return;
    }
    // 끝 신호(doneWhen)가 보이면 이 칸은 끝 (예: 캠페인 만들기 창을 다 지나 '카테고리' 칸이 뜸)
    if (item?.entry.doneWhen && this.languageOk && locateWith(this.doc, item.entry.doneWhen)) return this.advance();
    const dialog = openDialog(this.doc);
    // 창 밖 칸(웹사이트 URL)은 창 안의 같은 칸에 넣지 않는다: 창 안에 넣은 값은 [완료] 뒤 광고 화면 칸에 남지 않았다 (2026-11-26 실제 화면)
    const hit = item && this.languageOk && !(dialog && item.entry.outsideDialog) ? locateWith(dialog ?? this.doc, item.entry.find) : null;
    // 창 안에 없고 창 밖(가려진 곳)에 진짜 칸이 있으면: 창을 먼저 마쳐야 한다
    // (창 안의 '다음' 같은 준비 버튼이 보여도, 진짜 칸이 창 뒤에 있으면 그 버튼을 누르지 않는다)
    const realInside = Boolean(hit && !item?.entry.find[hit.index]?.say);
    this.behindDialog = Boolean(item && dialog && !realInside
      && (item.entry.outsideDialog || locateWith(this.doc, item.entry.find.filter((f) => !f.say))));
    if (!this.behindDialog && this.dialogWait) {   // 창이 닫혔다 → 기다림을 풀고 자동 진행이 이 칸을 다시 짚는다
      this.dialogWait = false;
      if (this.waiting === "owner") this.waiting = undefined;
      this.nextAt = 0;
    }
    this.finishBtn = this.behindDialog && item?.entry.outsideDialog && dialog ? (locateWith(dialog, FINISH_DIALOG)?.el ?? null) : null;
    this.target = this.finishBtn ?? hit?.el ?? null;   // 창을 마무리할 땐 뭉치가 그 단추를 가리킨다
    this.matched = this.finishBtn ? 0 : (hit?.index ?? 0);
    const isHint = hit ? Boolean(item!.entry.find[hit.index]?.say) : false;
    if (this.target && !this.finishBtn && item && item.entry.done === "value" && !isHint) {
      const el = this.target;
      const onChange = () => this.advance();
      // 'change'는 입력을 마쳤을 때(칸을 떠나거나 고름) 한 번 온다. 글자 하나마다 오는 'input'으로 넘기지 않는다.
      el.addEventListener("change", onChange, { once: true });
      this.detach = () => el.removeEventListener("change", onChange);
    }
    if (!this.target && item && this.languageOk && this.retryMs > 0 && this.tries < MAX_TRIES) {
      this.timer = setTimeout(() => this.retryNow(), this.retryMs);
    }
  }

  // ── 하위 단계가 있는 칸 (사진 고르기 등) ──

  private resetStage(): void {
    this.stage = -1;
    this.stageMiss = 0;
    this.stageShown = -1;
    this.stageBack = false;
  }

  /** 지금 하위 단계 찾기: 화면에 나타난 가장 뒤 단계가 지금 단계 (앞 단계를 다시 찾아 왔다갔다하지 않음).
   *  끝 신호(doneWhen)가 보이면 바로 다음 칸. 뒤 단계 요소가 잠깐 사라지면(다시 그리는 중) STAGE_HOLD번까지는 그대로 둔다. */
  private seekStage(): void {
    const item = this.steps[this.index];
    const stages = item?.entry.stages;
    if (!item || !stages) return;
    this.behindDialog = false;
    const dialog = openDialog(this.doc);
    const root = dialog ?? this.doc;
    if (item.entry.doneWhen && locateWith(root, item.entry.doneWhen)) return this.advance();
    let found: { at: number; el: HTMLElement; matched: number } | null = null;
    for (let at = stages.length - 1; at >= 0 && !found; at -= 1) {
      const st = stages[at]!;
      if ((st.where === "dialog" && !dialog) || (st.where === "page" && dialog)) continue;
      const hit = locateWith(root, st.find);
      // 새 단계로는 그 단계의 첫 방법으로 찾았을 때만 들어간다: 메타 사진 창은 '다음'이 먼저 뜨고 '업로드'가 0.7초 뒤에 떠서,
      // '다음'으로 들어가면 뭉치가 '다음'에 갔다가 '업로드'로 다시 걸어간다
      if (hit && (at <= this.stage || hit.index === 0)) found = { at, el: hit.el, matched: hit.index };
    }
    if (found && found.at >= this.stage) {
      if (found.at > this.stage) this.enterStage(found.at);
      this.target = found.el;
      this.matched = found.matched;
      this.stageMiss = 0;
      return;
    }
    // 뒤 단계 요소가 안 보임: 잠깐은 기다리고(같은 곳을 가리킨 채), 그래도 없으면 받아들인다
    if (this.stage >= 0 && this.stageMiss < STAGE_HOLD) {
      this.stageMiss += 1;
      if (this.target && !this.target.isConnected) this.target = null;
      return;
    }
    if (!found) { this.target = null; return; }   // 단계는 그대로 두고, 다음 요소가 나타나길 기다린다
    // 정말 앞 단계로 돌아갔다 (사장님이 창을 닫음 등) → 뭉치는 더 누르지 않고 사장님을 기다린다
    this.stage = found.at;
    this.target = found.el;
    this.matched = found.matched;
    this.stageMiss = 0;
    this.stageBack = true;
    if (this.auto) this.waiting = "owner";
  }

  private enterStage(at: number): void {
    this.stage = at;
    this.stageShown = -1;
    this.hintPresses = 0;
    this.finishPresses = 0;
    this.dialogWait = false;
    this.nextAt = 0;   // 다음 요소가 떴다 → 앞 단계의 '누른 뒤 기다리기'는 끝, 바로 이어서
    // 사장님이 직접 다음 단계로 넘겼으면 기다림을 풀고 이어서 한다
    if (this.waiting === "owner" && !this.stageBack) this.waiting = undefined;
  }

  /** 자동 진행 한 걸음 (하위 단계 칸): 뭉치 단계는 가리키고 → 누르고 → 다음 요소가 뜰 때까지 기다림, 사장님 단계는 짚고 기다림. */
  private autoStage(now: number): void {
    const item = this.steps[this.index]!;
    const st = item.entry.stages![this.stage];
    if (!this.target || !st) {
      const dialog = openDialog(this.doc);
      if (this.stage >= 0) { this.nextAt = now + SCAN_GAP; return; }   // 단계 사이: 스크롤하지 않고 다음 요소를 기다린다
      if (this.walkToField(now, dialog)) return;
      this.waiting = "owner";
      return;
    }
    if (st.by === "owner" || this.stageBack) { this.waiting = "owner"; return; }
    if (isPublishLike(this.target)) { this.waiting = "publish"; this.auto = false; return; }
    if (this.stageShown !== this.stage) { this.stageShown = this.stage; this.nextAt = now + STAGE_LOOK; return; }   // 먼저 가리켜 보여 주고
    if (this.hintPresses >= STAGE_PRESSES) { this.waiting = "owner"; return; }   // 눌러도 다음 요소가 안 뜸 → 사장님께
    if (!this.atTarget(this.target, now)) { this.nextAt = now + ARRIVE_POLL; return; }   // 뭉치가 도착한 뒤에 누른다
    this.hintPresses += 1;
    this.target.click();
    this.nextAt = now + STAGE_PRESS_WAIT;   // 다음 요소가 늦게 떠도 그 전엔 다시 누르지 않는다
  }
}
