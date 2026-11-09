---
lang: es
topic: lg-developer-mode
title: "LG Developer Mode para un launcher webOS No-root"
description: "Por qué Clean Your TV No-root necesita LG Developer Mode, cómo afecta la caducidad de la sesión a las aplicaciones instaladas y qué revisar si desaparece el launcher."
updated: '2026-11-09'
---

LG Developer Mode permite instalar y probar aplicaciones para televisores webOS sin obtener acceso root. Clean Your TV No-root utiliza este método de acceso junto con Home Helper, que se ejecuta en el televisor. Developer Mode tiene una sesión limitada: consulta el tiempo restante en la aplicación Developer Mode de LG y amplíalo antes de que caduque para mantener disponible tu instalación.

## ¿Qué permite Developer Mode?

Developer Mode proporciona acceso de desarrollo; no concede privilegios root ni garantiza que un asistente para el botón Home funcione en todos los modelos. Clean Your TV sigue comprobando los requisitos del entorno de ejecución y de entrada. Las aplicaciones de la tienda, las instaladas por vías de desarrollo y un sistema con root tienen formas de acceso distintas.

Utiliza No-root solo con una configuración de Developer Mode adecuada. Si el televisor ya tiene root, no actives Developer Mode sobre esa instalación. Lee primero [Root frente a No-root](/clean-your-tv-lg-webos/es/articles/root-vs-no-root/) y los [requisitos de compatibilidad](/clean-your-tv-lg-webos/es/compatibility/).

## Prepara el televisor y el dispositivo de instalación

Sigue la [guía de instalación actual](/clean-your-tv-lg-webos/es/install/) para conocer los pasos exactos. Necesitarás la aplicación Developer Mode de LG, el inicio de sesión de desarrollador de LG requerido y Key Server para el emparejamiento. El televisor y el ordenador o dispositivo Android compatible deben estar en una red donde puedan comunicarse. Una red de invitados o el aislamiento de clientes pueden impedir la configuración aunque ambos dispositivos tengan acceso a internet.

Mantén privadas las claves de emparejamiento y los datos de conexión. Utiliza el instalador publicado en la guía: descargar un IPK cualquiera no equivale a configurar completamente Home. Una vez terminada la instalación, el launcher y Helper se ejecutan en el televisor; puedes apagar el ordenador.

## Mantén activa la sesión

Abre la aplicación Developer Mode de LG, comprueba el tiempo restante y amplía la sesión mientras esté disponible la conexión necesaria. Sigue las instrucciones actuales de LG en lugar de confiar en un número fijo de horas citado en un artículo antiguo. Intentar renovar no demuestra que haya funcionado: comprueba después el tiempo restante que aparece en pantalla.

Clean Your TV ofrece la renovación automática opcional como función beta, desactivada de forma predeterminada. Si la activas, sigue comprobando el estado real de Developer Mode. No elimina los requisitos de sesión de LG ni convierte un modo desactivado en permanente.

## ¿Y si desaparece el launcher o Home abre LG Home?

Comprueba Developer Mode antes de reinstalar repetidamente. LG documenta que desactivar Developer Mode o dejar que caduque su sesión puede desinstalar las aplicaciones de desarrollo. Una sesión caducada no es lo mismo que una parada de emergencia de Home Helper, un problema de emparejamiento o una instalación interrumpida.

Si se han eliminado las aplicaciones de desarrollo, restaura Developer Mode según la documentación y utiliza la configuración guiada o la recuperación del instalador que corresponda al estado real. Si las aplicaciones siguen instaladas pero el control de Home está detenido, sigue la [ayuda del botón Home](/clean-your-tv-lg-webos/es/help/#home-button). Para trabajos interrumpidos, usa la [guía de recuperación](/clean-your-tv-lg-webos/es/help/#interrupted) en lugar de borrar archivos del sistema. Verifica por separado el comportamiento de Home después de recuperar la instalación.

## Fuentes y próximos pasos

- [LG: uso de la aplicación Developer Mode](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [Guía de instalación No-root del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Referencia de recuperación del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
