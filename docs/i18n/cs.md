# Clean Your TV — průvodce instalací

instalátor žádá název TV, výchozí **Home**; CLI: `--tv-name "Aashiyaan"`. Po aktualizaci starší instalace se automaticky objeví **Nastavení → Home → Název TV**. Název lze kdykoli uložit nebo obnovit Home. Uložený název přežije restart i podporované aktualizace; ostatní nastavení zůstanou zachována. Nejvýše 48 znaků. Nastavení ukládá název launcheru. Pro změnu úvodní obrazovky LG použijte stejný název v instalátoru. Druhá načítací obrazovka se nepřidává; síťový název se nemění.

Dosud nevydaná změna instalátoru: před novou instalací instalátor v počítači ověří novější stabilní verzi na GitHubu. Vyberte „Otevřít GitHub a stáhnout nejnovější verzi“ pro zastavení a stažení, nebo „Ne, nainstalovat tuto verzi“ pro výslovné pokračování. Pokud kontrola selže, můžete pokračovat. Nedokončené operace a obnovení kontrolu přeskočí.

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

U Root instalátor ověří a vybere dostupný způsob ovládání Home. Pokud nelze kompatibilitu ověřit, instalace se zastaví; neobcházejte neúspěšnou kontrolu.

**No-root → Root:** Pokud jste po úplném odebrání znovu nainstalovali No-root, přechod na Root může vyžadovat nejprve vyčištění instalace. Zálohujte nastavení Home, zvolte **Odinstalovat Clean Your TV** s uloženým připojením Root a počkejte na ověřené odebrání. Odebere se také No-root Home a Helper. Poté nainstalujte Root a uchovejte záznamy obnovy.

### Developer Mode (No-root)

1. V TV otevřete LG Apps, vyhledejte **Developer Mode** a nainstalujte ho.
2. Otevřete Developer Mode a přihlaste se účtem LG Developer. Účet si můžete vytvořit na [LG Developer](https://webostv.developer.lge.com).
3. Zapněte **Dev Mode Status**. TV se restartuje; poté Developer Mode znovu otevřete.
4. Zapněte **Key Server** a ponechte Developer Mode otevřený. **IP Address** je adresa TV, kterou zadáte do CYTV.
5. Použijte šestiznakový kód **Passphrase** z obrazovky TV. Rozlišujte velká a malá písmena.

Použijte kód z TV, nikoli heslo účtu LG. Pokud kód nevidíte, zapněte Key Server. Při samostatné žádosti o párování povolte CYTV dálkovým ovladačem.

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
4. Postupujte podle průvodce. Nechte TV zapnutou, neměňte síť a nezavírejte CYTV do dokončení. Na Androidu nevynucujte ukončení aplikace. Root zapne ovládání Home ihned po přípravě obnovy.

Instalace Root pokračuje s upozorněním, pokud nelze načíst vstupy televizoru, ale seznam aplikací je platný. V Home mohou chybět vstupy; chyba načtení nebo prázdný seznam aplikací instalaci nadále zastaví. Pokud se upozornění opakuje, uložte diagnostickou zprávu.

## 5. Vyzkoušejte ovladač

1. Otevřete jinou aplikaci na TV a krátce stiskněte **Home**. Má se otevřít Clean Your TV. V průvodci uveďte, co jste viděli; pokud jste test neprovedli, přeskočte ho.
2. Vyzkoušejte šipky, OK, Zpět, hlasitost a zvuk. Samostatně ověřte pohotovostní režim/probuzení a spuštění po odpojení napájení. Samotná úspěšná instalace tyto funkce neověřuje.

## 6. Každodenní ovládání

Podpora IR v No-root: uvolnění Home po krátkém stisku naplánuje Clean přibližně za 700 ms; nejprve může probliknout LG Home. Podržení Home zůstává webOS a trojí stisk stále zastaví Helper. Přístup v běžném Developer Mode není ověřen; neměňte oprávnění vstupních zařízení.

Šipky vybírají aplikaci, **OK** ji otevře. Podržením OK můžete měnit pořadí. Krátké **Zpět** zachová navigaci aplikace. Krátké **Home** otevře Clean Your TV při zapnutém ovládání Home. Podržení Zpět po dobu 1,2 sekundy otevře LG Home jednou, bez změny uložených nastavení.

**Stiskněte Home třikrát během dvou sekund**, mezi stisky tlačítko pusťte. Otevře se LG Home a ovládání Home se zastaví. Nastavení zůstanou zachována.

Pro opětovné zapnutí No-root otevřete **Home Helper**, zvolte spuštění Helperu a potvrďte. Pro Root zapněte **Změnit Home** v nastavení Home. **Otevřít LG Home** otevře původní prostředí jen jednou; pro trvalé používání LG Home vypněte Změnit Home. Nespouštějte oba ovladače Home současně. Při opakované chybě nechte LG Home aktivní.

Aktualizace znovu nespustí zastavený No-root Helper. Obnovte jej výslovně výše uvedeným postupem; ručně nemažte značky zastavení.

## Potřebujete pomoc?

Pokud se po resetu nebo změně SSH objeví `ssh-identity-changed`, zastavte se: CYTV zablokoval změněný uložený klíč před přihlášením. První potvrzení důvěry jej nenahradí; čekající odinstalace nevysvětluje neshodu. Zachovejte původní profil, klíče a záznamy obnovy. Podporovaný automatický příkaz pro obnovení důvěry není k dispozici. Je nutné nezávisle ověřit identitu/otisk TV a použít zkontrolovaný postup zachovávající profil: [obnova po změně identity SSH](../RECOVERY.md#ssh-identity-changed).

Po přerušené instalaci použijte stejné uložené připojení a nejprve kontrolu stavu TV (**Check TV status**). Pokračujte jen nabízenou obnovou. Pokud je stav neznámý, uložte diagnostickou zprávu a zastavte se. Zachovejte data obnovy a neopakujte instalaci naslepo.

Během obnovy ponechte ovládání Home vypnuté a zachovejte původní diagnostické zprávy i uložené připojení. Kontrolu a změny potvrzujte samostatně. Postupujte podle podrobného návodu pro nainstalovanou verzi; nevynucujte novou instalaci ani nemažte stav obnovy.

Uveďte model TV, firmware, No-root nebo Root, instalační zařízení, krok a chybovou zprávu. Před sdílením odstraňte hesla, klíče, adresy a osobní údaje. Zpráva se nezveřejňuje automaticky.

[Nahlásit problém — anglicky](../FEEDBACK.md) · [Obnovení — anglicky](../RECOVERY.md) · [Aktualizace a odstranění — anglicky](../MAINTENANCE.md) · [Další jazyky](../LANGUAGES.md)

### Jednoduché odebrání

Vyberte v Údržbě **Odinstalovat Clean Your TV** se stejným uloženým připojením TV. Potvrďte jednou. Přítomné známé aplikace a soubory projektu se odeberou, chybějící se přeskočí, i po částečné instalaci.

Na starších televizorech bez samostatné aplikace LG Home může odebrání No-root přepnout obrazovku na živé vysílání. Nechte televizor zapnutý a na požádání jej restartujte; nemažte data obnovení ani neresetujte televizor.

Na výzvu odpojte TV od napájení, znovu připojte, počkejte na síť a vyberte **Zkusit znovu**. Pohotovost nebo Quick Start není úplný restart; CYTV TV automaticky nerestartuje. Při ztrátě spojení je zkontrolujte a opakujte stejný cíl odebrání bez dalšího průvodce obnovou. Při odmítnutí přístupu použijte požadované připojení Root; pokud je TV zaneprázdněn, počkejte a zkuste znovu. Úspěch se zobrazí až po ověření závěrečného úklidu. Zachovejte klíče a původní zprávy. Nouzové ovládání a souhlas se sdílením výše platí dál.

Je po neúspěšné nebo přerušené instalaci přímo dostupná obnova. Pokud No-root nemůže pokračovat, potvrďte jednou úplné odebrání. Při dočasné ztrátě spojení nebo zaneprázdněném procesu CYTV proběhnou nejvýše tři pokusy. Je-li nutný Root, zvolte **Připojit přes Root** pro stejnou TV; ověřený úklid Root dokončí i její zablokované odebrání No-root. Po chybě aktivace Root se CYTV pokusí obnovit a ověřit LG Home bez opakované aktivace. Zrušení s nedokončenou prací zachová zprávu a kroky obnovy. Nouzové zastavení zůstane zachováno.

Po chybě připojení během odstranění otevřete podrobnosti, zkontrolujte síť nebo vyberte existující SSH klíč Root a zkuste to znovu. Adresa, edice, port a ověření klíče TV zůstávají pevné. No-root kontroluje Helper před párováním: zastavte jej a potvrďte opětovnou kontrolu ve stejném průvodci. Restart lze přeskočit pouze u ověřeně prázdné TV bez nedokončené instalace; po skutečném odstranění proveďte požadovaný restart. Při selhání služby vstupů pokračuje bezpečné odstranění balíčků; úspěch stále vyžaduje ověření odstranění zástupce.

**Přeinstalace Root:** S uloženým připojením zvolte **Nastavit televizor → Root** a potvrďte **Přeinstalovat Root?**. Instalátor obnoví LG Home a zcela odstraní Clean Your TV včetně aktualizátorů, Home Helper a uložených předvoleb. Po ověření odstranění nainstaluje a aktivuje balíčky a prostředí Root dodané v tomto instalátoru. Ostatní aplikace TV a stávající přístup root/SSH zůstanou zachovány. Pokud se odstranění zastaví nebo požádá o úplný restart, dokončete je před novým spuštěním instalace. Samotné **Odinstalovat Clean Your TV** nikdy nespustí novou instalaci.

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

## Počasí

Otevřete Nastavení → Počasí pod Tapetami. Zapněte počasí, otevřete Město a vyhledejte správnou oblast a zemi, nebo zvolte Automaticky pro přibližné určení podle internetového připojení. VPN může výsledek změnit; pokud město chybí nebo nesouhlasí, použijte ruční hledání. Určené či vybrané město je vidět v nastavení. Vyberte °C / m/s nebo °F / mph a dostupný formát: stručný, aktuální, podrobný nebo na čtyři dny. Náhled odpovídá motivu; označení Příklad znamená ukázková data. Liquid Glass podporuje pouze stručný formát; Ribbon a Atmosphere počasí nezobrazují. Vypnutí zastaví požadavky a skryje volby města, jednotek a formátu; výběr zdroje zůstává dostupný. Při výpadku mohou krátce zůstat nedávná data; později se počasí skryje do dalšího obnovení.

Vyberte zdroj předpovědi: Auto, MET Norway nebo Open-Meteo. Auto začne s MET Norway, při chybě jednou zkusí Open-Meteo a potom používá poslední úspěšný zdroj a jeho mezipaměť. Ruční výběr nikdy automaticky nemění zdroj. Nová nastavení používají Auto; uložená bez zdroje zachovají Open-Meteo. Skutečný zdroj je vidět v nastavení. Dostupnost závisí na síti. MET se obnovuje nejvýše jednou za tři hodiny; mezipaměť vyprší po šesti hodinách. Chybějící pole se skrývají: MET neposkytuje pocitovou teplotu ani pravděpodobnost srážek. Denní rozsahy shrnují body předpovědi, nikoli naměřené extrémy.

Souřadnice se posílají na api.met.no nebo api.open-meteo.com, hledání měst na geocoding-api.open-meteo.com. Volitelné automatické určení města předává veřejnou IP adresu na get.geojs.io. Spojení používají HTTPS; klíč API není potřeba. Místo, zdroj a mezipaměť zůstávají v televizoru. Zdroje dat obsahují podmínky a autorství včetně Norského meteorologického institutu (MET Norway, CC BY 4.0).

Tlačítko Zdroje dat v záhlaví Počasí otevře informace o službách a licencích.
