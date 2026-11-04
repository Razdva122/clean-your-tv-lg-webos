# Clean Your TV — Benutzeranleitung

**1.7.0 — Root-Startquellen:** Unter Einstellungen → Ihr Home-Bildschirm aktivieren Sie **Home ändern**, um **Clean Your TV zuerst öffnen** einzustellen. **LG Channels / Live-TV** ist standardmäßig an; **YouTube** ist aus. Bei ausgeschalteter Home-Änderung bleiben die Schalter sichtbar, aber gesperrt; die Werte bleiben gespeichert. Die Einstellungen werden privat auf diesem TV gespeichert und sind nicht im portablen Profilexport enthalten. Dies bestätigt kein geprüftes Start- oder Aufwachverhalten. Ist eine Quelle ausgeschaltet, entscheidet die TV-Firmware über den Start; die Rückkehr zu dieser Quelle ist nicht garantiert. Es gibt keinen HDMI-Startschalter. [Grenzen des nativen Starts (Englisch)](../../root-edition/README.md#candidate-native-startup-choices).

> Diese Anleitung beschreibt 1.7.0. Verfügbare Pakete finden Sie in den [veröffentlichten GitHub-Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). Enthalten sind alle fünf Installer-Verbesserungen. Root-Einstellungen lesen beim erneuten Öffnen den tatsächlichen Status; ein fehlgeschlagener Test aktiviert Home nicht. System Updater 1.2.0 gilt für zulässige Neueinrichtung oder geprüften Ersatz von 1.1.0/1.1.1. Installiertes 1.1.2 behält seine alten Kanäle; eine allgemeine Migration gibt es nicht. Wiederherstellungsdaten behalten und keinen Ersatz erzwingen. [Versionen und Grenzen](../RELEASE-1.7.0.md).

> v1.5.0: Designs, Galerie und PC-TV-Übertragung. Bekannte Root-Grenzen: Appearance kann um 110 px springen; Home startet nach Standby möglicherweise nicht automatisch. Die Geräteprüfung bleibt begrenzt. [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** Designs mit festem Layout behalten den Platz der ausgeblendeten Columns-Zeile, damit Apply die Scrollposition in Appearance erhält. Zeiger, Tastatur und Bedienungshilfen überspringen Columns.

[Dokumentation](../README.md) · [Problem melden](../FEEDBACK.md)

**Historischer Prüfumfang 1.5.4:** Die C3-Abnahme umfasst die dokumentierten Strom-, Home-, Fokus-, Aus-Zustand- und manuellen Rollback-Tests. Andere TVs, eARC-Audio und echte Android-Geräte sind nicht bestätigt; eine erfolgreiche Installation beweist keine Kompatibilität. [Prüfumfang (Englisch)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

**1.5.4:** Konsole, Desktop und Android zeigen für jede TV-Prüfung den Zustand: nicht geprüft, läuft, bestanden, fehlgeschlagen oder nicht verifizierbar. Ergebnisse bleiben nach Fehlern sichtbar. Node.js/Python wird auf dem TV geprüft; `doctor` bereitet Python nicht vor und fordert keine Steuerungskopplung an. Speichern Sie den Bericht vor einem neuen Versuch.

## Edition wählen

No-root und Root sind gleichwertige Optionen für unterschiedliche TV-Konfigurationen. Wählen Sie No-root für LG Developer Mode oder Root für vorhandenen Root-Zugriff per SSH. Kompatibilität und Testumfang hängen von der jeweiligen Edition ab.

- **No-root:** LG Developer Mode und Key Server einschalten. Die am Fernseher angezeigte Passphrase eingeben und die separate Kopplungsanfrage am Fernseher bestätigen. Developer Mode muss aktiv bleiben: Bei Ablauf können nachinstallierte Apps entfernt werden. Den offiziellen Timer auch mit aktivierter Beta-Verlängerung kontrollieren. Die Überwachung durch Helper benötigt das lokale Netzwerk.
- **Root:** Bereits vorhandener Root-Zugang über SSH ist nötig. Der Installer richtet keinen Root-Zugang ein. Developer Mode nicht auf einem bereits gerooteten Fernseher aktivieren. Root-Zugang und Wiederherstellungsdienste verfügbar halten.

Root benötigt funktionierende Home-Schnittstellen von Settings Service und System Profile (`com.webos.service.systemprofile`); vorhandener Root-Zugriff allein bestätigt keine Kompatibilität.

> **1.6.0:** Root prüft die benötigten Home-Schnittstellen vor der Vorbereitung von privatem Python oder Paketen. Ein Fehler stoppt die Einrichtung; ein erfolgreicher Test belegt weder Firmware-Kompatibilität noch die Funktion der Home-Taste. Bekannte Verbindungsfehler erhalten gezielte Hinweise. Profile, Vertrauensdaten und Wiederherstellungsdaten behalten; offene Vorgänge erfordern geprüfte Wiederherstellung statt blinder Wiederholung. Diagnosebericht speichern und prüfen. [Details](../development/INSTALLER-PREFLIGHT-HELP.md).

## Voraussetzungen

Fernseher einschalten und mit demselben vertrauenswürdigen Heimnetz wie den Computer verbinden. Danach muss der Computer nicht eingeschaltet bleiben. Die Kompatibilität hängt von Modell, Firmware und Fernbedienung ab; für Root stehen noch Gerätetests aus.

1.5.4 enthält Home Helper **0.6.21** für TV-Node.js **0.10.25+**; Root benötigt weiterhin Node.js **8+**. [Compatibility](../COMPATIBILITY.md).

**Unveröffentlichte Änderung für webOS 1.x:** Der nächste No-root-Installer akzeptiert TV-Node.js **0.10.15+** nach Helper-Tests mit genau dieser Laufzeit; veröffentlichte Installer 1.7.1 benötigen weiterhin **0.10.25+**. Dies bestätigt keine Kompatibilität mit altem WebKit, nativer Eingabe oder Home. TV-Laufzeit nicht ersetzen und Prüfungen nicht umgehen. Root benötigt weiterhin Node.js 8+. [Nachweise und Grenzen](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased).

No-root Helper benötigt TV-Node.js **0.10.25+**. Root benötigt Node.js **8+** und funktionierendes Python **3.9+**. Bei Bedarf lädt der Installer ein geprüftes privates Python; die erste Vorbereitung braucht **320 MiB** freien Platz. System-Python wird nicht ersetzt. Für die Wiederherstellung benötigte Laufzeitversionen behalten. [Python (Englisch)](../OPTIONAL-PYTHON.md). Developer-Mode-Verlängerung ist **Beta, standardmäßig aus**; echte Verlängerung ohne Root ist nicht bestätigt. Den offiziellen Timer weiterhin prüfen.

### Developer Mode einrichten (No-root)

Mit Developer Mode kann CYTV Apps auf einem TV ohne Root installieren.

1. Öffnen Sie am TV LG Apps, suchen Sie nach Developer Mode und installieren Sie die App.
2. Öffnen Sie Developer Mode und melden Sie sich mit Ihrem LG Developer-Konto an. Erstellen Sie bei Bedarf ein Konto unter webostv.developer.lge.com.
3. Schalten Sie Dev Mode Status ein. Der TV startet neu. Öffnen Sie danach Developer Mode erneut.
4. Schalten Sie Key Server ein und lassen Sie Developer Mode geöffnet. Tragen Sie die dort angezeigte IP Address als TV-Adresse in CYTV ein.
5. Geben Sie die Passphrase ein: die sechs Zeichen, die Developer Mode am TV anzeigt. Beachten Sie Groß- und Kleinschreibung.

Verwenden Sie den Code vom TV, nicht das Passwort Ihres LG-Kontos. Wird kein Code angezeigt, schalten Sie Key Server ein.

Die Kopplung ist ein eigener Schritt: Bestätigen Sie CYTV mit der Fernbedienung, wenn der TV danach fragt.

Halten Sie Developer Mode aktiv: Öffnen Sie die App vor Ablauf des Timers und drücken Sie bei bestehender Internetverbindung EXTEND. Nach Ablauf kann LG diese Apps entfernen.

## Installation und Sprache

- **Windows x64:** `cytv-windows-x64-desktop.zip` herunterladen, im Explorer **Alle extrahieren** wählen und `cytv-desktop/cytv-desktop.exe` öffnen. Den Ordner `_internal` daneben behalten. Eine Windows-Herausgebersignatur ist nicht eingerichtet. Die separate Konsole heißt `cytv-windows-x64.exe`; für die folgenden PowerShell-Befehle in `cytv.exe` umbenennen und `.\cytv.exe` verwenden.
- **macOS 13+:** `cytv-macos-arm64.zip` für Apple Silicon oder `cytv-macos-x64.zip` für Intel entpacken. `cytv.app` nach Programme verschieben und öffnen; Zugriff auf das lokale Netzwerk erlauben. Bei einer Sperre für einen vertrauenswürdigen Projekt-Download Datenschutz & Sicherheit → Dennoch öffnen verwenden. Gatekeeper nicht abschalten. Ältere Systeme sind nicht abschließend geprüft.
- **Linux x64:** Unter Ubuntu 22.04+, Debian 12+ oder Mint 21+ `cytv-linux-x64.deb` mit der grafischen Paketverwaltung installieren, dann Clean Your TV im Anwendungsmenü öffnen. Für Bibliotheken kann Internet nötig sein. Linux ARM wird nicht angeboten. Die eigenständige Datei `cytv-linux-x64` ist die CLI; für die grafische App das `.deb` verwenden.

[Android-Installer (Englisch)](../../android/README.md): Sprache oben rechts wählen. Ohne Deinstallation oder Datenlöschung aktualisieren. Android 7 / WebView 108 ist die Mindestanforderung, kein geprüftes Telefon; abgenommen wurde ein Emulator mit Android 15 ARM64 / WebView 124. Echte Telefone und Wiederherstellung über eine reale TV-Verbindung bleiben ungeprüft.

**Unveröffentlichter Android-Kandidat:** Bei einer ursprünglichen Root-Operation `install / coordinator-submitted` kann die Prüfung der Wiederherstellungsoptionen nach ausdrücklicher Bestätigung nur lesend auf das ursprüngliche Profil und den gespeicherten SSH-Schlüssel zugreifen. App und Daten nicht löschen, Profil nicht ersetzen und Installation nicht wiederholen. Nur die vom Maintainer benannte signierte, neu gebaute APK verwenden; die öffentliche APK enthält diesen Weg noch nicht. [Ablauf und Grenzen](../../android/README.md#interrupted-root-installation-inspection-unreleased).

Der Desktop-Assistent verwendet zunächst die Systemsprache und speichert eine ausdrückliche Auswahl. Am Fernseher unter **Einstellungen → Sprache** die gewünschte Sprache oder die automatische Systemauswahl wählen. Die Spracheinstellungen von Installer und Fernseher sind unabhängig. Alle Sprachcodes stehen im [Sprachverzeichnis](../LANGUAGES.md).

Für die separat heruntergeladene CLI unter macOS/Linux im entpackten Verzeichnis:

```sh
chmod +x cytv
./cytv --language de install
```

Fernseher oder IP-Adresse und Edition auswählen, dann die Zusammenfassung prüfen. Einer neuen SSH-Identität nur für den eigenen Fernseher im vertrauenswürdigen Netz zustimmen; ein geänderter gespeicherter Schlüssel blockiert den Zugang. Root aktiviert Home nach Einrichtung der Wiederherstellung sofort, ohne Testphase oder Behalten-Schritt. Pfeile, OK, Home, Zurück/Abbrechen, Lautstärke, Bereitschaft und Kaltstart am eigenen Fernseher testen.

**1.6.0:** Paketprüfung, Startprüfung und Ihre physische Home-Beobachtung werden getrennt gezeigt. Startbestätigung oder Helper-Prozess beweisen keine Home-Umleitung. Öffnen Sie eine andere TV-App, drücken Sie Home einmal kurz und wählen Sie die Beobachtung; Vorgabe ist **Nicht getestet / überspringen**. `--yes` beantwortet diese Prüfung nicht; nichtinteraktive Einrichtung lässt sie ungetestet. Fehler oder Überspringen deinstallieren nichts und starten keine Neuinstallation. Speichern Sie den lokalen Bericht bei Hilfebedarf; er wird nicht automatisch veröffentlicht. Andere Tasten, Ton, Standby und Kaltstart bleiben separate Prüfungen.

## Bedienung und Wiederherstellung

Pfeile wählen eine Kachel, OK öffnet sie; OK gedrückt halten zum Verschieben. Kurzes Zurück behält Navigation und Beendigungsdialog der App bei. Kurzes Home öffnet bei aktiver Home-Steuerung den Launcher. Zurück 1,2 Sekunden gedrückt halten, um LG Home einmalig zu öffnen. Der Home-Schalter und Ihre Einstellungen bleiben unverändert.

**Home innerhalb von zwei Sekunden dreimal kurz drücken**, dazwischen loslassen. Dies stellt LG Home wieder her und stoppt die Steuerung, ohne Einstellungen zurückzusetzen. Beim älteren No-root Helper bis einschließlich 0.6.13 stattdessen Home etwa zwei Sekunden halten. Langes Home ist nicht die Root-Notfallgeste.

No-root: Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten. Root: **Home ändern** in den Home-Einstellungen einschalten, um fortzufahren. **LG Home öffnen** öffnet LG Home einmalig, ohne das Home-Ziel zu ändern. Für LG Home als dauerhaftes Ziel **Home ändern** ausschalten oder `cytv restore` ausführen. Beide Steuerungen nie gleichzeitig betreiben. Bei wiederholtem Fehler LG Home aktiv lassen.

> **1.5.4 — Root:** Wenn Root fehlerfrei arbeitet und Sie **Home ändern** ausdrücklich einschalten, legt CYTV einen eigenen nativen Eingang **Clean** an und speichert Clean als gemerkten Eingang. Beim Abschalten der Home-Steuerung, Notfallstopp, Fehler, Pausieren für ein Update oder Deinstallieren wird der eigene Eintrag entfernt. Der vorherige Eingang wird nur wiederhergestellt, solange noch der von CYTV gesetzte Wert gilt; andere Eingänge und Vordergrund-Apps bleiben erhalten. Nicht unterstützte Fernseher oder fremde Einträge nutzen die normale abgesicherte Home-Steuerung. Clean ist nicht garantiert der sofortige erste Bildschirm. Die dokumentierten C3-Prüfungen für ersten Bildschirm, Bereitschaft und AC-Kaltstart bestanden; dies gilt nicht für alle Geräte. Nach Update/Rollback kann Home aus bleiben (#202), Einstellungen können veraltet sein (#206): Einstellungen schließen/öffnen, Home ändern ausdrücklich einschalten und auf Clean-Status warten. [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language de status
./cytv --language de doctor --report
./cytv --language de restore
./cytv --language de uninstall
```

> **1.6.0 (#152):** Bei abgelehntem Helper-Stopp kann die No-root-Wiederherstellung/Entfernung einen geprüften SSH-Stopp nutzen. Der Stoppzustand bleibt erhalten; bei unklarem Ergebnis bleibt das Journal bestehen. Keine Zustandsdateien löschen. Die Gerätebestätigung am EF950V steht aus. [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** Der No-root-Status bewahrt das Journal einer unterbrochenen Installation oder Entfernung. Gleiche Dateien oder fehlende Apps beweisen keinen Abschluss. Wird die Prüfung verweigert, stoppen Sie und bewahren Sie die Diagnose auf; eine reine Dateiprüfung reicht nicht aus. [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

Nach einer Unterbrechung zuerst `status` ausführen und Protokolle behalten. `restore` stellt LG Home ohne App-Entfernung wieder her; `uninstall` stellt es vor der Entfernung wieder her. Root-Wiederherstellungsdaten bleiben absichtlich erhalten; nicht zum Erzwingen einer Neuinstallation löschen. Diagnoseberichte vor Weitergabe prüfen; Schlüssel und Profilordner nicht veröffentlichen.

Öffne **Home-Einstellungen → Darstellung → Spalten** und wähle 1–8 Spalten oder **Nach Theme**, um dessen Wert zu verwenden (Classic: 5). Eine feste Zahl hat Vorrang vor dem Theme. Themes mit festem Layout blenden die Spaltenoption aus und verwenden den Wert des Autors. Deine gespeicherte Auswahl gilt wieder, sobald du zu einem Theme wechselst, das diese Einstellung unterstützt. Im heruntergeladenen Alpine liegen Apps in einem endlosen horizontalen Band: Links/Rechts blättert im Kreis, Oben öffnet die Schnellzugriffe und Unten kehrt zur selben App zurück. In Alpine lässt sich das Band auch mit Mausrad oder Touchpad bewegen; bei geöffnetem Dialog bleibt Home stehen.

1.5.4: Schalte unter **Home-Einstellungen → Darstellung** die Option **Kachel „App hinzufügen“ anzeigen** aus, um + auszublenden. Standardmäßig ist sie eingeschaltet. Über **App hinzufügen** im selben Bereich kannst du weiterhin Apps hinzufügen oder zurückholen. Verschieben und Ausblenden bleiben möglich; die Auswahl bleibt nach einem Neustart erhalten. Sind alle Apps ausgeblendet, bleiben die oberen Schaltflächen und Einstellungen erreichbar.

1.7.0: Das gewählte Theme bestimmt, ob **Eingänge** als Menü in der Kopfzeile oder als HDMI-Leiste erscheinen. Es gibt keine globale Platzierungsoption und keinen Schalter **Eingänge auf Home anzeigen**. Die Leiste unterstützt derzeit nur `dock-grid`. Liquid Glass wählt sie; Classic und Themes ohne diese Option behalten das Kopfmenü. Oben vom Dock öffnet die Leiste, erneut Oben die Kopfzeile; Unten oder Zurück führt zum Dock, OK startet die Quelle. Sind Quellkacheln vorhanden, ersetzt die Leiste das Eingangsmenü in der Kopfzeile. Der Gerätename stammt nur dann aus Eingangsmetadaten, wenn die Firmware ihn liefert; andernfalls steht bei einer verbundenen Quelle **Verbunden**. Home erfindet keinen PlayStation-Namen und garantiert keine CEC-Erkennung. Leere Anschlüsse bleiben wählbar. Vorschauen sind **standardmäßig an**; eine ausdrücklich gespeicherte Aus-Einstellung bleibt aus. Deaktiviere **Home-Einstellungen → Darstellung → Vorschau des ausgewählten Eingangs**, um sie auszuschalten. Solange sie aktiviert sind und das Theme die Leiste nutzt, erscheint nach etwa 0,8 Sekunden Fokus auf einem verbundenen HDMI-Eingang eine Vorschau. HDMI-Vorschauen können auf manchen TVs Ton abspielen oder HDR einschalten; Stille ist nicht garantiert. Home ändert die globale Stummschaltung oder HDR-Einstellungen des TVs nicht automatisch. Live-TV und leere Anschlüsse behalten statische Kacheln. Root liest den Eingangsstatus über seinen eigenen Dienst. No-root nutzt EIM direkt, soweit erlaubt; bei verweigerter Berechtigung erfolgt eine schreibgeschützte Abfrage über den gekoppelten Helper. Fehlgeschlagene Abfragen lassen den Status unbekannt; es gibt keinen neuen Schalter oder Kopplungsdialog.

In Theme-Vorschauen in 1.5.4 mit optionaler Seitenleiste wählst du mit Oben/Unten einen Menüpunkt, wechselst mit Rechts zu den Apps und kehrst mit Links aus der ersten App-Spalte zum Menü zurück.

No-root 1.5.0: Helper kann sich nach einem vorübergehenden Watchdog-Timeout beim Aufwachen erholen, höchstens fünfmal in zehn Minuten. Stop und dreifaches Home erfordern weiterhin einen ausdrücklichen Start Helper; wiederholte Fehler lassen Helper gestoppt. Die TV-Abnahme steht aus. [Verhalten und Grenzen (Englisch)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Aktualisierung und Entfernung

Funktionierende Pakete und private Einstellungssicherungen behalten. Bei No-root-Paketersatz vom Computer zuerst Helper stoppen und ohne vorherige Deinstallation aktualisieren, da diese Einstellungen löschen kann. Das Entfernen der Desktop-App entfernt keine TV-Apps. Keine einzelne IPK über eine aktive Root-Laufzeit installieren; den ausdrücklichen Wiederherstellungs- oder Neuinstallationsablauf von cytv verwenden.

Home-Einstellungen → Software-Updates öffnen und angebotene Versionen vor der Bestätigung prüfen. Updates/Rollback am TV benötigen **Root, Homebrew Channel** und vorbereitete passende Updater, auch bei der No-root-Edition. Ohne Root den Computer-Installer verwenden. Vollständige Systemupdates werden separat ausdrücklich vorbereitet: [Updates (Englisch)](../UPDATES.md). Unter Wiederherstellung steht die gespeicherte Rollback-Version; spätere Einstellungsänderungen können verloren gehen.

**Bestehende 1.3.0:** Der ursprüngliche System Updater kann geänderte Infrastruktur ablehnen. Abgebrochene Vorgänge behalten und die für 1.5.0+ dokumentierte geprüfte Wiederherstellung/Austauschvorbereitung befolgen; Journale nicht löschen oder blind wiederholen. Ein reines App-Update ersetzt keine festgelegte Root-Infrastruktur. [Umstieg und Wiederherstellung (Englisch)](../UPDATES.md#one-time-computer-preparation).

Die Korrektur des Home-Einstellungskanals wurde mit 1.5.0 veröffentlicht. Home und Helper gemeinsam mit einem passenden veröffentlichten Installer aktualisieren; ein reines Home-Update ändert den Helper nicht. Die Geräteprüfung bleibt modellspezifisch. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Root-HDMI-Tonwiederherstellung ist experimentell und **standardmäßig aus**; nur bei Bedarf aktivieren. Sie kann funktionierenden Ton unterbrechen und bestätigt keine eARC-Kompatibilität. [Tonwiederherstellung (Englisch)](../development/ROOT-AUDIO-RECOVERY.md). Der separate **CYTV Installer für Homebrew ist noch unveröffentlicht**; den veröffentlichten Computer-/Android-Installer verwenden.

Homebrew Channel verweigert diesem Installer den Zugriff. Unter webOS 11 benötigt Homebrew 0.7.3 ein Kompatibilitätsupdate von upstream. Bis eine unterstützte Homebrew-Version die Korrektur enthält, den veröffentlichten Computer- oder Android-Installer verwenden. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: Bei verweigertem Firmware-API-Zugriff wegen alter beschreibbarer Root-Verzeichnisse prüft `cytv enable-firmware-access --edition root --repair-package-permissions` das aktuelle Paket anhand vertrauenswürdiger privater Daten und entfernt Schreibrechte für Gruppe/andere nur aus Root-eigenen Pfaden. Unbekannte oder veränderte Dateien stoppen die Reparatur. Profil, Home-Auswahl und Firmware-Sperre bleiben erhalten; [Details (Englisch)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` hilft bei einem geprüften Root-Rollback, wenn alle Paketinstallationen beendet sind, aber die Launcher-Bereitschaft abläuft. Der echte Launcher muss seine Bereitschaft bestätigen; unbekannte Installer-Ergebnisse werden abgelehnt. Pakete, festgelegter Code/Schlüssel, Fehlernachweise und ausdrücklich ausgeschaltete Home-Steuerung bleiben erhalten. Der begrenzte Versuch wird privat protokolliert. Normale Wiederholungen verlängern den Versuch nicht. Erst nach Ablauf seiner 120 Sekunden, ohne bestätigte Bereitschaft oder unbekanntes Installer-Ergebnis, archiviert `--new-recovery-attempt` das vollständige alte Protokoll unter UUID/Hash und startet ausdrücklich einen neuen Versuch. Abgeschlossene Wiederherstellung bleibt idempotent; keine automatischen Wiederholungen. [Ablauf und Grenzen (Englisch)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.6.0: System Updater 1.2.0 ist für zulässige Neueinrichtungen oder den geprüften Ersatz von 1.1.0/1.1.1 mit `cytv replace-system-updater --edition root` vorgesehen. Nur System Updater wird ersetzt; Root-/Root-Updater-Apps, vollständiges Profil und Home-Auswahl bleiben erhalten, der alte Zustand wird archiviert. Unklare oder offene Vorgänge stoppen den Austausch. Installiertes 1.1.2 bleibt mit seinen alten Kanälen festgelegt; es gibt keine allgemeine Migration. Keinen Austausch erzwingen. Dies betrifft nicht die No-root-Feeds. [Ablauf (Englisch)](../RECOVERY.md#replace-the-root-system-updater-candidate)

## Hilfe und weitere Anleitungen

**1.6.0:** Wählen Sie **Wiederherstellungsoptionen prüfen** für denselben gespeicherten TV oder führen Sie `cytv recover` aus. Prüfung und Änderungen erfordern getrennte Bestätigungen mit Nein als Vorgabe; `--yes` genehmigt sie nicht. Root fährt nur nach bestehenden Prüfungen fort. No-root bietet Entfernen nur an, wenn die bestehende Paketdienstprüfung es zulässt; Home-Einstellungen können verloren gehen. Eine neue Einrichtung startet nie automatisch. Bei unbekanntem Zustand oder verweigertem Zugriff Bericht speichern und stoppen. Journale behalten und Entfernen nicht wiederholen. Die fehlenden Abschlussnachweise in #201 und Gerätebestätigung in #216 bleiben offen. [Recovery](../RECOVERY.md). Für Hilfe Modell, Firmware, Edition, Installer-Version, fehlgeschlagenen Schritt und erwartetes/tatsächliches Verhalten angeben; Bericht vor dem Teilen prüfen und Geheimnisse entfernen.

1.7.0: Eine vor der ersten Paketanfrage gestoppte No-root-Entfernung kann ohne Zugriff auf den globalen Paketstatus fortgesetzt werden, wenn das ursprüngliche Journal dies belegt. Entfernung gesondert bestätigen; nach verifizierter Entfernung die Installation separat starten. Unbekannte oder bereits gesendete Vorgänge bleiben gesperrt. Verbindung und Journale behalten. Nicht in 1.6.0 enthalten. [Details](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased).

[Dokumentation](../README.md) · [Problem melden](../FEEDBACK.md)

In Entwicklung: Wurde noch keine Paketentfernung angefordert, bietet eine fehlgeschlagene Entfernung **Wiederherstellungsoptionen prüfen** für denselben gespeicherten TV an. Prüfung und Entfernung erfordern getrennte Bestätigungen. Eine abgelehnte Paketstatusprüfung stoppt die Wiederherstellung und bietet einen Bericht an. Dessen `recovery`-Zusammenfassung unterscheidet nicht begonnene Entfernung, übernommene Vorgänge und unterbrochene Paketvorgänge ohne das vollständige Journal offenzulegen; sie erlaubt keine Wiederherstellung.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="optionales-python-für-root-in-v110"></a>
<a id="lg-firmware-sperre-in-120"></a>
<a id="neu-in-130-geführte-desktop-wiederherstellung"></a>
<a id="neu-in-130--12"></a>
<a id="unveröffentlichter-kandidat-root-über-homebrew-einrichten"></a>
<a id="unveröffentlichter-kandidat-hdmi-ton-wiederherstellen-root"></a>

<a id="designs-154"></a>

## Designs

In der Vorschau der nächsten Version zeigt **Home-Einstellungen → Hintergrundbilder** das Bild des aktiven Designs, erkannte TV-Fähigkeiten und den aktuellen Modus. Auto wählt eine kompatible Qualität; 4K, 1080p und Bild sind nur verfügbar, wenn das Design sie enthält. Bei Wiedergabeproblemen wird ein Bild angezeigt. Die Abdunklung lässt sich in 5-%-Schritten ändern; Zurücksetzen stellt die Designvorgaben wieder her. Classic und Designs ohne Bild zeigen dies ausdrücklich an.

Eigene Hintergrundbilder in der Vorschau der nächsten Version: In der CYTV-Desktop-App Hintergrundbilder öffnen, JPG/PNG auswählen, den Ausschnitt einstellen und die private TV-Adresse samt Empfangs-PIN aus Home eingeben. CYTV erstellt lokal ein stummes Video; 4K ist nur bei ausreichender Auflösung des Ausschnitts verfügbar. Am TV Empfang von CYTV oder Telefon-Upload wählen und im selben WLAN den QR-Code scannen. Das Telefon überträgt ein normales Bild bis 1920×1080 ohne native 4K-Videoebene; die Schärfe ist durch die Auflösung der TV-Oberfläche begrenzt. Den Hinweis vor dem Senden bestätigen, dann am TV Vorschau prüfen und anwenden. Eigene Uploads bleiben gespeichert und können unter Hintergrundbilder erneut ausgewählt oder entfernt werden. Abbruch oder abgelehnte Dateien behalten den bisherigen Hintergrund. Passende kommende Home-/Dienst- und CYTV-Builds sind erforderlich.

Kommende integrierte Hintergrundbilder: **Home-Einstellungen → Hintergrundbilder → Integrierte Hintergrundbilder → Black Hole**. Video von **Xecutioner**, mit Erlaubnis zur nichtkommerziellen Nutzung unter Namensnennung. Ein bestätigter Designwechsel aktiviert dessen eigenes Hintergrundbild; Black Hole und eigene Uploads bleiben erneut auswählbar. Der kontinuierliche 4K-Stream vermeidet Zurückspulen bei jeder Wiederholung; kompatibles Video/Bild bleibt als Ersatz verfügbar.

Android CYTV: **TV einrichten** · **Hintergrundbilder** · **Wartung**. Öffnen Sie am TV die Home-Einstellungen → Hintergrundbilder → Vom Telefon hochladen. Scannen Sie den QR-Code mit der Handykamera, wählen Sie JPG/PNG und übernehmen Sie das Bild am TV. Vom Telefon: Bilder bis 1920×1080, ohne natives 4K-Video. Für echtes 4K verwenden Sie CYTV am Computer.

1.7.0: **Einstellungen → Themes**. **Classic**, **Liquid Glass**, **Ribbon** sind integriert und benötigen keinen Design-Download; Classic bleibt Standard. **Channel** ist ein externes Showcase-Design. Beim Galerietest: Nach der Auswahl innerhalb von **20 Sekunden** **Design behalten** wählen. **Zurücksetzen**, Back oder Zeitablauf stellt das vorherige Design wieder her. Ein unterbrochener Versuch startet beim nächsten Home-Aufruf mit Classic. Integrierte und heruntergeladene Designs aus der installierten Liste werden sofort ohne Bestätigungstimer angewendet und gespeichert. Das gilt auch für vom Computer oder per URL installierte Designs. Nur Design testen in der Galerie startet einen 20-Sekunden-Test.

1.7.0: **Classic**, **Liquid Glass** und **Ribbon** sind integriert. **Alpine 1.4.4** wird im **Theme-Showcase** zum Download angeboten. Eine gespeicherte Auswahl `builtin:alpine` fällt mit dem bestehenden sichtbaren Wiederherstellungshinweis auf Classic zurück. Home lädt Alpine weder automatisch herunter noch ersetzt es durch Liquid Glass. Version 1.6.0 enthält Classic, Alpine und Ribbon.

Installierte Designs stehen in einer horizontal scrollbaren Reihe. Das aktive Design steht immer zuerst und seine Karte ist hervorgehoben. Mit Links/Rechts wechseln Sie zwischen den Karten.

Die Galerie zeigt nur auf diesem TV nicht installierte Designs. Classic, Liquid Glass, Ribbon und heruntergeladene Designs bleiben verborgen, auch bei einer neueren Katalogversion. Nach dem Entfernen erscheint das Design wieder. Updates erfolgen per URL oder Computerübertragung.

Die Designkarten sind direkt in Themes neben den Einstellungskategorien eingebettet. Katalog, Linkinstallation und Computerübertragung öffnen sich dort; nur ein Galerietest zeigt vorübergehend Home.

Beim Öffnen der Design-Galerie oder mit Aktualisieren wird der Hauptprojekt-Repository auf geprüfte Katalogupdates geprüft, ohne Home-Update oder Neuladen der Seite. Nach einem regulären Merge erscheinen neue Einträge; ein noch nicht integrierter Kandidat kann den mitgelieferten Katalog anzeigen. Offline oder bei Fehlern werden mitgelieferte Einträge und Vorschauen verwendet. Integrierte Designs entsprechen der installierten Home-Version. Vorschau öffnen und für Channel **Design herunterladen** wählen (Internet erforderlich). Nach dem Download testen und innerhalb von **20 Sekunden** **Design behalten** wählen. Installierte Designs funktionieren offline. **Per ID hinzufügen** bleibt für festgelegte Links verfügbar.

Für ein unveröffentlichtes Design zuerst am TV **Einstellungen → Themes → Vom Computer empfangen** öffnen. TV-Adresse und sechsstellige PIN dort im Computer-Vorschaufenster unter **Send to TV** eingeben, senden und am TV **Design anwenden** wählen. Die primäre Richtung nutzt eine ausgehende PC-Verbindung zu TV-TCP **8879**, ohne Computer-Firewalländerung. Beide Geräte müssen im selben vertrauenswürdigen Heimnetz sein. Der Empfänger schließt nach einem Upload, Abbruch, Verlassen der Ansicht oder **10 Minuten**. PINs werden nicht gespeichert; installierte Designs funktionieren offline. GitHub-Veröffentlichung ist nicht nötig.

Für ein veröffentlichtes Design unter **Weitere Optionen → Über URL hinzufügen** die ID (z. B. `102300a209`), `da.gd/102300a209` oder die vollständige GitHub-URL eingeben. Home zeigt vor dem Laden die ergänzte da.gd-Adresse und prüft danach GitHub-Ziel und Designpaket. Die ID steht in den Versionshinweisen oder unter **TV link → Copy ID** in der Computer-Vorschau.

**1.6.0:** **Diagnose anzeigen** im Home-Helper-Panel zeigt eine kleine, gefilterte Momentaufnahme seiner eigenen Statusabfragen. Das Anzeigen startet Helper nicht und ändert die Home-Steuerung nicht. Teilen Sie auf Anfrage nur die zuvor geprüfte JSON-Ausgabe; [Details](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

Anpassbare Leisten-Themen in 1.5.4 können Eingänge, WLAN und Einstellungen links unten platzieren. Wenn aktiviert, wählt Links bei der ersten sichtbaren App Einstellungen, dann WLAN und Eingänge; Rechts in den Einstellungen kehrt zur selben sichtbaren App zurück. Benötigt ein Thema eine neue Home-Funktion, wird seine Installation in einer nicht unterstützten Version abgelehnt; Aussehen und Auswahl bleiben erhalten. Aktualisieren Sie zuerst Home. Ein späteres Downgrade kann beim Start Classic wiederherstellen.

Designs zeigt Vorschauen der integrierten und aller selbst installierten Designs, auch offline. Die separate Schaltfläche für den Designkatalog öffnet veröffentlichte Designs; eine persönliche Installation veröffentlicht kein Design.

Darstellung enthält Spalten mit aktueller Anzahl und App-Einstellungen. Die separate Kategorie Themes enthält installierte Designs, die Galerie, den Empfang vom Computer und rechts Per ID hinzufügen (z. B. 102300a209). Classic wird über seine Karte gewählt; Downloads werden einzeln entfernt. In Sprache wird die Sprache direkt gewählt.

In der Browser-Vorschau erklärt Vom Computer empfangen die Schritte am Fernseher; auf dem Computer wird kein TV-Empfänger gestartet. Nutzen Sie Send to TV über der Vorschau. Das Entfernen eines heruntergeladenen Themes muss bestätigt werden. Beim aktiven Theme wird zuerst Classic wiederhergestellt. Abbrechen behält das Theme.

<a id="einstellungskategorien-unveröffentlichter-kandidat"></a>

## Einstellungskategorien (1.5.4)

In beiden Editionen stehen die Kategorien links und ihre Einstellungen rechts: Startbildschirm, Darstellung, Themes, Sprache, Software-Updates und Erweitert. No-root bietet zusätzlich Developer Mode; Root bietet LG-Firmware-Updates unter Software-Updates und HDMI-Ton unter Erweitert. Oben/Unten navigiert innerhalb einer Spalte, Rechts öffnet die Einstellungen und Links kehrt zu den Kategorien zurück. Zurück führt zuerst zu den Kategorien und schließt danach die Einstellungen. Tab erreicht auch die Schaltfläche zur Rückkehr zu Home.

Ein gelber Punkt bei Software-Updates und der zugehörigen Schaltfläche zeigt ein verfügbares Update an. Beide verschwinden, wenn eine erfolgreiche Prüfung kein Update bestätigt; bei einem Fehler bleibt der zuletzt bestätigte Stand erhalten.

<a id="automatische-grafikauflösung-kandidat"></a>

## Automatische Grafikauflösung (1.6.0)

Die Computer-/Android-Installer von 1.6.0 und migrierten OTA-Clients wählen 720p oder 1080p anhand der TV-Fähigkeit. Ist sie nicht überprüfbar, stoppt der Vorgang. Ältere separat installierte Updater benötigen die dokumentierte Migration am Computer; die Wiederherstellung behält ihre ursprünglichen Pakete.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** Bewahren Sie den Bericht des ursprünglichen Fehlversuchs auf. Neue Berichte trennen den gespeicherten ersten Fehler von späteren Prüfungen und enthalten eine gefilterte Doctor-/Statusübersicht. Auch nach erfolgreicher Einrichtung, Statusprüfung oder Wiederherstellung lässt sich ein Bericht speichern. Fehlende ältere Nachweise bleiben unbekannt; der Bericht erlaubt keine Wiederherstellungsaktion. [↗](../development/INSTALLER-DIAGNOSTICS.md).
