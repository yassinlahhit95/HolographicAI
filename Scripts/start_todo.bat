@echo off
rem Abre TODO con un doble clic: el holograma + el asistente (microfono, IA, voz y webcam).
rem La webcam se enciende en cuanto el holograma esta abierto (aviso "CAMARA ON" en pantalla).
rem   start_todo.bat        = holograma en ventana
rem   start_todo.bat full   = holograma en pantalla completa (o usa start_todo_pantalla_completa.bat)
rem Para cerrar: Ctrl+C en la ventana del asistente y Alt+F4 en el holograma.
set MODE=
if /i "%~1"=="full" (set MODE=full& shift)
call "%~dp0start_hologram.bat" %MODE%
call "%~dp0start_assistant.bat" %1 %2 %3 %4
