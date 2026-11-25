# (pregunta, {modulos aceptables})  -- 105 preguntas, estilo visitante hablado
H="02_historia_y_centro.md";O="03_oferta_educativa.md";L="04_formacion_lanbide.md";I="05_internacionalizacion.md"
P="06_proyectos_internacionales.md";T="07_innovacion_y_tecnologia.md";S="08_instalaciones_y_servicios.md"
A="09_actividades_escolares.md";C="10_colaboraciones.md";F="11_preguntas_frecuentes.md";G="13_conocimiento_educativo_general.md"
Y="14_identidad_y_capacidades_del_asistente.md";N="15_proyectos_internos_y_simulaciones.md"
Q=[
("¿Cuándo se fundó el colegio?",{H}),("¿Desde qué año existe Calasanz?",{H}),("¿Qué pasó en 2015 con el edificio?",{H,S}),
("¿Con qué centro os fusionasteis en 2020?",{H}),("¿Tenéis algún certificado de calidad?",{H,A}),("¿Qué es eso de la Q de Plata?",{H,A}),
("¿Desde cuándo hay Formación Profesional aquí?",{H}),("¿Qué es Calasanz Lanbide Ikastegia?",{H}),
("¿Qué etapas educativas tenéis?",{O}),("¿Desde qué edad aceptáis niños en Infantil?",{O}),("¿Usáis el método Singapur?",{O}),
("¿En qué idiomas se da clase en Primaria?",{O}),("¿Los alumnos de la ESO usan ordenador?",{O}),("¿Qué ciclos de sanidad tenéis?",{O}),
("¿Hay un grado de farmacia?",{O}),("¿Puedo estudiar radioterapia?",{O}),("¿Qué ciclos de grado medio ofrecéis?",{O}),
("Mi hija quiere estudiar marketing, ¿tenéis algo?",{O}),("¿Tenéis Bachillerato?",{F,O}),("¿Qué es el modelo ETHAZI?",{O,G,T,I,C}),
("¿Qué empleabilidad tiene la FP?",{O,S}),("¿Hay robótica en Primaria?",{O}),("¿Tenéis integración social?",{O}),
("¿Qué es el proyecto ONE TO ONE?",{O}),("¿Hay emergencias sanitarias?",{O}),
("¿Hacéis cursos para desempleados?",{L}),("¿Hay formación gratis para trabajadores?",{L}),("¿Qué certificados de profesionalidad tenéis?",{L}),
("¿Hay plazas libres en el curso de contabilidad?",{L,F}),("¿Hacéis formación a medida para empresas?",{L,C}),("¿Qué es Tkgune?",{L,C}),
("¿Dónde veo los cursos de Lanbide abiertos?",{L}),
("¿Qué es Calasanz International Campus?",{I}),("¿Quién lleva la parte internacional?",{I,C}),("¿Habéis estado en China?",{I}),
("¿Qué hicisteis en Beijing?",{I}),("¿Tenéis relación con Kenia?",{I}),("¿Con qué países europeos colaboráis?",{I}),
("¿Los alumnos de FP pueden hacer prácticas en el extranjero?",{I,P}),("¿Qué es el job shadowing?",{I,P}),("¿Trabajáis con Marruecos o Túnez?",{I,P}),
("¿Qué es Erasmus+?",{P,I}),("¿Qué es el proyecto PULSE?",{P,I}),("¿Qué es D-Light?",{P}),("¿Tenéis algo contra las fake news?",{P}),
("¿Qué es VET4YE?",{P}),("¿Algún proyecto de inclusión para alumnos con necesidades especiales?",{P}),("¿Hacéis algo de economía circular?",{P}),
("¿Qué es eTwinning?",{P,O,A}),("¿Qué premio ganó el proyecto de realidad virtual para mayores?",{P}),("¿Qué es ENNEPlus?",{P}),
("¿Qué es CuidaLab?",{T}),("¿Qué son los SmartLabs?",{T}),("¿Tenéis sala inmersiva?",{T,S}),("¿Usáis realidad virtual en clase?",{T,P,G}),
("¿Hacéis bioimpresión 3D?",{T}),("¿Qué metodologías activas usáis?",{T,O}),("¿Fomentáis el emprendimiento?",{T,P}),
("¿Dónde está el colegio?",{S}),("¿Tenéis comedor?",{S}),("¿A qué hora abre el servicio de madrugadores?",{S}),("¿Dónde se compran los uniformes?",{S}),
("¿Hay AMPA?",{S}),("¿Qué plataforma usáis con las familias?",{S}),("¿Se pueden alquilar las instalaciones?",{S}),("¿Hay bolsa de empleo?",{S}),
("¿Hacéis mindfulness?",{A,O}),("¿Qué es Bikoteka irakurtzen?",{A,O}),("¿Hacéis excursiones?",{A}),("¿Cuándo son las jornadas de puertas abiertas?",{A}),
("¿Tenéis huerta escolar?",{A}),("¿Qué premios ha recibido el colegio?",{A,H}),
("Somos una empresa, ¿podemos colaborar?",{C,F}),("Soy de una universidad extranjera, ¿cómo establecemos un convenio?",{C,I}),
("¿Nos dais financiación si colaboramos?",{C}),("¿Con quién hablo para una visita institucional?",{C,I}),
("¿Cuánto cuesta la matrícula?",{F}),("¿Cuál es el horario de secretaría?",{F}),("¿Cuándo empieza la prematrícula?",{F}),
("¿Cuál es la diferencia entre aprendizaje basado en retos y por proyectos?",{G}),("¿La inteligencia artificial sustituirá a los profesores?",{G}),
("¿Qué diferencia hay entre realidad virtual y aumentada?",{G}),("¿Qué es DigComp?",{G}),("¿Por qué es importante internacionalizar la FP?",{G,I}),
("¿Cómo imagináis la educación dentro de diez años?",{G}),("¿Las simulaciones pueden reemplazar las prácticas reales?",{G}),
("¿Qué opinas de la IA en las aulas?",{G}),("¿Cómo puede ayudar la tecnología a las personas mayores?",{G,T,P}),("¿Qué es GreenComp?",{G}),
("¿Quién eres?",{Y}),("¿Quién te ha creado?",{Y}),("¿Necesitas internet para funcionar?",{Y}),("¿Me grabas con la cámara?",{Y}),
("¿Me recordarás si vuelvo la semana que viene?",{Y}),("¿Qué modelo de inteligencia artificial usas?",{Y}),("¿Guardas lo que digo?",{Y}),
("¿Eres una persona de verdad?",{Y}),("¿Con qué programa te han hecho en 3D?",{Y}),("¿Qué no sabes hacer?",{Y}),("¿Cómo me entiendes cuando hablo?",{Y}),
("¿Trabajáis con CALASANZ AR?",{N}),("¿Tenéis simulaciones de electricidad?",{N}),("¿Hay una plataforma para gestionar Erasmus?",{N}),
("¿Qué proyectos tecnológicos están en desarrollo?",{N,T}),("¿Hacéis simulaciones de construcción?",{N}),
]
assert len(Q)==105, len(Q)

# Formulaciones distintas de la misma duda sobre internet (debe llegar el modulo 14 y/o las FAQ 11)
Q_INTERNET = [(q, {Y, F}) for q in [
    "¿Necesitas internet para funcionar?", "¿Funcionas sin conexión?", "¿Qué pasa si se va el wifi?",
    "¿Estás conectado a internet ahora mismo?", "¿Puedes buscar en internet qué tiempo hará mañana?",
    "¿Necesitas red para entenderme?", "Si desenchufamos el router, ¿te quedas mudo?",
    "¿Tu voz sale de internet o la generas tú?", "¿Consultas Google para responderme?",
    "¿Podrías funcionar en un sitio sin cobertura?",
]]

# Calasanz International Campus (actualización 25-11-2026): (pregunta, {modulos}, texto del titulo de seccion esperado o None, tipo)
Q_CAMPUS = [
    # preguntas de evaluacion del encargo
    ("¿Qué es Calasanz International Campus?", {I}, None, "directa"),
    ("¿Qué servicios ofrecéis?", {I, S}, None, "directa"),
    ("¿Quién se encarga de la internacionalización?", {I, C}, None, "directa"),
    ("¿Qué relación tenéis con Tknika?", {C}, "Tknika", "directa"),
    ("¿Qué es EFVET?", {C}, "EFVET", "directa"),
    ("¿Formáis parte de redes europeas?", {C}, "Redes", "directa"),
    ("¿Qué diferencia hay entre Erasmus y Capacity Building?", {G, P}, "Capacity", "directa"),
    ("¿Qué es un CoVE?", {G, P}, "CoVE", "directa"),
    ("¿Ofrecéis formación para profesores extranjeros?", {I, F}, None, "directa"),
    ("¿Puedo hacer job shadowing en vuestro centro?", {I, F}, None, "directa"),
    ("Somos una empresa, ¿cómo podemos colaborar?", {C, F}, None, "directa"),
    ("Somos un centro de FP de Marruecos, ¿podríamos trabajar juntos?", {C, I, F, P}, None, "directa"),
    ("¿Cómo ayudáis a los alumnos a mejorar su empleabilidad?", {I, S, O, G}, None, "directa"),
    ("¿Qué competencias desarrollan los alumnos durante una movilidad?", {G, I}, None, "directa"),
    ("¿Qué significa internacionalizar el currículo?", {G, I}, "curr", "directa"),
    # otras preguntas directas
    ("¿Qué es el SEPIE?", {C}, "SEPIE", "directa"),
    ("¿Sois miembros de AICE-IZEA?", {C}, "AICE", "directa"),
    ("¿Qué es la CECE?", {C}, "CECE", "directa"),
    ("¿Colaboráis con Bilbao Metropoli 30?", {C}, "Metropoli", "directa"),
    ("¿Qué es el INJUVE?", {C}, "INJUVE", "directa"),
    ("¿Qué es YES Forum?", {C}, "YES Forum", "directa"),
    ("¿Cuál es vuestra visión internacional?", {I}, "Visión", "directa"),
    ("¿Qué objetivos tiene vuestra internacionalización?", {I}, "Visión", "directa"),
    ("¿Quiénes son los tutores Erasmus?", {I}, "Equipo", "directa"),
    ("¿Tenéis algún proyecto CoVE?", {P, G}, None, "directa"),
    ("¿Participáis en algún proyecto Capacity Building?", {P}, "Capacity", "directa"),
    # varias redes a la vez
    ("¿Qué diferencia hay entre el SEPIE y Tknika?", {C}, None, "varias"),
    ("¿Estáis en EFVET y en la CECE?", {C}, None, "varias"),
    ("¿Con qué redes vascas y europeas trabajáis?", {C}, "Redes", "varias"),
    # transcripciones imperfectas (como las escribiria Whisper)
    ("¿Qué relación tenéis con Teknika?", {C}, "Tknika", "transcripcion"),
    ("¿Qué es EFE VET?", {C}, "EFVET", "transcripcion"),
    ("¿Sois socios de Aise Isea?", {C}, "AICE", "transcripcion"),
    ("¿Qué es el Sepi?", {C}, "SEPIE", "transcripcion"),
    ("¿Trabajáis con el Injube?", {C}, "INJUVE", "transcripcion"),
    ("¿Qué es un COBE?", {G, P}, "CoVE", "transcripcion"),
    ("¿Qué es capacity bilding?", {G, P}, "Capacity", "transcripcion"),
    ("¿Colaboráis con Bilbao Metrópoli treinta?", {C}, "Metropoli", "transcripcion"),
]

# Equipo del centro (25-11-2026): (pregunta, {modulos}, titulo de seccion esperado, tipo)
Q_EQUIPO_MOD = "16_equipo_del_centro.md"
Q_EQUIPO = [(q, {Q_EQUIPO_MOD} | extra, sec, kind) for q, extra, sec, kind in [
    ("¿Quién es Maribel?", set(), "Maribel", "nombre"),
    ("¿Quién es la directora del colegio?", set(), "Maribel", "cargo"),
    ("¿Quién dirige el centro?", set(), "Maribel|Quién es quién", "cargo"),
    ("¿Cómo es Maribel como directora?", set(), "Maribel", "nombre"),
    ("¿Quién es Rafa?", {I, C}, "Rafa", "nombre"),
    ("¿Quién es Rafael Balparda?", {I, C}, "Rafa", "nombre"),
    ("¿Qué tal es Rafa Balparda?", {I, C}, "Rafa", "nombre"),
    ("¿Quién es Raúl Setién?", set(), "Raúl", "nombre"),
    ("¿Quién es Raúl?", set(), "Raúl", "nombre"),
    ("¿Quién es el director de innovación?", set(), "Raúl", "cargo"),
    ("¿Quién se encarga de la innovación en el colegio?", set(), "Raúl", "cargo"),
    ("¿Quién es Jesús?", set(), "Jesús", "nombre"),
    ("¿Quién es el coordinador TIC?", set(), "Jesús", "cargo"),
    ("¿Quién lleva la informática del colegio?", set(), "Jesús", "cargo"),
    ("¿Quiénes forman el equipo del centro?", set(), None, "cargo"),
    # transcripciones imperfectas
    ("¿Quién es Rafa Valparda?", {I, C}, "Rafa", "transcripcion"),
    ("¿Quién es Raul Setien?", set(), "Raúl", "transcripcion"),
    ("¿Quién es Raúl Cetién?", set(), "Raúl", "transcripcion"),
    ("¿Quién es Jesus?", set(), "Jesús", "transcripcion"),
    ("¿Quién es Mari Bel?", set(), "Maribel", "transcripcion"),
    ("¿Quién es el coordinador de las TICs?", set(), "Jesús", "transcripcion"),
]]
