# Pruebas del asistente

Todas se ejecutan desde la carpeta del proyecto con el Python de `Tools/tts/.venv`
(`$env:PYTHONIOENCODING="utf-8"` en PowerShell para ver bien los acentos).

| Prueba | Comando | Qué mide |
|---|---|---|
| Recuperación (preguntas sueltas) | `Tools\tts\.venv\Scripts\python.exe Tests\retrieval\run_retrieval.py e5` (o `fallback`) | Si el fragmento de conocimiento correcto llega a la IA. 105 preguntas + 10 formas de preguntar por internet. |
| International Campus | `Tools\tts\.venv\Scripts\python.exe Tests\retrieval\run_campus.py e5 campus` (o `fallback`; `equipo` para el banco del equipo) | 37 preguntas sobre International Campus (y 21 sobre el equipo del centro), redes y conceptos (directas, varias redes, transcripciones imperfectas): módulo y **sección** correctos. |
etrieval
un_campus.py e5` (o `fallback`) | 37 preguntas sobre International Campus, redes y conceptos (directas, varias redes, transcripciones imperfectas): módulo y **sección** correctos. |
| Recuperación con contexto | `Tools\tts\.venv\Scripts\python.exe Tests\retrieval\run_context.py [margen ...]` | 30 conversaciones: seguimientos cortos, referencias indirectas largas, referencias a lo que dijo el asistente y cambios de tema. Con varios márgenes compara valores de `CONTEXT_MARGIN` (99 = sin contexto). |
| Conversación completa con la IA | `Tools\tts\.venv\Scripts\python.exe Tests\e2e_conversations.py [general\|internet\|contexto\|campus\|equipo\|presentaciones\|todo]` | Respuestas reales de qwen3:4b-instruct (necesita Ollama; sin voz ni Unreal). Guarda el texto en `Tests/results/`. |

- `retrieval/questions.py`: banco de preguntas y módulos aceptables.
- `retrieval/context_cases.py`: conversaciones con contexto.
- `results/`: resultados guardados (fecha en el nombre).
- "entregado" = el módulo correcto está entre los fragmentos que recibe la IA; "top1" = es el primero.

## Resultados 2026-11-25

- Recuperación E5: 96/105 (91,4 %), top1 80 %. Antes de estos cambios: 97/105 (92,4 %). La diferencia es
  "¿Hacéis excursiones?": el módulo 09 ya era el 5.º en puntuación y la nueva sección de conexión del módulo 14 lo deja fuera.
- Variantes de internet: 10/10 con E5 (8/10 con el buscador de respaldo por palabras).
- Buscador de respaldo (sin E5): 96/105 (antes 95/105).
- Contexto (margen 1.0): 29/30 entregados, top1 26/30; sin contexto 28/30, top1 25/30. Los 9 cambios de tema
  siguen con el tema nuevo en primer lugar. El único fallo ("la plataforma con las familias") también falla sin contexto.
- Conversación completa: `results/e2e_*_2026-11-25.txt` (`e2e_internet_2026-11-25_v1.txt` = antes de aclarar "completamente").

## Resultados 2026-11-25 (actualización International Campus)

Archivos: `results/retrieval_final_2026-11-25.txt`, `results/context_final_2026-11-25.txt`, `results/e2e_*_2026-11-25.txt`
(`e2e_campus_2026-11-25_v1.txt` = antes de corregir la redacción sobre Capacity Building/CoVE).

| Banco | E5 | Respaldo por palabras |
|---|---|---|
| 105 preguntas | 102/105 (97,1 %), top1 83,8 % | 99/105 (94,3 %) |
| Variantes de internet | 10/10 | 9/10 |
| International Campus (sección correcta) | 37/37 | 33/37 |
| Contexto (35 conversaciones, margen 1.0) | 34/35 | — |

Cambios de recuperación que explican la mejora: módulo 06 dividido en secciones, palabras reales del fragmento en el
buscador de respaldo, 2.º fragmento del mismo módulo también en el respaldo (>= 95 % de la puntuación) y, si un fragmento
no cabe en el límite de 4200 caracteres, se prueba el siguiente en vez de parar.

## Resultados 2026-11-25 (equipo del centro)

- Banco del equipo (21 preguntas: nombre, cargo, transcripciones imperfectas): E5 21/21 con la sección de la persona;
  respaldo por palabras 21/21 en módulo y 17/21 en sección (a veces gana el resumen "quién es quién").
- Sin regresiones: 105 preguntas 97,1 % (E5) / 94,3 % (respaldo), International Campus 37/37, contexto 34/35.
- Conversaciones: `results/e2e_equipo_2026-11-25.txt` (visitantes que preguntan por el equipo; `_v1` = antes de reescribir
  el módulo 16) y `results/e2e_presentaciones_2026-11-25.txt` (la propia persona se presenta, con perfil y sesión reales).
