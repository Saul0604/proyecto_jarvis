# Evolución de Jarvis

## Base implementada

La ejecución reserva un cierre, clasifica errores, valida esquemas y argumentos, limita el contexto completo y registra llamadas/actividad. La memoria puede recuperarse de fallos de resumen sin borrar los originales. La configuración operativa y la personalidad se cargan antes de consultar al proveedor. Se amplía la lectura a código, manteniendo `.env` fuera de las extensiones admitidas.

## Próximas entregas y criterios de aceptación

1. **Adaptador y red:** ampliar pruebas del protocolo Converse, redirecciones, errores y cancelación con operaciones reales acotadas. Verificar una consulta Bedrock en la cuenta configurada. Añadir precios configurables por modelo, distinguiendo consumo desconocido y caché.
2. **Conversación mientras trabaja:** streaming del proveedor, cola de tareas con identificadores, estados persistentes, interrupción y recuperación tras reiniciar. Poder preguntar por una tarea durante otra sin bloquear la interfaz ni mezclar sesiones.
3. **Memoria estructurada:** preferencias y hechos con procedencia, fecha y mecanismos para corregir/olvidar; recuperación selectiva. “Como la otra vez” debe referenciar una ejecución identificable o pedir aclaración.
4. **Escritura con revisión:** propuestas de cambios con diff y hash del original, aprobación ligada al cambio exacto, escritura atómica y recuperación. Detectar modificaciones concurrentes y rechazar aprobaciones obsoletas.
5. **Voz y visión:** entrada/salida de audio, interrupción al hablar y contrato multimodal. Probar latencia y transcripción en español; incorporar cámaras o imágenes únicamente con fuentes autorizadas.
6. **Integraciones del entorno:** adaptadores explícitos para aplicaciones, hogar y dispositivos, permisos por acción, límites físicos, estado observado y parada de emergencia. Los permisos de seguridad no se sustituyen con una insistencia verbal.
7. **Ingeniería:** herramientas de CAD, cálculo y simulación con unidades, supuestos, validaciones y resultados reproducibles. Robótica requiere hardware, controladores y ensayos propios.

El JARVIS cinematográfico es una referencia de experiencia, no una garantía técnica. Interpretar ironía, comprender situaciones incompletas y proponer acciones útiles requieren evaluaciones con ejemplos de uso reales, además de herramientas y memoria.
