/** AN-06 근거 탭 '가상 케이스' 6개 (v4 4-1장: 근거 탭·발표 자료만, 판정에는 안 씀).
 *  원본: server/data/demo/소연베이크_가상광고데이터.xlsx '케이스 요약' 시트의 '가상 실제' 줄
 *  (시뮬레이션 · 2026-11-12 · gen.py 시드 20261112 · 예산 30만 원 · 객단가 2.6만 원 · 광고 기간 + 잔존 7일).
 *  주문 = 광고 덕분 주문 합계(직접 클릭 + 광고를 보고 나중에 검색해서 산 주문, 시뮬레이터만 아는 정답).
 *  주문 1건당 비용(실제) = 지출 ÷ 그 합계, 마지막 클릭만 = 지출 ÷ 직접 클릭 주문. 숫자는 원 단위 반올림. */
export interface VirtualCase { id: string; name: string; spend: number; orders: number | null; cost: number | null; lastClick: number | null; roas: number | null }

export const VIRTUAL_CASES: VirtualCase[] = [
  { id: "C1", name: "추천 경로 (메타 + 네이버)", spend: 287868, orders: 28.44, cost: 10122, lastClick: 23989, roas: 2.57 },
  { id: "C2", name: "플랫폼 기본값 (메타 자동)", spend: 299461, orders: 29.34, cost: 10207, lastClick: 18716, roas: 2.55 },
  { id: "C3", name: "좁게·길게 인지도", spend: 301111, orders: 21.51, cost: 13999, lastClick: 100370, roas: 1.86 },
  { id: "C4", name: "네이버만", spend: 250835, orders: 15, cost: 16722, lastClick: 16722, roas: 1.55 },
  { id: "C0", name: "광고 안 함", spend: 0, orders: 0, cost: null, lastClick: null, roas: null },
  { id: "C1b", name: "개선 사이클 (C1을 한 번 고침)", spend: 304891, orders: 26.49, cost: 11510, lastClick: 25408, roas: 2.26 },
];
