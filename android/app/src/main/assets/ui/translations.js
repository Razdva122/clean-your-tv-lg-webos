'use strict';
// Bundled offline UI catalogs; language IDs match cytv.i18n.LANGUAGES.
const languages = {
  'cs': 'Čeština',
  'en': 'English',
  'de': 'Deutsch',
  'es': 'Español',
  'pt-BR': 'Português (Brasil)',
  'fr': 'Français',
  'it': 'Italiano',
  'ko': '한국어',
  'hi': 'हिन्दी',
  'pl': 'Polski',
  'ru': 'Русский',
  'zh-Hans': '简体中文',
  'zh-Hant': '繁體中文'
};
const words = {
  'cs': {
    'tryAgain': 'Zkusit znovu',
    'removalPending': 'Odebrání ještě není dokončeno.',
    'restartRemoval': 'Restartujte TV pro dokončení odebrání',
    'fullRestart':
      'Úplně restartujte TV: odpojte napájení, znovu je připojte a zvolte Zkusit znovu. Pohotovostní režim není úplný restart.',
    'connectionInterrupted':
      'Spojení s TV bylo přerušeno. Zkontrolujte připojení a zkuste to znovu.',
    'removalUnconfirmed':
      'Odebrání se nepodařilo potvrdit. Zkontrolujte připojení a zkuste to znovu.',

    'uninstall': 'Odinstalovat Clean Your TV',
    'uninstallDesc':
      'Odebere aplikace a jejich data nastavení. Vyžaduje samostatné potvrzení.',

    'setupTV': 'Nastavit televizor',
    'wallpapers': 'Tapety',
    'maintenance': 'Údržba',
    'wallpaperInstructions':
      'Na televizoru otevřete nastavení Home → Tapety → Nahrát z telefonu. Fotoaparátem telefonu naskenujte QR kód, vyberte soubor JPG/PNG a použijte tapetu na televizoru.',
    'wallpaperLimit':
      'Nahrávání z telefonu: obrázky do 1920×1080, bez nativního videa ve 4K. Pro skutečné 4K použijte CYTV na počítači.',
    'detect': 'Ověřit připojení',
    'detecting': 'Ověřování přístupu…',
    'detectedRoot':
      'Zjištěno Root SSH. Oprávnění root budou ověřena po přihlášení.',
    'detectedDev': 'Zjištěn Developer Mode. Tomuto připojení odpovídá No-root.',
    'detectedBoth':
      'Obě připojení jsou dostupná. Vyberte prostředí, které používáte.',
    'detectedNone':
      'Přístup nebyl zjištěn. Zkontrolujte televizor, síť a režim přístupu nebo vyberte edici ručně.',
    'connectionMatch': 'Podle připojení',
    'editionNext': 'Pokračovat',
    'android': 'pro Android',
    'hero': 'Nový Home.<br>Z vašeho telefonu.',
    'subtitle':
      'Nastavte Clean Your TV na LG webOS.<br>Bez počítače. Vše máte po ruce.',
    'choose': 'Vyberte edici',
    'noRootDesc': 'Používá LG Developer Mode',
    'rootDesc': 'Již nastavený přístup root a SSH',
    'connect': 'Připojit televizor',
    'networkFoot': 'Telefon a televizor ve stejné síti',
    'tools': 'Stav a obnovení',
    'back': 'Zpět',
    'step': 'Připojení',
    'connectTitle': 'Připojme se<br>k televizoru',
    'connectDesc':
      'Zapněte televizor a zadejte jeho IP adresu.<br>Najdete ji v nastavení sítě televizoru.',
    'ip': 'IP adresa televizoru',
    'port': 'Port',
    'ipHelp': 'Nastavení TV → Síť → Aktuální připojení',
    'ipError': 'Zadejte platnou IPv4 adresu, například 192.168.1.50.',
    'portError': 'Port musí být v rozsahu 1 až 65535.',
    'prepare': 'Připravte televizor',
    'dev': 'Zapněte Developer Mode',
    'devDesc':
      'Zapněte Dev Mode Status. Televizor se restartuje. Poté znovu otevřete Developer Mode.',
    'keyServer': 'Zapněte Key Server',
    'keyServerDesc':
      'Zapněte Key Server a nechte Developer Mode otevřený. V poli IP Address je adresa televizoru, kterou zadáte do CYTV.',
    'wifiTip':
      'Telefon a televizor musí být ve stejné místní síti. Během nastavení odpojte VPN.',
    'install': 'Zkontrolovat a nainstalovat',
    'reviewFoot': 'Před instalací zkontrolujte verze balíčků',
    'password': 'Heslo',
    'sshKey': 'Klíč SSH',
    'importKey': 'Vybrat soubor klíče',
    'keyImported': 'Klíč SSH byl přidán',
    'keyPrivate': 'Klíč zůstane pouze v tomto telefonu',
    'rootNotice':
      'Vyžaduje již nastavený přístup root. CYTV nezískává root ani nemění firmware televizoru.',
    'rootHint': 'Při připojení vás požádáme o heslo SSH.',
    'keyError': 'Nejprve vyberte soubor soukromého klíče SSH.',
    'keyFailed': 'Klíč se nepodařilo načíst. Vyberte soubor do 64 KB.',
    'browserKey': 'Import klíče je dostupný v aplikaci pro Android.',
    'progressTitle': 'Nastavujeme<br>váš nový Home',
    'progressDesc':
      'Nechte televizor zapnutý. CYTV ověří připojení a provede vás instalací.',
    'statusTitle': 'Kontrolujeme<br>televizor',
    'restoreTitle': 'Obnovujeme<br>LG Home',
    'progressFoot': 'Aplikaci můžete opustit: průběh se zobrazuje v oznámení',
    'steps': [
      'Připojení a kontroly',
      'Aplikace televizoru',
      'Instalace balíčků',
      'Nastavení Home'
    ],
    'log': 'Protokol operace',
    'awaiting': 'Čekání na televizor…',
    'success': 'Váš nový Home<br>je připraven ke spuštění',
    'successDesc':
      'Na televizoru vyzkoušejte Home, šipky a OK. Poté ověřte ukončování aplikací a přechod do pohotovostního režimu i probuzení.',
    'statusDone': 'Kontrola dokončena',
    'statusDoneDesc': 'Výsledky kontroly najdete v protokolu operace.',
    'restored': 'LG Home byl obnoven',
    'restoredDesc': 'Vyzkoušejte tlačítko Home na televizoru.',
    'cancelled': 'Operace byla zrušena',
    'cancelledDesc':
      'Pokud již začal přenos balíčků, před další instalací zkontrolujte stav televizoru.',
    'failed': 'Operaci se nepodařilo<br>dokončit',
    'failedDesc':
      'Operace nebyla dokončena. Projděte protokol a před dalším pokusem zkontrolujte stav televizoru.',
    'recoveryTitle': 'Návrat k LG Home',
    'recoveryDesc':
      'Stiskněte Home třikrát během dvou sekund. U starších verzí Helper do 0.6.13 podržte Home dvě sekundy.',
    'three': '3 stisknutí',
    'checkStatus': 'Zkontrolovat stav',
    'restore': 'Obnovit LG Home',
    'toConnection': 'Zpět k připojení',
    'done': 'Zpět na začátek',
    'trustTitle': 'Je to váš televizor?',
    'trustDesc':
      'Pokud máte důvěryhodné připojení, porovnejte s ním tento otisk SSH. CYTV si televizor zapamatuje a při změně jeho klíče se zastaví.',
    'trust': 'Důvěřovat a pokračovat',
    'cancel': 'Zrušit',
    'continue': 'Pokračovat',
    'secretTitle': 'Kód Developer Mode (Passphrase)',
    'secretDesc':
      'Zadejte Passphrase: šest znaků zobrazených v Developer Mode na televizoru. Rozlišujte velká a malá písmena. Použijte kód z televizoru, nikoli heslo k účtu LG. Pokud kód nevidíte, zapněte Key Server.',
    'rootSecretTitle': 'Heslo SSH',
    'rootSecretDesc':
      'Zadejte stávající heslo SSH pro přístup root k televizoru.',
    'keySecretTitle': 'Heslová fráze klíče SSH',
    'keySecretDesc': 'Zadejte heslovou frázi, která chrání váš soukromý klíč.',
    'secretLabel': 'Kód / heslo',
    'reviewTitle': 'Potvrďte tuto akci',
    'reviewDesc':
      'Projděte údaje z instalačního programu. Až budete připraveni, pokračujte.',
    'details': 'Podrobnosti',
    'toolsTitle': 'Váš televizor<br>pod kontrolou',
    'toolsDesc': 'Zkontrolujte instalaci nebo obnovte původní LG Home.',
    'statusTool': 'Stav instalace',
    'statusToolDesc': 'Zkontrolovat balíčky a nedokončené operace',
    'restoreToolDesc': 'Obnovit původní domovskou obrazovku televizoru',
    'toolsConnect': 'Zadejte adresu televizoru pro tuto operaci.',
    'check': 'Zkontrolovat stav',
    'preview': 'Ukázka rozhraní · bez připojení k televizoru',
    'previewOnly':
      'Toto je náhled rozhraní. Pro připojení k televizoru nainstalujte APK.',
    'prepareService': 'Příprava instalačního programu…',
    'confirmRestore': 'Obnovit LG Home?',
    'confirmRestoreDesc':
      'CYTV se připojí k televizoru a požádá vás o potvrzení obnovení. Ostatní aplikace zůstanou zachovány.',
    'languageTitle': 'Jazyk',
    'languageClose': 'Zavřít',
    'tvGreeting': 'Buďte tu jako doma.',
    'tvSubtitle': 'Vaše oblíbené aplikace. Více volného místa.',
    'seconds': 's',
    'errorPrefix': 'Chyba',
    'replayError':
      'Zobrazení operace se nepodařilo obnovit. Zkontrolujte stav televizoru.',
    'notificationText': 'Probíhá operace na televizoru',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Aktualizujte Android System WebView nebo Chrome a znovu otevřete CYTV (vyžaduje WebView 108 nebo novější).',
    'connectionMethod': 'Vyberte způsob připojení',
    'maintenanceProgress':
      'Nechte televizor zapnutý. CYTV provádí vybranou akci.',
    'homeDiagnostics': 'Diagnostika tlačítka Home',
    'homeDiagnosticsDesc':
      'Zaznamenejte jeden stisk Home a uložte zprávu. Pouze pro No-root Helper.',
    'diagnosticProgress':
      'Po výzvě jednou stiskněte Home. Nechte tuto aplikaci jednu minutu otevřenou.',
    'saveReport': 'Uložit zprávu',
    'reportDone': 'Zpráva je připravena',
    'reportDoneDesc':
      'Uložte zprávu ve formátu JSON a přiložte ji k hlášení problému.',
    'reportSaved': 'Zpráva byla uložena.',
    'reportError': 'Zprávu se nepodařilo uložit. Zkuste to znovu.',
    'devInstall':
      'Na televizoru otevřete LG Apps, vyhledejte Developer Mode a nainstalujte jej.',
    'devAccount':
      'Otevřete Developer Mode a přihlaste se účtem LG Developer. V případě potřeby si účet vytvořte na webostv.developer.lge.com.',
    'sessionHelp':
      'Udržujte Developer Mode aktivní: před vypršením časovače jej otevřete a stiskněte EXTEND, když je televizor online. Po vypršení může LG tyto aplikace odebrat.',
    'editionHelp':
      'No-root používá aplikaci Developer Mode od LG. Root vyžaduje již nastavený přístup správce k televizoru.',
    'pairingHelp':
      'Párování je samostatný krok: až vás televizor požádá, potvrďte CYTV dálkovým ovladačem.',
    'homeHelperHelp':
      'Home je obrazovka s vašimi aplikacemi. Home Helper zajistí, aby ji otevíralo tlačítko Home.',
    'tryHomeHelp':
      'Po instalaci stiskněte Home a vyzkoušejte jej. Pokud se otevře LG Home, spusťte Home Helper ze seznamu aplikací televizoru.',
    'resumeHomeHelp':
      'Tři krátká stisknutí Home během dvou sekund vás vrátí do LG Home. Ovládání tlačítka Home znovu zapnete tak, že otevřete Home Helper, vyberete Start Helper a potvrdíte. Uložená volba domovské obrazovky zůstane zachována.',
    'guideExample': 'Příklad od LG',
    'guideNote':
      'Příklad od LG. Na vašem televizoru může obrazovka vypadat jinak. Použijte kód zobrazený na vlastním televizoru.',
    'connectRoot': 'Připojit přes Root',
    'recoveryReview': 'Prohlédnout možnosti obnovení',
    'recoveryReviewDesc':
      'Než se rozhodnete, co dál, zkontrolujte přerušené nastavení. Změny vyžadují samostatné potvrzení.',
    'tvChecksReview': 'Prohlédnout kontroly televizoru',
    'homeObserved': 'Funkci tlačítka Home jste potvrdili',
    'tvChecksDesc':
      'Ověření balíčků, zpětná kontrola spuštění a vaše pozorování tlačítka Home jsou samostatné výsledky.'
  },
  'ru': {
    'tryAgain': 'Попробовать снова',
    'removalPending': 'Удаление ещё не завершено.',
    'restartRemoval': 'Перезапустите ТВ для завершения удаления',
    'fullRestart':
      'Полностью перезапустите ТВ: отключите питание, подключите снова и выберите «Попробовать снова». Режим ожидания не является полным перезапуском.',
    'connectionInterrupted':
      'Соединение с ТВ прервано. Проверьте подключение и попробуйте снова.',
    'removalUnconfirmed':
      'Не удалось подтвердить удаление. Проверьте подключение и попробуйте снова.',

    'uninstall': 'Удалить Clean Your TV',
    'uninstallDesc':
      'Удаление приложений и их данных настройки. Нужно отдельное подтверждение.',

    'setupTV': 'Настроить телевизор',
    'wallpapers': 'Обои',
    'maintenance': 'Обслуживание',
    'wallpaperInstructions':
      'На телевизоре откройте настройки Home → Обои → Загрузить с телефона. Отсканируйте QR-код камерой телефона, выберите JPG/PNG и примените обои на ТВ.',
    'wallpaperLimit':
      'С телефона: изображение до 1920×1080, без нативного видео 4K. Для настоящего 4K используйте CYTV на компьютере.',
    'detect': 'Проверить подключение',
    'detecting': 'Проверяем доступ…',
    'detectedRoot': 'Обнаружен Root SSH. Права root проверим после входа.',
    'detectedDev':
      'Обнаружен Developer Mode. Для этого подключения подходит No-root.',
    'detectedBoth':
      'Доступны оба подключения. Выберите окружение, которое используете.',
    'detectedNone':
      'Доступ не определён. Проверьте ТВ, сеть и нужный режим или выберите редакцию вручную.',
    'connectionMatch': 'По подключению',
    'editionNext': 'Продолжить',
    'android': 'для Android',
    'hero': 'Новый Home.<br>С вашего телефона.',
    'subtitle':
      'Настройте Clean Your TV на LG webOS.<br>Без компьютера. Всё под рукой.',
    'choose': 'Выберите редакцию',
    'noRootDesc': 'Через Developer Mode от LG',
    'rootDesc': 'Уже есть root и доступ по SSH',
    'connect': 'Подключить телевизор',
    'networkFoot': 'Телефон и ТВ в одной сети',
    'tools': 'Состояние и восстановление',
    'back': 'Назад',
    'step': 'Подключение',
    'connectTitle': 'Подключимся<br>к телевизору',
    'connectDesc':
      'Включите ТВ и введите его IP-адрес.<br>Адрес есть в настройках сети телевизора.',
    'ip': 'IP-адрес телевизора',
    'port': 'Порт',
    'ipHelp': 'Настройки ТВ → Сеть → Текущее подключение',
    'ipError': 'Введите корректный IPv4-адрес, например 192.168.1.50.',
    'portError': 'Порт должен быть от 1 до 65535.',
    'prepare': 'Подготовьте телевизор',
    'dev': 'Включите Developer Mode',
    'devDesc':
      'Включите Dev Mode Status. Телевизор перезагрузится. После этого снова откройте Developer Mode.',
    'keyServer': 'Включите Key Server',
    'keyServerDesc':
      'Включите Key Server и оставьте Developer Mode открытым. В поле IP Address указан адрес телевизора для ввода в CYTV.',
    'wifiTip':
      'Телефон и телевизор должны быть в одной локальной сети. На время настройки отключите VPN.',
    'install': 'Проверить и установить',
    'reviewFoot': 'Перед установкой покажем версии пакетов',
    'password': 'Пароль',
    'sshKey': 'SSH-ключ',
    'importKey': 'Выбрать файл ключа',
    'keyImported': 'SSH-ключ добавлен',
    'keyPrivate': 'Ключ останется только на этом телефоне',
    'rootNotice':
      'Требуется уже настроенный root-доступ. CYTV не получает root и не меняет прошивку телевизора.',
    'rootHint': 'Пароль SSH запросим при подключении.',
    'keyError': 'Сначала выберите файл приватного SSH-ключа.',
    'keyFailed': 'Не удалось прочитать ключ. Выберите файл размером до 64 КБ.',
    'browserKey': 'Импорт ключа доступен в Android-приложении.',
    'progressTitle': 'Настраиваем<br>ваш новый Home',
    'progressDesc':
      'Не выключайте ТВ. CYTV проверит подключение и проведёт установку.',
    'statusTitle': 'Проверяем<br>телевизор',
    'restoreTitle': 'Возвращаем<br>LG Home',
    'progressFoot': 'Можно свернуть приложение: ход работы будет в уведомлении',
    'steps': [
      'Подключение и проверка',
      'Приложения телевизора',
      'Установка пакетов',
      'Настройка Home'
    ],
    'log': 'Журнал операции',
    'awaiting': 'Ожидаем ответа телевизора…',
    'success': 'Ваш новый Home<br>готов к запуску',
    'successDesc':
      'Проверьте на ТВ кнопку Home, стрелки и OK. Затем проверьте выход из приложений и пробуждение.',
    'statusDone': 'Проверка завершена',
    'statusDoneDesc': 'Результат проверки доступен в журнале операции.',
    'restored': 'LG Home восстановлен',
    'restoredDesc': 'Проверьте кнопку Home на телевизоре.',
    'cancelled': 'Операция отменена',
    'cancelledDesc':
      'Если передача пакетов уже началась, проверьте состояние ТВ перед новой установкой.',
    'failed': 'Не удалось завершить<br>операцию',
    'failedDesc':
      'Операция не завершена. Посмотрите журнал и проверьте состояние ТВ перед повторной попыткой.',
    'recoveryTitle': 'Возврат к LG Home',
    'recoveryDesc':
      'Три коротких нажатия Home за две секунды. Для старых Helper до 0.6.13: удерживайте Home две секунды.',
    'three': '3 нажатия',
    'checkStatus': 'Проверить состояние',
    'restore': 'Восстановить LG Home',
    'toConnection': 'Вернуться к подключению',
    'done': 'На главный экран',
    'trustTitle': 'Это ваш телевизор?',
    'trustDesc':
      'Сравните отпечаток SSH с доверенным подключением, если он у вас есть. CYTV запомнит ТВ и остановит подключение, если ключ изменится.',
    'trust': 'Доверять и продолжить',
    'cancel': 'Отменить',
    'continue': 'Продолжить',
    'secretTitle': 'Код Developer Mode (Passphrase)',
    'secretDesc':
      'Введите Passphrase — код из шести символов на экране Developer Mode на телевизоре. Соблюдайте регистр букв. Нужен код с экрана ТВ, а не пароль аккаунта LG. Если кода нет, включите Key Server.',
    'rootSecretTitle': 'Пароль SSH',
    'rootSecretDesc': 'Введите существующий пароль root-доступа к телевизору.',
    'keySecretTitle': 'Пароль SSH-ключа',
    'keySecretDesc': 'Введите пароль, которым защищён ваш приватный ключ.',
    'secretLabel': 'Код / пароль',
    'reviewTitle': 'Подтвердите действие',
    'reviewDesc':
      'Проверьте сведения от установщика. Продолжайте, когда будете готовы.',
    'details': 'Подробности',
    'toolsTitle': 'Телевизор<br>под контролем',
    'toolsDesc': 'Проверьте установку или верните стандартный LG Home.',
    'statusTool': 'Состояние установки',
    'statusToolDesc': 'Проверить пакеты и незавершённые операции',
    'restoreToolDesc': 'Вернуть штатный главный экран телевизора',
    'toolsConnect': 'Введите адрес ТВ для выбранного действия.',
    'check': 'Проверить состояние',
    'preview': 'Демонстрация интерфейса · подключения к ТВ нет',
    'previewOnly':
      'Это превью интерфейса. Установите APK для подключения к ТВ.',
    'prepareService': 'Подготавливаем установщик…',
    'confirmRestore': 'Вернуть LG Home?',
    'confirmRestoreDesc':
      'CYTV подключится к телевизору и запросит подтверждение восстановления. Данные других приложений сохранятся.',
    'languageTitle': 'Язык',
    'languageClose': 'Закрыть',
    'tvGreeting': 'Хорошего вечера.',
    'tvSubtitle': 'Любимые приложения. Ничего лишнего.',
    'seconds': 'сек',
    'errorPrefix': 'Ошибка',
    'replayError':
      'Не удалось восстановить экран операции. Проверьте состояние ТВ.',
    'notificationText': 'Выполняется действие с телевизором',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Обновите Android System WebView или Chrome и откройте CYTV снова (нужен WebView 108+).',
    'connectionMethod': 'Выберите способ подключения',
    'maintenanceProgress':
      'Не выключайте телевизор. CYTV выполняет выбранное действие.',
    'homeDiagnostics': 'Диагностика кнопки Home',
    'homeDiagnosticsDesc':
      'Запишите одно нажатие Home и сохраните один отчёт. Только Helper без root.',
    'diagnosticProgress':
      'После приглашения нажмите Home один раз. Оставьте приложение открытым на минуту.',
    'saveReport': 'Сохранить отчёт',
    'reportDone': 'Отчёт готов',
    'reportDoneDesc': 'Сохраните JSON-отчёт и прикрепите его к обращению.',
    'reportSaved': 'Отчёт сохранён.',
    'reportError': 'Не удалось сохранить отчёт. Попробуйте ещё раз.',
    'devInstall':
      'На телевизоре откройте LG Apps, найдите Developer Mode и установите это приложение.',
    'devAccount':
      'Откройте Developer Mode и войдите в аккаунт LG Developer. Если аккаунта нет, создайте его на webostv.developer.lge.com.',
    'sessionHelp':
      'Следите за таймером Developer Mode: до его окончания откройте приложение и нажмите EXTEND при подключённом интернете. Если время истечёт, LG может удалить эти приложения.',
    'editionHelp':
      'No-root использует приложение Developer Mode от LG. Для Root нужны уже настроенные права администратора на телевизоре.',
    'pairingHelp':
      'Сопряжение — отдельный шаг: когда телевизор покажет запрос, разрешите подключение CYTV с пульта.',
    'homeHelperHelp':
      'Home — экран с вашими приложениями. Home Helper нужен, чтобы открывать его кнопкой Home на пульте.',
    'tryHomeHelp':
      'После установки нажмите Home для проверки. Если открылся LG Home, запустите Home Helper из списка приложений телевизора.',
    'resumeHomeHelp':
      'Трижды коротко нажмите Home за две секунды, чтобы вернуться в LG Home. Для возобновления откройте Home Helper, выберите «Запустить Helper» и подтвердите. Сохранённый выбор главного экрана не изменится.',
    'guideExample': 'Пример экрана LG',
    'guideNote':
      'Пример экрана LG. На вашем телевизоре он может выглядеть иначе. Вводите код со своего ТВ.',
    'connectRoot': 'Подключиться через Root',
    'recoveryReview': 'Проверить варианты восстановления',
    'recoveryReviewDesc':
      'Проверьте прерванную установку. Для изменений потребуется отдельное подтверждение.',
    'tvChecksReview': 'Проверьте результаты на ТВ',
    'homeObserved': 'Вы подтвердили работу Home',
    'tvChecksDesc':
      'Проверка пакетов, состояние запуска и ваше наблюдение за Home — разные результаты.'
  },
  'en': {
    'tryAgain': 'Try again',
    'removalPending': 'Removal is not finished yet.',
    'restartRemoval': 'Restart the TV to finish removal',
    'fullRestart':
      'Restart the TV completely: disconnect it from power, reconnect it, then choose Try again. Standby is not a full restart.',
    'connectionInterrupted':
      'Connection to the TV was interrupted. Check the connection and try again.',
    'removalUnconfirmed':
      'Removal could not be confirmed. Check the connection and try again.',

    'uninstall': 'Uninstall Clean Your TV',
    'uninstallDesc':
      'Remove the apps and owned setup data. A separate confirmation is required.',

    'setupTV': 'Set up TV',
    'wallpapers': 'Wallpapers',
    'maintenance': 'Maintenance',
    'wallpaperInstructions':
      'On the TV, open Home settings → Wallpapers → Upload from phone. Scan the QR code with your phone camera, choose a JPG/PNG and apply it on the TV.',
    'wallpaperLimit':
      'Phone uploads: images up to 1920×1080, without native 4K video. For true 4K, use CYTV on a computer.',
    'detect': 'Check connection',
    'detecting': 'Checking access…',
    'detectedRoot':
      'Root SSH detected. Root privileges will be verified after sign-in.',
    'detectedDev': 'Developer Mode detected. No-root matches this connection.',
    'detectedBoth':
      'Both connections are available. Choose the environment you use.',
    'detectedNone':
      'Access was not detected. Check your TV, network and access mode, or choose an edition manually.',
    'connectionMatch': 'Connection match',
    'editionNext': 'Continue',
    'android': 'for Android',
    'hero': 'A new Home.<br>From your phone.',
    'subtitle':
      'Set up Clean Your TV on LG webOS.<br>No computer. All right here.',
    'choose': 'Choose your edition',
    'noRootDesc': 'Uses LG Developer Mode',
    'rootDesc': 'Existing root and SSH access',
    'connect': 'Connect your TV',
    'networkFoot': 'Phone and TV on the same network',
    'tools': 'Status and recovery',
    'back': 'Back',
    'step': 'Connection',
    'connectTitle': 'Let’s connect<br>to your TV',
    'connectDesc':
      'Turn on your TV and enter its IP address.<br>Find it in your TV’s network settings.',
    'ip': 'TV IP address',
    'port': 'Port',
    'ipHelp': 'TV Settings → Network → Current connection',
    'ipError': 'Enter a valid IPv4 address, such as 192.168.1.50.',
    'portError': 'Port must be between 1 and 65535.',
    'prepare': 'Prepare your TV',
    'dev': 'Enable Developer Mode',
    'devDesc':
      'Turn on Dev Mode Status. The TV restarts. Open Developer Mode again.',
    'keyServer': 'Enable Key Server',
    'keyServerDesc':
      'Turn on Key Server and leave Developer Mode open. Its IP Address is the TV address to enter in CYTV.',
    'wifiTip':
      'Keep your phone and TV on the same local network. Disconnect your VPN during setup.',
    'install': 'Review and install',
    'reviewFoot': 'Review package versions before installation',
    'password': 'Password',
    'sshKey': 'SSH key',
    'importKey': 'Choose a key file',
    'keyImported': 'SSH key added',
    'keyPrivate': 'Your key stays on this phone',
    'rootNotice':
      'Requires existing root access. CYTV does not root your TV or change its firmware.',
    'rootHint': 'We’ll ask for your SSH password when connecting.',
    'keyError': 'Choose your private SSH key file first.',
    'keyFailed': 'Could not read the key. Choose a file up to 64 KB.',
    'browserKey': 'Key import is available in the Android app.',
    'progressTitle': 'Setting up<br>your new Home',
    'progressDesc':
      'Keep your TV on. CYTV will verify the connection and guide you through installation.',
    'statusTitle': 'Checking<br>your TV',
    'restoreTitle': 'Restoring<br>LG Home',
    'progressFoot': 'You can leave the app: progress stays in a notification',
    'steps': [
      'Connection and checks',
      'TV applications',
      'Package installation',
      'Home configuration'
    ],
    'log': 'Operation log',
    'awaiting': 'Waiting for your TV…',
    'success': 'Your new Home<br>is ready to launch',
    'successDesc':
      'Check Home, arrows and OK on the TV. Then check app exits and standby/wake.',
    'statusDone': 'Check complete',
    'statusDoneDesc': 'See the operation log for the check results.',
    'restored': 'LG Home restored',
    'restoredDesc': 'Check the Home button on your TV.',
    'cancelled': 'Operation cancelled',
    'cancelledDesc':
      'If package transfer already started, check the TV status before installing again.',
    'failed': 'Could not complete<br>this operation',
    'failedDesc':
      'The operation did not complete. Review the log and check TV status before trying again.',
    'recoveryTitle': 'Return to LG Home',
    'recoveryDesc':
      'Press Home three times within two seconds. For older Helper versions through 0.6.13, hold Home for two seconds.',
    'three': '3 presses',
    'checkStatus': 'Check status',
    'restore': 'Restore LG Home',
    'toConnection': 'Back to connection',
    'done': 'Back to start',
    'trustTitle': 'Is this your TV?',
    'trustDesc':
      'Compare this SSH fingerprint with a trusted connection if available. CYTV remembers your TV and stops if its key changes.',
    'trust': 'Trust and continue',
    'cancel': 'Cancel',
    'continue': 'Continue',
    'secretTitle': 'Developer Mode code (Passphrase)',
    'secretDesc':
      'Enter Passphrase: the six characters shown in Developer Mode on the TV. Match uppercase and lowercase letters. Use the code from the TV, not your LG account password. If no code is visible, turn on Key Server.',
    'rootSecretTitle': 'SSH password',
    'rootSecretDesc': 'Enter the existing root SSH password for your TV.',
    'keySecretTitle': 'SSH key passphrase',
    'keySecretDesc': 'Enter the passphrase protecting your private key.',
    'secretLabel': 'Code / password',
    'reviewTitle': 'Confirm this action',
    'reviewDesc':
      'Review the details from the installer. Continue when you’re ready.',
    'details': 'Details',
    'toolsTitle': 'Your TV,<br>under control',
    'toolsDesc': 'Check your installation or restore the standard LG Home.',
    'statusTool': 'Installation status',
    'statusToolDesc': 'Check packages and unresolved operations',
    'restoreToolDesc': 'Restore your TV’s original Home screen',
    'toolsConnect': 'Enter your TV address for this operation.',
    'check': 'Check status',
    'preview': 'Interface demonstration · no TV connection',
    'previewOnly':
      'This is a UI preview. Install the APK to connect to your TV.',
    'prepareService': 'Preparing the installer…',
    'confirmRestore': 'Restore LG Home?',
    'confirmRestoreDesc':
      'CYTV will connect to your TV and ask you to confirm recovery. Other apps are preserved.',
    'languageTitle': 'Language',
    'languageClose': 'Close',
    'tvGreeting': 'Make yourself at home.',
    'tvSubtitle': 'Your favourite apps. Room to breathe.',
    'seconds': 'sec',
    'errorPrefix': 'Error',
    'replayError': 'Could not restore operation view. Check your TV status.',
    'notificationText': 'TV operation in progress',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Update Android System WebView or Chrome, then reopen CYTV (WebView 108+ required).',
    'connectionMethod': 'Choose your connection method',
    'maintenanceProgress':
      'Keep the TV on. CYTV is carrying out the selected action.',
    'homeDiagnostics': 'Home button diagnostics',
    'homeDiagnosticsDesc':
      'Record one Home press and save one report. No-root Helper only.',
    'diagnosticProgress':
      'When prompted, press Home once. Keep this app open for one minute.',
    'saveReport': 'Save report',
    'reportDone': 'Report ready',
    'reportDoneDesc': 'Save the JSON report and attach it to your issue.',
    'reportSaved': 'Report saved.',
    'reportError': 'Could not save the report. Please try again.',
    'devInstall':
      'On the TV, open LG Apps, search for Developer Mode and install it.',
    'devAccount':
      'Open Developer Mode and sign in with your LG Developer account. Create an account at webostv.developer.lge.com if needed.',
    'sessionHelp':
      'Keep Developer Mode active: open it before the timer runs out and press EXTEND while the TV is online. If it expires, LG can remove these apps.',
    'editionHelp':
      "No-root uses LG's Developer Mode app. Root requires administrator access already set up on the TV.",
    'pairingHelp':
      'Pairing is a separate step: when the TV asks, approve CYTV with your remote.',
    'homeHelperHelp':
      'Home is your app screen. Home Helper makes the Home button open it.',
    'tryHomeHelp':
      "After installation, press Home to try it. If LG Home opens, open Home Helper from the TV's apps.",
    'resumeHomeHelp':
      'Three short Home presses within two seconds return to LG Home. To restart Home control, open Home Helper, choose Start Helper and confirm. Your saved Home screen choice is kept.',
    'guideExample': 'Example from LG',
    'guideNote':
      'Example from LG. The screen may look different on your TV. Use the code shown on your own TV.',
    'connectRoot': 'Connect using Root',
    'recoveryReview': 'Review recovery options',
    'recoveryReviewDesc':
      'Check an interrupted setup before deciding what to do. Changes require separate confirmation.',
    'tvChecksReview': 'Review TV checks',
    'homeObserved': 'Home button confirmed by you',
    'tvChecksDesc':
      'Package verification, startup readback and your Home-button observation are separate results.'
  },
  'de': {
    'tryAgain': 'Erneut versuchen',
    'removalPending': 'Die Entfernung ist noch nicht abgeschlossen.',
    'restartRemoval': 'TV neu starten, um die Entfernung abzuschließen',
    'fullRestart':
      'TV vollständig neu starten: vom Strom trennen, wieder anschließen und Erneut versuchen wählen. Standby ist kein vollständiger Neustart.',
    'connectionInterrupted':
      'Die Verbindung zum TV wurde unterbrochen. Verbindung prüfen und erneut versuchen.',
    'removalUnconfirmed':
      'Entfernung konnte nicht bestätigt werden. Verbindung prüfen und erneut versuchen.',

    'uninstall': 'Clean Your TV deinstallieren',
    'uninstallDesc':
      'Apps und eigene Einrichtungsdaten entfernen. Separate Bestätigung erforderlich.',

    'setupTV': 'TV einrichten',
    'wallpapers': 'Hintergrundbilder',
    'maintenance': 'Wartung',
    'wallpaperInstructions':
      'Öffnen Sie am TV die Home-Einstellungen → Hintergrundbilder → Vom Telefon hochladen. Scannen Sie den QR-Code mit der Handykamera, wählen Sie JPG/PNG und übernehmen Sie das Bild am TV.',
    'wallpaperLimit':
      'Vom Telefon: Bilder bis 1920×1080, ohne natives 4K-Video. Für echtes 4K verwenden Sie CYTV am Computer.',
    'detect': 'Verbindung prüfen',
    'detecting': 'Zugriff wird geprüft…',
    'detectedRoot':
      'Root-SSH erkannt. Die Root-Rechte werden nach der Anmeldung geprüft.',
    'detectedDev':
      'Developer Mode erkannt. No-root passt zu dieser Verbindung.',
    'detectedBoth':
      'Beide Verbindungen sind verfügbar. Wähle die Umgebung, die du nutzt.',
    'detectedNone':
      'Kein Zugriff erkannt. Prüfe Fernseher, Netzwerk und Zugriffsmodus oder wähle die Edition manuell.',
    'connectionMatch': 'Passend zur Verbindung',
    'editionNext': 'Weiter',
    'android': 'für Android',
    'hero': 'Ein neues Home.<br>Von deinem Smartphone.',
    'subtitle':
      'Richte Clean Your TV auf LG webOS ein.<br>Ohne Computer. Alles direkt hier.',
    'choose': 'Wähle deine Edition',
    'noRootDesc': 'Nutzt LG Developer Mode',
    'rootDesc': 'Root- und SSH-Zugriff bereits vorhanden',
    'connect': 'Fernseher verbinden',
    'networkFoot': 'Smartphone und Fernseher im selben Netzwerk',
    'tools': 'Status und Wiederherstellung',
    'back': 'Zurück',
    'step': 'Verbindung',
    'connectTitle': 'Verbinden wir uns<br>mit deinem Fernseher',
    'connectDesc':
      'Schalte den Fernseher ein und gib seine IP-Adresse ein.<br>Du findest sie in den Netzwerkeinstellungen des Fernsehers.',
    'ip': 'IP-Adresse des Fernsehers',
    'port': 'Port',
    'ipHelp': 'TV-Einstellungen → Netzwerk → Aktuelle Verbindung',
    'ipError': 'Gib eine gültige IPv4-Adresse ein, z. B. 192.168.1.50.',
    'portError': 'Der Port muss zwischen 1 und 65535 liegen.',
    'prepare': 'Fernseher vorbereiten',
    'dev': 'Developer Mode aktivieren',
    'devDesc':
      'Schalten Sie Dev Mode Status ein. Der TV startet neu. Öffnen Sie danach Developer Mode erneut.',
    'keyServer': 'Key Server aktivieren',
    'keyServerDesc':
      'Schalten Sie Key Server ein und lassen Sie Developer Mode geöffnet. Tragen Sie die dort angezeigte IP Address als TV-Adresse in CYTV ein.',
    'wifiTip':
      'Smartphone und Fernseher müssen im selben lokalen Netzwerk sein. Trenne die VPN-Verbindung während der Einrichtung.',
    'install': 'Prüfen und installieren',
    'reviewFoot': 'Paketversionen vor der Installation prüfen',
    'password': 'Passwort',
    'sshKey': 'SSH-Schlüssel',
    'importKey': 'Schlüsseldatei auswählen',
    'keyImported': 'SSH-Schlüssel hinzugefügt',
    'keyPrivate': 'Dein Schlüssel bleibt auf diesem Smartphone',
    'rootNotice':
      'Bereits eingerichteter Root-Zugriff erforderlich. CYTV rootet deinen Fernseher nicht und ändert seine Firmware nicht.',
    'rootHint': 'Beim Verbinden fragen wir nach deinem SSH-Passwort.',
    'keyError': 'Wähle zuerst die Datei mit deinem privaten SSH-Schlüssel.',
    'keyFailed':
      'Schlüssel konnte nicht gelesen werden. Wähle eine Datei mit maximal 64 KB.',
    'browserKey': 'Schlüsselimport ist in der Android-App verfügbar.',
    'progressTitle': 'Dein neues Home<br>wird eingerichtet',
    'progressDesc':
      'Lass den Fernseher eingeschaltet. CYTV prüft die Verbindung und führt dich durch die Installation.',
    'statusTitle': 'Dein Fernseher<br>wird geprüft',
    'restoreTitle': 'LG Home<br>wird wiederhergestellt',
    'progressFoot':
      'Du kannst die App verlassen: Der Fortschritt bleibt in einer Benachrichtigung sichtbar',
    'steps': [
      'Verbindung und Prüfung',
      'TV-Apps',
      'Paketinstallation',
      'Home-Einrichtung'
    ],
    'log': 'Vorgangsprotokoll',
    'awaiting': 'Warten auf deinen Fernseher…',
    'success': 'Dein neues Home<br>ist startbereit',
    'successDesc':
      'Prüfe Home, Pfeiltasten und OK am Fernseher. Prüfe danach das Verlassen von Apps sowie Standby und Aufwecken.',
    'statusDone': 'Prüfung abgeschlossen',
    'statusDoneDesc': 'Die Ergebnisse findest du im Vorgangsprotokoll.',
    'restored': 'LG Home wiederhergestellt',
    'restoredDesc': 'Prüfe die Home-Taste am Fernseher.',
    'cancelled': 'Vorgang abgebrochen',
    'cancelledDesc':
      'Falls die Paketübertragung bereits begonnen hat, prüfe vor einer erneuten Installation den TV-Status.',
    'failed': 'Vorgang konnte nicht<br>abgeschlossen werden',
    'failedDesc':
      'Der Vorgang wurde nicht abgeschlossen. Sieh im Protokoll nach und prüfe den TV-Status vor einem neuen Versuch.',
    'recoveryTitle': 'Zurück zu LG Home',
    'recoveryDesc':
      'Drücke Home dreimal innerhalb von zwei Sekunden. Bei älteren Helper-Versionen bis einschließlich 0.6.13: Halte Home zwei Sekunden lang gedrückt.',
    'three': '3 Tastendrücke',
    'checkStatus': 'Status prüfen',
    'restore': 'LG Home wiederherstellen',
    'toConnection': 'Zurück zur Verbindung',
    'done': 'Zurück zum Start',
    'trustTitle': 'Ist das dein Fernseher?',
    'trustDesc':
      'Vergleiche diesen SSH-Fingerabdruck mit einer vertrauenswürdigen Verbindung, falls vorhanden. CYTV merkt sich deinen Fernseher und stoppt, wenn sich sein Schlüssel ändert.',
    'trust': 'Vertrauen und weiter',
    'cancel': 'Abbrechen',
    'continue': 'Weiter',
    'secretTitle': 'Developer Mode-Code (Passphrase)',
    'secretDesc':
      'Geben Sie die Passphrase ein: die sechs Zeichen, die Developer Mode am TV anzeigt. Beachten Sie Groß- und Kleinschreibung. Verwenden Sie den Code vom TV, nicht das Passwort Ihres LG-Kontos. Wird kein Code angezeigt, schalten Sie Key Server ein.',
    'rootSecretTitle': 'SSH-Passwort',
    'rootSecretDesc':
      'Gib das vorhandene Root-SSH-Passwort deines Fernsehers ein.',
    'keySecretTitle': 'Passphrase des SSH-Schlüssels',
    'keySecretDesc':
      'Gib die Passphrase ein, die deinen privaten Schlüssel schützt.',
    'secretLabel': 'Code / Passwort',
    'reviewTitle': 'Aktion bestätigen',
    'reviewDesc':
      'Prüfe die Angaben des Installationsprogramms. Fahre fort, wenn du bereit bist.',
    'details': 'Details',
    'toolsTitle': 'Dein Fernseher.<br>Unter Kontrolle.',
    'toolsDesc':
      'Prüfe deine Installation oder stelle das ursprüngliche LG Home wieder her.',
    'statusTool': 'Installationsstatus',
    'statusToolDesc': 'Pakete und nicht abgeschlossene Vorgänge prüfen',
    'restoreToolDesc':
      'Ursprünglichen Home-Bildschirm des Fernsehers wiederherstellen',
    'toolsConnect': 'Gib für diesen Vorgang die Adresse deines Fernsehers ein.',
    'check': 'Status prüfen',
    'preview': 'Oberflächenvorschau · keine TV-Verbindung',
    'previewOnly':
      'Dies ist eine Vorschau der Oberfläche. Installiere die APK, um dich mit deinem Fernseher zu verbinden.',
    'prepareService': 'Installation wird vorbereitet…',
    'confirmRestore': 'LG Home wiederherstellen?',
    'confirmRestoreDesc':
      'CYTV verbindet sich mit deinem Fernseher und bittet dich, die Wiederherstellung zu bestätigen. Andere Apps bleiben erhalten.',
    'languageTitle': 'Sprache',
    'languageClose': 'Schließen',
    'tvGreeting': 'Mach es dir gemütlich.',
    'tvSubtitle': 'Deine Lieblingsapps. Raum zum Durchatmen.',
    'seconds': 'Sek.',
    'errorPrefix': 'Fehler',
    'replayError':
      'Die Vorgangsansicht konnte nicht wiederhergestellt werden. Prüfe den TV-Status.',
    'notificationText': 'TV-Aktion wird ausgeführt',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Aktualisiere Android System WebView oder Chrome und öffne CYTV erneut (WebView 108+ erforderlich).',
    'connectionMethod': 'Verbindungsmethode wählen',
    'maintenanceProgress':
      'Lassen Sie den Fernseher eingeschaltet. CYTV führt die gewählte Aktion aus.',
    'homeDiagnostics': 'Home-Taste diagnostizieren',
    'homeDiagnosticsDesc':
      'Einen Home-Tastendruck aufzeichnen und einen Bericht speichern. Nur No-root Helper.',
    'diagnosticProgress':
      'Nach Aufforderung einmal Home drücken. Diese App eine Minute geöffnet lassen.',
    'saveReport': 'Bericht speichern',
    'reportDone': 'Bericht bereit',
    'reportDoneDesc': 'JSON-Bericht speichern und an Ihre Meldung anhängen.',
    'reportSaved': 'Bericht gespeichert.',
    'reportError': 'Bericht konnte nicht gespeichert werden. Erneut versuchen.',
    'devInstall':
      'Öffnen Sie am TV LG Apps, suchen Sie nach Developer Mode und installieren Sie die App.',
    'devAccount':
      'Öffnen Sie Developer Mode und melden Sie sich mit Ihrem LG Developer-Konto an. Erstellen Sie bei Bedarf ein Konto unter webostv.developer.lge.com.',
    'sessionHelp':
      'Halten Sie Developer Mode aktiv: Öffnen Sie die App vor Ablauf des Timers und drücken Sie bei bestehender Internetverbindung EXTEND. Nach Ablauf kann LG diese Apps entfernen.',
    'editionHelp':
      'No-root nutzt LGs Developer Mode-App. Root erfordert bereits eingerichteten Administratorzugriff auf den TV.',
    'pairingHelp':
      'Die Kopplung ist ein eigener Schritt: Bestätigen Sie CYTV mit der Fernbedienung, wenn der TV danach fragt.',
    'homeHelperHelp':
      'Home ist Ihr App-Bildschirm. Home Helper sorgt dafür, dass die Home-Taste ihn öffnet.',
    'tryHomeHelp':
      'Drücken Sie nach der Installation zum Testen Home. Falls LG Home erscheint, öffnen Sie Home Helper in der App-Liste des TV.',
    'resumeHomeHelp':
      'Drei kurze Home-Tastendrücke in zwei Sekunden öffnen LG Home. Öffnen Sie zum Neustart der Home-Steuerung Home Helper, wählen Sie Helper starten und bestätigen Sie. Ihre gespeicherte Home-Auswahl bleibt erhalten.',
    'guideExample': 'Beispiel von LG',
    'guideNote':
      'Beispiel von LG. Der Bildschirm Ihres TV kann anders aussehen. Verwenden Sie den Code auf Ihrem eigenen TV.',
    'connectRoot': 'Mit Root verbinden',
    'recoveryReview': 'Wiederherstellungsoptionen prüfen',
    'recoveryReviewDesc':
      'Prüfen Sie eine unterbrochene Einrichtung. Änderungen erfordern eine gesonderte Bestätigung.',
    'tvChecksReview': 'TV-Prüfungen ansehen',
    'homeObserved': 'Home-Taste von Ihnen bestätigt',
    'tvChecksDesc':
      'Paketprüfung, Startprüfung und Ihre Home-Beobachtung sind getrennte Ergebnisse.'
  },
  'fr': {
    'tryAgain': 'Réessayer',
    'removalPending': 'La suppression n’est pas encore terminée.',
    'restartRemoval': 'Redémarrez le téléviseur pour terminer la suppression',
    'fullRestart':
      'Redémarrez complètement le téléviseur : débranchez l’alimentation, rebranchez-la, puis choisissez Réessayer. La veille n’est pas un redémarrage complet.',
    'connectionInterrupted':
      'La connexion au téléviseur a été interrompue. Vérifiez la connexion et réessayez.',
    'removalUnconfirmed':
      'La suppression n’a pas pu être confirmée. Vérifiez la connexion et réessayez.',

    'uninstall': 'Désinstaller Clean Your TV',
    'uninstallDesc':
      'Supprime les applications et leurs données de configuration. Confirmation séparée requise.',

    'setupTV': 'Configurer la TV',
    'wallpapers': 'Fonds d’écran',
    'maintenance': 'Maintenance',
    'wallpaperInstructions':
      'Sur la TV, ouvrez les paramètres Home → Fonds d’écran → Importer depuis le téléphone. Scannez le QR avec la caméra, choisissez JPG/PNG et appliquez le fond sur la TV.',
    'wallpaperLimit':
      'Depuis le téléphone : images jusqu’à 1920×1080, sans vidéo 4K native. Pour la vraie 4K, utilisez CYTV sur ordinateur.',
    'detect': 'Vérifier la connexion',
    'detecting': 'Vérification de l’accès…',
    'detectedRoot':
      'Accès SSH Root détecté. Les privilèges root seront vérifiés après connexion.',
    'detectedDev':
      'Developer Mode détecté. No-root convient à cette connexion.',
    'detectedBoth':
      'Les deux connexions sont disponibles. Choisissez l’environnement que vous utilisez.',
    'detectedNone':
      'Aucun accès détecté. Vérifiez le téléviseur, le réseau et le mode d’accès, ou choisissez une édition manuellement.',
    'connectionMatch': 'Selon la connexion',
    'editionNext': 'Continuer',
    'android': 'pour Android',
    'hero': 'Un nouveau Home.<br>Depuis votre téléphone.',
    'subtitle':
      'Configurez Clean Your TV sur LG webOS.<br>Sans ordinateur. Tout est ici.',
    'choose': 'Choisissez votre édition',
    'noRootDesc': 'Utilise Developer Mode de LG',
    'rootDesc': 'Accès root et SSH déjà configurés',
    'connect': 'Connecter votre téléviseur',
    'networkFoot': 'Téléphone et téléviseur sur le même réseau',
    'tools': 'État et restauration',
    'back': 'Retour',
    'step': 'Connexion',
    'connectTitle': 'Connectons-nous<br>à votre téléviseur',
    'connectDesc':
      'Allumez le téléviseur et saisissez son adresse IP.<br>Elle figure dans ses paramètres réseau.',
    'ip': 'Adresse IP du téléviseur',
    'port': 'Port',
    'ipHelp': 'Paramètres TV → Réseau → Connexion actuelle',
    'ipError': 'Saisissez une adresse IPv4 valide, par exemple 192.168.1.50.',
    'portError': 'Le port doit être compris entre 1 et 65535.',
    'prepare': 'Préparer votre téléviseur',
    'dev': 'Activer Developer Mode',
    'devDesc':
      'Activez Dev Mode Status. Le TV redémarre. Ouvrez ensuite Developer Mode à nouveau.',
    'keyServer': 'Activer Key Server',
    'keyServerDesc':
      'Activez Key Server et laissez Developer Mode ouvert. Saisissez son IP Address comme adresse du TV dans CYTV.',
    'wifiTip':
      'Le téléphone et le téléviseur doivent être sur le même réseau local. Déconnectez votre VPN pendant la configuration.',
    'install': 'Vérifier et installer',
    'reviewFoot': 'Vérifiez les versions des paquets avant l’installation',
    'password': 'Mot de passe',
    'sshKey': 'Clé SSH',
    'importKey': 'Choisir un fichier de clé',
    'keyImported': 'Clé SSH ajoutée',
    'keyPrivate': 'Votre clé reste sur ce téléphone',
    'rootNotice':
      'Nécessite un accès root déjà configuré. CYTV ne roote pas votre téléviseur et ne modifie pas son micrologiciel.',
    'rootHint': 'Votre mot de passe SSH sera demandé lors de la connexion.',
    'keyError': 'Choisissez d’abord le fichier de votre clé SSH privée.',
    'keyFailed':
      'Impossible de lire la clé. Choisissez un fichier de 64 Ko maximum.',
    'browserKey':
      'L’importation de clé est disponible dans l’application Android.',
    'progressTitle': 'Configuration<br>de votre nouveau Home',
    'progressDesc':
      'Laissez le téléviseur allumé. CYTV vérifiera la connexion et vous guidera pendant l’installation.',
    'statusTitle': 'Vérification<br>de votre téléviseur',
    'restoreTitle': 'Restauration<br>de LG Home',
    'progressFoot':
      'Vous pouvez quitter l’application : la progression reste dans une notification',
    'steps': [
      'Connexion et vérifications',
      'Applications du téléviseur',
      'Installation des paquets',
      'Configuration de Home'
    ],
    'log': 'Journal de l’opération',
    'awaiting': 'En attente du téléviseur…',
    'success': 'Votre nouveau Home<br>est prêt à démarrer',
    'successDesc':
      'Testez Home, les flèches et OK sur le téléviseur. Vérifiez ensuite la sortie des applications et la mise en veille et le réveil.',
    'statusDone': 'Vérification terminée',
    'statusDoneDesc': 'Consultez les résultats dans le journal de l’opération.',
    'restored': 'LG Home restauré',
    'restoredDesc': 'Testez la touche Home sur votre téléviseur.',
    'cancelled': 'Opération annulée',
    'cancelledDesc':
      'Si le transfert des paquets a déjà commencé, vérifiez l’état du téléviseur avant de relancer l’installation.',
    'failed': 'Impossible de terminer<br>cette opération',
    'failedDesc':
      'L’opération n’a pas abouti. Consultez le journal et vérifiez l’état du téléviseur avant de réessayer.',
    'recoveryTitle': 'Revenir à LG Home',
    'recoveryDesc':
      'Appuyez trois fois sur Home en deux secondes. Pour les anciennes versions de Helper jusqu’à la version 0.6.13 incluse, maintenez Home pendant deux secondes.',
    'three': '3 appuis',
    'checkStatus': 'Vérifier l’état',
    'restore': 'Restaurer LG Home',
    'toConnection': 'Retour à la connexion',
    'done': 'Retour au début',
    'trustTitle': 'Est-ce votre téléviseur ?',
    'trustDesc':
      'Comparez cette empreinte SSH avec celle d’une connexion de confiance, si vous en avez une. CYTV mémorise votre téléviseur et s’arrête si sa clé change.',
    'trust': 'Faire confiance et continuer',
    'cancel': 'Annuler',
    'continue': 'Continuer',
    'secretTitle': 'Code Developer Mode (Passphrase)',
    'secretDesc':
      'Saisissez la Passphrase : les six caractères affichés dans Developer Mode sur le TV. Respectez les majuscules et minuscules. Utilisez le code du TV, pas le mot de passe du compte LG. Si aucun code n’apparaît, activez Key Server.',
    'rootSecretTitle': 'Mot de passe SSH',
    'rootSecretDesc':
      'Saisissez le mot de passe SSH root existant de votre téléviseur.',
    'keySecretTitle': 'Phrase secrète de la clé SSH',
    'keySecretDesc':
      'Saisissez la phrase secrète qui protège votre clé privée.',
    'secretLabel': 'Code / mot de passe',
    'reviewTitle': 'Confirmer cette action',
    'reviewDesc':
      'Vérifiez les informations de l’installateur. Continuez lorsque vous êtes prêt.',
    'details': 'Détails',
    'toolsTitle': 'Votre téléviseur,<br>sous contrôle',
    'toolsDesc': 'Vérifiez votre installation ou restaurez LG Home d’origine.',
    'statusTool': 'État de l’installation',
    'statusToolDesc': 'Vérifier les paquets et les opérations non résolues',
    'restoreToolDesc': 'Restaurer l’écran Home d’origine du téléviseur',
    'toolsConnect': 'Saisissez l’adresse du téléviseur pour cette opération.',
    'check': 'Vérifier l’état',
    'preview': 'Démonstration de l’interface · aucune connexion au téléviseur',
    'previewOnly':
      'Ceci est un aperçu de l’interface. Installez l’APK pour vous connecter au téléviseur.',
    'prepareService': 'Préparation de l’installateur…',
    'confirmRestore': 'Restaurer LG Home ?',
    'confirmRestoreDesc':
      'CYTV se connectera au téléviseur et vous demandera de confirmer la restauration. Les autres applications seront conservées.',
    'languageTitle': 'Langue',
    'languageClose': 'Fermer',
    'tvGreeting': 'Faites comme chez vous.',
    'tvSubtitle': 'Vos applications préférées. De l’espace pour respirer.',
    'seconds': 's',
    'errorPrefix': 'Erreur',
    'replayError':
      'Impossible de restaurer l’écran de l’opération. Vérifiez l’état du téléviseur.',
    'notificationText': 'Action sur le téléviseur en cours',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Mettez à jour Android System WebView ou Chrome, puis rouvrez CYTV (WebView 108+ requis).',
    'connectionMethod': 'Choisissez le mode de connexion',
    'maintenanceProgress':
      'Laissez le téléviseur allumé. CYTV exécute l’action sélectionnée.',
    'homeDiagnostics': 'Diagnostic du bouton Home',
    'homeDiagnosticsDesc':
      'Enregistrez un appui sur Home et sauvegardez un rapport. Helper sans root uniquement.',
    'diagnosticProgress':
      'À l’invite, appuyez une fois sur Home. Gardez cette app ouverte une minute.',
    'saveReport': 'Enregistrer le rapport',
    'reportDone': 'Rapport prêt',
    'reportDoneDesc':
      'Enregistrez le rapport JSON et joignez-le à votre signalement.',
    'reportSaved': 'Rapport enregistré.',
    'reportError': 'Impossible d’enregistrer le rapport. Réessayez.',
    'devInstall':
      'Sur le TV, ouvrez LG Apps, cherchez Developer Mode et installez cette app.',
    'devAccount':
      'Ouvrez Developer Mode et connectez-vous avec votre compte LG Developer. Si nécessaire, créez un compte sur webostv.developer.lge.com.',
    'sessionHelp':
      'Gardez Developer Mode actif : avant la fin du compte à rebours, ouvrez-le et appuyez sur EXTEND avec le TV connecté à Internet. À expiration, LG peut supprimer ces apps.',
    'editionHelp':
      'No-root utilise l’app Developer Mode de LG. Root nécessite un accès administrateur déjà configuré sur le TV.',
    'pairingHelp':
      'L’appairage est une étape distincte : quand le TV le demande, autorisez CYTV avec la télécommande.',
    'homeHelperHelp':
      'Home est votre écran d’apps. Home Helper permet de l’ouvrir avec la touche Home.',
    'tryHomeHelp':
      'Après l’installation, appuyez sur Home pour essayer. Si LG Home s’ouvre, lancez Home Helper depuis les apps du TV.',
    'resumeHomeHelp':
      'Trois pressions brèves sur Home en deux secondes ramènent à LG Home. Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé.',
    'guideExample': 'Exemple LG',
    'guideNote':
      'Exemple LG. L’écran de votre TV peut être différent. Utilisez le code affiché sur votre propre TV.',
    'connectRoot': 'Se connecter avec Root',
    'recoveryReview': 'Examiner les options de récupération',
    'recoveryReviewDesc':
      'Vérifiez une installation interrompue. Les modifications nécessitent une confirmation distincte.',
    'tvChecksReview': 'Examiner les vérifications du TV',
    'homeObserved': 'Bouton Home confirmé par vous',
    'tvChecksDesc':
      'Vérification des paquets, démarrage et votre observation de Home sont des résultats distincts.'
  },
  'it': {
    'tryAgain': 'Riprova',
    'removalPending': 'La rimozione non è ancora terminata.',
    'restartRemoval': 'Riavvia la TV per completare la rimozione',
    'fullRestart':
      'Riavvia completamente la TV: scollega l’alimentazione, ricollegala, poi scegli Riprova. Lo standby non è un riavvio completo.',
    'connectionInterrupted':
      'La connessione alla TV si è interrotta. Controlla la connessione e riprova.',
    'removalUnconfirmed':
      'Impossibile confermare la rimozione. Controlla la connessione e riprova.',

    'uninstall': 'Disinstalla Clean Your TV',
    'uninstallDesc':
      'Rimuovi le app e i relativi dati di configurazione. Serve una conferma separata.',

    'setupTV': 'Configura TV',
    'wallpapers': 'Sfondi',
    'maintenance': 'Manutenzione',
    'wallpaperInstructions':
      'Sulla TV, apri le impostazioni Home → Sfondi → Carica dal telefono. Scansiona il QR con la fotocamera, scegli JPG/PNG e applica lo sfondo sulla TV.',
    'wallpaperLimit':
      'Dal telefono: immagini fino a 1920×1080, senza video 4K nativo. Per il vero 4K, usa CYTV sul computer.',
    'detect': 'Verifica connessione',
    'detecting': 'Verifica dell’accesso…',
    'detectedRoot':
      'Accesso SSH Root rilevato. I privilegi root saranno verificati dopo l’accesso.',
    'detectedDev':
      'Developer Mode rilevato. No-root è adatto a questa connessione.',
    'detectedBoth':
      'Sono disponibili entrambe le connessioni. Scegli l’ambiente che utilizzi.',
    'detectedNone':
      'Nessun accesso rilevato. Controlla TV, rete e modalità di accesso oppure scegli un’edizione manualmente.',
    'connectionMatch': 'In base alla connessione',
    'editionNext': 'Continua',
    'android': 'per Android',
    'hero': 'Un nuovo Home.<br>Dal tuo telefono.',
    'subtitle':
      'Configura Clean Your TV su LG webOS.<br>Senza computer. Tutto qui.',
    'choose': 'Scegli la tua edizione',
    'noRootDesc': 'Usa Developer Mode di LG',
    'rootDesc': 'Accesso root e SSH già configurato',
    'connect': 'Collega la TV',
    'networkFoot': 'Telefono e TV sulla stessa rete',
    'tools': 'Stato e ripristino',
    'back': 'Indietro',
    'step': 'Connessione',
    'connectTitle': 'Colleghiamoci<br>alla tua TV',
    'connectDesc':
      'Accendi la TV e inserisci il suo indirizzo IP.<br>Lo trovi nelle impostazioni di rete della TV.',
    'ip': 'Indirizzo IP della TV',
    'port': 'Porta',
    'ipHelp': 'Impostazioni TV → Rete → Connessione attuale',
    'ipError': 'Inserisci un indirizzo IPv4 valido, ad esempio 192.168.1.50.',
    'portError': 'La porta deve essere compresa tra 1 e 65535.',
    'prepare': 'Prepara la TV',
    'dev': 'Attiva Developer Mode',
    'devDesc':
      'Attiva Dev Mode Status. La TV si riavvia. Poi apri di nuovo Developer Mode.',
    'keyServer': 'Attiva Key Server',
    'keyServerDesc':
      'Attiva Key Server e lascia Developer Mode aperto. Inserisci il suo IP Address come indirizzo della TV in CYTV.',
    'wifiTip':
      'Telefono e TV devono essere sulla stessa rete locale. Disconnetti la VPN durante la configurazione.',
    'install': 'Verifica e installa',
    'reviewFoot': 'Verifica le versioni dei pacchetti prima dell’installazione',
    'password': 'Password',
    'sshKey': 'Chiave SSH',
    'importKey': 'Scegli un file chiave',
    'keyImported': 'Chiave SSH aggiunta',
    'keyPrivate': 'La chiave rimane su questo telefono',
    'rootNotice':
      'Richiede un accesso root già configurato. CYTV non esegue il root della TV e non ne modifica il firmware.',
    'rootHint': 'Ti chiederemo la password SSH durante la connessione.',
    'keyError': 'Scegli prima il file della tua chiave SSH privata.',
    'keyFailed':
      'Impossibile leggere la chiave. Scegli un file di massimo 64 KB.',
    'browserKey': 'L’importazione delle chiavi è disponibile nell’app Android.',
    'progressTitle': 'Configurazione<br>del tuo nuovo Home',
    'progressDesc':
      'Lascia la TV accesa. CYTV verificherà la connessione e ti guiderà nell’installazione.',
    'statusTitle': 'Verifica<br>della tua TV',
    'restoreTitle': 'Ripristino<br>di LG Home',
    'progressFoot':
      'Puoi uscire dall’app: l’avanzamento rimane in una notifica',
    'steps': [
      'Connessione e verifiche',
      'Applicazioni TV',
      'Installazione dei pacchetti',
      'Configurazione di Home'
    ],
    'log': 'Registro dell’operazione',
    'awaiting': 'In attesa della TV…',
    'success': 'Il tuo nuovo Home<br>è pronto per l’avvio',
    'successDesc':
      'Prova Home, le frecce e OK sulla TV. Poi verifica l’uscita dalle app e l’entrata e l’uscita dallo standby.',
    'statusDone': 'Verifica completata',
    'statusDoneDesc': 'Consulta i risultati nel registro dell’operazione.',
    'restored': 'LG Home ripristinato',
    'restoredDesc': 'Prova il tasto Home sulla TV.',
    'cancelled': 'Operazione annullata',
    'cancelledDesc':
      'Se il trasferimento dei pacchetti è già iniziato, verifica lo stato della TV prima di installare di nuovo.',
    'failed': 'Impossibile completare<br>l’operazione',
    'failedDesc':
      'L’operazione non è stata completata. Consulta il registro e verifica lo stato della TV prima di riprovare.',
    'recoveryTitle': 'Torna a LG Home',
    'recoveryDesc':
      'Premi Home tre volte entro due secondi. Per le versioni precedenti di Helper fino alla 0.6.13 inclusa, tieni premuto Home per due secondi.',
    'three': '3 pressioni',
    'checkStatus': 'Verifica stato',
    'restore': 'Ripristina LG Home',
    'toConnection': 'Torna alla connessione',
    'done': 'Torna all’inizio',
    'trustTitle': 'È la tua TV?',
    'trustDesc':
      'Confronta questa impronta SSH con una connessione attendibile, se disponibile. CYTV ricorda la TV e si ferma se la sua chiave cambia.',
    'trust': 'Considera attendibile e continua',
    'cancel': 'Annulla',
    'continue': 'Continua',
    'secretTitle': 'Codice Developer Mode (Passphrase)',
    'secretDesc':
      'Inserisci la Passphrase: i sei caratteri mostrati in Developer Mode sulla TV. Rispetta maiuscole e minuscole. Usa il codice della TV, non la password del tuo account LG. Se il codice non appare, attiva Key Server.',
    'rootSecretTitle': 'Password SSH',
    'rootSecretDesc': 'Inserisci la password SSH root esistente della TV.',
    'keySecretTitle': 'Passphrase della chiave SSH',
    'keySecretDesc':
      'Inserisci la passphrase che protegge la tua chiave privata.',
    'secretLabel': 'Codice / password',
    'reviewTitle': 'Conferma l’azione',
    'reviewDesc':
      'Verifica i dettagli del programma di installazione. Continua quando sei pronto.',
    'details': 'Dettagli',
    'toolsTitle': 'La tua TV,<br>sotto controllo',
    'toolsDesc': 'Verifica l’installazione o ripristina LG Home originale.',
    'statusTool': 'Stato dell’installazione',
    'statusToolDesc': 'Verifica pacchetti e operazioni non risolte',
    'restoreToolDesc': 'Ripristina la schermata Home originale della TV',
    'toolsConnect': 'Inserisci l’indirizzo della TV per questa operazione.',
    'check': 'Verifica stato',
    'preview': 'Dimostrazione dell’interfaccia · nessuna connessione alla TV',
    'previewOnly':
      'Questa è un’anteprima dell’interfaccia. Installa l’APK per collegarti alla TV.',
    'prepareService': 'Preparazione dell’installazione…',
    'confirmRestore': 'Ripristinare LG Home?',
    'confirmRestoreDesc':
      'CYTV si collegherà alla TV e ti chiederà di confermare il ripristino. Le altre app saranno conservate.',
    'languageTitle': 'Lingua',
    'languageClose': 'Chiudi',
    'tvGreeting': 'Sentiti a casa.',
    'tvSubtitle': 'Le tue app preferite. Spazio per respirare.',
    'seconds': 's',
    'errorPrefix': 'Errore',
    'replayError':
      'Impossibile ripristinare la schermata dell’operazione. Verifica lo stato della TV.',
    'notificationText': 'Operazione sulla TV in corso',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Aggiorna Android System WebView o Chrome, poi riapri CYTV (richiesto WebView 108+).',
    'connectionMethod': 'Scegli come connetterti',
    'maintenanceProgress':
      'Lascia la TV accesa. CYTV sta eseguendo l’azione selezionata.',
    'homeDiagnostics': 'Diagnostica del tasto Home',
    'homeDiagnosticsDesc':
      'Registra una pressione di Home e salva un rapporto. Solo Helper senza root.',
    'diagnosticProgress':
      'Quando richiesto, premi Home una volta. Tieni questa app aperta per un minuto.',
    'saveReport': 'Salva rapporto',
    'reportDone': 'Rapporto pronto',
    'reportDoneDesc': 'Salva il rapporto JSON e allegalo alla segnalazione.',
    'reportSaved': 'Rapporto salvato.',
    'reportError': 'Impossibile salvare il rapporto. Riprova.',
    'devInstall': 'Sulla TV, apri LG Apps, cerca Developer Mode e installalo.',
    'devAccount':
      'Apri Developer Mode e accedi con il tuo account LG Developer. Se necessario, crea un account su webostv.developer.lge.com.',
    'sessionHelp':
      'Mantieni Developer Mode attivo: prima che scada il timer, aprilo e premi EXTEND con la TV connessa a Internet. Alla scadenza, LG può rimuovere queste app.',
    'editionHelp':
      'No-root usa l’app Developer Mode di LG. Root richiede un accesso amministratore già configurato sulla TV.',
    'pairingHelp':
      'L’associazione è un passaggio separato: quando la TV lo chiede, autorizza CYTV con il telecomando.',
    'homeHelperHelp':
      'Home è la tua schermata delle app. Home Helper fa sì che il tasto Home la apra.',
    'tryHomeHelp':
      'Dopo l’installazione, premi Home per provare. Se si apre LG Home, apri Home Helper dalle app della TV.',
    'resumeHomeHelp':
      'Tre pressioni brevi di Home entro due secondi riportano a LG Home. Per riavviare il controllo Home, apri Home Helper, scegli Avvia Helper e conferma. La tua scelta della schermata Home viene mantenuta.',
    'guideExample': 'Esempio LG',
    'guideNote':
      'Esempio LG. La schermata della tua TV potrebbe essere diversa. Usa il codice mostrato sulla tua TV.',
    'connectRoot': 'Connetti con Root',
    'recoveryReview': 'Esamina le opzioni di ripristino',
    'recoveryReviewDesc':
      'Verifica una configurazione interrotta. Le modifiche richiedono una conferma separata.',
    'tvChecksReview': 'Esamina le verifiche della TV',
    'homeObserved': 'Tasto Home confermato da te',
    'tvChecksDesc':
      'Verifica pacchetti, avvio e tua osservazione di Home sono risultati separati.'
  },
  'es': {
    'tryAgain': 'Intentar de nuevo',
    'removalPending': 'La eliminación aún no ha terminado.',
    'restartRemoval': 'Reinicia el TV para terminar la eliminación',
    'fullRestart':
      'Reinicia el TV por completo: desconéctalo de la corriente, vuelve a conectarlo y elige Intentar de nuevo. El modo de espera no es un reinicio completo.',
    'connectionInterrupted':
      'Se interrumpió la conexión con el TV. Comprueba la conexión e inténtalo de nuevo.',
    'removalUnconfirmed':
      'No se pudo confirmar la eliminación. Comprueba la conexión e inténtalo de nuevo.',

    'uninstall': 'Desinstalar Clean Your TV',
    'uninstallDesc':
      'Elimina las apps y sus datos de configuración. Requiere confirmación aparte.',

    'setupTV': 'Configurar TV',
    'wallpapers': 'Fondos de pantalla',
    'maintenance': 'Mantenimiento',
    'wallpaperInstructions':
      'En el TV, abra los ajustes de Home → Fondos de pantalla → Subir desde el teléfono. Escanee el QR con la cámara, elija JPG/PNG y aplique el fondo en el TV.',
    'wallpaperLimit':
      'Desde el teléfono: imágenes de hasta 1920×1080, sin vídeo 4K nativo. Para 4K real, use CYTV en un ordenador.',
    'detect': 'Comprobar conexión',
    'detecting': 'Comprobando acceso…',
    'detectedRoot':
      'Root SSH detectado. Los permisos root se comprobarán tras iniciar sesión.',
    'detectedDev':
      'Developer Mode detectado. No-root corresponde a esta conexión.',
    'detectedBoth':
      'Ambas conexiones están disponibles. Elige el entorno que usas.',
    'detectedNone':
      'No se ha detectado acceso. Comprueba el televisor, la red y el modo de acceso, o elige una edición manualmente.',
    'connectionMatch': 'Según la conexión',
    'editionNext': 'Continuar',
    'android': 'para Android',
    'hero': 'Un nuevo Home.<br>Desde tu teléfono.',
    'subtitle':
      'Configura Clean Your TV en LG webOS.<br>Sin ordenador. Todo aquí.',
    'choose': 'Elige tu edición',
    'noRootDesc': 'Usa Developer Mode de LG',
    'rootDesc': 'Acceso root y SSH ya configurado',
    'connect': 'Conectar el televisor',
    'networkFoot': 'Teléfono y televisor en la misma red',
    'tools': 'Estado y recuperación',
    'back': 'Atrás',
    'step': 'Conexión',
    'connectTitle': 'Vamos a conectar<br>tu televisor',
    'connectDesc':
      'Enciende el televisor e introduce su dirección IP.<br>La encontrarás en los ajustes de red del televisor.',
    'ip': 'Dirección IP del televisor',
    'port': 'Puerto',
    'ipHelp': 'Ajustes del televisor → Red → Conexión actual',
    'ipError': 'Introduce una dirección IPv4 válida, como 192.168.1.50.',
    'portError': 'El puerto debe estar entre 1 y 65535.',
    'prepare': 'Prepara el televisor',
    'dev': 'Activa Developer Mode',
    'devDesc':
      'Activa Dev Mode Status. El TV se reiniciará. Después, abre Developer Mode de nuevo.',
    'keyServer': 'Activa Key Server',
    'keyServerDesc':
      'Activa Key Server y deja Developer Mode abierto. Introduce su IP Address como dirección del TV en CYTV.',
    'wifiTip':
      'Mantén el teléfono y el televisor en la misma red local. Desconecta la VPN durante la configuración.',
    'install': 'Revisar e instalar',
    'reviewFoot': 'Revisa las versiones de los paquetes antes de instalar',
    'password': 'Contraseña',
    'sshKey': 'Clave SSH',
    'importKey': 'Elegir archivo de clave',
    'keyImported': 'Clave SSH añadida',
    'keyPrivate': 'La clave se queda en este teléfono',
    'rootNotice':
      'Requiere acceso root ya configurado. CYTV no obtiene acceso root ni modifica el firmware del televisor.',
    'rootHint': 'Te pediremos la contraseña SSH al conectar.',
    'keyError': 'Primero elige el archivo de tu clave SSH privada.',
    'keyFailed': 'No se pudo leer la clave. Elige un archivo de hasta 64 KB.',
    'browserKey':
      'La importación de claves está disponible en la aplicación Android.',
    'progressTitle': 'Configurando<br>tu nuevo Home',
    'progressDesc':
      'Mantén el televisor encendido. CYTV comprobará la conexión y te guiará durante la instalación.',
    'statusTitle': 'Comprobando<br>tu televisor',
    'restoreTitle': 'Restaurando<br>LG Home',
    'progressFoot':
      'Puedes salir de la aplicación: verás el progreso en una notificación',
    'steps': [
      'Conexión y comprobaciones',
      'Aplicaciones del televisor',
      'Instalación de paquetes',
      'Configuración de Home'
    ],
    'log': 'Registro de la operación',
    'awaiting': 'Esperando al televisor…',
    'success': 'Tu nuevo Home<br>está listo para abrirse',
    'successDesc':
      'Prueba Home, las flechas y OK en el televisor. Después comprueba la salida de las aplicaciones y la entrada y salida del modo de espera.',
    'statusDone': 'Comprobación completada',
    'statusDoneDesc': 'Consulta los resultados en el registro de la operación.',
    'restored': 'LG Home restaurado',
    'restoredDesc': 'Prueba el botón Home del televisor.',
    'cancelled': 'Operación cancelada',
    'cancelledDesc':
      'Si la transferencia de paquetes ya había comenzado, comprueba el estado del televisor antes de volver a instalar.',
    'failed': 'No se pudo completar<br>la operación',
    'failedDesc':
      'La operación no se ha completado. Revisa el registro y comprueba el estado del televisor antes de reintentarlo.',
    'recoveryTitle': 'Volver a LG Home',
    'recoveryDesc':
      'Pulsa Home tres veces en dos segundos. En versiones antiguas de Helper hasta la 0.6.13 incluida, mantén pulsado Home durante dos segundos.',
    'three': '3 pulsaciones',
    'checkStatus': 'Comprobar estado',
    'restore': 'Restaurar LG Home',
    'toConnection': 'Volver a la conexión',
    'done': 'Volver al inicio',
    'trustTitle': '¿Es este tu televisor?',
    'trustDesc':
      'Compara esta huella SSH con la de una conexión de confianza, si dispones de ella. CYTV recordará el televisor y detendrá la conexión si su clave cambia.',
    'trust': 'Confiar y continuar',
    'cancel': 'Cancelar',
    'continue': 'Continuar',
    'secretTitle': 'Código de Developer Mode (Passphrase)',
    'secretDesc':
      'Introduce la Passphrase: los seis caracteres que muestra Developer Mode en el TV. Respeta mayúsculas y minúsculas. Usa el código del TV, no la contraseña de tu cuenta LG. Si no aparece el código, activa Key Server.',
    'rootSecretTitle': 'Contraseña SSH',
    'rootSecretDesc':
      'Introduce la contraseña SSH de acceso root que ya tiene el televisor.',
    'keySecretTitle': 'Contraseña de la clave SSH',
    'keySecretDesc': 'Introduce la contraseña que protege tu clave privada.',
    'secretLabel': 'Código / contraseña',
    'reviewTitle': 'Confirma esta acción',
    'reviewDesc':
      'Revisa los detalles del instalador. Continúa cuando estés listo.',
    'details': 'Detalles',
    'toolsTitle': 'Tu televisor,<br>bajo control',
    'toolsDesc': 'Comprueba la instalación o restaura LG Home de serie.',
    'statusTool': 'Estado de la instalación',
    'statusToolDesc': 'Comprobar paquetes y operaciones pendientes',
    'restoreToolDesc': 'Restaurar la pantalla Home original del televisor',
    'toolsConnect': 'Introduce la dirección del televisor para esta operación.',
    'check': 'Comprobar estado',
    'preview': 'Demostración de la interfaz · sin conexión al televisor',
    'previewOnly':
      'Esto es una vista previa de la interfaz. Instala el APK para conectarte al televisor.',
    'prepareService': 'Preparando el instalador…',
    'confirmRestore': '¿Restaurar LG Home?',
    'confirmRestoreDesc':
      'CYTV se conectará al televisor y te pedirá confirmar la recuperación. Las demás aplicaciones se conservarán.',
    'languageTitle': 'Idioma',
    'languageClose': 'Cerrar',
    'tvGreeting': 'Siéntete como en casa.',
    'tvSubtitle': 'Tus aplicaciones favoritas. Espacio para respirar.',
    'seconds': 's',
    'errorPrefix': 'Error',
    'replayError':
      'No se pudo restaurar la vista de la operación. Comprueba el estado del televisor.',
    'notificationText': 'Acción del televisor en curso',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Actualiza Android System WebView o Chrome y vuelve a abrir CYTV (se requiere WebView 108 o posterior).',
    'connectionMethod': 'Elige cómo conectarte',
    'maintenanceProgress':
      'Mantén el televisor encendido. CYTV está realizando la acción seleccionada.',
    'homeDiagnostics': 'Diagnóstico del botón Home',
    'homeDiagnosticsDesc':
      'Registra una pulsación de Home y guarda un informe. Solo Helper sin root.',
    'diagnosticProgress':
      'Cuando se indique, pulsa Home una vez. Mantén esta app abierta un minuto.',
    'saveReport': 'Guardar informe',
    'reportDone': 'Informe listo',
    'reportDoneDesc': 'Guarda el informe JSON y adjúntalo a tu incidencia.',
    'reportSaved': 'Informe guardado.',
    'reportError': 'No se pudo guardar el informe. Inténtalo de nuevo.',
    'devInstall': 'En el TV, abre LG Apps, busca Developer Mode e instálalo.',
    'devAccount':
      'Abre Developer Mode e inicia sesión con tu cuenta LG Developer. Si necesitas una, créala en webostv.developer.lge.com.',
    'sessionHelp':
      'Mantén Developer Mode activo: antes de que termine el tiempo, ábrelo y pulsa EXTEND con el TV conectado a Internet. Si caduca, LG puede eliminar estas apps.',
    'editionHelp':
      'No-root usa la app Developer Mode de LG. Root requiere acceso de administrador ya configurado en el TV.',
    'pairingHelp':
      'El emparejamiento es un paso aparte: cuando el TV lo pida, acepta CYTV con el mando.',
    'homeHelperHelp':
      'Home es tu pantalla de apps. Home Helper hace que el botón Home la abra.',
    'tryHomeHelp':
      'Tras instalar, pulsa Home para probarlo. Si se abre LG Home, abre Home Helper desde las apps del TV.',
    'resumeHomeHelp':
      'Pulsa Home brevemente tres veces en dos segundos para volver a LG Home. Para reiniciar el control de Home, abre Home Helper, elige Iniciar Helper y confirma. Se conserva tu pantalla Home elegida.',
    'guideExample': 'Ejemplo de LG',
    'guideNote':
      'Ejemplo de LG. La pantalla de tu TV puede ser diferente. Usa el código que aparece en tu propio TV.',
    'connectRoot': 'Conectar con Root',
    'recoveryReview': 'Revisar opciones de recuperación',
    'recoveryReviewDesc':
      'Comprueba una instalación interrumpida. Los cambios requieren otra confirmación.',
    'tvChecksReview': 'Revisar comprobaciones del TV',
    'homeObserved': 'Botón Home confirmado por ti',
    'tvChecksDesc':
      'La verificación de paquetes, el inicio y tu observación de Home son resultados separados.'
  },
  'pt-BR': {
    'tryAgain': 'Tentar novamente',
    'removalPending': 'A remoção ainda não terminou.',
    'restartRemoval': 'Reinicie a TV para concluir a remoção',
    'fullRestart':
      'Reinicie a TV por completo: desconecte da tomada, conecte novamente e escolha Tentar novamente. O modo de espera não é uma reinicialização completa.',
    'connectionInterrupted':
      'A conexão com a TV foi interrompida. Verifique a conexão e tente novamente.',
    'removalUnconfirmed':
      'Não foi possível confirmar a remoção. Verifique a conexão e tente novamente.',

    'uninstall': 'Desinstalar Clean Your TV',
    'uninstallDesc':
      'Remove os apps e seus dados de configuração. Exige confirmação separada.',

    'setupTV': 'Configurar TV',
    'wallpapers': 'Papéis de parede',
    'maintenance': 'Manutenção',
    'wallpaperInstructions':
      'Na TV, abra as configurações do Home → Papéis de parede → Enviar do celular. Leia o QR com a câmera, escolha JPG/PNG e aplique na TV.',
    'wallpaperLimit':
      'Pelo celular: imagens até 1920×1080, sem vídeo 4K nativo. Para 4K real, use CYTV no computador.',
    'detect': 'Verificar conexão',
    'detecting': 'Verificando acesso…',
    'detectedRoot':
      'Root SSH detectado. Os privilégios root serão verificados após o login.',
    'detectedDev':
      'Developer Mode detectado. No-root corresponde a esta conexão.',
    'detectedBoth':
      'As duas conexões estão disponíveis. Escolha o ambiente que você usa.',
    'detectedNone':
      'Nenhum acesso detectado. Verifique a TV, a rede e o modo de acesso ou escolha uma edição manualmente.',
    'connectionMatch': 'Conforme a conexão',
    'editionNext': 'Continuar',
    'android': 'para Android',
    'hero': 'Um novo Home.<br>Pelo seu celular.',
    'subtitle':
      'Configure o Clean Your TV no LG webOS.<br>Sem computador. Tudo aqui.',
    'choose': 'Escolha sua edição',
    'noRootDesc': 'Usa o Developer Mode da LG',
    'rootDesc': 'Acesso root e SSH já configurado',
    'connect': 'Conectar sua TV',
    'networkFoot': 'Celular e TV na mesma rede',
    'tools': 'Status e recuperação',
    'back': 'Voltar',
    'step': 'Conexão',
    'connectTitle': 'Vamos conectar<br>sua TV',
    'connectDesc':
      'Ligue a TV e informe o endereço IP dela.<br>Ele está nas configurações de rede da TV.',
    'ip': 'Endereço IP da TV',
    'port': 'Porta',
    'ipHelp': 'Configurações da TV → Rede → Conexão atual',
    'ipError': 'Informe um endereço IPv4 válido, como 192.168.1.50.',
    'portError': 'A porta deve estar entre 1 e 65535.',
    'prepare': 'Prepare sua TV',
    'dev': 'Ative o Developer Mode',
    'devDesc':
      'Ative Dev Mode Status. A TV reiniciará. Depois, abra Developer Mode novamente.',
    'keyServer': 'Ative o Key Server',
    'keyServerDesc':
      'Ative Key Server e deixe Developer Mode aberto. Use o IP Address exibido como endereço da TV no CYTV.',
    'wifiTip':
      'Mantenha o celular e a TV na mesma rede local. Desconecte a VPN durante a configuração.',
    'install': 'Revisar e instalar',
    'reviewFoot': 'Confira as versões dos pacotes antes de instalar',
    'password': 'Senha',
    'sshKey': 'Chave SSH',
    'importKey': 'Escolher arquivo de chave',
    'keyImported': 'Chave SSH adicionada',
    'keyPrivate': 'Sua chave fica apenas neste celular',
    'rootNotice':
      'Requer acesso root já configurado. O CYTV não faz root na TV nem altera o firmware.',
    'rootHint': 'Pediremos a senha SSH ao conectar.',
    'keyError': 'Primeiro, escolha o arquivo da sua chave SSH privada.',
    'keyFailed':
      'Não foi possível ler a chave. Escolha um arquivo de até 64 KB.',
    'browserKey':
      'A importação de chaves está disponível no aplicativo Android.',
    'progressTitle': 'Configurando<br>seu novo Home',
    'progressDesc':
      'Mantenha a TV ligada. O CYTV verificará a conexão e guiará você pela instalação.',
    'statusTitle': 'Verificando<br>sua TV',
    'restoreTitle': 'Restaurando<br>o LG Home',
    'progressFoot':
      'Você pode sair do aplicativo: o progresso fica na notificação',
    'steps': [
      'Conexão e verificações',
      'Aplicativos da TV',
      'Instalação dos pacotes',
      'Configuração do Home'
    ],
    'log': 'Registro da operação',
    'awaiting': 'Aguardando sua TV…',
    'success': 'Seu novo Home<br>está pronto para abrir',
    'successDesc':
      'Teste Home, as setas e OK na TV. Depois, confira a saída dos aplicativos e a entrada e saída do modo de espera.',
    'statusDone': 'Verificação concluída',
    'statusDoneDesc': 'Veja os resultados no registro da operação.',
    'restored': 'LG Home restaurado',
    'restoredDesc': 'Teste o botão Home da TV.',
    'cancelled': 'Operação cancelada',
    'cancelledDesc':
      'Se a transferência dos pacotes já começou, verifique o status da TV antes de instalar novamente.',
    'failed': 'Não foi possível concluir<br>a operação',
    'failedDesc':
      'A operação não foi concluída. Leia o registro e verifique o status da TV antes de tentar novamente.',
    'recoveryTitle': 'Voltar ao LG Home',
    'recoveryDesc':
      'Pressione Home três vezes em até dois segundos. Nas versões antigas do Helper até a 0.6.13 inclusive, segure Home por dois segundos.',
    'three': '3 toques',
    'checkStatus': 'Verificar status',
    'restore': 'Restaurar LG Home',
    'toConnection': 'Voltar à conexão',
    'done': 'Voltar ao início',
    'trustTitle': 'Esta é a sua TV?',
    'trustDesc':
      'Compare esta impressão digital SSH com a de uma conexão confiável, se disponível. O CYTV memoriza sua TV e interrompe a conexão se a chave mudar.',
    'trust': 'Confiar e continuar',
    'cancel': 'Cancelar',
    'continue': 'Continuar',
    'secretTitle': 'Código do Developer Mode (Passphrase)',
    'secretDesc':
      'Digite a Passphrase: os seis caracteres exibidos no Developer Mode da TV. Respeite maiúsculas e minúsculas. Use o código da TV, não a senha da sua conta LG. Se o código não aparecer, ative Key Server.',
    'rootSecretTitle': 'Senha SSH',
    'rootSecretDesc':
      'Informe a senha SSH do acesso root já configurado na TV.',
    'keySecretTitle': 'Senha da chave SSH',
    'keySecretDesc': 'Informe a senha que protege sua chave privada.',
    'secretLabel': 'Código / senha',
    'reviewTitle': 'Confirme esta ação',
    'reviewDesc':
      'Confira os detalhes do instalador. Continue quando estiver pronto.',
    'details': 'Detalhes',
    'toolsTitle': 'Sua TV,<br>sob controle',
    'toolsDesc': 'Verifique a instalação ou restaure o LG Home padrão.',
    'statusTool': 'Status da instalação',
    'statusToolDesc': 'Verificar pacotes e operações pendentes',
    'restoreToolDesc': 'Restaurar a tela Home original da TV',
    'toolsConnect': 'Informe o endereço da TV para esta operação.',
    'check': 'Verificar status',
    'preview': 'Demonstração da interface · sem conexão com a TV',
    'previewOnly':
      'Esta é uma prévia da interface. Instale o APK para conectar à TV.',
    'prepareService': 'Preparando o instalador…',
    'confirmRestore': 'Restaurar LG Home?',
    'confirmRestoreDesc':
      'O CYTV se conectará à TV e pedirá a confirmação da recuperação. Os outros aplicativos serão preservados.',
    'languageTitle': 'Idioma',
    'languageClose': 'Fechar',
    'tvGreeting': 'Sinta-se em casa.',
    'tvSubtitle': 'Seus aplicativos favoritos. Espaço para respirar.',
    'seconds': 's',
    'errorPrefix': 'Erro',
    'replayError':
      'Não foi possível restaurar a tela da operação. Verifique o status da TV.',
    'notificationText': 'Ação da TV em andamento',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Atualize o Android System WebView ou o Chrome e abra o CYTV novamente (requer WebView 108 ou superior).',
    'connectionMethod': 'Escolha como conectar',
    'maintenanceProgress':
      'Mantenha a TV ligada. O CYTV está executando a ação selecionada.',
    'homeDiagnostics': 'Diagnóstico do botão Home',
    'homeDiagnosticsDesc':
      'Grave um toque em Home e salve um relatório. Apenas Helper sem root.',
    'diagnosticProgress':
      'Quando solicitado, pressione Home uma vez. Mantenha este app aberto por um minuto.',
    'saveReport': 'Salvar relatório',
    'reportDone': 'Relatório pronto',
    'reportDoneDesc': 'Salve o relatório JSON e anexe ao seu chamado.',
    'reportSaved': 'Relatório salvo.',
    'reportError': 'Não foi possível salvar o relatório. Tente novamente.',
    'devInstall':
      'Na TV, abra LG Apps, procure Developer Mode e instale o app.',
    'devAccount':
      'Abra Developer Mode e entre com sua conta LG Developer. Se necessário, crie uma conta em webostv.developer.lge.com.',
    'sessionHelp':
      'Mantenha Developer Mode ativo: antes de o tempo acabar, abra o app e pressione EXTEND com a TV conectada à Internet. Se expirar, a LG pode remover esses apps.',
    'editionHelp':
      'No-root usa o app Developer Mode da LG. Root exige acesso de administrador já configurado na TV.',
    'pairingHelp':
      'O pareamento é uma etapa separada: quando a TV pedir, autorize o CYTV com o controle remoto.',
    'homeHelperHelp':
      'Home é sua tela de apps. Home Helper faz o botão Home abrir essa tela.',
    'tryHomeHelp':
      'Após instalar, pressione Home para testar. Se LG Home abrir, abra Home Helper na lista de apps da TV.',
    'resumeHomeHelp':
      'Pressione Home brevemente três vezes em dois segundos para voltar ao LG Home. Para reiniciar o controle de Home, abra Home Helper, escolha Iniciar Helper e confirme. Sua tela Home escolhida será mantida.',
    'guideExample': 'Exemplo da LG',
    'guideNote':
      'Exemplo da LG. A tela da sua TV pode ser diferente. Use o código exibido na sua própria TV.',
    'connectRoot': 'Conectar com Root',
    'recoveryReview': 'Revisar opções de recuperação',
    'recoveryReviewDesc':
      'Verifique uma instalação interrompida. Alterações exigem confirmação separada.',
    'tvChecksReview': 'Revisar verificações da TV',
    'homeObserved': 'Botão Home confirmado por você',
    'tvChecksDesc':
      'Verificação de pacotes, inicialização e sua observação de Home são resultados separados.'
  },
  'pl': {
    'tryAgain': 'Spróbuj ponownie',
    'removalPending': 'Usuwanie nie zostało jeszcze zakończone.',
    'restartRemoval': 'Uruchom TV ponownie, aby zakończyć usuwanie',
    'fullRestart':
      'Uruchom TV całkowicie ponownie: odłącz zasilanie, podłącz je ponownie i wybierz Spróbuj ponownie. Czuwanie nie jest pełnym restartem.',
    'connectionInterrupted':
      'Połączenie z TV zostało przerwane. Sprawdź połączenie i spróbuj ponownie.',
    'removalUnconfirmed':
      'Nie można potwierdzić usunięcia. Sprawdź połączenie i spróbuj ponownie.',

    'uninstall': 'Odinstaluj Clean Your TV',
    'uninstallDesc':
      'Usuń aplikacje i ich dane konfiguracji. Wymaga osobnego potwierdzenia.',

    'setupTV': 'Skonfiguruj TV',
    'wallpapers': 'Tapety',
    'maintenance': 'Konserwacja',
    'wallpaperInstructions':
      'Na TV otwórz ustawienia Home → Tapety → Prześlij z telefonu. Zeskanuj QR aparatem, wybierz JPG/PNG i zastosuj tapetę na TV.',
    'wallpaperLimit':
      'Z telefonu: obrazy do 1920×1080, bez natywnego wideo 4K. Aby uzyskać prawdziwe 4K, użyj CYTV na komputerze.',
    'detect': 'Sprawdź połączenie',
    'detecting': 'Sprawdzanie dostępu…',
    'detectedRoot':
      'Wykryto Root SSH. Uprawnienia root zostaną sprawdzone po zalogowaniu.',
    'detectedDev': 'Wykryto Developer Mode. Do tego połączenia pasuje No-root.',
    'detectedBoth':
      'Oba połączenia są dostępne. Wybierz środowisko, z którego korzystasz.',
    'detectedNone':
      'Nie wykryto dostępu. Sprawdź telewizor, sieć i tryb dostępu lub wybierz edycję ręcznie.',
    'connectionMatch': 'Według połączenia',
    'editionNext': 'Dalej',
    'android': 'na Androida',
    'hero': 'Nowy Home.<br>Z Twojego telefonu.',
    'subtitle':
      'Skonfiguruj Clean Your TV na LG webOS.<br>Bez komputera. Wszystko pod ręką.',
    'choose': 'Wybierz edycję',
    'noRootDesc': 'Korzysta z Developer Mode od LG',
    'rootDesc': 'Skonfigurowany dostęp root i SSH',
    'connect': 'Połącz telewizor',
    'networkFoot': 'Telefon i telewizor w tej samej sieci',
    'tools': 'Stan i przywracanie',
    'back': 'Wstecz',
    'step': 'Połączenie',
    'connectTitle': 'Połączmy się<br>z telewizorem',
    'connectDesc':
      'Włącz telewizor i wpisz jego adres IP.<br>Znajdziesz go w ustawieniach sieci telewizora.',
    'ip': 'Adres IP telewizora',
    'port': 'Port',
    'ipHelp': 'Ustawienia telewizora → Sieć → Bieżące połączenie',
    'ipError': 'Wpisz prawidłowy adres IPv4, np. 192.168.1.50.',
    'portError': 'Port musi być z zakresu od 1 do 65535.',
    'prepare': 'Przygotuj telewizor',
    'dev': 'Włącz Developer Mode',
    'devDesc':
      'Włącz Dev Mode Status. TV uruchomi się ponownie. Następnie otwórz ponownie Developer Mode.',
    'keyServer': 'Włącz Key Server',
    'keyServerDesc':
      'Włącz Key Server i pozostaw Developer Mode otwarty. Wpisz widoczny IP Address jako adres TV w CYTV.',
    'wifiTip':
      'Telefon i telewizor muszą być w tej samej sieci lokalnej. Na czas konfiguracji rozłącz VPN.',
    'install': 'Sprawdź i zainstaluj',
    'reviewFoot': 'Sprawdź wersje pakietów przed instalacją',
    'password': 'Hasło',
    'sshKey': 'Klucz SSH',
    'importKey': 'Wybierz plik klucza',
    'keyImported': 'Dodano klucz SSH',
    'keyPrivate': 'Klucz pozostaje tylko na tym telefonie',
    'rootNotice':
      'Wymaga już skonfigurowanego dostępu root. CYTV nie uzyskuje uprawnień root ani nie zmienia oprogramowania układowego telewizora.',
    'rootHint': 'Podczas łączenia poprosimy o hasło SSH.',
    'keyError': 'Najpierw wybierz plik prywatnego klucza SSH.',
    'keyFailed':
      'Nie można odczytać klucza. Wybierz plik o rozmiarze do 64 KB.',
    'browserKey': 'Import klucza jest dostępny w aplikacji na Androida.',
    'progressTitle': 'Konfigurowanie<br>nowego Home',
    'progressDesc':
      'Nie wyłączaj telewizora. CYTV sprawdzi połączenie i przeprowadzi Cię przez instalację.',
    'statusTitle': 'Sprawdzanie<br>telewizora',
    'restoreTitle': 'Przywracanie<br>LG Home',
    'progressFoot':
      'Możesz wyjść z aplikacji: postęp będzie widoczny w powiadomieniu',
    'steps': [
      'Połączenie i sprawdzenie',
      'Aplikacje telewizora',
      'Instalacja pakietów',
      'Konfiguracja Home'
    ],
    'log': 'Dziennik operacji',
    'awaiting': 'Oczekiwanie na telewizor…',
    'success': 'Nowy Home<br>jest gotowy do uruchomienia',
    'successDesc':
      'Sprawdź Home, strzałki i OK na telewizorze. Następnie sprawdź wychodzenie z aplikacji oraz przechodzenie w tryb czuwania i wybudzanie.',
    'statusDone': 'Sprawdzanie zakończone',
    'statusDoneDesc': 'Wyniki sprawdzenia znajdziesz w dzienniku operacji.',
    'restored': 'Przywrócono LG Home',
    'restoredDesc': 'Sprawdź przycisk Home na telewizorze.',
    'cancelled': 'Operacja anulowana',
    'cancelledDesc':
      'Jeśli przesyłanie pakietów już się rozpoczęło, sprawdź stan telewizora przed ponowną instalacją.',
    'failed': 'Nie udało się zakończyć<br>operacji',
    'failedDesc':
      'Operacja nie została ukończona. Przejrzyj dziennik i sprawdź stan telewizora przed ponowną próbą.',
    'recoveryTitle': 'Powrót do LG Home',
    'recoveryDesc':
      'Naciśnij Home trzy razy w ciągu dwóch sekund. W starszych wersjach Helper do 0.6.13 włącznie przytrzymaj Home przez dwie sekundy.',
    'three': '3 naciśnięcia',
    'checkStatus': 'Sprawdź stan',
    'restore': 'Przywróć LG Home',
    'toConnection': 'Wróć do połączenia',
    'done': 'Wróć na początek',
    'trustTitle': 'Czy to Twój telewizor?',
    'trustDesc':
      'Porównaj ten odcisk klucza SSH z zaufanym połączeniem, jeśli jest dostępne. CYTV zapamięta telewizor i przerwie połączenie, jeśli jego klucz się zmieni.',
    'trust': 'Zaufaj i kontynuuj',
    'cancel': 'Anuluj',
    'continue': 'Dalej',
    'secretTitle': 'Kod Developer Mode (Passphrase)',
    'secretDesc':
      'Wpisz Passphrase: sześć znaków widocznych w Developer Mode na TV. Zachowaj wielkość liter. Użyj kodu z TV, a nie hasła konta LG. Jeśli kodu nie widać, włącz Key Server.',
    'rootSecretTitle': 'Hasło SSH',
    'rootSecretDesc': 'Wpisz istniejące hasło SSH dostępu root do telewizora.',
    'keySecretTitle': 'Hasło klucza SSH',
    'keySecretDesc': 'Wpisz hasło chroniące Twój klucz prywatny.',
    'secretLabel': 'Kod / hasło',
    'reviewTitle': 'Potwierdź działanie',
    'reviewDesc':
      'Sprawdź szczegóły od instalatora. Kontynuuj, gdy wszystko będzie gotowe.',
    'details': 'Szczegóły',
    'toolsTitle': 'Twój telewizor<br>pod kontrolą',
    'toolsDesc': 'Sprawdź instalację lub przywróć standardowy LG Home.',
    'statusTool': 'Stan instalacji',
    'statusToolDesc': 'Sprawdź pakiety i niedokończone operacje',
    'restoreToolDesc': 'Przywróć oryginalny ekran Home telewizora',
    'toolsConnect': 'Wpisz adres telewizora dla tej operacji.',
    'check': 'Sprawdź stan',
    'preview': 'Prezentacja interfejsu · bez połączenia z telewizorem',
    'previewOnly':
      'To podgląd interfejsu. Zainstaluj APK, aby połączyć się z telewizorem.',
    'prepareService': 'Przygotowywanie instalatora…',
    'confirmRestore': 'Przywrócić LG Home?',
    'confirmRestoreDesc':
      'CYTV połączy się z telewizorem i poprosi o potwierdzenie przywracania. Inne aplikacje zostaną zachowane.',
    'languageTitle': 'Język',
    'languageClose': 'Zamknij',
    'tvGreeting': 'Czuj się jak u siebie.',
    'tvSubtitle': 'Twoje ulubione aplikacje. Więcej przestrzeni.',
    'seconds': 's',
    'errorPrefix': 'Błąd',
    'replayError':
      'Nie można przywrócić widoku operacji. Sprawdź stan telewizora.',
    'notificationText': 'Trwa działanie na telewizorze',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Zaktualizuj Android System WebView lub Chrome i ponownie otwórz CYTV (wymagany WebView 108 lub nowszy).',
    'connectionMethod': 'Wybierz sposób połączenia',
    'maintenanceProgress':
      'Pozostaw telewizor włączony. CYTV wykonuje wybrane działanie.',
    'homeDiagnostics': 'Diagnostyka przycisku Home',
    'homeDiagnosticsDesc':
      'Zapisz jedno naciśnięcie Home i jeden raport. Tylko Helper bez roota.',
    'diagnosticProgress':
      'Po wyświetleniu instrukcji naciśnij Home raz. Pozostaw aplikację otwartą przez minutę.',
    'saveReport': 'Zapisz raport',
    'reportDone': 'Raport gotowy',
    'reportDoneDesc': 'Zapisz raport JSON i dołącz go do zgłoszenia.',
    'reportSaved': 'Raport zapisany.',
    'reportError': 'Nie udało się zapisać raportu. Spróbuj ponownie.',
    'devInstall':
      'Na TV otwórz LG Apps, wyszukaj Developer Mode i zainstaluj aplikację.',
    'devAccount':
      'Otwórz Developer Mode i zaloguj się na konto LG Developer. W razie potrzeby utwórz konto na webostv.developer.lge.com.',
    'sessionHelp':
      'Utrzymuj Developer Mode aktywny: przed końcem odliczania otwórz aplikację i naciśnij EXTEND, gdy TV ma internet. Po wygaśnięciu LG może usunąć te aplikacje.',
    'editionHelp':
      'No-root korzysta z aplikacji Developer Mode firmy LG. Root wymaga wcześniej skonfigurowanego dostępu administratora do TV.',
    'pairingHelp':
      'Parowanie to osobny krok: gdy TV zapyta, zatwierdź CYTV pilotem.',
    'homeHelperHelp':
      'Home to ekran aplikacji. Home Helper sprawia, że przycisk Home otwiera ten ekran.',
    'tryHomeHelp':
      'Po instalacji naciśnij Home, aby sprawdzić działanie. Jeśli otworzy się LG Home, otwórz Home Helper z listy aplikacji TV.',
    'resumeHomeHelp':
      'Trzy krótkie naciśnięcia Home w ciągu dwóch sekund przywracają LG Home. Aby wznowić sterowanie Home, otwórz Home Helper, wybierz Uruchom Helper i potwierdź. Zapisany wybór ekranu Home zostaje zachowany.',
    'guideExample': 'Przykład LG',
    'guideNote':
      'Przykład LG. Ekran Twojego TV może wyglądać inaczej. Użyj kodu widocznego na własnym TV.',
    'connectRoot': 'Połącz przez Root',
    'recoveryReview': 'Sprawdź opcje odzyskiwania',
    'recoveryReviewDesc':
      'Sprawdź przerwaną konfigurację. Zmiany wymagają osobnego potwierdzenia.',
    'tvChecksReview': 'Przejrzyj kontrole TV',
    'homeObserved': 'Przycisk Home potwierdzony przez Ciebie',
    'tvChecksDesc':
      'Weryfikacja pakietów, odczyt startu i Twoja obserwacja Home to osobne wyniki.'
  },
  'ko': {
    'tryAgain': '다시 시도',
    'removalPending': '제거가 아직 완료되지 않았습니다.',
    'restartRemoval': '제거를 완료하려면 TV를 다시 시작하세요',
    'fullRestart':
      'TV를 완전히 다시 시작하세요. 전원을 분리했다가 다시 연결한 후 다시 시도를 선택하세요. 대기 모드는 완전한 재시작이 아닙니다.',
    'connectionInterrupted':
      'TV 연결이 끊겼습니다. 연결을 확인하고 다시 시도하세요.',
    'removalUnconfirmed':
      '제거를 확인할 수 없습니다. 연결을 확인하고 다시 시도하세요.',

    'uninstall': 'Clean Your TV 제거',
    'uninstallDesc':
      '앱과 해당 설정 데이터를 제거합니다. 별도 확인이 필요합니다.',

    'setupTV': 'TV 설정',
    'wallpapers': '배경화면',
    'maintenance': '유지 관리',
    'wallpaperInstructions':
      'TV에서 Home 설정 → 배경화면 → 휴대전화에서 업로드를 여세요. 휴대전화 카메라로 QR 코드를 스캔하고 JPG/PNG를 선택한 후 TV에서 적용하세요.',
    'wallpaperLimit':
      '휴대전화: 최대 1920×1080 이미지이며 네이티브 4K 동영상은 지원하지 않습니다. 실제 4K는 컴퓨터의 CYTV를 사용하세요.',
    'detect': '연결 확인',
    'detecting': '접근 가능 여부 확인 중…',
    'detectedRoot':
      'Root SSH가 감지되었습니다. 로그인 후 root 권한을 확인합니다.',
    'detectedDev':
      'Developer Mode가 감지되었습니다. 이 연결에는 No-root가 적합합니다.',
    'detectedBoth':
      '두 연결 모두 사용할 수 있습니다. 사용 중인 환경을 선택하세요.',
    'detectedNone':
      '접근 가능한 연결을 찾지 못했습니다. TV, 네트워크와 접근 모드를 확인하거나 에디션을 직접 선택하세요.',
    'connectionMatch': '연결에 맞는 에디션',
    'editionNext': '계속',
    'android': 'Android용',
    'hero': '새로운 Home.<br>휴대폰에서 바로.',
    'subtitle':
      'LG webOS에 Clean Your TV를 설정하세요.<br>컴퓨터 없이 여기서 모두.',
    'choose': '에디션 선택',
    'noRootDesc': 'LG Developer Mode 사용',
    'rootDesc': '기존 root 및 SSH 접근 권한 사용',
    'connect': 'TV 연결',
    'networkFoot': '휴대폰과 TV를 같은 네트워크에 연결하세요',
    'tools': '상태 및 복구',
    'back': '뒤로',
    'step': '연결',
    'connectTitle': 'TV에<br>연결해 볼까요',
    'connectDesc':
      'TV를 켜고 IP 주소를 입력하세요.<br>TV의 네트워크 설정에서 확인할 수 있습니다.',
    'ip': 'TV IP 주소',
    'port': '포트',
    'ipHelp': 'TV 설정 → 네트워크 → 현재 연결',
    'ipError': '올바른 IPv4 주소를 입력하세요. 예: 192.168.1.50',
    'portError': '포트는 1~65535 사이여야 합니다.',
    'prepare': 'TV 준비',
    'dev': 'Developer Mode 켜기',
    'devDesc':
      'Dev Mode Status를 켜세요. TV가 재시작되면 Developer Mode를 다시 여세요.',
    'keyServer': 'Key Server 켜기',
    'keyServerDesc':
      'Key Server를 켜고 Developer Mode를 열어 두세요. 표시된 IP Address를 CYTV의 TV 주소로 입력하세요.',
    'wifiTip':
      '휴대폰과 TV를 같은 로컬 네트워크에 연결하세요. 설정하는 동안 VPN 연결을 끊으세요.',
    'install': '검토 후 설치',
    'reviewFoot': '설치 전에 패키지 버전을 확인하세요',
    'password': '비밀번호',
    'sshKey': 'SSH 키',
    'importKey': '키 파일 선택',
    'keyImported': 'SSH 키가 추가되었습니다',
    'keyPrivate': '키는 이 휴대폰에만 저장됩니다',
    'rootNotice':
      '기존 root 접근 권한이 필요합니다. CYTV는 TV를 루팅하거나 펌웨어를 변경하지 않습니다.',
    'rootHint': '연결할 때 SSH 비밀번호를 요청합니다.',
    'keyError': '먼저 SSH 개인 키 파일을 선택하세요.',
    'keyFailed': '키를 읽을 수 없습니다. 64KB 이하의 파일을 선택하세요.',
    'browserKey': '키 가져오기는 Android 앱에서 사용할 수 있습니다.',
    'progressTitle': '새로운 Home을<br>설정하는 중',
    'progressDesc':
      'TV를 끄지 마세요. CYTV가 연결을 확인하고 설치를 안내합니다.',
    'statusTitle': 'TV<br>확인 중',
    'restoreTitle': 'LG Home<br>복원 중',
    'progressFoot': '앱을 나가도 알림에서 진행 상황을 확인할 수 있습니다',
    'steps': ['연결 및 확인', 'TV 앱', '패키지 설치', 'Home 설정'],
    'log': '작업 로그',
    'awaiting': 'TV 응답을 기다리는 중…',
    'success': '새로운 Home을<br>실행할 준비가 되었습니다',
    'successDesc':
      'TV에서 Home, 방향키와 OK를 확인하세요. 이어서 앱 종료와 대기 모드 전환 및 해제를 확인하세요.',
    'statusDone': '확인 완료',
    'statusDoneDesc': '작업 로그에서 확인 결과를 볼 수 있습니다.',
    'restored': 'LG Home이 복원되었습니다',
    'restoredDesc': 'TV의 Home 버튼을 확인하세요.',
    'cancelled': '작업이 취소되었습니다',
    'cancelledDesc':
      '패키지 전송이 이미 시작되었다면 다시 설치하기 전에 TV 상태를 확인하세요.',
    'failed': '작업을 완료할 수<br>없습니다',
    'failedDesc':
      '작업이 완료되지 않았습니다. 다시 시도하기 전에 로그와 TV 상태를 확인하세요.',
    'recoveryTitle': 'LG Home으로 돌아가기',
    'recoveryDesc':
      '2초 안에 Home을 세 번 누르세요. 0.6.13 이하의 이전 Helper 버전에서는 Home을 2초간 길게 누르세요.',
    'three': '3회 누르기',
    'checkStatus': '상태 확인',
    'restore': 'LG Home 복원',
    'toConnection': '연결 화면으로',
    'done': '처음으로',
    'trustTitle': '사용자의 TV가 맞나요?',
    'trustDesc':
      '신뢰할 수 있는 연결의 SSH 지문이 있다면 비교하세요. CYTV는 TV를 기억하고 키가 변경되면 연결을 중단합니다.',
    'trust': '신뢰하고 계속',
    'cancel': '취소',
    'continue': '계속',
    'secretTitle': 'Developer Mode 코드 (Passphrase)',
    'secretDesc':
      'TV의 Developer Mode에 표시된 6자리 Passphrase를 입력하세요. 대소문자를 구분하세요. LG 계정 비밀번호가 아닌 TV 화면의 코드를 사용하세요. 코드가 보이지 않으면 Key Server를 켜세요.',
    'rootSecretTitle': 'SSH 비밀번호',
    'rootSecretDesc': 'TV의 기존 root SSH 비밀번호를 입력하세요.',
    'keySecretTitle': 'SSH 키 암호',
    'keySecretDesc': '개인 키를 보호하는 암호를 입력하세요.',
    'secretLabel': '코드 / 비밀번호',
    'reviewTitle': '작업 확인',
    'reviewDesc':
      '설치 프로그램이 제공하는 세부 정보를 확인하세요. 준비되면 계속하세요.',
    'details': '세부 정보',
    'toolsTitle': '내 TV를<br>내 손안에',
    'toolsDesc': '설치 상태를 확인하거나 기본 LG Home을 복원하세요.',
    'statusTool': '설치 상태',
    'statusToolDesc': '패키지와 미완료 작업 확인',
    'restoreToolDesc': 'TV의 원래 Home 화면 복원',
    'toolsConnect': '이 작업을 수행할 TV의 주소를 입력하세요.',
    'check': '상태 확인',
    'preview': '인터페이스 데모 · TV에 연결되지 않음',
    'previewOnly': 'UI 미리 보기입니다. TV에 연결하려면 APK를 설치하세요.',
    'prepareService': '설치 프로그램 준비 중…',
    'confirmRestore': 'LG Home을 복원할까요?',
    'confirmRestoreDesc':
      'CYTV가 TV에 연결하여 복구 확인을 요청합니다. 다른 앱은 유지됩니다.',
    'languageTitle': '언어',
    'languageClose': '닫기',
    'tvGreeting': '편안하게 즐기세요.',
    'tvSubtitle': '좋아하는 앱만. 여유롭게.',
    'seconds': '초',
    'errorPrefix': '오류',
    'replayError': '작업 화면을 복원할 수 없습니다. TV 상태를 확인하세요.',
    'notificationText': 'TV 작업 진행 중',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Android System WebView 또는 Chrome을 업데이트한 후 CYTV를 다시 여세요(WebView 108 이상 필요).',
    'connectionMethod': '연결 방법 선택',
    'maintenanceProgress':
      'TV를 켜 두세요. CYTV가 선택한 작업을 실행하고 있습니다.',
    'homeDiagnostics': 'Home 버튼 진단',
    'homeDiagnosticsDesc':
      'Home 누르기를 기록하고 보고서 하나를 저장합니다. No-root Helper 전용입니다.',
    'diagnosticProgress':
      '안내가 나오면 Home을 한 번 누르세요. 앱을 1분 동안 열어 두세요.',
    'saveReport': '보고서 저장',
    'reportDone': '보고서 준비 완료',
    'reportDoneDesc': 'JSON 보고서를 저장하고 이슈에 첨부하세요.',
    'reportSaved': '보고서를 저장했습니다.',
    'reportError': '보고서를 저장하지 못했습니다. 다시 시도하세요.',
    'devInstall': 'TV에서 LG Apps를 열고 Developer Mode를 검색하여 설치하세요.',
    'devAccount':
      'Developer Mode를 열고 LG Developer 계정으로 로그인하세요. 계정이 없으면 webostv.developer.lge.com에서 만드세요.',
    'sessionHelp':
      '타이머가 끝나기 전에 Developer Mode를 열고 TV가 인터넷에 연결된 상태에서 EXTEND를 누르세요. 만료되면 LG가 이 앱들을 삭제할 수 있습니다.',
    'editionHelp':
      'No-root는 LG의 Developer Mode 앱을 사용합니다. Root는 TV에 관리자 접근이 미리 설정되어 있어야 합니다.',
    'pairingHelp':
      '페어링은 별도 단계입니다. TV에서 요청하면 리모컨으로 CYTV를 승인하세요.',
    'homeHelperHelp':
      'Home은 앱 화면입니다. Home Helper를 사용하면 Home 버튼으로 이 화면을 열 수 있습니다.',
    'tryHomeHelp':
      '설치 후 Home 버튼을 눌러 보세요. LG Home이 열리면 TV 앱 목록에서 Home Helper를 여세요.',
    'resumeHomeHelp':
      '2초 안에 Home 버튼을 짧게 세 번 누르면 LG Home으로 돌아갑니다. Home 제어를 다시 시작하려면 Home Helper를 열고 Helper 시작을 선택한 다음 확인하세요. 저장된 Home 화면 선택은 유지됩니다.',
    'guideExample': 'LG 예시 화면',
    'guideNote':
      'LG 예시 화면입니다. TV에 따라 화면이 다를 수 있습니다. 자신의 TV에 표시된 코드를 사용하세요.',
    'connectRoot': 'Root로 연결',
    'recoveryReview': '복구 옵션 확인',
    'recoveryReviewDesc':
      '중단된 설정을 확인합니다. 변경하려면 별도로 확인해야 합니다.',
    'tvChecksReview': 'TV 확인 결과 검토',
    'homeObserved': '사용자가 Home 버튼 확인',
    'tvChecksDesc':
      '패키지 검증, 시작 확인, Home 버튼 관찰은 별도의 결과입니다.'
  },
  'hi': {
    'tryAgain': 'फिर कोशिश करें',
    'removalPending': 'हटाना अभी पूरा नहीं हुआ है।',
    'restartRemoval': 'हटाना पूरा करने के लिए TV पुनः शुरू करें',
    'fullRestart':
      'TV पूरी तरह पुनः शुरू करें: बिजली से अलग करें, फिर जोड़ें और फिर कोशिश करें चुनें। स्टैंडबाय पूर्ण पुनः आरंभ नहीं है।',
    'connectionInterrupted':
      'TV से कनेक्शन टूट गया। कनेक्शन जाँचें और फिर कोशिश करें।',
    'removalUnconfirmed':
      'हटाने की पुष्टि नहीं हुई। कनेक्शन जाँचें और फिर कोशिश करें।',

    'uninstall': 'Clean Your TV हटाएं',
    'uninstallDesc': 'ऐप और उनका सेटअप डेटा हटाएँ। अलग पुष्टि आवश्यक है।',

    'setupTV': 'टीवी सेट करें',
    'wallpapers': 'वॉलपेपर',
    'maintenance': 'रखरखाव',
    'wallpaperInstructions':
      'टीवी पर Home सेटिंग → वॉलपेपर → फ़ोन से अपलोड खोलें। फ़ोन कैमरे से QR स्कैन करें, JPG/PNG चुनें और टीवी पर लागू करें।',
    'wallpaperLimit':
      'फ़ोन से: 1920×1080 तक की तस्वीरें, नेटिव 4K वीडियो नहीं। असली 4K के लिए कंप्यूटर पर CYTV इस्तेमाल करें।',
    'detect': 'कनेक्शन जाँचें',
    'detecting': 'ऐक्सेस जाँचा जा रहा है…',
    'detectedRoot':
      'Root SSH मिला। साइन इन के बाद root अनुमतियाँ जाँची जाएँगी।',
    'detectedDev': 'Developer Mode मिला। इस कनेक्शन के लिए No-root उपयुक्त है।',
    'detectedBoth':
      'दोनों कनेक्शन उपलब्ध हैं। अपना उपयोग किया जाने वाला परिवेश चुनें।',
    'detectedNone':
      'ऐक्सेस नहीं मिला। TV, नेटवर्क और ऐक्सेस मोड जाँचें या संस्करण खुद चुनें।',
    'connectionMatch': 'कनेक्शन के अनुसार',
    'editionNext': 'आगे बढ़ें',
    'android': 'Android के लिए',
    'hero': 'नया Home।<br>अपने फ़ोन से।',
    'subtitle':
      'LG webOS पर Clean Your TV सेट अप करें।<br>बिना कंप्यूटर। सब कुछ यहीं।',
    'choose': 'अपना संस्करण चुनें',
    'noRootDesc': 'LG Developer Mode के ज़रिए',
    'rootDesc': 'पहले से मौजूद root और SSH ऐक्सेस',
    'connect': 'अपना TV कनेक्ट करें',
    'networkFoot': 'फ़ोन और TV एक ही नेटवर्क पर हों',
    'tools': 'स्थिति और रिकवरी',
    'back': 'वापस',
    'step': 'कनेक्शन',
    'connectTitle': 'अपने TV से<br>कनेक्ट करें',
    'connectDesc':
      'TV चालू करें और उसका IP पता डालें।<br>यह TV की नेटवर्क सेटिंग में मिलेगा।',
    'ip': 'TV का IP पता',
    'port': 'पोर्ट',
    'ipHelp': 'TV सेटिंग → नेटवर्क → मौजूदा कनेक्शन',
    'ipError': 'सही IPv4 पता डालें, जैसे 192.168.1.50।',
    'portError': 'पोर्ट 1 से 65535 के बीच होना चाहिए।',
    'prepare': 'अपना TV तैयार करें',
    'dev': 'Developer Mode चालू करें',
    'devDesc':
      'Dev Mode Status चालू करें। TV फिर से शुरू होगा। उसके बाद Developer Mode दोबारा खोलें।',
    'keyServer': 'Key Server चालू करें',
    'keyServerDesc':
      'Key Server चालू करें और Developer Mode खुला रखें। वहाँ दिखा IP Address ही CYTV में डालने वाला TV का पता है।',
    'wifiTip':
      'फ़ोन और TV को एक ही स्थानीय नेटवर्क पर रखें। सेटअप के दौरान VPN डिस्कनेक्ट करें।',
    'install': 'जाँचें और इंस्टॉल करें',
    'reviewFoot': 'इंस्टॉल करने से पहले पैकेज के संस्करण देखें',
    'password': 'पासवर्ड',
    'sshKey': 'SSH कुंजी',
    'importKey': 'कुंजी फ़ाइल चुनें',
    'keyImported': 'SSH कुंजी जोड़ दी गई',
    'keyPrivate': 'आपकी कुंजी केवल इसी फ़ोन पर रहती है',
    'rootNotice':
      'पहले से मौजूद root ऐक्सेस ज़रूरी है। CYTV आपके TV को root नहीं करता और न ही उसका फ़र्मवेयर बदलता है।',
    'rootHint': 'कनेक्ट करते समय आपका SSH पासवर्ड माँगा जाएगा।',
    'keyError': 'पहले अपनी निजी SSH कुंजी की फ़ाइल चुनें।',
    'keyFailed': 'कुंजी पढ़ी नहीं जा सकी। अधिकतम 64 KB की फ़ाइल चुनें।',
    'browserKey': 'कुंजी इंपोर्ट करने की सुविधा Android ऐप में उपलब्ध है।',
    'progressTitle': 'आपका नया Home<br>सेट अप हो रहा है',
    'progressDesc':
      'TV चालू रखें। CYTV कनेक्शन जाँचेगा और इंस्टॉलेशन में आपका मार्गदर्शन करेगा।',
    'statusTitle': 'आपका TV<br>जाँचा जा रहा है',
    'restoreTitle': 'LG Home<br>बहाल हो रहा है',
    'progressFoot': 'आप ऐप से बाहर जा सकते हैं: प्रगति सूचना में दिखती रहेगी',
    'steps': ['कनेक्शन और जाँच', 'TV ऐप्स', 'पैकेज इंस्टॉलेशन', 'Home सेटअप'],
    'log': 'कार्रवाई का लॉग',
    'awaiting': 'TV के जवाब का इंतज़ार है…',
    'success': 'आपका नया Home<br>खुलने के लिए तैयार है',
    'successDesc':
      'TV पर Home, दिशा बटन और OK जाँचें। फिर ऐप से बाहर निकलना और स्टैंडबाय में जाना व उससे जागना जाँचें।',
    'statusDone': 'जाँच पूरी हुई',
    'statusDoneDesc': 'जाँच के नतीजे कार्रवाई के लॉग में देखें।',
    'restored': 'LG Home बहाल हो गया',
    'restoredDesc': 'अपने TV का Home बटन जाँचें।',
    'cancelled': 'कार्रवाई रद्द हुई',
    'cancelledDesc':
      'अगर पैकेज ट्रांसफ़र शुरू हो चुका था, तो दोबारा इंस्टॉल करने से पहले TV की स्थिति जाँचें।',
    'failed': 'कार्रवाई पूरी<br>नहीं हो सकी',
    'failedDesc':
      'कार्रवाई पूरी नहीं हुई। दोबारा कोशिश करने से पहले लॉग देखें और TV की स्थिति जाँचें।',
    'recoveryTitle': 'LG Home पर लौटें',
    'recoveryDesc':
      'दो सेकंड के भीतर Home को तीन बार दबाएँ। Helper के 0.6.13 तक के पुराने संस्करणों में Home को दो सेकंड तक दबाए रखें।',
    'three': '3 बार दबाएँ',
    'checkStatus': 'स्थिति जाँचें',
    'restore': 'LG Home बहाल करें',
    'toConnection': 'कनेक्शन पर वापस जाएँ',
    'done': 'शुरुआत पर जाएँ',
    'trustTitle': 'क्या यह आपका TV है?',
    'trustDesc':
      'अगर किसी विश्वसनीय कनेक्शन का SSH फ़िंगरप्रिंट उपलब्ध हो, तो उससे तुलना करें। CYTV आपके TV को याद रखता है और उसकी कुंजी बदलने पर कनेक्शन रोक देता है।',
    'trust': 'भरोसा करके आगे बढ़ें',
    'cancel': 'रद्द करें',
    'continue': 'आगे बढ़ें',
    'secretTitle': 'Developer Mode कोड (Passphrase)',
    'secretDesc':
      'TV के Developer Mode में दिखे छह अक्षरों वाला Passphrase डालें। बड़े और छोटे अक्षर जैसे दिखें वैसे ही लिखें। LG खाते का पासवर्ड नहीं, TV पर दिखा कोड डालें। कोड न दिखे तो Key Server चालू करें।',
    'rootSecretTitle': 'SSH पासवर्ड',
    'rootSecretDesc': 'अपने TV का मौजूदा root SSH पासवर्ड डालें।',
    'keySecretTitle': 'SSH कुंजी का पासफ़्रेज़',
    'keySecretDesc': 'अपनी निजी कुंजी को सुरक्षित रखने वाला पासफ़्रेज़ डालें।',
    'secretLabel': 'कोड / पासवर्ड',
    'reviewTitle': 'इस कार्रवाई की पुष्टि करें',
    'reviewDesc': 'इंस्टॉलर से मिली जानकारी जाँचें। तैयार होने पर आगे बढ़ें।',
    'details': 'विवरण',
    'toolsTitle': 'आपका TV,<br>आपके नियंत्रण में',
    'toolsDesc': 'इंस्टॉलेशन जाँचें या सामान्य LG Home बहाल करें।',
    'statusTool': 'इंस्टॉलेशन की स्थिति',
    'statusToolDesc': 'पैकेज और अधूरी कार्रवाइयाँ जाँचें',
    'restoreToolDesc': 'TV की मूल Home स्क्रीन बहाल करें',
    'toolsConnect': 'इस कार्रवाई के लिए अपने TV का पता डालें।',
    'check': 'स्थिति जाँचें',
    'preview': 'इंटरफ़ेस का डेमो · TV कनेक्ट नहीं है',
    'previewOnly':
      'यह UI का प्रीव्यू है। TV से कनेक्ट करने के लिए APK इंस्टॉल करें।',
    'prepareService': 'इंस्टॉलर तैयार हो रहा है…',
    'confirmRestore': 'LG Home बहाल करें?',
    'confirmRestoreDesc':
      'CYTV आपके TV से कनेक्ट होगा और रिकवरी की पुष्टि माँगेगा। दूसरे ऐप्स सुरक्षित रहेंगे।',
    'languageTitle': 'भाषा',
    'languageClose': 'बंद करें',
    'tvGreeting': 'आराम से आनंद लें।',
    'tvSubtitle': 'आपके पसंदीदा ऐप्स। सुकून के साथ।',
    'seconds': 'सेकंड',
    'errorPrefix': 'त्रुटि',
    'replayError': 'कार्रवाई की स्क्रीन बहाल नहीं हो सकी। TV की स्थिति जाँचें।',
    'notificationText': 'TV पर कार्रवाई जारी है',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      'Android System WebView या Chrome अपडेट करें, फिर CYTV दोबारा खोलें (WebView 108+ ज़रूरी है)।',
    'connectionMethod': 'कनेक्शन का तरीका चुनें',
    'maintenanceProgress': 'TV चालू रखें। CYTV चुनी गई कार्रवाई कर रहा है।',
    'homeDiagnostics': 'Home बटन की जाँच',
    'homeDiagnosticsDesc':
      'Home का एक प्रेस रिकॉर्ड करें और एक रिपोर्ट सेव करें। केवल No-root Helper के लिए।',
    'diagnosticProgress': 'कहने पर Home एक बार दबाएँ। यह ऐप एक मिनट खुला रखें।',
    'saveReport': 'रिपोर्ट सेव करें',
    'reportDone': 'रिपोर्ट तैयार है',
    'reportDoneDesc': 'JSON रिपोर्ट सेव करके अपनी समस्या के साथ संलग्न करें।',
    'reportSaved': 'रिपोर्ट सेव हो गई।',
    'reportError': 'रिपोर्ट सेव नहीं हुई। फिर कोशिश करें।',
    'devInstall': 'TV पर LG Apps खोलें, Developer Mode खोजें और इंस्टॉल करें।',
    'devAccount':
      'Developer Mode खोलें और अपने LG Developer खाते से साइन इन करें। ज़रूरत हो तो webostv.developer.lge.com पर खाता बनाएँ।',
    'sessionHelp':
      'Developer Mode चालू रखें: समय खत्म होने से पहले इसे खोलें और TV के इंटरनेट से जुड़े होने पर EXTEND दबाएँ। समय खत्म होने पर LG ये ऐप हटा सकता है।',
    'editionHelp':
      'No-root में LG का Developer Mode ऐप उपयोग होता है। Root के लिए TV पर व्यवस्थापक पहुँच पहले से सेट होनी चाहिए।',
    'pairingHelp':
      'पेयरिंग अलग चरण है: TV पर अनुरोध आने पर रिमोट से CYTV को अनुमति दें।',
    'homeHelperHelp':
      'Home आपके ऐप की स्क्रीन है। Home Helper से Home बटन दबाने पर यह स्क्रीन खुलती है।',
    'tryHomeHelp':
      'इंस्टॉल होने पर Home दबाकर देखें। LG Home खुले तो TV की ऐप सूची से Home Helper खोलें।',
    'resumeHomeHelp':
      'दो सेकंड में Home तीन बार छोटा दबाने से LG Home खुलता है। Home नियंत्रण फिर शुरू करने के लिए Home Helper खोलें, Helper शुरू करें चुनें और पुष्टि करें। चुनी हुई Home स्क्रीन बनी रहती है।',
    'guideExample': 'LG का उदाहरण',
    'guideNote':
      'यह LG का उदाहरण है। आपके TV की स्क्रीन अलग दिख सकती है। अपने TV पर दिखा कोड ही उपयोग करें।',
    'connectRoot': 'Root से कनेक्ट करें',
    'recoveryReview': 'पुनर्प्राप्ति विकल्प जाँचें',
    'recoveryReviewDesc':
      'रुके हुए सेटअप की जाँच करें। बदलाव के लिए अलग पुष्टि आवश्यक है।',
    'tvChecksReview': 'टीवी की जाँच देखें',
    'homeObserved': 'आपने Home बटन की पुष्टि की',
    'tvChecksDesc':
      'पैकेज सत्यापन, प्रारंभ जाँच और आपका Home अवलोकन अलग परिणाम हैं।'
  },
  'zh-Hans': {
    'tryAgain': '重试',
    'removalPending': '移除尚未完成。',
    'restartRemoval': '重启电视以完成移除',
    'fullRestart':
      '请完全重启电视：断开电源，重新连接，然后选择“重试”。待机不等于完全重启。',
    'connectionInterrupted': '与电视的连接已中断。请检查连接并重试。',
    'removalUnconfirmed': '无法确认移除。请检查连接并重试。',

    'uninstall': '卸载 Clean Your TV',
    'uninstallDesc': '移除应用及其设置数据。需要另行确认。',

    'setupTV': '设置电视',
    'wallpapers': '壁纸',
    'maintenance': '维护',
    'wallpaperInstructions':
      '在电视上打开 Home 设置 → 壁纸 → 从手机上传。用手机相机扫描二维码，选择 JPG/PNG，然后在电视上应用。',
    'wallpaperLimit':
      '手机上传：最高 1920×1080 的图片，不支持原生 4K 视频。真正的 4K 请使用电脑版 CYTV。',
    'detect': '检查连接',
    'detecting': '正在检查访问方式…',
    'detectedRoot': '已检测到 Root SSH。登录后将验证 root 权限。',
    'detectedDev': '已检测到 Developer Mode。此连接适合使用 No-root。',
    'detectedBoth': '两种连接均可用。请选择您使用的环境。',
    'detectedNone':
      '未检测到访问方式。请检查电视、网络及访问模式，或手动选择版本。',
    'connectionMatch': '适合此连接',
    'editionNext': '继续',
    'android': 'Android 版',
    'hero': '全新主屏幕。<br>手机轻松设置。',
    'subtitle': '在 LG webOS 上设置 Clean Your TV。<br>无需电脑，尽在手中。',
    'choose': '选择版本',
    'noRootDesc': '使用 LG Developer Mode',
    'rootDesc': '已有 root 权限和 SSH 访问权限',
    'connect': '连接电视',
    'networkFoot': '手机和电视须连接同一网络',
    'tools': '状态与恢复',
    'back': '返回',
    'step': '连接',
    'connectTitle': '连接<br>您的电视',
    'connectDesc': '打开电视并输入 IP 地址。<br>可在电视的网络设置中查看。',
    'ip': '电视 IP 地址',
    'port': '端口',
    'ipHelp': '电视设置 → 网络 → 当前连接',
    'ipError': '请输入有效的 IPv4 地址，例如 192.168.1.50。',
    'portError': '端口范围为 1 至 65535。',
    'prepare': '准备电视',
    'dev': '启用 Developer Mode',
    'devDesc':
      '开启 Dev Mode Status。电视将重启，然后请重新打开 Developer Mode。',
    'keyServer': '启用 Key Server',
    'keyServerDesc':
      '开启 Key Server 并保持 Developer Mode 打开。将其中的 IP Address 填入 CYTV 的电视地址栏。',
    'wifiTip': '请将手机和电视连接到同一局域网。设置期间请断开 VPN。',
    'install': '检查并安装',
    'reviewFoot': '安装前可查看软件包版本',
    'password': '密码',
    'sshKey': 'SSH 密钥',
    'importKey': '选择密钥文件',
    'keyImported': '已添加 SSH 密钥',
    'keyPrivate': '密钥仅保存在此手机上',
    'rootNotice':
      '需要已有 root 权限。CYTV 不会为电视获取 root 权限或更改固件。',
    'rootHint': '连接时会要求输入 SSH 密码。',
    'keyError': '请先选择 SSH 私钥文件。',
    'keyFailed': '无法读取密钥。请选择不超过 64 KB 的文件。',
    'browserKey': '密钥导入功能仅在 Android 应用中可用。',
    'progressTitle': '正在设置<br>您的新主屏幕',
    'progressDesc': '请保持电视开启。CYTV 将验证连接并引导您完成安装。',
    'statusTitle': '正在检查<br>您的电视',
    'restoreTitle': '正在恢复<br>LG Home',
    'progressFoot': '可以离开应用：通知中会显示进度',
    'steps': ['连接与检查', '电视应用', '软件包安装', '主屏幕设置'],
    'log': '操作日志',
    'awaiting': '正在等待电视响应…',
    'success': '您的新主屏幕<br>已准备就绪',
    'successDesc':
      '请在电视上测试 Home、方向键和 OK，再测试退出应用及待机/唤醒。',
    'statusDone': '检查完成',
    'statusDoneDesc': '请查看操作日志中的检查结果。',
    'restored': '已恢复 LG Home',
    'restoredDesc': '请测试电视的 Home 键。',
    'cancelled': '操作已取消',
    'cancelledDesc': '如果软件包已开始传输，请先检查电视状态，再重新安装。',
    'failed': '无法完成<br>此操作',
    'failedDesc': '操作未完成。请查看日志并检查电视状态，再重试。',
    'recoveryTitle': '返回 LG Home',
    'recoveryDesc':
      '在两秒内按三次 Home 键。对于 0.6.13 及更早版本的 Helper，请长按 Home 键两秒。',
    'three': '按 3 次',
    'checkStatus': '检查状态',
    'restore': '恢复 LG Home',
    'toConnection': '返回连接',
    'done': '返回首页',
    'trustTitle': '这是您的电视吗？',
    'trustDesc':
      '如有可信连接，请与其 SSH 指纹对比。CYTV 会记住您的电视，密钥发生变化时会停止连接。',
    'trust': '信任并继续',
    'cancel': '取消',
    'continue': '继续',
    'secretTitle': 'Developer Mode 代码（Passphrase）',
    'secretDesc':
      '输入电视上 Developer Mode 显示的六位 Passphrase，注意区分大小写。 请使用电视上的代码，而非 LG 账号密码。如未显示代码，请开启 Key Server。',
    'rootSecretTitle': 'SSH 密码',
    'rootSecretDesc': '请输入电视现有的 root SSH 密码。',
    'keySecretTitle': 'SSH 密钥口令',
    'keySecretDesc': '请输入用于保护私钥的口令。',
    'secretLabel': '代码 / 密码',
    'reviewTitle': '确认操作',
    'reviewDesc': '请查看安装程序提供的详细信息，准备好后继续。',
    'details': '详情',
    'toolsTitle': '您的电视，<br>尽在掌握',
    'toolsDesc': '检查安装状态，或恢复标准 LG Home。',
    'statusTool': '安装状态',
    'statusToolDesc': '检查软件包及未完成的操作',
    'restoreToolDesc': '恢复电视原有的主屏幕',
    'toolsConnect': '请输入电视地址以执行此操作。',
    'check': '检查状态',
    'preview': '界面演示 · 未连接电视',
    'previewOnly': '这是界面预览。请安装 APK 以连接电视。',
    'prepareService': '正在准备安装程序…',
    'confirmRestore': '恢复 LG Home？',
    'confirmRestoreDesc':
      'CYTV 将连接电视并请您确认恢复操作。其他应用将被保留。',
    'languageTitle': '语言',
    'languageClose': '关闭',
    'tvGreeting': '自在如家。',
    'tvSubtitle': '喜爱的应用，舒心的空间。',
    'seconds': '秒',
    'errorPrefix': '错误',
    'replayError': '无法恢复操作界面。请检查电视状态。',
    'notificationText': '电视操作进行中',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      '请更新 Android System WebView 或 Chrome，然后重新打开 CYTV（需要 WebView 108 或更高版本）。',
    'connectionMethod': '选择连接方式',
    'maintenanceProgress': '请保持电视开启。CYTV 正在执行所选操作。',
    'homeDiagnostics': 'Home 键诊断',
    'homeDiagnosticsDesc':
      '记录一次 Home 按键并保存报告。仅适用于 No-root Helper。',
    'diagnosticProgress':
      '看到提示后，请按一次 Home 键，并保持此应用开启一分钟。',
    'saveReport': '保存报告',
    'reportDone': '报告已就绪',
    'reportDoneDesc': '请保存 JSON 报告并附到您的问题报告中。',
    'reportSaved': '报告已保存。',
    'reportError': '无法保存报告，请重试。',
    'devInstall': '在电视上打开 LG Apps，搜索并安装 Developer Mode。',
    'devAccount':
      '打开 Developer Mode 并登录 LG Developer 账号。如需注册，请访问 webostv.developer.lge.com。',
    'sessionHelp':
      '请保持 Developer Mode 有效：计时结束前打开它，并在电视联网时按 EXTEND。过期后 LG 可能会删除这些应用。',
    'editionHelp':
      'No-root 使用 LG 的 Developer Mode 应用。Root 需要电视已配置管理员访问权限。',
    'pairingHelp': '配对是单独的步骤：电视提示时，请用遥控器允许 CYTV 连接。',
    'homeHelperHelp':
      'Home 是您的应用主屏幕。Home Helper 让遥控器的 Home 键打开此屏幕。',
    'tryHomeHelp':
      '安装后按 Home 键试用。如果打开的是 LG Home，请从电视应用列表中打开 Home Helper。',
    'resumeHomeHelp':
      '在两秒内短按 Home 三次可返回 LG Home。要重新启动 Home 控制，请打开 Home Helper，选择启动 Helper 并确认。已保存的主屏幕选择会保留。',
    'guideExample': 'LG 示例画面',
    'guideNote':
      'LG 示例画面。您的电视界面可能有所不同。请使用您自己电视上显示的代码。',
    'connectRoot': '通过 Root 连接',
    'recoveryReview': '检查恢复选项',
    'recoveryReviewDesc': '检查中断的安装。更改需要单独确认。',
    'tvChecksReview': '查看电视检查结果',
    'homeObserved': '您已确认 Home 按钮',
    'tvChecksDesc': '软件包验证、启动状态回读和您的 Home 按钮观察是不同结果。'
  },
  'zh-Hant': {
    'tryAgain': '重試',
    'removalPending': '移除尚未完成。',
    'restartRemoval': '重新啟動電視以完成移除',
    'fullRestart':
      '請完全重新啟動電視：斷開電源，重新連接，然後選擇「重試」。待機不等於完全重新啟動。',
    'connectionInterrupted': '與電視的連線已中斷。請檢查連線並重試。',
    'removalUnconfirmed': '無法確認移除。請檢查連線並重試。',

    'uninstall': '解除安裝 Clean Your TV',
    'uninstallDesc': '移除應用程式及其設定資料。需要另行確認。',

    'setupTV': '設定電視',
    'wallpapers': '桌布',
    'maintenance': '維護',
    'wallpaperInstructions':
      '在電視上開啟 Home 設定 → 桌布 → 從手機上傳。用手機相機掃描 QR 碼，選擇 JPG/PNG，然後在電視上套用。',
    'wallpaperLimit':
      '手機上傳：最高 1920×1080 的圖片，不支援原生 4K 影片。真正的 4K 請使用電腦版 CYTV。',
    'detect': '檢查連線',
    'detecting': '正在檢查存取方式…',
    'detectedRoot': '已偵測到 Root SSH。登入後將驗證 root 權限。',
    'detectedDev': '已偵測到 Developer Mode。此連線適合使用 No-root。',
    'detectedBoth': '兩種連線皆可用。請選擇您使用的環境。',
    'detectedNone':
      '未偵測到存取方式。請檢查電視、網路及存取模式，或手動選擇版本。',
    'connectionMatch': '適合此連線',
    'editionNext': '繼續',
    'android': 'Android 版',
    'hero': '全新主畫面。<br>手機輕鬆設定。',
    'subtitle': '在 LG webOS 上設定 Clean Your TV。<br>無需電腦，盡在手中。',
    'choose': '選擇版本',
    'noRootDesc': '使用 LG Developer Mode',
    'rootDesc': '已有 root 權限和 SSH 存取權限',
    'connect': '連接電視',
    'networkFoot': '手機和電視須連接同一網路',
    'tools': '狀態與還原',
    'back': '返回',
    'step': '連線',
    'connectTitle': '連接<br>您的電視',
    'connectDesc': '開啟電視並輸入 IP 位址。<br>可在電視的網路設定中查看。',
    'ip': '電視 IP 位址',
    'port': '連接埠',
    'ipHelp': '電視設定 → 網路 → 目前連線',
    'ipError': '請輸入有效的 IPv4 位址，例如 192.168.1.50。',
    'portError': '連接埠範圍為 1 至 65535。',
    'prepare': '準備電視',
    'dev': '啟用 Developer Mode',
    'devDesc':
      '開啟 Dev Mode Status。電視將重新啟動，之後請再次開啟 Developer Mode。',
    'keyServer': '啟用 Key Server',
    'keyServerDesc':
      '開啟 Key Server 並保持 Developer Mode 開啟。將其中的 IP Address 填入 CYTV 的電視位址欄。',
    'wifiTip': '請將手機和電視連接到同一區域網路。設定期間請中斷 VPN。',
    'install': '檢查並安裝',
    'reviewFoot': '安裝前可查看套件版本',
    'password': '密碼',
    'sshKey': 'SSH 金鑰',
    'importKey': '選擇金鑰檔案',
    'keyImported': '已加入 SSH 金鑰',
    'keyPrivate': '金鑰僅儲存在此手機上',
    'rootNotice':
      '需要已有 root 權限。CYTV 不會為電視取得 root 權限或變更韌體。',
    'rootHint': '連線時會要求輸入 SSH 密碼。',
    'keyError': '請先選擇 SSH 私鑰檔案。',
    'keyFailed': '無法讀取金鑰。請選擇不超過 64 KB 的檔案。',
    'browserKey': '金鑰匯入功能僅在 Android 應用程式中可用。',
    'progressTitle': '正在設定<br>您的新主畫面',
    'progressDesc': '請保持電視開啟。CYTV 將驗證連線並引導您完成安裝。',
    'statusTitle': '正在檢查<br>您的電視',
    'restoreTitle': '正在還原<br>LG Home',
    'progressFoot': '可以離開應用程式：通知中會顯示進度',
    'steps': ['連線與檢查', '電視應用程式', '套件安裝', '主畫面設定'],
    'log': '操作記錄',
    'awaiting': '正在等待電視回應…',
    'success': '您的新主畫面<br>已準備就緒',
    'successDesc':
      '請在電視上測試 Home、方向鍵和 OK，再測試退出應用程式及待機/喚醒。',
    'statusDone': '檢查完成',
    'statusDoneDesc': '請查看操作記錄中的檢查結果。',
    'restored': '已還原 LG Home',
    'restoredDesc': '請測試電視的 Home 鍵。',
    'cancelled': '操作已取消',
    'cancelledDesc': '如果套件已開始傳輸，請先檢查電視狀態，再重新安裝。',
    'failed': '無法完成<br>此操作',
    'failedDesc': '操作未完成。請查看記錄並檢查電視狀態，再重試。',
    'recoveryTitle': '返回 LG Home',
    'recoveryDesc':
      '在兩秒內按三次 Home 鍵。對於 0.6.13 及更早版本的 Helper，請長按 Home 鍵兩秒。',
    'three': '按 3 次',
    'checkStatus': '檢查狀態',
    'restore': '還原 LG Home',
    'toConnection': '返回連線',
    'done': '返回首頁',
    'trustTitle': '這是您的電視嗎？',
    'trustDesc':
      '如有可信連線，請與其 SSH 指紋比對。CYTV 會記住您的電視，金鑰發生變更時會停止連線。',
    'trust': '信任並繼續',
    'cancel': '取消',
    'continue': '繼續',
    'secretTitle': 'Developer Mode 代碼（Passphrase）',
    'secretDesc':
      '輸入電視上 Developer Mode 顯示的六位 Passphrase，注意區分大小寫。 請使用電視上的代碼，而非 LG 帳號密碼。如未顯示代碼，請開啟 Key Server。',
    'rootSecretTitle': 'SSH 密碼',
    'rootSecretDesc': '請輸入電視現有的 root SSH 密碼。',
    'keySecretTitle': 'SSH 金鑰密語',
    'keySecretDesc': '請輸入用於保護私鑰的密語。',
    'secretLabel': '代碼 / 密碼',
    'reviewTitle': '確認操作',
    'reviewDesc': '請查看安裝程式提供的詳細資訊，準備好後繼續。',
    'details': '詳細資訊',
    'toolsTitle': '您的電視，<br>盡在掌握',
    'toolsDesc': '檢查安裝狀態，或還原標準 LG Home。',
    'statusTool': '安裝狀態',
    'statusToolDesc': '檢查套件及未完成的操作',
    'restoreToolDesc': '還原電視原有的主畫面',
    'toolsConnect': '請輸入電視位址以執行此操作。',
    'check': '檢查狀態',
    'preview': '介面示範 · 未連接電視',
    'previewOnly': '這是介面預覽。請安裝 APK 以連接電視。',
    'prepareService': '正在準備安裝程式…',
    'confirmRestore': '還原 LG Home？',
    'confirmRestoreDesc':
      'CYTV 將連接電視並請您確認還原操作。其他應用程式將被保留。',
    'languageTitle': '語言',
    'languageClose': '關閉',
    'tvGreeting': '自在如家。',
    'tvSubtitle': '喜愛的應用程式，舒心的空間。',
    'seconds': '秒',
    'errorPrefix': '錯誤',
    'replayError': '無法還原操作畫面。請檢查電視狀態。',
    'notificationText': '電視操作進行中',
    'notificationChannel': 'CYTV',
    'webviewUpdate':
      '請更新 Android System WebView 或 Chrome，然後重新開啟 CYTV（需要 WebView 108 或更新版本）。',
    'connectionMethod': '選擇連線方式',
    'maintenanceProgress': '請保持電視開啟。CYTV 正在執行所選操作。',
    'homeDiagnostics': 'Home 鍵診斷',
    'homeDiagnosticsDesc':
      '記錄一次 Home 按鍵並儲存報告。僅適用於 No-root Helper。',
    'diagnosticProgress':
      '看到提示後，請按一次 Home 鍵，並保持此應用程式開啟一分鐘。',
    'saveReport': '儲存報告',
    'reportDone': '報告已就緒',
    'reportDoneDesc': '請儲存 JSON 報告並附到您的問題回報中。',
    'reportSaved': '報告已儲存。',
    'reportError': '無法儲存報告，請重試。',
    'devInstall': '在電視上開啟 LG Apps，搜尋並安裝 Developer Mode。',
    'devAccount':
      '開啟 Developer Mode 並登入 LG Developer 帳號。如需註冊，請前往 webostv.developer.lge.com。',
    'sessionHelp':
      '請保持 Developer Mode 有效：計時結束前開啟它，並在電視連網時按 EXTEND。過期後 LG 可能會刪除這些應用程式。',
    'editionHelp':
      'No-root 使用 LG 的 Developer Mode 應用程式。Root 需要電視已設定管理員存取權限。',
    'pairingHelp': '配對是獨立步驟：電視提示時，請用遙控器允許 CYTV 連線。',
    'homeHelperHelp':
      'Home 是您的應用程式主畫面。Home Helper 讓遙控器的 Home 鍵開啟此畫面。',
    'tryHomeHelp':
      '安裝後按 Home 鍵試用。如果開啟的是 LG Home，請從電視應用程式列表開啟 Home Helper。',
    'resumeHomeHelp':
      '在兩秒內短按 Home 三次可返回 LG Home。要重新啟動 Home 控制，請開啟 Home Helper，選擇啟動 Helper 並確認。已儲存的主畫面選擇會保留。',
    'guideExample': 'LG 範例畫面',
    'guideNote':
      'LG 範例畫面。您的電視介面可能有所不同。請使用您自己電視上顯示的代碼。',
    'connectRoot': '透過 Root 連線',
    'recoveryReview': '檢查復原選項',
    'recoveryReviewDesc': '檢查中斷的安裝。變更需要另行確認。',
    'tvChecksReview': '查看電視檢查結果',
    'homeObserved': '您已確認 Home 按鈕',
    'tvChecksDesc': '套件驗證、啟動狀態讀回和您的 Home 按鈕觀察是不同結果。'
  }
};
