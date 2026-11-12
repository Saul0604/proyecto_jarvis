# Herramientas iniciales

Ejecuta desde la raíz del proyecto con el Python donde instalaste Jarvis.

## Archivos

Autoriza una carpeta explícitamente:

```powershell
python -m jarvis.interfaces.cli.app --profile sonnet --files-root "C:\ruta\carpeta-de-prueba" "Lista los archivos y resume notas.txt"
```

Puedes cambiar sonnet por nova. Las herramientas list_files, search_files y read_file consultan únicamente la raíz autorizada. Las rutas relativas parten de esa raíz.

read_file admite .txt, .md, .csv y .json UTF-8 de hasta 2 MB. offset y limit se miden en caracteres. next_offset permite continuar una lectura. search_files busca por nombre y examina hasta 10,000 entradas. Los resultados informan truncamiento.

## Web

```powershell
python -m jarvis.interfaces.cli.app --profile sonnet --web "Lee https://example.com y resume su contenido"
```

search_web usa Brave Search API y requiere BRAVE_SEARCH_API_KEY en el entorno. La clave de Bedrock se usa para consultar el modelo. fetch_web_page funciona con URLs públicas sin clave adicional. .env.example es una plantilla y no se carga automáticamente.

fetch_web_page admite HTML y texto plano. Verifica IPs públicas, conecta a una dirección validada y valida también las redirecciones. Verifica TLS, limita la descarga a 1 MB y devuelve hasta 12,000 caracteres. No ejecuta JavaScript.

## Componentes y límites

domain/tools.py define contratos; tools/registry.py declara y habilita herramientas; tools/executor.py valida argumentos y devuelve datos o errores estructurados. agent/runner.py coordina hasta diez consultas al modelo, cinco llamadas por turno y 120 segundos de espera por tarea.

Los permisos se indican mediante --files-root y --web. La comprobación de rutas y enlaces no proporciona aislamiento frente a otros procesos que modifiquen enlaces concurrentemente. Autoriza carpetas de documentos de prueba.

La red y disco se ejecutan en threads. Cancelar la espera puede dejar una operación iniciada terminando en segundo plano, cuyos resultados se descartan. Las páginas dinámicas o autenticadas pueden no proporcionar contenido útil.

## Pruebas

```powershell
python -m unittest discover -s tests/unit -v
```

Las pruebas usan archivos temporales y respuestas simuladas. Las llamadas reales dependen de tus credenciales y conectividad.
