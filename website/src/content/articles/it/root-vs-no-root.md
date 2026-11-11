---
lang: it
topic: root-vs-no-root
title: "Root o No-root per un launcher LG webOS"
description: "Scegli l’edizione di Clean Your TV adatta al tuo TV LG webOS. Confronta accesso richiesto, gestione di Developer Mode, tasto Home e ripristino prima dell’installazione."
updated: '2026-11-09'
---

Scegli No-root se il tuo TV LG usa Developer Mode. Scegli Root solo se dispone già di accesso root funzionante e servizi compatibili. Entrambe le edizioni di Clean Your TV offrono la stessa interfaccia Home e funzionano sul televisore dopo l'installazione. Il programma di installazione non ottiene l'accesso root e non riscrive il firmware.

## Cosa richiede No-root?

No-root usa LG Developer Mode, Key Server e l'abbinamento locale durante la configurazione. Home Helper funziona sul televisore e gestisce il tasto Home dove dispositivo e firmware lo supportano. Per l'uso quotidiano non serve lasciare accesi computer o telefono.

Il requisito da mantenere nel tempo è Developer Mode: prolunga la sessione prima che scada. LG avverte che le app installate tramite Developer Mode possono essere rimosse se la modalità viene disattivata o scade. Il rinnovo automatico del progetto è facoltativo, in beta e disattivato per impostazione predefinita: non considerarlo una garanzia. Leggi la [guida a Developer Mode](/clean-your-tv-lg-webos/it/articles/lg-developer-mode/) prima di affidarti a questa edizione.

## Cosa richiede Root?

Root usa un accesso SSH root già esistente, servizi TV compatibili e capacità di gestione degli input e runtime supportate. Il solo accesso root non dimostra la compatibilità. Il programma di installazione controlla l'ambiente: non aggirare un prerequisito rifiutato e non sostituire i runtime di sistema per forzare l'esito positivo.

Root ha pacchetti e gestione del tasto Home separati. Non attivare Developer Mode su una configurazione già dotata di root e arresta Home Helper No-root prima di usare la gestione Root. Scegliere l'edizione dipende dall'accesso che hai già, non da un pulsante che eseguirà il root del televisore.

## Confronta manutenzione e ripristino

- **Uso quotidiano:** entrambe le edizioni funzionano sul TV, con app e temi nel launcher.
- **Manutenzione No-root:** mantieni attiva Developer Mode e conserva abbinamento e connettività richiesti da Helper.
- **Manutenzione Root:** mantieni disponibili i servizi di ripristino indipendenti e il runtime necessario. La disponibilità degli aggiornamenti dipende dall'edizione installata e dal percorso di aggiornamento supportato; il solo accesso root non abilita l'OTA.
- **Uscita di emergenza:** le edizioni attualmente supportate usano tre pressioni brevi di Home entro due secondi. Home Helper fino alla 0.6.13 usa invece una pressione prolungata di due secondi.

Dopo un arresto di emergenza, riattivare la gestione persistente richiede un'azione esplicita. In No-root apri Home Helper e scegli Start Helper; in Root usa Change Home nelle impostazioni Home. Consulta il [confronto delle edizioni](/clean-your-tv-lg-webos/it/editions/) e l'[aiuto per il ripristino](/clean-your-tv-lg-webos/it/help/#home-button).

## Controlla il televisore prima dell'installazione

Leggi la [pagina di compatibilità](/clean-your-tv-lg-webos/it/compatibility/) tenendo a portata di mano modello esatto, firmware, webOS e telecomando. I risultati segnalati riguardano una configurazione specifica. Dopo la configurazione, verifica separatamente Home, avvio delle app, audio, standby e avvio a freddo. L'installazione di un pacchetto non dimostra che tutto funzioni.

Usa il [programma di installazione pubblicato e la guida](/clean-your-tv-lg-webos/it/install/). Se hai già una configurazione funzionante e vuoi cambiare edizione, segui i passaggi documentati per il passaggio e la rimozione invece di installarne una sopra l'altra.

## Fonti e approfondimenti

- [Confronto delle edizioni del progetto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Requisiti e limiti noti del progetto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Cosa cambia una schermata Home diversa](/clean-your-tv-lg-webos/it/articles/change-lg-webos-home-screen/)
