# SignalBoard

부동산 신규 매물 알림에서 시작해, 장기적으로는 경제 학습 대시보드까지 확장하는 독립 프로젝트입니다.

현재 MVP 목표:

- 네이버부동산 저장 검색 URL 기반 신규 매물 감지
- 카카오톡 나에게 메시지 발송
- 이후 웹 UI와 모바일앱으로 확장 가능한 API-first 구조 유지

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
.\.venv\bin\python.exe -m app.cli poll-loop --interval-seconds 60
```

DB 없이 단일 URL만 빠르게 테스트:

```powershell
.\.venv\bin\python.exe -m app.cli poll-url --no-send-kakao
```
