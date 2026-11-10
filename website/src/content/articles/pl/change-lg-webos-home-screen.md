---
lang: pl
topic: change-lg-webos-home-screen
title: "Jak zmienić ekran główny telewizora LG webOS"
description: "Dostosuj ekran główny telewizora LG webOS dzięki Clean Your TV. Dowiedz się, co zmienia launcher, którą edycję wybrać i co sprawdzić przed instalacją."
updated: '2026-11-09'
---

Clean Your TV to alternatywny ekran główny dla telewizorów LG webOS. Pozwala ustawić aplikacje w wybranej kolejności, oferuje motywy i konfigurowalny dock. Po konfiguracji działa na telewizorze, więc możesz wyłączyć komputer. Obsługa przycisku Home zależy od telewizora, oprogramowania, pilota i metody instalacji.

## Co możesz dostosować?

Launcher zmienia ekran, na którym znajdujesz i uruchamiasz aplikacje telewizora. Możesz uporządkować ulubione aplikacje i wybrać układ, na przykład Classic, Liquid Glass lub Ribbon. Wypróbuj [demo w przeglądarce](/clean-your-tv-lg-webos/demo/), aby porównać układy przed instalacją. Sterowanie telewizorem jest w nim symulowane; demo nie sprawdzi zgodności z Twoim odbiornikiem.

Alternatywny launcher nie zastępuje oprogramowania webOS, nie odblokowuje płatnego streamingu ani nie usuwa reklam w innych aplikacjach. Ustawienia obrazu, wejścia i serwisy streamingowe pozostają oddzielnymi częściami telewizora. Jeśli zależy Ci głównie na spokojniejszym ekranie głównym, przeczytaj, [co zmienia się w kwestii reklam](/clean-your-tv-lg-webos/pl/articles/lg-tv-home-screen-ads/).

## Którą metodę instalacji wybrać?

Użyj No-root na telewizorze z aktywnym LG Developer Mode. Działający na telewizorze Home Helper obsługuje przycisk Home tam, gdzie jest to wspierane. Developer Mode musi pozostać aktywny; wygaśnięcie sesji może spowodować usunięcie aplikacji zainstalowanych poza sklepem.

Użyj Root tylko wtedy, gdy telewizor ma już działający dostęp root i spełnia wymagania dotyczące środowiska uruchomieniowego oraz usług. Instalator Clean Your TV nie rootuje telewizora. Nie włączaj Developer Mode na istniejącej konfiguracji z rootem i nie uruchamiaj obu metod obsługi Home jednocześnie. [Poradnik wyboru edycji](/clean-your-tv-lg-webos/pl/articles/root-vs-no-root/) wyjaśnia różnice i ograniczenia.

## Zanim zmienisz działającą konfigurację

1. Zapisz dokładny model, wersję oprogramowania, wersję webOS i typ pilota. Porównaj je z [wymaganiami i zgłoszonymi wynikami testów TV](/clean-your-tv-lg-webos/pl/compatibility/); każde zgłoszenie dotyczy opisanej w nim konfiguracji.
2. Postępuj zgodnie z [instrukcją instalacji](/clean-your-tv-lg-webos/pl/install/) i użyj opublikowanego instalatora wskazanego w przewodniku. Podczas konfiguracji telewizor i urządzenie z instalatorem muszą być w sieci, która umożliwia im komunikację.
3. Po konfiguracji sprawdź uruchamianie aplikacji i Home, a następnie oddzielnie dźwięk, czuwanie/wybudzanie i uruchamianie po pełnym wyłączeniu. Pomyślne zainstalowanie pakietu nie potwierdza tych zachowań.

## Jak wrócić do LG Home?

W obecnie wspieranych edycjach trzy krótkie naciśnięcia Home w ciągu dwóch sekund uruchamiają wyjście awaryjne. Starszy Home Helper, do wersji 0.6.13 włącznie, używa przytrzymania Home przez dwie sekundy. Jednorazowe otwarcie LG Home i wyłączenie stałej obsługi przycisku Home to różne czynności; skorzystaj z [instrukcji odzyskiwania](/clean-your-tv-lg-webos/pl/help/#home-button) dla zainstalowanej edycji. Przed zmianą zachowania przy uruchamianiu zapewnij sobie dostęp do sposobu odzyskania kontroli.

## Źródła i dalsze kroki

- [Dokumentacja projektu: edycje i sterowanie](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Instalacja i wymagania wstępne projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: jak zachować dostęp do konfiguracji No-root](/clean-your-tv-lg-webos/pl/articles/lg-developer-mode/)
