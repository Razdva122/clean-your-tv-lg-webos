---
lang: es
topic: root-vs-no-root
title: "Root frente a No-root para un launcher LG webOS"
description: "Elige la edición de Clean Your TV adecuada para tu LG webOS. Compara requisitos de acceso, mantenimiento de Developer Mode, control de Home y recuperación."
updated: '2026-11-09'
---

Elige No-root si tu televisor LG utiliza Developer Mode. Elige Root solo si ya tiene acceso root funcional y servicios compatibles. Ambas ediciones de Clean Your TV ofrecen la misma interfaz de inicio y se ejecutan en el televisor después de la instalación. El instalador no obtiene acceso root ni instala firmware.

## ¿Qué necesita No-root?

No-root utiliza LG Developer Mode, Key Server y emparejamiento local durante la configuración. Home Helper se ejecuta en el televisor y controla el botón Home cuando el dispositivo y el firmware lo permiten. No hace falta dejar encendido un ordenador o un teléfono para el uso diario.

El requisito continuo es Developer Mode: amplía su sesión antes de que caduque. LG advierte de que las aplicaciones instaladas mediante Developer Mode pueden eliminarse al desactivarlo o al caducar la sesión. La renovación automática del proyecto es una opción beta desactivada de forma predeterminada; no la consideres una garantía. Lee la [guía de Developer Mode](/clean-your-tv-lg-webos/es/articles/lg-developer-mode/) antes de depender de esta edición.

## ¿Qué necesita Root?

Root utiliza un acceso SSH root ya existente, servicios de TV compatibles y capacidades de entrada y ejecución admitidas. Tener root no demuestra por sí solo la compatibilidad. El instalador comprueba el entorno; no ignores un requisito rechazado ni sustituyas los entornos de ejecución del sistema para forzar la comprobación.

Root tiene paquetes y control de Home independientes. No actives Developer Mode sobre una instalación root existente y detén Home Helper de No-root antes de utilizar el control de Root. Elegir edición depende del acceso que ya tienes, no de pulsar un botón que vaya a obtener root en el televisor.

## Compara el mantenimiento y la recuperación

- **Uso diario:** ambas ediciones se ejecutan en el televisor, con aplicaciones y temas en el launcher.
- **Mantenimiento de No-root:** mantén activo Developer Mode y conserva el emparejamiento y la conectividad necesarios para Helper.
- **Mantenimiento de Root:** mantén disponibles los servicios de recuperación independientes y el entorno de ejecución que necesitan. La disponibilidad de actualizaciones depende de la edición instalada y de la vía de actualización admitida; tener root no habilita por sí solo OTA.
- **Salida de emergencia:** las ediciones compatibles actuales usan tres pulsaciones cortas de Home en dos segundos. Home Helper hasta la versión 0.6.13 utiliza en cambio una pulsación de dos segundos.

Tras una parada de emergencia, reactivar el control persistente requiere una acción explícita. En No-root, abre Home Helper y elige «Start Helper»; en Root, usa «Change Home» en los ajustes de Home. Consulta la [comparación de ediciones](/clean-your-tv-lg-webos/es/editions/) y la [ayuda de recuperación](/clean-your-tv-lg-webos/es/help/#home-button).

## Comprueba tu televisor antes de instalar

Lee la [página de compatibilidad](/clean-your-tv-lg-webos/es/compatibility/) con el modelo exacto, firmware, webOS y mando a mano. Los resultados comunicados corresponden a una configuración específica. Prueba Home, la apertura de aplicaciones, el sonido, el reposo y el arranque en frío por separado después de configurar. Instalar un paquete no demuestra que todo ello funcione.

Utiliza el [instalador publicado y la guía de instalación](/clean-your-tv-lg-webos/es/install/). Si ya tienes una configuración que funciona y quieres cambiar de edición, sigue los pasos documentados de transición y eliminación en lugar de instalar una encima de la otra.

## Fuentes y próximos pasos

- [Comparación de ediciones del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Requisitos y límites conocidos del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Qué cambia una pantalla de inicio diferente](/clean-your-tv-lg-webos/es/articles/change-lg-webos-home-screen/)
