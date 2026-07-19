@echo off
chcp 65001 >nul
title Xiaomi 13 Font Module Maker v1.3 - lzhp529
set "FONT_MODULE_MAKER_SCRIPT_ROOT=%~dp0"
set "TEMP_SCRIPT=%TEMP%\FontModuleMaker-%RANDOM%-%RANDOM%.ps1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "[IO.File]::WriteAllText('%TEMP_SCRIPT%', [IO.File]::ReadAllText('%~dp0FontModuleMaker.ps1', [Text.Encoding]::UTF8), (New-Object Text.UTF8Encoding($true)))"
if errorlevel 1 exit /b 1
powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -File "%TEMP_SCRIPT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
del /q "%TEMP_SCRIPT%" >nul 2>&1
echo.
pause
exit /b %EXIT_CODE%
