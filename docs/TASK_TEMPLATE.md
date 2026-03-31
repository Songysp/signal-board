# SignalBoard Task Template

이 템플릿은 `task.md`에 새 작업을 추가하거나, 개별 Task를 더 자세히 쪼개야 할 때 사용한다.

---

## Task ID

예:

- `T020`
- `T020-1`

---

## Title

짧고 책임이 하나로 보이게 쓴다.

좋은 예:

- PostgreSQL poll result 검증
- Naver fetch 예외 메시지 분리
- Kakao alert message format 정리

나쁜 예:

- 알림 시스템 완성
- 대시보드 개발

---

## Status

아래 중 하나만 사용한다.

- `DONE`
- `ACTIVE`
- `NEXT`
- `LATER`
- `BLOCKED`

---

## Goal

이 Task가 끝나면 정확히 무엇이 가능해져야 하는지 쓴다.

예:

- `poll` 실행 시 PostgreSQL에 snapshot이 저장되고 baseline 여부가 구분된다.

---

## Why

이 작업이 왜 필요한지, 어떤 리스크를 줄이는지 쓴다.

예:

- 현재는 `poll-url`만 실사용 검증이 가능하고, DB 기반 경로는 아직 완전히 닫히지 않았다.

---

## Inputs

작업에 필요한 입력, 설정, 외부 조건을 적는다.

예:

- `DATABASE_URL`
- 실행 중인 PostgreSQL
- 테스트용 Naver 저장 검색 URL

---

## Outputs

이 Task가 끝났을 때 남아야 하는 코드/문서/명령을 적는다.

예:

- `app/storage.py` 수정
- `poll` 검증 결과
- 문서 반영

---

## Constraints

절대 벗어나면 안 되는 제한을 적는다.

예:

- MVP 범위를 벗어나지 않는다
- UI는 만들지 않는다
- Redis는 추가하지 않는다

---

## Verification

반드시 실제 실행 가능한 형태로 쓴다.

예:

1. `python -m app.cli init-db`
2. `python -m app.cli add-watch "테스트" "<url>"`
3. `python -m app.cli poll`
4. DB row 또는 CLI 출력 확인

---

## Risks

남아 있는 리스크나 불확실성을 적는다.

예:

- 로컬 PostgreSQL 설정에 따라 연결 에러가 날 수 있음
- Naver 응답 포맷이 바뀌면 fetch가 깨질 수 있음

---

## Completion Note

작업 완료 후 아래 형식으로 남긴다.

- 무엇을 바꿨는지
- 어떻게 검증했는지
- 남은 리스크가 뭔지
