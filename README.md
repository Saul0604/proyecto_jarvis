# Jarvis

Asistente de IA en Python, organizado como monolito modular.

## Primera versión prevista

- Conversación en español con contexto de sesión.
- Búsqueda y lectura web con fuentes.
- Consulta de archivos dentro de una carpeta autorizada, de solo lectura.

Modelo inicial: DeepSeek V4.1 Flash mediante API (`deepseek-flash`), con proveedores intercambiables.

## Estructura

```text
config/                  Perfiles de modelos y ajustes de ejemplo
src/jarvis/
  bootstrap.py           Composición de componentes
  config/                Carga y validación de configuración
  domain/                Tipos y contratos compartidos
  agent/                 Ciclo del agente y contexto de tarea
  providers/deepseek/    Adaptador del proveedor inicial
  tools/web/             Búsqueda y lectura web
  tools/files/           Acceso restringido a archivos
  permissions/           Autorización de acciones
  memory/                Contexto y memoria persistente
  observability/         Eventos, errores y consumo
  interfaces/cli/        Interfaz inicial de terminal
  interfaces/voice/      Extensión futura de voz
  storage/sqlite/        Persistencia local prevista
docs/                    Arquitectura y decisiones
tests/unit/              Pruebas aisladas futuras
tests/integration/       Pruebas de integración futuras
var/                     Datos locales, excluidos de Git
```

## Estado

Esta entrega es el esqueleto del proyecto. Los paquetes contienen descripciones de su responsabilidad, sin implementaciones simuladas. Todavía no existe una interfaz ejecutable ni se realizan llamadas API, búsquedas o lecturas de archivos.

`config/models.json` declara el perfil inicial. `config/settings.example.json` propone ajustes que el futuro cargador deberá validar. La lista de carpetas autorizadas está vacía hasta elegir explícitamente una. `.env.example` es una plantilla; todavía no se carga automáticamente.

Las claves se obtendrán de variables de entorno. No deben guardarse en configuración ni en el repositorio.

El siguiente paso será definir los contratos e implementar una conversación por terminal con el adaptador DeepSeek. Consulta [la arquitectura](docs/architecture.md).
