#!/usr/bin/env bash
# Ad assistant를 Cloud Run에 올린다. 결제 계정이 연결된 GCP 프로젝트가 필요하다.
#   사용: scripts/deploy_cloudrun.sh [프로젝트ID]
# - API 키는 .env에서 읽어 Secret Manager에 넣고, 값은 화면에 출력하지 않는다.
# - 분석 결과 코드(4자리)를 서버 메모리에 보관하므로 인스턴스를 1개로 고정한다.
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="${1:-animated-lyceum-513416-e1}"
REGION="asia-northeast1"           # 도메인 연결(domain mapping)을 지원하는 가까운 리전 (도쿄)
SERVICE="ad-assistant"
DOMAIN="boaz-ad-assistant.gem-9ru.com"
KEYS=(NAVER_AD_API_KEY NAVER_AD_SECRET_KEY NAVER_AD_CUSTOMER_ID NAVER_HUB_CLIENT_ID NAVER_HUB_CLIENT_SECRET ANTHROPIC_API_KEY)

gcloud config set project "$PROJECT" >/dev/null
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

SECRETS=()
for k in "${KEYS[@]}"; do
  v="$(grep -E "^${k}=" .env | head -1 | cut -d= -f2- | sed -e 's/^["'\'']//' -e 's/["'\'']$//')"
  [ -z "$v" ] && { echo "$k 값이 .env에 없어 건너뜀"; continue; }
  name="ad-assistant-$(echo "$k" | tr 'A-Z_' 'a-z-')"
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf %s "$v" | gcloud secrets versions add "$name" --data-file=- >/dev/null
  else
    printf %s "$v" | gcloud secrets create "$name" --data-file=- --replication-policy=automatic >/dev/null
  fi
  SECRETS+=("${k}=${name}:latest")
  echo "비밀 값 저장: $name"
done

PROJECT_NUMBER="$(gcloud projects describe "$PROJECT" --format='value(projectNumber)')"
# Cloud Run 실행 계정이 비밀 값을 읽을 수 있게
for s in "${SECRETS[@]}"; do n="${s#*=}"; n="${n%:latest}"; gcloud secrets add-iam-policy-binding "$n" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role=roles/secretmanager.secretAccessor >/dev/null; done

gcloud run deploy "$SERVICE" --source . --region "$REGION" --allow-unauthenticated \
  --min-instances 1 --max-instances 1 --memory 1Gi --cpu 1 --timeout 120 \
  --set-secrets "$(IFS=,; echo "${SECRETS[*]}")"

echo "서비스 주소: $(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')"
echo "도메인 연결: gcloud beta run domain-mappings create --service $SERVICE --domain $DOMAIN --region $REGION"
