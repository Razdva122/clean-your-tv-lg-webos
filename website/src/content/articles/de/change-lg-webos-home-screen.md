---
lang: de
topic: change-lg-webos-home-screen
title: "So ändern Sie den Startbildschirm eines LG webOS TVs"
description: "Gestalten Sie den Startbildschirm Ihres LG webOS TVs mit Clean Your TV. Was ein Launcher verändert, welche Edition passt und was vor der Installation zu prüfen ist."
updated: '2026-11-09'
---

Clean Your TV ist ein alternativer Startbildschirm für LG webOS TVs. Sie können Ihre Apps nach Wunsch anordnen, Themes auswählen und das Dock anpassen. Nach der Einrichtung läuft alles auf dem Fernseher; den Computer können Sie ausschalten. Ob die Home-Taste den Launcher öffnen kann, hängt von Fernseher, Firmware, Fernbedienung und Installationsmethode ab.

## Was lässt sich anpassen?

Der Launcher verändert den Bildschirm, über den Sie TV-Apps suchen und öffnen. Ordnen Sie Ihre Favoriten an und wählen Sie ein Layout wie Classic, Liquid Glass oder Ribbon. Mit der [Browser-Demo](/clean-your-tv-lg-webos/demo/) können Sie die Layouts vor einer Installation vergleichen. Die TV-Bedienung wird in der Demo simuliert; die Kompatibilität mit Ihrem Fernseher lässt sich damit nicht testen.

Ein alternativer Launcher ersetzt weder die webOS-Firmware noch schaltet er kostenpflichtiges Streaming frei oder entfernt Werbung in anderen Apps. Bildeinstellungen, Eingänge und Streamingdienste bleiben eigenständige Bereiche Ihres Fernsehers. Wenn Sie vor allem einen ruhigeren Startbildschirm möchten, lesen Sie, [was sich bei der Werbung ändert](/clean-your-tv-lg-webos/de/articles/lg-tv-home-screen-ads/).

## Welche Installationsmethode passt?

Verwenden Sie No-root auf einem Fernseher mit aktivem LG Developer Mode. Der auf dem TV laufende Home Helper übernimmt die Home-Taste, soweit dies unterstützt wird. Developer Mode muss aktiv bleiben; abgelaufene Sitzungen können dazu führen, dass nachinstallierte Entwicklungs-Apps entfernt werden.

Verwenden Sie Root nur, wenn der Fernseher bereits einen funktionierenden Root-Zugang hat und die Laufzeit- und Dienstanforderungen erfüllt. Der Installer von Clean Your TV verschafft dem TV keinen Root-Zugang. Aktivieren Sie Developer Mode nicht zusätzlich zu einer bestehenden Root-Einrichtung und betreiben Sie nicht beide Methoden zur Home-Umleitung gleichzeitig. Der [Editionsvergleich](/clean-your-tv-lg-webos/de/articles/root-vs-no-root/) erklärt die Unterschiede.

## Bevor Sie Ihre funktionierende Einrichtung ändern

1. Notieren Sie das genaue Modell, die Firmware, die webOS-Version und den Fernbedienungstyp. Vergleichen Sie diese mit den [Anforderungen und gemeldeten TV-Ergebnissen](/clean-your-tv-lg-webos/de/compatibility/); jeder Bericht gilt für die darin dokumentierte Konfiguration.
2. Folgen Sie der [Installationsanleitung](/clean-your-tv-lg-webos/de/install/) und verwenden Sie den dort verlinkten veröffentlichten Installer. Während der Einrichtung müssen TV und Installationsgerät über das Netzwerk miteinander kommunizieren können.
3. Prüfen Sie nach der Einrichtung zuerst App-Start und Home, danach Ton, Standby mit Aufwecken und Kaltstart jeweils separat. Eine erfolgreiche Paketinstallation bestätigt diese Funktionen noch nicht.

## Wie kehren Sie zu LG Home zurück?

In den aktuell unterstützten Editionen lösen drei kurze Home-Tastendrücke innerhalb von zwei Sekunden den Notausstieg aus. Ältere Home-Helper-Versionen bis einschließlich 0.6.13 verwenden stattdessen ein zweisekündiges Halten der Home-Taste. LG Home einmal zu öffnen ist etwas anderes, als die dauerhafte Home-Umleitung zu deaktivieren. Nutzen Sie die [Wiederherstellungsanleitung](/clean-your-tv-lg-webos/de/help/#home-button) für Ihre installierte Edition. Halten Sie einen Wiederherstellungsweg bereit, bevor Sie das Startverhalten ändern.

## Quellen und nächste Schritte

- [Projektübersicht zu Editionen und Bedienung](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Installation und Voraussetzungen des Projekts](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: eine No-root-Einrichtung verfügbar halten](/clean-your-tv-lg-webos/de/articles/lg-developer-mode/)
