# Jarvis

Asistente modular en Python 3.11+ con conversación en español, herramientas de lectura y memoria local persistente. El proveedor implementado es **Amazon Bedrock Converse**; los perfiles se encuentran en `config/models.json`.

## Ejecutar

Desde la carpeta del proyecto, con tu entorno virtual activo:

```bash
python -m pip install -e .
python -m jarvis.interfaces.cli.app --settings config/settings.example.json --activity
```

Configura las credenciales AWS mediante los mecanismos habituales de boto3 y selecciona un perfil con `--profile`. Jarvis carga el archivo `.env` de la carpeta desde la que se ejecuta. Las variables ya definidas en la terminal tienen prioridad. Búsqueda web requiere `BRAVE_SEARCH_API_KEY` en el entorno.

```bash
python -m jarvis.interfaces.cli.app --files-root . "Revisa la estructura del proyecto"
python -m jarvis.interfaces.cli.app --web "Investiga este tema y cita fuentes"
python -m jarvis.interfaces.cli.app --session taller
python -m jarvis.interfaces.cli.app --session taller --history
python -m jarvis.interfaces.cli.app --session taller --usage
python -m jarvis.interfaces.cli.app --session taller --clear-memory
python -m jarvis.interfaces.cli.app --no-memory "Hola"
```

`--files-root` autoriza lectura de una carpeta. `--web` habilita herramientas web. Sin estas opciones no se habilitan. `--db` elige el archivo SQLite; el predeterminado es `var/jarvis.sqlite3`. `/salir` termina la conversación.

## Funcionalidad actual

- Personalidad serena, cortés, concisa y honesta; prompt personalizable con `agent.system_prompt`.
- Herramientas de búsqueda de archivos, listado, lectura de texto/código y búsqueda/lectura web pública.
- Validación JSON Schema de argumentos, incluidos objetos, listas y booleanos; rechazo de esquemas inválidos al registrarlos. No se admiten referencias externas.
- Errores diferenciados de configuración, argumentos, permisos, tamaño, red y fallos internos.
- Hasta `max_steps` rondas de herramientas y una llamada adicional de cierre. Si el modelo insiste en actuar, se informa una tarea incompleta y no se ejecutan esas nuevas acciones.
- Memoria por sesión, resumen acumulativo y recuperación con contexto reciente si el resumen falla. Los originales se conservan cuando falla la compactación.
- Registro SQLite de todas las llamadas al modelo, fase, duración, consumo informado y eventos de herramientas. No registra argumentos ni resultados en la telemetría; el historial conversacional sí guarda mensajes.
- `--activity` muestra avisos de actividad. No es streaming de tokens.

## Configuración y límites

`--settings` carga un JSON con el objeto `agent`; las opciones desconocidas o inválidas se rechazan. Sin el argumento se usan valores predeterminados. La plantilla ahora es ejecutable; los permisos se conceden explícitamente mediante los argumentos de terminal.

El presupuesto `max_request_characters` mide la representación JSON completa de la solicitud del dominio, incluyendo herramientas y salida solicitada. **No equivale al límite de tokens del proveedor.** Se descarta historial antiguo por turnos y se recortan resultados individuales conservando JSON válido y una marca de truncado. Si la tarea activa excede el presupuesto, se detiene con un error explicable antes de enviar otra solicitud.

`--usage` presenta cada llamada; los tokens desconocidos permanecen como `None`, no como cero. No estima todavía precios. `--no-memory` tampoco persiste telemetría. `--clear-memory` elimina historial, resumen y telemetría de esa sesión; una operación que siga activa puede registrar eventos posteriores.

La cancelación de una espera asíncrona no termina una operación de red o herramienta que ya se ejecuta en un hilo. Los límites de rutas tampoco son un aislamiento del sistema operativo. Las herramientas actuales son de lectura; la escritura y el control físico necesitan mecanismos adicionales.

## Comprobación

```bash
python -m unittest discover -s tests/unit -v
```

Las pruebas usan proveedores y respuestas HTTP simulados; no consumen llamadas reales a AWS. Si se ejecutan sin instalar el paquete en Linux/WSL, anteponer `PYTHONPATH=src`.

## Hacia el asistente propuesto

Consulta `docs/roadmap.md` para el alcance implementado y las etapas pendientes. Este proyecto aún no incorpora visión, trabajos simultáneos, control de dispositivos, robótica ni simulaciones físicas.

## Voz de Microsoft en español

Ejecuta Jarvis con Python nativo de Windows. Instala Spanish (Mexico), incluida la función Text-to-speech, en Settings → Time & language → Language & region → Language options.

```powershell
python -m jarvis.interfaces.cli.app --speak --no-memory "Salúdame como Jarvis."
```

Jarvis elige una voz de español de México disponible en el motor de escritorio, o una de otro país de habla española. Si no encuentra ninguna, muestra un aviso para instalarla. Para seleccionar una voz concreta, configura `JARVIS_WINDOWS_VOICE` con su nombre exacto en `.env`.

Lista las voces compatibles desde Windows PowerShell:

```powershell
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo } | Select-Object Name, Culture
$synth.Dispose()
```

Las voces que aparecen en Narrador pueden diferir de las disponibles en este motor. La síntesis es local y gratuita. La generación de respuestas conserva el proveedor de modelos configurado.
