# Clean Your TV — guida all’uso

> v1.5.0: temi, galleria e invio dal PC alla TV. Limiti Root noti: Appearance può spostarsi di 110 px; Home potrebbe non aprirsi automaticamente dopo lo standby. La verifica sui dispositivi resta limitata. [1.5.0](../RELEASE-1.5.0.md).

> Prossimo candidato (non pubblicato): i temi a layout fisso mantengono lo spazio della riga Columns nascosta per conservare lo scorrimento di Appearance durante Apply. Puntatore, tastiera e strumenti di accessibilità saltano Columns. La verifica sul TV è ancora da eseguire.

[Documentazione](../README.md) · [Segnalare un problema](../FEEDBACK.md)

Questa guida descrive la versione pubblicata **[1.5.2](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.5.2)**. L’accettazione C3 copre le prove registrate di alimentazione, Home, focus, stato disattivato e ripristino manuale della versione precedente. Altri TV, audio eARC e dispositivi Android fisici restano non verificati; l’installazione riuscita non dimostra compatibilità. [Ambito verificato (inglese)](../RELEASE-1.4.0-ACCEPTANCE.md).

**Installer non ancora pubblicato:** console, desktop e Android mostrano ogni verifica TV come non eseguita, in corso, superata, fallita o non verificabile. I risultati restano visibili dopo un errore. Node.js/Python viene verificato sulla TV; `doctor` non prepara Python né richiede l’abbinamento per il controllo. Salva il rapporto prima di riprovare.

## Scegliere l’edizione

No-root e Root sono opzioni equivalenti per diverse configurazioni della TV. Scegli No-root per LG Developer Mode oppure Root se disponi già di accesso root tramite SSH. Compatibilità e verifiche eseguite sono specifiche di ogni edizione.

- **No-root:** attiva LG Developer Mode e Key Server. Inserisci la frase di accesso mostrata sul televisore e accetta sullo schermo la richiesta separata di abbinamento. Developer Mode deve restare attivo: alla scadenza le app installate in questo modo possono essere rimosse. Controlla il timer ufficiale anche con rinnovo Beta attivo. Il monitoraggio di Helper richiede la rete locale.
- **Root:** serve un accesso SSH root già disponibile. L’installer non ottiene i privilegi root. Non attivare Developer Mode su una configurazione già dotata di root. Mantieni disponibili accesso root e servizi di ripristino.

Root richiede le interfacce Home funzionanti di Settings Service e System Profile (`com.webos.service.systemprofile`); il solo accesso root non garantisce la compatibilità.

## Prerequisiti

Accendi il televisore e collegalo alla stessa rete locale affidabile del computer. Dopo l’installazione il computer può restare spento. La compatibilità dipende da modello, firmware e telecomando; Root ha ancora verifiche hardware da completare.

Node 0.10.25 è supportato dalla build sorgente/di prova non pubblicata; gli installer pubblicati richiedono ancora 0.12.2+. Vedi [compatibilità](../COMPATIBILITY.md).

No-root Helper richiede Node.js **0.10.25+** sul TV. Root richiede Node.js **8+** e Python **3.9+** funzionante. Se necessario, l’installer scarica un Python privato verificato; la preparazione iniziale richiede **320 MiB** liberi. Non sostituisce Python di sistema. Conserva gli ambienti usati dal recupero. [Python (inglese)](../OPTIONAL-PYTHON.md). Il rinnovo Developer Mode è **Beta, disattivato per impostazione predefinita**; il rinnovo reale senza root non è confermato. Controlla ancora il timer ufficiale.

### Configurare Developer Mode (No-root)

Developer Mode permette a CYTV di installare app su una TV senza root.

1. Sulla TV, apri LG Apps, cerca Developer Mode e installalo.
2. Apri Developer Mode e accedi con il tuo account LG Developer. Se necessario, crea un account su webostv.developer.lge.com.
3. Attiva Dev Mode Status. La TV si riavvia. Poi apri di nuovo Developer Mode.
4. Attiva Key Server e lascia Developer Mode aperto. Inserisci il suo IP Address come indirizzo della TV in CYTV.
5. Inserisci la Passphrase: i sei caratteri mostrati in Developer Mode sulla TV. Rispetta maiuscole e minuscole.

Usa il codice della TV, non la password del tuo account LG. Se il codice non appare, attiva Key Server.

L’associazione è un passaggio separato: quando la TV lo chiede, autorizza CYTV con il telecomando.

Mantieni Developer Mode attivo: prima che scada il timer, aprilo e premi EXTEND con la TV connessa a Internet. Alla scadenza, LG può rimuovere queste app.

## Installazione e lingua

- **Windows x64:** scarica `cytv-windows-x64-desktop.zip`, scegli **Estrai tutto** in Esplora file e apri `cytv-desktop/cytv-desktop.exe`. Mantieni la cartella `_internal` accanto al file. La firma dell’editore Windows non è configurata. La console separata è `cytv-windows-x64.exe`; rinominala in `cytv.exe` e usa `.\cytv.exe` in PowerShell per i comandi seguenti.
- **macOS 13+:** estrai `cytv-macos-arm64.zip` per Apple Silicon oppure `cytv-macos-x64.zip` per Intel, sposta `cytv.app` in Applicazioni e aprila. Consenti l’accesso alla rete locale. Se un download affidabile viene bloccato, usa Privacy e sicurezza → Apri comunque; non disattivare Gatekeeper. La verifica sui sistemi meno recenti non è conclusa.
- **Linux x64:** su Ubuntu 22.04+, Debian 12+ o Mint 21+, installa `cytv-linux-x64.deb` con il gestore grafico dei pacchetti e apri Clean Your TV dal menu. Le librerie possono richiedere Internet. Linux ARM non è incluso. L’eseguibile autonomo `cytv-linux-x64` è la CLI; usa il `.deb` per l’app grafica.

[Installer Android (inglese)](../../android/README.md): scegli la lingua in alto a destra. Aggiorna senza disinstallare o cancellare dati. Android 7 / WebView 108 è il minimo, non una configurazione telefonica verificata; l’accettazione usa un emulatore Android 15 ARM64 / WebView 124. Telefoni fisici e recupero con TV reale restano non verificati.

L’assistente usa inizialmente la lingua del sistema e salva una scelta esplicita. Sul televisore, apri **Impostazioni → Lingua** e scegli una lingua oppure l’opzione automatica del sistema. Le preferenze del televisore e dell’installer sono separate. I codici sono nell’[indice delle lingue](../LANGUAGES.md).

Per la CLI scaricata separatamente su macOS/Linux, dalla cartella estratta:

```sh
chmod +x cytv
./cytv --language it install
```

Scegli il televisore o inserisci l’IP, seleziona l’edizione e controlla il riepilogo. Accetta una nuova identità SSH solo per il tuo televisore su una rete affidabile; una chiave salvata cambiata blocca l’accesso. Root prepara il ripristino e attiva subito Home, senza prova temporanea né passaggio per confermare il mantenimento. Verifica frecce, OK, Home, Indietro/Annulla, volume, standby e avvio a freddo.

## Uso e ripristino

Le frecce selezionano, OK apre; tieni premuto OK per riordinare. Un breve Indietro conserva navigazione e conferma di uscita dell’app. Home apre il launcher quando il controllo è attivo. Tieni premuto Indietro per 1,2 secondi per aprire LG Home una volta. L’interruttore del controllo Home e le impostazioni restano invariati.

**Premi Home tre volte entro due secondi**, rilasciandolo tra le pressioni. Ripristina LG Home e interrompe il controllo senza cancellare le preferenze. Con No-root Helper fino alla 0.6.13 inclusa, tieni invece premuto Home per circa due secondi. La pressione prolungata di Home non è il gesto di emergenza di Root.

No-root: Per riavviare il controllo Home, apri Home Helper, scegli Avvia Helper e conferma. La tua scelta della schermata Home viene mantenuta. Root: attiva **Cambia Home** nelle impostazioni Home per riprendere. **Apri LG Home** apre LG Home una volta senza cambiare la destinazione di Home. Per ripristinare LG Home come destinazione permanente, disattiva **Cambia Home** o esegui `cytv restore`. Non eseguire entrambi i controllori insieme. Se il problema ricompare, lascia attivo LG Home.

```sh
./cytv --language it status
./cytv --language it doctor --report
./cytv --language it restore
./cytv --language it uninstall
```

Dopo un’interruzione, esegui prima `status` e conserva i registri. `restore` ripristina LG Home senza rimuovere app; `uninstall` lo ripristina prima della rimozione. I dati di ripristino Root restano intenzionalmente: non cancellarli per forzare una reinstallazione. Controlla i rapporti prima di condividerli; non pubblicare chiavi o cartelle dei profili.

Solo nella versione candidata non ancora pubblicata, in entrambe le edizioni: apri **Impostazioni di Home → Aspetto → Colonne** e scegli da 1 a 8 colonne, oppure **Secondo il tema** per usarne il valore (Classic: 5). Un numero esplicito ha la precedenza sul tema. I temi con disposizione fissa nascondono l’opzione Colonne e usano il valore dell’autore. La scelta salvata viene ripristinata passando a un tema che supporta questa impostazione. Nell’anteprima candidata Alpine, le app formano una sola fila orizzontale ciclica: Sinistra/Destra scorre, Su apre le scorciatoie e Giù torna alla stessa app. Nell’anteprima Alpine puoi scorrere anche con la rotella o il touchpad; Home non si muove dietro una finestra aperta.

Candidato non ancora pubblicato, entrambe le edizioni: in **Impostazioni Home → Aspetto**, disattiva **Mostra riquadro «Aggiungi app»** per nascondere +. È attivo per impostazione predefinita. Usa **Aggiungi app** nella stessa sezione per aggiungere o ripristinare app anche con + nascosto. Puoi continuare a spostare e nascondere le app; la scelta resta dopo il riavvio. Se tutte le app sono nascoste, i controlli in alto e le impostazioni restano accessibili.

Nelle anteprime dei temi della versione candidata non pubblicata con barra laterale opzionale, Su/Giù seleziona una voce del menu, Destra passa alle app e Sinistra dalla prima colonna delle app torna al menu.

No-root 1.5.0: Helper può riprendersi da un timeout temporaneo del watchdog al risveglio, con un massimo di cinque tentativi in dieci minuti. Stop e tre pressioni di Home richiedono ancora un avvio esplicito di Helper; gli errori ripetuti lo lasciano fermo. La verifica sul TV è in attesa. [Comportamento e limiti (inglese)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Aggiornamenti e rimozione

Dopo la connessione, cytv mostra versione installata → inclusa e distingue prima installazione, reinstallazione e downgrade. Controlla il riepilogo prima della conferma; `--yes` non rende sicuro un passaggio incompatibile. Conserva pacchetti funzionanti e copie private delle impostazioni. Per gli aggiornamenti dal computer ferma No-root Helper prima di sostituire i pacchetti; non disinstallare prima. Non sovrascrivere un ambiente Root attivo con una sola IPK: usa il percorso previsto da cytv. Rimuovere l’app desktop non rimuove le app TV.

Apri impostazioni Home → Aggiornamenti software e verifica le versioni prima di confermare. Aggiornamento e rollback sul TV richiedono **root, Homebrew Channel** e infrastruttura di aggiornamento compatibile già preparata, anche per No-root. Senza root usa il computer. Preparare gli aggiornamenti completi è un’azione esplicita separata: [aggiornamenti (inglese)](../UPDATES.md). Recupero mostra la versione salvata; il rollback può perdere modifiche successive alle impostazioni.

**Installazione 1.3.0 esistente:** il System Updater originale può rifiutare modifiche all’infrastruttura. Conservare l’operazione interrotta e seguire il recupero e la preparazione della sostituzione verificati per 1.5.0+; non eliminare i registri né riprovare alla cieca. Aggiornare solo l’app non sostituisce l’infrastruttura Root fissata. [Migrazione e recupero (inglese)](../UPDATES.md#one-time-computer-preparation).

La correzione del canale impostazioni Home è pubblicata dalla 1.5.0. Aggiornare Home e Helper insieme con un installer pubblicato compatibile; aggiornare solo Home non modifica Helper. La verifica resta limitata ai modelli documentati. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

Il recupero audio HDMI Root è sperimentale e **disattivato per impostazione predefinita**; abilitalo solo se serve. Può interrompere audio funzionante e non dimostra compatibilità eARC. [Recupero audio (inglese)](../development/ROOT-AUDIO-RECOVERY.md). Il **CYTV Installer Homebrew non è ancora pubblicato**; usa l’installer pubblicato per computer o Android.

Homebrew Channel ha negato l’accesso a questo programma di installazione. Su webOS 11, Homebrew 0.7.3 richiede un aggiornamento di compatibilità dai suoi sviluppatori. Usa il programma pubblicato per computer o Android finché una versione supportata di Homebrew non include la correzione. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: se vecchie directory Root scrivibili impediscono l’accesso all’API del firmware, `cytv enable-firmware-access --edition root --repair-package-permissions` verifica il pacchetto corrente con dati privati attendibili e rimuove la scrittura per gruppo/altri solo dai percorsi propri di Root. File sconosciuti o modificati fermano la riparazione. Profilo, scelta Home e blocco firmware restano invariati; [dettagli (inglese)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` gestisce un ripristino Root verificato quando tutti gli installer dei pacchetti sono terminati, ma è scaduto il tempo di disponibilità del launcher. Richiede il segnale autentico del launcher e rifiuta risultati d’installazione sconosciuti. Conserva pacchetti, codice e chiavi fissati, prove dell’errore e la disattivazione esplicita di Home. Un registro privato documenta il tentativo limitato. Ripetere normalmente non estende il termine. Solo dopo la scadenza dei 120 secondi, senza un segnale di disponibilità accettato né risultati d’installazione sconosciuti, `--new-recovery-attempt` archivia l’intero registro precedente con UUID/hash e apre esplicitamente un nuovo tentativo. Un recupero completato resta idempotente; nessun tentativo automatico. [Procedura e limiti (inglese)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0: il pacchetto di sostituzione include System Updater 1.1.2. Prima dell’OTA, sostituisci esplicitamente 1.1.0 o 1.1.1 con `cytv replace-system-updater --edition root`. Cambia solo System Updater; app Root/Root Updater, profilo completo e scelta Home restano invariati, mentre lo stato precedente viene archiviato. Operazioni sconosciute o incomplete bloccano la sostituzione. Questo requisito non blocca i feed No-root. [Procedura (inglese)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Aiuto e altre istruzioni

Dopo un errore o un’interruzione, controlla lo stato e salva il rapporto diagnostico di quel tentativo. Il recupero guidato chiede conferme separate per rimozione e reinstallazione. Se il risultato è incerto, fermati e conserva registri privati e file di recupero; non eliminarli mai per forzare un tentativo. [Recupero (inglese)](../RECOVERY.md). Per assistenza indica modello, firmware, edizione, versione dell’installer, passaggio fallito e risultato atteso/effettivo; verifica e rimuovi i segreti dal rapporto prima di condividerlo.

[Documentazione](../README.md) · [Segnalare un problema](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="requisiti"></a>
<a id="python-opzionale-per-root"></a>
<a id="verifiche-hardware-e-limiti"></a>
<a id="blocco-firmware-lg-in-120"></a>
<a id="novità-della-130-ripristino-guidato-dal-computer"></a>
<a id="novità-della-130--12"></a>
<a id="candidato-non-pubblicato-installazione-root-tramite-homebrew"></a>
<a id="candidato-non-pubblicato-ripristino-audio-hdmi-root"></a>


## Temi: candidato in sviluppo

Nel candidato compatibile: **Impostazioni → Temi**. **Classic** e **Alpine** sono integrati e non richiedono il download del tema; Classic resta predefinito. **Channel** è esterno, dallo showcase. Durante una prova nella galleria: Scegli il tema e **Mantieni tema** entro **20 secondi**. **Ripristina**, Back o la scadenza ripristinano il precedente. Una prova interrotta avvia nuovamente Home con Classic. I temi integrati e scaricati scelti nell’elenco installato vengono applicati e salvati subito, senza timer. Vale anche per quelli ricevuti dal computer o installati tramite URL. Solo Prova tema nella galleria avvia una prova di 20 secondi.

I temi installati appaiono in una sola riga a scorrimento orizzontale. Il tema attivo è sempre il primo e la sua scheda è evidenziata. Usa Sinistra/Destra per scorrere la riga.

La galleria mostra solo temi non installati su questo TV. Classic, Alpine e i temi scaricati sono nascosti, anche se esiste una versione più recente. Dopo la rimozione il tema riappare. Aggiorna tramite URL o trasferimento dal computer.

Le schede sono integrate in Temi, accanto alle categorie. Galleria, installazione tramite link e trasferimento dal computer si aprono nello stesso pannello; solo una prova della galleria mostra temporaneamente Home.

Aprire la galleria o scegliere Aggiorna verifica gli aggiornamenti revisionati nel repository principale senza aggiornare Home o ricaricare la pagina. Le nuove voci arrivano dopo la normale integrazione; un candidato non integrato può mostrare il catalogo incluso. Offline o in caso di errore si usano voci e anteprime incluse. I temi integrati corrispondono alla versione installata di Home. Apri l’anteprima di Channel, poi **Scarica tema** (serve internet). Dopo il download, prova e scegli **Mantieni tema** entro **20 secondi**. I temi installati funzionano offline. **Aggiungi tramite ID** resta disponibile per i link fissati.

Per provare un tema non pubblicato, apri prima **Impostazioni → Temi → Ricevi dal computer** sul TV. Inserisci indirizzo TV e PIN a sei cifre in **Send to TV** nell’anteprima del computer, invia e scegli **Applica tema** sul TV. Il metodo principale collega il PC alla porta TCP **8879 del TV**, senza modificare il firewall del computer. Entrambi devono essere nella stessa rete domestica fidata. Il ricevitore si chiude dopo un invio, annullamento, uscita o **10 minuti**. Il PIN non viene salvato; il tema installato funziona offline. Non serve pubblicare su GitHub.

Per un tema pubblicato, apri **Aggiungi tramite ID** e inserisci l’ID (ad esempio `102300a209`), `da.gd/102300a209` o il link GitHub completo. Home mostra l’indirizzo da.gd prima del caricamento e verifica destinazione GitHub e pacchetto. L’autore può copiare l’ID dalle note di rilascio o da **TV link → Copy ID** nell’anteprima.

I pacchetti pubblicati potrebbero non avere ancora questi comandi. I test nel browser non provano la compatibilità TV. [Guida completa](../THEMES.md).

Questo candidato non ancora pubblicato include **Ribbon** insieme a Classic e Alpine, senza scaricare il tema. Classic rimane predefinito. Dopo aver aggiornato Home, scegli Ribbon in Impostazioni → Aspetto.

I temi con barra configurabile non ancora pubblicati possono collocare Ingressi, Wi-Fi e Impostazioni in basso a sinistra. Se abilitato, Sinistra dalla prima app visibile seleziona Impostazioni, poi Wi-Fi e Ingressi; Destra da Impostazioni torna alla stessa app visibile. L’installazione di un tema che richiede una nuova funzione Home viene rifiutata nelle versioni incompatibili, mantenendo aspetto e selezione attuali. Aggiorna prima Home. Un successivo downgrade può ripristinare Classic all’avvio.

Temi mostra le anteprime dei temi integrati e di tutti quelli installati personalmente, anche offline. Un pulsante separato apre il catalogo pubblicato; installare un tema personale non lo pubblica.

Aspetto contiene Colonne con il numero attuale e i controlli delle app. La categoria Temi contiene temi installati, galleria, ricezione dal computer e Aggiungi tramite ID a destra (es. 102300a209). Ripristina Classic dalla scheda e rimuovi i download singolarmente. Lingua offre direttamente la scelta.

Nell’anteprima del browser, Ricevi dal computer spiega i passaggi sul televisore senza avviare un ricevitore TV sul computer. Usa Send to TV sopra l’anteprima. Rimuovere un tema scaricato richiede conferma; se è attivo, viene prima ripristinato Classic. Annulla conserva il tema.

<a id="categorie-delle-impostazioni-candidato-non-pubblicato"></a>

## Categorie delle impostazioni (1.5.0)

Entrambe le edizioni mostrano le categorie a sinistra e le impostazioni a destra: schermata Home, Aspetto (temi e colonne), Lingua, Aggiornamenti software e Avanzate. No-root aggiunge Developer Mode; Root include il firmware LG negli aggiornamenti e l’audio HDMI in Avanzate. Su/Giù naviga nella colonna, Destra entra nelle impostazioni e Sinistra torna alle categorie. Indietro torna prima alle categorie, poi chiude le impostazioni. Tab raggiunge anche il pulsante per tornare a Home.

Un punto giallo su Aggiornamenti software e sul pulsante interno indica un aggiornamento disponibile. Entrambi scompaiono quando una verifica riuscita conferma che non ci sono aggiornamenti; in caso di errore resta l’ultimo stato confermato.
