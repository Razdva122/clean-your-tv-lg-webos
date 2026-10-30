# Clean Your TV — guía de uso

> v1.5.0: temas, galería y envío del PC al TV. Límites conocidos de Root: Appearance puede desplazarse 110 px; Home puede no abrirse automáticamente tras el modo de espera. La validación por dispositivo sigue limitada. [1.5.0](../RELEASE-1.5.0.md).

> Próximo candidato (sin publicar): los temas de diseño fijo conservan el espacio de la fila Columns oculta para mantener la posición de desplazamiento de Appearance al aplicar. El puntero, el teclado y las ayudas de accesibilidad omiten Columns. Falta la verificación en TV.

[Documentación](../README.md) · [Informar de un problema](../FEEDBACK.md)

Esta guía describe la versión publicada **[1.4.1](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.4.1)**. La aceptación del C3 cubre las pruebas registradas de alimentación, Home, foco, estado desactivado y reversión manual. Otros televisores, audio eARC y dispositivos Android físicos siguen sin verificar; instalar correctamente no demuestra compatibilidad. [Alcance probado (inglés)](../RELEASE-1.4.0-ACCEPTANCE.md).

**Instalador aún no publicado:** consola, escritorio y Android muestran cada comprobación del TV como pendiente, en curso, correcta, fallida o no verificable. Los resultados permanecen tras un error. Node.js/Python se comprueba en el TV; `doctor` no prepara Python ni solicita emparejamiento de control. Guarda el informe antes de reintentar.

## Elegir edición

No-root y Root son opciones equivalentes para distintas configuraciones del televisor. Elige No-root para LG Developer Mode o Root si ya tienes acceso root por SSH. La compatibilidad y las pruebas realizadas son específicas de cada edición.

- **No-root:** activa LG Developer Mode y Key Server. Introduce la frase de acceso que muestra el televisor y acepta en él la solicitud de emparejamiento independiente. Developer Mode debe permanecer activo: su caducidad puede eliminar aplicaciones instaladas por este método. Vigila el temporizador oficial incluso con la renovación Beta activada. La supervisión de Helper necesita la red local.
- **Root:** necesitas acceso SSH root previo. El instalador no obtiene root. No actives Developer Mode sobre una instalación ya rooteada. Conserva el acceso root y los servicios de recuperación.

Root necesita las interfaces de Home de Settings Service y System Profile (`com.webos.service.systemprofile`); tener acceso root no garantiza la compatibilidad.

## Requisitos

Enciende el televisor y conecta ambos equipos a la misma red local de confianza. Después, el ordenador puede estar apagado. La compatibilidad depende del modelo, firmware y mando; Root tiene pruebas físicas pendientes.

No-root Helper necesita Node.js **0.12.2+** en el televisor. Root necesita Node.js **8+** y Python **3.9+** funcional. Si hace falta, el instalador descarga un Python privado verificado; la preparación inicial necesita **320 MiB** libres. No sustituye Python del sistema. Conserva los entornos que use la recuperación. [Python (inglés)](../OPTIONAL-PYTHON.md). La renovación de Developer Mode es **Beta, desactivada por defecto**; la renovación real sin root no está confirmada. Sigue vigilando el temporizador oficial.

### Configurar Developer Mode (No-root)

Developer Mode permite a CYTV instalar apps en un TV sin root.

1. En el TV, abre LG Apps, busca Developer Mode e instálalo.
2. Abre Developer Mode e inicia sesión con tu cuenta LG Developer. Si necesitas una, créala en webostv.developer.lge.com.
3. Activa Dev Mode Status. El TV se reiniciará. Después, abre Developer Mode de nuevo.
4. Activa Key Server y deja Developer Mode abierto. Introduce su IP Address como dirección del TV en CYTV.
5. Introduce la Passphrase: los seis caracteres que muestra Developer Mode en el TV. Respeta mayúsculas y minúsculas.

Usa el código del TV, no la contraseña de tu cuenta LG. Si no aparece el código, activa Key Server.

El emparejamiento es un paso aparte: cuando el TV lo pida, acepta CYTV con el mando.

Mantén Developer Mode activo: antes de que termine el tiempo, ábrelo y pulsa EXTEND con el TV conectado a Internet. Si caduca, LG puede eliminar estas apps.

## Instalación e idioma

- **Windows x64:** descarga `cytv-windows-x64-desktop.zip`, elige **Extraer todo** en el Explorador y abre `cytv-desktop/cytv-desktop.exe`. Conserva la carpeta `_internal` a su lado. No se ha configurado la firma de editor de Windows. La consola separada es `cytv-windows-x64.exe`; renómbrala a `cytv.exe` y usa `.\cytv.exe` en PowerShell para los comandos siguientes.
- **macOS 13+:** extrae `cytv-macos-arm64.zip` para Apple Silicon o `cytv-macos-x64.zip` para Intel, mueve `cytv.app` a Aplicaciones y ábrela. Permite el acceso a la red local. Si se bloquea una descarga de confianza, usa Privacidad y seguridad → Abrir igualmente; no desactives Gatekeeper. La aceptación en sistemas antiguos no está confirmada.
- **Linux x64:** en Ubuntu 22.04+, Debian 12+ o Mint 21+, instala `cytv-linux-x64.deb` con el gestor gráfico de paquetes y abre Clean Your TV desde el menú de aplicaciones. Las bibliotecas pueden requerir Internet. No hay paquete Linux ARM. El ejecutable independiente `cytv-linux-x64` es la CLI; usa el `.deb` para la app gráfica.

[Instalador Android (inglés)](../../android/README.md): elige el idioma arriba a la derecha. Actualiza sin desinstalar ni borrar datos. Android 7 / WebView 108 es el mínimo, no una configuración de teléfono verificada; se aceptó el emulador Android 15 ARM64 / WebView 124. Los teléfonos físicos y la recuperación conectada a un televisor real no están verificados.

El asistente de escritorio usa inicialmente el idioma del sistema y guarda una selección explícita. En el televisor, abre **Ajustes → Idioma** y elige un idioma o la opción automática del sistema. Las preferencias del instalador y del televisor son independientes. Consulta los códigos en el [índice de idiomas](../LANGUAGES.md).

Para la CLI descargada por separado en macOS/Linux, desde la carpeta extraída:

```sh
chmod +x cytv
./cytv --language es install
```

Selecciona el televisor o introduce su IP, elige la edición y revisa el resumen. Confirma una nueva identidad SSH solo para tu televisor en una red de confianza; una clave guardada que haya cambiado bloquea el acceso. Root prepara la recuperación y activa Home inmediatamente, sin prueba temporal ni paso de conservación. Comprueba flechas, OK, Home, Atrás/Cancelar, volumen, suspensión y arranque en frío.

## Uso y recuperación

Las flechas seleccionan y OK abre; mantén OK para reordenar. Una pulsación breve de Atrás conserva la navegación y confirmación de salida de cada aplicación. Home abre el lanzador mientras el control está activo. Mantén Atrás durante 1,2 segundos para abrir LG Home una vez. El interruptor de control de Home y tus ajustes no cambian.

**Pulsa Home tres veces en dos segundos**, soltando entre pulsaciones. Se recupera LG Home y se detiene el control sin borrar preferencias. En No-root Helper hasta 0.6.13 inclusive, mantén Home unos dos segundos. Mantener Home no es el gesto de emergencia de Root.

No-root: Para reiniciar el control de Home, abre Home Helper, elige Iniciar Helper y confirma. Se conserva tu pantalla Home elegida. Root: activa **Cambiar Home** en los ajustes de Home para reanudar. **Abrir LG Home** lo abre una vez sin cambiar el destino de Home. Para recuperar LG Home como destino permanente, desactiva **Cambiar Home** o ejecuta `cytv restore`. No ejecutes ambos controladores a la vez. Si el fallo se repite, deja LG Home activo.

```sh
./cytv --language es status
./cytv --language es doctor --report
./cytv --language es restore
./cytv --language es uninstall
```

Tras una interrupción, ejecuta primero `status` y conserva los registros. `restore` recupera LG Home sin quitar aplicaciones; `uninstall` lo restaura antes de eliminarlas. Los datos de recuperación Root se conservan deliberadamente: no los borres para forzar otra instalación. Revisa los informes antes de compartirlos; no publiques claves ni carpetas de perfiles.

Solo en el candidato no publicado, en ambas ediciones: abre **Ajustes de Home → Apariencia → Columnas** y elige de 1 a 8 columnas, o **Según el tema** para usar su valor (Classic: 5). Un número explícito tiene prioridad sobre el tema. Los temas con una distribución fija ocultan la opción Columnas y usan el valor del autor. Tu elección guardada se recupera al cambiar a un tema que admita este ajuste. En la vista previa candidata de Alpine, las apps forman una cinta horizontal circular: Izquierda/Derecha desplaza, Arriba abre los accesos y Abajo vuelve a la misma app. En la vista previa de Alpine también puedes desplazar la cinta con la rueda o el panel táctil; Home no se mueve detrás de un diálogo abierto.

Candidato aún no publicado, ambas ediciones: en **Ajustes de Home → Apariencia**, desactiva **Mostrar tarjeta «Añadir app»** para ocultar +. Está activada de forma predeterminada. Usa **Añadir app** en la misma sección para añadir o recuperar apps aunque + esté oculto. Puedes seguir ordenando y ocultando apps; la elección se conserva al reiniciar. Si ocultas todas las apps, los controles superiores y los ajustes siguen disponibles.

En las vistas previas de temas del candidato no publicado con barra lateral opcional, Arriba/Abajo selecciona una opción del menú, Derecha pasa a las aplicaciones e Izquierda desde la primera columna de aplicaciones vuelve al menú.

No-root 1.5.0: Helper puede recuperarse de un tiempo de espera temporal del watchdog al salir del modo de espera, con un máximo de cinco intentos en diez minutos. Stop y pulsar Home tres veces siguen requiriendo iniciar Helper explícitamente; los fallos repetidos lo dejan detenido. La validación en TV está pendiente. [Comportamiento y límites (inglés)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Actualizaciones y eliminación

Guarda paquetes funcionales y copias privadas de ajustes. Para sustituir paquetes No-root desde el ordenador, detén Helper primero y actualiza sin desinstalar, ya que podrías perder ajustes. Eliminar la aplicación del ordenador no elimina las aplicaciones del televisor. No sustituyas un entorno Root activo con una IPK suelta; usa el proceso explícito de recuperación o reinstalación de cytv.

Abre ajustes de Home → Actualizaciones de software y revisa las versiones antes de confirmar. Actualizar y revertir desde el televisor requiere **root, Homebrew Channel** e infraestructura de actualización compatible ya preparada, incluso en No-root. Sin root, usa el instalador del ordenador. Preparar actualizaciones completas es una acción explícita aparte: [actualizaciones (inglés)](../UPDATES.md). Recuperación muestra la versión guardada; revertir puede perder ajustes posteriores.

**Si ya tienes 1.3.0:** el System Updater original no puede aplicar 1.4.0 porque cambió la lista de archivos permitidos. Si el intento se detuvo antes del reemplazo, conserva el registro y para; no borres el estado ni repitas a ciegas. Migra mediante recuperación comprobada e instalación nueva de 1.4.0; actualizar solo la app no sustituye los controladores Root conservados. La siguiente corrección OTA **no está publicada**. [Migración y recuperación (inglés)](../UPDATES.md#one-time-computer-preparation).

Corrección aún no publicada del canal de ajustes de Home: actualiza Home y Helper juntos cuando haya un candidato coordinado. Actualizar solo Home no incluye la corrección. Falta verificar la compilación final de la versión en el TV. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

La recuperación de sonido HDMI de Root es experimental y está **desactivada por defecto**; actívala solo si la necesitas. Puede interrumpir audio que funciona y no demuestra compatibilidad eARC. [Recuperación de sonido (inglés)](../development/ROOT-AUDIO-RECOVERY.md). El **CYTV Installer de Homebrew sigue sin publicarse**; usa el instalador publicado para ordenador o Android.

Homebrew Channel denegó el acceso a este instalador. En webOS 11, Homebrew 0.7.3 necesita una actualización de compatibilidad de sus desarrolladores. Usa el instalador publicado para ordenador o Android hasta que una versión compatible de Homebrew incluya la corrección. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

Solo candidato no publicado: si el acceso a la API de firmware falla por directorios Root antiguos con permisos de escritura, `cytv enable-firmware-access --edition root --repair-package-permissions` verifica el paquete actual con datos privados de confianza y elimina la escritura para grupo/otros solo en rutas propias de Root. Los archivos desconocidos o modificados detienen la reparación. Conserva el perfil, Home y el bloqueo de firmware; [detalles (inglés)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

Solo en el candidato no publicado: `cytv recover-system-rollback --edition root` recupera una reversión Root verificada cuyos instaladores terminaron, pero venció el plazo de disponibilidad del lanzador. Exige la señal auténtica del lanzador y rechaza resultados de instalación desconocidos. Conserva paquetes, código y claves fijados, pruebas del fallo y la desactivación explícita de Home. Un registro privado conserva el intento limitado. Repetir normalmente no amplía el plazo. Solo tras vencer los 120 segundos, sin señal de disponibilidad aceptada ni resultado de instalación desconocido, `--new-recovery-attempt` archiva el registro anterior completo con su UUID/hash e inicia explícitamente otro intento. Una recuperación completada sigue siendo idempotente; no hay intentos automáticos. [Procedimiento y límites (inglés)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0: el paquete de sustitución incluye System Updater 1.1.2. Antes de OTA, sustituye explícitamente 1.1.0 o 1.1.1 con `cytv replace-system-updater --edition root`. Solo cambia System Updater; se conservan las apps Root/Root Updater, el perfil completo y Home, y se archiva el estado anterior. Las operaciones desconocidas o pendientes bloquean la sustitución. Este requisito no bloquea los feeds No-root. [Procedimiento (inglés)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Ayuda y más instrucciones

Tras un fallo o interrupción, comprueba el estado y guarda el informe de diagnóstico de ese intento. La recuperación guiada pide confirmaciones separadas para eliminar y reinstalar. Si el resultado es incierto, para y conserva registros privados y archivos de recuperación; nunca los borres para forzar otro intento. [Recuperación (inglés)](../RECOVERY.md). Para pedir ayuda, indica modelo, firmware, edición, versión del instalador, paso fallido y resultado esperado/real; revisa y elimina secretos del informe antes de compartirlo.

[Documentación](../README.md) · [Informar de un problema](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="python-opcional-para-root-en-v110"></a>
<a id="bloqueo-de-firmware-lg-en-120"></a>
<a id="novedades-de-130-recuperación-guiada-de-escritorio"></a>
<a id="novedades-de-130--12"></a>
<a id="candidato-sin-publicar-instalar-root-mediante-homebrew"></a>
<a id="candidato-sin-publicar-recuperación-de-sonido-hdmi-root"></a>


## Temas: candidato en desarrollo

En el candidato compatible: **Ajustes → Apariencia**. **Classic** y **Alpine** están integrados y no necesitan descargar el tema; Classic sigue como predeterminado. **Channel** es externo, desde showcase. En las pruebas de la galería: Elige el tema y **Conservar tema** antes de **20 segundos**. **Revertir**, Back o el tiempo agotado recuperan el anterior. Una prueba interrumpida inicia Home con Classic. Los temas integrados y descargados elegidos en la lista instalada se aplican y guardan al instante, sin temporizador. Esto incluye los recibidos del ordenador o instalados por URL. Solo Probar tema dentro de la galería inicia una prueba de 20 segundos.

Los temas instalados aparecen en una sola fila con desplazamiento horizontal. El tema activo siempre está primero y su tarjeta está resaltada. Usa Izquierda/Derecha para recorrer la fila.

La galería solo muestra temas no instalados en este TV. Classic, Alpine y los descargados se ocultan, incluso si hay una versión más reciente. Al eliminar un tema vuelve a aparecer. Actualiza por URL o desde el ordenador.

Las tarjetas están integradas en Apariencia, junto a las categorías. La galería, la instalación por enlace y la transferencia desde el ordenador se abren ahí; solo una prueba de la galería muestra Home temporalmente.

Al abrir la galería o elegir Actualizar se consultan las novedades revisadas del repositorio principal sin actualizar Home ni recargar la página. Las nuevas entradas aparecen tras la integración normal; un candidato sin integrar puede mostrar el catálogo incluido. Sin conexión o ante errores se usan entradas y vistas previas incluidas. Los temas integrados corresponden a la versión instalada de Home. Abre la vista previa de Channel y elige **Descargar tema** (requiere internet). Tras descargarlo, pruébalo y elige **Conservar tema** en **20 segundos**. Los temas instalados funcionan sin conexión. **Añadir por URL** sigue disponible para enlaces fijados.

Para probar un tema no publicado, abre primero **Ajustes → Apariencia → Recibir del ordenador** en el TV. Introduce su dirección y PIN de seis dígitos en **Send to TV** de la vista previa del ordenador, envía y elige **Aplicar tema** en el TV. El método principal conecta desde el PC al puerto TCP **8879 del TV**, sin modificar el cortafuegos del ordenador. Ambos deben estar en la misma red doméstica de confianza. El receptor se cierra tras una carga, cancelar, salir o **10 minutos**. El PIN no se guarda; el tema instalado funciona sin conexión. No es necesario publicar en GitHub.

Para un tema publicado, abre **Más opciones → Añadir por URL** e introduce su ID (por ejemplo `102300a209`), `da.gd/102300a209` o el enlace completo de GitHub. Home muestra la dirección da.gd antes de cargar y verifica el destino GitHub y el paquete. El autor puede copiar el ID de las notas de versión o de **TV link → Copy ID** en la vista previa.

Los paquetes publicados quizá aún no tengan estos controles. Las pruebas de navegador no demuestran compatibilidad física. [Guía completa](../THEMES.md).

Temas muestra vistas previas de los temas integrados y de todos los que hayas instalado, incluso sin conexión. Un botón aparte abre el catálogo de temas publicados; instalar un tema personal no lo publica.

En la versión candidata, Apariencia muestra tarjetas grandes de los temas instalados y marca el elegido. La galería y recibir desde el ordenador son las acciones principales. Más opciones contiene añadir por URL, restaurar Classic y borrar temas descargados. Las flechas recorren tarjetas y botones; izquierda en el borde vuelve a las categorías.

En la vista previa del navegador, Recibir del ordenador explica los pasos del televisor; no inicia un receptor de TV en el ordenador. Usa Send to TV encima de la vista previa. Eliminar un tema descargado requiere confirmación; si está activo, se restaura Classic primero. Cancelar conserva el tema.

<a id="categorías-de-ajustes-candidato-no-publicado"></a>

## Categorías de ajustes (1.5.0)

Ambas ediciones muestran categorías a la izquierda y ajustes a la derecha: pantalla de inicio, Apariencia (temas y columnas), Idioma, Actualizaciones de software y Avanzado. No-root añade Developer Mode; Root incluye el firmware LG en actualizaciones y sonido HDMI en Avanzado. Arriba/abajo recorre una columna; derecha entra en los ajustes e izquierda vuelve a las categorías. Atrás vuelve primero a las categorías y después cierra los ajustes. Tab también permite volver a Home.

Un punto amarillo en Actualizaciones de software y en el botón interior indica que hay una actualización. Ambos desaparecen cuando una comprobación correcta confirma que no hay actualizaciones; si falla, se conserva el último estado confirmado.
