# Clean Your TV — instrukcja użytkownika

> **1.8.1 — Nieopublikowany kandydat:** [1.8.1 / English](../RELEASE-1.8.1.md).

**Nieopublikowana C1 Beta (#298):** Wybierz Root we wspólnym instalatorze na komputer. Kwalifikujące się telewizory C1 są wykrywane automatycznie; osobny instalator ani flaga nie są potrzebne. Ta ścieżka wymaga nowej instalacji, nie oferuje automatycznych aktualizacji i nie przeszła jeszcze odbioru na fizycznym C1. Otwórz LG Home, przytrzymanie Back lub zatrzymanie związane z bezpieczeństwem/zasilaniem mogą pozostawić sterowanie Home wyłączone; ponownie włącz Zmień Home w ustawieniach TV. Zwykła ścieżka Root pozostaje bez zmian. Jeśli pozostały inne składniki No-root, pełne usuwanie C1 zatrzyma się przed wprowadzeniem zmian. Najpierw usuń je zwykłą procedurą No-root; jeśli ich stan jest niejasny, zachowaj dane odzyskiwania. [C1 Beta contract (English)](../development/C1-NATIVE-GATE.md).

Jeszcze niewydane (#290): **+ / Dodaj aplikację** udostępnia telewizję na żywo pod nazwą z telewizora tylko wtedy, gdy tuner zostanie wykryty jako zainstalowany. Inne ukryte aplikacje systemowe pozostają pominięte. No-root wymaga zaktualizowanego Helpera i instalatora, a Root pakietu Home. Uruchamianie kanałów wymaga jeszcze sprawdzenia na TV.

**Niewydane — nakładka Ribbon:** Root obsługuje Ribbon nad bieżącą treścią. Kandydat zawiera połączenie Ribbon w tym samym Home i Helperze No-root; wyświetlanie nakładki wymaga działającego i uruchomionego Helpera. Home otwiera pasek; Wstecz lub ponowne Home go zamyka. Ustawienia i inne motywy są nieprzezroczyste, lecz odtwarzanie pod nimi może trwać. Nieznany kontekst oznacza statyczne, nieprzezroczyste tło. Pełny scenariusz No-root wymaga jeszcze testów końcowych pakietów na TV; symulacja w przeglądarce nie potwierdza zgodności. W No-root Wstecz zamyka też nieprzezroczysty Home z kart aplikacji po zamknięciu menu i edytora. Przy otwieraniu natywnego Root lub odświeżaniu jego kontekstu wideo tapety i podglądy wejść uruchamiają się dopiero po aktualnym potwierdzeniu braku treści pod Home; w przeciwnym razie nieprzezroczysty Home zachowuje statyczny obraz. [Ribbon](../THEMES.md#ribbon-over-applications-unreleased).

Ribbon: przytrzymaj OK, aby edytować; ←/→ przesuwa kartę, ↑ wybiera × (ukryj z Home), ↓ wraca do karty, OK zatwierdza, a Back anuluje. Bieżące tło pozostaje.

**1.7.0 — źródła startowe Root:** W Ustawienia → Twój ekran Home włącz **Zmień Home**, aby edytować **Otwórz Clean Your TV jako pierwsze**. **LG Channels / Telewizja na żywo** jest domyślnie włączone; **YouTube** jest wyłączone. Po wyłączeniu Zmień Home przełączniki pozostają widoczne, lecz niedostępne, a wartości są zachowane. Ustawienia są prywatnie zapisane na tym TV i nie obejmuje ich przenośny eksport profilu. Nie potwierdza to działania przy starcie ani wybudzeniu TV. Wyłączenie źródła pozostawia decyzję o uruchomieniu oprogramowaniu TV; nie gwarantuje wznowienia tego źródła. Nie ma przełącznika startowego HDMI. [Ograniczenia natywnego startu (angielski)](../../root-edition/README.md#candidate-native-startup-choices).

> Poradnik opisuje wersję 1.7.0. Dostępne pakiety pobieraj z [opublikowanych wydań GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). Zawiera pięć ulepszeń instalatora. Po ponownym otwarciu ustawienia Root odczytują rzeczywisty stan; nieudana kontrola nie włącza Home. System Updater 1.2.0 służy do dozwolonej nowej instalacji lub zweryfikowanej wymiany 1.1.0/1.1.1. Zainstalowany 1.1.2 zachowuje stare kanały; brak ogólnej migracji. Zachowaj dane odzyskiwania i nie wymuszaj wymiany. [Wersje i ograniczenia](../RELEASE-1.7.0.md).

> v1.5.0: motywy, galeria i przesyłanie z komputera na TV. Znane ograniczenia Root: Appearance może przesunąć się o 110 px; Home może nie otworzyć się automatycznie po czuwaniu. Zakres testów urządzeń jest ograniczony. [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** motywy o stałym układzie zachowują miejsce ukrytego wiersza Columns, aby Apply nie zmieniało pozycji przewijania Appearance. Wskaźnik, klawiatura i narzędzia dostępności pomijają Columns.

[Dokumentacja](../README.md) · [Zgłoś problem](../FEEDBACK.md)

**Historyczne wyniki 1.5.4:** Akceptacja C3 obejmuje zapisane testy zasilania, Home, fokusu, zachowania stanu wyłączenia i ręcznego cofnięcia wersji. Inne telewizory, dźwięk eARC i fizyczne urządzenia Android pozostają niezweryfikowane; udana instalacja nie dowodzi zgodności. [Zakres testów (angielski)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

**1.5.4:** konsola, aplikacja desktopowa i Android pokazują stan każdej kontroli TV: niesprawdzona, w toku, zaliczona, niezaliczona lub niemożliwa do potwierdzenia. Wyniki pozostają po błędzie. Node.js/Python jest sprawdzany w telewizorze; `doctor` nie przygotowuje Pythona ani nie prosi o parowanie sterowania. Zapisz raport przed ponowną próbą.

## Wybierz edycję

No-root i Root to równorzędne opcje dla różnych konfiguracji telewizora. Wybierz No-root dla LG Developer Mode lub Root, jeśli masz już dostęp root przez SSH. Zgodność i zakres wykonanych testów są określane osobno dla każdej wersji.

- **No-root:** włącz LG Developer Mode i Key Server. Wpisz hasło wyświetlane na telewizorze i zaakceptuj na nim osobne żądanie parowania. Developer Mode musi pozostać aktywny: wygaśnięcie sesji może usunąć tak zainstalowane aplikacje. Sprawdzaj oficjalny licznik także przy włączonym odnawianiu Beta. Monitorowanie Helper wymaga sieci lokalnej.
- **Root:** potrzebny jest istniejący dostęp root przez SSH. Instalator nie uzyskuje uprawnień root. Nie włączaj Developer Mode na telewizorze z istniejącym rootem. Zachowaj dostęp root i usługi odzyskiwania.

Root wymaga działających interfejsów Home usług Settings Service i System Profile (`com.webos.service.systemprofile`); sam dostęp root nie potwierdza zgodności.

> **1.6.0:** Root sprawdza wymagane interfejsy Home przed przygotowaniem prywatnego Pythona lub pakietów. Błąd zatrzymuje instalację; powodzenie nie potwierdza zgodności oprogramowania ani działania przycisku Home. Znane błędy połączenia mają osobne wskazówki. Zachowaj profile, dane zaufania i odzyskiwania; niedokończone operacje wymagają zweryfikowanego odzyskiwania, bez ponawiania w ciemno. Zapisz i sprawdź raport. [Szczegóły](../development/INSTALLER-PREFLIGHT-HELP.md).

## Wymagania

Włącz telewizor i połącz go z tą samą zaufaną siecią lokalną co komputer. Później komputer może być wyłączony. Zgodność zależy od modelu, oprogramowania i pilota; Root ma nieukończone testy sprzętowe.

1.5.4 zawiera Home Helper **0.6.21** dla TV Node.js **0.10.25+**; Root nadal wymaga Node.js **8+**. [Compatibility](../COMPATIBILITY.md).

**Nieopublikowana zmiana dla webOS 1.x:** następny instalator No-root akceptuje TV Node.js **0.10.15+** po testach Helpera na dokładnie tej wersji; opublikowany instalator 1.7.1 nadal wymaga **0.10.25+**. Nie potwierdza to zgodności starego WebKit, wejścia natywnego ani Home. Nie zastępuj środowiska TV i nie omijaj kontroli. Root nadal wymaga Node.js 8+. [Testy i ograniczenia](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased).

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

**Nieopublikowany kandydat Android:** dla pierwotnej operacji Root `install / coordinator-submitted` przegląd odzyskiwania może po wyraźnym potwierdzeniu wykonać kontrolę tylko do odczytu z pierwotnym profilem i kluczem hosta SSH. Nie odinstalowuj aplikacji, nie czyść danych, nie zastępuj profilu i nie ponawiaj instalacji. Używaj tylko podpisanego, ponownie zbudowanego APK wskazanego przez opiekuna; publiczny APK nie zawiera jeszcze tej ścieżki. [Procedura i ograniczenia](../../android/README.md#interrupted-root-installation-inspection-unreleased).

Kreator początkowo używa języka systemu i zapamiętuje wybrany język. Na telewizorze otwórz **Ustawienia → Język** i wybierz język lub automatyczny wybór według systemu. Preferencje instalatora i telewizora są niezależne. Kody zawiera [spis języków](../LANGUAGES.md).

Dla osobno pobranej CLI na macOS/Linux, w rozpakowanym katalogu:

```sh
chmod +x cytv
./cytv --language pl install
```

Wybierz telewizor lub podaj IP, wybierz edycję i sprawdź podsumowanie. Nową tożsamość SSH zatwierdzaj tylko dla własnego telewizora w zaufanej sieci; zmieniony zapisany klucz blokuje dostęp. Root przygotowuje odzyskiwanie i od razu aktywuje Home, bez okresu próbnego ani potwierdzenia zachowania ustawień. Sprawdź strzałki, OK, Home, Wstecz/Anuluj, głośność, czuwanie i uruchomienie po całkowitym odłączeniu zasilania.

**1.6.0:** weryfikacja pakietów, odczyt startu i Twoja obserwacja fizycznego Home są oddzielne. Potwierdzenie startu lub proces Helper nie dowodzą przechwytywania Home. Otwórz inną aplikację, krótko naciśnij Home raz i wybierz zaobserwowany wynik; domyślnie **Nie sprawdzono / pomiń**. `--yes` nie odpowiada za Ciebie, a tryb nieinteraktywny pozostawia test niewykonany. Błąd Home lub pominięcie nie usuwa pakietów i nie uruchamia ponownej instalacji. Zapisz lokalny raport, jeśli potrzebujesz pomocy; nie jest publikowany automatycznie. Inne przyciski, dźwięk, czuwanie i zimny start pozostają osobnymi testami.

## Obsługa i odzyskiwanie

Strzałki wybierają, OK otwiera; przytrzymaj OK, aby zmienić kolejność. Krótkie Wstecz zachowuje nawigację aplikacji i jej potwierdzenie wyjścia. Home otwiera ekran Clean Your TV, gdy sterowanie jest aktywne. Przytrzymaj Wstecz przez 1,2 sekundy, aby jednorazowo otworzyć LG Home. Przełącznik sterowania Home i ustawienia pozostają bez zmian.

**Naciśnij Home trzy razy w ciągu dwóch sekund**, puszczając przycisk po każdym naciśnięciu. Przywraca to LG Home i zatrzymuje sterowanie bez usuwania preferencji. W No-root Helper do wersji 0.6.13 włącznie zamiast tego przytrzymaj Home około dwóch sekund. Przytrzymanie Home nie jest gestem awaryjnym Root.

No-root: Aby wznowić sterowanie Home, otwórz Home Helper, wybierz Uruchom Helper i potwierdź. Zapisany wybór ekranu Home zostaje zachowany. Root: włącz **Zmień Home** w ustawieniach Home, aby wznowić. **Otwórz LG Home** otwiera LG Home jednorazowo bez zmiany celu przycisku Home. Aby przywrócić LG Home jako stały cel, wyłącz **Zmień Home** lub uruchom `cytv restore`. Nie uruchamiaj obu kontrolerów jednocześnie. Przy powtarzającym się błędzie pozostań przy LG Home.

Nieopublikowana poprawka Root: wyłączenie sterowania Home lub wybranie Open LG Home zamyka okno Root po potwierdzeniu uruchomienia LG Home. Aby otworzyć ustawienia przy wyłączonym sterowaniu Home, uruchom Home Root ręcznie.

> **1.5.4 — Root:** jawne włączenie **Zmień Home**, gdy Root działa prawidłowo, tworzy własne natywne wejście **Clean** CYTV i zapamiętuje Clean jako wejście. Wyłączenie sterowania Home, zatrzymanie awaryjne, błąd, wstrzymanie na czas aktualizacji lub odinstalowanie usuwa wpis CYTV. Poprzednie zapamiętane wejście jest przywracane tylko wtedy, gdy bieżąca wartość nadal jest wartością ustawioną przez CYTV; inne wejścia i aplikacje na pierwszym planie pozostają bez zmian. Na nieobsługiwanych TV lub przy cudzych wpisach pozostaje zwykłe sterowanie Home z zabezpieczeniami. Nie ma gwarancji, że Clean pojawi się natychmiast jako pierwszy ekran. Zapisane testy pierwszego ekranu, czuwania i startu po odłączeniu zasilania na C3 przeszły; nie gwarantuje to zgodności wszystkich TV. Po aktualizacji/cofnięciu Home może być wyłączone (#202), a ustawienia pokazywać stary stan (#206): zamknij/otwórz ustawienia, jawnie włącz Zmień Home i poczekaj na stan Clean. [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language pl status
./cytv --language pl doctor --report
./cytv --language pl restore
./cytv --language pl uninstall
```

> **1.6.0 (#152):** po odmowie wyłączenia Helper przywracanie/usuwanie No-root będzie mogło użyć sprawdzonego zatrzymania przez SSH. Stan zatrzymania zostaje zachowany; niepewny wynik zachowuje dziennik. Nie usuwaj plików stanu. Potwierdzenie na EF950V nadal jest potrzebne. [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** status No-root zachowuje dziennik przerwanej instalacji lub usuwania. Zgodne pliki lub brak aplikacji nie dowodzą zakończenia operacji. Jeśli weryfikacja jest odrzucona, zatrzymaj się i zachowaj diagnostykę; same pliki nie pozwalają obejść kontroli. [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

Po przerwaniu operacji najpierw uruchom `status` i zachowaj dzienniki. `restore` przywraca LG Home bez usuwania aplikacji; `uninstall` przywraca je przed usunięciem. Dane odzyskiwania Root pozostają celowo: nie kasuj ich, by wymusić ponowną instalację. Sprawdź raporty przed udostępnieniem; nie publikuj kluczy ani katalogów profili.

Otwórz **Ustawienia Home → Wygląd → Kolumny** i wybierz od 1 do 8 kolumn lub **Według motywu**, aby użyć wartości motywu (Classic: 5). Wybrana liczba ma pierwszeństwo przed motywem. Motywy ze stałym układem ukrywają opcję kolumn i używają wartości autora. Zapisany wybór wraca po przełączeniu na motyw obsługujący to ustawienie. W pobranym motywie Alpine aplikacje tworzą jeden zapętlony poziomy pasek: Lewo/Prawo przewija, Góra otwiera skróty, a Dół wraca do tej samej aplikacji. W Alpine pasek można też przewijać kółkiem myszy lub touchpadem; Home nie przesuwa się za otwartym oknem dialogowym.

1.5.4: w **Ustawienia Home → Wygląd** wyłącz **Pokaż kafelek „Dodaj aplikację”**, aby ukryć +. Opcja jest domyślnie włączona. Użyj **Dodaj aplikację** w tej samej sekcji, aby dodawać lub przywracać aplikacje przy ukrytym +. Nadal można zmieniać kolejność i ukrywać aplikacje; wybór zostaje po ponownym uruchomieniu. Po ukryciu wszystkich aplikacji górne przyciski i ustawienia pozostają dostępne.

1.7.0: wybrany motyw określa menu **Wejścia** w nagłówku albo półkę HDMI; nie ma globalnego ustawienia położenia ani przełącznika **Pokaż wejścia na Home**. Półka obsługuje obecnie tylko `dock-grid`. Liquid Glass ją wybiera; Classic i motywy bez tej opcji zachowują menu w nagłówku. Góra z doku przechodzi do półki, ponownie Góra do nagłówka, Dół lub Wstecz wraca do doku, a OK uruchamia źródło. Jeśli są kafelki źródeł, półka zastępuje menu Wejścia w nagłówku. Nazwa urządzenia pochodzi z metadanych wejść tylko wtedy, gdy firmware ją udostępnia; w przeciwnym razie podłączone źródło pokazuje **Podłączono**. Home nie wymyśla nazwy PlayStation i nie gwarantuje identyfikacji CEC. Puste porty pozostają dostępne. Podglądy są **domyślnie włączone**; jawnie zapisana opcja Wyłączone pozostaje wyłączona. Wyłącz **Ustawienia Home → Wygląd → Podgląd wybranego wejścia**, aby je zatrzymać. Gdy są włączone i motyw ma półkę, podłączone HDMI może wyświetlić podgląd po około 0,8 sekundy zaznaczenia. Na niektórych TV podglądy HDMI mogą odtwarzać dźwięk lub włączać HDR; cisza nie jest gwarantowana. Home nie zmienia automatycznie globalnego wyciszenia ani ustawień HDR telewizora. Live TV i puste porty zachowują statyczne kafelki. Root odczytuje stan wejść przez własną usługę. No-root zachowuje bezpośredni EIM, gdy jest dozwolony; odmowa uprawnień uruchamia odczyt przez już sparowany Helper. Błąd pozostawia stan nieznany; nie dodano nowego ustawienia ani prośby o parowanie.

W podglądach motywów wersji 1.5.4 z opcjonalnym panelem bocznym Góra/Dół wybiera pozycję menu, Prawo przechodzi do aplikacji, a Lewo z pierwszej kolumny aplikacji wraca do menu.

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

1.6.0: System Updater 1.2.0 służy do dozwolonej nowej instalacji lub zweryfikowanej wymiany 1.1.0/1.1.1 poleceniem `cytv replace-system-updater --edition root`. Wymieniany jest tylko System Updater; aplikacje Root/Root Updater, pełny profil i wybór Home zostają zachowane, a poprzedni stan jest archiwizowany. Nieznane lub niedokończone operacje blokują wymianę. Zainstalowany 1.1.2 pozostaje przypięty do starych kanałów; nie ma ogólnej migracji. Nie wymuszaj wymiany. Nie ogranicza to kanałów No-root. [Procedura (angielski)](../RECOVERY.md#replace-the-root-system-updater-candidate)

## Pomoc i dalsze instrukcje

**1.6.0:** wybierz **Sprawdź opcje odzyskiwania** dla tego samego zapisanego TV lub uruchom `cytv recover`. Kontrola i zmiany wymagają osobnych potwierdzeń z domyślnym Nie; `--yes` ich nie zatwierdza. Root kontynuuje tylko po istniejących weryfikacjach. No-root proponuje usuwanie wyłącznie za zgodą dotychczasowej kontroli usługi pakietów; ustawienia Home mogą zostać zresetowane. Nowa instalacja nie zaczyna się automatycznie. Przy nieznanym stanie lub odmowie dostępu zapisz raport i zatrzymaj się. Zachowaj dzienniki i nie powtarzaj usuwania. Nadal brakuje dowodów zakończenia dla #201 i potwierdzenia odzyskania TV dla #216. [Recovery](../RECOVERY.md). Prosząc o pomoc podaj model, firmware, edycję, wersję instalatora, nieudany krok oraz oczekiwane/rzeczywiste zachowanie; przed udostępnieniem przejrzyj raport i usuń sekrety.

1.7.0: odzyskiwanie może wznowić usuwanie No-root zatrzymane przed pierwszym żądaniem pakietu bez dostępu do globalnego stanu, jeśli potwierdza to oryginalny dziennik. Potwierdź usuwanie osobno; po jego weryfikacji rozpocznij instalację oddzielnie. Nieznane lub już wysłane operacje nadal blokują kontynuację. Zachowaj połączenie i dzienniki. Brak w 1.6.0. [Szczegóły](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased).

[Dokumentacja](../README.md) · [Zgłoś problem](../FEEDBACK.md)

W przygotowaniu: jeśli nie wysłano żądania usunięcia pakietów, po błędzie dostępne jest **Przejrzyj opcje odzyskiwania** dla tego samego zapisanego TV. Kontrola i usuwanie wymagają osobnych potwierdzeń. Odmowa sprawdzenia stanu pakietów zatrzymuje odzyskiwanie i udostępnia raport. Podsumowanie `recovery` rozróżnia nierozpoczęte usuwanie, odziedziczoną operację i przerwane operacje na pakietach bez publikowania całego dziennika; nie upoważnia do odzyskiwania.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="opcjonalny-python-dla-root"></a>
<a id="testy-sprzętowe-i-ograniczenia"></a>
<a id="blokada-oprogramowania-lg-w-120"></a>
<a id="nowości-w-130-odzyskiwanie-w-instalatorze-komputerowym"></a>
<a id="nowości-w-130--12"></a>
<a id="nieopublikowany-kandydat-instalacja-root-przez-homebrew"></a>
<a id="nieopublikowany-kandydat-odzyskiwanie-dźwięku-hdmi-root"></a>

<a id="motywy--kandydat-rozwojowy"></a>

## Motywy

W podglądzie następnej wersji **Ustawienia Home → Tapety** pokazuje tapetę aktywnego motywu, wykryte możliwości TV i bieżący tryb. Auto wybiera zgodną jakość; 4K, 1080p i Obraz są dostępne tylko wtedy, gdy zawiera je motyw. Przy błędzie wideo wyświetlany jest obraz. Przyciemnienie zmienia się co 5%; reset przywraca ustawienia motywu. Classic i motywy bez tapety wyraźnie pokazują ten stan.

Własne tapety w podglądzie kolejnej wersji: otwórz Tapety w komputerowym CYTV, wybierz JPG/PNG, ustaw kadr i podaj prywatny adres TV oraz PIN odbioru z Home. CYTV lokalnie przygotowuje film bez dźwięku; 4K jest dostępne tylko przy odpowiedniej rozdzielczości kadru. Na TV wybierz odbiór z CYTV lub przesyłanie z telefonu i zeskanuj QR w tej samej sieci Wi-Fi. Telefon przesyła zwykły obraz do 1920×1080 bez natywnej warstwy wideo 4K; ostrość ogranicza rozdzielczość interfejsu TV. Potwierdź ostrzeżenie przed wysłaniem, potem sprawdź podgląd i zastosuj na TV. Własne obrazy pozostają zapisane i można je ponownie wybrać lub usunąć w Tapetach. Anulowanie lub odrzucenie pliku zachowuje poprzednie tło. Wymagane są zgodne kompilacje kolejnej wersji Home/usługi oraz CYTV.

Własne ruchome wideo (podgląd następnej wersji): w komputerowym CYTV → Tapety wybierz MP4/MOV/MKV/WebM, 1–60 sekund, do 512 MiB i 3840×2160. Dźwięk jest usuwany, a kadr przycinany centralnie do 16:9. Mniejsze wideo korzysta ze zgodnego wyjścia 1080p; UHD wymaga odpowiednio dużego kadru źródłowego. Wyślij przez adres/PIN TV, a następnie obejrzyj i zastosuj na TV. Z telefonu nadal tylko JPG/PNG. Weryfikacja końcowego pakietu i testy na fizycznym TV pozostają do wykonania.

Wbudowane tapety następnej wersji: **Ustawienia Home → Tapety → Wbudowane tapety → Black Hole**. Autor filmu: **Xecutioner**, ze zgodą na użytek niekomercyjny z podaniem autora. Zatwierdzenie innego motywu włącza jego własną tapetę; Black Hole i własne obrazy nadal można wybrać. Ciągły strumień 4K eliminuje przewijanie przy każdym powtórzeniu, z kompatybilnym filmem/obrazem w razie problemów.

Android CYTV: **Skonfiguruj TV** · **Tapety** · **Konserwacja**. Na TV otwórz ustawienia Home → Tapety → Prześlij z telefonu. Zeskanuj QR aparatem, wybierz JPG/PNG i zastosuj tapetę na TV. Z telefonu: obrazy do 1920×1080, bez natywnego wideo 4K. Aby uzyskać prawdziwe 4K, użyj CYTV na komputerze.

1.7.0: **Ustawienia → Motywy**. **Classic**, **Liquid Glass**, **Ribbon** są wbudowane i nie wymagają pobierania motywu; domyślny pozostaje Classic. **Channel** jest zewnętrznym motywem ze showcase. Podczas próby w galerii: Wybierz motyw i **Zachowaj motyw** w ciągu **20 sekund**. **Przywróć**, Back lub upływ czasu przywraca poprzedni. Przerwana próba uruchomi Home z Classic. Motywy wbudowane i pobrane wybrane z listy zainstalowanych są stosowane i zapisywane od razu, bez odliczania. Dotyczy to również motywów z komputera lub URL. Tylko Wypróbuj motyw w galerii rozpoczyna próbę 20 sekund.

1.7.0: **Classic**, **Liquid Glass** i **Ribbon** są wbudowane. **Alpine 1.4.4** przechodzi do pobierania w **galerii motywów**. Zapisany wybór `builtin:alpine` wraca do Classic z istniejącym widocznym komunikatem odzyskiwania; Home nie pobiera Alpine automatycznie ani nie zastępuje go Liquid Glass. Wersja 1.6.0 zawiera Classic, Alpine i Ribbon.

Zainstalowane motywy są w jednym przewijanym poziomo rzędzie. Aktywny motyw jest zawsze pierwszy, a jego karta jest wyróżniona. Do przeglądania użyj strzałek w lewo/prawo.

Galeria pokazuje tylko motywy niezainstalowane na tym TV. Classic, Liquid Glass, Ribbon i pobrane motywy są ukryte, także gdy istnieje nowsza wersja. Po usunięciu motyw pojawia się ponownie. Aktualizuj przez URL lub transfer z komputera.

Karty motywów są osadzone bezpośrednio w Motywyzie obok kategorii. Galeria, instalacja z linku i przesyłanie z komputera otwierają się w tym panelu; tylko próba w galerii tymczasowo pokazuje Home.

Otwarcie galerii lub wybranie Odśwież sprawdza zatwierdzone aktualizacje katalogu w głównym repozytorium bez aktualizacji Home i przeładowania strony. Nowe wpisy pojawiają się po zwykłym scaleniu; niescalony kandydat może pokazywać katalog dołączony. Offline lub przy błędach używane są dołączone wpisy i podglądy. Wbudowane motywy odpowiadają zainstalowanej wersji Home. Otwórz podgląd Channel i wybierz **Pobierz motyw** (wymagany internet). Po pobraniu wypróbuj i wybierz **Zachowaj motyw** w ciągu **20 sekund**. Zainstalowane motywy działają offline. **Dodaj przez ID** nadal obsługuje przypięte linki.

Aby przetestować nieopublikowany motyw, najpierw otwórz na TV **Ustawienia → Motywy → Odbierz z komputera**. Wpisz adres TV i sześciocyfrowy PIN w **Send to TV** w podglądzie na komputerze, wyślij i wybierz **Zastosuj motyw** na TV. Główna metoda łączy PC z TCP **8879 telewizora**, bez zmiany zapory komputera. Oba urządzenia muszą być w tej samej zaufanej sieci domowej. Odbiornik zamyka się po jednym wysłaniu, anulowaniu, wyjściu lub **10 minutach**. PIN nie jest zapisywany; motyw działa offline. Publikacja w GitHub nie jest wymagana.

Dla opublikowanego motywu otwórz **Dodaj przez ID** i wpisz ID (np. `102300a209`), `da.gd/102300a209` lub pełny link GitHub. Home pokaże adres da.gd przed wczytaniem, a następnie sprawdzi cel GitHub i pakiet motywu. Autor może skopiować ID z opisu wydania albo **TV link → Copy ID** w podglądzie na komputerze.

**1.6.0:** **Pokaż diagnostykę** w panelu Home Helper pokazuje niewielki, przefiltrowany wynik jego własnych zapytań o stan. Wyświetlenie nie uruchamia Helpera ani nie zmienia sterowania Home. Na prośbę udostępnij tylko sprawdzony JSON; [szczegóły](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

Motywy z konfigurowalną wstęgą w 1.5.4 mogą umieszczać wejścia, Wi-Fi i ustawienia w lewym dolnym rogu. Gdy opcja jest włączona, Lewo przy pierwszej widocznej aplikacji wybiera ustawienia, potem Wi-Fi i wejścia; Prawo w ustawieniach wraca do tej samej widocznej aplikacji. Instalacja motywu wymagającego nowej funkcji Home jest odrzucana w nieobsługiwanej wersji, zachowując wygląd i wybór. Najpierw zaktualizuj Home. Późniejsze obniżenie wersji może przywrócić Classic podczas startu.

Motywy pokazują podglądy wbudowanych i wszystkich samodzielnie zainstalowanych motywów, także offline. Osobny przycisk otwiera opublikowany katalog; prywatna instalacja nie publikuje motywu.

Wygląd zawiera Kolumny z bieżącą liczbą i ustawienia aplikacji. Osobna kategoria Motywy zawiera zainstalowane motywy, galerię, odbiór z komputera i Dodaj przez ID po prawej (np. 102300a209). Przywróć Classic jego kartą i usuwaj pobrane motywy pojedynczo. W kategorii Język wybierasz język bezpośrednio.

W podglądzie przeglądarki Odbierz z komputera wyjaśnia kroki na telewizorze i nie uruchamia odbiornika TV na komputerze. Użyj Send to TV nad podglądem. Usunięcie pobranego motywu wymaga potwierdzenia; przy aktywnym motywie najpierw przywracany jest Classic. Anulowanie zachowuje motyw.

<a id="kategorie-ustawień-nieopublikowany-kandydat"></a>

## Kategorie ustawień (1.5.4)

W obu edycjach kategorie są po lewej, a ustawienia po prawej: ekran główny, Wygląd, Motywy, Język, Aktualizacje i Zaawansowane. No-root ma też Developer Mode; Root zawiera aktualizacje firmware LG w aktualizacjach i dźwięk HDMI w Zaawansowanych. Góra/dół porusza się w kolumnie, prawo otwiera ustawienia, a lewo wraca do kategorii. Wstecz najpierw wraca do kategorii, potem zamyka ustawienia. Tab pozwala też wybrać powrót do Home.

Żółta kropka przy kategorii aktualizacji i jej przycisku oznacza dostępne uaktualnienie. Obie znikają, gdy udane sprawdzenie potwierdzi brak aktualizacji; przy błędzie pozostaje ostatni potwierdzony stan.

<a id="automatyczna-rozdzielczość-grafiki-kandydat"></a>

## Automatyczna rozdzielczość grafiki (1.6.0)

Instalatory komputerowe/Android 1.6.0 i zmigrowane klienty OTA wybierają 720p lub 1080p na podstawie możliwości TV. Jeśli nie można ich potwierdzić, operacja zostaje zatrzymana. Starsze osobno instalowane aktualizatory wymagają opisanej migracji z komputera; odzyskiwanie zachowuje oryginalne pakiety.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** zachowaj raport z pierwotnej nieudanej próby. Nowe raporty oddzielają pierwszy zapisany błąd od kolejnych kontroli i zawierają filtrowane podsumowanie Doctor/stanu. Eksport jest dostępny także po udanej instalacji, kontroli stanu lub przywróceniu. Brakujące starsze dane pozostają nieznane; raport nie uprawnia do odzyskiwania. [↗](../development/INSTALLER-DIAGNOSTICS.md).
