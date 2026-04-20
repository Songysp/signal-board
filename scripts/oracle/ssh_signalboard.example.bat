@echo off
REM Copy this file to ssh_signalboard.bat and edit ORACLE_HOST / KEY_FILE.
set ORACLE_HOST=YOUR_ORACLE_PUBLIC_IP
set ORACLE_USER=opc
set KEY_FILE=%USERPROFILE%\.ssh\oracle-key.pem

ssh -i "%KEY_FILE%" %ORACLE_USER%@%ORACLE_HOST%
