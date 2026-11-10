---
lang: cs
topic: change-lg-webos-home-screen
title: "Jak změnit domovskou obrazovku televizoru LG webOS"
description: "Přizpůsobte si domovskou obrazovku LG webOS pomocí Clean Your TV. Zjistěte, co launcher mění, jak vybrat edici a co ověřit před instalací."
updated: '2026-11-09'
---

Clean Your TV je alternativní domovská obrazovka pro televizory LG webOS. Umožňuje uspořádat aplikace podle vašich představ a nabízí motivy i přizpůsobitelný dock. Po nastavení běží na televizoru, takže počítač můžete vypnout. Zda dokáže obsluhovat tlačítko Home, závisí na televizoru, firmwaru, ovladači a způsobu instalace.

## Co si můžete přizpůsobit?

Launcher mění obrazovku, na které hledáte a spouštíte televizní aplikace. Můžete uspořádat oblíbené aplikace a vybrat rozložení, například Classic, Liquid Glass nebo Ribbon. Před instalací vyzkoušejte [demo v prohlížeči](/clean-your-tv-lg-webos/demo/) a porovnejte jednotlivá rozložení. Ovládání televizoru je v demu simulované; kompatibilitu s vaším televizorem neověří.

Alternativní launcher nenahrazuje firmware webOS, neodemyká placené streamování ani neodstraňuje reklamu v ostatních aplikacích. Nastavení obrazu, vstupy a streamovací služby zůstávají samostatnými částmi televizoru. Pokud vám jde především o klidnější domovskou obrazovku, přečtěte si, [co se mění v oblasti reklamy](/clean-your-tv-lg-webos/cs/articles/lg-tv-home-screen-ads/).

## Jaký způsob instalace zvolit?

No-root použijte na televizoru s aktivním LG Developer Mode. Home Helper běží přímo na televizoru a obsluhuje tlačítko Home tam, kde je to podporováno. Developer Mode musí zůstat aktivní; po vypršení relace mohou být aplikace nainstalované mimo obchod odebrány.

Root použijte pouze tehdy, pokud televizor již má funkční přístup root a splňuje požadavky na běhové prostředí a služby. Instalátor Clean Your TV přístup root nezískává. Nezapínejte Developer Mode na stávající konfiguraci s rootem a nepoužívejte oba způsoby obsluhy Home současně. Podrobnosti a kompromisy vysvětluje [průvodce edicemi](/clean-your-tv-lg-webos/cs/articles/root-vs-no-root/).

## Než změníte funkční nastavení

1. Zaznamenejte přesný model, firmware, verzi webOS a typ ovladače. Porovnejte je s [požadavky a nahlášenými výsledky na televizorech](/clean-your-tv-lg-webos/cs/compatibility/); každé hlášení platí pro uvedenou konfiguraci.
2. Postupujte podle [návodu k instalaci](/clean-your-tv-lg-webos/cs/install/) a použijte zveřejněný instalátor, na který návod odkazuje. Televizor a zařízení s instalátorem musí být během nastavení v síti, která jim umožní vzájemnou komunikaci.
3. Po nastavení ověřte spouštění aplikací a Home, poté samostatně zvuk, pohotovostní režim/probuzení a spuštění po úplném vypnutí. Úspěšná instalace balíčku tyto funkce neověřuje.

## Jak se vrátit do LG Home?

V aktuálně podporovaných edicích spustí nouzové opuštění tři krátká stisknutí Home během dvou sekund. Starší Home Helper do verze 0.6.13 včetně používá dvousekundové podržení Home. Jednorázové otevření LG Home a vypnutí trvalé obsluhy tlačítka Home jsou různé úkony; použijte [pokyny k obnovení](/clean-your-tv-lg-webos/cs/help/#home-button) pro nainstalovanou edici. Než změníte chování při spuštění, zajistěte si dostupnou cestu k obnovení ovládání.

## Zdroje a další kroky

- [Dokumentace projektu k edicím a ovládání](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Instalace a předpoklady projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: jak zachovat dostupnost nastavení No-root](/clean-your-tv-lg-webos/cs/articles/lg-developer-mode/)
