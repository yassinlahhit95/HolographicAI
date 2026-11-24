**Do not build the entire project in one go.** Work with me in small, clear stages:
1. Inspect the existing files, software, and development environment first.
2. Briefly explain what you plan to do in the current stage.
3. Implement only the current stage.
4. Test the result yourself.
5. Tell me how to run it and what I should expect to see.
6. Do not move to the next stage until I confirm that the current one works.

I need practical, beginner-friendly guidance. Do not assume I am an experienced programmer. Do not give me theory or isolated code snippets without integrating and testing them.

## 2. Project concept

Create an interactive AI character: a floating futuristic human/robot head with a holographic appearance. It should initially run on my computer screen and later be suitable for a large display.

The character must look alive, not like a static 3D model or a robot moving mechanically.

**Important:** For this prototype, â€œholographicâ€ means a visual effect rendered on a normal screen using materials, lighting, a dark background, and visual effects. Do not assume I own a physical hologram device or transparent display.

## 3. Available hardware and software

- GPU: 6 GB VRAM â€” exact GPU model is not yet known.
- System RAM: 16 GB.
- Blender is installed.
- Unity is installed.
- Unreal Engine is installed (if by â€œReal Engineâ€ I meant Unreal Engine, verify this).
- Visual Studio Code is installed.
- Python is installed.
- I want to use my computer's built-in webcam, microphone, and speakers initially.
- I do not want to buy additional hardware for the first prototype.
- I prefer free and open-source tools and local processing wherever practical.
- Do not use paid APIs, subscriptions, or cloud services unless you ask for and receive my explicit approval.

Before installing anything, inspect what is already installed and its version. Do not reinstall existing software unnecessarily.

## 4. Choose one rendering engine

I have both Unity and Unreal Engine. Do not build the project in both engines.

Inspect their installed versions and the computer's capabilities. Then choose one engine for the prototype and explain why. Prioritize:
- Stable performance with 6 GB VRAM and 16 GB RAM.
- Straightforward integration with Python, microphone, and webcam.
- Facial animation, eye movement, and lip synchronization.
- Ease of future development.

Blender may be used to create or modify the 3D character. Use only the selected engine to render and animate it.

## 5. Visual appearance

Desired design:
- A floating futuristic head with a blue/cyan holographic appearance.
- Clear, attractive facial features and eyes that look as realistic as possible.
- Emissive lighting, subtle glow, and holographic transparency/gradients where appropriate.
- A dark background so the holographic effect is clearly visible.
- A clean, polished appearance â€” not childish, cartoon-like, or pixel-art.
- Avoid excessive particles and effects that reduce facial clarity or performance.

Do not create an unnecessarily complex model before confirming that it can be animated. The face should support animation, especially:
- Eyelids and eyes.
- Jaw and lips.
- Head and neck.
- Basic facial expressions, if supported by the model.

If the selected model does not have suitable bones or blend shapes, tell me before building the animation system around it.

## 6. Continuous lifelike movement â€” a core requirement

The character must remain alive even when it is not speaking or interacting.

### Eyes
- Natural, irregular blinking rather than blinking at an exact fixed interval.
- An initial approximate interval of 2â€“5 seconds, with reasonable variation.
- Smooth eyelid closing and opening.
- Small eye movements to the sides and occasionally downward, with natural pauses.
- Avoid fast or exaggerated random eye movements.
- Avoid mechanical synchronized blinking or repeating exactly the same movement.

### Head and body
- Very subtle, slow head movements from side to side.
- Occasional slight head tilts.
- Extremely subtle breathing-like movement if the model supports it.
- Smooth transitions between movements, with no shaking or sudden jumps.
- Avoid an obviously repetitive animation loop.

### Expressions
- A subtle smile during the greeting.
- An attentive expression while listening.
- A slight head tilt while thinking.
- Avoid exaggerated expressions.

### Important architecture principle
Keep these two systems separate:

1. **Autonomous/Idle Animation:** Runs continuously inside the rendering engine and does not depend on internet access or AI response speed.
2. **AI Interaction:** Sends state commands such as listening, thinking, speaking, and greeting.

The eyes and head must never freeze just because the AI model is taking time to generate an answer.

## 7. First startup introduction

When the application starts, the character should speak an introduction in English, followed by Spanish. Use the following text exactly for the first version:

**English:**
â€œHello! Welcome. I am a prototype, the first version of an idea brought to life by my friend Yassin. It is a pleasure to meet you!â€

**Spanish:**
â€œÂ¡Hola! Bienvenido. Soy un prototipo, la primera versiÃ³n de una idea hecha realidad por mi amigo Yassin. Â¡Es un placer conocerte!â€

After the introduction:
- The character enters standby/listening mode.
- Do not repeat the introduction automatically except when the application is restarted or when explicitly requested.
- Provide an easy way to replay the introduction during testing.

Do not start voice conversation before the introduction finishes, unless we decide to change this later.

## 8. Voice interaction and languages

The long-term goal is to speak to the character through the computer microphone and hear its spoken responses through the speakers.

Required flow:
1. Capture audio from the microphone.
2. Detect when speech starts and ends (Voice Activity Detection).
3. Convert speech to text (Speech-to-Text).
4. Identify the language being used.
5. Generate a response in the same language whenever possible.
6. Convert the response text into speech (Text-to-Speech).
7. Play the audio and animate the mouth in synchronization with it.

Start by testing English and Spanish. After those work, test French and Arabic, then evaluate Moroccan Darija and Basque separately. **Do not assume that any model supports every language or dialect well; test them in practice.**

Prefer free local solutions:
- A small local language model through Ollama or another suitable option.
- Whisper or another local speech recognition tool.
- A free local TTS engine, after checking voice quality, language availability, and licenses.

Do not choose a large model before measuring VRAM and RAM usage. With 6 GB VRAM and 16 GB RAM, begin with lightweight, appropriately quantized models and monitor memory usage. Avoid running several heavy models at the same time.

## 9. Webcam

Use the computer's built-in webcam initially, but do not identify who a person is.

First stage:
- Detect only whether a person is present in front of the camera, if this can be done reliably.
- When a person is detected, the character may orient its gaze approximately toward the camera.
- Do not store images or video.
- Do not activate the camera or record without making its active status clear to the user.

Person detection must not be required for the character's idle animation. The character must remain alive even when nobody is in front of the camera.

## 10. Character states

Create clear, testable states:

- **Idle:** Blinking and subtle eye/head movement.
- **Greeting:** Looks forward, smiles, and delivers the introduction.
- **Listening:** Focuses its gaze toward the speaker and appears attentive.
- **Thinking:** Makes a subtle head movement while processing the response.
- **Speaking:** Moves its lips in synchronization with the audio.
- **No person:** Returns to a calm idle behavior without becoming completely still.

State transitions must be smooth. Do not let one state disable the basic blinking and eye movement system.

## 11. Suggested technical architecture

Python can act as a local bridge between audio, webcam, AI processing, and the rendering engine.

Initial architecture:
- Blender: prepare the 3D character and materials.
- Unity or Unreal (choose only one): render the head, animation, and visual effects.
- Python: manage microphone, webcam, speech recognition, language model, and speech synthesis.
- Local communication between Python and the rendering engine, for example through WebSocket or HTTP on the same computer.

This is a proposed architecture, not a fixed decision. Check compatibility first and choose the simplest stable solution. Do not add servers, databases, or cloud services that are not needed.

## 12. Performance requirements

Available computer memory:
- 6 GB VRAM.
- 16 GB RAM.

Performance rules:
- Start with one head and a simple scene.
- Do not use expensive post-processing effects without measuring their impact.
- Monitor GPU, VRAM, RAM, and CPU usage.
- Avoid loading multiple AI models at the same time.
- If performance is poor, reduce model complexity, rendering resolution, or AI model size before adding features.
- Do not promise instant responses or real-time conversation before testing performance on this computer.

## 13. Required implementation stages

### Stage 0 â€” Inspect the computer and installed software
- Identify the operating system.
- Identify the exact GPU model and actual VRAM.
- Check RAM and versions of Python, Blender, Unity, and Unreal Engine.
- Check whether Ollama and audio tools are already installed.
- Do not install anything before showing me the installation plan.
- Give me a short report and recommend one rendering engine.

### Stage 1 â€” Animated visual prototype
- Create or import a suitable head model.
- Render it with a black background and holographic appearance.
- Add blinking, eye movement, and subtle head movement.
- Keep the animation running continuously without any AI.
- Test smoothness and performance.

**Success criteria:** I can see the holographic head on screen. It blinks, looks around, and moves subtly and naturally even when there is no interaction.

### Stage 2 â€” Voice introduction and audio
- Play the English introduction followed by the Spanish introduction.
- Connect audio playback and set up acceptable mouth movement timing.
- Add a command to replay the introduction.
- Test the microphone separately if practical, but do not add AI conversation yet.

**Success criteria:** I can hear the introduction in both languages and see acceptable mouth movement synchronized with the speech.

### Stage 3 â€” Listening and responses
- Connect the microphone.
- Detect speech and convert it to text.
- Connect a lightweight local language model.
- Generate spoken responses.
- Show listening, thinking, and speaking states.

**Success criteria:** I can ask a simple question in English or Spanish and receive an understandable spoken response.

### Stage 4 â€” Webcam
- Detect whether a person is present.
- Orient the character's gaze approximately toward the person.
- Test lighting and distance.
- Respect privacy and do not save video.

### Stage 5 â€” Improve realism and expand
- Improve eye movement and facial expressions.
- Improve lip synchronization.
- Add more languages only after testing them.
- Improve interruption handling and response speed.
- Prepare the application for a large display.

Do not begin a new stage until the previous stage's success criteria have been met.

## 14. File and code working rules

- Inspect the existing project before creating a new one.
- Do not delete or replace existing files without telling me.
- Do not make broad system or software configuration changes without my approval.
- Create a backup before major changes.
- Use clear file and folder names.
- Never put passwords or API keys directly in source code.
- Write run instructions in a README using simple English or Spanish.
- If an error occurs, read the full error message and identify the cause. Do not hide errors with random changes.
- After each stage, list the files you created or modified and explain how to run the project.

## 15. Your first task

Start with **Stage 0 only**.

1. Inspect the computer and available software without changing anything.
2. Identify the exact GPU model. The information that it has 6 GB VRAM is not sufficient by itself.
3. Verify whether â€œReal Engineâ€ refers to Unreal Engine.
4. Compare Unity and Unreal for this specific project, then recommend one.
5. Give me a short report containing:
   - The hardware specifications you verified.
   - The engine you recommend and why.
   - Only the additional tools we actually need.
   - The plan for Stage 1.
6. Wait for my approval before installing tools or creating the project.

**Final goal:** A holographic assistant that can speak with visitors. The immediate priority is to create a beautiful, lifelike head with natural blinking and subtle, smooth movements, then add voice, and finally connect the AI step by step.