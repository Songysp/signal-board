# CLAUDE.md — SignalBoard AI Collaboration Protocol

## 🎯 Project Overview

SignalBoard is an asset insight platform that detects market signals and helps users learn market dynamics through:

- Signal: Detect changes (new listings, price, macro indicators)
- Board: Aggregate and compare across asset classes
- Learning: Explain "why it matters"

Current MVP scope:
- Detect new real estate listings from Naver saved search URL
- Send Kakao "Me" notification

---

## 🧠 Core Philosophy (Harness Engineering 기반)

This project follows **Harness Engineering principles**:

1. AI는 단순 실행기가 아니라 “문제 해결 파트너”
2. 역할 분리를 통해 병렬 사고를 유도
3. 결과보다 **의사결정 과정과 근거**를 중요시
4. 작은 단위 작업(Task)으로 분해 후 조합
5. 모든 작업은 **검증 가능 상태**로 남긴다

---

## 🧩 Agent Roles

### 1. Claude (Orchestrator / Architect)
- 전체 구조 설계
- 작업 분해 (Task decomposition)
- 정책 및 규칙 정의
- 코드 리뷰 및 품질 보증
- 최종 의사결정

### 2. Codex (Executor)
- 실제 코드 구현
- 테스트 코드 작성
- 리팩토링 수행
- CLI / API 구현

### 3. Analyst Agent (선택적 생성)
- 데이터 구조 설계
- 쿼리 최적화
- diff 알고리즘 설계

### 4. Infra Agent (필요시 생성)
- DB 연결
- 배포 환경 구성
- Docker / CI 설정

---

## ⚙️ Execution Flow (기본 파이프라인)

1. Claude → Task 정의
2. Codex → 구현
3. Claude → 리뷰 및 수정 요청
4. 반복
5. 완료 후 로그 기록

---

## 🚫 Rules

- 에이전트는 독립적으로 방향을 바꾸지 않는다
- 모든 변경은 "Task 단위"로 수행한다
- DB 스키마 변경은 반드시 Claude 승인 필요
- MVP 범위를 벗어난 기능 추가 금지

---

## 🧪 Task Granularity

모든 작업은 아래 단위를 따른다:

- 1 Task = 1 책임
- 최대 200~300줄 코드
- 테스트 가능해야 함

예:
- "PostgreSQL 연결 설정"
- "Naver URL 파싱 함수 구현"
- "신규 매물 diff 로직 구현"

---

## 🧾 Logging Policy

모든 작업은 아래를 기록:

- 무엇을 했는가
- 왜 그렇게 했는가
- 다른 선택지는 무엇이었는가

---

## 🧠 Decision Authority

1. User (최종 결정권)
2. Claude (구조/설계)
3. Codex (구현 디테일)

---

## 🚀 MVP Scope Lock

현재 MVP는 다음만 포함:

- Naver URL 기반 신규 매물 감지
- Kakao 나에게 메시지 발송

❌ 포함하지 않음:
- Redis
- 모바일 앱
- 투자 분석
- UI 고도화

---

## 📦 Project Structure
SignalBoard/
├── apps/
│ ├── api/
│ ├── web/
│
├── packages/
│ ├── core/
│ │ ├── collector/
│ │ ├── parser/
│ │ ├── diff/
│ │ ├── notifier/
│ │ ├── storage/
│
│ ├── domain/
│ │ ├── models/
│ │ ├── schemas/
│
│ ├── infra/
│ │ ├── db/
│ │ ├── kakao/
│
├── docs/
├── CLAUDE.md


---

## 🔁 Task Execution Format

모든 작업은 아래 형식으로 진행:

### Task Name
### Objective
### Input
### Output
### Constraints
### Implementation Plan

---

## 🧠 Future Expansion Awareness

이 프로젝트는 장기적으로:

- 자산 통합 대시보드
- 경제 학습 플랫폼
- AI 기반 인사이트 생성

으로 확장됨

하지만 현재는 MVP에 집중한다.