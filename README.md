# SignalBoard

부동산 신규 매물 알림에서 시작해, 장기적으로는 경제 학습 대시보드까지 확장하는 독립 프로젝트입니다.

현재 MVP 목표:

- 네이버부동산 저장 검색 URL 기반 신규 매물 감지
- 카카오톡 나에게 메시지 발송
- 이후 웹 UI와 모바일앱으로 확장 가능한 API-first 구조 유지

현재 수집 기준:

- 안정적으로 수집 가능한 1차 MVP는 개별 매물 상세가 아니라 검색 결과 단지/클러스터입니다.
- `articleList`가 비어 있는 지도 URL은 `complexList` 결과로 fallback합니다.
- 단지/클러스터의 가격 범위, 면적 범위, 검색 결과 수 변화도 감지합니다.
- 개별 매물 상세 수집은 단지 상세 경로가 안전하게 확인된 뒤 별도 task로 진행합니다.

채널 이름:

- `부동산알리미`

현재 상태:

- `app/` : 백엔드 코드
- `assets/` : 브랜딩/채널 이미지
- `docs/` : 설계/상태 문서
- `.env.example` : 환경변수 예시

이미 구현된 것:

1. Kakao self-message 토큰 관리 및 테스트 발송
2. Naver `fin.land` / `new.land` / `m.land` URL 파싱
3. 신버전 URL을 mobile 수집 경로로 연결하는 브리지 로직
4. 신규 매물 diff 로직
5. PostgreSQL 스키마와 저장 함수
6. DB 없이 바로 써볼 수 있는 `preview-search`, `poll-url` CLI
7. Docker Compose 기반 로컬 PostgreSQL
8. DB-backed `poll` 및 `poll-loop` CLI

상세 방향과 최신 구현 상태:

- [ARCHITECTURE.md](/Users/song/Documents/signal-board/docs/ARCHITECTURE.md)

## Local MVP Runbook

```powershell
docker compose up -d postgres
.\.venv\bin\python.exe -m app.cli init-db
.\.venv\bin\python.exe -m app.cli db-check
.\.venv\bin\python.exe -m app.cli preview-search
.\.venv\bin\python.exe -m app.cli poll
```

반복 실행:

```powershell
.\.venv\bin\python.exe -m app.cli poll-loop
```

기본 반복 간격은 네이버 차단 리스크를 줄이기 위해 4시간입니다. 필요할 때만 `--interval-seconds 14400`처럼 직접 조정합니다.

네이버 수집 안전선:

- 반복 수집 기본 간격은 4시간입니다.
- 4시간보다 짧은 반복 수집은 기본 차단됩니다.
- 로컬 개발 테스트에서만 `--allow-fast-poll`을 명시해 짧은 간격을 허용할 수 있습니다.
- IP 우회, Captcha 우회, 로그인 세션 우회, 차단 우회는 하지 않습니다.

API 실행:

```powershell
.\.venv\bin\python.exe -m pip install -e .[api]
.\.venv\bin\python.exe -m uvicorn app.main:app --reload
```

관리 화면:

- `http://127.0.0.1:8000/`

초기 API:

- `GET /health`
- `GET /watches`
- `POST /watches`
- `POST /poll`
- `GET /alerts`
- `POST /preview-search`
- `POST /kakao/test`

DB 없이 단일 URL만 빠르게 테스트:

```powershell
.\.venv\bin\python.exe -m app.cli poll-url --no-send-kakao
```

읽기 전용 상태 점검:

```powershell
.\.venv\bin\python.exe -m app.cli doctor
```

장시간 운영 전에는 `doctor`에서 `KAKAO_REFRESH_TOKEN`이 있는지 확인하세요. 없으면 `kakao-login`으로 refresh token을 저장하는 편이 안전합니다.

Slack 알림:

- Slack Incoming Webhook URL을 `.env`의 `SLACK_WEBHOOK_URL`에 저장하면 카카오 알림과 함께 Slack에도 발송합니다.
- 테스트: `.\.venv\bin\python.exe -m app.cli send-test-slack`

로컬 운영 runbook:

- [docs/RUNBOOK.md](docs/RUNBOOK.md)
- [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md)

선택적 관리 토큰:

- `.env`에 `SIGNALBOARD_ADMIN_TOKEN`을 설정하면 watch 등록/토글, poll, Kakao 테스트 같은 변경 API가 `X-SignalBoard-Token` 헤더를 요구합니다.
- 관리화면의 `관리 토큰` 입력란에 같은 값을 저장하면 UI에서 변경 작업을 계속 사용할 수 있습니다.
