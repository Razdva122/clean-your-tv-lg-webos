# Clean Your TV — průvodce instalací

Clean Your TV je vaše vlastní domovská obrazovka pro LG webOS: aplikace ve vašem pořadí, bez sponzorovaných řádků v této nabídce. Instalujte z počítače nebo telefonu s Androidem; po nastavení může být počítač vypnutý.

## 1. Stáhněte instalátor

Klikněte na obrázek svého zařízení. Tlačítka stahují nejnovější zveřejněné vydání. Na Macu vyberte Apple Silicon (M1 nebo novější) nebo Intel; typ najdete v nabídce Apple → O tomto Macu.

[![Stáhnout — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Stáhnout — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Stáhnout — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Stáhnout — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Stáhnout — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

## 2. Připravte televizor

Zapněte TV a připojte ji ke stejné domácí síti jako počítač nebo telefon. Na vyžádání povolte aplikaci CYTV přístup k místní síti.

- **No-root** — pokud nemáte root přístup. Připravte Developer Mode podle kroků níže.
- **Root** — pokud už máte root přístup přes SSH. Instalátor televizor nerootuje. Na této TV nezapínejte Developer Mode; zachovejte SSH přístup a data obnovy.

Pokud instalátor nabídne **No-root**, můžete pokračovat přes stávající root připojení SSH bez zapínání Developer Mode.

[Podrobná instalace](../INSTALL.md) · [Kompatibilita](../COMPATIBILITY.md)

### Developer Mode (No-root)

1. V TV otevřete LG Apps, vyhledejte **Developer Mode** a nainstalujte ho.
2. Otevřete Developer Mode a přihlaste se účtem LG Developer. Účet si můžete vytvořit na [LG Developer](https://webostv.developer.lge.com).
3. Zapněte **Dev Mode Status**. TV se restartuje; poté Developer Mode znovu otevřete.
4. Zapněte **Key Server** a ponechte Developer Mode otevřený. **IP Address** je adresa TV, kterou zadáte do CYTV.
5. Použijte šestiznakový kód **Passphrase** z obrazovky TV. Rozlišujte velká a malá písmena.

Použijte kód z TV, nikoli heslo účtu LG. Pokud kód nevidíte, zapněte Key Server. Při samostatné žádosti o párování povolte CYTV dálkovým ovladačem. Pokud TV žádost odmítne, potvrďte v CYTV opakování párování se stejným televizorem.

Pokud televizor odmítne připojení k dálkovému ovládání, nechte ho zapnutý a ověřte přístup k portu TCP 3001 z počítače. Potom v počítačovém instalátoru zvolte **Zkusit znovu**.

Pokud při první instalaci No-root instalátor upozorní, že nemohl načíst vstupy HDMI, můžete pokračovat s nalezenými aplikacemi.

Před vypršením časovače otevřete Developer Mode a při připojení TV k internetu stiskněte **EXTEND**. Po vypršení může LG takto instalované aplikace odstranit.

## 3. Otevřete instalátor

- **Windows x64:** rozbalte celý `cytv-windows-x64-desktop.zip` pomocí **Extrahovat vše** a otevřete `cytv-desktop/cytv-desktop.exe`. Ponechte vedle něj složku `_internal`.
- **macOS 13+:** rozbalte ZIP pro Apple Silicon nebo Intel, přesuňte `cytv.app` do Aplikací a otevřete ji. Povolte místní síť. Pokud macOS zablokuje důvěryhodné stažení z projektu, použijte **Soukromí a zabezpečení → Přesto otevřít**. Nevypínejte Gatekeeper.
- **Linux x64:** na Ubuntu 22.04+, Debianu 12+ nebo Mintu 21+ otevřete `cytv-linux-x64.deb` ve správci balíčků, nainstalujte ho a spusťte Clean Your TV z nabídky aplikací. Ke stažení knihoven může být potřeba internet. Balíček pro Linux ARM není k dispozici.
- **Android ARM64:** potřebujete 64bitový ARM telefon s Androidem 7+ a WebView/Chrome 108+. Otevřete APK, na vyžádání povolte instalaci z tohoto zdroje a spusťte CYTV. Aktualizujte bez odinstalování nebo mazání dat.

Jazyk vyberte v instalátoru; na Androidu je volba vpravo nahoře. Jazyk TV se nastavuje zvlášť v **Nastavení → Jazyk**. Pokud vaše stažená aplikace ještě nenabízí **Čeština**, zvolte **English**; tento postup platí i pro ni.

## 4. Nainstalujte na TV

1. V CYTV zvolte nastavení TV (**Set up my TV**). Na počítači vyberte nalezenou TV; na Androidu zadejte její IP adresu. Pokud hledání nic nenajde, zadejte adresu ručně.
2. Vyberte **No-root** nebo **Root** a před pokračováním zkontrolujte televizor.
3. No-root: zadejte kód z Developer Mode a potvrďte žádost na TV. Root: použijte svůj stávající SSH přístup. Novou SSH identitu potvrďte pouze pro vlastní TV v důvěryhodné síti. Pokud se uložený klíč změnil, zastavte se a zjistěte příčinu.
4. Postupujte podle průvodce. Nechte TV zapnutou, neměňte síť a nezavírejte CYTV do dokončení. Na Androidu nevynucujte ukončení aplikace.

V instalátoru pro počítač po úspěšné kontrole připojení zvolte **Pokračovat v nastavení**. Zachová se stejné připojení k televizoru a edice. Průvodce vysvětlí stav předchozí instalace; technické výsledky jsou v podrobnostech. Pokud předchozí operace vyžaduje obnovení, nejprve použijte nabídnutou akci obnovení. Průvodce před změnami zkontroluje nainstalované verze a požádá o potvrzení. Uložené požadavky na restart se znovu ověřují; průvodce požádá o restart pouze tehdy, když ho vyžaduje aktuální čištění.

Pokud instalátor Root nabídne nahrazení současné integrace Home, potvrďte je jen tehdy, pokud chcete obnovit LG Home a pokračovat. Při odmítnutí zůstane současný Home aktivní.

Při instalaci Root instalátor podle potřeby automaticky použije ověřené interní dočasné úložiště; USB disk není potřeba, a pokud kontrola úložiště selže, ponechte data pro obnovení a uložte diagnostickou zprávu.

### Pokud už je na televizoru otevřený CYTV Installer

Zvolte **Nainstalovat a aktivovat** a jednou potvrďte. Instalátor společně nainstaluje Root Home, Root Updater a System Updater. Tlačítko Home pak otevře Root Home, pokud není aktivní nouzové vypnutí. Pokud vás instalátor při nastavování Root odkáže na počítač, pokračujte tam. Nabídne-li No-root, použijte instalátor na počítači nebo zařízení se systémem Android.

Po instalaci se v Root Home otevře **Nastavit televizor**. V nabídce **Motivy** vyberte vestavěný motiv. V nabídce **Upravit nastavení LG** označte reklamy a doporučení, které chcete změnit, zvolte **Použít vybraná nastavení** a zkontrolujte výsledek každé změny. Chcete-li vrátit uložené původní hodnoty, označte položky a zvolte **Obnovit vybraná nastavení**. Chcete-li přejít na domovskou obrazovku, zvolte **Otevřít Home**. Později můžete panel otevřít přes **Nastavení → Pokročilé → Nastavit televizor**.

Pokud instalátor ohlásí problém, postupujte podle pokynu na obrazovce. Volba pro uložení diagnostické zprávy uloží kopii v televizoru. Uloženou zprávu pak můžete otevřít v instalátoru nebo v nabídce obnovení dlaždice a přečíst si ji či naskenovat její QR kód telefonem. Seznam ukazuje hotové kontroly, aktuální krok a případnou chybu. Po naskenování QR kódu stáhněte zprávu JSON nebo otevřete předvyplněný návrh na GitHubu. Před odesláním stručně popište problém.

Pro odinstalaci na televizoru otevřete v Root Home **Nastavení → Pokročilé → Obnovení Clean Your TV** a potvrďte úplné odebrání. Pokud je vyžadován úplný restart, restartujte televizor, znovu otevřete Clean Your TV a pokračujte v odebrání. Po ověření můžete na obrazovce výsledku odstranit i dlaždici instalátoru.

## 5. Vyzkoušejte ovladač

1. Otevřete jinou aplikaci na TV a krátce stiskněte **Home**. Má se otevřít Clean Your TV. V průvodci uveďte, co jste viděli; pokud jste test neprovedli, přeskočte ho.
2. Vyzkoušejte šipky, OK, Zpět, hlasitost a zvuk.

## 6. Každodenní ovládání

Chcete-li aktualizovat prostředí automatického spuštění stávající Root Beta, vypněte **Change Home** a spusťte `cytv migrate-root-beta --edition root --root-variant node012-beta` přes uložené připojení Root SSH. Aplikace a nastavení zůstanou zachovány. Pokud předchozí odinstalace již změnila instalaci, migrace se zastaví. Po dokončení zapněte Change Home a vyberte zdroje automatického spuštění v nastavení Home.

Chcete-li připnout vstup HDMI, vyberte ho v nabídce **+ / Přidat aplikaci**. Tlačítkem OK přepnete na tento vstup. Podržením OK můžete dlaždici přesunout nebo skrýt.

Šipky vybírají aplikaci, **OK** ji otevře. Podržením OK můžete měnit pořadí. Krátké **Zpět** zachová navigaci aplikace. Krátké **Home** otevře Clean Your TV při zapnutém ovládání Home.

Pro úpravy krátkými stisky otevřete **Nastavení Home → Vzhled → Upravit dlaždice**. Stiskněte OK, přesuňte dlaždici šipkami a znovu stiskněte OK pro umístění. Zpět zruší přesun nebo ukončí úpravy.

Pokud se dálkový ovladač dočasně odpojí, nechte ovládání Home zapnuté. Jakmile televizor ovladač znovu rozpozná, ovládání Home se obnoví.

**Stiskněte Home třikrát během dvou sekund**, mezi stisky tlačítko pusťte. Otevře se LG Home a ovládání Home se zastaví. Nastavení zůstanou zachována.

Pro opětovné zapnutí No-root otevřete **Home Helper**, zvolte spuštění Helperu a potvrďte. Pro Root zapněte **Změnit Home** v nastavení Home. **Otevřít LG Home** otevře původní prostředí jen jednou; pro trvalé používání LG Home vypněte Změnit Home. Nespouštějte oba ovladače Home současně. Při opakované chybě nechte LG Home aktivní.

Pokud je Home Helper zastavený, můžete také zvolit **Spustit Helper** v nastavení obrazovky Home nebo spořiče. Stav se po spuštění automaticky aktualizuje.

Na televizorech, kde se LG Home otevírá jako panel, může zapnutí nebo vypnutí **Change Home** v Root krátce restartovat rozhraní televizoru. Po restartu nebo chybě otevřete Clean Your TV a znovu zapněte **Change Home**, aby se ovládání obnovilo. LG Home zůstává dostupný.

Po návratu k předchozí verzi Home uvolníte místo v nabídce **Nastavení → Motivy**. U nedostupného staženého motivu zvolte **Odstranit** a potvrďte.

## Potřebujete pomoc?

Pokud se zobrazí chyba `ssh-identity-changed`, zastavte se a ověřte klíč televizoru. [Obnova po změně klíče SSH](../RECOVERY.md#ssh-identity-changed)

Po obnovení továrního nastavení vlastní TV s No-root vyberte při změně klíče **Připojit znovu po obnovení továrního nastavení**. Postupujte podle pokynů v důvěryhodné domácí síti. Původní profil a záznam o odinstalaci se zachovají.

Pokud instalace na počítači zůstala nedokončená, na obrazovce s výsledkem vyberte **Prověřit možnosti obnovy** a u otázky **Prověřit možnosti obnovy?** zvolte **Pokračovat**. Průvodce použije stejné uložené připojení k TV. Pokud výsledek operace s balíčky No-root není známý a instalátor nabízí tlačítko **Zkontrolovat stav televizoru**, použijte ho nejdřív. Nabídnutou změnu potvrďte zvlášť. Pokud instalaci stále nelze dokončit, zachovejte uložené připojení i data obnovy.

Pokud No-root nabídne **Zopakovat kontrolu úložiště**, zvolte tuto možnost a zopakujte kontrolu pouze pro čtení na stejném televizoru. Po úspěšné kontrole potvrďte instalaci zvlášť. Pokud instalátor zjistí nedokončenou operaci, zvolte **Prověřit možnosti obnovy**.

Pokud ověřená instalace neotevře Clean Your TV tlačítkem Home, zvolte na obrazovce výsledků v No-root **Diagnostika tlačítka Home** nebo v Root **Zkontrolovat stav televizoru**. No-root zobrazí již zaznamenaný výsledek. Zprávu můžete uložit tlačítkem **Uložit diagnostickou zprávu**.

Chcete-li si zprávu ponechat, na obrazovce s výsledkem na počítači zvolte **Uložit diagnostickou zprávu…**. Pokud potřebujete pomoc, otevřete **Nahlásit problém**, prohlédněte návrh a použijte **Zkopírovat návrh** a **Otevřít formulář**. Vložte návrh a přiložte uloženou zprávu, pokud ji máte.

[Nahlásit problém — anglicky](../FEEDBACK.md) · [Obnovení — anglicky](../RECOVERY.md) · [Aktualizace a odstranění — anglicky](../MAINTENANCE.md) · [Další jazyky](../LANGUAGES.md)

### Jednoduché odebrání

Vyberte v Údržbě **Odinstalovat Clean Your TV** se stejným uloženým připojením TV. Potvrďte jednou. Přítomné známé aplikace a soubory projektu se odeberou, chybějící se přeskočí, i po částečné instalaci.

Na výzvu odpojte TV od napájení, znovu připojte, počkejte na síť. Pohotovost nebo Quick Start není úplný restart; CYTV TV automaticky nerestartuje. Pokud uklízení vyžaduje Root, použijte stávající přístup Root ke stejnému televizoru. Bez něj zůstane úklid nedokončený. Pokud je TV zaneprázdněný, počkejte a zkuste to znovu. Úspěch se zobrazí až po ověření závěrečného úklidu. Zachovejte klíče a původní zprávy. Nouzové ovládání a souhlas se sdílením výše platí dál.

Pokud instalátor na počítači čeká na TV, vyberte **Pokračovat v odinstalaci**, až se tato možnost zobrazí. Tlačítkem **Zrušit** čekání ukončíte a tlačítkem **Zkusit znovu** spojení ověříte ručně.

Pokud se na obrazovce odinstalace zobrazí **Návrat k LG Home**, zvolte tuto možnost a po ověření obnovení vyberte **Pokračovat v odinstalaci**. Při samostatném návratu k LG Home z nabídky Údržba zůstanou aplikace nainstalované.

Pokud instalátor nemůže ověřit odebrání, závěrečný úklid, ovládání TV či výsledek operace s balíčky nebo hlásí změnu cest projektu, zvolte **Prověřit možnosti obnovy** s původním uloženým připojením. Nabídne-li instalátor pokračování, potvrďte je samostatně. Pokud instalátor při obnově instalace No-root nabídne **Zkontrolovat stav televizoru**, zvolte tuto možnost a zachovejte data obnovy.

Pokud instalátor nemůže ověřit požadovaný úplný restart, uložte a přiložte diagnostickou zprávu. Zachovejte uložené připojení a data obnovy. Neopakujte stále odpojování napájení a nemažte ručně nedokončenou operaci.

Když se na počítači zobrazí **Odebrání Clean Your TV je ověřeno.**, můžete instalátor ukončit tlačítkem **Zavřít**. Tlačítko **Nastavit televizor** spustí novou instalaci na stejném televizoru se stejným připojením a edicí.

**Přeinstalace Root:** S uloženým připojením zvolte **Nastavit televizor → Root** a potvrďte **Přeinstalovat Root?**. Instalátor obnoví LG Home a zcela odstraní Clean Your TV včetně aktualizátorů, Home Helper a uložených předvoleb. Po ověření odstranění nainstaluje a aktivuje balíčky a prostředí Root dodané v tomto instalátoru. Ostatní aplikace TV a stávající přístup root/SSH zůstanou zachovány. Pokud se průvodce v počítači zastaví, otevřete stejný instalátor a zvolte **Pokračovat v přeinstalaci Root**. Po ověření odstranění zvolte **Pokračovat v instalaci Root**. Samotné **Odinstalovat Clean Your TV** nikdy nespustí novou instalaci.

Pokud průvodce během čištění požádá o úplný restart, odpojte televizor od napájení, znovu jej připojte a zapněte. Po spuštění zvolte **Televizor jsem restartoval — ověřit a pokračovat**.

### Úprava nastavení LG a dokončení obnovy Root

V desktopovém instalátoru otevřete **Údržba → Upravit nastavení LG (Debloat)** a použijte uložené připojení k TV. Vyberte nastavení, která chcete změnit, klikněte na **Použít vybraná nastavení** a zkontrolujte výsledky. Pokud je předchozí operace nedokončená, zvolte nejprve **Prověřit možnosti obnovy** s původním uloženým připojením.

- [Root Updater](../RECOVERY.md#standalone-root-updater-rollback-readiness)
- [Root System Updater](../RECOVERY.md#root-system-rollback-readiness-candidate)

<!-- Legacy anchors retained for existing links. -->
<a id="automatické-rozlišení-grafiky-kandidát"></a>
<a id="čeština--rozhraní-televizoru"></a>
<a id="jazyk-a-ovládání"></a>
<a id="aktualizace-a-obnovení"></a>
<a id="automatické-rozlišení-grafiky-160"></a>
<a id="místo-v-úložišti"></a>

<a id="kandidát-unreleased-starší-nodejs-v-tv"></a>
<a id="starší-nodejs-v-tv-vydáno-ve-v1120"></a>
<a id="jednoduché-odebrání-v1110"></a>

## Nastavení

Pokud jste spořič obrazovky ještě nenastavili, je ve výchozím nastavení zapnutý. V nastavení obrazovky Home v části **Spořič obrazovky** jej můžete vypnout.

V nabídce **Nastavení → Vzhled** zapněte **Nejčastěji používané aplikace první**. Pořadí v doku se zachová. Podržením OK upravíte ruční pořadí nebo skryjete dlaždici. Vypnutím volby se vrátíte k ručnímu pořadí. Volbu najdete také na konci nastavení v instalátoru cytv.

Pomocí ↑ ↓ vyberte kategorii a pomocí → nebo OK do ní vstupte. ← se vrací ke kategoriím; Zpět se nejprve vrátí k nim a poté zavře nastavení. Při návratu do sekce se obnoví poslední dostupný ovládací prvek. Ve Sloupcích šipky odpovídají mřížce se třemi sloupci. V Jazyku se zaměří vybraný jazyk.

V **Nastavení → Vaše obrazovka Home → Formát času** vyberte **Automaticky (podle nastavení TV)**, **12hodinový** nebo **24hodinový** formát.

V edici No-root otevřete **Nastavení → Vaše obrazovka Home → Po probuzení zůstat na HDMI nebo živém vysílání**.

Pokud televizor po probuzení z pohotovostního režimu už zobrazuje herní konzoli, živé vysílání nebo jiný vstup, zůstane na této obrazovce. Tlačítko Home funguje jako obvykle. Tato volba je ve výchozím nastavení vypnutá.

Pokud No-root nemůže načíst stav Home, zvolte Zkusit znovu. Nedostupný přepínač neznamená vypnuté ovládání Home. V Tapetách nahrajte obrázek z telefonu nebo CYTV; kvalita a ztmavení jsou dostupné po výběru tapety. Odstranění vlastní tapety vyžaduje potvrzení; Zrušit ji zachová.

## Počasí

Otevřete Nastavení → Počasí pod Tapetami. Zapněte počasí, otevřete Město a vyhledejte správnou oblast a zemi, nebo zvolte Automaticky pro přibližné určení podle internetového připojení. VPN může výsledek změnit; pokud město chybí nebo nesouhlasí, použijte ruční hledání. Určené či vybrané město je vidět v nastavení. Vyberte °C / m/s nebo °F / mph a dostupný formát: stručný, aktuální, podrobný nebo na čtyři dny. Náhled odpovídá motivu; označení Příklad znamená ukázková data. Liquid Glass podporuje pouze stručný formát; Ribbon a Atmosphere počasí nezobrazují. Vypnutí zastaví požadavky a skryje volby města, jednotek a formátu; výběr zdroje zůstává dostupný. Při výpadku mohou krátce zůstat nedávná data; později se počasí skryje do dalšího obnovení.

Vyberte zdroj předpovědi: Auto, MET Norway nebo Open-Meteo. Auto začne s MET Norway, při chybě jednou zkusí Open-Meteo a potom používá poslední úspěšný zdroj a jeho mezipaměť. Ruční výběr nikdy automaticky nemění zdroj. Nová nastavení používají Auto; uložená bez zdroje zachovají Open-Meteo. Skutečný zdroj je vidět v nastavení. Dostupnost závisí na síti. MET se obnovuje nejvýše jednou za tři hodiny; mezipaměť vyprší po šesti hodinách. Chybějící pole se skrývají: MET neposkytuje pocitovou teplotu ani pravděpodobnost srážek. Denní rozsahy shrnují body předpovědi, nikoli naměřené extrémy.

Souřadnice se posílají na api.met.no nebo api.open-meteo.com, hledání měst na geocoding-api.open-meteo.com. Volitelné automatické určení města předává veřejnou IP adresu na get.geojs.io. Spojení používají HTTPS; klíč API není potřeba. Místo, zdroj a mezipaměť zůstávají v televizoru. Zdroje dat obsahují podmínky a autorství včetně Norského meteorologického institutu (MET Norway, CC BY 4.0).

Tlačítko Zdroje dat v záhlaví Počasí otevře informace o službách a licencích.

## Nahrání tapety z iPhonu

Otevřete Nastavení → Tapety → Nahrát z telefonu a naskenujte kód. Vyberte JPG, PNG nebo HEIC/HEIF, upravte výřez, potvrďte omezení kvality a odešlete. Na TV zvolte Použít. Safari používá vlastní podporu HEIC; Chrome, Firefox a další moderní prohlížeče podle potřeby přibalený místní dekodér. Převod probíhá v telefonu bez externí služby. Zrušení nebo výběr jiného souboru převod zastaví. Vstup: 32 MiB a 50 milionů pixelů; výstup: nejvýše 1080p a 2 MiB. Při chybě zkuste jinou fotku nebo JPG/PNG. Platí pro stránku v telefonu, ne aplikaci pro Mac.

## Nastavte si Clean Your TV

Před výběrem motivu zvolte v kroku **Debloat**, která nastavení reklam, doporučení, soukromí a oznámení LG chcete změnit. Zkontrolujte každý výsledek. Pokud instalátor nemůže přečíst původní hodnotu, nemůže ji uložit pro automatické obnovení. Volbou **Přeskočit Debloat** zachováte aktuální nastavení.

Pokud televizor změnu odmítne, vyhledejte postup pro svůj model v [průvodci nastavením soukromí pomocí ovladače (anglicky)](../PRIVACY.md).

Obě edice mohou vypnout propagační vysílání LG, pokud televizor toto nastavení nabízí.

V nastavení soukromí můžete samostatně vypnout odesílání ladicích protokolů a protokolů o chybách společnosti LG. Nastavení se přeskočí, pokud nelze přečíst jeho původní hodnotu. V režimu No-root může firmware změnu odmítnout. Některé televizory při spuštění odesílání ladicích protokolů opět zapnou. Po restartu nastavení zkontrolujte.

Chcete-li vrátit jednu změnu, otevřete Debloat v nabídce údržby se stejným uloženým připojením k televizoru. Vyberte nastavení, zkontrolujte původní hodnotu a potvrďte obnovení. Na podporovaných televizorech můžete automatické spuštění LG Channels vypnout v nabídce Všechna nastavení → Obecné → Kanály → Automatické spuštění LG Channels.

Při odinstalaci můžete potvrdit obnovení uložených původních nastavení Debloat. Pokud obnovení přeskočíte, odinstalace pokračuje bez jejich změny.

Po úspěšné instalaci vyberte Classic, Liquid Glass nebo Ribbon a zapněte či vypněte počasí. Ribbon počasí nepodporuje; Liquid Glass používá stručný formát. Město se odhaduje podle připojení a lze je změnit v Home.

No-root s Developer Mode nabízí automatické prodloužení; nadále sledujte oficiální časovač. U nových instalací No-root přes stávající root SSH se karta Developer Mode nezobrazuje. Root umožňuje přes Homebrew Channel blokovat aktualizace firmwaru LG včetně bezpečnostních; je nutný skutečný restart přes Homebrew Channel. Aktualizace CYTV jsou samostatné.

Ponechat aktuální nastavení přeskočí přizpůsobení. Přepínač zobrazuje aktuální stav funkce režimu. Nezměněná nastavení zůstanou zachována. Přeinstalace Root nadále odstraní nastavení CYTV podle popisu výše. Ověřte vzhled na TV a nepotvrzené volby v Home před opakováním.

## Aktualizace na televizoru s rootem

Pokud je nastaven System Updater s vlastní aktualizací, použijte **Aktualizace softwaru → Aktualizovat vše** pro Root nebo No-root na televizoru s rootem. Nechte televizor zapnutý až do dokončení. Chcete-li opravit pouze aktualizátor, otevřete Home a vyberte **Aktualizace softwaru → Obnovení → Přeinstalovat System Updater**; Home a nastavení zůstanou zachovány. No-root bez rootu nadále používá instalaci z počítače.
