# Clean Your TV — Benutzeranleitung

> v1.5.0: Designs, Galerie und PC-TV-Übertragung. Bekannte Root-Grenzen: Appearance kann um 110 px springen; Home startet nach Standby möglicherweise nicht automatisch. Die Geräteprüfung bleibt begrenzt. [1.5.0](../RELEASE-1.5.0.md).

[Dokumentation](../README.md) · [Problem melden](../FEEDBACK.md)

Diese Anleitung gilt für die veröffentlichte **[1.4.1](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.4.1)**. Die C3-Abnahme umfasst die dokumentierten Strom-, Home-, Fokus-, Aus-Zustand- und manuellen Rollback-Tests. Andere TVs, eARC-Audio und echte Android-Geräte sind nicht bestätigt; eine erfolgreiche Installation beweist keine Kompatibilität. [Prüfumfang (Englisch)](../RELEASE-1.4.0-ACCEPTANCE.md).

## Edition wählen

No-root und Root sind gleichwertige Optionen für unterschiedliche TV-Konfigurationen. Wählen Sie No-root für LG Developer Mode oder Root für vorhandenen Root-Zugriff per SSH. Kompatibilität und Testumfang hängen von der jeweiligen Edition ab.

- **No-root:** LG Developer Mode und Key Server einschalten. Die am Fernseher angezeigte Passphrase eingeben und die separate Kopplungsanfrage am Fernseher bestätigen. Developer Mode muss aktiv bleiben: Bei Ablauf können nachinstallierte Apps entfernt werden. Den offiziellen Timer auch mit aktivierter Beta-Verlängerung kontrollieren. Die Überwachung durch Helper benötigt das lokale Netzwerk.
- **Root:** Bereits vorhandener Root-Zugang über SSH ist nötig. Der Installer richtet keinen Root-Zugang ein. Developer Mode nicht auf einem bereits gerooteten Fernseher aktivieren. Root-Zugang und Wiederherstellungsdienste verfügbar halten.

Root benötigt funktionierende Home-Schnittstellen von Settings Service und System Profile (`com.webos.service.systemprofile`); vorhandener Root-Zugriff allein bestätigt keine Kompatibilität.

## Voraussetzungen

Fernseher einschalten und mit demselben vertrauenswürdigen Heimnetz wie den Computer verbinden. Danach muss der Computer nicht eingeschaltet bleiben. Die Kompatibilität hängt von Modell, Firmware und Fernbedienung ab; für Root stehen noch Gerätetests aus.

Node 0.10.25 gilt für den unveröffentlichten Quell-/Testbuild; veröffentlichte Installer benötigen weiterhin 0.12.2+. Siehe [Kompatibilität](../COMPATIBILITY.md).

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

Der Desktop-Assistent verwendet zunächst die Systemsprache und speichert eine ausdrückliche Auswahl. Am Fernseher unter **Einstellungen → Sprache** die gewünschte Sprache oder die automatische Systemauswahl wählen. Die Spracheinstellungen von Installer und Fernseher sind unabhängig. Alle Sprachcodes stehen im [Sprachverzeichnis](../LANGUAGES.md).

Für die separat heruntergeladene CLI unter macOS/Linux im entpackten Verzeichnis:

```sh
chmod +x cytv
./cytv --language de install
```

Fernseher oder IP-Adresse und Edition auswählen, dann die Zusammenfassung prüfen. Einer neuen SSH-Identität nur für den eigenen Fernseher im vertrauenswürdigen Netz zustimmen; ein geänderter gespeicherter Schlüssel blockiert den Zugang. Root aktiviert Home nach Einrichtung der Wiederherstellung sofort, ohne Testphase oder Behalten-Schritt. Pfeile, OK, Home, Zurück/Abbrechen, Lautstärke, Bereitschaft und Kaltstart am eigenen Fernseher testen.

## Bedienung und Wiederherstellung

Pfeile wählen eine Kachel, OK öffnet sie; OK gedrückt halten zum Verschieben. Kurzes Zurück behält Navigation und Beendigungsdialog der App bei. Kurzes Home öffnet bei aktiver Home-Steuerung den Launcher. Zurück 1,2 Sekunden gedrückt halten, um LG Home einmalig zu öffnen. Der Home-Schalter und Ihre Einstellungen bleiben unverändert.

**Home innerhalb von zwei Sekunden dreimal kurz drücken**, dazwischen loslassen. Dies stellt LG Home wieder her und stoppt die Steuerung, ohne Einstellungen zurückzusetzen. Beim älteren No-root Helper bis einschließlich 0.6.13 stattdessen Home etwa zwei Sekunden halten. Langes Home ist nicht die Root-Notfallgeste.

No-root: Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten. Root: **Home ändern** in den Home-Einstellungen einschalten, um fortzufahren. **LG Home öffnen** öffnet LG Home einmalig, ohne das Home-Ziel zu ändern. Für LG Home als dauerhaftes Ziel **Home ändern** ausschalten oder `cytv restore` ausführen. Beide Steuerungen nie gleichzeitig betreiben. Bei wiederholtem Fehler LG Home aktiv lassen.

```sh
./cytv --language de status
./cytv --language de doctor --report
./cytv --language de restore
./cytv --language de uninstall
```

Nach einer Unterbrechung zuerst `status` ausführen und Protokolle behalten. `restore` stellt LG Home ohne App-Entfernung wieder her; `uninstall` stellt es vor der Entfernung wieder her. Root-Wiederherstellungsdaten bleiben absichtlich erhalten; nicht zum Erzwingen einer Neuinstallation löschen. Diagnoseberichte vor Weitergabe prüfen; Schlüssel und Profilordner nicht veröffentlichen.

Nur im unveröffentlichten Kandidaten, in beiden Editionen: Öffne **Home-Einstellungen → Darstellung → Spalten** und wähle 1–8 Spalten oder **Nach Theme**, um dessen Wert zu verwenden (Classic: 5). Eine feste Zahl hat Vorrang vor dem Theme. Themes mit festem Layout blenden die Spaltenoption aus und verwenden den Wert des Autors. Deine gespeicherte Auswahl gilt wieder, sobald du zu einem Theme wechselst, das diese Einstellung unterstützt. In der Alpine-Kandidatenvorschau liegen Apps in einem endlosen horizontalen Band: Links/Rechts blättert im Kreis, Oben öffnet die Schnellzugriffe und Unten kehrt zur selben App zurück. In der Alpine-Vorschau lässt sich das Band auch mit Mausrad oder Touchpad bewegen; bei geöffnetem Dialog bleibt Home stehen.

Unveröffentlichter Kandidat, beide Editionen: Schalte unter **Home-Einstellungen → Darstellung** die Option **Kachel „App hinzufügen“ anzeigen** aus, um + auszublenden. Standardmäßig ist sie eingeschaltet. Über **App hinzufügen** im selben Bereich kannst du weiterhin Apps hinzufügen oder zurückholen. Verschieben und Ausblenden bleiben möglich; die Auswahl bleibt nach einem Neustart erhalten. Sind alle Apps ausgeblendet, bleiben die oberen Schaltflächen und Einstellungen erreichbar.

In Theme-Vorschauen des unveröffentlichten Kandidaten mit optionaler Seitenleiste wählst du mit Oben/Unten einen Menüpunkt, wechselst mit Rechts zu den Apps und kehrst mit Links aus der ersten App-Spalte zum Menü zurück.

No-root 1.5.0: Helper kann sich nach einem vorübergehenden Watchdog-Timeout beim Aufwachen erholen, höchstens fünfmal in zehn Minuten. Stop und dreifaches Home erfordern weiterhin einen ausdrücklichen Start Helper; wiederholte Fehler lassen Helper gestoppt. Die TV-Abnahme steht aus. [Verhalten und Grenzen (Englisch)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Aktualisierung und Entfernung

Funktionierende Pakete und private Einstellungssicherungen behalten. Bei No-root-Paketersatz vom Computer zuerst Helper stoppen und ohne vorherige Deinstallation aktualisieren, da diese Einstellungen löschen kann. Das Entfernen der Desktop-App entfernt keine TV-Apps. Keine einzelne IPK über eine aktive Root-Laufzeit installieren; den ausdrücklichen Wiederherstellungs- oder Neuinstallationsablauf von cytv verwenden.

Home-Einstellungen → Software-Updates öffnen und angebotene Versionen vor der Bestätigung prüfen. Updates/Rollback am TV benötigen **Root, Homebrew Channel** und vorbereitete passende Updater, auch bei der No-root-Edition. Ohne Root den Computer-Installer verwenden. Vollständige Systemupdates werden separat ausdrücklich vorbereitet: [Updates (Englisch)](../UPDATES.md). Unter Wiederherstellung steht die gespeicherte Rollback-Version; spätere Einstellungsänderungen können verloren gehen.

**Bestehende 1.3.0:** Der ursprüngliche System Updater kann 1.4.0 wegen des geänderten erlaubten Dateibestands nicht installieren. Stoppt ein Versuch vor dem Austausch, Journal behalten und aufhören; Zustand nicht löschen oder blind wiederholen. Für den Wechsel geprüfte Wiederherstellung und frische 1.4.0-Einrichtung verwenden. Ein reines App-Update ersetzt keine behaltenen Root-Treiber. Die nächste OTA-Korrektur ist **noch nicht veröffentlicht**. [Umstieg und Wiederherstellung (Englisch)](../UPDATES.md#one-time-computer-preparation).

Unveröffentlichte Korrektur des Home-Einstellungskanals: Home und Helper gemeinsam aktualisieren, sobald ein abgestimmter Kandidat verfügbar ist. Ein reines Home-Update reicht nicht aus. Die TV-Abnahme des endgültigen Release-Builds steht noch aus. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Root-HDMI-Tonwiederherstellung ist experimentell und **standardmäßig aus**; nur bei Bedarf aktivieren. Sie kann funktionierenden Ton unterbrechen und bestätigt keine eARC-Kompatibilität. [Tonwiederherstellung (Englisch)](../development/ROOT-AUDIO-RECOVERY.md). Der separate **CYTV Installer für Homebrew ist noch unveröffentlicht**; den veröffentlichten Computer-/Android-Installer verwenden.

Nur unveröffentlichter Kandidat: Bei verweigertem Firmware-API-Zugriff wegen alter beschreibbarer Root-Verzeichnisse prüft `cytv enable-firmware-access --edition root --repair-package-permissions` das aktuelle Paket anhand vertrauenswürdiger privater Daten und entfernt Schreibrechte für Gruppe/andere nur aus Root-eigenen Pfaden. Unbekannte oder veränderte Dateien stoppen die Reparatur. Profil, Home-Auswahl und Firmware-Sperre bleiben erhalten; [Details (Englisch)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

Nur im unveröffentlichten Kandidaten: `cytv recover-system-rollback --edition root` hilft bei einem geprüften Root-Rollback, wenn alle Paketinstallationen beendet sind, aber die Launcher-Bereitschaft abläuft. Der echte Launcher muss seine Bereitschaft bestätigen; unbekannte Installer-Ergebnisse werden abgelehnt. Pakete, festgelegter Code/Schlüssel, Fehlernachweise und ausdrücklich ausgeschaltete Home-Steuerung bleiben erhalten. Der begrenzte Versuch wird privat protokolliert. Normale Wiederholungen verlängern den Versuch nicht. Erst nach Ablauf seiner 120 Sekunden, ohne bestätigte Bereitschaft oder unbekanntes Installer-Ergebnis, archiviert `--new-recovery-attempt` das vollständige alte Protokoll unter UUID/Hash und startet ausdrücklich einen neuen Versuch. Abgeschlossene Wiederherstellung bleibt idempotent; keine automatischen Wiederholungen. [Ablauf und Grenzen (Englisch)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0: Das Austauschpaket enthält System Updater 1.1.2. Vor TV-OTA die Version 1.1.0 oder 1.1.1 ausdrücklich mit `cytv replace-system-updater --edition root` ersetzen. Nur System Updater wird ersetzt; Root-/Root-Updater-Apps, vollständiges Profil und Home-Auswahl bleiben erhalten, der alte Zustand wird archiviert. Unbekannte oder offene Vorgänge stoppen den Austausch. Diese Bedingung sperrt keine No-root-Feeds. [Ablauf (Englisch)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Hilfe und weitere Anleitungen

Nach Fehlern oder Unterbrechungen Status prüfen und den Diagnosebericht dieses Versuchs speichern. Geführte Wiederherstellung fragt Entfernung und Neuinstallation getrennt ab. Bei unklarem Ergebnis aufhören und private Protokolle, Journale und Wiederherstellungsdateien behalten; niemals für einen neuen Versuch löschen. [Wiederherstellung (Englisch)](../RECOVERY.md). Für Hilfe Modell, Firmware, Edition, Installer-Version, fehlgeschlagenen Schritt und erwartetes/tatsächliches Verhalten angeben; Bericht vor dem Teilen prüfen und Geheimnisse entfernen.

[Dokumentation](../README.md) · [Problem melden](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="optionales-python-für-root-in-v110"></a>
<a id="lg-firmware-sperre-in-120"></a>
<a id="neu-in-130-geführte-desktop-wiederherstellung"></a>
<a id="neu-in-130--12"></a>
<a id="unveröffentlichter-kandidat-root-über-homebrew-einrichten"></a>
<a id="unveröffentlichter-kandidat-hdmi-ton-wiederherstellen-root"></a>


## Designs – Entwicklungskandidat

Im Kandidaten mit Design-Unterstützung: **Einstellungen → Darstellung**. **Classic** und **Alpine** sind integriert und benötigen keinen Design-Download; Classic bleibt Standard. **Channel** ist ein externes Showcase-Design. Beim Galerietest: Nach der Auswahl innerhalb von **20 Sekunden** **Design behalten** wählen. **Zurücksetzen**, Back oder Zeitablauf stellt das vorherige Design wieder her. Ein unterbrochener Versuch startet beim nächsten Home-Aufruf mit Classic. Integrierte und heruntergeladene Designs aus der installierten Liste werden sofort ohne Bestätigungstimer angewendet und gespeichert. Das gilt auch für vom Computer oder per URL installierte Designs. Nur Design testen in der Galerie startet einen 20-Sekunden-Test.

Installierte Designs stehen in einer horizontal scrollbaren Reihe. Das aktive Design steht immer zuerst und seine Karte ist hervorgehoben. Mit Links/Rechts wechseln Sie zwischen den Karten.

Die Galerie zeigt nur auf diesem TV nicht installierte Designs. Classic, Alpine und heruntergeladene Designs bleiben verborgen, auch bei einer neueren Katalogversion. Nach dem Entfernen erscheint das Design wieder. Updates erfolgen per URL oder Computerübertragung.

Die Designkarten sind direkt in Darstellung neben den Einstellungskategorien eingebettet. Katalog, Linkinstallation und Computerübertragung öffnen sich dort; nur ein Galerietest zeigt vorübergehend Home.

Beim Öffnen der Design-Galerie oder mit Aktualisieren wird der Hauptprojekt-Repository auf geprüfte Katalogupdates geprüft, ohne Home-Update oder Neuladen der Seite. Nach einem regulären Merge erscheinen neue Einträge; ein noch nicht integrierter Kandidat kann den mitgelieferten Katalog anzeigen. Offline oder bei Fehlern werden mitgelieferte Einträge und Vorschauen verwendet. Integrierte Designs entsprechen der installierten Home-Version. Vorschau öffnen und für Channel **Design herunterladen** wählen (Internet erforderlich). Nach dem Download testen und innerhalb von **20 Sekunden** **Design behalten** wählen. Installierte Designs funktionieren offline. **Per URL hinzufügen** bleibt für festgelegte Links verfügbar.

Für ein unveröffentlichtes Design zuerst am TV **Einstellungen → Darstellung → Vom Computer empfangen** öffnen. TV-Adresse und sechsstellige PIN dort im Computer-Vorschaufenster unter **Send to TV** eingeben, senden und am TV **Design anwenden** wählen. Die primäre Richtung nutzt eine ausgehende PC-Verbindung zu TV-TCP **8879**, ohne Computer-Firewalländerung. Beide Geräte müssen im selben vertrauenswürdigen Heimnetz sein. Der Empfänger schließt nach einem Upload, Abbruch, Verlassen der Ansicht oder **10 Minuten**. PINs werden nicht gespeichert; installierte Designs funktionieren offline. GitHub-Veröffentlichung ist nicht nötig.

Für ein veröffentlichtes Design unter **Weitere Optionen → Über URL hinzufügen** die ID (z. B. `102300a209`), `da.gd/102300a209` oder die vollständige GitHub-URL eingeben. Home zeigt vor dem Laden die ergänzte da.gd-Adresse und prüft danach GitHub-Ziel und Designpaket. Die ID steht in den Versionshinweisen oder unter **TV link → Copy ID** in der Computer-Vorschau.

Veröffentlichte Pakete enthalten diese Funktion möglicherweise noch nicht. Browserprüfungen sind kein TV-Kompatibilitätsnachweis. [Vollständige Anleitung](../THEMES.md).

Designs zeigt Vorschauen der integrierten und aller selbst installierten Designs, auch offline. Die separate Schaltfläche für den Designkatalog öffnet veröffentlichte Designs; eine persönliche Installation veröffentlicht kein Design.

Im Appearance-Kandidaten zeigen große Vorschaubilder die installierten Themes und markieren das ausgewählte. Theme showcase und Receive from computer sind die Hauptaktionen. More options enthält Add by URL, Restore Classic und Clear downloaded themes. Pfeiltasten bewegen den Fokus zwischen Karten und Schaltflächen; Links am Rand führt zu den Kategorien.

In der Browser-Vorschau erklärt Vom Computer empfangen die Schritte am Fernseher; auf dem Computer wird kein TV-Empfänger gestartet. Nutzen Sie Send to TV über der Vorschau. Das Entfernen eines heruntergeladenen Themes muss bestätigt werden. Beim aktiven Theme wird zuerst Classic wiederhergestellt. Abbrechen behält das Theme.

<a id="einstellungskategorien-unveröffentlichter-kandidat"></a>

## Einstellungskategorien (1.5.0)

In beiden Editionen stehen die Kategorien links und ihre Einstellungen rechts: Startbildschirm, Darstellung (Themes und Spalten), Sprache, Software-Updates und Erweitert. No-root bietet zusätzlich Developer Mode; Root bietet LG-Firmware-Updates unter Software-Updates und HDMI-Ton unter Erweitert. Oben/Unten navigiert innerhalb einer Spalte, Rechts öffnet die Einstellungen und Links kehrt zu den Kategorien zurück. Zurück führt zuerst zu den Kategorien und schließt danach die Einstellungen. Tab erreicht auch die Schaltfläche zur Rückkehr zu Home.

Ein gelber Punkt bei Software-Updates und der zugehörigen Schaltfläche zeigt ein verfügbares Update an. Beide verschwinden, wenn eine erfolgreiche Prüfung kein Update bestätigt; bei einem Fehler bleibt der zuletzt bestätigte Stand erhalten.
