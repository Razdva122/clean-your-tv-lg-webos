# Clean Your TV — Benutzeranleitung

Der Installer fragt nach dem TV-Namen, Standard **Home**; CLI: `--tv-name "Aashiyaan"`. Nach einem Upgrade erscheint **Einstellungen → Home → TV-Name** automatisch. Dort lässt sich der Name jederzeit speichern oder auf Home zurücksetzen. Er bleibt bei Neustarts und unterstützten Updates erhalten; andere Einstellungen bleiben bestehen. Maximal 48 Zeichen. Gilt für Launcher und eigene Ladeanzeige, nicht den Netzwerknamen. Die frühere LG-Anzeige muss eventuell über den Installer geändert werden.

Noch unveröffentlichte Installer-Änderung: Vor einer neuen Installation prüft der Computer-Installer GitHub auf eine neuere stabile Version. Wähle „GitHub öffnen und die neueste Version herunterladen“, um anzuhalten und sie herunterzuladen, oder „Nein, diese Version installieren“, um ausdrücklich fortzufahren. Bei fehlgeschlagener Prüfung kannst du fortfahren. Ausstehende Vorgänge und Wiederherstellung überspringen die Prüfung.

Clean Your TV ist Ihr persönlicher Startbildschirm für LG webOS: Ihre Apps in Ihrer Reihenfolge, ohne Werbereihen in diesem Menü. Installieren Sie es mit einem Computer oder Android-Smartphone; danach kann der Computer ausgeschaltet bleiben.

## 1. Installer herunterladen

Klicken Sie auf das Bild für Ihr Gerät. Die Schaltflächen laden die neueste veröffentlichte Ausgabe herunter. Beim Mac wählen Sie Apple Silicon (M1 oder neuer) oder Intel; nachsehen unter Apple-Menü → Über diesen Mac.

[![Herunterladen — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Herunterladen — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Herunterladen — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Herunterladen — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Herunterladen — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="edition-wählen"></a>

<a id="voraussetzungen"></a>

## 2. Edition wählen

Schalten Sie den TV ein und verbinden Sie ihn und Ihren Computer oder Ihr Smartphone mit demselben Heimnetz. Erlauben Sie CYTV bei Nachfrage den Zugriff auf das lokale Netzwerk.

- **No-root** — wenn kein Root-Zugang vorhanden ist. Richten Sie Developer Mode wie unten beschrieben ein.
- **Root** — wenn Root-Zugang per SSH bereits vorhanden ist. Der Installer richtet keinen Root-Zugang ein. Aktivieren Sie auf diesem TV keinen Developer Mode; behalten Sie SSH-Zugang und Wiederherstellungsdaten.

Bei Root prüft und wählt der Installer eine verfügbare Methode zur Home-Steuerung. Kann die Kompatibilität nicht bestätigt werden, stoppt die Einrichtung; umgehen Sie die fehlgeschlagene Prüfung nicht.

**No-root → Root:** Wenn No-root nach einer vollständigen Entfernung erneut installiert wurde, kann vor dem Wechsel zu Root eine Bereinigung nötig sein. Sichern Sie die Home-Einstellungen, wählen Sie **Clean Your TV deinstallieren** mit der gespeicherten Root-Verbindung und warten Sie auf die bestätigte Entfernung. Dabei werden auch No-root Home und Helper entfernt. Installieren Sie danach Root und bewahren Sie die Wiederherstellungsdaten auf.

### Developer Mode einrichten (No-root)

Mit Developer Mode kann CYTV Apps auf einem TV ohne Root installieren.

1. Öffnen Sie am TV LG Apps, suchen Sie nach Developer Mode und installieren Sie die App.
2. Öffnen Sie Developer Mode und melden Sie sich mit Ihrem LG Developer-Konto an. Erstellen Sie bei Bedarf ein Konto unter [LG Developer](https://webostv.developer.lge.com).
3. Schalten Sie Dev Mode Status ein. Der TV startet neu. Öffnen Sie danach Developer Mode erneut.
4. Schalten Sie Key Server ein und lassen Sie Developer Mode geöffnet. Tragen Sie die dort angezeigte IP Address als TV-Adresse in CYTV ein.
5. Geben Sie die Passphrase ein: die sechs Zeichen, die Developer Mode am TV anzeigt. Beachten Sie Groß- und Kleinschreibung.

Verwenden Sie den Code vom TV, nicht das Passwort Ihres LG-Kontos. Wird kein Code angezeigt, schalten Sie Key Server ein.

Die Kopplung ist ein eigener Schritt: Bestätigen Sie CYTV mit der Fernbedienung, wenn der TV danach fragt.

Halten Sie Developer Mode aktiv: Öffnen Sie die App vor Ablauf des Timers und drücken Sie bei bestehender Internetverbindung EXTEND. Nach Ablauf kann LG diese Apps entfernen.

<a id="installation-und-sprache"></a>

## 3. Installer öffnen

- **Windows x64:** `cytv-windows-x64-desktop.zip` herunterladen, im Explorer **Alle extrahieren** wählen und `cytv-desktop/cytv-desktop.exe` öffnen. Den Ordner `_internal` daneben behalten.
- **macOS 13+:** `cytv-macos-arm64.zip` für Apple Silicon oder `cytv-macos-x64.zip` für Intel entpacken. `cytv.app` nach Programme verschieben und öffnen; Zugriff auf das lokale Netzwerk erlauben. Bei einer Sperre für einen vertrauenswürdigen Projekt-Download Datenschutz & Sicherheit → Dennoch öffnen verwenden. Gatekeeper nicht abschalten.
- **Linux x64:** Unter Ubuntu 22.04+, Debian 12+ oder Mint 21+ `cytv-linux-x64.deb` mit der grafischen Paketverwaltung installieren, dann Clean Your TV im Anwendungsmenü öffnen. Für Bibliotheken kann Internet nötig sein. Linux ARM wird nicht angeboten.

**Android ARM64:** Sie benötigen ein 64-Bit-ARM-Smartphone mit Android 7+ und WebView/Chrome 108+. Öffnen Sie die APK und erlauben Sie bei Nachfrage die Installation aus dieser Quelle. Öffnen Sie CYTV; die Sprachauswahl ist oben rechts. Aktualisieren Sie ohne Deinstallation oder Datenlöschung.

Der Desktop-Assistent verwendet zunächst die Systemsprache und speichert eine ausdrückliche Auswahl. Am Fernseher unter **Einstellungen → Sprache** die gewünschte Sprache oder die automatische Systemauswahl wählen. Die Spracheinstellungen von Installer und Fernseher sind unabhängig. Alle Sprachcodes stehen im [Sprachverzeichnis](../LANGUAGES.md).

## 4. Auf dem Fernseher installieren

1. Wählen Sie in CYTV **TV einrichten**. Wählen Sie am Computer einen gefundenen TV; unter Android geben Sie seine IP-Adresse ein. Falls die Suche nichts findet, geben Sie die Adresse manuell ein.
2. Wählen Sie **No-root** oder **Root** und prüfen Sie vor dem Fortfahren den gewählten TV.
3. No-root: Geben Sie den Code aus Developer Mode ein und bestätigen Sie die Anfrage am TV. Root: Verwenden Sie Ihren SSH-Zugang. Bestätigen Sie eine neue SSH-Identität nur für Ihren eigenen TV im vertrauenswürdigen Netz. Bei einem geänderten gespeicherten Schlüssel stoppen und die Ursache klären.
4. Folgen Sie dem Assistenten. Lassen Sie TV und CYTV eingeschaltet und wechseln Sie bis zum Abschluss nicht das Netzwerk. Beenden Sie die Android-App nicht zwangsweise. Root aktiviert die Home-Steuerung direkt nach Vorbereitung der Wiederherstellung.

In der veröffentlichten Version wird die Root-Einrichtung mit einer Warnung fortgesetzt, wenn TV-Eingänge nicht gelesen werden können, die Anwendungsliste aber gültig ist. Eingänge können in Home fehlen; eine fehlerhafte oder leere Anwendungsliste stoppt die Einrichtung weiterhin. Speichern Sie bei wiederholter Warnung den Diagnosebericht.

## 5. Fernbedienung prüfen

1. Öffnen Sie eine andere TV-App und drücken Sie kurz **Home**. Clean Your TV sollte erscheinen. Geben Sie im Assistenten Ihre Beobachtung an; überspringen Sie den Test, wenn Sie ihn nicht durchgeführt haben.
2. Prüfen Sie Pfeile, OK, Zurück, Lautstärke und Ton. Prüfen Sie Bereitschaft/Aufwachen und einen Start nach Trennung vom Strom separat. Eine erfolgreiche Installation allein prüft diese Funktionen nicht.

<a id="bedienung-und-wiederherstellung"></a>

## 6. Bedienung und Wiederherstellung

IR-Unterstützung für No-root: Nach kurzem Drücken und Loslassen von Home wird Clean nach etwa 700 ms geöffnet; LG Home kann zuerst aufblitzen. Langes Home bleibt bei webOS; dreimal Home stoppt weiterhin Helper. Der Zugriff mit normalem Developer Mode ist unbestätigt; ändern Sie keine Eingabegeräteberechtigungen.

Pfeile wählen eine Kachel, OK öffnet sie; OK gedrückt halten zum Verschieben. Kurzes Zurück behält Navigation und Beendigungsdialog der App bei. Kurzes Home öffnet bei aktiver Home-Steuerung den Launcher. Zurück 1,2 Sekunden gedrückt halten, um LG Home einmalig zu öffnen. Der Home-Schalter und Ihre Einstellungen bleiben unverändert.

**Home innerhalb von zwei Sekunden dreimal kurz drücken**, dazwischen loslassen. Dies stellt LG Home wieder her und stoppt die Steuerung, ohne Einstellungen zurückzusetzen.

No-root: Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten. Root: **Home ändern** in den Home-Einstellungen einschalten, um fortzufahren. **LG Home öffnen** öffnet LG Home einmalig, ohne das Home-Ziel zu ändern. Für LG Home als dauerhaftes Ziel **Home ändern** ausschalten. Beide Steuerungen nie gleichzeitig betreiben. Bei wiederholtem Fehler LG Home aktiv lassen.

Ein Update startet einen gestoppten No-root Helper nicht neu. Starten Sie ihn ausdrücklich wie oben beschrieben; löschen Sie keine Stoppmarkierungen manuell.

## Brauchen Sie Hilfe?

Bei `ssh-identity-changed` nach einem Reset oder einer SSH-Änderung stoppen: CYTV blockiert den geänderten gespeicherten Schlüssel vor der Anmeldung. Die erstmalige Vertrauensabfrage ersetzt ihn nicht; eine ausstehende Deinstallation erklärt die Abweichung nicht. Ursprüngliches Profil, Schlüssel und Wiederherstellungsdaten behalten. Es gibt keinen unterstützten automatischen Befehl zum erneuten Vertrauen. TV-Identität/Fingerabdruck müssen unabhängig geprüft werden; anschließend ist ein geprüftes Verfahren unter Erhalt des Profils nötig: [Wiederherstellung bei geänderter SSH-Identität](../RECOVERY.md#ssh-identity-changed).

Nach einer unterbrochenen Installation verwenden Sie dieselbe gespeicherte Verbindung und zuerst **TV-Status prüfen**. Fahren Sie nur mit der vom Assistenten angebotenen Wiederherstellung fort. Bei unbekanntem Zustand Diagnosebericht speichern und stoppen; Wiederherstellungsdaten behalten und nicht blind neu installieren.

Lassen Sie während der Wiederherstellung die Home-Steuerung ausgeschaltet und bewahren Sie die ursprünglichen Diagnoseberichte und die gespeicherte Verbindung auf. Bestätigen Sie Prüfung und Änderungen getrennt. Folgen Sie der ausführlichen Anleitung für Ihre installierte Version; erzwingen Sie keine Neuinstallation und löschen Sie keinen Wiederherstellungszustand.

Nennen Sie TV-Modell, Firmware, No-root oder Root, Installationsgerät, Schritt und Fehlermeldung. Entfernen Sie vor dem Teilen Passwörter, Schlüssel, Adressen und persönliche Daten. Berichte werden nicht automatisch veröffentlicht.

[Problem melden](../FEEDBACK.md) · [Wiederherstellung — Englisch](../RECOVERY.md) · [Aktualisieren oder entfernen — Englisch](../MAINTENANCE.md) · [Andere Sprachen](../LANGUAGES.md)

### Einfache Entfernung

Unter Wartung **Clean Your TV deinstallieren** mit derselben gespeicherten TV-Verbindung wählen. Einmal bestätigen. Vorhandene bekannte Projekt-Apps und Dateien werden entfernt, fehlende übersprungen, auch nach einer Teilinstallation.

Bei älteren TVs ohne eigene LG-Home-App kann die No-root-Entfernung zu Live TV wechseln. Lassen Sie den TV eingeschaltet und führen Sie einen angeforderten Neustart aus; löschen Sie keine Wiederherstellungsdaten und setzen Sie den TV nicht zurück.

Wenn aufgefordert, den TV vom Strom trennen, wieder anschließen, auf das Netzwerk warten und **Erneut versuchen** wählen. Standby oder Quick Start ist kein vollständiger Neustart; CYTV startet den TV nicht automatisch neu. Bei Verbindungsabbruch Verbindung prüfen und dasselbe Entfernen erneut versuchen, ohne weiteren Wiederherstellungsassistenten. Bei verweigertem Zugriff die angeforderte Root-Verbindung verwenden; bei beschäftigtem TV warten und erneut versuchen. Erfolg erscheint erst nach bestätigter abschließender Bereinigung. Schlüssel und Originalberichte behalten. Notfallsteuerung und Zustimmung zum Teilen gelten weiter.

Eine fehlgeschlagene oder unterbrochene Einrichtung bietet direkt die Wiederherstellung an. Kann No-root nicht fortgesetzt werden, bestätigen Sie die vollständige Entfernung einmal. Bei vorübergehendem Verbindungsverlust oder einem beschäftigten CYTV-Prozess erfolgen bis zu drei Versuche. Wählen Sie bei erforderlichem Root-Zugriff **Mit Root verbinden** für denselben TV; die verifizierte Root-Bereinigung beendet auch dessen blockierte No-root-Entfernung. Nach einem Root-Aktivierungsfehler versucht CYTV, LG Home wiederherzustellen und zu prüfen, ohne erneut zu aktivieren. Ein Abbruch mit unerledigter Arbeit behält Bericht und Wiederherstellungsaktionen. Der Notstopp bleibt erhalten.

Öffnen Sie nach einem Verbindungsfehler beim Entfernen die Verbindungsdetails, prüfen Sie das Netzwerk oder wählen Sie einen vorhandenen Root-SSH-Schlüssel und versuchen Sie es erneut. TV-Adresse, Edition, Port und Hostschlüsselprüfung bleiben fest. No-root prüft Helper vor dem Pairing: stoppen Sie ihn und bestätigen Sie die erneute Prüfung im selben Ablauf. Nur ein nachweislich leerer TV ohne offene Einrichtung kann den Neustart überspringen; nach tatsächlichem Entfernen bleibt der angeforderte Neustart nötig. Bei Fehlern des Eingangsdiensts geht die sichere Paketbereinigung weiter; Erfolg erfordert weiterhin die bestätigte Verknüpfungsbereinigung.

**Root neu installieren:** Wählen Sie mit der gespeicherten Verbindung **Meinen Fernseher einrichten → Root** und bestätigen Sie **Root neu installieren?**. Der Installer stellt LG Home wieder her und entfernt Clean Your TV samt Updatern, Home Helper und gespeicherten Einstellungen vollständig. Nach verifizierter Entfernung installiert und aktiviert er die enthaltenen Pakete und die Root-Laufzeit. Andere TV-Apps und bestehender Root-/SSH-Zugriff bleiben erhalten. Stoppt die Entfernung oder wird ein vollständiger Neustart verlangt, schließen Sie sie vor einer erneuten Einrichtung ab. **Clean Your TV deinstallieren** allein startet keine neue Installation.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="optionales-python-für-root-in-v110"></a>
<a id="lg-firmware-sperre-in-120"></a>
<a id="neu-in-130-geführte-desktop-wiederherstellung"></a>
<a id="neu-in-130--12"></a>
<a id="unveröffentlichter-kandidat-root-über-homebrew-einrichten"></a>
<a id="unveröffentlichter-kandidat-hdmi-ton-wiederherstellen-root"></a>
<a id="designs-154"></a>
<a id="einstellungskategorien-unveröffentlichter-kandidat"></a>
<a id="automatische-grafikauflösung-kandidat"></a>
<a id="aktualisierung-und-entfernung"></a>
<a id="hilfe-und-weitere-anleitungen"></a>
<a id="designs"></a>
<a id="einstellungskategorien-154"></a>
<a id="automatische-grafikauflösung-160"></a>
<a id="speicherplatz"></a>

Ausführliche Referenzen auf Englisch: [Voraussetzungen](../COMPATIBILITY.md) · [Bedienung](../CONTROLS.md) · [Designs](../THEMES.md) · [Updates](../UPDATES.md).

<a id="unreleased-kandidat-älteres-tv-nodejs"></a>
<a id="älteres-tv-nodejs-veröffentlicht-in-v1120"></a>
<a id="einfache-entfernung-v1110"></a>

## Wetter

Öffnen Sie Einstellungen → Wetter unter Hintergrundbilder. Schalten Sie das Wetter ein und suchen Sie unter Stadt nach dem richtigen Ort mit Region und Land. Automatisch ermittelt einen ungefähren Ort anhand der Internetverbindung. Ein VPN kann das Ergebnis verändern; verwenden Sie bei fehlendem oder falschem Ort die manuelle Suche. Der erkannte oder gewählte Ort wird angezeigt. Wählen Sie °C / m/s oder °F / mph sowie ein verfügbares Format: kompakt, aktuell, ausführlich oder vier Tage. Die Vorschau folgt dem Design; Beispiel kennzeichnet Musterdaten. Liquid Glass unterstützt nur kompakt. Ribbon und Atmosphere zeigen kein Wetter. Ausschalten beendet Anfragen und blendet Stadt, Einheiten und Format aus; die Quellenauswahl bleibt verfügbar. Bei einer Störung bleiben aktuelle Daten kurz erhalten; nach längerer Zeit wird das Wetter bis zur Aktualisierung ausgeblendet.

Wählen Sie die Vorhersagequelle: Auto, MET Norway oder Open-Meteo. Auto beginnt mit MET Norway, versucht bei einem Fehler einmal Open-Meteo und verwendet danach die zuletzt erfolgreiche Quelle und deren Cache. Eine manuelle Auswahl wechselt die Quelle nie automatisch. Neue Einstellungen verwenden Auto; ältere gespeicherte Einstellungen ohne Quelle behalten Open-Meteo. Die tatsächliche Quelle wird angezeigt. Die Verfügbarkeit hängt vom Netzwerk ab. MET aktualisiert höchstens alle drei Stunden; der Cache verfällt nach sechs Stunden. Fehlende Werte werden ausgeblendet: MET liefert keine gefühlte Temperatur oder Niederschlagswahrscheinlichkeit. Tagesbereiche fassen Vorhersagepunkte zusammen, keine gemessenen Extremwerte.

Vorhersagekoordinaten gehen an api.met.no oder api.open-meteo.com, Stadtsuchen an geocoding-api.open-meteo.com. Die optionale automatische Ortssuche übermittelt die öffentliche IP an get.geojs.io. Alle Verbindungen nutzen HTTPS; ein API-Schlüssel ist nicht nötig. Ort, Quelle und Cache bleiben auf dem Fernseher. Datenquellen enthält Bedingungen und Urheberangaben, darunter das Norwegische Meteorologische Institut (MET Norway, CC BY 4.0).

Die Schaltfläche Datenquellen in der Wetterüberschrift öffnet Informationen zu Diensten und Lizenzen.
