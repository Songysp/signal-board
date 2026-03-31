# SignalBoard Agent Guide

## Purpose

이 문서는 SignalBoard에서 여러 AI가 작업할 때 무엇을 먼저 읽고, 어떤 순서로 판단하고, 어떤 방식으로 결과를 남겨야 하는지 정의한다.

이 프로젝트의 목표는 단순한 코드 생성이 아니라, 빠른 MVP 진행과 이후 확장 가능성을 동시에 지키는 것이다.

## First Read Order

SignalBoard에서 작업을 시작하는 AI는 아래 순서로 문서를 읽는다.

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `task.md`
4. 이 문서 `docs/AGENT_GUIDE.md`

이 순서를 지키는 이유:

- README로 제품의 현재 목적을 빠르게 이해
- ARCHITECTURE로 현재 구현 상태와 한계를 파악
- task.md로 지금 당장 해야 할 우선순위를 확인
- AGENT_GUIDE로 작업 규칙을 확인

## Scope Discipline

현재 MVP 범위는 고정이다.

- 네이버 저장 검색 URL 기반 신규 매물 감지
- 카카오 나에게 메시지 발송

현재 만들지 않는 것:

- 친구 발송
- 카카오 채널 발송
- 모바일 앱
- 경제 지표 ingestion
- 대시보드 UI
- Redis

새 아이디어가 떠올라도, 지금 구현하지 않는다.
필요하면 `task.md`의 `LATER`에만 추가한다.

## How To Choose Work

모든 AI는 아래 규칙으로 작업을 선택한다.

1. `task.md`의 `ACTIVE`를 먼저 본다.
2. `ACTIVE`의 가장 위 Task부터 처리한다.
3. `ACTIVE`가 모두 끝나면 `NEXT`로 간다.
4. `LATER`는 사용자 요청이 없으면 건드리지 않는다.
5. `BLOCKED`는 차단 원인을 먼저 해소하지 않으면 구현하지 않는다.

## Task Granularity Rule

Task는 반드시 작아야 한다.

좋은 Task 예시:

- PostgreSQL 연결 검증
- `poll` 에러 메시지 개선
- Kakao 알림 메시지 포맷 조정
- Naver fetch 실패 유형 분리

나쁜 Task 예시:

- “알림 시스템 전부 완성”
- “웹 UI 만들기”
- “대시보드 다 구현”

좋은 Task의 조건:

- 한 책임만 가진다
- 검증 방법이 명확하다
- 1회 작업으로 끝낼 수 있다
- 실패해도 영향 범위가 작다

## Working Style

SignalBoard에서의 기본 작업 방식은 아래와 같다.

1. 현재 상태를 읽고 이해한다.
2. 한 Task만 고른다.
3. 관련 파일만 수정한다.
4. 직접 실행으로 검증한다.
5. 무엇을 바꿨는지, 어떻게 확인했는지, 남은 리스크가 뭔지 남긴다.

## Required Output After Each Task

각 Task 완료 후에는 최소한 아래 3가지를 남긴다.

1. 무엇을 바꿨는가
2. 어떻게 검증했는가
3. 남은 리스크는 무엇인가

이 형식을 지키면 다음 AI가 이어받기 쉽다.

## Directory Intent

주요 디렉터리의 의도는 아래와 같다.

- `app/`
  - 현재 MVP의 실제 실행 코드
- `assets/`
  - 채널/브랜딩 리소스
- `docs/`
  - 설계, 상태, 작업 프로토콜 문서
- `task.md`
  - 현재와 다음 작업의 실행 보드

## File Ownership Hints

대략적인 책임 분리는 아래를 따른다.

- `app/kakao_tokens.py`
  - Kakao OAuth, refresh, token storage
- `app/kakao_notifier.py`
  - Kakao self-message sending
- `app/naver.py`
  - Naver URL parsing, filter normalization, listing fetch
- `app/alerts.py`
  - new listing diff + alert flow
- `app/storage.py`
  - DB persistence
- `app/cli.py`
  - operator-facing CLI

## Common Mistakes To Avoid

1. MVP 범위를 벗어난 기능을 슬쩍 추가하는 것
2. DB 없이도 되는 실험을 너무 일찍 인프라 중심으로 바꾸는 것
3. Naver 파서 문제를 UI로 우회하려는 것
4. Kakao friend-send를 self-message보다 먼저 완성하려는 것
5. task.md를 읽지 않고 임의로 우선순위를 바꾸는 것

## Current Best Next Move

문서 기준으로 지금 가장 올바른 다음 작업은 이것이다.

1. PostgreSQL end-to-end 연결 검증
2. Naver fetch failure hardening
3. 반복 polling runner 추가

이 순서를 특별한 이유 없이 바꾸지 않는다.
