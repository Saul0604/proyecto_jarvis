# Pruebas

Ejecutar con el paquete instalado y sus dependencias:

```bash
python -m unittest discover -s tests/unit -v
```

En Linux/WSL sin instalación editable: `PYTHONPATH=src python3 -m unittest discover -s tests/unit -v`.

La suite cubre contratos del dominio, permisos, herramientas, recuperación de memoria, migración SQLite, esquemas, errores, presupuesto de contexto, cierre de tareas, persistencia del consumo y cancelación de esperas con un hilo real. Usa respuestas de modelos/HTTP simuladas y bases temporales; no consulta AWS ni Brave. Aún faltan pruebas específicas del adaptador Bedrock y más casos HTTP.

La prueba de cancelación verifica explícitamente que cancelar la espera **no detiene** el hilo; lo libera al terminar. Ejecutar en un entorno que permita threads. No reemplazar globalmente `asyncio.to_thread` si se quiere verificar esa propiedad.
