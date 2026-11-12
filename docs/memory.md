# Memoria de conversación

Jarvis guarda por defecto cada mensaje del usuario y la respuesta final en var/jarvis.sqlite3. La base permanece local y no está cifrada. Los turnos recuperados se envían al modelo como contexto y consumen tokens de entrada. El historial puede contener datos de archivos que el asistente haya citado.

## Ejemplos desde la raíz del proyecto

```powershell
python -m jarvis.interfaces.cli.app --profile sonnet --session faro "Faro tiene un presupuesto de 12000 MXN."
python -m jarvis.interfaces.cli.app --profile sonnet --session faro "Gasté 3500. ¿Cuánto queda?"
python -m jarvis.interfaces.cli.app --profile nova --session faro
```

El tercer comando abre una conversación interactiva. /salir la termina. El nombre de sesión selecciona o crea una conversación y permite retomarla incluso con otro modelo.

```powershell
python -m jarvis.interfaces.cli.app --session faro --history
python -m jarvis.interfaces.cli.app --list-sessions
python -m jarvis.interfaces.cli.app --session faro --clear-memory
python -m jarvis.interfaces.cli.app --no-memory "Explica qué es una API."
```

--db permite escoger otro archivo SQLite. Sin --session, se usa principal. Los permisos de herramientas se habilitan en cada ejecución con --files-root y --web.

## Alcance

Antes de enviar una nueva consulta, Jarvis resume cuando hay 20 turnos sin condensar (un turno es tu mensaje y su respuesta) o cuando el historial junto al resumen llega a 45000 caracteres. Conserva los seis turnos más recientes. Si esos turnos superan 24000 caracteres, conserva menos y resume también los necesarios.

El resumen se genera con el modelo seleccionado e integra el resumen previo. Se conservan decisiones, nombres, cifras, preferencias explícitas, correcciones y pendientes. Tiene un máximo aceptado de 8000 caracteres, con un objetivo solicitado de 6000. La generación está limitada a 2048 tokens de salida por fragmento. Los originales se procesan en fragmentos de hasta 16000 caracteres sin omitir contenido.

Una vez completado el resumen, se guarda y se eliminan los turnos condensados en la misma transacción. --history muestra el resumen acumulado y los turnos que siguen disponibles. --clear-memory borra ambos. Los cambios de esquema se aplican automáticamente al abrir una base existente.

Resumir realiza consultas adicionales al modelo y consume tokens. Un resumen puede perder matices o datos textuales exactos. Si falla, se cancela, se corta la salida o cambia la sesión concurrentemente, los turnos originales no se eliminan por esa operación. La consulta puede repetirse.

El resumen se incorpora como contexto histórico de usuario, sin privilegios de instrucciones de sistema. Se guardan mensajes y respuestas finales; las herramientas intermedias solo se usan durante la tarea. Las preferencias todavía pertenecen a cada sesión.

El contexto enviado sigue limitado a 60000 caracteres. SQLite reutiliza el espacio liberado: eliminar turnos no necesariamente reduce inmediatamente el tamaño físico del archivo.

Cada turno exitoso se confirma en una transacción. Una consulta fallida o cancelada no agrega un turno parcial. Si otra ejecución modifica o borra la sesión mientras se genera la respuesta, el guardado detecta el conflicto y pide repetir la consulta.

--clear-memory elimina los turnos lógicos de la sesión y conserva su nombre vacío. No garantiza borrado físico de copias de seguridad, sincronización de OneDrive o páginas recuperables del archivo SQLite.
