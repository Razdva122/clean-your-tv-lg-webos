# Clean Your TV — Benutzeranleitung

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

Wenn der Installer **No-root** anbietet, können Sie über Ihre vorhandene Root-SSH-Verbindung fortfahren. Developer Mode ist dafür nicht erforderlich.

[Ausführliche Installation](../INSTALL.md) · [Kompatibilität](../COMPATIBILITY.md)

### Developer Mode einrichten (No-root)

Mit Developer Mode kann CYTV Apps auf einem TV ohne Root installieren.

1. Öffnen Sie am TV LG Apps, suchen Sie nach Developer Mode und installieren Sie die App.
2. Öffnen Sie Developer Mode und melden Sie sich mit Ihrem LG Developer-Konto an. Erstellen Sie bei Bedarf ein Konto unter [LG Developer](https://webostv.developer.lge.com).
3. Schalten Sie Dev Mode Status ein. Der TV startet neu. Öffnen Sie danach Developer Mode erneut.
4. Schalten Sie Key Server ein und lassen Sie Developer Mode geöffnet. Tragen Sie die dort angezeigte IP Address als TV-Adresse in CYTV ein.
5. Geben Sie die Passphrase ein: die sechs Zeichen, die Developer Mode am TV anzeigt. Beachten Sie Groß- und Kleinschreibung.

Verwenden Sie den Code vom TV, nicht das Passwort Ihres LG-Kontos. Wird kein Code angezeigt, schalten Sie Key Server ein.

Die Kopplung ist ein eigener Schritt: Bestätigen Sie CYTV mit der Fernbedienung, wenn der TV danach fragt. Wenn der TV die Anfrage ablehnt, bestätigen Sie in CYTV einen neuen Versuch mit demselben TV.

Wenn sich die HDMI-Eingänge bei der ersten No-root-Einrichtung nicht lesen lassen, können Sie nach dem Hinweis mit den gefundenen Apps fortfahren.

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
4. Folgen Sie dem Assistenten. Lassen Sie TV und CYTV eingeschaltet und wechseln Sie bis zum Abschluss nicht das Netzwerk. Beenden Sie die Android-App nicht zwangsweise.

Wähle im Desktop-Installationsprogramm nach erfolgreicher Verbindungsprüfung **Einrichtung fortsetzen**, um dieselbe TV-Verbindung und Edition zu behalten. Der Assistent erklärt den Zustand einer früheren Installation; technische Ergebnisse stehen unter **Details**. Falls eine frühere Aktion Wiederherstellung erfordert, nutze zuerst die angebotene Wiederherstellung. Vor Änderungen prüft die Einrichtung installierte Versionen und fragt nach Bestätigung. Gespeicherte Neustartanforderungen werden erneut geprüft; der Assistent fordert einen Neustart nur an, wenn die aktuelle Bereinigung ihn benötigt.

Wenn der Installer anbietet, die aktuelle Home-Integration zu ersetzen, bestätigen Sie nur, wenn Sie LG Home wiederherstellen und die Root-Installation fortsetzen möchten. Wenn Sie ablehnen, bleibt das aktuelle Home aktiv.

## 5. Fernbedienung prüfen

1. Öffnen Sie eine andere TV-App und drücken Sie kurz **Home**. Clean Your TV sollte erscheinen. Geben Sie im Assistenten Ihre Beobachtung an; überspringen Sie den Test, wenn Sie ihn nicht durchgeführt haben.
2. Prüfen Sie Pfeile, OK, Zurück, Lautstärke und Ton.

<a id="bedienung-und-wiederherstellung"></a>

## 6. Bedienung und Wiederherstellung

Um die Startumgebung der vorhandenen Root Beta zu migrieren, schalten Sie **Change Home** aus und führen Sie `cytv migrate-root-beta --edition root --root-variant node012-beta` über die gespeicherte Root-SSH-Verbindung aus. App und Einstellungen bleiben erhalten. Hat eine frühere Deinstallation die Installation bereits verändert, stoppt die Migration. Schalten Sie anschließend Change Home ein und wählen Sie die Startquellen in den Home-Einstellungen.

Wählen Sie unter **+ / App hinzufügen** einen HDMI-Eingang aus, um ihn anzuheften. Mit OK wechseln Sie zum Eingang. Halten Sie OK gedrückt, um die Kachel zu verschieben oder auszublenden.

Pfeile wählen eine Kachel, OK öffnet sie; OK gedrückt halten zum Verschieben. Kurzes Zurück behält Navigation und Beendigungsdialog der App bei. Kurzes Home öffnet bei aktiver Home-Steuerung den Launcher. Zurück 1,2 Sekunden gedrückt halten, um LG Home einmalig zu öffnen. Der Home-Schalter und Ihre Einstellungen bleiben unverändert.

Öffnen Sie **Home-Einstellungen → Darstellung → Kacheln bearbeiten**, um Kacheln mit kurzen Tastendrücken zu bearbeiten. Nehmen Sie die Kachel mit OK auf, verschieben Sie sie mit den Pfeiltasten und legen Sie sie mit OK ab. Zurück bricht das Verschieben ab oder beendet die Bearbeitung.

**Home innerhalb von zwei Sekunden dreimal kurz drücken**, dazwischen loslassen. Dies stellt LG Home wieder her und stoppt die Steuerung, ohne Einstellungen zurückzusetzen.

No-root: Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten. Root: **Home ändern** in den Home-Einstellungen einschalten, um fortzufahren. **LG Home öffnen** öffnet LG Home einmalig, ohne das Home-Ziel zu ändern. Für LG Home als dauerhaftes Ziel **Home ändern** ausschalten. Beide Steuerungen nie gleichzeitig betreiben. Bei wiederholtem Fehler LG Home aktiv lassen.

Wenn Home Helper angehalten ist, können Sie auch in den Einstellungen für den Home-Bildschirm oder den Bildschirmschoner **Helper starten** wählen. Der Status wird nach dem Start automatisch aktualisiert.

Auf Fernsehern, auf denen LG Home als Leiste erscheint, kann das Ein- oder Ausschalten von **Change Home** in Root die TV-Oberfläche kurz neu starten. Öffnen Sie nach einem Neustart oder Fehler Clean Your TV und schalten Sie **Change Home** erneut ein. LG Home bleibt verfügbar.

## Brauchen Sie Hilfe?

Halten Sie bei `ssh-identity-changed` an und überprüfen Sie den SSH-Schlüssel des Fernsehers. [Wiederherstellung bei geändertem SSH-Schlüssel](../RECOVERY.md#ssh-identity-changed)

Wenn Sie Ihren No-root-Fernseher auf die Werkseinstellungen zurückgesetzt haben, wählen Sie bei geändertem Schlüssel **Nach dem Werksreset erneut verbinden**. Folgen Sie den Schritten in Ihrem vertrauenswürdigen Heimnetz. Das alte Profil und der Deinstallationseintrag bleiben erhalten.

Ist die Installation am Computer noch offen, wählen Sie im Ergebnis **Wiederherstellungsoptionen prüfen** und bei **Wiederherstellungsoptionen prüfen?** die Schaltfläche **Weiter**. Der Assistent verwendet dieselbe gespeicherte TV-Verbindung. Ist bei No-root das Paketergebnis unklar, wählen Sie zuerst **TV-Status prüfen**, sofern die Schaltfläche angeboten wird. Bestätigen Sie angebotene Änderungen separat. Bleibt die Einrichtung blockiert, behalten Sie die gespeicherte Verbindung und die Wiederherstellungsdaten.

Wenn No-root **Speicherprüfung wiederholen** anbietet, wähle die Schaltfläche, um denselben Fernseher ohne Änderungen erneut zu prüfen. Bestätige die Installation nach erfolgreicher Prüfung separat. Bei einem offenen Vorgang wähle **Wiederherstellungsoptionen prüfen**.

Wenn das Desktop-Installationsprogramm die Pakete geprüft hat, die Home-Taste aber Clean Your TV nicht öffnet, wählen Sie auf der Ergebnisseite bei No-root **Home-Taste diagnostizieren** und bei Root **TV-Status prüfen**. Bei No-root wird das bereits erfasste Ergebnis angezeigt. Den Bericht können Sie über **Diagnosebericht speichern** sichern.

Sichern Sie den Bericht am Computer mit **Diagnosebericht speichern…** auf der Ergebnisseite. Wenn Sie Hilfe brauchen, wählen Sie **Problem melden**, prüfen den Entwurf und wählen **Entwurf kopieren** und **Meldeformular öffnen**. Fügen Sie den Entwurf ein und hängen Sie den gespeicherten Bericht an, falls vorhanden.

[Problem melden](../FEEDBACK.md) · [Wiederherstellung — Englisch](../RECOVERY.md) · [Aktualisieren oder entfernen — Englisch](../MAINTENANCE.md) · [Andere Sprachen](../LANGUAGES.md)

### Einfache Entfernung

Unter Wartung **Clean Your TV deinstallieren** mit derselben gespeicherten TV-Verbindung wählen. Einmal bestätigen. Vorhandene bekannte Projekt-Apps und Dateien werden entfernt, fehlende übersprungen, auch nach einer Teilinstallation.

Wenn aufgefordert, den TV vom Strom trennen, wieder anschließen, auf das Netzwerk warten. Standby oder Quick Start ist kein vollständiger Neustart; CYTV startet den TV nicht automatisch neu. Wenn die Bereinigung Root-Zugriff erfordert, verwenden Sie den vorhandenen Root-Zugang zu demselben TV. Ohne diesen Zugang bleibt die Bereinigung unvollständig. Wenn der TV beschäftigt ist, warten Sie und versuchen Sie es erneut. Erfolg erscheint erst nach bestätigter abschließender Bereinigung. Schlüssel und Originalberichte behalten. Notfallsteuerung und Zustimmung zum Teilen gelten weiter.

Wenn das Installationsprogramm am Computer auf den TV wartet, wählen Sie **Entfernung fortsetzen**, sobald die Schaltfläche erscheint. Mit **Abbrechen** beenden Sie das Warten und mit **Erneut versuchen** prüfen Sie die Verbindung manuell.

Wenn bei der Entfernung **Zu LG Home zurückkehren** angezeigt wird, wählen Sie diese Option. Nach bestätigter Wiederherstellung wählen Sie **Entfernung fortsetzen**. Wenn Sie direkt über die Wartung zu LG Home zurückkehren, bleiben die Apps installiert.

Wenn der Installer die Entfernung, die abschließende Bereinigung, die TV-Steuerung oder das Ergebnis des Paketvorgangs nicht bestätigen kann oder geänderte Projektpfade meldet, wählen Sie **Wiederherstellungsoptionen prüfen** mit der ursprünglichen gespeicherten Verbindung. Bestätigen Sie die Fortsetzung separat, wenn der Installer sie anbietet. Wenn bei der Wiederherstellung einer No-root-Installation **TV-Status prüfen** angeboten wird, wählen Sie diese Option und behalten Sie die Wiederherstellungsdaten.

Kann der Installer den angeforderten vollständigen Neustart nicht bestätigen, speichern Sie den Diagnosebericht und hängen Sie ihn an. Behalten Sie die gespeicherte Verbindung und Wiederherstellungsdaten. Wiederholen Sie die Stromunterbrechung nicht ständig und löschen Sie den unvollständigen Vorgang nicht manuell.

Sobald am Computer **Entfernung von Clean Your TV ist bestätigt.** angezeigt wird, wählen Sie **Schließen**. Mit **Meinen Fernseher einrichten** können Sie die Einrichtung am selben Fernseher mit derselben Verbindung und Edition neu starten.

**Root neu installieren:** Wählen Sie mit der gespeicherten Verbindung **Meinen Fernseher einrichten → Root** und bestätigen Sie **Root neu installieren?**. Der Installer stellt LG Home wieder her und entfernt Clean Your TV samt Updatern, Home Helper und gespeicherten Einstellungen vollständig. Nach verifizierter Entfernung installiert und aktiviert er die enthaltenen Pakete und die Root-Laufzeit. Andere TV-Apps und bestehender Root-/SSH-Zugriff bleiben erhalten. Wenn der Desktop-Assistent pausiert, öffnen Sie denselben Installer und wählen Sie **Root-Neuinstallation fortsetzen**. Nach bestätigter Entfernung wählen Sie **Root-Installation fortsetzen**. **Clean Your TV deinstallieren** allein startet keine neue Installation.

Wenn der Assistent bei der Bereinigung einen vollständigen Neustart verlangt, trennen Sie den Fernseher vom Strom, schließen Sie ihn wieder an und schalten Sie ihn ein. Wählen Sie nach dem Start **Ich habe den TV neu gestartet — prüfen und fortfahren**.

### LG-Einstellungen ändern und Root-Rollback abschließen

Öffnen Sie im Desktop-Installer **Wartungsaktion → LG-Einstellungen anpassen (Debloat)** mit der gespeicherten TV-Verbindung. Wählen Sie die gewünschten Einstellungen aus, klicken Sie auf **Ausgewählte Einstellungen anwenden** und prüfen Sie die Ergebnisse. Ist ein früherer Vorgang offen, wählen Sie zuerst **Wiederherstellungsoptionen prüfen** mit dessen ursprünglicher gespeicherter Verbindung.

- [Root Updater](../RECOVERY.md#standalone-root-updater-rollback-readiness)
- [Root System Updater](../RECOVERY.md#root-system-rollback-readiness-candidate)

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

## Einstellungen

Ohne gespeicherte Einstellung ist der Bildschirmschoner standardmäßig eingeschaltet. Sie können ihn in den Home-Einstellungen unter **Bildschirmschoner** ausschalten.

Aktiviere unter **Einstellungen → Darstellung** die Option **Häufig genutzte Apps zuerst**. Die Reihenfolge im Dock bleibt erhalten. Halte OK gedrückt, um Kacheln in der manuellen Reihenfolge zu verschieben oder auszublenden. Schalte die Option aus, um zur manuellen Reihenfolge zurückzukehren. Die Option gibt es auch am Ende der Einstellungen im cytv-Installationsprogramm.

Wähle mit ↑ ↓ eine Kategorie und öffne sie mit → oder OK. ← führt zu den Kategorien zurück; Zurück führt zuerst dorthin und schließt danach die Einstellungen. Beim erneuten Betreten bleibt der Fokus auf dem letzten verfügbaren Element. Unter Spalten folgen die Pfeile dem dreispaltigen Raster. Unter Sprache wird die gewählte Sprache fokussiert.

Wählen Sie unter **Einstellungen → Ihr Home-Bildschirm → Uhrzeitformat** zwischen **Automatisch (TV-Region)**, **12 Stunden** und **24 Stunden**.

Kann No-root den Home-Status nicht lesen, wähle Erneut versuchen. Ein nicht verfügbarer Schalter bedeutet nicht, dass die Home-Steuerung ausgeschaltet ist. Unter Hintergründe kannst du ein Bild vom Smartphone oder CYTV übertragen; Qualität und Abdunklung erscheinen, wenn ein Hintergrund verfügbar ist. Das Entfernen eines eigenen Hintergrunds muss bestätigt werden; Abbrechen behält ihn.

## Wetter

Öffnen Sie Einstellungen → Wetter unter Hintergrundbilder. Schalten Sie das Wetter ein und suchen Sie unter Stadt nach dem richtigen Ort mit Region und Land. Automatisch ermittelt einen ungefähren Ort anhand der Internetverbindung. Ein VPN kann das Ergebnis verändern; verwenden Sie bei fehlendem oder falschem Ort die manuelle Suche. Der erkannte oder gewählte Ort wird angezeigt. Wählen Sie °C / m/s oder °F / mph sowie ein verfügbares Format: kompakt, aktuell, ausführlich oder vier Tage. Die Vorschau folgt dem Design; Beispiel kennzeichnet Musterdaten. Liquid Glass unterstützt nur kompakt. Ribbon und Atmosphere zeigen kein Wetter. Ausschalten beendet Anfragen und blendet Stadt, Einheiten und Format aus; die Quellenauswahl bleibt verfügbar. Bei einer Störung bleiben aktuelle Daten kurz erhalten; nach längerer Zeit wird das Wetter bis zur Aktualisierung ausgeblendet.

Wählen Sie die Vorhersagequelle: Auto, MET Norway oder Open-Meteo. Auto beginnt mit MET Norway, versucht bei einem Fehler einmal Open-Meteo und verwendet danach die zuletzt erfolgreiche Quelle und deren Cache. Eine manuelle Auswahl wechselt die Quelle nie automatisch. Neue Einstellungen verwenden Auto; ältere gespeicherte Einstellungen ohne Quelle behalten Open-Meteo. Die tatsächliche Quelle wird angezeigt. Die Verfügbarkeit hängt vom Netzwerk ab. MET aktualisiert höchstens alle drei Stunden; der Cache verfällt nach sechs Stunden. Fehlende Werte werden ausgeblendet: MET liefert keine gefühlte Temperatur oder Niederschlagswahrscheinlichkeit. Tagesbereiche fassen Vorhersagepunkte zusammen, keine gemessenen Extremwerte.

Vorhersagekoordinaten gehen an api.met.no oder api.open-meteo.com, Stadtsuchen an geocoding-api.open-meteo.com. Die optionale automatische Ortssuche übermittelt die öffentliche IP an get.geojs.io. Alle Verbindungen nutzen HTTPS; ein API-Schlüssel ist nicht nötig. Ort, Quelle und Cache bleiben auf dem Fernseher. Datenquellen enthält Bedingungen und Urheberangaben, darunter das Norwegische Meteorologische Institut (MET Norway, CC BY 4.0).

Die Schaltfläche Datenquellen in der Wetterüberschrift öffnet Informationen zu Diensten und Lizenzen.

## iPhone-Foto als Hintergrund

Einstellungen → Hintergrundbilder → Vom Telefon hochladen öffnen und den Code scannen. JPG, PNG oder HEIC/HEIF wählen, zuschneiden, Qualitätsgrenze bestätigen und senden. Am TV Anwenden wählen. Safari nutzt native HEIC-Unterstützung; Chrome, Firefox und andere moderne Browser bei Bedarf den mitgelieferten lokalen Decoder. Die Umwandlung erfolgt auf dem Telefon ohne externen Dienst. Abbrechen oder eine andere Datei beendet die Umwandlung. Eingabe: 32 MiB und 50 Millionen Pixel; Ausgabe: maximal 1080p und 2 MiB. Bei Fehlern ein anderes Foto oder JPG/PNG wählen. Gilt für die Telefonseite, nicht die Mac-App.

## Clean Your TV einrichten

Wählen Sie vor dem Design unter **Debloat**, welche LG-Einstellungen für Werbung, Empfehlungen, Datenschutz und Benachrichtigungen Sie ändern möchten. Prüfen Sie jedes Ergebnis. Kann der ursprüngliche Wert nicht gelesen werden, steht dafür keine automatische Wiederherstellung zur Verfügung. Wählen Sie **Debloat überspringen**, um die Einstellungen beizubehalten.

Bei der Deinstallation können Sie die gespeicherten ursprünglichen Debloat-Einstellungen wiederherstellen. Wenn Sie die Wiederherstellung überspringen, läuft die Deinstallation ohne diese Änderungen weiter.

Wähle nach erfolgreicher Installation Classic, Liquid Glass oder Ribbon und schalte das Wetter ein oder aus. Ribbon unterstützt kein Wetter; Liquid Glass nutzt das Kurzformat. Der ungefähre Ort wird über die Internetverbindung ermittelt und lässt sich in Home ändern.

No-root mit Developer Mode bietet automatische Verlängerung; prüfe weiterhin den offiziellen Timer. Bei neuen No-root-Installationen über vorhandenes root-SSH wird der Tab Developer Mode ausgeblendet. Root bietet über Homebrew Channel eine Sperre für LG-Firmwareupdates, einschließlich Sicherheitsupdates; ein echter Neustart über Homebrew Channel ist erforderlich. CYTV-Updates bleiben separat.

Mit Aktuelle Einstellungen beibehalten überspringst du die Anpassung. Der Schalter zeigt den aktuellen Ein/Aus-Zustand der Modusfunktion. Unveränderte Einstellungen bleiben erhalten. Die Root-Neuinstallation entfernt weiterhin gespeicherte CYTV-Einstellungen wie oben beschrieben. Prüfe das Aussehen am TV und unbestätigte Optionen vor einem neuen Versuch in Home.

## Updates auf einem Fernseher mit Root

Wenn ein selbstaktualisierender System Updater eingerichtet ist, nutzen Sie **Softwareupdates → Alles aktualisieren** für Root oder No-root auf einem Fernseher mit Root. Lassen Sie den Fernseher bis zum Abschluss eingeschaltet. Zur Reparatur nur des Updaters öffnen Sie Home und wählen **Softwareupdates → Wiederherstellung → System Updater neu installieren**; Home und Einstellungen bleiben erhalten. No-root ohne Root-Zugriff verwendet weiterhin die Installation über den Computer.
