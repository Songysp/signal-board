# Oracle Cloud 배포 가이드

이 문서는 Oracle Cloud VM에서 SignalBoard를 Docker Compose로 실행하는 방법입니다.

관리자 보드는 인터넷에 직접 공개하지 않고, **SSH 터널로 접속**하는 방식을 추천합니다.

## 최종 구조

```text
Oracle VM
├─ postgres 컨테이너
├─ app 컨테이너      관리자 화면 / API
└─ worker 컨테이너   4시간마다 poll-loop 실행
```

알림은 Slack Webhook을 기본으로 사용합니다. Kakao는 일단 비워둬도 됩니다.

## 1. 서버 최초 세팅

Oracle VM에 SSH로 접속한 뒤 아래 명령을 실행합니다.

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Songysp/signal-board/main/scripts/oracle/bootstrap_oracle.sh)
```

이 스크립트가 하는 일:

- Docker 설치
- git 설치
- SignalBoard repo clone
- `.env.prod.example`을 `.env`로 복사

완료되면:

```bash
cd ~/signal-board
nano .env
```

## 2. `.env` 수정

최소한 아래 값은 바꿔주세요.

```env
POSTGRES_PASSWORD=긴_랜덤_비밀번호
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SIGNALBOARD_ADMIN_TOKEN=긴_랜덤_관리자_토큰
```

검색 URL을 기본값으로 넣고 싶으면:

```env
NAVER_SEARCH_URL=https://new.land.naver.com/...
```

Kakao를 당장 안 쓸 거면 아래 값들은 비워둬도 됩니다.

```env
KAKAO_REST_API_KEY=
KAKAO_ACCESS_TOKEN=
KAKAO_REFRESH_TOKEN=
```

## 3. 배포 실행

서버에서:

```bash
cd ~/signal-board
./scripts/oracle/deploy_oracle.sh
```

이 스크립트가 하는 일:

- 최신 main pull
- Docker 이미지 build
- postgres/app/worker 컨테이너 실행
- DB 초기화
- doctor 점검

## 4. 관리자 보드 접속

관리자 보드는 Oracle 서버 내부 `127.0.0.1:8000`에만 열립니다.

내 Windows PC에서 SSH 터널을 엽니다.

```powershell
ssh -i C:\Users\song\.ssh\oracle-key.pem -L 8000:127.0.0.1:8000 opc@오라클서버IP
```

그 다음 브라우저에서 접속합니다.

```text
http://127.0.0.1:8000/
```

`SIGNALBOARD_ADMIN_TOKEN`을 설정했다면 관리자 화면의 `관리 토큰` 입력칸에 같은 값을 넣고 저장하세요.

## 5. Windows 배치 파일로 접속 쉽게 하기

아래 파일을 복사합니다.

```text
scripts\oracle\tunnel_signalboard.example.bat
```

복사한 파일 이름 예:

```text
tunnel_signalboard.bat
```

파일 안의 값을 수정합니다.

```bat
set ORACLE_HOST=오라클서버IP
set ORACLE_USER=opc
set KEY_FILE=%USERPROFILE%\.ssh\oracle-key.pem
set LOCAL_PORT=8000
```

이후에는 `tunnel_signalboard.bat`을 더블클릭하면 터널이 열립니다.

일반 SSH 접속용 템플릿도 있습니다.

```text
scripts\oracle\ssh_signalboard.example.bat
```

## 6. 로그 보기

서버에서:

```bash
cd ~/signal-board
./scripts/oracle/logs_oracle.sh app
./scripts/oracle/logs_oracle.sh worker
./scripts/oracle/logs_oracle.sh postgres
```

직접 Docker 명령으로 봐도 됩니다.

```bash
docker compose -f compose.prod.yaml logs -f worker
```

## 7. 재배포

서버에서:

```bash
cd ~/signal-board
./scripts/oracle/deploy_oracle.sh
```

## 8. 중지

```bash
cd ~/signal-board
docker compose -f compose.prod.yaml down
```

주의: volume을 삭제하지 않으면 DB 데이터는 유지됩니다.

## 9. DB 백업

```bash
cd ~/signal-board
./scripts/oracle/backup_oracle.sh
```

백업 파일은 기본적으로 아래에 생성됩니다.

```text
~/signalboard-backups/
```

## 10. 운영 전 체크

배포 후 아래를 확인하세요.

```bash
docker compose -f compose.prod.yaml ps
docker compose -f compose.prod.yaml exec app python -m app.cli doctor --no-check-kakao
```

내 PC에서:

```powershell
ssh -i C:\Users\song\.ssh\oracle-key.pem -L 8000:127.0.0.1:8000 opc@오라클서버IP
```

브라우저:

```text
http://127.0.0.1:8000/
```

## 11. 안전 원칙

- 관리자 보드는 직접 인터넷에 공개하지 않습니다.
- SSH 터널로만 접속합니다.
- worker는 기본 4시간 간격으로 poll합니다.
- 4시간보다 짧은 무인 polling은 쓰지 않습니다.
- Naver 차단, Captcha, 로그인 제한을 우회하지 않습니다.
- `.env`는 절대 Git에 올리지 않습니다.
