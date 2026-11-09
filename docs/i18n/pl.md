# Clean Your TV — instrukcja użytkownika

instalator pyta o nazwę, domyślnie **Home**; CLI: `--tv-name "Aashiyaan"`. Po aktualizacji starszej instalacji automatycznie pojawia się **Ustawienia → Home → Nazwa TV**. Można ją zapisać lub przywrócić Home w każdej chwili. Nazwa przetrwa restart i obsługiwane aktualizacje; inne ustawienia pozostają zachowane. Do 48 znaków. Dotyczy launchera i jego ładowania, nie nazwy sieciowej. Wcześniejszy ekran LG może wymagać instalatora.

Nieopublikowana zmiana instalatora: przed nową instalacją instalator na komputerze sprawdza nowszą stabilną wersję na GitHubie. Wybierz „Otwórz GitHub i pobierz najnowszą wersję”, aby zatrzymać instalację i ją pobrać, lub „Nie, zainstaluj tę wersję”, aby jawnie kontynuować. Jeśli sprawdzenie się nie powiedzie, możesz kontynuować. Oczekujące operacje i odzyskiwanie pomijają sprawdzenie.

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

Dla Root instalator sprawdza i wybiera dostępny sposób sterowania Home. Jeśli nie można potwierdzić zgodności, instalacja zostaje zatrzymana; nie omijaj nieudanej kontroli.

**No-root → Root:** Jeśli po pełnym usunięciu ponownie zainstalowano No-root, przejście na Root może wymagać najpierw wyczyszczenia instalacji. Zachowaj ustawienia Home, wybierz **Odinstaluj Clean Your TV** z zapisanym połączeniem Root i poczekaj na potwierdzone usunięcie. Usunie to również Home i Helper z No-root. Następnie zainstaluj Root; zachowaj dane odzyskiwania.

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

Instalacja Root jest kontynuowana z ostrzeżeniem, jeśli nie można odczytać wejść TV, ale lista aplikacji jest prawidłowa. W Home może brakować wejść; nieodczytana lub pusta lista aplikacji nadal zatrzymuje instalację. Jeśli ostrzeżenie się powtarza, zapisz raport diagnostyczny.

## 5. Sprawdź pilota

1. Otwórz inną aplikację na TV i krótko naciśnij **Home**. Powinien otworzyć się Clean Your TV. W kreatorze zaznacz, co zobaczyłeś; pomiń test, jeśli go nie wykonałeś.
2. Sprawdź strzałki, OK, Wstecz, głośność i dźwięk. Osobno sprawdź czuwanie/wybudzenie i uruchomienie po odłączeniu zasilania. Sama udana instalacja nie sprawdza tych działań.

<a id="obsługa-i-odzyskiwanie"></a>

## 6. Obsługa i odzyskiwanie

Obsługa pilotów IR w No-root: zwolnienie Home po krótkim naciśnięciu planuje otwarcie Clean po około 700 ms; najpierw może mignąć LG Home. Przytrzymanie Home pozostaje w gestii webOS, a trzy naciśnięcia nadal zatrzymują Helper. Dostęp w zwykłym Developer Mode nie jest potwierdzony; nie zmieniaj uprawnień urządzeń wejściowych.

Strzałki wybierają, OK otwiera; przytrzymaj OK, aby zmienić kolejność. Krótkie Wstecz zachowuje nawigację aplikacji i jej potwierdzenie wyjścia. Home otwiera ekran Clean Your TV, gdy sterowanie jest aktywne. Przytrzymaj Wstecz przez 1,2 sekundy, aby jednorazowo otworzyć LG Home. Przełącznik sterowania Home i ustawienia pozostają bez zmian.

**Naciśnij Home trzy razy w ciągu dwóch sekund**, puszczając przycisk po każdym naciśnięciu. Przywraca to LG Home i zatrzymuje sterowanie bez usuwania preferencji.

No-root: Aby wznowić sterowanie Home, otwórz Home Helper, wybierz Uruchom Helper i potwierdź. Zapisany wybór ekranu Home zostaje zachowany. Root: włącz **Zmień Home** w ustawieniach Home, aby wznowić. **Otwórz LG Home** otwiera LG Home jednorazowo bez zmiany celu przycisku Home. Aby przywrócić LG Home jako stały cel, wyłącz **Zmień Home**. Nie uruchamiaj obu kontrolerów jednocześnie. Przy powtarzającym się błędzie pozostań przy LG Home.

Aktualizacja nie uruchamia ponownie zatrzymanego Helpera No-root. Wznów go jawnie zgodnie z opisem powyżej; nie usuwaj ręcznie znaczników zatrzymania.

## Potrzebujesz pomocy?

Jeśli po resecie lub zmianie SSH pojawi się `ssh-identity-changed`, zatrzymaj się: CYTV zablokował zmianę zapisanego klucza przed logowaniem. Pierwsza zgoda na zaufanie nie zastępuje klucza; oczekująca dezinstalacja nie wyjaśnia niezgodności. Zachowaj oryginalny profil, klucze i dane odzyskiwania. Nie ma obsługiwanego automatycznego polecenia ponownego zaufania. Potrzebna jest niezależna weryfikacja tożsamości/odcisku TV oraz sprawdzona procedura zachowująca profil: [odzyskiwanie po zmianie tożsamości SSH](../RECOVERY.md#ssh-identity-changed).

Po przerwaniu instalacji użyj tego samego zapisanego połączenia i najpierw wybierz **Sprawdź stan TV**. Kontynuuj tylko przez odzyskiwanie zaproponowane przez kreator. Gdy stan jest nieznany, zapisz raport diagnostyczny i zatrzymaj się; zachowaj dane odzyskiwania i nie ponawiaj instalacji w ciemno.

Podczas odzyskiwania pozostaw sterowanie Home wyłączone i zachowaj oryginalne raporty diagnostyczne oraz zapisane połączenie. Kontrolę i zmiany potwierdzaj osobno. Postępuj zgodnie ze szczegółowym przewodnikiem dla zainstalowanej wersji; nie wymuszaj ponownej instalacji ani nie usuwaj stanu odzyskiwania.

Podaj model TV, firmware, No-root lub Root, urządzenie instalujące, krok i komunikat błędu. Usuń hasła, klucze, adresy i dane osobiste przed udostępnieniem raportu. Raport nie jest publikowany automatycznie.

[Zgłoś problem](../FEEDBACK.md) · [Odzyskiwanie — angielski](../RECOVERY.md) · [Aktualizacja i usuwanie — angielski](../MAINTENANCE.md) · [Inne języki](../LANGUAGES.md)

### Proste usuwanie

Wybierz **Odinstaluj Clean Your TV** w Konserwacji dla tego samego zapisanego połączenia. Potwierdź raz. Znane aplikacje i pliki projektu, które istnieją, zostaną usunięte; brakujące zostaną pominięte, także po częściowej instalacji.

Na starszych telewizorach bez osobnej aplikacji LG Home usuwanie No-root może przełączyć ekran na telewizję na żywo. Pozostaw telewizor włączony i uruchom go ponownie, jeśli pojawi się prośba; nie usuwaj danych odzyskiwania ani nie resetuj telewizora.

Gdy pojawi się prośba, odłącz zasilanie TV, podłącz ponownie, poczekaj na sieć i wybierz **Spróbuj ponownie**. Czuwanie lub Quick Start nie jest pełnym restartem; CYTV nie uruchamia TV ponownie automatycznie. Po utracie połączenia sprawdź je i ponów to samo usuwanie bez kolejnego kreatora odzyskiwania. Przy odmowie dostępu użyj żądanego połączenia Root; gdy TV jest zajęty, poczekaj i ponów. Sukces pojawi się dopiero po weryfikacji końcowego czyszczenia. Zachowaj klucze i oryginalne raporty. Sterowanie awaryjne i zgoda na udostępnianie nadal obowiązują.

Po nieudanej lub przerwanej instalacji odzyskiwanie jest dostępne bezpośrednio. Jeśli No-root nie może kontynuować, potwierdź raz pełne usunięcie. Przy chwilowej utracie połączenia lub zajętym procesie CYTV usuwanie podejmuje do trzech prób. Jeśli potrzebny jest Root, wybierz **Połącz przez Root** dla tego samego TV; zweryfikowane czyszczenie Root kończy też zablokowane usuwanie No-root. Po błędzie aktywacji Root CYTV próbuje przywrócić i sprawdzić LG Home bez ponownej aktywacji. Anulowanie z niedokończoną pracą zachowuje raport i działania odzyskiwania. Stan zatrzymania awaryjnego pozostaje bez zmian.

Po błędzie połączenia podczas usuwania otwórz szczegóły, sprawdź sieć lub wybierz istniejący klucz SSH Root i ponów próbę. Adres, edycja, port i weryfikacja klucza telewizora pozostają ustalone. No-root sprawdza Helper przed parowaniem: zatrzymaj go i potwierdź ponowne sprawdzenie w tym samym procesie. Tylko zweryfikowany pusty telewizor bez niedokończonej instalacji może pominąć restart; po faktycznym usuwaniu wykonaj wymagany restart. Awaria usługi wejść pozwala kontynuować bezpieczne usuwanie pakietów; sukces nadal wymaga potwierdzenia usunięcia skrótu.

**Ponowna instalacja Root:** Wybierz **Skonfiguruj telewizor → Root** z zapisanym połączeniem i potwierdź **Zainstalować Root ponownie?**. Instalator przywraca LG Home i całkowicie usuwa Clean Your TV, jego aktualizatory, Home Helper i zapisane ustawienia. Po zweryfikowaniu usunięcia instaluje i aktywuje pakiety oraz środowisko Root dołączone do tego instalatora. Inne aplikacje TV i istniejący dostęp root/SSH zostają zachowane. Jeśli usuwanie się zatrzyma lub zażąda pełnego restartu, dokończ je przed ponownym rozpoczęciem konfiguracji. Samo **Odinstaluj Clean Your TV** nigdy nie uruchamia nowej instalacji.

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

<a id="kandydat-unreleased-starszy-nodejs-w-tv"></a>
<a id="starszy-nodejs-w-tv-opublikowano-w-v1120"></a>
<a id="proste-usuwanie-v1110"></a>

## Pogoda

Otwórz Ustawienia → Pogoda, pod Tapetami. Włącz pogodę i otwórz Miasto, aby wyszukać właściwy region i kraj, lub wybierz Automatycznie, aby określić przybliżone miasto według połączenia internetowego. VPN może zmienić wynik; jeśli miasta brakuje lub jest błędne, użyj wyszukiwania ręcznego. Wykryte lub wybrane miasto widać w ustawieniach. Wybierz °C / m/s lub °F / mph oraz dostępny format: krótki, aktualny, szczegółowy lub cztery dni. Podgląd pasuje do motywu; Przykład oznacza dane demonstracyjne. Liquid Glass obsługuje tylko krótki format. Ribbon i Atmosphere nie pokazują pogody. Wyłączenie zatrzymuje zapytania i ukrywa miasto, jednostki oraz format; wybór źródła pozostaje dostępny. Podczas awarii ostatnie dane mogą pozostać przez pewien czas; później pogoda znika do czasu odświeżenia.

Wybierz źródło prognozy: Auto, MET Norway lub Open-Meteo. Auto zaczyna od MET Norway, po błędzie raz próbuje Open-Meteo, a następnie korzysta z ostatniego działającego źródła i jego pamięci podręcznej. Wybór ręczny nigdy nie zmienia źródła automatycznie. Nowe ustawienia używają Auto; zapisane bez źródła zachowują Open-Meteo. Rzeczywiste źródło jest widoczne w ustawieniach. Dostępność zależy od sieci. MET odświeża dane najwyżej co trzy godziny; pamięć podręczna wygasa po sześciu godzinach. Brakujące pola są ukryte: MET nie podaje temperatury odczuwalnej ani prawdopodobieństwa opadów. Zakresy dobowe podsumowują punkty prognozy, nie zmierzone ekstrema.

Współrzędne trafiają do api.met.no lub api.open-meteo.com, wyszukiwania miast do geocoding-api.open-meteo.com. Opcjonalna automatyczna lokalizacja wysyła publiczny adres IP do get.geojs.io. Połączenia używają HTTPS; klucz API nie jest potrzebny. Miejsce, źródło i pamięć podręczna pozostają w telewizorze. Źródła danych zawierają warunki i autorstwo, w tym Norweski Instytut Meteorologiczny (MET Norway, CC BY 4.0).

Przycisk Źródła danych w nagłówku Pogoda otwiera informacje o usługach i licencjach.
