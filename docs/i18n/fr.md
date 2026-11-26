# Clean Your TV — guide d’utilisation

Clean Your TV donne à votre LG webOS un écran d’accueil personnel: vos applications dans votre ordre, sans rangées sponsorisées dans ce menu. Installez-le depuis un ordinateur ou un téléphone Android ; l’ordinateur peut ensuite rester éteint.

## 1. Télécharger l’installateur

Cliquez sur l’image de votre appareil. Les boutons téléchargent la dernière version publiée. Sur Mac, choisissez Apple Silicon (M1 ou plus récent) ou Intel: menu Apple → À propos de ce Mac.

[![Télécharger — Windows x64](../../assets/brand/downloads/windows.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-windows-x64-desktop.zip)
[![Télécharger — macOS Apple Silicon](../../assets/brand/downloads/macos-arm64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-arm64.zip)
[![Télécharger — macOS Intel](../../assets/brand/downloads/macos-x64.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-macos-x64.zip)
[![Télécharger — Linux x64](../../assets/brand/downloads/linux.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-linux-x64.deb)
[![Télécharger — Android ARM64](../../assets/brand/downloads/android.svg)](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/latest/download/cytv-android-arm64.apk)

<a id="choisir-une-édition"></a>

<a id="prérequis"></a>

## 2. Choisir une édition

Allumez la TV et connectez-la au même réseau domestique que votre ordinateur ou téléphone. Autorisez CYTV à accéder au réseau local si demandé.

- **No-root** — si vous n’avez pas d’accès root. Configurez Developer Mode ci-dessous.
- **Root** — si vous avez déjà un accès root par SSH. L’installateur ne roote pas la TV. N’activez pas Developer Mode sur cette TV ; conservez l’accès SSH et les données de récupération.

Si l’installateur propose **No-root**, vous pouvez continuer avec votre connexion SSH root existante. Cette option ne nécessite pas Developer Mode.

[Guide d’installation détaillé](../INSTALL.md) · [Compatibilité](../COMPATIBILITY.md)

### Configurer Developer Mode (No-root)

Developer Mode permet à CYTV d’installer des apps sur un TV sans root.

1. Sur le TV, ouvrez LG Apps, cherchez Developer Mode et installez cette app.
2. Ouvrez Developer Mode et connectez-vous avec votre compte LG Developer. Si nécessaire, créez un compte sur [LG Developer](https://webostv.developer.lge.com).
3. Activez Dev Mode Status. Le TV redémarre. Ouvrez ensuite Developer Mode à nouveau.
4. Activez Key Server et laissez Developer Mode ouvert. Saisissez son IP Address comme adresse du TV dans CYTV.
5. Saisissez la Passphrase: les six caractères affichés dans Developer Mode sur le TV. Respectez les majuscules et minuscules.

Utilisez le code du TV, pas le mot de passe du compte LG. Si aucun code n’apparaît, activez Key Server.

L’appairage est une étape distincte: quand le TV le demande, autorisez CYTV avec la télécommande. Si le téléviseur refuse la demande, confirmez dans CYTV que vous souhaitez réessayer avec le même téléviseur.

Si la connexion à la commande à distance est refusée, laissez le téléviseur allumé et vérifiez depuis votre ordinateur l’accès au port TCP 3001. Choisissez ensuite **Réessayer** dans l’installateur pour ordinateur.

Si un avertissement indique que les entrées HDMI n’ont pas pu être lues lors de la première installation de No-root, vous pouvez continuer avec les applications détectées.

Gardez Developer Mode actif: avant la fin du compte à rebours, ouvrez-le et appuyez sur EXTEND avec le TV connecté à Internet. À expiration, LG peut supprimer ces apps.

<a id="installation-et-langue"></a>

## 3. Ouvrir l’installateur

- **Windows x64:** téléchargez `cytv-windows-x64-desktop.zip`, choisissez **Extraire tout** dans l’Explorateur, puis ouvrez `cytv-desktop/cytv-desktop.exe`. Gardez le dossier `_internal` à côté.
- **macOS 13+:** décompressez `cytv-macos-arm64.zip` pour Apple Silicon ou `cytv-macos-x64.zip` pour Intel. Placez `cytv.app` dans Applications et ouvrez-la ; autorisez l’accès au réseau local. En cas de blocage d’un téléchargement fiable, utilisez Confidentialité et sécurité → Ouvrir quand même, sans désactiver Gatekeeper.
- **Linux x64:** sous Ubuntu 22.04+, Debian 12+ ou Mint 21+, installez `cytv-linux-x64.deb` avec le gestionnaire graphique de paquets, puis ouvrez Clean Your TV depuis le menu. Internet peut être nécessaire pour les bibliothèques. Linux ARM n’est pas fourni.

**Android ARM64:** utilisez un téléphone ARM 64 bits avec Android 7+ et WebView/Chrome 108+. Ouvrez l’APK téléchargé et autorisez l’installation depuis cette source si Android le demande. Ouvrez CYTV ; la langue se choisit en haut à droite. Mettez à jour sans désinstaller ni effacer les données.

L’assistant utilise initialement la langue du système et mémorise votre choix explicite. Sur le téléviseur, ouvrez **Paramètres → Langue** et choisissez une langue ou l’option automatique du système. Les préférences du téléviseur et de l’installateur sont indépendantes. Les codes figurent dans l’[index des langues](../LANGUAGES.md).

## 4. Installer sur le téléviseur

1. Dans CYTV, choisissez **Configurer mon téléviseur**. Sur ordinateur, sélectionnez une TV détectée ; sur Android, saisissez son adresse IP. Si la recherche ne trouve rien, saisissez l’adresse manuellement.
2. Choisissez **No-root** ou **Root** et vérifiez le téléviseur sélectionné avant de continuer.
3. No-root: saisissez le code de Developer Mode et acceptez la demande sur la TV. Root: utilisez vos identifiants SSH. N’acceptez une nouvelle identité SSH que pour votre propre TV sur un réseau fiable. Si une clé enregistrée a changé, arrêtez-vous et recherchez la cause.
4. Suivez l’assistant. Gardez la TV allumée, le même réseau et CYTV ouvert jusqu’à la fin. Ne forcez pas l’arrêt de l’application Android.

Dans l’installateur pour ordinateur, après une vérification réussie de la connexion, choisissez **Continuer la configuration** pour conserver la même connexion et la même édition. L’assistant explique l’état d’une installation précédente ; les résultats techniques sont dans **Détails**. Si une opération précédente nécessite une récupération, utilisez d’abord l’action proposée. L’assistant vérifie les versions installées et demande confirmation avant toute modification. Les demandes de redémarrage enregistrées sont revérifiées ; l’assistant ne demande un redémarrage que si le nettoyage en cours le nécessite.

Si l’installateur Root propose de remplacer l’intégration Home actuelle, confirmez uniquement si vous souhaitez rétablir LG Home et poursuivre. En cas de refus, le Home actuel reste actif.

Pour la configuration Root, l’installateur utilise automatiquement un stockage temporaire interne vérifié si nécessaire ; aucune clé USB n’est requise et, si la vérification du stockage échoue, conservez les données de récupération et enregistrez un rapport de diagnostic.

## 5. Vérifier la télécommande

1. Ouvrez une autre application sur la TV et appuyez brièvement sur **Home**. Clean Your TV doit s’ouvrir. Indiquez votre observation dans l’assistant ; ignorez le test si vous ne l’avez pas effectué.
2. Vérifiez flèches, OK, Retour, volume et son.

<a id="utilisation-et-récupération"></a>

## 6. Utilisation et récupération

Pour migrer l’environnement de démarrage de Root Beta existant, désactivez **Change Home** et exécutez `cytv migrate-root-beta --edition root --root-variant node012-beta` avec la connexion Root SSH enregistrée. L’application et les préférences sont conservées. La migration s’arrête si une désinstallation précédente a déjà modifié l’installation. Ensuite, activez Change Home et choisissez les sources de démarrage dans les paramètres Home.

Pour épingler une entrée HDMI, sélectionnez-la dans **+ / Ajouter une application**. Appuyez sur OK pour basculer vers cette entrée. Maintenez OK pour déplacer ou masquer sa tuile.

Les flèches sélectionnent, OK ouvre ; maintenez OK pour réorganiser. Un appui bref sur Retour conserve la navigation et la confirmation de sortie de l’application. Home ouvre le lanceur si le contrôle est actif.

Pour modifier les tuiles avec des appuis courts, ouvrez **Paramètres de Home → Apparence → Modifier les tuiles**. Appuyez sur OK pour sélectionner une tuile, déplacez-la avec les flèches puis appuyez sur OK pour la poser. Retour annule le déplacement ou quitte la modification.

Si la télécommande se déconnecte temporairement, laissez la commande de Home activée. Elle reprend dès que le téléviseur détecte à nouveau la télécommande.

**Appuyez trois fois sur Home en deux secondes**, en relâchant entre les appuis. Cela rétablit LG Home et arrête le contrôle sans effacer vos préférences.

No-root: Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé. Root: activez **Changer Home** dans les paramètres de Home pour reprendre. **Ouvrir LG Home** ouvre LG Home une fois sans modifier la destination de Home. Pour rétablir LG Home comme destination permanente, désactivez **Changer Home**. N’exécutez jamais les deux contrôleurs ensemble. Si la panne revient, laissez LG Home actif.

Si Home Helper est arrêté, vous pouvez aussi choisir **Démarrer Helper** dans les paramètres de l’écran Home ou de l’économiseur d’écran. L’état se met à jour automatiquement après le démarrage.

Sur les téléviseurs où LG Home s’ouvre sous forme de panneau, activer ou désactiver **Change Home** dans Root peut redémarrer brièvement l’interface du téléviseur. Après un redémarrage ou une panne, ouvrez Clean Your TV et réactivez **Change Home** pour reprendre le contrôle. LG Home reste accessible.

Pour libérer de la place après le retour à une version antérieure de Home, ouvrez **Paramètres → Thèmes**, choisissez **Supprimer** pour le thème téléchargé indisponible et confirmez.

## Besoin d’aide ?

Si `ssh-identity-changed` s’affiche, arrêtez-vous et vérifiez la clé SSH du téléviseur. [Récupération après un changement de clé SSH](../RECOVERY.md#ssh-identity-changed)

Après avoir réinitialisé votre téléviseur No-root aux réglages d’usine, choisissez **Reconnecter après la réinitialisation d’usine** si la clé a changé. Suivez les étapes sur votre réseau domestique de confiance. L’ancien profil et le dossier de désinstallation sont conservés.

Si l’installation reste inachevée sur ordinateur, choisissez **Examiner les options de récupération** sur l’écran des résultats, puis **Continuer** à la question **Vérifier les options de récupération ?**. L’assistant utilise la même connexion enregistrée au téléviseur. Avec No-root, si le résultat concernant les paquets est inconnu, choisissez d’abord **Vérifier l’état du téléviseur** si ce bouton est proposé. Confirmez séparément la modification proposée. Si l’installation reste bloquée, conservez la connexion et les données de récupération.

Si No-root propose **Relancer la vérification du stockage**, choisissez cette option pour vérifier le même téléviseur en lecture seule. Une fois la vérification réussie, confirmez l’installation séparément. Si une opération reste en cours, choisissez **Examiner les options de récupération**.

Si l’installateur de bureau a vérifié les paquets mais que la touche Home n’ouvre pas Clean Your TV, choisissez **Diagnostic du bouton Home** avec No-root ou **Vérifier l’état du téléviseur** avec Root sur l’écran des résultats. Avec No-root, le résultat déjà enregistré s’affiche. Utilisez **Enregistrer le rapport de diagnostic** pour en conserver une copie.

Pour garder une copie sur ordinateur, choisissez **Enregistrer le rapport de diagnostic…** sur l’écran des résultats. Pour demander de l’aide, choisissez **Signaler un problème**, relisez le brouillon, puis choisissez **Copier le brouillon** et **Ouvrir le formulaire**. Collez le brouillon et joignez le rapport enregistré si vous en avez un.

[Signaler un problème](../FEEDBACK.md) · [Récupération — anglais](../RECOVERY.md) · [Mettre à jour ou supprimer — anglais](../MAINTENANCE.md) · [Autres langues](../LANGUAGES.md)

### Suppression simple

Choisissez **Désinstaller Clean Your TV** dans Maintenance avec la même connexion enregistrée. Confirmez une fois. Les applications et fichiers connus du projet présents sont supprimés ; les éléments absents sont ignorés, même après une installation partielle.

Quand demandé, débranchez l’alimentation TV, rebranchez-la, attendez le retour du réseau. Veille ou Quick Start n’est pas un redémarrage complet ; CYTV ne redémarre pas le téléviseur automatiquement. Si le nettoyage nécessite un accès Root, utilisez votre connexion Root existante au même téléviseur. Sans cet accès, le nettoyage reste incomplet. Si le téléviseur est occupé, patientez et réessayez. Le succès apparaît seulement après vérification du nettoyage final. Gardez les clés et rapports d’origine. Les commandes d’urgence et le consentement au partage restent applicables.

Si l’installateur sur ordinateur attend le téléviseur, choisissez **Poursuivre la désinstallation** quand le bouton apparaît. Choisissez **Annuler** pour arrêter l’attente ou **Réessayer** pour vérifier la connexion manuellement.

Si **Revenir à LG Home** apparaît pendant la désinstallation, sélectionnez cette option. Une fois la restauration vérifiée, choisissez **Poursuivre la désinstallation**. Si vous revenez à LG Home directement depuis le menu de maintenance, les applications restent installées.

Si l’installateur ne peut pas vérifier la suppression, le nettoyage final, les commandes du téléviseur ou le résultat de l’opération sur les paquets, ou signale des chemins de projet modifiés, choisissez **Examiner les options de récupération** avec la connexion d’origine enregistrée. Confirmez séparément la poursuite si l’installateur la propose. Si la récupération d’une installation No-root propose **Vérifier l’état du téléviseur**, choisissez cette option et conservez les données de récupération.

Si l’installateur ne peut pas vérifier le redémarrage complet demandé, enregistrez et joignez le rapport de diagnostic. Conservez la connexion enregistrée et les données de récupération. Ne répétez pas les coupures de courant et n’effacez pas manuellement l’opération inachevée.

Quand l’installateur sur ordinateur affiche **La suppression de Clean Your TV est vérifiée.**, choisissez **Fermer** pour terminer ou **Configurer mon téléviseur** pour lancer une nouvelle installation sur le même téléviseur avec la même édition et la même connexion.

**Réinstaller Root :** Choisissez **Configurer mon téléviseur → Root** avec la connexion enregistrée et confirmez **Réinstaller Root ?**. L’installateur rétablit LG Home et supprime entièrement Clean Your TV, ses outils de mise à jour, Home Helper et les préférences enregistrées. Après vérification de la suppression, il installe et active les paquets et l’environnement Root fournis avec cet installateur. Les autres apps du TV et l’accès root/SSH existant sont conservés. Si l’assistant sur ordinateur s’interrompt, ouvrez le même installateur et choisissez **Reprendre la réinstallation de Root**. Après vérification de la suppression, choisissez **Poursuivre l’installation de Root**. **Désinstaller Clean Your TV** seul ne lance jamais une nouvelle installation.

Si l’assistant demande un redémarrage complet pendant le nettoyage, débranchez le téléviseur, rebranchez-le et allumez-le. Une fois le démarrage terminé, choisissez **J’ai redémarré le téléviseur — vérifier et continuer**.

### Modifier les réglages LG et terminer la récupération Root

Dans l’installateur de bureau, ouvrez **Action de maintenance → Ajuster les réglages LG (Debloat)** avec la connexion TV enregistrée. Sélectionnez les réglages à modifier, choisissez **Appliquer les réglages sélectionnés**, puis vérifiez les résultats. Si une opération reste en attente, choisissez d’abord **Examiner les options de récupération** avec sa connexion d’origine enregistrée.

- [Root Updater](../RECOVERY.md#standalone-root-updater-rollback-readiness)
- [Root System Updater](../RECOVERY.md#root-system-rollback-readiness-candidate)

<!-- Legacy anchors retained for existing links. Detailed references: -->
<a id="python-facultatif-pour-root-dans-v110"></a>
<a id="blocage-du-micrologiciel-lg-dans-120"></a>
<a id="nouveautés-de-130-récupération-guidée-sur-ordinateur"></a>
<a id="nouveautés-de-130--12"></a>
<a id="candidat-non-publié--installer-root-avec-homebrew"></a>
<a id="candidat-non-publié--récupération-du-son-hdmi-root"></a>
<a id="thèmes-154"></a>
<a id="catégories-des-paramètres-candidat-non-publié"></a>
<a id="résolution-graphique-automatique-candidat"></a>
<a id="mises-à-jour-et-suppression"></a>
<a id="aide-et-autres-instructions"></a>
<a id="thèmes"></a>
<a id="catégories-des-paramètres-154"></a>
<a id="résolution-graphique-automatique-160"></a>
<a id="espace-de-stockage"></a>

Références détaillées en anglais: [prérequis](../COMPATIBILITY.md) · [commandes](../CONTROLS.md) · [thèmes](../THEMES.md) · [mises à jour](../UPDATES.md).

<a id="candidat-unreleased--ancien-nodejs-du-tv"></a>
<a id="ancien-nodejs-du-tv-publié-dans-v1120"></a>
<a id="suppression-simple-v1110"></a>

## Réglages

En l’absence de préférence enregistrée, l’économiseur d’écran est activé par défaut. Pour le désactiver, ouvrez **Réglages de Home → Économiseur d’écran**.

Dans **Réglages → Apparence**, activez **Applications les plus utilisées en premier**. L’ordre du dock est conservé. Maintenez OK pour déplacer ou masquer une tuile dans l’ordre manuel. Désactivez l’option pour revenir à l’ordre manuel. L’option figure aussi à la fin des réglages du programme d’installation cytv.

Utilisez ↑ ↓ pour choisir une catégorie, puis → ou OK pour y entrer. ← revient aux catégories ; Retour y revient d’abord, puis ferme les réglages. En revenant dans une section, le dernier contrôle disponible reprend le focus. Dans Colonnes, les flèches suivent la grille de trois colonnes. Dans Langue, le focus se place sur la langue choisie.

Dans **Réglages → Votre écran Home → Format de l’heure**, choisissez **Automatique (région du téléviseur)**, **12 heures** ou **24 heures**.

Dans l’édition No-root, ouvrez **Réglages → Votre écran Home → Rester sur HDMI ou la TV en direct à la sortie de veille**.

Si le téléviseur affiche déjà une console, la TV en direct ou une autre entrée à la sortie de veille, cet écran reste affiché. Le bouton Home fonctionne comme d’habitude. L’option est désactivée par défaut.

Si No-root ne peut pas lire l’état de Home, choisissez Réessayer. Un contrôle indisponible ne signifie pas que Home est désactivé. Dans Fonds d’écran, transférez une image depuis le téléphone ou CYTV ; qualité et assombrissement apparaissent lorsqu’un fond est disponible. La suppression d’un fond personnel demande confirmation ; Annuler le conserve.

## Météo

Ouvrez Réglages → Météo, sous Fonds d’écran. Activez la météo puis ouvrez Ville pour rechercher et choisir la bonne région et le bon pays, ou choisissez Automatique pour une ville approximative selon votre connexion. Un VPN peut modifier le résultat ; utilisez la recherche manuelle si la ville manque ou est incorrecte. La ville détectée ou choisie apparaît dans les réglages. Choisissez °C / m/s ou °F / mph et un format disponible : compact, actuel, détaillé ou quatre jours. L’aperçu suit le thème ; Exemple indique des données fictives. Liquid Glass accepte uniquement le format compact. Ribbon et Atmosphere n’affichent pas la météo. La désactivation arrête les requêtes et masque la ville, les unités et le format ; le choix de la source reste disponible. En cas de panne, les données récentes peuvent rester temporairement ; ensuite la météo est masquée jusqu’à son actualisation.

Choisissez la source des prévisions : Auto, MET Norway ou Open-Meteo. Auto commence par MET Norway, essaie une fois Open-Meteo en cas d’échec, puis réutilise la dernière source fonctionnelle et son cache. Le choix manuel ne change jamais automatiquement de source. Les nouveaux réglages utilisent Auto ; les anciens réglages sans source conservent Open-Meteo. La source réelle est affichée. La disponibilité dépend du réseau. MET s’actualise au plus toutes les trois heures ; le cache expire après six heures. Les champs absents sont masqués : MET ne fournit ni température ressentie ni probabilité de précipitations. Les plages quotidiennes résument des points de prévision, pas des extrêmes mesurés.

Les coordonnées sont envoyées à api.met.no ou api.open-meteo.com, les recherches de villes à geocoding-api.open-meteo.com. La localisation automatique facultative transmet votre IP publique à get.geojs.io. Les connexions utilisent HTTPS ; aucune clé API n’est nécessaire. Le lieu, la source et le cache restent sur le téléviseur. Sources des données présente les conditions et crédits, dont l’Institut météorologique norvégien (MET Norway, CC BY 4.0).

Le bouton Sources des données dans l’en-tête Météo ouvre les informations sur les services et licences.

## Photo iPhone comme fond d’écran

Ouvrez Paramètres → Fonds d’écran → Envoyer depuis le téléphone et scannez le code. Choisissez JPG, PNG ou HEIC/HEIF, recadrez, acceptez la limite de qualité et envoyez. Choisissez Appliquer sur le TV. Safari utilise HEIC natif ; Chrome, Firefox et les autres navigateurs modernes utilisent le décodeur local inclus si nécessaire. La conversion reste sur le téléphone, sans service externe. Annuler ou changer de fichier arrête la conversion. Entrée : 32 Mio et 50 millions de pixels ; sortie : 1080p et 2 Mio maximum. En cas d’échec, essayez une autre photo ou JPG/PNG. Cela concerne la page du téléphone, pas l’app Mac.

## Configurer votre Clean Your TV

Avant de choisir un thème, utilisez **Debloat** pour sélectionner les réglages LG de publicité, de recommandations, de confidentialité et de notifications à modifier. Vérifiez chaque résultat. Si la valeur d’origine ne peut pas être lue, elle ne peut pas être enregistrée pour une restauration automatique. Choisissez **Ignorer Debloat** pour conserver vos réglages.

Les deux éditions peuvent désactiver les flux promotionnels LG si le téléviseur propose ce réglage. Dans Root, vous pouvez désactiver séparément le préchargement de Netflix, de YouTube ou du navigateur pour la session en cours. Ces options sont décochées par défaut. L’application peut mettre plus de temps à s’ouvrir. Le téléviseur peut reprendre le préchargement après une veille ou un redémarrage.

Lors de la désinstallation, vous pouvez rétablir les valeurs d’origine enregistrées par Debloat. Si vous ignorez la restauration, la désinstallation se poursuit sans modifier ces réglages.

Après une installation réussie, choisissez Classic, Liquid Glass ou Ribbon et activez ou désactivez la météo. Ribbon ne prend pas en charge la météo ; Liquid Glass utilise le format compact. La ville est estimée selon votre connexion et peut être modifiée dans Home.

No-root avec Developer Mode propose la prolongation automatique ; surveillez toujours le compteur officiel. Dans les nouvelles installations No-root via un accès SSH root existant, l’onglet Developer Mode est masqué. Root permet de bloquer les mises à jour du micrologiciel LG via Homebrew Channel, y compris celles de sécurité ; un vrai redémarrage via Homebrew Channel est requis. Les mises à jour CYTV restent distinctes.

Conserver les réglages actuels permet de passer la personnalisation. L’interrupteur affiche l’état actuel de la fonction du mode. Les réglages inchangés sont conservés. La réinstallation Root supprime toujours les préférences CYTV comme indiqué plus haut. Vérifiez l’apparence sur le TV et les options non confirmées dans Home avant de réessayer.

## Mises à jour sur un téléviseur avec root

Si un System Updater capable de se mettre à jour est configuré, utilisez **Mises à jour logicielles → Tout mettre à jour** pour Root ou No-root sur un téléviseur avec root. Gardez le téléviseur allumé jusqu’à la fin. Pour réparer uniquement l’outil de mise à jour, ouvrez Home puis **Mises à jour logicielles → Récupération → Réinstaller System Updater** ; Home et vos réglages sont conservés. No-root sans accès root utilise toujours l’installation depuis l’ordinateur.
