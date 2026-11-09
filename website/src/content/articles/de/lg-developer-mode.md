---
lang: de
topic: lg-developer-mode
title: "LG Developer Mode für einen No-root-Launcher auf webOS"
description: "Warum Clean Your TV No-root den LG Developer Mode benötigt, was ablaufende Sitzungen für Entwicklungs-Apps bedeuten und was bei einem verschwundenen Launcher zu prüfen ist."
updated: '2026-11-09'
---

Mit LG Developer Mode können Sie webOS-TV-Apps installieren und testen, ohne den Fernseher zu rooten. Clean Your TV No-root nutzt diesen Zugangsweg zusammen mit dem auf dem TV laufenden Home Helper. Die Developer-Mode-Sitzung ist zeitlich begrenzt: Prüfen Sie die verbleibende Zeit in LGs Developer-Mode-App und verlängern Sie die Sitzung vor Ablauf, damit Ihre nachinstallierte Einrichtung verfügbar bleibt.

## Was ermöglicht Developer Mode?

Developer Mode gewährt Entwicklungszugang. Er vergibt keine Root-Rechte und garantiert nicht, dass ein Helfer für die Home-Taste auf jedem Modell funktioniert. Clean Your TV prüft weiterhin die Anforderungen an Laufzeitumgebung und Eingabeverarbeitung. Normale Store-Apps, nachinstallierte Entwicklungs-Apps und ein gerootetes System nutzen unterschiedliche Zugangswege.

Verwenden Sie No-root nur mit einer geeigneten Developer-Mode-Einrichtung. Ist der TV bereits gerootet, aktivieren Sie Developer Mode nicht zusätzlich. Lesen Sie zuerst den [Vergleich Root und No-root](/clean-your-tv-lg-webos/de/articles/root-vs-no-root/) sowie die [Kompatibilitätsanforderungen](/clean-your-tv-lg-webos/de/compatibility/).

## Fernseher und Installationsgerät vorbereiten

Die genauen Schritte finden Sie in der [aktuellen Installationsanleitung](/clean-your-tv-lg-webos/de/install/). Sie benötigen LGs Developer-Mode-App, die erforderliche Anmeldung bei LG Developer und den Key Server für die Kopplung. Fernseher und Computer oder unterstütztes Android-Gerät müssen über das Netzwerk miteinander kommunizieren können. Ein Gastnetz oder eine Client-Isolierung kann die Einrichtung verhindern, selbst wenn beide Geräte Internetzugang haben.

Bewahren Sie Kopplungsschlüssel und Verbindungsdaten vertraulich auf. Verwenden Sie den veröffentlichten Installer aus der Anleitung; ein beliebiger IPK-Download ist noch keine vollständige Home-Einrichtung. Nach Abschluss der Installation laufen Launcher und Helper auf dem Fernseher. Der Computer kann ausgeschaltet werden.

## Die Sitzung aktiv halten

Öffnen Sie LGs Developer-Mode-App, prüfen Sie die verbleibende Sitzungszeit und verlängern Sie sie, solange die erforderliche Verbindung besteht. Folgen Sie LGs aktuellen Anweisungen, statt sich auf eine feste Stundenanzahl aus einem älteren Artikel zu verlassen. Ein Verlängerungsversuch beweist keinen Erfolg: Kontrollieren Sie anschließend die angezeigte Restzeit.

Clean Your TV bietet eine optionale automatische Verlängerung als Beta-Funktion an, die standardmäßig ausgeschaltet ist. Wenn Sie sie aktivieren, prüfen Sie weiterhin den tatsächlichen Developer-Mode-Status. Sie hebt LGs Sitzungsanforderungen nicht auf und macht einen deaktivierten Modus nicht dauerhaft aktiv.

## Was tun, wenn der Launcher verschwindet oder Home LG Home öffnet?

Prüfen Sie Developer Mode, bevor Sie wiederholt neu installieren. LG dokumentiert, dass beim Deaktivieren oder Ablauf von Developer Mode Entwicklungs-Apps deinstalliert werden können. Eine abgelaufene Sitzung ist etwas anderes als ein Notstopp des Home Helpers, ein Kopplungsproblem oder eine unterbrochene Installation.

Wurden Entwicklungs-Apps entfernt, stellen Sie Developer Mode gemäß Anleitung wieder her und nutzen Sie die geführte Einrichtung oder Wiederherstellung des Installers passend zum tatsächlichen Zustand. Sind die Apps noch vorhanden, aber die Home-Umleitung gestoppt, folgen Sie der [Hilfe zur Home-Taste](/clean-your-tv-lg-webos/de/help/#home-button). Bei unterbrochenen Vorgängen nutzen Sie die [Wiederherstellungsanleitung](/clean-your-tv-lg-webos/de/help/#interrupted), statt Systemdateien zu löschen. Prüfen Sie das Home-Verhalten nach der Wiederherstellung separat.

## Quellen und nächste Schritte

- [LG: Verwendung der Developer-Mode-App](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [No-root-Installationsanleitung des Projekts](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Wiederherstellungsreferenz des Projekts](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
