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

## 5. Vyzkoušejte ovladač

1. Otevřete jinou aplikaci na TV a krátce stiskněte **Home**. Má se otevřít Clean Your TV. V průvodci uveďte, co jste viděli; pokud jste test neprovedli, přeskočte ho.
2. Vyzkoušejte šipky, OK, Zpět, hlasitost a zvuk. Samostatně ověřte pohotovostní režim/probuzení a spuštění po odpojení napájení. Samotná úspěšná instalace tyto funkce neověřuje.

## 6. Každodenní ovládání

Šipky vybírají aplikaci, **OK** ji otevře. Podržením OK můžete měnit pořadí. Krátké **Zpět** zachová navigaci aplikace. Krátké **Home** otevře Clean Your TV při zapnutém ovládání Home. Podržení Zpět po dobu 1,2 sekundy otevře LG Home jednou, bez změny uložených nastavení.

**Stiskněte Home třikrát během dvou sekund**, mezi stisky tlačítko pusťte. Otevře se LG Home a ovládání Home se zastaví. Nastavení zůstanou zachována.

Pro opětovné zapnutí No-root otevřete **Home Helper**, zvolte spuštění Helperu a potvrďte. Pro Root zapněte **Změnit Home** v nastavení Home. **Otevřít LG Home** otevře původní prostředí jen jednou; pro trvalé používání LG Home vypněte Změnit Home. Nespouštějte oba ovladače Home současně. Při opakované chybě nechte LG Home aktivní.

## Potřebujete pomoc?

Po přerušené instalaci použijte stejné uložené připojení a nejprve kontrolu stavu TV (**Check TV status**). Pokračujte jen nabízenou obnovou. Pokud je stav neznámý, uložte diagnostickou zprávu a zastavte se. Zachovejte data obnovy a neopakujte instalaci naslepo.

Během obnovy ponechte ovládání Home vypnuté a zachovejte původní diagnostické zprávy i uložené připojení. Kontrolu a změny potvrzujte samostatně. Postupujte podle podrobného návodu pro nainstalovanou verzi; nevynucujte novou instalaci ani nemažte stav obnovy.

Uveďte model TV, firmware, No-root nebo Root, instalační zařízení, krok a chybovou zprávu. Před sdílením odstraňte hesla, klíče, adresy a osobní údaje. Zpráva se nezveřejňuje automaticky.

[Nahlásit problém — anglicky](../FEEDBACK.md) · [Obnovení — anglicky](../RECOVERY.md) · [Aktualizace a odstranění — anglicky](../MAINTENANCE.md) · [Další jazyky](../LANGUAGES.md)

<!-- Legacy anchors retained for existing links. -->
<a id="automatické-rozlišení-grafiky-kandidát"></a>
<a id="čeština--rozhraní-televizoru"></a>
<a id="jazyk-a-ovládání"></a>
<a id="aktualizace-a-obnovení"></a>
<a id="automatické-rozlišení-grafiky-160"></a>
<a id="místo-v-úložišti"></a>
