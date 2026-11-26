// 분석 페이지 옆의 광고 어시스턴트 (설계서 v4.2 AN-COM ④ · AN-FLOW).
// 분석 페이지는 크롬 탭에 펼쳐 두고, 오른쪽 사이드 패널(이 확장)이 그 페이지의 단계에 맞춰 설명한다.
// 분석 페이지는 주소 # 뒤에 지금 상태를 적는다: #s=세팅값키&code=AB12&step=AN-02&send=시각&budget=6000
// (# 뒤는 서버로 가지 않고, 코드 4자리는 결과를 찾는 열쇠일 뿐 개인 정보가 아니다.)
import { useEffect, useState } from "react";
import { ANALYSIS_PAGE } from "./api";

export interface AnalysisTab {
  tabId: number;
  /** 분석 결과 코드 (아직 파일을 안 올렸으면 null → AN-00 업로드 화면) */
  code: string | null;
  /** AN-01 ~ AN-06 */
  step: string | null;
  /** AN-06 [확장 프로그램으로 보내기]를 누른 시각 (바뀔 때마다 테스트안을 받는다) */
  send: string | null;
  /** ③ 준비하기에서 고른 세트당 총예산(원). 보내기 때 함께 적는다. 없으면 서버 계획의 per_set 그대로 */
  budget?: number | null;
}

/** 탭 주소가 분석 페이지면 # 뒤 상태를 읽는다. 아니면 null. */
export function parseAnalysisUrl(url: string | undefined, page = ANALYSIS_PAGE): Omit<AnalysisTab, "tabId"> | null {
  if (!url) return null;
  const [base, hash = ""] = url.split("#");
  const clean = (base ?? "").split("?")[0]!.replace(/\/+$/, "");
  const pages = [page.replace(/\/+$/, ""), ...LOCAL_PAGES];
  if (!pages.includes(clean)) return null;
  const q = new URLSearchParams(hash);
  const code = q.get("code");
  const step = q.get("step");
  const budget = Number(q.get("budget"));   // 숫자만, 1천 원 ~ 1천만 원 (주소는 사장님이 고칠 수 있어서 범위를 본다)
  return { code: code && /^[A-Z0-9]{4}$/.test(code) ? code : null, step: step && /^AN-0[1-6]$/.test(step) ? step : null, send: q.get("send"),
    budget: Number.isInteger(budget) && budget >= 1000 && budget <= 10_000_000 ? budget : null };
}

// 개발 중에 쓰는 내 컴퓨터 주소 (서버를 다른 포트로 띄워도 알아보게)
const LOCAL_PAGES = ["http://localhost:8000/analysis", "http://127.0.0.1:8000/analysis", "http://localhost:8010/analysis",
  "https://ad-report.gem-9ru.com/analysis"];   // 분석 페이지 전용 공개 주소 (같은 서버)

/** 지금 창에서 보고 있는 탭이 분석 페이지인지 따라간다 (탭 바꾸기 · 주소 # 바뀜). */
export function useAnalysisTab(): AnalysisTab | null {
  const [tab, setTab] = useState<AnalysisTab | null>(null);
  useEffect(() => {
    let alive = true;
    const check = async () => {
      const [active] = await browser.tabs.query({ active: true, currentWindow: true }).catch(() => []);
      const parsed = parseAnalysisUrl(active?.url);
      if (!alive) return;
      setTab(parsed && active?.id != null ? { tabId: active.id, ...parsed } : null);
    };
    void check();
    const onActivated = () => void check();
    const onUpdated = (_id: number, info: { url?: string; status?: string }) => { if (info.url || info.status === "complete") void check(); };
    browser.tabs.onActivated.addListener(onActivated);
    browser.tabs.onUpdated.addListener(onUpdated);
    browser.windows?.onFocusChanged?.addListener(onActivated);
    return () => {
      alive = false;
      browser.tabs.onActivated.removeListener(onActivated);
      browser.tabs.onUpdated.removeListener(onUpdated);
      browser.windows?.onFocusChanged?.removeListener(onActivated);
    };
  }, []);
  return tab;
}

/** 분석 단계 이름 (분석 페이지 스테퍼와 같게). */
export const ANALYSIS_STEPS: Record<string, string> = {
  // 축소안 v5: 3단계 (예전 AN-03·04는 ②, AN-05는 ③에 합쳐짐)
  "AN-01": "① 결론", "AN-02": "② 왜 그런지", "AN-03": "② 왜 그런지", "AN-04": "② 왜 그런지", "AN-05": "③ 준비하기", "AN-06": "③ 준비하기",
};
