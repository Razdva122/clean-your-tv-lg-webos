---
lang: fr
topic: root-vs-no-root
title: "Root ou No-root pour un lanceur LG webOS"
description: "Choisissez l’édition Clean Your TV adaptée à votre LG webOS. Comparez accès, entretien de Developer Mode, contrôle de Home et récupération avant l’installation."
updated: '2026-11-09'
---

Choisissez No-root si votre téléviseur LG utilise Developer Mode. Choisissez Root uniquement s’il dispose déjà d’un accès root fonctionnel et de services compatibles. Les deux éditions de Clean Your TV proposent la même interface d’accueil et fonctionnent sur le téléviseur après l’installation. L’installateur n’obtient pas d’accès root et ne flashe pas le firmware.

## Que nécessite No-root ?

No-root utilise LG Developer Mode, Key Server et un appairage local pendant la configuration. Home Helper fonctionne sur le téléviseur et prend en charge le bouton Home lorsque l’appareil et le firmware le permettent. Il n’est pas nécessaire de laisser un ordinateur ou un téléphone allumé pour l’utilisation quotidienne.

L’exigence permanente est Developer Mode : prolongez sa session avant son expiration. LG avertit que les applications installées via Developer Mode peuvent être supprimées lors de sa désactivation ou de l’expiration de la session. Le renouvellement automatique du projet est une option bêta désactivée par défaut ; ne le considérez pas comme une garantie. Lisez le [guide Developer Mode](/clean-your-tv-lg-webos/fr/articles/lg-developer-mode/) avant de vous appuyer sur cette édition.

## Que nécessite Root ?

Root utilise un accès SSH root existant, des services TV compatibles et des capacités d’entrée et d’exécution prises en charge. L’accès root seul ne prouve pas la compatibilité. L’installateur vérifie l’environnement ; ne contournez pas un prérequis refusé et ne remplacez pas les environnements d’exécution du système pour forcer la validation.

Root utilise des paquets et une redirection de Home distincts. N’activez pas Developer Mode sur une configuration root existante et arrêtez Home Helper de No-root avant d’utiliser la redirection Root. Le choix de l’édition dépend de l’accès dont vous disposez déjà ; ce n’est pas un bouton qui va rooter le téléviseur.

## Comparer l’entretien et la récupération

- **Utilisation quotidienne :** les deux éditions fonctionnent sur le téléviseur, avec les applications et les thèmes dans le lanceur.
- **Entretien de No-root :** gardez Developer Mode actif et conservez l’appairage et la connectivité nécessaires à Helper.
- **Entretien de Root :** gardez disponibles les services de récupération indépendants et leur environnement d’exécution requis. La disponibilité des mises à jour dépend de l’édition installée et du parcours de mise à jour pris en charge ; l’accès root seul n’active pas les mises à jour OTA.
- **Sortie d’urgence :** les éditions actuellement prises en charge utilisent trois appuis courts sur Home en moins de deux secondes. Home Helper jusqu’à la version 0.6.13 utilise à la place un appui de deux secondes.

Après un arrêt d’urgence, le redémarrage de la redirection persistante demande une action explicite. Dans No-root, ouvrez Home Helper et choisissez « Start Helper » ; dans Root, utilisez « Change Home » dans les réglages Home. Consultez la [comparaison des éditions](/clean-your-tv-lg-webos/fr/editions/) et l’[aide à la récupération](/clean-your-tv-lg-webos/fr/help/#home-button).

## Vérifier le téléviseur avant l’installation

Lisez la [page de compatibilité](/clean-your-tv-lg-webos/fr/compatibility/) avec le modèle exact, le firmware, webOS et la télécommande à portée de main. Les résultats signalés concernent une configuration précise. Testez séparément Home, l’ouverture des applications, le son, la veille et le démarrage à froid après la configuration. L’installation d’un paquet ne prouve pas que tous ces éléments fonctionnent.

Utilisez l’[installateur publié et le guide d’installation](/clean-your-tv-lg-webos/fr/install/). Si vous disposez déjà d’une configuration fonctionnelle et souhaitez changer d’édition, suivez les étapes documentées de transition et de suppression au lieu d’installer une édition par-dessus l’autre.

## Sources et étapes suivantes

- [Comparaison des éditions du projet](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/EDITIONS.md)
- [Prérequis et limites connues du projet](https://github.com/Razdva122/clean-your-tv-lg-webos/blob/main/docs/COMPATIBILITY.md)
- [Ce que change un autre écran d’accueil](/clean-your-tv-lg-webos/fr/articles/change-lg-webos-home-screen/)
