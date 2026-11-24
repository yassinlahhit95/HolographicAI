@echo off
rem Renders 3 preview images into "UnrealProject 5.8\Saved\Preview" and closes Unreal.
rem Close the Unreal editor before running this.
echo Rendering preview... (takes 1-3 minutes)
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" "%~dp0..\UnrealProject 5.8\HolographicAI.uproject" -ExecCmds="py %~sdp0preview_render.py" -nosplash -abslog="%TEMP%\holo_preview.log"
echo Done. Images are in "%~dp0..\UnrealProject 5.8\Saved\Preview"
