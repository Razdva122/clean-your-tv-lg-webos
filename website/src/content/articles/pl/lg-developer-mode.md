---
lang: pl
topic: lg-developer-mode
title: "LG Developer Mode dla launchera webOS No-root"
description: "Dowiedz się, dlaczego Clean Your TV No-root wymaga LG Developer Mode, co wygaśnięcie sesji oznacza dla aplikacji spoza sklepu i co sprawdzić, gdy launcher zniknie."
updated: '2026-11-09'
---

LG Developer Mode pozwala instalować i testować aplikacje webOS TV bez rootowania telewizora. Clean Your TV No-root korzysta z tej metody dostępu wraz z działającym na telewizorze Home Helperem. Sesja Developer Mode ma ograniczony czas: sprawdzaj pozostały czas w aplikacji Developer Mode firmy LG i przedłużaj sesję przed wygaśnięciem, aby zachować dostęp do aplikacji zainstalowanych poza sklepem.

## Co zapewnia Developer Mode?

Developer Mode zapewnia dostęp programistyczny; nie daje uprawnień root ani gwarancji, że narzędzie obsługujące przycisk Home zadziała na każdym modelu. Clean Your TV nadal sprawdza wymagania dotyczące środowiska uruchomieniowego i obsługi przycisków. Zwykłe aplikacje ze sklepu, aplikacje instalowane poza sklepem i system z rootem korzystają z różnych sposobów dostępu.

Używaj No-root wyłącznie z odpowiednią konfiguracją Developer Mode. Jeśli telewizor ma już root, nie włączaj na nim Developer Mode. Najpierw przeczytaj [porównanie Root i No-root](/clean-your-tv-lg-webos/pl/articles/root-vs-no-root/) oraz [wymagania zgodności](/clean-your-tv-lg-webos/pl/compatibility/).

## Przygotuj telewizor i urządzenie do instalacji

Dokładne kroki znajdziesz w [aktualnej instrukcji instalacji](/clean-your-tv-lg-webos/pl/install/). Potrzebne będą aplikacja Developer Mode firmy LG, wymagane logowanie na konto programisty LG i Key Server do parowania. Telewizor oraz komputer lub obsługiwane urządzenie z Androidem muszą być w sieci umożliwiającej im komunikację. Sieć dla gości lub izolacja klientów mogą uniemożliwić konfigurację, nawet jeśli oba urządzenia mają dostęp do internetu.

Zachowaj klucze parowania i dane połączenia w tajemnicy. Korzystaj z opublikowanego instalatora wskazanego w instrukcji; pobranie dowolnego pliku IPK nie jest pełną konfiguracją obsługi Home. Po instalacji launcher i Helper działają na telewizorze; komputer można wyłączyć.

## Utrzymuj aktywną sesję

Otwórz aplikację Developer Mode firmy LG, sprawdź pozostały czas sesji i przedłuż ją, gdy dostępne jest wymagane połączenie. Kieruj się aktualnymi instrukcjami LG, zamiast polegać na stałej liczbie godzin podanej w starym artykule. Sama próba przedłużenia nie potwierdza sukcesu: po niej sprawdź wyświetlany pozostały czas.

Clean Your TV oferuje opcjonalne automatyczne przedłużanie jako funkcję beta, domyślnie wyłączoną. Jeśli ją włączysz, nadal sprawdzaj rzeczywisty stan Developer Mode. Funkcja nie znosi wymagań LG dotyczących sesji i nie utrwala wyłączonego trybu.

## Co zrobić, gdy launcher zniknie lub Home otwiera LG Home?

Sprawdź Developer Mode, zanim zaczniesz wielokrotnie powtarzać instalację. Dokumentacja LG mówi, że wyłączenie Developer Mode lub wygaśnięcie sesji może odinstalować aplikacje programistyczne. Wygaśnięcie sesji to inna sytuacja niż awaryjne zatrzymanie Home Helpera, problem z parowaniem lub przerwana instalacja.

Jeśli aplikacje programistyczne zostały usunięte, przywróć Developer Mode zgodnie z dokumentacją i użyj prowadzonej konfiguracji lub odzyskiwania w instalatorze, odpowiednio do faktycznego stanu. Jeśli aplikacje pozostały, ale obsługa Home jest zatrzymana, skorzystaj z [pomocy dotyczącej przycisku Home](/clean-your-tv-lg-webos/pl/help/#home-button). Przy przerwanej operacji skorzystaj z [poradnika odzyskiwania](/clean-your-tv-lg-webos/pl/help/#interrupted), zamiast usuwać pliki systemowe. Po odzyskaniu konfiguracji oddzielnie sprawdź zachowanie Home.

## Źródła i dalsze kroki

- [LG: korzystanie z aplikacji Developer Mode](https://webostv.developer.lge.com/develop/getting-started/developer-mode-app)
- [Instrukcja instalacji No-root projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Dokumentacja odzyskiwania projektu](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/RECOVERY.md)
