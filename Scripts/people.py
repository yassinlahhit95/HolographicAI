# Reconocimiento de personas POR NOMBRE (lo que la persona dice, nunca la camara).
#
# - Los perfiles estan en Knowledge\people_profiles.json (se editan sin tocar codigo).
# - Solo cuenta como presentacion que la persona hable de SI MISMA ("soy Rafa", "me llamo Rafa",
#   "I'm Rafa"). Mencionar a otra persona ("¿conoces a Rafa?") no cambia quien esta hablando.
# - Nada se guarda en disco: la memoria de la sesion vive en RAM y se borra al terminar la sesion.
#
# Prueba rapida (sin IA):  python Scripts\people.py "Hola, soy Yassine"
import json
import os
import random
import re
import sys
import unicodedata

GREETING_EXAMPLE_P = 0.35   # probabilidad de ensenar a la IA el saludo de ejemplo del perfil
FIELDS_TEXT = ("name", "role", "description", "personality", "greeting")
FIELDS_LIST = ("aliases", "topics", "conversation_guidelines", "privacy_restrictions")


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------ nombres
def normalize(name):
    """'Raúl' -> 'raul', 'Iñaki' -> 'inaki', 'Yassine' -> 'yassine'."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def loose(name):
    """Forma 'suelta' para variantes de escritura: letras dobles y 'e' final fuera.
    Yassin / Yassine / Yasin -> 'yasin'."""
    s = normalize(name).replace(" ", "")
    # sonidos que Whisper escribe de varias formas: Yacin/Yassin, Iñaki/Inaqui, Zuriñe/Suriñe
    s = re.sub(r"c(?=[ei])", "s", s).replace("z", "s").replace("qu", "k").replace("ch", "x").replace("c", "k")
    s = re.sub(r"(.)\1+", r"\1", s)
    return s[:-1] if len(s) > 4 and s.endswith("e") else s


# ------------------------------------------------------------------ perfiles
def _clean_profile(p, i):
    if not isinstance(p, dict):
        raise ValueError("el perfil %d no es un objeto {...}" % i)
    name = p.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("el perfil %d no tiene 'name'" % i)
    out = dict(p)        # se conservan tambien los campos extra que tenga el JSON
    out.setdefault("id", normalize(name).replace(" ", "_"))
    for f in FIELDS_TEXT:
        v = p.get(f, "")
        out[f] = v.strip() if isinstance(v, str) else ""
    for f in FIELDS_LIST:
        v = p.get(f, [])
        if isinstance(v, str):
            v = [v]
        out[f] = [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    return out


def load_profiles(path):
    """Devuelve {forma_suelta_del_nombre: perfil}. Nunca lanza error: si el archivo falta o
    esta mal, avisa y sigue sin perfiles (el asistente funciona igual)."""
    if not os.path.exists(path):
        log("Perfiles: no existe %s (sigo sin perfiles)" % path)
        return {}
    try:
        with open(path, encoding="utf-8-sig") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        log("Perfiles: ERROR leyendo %s -> %s (sigo sin perfiles)" % (os.path.basename(path), e))
        return {}
    people = data.get("people") if isinstance(data, dict) else data
    if not isinstance(people, list):
        log("Perfiles: el JSON debe tener una lista 'people' (sigo sin perfiles)")
        return {}
    index = {}
    for i, p in enumerate(people):
        try:
            p = _clean_profile(p, i)
        except ValueError as e:
            log("Perfiles: salto un perfil -> %s" % e)
            continue
        for n in [p["name"]] + p["aliases"]:
            key = loose(n.split()[0]) if n.split() else ""
            if not key:
                continue
            if key in index and index[key]["id"] != p["id"]:
                log("Perfiles: AVISO el nombre '%s' esta en dos perfiles (%s y %s); uso el primero"
                    % (n, index[key]["id"], p["id"]))
                continue
            index[key] = p
    log("Perfiles cargados: %d personas (%s)"
        % (len({p["id"] for p in index.values()}), ", ".join(sorted({p["name"] for p in index.values()}))))
    return index


# ------------------------------------------------------------------ detectar presentaciones
TITLES = r"(?:(?:el|la|the)\s+)?(?:(?:profe(?:sor|sora)?|maestr[oa]|director[a]?|jefe|jefa|coordinador[a]?|" \
         r"tutor[a]?|don|doña|teacher|mr\.?|mrs\.?|ms\.?|miss|dr\.?|doctor[a]?)\s+)?"
NAME = r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]+)"
INTRO_PATTERNS = [
    r"\bme llamo\s+" + NAME,
    r"\bmi nombre es\s+" + NAME,
    r"\bmy name is\s+" + NAME,
    r"\bsoy\s+" + TITLES + NAME,
    r"\b(?:i am|i'm|im|this is|it's)\s+" + TITLES + NAME,
]
# Palabras que pueden ir detras de "soy"/"I'm" y NO son nombres.
NOT_NAMES = set("""
de del un una el la los las yo nuevo nueva alumno alumna estudiante profesor profesora profe maestro maestra
director directora padre madre abuelo abuela visitante amigo amiga muy bastante tan solo aqui aca
de la familia del colegio tu su vuestro vuestra
a an the from here new student teacher parent visitor very so just fine good okay ok glad happy sorry not
calasanz santurtzi colegio holograma
bien mal genial feliz encantado encantada curioso curiosa interesado interesada informatico informatica
""".split())
# "soy profesor de informatica" -> papel confirmado en esta sesion (no se guarda)
ROLE_PATTERN = re.compile(
    r"\b(?:soy|trabajo como|i am|i'm|i work as)\s+(?:un |una |el |la |a |an |the )?"
    r"((?:profesor|profesora|profe|maestr[oa]|director[a]?|jefe de estudios|coordinador[a]?|tutor[a]?|"
    r"orientador[a]?|alumn[oa]|estudiante|exalumn[oa]|padre|madre|familia|conserje|secretari[oa]|"
    r"teacher|student|parent|principal|headteacher)"
    r"(?:\s+(?:de|del|en|of|in)\s+[\wáéíóúñ ]{2,40})?)", re.I)


def find_introduction(text, profiles=None):
    """Nombre con el que la persona se presenta, o None."""
    for pat in INTRO_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            cand = m.group(1)
            if normalize(cand) in NOT_NAMES:
                continue
            known = profiles is not None and loose(cand) in profiles
            # Whisper escribe los nombres propios con mayuscula; si no la tiene y no es un nombre
            # conocido, lo mas probable es que no sea un nombre ("soy vegetariano").
            if not known and not cand[0].isupper():
                continue
            return cand[0].upper() + cand[1:]
    return None


def find_role(text):
    m = ROLE_PATTERN.search(text)
    if not m:
        return None
    role = m.group(1).strip(" .,!?")
    return re.split(r"\s+(?:y|and|pero|but)\s+", role)[0]


# ------------------------------------------------------------------ memoria de la sesion
VISITOR_SIGNALS = [
    ("delegation", re.compile(r"\b(?:delegaci[oó]n|venimos de (?:un |una )?(?:centro|instituto|universidad|pa[ií]s)|from (?:portugal|poland|italy|china|kenya)|de (?:portugal|italia|polonia|china|kenia|francia|grecia|estonia|finlandia))\b", re.I)),
    ("university", re.compile(r"\b(?:universidad|facultad|grado universitario)\b", re.I)),
    ("company", re.compile(r"\b(?:empresa|compa[ñn][ií]a|sector (?:sanitario|m[eé]dico|tecnol[oó]gico)|plantilla|contratar|reclutar)\b", re.I)),
    ("director", re.compile(r"\b(?:soy director|soy directora|dirijo un centro|equipo directivo)\b", re.I)),
    ("teacher", re.compile(r"\b(?:soy profe|profesor|profesora|docente|maestro|maestra|ense[ñn]o)\b", re.I)),
    ("family", re.compile(r"\b(?:mi hij[oa]|nuestr[oa] hij[oa]|somos padres|buscamos colegio|para mi ni[ñn][oa])\b", re.I)),
    ("child", re.compile(r"\b(?:soy un ni[ñn]o|soy una ni[ñn]a|tengo (?:6|7|8|9|10|11) a[ñn]os)\b", re.I)),
    ("student", re.compile(r"\b(?:estoy en (?:eso|4|cuarto)|quiero estudiar|soy alumno|soy alumna|soy estudiante)\b", re.I)),
]
INTEREST_SIGNALS = [
    ("salud / CuidaLab", re.compile(r"\b(?:sanidad|sanitari[oa]|salud|enfermer|farmacia|cuidalab|radioterapia|laboratorio|dependencia|mayores)\b", re.I)),
    ("tecnología / RV / IA", re.compile(r"\b(?:tecnolog[ií]a|realidad virtual|rv|inteligencia artificial|ia|rob[oó]tica|3d|360|inmersiva|smartlab|simulaci[oó]n)\b", re.I)),
    ("internacional / Erasmus+", re.compile(r"\b(?:internacional|erasmus|china|africa|[aá]frica|kenia|europa|intercambio|movilidad|delegaci[oó]n|colabora)\b", re.I)),
    ("emprendimiento", re.compile(r"\b(?:emprend|empresa|urrats|enpresari|pulse|negocio|tkgune)\b", re.I)),
    ("sostenibilidad / inclusión", re.compile(r"\b(?:sostenib|ecolog|agenda 2030|cesar|inclusi[oó]n|diversidad|amor|apoyo)\b", re.I)),
]


class Session:
    """Lo que el asistente sabe de la persona que tiene delante, SOLO durante esta visita."""

    def __init__(self):
        self.name = None        # nombre dicho por la persona
        self.profile = None     # perfil aprobado (o None si es desconocida)
        self.role = None        # papel que la persona ha confirmado en esta sesion
        self.visitor_type = None
        self.organization = None
        self.sector = None
        self.interests = []
        self.topics_discussed = []
        self.relevant_projects = []
        self.corrections = []
        self.current_goal = None
        self.just_introduced = False

    def reset(self):
        self.__init__()

    def update(self, text, profiles):
        """Analiza lo que ha dicho la persona. Devuelve una frase para el registro, o None."""
        self.just_introduced = False
        note = []
        name = find_introduction(text, profiles)
        if name and self.name and loose(name) == loose(self.name):
            self.just_introduced = True     # se vuelve a presentar: se le vuelve a saludar (sin olvidar nada)
        elif name:
            # Si cambia de persona en la misma sesion sin pausa, reiniciamos memoria personal previa
            if self.name:
                self.reset()
            self.name = name
            self.profile = profiles.get(loose(name))
            self.role = None
            self.just_introduced = True
            note.append("presentacion: %s -> %s" % (name, ("perfil '%s'" % self.profile["id"])
                                                    if self.profile else "sin perfil"))
        role = find_role(text)
        if role and not self.profile:
            self.role = role
            note.append("papel confirmado en esta sesion: %s" % role)
        m_org = re.search(
            r"\b(?:vengo de|venimos de|somos de|trabajo en|represento a|de la empresa|del instituto|de la universidad)\s+"
            r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9' -]{3,40})", text, re.I
        )
        if m_org:
            self.organization = re.split(r"[.,;?!]|\s+(?:y|para|que|buscamos)\s+", m_org.group(1))[0].strip()
        for vtype, pat in VISITOR_SIGNALS:
            if pat.search(text):
                self.visitor_type = vtype
                break
        if re.search(r"\b(?:sanidad|sanitario|salud|enfermer|hospital|m[eé]dico)\b", text, re.I):
            self.sector = "sanitario"
        elif re.search(r"\b(?:tecnolog|software|rob[oó]tica|ia|realidad virtual|3d)\b", text, re.I):
            self.sector = "tecnológico"
        elif re.search(r"\b(?:educaci[oó]n|colegio|instituto|universidad|fp|docente)\b", text, re.I):
            self.sector = "educativo"
        if re.search(r"\b(?:no me refer[ií]a|hablaba de|digo )\b", text, re.I):
            self.corrections = (self.corrections + [text.strip()[:60]])[-2:]
        if re.search(r"\b(?:colaborar|colaboraci[oó]n|juntos|socios|acuerdo|convenio)\b", text, re.I):
            self.current_goal = "explorar colaboración"
        for proj in ("CuidaLab", "SmartLabs", "Sala Inmersiva 360", "ETHAZI", "PULSE", "D-Light", "FOR", "A.M.O.R.", "C.E.S.A.R.", "Erasmus+"):
            if proj.lower() in text.lower() and proj not in self.relevant_projects:
                self.relevant_projects = (self.relevant_projects + [proj])[-4:]
        for label, pat in INTEREST_SIGNALS:
            if pat.search(text):
                if label not in self.interests:
                    self.interests = (self.interests + [label])[-4:]
                if label not in self.topics_discussed:
                    self.topics_discussed = (self.topics_discussed + [label])[-5:]
        return "; ".join(note) or None

    def context(self, lang):
        """Perfil de la persona actual para la IA ('' si no sabemos quien es).
        IMPORTANTE para la velocidad: este texto NO cambia entre turnos, asi Ollama lo lee una sola vez
        (cada cambio le obliga a releer el perfil y toda la conversacion: ~12 s en el procesador).
        Lo que cambia en cada turno va en turn_note(). Las reglas generales estan en _identidad_asistente.txt."""
        if not self.name:
            return ""
        if self.profile:
            p = self.profile
            status = p.get("validation_status", "")
            L = ["CURRENT VISITOR: %s (%s)." % (p.get("full_name") or p["name"], status or "approved profile")]
            if status == "draft":
                L.append("Note: this profile is a DRAFT; do not state unconfirmed titles or details as official facts.")
            for label, key in (("Position", "official_position"), ("Role", "role"), ("Department", "department"),
                               ("About", "public_description"), ("Note", "description"), ("Tone", "personality")):
                if p.get(key):
                    L.append("%s: %s" % (label, p[key]))
            if p["topics"]:
                L.append("Topics they like: %s" % ", ".join(p["topics"]))
            for g in p["conversation_guidelines"] + p["privacy_restrictions"]:
                L.append("- %s" % g)
            return "\n".join(L)
        # el papel confirmado va en turn_note(): si cambiara este texto, Ollama releeria la conversacion
        return "CURRENT VISITOR: says their name is %s. No approved profile: do not guess their role." % self.name

    def turn_note(self):
        """Nota corta para ESTE turno (va pegada a la pregunta, al final, para no romper la cache)."""
        parts = []
        if self.visitor_type:
            parts.append("Visitor type: %s." % self.visitor_type)
        if self.organization:
            parts.append("Org: %s." % self.organization)
        if self.sector:
            parts.append("Sector: %s." % self.sector)
        if self.current_goal:
            parts.append("Goal: %s." % self.current_goal)
        if self.interests:
            parts.append("Interests: %s." % ", ".join(self.interests))
        if self.relevant_projects:
            parts.append("Projects mentioned: %s." % ", ".join(self.relevant_projects))
        if self.topics_discussed:
            parts.append("Already discussed: %s (do not repeat)." % ", ".join(self.topics_discussed[-3:]))
        if not self.name:
            return ("(" + " ".join(parts) + ")") if parts else ""
        role = (" They told you their role: %s; adapt to it without inventing details." % self.role) if self.role else ""
        if not self.just_introduced:
            parts.insert(0, "Already greeted: do not greet again or ask who they are.%s" % role)
            return "(%s)" % " ".join(parts)
        if self.profile:
            note = ("They just introduced themself: greet %s warmly by name, nice to SEE them again, "
                    "one or two short sentences, fresh words." % self.profile["name"])
            if self.profile["greeting"] and random.random() < GREETING_EXAMPLE_P:
                note += " Style they like, in your own words: %s" % self.profile["greeting"]
            return "(%s)" % note
        if self.role:
            return "(They just introduced themself: greet %s warmly by name, short.)" % self.name
        return ("(They just introduced themself: greet %s warmly by name and ask kindly whether they are a "
                "teacher here at Calasanz or what brings them here. Two short sentences.)" % self.name)


# ------------------------------------------------------------------ prueba rapida
if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profs = load_profiles(os.path.join(root, "Knowledge", "people_profiles.json"))
    s = Session()
    for t in sys.argv[1:] or ["Hola, soy Yassine", "¿Conoces a Rafa?", "Soy profesor de informática"]:
        print("\n>", t, "|", s.update(t, profs))
        print(s.context("es"))
        print(s.turn_note())
