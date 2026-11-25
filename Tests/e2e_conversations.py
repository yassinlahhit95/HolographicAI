"""Prueba completa con la IA (Ollama + qwen3:4b-instruct), sin voz ni Unreal.
Uso: python Tests/e2e_conversations.py [general|internet|contexto|campus|equipo|presentaciones|todo]
Guarda el resultado en Tests/results/e2e_<grupo>_<fecha>.txt"""
import sys, os, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "retrieval"))
from common import load_assistant, docs_of

GENERAL = [
 ["¿Qué ciclos de sanidad tenéis?", "¿Y cuál de ellos tiene más salidas?", "¿Hacen prácticas en el extranjero?"],
 ["¿Quién te ha creado?", "¿Necesitas internet para funcionar?", "¿Me recordarás si vuelvo la semana que viene?", "¿Me estás grabando con la cámara?"],
 ["¿Trabajáis con simulaciones de electricidad o con CALASANZ AR?"],
 ["La FP me parece menos práctica de lo que dicen, ¿por qué merece la pena?"],
 ["¡Qué interesante!"],
 ["¿La inteligencia artificial sustituirá a los profesores?", "Pero entonces, ¿para qué sirve en clase?"],
 ["¿Qué diferencia hay entre realidad virtual y realidad aumentada?", "¿Y vosotros cuál usáis?"],
 ["¿Cómo sería el aula del futuro para un ciclo de enfermería?"],
 ["Soy de una universidad de Kenia, ¿cómo podríamos colaborar?", "¿Nos daríais financiación?"],
 ["¿Cómo puede ayudar la tecnología a las personas mayores?"],
 ["¿Cuánto cuesta la matrícula?", "¿Y dónde lo miro?"],
 ["¿Cuándo se fundó el colegio?", "¿Y con quién os fusionasteis?"],
 ["¿Tenéis comedor y madrugadores?"],
 ["¿Qué es el proyecto PULSE?", "¿Qué relación tiene con el emprendimiento que trabajáis aquí?"],
 ["Eres muy simpático, ¿eres una persona?"],
 ["¿Por qué es importante internacionalizar la FP?"],
 ["¿Hacéis algo contra las fake news?"],
 ["¿Tenéis Bachillerato?"],
]
INTERNET = [
 ["¿Necesitas internet para funcionar?"],
 ["¿Funcionas sin conexión?"],
 ["¿Qué pasa si se va el wifi?"],
 ["¿Puedes buscar en internet qué tiempo hará mañana?"],
 ["Si desenchufamos el router, ¿te quedas mudo?"],
 ["¿Consultas Google para responderme?"],
 ["¿Cómo me entiendes cuando hablo?", "¿Y para eso hace falta estar conectado?", "¿Y tu voz?"],
 ["¿Qué tecnología usas para hablar?", "Si mañana se cae la conexión del colegio durante una visita importante, ¿podrías seguir hablando con la gente?", "¿Se notaría mucho la diferencia?"],
 ["¿Quién eres?", "Todo eso que me cuentas, ¿lo vas buscando en alguna web mientras hablamos?"],
]
CONTEXTO = [
 ["¿Colaboráis con algún país de África?", "Me ha llamado mucho la atención lo de la universidad que has mencionado, ¿en qué área concreta trabajáis con ella?"],
 ["¿Qué proyectos internacionales tenéis?", "Háblame un poco más del último que has nombrado, por favor, me interesa bastante"],
 ["¿Qué espacios tecnológicos tenéis?", "El segundo que has dicho, ¿qué tipo de prácticas hacen allí los alumnos exactamente?"],
 ["¿Tenéis algún reconocimiento de calidad?", "¿Qué significa exactamente la primera distinción que has comentado?"],
 ["¿Habéis estado en China?", "¿Qué fuisteis a hacer exactamente durante aquel viaje tan largo con la delegación?"],
 ["¿Tenéis formación para desempleados?", "Mi hermano está buscando trabajo, ¿esos certificados que comentas tienen validez oficial para él?"],
 ["¿Qué es PULSE?", "¿Cuándo se fundó el colegio?"],
]
CAMPUS = [
 ["¿Qué es Calasanz International Campus?", "¿Qué servicios ofrecéis?"],
 ["¿Quién se encarga de la internacionalización?", "¿Y quiénes son los tutores Erasmus?"],
 ["¿Qué relación tenéis con Tknika?"],
 ["¿Qué es EFVET?", "¿Sois miembros oficiales?"],
 ["¿Formáis parte de redes europeas?", "¿Y en el País Vasco?"],
 ["¿Qué diferencia hay entre Erasmus y Capacity Building?", "¿Participáis en alguno de Capacity Building?"],
 ["¿Qué es un CoVE?", "¿Vosotros sois un CoVE?"],
 ["¿Ofrecéis formación para profesores extranjeros?"],
 ["¿Puedo hacer job shadowing en vuestro centro?", "¿Cuántas plazas hay y cuánto dinero dan?"],
 ["Somos una empresa, ¿cómo podemos colaborar?"],
 ["Somos un centro de FP de Marruecos, ¿podríamos trabajar juntos?"],
 ["¿Cómo ayudáis a los alumnos a mejorar su empleabilidad?"],
 ["¿Qué competencias desarrollan los alumnos durante una movilidad?"],
 ["¿Qué significa internacionalizar el currículo?", "¿Me pones un ejemplo práctico?"],
 ["¿Qué diferencia hay entre el SEPIE y Tknika?"],
 ["¿Qué relación tenéis con Teknika?"],
 ["¿Qué es la CECE?", "¿Y Bilbao Metropoli 30?", "¿Y el INJUVE?"],
 ["¿Cuál es la visión de vuestra internacionalización?"],
]
EQUIPO = [
 ["¿Quién es la directora del colegio?", "¿Y cómo es ella?"],
 ["¿Quién es Rafa?", "¿Qué tal persona es?"],
 ["¿Quién es Rafael Balparda?"],
 ["¿Quién se encarga de la parte internacional?", "Háblame un poco más de él"],
 ["¿Quién es Raúl Setién?"],
 ["¿Quién es el director de innovación?", "¿Es buen jefe?"],
 ["¿Quién lleva la informática del colegio?", "¿Y cómo es trabajar con él?"],
 ["Háblame de Jesús"],
 ["¿Quiénes forman el equipo del centro?"],
 ["¿Quién es Rafa Valparda?"],
 ["¿Quién es Raul Setien?"],
 ["¿Me das el móvil de Maribel?"],
 ["¿Quién es el director del colegio?"],
]
# La propia persona se presenta: se usa people.Session y el perfil, como en el asistente real.
PRESENTACIONES = [
 ["Hola, soy Raúl Setién, ¿qué proyectos de innovación tenéis ahora mismo?", "¿Qué me recomiendas mejorar?"],
 ["Buenos días, soy Maribel. ¿Cómo está yendo la jornada de puertas abiertas?"],
 ["Hola, me llamo Jesús, soy el coordinador TIC. ¿Funciona bien la cámara?", "¿Y si se va internet?"],
 ["Hola, soy Rafa, vengo con una delegación de Portugal. ¿Les cuentas qué es International Campus?"],
 ["Soy Rafael Balparda. ¿Qué tal todo?"],
]
GROUPS = {"general": GENERAL, "internet": INTERNET, "contexto": CONTEXTO, "campus": CAMPUS, "equipo": EQUIPO,
          "presentaciones": PRESENTACIONES}

def run(name, convs, a, out):
    import people
    profiles = people.load_profiles(a.PROFILES_FILE) if name == "presentaciones" else {}
    for conv in convs:
        hist = []; session = people.Session()
        out("=" * 70)
        for q in conv:
            info = {}; t = time.time()
            intent, _, needs_kb = a.detect_intent(q)
            mods = [x[:2] for x in docs_of(a, a.retrieve_knowledge(q, hist))] if needs_kb else []
            if profiles:
                note = session.update(q, profiles)
                if note:
                    out("   [persona: %s]" % note)
            ans = " ".join(a.stream_llm(hist, q, "es", session.context("es"), session.turn_note(),
                                        pause_each=False, info=info))
            hist += [info["user"], {"role": "assistant", "content": info["raw"]}]
            out("P: %s\n   [%s | modulos %s | %.1fs]\nR: %s" % (q, intent, mods, time.time() - t, ans))

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "todo"
    a = load_assistant("e5")
    a.SYSTEM_PROMPTS.update(a.build_system_prompt()[0])
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    for name in (GROUPS if which == "todo" else [which]):
        path = os.path.join(HERE, "results", "e2e_%s_%s.txt" % (name, time.strftime("%Y-%m-%d")))
        with open(path, "w", encoding="utf-8") as fh:
            def out(s):
                print(s, flush=True); fh.write(s + "\n"); fh.flush()
            out("# %s | modelo %s | %s" % (name, a.LLM_MODEL, time.strftime("%Y-%m-%d %H:%M")))
            run(name, GROUPS[name], a, out)
