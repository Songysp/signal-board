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
  - 단지/클러스터 매물 카운트가 있으면 `total=0` 대신 명시 오류로 중단
  - API 테스트가 실제 네이버 응답에 흔들리지 않도록 mock 기반으로 변경
- Verification:
  - `python -m app.cli preview-search` now stops with a clear mismatch error for the current URL
  - `pytest` regression tests

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
  - 그래서 현재는 false `total=0`을 막는 데서 멈춤
- Need:
  - 실제 브라우저 DevTools Network에서 해당 URL을 열었을 때 성공하는 매물 목록 API 요청 1건의 URL, method, request payload, response shape
  - 또는 네이버 외 공식/허가된 데이터 소스 선택
- Verification so far:
  - `preview-search` now reports a clear mismatch instead of `total=0`
  - `pytest` passes

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
