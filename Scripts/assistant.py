# Etapa 3 - Asistente de voz local: microfono -> texto -> IA -> voz -> holograma.
#
# Se ejecuta con el Python aislado (NO con el Python normal):
#   "Tools\tts\.venv\Scripts\python.exe" Scripts\assistant.py
#
# Antes: abre el holograma (Scripts\start_hologram.bat). El asistente espera a que termine
# la presentacion y luego empieza a escuchar.
#
# Pruebas sin microfono:
#   ... assistant.py --text "What is your name?"        (una pregunta escrita y sale)
#   ... assistant.py --text "¿Cómo estás?" --text "¿Qué eres?"
#
# Privacidad: el audio del microfono solo existe en memoria y se descarta tras transcribirlo.
# No se guarda ninguna grabacion. Solo se guardan las respuestas habladas del personaje
# (UnrealProject 5.8/Voice/replies, se borran las antiguas).
#
# Nada sale de este ordenador: Whisper, Ollama y Chatterbox funcionan en local.
import argparse
import json
import os
import queue
import random
import re
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ ajustes
UE_PORT = 7810            # Unreal escucha aqui
MY_PORT = 7811            # Unreal nos avisa aqui
OLLAMA_URL = "http://127.0.0.1:11434"
LLM_MODEL = "qwen3:4b-instruct"   # elegido el 24-11-2026 frente a gemma3:4b y qwen2.5:3b (ver README)
LLM_ON_GPU = True         # True: con Edge/Piper la GPU queda libre para Qwen3 (~4.3 GB con Whisper)
TTS_ENGINE = "edge"       # "edge" (principal + fallback Piper), "piper" (100% offline), "chatterbox" (GPU)
EDGE_VOICES = {"es": "es-ES-AlvaroNeural", "en": "en-US-AndrewNeural"}
EDGE_TIMEOUT = 10.0       # s maximos esperando a Edge TTS antes de pasar a Piper offline
PIPER_EXE = os.path.join(ROOT, "Tools", "piper", "piper.exe")
PIPER_VOICES = {
    "es": os.path.join(ROOT, "Tools", "piper", "voices", "es_ES-davefx-medium.onnx"),
    "en": os.path.join(ROOT, "Tools", "piper", "voices", "en_US-joe-medium.onnx"),
}
WHISPER_MODEL = "small"
WHISPER_ON_GPU = True     # GPU: 0,2 s en vez de 3,3 s por frase (~0,1 GB de VRAM); si falla, usa el procesador
LANGS = {"es": "Spanish"}   # idioma activo: solo espanol por ahora (enfoque en calidad ES)
VOICE_REF = "ref_beowulf.wav"
REPLY_DIR = os.path.join(ROOT, "UnrealProject 5.8", "Voice", "replies")
KEEP_REPLIES = 15         # archivos de voz guardados (uno por frase)
MIN_FIRST = 32            # la primera frase puede cortarse antes (en una coma) para empezar a hablar antes
MIN_PIECE = 25            # la respuesta se dice frase a frase; frases de menos letras se juntan
MAX_PIECE = 160           # frases mas largas (listas) se cortan en una coma
USE_FILLERS = True        # muletillas mientras piensa ("Mmm...", "A ver...") -> ver Scripts\fillers.py
USE_QUICK = True          # respuestas grabadas para lo sencillo (hola, que tal...) -> Scripts\quick_replies.py
THINKING_FILLER_P = 1.0   # probabilidad de usar una muletilla si la IA tarda > FILLER_DELAY s
FILLER_DELAY = 1.6        # s: si la primera frase esta lista antes, responde directo sin muletilla
BREATH = 0.35             # s de pausa entre la muletilla y la respuesta
HISTORY_MAX = 12         # mensajes de conversacion que recuerda; al pasarse, se queda con los
HISTORY_KEEP = 4          # ultimos 4 de golpe (asi Ollama reutiliza su cache y responde antes)

# Deteccion de voz (VAD) por energia
SR = 16000
BLOCK = 480                     # 30 ms
START_FACTOR = 3.0              # voz = energia > ruido de fondo x 3
MIN_THRESHOLD = 0.004       # bajado de 0.006: voces suaves no llegaban (24-11-2026)
START_BLOCKS = 4                # 120 ms seguidos con voz para empezar
END_SILENCE = 0.9               # segundos de silencio para terminar la frase
MAX_UTTERANCE = 15.0
PREROLL = 0.3

# Identidad y conocimiento (Colegio Calasanz Santurtzi): carpeta Knowledge del proyecto.
#  - Knowledge\_identidad_asistente.txt : reglas de identidad, ambito y estilo ({language}, {knowledge})
#  - Knowledge\*.md / *.txt             : informacion aprobada del colegio (web oficial + documentos)
# Para anadir informacion: copiar un .md o .txt en esa carpeta y reiniciar el asistente.
KNOWLEDGE_DIR = os.path.join(ROOT, "Knowledge")
IDENTITY_FILE = os.path.join(KNOWLEDGE_DIR, "_identidad_asistente.txt")
PROFILES_FILE = os.path.join(KNOWLEDGE_DIR, "people_profiles.json")   # personas que se presentan por su nombre
UNREAL_WAIT = 240         # s maximos esperando a que se abra el holograma
SESSION_IDLE = 120        # s sin hablar (y sin cara delante) -> nueva visita: se olvida nombre y conversacion
DEFAULT_LANG = "es"        # idioma por defecto si no esta claro
LLM_CONTEXT = 6144         # tokens de contexto (5146 sistema + ~1000 historial; ahorra VRAM para Unreal)


def _norm_kw(text):
    import unicodedata
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", s)


def _char_trigrams(text):
    import unicodedata
    s = unicodedata.normalize("NFKD", text.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", " ".join(s.split()))
    return [s[i:i + 3] for i in range(max(0, len(s) - 2))]


def _cosine_sim(c1, c2):
    import math
    if not c1 or not c2:
        return 0.0
    dot = sum(v * c2[k] for k, v in c1.items() if k in c2)
    if not dot:
        return 0.0
    n1 = math.sqrt(sum(v * v for v in c1.values()))
    n2 = math.sqrt(sum(v * v for v in c2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


KNOWLEDGE_MODULES = []    # [(filename, text, set_of_tokens, trigram_counter)]
CONV_EXAMPLES = []        # [(tags_set, trigram_counter, formatted_text)]
MODULE_SYNONYMS = {
    "02_historia_y_centro.md": {"historia", "ano", "anos", "1969", "fundacion", "efqm", "iso", "aenor", "ibaiondo", "origen"},
    "03_oferta_educativa.md": {"oferta", "etapa", "etapas", "infantil", "primaria", "eso", "dbh", "fp", "ciclo", "ciclos", "grado", "sanidad", "sanitario", "sanitarios", "farmacia", "enfermeria", "laboratorio", "radioterapia", "imagen", "administracion", "marketing", "integracion", "bachillerato", "trilingue", "singapur", "chromebook"},
    "04_formacion_lanbide.md": {"lanbide", "empleo", "desempleado", "desempleados", "trabajadores", "certificado", "certificados", "acreditada", "acreditadas", "inscrita", "especialidad", "especialidades", "in company", "tkgune", "curso", "cursos"},
    "05_internacionalizacion.md": {"internacional", "internacionalizacion", "campus", "erasmus", "europa", "asia", "africa", "china", "beijing", "pekin", "nanchang", "jingdezhen", "kenia", "kenya", "marruecos", "tunez", "libia", "portugal", "italia", "grecia", "polonia", "serbia", "estonia", "francia", "lituania", "eslovenia", "finlandia", "paises bajos", "holanda", "malta", "bulgaria", "rafael", "rafa", "balparda", "barparda", "catia", "freitas", "delegacion", "movilidad", "shadowing", "intercambio", "nairobi", "paul", "fuera", "extranjero", "practicas"},
    "06_proyectos_internacionales.md": {"proyecto", "proyectos", "erasmus", "pulse", "fake", "real", "for", "vet4ye", "amor", "enneplus", "cesar", "entreasses", "dlight", "d-light", "realidad", "virtual", "rv", "europa", "etwinning", "ka1", "ka2", "ka171", "ka220", "greenovetion", "keys", "europeo", "europeos"},
    "07_innovacion_y_tecnologia.md": {"innovacion", "tecnologia", "tecnologico", "ethazi", "retos", "steam", "robotica", "cuidalab", "smartlab", "smartlabs", "inmersiva", "360", "ia", "inteligencia", "artificial", "virtual", "aumentada", "simulacion", "holograma", "asistente", "3d", "bioimpresion", "urrats", "sostenibilidad", "inclusion"},
    "08_instalaciones_y_servicios.md": {"instalaciones", "edificio", "aula", "aulas", "comedor", "jantoki", "jantxiki", "madrugadores", "uniforme", "uniformes", "ampa", "alexia", "padlet", "orientacion", "bolsa", "alquiler", "paseo", "donde", "direccion", "ubicacion", "calle"},
    "09_actividades_escolares.md": {"actividad", "actividades", "premio", "premios", "logro", "logros", "bikoteka", "lectura", "mindfulness", "emocional", "puertas", "abiertas", "visita", "visitas"},
    "10_colaboraciones.md": {"colaborar", "colaboracion", "colaboraciones", "alianza", "socio", "socios", "empresa", "empresas", "universidad", "universidades", "centro", "centros", "convenio", "acuerdo", "practicas"},
    "11_preguntas_frecuentes.md": {"colaborar", "empresa", "empresas", "bachillerato", "matricula", "prematricula", "horario", "horarios", "secretaria", "precio", "cuesta"},
}


def load_conv_examples():
    from collections import Counter
    CONV_EXAMPLES.clear()
    conv_dir = os.path.join(KNOWLEDGE_DIR, "Conversation")
    if not os.path.isdir(conv_dir):
        return
    for fn in sorted(os.listdir(conv_dir)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(conv_dir, fn), encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                turns = obj.get("turns") or []
                if not turns:
                    continue
                # Tomamos el ultimo par user->assistant como ejemplo compacto de estilo
                pair = turns[-2:] if len(turns) >= 2 else turns
                fmt = " / ".join(
                    ("%s: %s" % ("Visitante" if t["role"] == "user" else "Asistente", t["content"]))
                    for t in pair
                )
                u_txt = " ".join(t["content"] for t in turns if t["role"] == "user")
                tags = set(_norm_kw(" ".join(obj.get("tags") or []))) | set(_norm_kw(u_txt))
                CONV_EXAMPLES.append((tags, Counter(_char_trigrams(u_txt)), fmt))


def retrieve_examples(query, max_examples=2, max_chars=520):
    from collections import Counter
    if not CONV_EXAMPLES:
        return ""
    q_tok = set(_norm_kw(query))
    q_tri = Counter(_char_trigrams(query))
    scored = []
    for tags, tri, fmt in CONV_EXAMPLES:
        sim = 3.0 * len(q_tok & tags) + 12.0 * _cosine_sim(q_tri, tri)
        if sim > 2.5:
            scored.append((sim, fmt))
    scored.sort(key=lambda x: -x[0])
    out, used = [], 0
    for _, fmt in scored[:max_examples]:
        if used + len(fmt) > max_chars and out:
            break
        out.append("- " + fmt)
        used += len(fmt)
    return "\n".join(out)


def load_knowledge():
    from collections import Counter
    KNOWLEDGE_MODULES.clear()
    core_parts = []
    total_chars = 0
    for f in sorted(os.listdir(KNOWLEDGE_DIR)):
        if f.startswith("_") or not f.lower().endswith((".md", ".txt")):
            continue
        with open(os.path.join(KNOWLEDGE_DIR, f), encoding="utf-8") as fh:
            text = re.sub(r"<!--.*?-->", "", fh.read(), flags=re.S).strip()
        if not text:
            continue
        total_chars += len(text)
        if f.startswith(("01_", "12_")):
            core_parts.append(text)
        else:
            kws = set(_norm_kw(text)) | MODULE_SYNONYMS.get(f, set())
            KNOWLEDGE_MODULES.append((f, text, kws, Counter(_char_trigrams(text))))
    load_conv_examples()
    return "\n\n".join(core_parts), total_chars


CONCEPT_LINKS = {
    # Conexiones transversales entre modulos (razonamiento cruzado)
    "06_proyectos_internacionales.md": {"sanidad", "salud", "mayores", "dependencia", "emprender", "emprendimiento", "bulos", "desinformacion", "noticias", "falsas", "inclusion", "accesibilidad", "discapacidad", "economia", "circular", "sostenibilidad", "reciclaje"},
    "07_innovacion_y_tecnologia.md": {"sanidad", "salud", "mayores", "dependencia", "empresa", "empresas", "practica", "practicas", "empleabilidad", "simular", "simulaciones"},
    "05_internacionalizacion.md": {"colaborar", "colaboracion", "socios", "alianza", "universidad", "extranjero", "fuera", "becas"},
    "10_colaboraciones.md": {"practicas", "empleo", "talento", "alumnado", "proyecto", "conjunto", "juntos", "acuerdo", "convenio"},
}


def detect_intent(text):
    """Clasifica la intencion conversacional y devuelve (intent, strategy_hint, needs_kb)."""
    t = text.strip().lower()
    words = t.split()
    has_q = "?" in t or bool(re.match(r"^(?:qué|que|cómo|como|cuál|cual|cuándo|cuando|dónde|donde|quién|quien|por qué|cuánto|cuanto|tenéis|teneis|hay|se puede|podemos|hacéis|haceis)\b", t))
    if re.search(r"\b(?:no me refer[ií]a|hablaba de|no,? digo|quer[ií]a decir)\b", t):
        return "correction", "Strategy: constructive correction. Acknowledge briefly without apologizing excessively and answer the clarified topic.", True
    if not has_q and len(words) <= 8 and re.search(
        r"\b(?:qu[eé] interesante|qu[eé] bien|qu[eé] guay|qu[eé] pasada|qu[eé] chulo|vaya|impresionante|incre[ií]ble|genial|perfecto|estupendo|vale|entendido|muchas gracias|gracias|de nada|me alegro|qu[eé] majo)\b", t
    ):
        return "social_ack", "Strategy: brief natural social reaction (1 short sentence, max 15 words). Do NOT echo the visitor's phrase, do NOT explain Calasanz projects unless asked, do NOT ask a question.", False
    if not has_q and re.search(r"\b(?:me voy|hasta luego|ya est[aá]|suficiente por hoy|nos vemos|adi[oó]s)\b", t):
        return "farewell", "Strategy: warm brief farewell (1 short sentence).", False
    if re.search(r"\b(?:chiste|comes|fantasma|años tienes|robot|quitar el trabajo)\b", t):
        return "joke", "Strategy: warm playful 1-2 sentence reply, transparent that you are a virtual assistant.", False
    if re.search(r"\b(?:colaborar|colaboraci[oó]n|algo juntos|socios|convenio|alianza|desde nuestro centro|desde nuestra empresa)\b", t):
        return "collaboration", "Strategy: explore shared interests constructively, connect relevant Calasanz projects, and guide to Rafael Balparda/Cátia Freitas or secretaría without promising approval or funding.", True
    if re.search(r"\b(?:no s[eé] si|me da respeto|no creo|demasiada|fama de ser menos|no sirven)\b", t):
        return "criticism_or_doubt", "Strategy: empathetic, constructive, factual response without sounding defensive.", True
    if re.search(r"\b(?:ejemplo|por ejemplo|c[oó]mo funciona|expl[ií]came|en qu[eé] consiste)\b", t):
        return "explanation_or_example", "Strategy: clear explanation with a concrete practical example in plain spoken Spanish.", True
    if len(words) <= 6 and re.search(r"\b(?:y en|y eso|y ese|y esa|cu[eé]ntame m[aá]s|otros proyectos|qu[eé] m[aá]s)\b", t):
        return "followup", "Strategy: contextual follow-up building directly on the prior turn without repeating what was already said.", True
    return "factual", "Strategy: direct, natural spoken answer connecting relevant facts concisely.", True


def retrieve_knowledge(query, history=None, max_modules=3, max_chars=4500):
    """Recuperacion hibrida (lexica + trigramas + enlaces conceptuales) sobre modulos relevantes."""
    from collections import Counter
    if not KNOWLEDGE_MODULES:
        return ""
    ctx_parts = []
    for m in (history or [])[-2:]:
        c = re.sub(r"^\[Answer in[^\]]*\]\s*(?:\([^\)]*\)\s*)?", "", m.get("content", ""))
        ctx_parts.append(c)
    q_tokens = set(_norm_kw(query))
    q_tri = Counter(_char_trigrams(query))
    ctx_tokens = set(_norm_kw(" ".join(ctx_parts))) - q_tokens
    scored = []
    for f, text, kws, tri in KNOWLEDGE_MODULES:
        syns = MODULE_SYNONYMS.get(f, set())
        links = CONCEPT_LINKS.get(f, set())
        sem = 25.0 * _cosine_sim(q_tri, tri)
        score = (50 * len(q_tokens & syns)
                 + 12 * len(q_tokens & links)
                 + 3 * len(q_tokens & kws)
                 + 3 * len(ctx_tokens & syns)
                 + len(ctx_tokens & kws)
                 + sem)
        if score > 1.5:
            scored.append((score, f, text))
    scored.sort(key=lambda x: (-x[0], x[1]))
    picked, used = [], 0
    for _, f, text in scored[:max_modules]:
        if used + len(text) > max_chars and picked:
            break
        picked.append(text)
        used += len(text)
    if not picked:
        for f, text, _, _ in KNOWLEDGE_MODULES:
            if f.startswith("03_"):
                picked.append(text)
                break
    return "\n\n".join(picked)


def build_system_prompt():
    with open(IDENTITY_FILE, encoding="utf-8") as fh:
        template = fh.read()
    core_knowledge, total_chars = load_knowledge()
    # El MISMO texto base (compacto) para mantener la cache de Ollama; los modulos relevantes van con la pregunta.
    text = template.replace("{language}", "Spanish (Spain)")
    text = text.replace("{knowledge}", core_knowledge)
    return {l: text for l in LANGS}, total_chars


SYSTEM_PROMPTS = {}


LOG_DIR = os.path.join(ROOT, "Logs")   # copia de lo que sale en la ventana (para revisar pruebas)


def log(msg):
    line = "%s %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "assistant_%s.log" % time.strftime("%Y-%m-%d")), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


# ------------------------------------------------------------------ puente con Unreal
class Bridge:
    def __init__(self):
        self.events = queue.Queue()
        self._deferred = []
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", MY_PORT))
        self.sock.settimeout(0.5)
        self.out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        threading.Thread(target=self._recv, daemon=True).start()

    def _recv(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(65535)
                self.events.put(json.loads(data.decode("utf-8")))
            except socket.timeout:
                continue
            except (OSError, ValueError):
                continue

    def send(self, **msg):
        self.out.sendto(json.dumps(msg).encode("utf-8"), ("127.0.0.1", UE_PORT))

    def wait(self, names, timeout):
        for i, ev in enumerate(self._deferred):
            if ev.get("event") in names:
                return self._deferred.pop(i)
        end = time.time() + timeout
        while time.time() < end:
            try:
                ev = self.events.get(timeout=max(0.05, end - time.time()))
            except queue.Empty:
                break
            if ev.get("event") in names:
                return ev
            self._deferred.append(ev)
            if len(self._deferred) > 32:
                self._deferred.pop(0)
        return None

    def status(self, timeout=1.0):
        while not self.events.empty():
            ev = self.events.get_nowait()
            if ev.get("event") != "status":
                self._deferred.append(ev)
                if len(self._deferred) > 32:
                    self._deferred.pop(0)
        self._deferred = [ev for ev in self._deferred if ev.get("event") != "status"]
        self.send(cmd="status")
        return self.wait({"status"}, timeout)


# ------------------------------------------------------------------ microfono
def record_utterance(sd):
    """Escucha hasta que alguien habla y se calla. Devuelve audio float32 16 kHz (en memoria)."""
    q = queue.Queue()

    def cb(indata, frames, t, status):
        q.put(indata[:, 0].copy())

    pre = []
    pre_max = int(PREROLL * SR / BLOCK)
    voiced, rec, silence, noise = 0, [], 0.0, None
    started = False
    with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=BLOCK, callback=cb):
        t_hint, peak = time.time(), 0.0
        while True:
            b = q.get()
            rms = float(np.sqrt(np.mean(b * b)))
            if noise is None:
                noise = rms
            if not started:
                peak = max(peak, rms)
                if time.time() - t_hint > 15:
                    log("  (nada detectado en 15 s: nivel maximo %.4f, umbral %.4f -> si hablas y el nivel "
                        "es menor que el umbral, baja MIN_THRESHOLD en assistant.py o sube el volumen del microfono)"
                        % (peak, max(noise * START_FACTOR, MIN_THRESHOLD)))
                    t_hint, peak = time.time(), 0.0
                # el ruido de fondo se adapta lentamente mientras nadie habla
                noise = 0.95 * noise + 0.05 * rms if rms < noise * 2 else noise
                thr = max(noise * START_FACTOR, MIN_THRESHOLD)
                pre.append(b)
                pre = pre[-pre_max:]
                voiced = voiced + 1 if rms > thr else 0
                if voiced >= START_BLOCKS:
                    started = True
                    rec = list(pre)
                    t_start = time.time()
                    log("  (voz detectada)")
            else:
                rec.append(b)
                thr = max(noise * START_FACTOR, MIN_THRESHOLD) * 0.7
                silence = silence + BLOCK / SR if rms < thr else 0.0
                if silence >= END_SILENCE or time.time() - t_start > MAX_UTTERANCE:
                    break
    return np.concatenate(rec)


# ------------------------------------------------------------------ voz -> texto
WHISPER_HINT = "Colegio Calasanz Santurtzi. Holograma, sala inmersiva, FP, ESO."   # ayuda con los nombres
LANG_SWITCH_P = 0.85      # seguridad minima de Whisper para cambiar de idioma a mitad de conversacion
                          # (con frases cortas "Hola, soy Javier" Whisper a veces dice "ingles 50 %")


def transcribe(whisper, audio, conv_lang=DEFAULT_LANG, hint=WHISPER_HINT):
    lang = conv_lang if conv_lang in LANGS else DEFAULT_LANG
    kw = {"beam_size": 1, "vad_filter": True, "initial_prompt": hint}
    if len(LANGS) == 1:
        kw["language"] = lang
    segs, info = whisper.transcribe(audio, **kw)
    segs = list(segs)
    if len(LANGS) > 1:
        det = info.language
        redo = None
        if det not in LANGS:
            probs = dict(info.all_language_probs or [])
            best = max(LANGS, key=lambda l: probs.get(l, 0.0))
            others = [probs.get(l, 0.0) for l in LANGS if l != best]
            redo = best if probs.get(best, 0.0) > 2 * max(others + [0.0]) else conv_lang
        elif det != conv_lang and info.language_probability < LANG_SWITCH_P:
            redo = conv_lang
        if redo:
            lang = redo
            segs, info = whisper.transcribe(audio, beam_size=1, vad_filter=True, language=lang, initial_prompt=hint)
            segs = list(segs)
        else:
            lang = det
    segs = [s for s in segs if s.no_speech_prob < 0.6]
    text = " ".join(s.text.strip() for s in segs).strip()
    if len(text) < 2:
        # Palabras muy cortas ("Hola") a veces las borra el filtro de silencio: segundo intento sin filtro
        segs, info2 = whisper.transcribe(audio, beam_size=1, vad_filter=False, language=lang, initial_prompt=hint)
        text = " ".join(s.text.strip() for s in segs if s.no_speech_prob < 0.8).strip()
    if re.search(r"subt[ií]tul|suscr[ií]b|gracias por ver|amara\.org|thanks for watching", text, re.I):
        text = ""     # frases que Whisper "inventa" con ruido (vienen de videos de internet)
    return text, lang, info.language_probability


# ------------------------------------------------------------------ IA (Ollama)
def ollama(path, payload=None, timeout=120):
    req = urllib.request.Request(OLLAMA_URL + path,
                                 data=json.dumps(payload).encode("utf-8") if payload else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def clean_for_speech(text):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"<think>.*$", "", text, flags=re.S)
    text = re.sub(r"[*_#`>\[\]]", "", text)
    text = re.sub(r"(^|\s)-\s+", r"\1", text)          # vinetas de lista
    text = re.sub(r"[\U0001F300-\U0001FAFF☀-➿]", "", text)
    return " ".join(text.split())


def _next_piece(buf, final, first=False):
    """Corta el primer trozo que ya se puede decir en voz alta (frase completa). (trozo, resto).
    El PRIMER trozo tambien se puede cortar en una coma: cuanto mas corto, antes empieza a hablar."""
    for m in re.finditer(r"[.!?…:;,](?=\s)" if first else r"[.!?…:;](?=\s)", buf):
        if m.end() >= (MIN_FIRST if first else MIN_PIECE):
            return buf[:m.end()], buf[m.end():]
    if len(buf) > MAX_PIECE:                          # frase muy larga (listas): cortar en una coma
        cut = buf.rfind(", ", MIN_PIECE, MAX_PIECE)
        if cut > 0:
            return buf[:cut + 1], buf[cut + 1:]
    if final and buf.strip():
        return buf, ""
    return None, buf


def stream_llm(history, text, lang, person_context="", turn_note="", pause_each=True, info=None):
    """Pregunta a la IA y va devolviendo la respuesta FRASE A FRASE mientras se genera.

    Orden de los mensajes pensado para la cache de Ollama (lo que no cambia, primero):
    identidad+conocimiento -> perfil de la persona (estable) -> conversacion -> nota del turno + pregunta.
    Si algo del principio cambia, Ollama tiene que releerlo todo (~40 tokens/s en el procesador)."""
    if not SYSTEM_PROMPTS:
        SYSTEM_PROMPTS.update(build_system_prompt()[0])
    msgs = [{"role": "system", "content": SYSTEM_PROMPTS[lang]}]
    if person_context:
        msgs.append({"role": "system", "content": person_context})
    msgs += history
    intent, strategy, needs_kb = detect_intent(text)
    rel_kb = retrieve_knowledge(text, history) if needs_kb else ""
    rel_ex = retrieve_examples(text)
    kb_block = ("\n[RELEVANT SCHOOL INFO]\n" + rel_kb + "\n[/RELEVANT SCHOOL INFO]") if rel_kb else ""
    ex_block = ("\n[STYLE EXAMPLES - adapt naturally, vary wording]\n" + rel_ex + "\n[/STYLE EXAMPLES]") if rel_ex else ""
    end_rule = " End with a warm statement, NOT a question." if (intent == "social_ack" or (len(history or []) // 2) % 2 == 1) else ""
    note = "[Answer in %s, 1-3 natural spoken sentences, vary wording. %s%s]%s" % (
        LANGS.get(lang, "Spanish"), strategy, end_rule, (" " + turn_note) if turn_note else ""
    )
    user_msg = {"role": "user", "content": note + kb_block + ex_block + "\nVisitor: " + text}
    msgs.append(user_msg)
    if info is not None:
        # Guardamos en el historial solo la pregunta limpia (sin el bloque de conocimiento recuperado)
        # para no hinchar el historial entre turnos.
        info["user"] = {"role": "user", "content": note + "\n" + text}
        info["raw"] = ""
    options = {"temperature": 0.65, "top_p": 0.9, "repeat_penalty": 1.08, "num_predict": 140, "num_ctx": LLM_CONTEXT}
    if not LLM_ON_GPU:
        options["num_gpu"] = 0
    payload = {"model": LLM_MODEL, "messages": msgs, "stream": True,
               "keep_alive": "30m", "options": options}
    if LLM_MODEL.startswith("qwen3"):
        payload["think"] = False      # qwen3 "piensa" en voz baja antes de responder: muy lento en CPU

    # PAUSA ENTRE FRASES (pause_each): en este portatil la IA (10 nucleos) y la voz no pueden trabajar a
    # la vez: la voz va 2,5 veces mas lenta. Por eso, en cuanto la IA termina una frase cortamos la
    # conexion (Ollama deja de generar), la voz genera esa frase SOLA y, mientras suena, pedimos a la
    # IA que CONTINUE su respuesta donde la dejo (se le pasa lo ya dicho como respuesta empezada).
    said, n_tokens, first = "", 0, True
    while True:
        p = dict(payload, messages=msgs + ([{"role": "assistant", "content": said}] if said else []))
        p["options"] = dict(options, num_predict=max(20, options["num_predict"] - n_tokens))
        req = urllib.request.Request(OLLAMA_URL + "/api/chat", data=json.dumps(p).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        buf, finished, out, n_before = "", False, [], n_tokens
        t_req = time.time()
        with urllib.request.urlopen(req, timeout=180) as r:
            for line in r:
                d = json.loads(line.decode("utf-8"))
                chunk = d.get("message", {}).get("content", "")
                if info is not None and chunk and n_tokens == n_before:
                    info.setdefault("read_s", []).append(round(time.time() - t_req, 1))  # leer (prompt)
                n_tokens += 1 if chunk else 0
                buf += chunk
                finished = d.get("done", False)
                while True:
                    piece, buf = _next_piece(buf, finished, first)
                    if piece is None:
                        break
                    said += piece
                    out.append(piece)
                    if info is not None:
                        info["raw"] = said
                    first = False
                    if pause_each and not finished:
                        break
                if out and pause_each and not finished:
                    break              # salir del "with" cierra la conexion: la IA se detiene
                if finished:
                    break
        for piece in out:
            piece = clean_for_speech(piece)
            if piece:
                yield piece
        if finished or not out or n_tokens >= options["num_predict"]:
            return


def ask_llm(history, text, lang, person_context="", turn_note=""):
    """Respuesta completa de una vez (pruebas y calentamiento)."""
    return " ".join(stream_llm(history, text, lang, person_context, turn_note, pause_each=False))


# ------------------------------------------------------------------ texto -> voz
def split_sentences(text):
    parts = re.split(r"(?<=[.!?¡¿…])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if out and len(out[-1]) < 25:     # frases muy cortas se juntan con la anterior
            out[-1] += " " + p
        else:
            out.append(p)
    return out or [text]


def _to_unreal_wav(src, dst, normalize=True):
    import subprocess
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", src]
    if normalize:
        cmd += ["-af", "loudnorm=I=-16:TP=-1.5:LRA=9"]
    cmd += ["-ar", "44100", "-ac", "1", "-sample_fmt", "s16", dst]
    subprocess.run(cmd, check=True)


def _synth_piper(text, lang, out_path):
    import subprocess
    model = PIPER_VOICES.get(lang, PIPER_VOICES["es"])
    if not os.path.isfile(PIPER_EXE) or not os.path.isfile(model):
        raise FileNotFoundError("Piper o modelo no encontrado: %s" % model)
    raw = out_path.replace(".wav", "_raw.wav")
    try:
        r = subprocess.run(
            [PIPER_EXE, "--model", model, "--output_file", raw,
             "--length_scale", "1.02", "--sentence_silence", "0.25"],
            input=text.encode("utf-8"), capture_output=True, timeout=30,
        )
        if r.returncode != 0 or not os.path.isfile(raw):
            raise RuntimeError(r.stderr.decode("utf-8", "replace"))
        _to_unreal_wav(raw, out_path)
    finally:
        if os.path.exists(raw):
            os.remove(raw)


def _synth_edge(text, lang, out_path):
    import asyncio
    import edge_tts
    voice = EDGE_VOICES.get(lang, EDGE_VOICES["es"])
    mp3 = out_path.replace(".wav", "_edge.mp3")

    async def _run():
        comm = edge_tts.Communicate(text, voice, rate="+0%")
        await asyncio.wait_for(comm.save(mp3), timeout=EDGE_TIMEOUT)

    try:
        asyncio.run(_run())
        if not os.path.isfile(mp3) or os.path.getsize(mp3) == 0:
            raise RuntimeError("Edge TTS devolvio audio vacio")
        _to_unreal_wav(mp3, out_path)
    finally:
        if os.path.exists(mp3):
            os.remove(mp3)


def _synth_chatterbox(tts, text, lang, out_path):
    import torch
    import torchaudio as ta
    from make_intro_audio_chatterbox import EXAGGERATION, CFG_WEIGHT, TEMPERATURE, cinema
    pieces = []
    silence = torch.zeros(1, int(tts.sr * 0.25))
    for s in split_sentences(text):
        wav = tts.generate(s, language_id=lang, exaggeration=EXAGGERATION,
                           cfg_weight=CFG_WEIGHT, temperature=TEMPERATURE)
        pieces += [wav.cpu(), silence]
    raw = out_path.replace(".wav", "_raw.wav")
    try:
        ta.save(raw, torch.cat(pieces[:-1], dim=-1), tts.sr)
        cinema(raw, out_path)
    finally:
        if os.path.exists(raw):
            os.remove(raw)


def synthesize(tts, text, lang, out_path):
    from make_intro_audio_chatterbox import for_speech
    speech_text = for_speech(text, lang)
    if TTS_ENGINE == "chatterbox":
        _synth_chatterbox(tts, speech_text, lang, out_path)
    elif TTS_ENGINE == "piper":
        _synth_piper(speech_text, lang, out_path)
    else:
        try:
            _synth_edge(speech_text, lang, out_path)
        except Exception as e:
            log("AVISO: Edge TTS no disponible (%s) -> usando Piper offline" % type(e).__name__)
            _synth_piper(speech_text, lang, out_path)
    with wave.open(out_path) as w:
        return w.getnframes() / float(w.getframerate())


class Speaker:
    """Encadena audios en el holograma sin cortarlos: muletillas y frases de la respuesta.
    Cada 'say' espera a que termine el audio anterior (Unreal corta lo que suena si llega otro)."""

    def __init__(self, bridge, unreal):
        self.bridge, self.unreal = bridge, unreal
        self.pending = False        # hay un audio sonando cuyo final aun no hemos recibido
        self.ends_at = 0.0
        self.was_filler = False
        self._think_timer = None

    def _cancel_timer(self):
        if self._think_timer is not None:
            self._think_timer.cancel()
            self._think_timer = None

    def say(self, path, dur, filler=False):
        self._cancel_timer()
        if not self.unreal:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME)
            return
        if self.pending:
            self.bridge.wait({"speech_end"}, max(0.2, self.ends_at - time.time()) + 2.5)
            self.pending = False
            if self.was_filler and not filler:
                time.sleep(BREATH)  # pequena pausa, como una respiracion, antes de responder
        self.bridge.send(cmd="say", file=path.replace("\\", "/"))
        if self.bridge.wait({"speech_start", "error"}, 5) is None:
            log("AVISO: Unreal no confirmo la reproduccion")
        self.pending, self.ends_at, self.was_filler = True, time.time() + dur, filler
        if filler:
            # al acabar la muletilla, la cabeza vuelve a poner cara de pensar
            t = threading.Timer(dur + 0.2, lambda: self.bridge.send(cmd="mode", mode="thinking"))
            t.daemon = True
            t.start()
            self._think_timer = t

    def finish(self):
        self._cancel_timer()
        if self.unreal and self.pending:
            self.bridge.wait({"speech_end"}, max(0.2, self.ends_at - time.time()) + 2.5)
            self.pending = False


def cleanup_replies():
    files = sorted((f for f in os.listdir(REPLY_DIR)
                    if f.startswith(("reply_", "quick_hello_"))),
                   key=lambda f: os.path.getmtime(os.path.join(REPLY_DIR, f)))
    for f in files[:-KEEP_REPLIES]:
        try:
            os.remove(os.path.join(REPLY_DIR, f))
        except OSError:
            pass


# ------------------------------------------------------------------ programa
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", action="append", help="pregunta escrita (sin microfono)")
    ap.add_argument("--lang", default=None, help="idioma de --text (en/es); por defecto se detecta")
    ap.add_argument("--no-camera", action="store_true", help="no encender la webcam (Etapa 4)")
    args = ap.parse_args()

    os.makedirs(REPLY_DIR, exist_ok=True)
    bridge = Bridge()

    # 1) Comprobar Ollama y el modelo
    try:
        tags = ollama("/api/tags", timeout=5)
    except (urllib.error.URLError, OSError):
        sys.exit("Ollama no responde en %s. Abre Ollama (menu Inicio) y vuelve a intentarlo." % OLLAMA_URL)
    if not any(m["name"].startswith(LLM_MODEL) for m in tags.get("models", [])):
        sys.exit("Falta el modelo %s. Ejecuta:  ollama pull %s" % (LLM_MODEL, LLM_MODEL))

    # 2) Cargar modelos (una sola vez).
    # IMPORTANTE: PyTorch/Chatterbox ANTES que Whisper. Si Whisper (ctranslate2) se carga
    # primero, mete su propia libreria cuDNN y PyTorch falla con "cudnnGetLibConfig".
    import logging
    import warnings
    warnings.filterwarnings("ignore")
    for name in ("chatterbox", "huggingface_hub", "transformers", "diffusers"):
        logging.getLogger(name).setLevel(logging.ERROR)    # avisos internos que solo confunden
    os.environ.setdefault("TQDM_DISABLE", "1")
    import torch
    tts = None
    if TTS_ENGINE == "chatterbox":
        log("Cargando voz (Chatterbox, GPU)...")
        from chatterbox.mtl_tts import ChatterboxMultilingualTTS
        from make_intro_audio_chatterbox import EXAGGERATION
        tts = ChatterboxMultilingualTTS.from_pretrained(device=torch.device("cuda" if torch.cuda.is_available() else "cpu"))
        tts.prepare_conditionals(os.path.join(ROOT, "Tools", "tts", "voices", VOICE_REF), exaggeration=EXAGGERATION)
    else:
        log("Voz configurada: %s (fallback offline: Piper)" % TTS_ENGINE)
    log("Cargando Whisper (%s, %s)..." % (WHISPER_MODEL, "GPU" if WHISPER_ON_GPU else "procesador"))
    from faster_whisper import WhisperModel
    whisper = None
    if WHISPER_ON_GPU and torch.cuda.is_available():
        try:
            whisper = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="float16")
            whisper.transcribe(np.zeros(SR, dtype=np.float32), beam_size=1)   # prueba
        except Exception as e:
            log("  Whisper no funciona en la GPU (%s): uso el procesador" % e)
            whisper = None
    if whisper is None:
        whisper = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", cpu_threads=8)
        whisper._on_cpu = True
    prompts, kb_chars = build_system_prompt()
    SYSTEM_PROMPTS.update(prompts)
    log("Conocimiento del colegio: %d caracteres (carpeta Knowledge)" % kb_chars)
    import people
    profiles = people.load_profiles(PROFILES_FILE)
    session = people.Session()
    # los nombres de los perfiles ayudan a Whisper a escribirlos bien (Yassin y no "Yacin")
    hint = WHISPER_HINT + " " + ", ".join(sorted({p["name"] for p in profiles.values()}))
    conv_lang = DEFAULT_LANG
    log("Calentando la IA (%s, %s; la primera vez tarda mas)..." % (LLM_MODEL, "GPU" if LLM_ON_GPU else "procesador"))
    t0 = time.time()
    ask_llm([], "Hola", DEFAULT_LANG)
    log("IA lista en %.1f s" % (time.time() - t0))
    if torch.cuda.is_available():
        log("VRAM usada por la voz: %.2f GB" % (torch.cuda.memory_allocated() / 1e9))

    # 3) Conectar con Unreal y esperar a que termine la presentacion
    # Unreal tarda 1-2 minutos en abrirse: si se lanzan a la vez, esperamos al holograma
    # (antes se rendia a los 2 s y entonces la camara no llegaba a encenderse nunca).
    st = bridge.status(2.0)
    t_wait = time.time()
    while st is None and not args.text and time.time() - t_wait < UNREAL_WAIT:
        if int(time.time() - t_wait) % 20 < 2:
            log("Esperando a que se abra el holograma... (%d s)" % (time.time() - t_wait))
        st = bridge.status(2.0)
    unreal = st is not None
    if not unreal:
        log("AVISO: el holograma no responde (¿esta abierto?). Las respuestas se reproduciran por los altavoces sin animacion.")
    else:
        # Etapa 4: la webcam se enciende con el asistente (solo si el holograma esta abierto).
        if not args.no_camera:
            from vision import FaceTracker, unreal_sender
            up, cam = unreal_sender(UE_PORT)
            TRACKER.append(FaceTracker(up, cam).start())
        while not st.get("intro_done"):
            log("Esperando a que termine la presentacion...")
            bridge.wait({"intro_done"}, 30)
            st = bridge.status(2.0) or {"intro_done": True}
    log("Listo.")

    import fillers as fillers_mod
    fillers = fillers_mod.Fillers(tts, synthesize, log, langs=tuple(LANGS))
    MIN_UTTERANCE = fillers_mod.MIN_UTTERANCE
    speaker = Speaker(bridge, unreal)
    import quick_replies
    quick = quick_replies.QuickReplies(tts, synthesize, profiles, log, langs=tuple(LANGS))

    history = []
    last_talk = time.time()
    pending = list(args.text or [])
    sd = None
    n = 0
    while True:
        # ---------- escuchar
        if args.text is not None:
            if not pending:
                break
            text_in, lang = pending.pop(0), args.lang
            t_stt = 0.0
            if lang is None:
                lang = DEFAULT_LANG
            log("Pregunta escrita [%s]: %s" % (lang, text_in))
            t_heard = time.time()
            if unreal:
                bridge.send(cmd="mode", mode="thinking")
                if TTS_ENGINE == "chatterbox":
                    bridge.send(cmd="busy", on=True)
        else:
            if sd is None:
                import sounddevice as sd
            if unreal:
                bridge.send(cmd="mode", mode="listening")
            log(">>> MICROFONO ACTIVO - escuchando (Ctrl+C para salir) <<<")
            audio = record_utterance(sd)
            t_heard = time.time()
            log(">>> microfono apagado <<<")
            if unreal:
                bridge.send(cmd="mode", mode="thinking")
                if TTS_ENGINE == "chatterbox":
                    bridge.send(cmd="busy", on=True)    # Unreal a 30 FPS: la GPU es para la voz
            # "Mmm..." mientras Whisper escucha, SOLO si Whisper va lento (procesador). En la GPU tarda
            # <1 s: mejor saber antes que ha dicho (un "hola" se contesta al momento, sin "Mmm").
            slow_stt = getattr(whisper, "_on_cpu", False)
            f = fillers.pick("instant") if slow_stt and len(audio) / SR >= MIN_UTTERANCE and USE_FILLERS else None
            if f:
                speaker.say(f[0], f[1], filler=True)
            t0 = time.time()
            audio_sec = len(audio) / SR
            text_in, lang, p = transcribe(whisper, audio, conv_lang, hint)
            del audio   # el audio del microfono no se guarda
            t_stt = time.time() - t0
            if len(text_in) < 2:
                log("  (no he entendido nada, sigo escuchando)")
                # si ha hablado de verdad (no un ruido corto), mejor decirlo que quedarse callado
                c = quick.sorry(conv_lang) if USE_QUICK and audio_sec >= MIN_UTTERANCE else None
                if c:
                    speaker.say(c[1], c[2])
                speaker.finish()
                if unreal and TTS_ENGINE == "chatterbox":
                    bridge.send(cmd="busy", on=False)
                continue
            log("Has dicho [%s %.0f%%]: %s" % (lang, p * 100, text_in))

        # ---------- quien habla (solo por lo que dice; la camara no identifica a nadie)
        face_here = bool(TRACKER) and TRACKER[0].present
        if history and time.time() - last_talk > SESSION_IDLE and not face_here:
            log("  (nueva visita: olvido el nombre y la conversacion anterior)")
            history, _ = [], session.reset()
            conv_lang = DEFAULT_LANG
        note = session.update(text_in, profiles)
        if note:
            log("  Persona: " + note)

        # ---------- lo sencillo ("hola", "¿que tal?", "hola, soy Yassin"...): respuesta grabada, sin IA
        qr = quick.reply(text_in, lang, session, REPLY_DIR) if USE_QUICK else None
        if qr:
            for c in qr:
                if c is qr[0] and not unreal:
                    log("  (respuesta rapida %.1f s despues de que dejaras de hablar)" % (time.time() - t_heard))
                speaker.say(c[1], c[2])
                if c is qr[0] and unreal:
                    log("  (respuesta rapida %.1f s despues de que dejaras de hablar)" % (time.time() - t_heard))
            if unreal and TTS_ENGINE == "chatterbox":
                bridge.send(cmd="busy", on=False)
            reply = " ".join(c[0] for c in qr)
            log("Respuesta rapida: %s" % reply)
            speaker.finish()
            history += [{"role": "user", "content": text_in}, {"role": "assistant", "content": reply}]
            if len(history) > HISTORY_MAX:
                history = history[-HISTORY_KEEP:]
            conv_lang = lang
            cleanup_replies()
            last_talk = time.time()
            continue

        # ---------- pensar y hablar con muletilla inteligente (solo si la IA tarda > FILLER_DELAY):
        t0 = time.time()
        n += 1
        pieces, t_first, t_audio = [], None, 0.0
        t_mark = time.time()
        info = {}
        piece_q = queue.Queue()

        def _produce():
            try:
                for p_txt in stream_llm(history, text_in, lang, session.context(lang), session.turn_note(),
                                        pause_each=(TTS_ENGINE == "chatterbox"), info=info):
                    piece_q.put(("piece", p_txt))
            except Exception as exc:
                piece_q.put(("err", exc))
            finally:
                piece_q.put(("done", None))

        threading.Thread(target=_produce, daemon=True).start()
        filler_played = False
        first_item = None
        if USE_FILLERS and not session.just_introduced and random.random() < THINKING_FILLER_P:
            try:
                first_item = piece_q.get(timeout=FILLER_DELAY)
            except queue.Empty:
                is_q = "?" in text_in
                f = fillers.pick("question" if is_q and random.random() < 0.5 else "thinking", lang)
                if f:
                    speaker.say(f[0], f[1], filler=True)
                    filler_played = True

        k = 0
        while True:
            kind_ev, payload_ev = first_item if first_item is not None else piece_q.get()
            first_item = None
            if kind_ev == "done":
                break
            if kind_ev == "err":
                raise payload_ev
            piece = payload_ev
            pieces.append(piece)
            t_ia = time.time() - t_mark
            out = os.path.join(REPLY_DIR, "reply_%s_%03d_%02d.wav" % (time.strftime("%H%M%S"), n, k))
            t_s = time.time()
            dur = synthesize(tts, piece, lang, out)
            t_audio += dur
            log("  frase %d: esperar a la IA %.1fs | voz %.1fs para %.1fs de audio" % (k + 1, t_ia, time.time() - t_s, dur))
            speaker.say(out, dur)
            t_mark = time.time()
            if t_first is None:
                t_first = time.time() - t_heard
                log("  (empieza a responder %.1f s despues de que dejaras de hablar)" % t_first)
            k += 1
        if unreal and TTS_ENGINE == "chatterbox":
            bridge.send(cmd="busy", on=False)    # ya no se genera voz: Unreal vuelve a 60 FPS
        speaker.finish()
        reply = " ".join(pieces)
        log("Respuesta: %s" % reply)
        log("Tiempos: voz->texto %.1fs | hasta la respuesta %.1fs | respuesta completa %.1fs (audio %.1fs, %d frases)"
            % (t_stt, t_first or 0, time.time() - t_heard, t_audio, len(pieces)))
        history += [info["user"], {"role": "assistant", "content": info.get("raw") or reply}]
        if len(history) > HISTORY_MAX:
            # se recorta de golpe y no un poco en cada turno: si el principio de la conversacion
            # cambia cada vez, Ollama tiene que releerla entera (lento)
            history = history[-HISTORY_KEEP:]
        conv_lang = lang
        cleanup_replies()
        last_talk = time.time()

    if unreal:
        bridge.send(cmd="mode", mode="idle")


TRACKER = []   # Etapa 4: webcam activa (se apaga siempre al salir)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAdios.")
    finally:
        for t in TRACKER:
            t.stop()
