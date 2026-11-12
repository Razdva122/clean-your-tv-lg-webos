# Clean Your TV — guía de uso

Solo Root Edition: configura el nombre de la pantalla de inicio en la última página del instalador. Deja el campo vacío para conservar el nombre actual. En la CLI, usa `--tv-name`.

Antes de una nueva instalación, el instalador del ordenador busca una versión estable más reciente en GitHub. Elige «Abrir GitHub y descargar la última versión» para detenerte y descargarla, o «No, instalar esta versión» para continuar explícitamente. Si falla la comprobación, puedes continuar. Las operaciones pendientes y la recuperación omiten esta comprobación.

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

Para Root, el instalador comprueba y selecciona un método disponible para controlar Home. Si no puede verificar la compatibilidad, la instalación se detiene; no omitas la comprobación fallida.

Si el instalador ofrece **No-root**, puedes continuar con tu conexión SSH root actual. Esta opción no requiere Developer Mode.

**No-root → Root:** Si volvió a instalar No-root después de una eliminación completa, cambiar a Root puede requerir una limpieza previa. Guarde las preferencias de Home, elija **Desinstalar Clean Your TV** con la conexión Root guardada y espere la eliminación verificada. Esto también elimina Home y Helper de No-root. Luego instale Root; conserve los registros de recuperación.

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

La instalación Root continúa con un aviso si no se pueden leer las entradas del TV pero la lista de aplicaciones es válida. Pueden faltar entradas en Home; una lista de aplicaciones fallida o vacía sigue deteniendo la instalación. Guarda el informe de diagnóstico si el aviso persiste.

## 5. Comprueba el mando

1. Abre otra app del TV y pulsa brevemente **Home**. Debe abrirse Clean Your TV. Indica al asistente lo que viste; omite la prueba si no la hiciste.
2. Comprueba flechas, OK, Atrás, volumen y sonido. Prueba por separado la suspensión/reactivación y el arranque tras desconectar la alimentación. Una instalación correcta no verifica por sí sola estas acciones.

La configuración No-root activa Home tras verificar los paquetes si Helper no se ha detenido. Tras una parada, elige Iniciar Helper en el TV. Puedes desactivar Home después en Ajustes.

Usa la conexión y los datos de recuperación originales. Si se perdieron, vuelve a conectarte al mismo TV y elige Desinstalar Clean Your TV. Completa la eliminación verificada antes de configurar; no borres archivos de reserva. Si la eliminación se detiene, guarda el informe de diagnóstico.

<a id="uso-y-recuperación"></a>

## 6. Uso y recuperación

Para fijar una entrada HDMI, selecciónala en **+ / Añadir aplicación**. Pulsa OK para cambiar a esa entrada. Mantén pulsado OK para mover u ocultar su mosaico.

Si el instalador muestra «La configuración Root está incompleta, pero falta su registro de instalación en el TV.»: Elige Revisar opciones de recuperación para eliminar Clean Your TV y después inicia la configuración por separado. La eliminación completa también borra No-root Home y Helper; guarda primero tus preferencias.

Compatibilidad IR de No-root: al soltar Home tras una pulsación breve, Clean se programa para unos 700 ms después; LG Home puede aparecer primero. Mantener Home sigue correspondiendo a webOS y tres pulsaciones siguen deteniendo Helper. El acceso con Developer Mode normal no está verificado; no cambie los permisos de entrada.

Las flechas seleccionan y OK abre; mantén OK para reordenar. Una pulsación breve de Atrás conserva la navegación y confirmación de salida de cada aplicación. Home abre el lanzador mientras el control está activo. Mantén Atrás durante 1,2 segundos para abrir LG Home una vez. El interruptor de control de Home y tus ajustes no cambian.

**Pulsa Home tres veces en dos segundos**, soltando entre pulsaciones. Se recupera LG Home y se detiene el control sin borrar preferencias.

No-root: Para reiniciar el control de Home, abre Home Helper, elige Iniciar Helper y confirma. Se conserva tu pantalla Home elegida. Root: activa **Cambiar Home** en los ajustes de Home para reanudar. **Abrir LG Home** lo abre una vez sin cambiar el destino de Home. Para recuperar LG Home como destino permanente, desactiva **Cambiar Home**. No ejecutes ambos controladores a la vez. Si el fallo se repite, deja LG Home activo.

Las actualizaciones automáticas del TV no reinician Helper detenido. Para reanudarlo por separado usa Iniciar Helper; no borres archivos de parada.

## ¿Necesitas ayuda?

Si aparece `ssh-identity-changed` tras un reinicio de fábrica o un cambio de SSH, detente: CYTV bloqueó la clave guardada modificada antes de autenticar. La confirmación inicial de confianza no la reemplaza; una desinstalación pendiente no explica la discrepancia. Conserva el perfil original, las claves y los registros de recuperación. Si el perfil Root guardado tiene una desinstalación pendiente, puedes registrar en la consola la huella verificada de forma independiente. La desinstalación anterior seguirá bloqueada. Consulta [recuperación de identidad SSH](../RECOVERY.md#ssh-identity-changed).

Si se interrumpe la instalación, usa la misma conexión guardada y comienza por **Comprobar estado del TV**. Continúa solo mediante la recuperación que ofrezca el asistente. Si el estado es desconocido, guarda el informe de diagnóstico y detente; conserva los datos de recuperación y no repitas la instalación a ciegas.

Durante la recuperación, mantén desactivado el control de Home y conserva los informes originales y la conexión guardada. Confirma la inspección y los cambios por separado. Sigue la guía detallada correspondiente a tu versión instalada; no fuerces la reinstalación ni borres el estado de recuperación.

Indica modelo, firmware, No-root o Root, dispositivo de instalación, paso y mensaje de error. Elimina contraseñas, claves, direcciones y datos personales antes de compartir el informe. No se publica automáticamente.

[Informar de un problema](../FEEDBACK.md) · [Recuperación — inglés](../RECOVERY.md) · [Actualizar o eliminar — inglés](../MAINTENANCE.md) · [Otros idiomas](../LANGUAGES.md)

### Eliminación sencilla

Elige **Desinstalar Clean Your TV** en Mantenimiento con la misma conexión guardada. Confirma una vez. Se eliminan las apps y archivos conocidos del proyecto que estén presentes y se omiten los ausentes, incluso después de una instalación parcial.

En televisores antiguos sin una aplicación LG Home independiente, la eliminación de No-root puede cambiar a TV en directo. Mantenga el televisor encendido y reinícielo si se solicita; no borre los datos de recuperación ni restablezca el televisor.

Cuando se indique, desconecta la alimentación del TV, vuelve a conectarla, espera la red y elige **Intentar de nuevo**. Espera o Quick Start no es un reinicio completo; CYTV no reinicia el TV automáticamente. Si se pierde la conexión, compruébala y reintenta la misma eliminación sin otro asistente de recuperación. Si se deniega el acceso, usa la conexión Root solicitada; si el TV está ocupado, espera y reintenta. Solo se muestra éxito tras verificar la limpieza final. Conserva las claves y los informes originales. Siguen vigentes los controles de emergencia y el consentimiento para compartir.

Si el instalador no puede verificar el reinicio completo solicitado, guarda y adjunta el informe de diagnóstico. Conserva la conexión guardada y los datos de recuperación. No repitas los cortes de alimentación ni borres manualmente la operación pendiente.

Una instalación fallida o interrumpida ofrece recuperación directamente. Si No-root no puede continuar, confirma la eliminación completa una vez. La eliminación realiza hasta tres intentos ante cortes temporales de conexión o un proceso CYTV ocupado. Si requiere Root, elige **Conectar con Root** para el mismo TV; la limpieza Root verificada también completa su eliminación No-root bloqueada. Si falla la activación Root, CYTV intenta restaurar y verificar LG Home sin repetir la activación. Cancelar trabajo pendiente conserva el informe y las acciones de recuperación. Se mantiene la parada de emergencia.

Si falla la conexión durante la eliminación, abre sus detalles, comprueba la red o elige una clave SSH Root existente y reintenta. La dirección, edición, puerto y verificación de la clave del TV siguen fijados. Al reinstalar No-root, el asistente intenta detener Helper automáticamente. Pulsa Home solo si el asistente te lo pide y confirma la nueva comprobación. La eliminación puede finalizar sin reiniciar si se verifican los controles, la desactivación del inicio automático y la ausencia de paquetes, archivos y procesos, sin instalaciones pendientes. Si se solicita reiniciar, hazlo y reintenta. Si falla el servicio de entradas, continúa la limpieza segura de paquetes; el éxito exige verificar también la limpieza del acceso directo.

**Reinstalar Root:** Elige **Configurar mi televisor → Root** con la conexión guardada y confirma **¿Reinstalar Root?**. El instalador restaura LG Home y elimina por completo Clean Your TV, incluidos sus actualizadores, Home Helper y las preferencias guardadas. Tras verificar la eliminación, instala y activa los paquetes y el entorno Root incluidos en ese instalador. Se conservan las demás apps del TV y el acceso root/SSH existente. Si la eliminación se detiene o pide un reinicio completo, termínala antes de iniciar otra vez la configuración. **Desinstalar Clean Your TV** por sí solo nunca inicia otra instalación.

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

<a id="candidato-unreleased-nodejs-antiguo-en-el-tv"></a>
<a id="nodejs-antiguo-en-el-tv-publicado-en-v1120"></a>
<a id="eliminación-sencilla-v1110"></a>

## Ajustes

Usa ↑ ↓ para elegir una categoría y → u OK para entrar. ← vuelve a las categorías; Atrás vuelve primero a ellas y luego cierra los ajustes. Al volver a una sección se recupera el último control disponible. En Columnas, las flechas siguen la cuadrícula de tres columnas. En Idioma, el foco entra en el idioma seleccionado.

Si No-root no puede leer el estado de Home, elige Reintentar. Un control no disponible no significa que Home esté desactivado. En Fondos puedes subir una imagen desde el teléfono o CYTV; la calidad y el oscurecimiento aparecen cuando hay un fondo disponible. Eliminar un fondo personal requiere confirmación; Cancelar lo conserva.

## Tiempo

Abra Ajustes → Tiempo, debajo de Fondos. Active el tiempo y abra Ciudad para buscar y elegir la región y el país correctos, o seleccione Automático para obtener una ciudad aproximada según su conexión. Una VPN puede cambiar el resultado; si falta la ciudad o es incorrecta, use la búsqueda manual. La ciudad detectada o elegida aparece en ajustes. Elija °C / m/s o °F / mph y un formato disponible: breve, actual, detallado o cuatro días. La vista previa sigue el tema; Ejemplo indica datos de muestra. Liquid Glass solo admite el formato breve. Ribbon y Atmosphere no muestran el tiempo. Desactivarlo detiene las solicitudes y oculta ciudad, unidades y formato; la selección de fuente sigue disponible. Durante un fallo pueden mantenerse datos recientes temporalmente; después se ocultan hasta poder actualizarlos.

Elija la fuente del pronóstico: Auto, MET Norway u Open-Meteo. Auto empieza con MET Norway, prueba Open-Meteo una vez si falla y después reutiliza la última fuente que funcionó y su caché. La selección manual nunca cambia de fuente automáticamente. Los ajustes nuevos usan Auto; los guardados sin fuente conservan Open-Meteo. Se muestra la fuente real. La disponibilidad depende de la red. La aplicación consulta MET como máximo una vez cada tres horas; la caché caduca a las seis horas. Los campos ausentes se ocultan: MET no ofrece sensación térmica ni probabilidad de precipitación. Los rangos diarios resumen puntos del pronóstico, no extremos medidos.

Las coordenadas se envían a api.met.no o api.open-meteo.com y las búsquedas de ciudades a geocoding-api.open-meteo.com. La ubicación automática opcional transmite la IP pública a get.geojs.io. Las conexiones usan HTTPS; no hace falta una clave API. La ubicación, fuente y caché se guardan en el televisor. Fuentes de datos incluye condiciones y créditos, como el Instituto Meteorológico Noruego (MET Norway, CC BY 4.0).

El botón Fuentes de datos del encabezado Tiempo abre la información de servicios y licencias.

## Fondo desde el iPhone

Abre Ajustes → Fondos → Subir desde el teléfono y escanea el código. Elige JPG, PNG o HEIC/HEIF, recorta, acepta el límite de calidad y envía. Selecciona Aplicar en el TV. Safari usa HEIC nativo; Chrome, Firefox y otros navegadores modernos usan el decodificador local incluido cuando hace falta. La conversión ocurre en el teléfono, sin servicio externo. Cancelar o elegir otro archivo detiene la conversión. Entrada: 32 MiB y 50 millones de píxeles; salida: hasta 1080p y 2 MiB. Si falla, prueba otra foto o JPG/PNG. Es para la página del teléfono, no la app Mac.

## Configura tu Clean Your TV

Antes de elegir un tema, usa **Debloat** para seleccionar los ajustes de publicidad, recomendaciones, privacidad y notificaciones de LG que quieras cambiar. Revisa cada resultado. Si el instalador no puede leer el valor original, no podrá guardarlo para restaurarlo automáticamente. Elige **Omitir Debloat** para conservar los ajustes actuales.

Después de instalar correctamente, elige Classic, Liquid Glass o Ribbon y activa o desactiva el tiempo. Ribbon no admite el tiempo; Liquid Glass usa el formato compacto. La ciudad se estima por tu conexión y puedes cambiarla en Home.

No-root con Developer Mode ofrece renovación automática (Beta); sigue revisando el temporizador oficial. En las nuevas instalaciones de No-root mediante un acceso SSH root existente, la pestaña Developer Mode está oculta. Root permite bloquear actualizaciones de firmware LG mediante Homebrew Channel, incluidas las de seguridad; requiere un reinicio real desde Homebrew Channel. Las actualizaciones de CYTV son independientes.

Conservar ajustes actuales omite la personalización. El interruptor muestra el estado actual de la función del modo. Los ajustes que no cambies se conservan. Reinstalar Root sigue eliminando las preferencias CYTV como se describe arriba. Comprueba la apariencia en el TV y las opciones sin confirmar en Home antes de reintentar.
