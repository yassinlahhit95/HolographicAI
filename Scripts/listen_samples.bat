@echo off
rem Plays the 4 voice candidates (English + Spanish) one after another.
setlocal
set "S=%~dp0..\UnrealProject 5.8\Voice\samples"
for %%V in (beowulf invisible moby great) do (
  echo.
  echo ===== Voice: %%V =====
  powershell -NoProfile -Command "(New-Object Media.SoundPlayer '%S%\intro_en_%%V.wav').PlaySync(); Start-Sleep -Milliseconds 500; (New-Object Media.SoundPlayer '%S%\intro_es_%%V.wav').PlaySync()"
  timeout /t 2 >nul
)
echo.
echo Done. Tell Claude which voice you prefer: beowulf, invisible, moby or great.
pause
