// scripts/virtual_cases.py 가 만든 파일 (손으로 고치지 않음). 원본: server/engine/loop/virtual.py, 시드 20261126
/** AN-06 근거 탭 '가상 케이스' 6개: 메타 설정 하나만 다르게 한 A/B를 오븐로그 실측 비율로 만들어 분석 엔진에 넣은 결과. 판정에는 안 씀. */
export interface VirtualCase { id: string; setting: string; basis: string; conclusion: string;
  word: "확실해요" | "A 쪽이에요" | "B 쪽이에요" | "아직 몰라요" | null; prob: number | null; better: "A" | "B" | null; alerts: string[] }

export const VIRTUAL_CASES: VirtualCase[] = [
  {
    "id": "V1",
    "setting": "노출 위치: 자동 vs 직접 고르기",
    "basis": "실측",
    "conclusion": "광고 › 형식·미디어: + 세로(9:16) 1개",
    "word": "B 쪽이에요",
    "prob": 0.74,
    "better": "B",
    "alerts": [
      "small_sample"
    ]
  },
  {
    "id": "V2",
    "setting": "같은 설정 두 세트 (차이 없음)",
    "basis": "실측",
    "conclusion": "광고 › 형식·미디어: + 세로(9:16) 1개",
    "word": "확실해요",
    "prob": 0.93,
    "better": "B",
    "alerts": []
  },
  {
    "id": "V3",
    "setting": "총예산이 '하루 최소 × 기간'보다 적음 (두 세트 모두 2,000원)",
    "basis": "실측 (11/17 안 나간 날)",
    "conclusion": "광고 세트 › 예산: 총예산 넉넉하게",
    "word": "B 쪽이에요",
    "prob": 0.81,
    "better": "B",
    "alerts": [
      "no_delivery",
      "underspent",
      "small_sample"
    ]
  },
  {
    "id": "V4",
    "setting": "예산 공유(최대 20%) 켬 → 한 세트에 돈이 몰림",
    "basis": "실측 (베이커리 실험 2 28 : 72)",
    "conclusion": "광고 › 형식·미디어: + 세로(9:16) 1개",
    "word": "아직 몰라요",
    "prob": 0.88,
    "better": "B",
    "alerts": [
      "spend_gap"
    ]
  },
  {
    "id": "V5",
    "setting": "B 웹사이트 주소 잘못 (페이지가 늦게 열림)",
    "basis": "가정: 도착 비율 45%",
    "conclusion": "광고 › 웹사이트 URL: 주소·속도 점검",
    "word": "A 쪽이에요",
    "prob": 0.72,
    "better": "A",
    "alerts": [
      "low_visit_rate"
    ]
  },
  {
    "id": "V6",
    "setting": "좁은 지역 + 14일 (같은 사람에게 반복)",
    "basis": "가정: 빈도 3번 · 뒤 절반 클릭 30%↓",
    "conclusion": "광고 › 형식·미디어: + 새 소재 1개",
    "word": "아직 몰라요",
    "prob": 0.67,
    "better": "B",
    "alerts": [
      "high_frequency"
    ]
  }
];
