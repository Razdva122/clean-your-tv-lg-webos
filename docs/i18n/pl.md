# Clean Your TV — instrukcja użytkownika

Clean Your TV to własny ekran główny dla LG webOS: Twoje aplikacje w Twojej kolejności, bez sponsorowanych rzędów w tym menu. Zainstaluj go z komputera lub telefonu z Androidem; potem komputer może być wyłączony.

## 1. Pobierz instalator

Kliknij obrazek swojego urządzenia. Przyciski pobierają najnowsze opublikowane wydanie. Na Macu wybierz Apple Silicon (M1 lub nowszy) albo Intel; sprawdź w menu Apple → Ten Mac.

[![Pobierz — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Pobierz — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Pobierz — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Pobierz — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Pobierz — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="wybierz-edycję"></a>

<a id="wymagania"></a>

## 2. Wybierz edycję

Włącz TV i podłącz go do tej samej sieci domowej co komputer lub telefon. Zezwól CYTV na dostęp do sieci lokalnej, gdy o to poprosi.

- **No-root** — jeśli nie masz dostępu root. Przygotuj Developer Mode zgodnie z instrukcją poniżej.
- **Root** — jeśli masz już dostęp root przez SSH. Instalator nie rootuje TV. Nie włączaj Developer Mode na tym TV; zachowaj dostęp SSH i dane odzyskiwania.

### Konfiguracja Developer Mode (No-root)

Developer Mode pozwala CYTV instalować aplikacje na TV bez roota.

1. Na TV otwórz LG Apps, wyszukaj Developer Mode i zainstaluj aplikację.
2. Otwórz Developer Mode i zaloguj się na konto LG Developer. W razie potrzeby utwórz konto na [LG Developer](https://webostv.developer.lge.com).
3. Włącz Dev Mode Status. TV uruchomi się ponownie. Następnie otwórz ponownie Developer Mode.
4. Włącz Key Server i pozostaw Developer Mode otwarty. Wpisz widoczny IP Address jako adres TV w CYTV.
5. Wpisz Passphrase: sześć znaków widocznych w Developer Mode na TV. Zachowaj wielkość liter.

Użyj kodu z TV, a nie hasła konta LG. Jeśli kodu nie widać, włącz Key Server.

Parowanie to osobny krok: gdy TV zapyta, zatwierdź CYTV pilotem.

Utrzymuj Developer Mode aktywny: przed końcem odliczania otwórz aplikację i naciśnij EXTEND, gdy TV ma internet. Po wygaśnięciu LG może usunąć te aplikacje.

<a id="instalacja-i-język"></a>

## 3. Otwórz instalator

- **Windows x64:** pobierz `cytv-windows-x64-desktop.zip`, wybierz **Wyodrębnij wszystkie** w Eksploratorze i otwórz `cytv-desktop/cytv-desktop.exe`. Zachowaj obok folder `_internal`.
- **macOS 13+:** rozpakuj `cytv-macos-arm64.zip` dla Apple Silicon lub `cytv-macos-x64.zip` dla Intela. Przenieś `cytv.app` do Aplikacji i otwórz; zezwól na dostęp do sieci lokalnej. Jeśli zaufany plik zostanie zablokowany, użyj Prywatność i ochrona → Otwórz mimo to; nie wyłączaj Gatekeepera.
- **Linux x64:** na Ubuntu 22.04+, Debianie 12+ lub Mint 21+ zainstaluj `cytv-linux-x64.deb` przez graficzny menedżer pakietów i otwórz Clean Your TV z menu. Pobranie bibliotek może wymagać Internetu. Nie ma pakietu Linux ARM.

**Android ARM64:** potrzebny jest telefon ARM 64-bit z Androidem 7+ i WebView/Chrome 108+. Otwórz pobrany APK i zezwól na instalację z tego źródła, jeśli Android o to poprosi. Otwórz CYTV; język wybierzesz w prawym górnym rogu. Aktualizuj bez odinstalowywania i czyszczenia danych.

Kreator początkowo używa języka systemu i zapamiętuje wybrany język. Na telewizorze otwórz **Ustawienia → Język** i wybierz język lub automatyczny wybór według systemu. Preferencje instalatora i telewizora są niezależne. Kody zawiera [spis języków](../LANGUAGES.md).

## 4. Zainstaluj na telewizorze

1. W CYTV wybierz **Skonfiguruj mój TV**. Na komputerze wybierz wykryty TV; na Androidzie wpisz jego adres IP. Jeśli wyszukiwanie nic nie znajdzie, wpisz adres ręcznie.
2. Wybierz **No-root** lub **Root** i sprawdź wybrany TV przed kontynuowaniem.
3. No-root: wpisz kod z Developer Mode i zaakceptuj prośbę na TV. Root: użyj swoich danych SSH. Akceptuj nową tożsamość SSH tylko dla własnego TV w zaufanej sieci. Jeśli zapisany klucz się zmienił, zatrzymaj się i ustal przyczynę.
4. Postępuj według kreatora. Zostaw TV włączony, nie zmieniaj sieci i nie zamykaj CYTV do końca. Nie wymuszaj zatrzymania aplikacji Android. Root włącza sterowanie Home zaraz po przygotowaniu odzyskiwania.

## 5. Sprawdź pilota

1. Otwórz inną aplikację na TV i krótko naciśnij **Home**. Powinien otworzyć się Clean Your TV. W kreatorze zaznacz, co zobaczyłeś; pomiń test, jeśli go nie wykonałeś.
2. Sprawdź strzałki, OK, Wstecz, głośność i dźwięk. Osobno sprawdź czuwanie/wybudzenie i uruchomienie po odłączeniu zasilania. Sama udana instalacja nie sprawdza tych działań.

<a id="obsługa-i-odzyskiwanie"></a>

## 6. Obsługa i odzyskiwanie

Strzałki wybierają, OK otwiera; przytrzymaj OK, aby zmienić kolejność. Krótkie Wstecz zachowuje nawigację aplikacji i jej potwierdzenie wyjścia. Home otwiera ekran Clean Your TV, gdy sterowanie jest aktywne. Przytrzymaj Wstecz przez 1,2 sekundy, aby jednorazowo otworzyć LG Home. Przełącznik sterowania Home i ustawienia pozostają bez zmian.

**Naciśnij Home trzy razy w ciągu dwóch sekund**, puszczając przycisk po każdym naciśnięciu. Przywraca to LG Home i zatrzymuje sterowanie bez usuwania preferencji.

No-root: Aby wznowić sterowanie Home, otwórz Home Helper, wybierz Uruchom Helper i potwierdź. Zapisany wybór ekranu Home zostaje zachowany. Root: włącz **Zmień Home** w ustawieniach Home, aby wznowić. **Otwórz LG Home** otwiera LG Home jednorazowo bez zmiany celu przycisku Home. Aby przywrócić LG Home jako stały cel, wyłącz **Zmień Home**. Nie uruchamiaj obu kontrolerów jednocześnie. Przy powtarzającym się błędzie pozostań przy LG Home.

## Potrzebujesz pomocy?

Po przerwaniu instalacji użyj tego samego zapisanego połączenia i najpierw wybierz **Sprawdź stan TV**. Kontynuuj tylko przez odzyskiwanie zaproponowane przez kreator. Gdy stan jest nieznany, zapisz raport diagnostyczny i zatrzymaj się; zachowaj dane odzyskiwania i nie ponawiaj instalacji w ciemno.

Podczas odzyskiwania pozostaw sterowanie Home wyłączone i zachowaj oryginalne raporty diagnostyczne oraz zapisane połączenie. Kontrolę i zmiany potwierdzaj osobno. Postępuj zgodnie ze szczegółowym przewodnikiem dla zainstalowanej wersji; nie wymuszaj ponownej instalacji ani nie usuwaj stanu odzyskiwania.

Podaj model TV, firmware, No-root lub Root, urządzenie instalujące, krok i komunikat błędu. Usuń hasła, klucze, adresy i dane osobiste przed udostępnieniem raportu. Raport nie jest publikowany automatycznie.

[Zgłoś problem](../FEEDBACK.md) · [Odzyskiwanie — angielski](../RECOVERY.md) · [Aktualizacja i usuwanie — angielski](../MAINTENANCE.md) · [Inne języki](../LANGUAGES.md)

W nadchodzących kompilacjach ostrzeżenie i przycisk „Wyłącz podgląd HDMI” pojawią się przy wybranym lub aktywnym 4K tylko w motywach z włączonym podglądem wejść. Podczas podglądu HDMI tapeta wideo 4K jest tymczasowo zastępowana statycznym obrazem 1080p. Wyłącz podgląd wejść, aby zachować tapetę w 4K.

### Kandydat: odzyskiwanie i pełne usuwanie

Przyciski powyżej nadal pobierają opublikowaną wersję. Następny kandydat dodaje kontynuację oryginalnej operacji i **Odinstaluj Clean Your TV** na komputerze i Androidzie. Użyj tego samego zapisanego połączenia; osobno potwierdź kontrolę i każdą zmianę. Kwalifikującą się konfigurację Root można zakończyć z LG Home i wyłączonym sterowaniem Home. Wybrany cel jest osiągnięty; fizyczny Home, dźwięk, czuwanie i zimny start pozostają osobnymi kontrolami.

Usuwanie zachowuje wcześniejszy wynik i zgłasza sukces dopiero po sprawdzeniu usunięcia własnych aplikacji, usług, autostartu i prywatnych danych konfiguracji. Oczekujące zadania, nieznany wynik dostawcy, konflikt własności lub brak kontroli mogą je zablokować; nie jest gwarantowane po każdej awarii. Zachowaj istniejący raport i dane odzyskiwania. Nie instaluj ponownie, nie kasuj danych aplikacji, nie resetuj Developer Mode i nie wymuszaj usuwania. Przyszła obserwacja nie odtworzy dawnych wyników. Powyższe sterowanie awaryjne pozostaje dostępne; udostępnienie raportu wymaga Twojej zgody.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="opcjonalny-python-dla-root"></a>
<a id="testy-sprzętowe-i-ograniczenia"></a>
<a id="blokada-oprogramowania-lg-w-120"></a>
<a id="nowości-w-130-odzyskiwanie-w-instalatorze-komputerowym"></a>
<a id="nowości-w-130--12"></a>
<a id="nieopublikowany-kandydat-instalacja-root-przez-homebrew"></a>
<a id="nieopublikowany-kandydat-odzyskiwanie-dźwięku-hdmi-root"></a>
<a id="motywy--kandydat-rozwojowy"></a>
<a id="kategorie-ustawień-nieopublikowany-kandydat"></a>
<a id="automatyczna-rozdzielczość-grafiki-kandydat"></a>
<a id="aktualizacja-i-usuwanie"></a>
<a id="pomoc-i-dalsze-instrukcje"></a>
<a id="motywy"></a>
<a id="kategorie-ustawień-154"></a>
<a id="automatyczna-rozdzielczość-grafiki-160"></a>
<a id="miejsce-na-dane"></a>

Szczegółowe instrukcje po angielsku: [wymagania](../COMPATIBILITY.md) · [sterowanie](../CONTROLS.md) · [motywy](../THEMES.md) · [aktualizacje](../UPDATES.md).
