# SignalBoard Task Board

## Purpose

이 문서는 SignalBoard에서 AI 에이전트가 현재 상태를 빠르게 파악하고, 다음 작업을 작은 단위로 이어서 진행할 수 있도록 만든 작업 기준 문서다.

원칙:

- 한 번에 한 Task만 끝낸다.
- 각 Task는 한 책임만 가진다.
- 구현 후에는 반드시 실행 가능한 검증 방법을 남긴다.
- MVP 범위를 벗어나는 확장은 `Later`로 보낸다.

## Product Scope Lock

현재 MVP는 이것만 포함한다.

- 네이버부동산 저장 검색 URL 기반 신규 매물 감지
- 카카오 나에게 메시지 알림

현재 제외한다.

- 친구 발송
- 카카오 채널 발송
- 모바일 앱
- 경제 지표 수집
- 학습 대시보드 UI
- Redis

## Current System Snapshot

현재 구현 완료 상태:

- Kakao OAuth code exchange / refresh / self-message 발송
- Naver `fin.land` / `new.land` / `m.land` URL 파싱
- 신버전 URL을 mobile listing fetch 경로로 브리지
- 신규 매물 diff 로직
- PostgreSQL 스키마 및 저장 함수
- `preview-search` CLI
- `poll-url` CLI
- `init-db`, `add-watch`, `list-watches`, `poll` CLI

현재 주의사항:

- `poll-url`은 DB 없이 바로 테스트 가능
- `poll`은 PostgreSQL 연결이 실제로 되어 있어야 함
- Naver 내부 구조 변경 가능성이 있으므로 fetch 실패 처리 보강이 필요함

## Status Legend

- `DONE`: 구현 및 기본 검증 완료
- `ACTIVE`: 바로 이어서 진행할 작업
- `NEXT`: ACTIVE 다음 우선순위
- `LATER`: MVP 이후 작업
- `BLOCKED`: 외부 설정이나 사람 개입이 필요한 작업

## DONE

### T020 Naver Safe Collection Guardrails
- Status: `DONE`
- Goal: 네이버 수집이 차단/약관 리스크를 키우지 않도록 보수 운영 기본값을 코드에 고정
- Output:
  - 반복 poll 기본 간격 4시간 유지
  - 4시간 미만 반복 poll은 기본 차단
  - 개발용 짧은 반복 poll은 `--allow-fast-poll` 명시 필요
  - README/ARCHITECTURE에 IP 우회, Captcha 우회, 로그인 세션 우회 금지 명시
- Verification:
  - `python -m app.cli poll-loop --help`
  - `pytest` guardrail tests

### T021 Prevent False Zero Listing Reports
- Status: `DONE`
- Goal: 네이버 지도에는 결과가 있는데 SignalBoard가 `total=0`으로 오해하는 상황 방지
- Root cause:
  - 일부 지도 URL은 단지/클러스터 결과를 반환하지만, 현재 사용하는 mobile `articleList` endpoint는 `null`을 반환함
- Output:
  - `articleList`가 비어 있을 때 `complexList`를 확인
  - 단지/클러스터 매물 카운트가 있으면 단지 단위 결과로 fallback 수집
  - API 테스트가 실제 네이버 응답에 흔들리지 않도록 mock 기반으로 변경
- Verification:
  - `python -m app.cli preview-search "https://new.land.naver.com/complexes?ms=37.385694,126.6477823,15&a=APT:ABYG:JGC&b=A1&e=RETAIL&f=40000&g=60000"` returns `total=20`
  - `pytest` regression tests

### T024 Search Result Collector MVP
- Status: `DONE`
- Goal: 개별 매물이 아닌 검색 결과 단지/클러스터 기준으로 MVP 알림이 동작하게 만들기
- Output:
  - `NaverListing.result_level`
  - complex fallback results saved as `result_level='complex'`
  - DB schema columns for `result_level`
  - Kakao message headline changed to `신규 검색 결과` for complex results
  - management UI copy changed from individual listing wording to search-result wording
  - legacy URL normalization keeps original zoom instead of increasing it
- Verification:
  - provided Songdo URL returns `total=20`
  - DB watch poll returns `total=20`
  - repeat poll returns `new=0`
  - `pytest` passes

### T025 Complex Result Change Detection
- Status: `DONE`
- Goal: 검색 결과 단지/클러스터의 가격 범위, 면적 범위, 검색 결과 수 변화 감지
- Output:
  - `NaverListing.result_count`
  - `listing_snapshots.result_count`
  - `listing_current_state.result_count`
  - current-state comparison for complex results
  - `changed_result:{hash}` alert event type for deduped change notifications
  - Kakao message format for `[부동산알리미] 검색 결과 변화`
  - CLI poll output includes `changed=N`
- Verification:
  - `pytest` passes
  - provided Songdo URL preview returns `total=20`
  - DB watch id=3 fake-notifier poll produced `changed=20` once after schema upgrade, then repeat poll produced `changed=0`

### T026 Alert Event UI
- Status: `DONE`
- Goal: 관리화면에서 신규 검색 결과와 검색 결과 변화 이벤트를 구분해서 읽기 쉽게 표시
- Output:
  - recent alerts rendered as cards instead of raw JSON
  - event type badges for `신규 검색 결과` and `검색 결과 변화`
  - status badges for sent/pending/failed
  - alert message rendered with line breaks
- Verification:
  - dashboard HTML test checks `검색 결과 변화` UI copy
  - `pytest` passes

### T027 Watch Management Controls
- Status: `DONE`
- Goal: 오래된 테스트 watch를 SQL 없이 관리화면에서 활성/비활성 처리
- Output:
  - `set_watch_active()` storage function
  - `PATCH /watches/{watch_id}/active`
  - watch cards in management UI
  - active/inactive badges
  - activate/deactivate buttons
- Verification:
  - API tests for success and 404 paths
  - dashboard HTML test checks `setWatchActive`
  - DB smoke test toggled one watch off and restored original state
  - `pytest` passes

### T028 Watch Status Summary
- Status: `DONE`
- Goal: 관리화면과 CLI에서 각 watch의 현재 상태를 빠르게 파악
- Output:
  - `list_watches()` includes current known result count
  - `list_watches()` includes alert event count
  - `GET /watches` exposes `current_result_count` and `alert_event_count`
  - management UI watch cards display current results, alert count, and last checked time
  - CLI `list-watches` shows `results=N alerts=N`
- Verification:
  - API test checks summary fields
  - CLI smoke test shows watch summaries
  - `pytest` passes

### T029 App Doctor Command
- Status: `DONE`
- Goal: 운영 전 로컬 상태를 읽기 전용으로 한 번에 점검
- Output:
  - `doctor` CLI command
  - env presence checks for DB, Kakao, Naver URL
  - PostgreSQL connectivity and watch counts
  - optional Kakao profile check
  - optional Naver preview check with result-level summary
- Verification:
  - `doctor --no-check-kakao --no-check-naver`
  - `doctor`
  - `pytest` passes

### T030 Safe Local Scheduler Runbook
- Status: `DONE`
- Goal: 4시간 기본 주기로 로컬 운영을 안전하게 반복 실행할 수 있는 스크립트와 문서 제공
- Output:
  - `scripts/run_poll_once.ps1`
  - `scripts/install_windows_task.ps1`
  - `scripts/uninstall_windows_task.ps1`
  - `docs/RUNBOOK.md`
  - README runbook link
- Safety:
  - install script refuses intervals below 4 hours
  - run script starts local Docker Postgres before doctor/poll
  - dry-run mode verifies readiness without polling or sending alerts
- Verification:
  - PowerShell parser check for all scripts
  - `install_windows_task.ps1 -IntervalHours 3` fails as expected
  - `run_poll_once.ps1 -DryRun` succeeds
  - `pytest` passes

### T031 Optional Admin Token Guard
- Status: `DONE`
- Goal: 관리화면/API가 로컬 외부로 노출될 경우 변경 작업을 선택적으로 보호
- Output:
  - `SIGNALBOARD_ADMIN_TOKEN`
  - write routes require `X-SignalBoard-Token` when token is configured
  - protected routes: watch create, watch active toggle, poll, Kakao test
  - management UI token input stored in localStorage
- Verification:
  - API tests cover 401 without token and success with token
  - dashboard HTML test checks token UI
  - `pytest` passes

### T032 Kakao Token Longevity Warning
- Status: `DONE`
- Goal: 장시간 polling 중 access token 만료 리스크를 doctor/runbook에서 드러내기
- Output:
  - `doctor` warns when `KAKAO_REFRESH_TOKEN` is missing
  - README note for refresh token
  - RUNBOOK Kakao token longevity section
- Verification:
  - `doctor --no-check-kakao --no-check-naver` shows refresh-token warning
  - `pytest` passes

### T033 Current Results View
- Status: `DONE`
- Goal: 각 watch가 현재 알고 있는 단지/클러스터 검색 결과를 관리화면에서 확인
- Output:
  - `list_current_results(watch_id, limit)`
  - `GET /watches/{watch_id}/results`
  - management UI `현재 결과 보기` button
  - current results rendered as cards with level, result count, price, area, and Naver link
- Verification:
  - API test for watch results endpoint
  - DB smoke test for watch #3 current results
  - `pytest` passes

### T034 Retention Cleanup Command
- Status: `DONE`
- Goal: 오래된 alert 이벤트와 로컬 로그가 무한히 쌓이지 않도록 수동 cleanup 제공
- Output:
  - `prune_alert_events(days, apply=False)`
  - `cleanup-retention` CLI command
  - dry-run by default
  - `--apply` required for deletion
  - runbook retention cleanup section
- Verification:
  - `pytest` passes
  - `cleanup-retention --days 1` dry-run reports old alert events/log files without deleting
  - `cleanup-retention --help`

### T035 Single Watch Poll
- Status: `DONE`
- Goal: 전체 watch 대신 특정 watch만 수동 poll하여 불필요한 요청을 줄임
- Output:
  - `get_watch(watch_id)`
  - `POST /watches/{watch_id}/poll`
  - `poll-watch WATCH_ID` CLI
  - management UI `이 watch poll` button
- Verification:
  - API tests cover success and inactive watch rejection
  - CLI help smoke test
  - `pytest` passes

### T036 Preview Result Cards
- Status: `DONE`
- Goal: 관리화면 미리보기 결과를 raw JSON 대신 결과 카드로 바로 확인
- Output:
  - preview-search success renders cards in current results area
  - output panel shows compact preview summary
- Verification:
  - dashboard HTML test checks `renderPreviewResults`
  - `pytest` passes

### T037 Management UI Result Filter
- Status: `DONE`
- Goal: 현재 검색 결과가 많을 때 관리화면에서 원하는 단지/조건을 빠르게 찾기
- Output:
  - result search input
  - sort selector for result count, name, and price text
  - filtered count summary
  - preview and saved results share the same card renderer
- Verification:
  - dashboard HTML test checks filter functions
  - `pytest` passes

### T038 Manual QA Pass
- Status: `DONE`
- Goal: 관리화면이 실제 로컬 서버와 브라우저 DOM에서 핵심 요소를 렌더링하는지 확인
- Output:
  - `docs/QA_MANUAL.md`
- Verification:
  - local `GET /health`
  - local dashboard HTTP 200
  - Chrome headless DOM smoke
  - watch cards rendered
  - alert cards rendered
  - result filter controls rendered
  - single-watch poll buttons rendered

### T041 Naver Article API Spike
- Status: `DONE`
- Goal: GitHub 사례처럼 네이버 내부 article API를 제품 코드에 붙일 수 있는지 안전하게 1회성 검증
- Attempts:
  - `https://fin.land.naver.com/front-api/v1/complex/article/list`
  - single complex numbers from current Songdo search results
  - browser-like JSON headers without login/session/IP/Captcha bypass
- Findings:
  - single article-list probe returned `429 TOO_MANY_REQUESTS`
  - repeated per-complex article calls were removed from product code
  - current safe product behavior remains complex/cluster-level collection
- Additional fix:
  - mobile `complexList` works without `cortarNo`; when region-code resolution fails, SignalBoard now falls back to coordinate bounds instead of failing the whole preview.
- Verification:
  - provided Songdo URL `preview-search` returns complex-level `total=20`
  - official pytest suite passes

### T040 Production Readiness Checklist
- Status: `DONE`
- Goal: 무인 polling 시작 전 확인 항목을 명확히 문서화
- Output:
  - `docs/PRODUCTION_READINESS.md`
  - README link
  - RUNBOOK link
- Verification:
  - checklist covers Docker, DB, Kakao, refresh token, active watches, doctor, dry-run, 4h interval, admin token, retention cleanup

### T001 Project Separation
- Status: `DONE`
- Goal: SignalBoard를 독립 폴더/독립 repo로 분리
- Output:
  - 별도 repo
  - 별도 GitHub 원격
- Verification:
  - GitHub repo 존재
  - 상위 OrchAI와 분리된 경로에서 작업

### T002 Kakao Token Manager Split
- Status: `DONE`
- Goal: 토큰 관리와 메시지 발송 로직 분리
- Output:
  - `app/kakao_tokens.py`
  - `app/kakao_notifier.py`
- Verification:
  - `python -m app.cli kakao-me`
  - `python -m app.cli send-test-kakao`

### T003 Naver URL Parser
- Status: `DONE`
- Goal: Naver 검색 URL을 구조화된 필터로 파싱
- Output:
  - `app/models.py`
  - `app/naver.py`
- Supports:
  - `fin.land.naver.com`
  - `new.land.naver.com`
  - `m.land.naver.com`
- Verification:
  - `python -m app.cli inspect-search-url "<url>"`

### T004 Naver Mobile Fetch Bridge
- Status: `DONE`
- Goal: 신버전 URL을 직접 긁는 대신 mobile listing fetch 경로로 연결
- Output:
  - `NaverSearchClient.fetch_listings()`
- Verification:
  - `python -m app.cli preview-search "<fin.land url>"`

### T005 New Listing Diff
- Status: `DONE`
- Goal: 첫 수집은 baseline만 만들고, 이후에는 신규 ID만 감지
- Output:
  - `app/alerts.py`
  - `poll-url` baseline/new logic
- Verification:
  - 같은 URL로 `poll-url` 2회 실행

### T006 PostgreSQL Schema
- Status: `DONE`
- Goal: watch/listing/alert 저장 구조 정의
- Output:
  - `app/db.py`
  - `app/storage.py`
- Tables:
  - `watch_targets`
  - `listing_snapshots`
  - `listing_current_state`
  - `alert_events`
- Verification:
  - `python -m app.cli init-db`

### T007 Local No-DB Polling
- Status: `DONE`
- Goal: PostgreSQL 없이도 바로 감시 테스트 가능하게 만들기
- Output:
  - `preview-search`
  - `poll-url`
- Verification:
  - `python -m app.cli poll-url "<url>" --no-send-kakao`

## ACTIVE

### T008 PostgreSQL End-to-End Wiring
- Status: `DONE`
- Goal: DB가 실제 떠 있는 환경에서 `add-watch -> poll -> alert_events` 전체 플로우 검증
- Why:
  - 현재 schema와 저장 함수는 구현돼 있지만 로컬 DB 연결 확인이 아직 완전히 끝나지 않음
- Input:
  - `DATABASE_URL`
  - 실행 중인 PostgreSQL
- Output:
  - 등록된 watch가 DB 기반으로 baseline 저장
  - 이후 신규 매물만 alert event 생성
- Verification:
  1. `python -m app.cli init-db`
  2. `python -m app.cli add-watch "테스트" "<url>"`
  3. `python -m app.cli poll`
  4. DB row 확인 또는 CLI 결과 확인
- Completed verification:
  - `docker compose up -d postgres`
  - `python -m app.cli db-check`
  - `python -m app.cli init-db`
  - `python -m app.cli poll`
  - first poll baseline, second poll `new=0`

### T009 Fetch Failure Hardening
- Status: `DONE`
- Goal: Naver fetch 실패를 명시적인 오류 상태로 다루기
- Why:
  - 현재는 구조 변경, 빈 결과, 지역 추론 실패가 모두 예외로 섞일 수 있음
- Subtasks:
  - `T009-1` region resolution 실패 메시지 정리
  - `T009-2` Naver 응답 비정상 케이스 분류
  - `T009-3` CLI에서 사용자 친화적 에러 출력
- Verification:
  - 잘못된 URL
  - 빈 지역
  - 비정상 응답
  - 각각에서 다른 오류 메시지 확인

Completed output:

- Naver `null` listing response is treated as an empty result instead of crashing.
- `poll-url` and DB-backed baseline detection now handle zero-listing baselines.
- CLI commands now show friendly Korean errors for unsupported URLs, missing map coordinates, region resolution failures, Naver rate limits, Kakao send failures, and DB connection failures.
- Regression tests cover null listing responses and key CLI error formatting.

## NEXT

### T010 Repeated Poll Runner
- Status: `DONE`
- Goal: 일정 간격으로 반복 실행되는 경량 러너 추가
- Scope:
  - 우선은 단순 while loop + sleep
  - 서비스/daemon화는 나중
- Output:
  - `run` 또는 `watch-loop` 계열 CLI
- Verification:
  - 60초 또는 300초 간격 반복 동작
- Completed output:
  - `poll-url-loop`
  - `poll-loop`

### T011 API Surface For Watches
- Status: `DONE`
- Goal: 웹/앱에서 재사용할 최소 API 추가
- Scope:
  - watch 등록
  - watch 목록
  - 마지막 poll 결과
  - alert history
- Output:
  - `FastAPI` route skeleton
- Verification:
  - `/health`
  - `/watches`
  - `/alerts`
- Completed output:
  - `GET /health`
  - `GET /watches`
  - `POST /watches`
  - `POST /poll`
  - `GET /alerts`
  - `POST /preview-search`
  - `POST /kakao/test`
  - API dependencies pinned to FastAPI `0.99.x` / Pydantic `1.x` for this Python environment

### T012 Thin Web UI
- Status: `DONE`
- Goal: 관리용 최소 웹 화면 추가
- Scope:
  - 감시 조건 등록
  - 감시 목록 보기
  - 최근 신규 매물 로그
  - Kakao 연결 상태 보기
- Verification:
  - 브라우저에서 watch 등록 후 poll 결과 조회
- Completed output:
  - `GET /` management page
  - watch registration form
  - watch list viewer
  - manual poll button
  - alert history viewer
  - Kakao test button
  - API test coverage for dashboard HTML

## LATER

### T013 Structured Condition Storage
- Status: `LATER`
- Goal: URL만 저장하지 않고 구조화 조건도 1급 엔티티로 저장
- Why:
  - Naver URL 변경 리스크 완화

### T014 Price Change Detection
- Status: `LATER`
- Goal: 신규 매물뿐 아니라 가격 변동도 감지

### T015 Kakao Friend Send
- Status: `LATER`
- Goal: Kakao 친구 발송 지원
- Note:
  - app review / team member restriction 해결 필요

### T016 Kakao Channel Send
- Status: `LATER`
- Goal: 카카오 채널 기반 발송으로 확장

### T017 Dashboard Foundation
- Status: `LATER`
- Goal: 자산 인사이트 대시보드의 데이터 모델과 API 뼈대 추가

### T018 Macro/Gold/Stock Ingestion
- Status: `LATER`
- Goal: 부동산 외 경제 지표 수집 파이프라인 추가

## BLOCKED

### T023 Browser URL Collector Fallback
- Status: `BLOCKED`
- Goal: 네이버 내부 API 직접 매핑 대신 저장 URL을 브라우저로 열고 화면에 렌더링된 결과를 읽는 fallback 수집기 구현
- Attempts:
  - Python Playwright optional dependency 검토
  - Selenium optional dependency 검토
  - Chrome DevTools Protocol 직접 연결 검토
- Findings:
  - Playwright는 현재 MSYS Python 환경에서 wheel을 찾지 못해 설치 불가
  - Selenium은 `cffi` 빌드 실패로 설치 불가
  - Chrome CDP 직접 연결은 성공
  - `fin.land.naver.com` 화면은 열리지만 데이터 API가 `429 TOO_MANY_REQUESTS`라 매물 DOM이 렌더링되지 않음
  - 원래 `new.land.naver.com/complexes/...` URL은 headless Chrome에서 `/404`로 리다이렉트됨
- Safety decision:
  - DevTools 차단 해제, IP 우회, 로그인 세션 우회, Captcha/차단 우회는 하지 않음
  - 검증 불가능한 크롤러 코드는 추가하지 않음
- Need:
  - 사람이 일반 브라우저에서 성공적으로 보는 화면의 허용 가능한 데이터 접근 방식
  - 또는 네이버 외 공식/허가된 부동산 데이터 소스
  - 또는 Windows 표준 Python 환경으로 별도 브라우저 자동화 런타임 재구성 후 재검토

### T022 Complex To Article Listing Path
- Status: `BLOCKED`
- Goal: 네이버 지도 단지/클러스터 결과에서 개별 매물 목록까지 안전하게 내려가기
- Root cause:
  - 현재 URL은 지도에 단지/클러스터 결과가 있음
  - mobile `articleList`는 `null` 반환
  - mobile `complexList`는 단지 결과와 매물 카운트를 반환
  - 신형 화면은 `fin.land.naver.com/front-api/v1/...` 계열을 쓰는 것으로 보이나 직접 확인 시 `TOO_MANY_REQUESTS`가 반환됨
- Safety decision:
  - IP 우회, Captcha 우회, 요청 반복, 로그인 세션 우회는 하지 않음
  - product code must not call article-level internal APIs in a loop while they return 429
- Need:
  - 실제 브라우저 DevTools Network에서 해당 URL을 열었을 때 성공하는 매물 목록 API 요청 1건의 URL, method, request payload, response shape
  - 또는 네이버 외 공식/허가된 데이터 소스 선택
- Verification so far:
  - complex-level `preview-search` works
  - single article-list probe returned 429

### T019 Kakao Friend List / Friend Send
- Status: `BLOCKED`
- Blocker:
  - 카카오 앱 검수 또는 테스터 등록 필요
- Current finding:
  - `friends` scope는 확보했지만 unreviewed app restriction 존재

## Implementation Rules For AI Agents

모든 AI는 아래를 지켜야 한다.

1. 새 기능을 만들기 전에 `DONE / ACTIVE / NEXT / LATER`를 먼저 확인한다.
2. `ACTIVE`에서 가장 위에 있는 Task부터 처리한다.
3. 한 번에 하나의 Task만 끝낸다.
4. Task를 완료하면 아래 3가지를 남긴다.
- 무엇을 바꿨는지
- 어떻게 검증했는지
- 남은 리스크가 뭔지
5. MVP 범위를 벗어나는 제안은 구현하지 말고 `LATER`에 추가만 한다.

## Recommended Immediate Order

바로 다음 순서는 이 순서를 따른다.

1. `T008` PostgreSQL end-to-end wiring
2. `T009` fetch failure hardening
3. `T010` repeated poll runner
4. `T011` API surface
5. `T012` thin web UI
