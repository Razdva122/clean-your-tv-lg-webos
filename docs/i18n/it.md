# Clean Your TV — guida all’uso

l’installer chiede un nome, predefinito **Home**; CLI: `--tv-name "Aashiyaan"`. Dopo un aggiornamento compare automaticamente **Impostazioni → Home → Nome TV**. Puoi salvarlo o ripristinare Home in qualsiasi momento. Rimane dopo riavvii e aggiornamenti supportati; le altre impostazioni restano intatte. Massimo 48 caratteri. Cambia il launcher e il suo caricamento, non il nome di rete. La schermata precedente di LG potrebbe richiedere l’installer.

Modifica non ancora pubblicata: prima di una nuova installazione, l’installer del computer cerca una versione stabile più recente su GitHub. Scegli “Apri GitHub e scarica l’ultima versione” per fermarti e scaricarla, oppure “No, installa questa versione” per continuare esplicitamente. Se la verifica non riesce, puoi continuare. Le operazioni in sospeso e il ripristino saltano la verifica.

Clean Your TV offre al tuo LG webOS una schermata Home personale: le tue app nel tuo ordine, senza righe sponsorizzate in questo menu. Installa da computer o telefono Android; dopo la configurazione puoi spegnere il computer.

## 1. Scarica l’installer

Premi l’immagine del tuo dispositivo. I pulsanti scaricano l’ultima versione pubblicata. Su Mac scegli Apple Silicon (M1 o successivo) o Intel; controlla nel menu Apple → Informazioni su questo Mac.

[![Scarica — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Scarica — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Scarica — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Scarica — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Scarica — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="scegliere-ledizione"></a>

<a id="prerequisiti"></a>

## 2. Scegliere l’edizione

Accendi la TV e collegala alla stessa rete domestica del computer o telefono. Consenti a CYTV l’accesso alla rete locale quando richiesto.

- **No-root** — se non hai accesso root. Configura Developer Mode come indicato sotto.
- **Root** — se hai già accesso root via SSH. L’installer non esegue il root della TV. Non attivare Developer Mode su questa TV; conserva accesso SSH e dati di ripristino.

Per Root, l’installer verifica e sceglie un metodo disponibile per controllare Home. Se non può verificare la compatibilità, l’installazione si interrompe; non aggirare il controllo fallito.

**No-root → Root:** Se No-root è stato reinstallato dopo una rimozione completa, il passaggio a Root può richiedere prima una pulizia. Salva le preferenze di Home, scegli **Disinstalla Clean Your TV** con la connessione Root salvata e attendi la rimozione verificata. Verranno rimossi anche Home e Helper di No-root. Poi installa Root e conserva i dati di ripristino.

### Configurare Developer Mode (No-root)

Developer Mode permette a CYTV di installare app su una TV senza root.

1. Sulla TV, apri LG Apps, cerca Developer Mode e installalo.
2. Apri Developer Mode e accedi con il tuo account LG Developer. Se necessario, crea un account su [LG Developer](https://webostv.developer.lge.com).
3. Attiva Dev Mode Status. La TV si riavvia. Poi apri di nuovo Developer Mode.
4. Attiva Key Server e lascia Developer Mode aperto. Inserisci il suo IP Address come indirizzo della TV in CYTV.
5. Inserisci la Passphrase: i sei caratteri mostrati in Developer Mode sulla TV. Rispetta maiuscole e minuscole.

Usa il codice della TV, non la password del tuo account LG. Se il codice non appare, attiva Key Server.

L’associazione è un passaggio separato: quando la TV lo chiede, autorizza CYTV con il telecomando.

Mantieni Developer Mode attivo: prima che scada il timer, aprilo e premi EXTEND con la TV connessa a Internet. Alla scadenza, LG può rimuovere queste app.

<a id="installazione-e-lingua"></a>

## 3. Apri l’installer

- **Windows x64:** scarica `cytv-windows-x64-desktop.zip`, scegli **Estrai tutto** in Esplora file e apri `cytv-desktop/cytv-desktop.exe`. Mantieni la cartella `_internal` accanto al file.
- **macOS 13+:** estrai `cytv-macos-arm64.zip` per Apple Silicon oppure `cytv-macos-x64.zip` per Intel, sposta `cytv.app` in Applicazioni e aprila. Consenti l’accesso alla rete locale. Se un download affidabile viene bloccato, usa Privacy e sicurezza → Apri comunque; non disattivare Gatekeeper.
- **Linux x64:** su Ubuntu 22.04+, Debian 12+ o Mint 21+, installa `cytv-linux-x64.deb` con il gestore grafico dei pacchetti e apri Clean Your TV dal menu. Le librerie possono richiedere Internet. Linux ARM non è incluso.

**Android ARM64:** serve un telefono ARM a 64 bit con Android 7+ e WebView/Chrome 108+. Apri l’APK scaricato e autorizza l’installazione da questa origine se Android lo chiede. Apri CYTV; scegli la lingua in alto a destra. Aggiorna senza disinstallare o cancellare dati.

L’assistente usa inizialmente la lingua del sistema e salva una scelta esplicita. Sul televisore, apri **Impostazioni → Lingua** e scegli una lingua oppure l’opzione automatica del sistema. Le preferenze del televisore e dell’installer sono separate. I codici sono nell’[indice delle lingue](../LANGUAGES.md).

## 4. Installa sul televisore

1. In CYTV scegli **Configura la mia TV**. Sul computer seleziona una TV rilevata; su Android inserisci il suo indirizzo IP. Se la ricerca non trova la TV, inserisci l’indirizzo manualmente.
2. Scegli **No-root** o **Root** e controlla il televisore prima di continuare.
3. No-root: inserisci il codice di Developer Mode e accetta la richiesta sulla TV. Root: usa le credenziali SSH esistenti. Accetta una nuova identità SSH solo per la tua TV su una rete fidata. Se una chiave salvata cambia, fermati e verifica il motivo.
4. Segui la procedura guidata. Tieni la TV accesa, non cambiare rete e lascia CYTV aperto fino al termine. Non forzare l’arresto dell’app Android. Root attiva il controllo Home subito dopo aver preparato il ripristino.

L’installazione Root continua con un avviso se non è possibile leggere gli ingressi TV ma l’elenco delle app è valido. Gli ingressi potrebbero mancare in Home; un elenco delle app non leggibile o vuoto interrompe comunque l’installazione. Salva il rapporto diagnostico se l’avviso persiste.

## 5. Controlla il telecomando

1. Apri un’altra app sulla TV e premi brevemente **Home**. Deve aprirsi Clean Your TV. Indica nella procedura guidata ciò che hai visto; salta la verifica se non l’hai eseguita.
2. Controlla frecce, OK, Indietro, volume e audio. Prova separatamente standby/riattivazione e avvio dopo aver scollegato l’alimentazione. L’installazione riuscita non verifica da sola queste azioni.

<a id="uso-e-ripristino"></a>

## 6. Uso e ripristino

Supporto IR No-root: rilasciare Home dopo una pressione breve programma Clean dopo circa 700 ms; LG Home potrebbe apparire prima. La pressione prolungata resta a webOS e tre pressioni fermano ancora Helper. L’accesso con Developer Mode standard non è verificato; non modificare i permessi dei dispositivi di input.

Le frecce selezionano, OK apre; tieni premuto OK per riordinare. Un breve Indietro conserva navigazione e conferma di uscita dell’app. Home apre il launcher quando il controllo è attivo. Tieni premuto Indietro per 1,2 secondi per aprire LG Home una volta. L’interruttore del controllo Home e le impostazioni restano invariati.

**Premi Home tre volte entro due secondi**, rilasciandolo tra le pressioni. Ripristina LG Home e interrompe il controllo senza cancellare le preferenze.

No-root: Per riavviare il controllo Home, apri Home Helper, scegli Avvia Helper e conferma. La tua scelta della schermata Home viene mantenuta. Root: attiva **Cambia Home** nelle impostazioni Home per riprendere. **Apri LG Home** apre LG Home una volta senza cambiare la destinazione di Home. Per ripristinare LG Home come destinazione permanente, disattiva **Cambia Home**. Non eseguire entrambi i controllori insieme. Se il problema ricompare, lascia attivo LG Home.

Un aggiornamento non riavvia un Helper No-root arrestato. Riattivalo esplicitamente come descritto sopra; non eliminare manualmente i marcatori di arresto.

## Serve aiuto?

Se compare `ssh-identity-changed` dopo un ripristino o una modifica SSH, fermati: CYTV ha bloccato la chiave salvata modificata prima dell’autenticazione. La conferma iniziale di fiducia non la sostituisce; una disinstallazione in sospeso non spiega la differenza. Conserva il profilo originale, le chiavi e i dati di recupero. Non esiste un comando automatico supportato per rinnovare la fiducia. Servono una verifica indipendente dell’identità/impronta del TV e una procedura revisionata che preservi il profilo: [recupero dell’identità SSH](../RECOVERY.md#ssh-identity-changed).

Se l’installazione viene interrotta, usa la stessa connessione salvata e scegli prima **Controlla stato TV**. Prosegui solo con il ripristino proposto dalla procedura guidata. Se lo stato è sconosciuto, salva il rapporto diagnostico e fermati; conserva i dati di ripristino e non ripetere l’installazione alla cieca.

Durante il ripristino, lascia disattivato il controllo Home e conserva i rapporti diagnostici originali e la connessione salvata. Conferma separatamente la verifica e le modifiche. Segui la guida dettagliata per la versione installata; non forzare la reinstallazione e non cancellare lo stato di ripristino.

Indica modello TV, firmware, No-root o Root, dispositivo di installazione, passaggio e messaggio di errore. Rimuovi password, chiavi, indirizzi e dati personali prima di condividere il rapporto. Non viene pubblicato automaticamente.

[Segnala un problema](../FEEDBACK.md) · [Ripristino — inglese](../RECOVERY.md) · [Aggiornare o rimuovere — inglese](../MAINTENANCE.md) · [Altre lingue](../LANGUAGES.md)

### Rimozione semplice

Scegli **Disinstalla Clean Your TV** in Manutenzione con la stessa connessione salvata. Conferma una volta. Le app e i file noti del progetto presenti vengono eliminati; gli elementi assenti vengono saltati, anche dopo un’installazione parziale.

Sui TV meno recenti senza un’app LG Home separata, la rimozione No-root può passare alla TV in diretta. Lasciare il TV acceso ed eseguire il riavvio richiesto; non eliminare i dati di recupero né ripristinare il TV.

Quando richiesto, scollega l’alimentazione della TV, ricollegala, attendi la rete e scegli **Riprova**. Standby o Quick Start non è un riavvio completo; CYTV non riavvia automaticamente la TV. Se la connessione si interrompe, controllala e riprova la stessa rimozione senza un altro assistente di ripristino. Se l’accesso è negato, usa la connessione Root richiesta; se la TV è occupata, attendi e riprova. Il successo appare solo dopo la verifica della pulizia finale. Conserva chiavi e rapporti originali. Restano validi i comandi di emergenza e il consenso alla condivisione.

Un’installazione non riuscita o interrotta offre direttamente il ripristino. Se No-root non può proseguire, conferma una volta la rimozione completa. La rimozione esegue fino a tre tentativi in caso di perdita temporanea della connessione o processo CYTV occupato. Se serve Root, scegli **Connetti con Root** per la stessa TV; la pulizia Root verificata completa anche la rimozione No-root bloccata. Se l’attivazione Root fallisce, CYTV tenta di ripristinare e verificare LG Home senza ripetere l’attivazione. L’annullamento con lavoro incompleto conserva rapporto e azioni di ripristino. L’arresto di emergenza resta invariato.

Dopo un errore di connessione durante la rimozione, apri i dettagli, verifica la rete o scegli una chiave SSH Root esistente e riprova. Indirizzo, edizione, porta e verifica della chiave del TV restano fissi. No-root controlla Helper prima dell’abbinamento: arrestalo e conferma il nuovo controllo nello stesso percorso. Solo un TV vuoto verificato senza installazioni in sospeso può evitare il riavvio; dopo una rimozione effettiva serve il riavvio richiesto. Se il servizio ingressi non funziona, la pulizia sicura dei pacchetti prosegue; il successo richiede comunque la verifica della pulizia del collegamento.

**Reinstallare Root:** Scegli **Configura la mia TV → Root** con la connessione salvata e conferma **Reinstallare Root?**. L’installer ripristina LG Home e rimuove completamente Clean Your TV, inclusi i suoi updater, Home Helper e le preferenze salvate. Dopo aver verificato la rimozione, installa e attiva i pacchetti e l’ambiente Root inclusi nell’installer. Le altre app della TV e l’accesso root/SSH esistente sono conservati. Se la rimozione si interrompe o richiede un riavvio completo, completala prima di ricominciare la configurazione. **Disinstalla Clean Your TV** da solo non avvia mai una nuova installazione.

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="requisiti"></a>
<a id="python-opzionale-per-root"></a>
<a id="verifiche-hardware-e-limiti"></a>
<a id="blocco-firmware-lg-in-120"></a>
<a id="novità-della-130-ripristino-guidato-dal-computer"></a>
<a id="novità-della-130--12"></a>
<a id="candidato-non-pubblicato-installazione-root-tramite-homebrew"></a>
<a id="candidato-non-pubblicato-ripristino-audio-hdmi-root"></a>
<a id="temi-154"></a>
<a id="categorie-delle-impostazioni-candidato-non-pubblicato"></a>
<a id="risoluzione-grafica-automatica-candidato"></a>
<a id="aggiornamenti-e-rimozione"></a>
<a id="aiuto-e-altre-istruzioni"></a>
<a id="temi"></a>
<a id="categorie-delle-impostazioni-154"></a>
<a id="risoluzione-grafica-automatica-160"></a>
<a id="spazio-di-archiviazione"></a>

Riferimenti dettagliati in inglese: [requisiti](../COMPATIBILITY.md) · [comandi](../CONTROLS.md) · [temi](../THEMES.md) · [aggiornamenti](../UPDATES.md).

<a id="candidato-unreleased-nodejs-tv-meno-recente"></a>
<a id="nodejs-tv-meno-recente-pubblicato-in-v1120"></a>
<a id="rimozione-semplice-v1110"></a>

## Meteo

Apri Impostazioni → Meteo, sotto Sfondi. Attiva il meteo e apri Città per cercare e scegliere regione e paese corretti, oppure scegli Automatico per una città approssimativa in base alla connessione. Una VPN può modificare il risultato; se la città manca o è errata, usa la ricerca manuale. La città rilevata o scelta appare nelle impostazioni. Scegli °C / m/s o °F / mph e un formato disponibile: compatto, attuale, dettagliato o quattro giorni. L’anteprima segue il tema; Esempio indica dati dimostrativi. Liquid Glass supporta solo il formato compatto. Ribbon e Atmosphere non mostrano il meteo. Disattivandolo si interrompono le richieste e si nascondono città, unità e formato; la scelta della fonte resta disponibile. Durante un guasto i dati recenti possono restare temporaneamente; poi il meteo scompare fino all’aggiornamento.

Scegli la fonte delle previsioni: Auto, MET Norway o Open-Meteo. Auto inizia con MET Norway, prova Open-Meteo una volta in caso di errore, poi riutilizza l’ultima fonte riuscita e la sua cache. La scelta manuale non cambia mai fonte automaticamente. Le nuove impostazioni usano Auto; quelle salvate senza fonte mantengono Open-Meteo. La fonte effettiva è visibile. La disponibilità dipende dalla rete. MET si aggiorna al massimo ogni tre ore; la cache scade dopo sei ore. I campi assenti sono nascosti: MET non fornisce temperatura percepita o probabilità di precipitazioni. Gli intervalli giornalieri riassumono punti di previsione, non estremi misurati.

Le coordinate vanno a api.met.no o api.open-meteo.com, le ricerche di città a geocoding-api.open-meteo.com. La posizione automatica facoltativa invia l’IP pubblico a get.geojs.io. Le connessioni usano HTTPS; non serve una chiave API. Posizione, fonte e cache restano sul televisore. Fonti dei dati contiene condizioni e crediti, incluso l’Istituto meteorologico norvegese (MET Norway, CC BY 4.0).

Il pulsante Fonti dei dati nel titolo Meteo apre le informazioni su servizi e licenze.
