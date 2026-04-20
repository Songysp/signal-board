@echo off
REM Copy this file to tunnel_signalboard.bat and edit ORACLE_HOST / KEY_FILE.
set ORACLE_HOST=YOUR_ORACLE_PUBLIC_IP
set ORACLE_USER=opc
set KEY_FILE=%USERPROFILE%\.ssh\oracle-key.pem
set LOCAL_PORT=8000

echo Open http://127.0.0.1:%LOCAL_PORT%/ after this tunnel connects.
ssh -i "%KEY_FILE%" -L %LOCAL_PORT%:127.0.0.1:8000 %ORACLE_USER%@%ORACLE_HOST%
