# Conversaciones con contexto: (historial [(visitante, asistente)], pregunta, {modulos aceptables}, tipo)
# tipo: "corta" = seguimiento corto; "larga" = referencia indirecta larga, sin "y/pero/entonces";
#       "respuesta" = se refiere a algo que dijo el ASISTENTE; "cambio" = pregunta nueva e independiente
#       (el contexto NO debe arrastrarla al tema anterior)
from questions import H, O, L, I, P, T, S, A, C, F, G, Y, N

FUND = ("¿Cuándo se fundó el colegio?", "El centro empezó su actividad en 1969 como centro de preescolar y EGB.")
SAN = ("¿Qué ciclos de sanidad tenéis?", "En grado superior tenemos Laboratorio Clínico, Imagen para el Diagnóstico y Radioterapia; en grado medio, Farmacia, Cuidados Auxiliares de Enfermería y Emergencias Sanitarias.")
COM = ("¿Tenéis comedor?", "Sí, Jantxiki en Infantil y Jantoki en Primaria y Secundaria.")
AFR = ("¿Colaboráis con algún país de África?", "Sí, en Kenia trabajamos con St. Paul's University en Nairobi dentro de un consorcio Erasmus+ de salud, y con Marruecos, Túnez y Libia a través de PULSE.")
PROY = ("¿Qué proyectos internacionales tenéis?", "Participamos en Erasmus+, en PULSE sobre emprendimiento y en D-Light, que usa realidad virtual para el cuidado de personas mayores.")
ESP = ("¿Qué espacios tecnológicos tenéis?", "Tenemos la Sala Inmersiva 360º, el CuidaLab de simulación sociosanitaria y los SmartLabs.")
CHI = ("¿Habéis estado en China?", "Sí, formamos parte de una delegación educativa europea que visitó Beijing, Nanchang y Jingdezhen.")
CAL = ("¿Tenéis algún reconocimiento de calidad?", "Sí, la Q de Plata del modelo EFQM en 2005 y la certificación ISO 9001 de AENOR desde 2011.")
VOZ = ("¿Qué tecnología usas para hablar?", "Mi voz principal es Edge Neural TTS y tengo una voz local de respaldo que se llama Piper.")
DENTRO = ("¿Cómo funcionas por dentro?", "Entiendo la voz con Whisper y pienso las respuestas con un modelo de inteligencia artificial que funciona en este ordenador.")
CAM = ("¿Me estás grabando?", "No, la cámara solo detecta si hay alguien delante para orientar mi mirada y no guarda imágenes.")
PUL = ("¿Qué es PULSE?", "Es un proyecto Erasmus+ de emprendimiento en FP con socios de España, Francia, Grecia, Marruecos, Túnez y Libia.")
EMO = ("¿Qué hacéis en educación emocional?", "Tenemos un panel diario de sentimientos y mindfulness desde Educación Infantil.")
EMP = ("¿Tenéis formación para desempleados?", "Sí, formación para el empleo y certificados profesionales vinculados a Lanbide.")
IDI = ("¿En qué idiomas se da clase en Primaria?", "Trabajamos en euskera, castellano e inglés.")
NET = ("¿Necesitas internet?", "Puedo entenderte y responder sin conexión; mi voz principal usa internet, pero sin conexión sigo hablando con una voz local.")

CASES = [
    # --- seguimientos cortos
    ([FUND], "¿Y con quién os fusionasteis?", {H}, "corta"),
    ([SAN], "¿Y cuál tiene más salidas?", {O, S}, "corta"),
    ([COM], "¿Y a qué hora abrís por la mañana?", {S}, "corta"),
    ([CAM], "¿Y el micro?", {Y}, "corta"),
    ([VOZ], "¿Y sin wifi?", {Y, F}, "corta"),
    ([EMP], "¿Son oficiales?", {L}, "corta"),
    # --- referencias indirectas largas
    ([AFR], "Me ha llamado mucho la atención lo de la universidad que has mencionado, ¿en qué área concreta trabajáis con ella?", {I}, "larga"),
    ([CHI], "¿Qué fuisteis a hacer exactamente durante aquel viaje tan largo con la delegación?", {I}, "larga"),
    ([VOZ], "Si mañana se cae la conexión del colegio durante una visita importante, ¿podrías seguir hablando con la gente?", {Y, F}, "larga"),
    ([DENTRO], "Todo eso que me cuentas, ¿lo vas buscando en Google o en alguna web mientras hablamos contigo?", {Y, F}, "larga"),
    ([CAM], "Lo que te estoy diciendo ahora mismo por el micrófono, ¿queda guardado en algún sitio después?", {Y}, "larga"),
    ([EMO], "Me parece precioso, ¿desde qué edad pueden empezar los niños en esa etapa en vuestro colegio?", {O}, "larga"),
    ([EMP], "Mi hermano está buscando trabajo, ¿esos certificados que comentas tienen validez oficial para él?", {L}, "larga"),
    ([IDI], "Me parece muy bien, ¿la plataforma con la que os comunicáis con las familias cuál es?", {S}, "larga"),
    ([NET], "Me deja más tranquilo, pero cuando no hay conexión, ¿se nota mucho la diferencia en cómo suenas?", {Y, F}, "larga"),
    # --- referencias a algo que dijo el asistente
    ([PROY], "Háblame un poco más del último que has nombrado, por favor, me interesa bastante", {P}, "respuesta"),
    ([ESP], "El segundo que has dicho, ¿qué tipo de prácticas hacen allí los alumnos exactamente?", {T}, "respuesta"),
    ([CAL], "¿Qué significa exactamente la primera distinción que has comentado?", {H, A}, "respuesta"),
    ([PUL], "Esos países del norte de África que has mencionado, ¿colaboran también en otras cosas con vosotros?", {I, P}, "respuesta"),
    ([AFR], "Lo de la ciudad keniana que has dicho, ¿vienen alumnos de allí?", {I}, "respuesta"),
    ([SAN], "El último ciclo de grado medio que has nombrado, ¿tiene prácticas reales?", {O, T, S}, "respuesta"),
    # --- cambios de tema (el contexto no debe estorbar)
    ([FUND], "¿Tenéis servicio de comedor para los pequeños?", {S}, "cambio"),
    ([NET], "¿Qué ciclos de grado medio ofrecéis?", {O}, "cambio"),
    ([PUL], "¿Cuándo se fundó el colegio?", {H}, "cambio"),
    ([CHI], "¿Me estás grabando con la cámara?", {Y}, "cambio"),
    ([COM], "¿Qué es el proyecto D-Light?", {P}, "cambio"),
    ([ESP], "¿Tenéis Bachillerato?", {F, O}, "cambio"),
    ([AFR], "¿Hacéis algo contra las fake news?", {P}, "cambio"),
    ([CAL], "¿Necesitas internet para funcionar?", {Y, F}, "cambio"),
    ([VOZ], "¿Qué certificados profesionales tenéis con Lanbide?", {L}, "cambio"),
    # --- International Campus (25-11-2026)
    ([("¿Formáis parte de redes europeas?", "Sí, nos relacionamos con redes europeas como EFVET, INNOTECS y YES Forum, y en el País Vasco con Tknika y AICE-IZEA.")],
     "¿Y la última que has nombrado a qué se dedica exactamente?", {C}, "respuesta"),
    ([("¿Qué servicios ofrece International Campus?", "Gestionamos movilidades, job shadowing para docentes, y difundimos proyectos europeos KA2, Capacity Building y CoVE.")],
     "¿Qué es eso del CoVE que has dicho?", {G, P}, "respuesta"),
    ([("¿Qué relación tenéis con Tknika?", "Colaboramos con Tknika, el centro vasco de innovación en FP, y aplicamos su metodología ETHAZI.")],
     "¿Y con la agencia nacional de Erasmus?", {C}, "corta"),
    ([("¿Ofrecéis job shadowing?", "Sí, Calasanz International Campus ofrece formación y job shadowing para docentes internacionales.")],
     "Soy profesora en Portugal, ¿cómo podría solicitarlo y cuánto tiempo suele durar una estancia así?", {I, F, G}, "larga"),
    ([("¿Qué es EFVET?", "Es una red europea de centros de Formación Profesional.")],
     "¿Tenéis comedor?", {S}, "cambio"),
]
