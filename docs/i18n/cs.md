# Čeština — rozhraní televizoru

> Zmrazený kandidát 1.6.0 ještě není vydán; stabilní verze zůstává 1.5.4. Čeština je dostupná v rozhraní TV, instalátory nadále nabízejí dvanáct jazyků. Ověření na TV a kontrola rodilým mluvčím dosud neproběhly. [Verze a omezení](../RELEASE-1.6.0.md).

[Dokumentace](../README.md) · [Jazyky](../LANGUAGES.md)

**Připravované vydání:** čeština zatím není součástí zveřejněné stabilní verze.
Tento průvodce popisuje rozhraní Home a Root Home v připravovaném vydání,
nikoli český instalační program. Instalátory pro počítač, Android a Homebrew
nadále používají dosavadních dvanáct jazyků. Pro instalaci použijte
[anglický průvodce](en.md); nepoužívejte přepínač `--language cs`.

## Jazyk a ovládání

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

V připravovaném vydání zobrazí **Zobrazit diagnostiku** v panelu Home Helper filtrovaný výsledek jeho vlastních dotazů na stav. Zobrazení nespustí Helper a nezmění ovládání Home. Na vyžádání sdílejte pouze zkontrolovaný JSON; [podrobnosti v angličtině](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

Překlad byl ověřen automatickými kontrolami a v počítačovém prohlížeči.
Ověření rodilým mluvčím a na fyzickém televizoru zatím neproběhlo.
Kompatibilita závisí na konkrétním modelu, firmwaru a ovladači.

[Kompatibilita (anglicky)](../COMPATIBILITY.md) ·
[Zpětná vazba (anglicky)](../FEEDBACK.md) ·
[Technické podklady (anglicky)](../development/README.md)

## Automatické rozlišení grafiky (kandidát)

Připravované instalátory pro počítač/Android a migrovaní klienti OTA volí 720p nebo 1080p podle schopností TV. Pokud je nelze ověřit, operace se zastaví. Starší samostatně instalované aktualizátory vyžadují popsanou migraci z počítače; obnova zachová původní balíčky.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).
