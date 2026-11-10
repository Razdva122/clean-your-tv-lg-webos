---
lang: it
topic: change-lg-webos-home-screen
title: "Come cambiare la schermata Home di un TV LG webOS"
description: "Personalizza la schermata Home del tuo TV LG webOS con Clean Your TV. Scopri cosa cambia un launcher, quale edizione scegliere e cosa verificare prima di installarlo."
updated: '2026-11-09'
---

Clean Your TV è una schermata Home alternativa per i televisori LG webOS. Consente di ordinare le app come preferisci e offre temi e un dock personalizzabile. Dopo la configurazione funziona sul televisore, quindi puoi spegnere il computer. La possibilità di gestire il tasto Home dipende da TV, firmware, telecomando e metodo di installazione.

## Cosa puoi personalizzare?

Il launcher cambia la schermata usata per trovare e aprire le app del televisore. Puoi organizzare i preferiti e scegliere un layout come Classic, Liquid Glass o Ribbon. Prova la [demo nel browser](/clean-your-tv-lg-webos/demo/) per confrontare i layout prima di installare qualcosa. I comandi TV della demo sono simulati: non possono verificare la compatibilità con il tuo televisore.

Un launcher alternativo non sostituisce il firmware webOS, non sblocca servizi di streaming a pagamento e non elimina la pubblicità nelle altre app. Impostazioni immagine, ingressi e servizi di streaming restano funzioni separate del TV. Se cerchi soprattutto una schermata Home più tranquilla, leggi [cosa cambia per la pubblicità](/clean-your-tv-lg-webos/it/articles/lg-tv-home-screen-ads/).

## Quale metodo di installazione scegliere?

Usa No-root su un televisore con LG Developer Mode attiva. Home Helper, eseguito sul TV, gestisce il tasto Home dove è supportato. Developer Mode deve rimanere attiva: la scadenza della sessione può comportare la rimozione delle app installate al di fuori dello store.

Usa Root solo se il televisore dispone già di accesso root funzionante e soddisfa i requisiti di runtime e servizi. Il programma di installazione di Clean Your TV non esegue il root del TV. Non attivare Developer Mode su una configurazione già dotata di root e non usare contemporaneamente entrambi i metodi di gestione di Home. La [guida alle edizioni](/clean-your-tv-lg-webos/it/articles/root-vs-no-root/) spiega vantaggi e vincoli.

## Prima di modificare una configurazione funzionante

1. Annota modello esatto, firmware, versione webOS e tipo di telecomando. Confrontali con i [requisiti e i risultati segnalati sui TV](/clean-your-tv-lg-webos/it/compatibility/): ogni segnalazione riguarda la configurazione indicata.
2. Segui la [guida all'installazione](/clean-your-tv-lg-webos/it/install/) e usa il programma di installazione pubblicato a cui rimanda. Durante la configurazione, il TV e il dispositivo su cui esegui il programma devono essere su una rete che permetta loro di comunicare.
3. Dopo la configurazione verifica l'avvio delle app e il tasto Home, poi controlla separatamente audio, standby/riattivazione e avvio a freddo. La sola installazione riuscita di un pacchetto non verifica questi comportamenti.

## Come si torna a LG Home?

Nelle edizioni attualmente supportate, tre pressioni brevi di Home entro due secondi attivano l'uscita di emergenza. Le vecchie versioni di Home Helper fino alla 0.6.13 usano invece una pressione prolungata di due secondi. Aprire LG Home una volta e disattivare la gestione persistente del tasto Home sono operazioni diverse: consulta le [istruzioni di ripristino](/clean-your-tv-lg-webos/it/help/#home-button) per l'edizione installata. Prima di cambiare il comportamento all'avvio, assicurati di avere una via di ripristino disponibile.

## Fonti e approfondimenti

- [Riferimento del progetto su edizioni e comandi](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Installazione e prerequisiti del progetto](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode: mantenere disponibile una configurazione No-root](/clean-your-tv-lg-webos/it/articles/lg-developer-mode/)
