# Etapa 2 - Genera el audio de la presentacion (ingles + espanol) con Piper (local, sin internet).
# Salida: "UnrealProject 5.8/Voice/intro_en.wav" y "intro_es.wav" (16 bits, mono, 22050 Hz).
# Unreal carga estos WAV al arrancar, asi que basta con volver a ejecutar este
# script si cambias el texto o la voz.
#
# Uso:  python "Scripts/make_intro_audio.py"
import os
import subprocess
import sys
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPER = os.path.join(ROOT, "Tools", "piper", "piper.exe")
VOICES = os.path.join(ROOT, "Tools", "piper", "voices")
OUT_DIR = os.path.join(ROOT, "UnrealProject 5.8", "Voice")

# Texto exacto de la primera version (ver "Holographic AI Assistant.md", seccion 7).
INTRO = [
    ("intro_en.wav", "en_US-joe-medium.onnx",
     "Hello! Welcome. I am a prototype, the first version of an idea brought to life "
     "by my friend Yassin. It is a pleasure to meet you!"),
    ("intro_es.wav", "es_ES-davefx-medium.onnx",
     "¡Hola! Bienvenido. Soy un prototipo, la primera versión de una idea hecha realidad "
     "por mi amigo Yassin. ¡Es un placer conocerte!"),
]

# 1.0 = velocidad normal de la voz; un poco mas alto = mas pausado y claro.
LENGTH_SCALE = "1.08"
SENTENCE_SILENCE = "0.30"   # segundos de pausa entre frases


def main():
    if not os.path.isfile(PIPER):
        sys.exit("No encuentro Piper en: " + PIPER)
    os.makedirs(OUT_DIR, exist_ok=True)
    for out_name, voice, text in INTRO:
        out = os.path.join(OUT_DIR, out_name)
        model = os.path.join(VOICES, voice)
        cmd = [PIPER, "--model", model, "--output_file", out,
               "--length_scale", LENGTH_SCALE, "--sentence_silence", SENTENCE_SILENCE]
        r = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True)
        if r.returncode != 0 or not os.path.isfile(out):
            print(r.stderr.decode("utf-8", "replace"))
            sys.exit("Piper fallo con " + voice)
        with wave.open(out, "rb") as w:
            secs = w.getnframes() / float(w.getframerate())
            print("OK %-13s %.1f s  %d Hz  %d bits  %d canal(es)" % (
                out_name, secs, w.getframerate(), w.getsampwidth() * 8, w.getnchannels()))


if __name__ == "__main__":
    main()
