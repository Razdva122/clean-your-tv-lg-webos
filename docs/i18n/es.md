# Clean Your TV — guía de uso

> **1.8.2 — Candidato no publicado:** [1.8.2 / English](../RELEASE-1.8.2.md).

**C1 Beta sin publicar (#298):** Elige Root en el instalador común para ordenador. Los C1 aptos se detectan automáticamente; no hace falta otro instalador ni una opción especial. Esta vía exige una instalación limpia, no tiene actualizaciones automáticas y aún no ha superado la validación en un C1 físico. Abrir LG Home, mantener Back o una parada por seguridad o alimentación pueden dejar desactivado el control de Home; vuelve a activar Cambiar Home en los ajustes del TV. La vía Root normal no cambia. Si quedan otros componentes No-root, la eliminación completa de C1 se detiene antes de hacer cambios. Elimínalos primero mediante su flujo normal de No-root; conserva los datos de recuperación si su estado no está resuelto. [C1 Beta contract (English)](../development/C1-NATIVE-GATE.md). C1 Beta filtra la tecla Home y vuelve al cerrar una app, sin cambiar permisos de CRIU/checkpoint. LG Home puede aparecer brevemente. Pulsar Home tres veces también detiene la redirección; después vuelve a activar Cambiar Home.

Sin publicar (#290): **+ / Añadir app** ofrece TV en directo con el nombre del televisor solo si detecta el sintonizador instalado. Las demás apps del sistema ocultas siguen excluidas. No-root necesita Helper e instalador actualizados; Root necesita el paquete Home actualizado. Falta verificar el inicio de canales en el TV.

**Sin publicar — Ribbon en Home:** Ribbon es un tema de la única aplicación Home a pantalla completa en ambas ediciones, con su propio fondo. No se muestra vídeo ni HDMI detrás de las tarjetas. Seleccionar una aplicación utiliza el cambio normal de aplicaciones del televisor. Los controles de emergencia no cambian. Faltan los paquetes finales y la validación en TV. [Ribbon](../THEMES.md#ribbon-over-applications-unreleased).

Ribbon: mantén OK para editar; ←/→ mueve la tarjeta, ↑ selecciona × (ocultar de Home), ↓ vuelve a la tarjeta, OK confirma y Back cancela. Se conserva el fondo actual.

**1.7.0 — fuentes de inicio Root:** En Ajustes → Tu pantalla Home, activa **Cambiar Home** para editar **Abrir Clean Your TV primero**. **LG Channels / TV en directo** está activado por defecto; **YouTube** está desactivado. Al desactivar Cambiar Home, los interruptores siguen visibles pero bloqueados y conservan sus valores. Estas preferencias se guardan de forma privada en el televisor y no se incluyen en la exportación portátil del perfil. No confirma el inicio ni la reactivación del TV. Una fuente desactivada deja la decisión de inicio al firmware del TV; no garantiza volver a esa fuente. No hay interruptor de inicio HDMI. [Límites del inicio nativo (inglés)](../../root-edition/README.md#candidate-native-startup-choices).

> Esta guía describe 1.7.0. Descarga los paquetes disponibles desde las [publicaciones de GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). Incluye las cinco mejoras del instalador. Al reabrirse, Ajustes de Root lee el estado real; una comprobación fallida no activa Home. System Updater 1.2.0 sirve para una instalación nueva admitida o la sustitución verificada de 1.1.0/1.1.1. El 1.1.2 instalado conserva sus canales anteriores; no hay migración general. Conserva los datos de recuperación y no fuerces la sustitución. [Versiones y límites](../RELEASE-1.7.0.md).

> v1.5.0: temas, galería y envío del PC al TV. Límites conocidos de Root: Appearance puede desplazarse 110 px; Home puede no abrirse automáticamente tras el modo de espera. La validación por dispositivo sigue limitada. [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** los temas de diseño fijo conservan el espacio de la fila Columns oculta para mantener la posición de desplazamiento de Appearance al aplicar. El puntero, el teclado y las ayudas de accesibilidad omiten Columns.

[Documentación](../README.md) · [Informar de un problema](../FEEDBACK.md)

**Pruebas históricas de 1.5.4:** La aceptación del C3 cubre las pruebas registradas de alimentación, Home, foco, estado desactivado y reversión manual. Otros televisores, audio eARC y dispositivos Android físicos siguen sin verificar; instalar correctamente no demuestra compatibilidad. [Alcance probado (inglés)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

**1.5.4:** consola, escritorio y Android muestran cada comprobación del TV como pendiente, en curso, correcta, fallida o no verificable. Los resultados permanecen tras un error. Node.js/Python se comprueba en el TV; `doctor` no prepara Python ni solicita emparejamiento de control. Guarda el informe antes de reintentar.

## Elegir edición

No-root y Root son opciones equivalentes para distintas configuraciones del televisor. Elige No-root para LG Developer Mode o Root si ya tienes acceso root por SSH. La compatibilidad y las pruebas realizadas son específicas de cada edición.

- **No-root:** activa LG Developer Mode y Key Server. Introduce la frase de acceso que muestra el televisor y acepta en él la solicitud de emparejamiento independiente. Developer Mode debe permanecer activo: su caducidad puede eliminar aplicaciones instaladas por este método. Vigila el temporizador oficial incluso con la renovación Beta activada. La supervisión de Helper necesita la red local.
- **Root:** necesitas acceso SSH root previo. El instalador no obtiene root. No actives Developer Mode sobre una instalación ya rooteada. Conserva el acceso root y los servicios de recuperación.

Root necesita las interfaces de Home de Settings Service y System Profile (`com.webos.service.systemprofile`); tener acceso root no garantiza la compatibilidad.

> **1.6.0:** Root comprueba las interfaces Home necesarias antes de preparar Python privado o paquetes. Un fallo detiene la instalación; superar la prueba no demuestra compatibilidad del firmware ni el funcionamiento del botón Home. Los errores de conexión conocidos muestran consejos específicos. Conserva perfiles, datos de confianza y recuperación; las operaciones pendientes requieren recuperación verificada, no repetir a ciegas. Guarda y revisa el informe. [Detalles](../development/INSTALLER-PREFLIGHT-HELP.md).

## Requisitos

Enciende el televisor y conecta ambos equipos a la misma red local de confianza. Después, el ordenador puede estar apagado. La compatibilidad depende del modelo, firmware y mando; Root tiene pruebas físicas pendientes.

1.5.4 incluye Home Helper **0.6.21** para Node.js **0.10.25+** en el TV; Root sigue necesitando Node.js **8+**. [Compatibility](../COMPATIBILITY.md).

**Cambio no publicado para webOS 1.x:** el próximo instalador No-root admite Node.js **0.10.15+** del TV tras pruebas de Helper con esa versión exacta; el instalador publicado 1.7.1 aún requiere **0.10.25+**. Esto no confirma compatibilidad con WebKit antiguo, entrada nativa ni Home. No sustituyas el runtime del TV ni omitas las comprobaciones. Root sigue necesitando Node.js 8+. [Pruebas y límites](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased).

No-root Helper necesita Node.js **0.10.25+** en el televisor. Root necesita Node.js **8+** y Python **3.9+** funcional. Si hace falta, el instalador descarga un Python privado verificado; la preparación inicial necesita **320 MiB** libres. No sustituye Python del sistema. Conserva los entornos que use la recuperación. [Python (inglés)](../OPTIONAL-PYTHON.md). La renovación de Developer Mode es **Beta, desactivada por defecto**; la renovación real sin root no está confirmada. Sigue vigilando el temporizador oficial.

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

**Candidato Android no publicado:** para una operación Root original `install / coordinator-submitted`, la revisión de recuperación puede realizar una inspección de solo lectura tras confirmación explícita, usando el perfil y la clave de host SSH originales. No desinstales, borres datos, sustituyas el perfil ni repitas la instalación. Usa solo el APK reconstruido y firmado indicado por el mantenedor; el APK público aún no incluye esta ruta. [Procedimiento y límites](../../android/README.md#interrupted-root-installation-inspection-unreleased).

El asistente de escritorio usa inicialmente el idioma del sistema y guarda una selección explícita. En el televisor, abre **Ajustes → Idioma** y elige un idioma o la opción automática del sistema. Las preferencias del instalador y del televisor son independientes. Consulta los códigos en el [índice de idiomas](../LANGUAGES.md).

Para la CLI descargada por separado en macOS/Linux, desde la carpeta extraída:

```sh
chmod +x cytv
./cytv --language es install
```

Selecciona el televisor o introduce su IP, elige la edición y revisa el resumen. Confirma una nueva identidad SSH solo para tu televisor en una red de confianza; una clave guardada que haya cambiado bloquea el acceso. Root prepara la recuperación y activa Home inmediatamente, sin prueba temporal ni paso de conservación. Comprueba flechas, OK, Home, Atrás/Cancelar, volumen, suspensión y arranque en frío.

**1.6.0:** se muestran por separado la verificación de paquetes, el inicio y tu observación del botón Home físico. Una confirmación de inicio o un proceso Helper no prueban la interceptación de Home. Abre otra app, pulsa Home una vez brevemente y elige lo observado; el valor predeterminado es **No probado / omitir**. `--yes` no responde por ti y el modo no interactivo deja la prueba pendiente. Un fallo de Home o una omisión no deshacen los paquetes ni reinstalan. Guarda el informe local para pedir ayuda; no se publica automáticamente. Otros controles, sonido, espera y arranque en frío se prueban aparte.

## Uso y recuperación

Las flechas seleccionan y OK abre; mantén OK para reordenar. Una pulsación breve de Atrás conserva la navegación y confirmación de salida de cada aplicación. Home abre el lanzador mientras el control está activo. Mantén Atrás durante 1,2 segundos para abrir LG Home una vez. El interruptor de control de Home y tus ajustes no cambian.

**Pulsa Home tres veces en dos segundos**, soltando entre pulsaciones. Se recupera LG Home y se detiene el control sin borrar preferencias. En No-root Helper hasta 0.6.13 inclusive, mantén Home unos dos segundos. Mantener Home no es el gesto de emergencia de Root.

No-root: Para reiniciar el control de Home, abre Home Helper, elige Iniciar Helper y confirma. Se conserva tu pantalla Home elegida. Root: activa **Cambiar Home** en los ajustes de Home para reanudar. **Abrir LG Home** lo abre una vez sin cambiar el destino de Home. Para recuperar LG Home como destino permanente, desactiva **Cambiar Home** o ejecuta `cytv restore`. No ejecutes ambos controladores a la vez. Si el fallo se repite, deja LG Home activo.

Corrección de Root aún no publicada: al desactivar el control de Home o elegir Open LG Home, la ventana de Root se cierra cuando LG Home confirma el inicio. Puede abrir Home Root manualmente para acceder a Ajustes mientras el control de Home sigue desactivado.

> **1.5.4 — Root:** al activar explícitamente **Cambiar Home** con Root funcionando correctamente, CYTV crea su propia entrada nativa **Clean** y guarda Clean como entrada recordada. Al desactivar el control de Home, detenerlo por emergencia, producirse un fallo, suspenderlo para actualizar o desinstalar, elimina su entrada y restaura la anterior solo si el valor actual sigue siendo el que puso CYTV; conserva otras entradas y aplicaciones en primer plano. En televisores no compatibles o con entradas que no pertenecen a CYTV se mantiene el control habitual de Home con sus protecciones. No se garantiza que Clean sea la primera pantalla inmediata. Pasaron las pruebas registradas de primera pantalla, suspensión y arranque sin alimentación en el C3; no garantizan compatibilidad universal. Home puede quedar desactivado tras actualizar/revertir (#202), y Ajustes puede mostrar un estado antiguo (#206): cierra y abre Ajustes, activa Cambiar Home explícitamente y espera el estado Clean. [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language es status
./cytv --language es doctor --report
./cytv --language es restore
./cytv --language es uninstall
```

> **1.6.0 (#152):** si se rechaza desactivar Helper, la restauración/eliminación No-root podrá usar una detención verificada por SSH. Se conserva el estado de parada y, si el resultado es incierto, el registro. No borres archivos de estado. Falta la confirmación en el EF950V. [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** el estado de No-root conserva el registro de una instalación o eliminación interrumpida. Los archivos coincidentes o las aplicaciones ausentes no demuestran que la operación haya terminado. Si se deniega la verificación, deténgase y conserve el diagnóstico; no hay un método basado solo en archivos para omitirla. [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

Tras una interrupción, ejecuta primero `status` y conserva los registros. `restore` recupera LG Home sin quitar aplicaciones; `uninstall` lo restaura antes de eliminarlas. Los datos de recuperación Root se conservan deliberadamente: no los borres para forzar otra instalación. Revisa los informes antes de compartirlos; no publiques claves ni carpetas de perfiles.

Abre **Ajustes de Home → Apariencia → Columnas** y elige de 1 a 8 columnas, o **Según el tema** para usar su valor (Classic: 5). Un número explícito tiene prioridad sobre el tema. Los temas con una distribución fija ocultan la opción Columnas y usan el valor del autor. Tu elección guardada se recupera al cambiar a un tema que admita este ajuste. En Alpine descargado, las apps forman una cinta horizontal circular: Izquierda/Derecha desplaza, Arriba abre los accesos y Abajo vuelve a la misma app. En Alpine también puedes desplazar la cinta con la rueda o el panel táctil; Home no se mueve detrás de un diálogo abierto.

1.5.4: en **Ajustes de Home → Apariencia**, desactiva **Mostrar tarjeta «Añadir app»** para ocultar +. Está activada de forma predeterminada. Usa **Añadir app** en la misma sección para añadir o recuperar apps aunque + esté oculto. Puedes seguir ordenando y ocultando apps; la elección se conserva al reiniciar. Si ocultas todas las apps, los controles superiores y los ajustes siguen disponibles.

1.7.0: el tema elegido determina si **Entradas** aparece como menú en la cabecera o como fila HDMI; no hay un ajuste global de ubicación ni el interruptor **Mostrar entradas en Home**. La fila solo admite `dock-grid` por ahora. Liquid Glass la elige; Classic y los temas sin esta opción conservan el menú superior. Arriba desde el dock entra en la fila, otra vez Arriba llega a la cabecera, Abajo o Atrás vuelve al dock y OK abre la fuente. Si hay tarjetas de fuentes, la fila sustituye al menú Entradas de la cabecera. El nombre del dispositivo procede de los metadatos de entradas solo si el firmware lo proporciona; de lo contrario, la fuente conectada muestra **Conectado**. Home no inventa un nombre de PlayStation ni garantiza la identificación CEC. Los puertos vacíos siguen seleccionables. Las vistas previas están **activadas de forma predeterminada**; una opción Desactivado guardada explícitamente se conserva. Desactiva **Ajustes de Home → Apariencia → Vista previa de la entrada seleccionada** para apagarlas. Mientras estén activadas y el tema tenga la fila, un HDMI conectado puede mostrar una vista previa tras unos 0,8 segundos de foco. En algunos TV, las vistas previas HDMI pueden reproducir sonido o activar HDR; no se garantiza el silencio. Home no cambia automáticamente el silencio global ni los ajustes HDR del TV. Live TV y los puertos vacíos mantienen tarjetas estáticas. Root consulta el estado de entradas mediante su propio servicio. No-root conserva EIM directo cuando está permitido; si se deniega el permiso, hace una consulta de solo lectura mediante Helper ya vinculado. Si falla, el estado queda desconocido; no hay un control ni una solicitud de vinculación nuevos.

En las vistas previas de temas de 1.5.4 con barra lateral opcional, Arriba/Abajo selecciona una opción del menú, Derecha pasa a las aplicaciones e Izquierda desde la primera columna de aplicaciones vuelve al menú.

No-root 1.5.0: Helper puede recuperarse de un tiempo de espera temporal del watchdog al salir del modo de espera, con un máximo de cinco intentos en diez minutos. Stop y pulsar Home tres veces siguen requiriendo iniciar Helper explícitamente; los fallos repetidos lo dejan detenido. La validación en TV está pendiente. [Comportamiento y límites (inglés)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Actualizaciones y eliminación

Guarda paquetes funcionales y copias privadas de ajustes. Para sustituir paquetes No-root desde el ordenador, detén Helper primero y actualiza sin desinstalar, ya que podrías perder ajustes. Eliminar la aplicación del ordenador no elimina las aplicaciones del televisor. No sustituyas un entorno Root activo con una IPK suelta; usa el proceso explícito de recuperación o reinstalación de cytv.

Abre ajustes de Home → Actualizaciones de software y revisa las versiones antes de confirmar. Actualizar y revertir desde el televisor requiere **root, Homebrew Channel** e infraestructura de actualización compatible ya preparada, incluso en No-root. Sin root, usa el instalador del ordenador. Preparar actualizaciones completas es una acción explícita aparte: [actualizaciones (inglés)](../UPDATES.md). Recuperación muestra la versión guardada; revertir puede perder ajustes posteriores.

**Si ya tienes 1.3.0:** su System Updater original puede rechazar cambios de infraestructura. Conserva la operación interrumpida y sigue la recuperación y preparación de reemplazo verificadas para 1.5.0+; no borres registros ni repitas a ciegas. Actualizar solo la app no sustituye la infraestructura Root fijada. [Migración y recuperación (inglés)](../UPDATES.md#one-time-computer-preparation).

La corrección del canal de ajustes de Home se publicó en 1.5.0. Actualiza Home y Helper juntos con un instalador publicado compatible; actualizar solo Home no cambia Helper. La validación sigue limitada a los modelos registrados. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

La recuperación de sonido HDMI de Root es experimental y está **desactivada por defecto**; actívala solo si la necesitas. Puede interrumpir audio que funciona y no demuestra compatibilidad eARC. [Recuperación de sonido (inglés)](../development/ROOT-AUDIO-RECOVERY.md). El **CYTV Installer de Homebrew sigue sin publicarse**; usa el instalador publicado para ordenador o Android.

Homebrew Channel denegó el acceso a este instalador. En webOS 11, Homebrew 0.7.3 necesita una actualización de compatibilidad de sus desarrolladores. Usa el instalador publicado para ordenador o Android hasta que una versión compatible de Homebrew incluya la corrección. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: si el acceso a la API de firmware falla por directorios Root antiguos con permisos de escritura, `cytv enable-firmware-access --edition root --repair-package-permissions` verifica el paquete actual con datos privados de confianza y elimina la escritura para grupo/otros solo en rutas propias de Root. Los archivos desconocidos o modificados detienen la reparación. Conserva el perfil, Home y el bloqueo de firmware; [detalles (inglés)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` recupera una reversión Root verificada cuyos instaladores terminaron, pero venció el plazo de disponibilidad del lanzador. Exige la señal auténtica del lanzador y rechaza resultados de instalación desconocidos. Conserva paquetes, código y claves fijados, pruebas del fallo y la desactivación explícita de Home. Un registro privado conserva el intento limitado. Repetir normalmente no amplía el plazo. Solo tras vencer los 120 segundos, sin señal de disponibilidad aceptada ni resultado de instalación desconocido, `--new-recovery-attempt` archiva el registro anterior completo con su UUID/hash e inicia explícitamente otro intento. Una recuperación completada sigue siendo idempotente; no hay intentos automáticos. [Procedimiento y límites (inglés)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.6.0: System Updater 1.2.0 sirve para una instalación nueva admitida o la sustitución verificada de 1.1.0/1.1.1 con `cytv replace-system-updater --edition root`. Solo cambia System Updater; se conservan las apps Root/Root Updater, el perfil completo y la elección de Home, y se archiva el estado anterior. Las operaciones desconocidas o incompletas detienen el cambio. El 1.1.2 instalado sigue fijado con sus canales antiguos; no hay migración general y no debe forzarse la sustitución. Esto no condiciona los canales No-root. [Procedimiento (inglés)](../RECOVERY.md#replace-the-root-system-updater-candidate)

## Ayuda y más instrucciones

**1.6.0:** elige **Revisar opciones de recuperación** para el mismo TV guardado o ejecuta `cytv recover`. La comprobación y los cambios requieren confirmaciones separadas con No predeterminado; `--yes` no los autoriza. Root continúa solo tras las verificaciones existentes. No-root ofrece eliminar solo si lo permite la comprobación del servicio de paquetes; se pueden restablecer las preferencias de Home. No se inicia otra instalación automáticamente. Ante estado desconocido o acceso denegado, guarda el informe y detente. Conserva los registros y no repitas la eliminación. Siguen pendientes las pruebas de finalización de #201 y la recuperación real de #216. [Recovery](../RECOVERY.md). Para pedir ayuda, indica modelo, firmware, edición, versión del instalador, paso fallido y resultado esperado/real; revisa y elimina secretos del informe antes de compartirlo.

1.7.0: la recuperación puede continuar una eliminación No-root detenida antes de la primera solicitud de paquete sin acceso al estado global, si el registro original lo demuestra. Confirma la eliminación por separado; tras verificarla, inicia la instalación aparte. Las operaciones desconocidas o ya enviadas siguen bloqueadas. Conserva la conexión y los registros. No está en 1.6.0. [Detalles](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased).

[Documentación](../README.md) · [Informar de un problema](../FEEDBACK.md)

En desarrollo: si no se envió ninguna solicitud de eliminación de paquetes, un fallo ofrece **Revisar opciones de recuperación** con la misma conexión guardada del TV. La comprobación y la eliminación requieren confirmaciones separadas. Si el TV rechaza la consulta de estado de paquetes, la recuperación se detiene y ofrece un informe. El resumen `recovery` distingue la eliminación no iniciada, una operación heredada y operaciones de paquetes interrumpidas sin publicar el registro completo; no autoriza la recuperación.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="python-opcional-para-root-en-v110"></a>
<a id="bloqueo-de-firmware-lg-en-120"></a>
<a id="novedades-de-130-recuperación-guiada-de-escritorio"></a>
<a id="novedades-de-130--12"></a>
<a id="candidato-sin-publicar-instalar-root-mediante-homebrew"></a>
<a id="candidato-sin-publicar-recuperación-de-sonido-hdmi-root"></a>

<a id="temas-154"></a>

## Temas

En la vista previa de la próxima versión, **Ajustes de Home → Fondos de pantalla** muestra el fondo del tema activo, la capacidad detectada del TV y el modo actual. Auto elige una calidad compatible; 4K, 1080p e Imagen solo están disponibles si el tema los incluye. Si falla el vídeo, se muestra una imagen. Ajusta el oscurecimiento en pasos del 5 % o restablece los valores del tema. Classic y los temas sin fondo lo indican claramente.

Fondos personales en la vista previa de la próxima versión: abre Fondos en CYTV de escritorio, elige un JPG/PNG, ajusta el recorte e introduce la dirección privada del TV y el PIN de recepción de Home. CYTV prepara vídeo sin sonido localmente; ofrece 4K solo si el recorte tiene resolución suficiente. En el TV elige recibir desde CYTV o cargar desde el teléfono y escanea el QR en la misma red Wi-Fi. El teléfono envía una imagen normal de hasta 1920×1080, sin la capa de vídeo 4K nativa; la nitidez está limitada por la resolución de la interfaz del TV. Confirma el aviso antes de enviar y revisa y aplica en el TV. Las cargas personales se guardan y pueden volver a elegirse o eliminarse en Fondos. Cancelar o rechazar un archivo conserva el fondo anterior. Se requieren versiones compatibles del próximo Home/servicio y CYTV.

Vídeo propio en movimiento (vista previa de la próxima versión): en CYTV de escritorio → Fondos, elige MP4/MOV/MKV/WebM de 1–60 segundos, hasta 512 MiB y 3840×2160. Se elimina el sonido y se recorta al centro en 16:9. Los vídeos menores usan salida compatible de 1080p; UHD requiere un recorte de origen suficiente. Envía con dirección/PIN del TV y después revisa y aplica en el TV. Desde el teléfono solo JPG/PNG. Pendientes la validación del paquete final y las pruebas físicas en TV.

Fondos incluidos de la próxima versión: **Ajustes de Home → Fondos → Fondos incluidos → Black Hole**. Vídeo de **Xecutioner**, usado con permiso para uso no comercial y atribución. Confirmar otro tema activa su propio fondo; Black Hole y las cargas personales siguen disponibles. El flujo 4K continuo evita rebobinar en cada repetición y ofrece vídeo/imagen compatible como alternativa.

Android CYTV: **Configurar TV** · **Fondos de pantalla** · **Mantenimiento**. En el TV, abra los ajustes de Home → Fondos de pantalla → Subir desde el teléfono. Escanee el QR con la cámara, elija JPG/PNG y aplique el fondo en el TV. Desde el teléfono: imágenes de hasta 1920×1080, sin vídeo 4K nativo. Para 4K real, use CYTV en un ordenador.

1.7.0: **Ajustes → Temas**. **Classic**, **Liquid Glass**, **Ribbon** están integrados y no necesitan descargar el tema; Classic sigue como predeterminado. **Channel** es externo, desde showcase. En las pruebas de la galería: Elige el tema y **Conservar tema** antes de **20 segundos**. **Revertir**, Back o el tiempo agotado recuperan el anterior. Una prueba interrumpida inicia Home con Classic. Los temas integrados y descargados elegidos en la lista instalada se aplican y guardan al instante, sin temporizador. Esto incluye los recibidos del ordenador o instalados por URL. Solo Probar tema dentro de la galería inicia una prueba de 20 segundos.

1.7.0: **Classic**, **Liquid Glass** y **Ribbon** están integrados. **Alpine 1.4.4** pasa a la **galería de temas** como descarga. Una selección guardada de `builtin:alpine` vuelve a Classic con el aviso de recuperación visible existente; Home no descarga Alpine automáticamente ni lo sustituye por Liquid Glass. La versión 1.6.0 incluye Classic, Alpine y Ribbon.

Los temas instalados aparecen en una sola fila con desplazamiento horizontal. El tema activo siempre está primero y su tarjeta está resaltada. Usa Izquierda/Derecha para recorrer la fila.

La galería solo muestra temas no instalados en este TV. Classic, Liquid Glass, Ribbon y los descargados se ocultan, incluso si hay una versión más reciente. Al eliminar un tema vuelve a aparecer. Actualiza por URL o desde el ordenador.

Las tarjetas están integradas en Temas, junto a las categorías. La galería, la instalación por enlace y la transferencia desde el ordenador se abren ahí; solo una prueba de la galería muestra Home temporalmente.

Al abrir la galería o elegir Actualizar se consultan las novedades revisadas del repositorio principal sin actualizar Home ni recargar la página. Las nuevas entradas aparecen tras la integración normal; un candidato sin integrar puede mostrar el catálogo incluido. Sin conexión o ante errores se usan entradas y vistas previas incluidas. Los temas integrados corresponden a la versión instalada de Home. Abre la vista previa de Channel y elige **Descargar tema** (requiere internet). Tras descargarlo, pruébalo y elige **Conservar tema** en **20 segundos**. Los temas instalados funcionan sin conexión. **Añadir por ID** sigue disponible para enlaces fijados.

Para probar un tema no publicado, abre primero **Ajustes → Temas → Recibir del ordenador** en el TV. Introduce su dirección y PIN de seis dígitos en **Send to TV** de la vista previa del ordenador, envía y elige **Aplicar tema** en el TV. El método principal conecta desde el PC al puerto TCP **8879 del TV**, sin modificar el cortafuegos del ordenador. Ambos deben estar en la misma red doméstica de confianza. El receptor se cierra tras una carga, cancelar, salir o **10 minutos**. El PIN no se guarda; el tema instalado funciona sin conexión. No es necesario publicar en GitHub.

Para un tema publicado, abre **Añadir por ID** e introduce su ID (por ejemplo `102300a209`), `da.gd/102300a209` o el enlace completo de GitHub. Home muestra la dirección da.gd antes de cargar y verifica el destino GitHub y el paquete. El autor puede copiar el ID de las notas de versión o de **TV link → Copy ID** en la vista previa.

**1.6.0:** **Mostrar diagnóstico** en el panel Home Helper muestra un resumen filtrado de sus propias consultas de estado. Consultarlo no inicia Helper ni cambia el control de Home. Comparte solo ese JSON cuando se solicite, después de revisarlo; [detalles](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

Los temas de cinta configurable de 1.5.4 pueden colocar entradas, Wi-Fi y ajustes abajo a la izquierda. Si se activa, Izquierda desde la primera app visible selecciona ajustes, luego Wi-Fi y entradas; Derecha desde ajustes vuelve a la misma app visible. La instalación de un tema que exige una función nueva de Home se rechaza en versiones incompatibles, conservando el aspecto y la selección actuales. Actualiza Home primero. Un downgrade posterior puede restaurar Classic al iniciar.

Temas muestra vistas previas de los temas integrados y de todos los que hayas instalado, incluso sin conexión. Un botón aparte abre el catálogo de temas publicados; instalar un tema personal no lo publica.

Apariencia contiene Columnas con la cantidad actual y los controles de aplicaciones. La categoría Temas contiene los temas instalados, la galería, recibir del ordenador y Añadir por ID a la derecha (p. ej. 102300a209). Restaura Classic con su tarjeta y elimina descargas individualmente. Idioma permite elegir directamente.

En la vista previa del navegador, Recibir del ordenador explica los pasos del televisor; no inicia un receptor de TV en el ordenador. Usa Send to TV encima de la vista previa. Eliminar un tema descargado requiere confirmación; si está activo, se restaura Classic primero. Cancelar conserva el tema.

<a id="categorías-de-ajustes-candidato-no-publicado"></a>

## Categorías de ajustes (1.5.4)

Ambas ediciones muestran categorías a la izquierda y ajustes a la derecha: pantalla de inicio, Apariencia, Temas, Idioma, Actualizaciones de software y Avanzado. No-root añade Developer Mode; Root incluye el firmware LG en actualizaciones y sonido HDMI en Avanzado. Arriba/abajo recorre una columna; derecha entra en los ajustes e izquierda vuelve a las categorías. Atrás vuelve primero a las categorías y después cierra los ajustes. Tab también permite volver a Home.

Un punto amarillo en Actualizaciones de software y en el botón interior indica que hay una actualización. Ambos desaparecen cuando una comprobación correcta confirma que no hay actualizaciones; si falla, se conserva el último estado confirmado.

<a id="resolución-gráfica-automática-candidato"></a>

## Resolución gráfica automática (1.6.0)

Los instaladores 1.6.0 para ordenador/Android y clientes OTA migrados eligen 720p o 1080p según la capacidad del TV. Si no puede verificarse, la operación se detiene. Los actualizadores antiguos instalados por separado requieren la migración documentada desde el ordenador; la recuperación conserva sus paquetes originales.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** guarde el informe del intento fallido original. Los nuevos informes separan el primer error registrado de las comprobaciones posteriores e incluyen un resumen filtrado de Doctor/estado. También permiten exportar tras configurar, consultar el estado o restaurar correctamente. Los datos antiguos ausentes siguen siendo desconocidos; el informe no autoriza la recuperación. [↗](../development/INSTALLER-DIAGNOSTICS.md).

## Espacio de almacenamiento

Las compilaciones candidatas muestran espacio necesario, libre y faltante en MiB para instalar, añadir temas y fondos de foto/vídeo. Incluyen copias temporales y reserva. La cuota de la app, la caché de temas de 64 MiB y la de vídeo son límites distintos. Los valores desconocidos se indican. Libera el almacenamiento indicado; no hay limpieza automática.

Espacio estimado (TV): necesario 128.0 MiB; libre 96.0 MiB; faltan 32.0 MiB.
