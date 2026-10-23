# VigiMarket

Marketplace responsive de seguridad privada en Perú: búsqueda y filtros, categorías, detalles, registro, sesiones, publicaciones con imagen, perfil y WhatsApp opcional. Las seis publicaciones ilustrativas están identificadas y no tienen contactos ficticios.

## Ejecutar

Requiere Python 3.12 o posterior. No necesita instalar paquetes ni compilar el frontend.

```sh
python server.py
```

El puerto predeterminado es 3000. Configuración opcional:

| Variable | Uso |
| --- | --- |
| `PORT` | Puerto asignado por el alojamiento. |
| `DATA_DIR` | Directorio persistente de SQLite; predeterminado `data/`. |
| `COOKIE_SECURE` | Usar `1` cuando el servicio se publique con HTTPS. |

La base `vigimarket.db` conserva usuarios, sesiones y publicaciones. No forma parte de Git. Las contraseñas usan scrypt; las cookies de sesión son HttpOnly y SameSite=Lax. No se guardan contraseñas en el navegador. Las sesiones duran 30 días. El servidor limita intentos de acceso, valida el origen y los cuerpos JSON y admite imágenes JPG, PNG y WebP de hasta 1 MiB. Los límites de intentos son locales a cada proceso.

## Pruebas

```sh
python -m unittest discover -s tests -v
node --check static/app.js
```

Las pruebas usan bases temporales y verifican autenticación, publicaciones, persistencia tras reinicio, almacenamiento configurable y rechazo de solicitudes inválidas. Se comprobó también el flujo completo en Chromium: registro → publicación → perfil tras recarga → contacto → cierre de sesión, búsqueda y ausencia de desbordamiento a 360, 390, 768 y 1440 píxeles.

## Publicación

`render.yaml` prepara un servicio Python con HTTPS de Render y un disco persistente de 1 GB. El plan Starter y el disco tienen coste; Render muestra el precio antes de confirmar. Importa `perseo1346-rgb/Proyecto-clc` como Blueprint desde tu cuenta de Render. El archivo no crea por sí solo un servicio. Los cambios en `main` pueden desplegarse automáticamente tras vincular el repositorio.

Este servicio conserva el frontend y la API en el mismo dominio. Un alojamiento estático como GitHub Pages no ejecuta cuentas ni publicaciones. La URL pública solo existe cuando el alojamiento confirma un despliegue correcto. Aún no se ha confirmado un despliegue público.

Para automatizar el despliegue desde el entorno de Codex, hace falta una credencial `RENDER_API_KEY` vinculada de forma segura a `api.render.com` y acceso de red a esa API. No pegues credenciales en archivos, commits ni en el chat. El borrador del entorno ya declara el requisito. Guardar un borrador no publica la aplicación.

## Respaldo de información

```sh
python scripts/backup_database.py
# O indica otro directorio de destino:
python scripts/backup_database.py --destination /ruta/de/respaldos
```

El comando usa la API de respaldo de SQLite y verifica la integridad del resultado. El destino predeterminado es `DATA_DIR/backups`; conserva también copias fuera del servidor. Para restaurar, detén el servicio, conserva la base actual y copia el respaldo verificado como `DATA_DIR/vigimarket.db` antes de reiniciar. Nunca publiques estas bases: contienen datos privados.

## Continuar modificando

- Diseño y contenido: `static/index.html`, `static/style.css`.
- Interacciones: `static/app.js`.
- API, cuentas y publicaciones: `server.py`.
- Despliegue: `render.yaml`.
- Instrucciones para futuras tareas: `AGENTS.md`.

El código se mantiene en `perseo1346-rgb/Proyecto-clc`, rama `main`. La base de datos necesita respaldo independiente. No hay pagos ni mensajería interna, y no se simulan verificaciones oficiales. No se ha integrado un proveedor de correo para recuperación de contraseña ni se ha proporcionado un canal comercial de soporte.

## Recursos visuales

Las imágenes ilustrativas de `static/assets/marketplace-examples.png` se generaron para el proyecto y se sirven localmente. No representan proveedores reales. Las fuentes Inter y Poppins se alojan en `static/fonts`, con sus licencias SIL OFL incluidas; sus paquetes Fontsource 5.3.0 se verificaron contra la integridad SHA-512 publicada por npm. El diseño principal funciona sin cargar fuentes ni imágenes externas.

## Vista previa pública

GitHub Pages sirve una vista previa navegable del diseño en https://perseo1346-rgb.github.io/Proyecto-clc/. La rama `gh-pages` contiene únicamente archivos estáticos. Esta vista está identificada explícitamente: permite explorar y filtrar ejemplos, pero no solicita contraseñas ni simula registros o publicaciones. La aplicación completa y su API siguen en `main`; requieren el alojamiento Python descrito arriba.

Para actualizar la vista previa después de modificar y guardar el código en Git:

```sh
python scripts/publish_preview.py
```

El script genera una copia en un directorio temporal y actualiza `gh-pages`, sin cambiar el checkout de trabajo ni incluir la base de datos. GitHub Pages despliega automáticamente esa rama. Comprueba el resultado del workflow `pages build and deployment` antes de confirmar que los cambios son públicos.
