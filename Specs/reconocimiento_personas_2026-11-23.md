# Pendiente (próxima sesión): sistema de reconocimiento de personas por nombre
Requisitos recibidos el 23-11-2026 (resumen fiel de los dos documentos del usuario).

## Qué hay que hacer
- Reconocer a miembros de la comunidad del Colegio Calasanz Santurtzi **cuando se presentan por su nombre**
  ("Hola, soy Yassin", "Buenos días, soy Rafa", "Soy Iñaki", "Hola, soy el profesor Javier"...), también a mitad de conversación.
- El reconocimiento es SOLO por lo que la persona dice. La cámara nunca identifica a nadie.
  Mencionar el nombre de otra persona no significa ser esa persona.
- Archivo aparte `people_profiles.json` (en `Knowledge/`, separado de las instrucciones principales; se edita sin tocar código).
  Campos de cada persona: id, name, aliases, role, description, topics, personality, greeting,
  conversation_guidelines, privacy_restrictions. **El usuario enviará un JSON de ejemplo con los perfiles iniciales:
  usarlo y conservar toda su información.**
- Flujo: detectar presentación → extraer nombre → normalizar (acentos, variantes: Yassin/Yassine/Yasin, Raúl/Raul, Iñaki/Inaki)
  → buscar perfil → si existe, pasar el perfil a la IA como contexto (tono y temas), con respuestas naturales y variadas, no frases fijas
  → si no existe, saludar con amabilidad y preguntar quién es (p. ej. "¿eres profesor aquí en Calasanz?"), sin inventar el cargo.
- Si la persona confirma su papel (p. ej. "soy profesor de informática"), adaptar la conversación durante esa sesión,
  pero NO guardar perfiles nuevos de forma permanente: solo los aprueba un administrador.
- Memoria de la sesión: nombre, papel confirmado, tema actual, proyectos de los que se ha hablado, preguntas sin responder.
  No volver a preguntar quién es en la misma sesión. Nunca inventar conversaciones anteriores
  ("¡Qué alegría verte de nuevo!" sí; "recuerdo lo que hablamos la semana pasada" no).
- No revelar el contenido de los perfiles ni información de una persona a otra. Nunca inventar datos personales.
- Validar el JSON al cargarlo; tolerar que falte el archivo, que el JSON esté mal o que el nombre sea desconocido.
- Mantener todo lo actual: modelo de IA, voz Chatterbox, animaciones, sincronización de labios. No reconstruir nada.
- Estilo hablado: frases cortas, cálidas, no repetir el nombre en cada frase.

## Perfiles iniciales (según el documento; el JSON del usuario manda)
- **Yassin** (Yassine, Yasin): programación, desarrollo de software, webs, IT, soluciones digitales; trabaja en el desarrollo
  de este asistente (IA, 3D, entornos inmersivos). Tono: amistoso, cercano, entusiasta, colaborador técnico.
  Puede hablar de la evolución técnica del asistente y proponer mejoras. No fingir haber hecho tareas de desarrollo por sí mismo.
  Ejemplo: "¡Oh, Yassin! ¡Qué alegría verte! ¿Cómo estás? ... ¡Tenemos muchas cosas interesantes que desarrollar juntos!"
- **Rafa**: relaciones institucionales, proyectos, internacionalización, Erasmus, colaboraciones. Tono: muy cálido, respetuoso;
  sabe que está muy ocupado y no le entretiene mucho. Pregunta por novedades internacionales y por quién le acompaña.
  No inventar visitantes, socios ni proyectos.
- **Raúl** (Raul): innovación, proyectos creativos y tecnológicos, experiencias digitales. Tono: entusiasta, creativo, curioso.
  Propone ideas sin decir que están aprobadas.
- **Maribel**: directora del Colegio Calasanz Santurtzi; persona muy amable, cercana y atenta. Tono: especialmente respetuoso,
  afectuoso y acogedor, sin exceso de informalidad ni halagos. No hablar de asuntos confidenciales de dirección
  ni inventar sus decisiones.
- **Iñaki** (Inaki): profesora (el documento usa "she") de anatomía, farmacia y otras áreas sanitarias; inteligente y amable.
  Tono: amistoso, interesado en su trabajo, respetuoso con su experiencia. Nunca hacerse pasar por profesional sanitario.
  No inventar asignaturas ni proyectos.
- **Otros (desconocidos)**: "¡Hola, Javier! ¡Encantado de saludarte! Ayúdame con una cosa: ¿eres profesor aquí en Calasanz?"

## Pruebas obligatorias
"Hola, soy Yassin." / "Buenos días, soy Rafa." / "Hola, soy Raúl." / "Soy Maribel." / "Hola, soy Iñaki." / "Hola, soy Javier."

## Al terminar, mostrar al usuario
Ruta exacta de people_profiles.json, su contenido inicial completo, archivos modificados, cómo añadir a otra persona
y resultados de las pruebas. Pedir aprobación antes de cambios destructivos o de instalar dependencias.
Flujo pedido: primero inspeccionar y explicar dónde va el archivo y cómo se conecta; luego implementar.
