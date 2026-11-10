---
lang: es
topic: change-lg-webos-home-screen
title: "Cómo cambiar la pantalla de inicio de un televisor LG webOS"
description: "Personaliza la pantalla de inicio de tu LG webOS con Clean Your TV. Descubre qué cambia un launcher, cómo elegir edición y qué comprobar antes de instalar."
updated: '2026-11-09'
---

Clean Your TV es una pantalla de inicio alternativa para televisores LG webOS. Permite ordenar las aplicaciones a tu gusto y ofrece temas y un dock personalizable. Tras la configuración se ejecuta en el televisor, así que puedes apagar el ordenador. La posibilidad de controlar el botón Home depende del televisor, el firmware, el mando y el método de instalación.

## ¿Qué puedes personalizar?

El launcher cambia la pantalla que utilizas para buscar y abrir aplicaciones del televisor. Puedes ordenar tus favoritas y elegir un diseño como Classic, Liquid Glass o Ribbon. Prueba la [demo en el navegador](/clean-your-tv-lg-webos/demo/) para comparar diseños antes de instalar nada. Los controles del televisor están simulados en la demo; no sirve para comprobar la compatibilidad con tu equipo.

Un launcher alternativo no sustituye el firmware de webOS, no desbloquea servicios de streaming de pago ni elimina la publicidad dentro de otras aplicaciones. Los ajustes de imagen, las entradas y los servicios de streaming siguen siendo partes independientes del televisor. Lee [qué cambia respecto a la publicidad](/clean-your-tv-lg-webos/es/articles/lg-tv-home-screen-ads/) si buscas sobre todo una pantalla de inicio más tranquila.

## ¿Qué método de instalación elegir?

Usa No-root en un televisor con LG Developer Mode activo. Su Home Helper, que se ejecuta en el televisor, controla el botón Home cuando es compatible. Developer Mode debe permanecer activo; si caduca la sesión, las aplicaciones instaladas mediante este modo pueden eliminarse.

Usa Root solo si el televisor ya tiene acceso root funcional y cumple los requisitos de entorno de ejecución y servicios. El instalador de Clean Your TV no obtiene acceso root. No actives Developer Mode sobre una instalación root existente ni uses ambos métodos de control de Home a la vez. La [guía de ediciones](/clean-your-tv-lg-webos/es/articles/root-vs-no-root/) explica las diferencias.

## Antes de cambiar una configuración que ya funciona

1. Anota el modelo exacto, el firmware, la versión de webOS y el tipo de mando. Compáralos con los [requisitos y resultados comunicados de televisores](/clean-your-tv-lg-webos/es/compatibility/); cada informe se refiere a la configuración que documenta.
2. Sigue la [guía de instalación](/clean-your-tv-lg-webos/es/install/) y utiliza el instalador publicado que enlaza. Durante la configuración, el televisor y el dispositivo de instalación deben estar en una red que les permita comunicarse.
3. Después, comprueba la apertura de aplicaciones y Home; prueba por separado el sonido, el reposo y la reanudación, y el arranque en frío. Instalar correctamente un paquete no verifica estos comportamientos.

## ¿Cómo volver a LG Home?

En las ediciones compatibles actuales, tres pulsaciones cortas de Home en dos segundos activan la salida de emergencia. Las versiones antiguas de Home Helper hasta la 0.6.13 utilizan una pulsación de Home de dos segundos. Abrir LG Home una vez y desactivar el control persistente de Home son acciones distintas; consulta las [instrucciones de recuperación](/clean-your-tv-lg-webos/es/help/#home-button) de la edición instalada. Mantén una vía de recuperación disponible antes de cambiar el comportamiento de inicio.

## Fuentes y próximos pasos

- [Referencia de ediciones y controles del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Instalación y requisitos del proyecto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: mantener disponible una instalación No-root](/clean-your-tv-lg-webos/es/articles/lg-developer-mode/)
