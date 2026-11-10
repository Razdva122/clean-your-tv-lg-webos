---
lang: cs
topic: root-vs-no-root
title: "Root nebo No-root pro launcher LG webOS"
description: "Vyberte správnou edici Clean Your TV pro svůj LG webOS TV. Před instalací porovnejte požadavky na přístup, správu Developer Mode, ovládání Home a obnovení."
updated: '2026-11-09'
---

No-root zvolte, pokud váš televizor LG používá Developer Mode. Root zvolte pouze tehdy, pokud už má funkční přístup root a kompatibilní služby. Obě edice Clean Your TV nabízejí stejné rozhraní Home a po instalaci běží na televizoru. Instalátor nezískává přístup root ani nepřehrává firmware.

## Co vyžaduje No-root?

No-root při nastavení používá LG Developer Mode, Key Server a místní párování. Home Helper běží na televizoru a obsluhuje tlačítko Home tam, kde to zařízení a firmware podporují. Pro každodenní používání nemusíte nechávat zapnutý počítač ani telefon.

Trvalým požadavkem je Developer Mode: prodlužujte jeho relaci před vypršením. LG upozorňuje, že aplikace nainstalované přes Developer Mode mohou být po vypnutí režimu nebo vypršení relace odebrány. Automatické prodlužování v projektu je volitelná funkce beta, ve výchozím nastavení vypnutá; nepovažujte ji za záruku. Než se na tuto edici spolehnete, přečtěte si [průvodce Developer Mode](/clean-your-tv-lg-webos/cs/articles/lg-developer-mode/).

## Co vyžaduje Root?

Root používá existující SSH přístup s oprávněním root, kompatibilní služby televizoru a podporované možnosti zpracování vstupů i běhového prostředí. Samotný přístup root nepotvrzuje kompatibilitu. Instalátor prostředí kontroluje; neobcházejte nesplněný předpoklad ani nenahrazujte systémová běhová prostředí, abyste kontrolu vynutili.

Root má samostatné balíčky a vlastní obsluhu Home. Nezapínejte Developer Mode na existující konfiguraci s rootem a před použitím obsluhy Root zastavte Home Helper z edice No-root. Výběr edice se řídí přístupem, který již máte, nejde o výběr tlačítka, které televizoru získá root.

## Porovnejte údržbu a obnovení

- **Každodenní používání:** obě edice běží na televizoru a nabízejí aplikace i motivy v launcheru.
- **Údržba No-root:** udržujte aktivní Developer Mode a zachovejte párování i připojení vyžadované Helperem.
- **Údržba Root:** zachovejte dostupnost nezávislých služeb pro obnovení a jejich požadovaného běhového prostředí. Dostupnost aktualizací závisí na nainstalované edici a podporované cestě aktualizace; samotný přístup root nezapíná OTA.
- **Nouzové opuštění:** aktuálně podporované edice používají tři krátká stisknutí Home během dvou sekund. Home Helper do verze 0.6.13 včetně místo toho používá dvousekundové podržení.

Po nouzovém zastavení vyžaduje obnovení trvalé obsluhy Home výslovný krok. V No-root otevřete Home Helper a zvolte Start Helper; v Root použijte Change Home v nastavení Home. Viz [srovnání edic](/clean-your-tv-lg-webos/cs/editions/) a [nápověda k obnovení](/clean-your-tv-lg-webos/cs/help/#home-button).

## Před instalací zkontrolujte televizor

Přečtěte si [stránku kompatibility](/clean-your-tv-lg-webos/cs/compatibility/) s přesným modelem, firmwarem, verzí webOS a typem ovladače po ruce. Nahlášené výsledky se vztahují ke konkrétní konfiguraci. Po nastavení samostatně vyzkoušejte Home, spouštění aplikací, zvuk, pohotovostní režim a spuštění po úplném vypnutí. Instalace balíčku nedokazuje, že vše funguje.

Použijte [zveřejněný instalátor a návod k instalaci](/clean-your-tv-lg-webos/cs/install/). Pokud již máte funkční nastavení a chcete přejít na jinou edici, postupujte podle zdokumentovaných kroků přechodu a odebrání místo instalace jedné edice přes druhou.

## Zdroje a další kroky

- [Srovnání edic projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Požadavky a známá omezení projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Co změní jiná domovská obrazovka](/clean-your-tv-lg-webos/cs/articles/change-lg-webos-home-screen/)
