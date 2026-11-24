@echo off
rem Opens the holographic head in a window (no editor needed).
rem   start_hologram.bat        = ventana
rem   start_hologram.bat full   = pantalla completa
rem Teclas y raton:
rem   F11 o doble clic          = pantalla completa / ventana
rem   arrastrar (boton izq.)    = girar alrededor de la cabeza
rem   rueda                     = acercar / alejar
rem   arrastrar (boton dcho.)   = desplazar la vista
rem   clic central o C          = vista inicial
rem   H = ocultar/mostrar textos de estado   R = repetir la presentacion   Alt+F4 = cerrar
set HOLOFULL=
if /i "%~1"=="full" set HOLOFULL=-holofull
echo Starting the hologram... (the first start can take a few minutes)
start "" "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0..\UnrealProject 5.8\HolographicAI.uproject" /Game/Hologram/L_Hologram -game -windowed -ResX=1280 -ResY=720 -nosplash %HOLOFULL%
