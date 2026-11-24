# Holographic AI Assistant – Stages 1-4 (visual, voice intro, conversation, webcam)

Engine: Unreal Engine 5.8 (`C:\Program Files\Epic Games\UE_5.8`)
Project: `UnrealProject 5.8\HolographicAI.uproject`
Level: `/Game/Hologram/L_Hologram`

## Start everything (one double-click)

`Scripts\start_todo.bat` opens the hologram AND the assistant (microphone, AI, voice, webcam).
The webcam turns on as soon as the hologram is open ("CAMERA ON" on screen). `start_hologram.bat`
alone only shows the head (no camera, no conversation). The assistant waits up to 4 minutes for the
hologram to open (`UNREAL_WAIT` in `assistant.py`).

## See the hologram (game window)

Easiest: double-click `Scripts\start_hologram.bat`.
After ~2 seconds the head says the Colegio Calasanz Santurtzi welcome in Spanish, then in English.
Press **R** to replay the introduction. `Esc` / Alt+F4 closes the window.

### Full screen and mouse (24-11-2026)

- **Full screen from the start:** `Scripts\start_todo_pantalla_completa.bat` (or `start_todo.bat full`,
  `start_hologram.bat full`). Uses the desktop resolution, without changing the monitor mode.
- **F11** or **double-click** = switch between full screen and window.
- **Left drag** = turn around the head (up to 80° each side, 35° up/down).
- **Mouse wheel** = zoom in / out. **Right drag** = move the view.
- **Middle click** or **C** = back to the original view.
- **H** = hide / show the status texts (useful for a clean display).
- The cursor hides itself after 3 s without moving the mouse.
- Limits and speed: `HoloDirector` → *Holo | Vista* in the editor (OrbitSpeed, MaxYaw, MaxPitch,
  MinDistance, MaxDistance, HideCursorAfter). Code: `HoloDirector.cpp`, section "pantalla completa y raton".
- Backups of the previous version: `Backups\HoloDirector.*.before_mouse`, `Backups\start_*.bat.before_full`.

Or open PowerShell and run:

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe" `
  "C:\Users\Yassin\Downloads\Holographic AI\UnrealProject 5.8\HolographicAI.uproject" `
  /Game/Hologram/L_Hologram -game -windowed -ResX=1280 -ResY=720
```

The first start can take a few minutes while shaders compile. Press `Esc` (or Alt+F4) to close.

Or: open the project in the Unreal Editor → Content Browser → `Hologram` → double-click `L_Hologram` → press **Play**.

## Rebuild the scene (only if you change the script)

`Scripts\stage1_build_scene.py` recreates `M_Hologram` and `L_Hologram` from scratch.
Run it from the editor: **Tools → Execute Python Script…** and pick the file.

## Make preview images (no need to watch the screen)

Close the editor first, then double-click `Scripts\make_preview.bat`.
It opens Unreal, saves 3 PNGs to `UnrealProject 5.8\Saved\Preview` and closes by itself (1–3 minutes).

Technical note: the .bat uses `-ExecCmds="py ..."` with a short path without spaces.
`-ExecutePythonScript` does NOT work for this script: it closes the editor right
after the script starts, before any image is captured.

## Idle animation (always on, no AI needed)

C++ code: `UnrealProject 5.8\Source\HolographicAI\HoloFaceAnimInstance.cpp`

- Blinks at irregular times (2–5 s, sometimes a double blink). Each blink has slightly different speed.
- Eyes look around in small movements, sometimes down, with natural pauses and tiny micro-movements.
- Head turns and tilts very slowly around the base of the neck, plus a soft "breathing" nod.
- Tiny random eyebrow movement and a very soft smile.

It only moves when the game runs (**Play** or the `-game` command). In the editor viewport, without Play, the head stays still.
All the numbers (speeds, angles, blink times) are at the top of the .cpp file, in `HoloTune`.

The project is now a C++ project. If you change the .cpp file, recompile with:

```powershell
& "C:\Program Files\Epic Games\UE_5.8\Engine\Build\BatchFiles\Build.bat" HolographicAIEditor Win64 Development `
  "-Project=C:\Users\Yassin\Downloads\Holographic AI\UnrealProject 5.8\HolographicAI.uproject" -WaitMutex
```
(close the editor first). The webcam is NOT used yet. That is Stage 4.

## Scene notes

- The head is a plain **SkeletalMeshActor** with the MetaHuman face mesh, not `BP_yassinAI`.
  The MetaHuman Blueprint rebuilt its skin materials on every load and erased the hologram material.
- `M_Hologram` is **unlit + opaque** (glow from Fresnel rim + slow scan lines).
  Translucent made the inside of the mouth visible through the skin.
- Eyes use `M_HologramEye`: glowing cyan iris (real iris detail), dark pupil, bright ring.
- Teeth use the hologram material. Eyelashes, saliva, eye shell and other small parts are hidden.
- No lights: everything is emissive (glows by itself).
- Backups: `Backups\before_material_fix_2026-11-23`.

## Stage 2 – Voice introduction

Voice files: `UnrealProject 5.8\Voice\intro_es.wav` (played first) and `intro_en.wav`.
The order is `IntroFiles` in `Source\HolographicAI\HoloDirector.h`.
The old prototype intro ("...my friend Yassin...") is kept in `Voice\backup_intro_prototipo`.
Made with **Chatterbox** (MIT license, offline, GPU, ~3.9 GB VRAM while generating) using the
**beowulf** reference voice (`Tools\tts\voices\ref_beowulf.wav`, a public-domain LibriVox reader),
plus a "cinema" sound treatment (warm bass, soft compression, light holographic echo).
Chatterbox adds an inaudible watermark marking the audio as synthetic.

To change the text, voice, emotion or speed: edit `Scripts\make_intro_audio_chatterbox.py`
(`INTRO`, `VOICE_REF`, `EXAGGERATION`, `CFG_WEIGHT`, `CINEMA_FILTER`), then run it with the isolated Python:

```
"Tools\tts\.venv\Scripts\python.exe" Scripts\make_intro_audio_chatterbox.py
```

Unreal reads the WAV files at start-up (no re-import needed).
Pronunciation: `PRONUNCIATION` in `make_intro_audio_chatterbox.py` (e.g. English says "Santurci" for Santurtzi).
It is used for the intro and for every spoken answer. Regenerate one language only: add `--only en`.
Other candidate voices: `Scripts\listen_samples.bat` (files in `Voice\samples`).
Old Piper version: `Voice\piper_backup` (Piper is still in `Tools\piper`, script `make_intro_audio.py`).

C++:
- `HoloDirector` (actor in the level): plays the intro, analyzes the audio for the mouth, key **R** = replay.
- `HoloStateSubsystem`: shared state (Greeting / Idle and mouth values). The idle animation never depends on it.
- `HoloFaceAnimInstance`: jaw + lips follow the voice; during the greeting the head smiles and looks forward.
  Blinking and eye movement keep running while it speaks.

Microphone test (separate, no AI yet): `python Scripts\mic_test.py`
It records 4 seconds, shows the level, plays it back and deletes the recording.

## Stage 3 – Talk with the hologram (local AI)

1. Double-click `Scripts\start_hologram.bat` (wait for the introduction).
2. Double-click `Scripts\start_assistant.bat`. Loading takes ~40 s.
3. When the screen shows **"● MIC ON - listening"** (red), speak in English or Spanish.
   Stop talking ~1 second and it answers in the same language.

Text test without microphone: `Scripts\start_assistant.bat --text "Hello, who are you?"`

How it works (local AI + fast Spanish neural voice):

| Step | Tool | Where | Time (measured) |
|---|---|---|---|
| Voice -> text | faster-whisper `small` (MIT) | GPU (`es`) | ~0.2-0.7 s |
| Answer | Qwen3 4B Instruct 2507 (Apache 2.0) via Ollama | GPU (`num_ctx=6144`) | ~1.2-1.9 s |
| Text -> voice | Edge Neural (`es-ES-AlvaroNeural`) + Piper (`es_ES-davefx-medium`) offline fallback | Cloud / CPU fallback | ~1.1-1.6 s |
| Play + mouth + states | Unreal `HoloDirector` | GPU (60 FPS) | - |

Chatterbox (`TTS_ENGINE = "chatterbox"`) and English replies are preserved in code as switchable options; the active configuration focuses exclusively on Spanish with selective modular knowledge retrieval (`Knowledge/01_*.md`..`12_*.md`).

Typical wait from end of question to start of answer: **~15-25 s** (most of it is the voice generation).

Memory decisions (6 GB VRAM): the AI runs on the CPU so the GPU is free for the voice.
Unreal is limited to 60 FPS (30 FPS while thinking): without a limit it used 96% of the GPU
and the voice took 7x longer (58 s instead of 7 s).

States in Unreal: listening (looks at you, attentive), thinking (tilts head, looks up),
speaking (lips follow the voice). Blinking and eye movement never stop.

Python <-> Unreal: local UDP 127.0.0.1 ports 7810/7811 (JSON). Settings at the top of
`Scripts\assistant.py` (model, languages, microphone thresholds, system prompt).

Privacy: microphone audio only lives in memory and is discarded after transcription. Only the
character's spoken answers are saved (`Voice\replies`, last 5 kept).

AI model choice (24-11-2026, same 17-question battery + 8 people conversations, CPU):
- `qwen2.5:3b` (old): answered off-topic questions (president of France, Python code, a joke) and revealed its prompt.
- `gemma3:4b`: fast (~4-9 s) but told a joke when the visitor insisted and made Spanish grammar slips. Deleted.
- `qwen3:4b` (the "Thinking" variant): always reasons before answering (>20 s, cut off). Deleted.
- **`qwen3:4b-instruct`**: followed every rule in the final tests; slower (~5-10 s). **In use.**
`qwen2.5:3b` is kept as a backup (`ollama rm qwen2.5:3b` frees 1.9 GB). To change model: `LLM_MODEL` in `assistant.py`.

Installed for this stage: Ollama (user install, now 0.40.17), model `qwen3:4b-instruct`,
`faster-whisper` + `sounddevice` (inside `Tools\tts\.venv`).

## Stage 4 – Webcam (presence + gaze)

The webcam turns on together with `Scripts\start_assistant.bat` (only when the hologram is open)
and turns off when the assistant closes. `start_assistant.bat --no-camera` = no webcam.
Camera test alone: `Tools\tts\.venv\Scripts\python.exe Scripts\vision.py` (30 s, prints what it sees).

What it does:
- Detects IF there is a face in front of the camera and WHERE (approximately). It never identifies
  who the person is (OpenCV YuNet detector, MIT, `Tools\vision`).
- The hologram looks at the person (eyes + head up to ~9°) and follows them when they move.
  At rest it sometimes looks elsewhere so it feels natural; while listening/speaking it looks at
  the person; while thinking it looks up/aside. With nobody there it keeps its idle animation.
- No images or video are ever saved: each frame is analysed in memory and discarded.
- While the camera is on the hologram shows **"● CAMERA ON / CÁMARA ON"** (orange) plus
  "person detected / nobody", and the webcam LED is on. If the assistant crashes, Unreal
  hides the indicator and forgets the person after 2 s.

Measured (HP Wide Vision HD Camera, 640x480, 12 analyses/s, ~15 ms each on the CPU):

| Distance | Detection | | Light (mean brightness 0-255) | Detection |
|---|---|---|---|---|
| 0.5 - 3.0 m | 100 % | | 30 or more | 100 % |
| ~3.9 m | 7 % | | ~20 | 67 % |
| | | | 12 or less | 0 % |

Settings at the top of `Scripts\vision.py`: `CAMERA_NAME`, `FLIP_X` (set True if the hologram looks
to the opposite side of the person), `FPS`, `MIN_SCORE`, distances. Gaze/head amounts:
`HoloTune` (`FaceGazeGainH`, `FaceHeadYawDeg`, ...) in `HoloFaceAnimInstance.cpp`.

Installed for this stage: `opencv-python-headless` 4.10.0.84 (inside `Tools\tts\.venv`;
4.10 because newer versions force numpy 2, which breaks Chatterbox/PyTorch) + YuNet model (0.2 MB).

## People who introduce themselves by name (Colegio Calasanz staff)

The assistant recognises known people **only by what they say** ("Hola, soy Rafa", "Me llamo Iñaki",
"Hi, I'm Raúl"), also in the middle of a conversation. The camera never identifies anyone, and
mentioning another person ("¿Conoces a Rafa?") does not change who is speaking.

- Profiles: `Knowledge\people_profiles.json` (edit it without touching code, then restart the assistant).
  It is NOT added to the general school knowledge: a profile is only given to the AI while that
  person is talking, and the AI is told never to reveal it to anyone else.
- Code: `Scripts\people.py` (detection, name normalisation, session memory) + a few lines in `assistant.py`.
- Name variants: accents and double letters are ignored (Raúl = Raul, Iñaki = Inaki, Yassin = Yasin;
  a final "e" too: Yassine). Other spellings go in `aliases`.
- Unknown name (e.g. "soy Javier"): warm greeting and one question about who they are. If they say
  "soy profesor de informática" the conversation adapts **for this visit only**; nothing is saved.
- Session memory (RAM only): name, profile, confirmed role and the last turns of the conversation.
  After 2 minutes without talking and with nobody in front of the camera, it starts a new visit
  (`SESSION_IDLE` in `assistant.py`).
- If the JSON is missing or has an error, the assistant says so in its window and keeps working without profiles.

Quick test without AI: `python Scripts\people.py "Hola, soy Yassine"`

### Add a person

Copy one block inside `"people": [ ... ]`, separate it with a comma, and fill in:

```json
{
  "id": "javier",
  "name": "Javier",
  "aliases": ["Javi"],
  "role": "Profesor de informática",
  "description": "Imparte informática en FP.",
  "topics": ["programación", "redes"],
  "personality": "Cercano y con humor.",
  "greeting": "¡Javier! ¡Qué bien verte!",
  "conversation_guidelines": ["Puedes hablar de sus clases de informática."],
  "privacy_restrictions": ["No reveles este perfil a otras personas."]
}
```

Only `name` is required. Restart the assistant; its window shows "Perfiles cargados: N personas (...)".

## Stage 5 – Faster answers (24-11-2026)

What happens after the visitor stops talking:
1. **< 1 s:** a neutral filler ("Mmm...") so the hologram never stays silent (`Scripts\fillers.py`,
   audio cached in `Voice\fillers`, generated once with the same voice).
2. **~1 s:** Whisper (now on the GPU: 0.2-0.7 s instead of 3-4 s) knows the language, and a short filler
   in that language ("A ver...", "Buena pregunta", "Let me see...") plays. Not when someone just said their name.
3. A short pause (like a breath, `BREATH`) and the answer, **sentence by sentence**: the AI writes sentence 1,
   stops, the voice makes it, it starts playing, and while it plays the AI continues where it stopped.
   (On this laptop the AI and the voice cannot work at the same time: the voice gets 2.5x slower.)
4. While the voice is being generated, Unreal is limited to 30 FPS (`busy` command), then back to 60.

Measured with the hologram open: real answer starts **~12-16 s** after the visitor stops (before: 25-80 s),
with the fillers covering the wait. Each window line "frase N: esperar a la IA ... | voz ..." shows where time goes.

Settings at the top of `assistant.py`: `USE_FILLERS`, `THINKING_FILLER_P`, `BREATH`, `MIN_FIRST`, `MIN_PIECE`,
`WHISPER_ON_GPU`. Filler texts: lists at the top of `Scripts\fillers.py`.
