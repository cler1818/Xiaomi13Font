@echo off
chcp 65001 >nul
title Xiaomi13Font - lzhp529
set "SCRIPT=%~dp0Xiaomi13Font.ps1"
set "XIAOMI13FONT_SCRIPT_ROOT=%~dp0"

if not exist "%SCRIPT%" (
  echo Xiaomi13Font.ps1 was not found. Keep CMD and PS1 in the same folder.
  if not defined XIAOMI13FONT_NOPAUSE pause
  exit /b 1
)

set "TEMP_SCRIPT=%TEMP%\Xiaomi13Font-%RANDOM%-%RANDOM%.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "[IO.File]::WriteAllText('%TEMP_SCRIPT%', [IO.File]::ReadAllText('%SCRIPT%', [Text.Encoding]::UTF8), (New-Object Text.UTF8Encoding($true)))"
if errorlevel 1 (
  echo Failed to prepare the temporary PowerShell script.
  if not defined XIAOMI13FONT_NOPAUSE pause
  exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TEMP_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
del /q "%TEMP_SCRIPT%" >nul 2>&1

echo.
if not "%EXIT_CODE%"=="0" echo Operation failed. Exit code: %EXIT_CODE%
if not defined XIAOMI13FONT_NOPAUSE pause
exit /b %EXIT_CODE%
