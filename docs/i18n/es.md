# Clean Your TV — guía de uso

Clean Your TV ofrece una pantalla de inicio personal para tu LG webOS: tus aplicaciones en tu orden, sin filas patrocinadas en este menú. Instálalo desde un ordenador o teléfono Android; después puedes apagar el ordenador.

## 1. Descarga el instalador

Pulsa la imagen de tu dispositivo. Los botones descargan la última versión publicada. En Mac, elige Apple Silicon (M1 o posterior) o Intel; consulta menú Apple → Acerca de este Mac.

[![Descargar — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Descargar — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Descargar — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Descargar — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Descargar — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="elegir-edición"></a>

<a id="requisitos"></a>

## 2. Elegir edición

Enciende el TV y conéctalo a la misma red doméstica que el ordenador o teléfono. Permite a CYTV acceder a la red local cuando lo solicite.

- **No-root** — si no tienes acceso root. Prepara Developer Mode siguiendo los pasos de abajo.
- **Root** — si ya tienes acceso root por SSH. El instalador no obtiene root. No actives Developer Mode en ese TV; conserva el acceso SSH y los datos de recuperación.

### Configurar Developer Mode (No-root)

Developer Mode permite a CYTV instalar apps en un TV sin root.

1. En el TV, abre LG Apps, busca Developer Mode e instálalo.
2. Abre Developer Mode e inicia sesión con tu cuenta LG Developer. Si necesitas una, créala en [LG Developer](https://webostv.developer.lge.com).
3. Activa Dev Mode Status. El TV se reiniciará. Después, abre Developer Mode de nuevo.
4. Activa Key Server y deja Developer Mode abierto. Introduce su IP Address como dirección del TV en CYTV.
5. Introduce la Passphrase: los seis caracteres que muestra Developer Mode en el TV. Respeta mayúsculas y minúsculas.

Usa el código del TV, no la contraseña de tu cuenta LG. Si no aparece el código, activa Key Server.

El emparejamiento es un paso aparte: cuando el TV lo pida, acepta CYTV con el mando.

Mantén Developer Mode activo: antes de que termine el tiempo, ábrelo y pulsa EXTEND con el TV conectado a Internet. Si caduca, LG puede eliminar estas apps.

<a id="instalación-e-idioma"></a>

## 3. Abre el instalador

- **Windows x64:** descarga `cytv-windows-x64-desktop.zip`, elige **Extraer todo** en el Explorador y abre `cytv-desktop/cytv-desktop.exe`. Conserva la carpeta `_internal` a su lado.
- **macOS 13+:** extrae `cytv-macos-arm64.zip` para Apple Silicon o `cytv-macos-x64.zip` para Intel, mueve `cytv.app` a Aplicaciones y ábrela. Permite el acceso a la red local. Si se bloquea una descarga de confianza, usa Privacidad y seguridad → Abrir igualmente; no desactives Gatekeeper.
- **Linux x64:** en Ubuntu 22.04+, Debian 12+ o Mint 21+, instala `cytv-linux-x64.deb` con el gestor gráfico de paquetes y abre Clean Your TV desde el menú de aplicaciones. Las bibliotecas pueden requerir Internet. No hay paquete Linux ARM.

**Android ARM64:** necesitas un teléfono ARM de 64 bits con Android 7+ y WebView/Chrome 108+. Abre el APK descargado y permite la instalación desde esa fuente si Android lo solicita. Abre CYTV; el idioma se elige arriba a la derecha. Actualiza sin desinstalar ni borrar datos.

El asistente de escritorio usa inicialmente el idioma del sistema y guarda una selección explícita. En el televisor, abre **Ajustes → Idioma** y elige un idioma o la opción automática del sistema. Las preferencias del instalador y del televisor son independientes. Consulta los códigos en el [índice de idiomas](../LANGUAGES.md).

## 4. Instala en el televisor

1. En CYTV, elige **Configurar mi TV**. En el ordenador, selecciona un TV detectado; en Android, introduce su dirección IP. Si la búsqueda no lo encuentra, escribe la dirección manualmente.
2. Elige **No-root** o **Root** y comprueba el televisor seleccionado antes de continuar.
3. No-root: introduce el código de Developer Mode y acepta la solicitud en el TV. Root: usa tus credenciales SSH. Acepta una nueva identidad SSH solo para tu propio TV en una red de confianza. Si cambia una clave guardada, detente e investiga.
4. Sigue el asistente. Mantén el TV encendido, la misma red y CYTV abierto hasta que termine. No fuerces el cierre de la app Android. Root activa el control de Home justo después de preparar la recuperación.

## 5. Comprueba el mando

1. Abre otra app del TV y pulsa brevemente **Home**. Debe abrirse Clean Your TV. Indica al asistente lo que viste; omite la prueba si no la hiciste.
2. Comprueba flechas, OK, Atrás, volumen y sonido. Prueba por separado la suspensión/reactivación y el arranque tras desconectar la alimentación. Una instalación correcta no verifica por sí sola estas acciones.

<a id="uso-y-recuperación"></a>

## 6. Uso y recuperación

Las flechas seleccionan y OK abre; mantén OK para reordenar. Una pulsación breve de Atrás conserva la navegación y confirmación de salida de cada aplicación. Home abre el lanzador mientras el control está activo. Mantén Atrás durante 1,2 segundos para abrir LG Home una vez. El interruptor de control de Home y tus ajustes no cambian.

**Pulsa Home tres veces en dos segundos**, soltando entre pulsaciones. Se recupera LG Home y se detiene el control sin borrar preferencias.

No-root: Para reiniciar el control de Home, abre Home Helper, elige Iniciar Helper y confirma. Se conserva tu pantalla Home elegida. Root: activa **Cambiar Home** en los ajustes de Home para reanudar. **Abrir LG Home** lo abre una vez sin cambiar el destino de Home. Para recuperar LG Home como destino permanente, desactiva **Cambiar Home**. No ejecutes ambos controladores a la vez. Si el fallo se repite, deja LG Home activo.

## ¿Necesitas ayuda?

Si se interrumpe la instalación, usa la misma conexión guardada y comienza por **Comprobar estado del TV**. Continúa solo mediante la recuperación que ofrezca el asistente. Si el estado es desconocido, guarda el informe de diagnóstico y detente; conserva los datos de recuperación y no repitas la instalación a ciegas.

Durante la recuperación, mantén desactivado el control de Home y conserva los informes originales y la conexión guardada. Confirma la inspección y los cambios por separado. Sigue la guía detallada correspondiente a tu versión instalada; no fuerces la reinstalación ni borres el estado de recuperación.

Indica modelo, firmware, No-root o Root, dispositivo de instalación, paso y mensaje de error. Elimina contraseñas, claves, direcciones y datos personales antes de compartir el informe. No se publica automáticamente.

[Informar de un problema](../FEEDBACK.md) · [Recuperación — inglés](../RECOVERY.md) · [Actualizar o eliminar — inglés](../MAINTENANCE.md) · [Otros idiomas](../LANGUAGES.md)

En las próximas compilaciones, el aviso y el botón «Desactivar vista previa HDMI» solo aparecen con 4K seleccionado o activo en temas con la vista previa de entradas activada. Durante la vista previa HDMI, el fondo de vídeo 4K se sustituye temporalmente por una imagen estática de 1080p. Desactiva la vista previa de entradas para mantener el fondo en 4K.

### Candidato: eliminación sencilla

Los botones anteriores siguen ofreciendo la versión publicada. En el próximo candidato, elige **Desinstalar Clean Your TV** en Mantenimiento con la misma conexión guardada. Confirma una vez. Se eliminan las apps y archivos conocidos del proyecto que estén presentes y se omiten los ausentes, incluso después de una instalación parcial.

Cuando se indique, desconecta la alimentación del TV, vuelve a conectarla, espera la red y elige **Intentar de nuevo**. Espera o Quick Start no es un reinicio completo; CYTV no reinicia el TV automáticamente. Si se pierde la conexión, compruébala y reintenta la misma eliminación sin otro asistente de recuperación. Si se deniega el acceso, usa la conexión Root solicitada; si el TV está ocupado, espera y reintenta. Solo se muestra éxito tras verificar la limpieza final. Conserva las claves y los informes originales. Siguen vigentes los controles de emergencia y el consentimiento para compartir.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="python-opcional-para-root-en-v110"></a>
<a id="bloqueo-de-firmware-lg-en-120"></a>
<a id="novedades-de-130-recuperación-guiada-de-escritorio"></a>
<a id="novedades-de-130--12"></a>
<a id="candidato-sin-publicar-instalar-root-mediante-homebrew"></a>
<a id="candidato-sin-publicar-recuperación-de-sonido-hdmi-root"></a>
<a id="temas-154"></a>
<a id="categorías-de-ajustes-candidato-no-publicado"></a>
<a id="resolución-gráfica-automática-candidato"></a>
<a id="actualizaciones-y-eliminación"></a>
<a id="ayuda-y-más-instrucciones"></a>
<a id="temas"></a>
<a id="categorías-de-ajustes-154"></a>
<a id="resolución-gráfica-automática-160"></a>
<a id="espacio-de-almacenamiento"></a>

Referencias detalladas en inglés: [requisitos](../COMPATIBILITY.md) · [controles](../CONTROLS.md) · [temas](../THEMES.md) · [actualizaciones](../UPDATES.md).

> Candidato no publicado: Root Home experimental se elige por capacidades de Qt SDK 6–9, sin lista de modelos. La compatibilidad física y OTA normal no están verificadas. No se modifican otras integraciones Home; tras una parada de seguridad o energía, activa Home explícitamente. [#364](../development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).
