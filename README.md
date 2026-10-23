# VigiMarket
Marketplace responsive para el sector de seguridad privada en Perú. Frontend sin compilación y backend Python 3.12 con SQLite; no requiere paquetes externos.

## Ejecutar
```sh
cd /workspace/Proyecto-clc
python server.py
```
Puerto predeterminado: 3000; se puede cambiar con `PORT`. SQLite se crea en `data/vigimarket.db` (ignorado por Git). Conserva este archivo para mantener cuentas y anuncios. Las contraseñas usan scrypt, y las sesiones de 30 días se guardan en el servidor con cookies HttpOnly y SameSite=Lax. No se almacenan contraseñas en el navegador.

En producción, colocar detrás de HTTPS y establecer `COOKIE_SECURE=1`. Antes de abrir un servicio público, añadir límites de solicitudes/intentos de acceso, copias de seguridad, recuperación de contraseña por correo y políticas de privacidad y moderación. El servidor integrado está destinado al desarrollo y a la validación funcional.

Las publicaciones ilustrativas están identificadas; no admiten contacto. Las publicaciones reales se guardan en SQLite, con imágenes de hasta 1 MB y WhatsApp opcional. Las fotografías ilustrativas usan Unsplash y las fuentes Google Fonts; el contenido y las fuentes de sistema siguen disponibles si estos servicios no responden. No hay pagos, valoraciones ni verificaciones inventadas. El canal de soporte no está configurado.

## Verificación
```sh
python -m unittest discover -s tests -v
```
Las pruebas arrancan un servidor y una base de datos temporales, comprueban autenticación, cookies, publicación, persistencia y rechazo de operaciones no autorizadas.

## Continuar modificando el proyecto

Repositorio: `perseo1346-rgb/Proyecto-clc`. Diseño y contenido: `static/index.html` y `static/style.css`; interacciones: `static/app.js`; cuentas y publicaciones: `server.py`. Las cuentas y anuncios requieren un servidor Python con almacenamiento persistente; GitHub Pages no ejecuta este backend.

Para alojarlo, inicia `python server.py` desde la raíz del proyecto, configura `PORT` según el proveedor y `DATA_DIR` con la ruta de un disco persistente. Activa HTTPS y `COOKIE_SECURE=1`. El repositorio conserva el código; la base de datos requiere respaldos independientes.
