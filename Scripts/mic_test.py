# Etapa 2 - Prueba del microfono (separada; todavia no hay conversacion con IA).
# Graba 4 segundos, muestra el nivel, lo reproduce por los altavoces y BORRA la grabacion.
# No guarda nada. Usa ffmpeg (ya instalado) y winsound (incluido en Python).
#
# Uso:  python "Scripts/mic_test.py"          (microfono interno por defecto)
#       python "Scripts/mic_test.py" --list   (ver microfonos disponibles)
import os
import re
import subprocess
import sys
import tempfile
import wave
import winsound

SECONDS = 4
PREFERRED = ["Smart Sound", "Micr"]    # el microfono interno del portatil


def list_mics():
    r = subprocess.run(["ffmpeg", "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
                       capture_output=True)
    text = r.stderr.decode("utf-8", "replace")
    return re.findall(r'"([^"]+)" \(audio\)', text)


def pick_mic(mics):
    for key in PREFERRED:
        for m in mics:
            if key.lower() in m.lower() and "virtual" not in m.lower():
                return m
    return mics[0] if mics else None


def level_bar(rms):
    n = min(40, int(rms * 400))
    return "[" + "#" * n + " " * (40 - n) + "]"


def main():
    mics = list_mics()
    if "--list" in sys.argv:
        for m in mics:
            print(" -", m)
        return
    mic = pick_mic(mics)
    if not mic:
        sys.exit("No se encontro ningun microfono.")

    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        print("Microfono:", mic)
        print(">>> MICROFONO ACTIVO: habla durante %d segundos... <<<" % SECONDS)
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "dshow",
                            "-i", "audio=" + mic, "-t", str(SECONDS), "-ac", "1", "-ar", "16000",
                            "-sample_fmt", "s16", path], capture_output=True)
        print(">>> Microfono apagado. <<<")
        if r.returncode != 0:
            sys.exit("Error de ffmpeg: " + r.stderr.decode("utf-8", "replace"))

        with wave.open(path, "rb") as w:
            data = w.readframes(w.getnframes())
            rate = w.getframerate()
        import array
        a = array.array("h", data)
        if not a:
            sys.exit("La grabacion esta vacia.")
        # nivel por cada 0.5 s
        step = rate // 2
        print("\nNivel (cada 0.5 s):")
        peak = 0.0
        for i in range(0, len(a), step):
            chunk = a[i:i + step]
            rms = (sum(x * x for x in chunk) / len(chunk)) ** 0.5 / 32768.0
            peak = max(peak, rms)
            print("  %4.1f s %s" % (i / rate, level_bar(rms)))
        if peak < 0.005:
            print("\nCasi silencio: revisa que el microfono no este silenciado en Windows "
                  "(Configuracion > Sistema > Sonido > Entrada) o el permiso de microfono.")
        else:
            print("\nEl microfono funciona. Reproduciendo la grabacion...")
            winsound.PlaySound(path, winsound.SND_FILENAME)
    finally:
        os.remove(path)
        print("Grabacion borrada (no se guarda nada).")


if __name__ == "__main__":
    main()
