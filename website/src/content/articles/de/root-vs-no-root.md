---
lang: de
topic: root-vs-no-root
title: "Root oder No-root für einen LG-webOS-Launcher"
description: "Wählen Sie die passende Clean Your TV Edition für Ihren LG webOS TV. Vergleichen Sie Zugang, Developer-Mode-Pflege, Home-Steuerung und Wiederherstellung vor der Installation."
updated: '2026-11-09'
---

Wählen Sie No-root, wenn Ihr LG TV Developer Mode verwendet. Wählen Sie Root nur, wenn bereits ein funktionierender Root-Zugang und kompatible Dienste vorhanden sind. Beide Clean Your TV Editionen bieten dieselbe Home-Oberfläche und laufen nach der Installation auf dem Fernseher. Der Installer verschafft keinen Root-Zugang und spielt keine Firmware auf.

## Was benötigt No-root?

No-root nutzt während der Einrichtung LG Developer Mode, Key Server und lokale Kopplung. Home Helper läuft auf dem Fernseher und übernimmt die Home-Taste, soweit Gerät und Firmware dies unterstützen. Für den täglichen Betrieb muss kein Computer oder Smartphone eingeschaltet bleiben.

Dauerhaft erforderlich ist Developer Mode: Verlängern Sie die Sitzung vor ihrem Ablauf. LG weist darauf hin, dass über Developer Mode installierte Apps beim Deaktivieren oder Ablauf entfernt werden können. Die automatische Verlängerung des Projekts ist eine optionale Beta-Funktion und standardmäßig aus; betrachten Sie sie nicht als Garantie. Lesen Sie die [Developer-Mode-Anleitung](/clean-your-tv-lg-webos/de/articles/lg-developer-mode/), bevor Sie sich auf diese Edition verlassen.

## Was benötigt Root?

Root verwendet bestehenden SSH-Zugang mit Root-Rechten, kompatible TV-Dienste und unterstützte Eingabe- und Laufzeitfunktionen. Root-Zugang allein belegt keine Kompatibilität. Der Installer prüft die Umgebung. Umgehen Sie keine abgelehnte Voraussetzung und ersetzen Sie keine Systemlaufzeiten, um eine Prüfung zu erzwingen.

Root verwendet eigene Pakete und eine eigene Home-Umleitung. Aktivieren Sie Developer Mode nicht zusätzlich zu einer bestehenden Root-Einrichtung und stoppen Sie den No-root Home Helper, bevor Sie die Root-Umleitung verwenden. Bei der Editionswahl geht es um den bereits vorhandenen Zugang, nicht um eine Schaltfläche, die den Fernseher rootet.

## Wartung und Wiederherstellung im Vergleich

- **Tägliche Nutzung:** Beide Editionen laufen auf dem TV und bieten Apps und Themes im Launcher.
- **Pflege bei No-root:** Halten Sie Developer Mode aktiv und erhalten Sie die für den Helper erforderliche Kopplung und Verbindung.
- **Pflege bei Root:** Halten Sie unabhängige Wiederherstellungsdienste und deren benötigte Laufzeitumgebung verfügbar. Die Verfügbarkeit von Updates hängt von installierter Edition und unterstütztem Updateweg ab; Root-Zugang allein aktiviert keine OTA-Updates.
- **Notausstieg:** Aktuell unterstützte Editionen nutzen drei kurze Home-Tastendrücke innerhalb von zwei Sekunden. Home Helper bis einschließlich 0.6.13 verwendet stattdessen zweisekündiges Halten.

Nach einem Notstopp muss die dauerhafte Umleitung ausdrücklich neu gestartet werden. Öffnen Sie bei No-root Home Helper und wählen Sie „Start Helper“; bei Root verwenden Sie „Change Home“ in den Home-Einstellungen. Siehe [Editionsvergleich](/clean-your-tv-lg-webos/de/editions/) und [Wiederherstellungshilfe](/clean-your-tv-lg-webos/de/help/#home-button).

## Fernseher vor der Installation prüfen

Lesen Sie die [Kompatibilitätsseite](/clean-your-tv-lg-webos/de/compatibility/) mit den genauen Angaben zu Modell, Firmware, webOS und Fernbedienung. Gemeldete Ergebnisse beziehen sich auf eine bestimmte Konfiguration. Testen Sie nach der Einrichtung Home, App-Start, Ton, Standby und Kaltstart jeweils separat. Eine Paketinstallation beweist nicht, dass alle diese Funktionen arbeiten.

Verwenden Sie den [veröffentlichten Installer und die Installationsanleitung](/clean-your-tv-lg-webos/de/install/). Wenn Sie bereits eine funktionierende Einrichtung haben und die Edition wechseln möchten, folgen Sie den dokumentierten Wechsel- und Entfernungsschritten, statt eine Edition über die andere zu installieren.

## Quellen und nächste Schritte

- [Editionsvergleich des Projekts](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Anforderungen und bekannte Einschränkungen des Projekts](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Was ein anderer Startbildschirm verändert](/clean-your-tv-lg-webos/de/articles/change-lg-webos-home-screen/)
