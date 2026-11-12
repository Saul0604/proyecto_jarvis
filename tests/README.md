# Pruebas

Se añadirán con la funcionalidad ejecutable.

- `unit/`: configuración, permisos, selección de modelos y lógica sin red.
- `integration/`: colaboración entre componentes y persistencia temporal. Las pruebas API reales serán explícitas, opcionales y usarán claves del entorno.

Casos prioritarios: rechazar rutas no autorizadas, detener ciclos al llegar al límite y manejar errores sin duplicar acciones.
