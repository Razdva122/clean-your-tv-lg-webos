# Čeština — rozhraní televizoru

> **1.8.0 — Nevydaný kandidát:** [1.8.0 / English](../RELEASE-1.8.0.md).

**Nevydaná C1 Beta (#298):** Ve společném instalačním programu pro počítač zvolte Root. Způsobilé TV C1 se rozpoznají automaticky; není potřeba samostatný instalátor ani přepínač. Tato cesta vyžaduje novou instalaci, nemá automatické aktualizace a dosud neprošla přejímkou na fyzickém C1. Otevřít LG Home, dlouhý Back nebo bezpečnostní/výpadková zastávka mohou ponechat ovládání Home vypnuté; v nastavení TV znovu zapněte Změnit Home. Běžná cesta Root se nemění. Pokud zůstávají další komponenty No-root, úplné odstranění C1 se zastaví před změnami. Nejdříve je odstraňte běžným postupem No-root; při nejasném stavu zachovejte data obnovy. [C1 Beta contract (English)](../development/C1-NATIVE-GATE.md).

Nevydáno (#290): **+ / Přidat aplikaci** nabídne živé TV pod názvem z televizoru pouze při zjištění nainstalovaného tuneru. Ostatní skryté systémové aplikace zůstávají vynechané. No-root potřebuje aktualizovaný Helper a instalátor; Root aktualizovaný balíček Home. Spuštění kanálů ještě vyžaduje ověření na TV.

**Nevydáno — překryv Ribbon:** Root podporuje Ribbon nad aktuálním obsahem. Integrace do stejného Home a Helperu No-root probíhá. Home otevře lištu; Zpět nebo další Home ji zavře. Nastavení a ostatní motivy jsou neprůhledné, ale přehrávání pod nimi může pokračovat. Neznámý kontext používá statické neprůhledné pozadí. Úplný scénář No-root ještě vyžaduje test konečných balíčků na TV; simulace v prohlížeči nepotvrzuje kompatibilitu. V No-root Zpět zavře i neprůhledný Home z karet aplikací po zavření nabídky a editoru. [Ribbon](../THEMES.md#ribbon-over-applications-unreleased).

Ribbon: podržte OK pro úpravy; ←/→ přesouvá kartu, ↑ vybere × (skrýt z Home), ↓ vrátí výběr na kartu, OK potvrdí a Back zruší. Aktuální pozadí zůstává.


**Nevydaný kandidát — zdroje při spuštění Root:** V Nastavení → Vaše domovská obrazovka zapněte **Změnit Home** a upravte **Otevřít Clean Your TV jako první**. **LG Channels / Živé TV** je ve výchozím nastavení zapnuté; **YouTube** a **HDMI** vypnuté. Při vypnutí změny Home zůstanou přepínače viditelné, ale nedostupné, a volby se zachovají. Nastavení se ukládá soukromě v tomto televizoru a není součástí přenosného exportu profilu. Jde o kandidáta, ne o ověřené spuštění či probuzení TV.

> Tento průvodce popisuje verzi 1.6.0. Dostupné balíčky stahujte z [publikovaných vydání GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). Čeština je dostupná v rozhraní TV, instalátory nadále nabízejí dvanáct jazyků. Ověření na TV a kontrola rodilým mluvčím dosud neproběhly. [Verze a omezení](../RELEASE-1.6.0.md).

[Dokumentace](../README.md) · [Jazyky](../LANGUAGES.md)

Tento průvodce popisuje české rozhraní Home a Root Home ve verzi 1.6.0,
nikoli český instalační program. Instalátory pro počítač, Android a Homebrew
nadále používají dosavadních dvanáct jazyků. Pro instalaci použijte
[anglický průvodce](en.md); nepoužívejte přepínač `--language cs`.
Samostatný Homebrew CYTV Installer zůstává nevydaný.

## Jazyk a ovládání

V náhledu příští verze zobrazuje **Nastavení Home → Tapety** tapetu aktivního motivu, zjištěné možnosti TV a aktuální režim. Auto volí kompatibilní kvalitu; 4K, 1080p a obrázek jsou dostupné jen podle obsahu motivu. Při potížích se zobrazí obrázek. Ztmavení se mění po 5 %; obnovení vrátí nastavení motivu. Classic a motivy bez tapety zobrazí tento stav výslovně.

Vlastní tapety v náhledu příští verze: v počítačovém CYTV otevřete Tapety, vyberte JPG/PNG, upravte výřez a zadejte místní adresu TV a přijímací PIN z nastavení Home. CYTV vytvoří video bez zvuku místně; 4K nabídne jen při dostatečném rozlišení výřezu. Na TV zvolte příjem z CYTV nebo nahrávání z telefonu a ve stejné Wi-Fi naskenujte QR kód. Telefon posílá běžný obrázek nejvýše 1920×1080 bez nativní 4K video vrstvy; ostrost omezuje rozlišení rozhraní TV. Před odesláním potvrďte upozornění, pak na TV zkontrolujte náhled a použijte tapetu. Vlastní obrázky zůstávají uložené a lze je znovu vybrat nebo odstranit v Tapetách. Zrušení či odmítnutý soubor zachová dosavadní pozadí. Jsou nutná odpovídající připravovaná sestavení Home/služby a CYTV.

Vlastní pohyblivé video (náhled příští verze): v počítačovém CYTV → Tapety vyberte MP4/MOV/MKV/WebM, 1–60 sekund, do 512 MiB a 3840×2160. Zvuk se odstraní a obraz se ořízne uprostřed na 16:9. Menší videa používají kompatibilní výstup 1080p; UHD vyžaduje dostatečný zdrojový výřez. Odešlete přes adresu/PIN TV, potom zkontrolujte a použijte na TV. Z telefonu nadále jen JPG/PNG. Ověření finálního balíčku a fyzického TV zatím čeká.

Připravované vestavěné tapety: **Nastavení Home → Tapety → Vestavěné tapety → Black Hole**. Autor videa: **Xecutioner**; povoleno nekomerční použití s uvedením autora. Potvrzení jiného motivu obnoví jeho vlastní tapetu. Black Hole i vlastní obrázky lze vybrat znovu. Souvislý 4K stream nepřetáčí video při každém opakování; k dispozici je kompatibilní video nebo obrázek.

Android CYTV: **Nastavit TV** · **Tapety** · **Údržba**. Na TV otevřete nastavení Home → Tapety → Nahrát z telefonu. Naskenujte QR fotoaparátem telefonu, vyberte JPG/PNG a použijte tapetu na TV. Telefon odesílá obrázek do 1920×1080 bez nativního 4K videa; pro skutečné 4K použijte CYTV na počítači.

Na televizoru otevřete **Settings → Language → Čeština**. Po změně se Home
znovu načte. Volba **Automaticky (jazyk systému)** používá jazyk televizoru;
rozpozná i `cs-CZ`. Jazyk instalátoru a televizoru se ukládá samostatně.
Názvy aplikací, produktů a technické identifikátory se nepřekládají.

Šipkami vyberte položku, tlačítkem OK ji otevřete a tlačítkem Zpět zavřete
panel. V nabídce **Nastavení** najdete vzhled, motivy, jazyk, aktualizace a
pokročilé možnosti. Přepínač Home určuje, kam vás tlačítko Home a návrat
z aplikací přivedou. **Otevřít LG Home** otevře původní prostředí jednou;
uložená volba Home se nezmění. Podržení tlačítka Zpět po dobu 1,2 sekundy
rovněž otevře LG Home.

Při problému s ovládáním třikrát rychle stiskněte Home — nouzové vypnutí
obnoví LG Home. U starších verzí Helper do 0.6.13 se používá dlouhé podržení
Home. Nouzové vypnutí se automaticky neruší; ovládání Home znovu zapněte
pouze vlastním výslovným rozhodnutím.

## Aktualizace a obnovení

Před potvrzením aktualizace si přečtěte zobrazené informace. Nechte televizor
zapnutý. Aplikace a nastavení se před aktualizací uloží. Pokud výsledek není
potvrzený, otevřete samostatnou aplikaci Home Updater nebo Root Updater a
nejprve obnovte stav; neopakujte ihned instalaci.

Návrat k předchozí verzi je možný jen tehdy, když jej nástroj nabídne.
Obnoví i nastavení před aktualizací; pozdější změny nastavení budou ztraceny.
Obnovení zůstává blokováno, dokud se instalační program prokazatelně nezastaví.
Uchovejte záznamy obnovení a použijte [postup obnovení v angličtině](../RECOVERY.md).

No-root vyžaduje aktivní Developer Mode. Před vypršením časovače jej otevřete
a při připojení televizoru k internetu stiskněte EXTEND. Automatické
prodlužování je Beta, ve výchozím stavu vypnuté; kontrolujte oficiální časovač.
Root vyžaduje již existující root přístup. Instalační program televizor nerootuje.

Ve verzi 1.6.0 zobrazí **Zobrazit diagnostiku** v panelu Home Helper filtrovaný výsledek jeho vlastních dotazů na stav. Zobrazení nespustí Helper a nezmění ovládání Home. Na vyžádání sdílejte pouze zkontrolovaný JSON; [podrobnosti v angličtině](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

Překlad byl ověřen automatickými kontrolami a v počítačovém prohlížeči.
Ověření rodilým mluvčím a na fyzickém televizoru zatím neproběhlo.
Kompatibilita závisí na konkrétním modelu, firmwaru a ovladači.

[Kompatibilita (anglicky)](../COMPATIBILITY.md) ·
[Zpětná vazba (anglicky)](../FEEDBACK.md) ·
[Technické podklady (anglicky)](../development/README.md)

<a id="automatické-rozlišení-grafiky-kandidát"></a>

## Automatické rozlišení grafiky (1.6.0)

Instalátory 1.6.0 pro počítač/Android a migrovaní klienti OTA volí 720p nebo 1080p podle schopností TV. Pokud je nelze ověřit, operace se zastaví. Starší samostatně instalované aktualizátory vyžadují popsanou migraci z počítače; obnova zachová původní balíčky.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).
