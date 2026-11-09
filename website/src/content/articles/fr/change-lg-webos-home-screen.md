---
lang: fr
topic: change-lg-webos-home-screen
title: "Comment changer l’écran d’accueil d’un téléviseur LG webOS"
description: "Personnalisez l’accueil de votre LG webOS avec Clean Your TV. Découvrez ce qu’un lanceur change, quelle édition choisir et quoi vérifier avant l’installation."
updated: '2026-11-09'
---

Clean Your TV est un écran d’accueil alternatif pour les téléviseurs LG webOS. Il permet de classer vos applications dans l’ordre souhaité et propose des thèmes ainsi qu’un dock personnalisable. Après la configuration, il fonctionne sur le téléviseur : vous pouvez donc éteindre votre ordinateur. La prise en charge du bouton Home dépend du téléviseur, du firmware, de la télécommande et de la méthode d’installation.

## Que peut-on personnaliser ?

Le lanceur modifie l’écran utilisé pour trouver et ouvrir les applications du téléviseur. Vous pouvez organiser vos favoris et choisir une présentation comme Classic, Liquid Glass ou Ribbon. Essayez la [démonstration dans le navigateur](/clean-your-tv-lg-webos/demo/) pour comparer les présentations avant toute installation. Les commandes du téléviseur y sont simulées ; elle ne permet pas de tester la compatibilité avec votre appareil.

Un lanceur alternatif ne remplace pas le firmware webOS, ne débloque pas le streaming payant et ne supprime pas les publicités dans les autres applications. Les réglages d’image, les entrées et les services de streaming restent des éléments distincts du téléviseur. Lisez [ce qui change concernant la publicité](/clean-your-tv-lg-webos/fr/articles/lg-tv-home-screen-ads/) si vous cherchez surtout un accueil plus sobre.

## Quelle méthode d’installation choisir ?

Utilisez No-root sur un téléviseur dont le LG Developer Mode est actif. Son Home Helper, exécuté sur le téléviseur, prend en charge le bouton Home lorsque cela est possible. Developer Mode doit rester actif ; l’expiration de la session peut entraîner la suppression des applications installées par ce mode.

Utilisez Root uniquement si le téléviseur dispose déjà d’un accès root fonctionnel et satisfait aux exigences d’environnement d’exécution et de services. L’installateur Clean Your TV ne roote pas le téléviseur. N’activez pas Developer Mode sur une configuration root existante et n’utilisez pas simultanément les deux méthodes de redirection de Home. Le [guide des éditions](/clean-your-tv-lg-webos/fr/articles/root-vs-no-root/) explique les différences.

## Avant de modifier une configuration qui fonctionne

1. Notez le modèle exact, le firmware, la version de webOS et le type de télécommande. Comparez-les aux [prérequis et résultats signalés sur les téléviseurs](/clean-your-tv-lg-webos/fr/compatibility/) ; chaque compte rendu s’applique à la configuration qui y est décrite.
2. Suivez le [guide d’installation](/clean-your-tv-lg-webos/fr/install/) et utilisez l’installateur publié qui y est lié. Pendant la configuration, le téléviseur et l’appareil d’installation doivent pouvoir communiquer sur le réseau.
3. Après la configuration, vérifiez l’ouverture des applications et Home, puis testez séparément le son, la mise en veille et la reprise, ainsi que le démarrage à froid. L’installation réussie d’un paquet ne valide pas ces comportements.

## Comment revenir à LG Home ?

Dans les éditions actuellement prises en charge, trois appuis courts sur Home en moins de deux secondes déclenchent la sortie d’urgence. Les anciennes versions de Home Helper jusqu’à la 0.6.13 utilisent un appui de deux secondes sur Home. Ouvrir LG Home une fois et désactiver la redirection persistante de Home sont deux actions différentes ; consultez les [instructions de récupération](/clean-your-tv-lg-webos/fr/help/#home-button) de votre édition installée. Gardez un moyen de récupération disponible avant de modifier le comportement au démarrage.

## Sources et étapes suivantes

- [Référence du projet : éditions et commandes](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Installation et prérequis du projet](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/INSTALL.md)
- [Developer Mode : garder une configuration No-root disponible](/clean-your-tv-lg-webos/fr/articles/lg-developer-mode/)
