# Clean Your TV — instrukcja użytkownika

> v1.5.0: motywy, galeria i przesyłanie z komputera na TV. Znane ograniczenia Root: Appearance może przesunąć się o 110 px; Home może nie otworzyć się automatycznie po czuwaniu. Zakres testów urządzeń jest ograniczony. [1.5.0](../RELEASE-1.5.0.md).

> Następny kandydat (nieopublikowany): motywy o stałym układzie zachowują miejsce ukrytego wiersza Columns, aby Apply nie zmieniało pozycji przewijania Appearance. Wskaźnik, klawiatura i narzędzia dostępności pomijają Columns. Weryfikacja na TV pozostaje do wykonania.

[Dokumentacja](../README.md) · [Zgłoś problem](../FEEDBACK.md)

Poradnik opisuje opublikowaną wersję **[1.5.2](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.5.2)**. Akceptacja C3 obejmuje zapisane testy zasilania, Home, fokusu, zachowania stanu wyłączenia i ręcznego cofnięcia wersji. Inne telewizory, dźwięk eARC i fizyczne urządzenia Android pozostają niezweryfikowane; udana instalacja nie dowodzi zgodności. [Zakres testów (angielski)](../RELEASE-1.4.0-ACCEPTANCE.md).

**Nieopublikowany instalator:** konsola, aplikacja desktopowa i Android pokazują stan każdej kontroli TV: niesprawdzona, w toku, zaliczona, niezaliczona lub niemożliwa do potwierdzenia. Wyniki pozostają po błędzie. Node.js/Python jest sprawdzany w telewizorze; `doctor` nie przygotowuje Pythona ani nie prosi o parowanie sterowania. Zapisz raport przed ponowną próbą.

## Wybierz edycję

No-root i Root to równorzędne opcje dla różnych konfiguracji telewizora. Wybierz No-root dla LG Developer Mode lub Root, jeśli masz już dostęp root przez SSH. Zgodność i zakres wykonanych testów są określane osobno dla każdej wersji.

- **No-root:** włącz LG Developer Mode i Key Server. Wpisz hasło wyświetlane na telewizorze i zaakceptuj na nim osobne żądanie parowania. Developer Mode musi pozostać aktywny: wygaśnięcie sesji może usunąć tak zainstalowane aplikacje. Sprawdzaj oficjalny licznik także przy włączonym odnawianiu Beta. Monitorowanie Helper wymaga sieci lokalnej.
- **Root:** potrzebny jest istniejący dostęp root przez SSH. Instalator nie uzyskuje uprawnień root. Nie włączaj Developer Mode na telewizorze z istniejącym rootem. Zachowaj dostęp root i usługi odzyskiwania.

Root wymaga działających interfejsów Home usług Settings Service i System Profile (`com.webos.service.systemprofile`); sam dostęp root nie potwierdza zgodności.

## Wymagania

Włącz telewizor i połącz go z tą samą zaufaną siecią lokalną co komputer. Później komputer może być wyłączony. Zgodność zależy od modelu, oprogramowania i pilota; Root ma nieukończone testy sprzętowe.

Node 0.10.25 dotyczy nieopublikowanej kompilacji źródłowej/testowej; opublikowane instalatory nadal wymagają 0.12.2+. Zobacz [zgodność](../COMPATIBILITY.md).

No-root Helper wymaga Node.js **0.10.25+** na TV. Root wymaga Node.js **8+** i działającego Pythona **3.9+**. W razie potrzeby instalator pobierze zweryfikowanego prywatnego Pythona; początkowe przygotowanie wymaga **320 MiB** wolnego miejsca. Nie zastępuje Pythona systemowego. Zachowaj środowiska potrzebne do odzyskiwania. [Python (angielski)](../OPTIONAL-PYTHON.md). Odnawianie Developer Mode to **Beta, domyślnie wyłączona**; rzeczywiste odnawianie bez roota nie zostało potwierdzone. Nadal sprawdzaj oficjalny licznik.

### Konfiguracja Developer Mode (No-root)

Developer Mode pozwala CYTV instalować aplikacje na TV bez roota.

1. Na TV otwórz LG Apps, wyszukaj Developer Mode i zainstaluj aplikację.
2. Otwórz Developer Mode i zaloguj się na konto LG Developer. W razie potrzeby utwórz konto na webostv.developer.lge.com.
3. Włącz Dev Mode Status. TV uruchomi się ponownie. Następnie otwórz ponownie Developer Mode.
4. Włącz Key Server i pozostaw Developer Mode otwarty. Wpisz widoczny IP Address jako adres TV w CYTV.
5. Wpisz Passphrase: sześć znaków widocznych w Developer Mode na TV. Zachowaj wielkość liter.

Użyj kodu z TV, a nie hasła konta LG. Jeśli kodu nie widać, włącz Key Server.

Parowanie to osobny krok: gdy TV zapyta, zatwierdź CYTV pilotem.

Utrzymuj Developer Mode aktywny: przed końcem odliczania otwórz aplikację i naciśnij EXTEND, gdy TV ma internet. Po wygaśnięciu LG może usunąć te aplikacje.

## Instalacja i język

- **Windows x64:** pobierz `cytv-windows-x64-desktop.zip`, wybierz **Wyodrębnij wszystkie** w Eksploratorze i otwórz `cytv-desktop/cytv-desktop.exe`. Zachowaj obok folder `_internal`. Podpis wydawcy Windows nie jest skonfigurowany. Osobna konsola to `cytv-windows-x64.exe`; zmień nazwę na `cytv.exe` i użyj `.\cytv.exe` w PowerShell dla poniższych poleceń.
- **macOS 13+:** rozpakuj `cytv-macos-arm64.zip` dla Apple Silicon lub `cytv-macos-x64.zip` dla Intela. Przenieś `cytv.app` do Aplikacji i otwórz; zezwól na dostęp do sieci lokalnej. Jeśli zaufany plik zostanie zablokowany, użyj Prywatność i ochrona → Otwórz mimo to; nie wyłączaj Gatekeepera. Zgodność ze starszymi systemami nie jest w pełni potwierdzona.
- **Linux x64:** na Ubuntu 22.04+, Debianie 12+ lub Mint 21+ zainstaluj `cytv-linux-x64.deb` przez graficzny menedżer pakietów i otwórz Clean Your TV z menu. Pobranie bibliotek może wymagać Internetu. Nie ma pakietu Linux ARM. Samodzielny plik `cytv-linux-x64` to CLI; aplikacja graficzna jest w pakiecie `.deb`.

[Instalator Android (angielski)](../../android/README.md): wybierz język w prawym górnym rogu. Aktualizuj bez odinstalowania i czyszczenia danych. Android 7 / WebView 108 to minimum, a nie sprawdzony telefon; testy akceptacyjne używały emulatora Android 15 ARM64 / WebView 124. Fizyczne telefony i odzyskiwanie z połączeniem do prawdziwego TV pozostają niezweryfikowane.

Kreator początkowo używa języka systemu i zapamiętuje wybrany język. Na telewizorze otwórz **Ustawienia → Język** i wybierz język lub automatyczny wybór według systemu. Preferencje instalatora i telewizora są niezależne. Kody zawiera [spis języków](../LANGUAGES.md).

Dla osobno pobranej CLI na macOS/Linux, w rozpakowanym katalogu:

```sh
chmod +x cytv
./cytv --language pl install
```

Wybierz telewizor lub podaj IP, wybierz edycję i sprawdź podsumowanie. Nową tożsamość SSH zatwierdzaj tylko dla własnego telewizora w zaufanej sieci; zmieniony zapisany klucz blokuje dostęp. Root przygotowuje odzyskiwanie i od razu aktywuje Home, bez okresu próbnego ani potwierdzenia zachowania ustawień. Sprawdź strzałki, OK, Home, Wstecz/Anuluj, głośność, czuwanie i uruchomienie po całkowitym odłączeniu zasilania.

## Obsługa i odzyskiwanie

Strzałki wybierają, OK otwiera; przytrzymaj OK, aby zmienić kolejność. Krótkie Wstecz zachowuje nawigację aplikacji i jej potwierdzenie wyjścia. Home otwiera ekran Clean Your TV, gdy sterowanie jest aktywne. Przytrzymaj Wstecz przez 1,2 sekundy, aby jednorazowo otworzyć LG Home. Przełącznik sterowania Home i ustawienia pozostają bez zmian.

**Naciśnij Home trzy razy w ciągu dwóch sekund**, puszczając przycisk po każdym naciśnięciu. Przywraca to LG Home i zatrzymuje sterowanie bez usuwania preferencji. W No-root Helper do wersji 0.6.13 włącznie zamiast tego przytrzymaj Home około dwóch sekund. Przytrzymanie Home nie jest gestem awaryjnym Root.

No-root: Aby wznowić sterowanie Home, otwórz Home Helper, wybierz Uruchom Helper i potwierdź. Zapisany wybór ekranu Home zostaje zachowany. Root: włącz **Zmień Home** w ustawieniach Home, aby wznowić. **Otwórz LG Home** otwiera LG Home jednorazowo bez zmiany celu przycisku Home. Aby przywrócić LG Home jako stały cel, wyłącz **Zmień Home** lub uruchom `cytv restore`. Nie uruchamiaj obu kontrolerów jednocześnie. Przy powtarzającym się błędzie pozostań przy LG Home.

```sh
./cytv --language pl status
./cytv --language pl doctor --report
./cytv --language pl restore
./cytv --language pl uninstall
```

Po przerwaniu operacji najpierw uruchom `status` i zachowaj dzienniki. `restore` przywraca LG Home bez usuwania aplikacji; `uninstall` przywraca je przed usunięciem. Dane odzyskiwania Root pozostają celowo: nie kasuj ich, by wymusić ponowną instalację. Sprawdź raporty przed udostępnieniem; nie publikuj kluczy ani katalogów profili.

Tylko w nieopublikowanej wersji kandydującej, w obu edycjach: otwórz **Ustawienia Home → Wygląd → Kolumny** i wybierz od 1 do 8 kolumn lub **Według motywu**, aby użyć wartości motywu (Classic: 5). Wybrana liczba ma pierwszeństwo przed motywem. Motywy ze stałym układem ukrywają opcję kolumn i używają wartości autora. Zapisany wybór wraca po przełączeniu na motyw obsługujący to ustawienie. W podglądzie kandydata Alpine aplikacje tworzą jeden zapętlony poziomy pasek: Lewo/Prawo przewija, Góra otwiera skróty, a Dół wraca do tej samej aplikacji. W podglądzie Alpine pasek można też przewijać kółkiem myszy lub touchpadem; Home nie przesuwa się za otwartym oknem dialogowym.

Nieopublikowany kandydat, obie edycje: w **Ustawienia Home → Wygląd** wyłącz **Pokaż kafelek „Dodaj aplikację”**, aby ukryć +. Opcja jest domyślnie włączona. Użyj **Dodaj aplikację** w tej samej sekcji, aby dodawać lub przywracać aplikacje przy ukrytym +. Nadal można zmieniać kolejność i ukrywać aplikacje; wybór zostaje po ponownym uruchomieniu. Po ukryciu wszystkich aplikacji górne przyciski i ustawienia pozostają dostępne.

W podglądach motywów nieopublikowanej wersji kandydującej z opcjonalnym panelem bocznym Góra/Dół wybiera pozycję menu, Prawo przechodzi do aplikacji, a Lewo z pierwszej kolumny aplikacji wraca do menu.

No-root 1.5.0: Helper może wznowić działanie po przejściowym przekroczeniu czasu watchdog przy wybudzaniu, maksymalnie pięć razy w ciągu dziesięciu minut. Stop i trzykrotne Home nadal wymagają jawnego uruchomienia Helper; powtarzające się błędy pozostawiają go zatrzymanym. Weryfikacja na TV jest w toku. [Działanie i ograniczenia (angielski)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Aktualizacja i usuwanie

Po połączeniu cytv pokazuje wersję zainstalowaną → dołączoną i rozróżnia pierwszą instalację, ponowną instalację i cofnięcie wersji. Sprawdź podsumowanie przed potwierdzeniem; `--yes` nie omija kontroli zgodności. Zachowaj działające pakiety i prywatne kopie ustawień. Przed wymianą pakietów z komputera zatrzymaj No-root Helper; nie odinstalowuj wcześniej aplikacji. Nie zastępuj działającego Root pojedynczym IPK: użyj odpowiedniej procedury cytv. Usunięcie aplikacji komputerowej nie usuwa aplikacji z TV.

Otwórz ustawienia Home → Aktualizacje oprogramowania i sprawdź wersje przed potwierdzeniem. Aktualizacje i cofanie wersji na TV wymagają **roota, Homebrew Channel** i przygotowanej zgodnej infrastruktury aktualizacji, również dla edycji No-root. Bez roota użyj komputera. Przygotowanie pełnych aktualizacji systemu to osobna świadoma czynność: [aktualizacje (angielski)](../UPDATES.md). Odzyskiwanie pokazuje zapisaną wersję; cofnięcie może utracić późniejsze zmiany ustawień.

**Istniejąca instalacja 1.3.0:** pierwotny System Updater może odmówić zmiany infrastruktury. Zachowaj przerwaną operację i postępuj według sprawdzonego odzyskiwania i przygotowania wymiany dla 1.5.0+; nie usuwaj dzienników ani nie ponawiaj w ciemno. Aktualizacja samej aplikacji nie zastępuje przypiętej infrastruktury Root. [Migracja i odzyskiwanie (angielski)](../UPDATES.md#one-time-computer-preparation).

Poprawka kanału ustawień Home została wydana w 1.5.0. Zaktualizuj Home i Helper razem zgodnym opublikowanym instalatorem; aktualizacja samego Home nie zmienia Helpera. Weryfikacja pozostaje ograniczona do opisanych modeli. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Odzyskiwanie dźwięku HDMI w Root jest eksperymentalne i **domyślnie wyłączone**; włączaj tylko w razie potrzeby. Może przerwać poprawny dźwięk i nie dowodzi zgodności eARC. [Odzyskiwanie dźwięku (angielski)](../development/ROOT-AUDIO-RECOVERY.md). Osobny **CYTV Installer dla Homebrew nie jest jeszcze wydany**; użyj opublikowanego instalatora komputerowego lub Android.

Homebrew Channel odmówił temu instalatorowi dostępu. W webOS 11 Homebrew 0.7.3 wymaga aktualizacji zgodności od swoich twórców. Dopóki obsługiwana wersja Homebrew nie zawiera poprawki, użyj opublikowanego instalatora na komputer lub Android. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: gdy stare zapisywalne katalogi Root blokują dostęp do API oprogramowania TV, `cytv enable-firmware-access --edition root --repair-package-permissions` sprawdza bieżący pakiet według zaufanych danych prywatnych i usuwa zapis dla grupy/innych wyłącznie we własnych ścieżkach Root. Nieznane lub zmienione pliki zatrzymują naprawę. Profil, wybór Home i blokowanie aktualizacji pozostają bez zmian; [szczegóły (angielski)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` obsługuje zweryfikowane przywracanie Root, gdy wszystkie instalatory pakietów zakończyły pracę, ale upłynął czas gotowości launchera. Wymaga prawdziwego sygnału launchera i odrzuca nieznane wyniki instalacji. Zachowuje pakiety, przypięty kod i klucze, dowody błędu oraz jawnie wyłączone sterowanie Home. Prywatny zapis dokumentuje ograniczoną próbę. Zwykłe ponowienie nie wydłuża terminu. Dopiero po 120 sekundach, bez zaakceptowanego sygnału gotowości i nieznanych wyników instalacji, `--new-recovery-attempt` archiwizuje cały poprzedni zapis pod UUID/haszem i jawnie rozpoczyna nową próbę. Ukończone odzyskiwanie pozostaje idempotentne; brak automatycznych kolejnych prób. [Procedura i ograniczenia (angielski)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0: pakiet wymiany zawiera System Updater 1.1.2. Przed OTA jawnie zastąp 1.1.0 lub 1.1.1 poleceniem `cytv replace-system-updater --edition root`. Wymieniany jest tylko System Updater; aplikacje Root/Root Updater, pełny profil i wybór Home pozostają, a stary stan jest archiwizowany. Nieznane lub niedokończone operacje blokują wymianę. Wymóg nie blokuje kanałów No-root. [Procedura (angielski)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Pomoc i dalsze instrukcje

Po błędzie lub przerwaniu sprawdź stan i zapisz raport diagnostyczny tej próby. Prowadzone odzyskiwanie prosi oddzielnie o zgodę na usunięcie i ponowną instalację. Przy niepewnym wyniku przerwij i zachowaj prywatne logi, dzienniki oraz pliki odzyskiwania; nigdy nie usuwaj ich, aby wymusić ponowienie. [Odzyskiwanie (angielski)](../RECOVERY.md). Prosząc o pomoc podaj model, firmware, edycję, wersję instalatora, nieudany krok oraz oczekiwane/rzeczywiste zachowanie; przed udostępnieniem przejrzyj raport i usuń sekrety.

[Dokumentacja](../README.md) · [Zgłoś problem](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="opcjonalny-python-dla-root"></a>
<a id="testy-sprzętowe-i-ograniczenia"></a>
<a id="blokada-oprogramowania-lg-w-120"></a>
<a id="nowości-w-130-odzyskiwanie-w-instalatorze-komputerowym"></a>
<a id="nowości-w-130--12"></a>
<a id="nieopublikowany-kandydat-instalacja-root-przez-homebrew"></a>
<a id="nieopublikowany-kandydat-odzyskiwanie-dźwięku-hdmi-root"></a>


## Motywy – kandydat rozwojowy

W kandydacie z obsługą motywów otwórz **Ustawienia → Wygląd**. **Classic** i **Alpine** są wbudowane i nie wymagają pobierania motywu; domyślny pozostaje Classic. **Channel** jest zewnętrznym motywem ze showcase. Podczas próby w galerii: Wybierz motyw i **Zachowaj motyw** w ciągu **20 sekund**. **Przywróć**, Back lub upływ czasu przywraca poprzedni. Przerwana próba uruchomi Home z Classic. Motywy wbudowane i pobrane wybrane z listy zainstalowanych są stosowane i zapisywane od razu, bez odliczania. Dotyczy to również motywów z komputera lub URL. Tylko Wypróbuj motyw w galerii rozpoczyna próbę 20 sekund.

Zainstalowane motywy są w jednym przewijanym poziomo rzędzie. Aktywny motyw jest zawsze pierwszy, a jego karta jest wyróżniona. Do przeglądania użyj strzałek w lewo/prawo.

Galeria pokazuje tylko motywy niezainstalowane na tym TV. Classic, Alpine i pobrane motywy są ukryte, także gdy istnieje nowsza wersja. Po usunięciu motyw pojawia się ponownie. Aktualizuj przez URL lub transfer z komputera.

Karty motywów są osadzone bezpośrednio w Wyglądzie obok kategorii. Galeria, instalacja z linku i przesyłanie z komputera otwierają się w tym panelu; tylko próba w galerii tymczasowo pokazuje Home.

Otwarcie galerii lub wybranie Odśwież sprawdza zatwierdzone aktualizacje katalogu w głównym repozytorium bez aktualizacji Home i przeładowania strony. Nowe wpisy pojawiają się po zwykłym scaleniu; niescalony kandydat może pokazywać katalog dołączony. Offline lub przy błędach używane są dołączone wpisy i podglądy. Wbudowane motywy odpowiadają zainstalowanej wersji Home. Otwórz podgląd Channel i wybierz **Pobierz motyw** (wymagany internet). Po pobraniu wypróbuj i wybierz **Zachowaj motyw** w ciągu **20 sekund**. Zainstalowane motywy działają offline. **Dodaj przez URL** nadal obsługuje przypięte linki.

Aby przetestować nieopublikowany motyw, najpierw otwórz na TV **Ustawienia → Wygląd → Odbierz z komputera**. Wpisz adres TV i sześciocyfrowy PIN w **Send to TV** w podglądzie na komputerze, wyślij i wybierz **Zastosuj motyw** na TV. Główna metoda łączy PC z TCP **8879 telewizora**, bez zmiany zapory komputera. Oba urządzenia muszą być w tej samej zaufanej sieci domowej. Odbiornik zamyka się po jednym wysłaniu, anulowaniu, wyjściu lub **10 minutach**. PIN nie jest zapisywany; motyw działa offline. Publikacja w GitHub nie jest wymagana.

Dla opublikowanego motywu otwórz **Więcej opcji → Dodaj przez URL** i wpisz ID (np. `102300a209`), `da.gd/102300a209` lub pełny link GitHub. Home pokaże adres da.gd przed wczytaniem, a następnie sprawdzi cel GitHub i pakiet motywu. Autor może skopiować ID z opisu wydania albo **TV link → Copy ID** w podglądzie na komputerze.

Opublikowane pakiety mogą jeszcze nie mieć tych opcji. Test przeglądarki nie potwierdza zgodności z fizycznym TV. [Pełny poradnik](../THEMES.md).

Ten nieopublikowany kandydat zawiera **Ribbon** obok Classic i Alpine, bez pobierania motywu. Classic pozostaje domyślny. Po aktualizacji Home wybierz Ribbon w Ustawienia → Wygląd.

Nieopublikowane motywy z konfigurowalną wstęgą mogą umieszczać wejścia, Wi-Fi i ustawienia w lewym dolnym rogu. Gdy opcja jest włączona, Lewo przy pierwszej widocznej aplikacji wybiera ustawienia, potem Wi-Fi i wejścia; Prawo w ustawieniach wraca do tej samej widocznej aplikacji. Instalacja motywu wymagającego nowej funkcji Home jest odrzucana w nieobsługiwanej wersji, zachowując wygląd i wybór. Najpierw zaktualizuj Home. Późniejsze obniżenie wersji może przywrócić Classic podczas startu.

Motywy pokazują podglądy wbudowanych i wszystkich samodzielnie zainstalowanych motywów, także offline. Osobny przycisk otwiera opublikowany katalog; prywatna instalacja nie publikuje motywu.

W kandydacie Wygląd pokazuje duże podglądy zainstalowanych motywów i oznacza wybrany. Galeria motywów i odbieranie z komputera to główne działania. Więcej opcji zawiera dodawanie przez URL, przywracanie Classic i usuwanie pobranych motywów. Strzałki przenoszą fokus między kartami i przyciskami; lewa strzałka na krawędzi wraca do kategorii.

W podglądzie przeglądarki Odbierz z komputera wyjaśnia kroki na telewizorze i nie uruchamia odbiornika TV na komputerze. Użyj Send to TV nad podglądem. Usunięcie pobranego motywu wymaga potwierdzenia; przy aktywnym motywie najpierw przywracany jest Classic. Anulowanie zachowuje motyw.

<a id="kategorie-ustawień-nieopublikowany-kandydat"></a>

## Kategorie ustawień (1.5.0)

W obu edycjach kategorie są po lewej, a ustawienia po prawej: ekran główny, Wygląd (motywy i kolumny), Język, Aktualizacje i Zaawansowane. No-root ma też Developer Mode; Root zawiera aktualizacje firmware LG w aktualizacjach i dźwięk HDMI w Zaawansowanych. Góra/dół porusza się w kolumnie, prawo otwiera ustawienia, a lewo wraca do kategorii. Wstecz najpierw wraca do kategorii, potem zamyka ustawienia. Tab pozwala też wybrać powrót do Home.

Żółta kropka przy kategorii aktualizacji i jej przycisku oznacza dostępne uaktualnienie. Obie znikają, gdy udane sprawdzenie potwierdzi brak aktualizacji; przy błędzie pozostaje ostatni potwierdzony stan.
