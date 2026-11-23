# 광고 코치 v3 시연 체크리스트 (12/5 발표 전)

## 전날 (12/4)
- [ ] `git pull` 후 `feat/v3-extension` 브랜치인지 확인
- [ ] 서버 테스트: `.venv/bin/python -m pytest server/tests -q` → 전부 통과
- [ ] 확장 테스트·빌드: `cd extension && mise exec -- npx vitest run && mise exec -- npx wxt build`
- [ ] 크롬 `chrome://extensions` → 개발자 모드 → **압축해제된 확장 프로그램 로드** → `extension/.output/chrome-mv3`
- [ ] 확장 아이콘을 누르면 오른쪽에 사이드 패널이 열리는지
- [ ] 시연할 메타 계정(지금은 내 계정, Facebook 페이지 연결 없음 → 게시 직전까지만) 광고 관리자 화면 언어가 **한국어**인지 (영어면 캐릭터가 "한국어로 바꿔 주세요"만 말함)
- [ ] **안내 목록 갱신**: 광고 관리자에서 트래픽 캠페인 만들기를 끝까지 따라가며 칸 이름이 `extension/guide/meta_traffic.json`의 `find`와 같은지 확인, 다르면 고치고 다시 빌드
- [ ] 칸마다 대체 스크린샷이 `extension/public/guide/`에 있는지 (지금은 `placeholder.png` 하나)

## 당일
- [ ] 서버 켜기: `.venv/bin/uvicorn server.app:app --port 8000`
  - 발표장 인터넷이 불안하면: `COACH_OFFLINE=1 .venv/bin/uvicorn server.app:app --port 8000` (네이버는 저장본, "수제 쿠키" 저장됨)
  - Claude 키 문제가 있으면 `COACH_NO_LLM=1` (문구는 문장 틀로)
- [ ] 사이드 패널 오른쪽 위 "처음부터"로 지난 연습 상태 지우기

## 시연 순서 (설계서 9장)
1. ① 찾기: "수제 쿠키" → 30대 여성 막대 · 추천 키워드 · 출처 줄 → "이 사람들로 할게요"
2. ② 문구: 좋은 점 "버터 듬뿍, 당일 구움" → 3안 중 하나
3. ② 질문 9개 (권장값 그대로 눌러도 됨) → "묻지 않고 이렇게 두었어요" 펼쳐 보여 주기
4. "광고 관리자 열기" → 캐릭터가 칸마다 안내 → 게시 버튼 앞에서 멈춤 (누르지 않음)
5. 사이드 패널 "결과 파일 올리기" → `server/data/demo/오븐로그_메타AB_20261117-20261120.csv`
6. 결과 카드: "아직 판단하기 일러요" · B가 나을 확률 약 61% · 종료 날짜 7일 더 연장 · 링크 클릭률 범위가 좁혀지는 모습
7. "보고서 크게 보기" (발표 대시보드) → "바꾸러 가기" → 캐릭터가 광고 세트 수정 화면에서 종료 날짜 칸 안내

## 막혔을 때
- 사이드 패널에 "도우미 서버에 연결할 수 없어요" → 서버 터미널이 켜져 있는지, 포트 8000인지
- 캐릭터가 칸을 못 찾음 → 말풍선의 "했어요"로 다음 단계, 끝나고 `meta_traffic.json` 고치기

## 공개 주소로 띄우기 (Cloudflare Tunnel, 2026-11-23)

- 시작: `scripts/serve_public.sh` → https://boaz-ad-assistant.gem-9ru.com (분석 페이지: `/analysis`)
- 멈춤: `scripts/serve_public.sh stop` · 로그: `logs/server.log`, `logs/tunnel.log`
- 이 맥과 스크립트가 켜져 있을 때만 접속된다. 분석 코드(4자리)는 서버 메모리에 있어서 서버를 다시 켜면 사라진다.
- 확장을 공개 주소로 빌드: `cd extension && WXT_API_BASE=https://boaz-ad-assistant.gem-9ru.com npx wxt build` → 크롬 확장 새로고침
- 항상 켜 둬야 하면: 결제 계정 연결 후 `scripts/deploy_cloudrun.sh` (Cloud Run)
