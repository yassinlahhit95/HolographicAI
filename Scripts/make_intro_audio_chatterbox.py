# Etapa 2 (voz mejorada) - Genera la presentacion con Chatterbox (local, GPU, licencia MIT)
# y le aplica un tratamiento de sonido "de cine" con ffmpeg.
#
# Se ejecuta con el Python aislado de Tools/tts (NO con el Python normal):
#   "Tools\tts\.venv\Scripts\python.exe" Scripts\make_intro_audio_chatterbox.py
#
# Opciones:
#   --ref NOMBRE      voz de referencia de Tools/tts/voices (por defecto: la de VOICE_REF)
#   --samples         genera una version por cada voz de referencia en Voice/samples para comparar
#
# Salida normal: "UnrealProject 5.8/Voice/intro_en.wav" e "intro_es.wav".
# Unreal los lee al arrancar: no hay que importar nada.
import argparse
import os
import re
import subprocess
import sys

import torch
import torchaudio as ta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE_DIR = os.path.join(ROOT, "UnrealProject 5.8", "Voice")
REF_DIR = os.path.join(ROOT, "Tools", "tts", "voices")
VOICE_REF = "ref_beowulf.wav"  # voz elegida por Yassin (LibriVox, dominio publico)

# Bienvenida del Colegio Calasanz Santurtzi (version corta del ejemplo de la seccion 8 del
# documento del colegio). Primero en espanol y luego en ingles. Sin nombrar a ninguna persona.
# La version anterior (prototipo) esta en "UnrealProject 5.8/Voice/backup_intro_prototipo".
INTRO = [
    ("intro_es.wav", "es",
     "¡Hola! Bienvenidos al Colegio Calasanz Santurtzi. Soy el asistente digital del colegio, "
     "y estoy aquí para ayudaros a descubrir nuestros proyectos educativos y tecnológicos. "
     "Estáis en nuestra sala inmersiva, un espacio donde la educación, la creatividad "
     "y la tecnología se dan la mano. ¡Y esto es solo el principio!"),
    ("intro_en.wav", "en",
     "Hello, and welcome to Colegio Calasanz Santurtzi. I am the school's digital assistant, "
     "here to help you discover our educational and technological projects. "
     "You are in our immersive room, a space where education, creativity "
     "and technology come together. And this is just the beginning!"),
]

# Pronunciacion: palabras que la voz debe decir distinto en cada idioma (solo cambia el audio,
# el texto que se muestra/registra no cambia). En ingles "Santurtzi" se dice "Santurci".
PRONUNCIATION = {
    "en": {"Santurtzi": "Santurci"},
    "es": {
        "FP": "efe pe",
        "IA": "i a",
        "3D": "tres de",
        "DBH": "de be hache",
        "EFQM": "e efe cu eme",
        "ECHE": "eche",
        "ETHAZI": "etazi",
        "STEAM": "estím",
        "UE": "u e",
    },
}

_ES_UNITS = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve",
    "veinte", "veintiuno", "veintidós", "veintitrés", "veinticuatro", "veinticinco",
    "veintiséis", "veintisiete", "veintiocho", "veintinueve",
)
_ES_TENS = ("", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa")
_ES_HUNDREDS = (
    "", "ciento", "doscientos", "trescientos", "cuatrocientos",
    "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos",
)
_ES_ORDINALS = {
    "1º": "primero", "1.º": "primero", "1ª": "primera", "1.ª": "primera",
    "2º": "segundo", "2.º": "segundo", "2ª": "segunda", "2.ª": "segunda",
    "3º": "tercero", "3.º": "tercero", "3ª": "tercera", "3.ª": "tercera",
    "4º": "cuarto", "4.º": "cuarto", "4ª": "cuarta", "4.ª": "cuarta",
}


def _num_to_es(n):
    if n < 0:
        return "menos " + _num_to_es(-n)
    if n < 30:
        return _ES_UNITS[n]
    if n < 100:
        t, u = divmod(n, 10)
        return _ES_TENS[t] if u == 0 else "%s y %s" % (_ES_TENS[t], _ES_UNITS[u])
    if n == 100:
        return "cien"
    if n < 1000:
        c, r = divmod(n, 100)
        return _ES_HUNDREDS[c] if r == 0 else "%s %s" % (_ES_HUNDREDS[c], _num_to_es(r))
    if n < 1000000:
        m, r = divmod(n, 1000)
        pref = "mil" if m == 1 else "%s mil" % _num_to_es(m)
        return pref if r == 0 else "%s %s" % (pref, _num_to_es(r))
    return " ".join(_ES_UNITS[int(d)] for d in str(n))


def _normalize_es(text):
    # Telefonos tipo 944 61 35 19 -> grupos leidos de forma natural en Espana
    text = re.sub(
        r"\b(\d{3})\s+(\d{2})\s+(\d{2})\s+(\d{2})\b",
        lambda m: ", ".join(_num_to_es(int(g)) for g in m.groups()),
        text,
    )
    # URLs y dominios
    text = re.sub(r"https?://(?:www\.)?", "", text, flags=re.I)
    text = re.sub(r"\b([a-z0-9-]+)\.(eus|com|es|org|net)\b", r"\1 punto \2", text, flags=re.I)
    # Ordinales (1.º, 2º, etc.)
    for k, v in _ES_ORDINALS.items():
        text = re.sub(r"(?<!\d)%s" % re.escape(k), v, text)
    # Porcentajes, euros y decimales
    text = re.sub(r"(\d+)\s*%", r"\1 por ciento", text)
    text = re.sub(r"(\d+)\s*€", r"\1 euros", text)
    text = re.sub(r"\b(\d+)[.,](\d+)\b",
                  lambda m: "%s %s %s" % (_num_to_es(int(m.group(1))),
                                          "coma" if "," in m.group(0) else "punto",
                                          _num_to_es(int(m.group(2)))),
                  text)
    # Resto de numeros enteros
    text = re.sub(r"\b(\d{1,6})\b", lambda m: _num_to_es(int(m.group(1))), text)
    return text


def for_speech(text, lang):
    if lang == "es":
        text = _normalize_es(text)
    for word, said in PRONUNCIATION.get(lang, {}).items():
        flags = 0 if word.isupper() else re.I
        text = re.sub(r"\b%s\b" % re.escape(word), said, text, flags=flags)
    return " ".join(text.split())


# Interpretacion: exaggeration = emocion (0.45 natural); cfg_weight >= 0.5 evita balbuceos al final.
EXAGGERATION = 0.45
CFG_WEIGHT = 0.50
TEMPERATURE = 0.60
SEED = 7

# Sonido de cine: limpia graves sordos, calidez en graves, presencia en la voz, compresion
# suave, eco holografico muy leve y volumen normalizado.
CINEMA_FILTER = ",".join([
    "highpass=f=65",
    "equalizer=f=140:t=q:w=1.0:g=3.5",
    "equalizer=f=3200:t=q:w=1.2:g=1.5",
    "equalizer=f=7500:t=q:w=1.5:g=-2",
    "acompressor=threshold=-22dB:ratio=3:attack=8:release=180:makeup=2",
    "aecho=0.85:0.55:35|75:0.16|0.09",
    "loudnorm=I=-16:TP=-1.5:LRA=9",
])


def cinema(src, dst):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-af", CINEMA_FILTER,
                    "-ar", "44100", "-ac", "1", "-sample_fmt", "s16", dst], check=True)


def generate(model, ref_path, out_dir, suffix="", only=None):
    os.makedirs(out_dir, exist_ok=True)
    for name, lang, text in INTRO:
        if only and lang != only:
            continue
        torch.manual_seed(SEED)
        # frase a frase: Chatterbox pierde calidad (o corta) con textos largos
        pieces = []
        for i, s in enumerate(re.split(r"(?<=[.!?])\s+", for_speech(text, lang))):
            w = model.generate(s, language_id=lang, audio_prompt_path=ref_path if i == 0 else None,
                               exaggeration=EXAGGERATION, cfg_weight=CFG_WEIGHT,
                               temperature=TEMPERATURE)
            pieces += [w.cpu(), torch.zeros(1, int(model.sr * 0.3))]
        wav = torch.cat(pieces[:-1], dim=-1)
        raw = os.path.join(out_dir, "_raw_" + name)
        ta.save(raw, wav.cpu(), model.sr)
        final = os.path.join(out_dir, name.replace(".wav", suffix + ".wav"))
        cinema(raw, final)
        os.remove(raw)
        secs = wav.shape[-1] / model.sr
        print("OK %-28s %.1f s" % (os.path.relpath(final, ROOT), secs), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=VOICE_REF)
    ap.add_argument("--samples", action="store_true")
    ap.add_argument("--only", choices=["es", "en"], help="regenerar solo un idioma")
    args = ap.parse_args()

    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Cargando Chatterbox en", device, "...", flush=True)
    model = ChatterboxMultilingualTTS.from_pretrained(device=torch.device(device))

    if args.samples:
        for ref in sorted(f for f in os.listdir(REF_DIR) if f.endswith(".wav")):
            tag = "_" + ref[len("ref_"):-len(".wav")]
            generate(model, os.path.join(REF_DIR, ref), os.path.join(VOICE_DIR, "samples"), tag)
    else:
        generate(model, os.path.join(REF_DIR, args.ref), VOICE_DIR, only=args.only)

    if device == "cuda":
        print("VRAM maxima usada: %.2f GB" % (torch.cuda.max_memory_allocated() / 1e9))


if __name__ == "__main__":
    main()
