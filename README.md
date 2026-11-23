# AEM Author y WKND en Render

Demo con AEM Cloud SDK `2026.2.24464` y WKND Sites `4.0.4`. El Dockerfile descarga el paquete oficial de Adobe, verifica su SHA-256 y lo deja en `crx-quickstart/install` para que Author lo instale al arrancar. El paquete incluye el contenido de muestra.

## Desplegar

- En el servicio existente `aem-demo-author`, usá **Manual Deploy → Deploy latest commit** para reconstruir desde `main`.
- Para una instancia nueva, importá el repositorio como **Blueprint** en Render. Cambiá el nombre del servicio si ya existe uno con ese nombre. El Blueprint usa un plan pago de 2 CPU y 4 GB de RAM.
- Cuando finalice la instalación de paquetes, iniciá sesión en Author y abrí `/content/wknd/us/en.html` o buscá **WKND Site** en **Sites**. El primer arranque puede tardar varios minutos.

El servicio tiene URL pública y almacenamiento efímero. Los cambios hechos en Author pueden perderse al reiniciar o redesplegar. El paquete WKND se incluye en cada build.

[Release oficial de WKND](https://github.com/adobe/aem-guides-wknd/releases/tag/aem-guides-wknd-4.0.4) · [Blueprints de Render](https://render.com/docs/infrastructure-as-code)
