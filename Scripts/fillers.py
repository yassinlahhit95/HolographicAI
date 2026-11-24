# Muletillas para que el holograma no se quede callado mientras piensa.
#
#   1) Nada mas terminar de hablar el visitante: un sonido neutro ("Mmm...") que vale para cualquier idioma.
#   2) Cuando ya sabemos el idioma (Whisper): una muletilla corta ("A ver...", "Let me see...").
#   3) Pausa breve (como una respiracion) y la respuesta, frase a frase.
#
# Los audios se generan UNA vez con la misma voz (Chatterbox) y se guardan en
# "UnrealProject 5.8/Voice/fillers". Si cambias un texto, se regenera solo ese audio al arrancar.
# Para anadir o quitar muletillas: edita las listas de abajo y reinicia el asistente.
import hashlib
import os
import random
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILLER_DIR = os.path.join(ROOT, "UnrealProject 5.8", "Voice", "fillers")

# (texto, idioma con el que se genera la voz)
INSTANT = []   # sin sonidos artificiales tipo "Mmm..." / "Hmm..."
THINKING = {
    "es": [
        "Pues, a ver...",
        "Vamos a ver...",
        "Un momentito...",
        "Déjame ver...",
        "A ver, te cuento...",
        "Un segundo, por favor.",
        "Pues mira...",
    ],
    "en": ["Let me see...", "Okay, let me think.", "One moment, please.", "Let's see..."],
}
QUESTION = {   # solo si lo que ha dicho el visitante es una pregunta
    "es": ["Buena pregunta.", "Claro, te explico."],
    "en": ["Good question.", "Sure, let me explain."],
}
MIN_UTTERANCE = 0.6     # s: por debajo no decimos "Mmm" (probablemente era un ruido)


def _path(text, lang):
    h = hashlib.md5(("%s|%s" % (lang, text)).encode("utf-8")).hexdigest()[:10]
    return os.path.join(FILLER_DIR, "filler_%s_%s.wav" % (lang, h))


def _duration(path):
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())


class Fillers:
    def __init__(self, tts, synthesize, log=print, langs=("es",)):
        """synthesize(tts, text, lang, out_path) -> duracion (la de assistant.py, con el mismo sonido)."""
        os.makedirs(FILLER_DIR, exist_ok=True)
        self.clips = {}           # (grupo, idioma) -> [(ruta, duracion), ...]
        self._last = {}
        made = 0
        groups = [("instant", l, t) for t, l in INSTANT if l in langs]
        groups += [("thinking", l, t) for l, ts in THINKING.items() if l in langs for t in ts]
        groups += [("question", l, t) for l, ts in QUESTION.items() if l in langs for t in ts]
        for group, lang, text in groups:
            p = _path(text, lang)
            if not os.path.exists(p):
                synthesize(tts, text, lang, p)
                made += 1
            key = (group, "any" if group == "instant" else lang)
            self.clips.setdefault(key, []).append((p, _duration(p)))
        log("Muletillas listas: %d audios (%d nuevos) en Voice\\fillers" % (len(groups), made))

    def pick(self, group, lang="any"):
        """Una muletilla al azar, sin repetir la ultima de ese grupo. (ruta, duracion) o None."""
        opts = self.clips.get((group, lang)) or []
        if not opts:
            return None
        choices = [c for c in opts if c != self._last.get((group, lang))] or opts
        c = random.choice(choices)
        self._last[(group, lang)] = c
        return c
