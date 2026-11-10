---
lang: pl
topic: root-vs-no-root
title: "Root czy No-root dla launchera LG webOS"
description: "Wybierz odpowiednią edycję Clean Your TV dla telewizora LG webOS. Porównaj wymagany dostęp, utrzymanie Developer Mode, obsługę Home i odzyskiwanie przed instalacją."
updated: '2026-11-09'
---

Wybierz No-root, jeśli Twój telewizor LG korzysta z Developer Mode. Wybierz Root tylko wtedy, gdy ma już działający dostęp root i zgodne usługi. Obie edycje Clean Your TV oferują ten sam interfejs Home i po instalacji działają na telewizorze. Instalator nie uzyskuje dostępu root ani nie wgrywa oprogramowania sprzętowego.

## Czego wymaga No-root?

No-root podczas konfiguracji korzysta z LG Developer Mode, Key Server i lokalnego parowania. Home Helper działa na telewizorze i obsługuje przycisk Home tam, gdzie pozwalają na to urządzenie i oprogramowanie. Do codziennego korzystania nie trzeba zostawiać włączonego komputera ani telefonu.

Stałym wymaganiem jest Developer Mode: przedłużaj jego sesję przed wygaśnięciem. LG ostrzega, że aplikacje zainstalowane przez Developer Mode mogą zostać usunięte po wyłączeniu trybu lub wygaśnięciu sesji. Automatyczne przedłużanie w projekcie jest opcjonalną funkcją beta, domyślnie wyłączoną; nie traktuj go jako gwarancji. Przeczytaj [poradnik Developer Mode](/clean-your-tv-lg-webos/pl/articles/lg-developer-mode/), zanim oprzesz konfigurację na tej edycji.

## Czego wymaga Root?

Root korzysta z istniejącego dostępu SSH z uprawnieniami root, zgodnych usług telewizora oraz obsługiwanych możliwości wejścia i środowiska uruchomieniowego. Sam dostęp root nie potwierdza zgodności. Instalator sprawdza środowisko; nie obchodź odrzuconego wymagania wstępnego ani nie zastępuj systemowych środowisk uruchomieniowych, by wymusić pozytywny wynik.

Root ma osobne pakiety i obsługę przycisku Home. Nie włączaj Developer Mode na istniejącej konfiguracji z rootem i zatrzymaj Home Helper No-root przed użyciem obsługi Home z edycji Root. Wybór edycji zależy od dostępu, który już masz; nie jest wyborem przycisku, który zrootuje telewizor.

## Porównaj utrzymanie i odzyskiwanie

- **Codzienne korzystanie:** obie edycje działają na telewizorze, z aplikacjami i motywami w launcherze.
- **Utrzymanie No-root:** zachowaj aktywny Developer Mode oraz wymagane przez Helper parowanie i łączność.
- **Utrzymanie Root:** zachowaj dostęp do niezależnych usług odzyskiwania i wymaganego przez nie środowiska uruchomieniowego. Dostępność aktualizacji zależy od zainstalowanej edycji i obsługiwanej ścieżki aktualizacji; sam root nie włącza OTA.
- **Wyjście awaryjne:** obecnie wspierane edycje używają trzech krótkich naciśnięć Home w ciągu dwóch sekund. Home Helper do wersji 0.6.13 włącznie używa zamiast tego przytrzymania przez dwie sekundy.

Po zatrzymaniu awaryjnym ponowne włączenie stałej obsługi Home wymaga wyraźnej czynności. W No-root otwórz Home Helper i wybierz Start Helper; w Root użyj Change Home w ustawieniach Home. Zobacz [porównanie edycji](/clean-your-tv-lg-webos/pl/editions/) i [pomoc w odzyskiwaniu](/clean-your-tv-lg-webos/pl/help/#home-button).

## Sprawdź telewizor przed instalacją

Przeczytaj [stronę zgodności](/clean-your-tv-lg-webos/pl/compatibility/), mając pod ręką dokładny model, wersję oprogramowania, webOS i typ pilota. Zgłoszone wyniki dotyczą konkretnej konfiguracji. Po konfiguracji sprawdź oddzielnie Home, uruchamianie aplikacji, dźwięk, czuwanie i uruchamianie po pełnym wyłączeniu. Zainstalowanie pakietu nie dowodzi, że wszystko działa.

Korzystaj z [opublikowanego instalatora i instrukcji instalacji](/clean-your-tv-lg-webos/pl/install/). Jeśli masz już działającą konfigurację i chcesz zmienić edycję, postępuj zgodnie z opisanymi krokami przejścia i usuwania zamiast instalować jedną na drugiej.

## Źródła i dalsze kroki

- [Porównanie edycji projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Wymagania i znane ograniczenia projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Co zmienia inny ekran główny](/clean-your-tv-lg-webos/pl/articles/change-lg-webos-home-screen/)
