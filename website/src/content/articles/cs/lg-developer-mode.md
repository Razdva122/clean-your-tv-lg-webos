---
lang: cs
topic: lg-developer-mode
title: "LG Developer Mode pro launcher webOS No-root"
description: "Zjistěte, proč Clean Your TV No-root potřebuje LG Developer Mode, jak vypršení relace ovlivňuje aplikace mimo obchod a co ověřit, když launcher zmizí."
updated: '2026-11-09'
---

LG Developer Mode umožňuje instalovat a testovat aplikace webOS TV bez získání přístupu root k televizoru. Clean Your TV No-root používá tento způsob přístupu společně s Home Helperem běžícím na televizoru. Relace Developer Mode je časově omezená: v aplikaci Developer Mode od LG kontrolujte zbývající čas a prodlužte ji před vypršením, aby aplikace nainstalované mimo obchod zůstaly dostupné.

## Co Developer Mode poskytuje?

Developer Mode poskytuje přístup pro vývoj; neuděluje oprávnění root ani nezaručuje, že pomocná aplikace pro tlačítko Home bude fungovat na každém modelu. Clean Your TV nadále ověřuje požadavky na běhové prostředí a zpracování vstupů. Běžné aplikace z obchodu, aplikace instalované mimo obchod a systém s rootem využívají odlišné způsoby přístupu.

No-root používejte pouze na odpovídající konfiguraci Developer Mode. Pokud má televizor již root, Developer Mode na něm nezapínejte. Nejprve si přečtěte [srovnání Root a No-root](/clean-your-tv-lg-webos/cs/articles/root-vs-no-root/) a [požadavky na kompatibilitu](/clean-your-tv-lg-webos/cs/compatibility/).

## Připravte televizor a zařízení pro instalaci

Přesný postup najdete v [aktuálním návodu k instalaci](/clean-your-tv-lg-webos/cs/install/). Budete potřebovat aplikaci Developer Mode od LG, požadované přihlášení k vývojářskému účtu LG a Key Server pro párování. Televizor a počítač nebo podporované zařízení s Androidem musí být v síti, která jim umožní vzájemnou komunikaci. Síť pro hosty nebo izolace klientů mohou nastavení zablokovat, i když mají obě zařízení přístup k internetu.

Párovací klíče a údaje o připojení uchovávejte v soukromí. Použijte zveřejněný instalátor z návodu; stažení libovolného IPK nepředstavuje úplné nastavení Home. Po dokončení instalace běží launcher i Helper na televizoru a počítač lze vypnout.

## Udržujte relaci aktivní

Otevřete aplikaci Developer Mode od LG, zkontrolujte zbývající čas relace a prodlužte ji, když je dostupné požadované připojení. Řiďte se aktuálními pokyny LG místo pevného počtu hodin uvedeného ve starém článku. Pokus o prodloužení není důkazem úspěchu: poté zkontrolujte zobrazený zbývající čas.

Clean Your TV nabízí volitelné automatické prodlužování jako funkci beta, která je ve výchozím nastavení vypnutá. Pokud ji zapnete, dál kontrolujte skutečný stav Developer Mode. Funkce neruší požadavky LG na relaci a nezajistí trvalou platnost vypnutého režimu.

## Co když launcher zmizí nebo Home otevírá LG Home?

Než začnete opakovat instalaci, zkontrolujte Developer Mode. LG uvádí, že vypnutí Developer Mode nebo vypršení relace může odinstalovat vývojové aplikace. Vypršená relace je jiná situace než nouzové zastavení Home Helperu, problém s párováním nebo přerušená instalace.

Pokud byly vývojové aplikace odebrány, obnovte Developer Mode podle dokumentace a použijte průvodce nastavením nebo obnovením v instalátoru podle skutečného stavu. Pokud aplikace zůstaly, ale obsluha Home je zastavená, postupujte podle [nápovědy k tlačítku Home](/clean-your-tv-lg-webos/cs/help/#home-button). Při přerušené operaci použijte [návod k obnovení](/clean-your-tv-lg-webos/cs/help/#interrupted) místo mazání systémových souborů. Po obnovení samostatně ověřte chování Home.

## Zdroje a další kroky

- [LG: používání aplikace Developer Mode](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [Návod projektu k instalaci No-root](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Dokumentace projektu k obnovení](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
