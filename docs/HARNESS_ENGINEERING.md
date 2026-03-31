# Harness Engineering For SignalBoard

## Why This Exists

SignalBoard는 외부 서비스에 의존하는 제품이다.

- Kakao OAuth
- Kakao message API
- Naver search URL
- Naver mobile listing response
- PostgreSQL

이런 프로젝트는 “대충 되는 코드”보다 “관측 가능하고 검증 가능한 작업 방식”이 훨씬 중요하다.

그래서 SignalBoard는 Harness Engineering 방식으로 개발한다.

## Core Idea

AI를 단순 코드 생성기로 쓰지 않는다.
AI를 다음 세 가지 역할을 가진 시스템 구성 요소로 쓴다.

1. 문제를 작게 분해한다
2. 각 단계에서 검증 가능한 결과를 만든다
3. 실패 원인을 다음 작업자가 재현할 수 있게 남긴다

## Three Control Points

### 1. Scope Control

무엇을 지금 만들지 않는지 먼저 정한다.

현재 SignalBoard의 예:

- Kakao self-message는 한다
- Kakao friend-send는 지금 안 한다
- 웹 UI는 지금 안 한다
- 경제 지표는 지금 안 한다

이걸 먼저 고정해야 MVP가 빨리 나온다.

### 2. Interface Control

바깥 세상과 만나는 경계는 최대한 단순하고 명확해야 한다.

현재 주요 경계:

- `NaverSearchClient.fetch_listings(search_url)`
- `KakaoNotifier.send_text(message, web_url=...)`
- `AlertService.poll_watch(...)`

각 경계는 입력과 출력이 뚜렷해야 한다.

### 3. Verification Control

모든 구현은 실제 실행 가능한 검증 명령이 있어야 한다.

예:

- `python -m app.cli kakao-me`
- `python -m app.cli send-test-kakao`
- `python -m app.cli inspect-search-url "<url>"`
- `python -m app.cli preview-search "<url>"`
- `python -m app.cli poll-url "<url>" --no-send-kakao`

## Practical Rules

SignalBoard에서 Harness Engineering은 아래 규칙으로 실천한다.

1. 기능보다 먼저 “입력/출력/검증”을 정한다.
2. 구현 후 반드시 실행으로 확인한다.
3. 실패는 숨기지 말고 분류한다.
4. 불확실한 것은 문서와 task.md에 남긴다.
5. 복잡한 외부 연동은 fallback 경로를 남긴다.

## Example In This Project

### Example 1: Naver Search

문제:

- 신버전 `fin.land` URL은 직접 수집이 불안정함

Harness 방식 해결:

1. 신버전 URL을 구조화 필터로 파싱
2. 모바일 listing fetch 경로로 브리지
3. `preview-search`로 바로 검증

즉 “바로 API를 때려보는 해킹”이 아니라 “중간 모델을 만든 뒤 검증 가능한 경로로 우회”한 것이다.

### Example 2: Kakao Alert

문제:

- access token은 만료되고 OAuth 흐름이 있음

Harness 방식 해결:

1. token manager와 notifier를 분리
2. `kakao-me`로 토큰 검증
3. `send-test-kakao`로 발송 검증

즉 “메시지 보내기 전에 토큰 상태를 따로 확인할 수 있는 구조”를 만든 것이다.

## What Good Work Looks Like

좋은 작업은 이런 특징을 가진다.

- 한 문장으로 설명 가능하다
- 입력과 출력이 분명하다
- 검증 명령이 있다
- 실패했을 때 원인을 좁힐 수 있다
- 다음 AI가 이어받기 쉽다

## What Bad Work Looks Like

나쁜 작업은 이런 특징을 가진다.

- 구현은 했는데 검증이 없다
- 외부 연동 실패가 전부 같은 에러로 보인다
- 작은 문제를 UI나 인프라로 덮으려 한다
- 문서와 실제 코드 상태가 다르다

## Rule For Future Expansion

나중에 경제 지표, 대시보드, 학습 카드가 붙더라도 방식은 같다.

1. 작은 ingest unit을 만든다
2. 정규화 모델을 만든다
3. 검증 가능한 CLI/API를 만든다
4. 그 위에 UI를 얹는다

즉 SignalBoard는 앞으로 커져도 같은 방식으로 자라야 한다.
