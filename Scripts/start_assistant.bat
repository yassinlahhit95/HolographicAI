@echo off
rem Stage 3+4 - voice assistant (microphone -> Whisper -> Qwen/Ollama -> Chatterbox -> hologram)
rem              + webcam (only detects WHERE a face is; no images saved). Add --no-camera to disable.
rem 1) First open the hologram: start_hologram.bat
rem 2) Then run this. It waits for the introduction to finish and starts listening.
rem Ctrl+C = stop.
title Holographic AI - assistant
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set TRANSFORMERS_VERBOSITY=error
rem sin barras de progreso ni avisos internos de las librerias (la ventana se lee mejor)
set TQDM_DISABLE=1
set PYTHONWARNINGS=ignore
set HF_HUB_DISABLE_PROGRESS_BARS=1
"%~dp0..\Tools\tts\.venv\Scripts\python.exe" "%~dp0assistant.py" %*
pause
