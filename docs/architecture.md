# Arquitectura

## Enfoque y dependencias

Un monolito modular: un proceso con responsabilidades separadas. No se requieren microservicios ni múltiples agentes inicialmente.

- `domain` define mensajes, solicitudes y resultados de herramientas, consumo y contratos. No depende de SDKs, bases de datos ni interfaces.
- `agent` coordina el trabajo usando contratos. No instancia proveedores ni abre archivos directamente.
- `providers`, `tools` y `storage` implementan integraciones concretas.
- `permissions` decide autorizaciones y debe intervenir antes de ejecutar herramientas.
- `memory` selecciona contexto y conserva recuerdos mediante contratos de persistencia.
- `interfaces` traduce entradas y salidas sin contener reglas del agente.
- `bootstrap` ensambla implementaciones y configuración, sin efectos al importar.

## Flujo previsto

Solicitud → contexto → modelo → respuesta o llamada a herramienta → validación de argumentos y permisos → ejecución → resultado al modelo → respuesta final.

Cada tarea tendrá identificador, cancelación y límites de pasos, tiempo y salida. Se incorporará control de presupuesto antes de habilitar autonomía prolongada; limitar tokens por llamada no equivale a limitar gasto total.

## Modelos

Cada proveedor adaptará mensajes, llamadas a herramientas y consumo a una interfaz común. Declarará capacidades verificadas; no se asume que todos admiten las mismas modalidades o protocolos.

La selección será explícita por perfil, inicialmente sin cambio automático de proveedor. Cambiar de modelo conservará los datos persistentes, aunque el contexto de conversación podría requerir conversión o resumen. Los reintentos deberán evitar duplicar acciones.

## Herramientas y permisos

Cada herramienta declarará nombre, descripción, esquema de argumentos, permisos y formato de resultado. Un registro permitirá añadir herramientas sin modificar el ciclo central.

Las restricciones se aplicarán en código. Los archivos serán inicialmente de solo lectura y solo dentro de raíces autorizadas, validando rutas resueltas y enlaces simbólicos. El contenido externo se tratará como datos, sin autoridad para cambiar permisos o instrucciones.

La herramienta web deberá limitar tiempos, tamaños y destinos de red para evitar acceso involuntario a servicios internos. Los errores tendrán resultados explícitos.

## Persistencia y registros

Separar contexto de sesión y memoria persistente. SQLite será el primer adaptador previsto; se añadirán migraciones al definir el esquema. Los recuerdos deberán poder consultarse, corregirse y borrarse.

Registrar resultados, errores, duración y consumo por tarea y modelo. No registrar claves ni contenido de conversaciones por defecto.

## Etapas de implementación

1. Contratos de dominio y configuración validada.
2. Adaptador DeepSeek y conversación por terminal.
3. Ejecutor de herramientas con permisos y lectura de archivos autorizados.
4. Búsqueda y lectura web con fuentes.
5. Persistencia, memoria y evaluación de tareas completas.
6. Otros proveedores, voz e interfaces adicionales.

Todo este documento describe requisitos pendientes de implementación.
