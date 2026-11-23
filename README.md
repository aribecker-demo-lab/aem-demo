# AEM Author en Render

Prueba de arranque con la imagen de terceros `aemdesign/aem:sdk-2026.2.24464` del AEM Cloud SDK.

## Desplegar

1. En el [Dashboard de Render](https://dashboard.render.com/), elegí **New → Blueprint** y conectá este repositorio en la rama `main`.
2. Revisá el servicio web `aem-demo-author` y su plan pago `2c-4g` (2 CPU y 4 GB de RAM).
3. Al aplicar el Blueprint, Render descargará la imagen. Revisá los logs y abrí la URL del servicio cuando esté disponible. El chequeo HTTP consulta `/` en el puerto interno 8080.

El servicio tiene una URL pública y usa almacenamiento efímero. Los cambios en el repositorio de contenido pueden perderse al reiniciar o redesplegar. Si aparece una pantalla de registro o activación, eso confirma que el proceso responde por HTTP. El acceso a Author depende de lo que requiera la imagen al arrancar.

[Documentación de la imagen](https://hub.docker.com/r/aemdesign/aem) · [Blueprints de Render](https://render.com/docs/infrastructure-as-code)
