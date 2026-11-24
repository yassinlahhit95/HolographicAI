# Respuestas RAPIDAS para lo sencillo: "hola", "¿que tal?", "how are you", "gracias", "adios",
# "hola, soy Yassin"... No pasan por la IA: son frases ya grabadas con la misma voz (varias versiones
# para no repetirse), asi el holograma contesta en ~1 segundo.
#
# Solo se usan si la frase es SOLO eso. "Hola, ¿que ciclos teneis?" va a la IA como siempre.
# Audios en "UnrealProject 5.8/Voice/quick" (se generan una vez; si cambias un texto, se regenera solo ese).
# Para cambiar o anadir frases: edita las listas de abajo y reinicia el asistente.
import hashlib
import os
import random
import re
import unicodedata
import wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUICK_DIR = os.path.join(ROOT, "UnrealProject 5.8", "Voice", "quick")

REPLIES = {
    "greet": {
        "es": ["¡Hola! Bienvenido al Colegio Calasanz. ¿En qué te puedo ayudar?",
               "¡Hola! ¡Qué bien que vengas a vernos! ¿Qué te gustaría descubrir del colegio?",
               "¡Hola! Encantado de saludarte. ¿Qué quieres saber del colegio?"],
        "en": ["Hello! Welcome to Colegio Calasanz. How can I help you?",
               "Hi there! Great to see you. What would you like to discover about the school?"],
    },
    "how": {
        "es": ["¡Muy bien, gracias! Con muchas ganas de enseñarte el colegio. ¿Y tú, qué tal?",
               "¡Genial, gracias por preguntar! ¿En qué te puedo ayudar hoy?",
               "¡Muy bien! Aquí estoy, listo para contarte cosas del colegio. ¿Y tú?"],
        "en": ["I'm great, thank you! Ready to show you the school. How about you?",
               "Very well, thanks for asking! How can I help you today?"],
    },
    "greet_how": {
        "es": ["¡Hola! Muy bien, gracias. ¿Y tú, qué tal? ¿Qué te gustaría saber del colegio?",
               "¡Hola! ¡Genial, gracias por preguntar! ¿En qué te puedo ayudar?"],
        "en": ["Hi! I'm great, thank you. How are you? What would you like to know about the school?",
               "Hello! Very well, thanks for asking! How can I help you?"],
    },
    "thanks": {
        "es": ["¡De nada! Ha sido un placer.", "¡A ti! ¿Quieres saber algo más del colegio?"],
        "en": ["You're welcome! It's a pleasure.", "Thank you! Would you like to know anything else?"],
    },
    "bye": {
        "es": ["¡Hasta pronto! Ha sido un placer.", "¡Adiós! Que disfrutes mucho de la visita."],
        "en": ["Goodbye! It was a pleasure.", "See you soon! Enjoy your visit."],
    },
    "fine": {   # respuesta a "bien, ¿y tu?" despues de preguntarle que tal
        "es": ["¡Me alegro mucho! Yo también muy bien, gracias. ¿Qué te gustaría descubrir del colegio?",
               "¡Qué bien! Yo estoy genial, gracias. ¿En qué te puedo ayudar?"],
        "en": ["Glad to hear it! I'm very well too, thanks. What would you like to discover about the school?"],
    },
    "sorry": {  # no se ha entendido lo que ha dicho
        "es": ["¿Perdona? No te he oído bien. ¿Me lo repites?", "Perdona, no te he entendido. ¿Puedes repetirlo?"],
        "en": ["Sorry, I didn't catch that. Could you say it again?"],
    },
    "nice": {
        "es": ["¡Igualmente! ¿Qué te gustaría descubrir del Colegio Calasanz?",
               "¡El placer es mío! ¿En qué te puedo ayudar hoy?"],
        "en": ["Nice to meet you too! What would you like to discover about Colegio Calasanz?",
               "The pleasure is mine! How can I help you today?"],
    },
    "identity": {
        "es": ["Soy el asistente digital holográfico del Colegio Calasanz Santurtzi. Estoy aquí para ayudarte a conocer el colegio y sus proyectos.",
               "Soy el asistente digital del Colegio Calasanz Santurtzi. Pregúntame lo que quieras sobre nuestras etapas educativas o la sala inmersiva."],
        "en": ["I am the holographic digital assistant of Colegio Calasanz Santurtzi. I'm here to help you discover our school and projects.",
               "I am Colegio Calasanz Santurtzi's digital assistant. Feel free to ask me about our programs or the immersive room."],
    },
}
# Saludo a una persona con perfil que se presenta ({name} = su nombre). El "greeting" de su perfil
# se anade tambien como una version mas.
PERSON = {
    "es": ["¡Hola, {name}! ¡Qué alegría verte! ¿Cómo estás?",
           "¡{name}! ¡Qué bien verte por aquí! ¿Qué tal todo?",
           "¡Hola, {name}! ¡Qué gusto verte de nuevo! ¿Cómo va todo?"],
    "en": ["Hi {name}! So nice to see you! How are you?",
           "{name}! Great to see you again! How is everything?"],
}
# Persona sin perfil: el nombre se genera en el momento (corto) y el resto ya esta grabado.
UNKNOWN_HELLO = {"es": "¡Hola, {name}!", "en": "Hi {name}!"}
UNKNOWN_TAIL = {
    "es": ["Encantado de saludarte. ¿Eres profesor aquí en Calasanz, o qué te trae por aquí?",
           "¡Qué bien conocerte! ¿Trabajas aquí en el colegio, o vienes de visita?"],
    "en": ["Nice to meet you. Are you a teacher here at Calasanz, or what brings you here?"],
}

# ------------------------------------------------------------------ reconocer frases sencillas
GREET = ["hola", "holaa", "ola", "ona", "ole", "buenas", "muy buenas", "buen dia", "buenos dias",
         "buenas tardes", "buenas noches", "hey", "hey there", "hello", "hi",
         "good morning", "good afternoon", "good evening", "saludos", "kaixo", "egun on", "ey",
         "que pasa", "que hay"]
HOW = ["que tal", "que tal estas", "que tal estas hoy", "como estas", "como estas hoy", "como esta",
       "como va", "como te va", "como andas", "que tal todo", "que tal va todo", "todo bien",
       "how are you", "how are you doing", "how is it going", "hows it going", "how do you do",
       "how are things", "whats up", "how have you been"]
THANKS = ["gracias", "muchas gracias", "muchisimas gracias", "mil gracias", "te lo agradezco",
          "de nada", "no hay de que", "thank you", "thank you so much", "thanks", "thanks a lot",
          "thank you very much", "eskerrik asko"]
BYE = ["adios", "hasta luego", "hasta pronto", "hasta manana", "chao", "agur", "bye", "goodbye", "see you",
       "bye bye", "nos vemos"]
FINE = ["estoy bien", "estoy muy bien", "todo bien", "bien bien", "estoy genial", "bien", "muy bien",
        "genial", "estupendo", "fenomenal", "bien gracias", "muy bien gracias",
        "bien y tu", "muy bien y tu", "fine", "im very well", "very well", "im great", "good", "great",
        "im fine", "im good", "fine thanks", "good thanks"]
NICE = ["encantado", "encantada", "mucho gusto", "igualmente", "un placer", "el placer es mio",
        "nice to meet you", "pleasure to meet you", "glad to meet you"]
IDENTITY = ["quien eres", "como te llamas", "que eres", "cual es tu nombre", "como te llaman",
            "who are you", "what is your name", "whats your name", "what are you"]
FILLER_WORDS = {"y", "tu", "usted", "oye", "eh", "ah", "bueno", "vale", "ok", "okay", "pues", "que", "muy",
                "and", "you", "oh", "well", "so", "senor", "senora", "holograma", "amigo", "amiga", "a", "todos",
                "everyone", "there", "gracias", "thanks", "por", "favor", "hoy", "aqui", "perfecto", "genial",
                "claro", "si", "no", "today", "here", "please", "sir", "madam", "too", "also", "tambien",
                "colegio", "calasanz", "santurtzi", "chico", "chica"}
_TITLES = (r"(?:(?:el|la|the)\s+)?(?:(?:profe(?:sor|sora)?|maestr[oa]|director[a]?|jefe|jefa|"
           r"coordinador[a]?|tutor[a]?|don|dona|teacher|mr|mrs|ms|miss|dr|doctor[a]?)\s+)?")
INTRO = re.compile(r"\b(?:me llamo|mi nombre es|soy|my name is|i am|im|this is)\s+" + _TITLES + r"[a-z'-]+(?:\s+[a-z'-]+)?")


def norm(text):
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("'", "")
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


def _strip(s, phrases):
    found = False
    for p in sorted(phrases, key=len, reverse=True):
        new = re.sub(r"\b%s\b" % re.escape(p), " ", s)
        if new != s:
            found, s = True, new
    return " ".join(s.split()), found


def classify(text, introduced):
    """Tipo de frase sencilla ('greet', 'how', ..., 'intro') o None si hay que preguntar a la IA."""
    s = norm(text)
    if not s or len(s.split()) > 12:
        return None
    if introduced:
        s = INTRO.sub(" ", s)
    s, i = _strip(s, IDENTITY)
    s, n = _strip(s, NICE)
    s, g = _strip(s, GREET)
    s, h = _strip(s, HOW)
    s, f = _strip(s, FINE) if not (g or h) else (s, False)
    s, t = _strip(s, THANKS)
    s, b = _strip(s, BYE)
    if any(w not in FILLER_WORDS for w in s.split()):
        return None                       # hay algo mas (una pregunta de verdad): a la IA
    if introduced:
        return "intro"
    if i:
        return "identity"
    if b:
        return "bye"
    if g and h:
        return "greet_how"
    if h:
        return "how"
    if n:
        return "nice"
    if g:
        return "greet"
    if t:
        return "thanks"
    if f:
        return "fine"
    return None


# ------------------------------------------------------------------ audios
def _path(text, lang):
    h = hashlib.md5(("%s|%s" % (lang, text)).encode("utf-8")).hexdigest()[:10]
    return os.path.join(QUICK_DIR, "quick_%s_%s.wav" % (lang, h))


def _duration(path):
    with wave.open(path) as w:
        return w.getnframes() / float(w.getframerate())


class QuickReplies:
    def __init__(self, tts, synthesize, profiles, log=print, langs=("es",)):
        self.tts, self.synth, self.log = tts, synthesize, log
        os.makedirs(QUICK_DIR, exist_ok=True)
        self.clips = {}       # (tipo, idioma) -> [(texto, ruta, duracion)]
        self._last = {}
        todo = [(kind, lang, t) for kind, by in REPLIES.items() for lang, ts in by.items() if lang in langs for t in ts]
        todo += [("tail", lang, t) for lang, ts in UNKNOWN_TAIL.items() if lang in langs for t in ts]
        for p in {p["id"]: p for p in profiles.values()}.values():
            for lang, ts in PERSON.items():
                if lang not in langs:
                    continue
                texts = [t.format(name=p["name"]) for t in ts]
                if lang == "es" and p.get("greeting"):
                    texts.append(p["greeting"])
                todo += [("person:" + p["id"], lang, t) for t in texts]
        made = 0
        t0 = __import__("time").time()
        for kind, lang, text in todo:
            path = _path(text, lang)
            if not os.path.exists(path):
                if made == 0:
                    log("Grabando respuestas rapidas (solo la primera vez, unos minutos)...")
                synthesize(tts, text, lang, path)
                made += 1
            self.clips.setdefault((kind, lang), []).append((text, path, _duration(path)))
        log("Respuestas rapidas listas: %d audios (%d nuevos, %.0f s)" % (len(todo), made, __import__("time").time() - t0))

    def _pick(self, kind, lang):
        opts = self.clips.get((kind, lang)) or self.clips.get((kind, "es")) or []
        if not opts:
            return None
        choices = [c for c in opts if c != self._last.get((kind, lang))] or opts
        c = random.choice(choices)
        self._last[(kind, lang)] = c
        return c

    def reply(self, text, lang, session, out_dir):
        """[(texto, ruta, duracion), ...] para decir YA, o None si hay que preguntar a la IA."""
        kind = classify(text, session.just_introduced)
        if kind is None:
            return None
        if kind == "intro":
            if session.profile:
                c = self._pick("person:" + session.profile["id"], lang)
                return [c] if c else None
            # sin perfil: "¡Hola, Javier!" se genera ahora (frase muy corta, ~1-2 s) + resto grabado
            hello = UNKNOWN_HELLO.get(lang, UNKNOWN_HELLO["es"]).format(name=session.name)
            path = os.path.join(out_dir, "quick_hello_%s.wav" % norm(session.name).replace(" ", "_"))
            dur = self.synth(self.tts, hello, lang, path)
            tail = self._pick("tail", lang)
            return [(hello, path, dur)] + ([tail] if tail else [])
        c = self._pick(kind, lang)
        return [c] if c else None

    def sorry(self, lang):
        return self._pick("sorry", lang)


if __name__ == "__main__":
    import sys
    for t in sys.argv[1:] or ["Hola", "Hola, ¿qué tal?", "How are you?", "Hola, soy Yassin", "Gracias",
                              "Hola, ¿qué ciclos tenéis?", "Muy bien, ¿y tú?", "Adiós", "Buenos días"]:
        intro = bool(re.search(r"\b(soy|me llamo|i'm|i am|my name is)\b", t.lower()))
        print("%-32s -> %s" % (t, classify(t, intro)))
