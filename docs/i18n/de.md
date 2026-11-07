# Clean Your TV — Benutzeranleitung

Clean Your TV ist Ihr persönlicher Startbildschirm für LG webOS: Ihre Apps in Ihrer Reihenfolge, ohne Werbereihen in diesem Menü. Installieren Sie es mit einem Computer oder Android-Smartphone; danach kann der Computer ausgeschaltet bleiben.

## UNRELEASED-Kandidat: älteres TV-Node.js

Diese Optionen gehören zu einem unveröffentlichten Kandidaten, nicht zu den veröffentlichten Downloads. Wenn reguläres Root die TV-Node.js-Version ablehnt (Node.js 8+ erforderlich), kann der Installer **No-root über vorhandenes Root-SSH** anbieten: Home und Home Helper ohne Installation von Developer Mode. Aktivieren Sie Developer Mode niemals bei bestehendem Root. Nur bei **exakt Node.js 0.12.2** ist zusätzlich **Root Beta** mit separaten Paketen und ausdrücklicher Bestätigung verfügbar. System-Node.js wird nicht ersetzt; automatische/OTA-Updates sind nicht verfügbar. Verwenden Sie den Computer-Installer. No-root hat einen eingeschränkten Funktionsumfang: keine systemweite Home-Umleitung und keine Root-exklusive Steuerung. Root Beta wurde auf TVs nicht ausreichend getestet.

Alle übrigen Anforderungen an native Komponenten, Home-Schnittstellen und Python bleiben verbindlich. Physische Tests unter Aufsicht des Besitzers stehen noch aus; dies ist keine Kompatibilitätszusage. Speichern Sie den Diagnosebericht, kennzeichnen Sie ungetestete Prüfungen und teilen Sie freiwillig ein bereinigtes Ergebnis manuell nach dem [Feedback-Leitfaden](../FEEDBACK.md). Nichts wird automatisch veröffentlicht.

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

Im nächsten unveröffentlichten Kandidaten wird die Root-Einrichtung mit einer Warnung fortgesetzt, wenn TV-Eingänge nicht gelesen werden können, die Anwendungsliste aber gültig ist. Eingänge können in Home fehlen; eine fehlerhafte oder leere Anwendungsliste stoppt die Einrichtung weiterhin. Speichern Sie bei wiederholter Warnung den Diagnosebericht.

## 5. Fernbedienung prüfen

1. Öffnen Sie eine andere TV-App und drücken Sie kurz **Home**. Clean Your TV sollte erscheinen. Geben Sie im Assistenten Ihre Beobachtung an; überspringen Sie den Test, wenn Sie ihn nicht durchgeführt haben.
2. Prüfen Sie Pfeile, OK, Zurück, Lautstärke und Ton. Prüfen Sie Bereitschaft/Aufwachen und einen Start nach Trennung vom Strom separat. Eine erfolgreiche Installation allein prüft diese Funktionen nicht.

<a id="bedienung-und-wiederherstellung"></a>

## 6. Bedienung und Wiederherstellung

Pfeile wählen eine Kachel, OK öffnet sie; OK gedrückt halten zum Verschieben. Kurzes Zurück behält Navigation und Beendigungsdialog der App bei. Kurzes Home öffnet bei aktiver Home-Steuerung den Launcher. Zurück 1,2 Sekunden gedrückt halten, um LG Home einmalig zu öffnen. Der Home-Schalter und Ihre Einstellungen bleiben unverändert.

**Home innerhalb von zwei Sekunden dreimal kurz drücken**, dazwischen loslassen. Dies stellt LG Home wieder her und stoppt die Steuerung, ohne Einstellungen zurückzusetzen.

No-root: Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten. Root: **Home ändern** in den Home-Einstellungen einschalten, um fortzufahren. **LG Home öffnen** öffnet LG Home einmalig, ohne das Home-Ziel zu ändern. Für LG Home als dauerhaftes Ziel **Home ändern** ausschalten. Beide Steuerungen nie gleichzeitig betreiben. Bei wiederholtem Fehler LG Home aktiv lassen.

## Brauchen Sie Hilfe?

Bei `ssh-identity-changed` nach einem Reset oder einer SSH-Änderung stoppen: CYTV blockiert den geänderten gespeicherten Schlüssel vor der Anmeldung. Die erstmalige Vertrauensabfrage ersetzt ihn nicht; eine ausstehende Deinstallation erklärt die Abweichung nicht. Ursprüngliches Profil, Schlüssel und Wiederherstellungsdaten behalten. Es gibt keinen unterstützten automatischen Befehl zum erneuten Vertrauen. TV-Identität/Fingerabdruck müssen unabhängig geprüft werden; anschließend ist ein geprüftes Verfahren unter Erhalt des Profils nötig: [Wiederherstellung bei geänderter SSH-Identität](../RECOVERY.md#ssh-identity-changed).

Nach einer unterbrochenen Installation verwenden Sie dieselbe gespeicherte Verbindung und zuerst **TV-Status prüfen**. Fahren Sie nur mit der vom Assistenten angebotenen Wiederherstellung fort. Bei unbekanntem Zustand Diagnosebericht speichern und stoppen; Wiederherstellungsdaten behalten und nicht blind neu installieren.

Lassen Sie während der Wiederherstellung die Home-Steuerung ausgeschaltet und bewahren Sie die ursprünglichen Diagnoseberichte und die gespeicherte Verbindung auf. Bestätigen Sie Prüfung und Änderungen getrennt. Folgen Sie der ausführlichen Anleitung für Ihre installierte Version; erzwingen Sie keine Neuinstallation und löschen Sie keinen Wiederherstellungszustand.

Nennen Sie TV-Modell, Firmware, No-root oder Root, Installationsgerät, Schritt und Fehlermeldung. Entfernen Sie vor dem Teilen Passwörter, Schlüssel, Adressen und persönliche Daten. Berichte werden nicht automatisch veröffentlicht.

[Problem melden](../FEEDBACK.md) · [Wiederherstellung — Englisch](../RECOVERY.md) · [Aktualisieren oder entfernen — Englisch](../MAINTENANCE.md) · [Andere Sprachen](../LANGUAGES.md)

In kommenden Builds erscheinen bei ausgewähltem oder aktivem 4K der Hinweis und die Schaltfläche „HDMI-Vorschau deaktivieren“ nur bei Designs mit aktivierter Eingangsvorschau. Während der HDMI-Vorschau wird das 4K-Hintergrundvideo vorübergehend durch ein statisches 1080p-Bild ersetzt. Deaktivieren Sie die Eingangsvorschau, um den Hintergrund in 4K zu behalten.

### Einfache Entfernung (v1.11.0+)

Ab der veröffentlichten Version v1.11.0 unter Wartung **Clean Your TV deinstallieren** mit derselben gespeicherten TV-Verbindung wählen. Einmal bestätigen. Vorhandene bekannte Projekt-Apps und Dateien werden entfernt, fehlende übersprungen, auch nach einer Teilinstallation.

Wenn aufgefordert, den TV vom Strom trennen, wieder anschließen, auf das Netzwerk warten und **Erneut versuchen** wählen. Standby oder Quick Start ist kein vollständiger Neustart; CYTV startet den TV nicht automatisch neu. Bei Verbindungsabbruch Verbindung prüfen und dasselbe Entfernen erneut versuchen, ohne weiteren Wiederherstellungsassistenten. Bei verweigertem Zugriff die angeforderte Root-Verbindung verwenden; bei beschäftigtem TV warten und erneut versuchen. Erfolg erscheint erst nach bestätigter abschließender Bereinigung. Schlüssel und Originalberichte behalten. Notfallsteuerung und Zustimmung zum Teilen gelten weiter.

Ab v1.11.0 bietet eine fehlgeschlagene oder unterbrochene Einrichtung direkt die Wiederherstellung an. Kann No-root nicht fortgesetzt werden, bestätigen Sie die vollständige Entfernung einmal. Bei vorübergehendem Verbindungsverlust oder einem beschäftigten CYTV-Prozess erfolgen bis zu drei Versuche. Wählen Sie bei erforderlichem Root-Zugriff **Mit Root verbinden** für denselben TV; die verifizierte Root-Bereinigung beendet auch dessen blockierte No-root-Entfernung. Nach einem Root-Aktivierungsfehler versucht CYTV, LG Home wiederherzustellen und zu prüfen, ohne erneut zu aktivieren. Ein Abbruch mit unerledigter Arbeit behält Bericht und Wiederherstellungsaktionen. Der Notstopp bleibt erhalten.

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

> Unveröffentlichter Kandidat: experimentelles Root Home wird anhand der Fähigkeiten von Qt SDK 6–9 gewählt, ohne Modellliste. Hardware-Kompatibilität und normales OTA sind ungeprüft. Andere Home-Integrationen bleiben unverändert; nach einem Sicherheits- oder Stromstopp Home explizit aktivieren. [#364](../development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).
