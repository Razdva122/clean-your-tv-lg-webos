# Clean Your TV — guide d’utilisation

> v1.5.0 : thèmes, galerie et transfert du PC au téléviseur. Limites Root connues : Appearance peut se décaler de 110 px ; Home peut ne pas s’ouvrir automatiquement après la veille. La validation par appareil reste limitée. [1.5.0](../RELEASE-1.5.0.md).

[Documentation](../README.md) · [Signaler un problème](../FEEDBACK.md)

Ce guide décrit la version publiée **[1.4.1](https://github.com/Razdva122/clean-your-tv-lg-webos/releases/tag/v1.4.1)**. La validation C3 couvre les essais consignés d’alimentation, Home, focus, maintien de la désactivation et retour manuel à la version précédente. Les autres TV, le son eARC et les appareils Android physiques restent non vérifiés ; une installation réussie ne prouve pas la compatibilité. [Périmètre testé (anglais)](../RELEASE-1.4.0-ACCEPTANCE.md).

**Installateur non publié :** console, ordinateur et Android indiquent chaque vérification du TV : non effectuée, en cours, réussie, échouée ou invérifiable. Les résultats restent visibles après une erreur. Node.js/Python est vérifié sur le TV ; `doctor` ne prépare pas Python et ne demande pas d’association de contrôle. Enregistrez le rapport avant de réessayer.

## Choisir une édition

No-root et Root sont des options équivalentes pour différentes configurations du téléviseur. Choisissez No-root pour LG Developer Mode ou Root si vous disposez déjà d’un accès root par SSH. La compatibilité et les essais réalisés sont propres à chaque édition.

- **No-root :** activez LG Developer Mode et Key Server. Saisissez la phrase secrète affichée sur le téléviseur et acceptez sur celui-ci la demande d’association distincte. Developer Mode doit rester actif : son expiration peut supprimer les applications installées ainsi. Surveillez son compteur officiel même avec le renouvellement Beta activé. La surveillance du Helper nécessite le réseau local.
- **Root :** un accès SSH root existant est nécessaire. L’installateur ne roote pas le téléviseur. N’activez pas Developer Mode sur une installation déjà rootée. Conservez l’accès root et les services de récupération.

Root nécessite les interfaces Home fonctionnelles de Settings Service et System Profile (`com.webos.service.systemprofile`) ; un accès root seul ne garantit pas la compatibilité.

## Prérequis

Allumez le téléviseur et reliez-le au même réseau local de confiance que l’ordinateur. L’ordinateur peut ensuite rester éteint. La compatibilité dépend du modèle, du micrologiciel et de la télécommande ; des essais matériels restent à terminer pour Root.

No-root Helper nécessite Node.js **0.12.2+** sur la TV. Root nécessite Node.js **8+** et Python **3.9+** fonctionnel. Au besoin, l’installateur télécharge un Python privé vérifié ; la préparation initiale demande **320 MiB** libres. Il ne remplace pas Python système. Conservez les environnements utilisés par la récupération. [Python (anglais)](../OPTIONAL-PYTHON.md). Le renouvellement Developer Mode est **Beta, désactivé par défaut** ; son fonctionnement réel sans root n’est pas confirmé. Surveillez toujours le compteur officiel.

### Configurer Developer Mode (No-root)

Developer Mode permet à CYTV d’installer des apps sur un TV sans root.

1. Sur le TV, ouvrez LG Apps, cherchez Developer Mode et installez cette app.
2. Ouvrez Developer Mode et connectez-vous avec votre compte LG Developer. Si nécessaire, créez un compte sur webostv.developer.lge.com.
3. Activez Dev Mode Status. Le TV redémarre. Ouvrez ensuite Developer Mode à nouveau.
4. Activez Key Server et laissez Developer Mode ouvert. Saisissez son IP Address comme adresse du TV dans CYTV.
5. Saisissez la Passphrase : les six caractères affichés dans Developer Mode sur le TV. Respectez les majuscules et minuscules.

Utilisez le code du TV, pas le mot de passe du compte LG. Si aucun code n’apparaît, activez Key Server.

L’appairage est une étape distincte : quand le TV le demande, autorisez CYTV avec la télécommande.

Gardez Developer Mode actif : avant la fin du compte à rebours, ouvrez-le et appuyez sur EXTEND avec le TV connecté à Internet. À expiration, LG peut supprimer ces apps.

## Installation et langue

- **Windows x64 :** téléchargez `cytv-windows-x64-desktop.zip`, choisissez **Extraire tout** dans l’Explorateur, puis ouvrez `cytv-desktop/cytv-desktop.exe`. Gardez le dossier `_internal` à côté. La signature d’éditeur Windows n’est pas configurée. La console séparée est `cytv-windows-x64.exe` ; renommez-la en `cytv.exe` et utilisez `.\cytv.exe` dans PowerShell pour les commandes suivantes.
- **macOS 13+ :** décompressez `cytv-macos-arm64.zip` pour Apple Silicon ou `cytv-macos-x64.zip` pour Intel. Placez `cytv.app` dans Applications et ouvrez-la ; autorisez l’accès au réseau local. En cas de blocage d’un téléchargement fiable, utilisez Confidentialité et sécurité → Ouvrir quand même, sans désactiver Gatekeeper. La validation sur les anciens systèmes reste ouverte.
- **Linux x64 :** sous Ubuntu 22.04+, Debian 12+ ou Mint 21+, installez `cytv-linux-x64.deb` avec le gestionnaire graphique de paquets, puis ouvrez Clean Your TV depuis le menu. Internet peut être nécessaire pour les bibliothèques. Linux ARM n’est pas fourni. L’exécutable autonome `cytv-linux-x64` est la CLI ; utilisez le `.deb` pour l’application graphique.

[Installateur Android (anglais)](../../android/README.md) : choisissez la langue en haut à droite. Mettez à jour sans désinstaller ni effacer les données. Android 7 / WebView 108 est le minimum, pas un téléphone validé ; la validation utilise un émulateur Android 15 ARM64 / WebView 124. Les téléphones physiques et la récupération reliée à une vraie TV restent non vérifiés.

L’assistant utilise initialement la langue du système et mémorise votre choix explicite. Sur le téléviseur, ouvrez **Paramètres → Langue** et choisissez une langue ou l’option automatique du système. Les préférences du téléviseur et de l’installateur sont indépendantes. Les codes figurent dans l’[index des langues](../LANGUAGES.md).

Pour la CLI téléchargée séparément sous macOS/Linux, depuis son dossier décompressé :

```sh
chmod +x cytv
./cytv --language fr install
```

Choisissez le téléviseur ou son adresse IP, l’édition, puis vérifiez le récapitulatif. N’acceptez une nouvelle identité SSH que pour votre téléviseur sur un réseau fiable ; une clé enregistrée modifiée bloque la connexion. Root prépare la récupération et active Home immédiatement, sans essai temporaire ni étape de conservation. Testez flèches, OK, Home, Retour/Annuler, volume, veille et démarrage à froid.

## Utilisation et récupération

Les flèches sélectionnent, OK ouvre ; maintenez OK pour réorganiser. Un appui bref sur Retour conserve la navigation et la confirmation de sortie de l’application. Home ouvre le lanceur si le contrôle est actif. Maintenez Retour pendant 1,2 seconde pour ouvrir LG Home une fois. L’interrupteur du contrôle de Home et vos paramètres restent inchangés.

**Appuyez trois fois sur Home en deux secondes**, en relâchant entre les appuis. Cela rétablit LG Home et arrête le contrôle sans effacer vos préférences. Avec No-root Helper jusqu’à 0.6.13 inclus, maintenez plutôt Home environ deux secondes. Maintenir Home n’est pas le geste d’urgence de Root.

No-root: Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé. Root : activez **Changer Home** dans les paramètres de Home pour reprendre. **Ouvrir LG Home** ouvre LG Home une fois sans modifier la destination de Home. Pour rétablir LG Home comme destination permanente, désactivez **Changer Home** ou exécutez `cytv restore`. N’exécutez jamais les deux contrôleurs ensemble. Si la panne revient, laissez LG Home actif.

```sh
./cytv --language fr status
./cytv --language fr doctor --report
./cytv --language fr restore
./cytv --language fr uninstall
```

Après interruption, lancez d’abord `status` et conservez les journaux. `restore` rétablit LG Home sans supprimer les applications ; `uninstall` le rétablit avant leur suppression. Les données de récupération Root sont conservées volontairement : ne les effacez pas pour forcer une réinstallation. Vérifiez les rapports avant partage ; ne publiez ni clés ni dossiers de profils.

Uniquement dans la version candidate non publiée, dans les deux éditions : ouvrez **Paramètres de Home → Apparence → Colonnes** et choisissez de 1 à 8 colonnes, ou **Selon le thème** pour utiliser sa valeur (Classic : 5). Un nombre explicite est prioritaire sur le thème. Les thèmes à disposition fixe masquent l’option Colonnes et utilisent la valeur de l’auteur. Votre choix enregistré est rétabli lorsque vous passez à un thème qui prend en charge ce réglage. Dans l’aperçu candidat Alpine, les applications forment un ruban horizontal en boucle : Gauche/Droite fait défiler, Haut ouvre les raccourcis et Bas revient à la même application. Dans l’aperçu Alpine, la molette ou le pavé tactile fait aussi défiler le ruban ; Home reste immobile derrière une boîte de dialogue ouverte.

Candidat non publié, dans les deux éditions : dans **Paramètres Home → Apparence**, désactivez **Afficher la tuile « Ajouter une app »** pour masquer +. Cette option est activée par défaut. Utilisez **Ajouter une app** dans la même section pour ajouter ou rétablir des apps lorsque + est masqué. Le déplacement et le masquage restent disponibles ; le choix est conservé au redémarrage. Si toutes les apps sont masquées, les commandes du haut et les paramètres restent accessibles.

Dans les aperçus de thèmes du candidat non publié avec barre latérale facultative, Haut/Bas sélectionne une entrée du menu, Droite passe aux applications et Gauche depuis leur première colonne revient au menu.

No-root 1.5.0 : Helper peut récupérer après un délai watchdog temporaire à la sortie de veille, avec au maximum cinq tentatives en dix minutes. Stop et trois pressions sur Home exigent toujours un démarrage explicite de Helper ; les échecs répétés le laissent arrêté. La validation sur TV reste à faire. [Comportement et limites (anglais)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Mises à jour et suppression

Gardez les paquets fonctionnels et des sauvegardes privées des paramètres. Pour remplacer les paquets No-root depuis l’ordinateur, arrêtez d’abord Helper et mettez à jour sans désinstaller : la désinstallation peut effacer les réglages. Supprimer l’application de bureau ne supprime pas les applications TV. Ne remplacez pas un environnement Root actif par une IPK isolée ; utilisez le parcours explicite de récupération ou de réinstallation de cytv.

Ouvrez les paramètres Home → Mises à jour et vérifiez les versions avant confirmation. Mise à jour et retour arrière sur TV nécessitent **root, Homebrew Channel** et les composants de mise à jour correspondants préparés, même pour No-root. Sans root, utilisez l’ordinateur. La préparation des mises à jour complètes est une action explicite distincte : [mises à jour (anglais)](../UPDATES.md). Récupération indique la version sauvegardée ; les réglages ultérieurs peuvent être perdus lors du retour arrière.

**Installation 1.3.0 existante :** le System Updater d’origine ne peut pas appliquer 1.4.0 car la liste des fichiers autorisés a changé. Si un essai s’arrête avant le remplacement, conservez son journal et arrêtez ; n’effacez pas l’état et ne réessayez pas à l’aveugle. Passez par la récupération vérifiée puis une nouvelle installation 1.4.0 ; une mise à jour de l’app seule ne remplace pas les pilotes Root conservés. La prochaine correction OTA **n’est pas publiée**. [Migration et récupération (anglais)](../UPDATES.md#one-time-computer-preparation).

Correction non publiée du canal des réglages Home : mettre à jour Home et Helper ensemble lorsqu’un candidat coordonné sera disponible. Une mise à jour de Home seul ne suffit pas. La validation sur TV de la compilation finale reste à faire. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

La récupération audio HDMI Root est expérimentale et **désactivée par défaut** ; activez-la uniquement si nécessaire. Elle peut interrompre un son fonctionnel et ne valide pas eARC. [Récupération audio (anglais)](../development/ROOT-AUDIO-RECOVERY.md). Le **CYTV Installer Homebrew reste non publié** ; utilisez l’installateur publié pour ordinateur ou Android.

Homebrew Channel a refusé l’accès à cet installateur. Sur webOS 11, Homebrew 0.7.3 nécessite une mise à jour de compatibilité de ses développeurs. Utilisez l’installateur publié pour ordinateur ou Android jusqu’à ce qu’une version prise en charge de Homebrew intègre la correction. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

Candidat non publié uniquement : si les anciens répertoires Root inscriptibles empêchent l’accès à l’API du micrologiciel, `cytv enable-firmware-access --edition root --repair-package-permissions` vérifie le paquet actuel avec les données privées fiables puis retire les droits d’écriture du groupe et des autres sur les seuls chemins propres à Root. Des fichiers inconnus ou modifiés arrêtent la réparation. Profil, choix Home et blocage du micrologiciel sont conservés ; [détails (anglais)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

Candidat non publié uniquement : `cytv recover-system-rollback --edition root` traite un retour Root vérifié dont les installations de paquets sont terminées, mais dont le délai de disponibilité du lanceur a expiré. Le véritable lanceur doit confirmer son état ; les résultats d’installation inconnus sont refusés. Paquets, code et clés conservés, preuves d’échec et désactivation explicite de Home sont préservés. Une trace privée consigne cet essai limité. Une nouvelle exécution normale ne prolonge pas le délai. Après expiration des 120 secondes seulement, sans signal de disponibilité accepté ni résultat d’installation inconnu, `--new-recovery-attempt` archive la trace précédente complète sous son UUID/empreinte et ouvre explicitement un nouvel essai. Une récupération terminée reste idempotente ; aucun essai automatique. [Procédure et limites (anglais)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.5.0 : le paquet de remplacement contient System Updater 1.1.2. Avant OTA, remplacez explicitement 1.1.0 ou 1.1.1 avec `cytv replace-system-updater --edition root`. Seul System Updater est remplacé ; les apps Root/Root Updater, le profil complet et le choix Home sont conservés, et l’ancien état est archivé. Les opérations inconnues ou inachevées bloquent le remplacement. Cette exigence ne bloque pas les flux No-root. [Procédure (anglais)](../RECOVERY.md#replace-the-root-system-updater-candidate).

## Aide et autres instructions

Après un échec ou une interruption, vérifiez l’état et enregistrez le rapport de diagnostic de cet essai. La récupération guidée confirme séparément suppression et réinstallation. Si le résultat est incertain, arrêtez et conservez journaux privés et fichiers de récupération ; ne les supprimez jamais pour forcer un nouvel essai. [Récupération (anglais)](../RECOVERY.md). Pour obtenir de l’aide, précisez modèle, micrologiciel, édition, version de l’installateur, étape en échec et résultat attendu/réel ; vérifiez et expurgez le rapport avant partage.

[Documentation](../README.md) · [Signaler un problème](../FEEDBACK.md)

<!-- Anchors retained for links to earlier guide headings. -->
<a id="python-facultatif-pour-root-dans-v110"></a>
<a id="blocage-du-micrologiciel-lg-dans-120"></a>
<a id="nouveautés-de-130-récupération-guidée-sur-ordinateur"></a>
<a id="nouveautés-de-130--12"></a>
<a id="candidat-non-publié--installer-root-avec-homebrew"></a>
<a id="candidat-non-publié--récupération-du-son-hdmi-root"></a>


## Thèmes : candidat en développement

Dans le candidat compatible : **Paramètres → Apparence**. **Classic** et **Alpine** sont intégrés, sans téléchargement du thème ; Classic reste le choix initial. **Channel** est un thème externe du showcase. Lors d’un essai dans la galerie : Choisissez le thème puis **Conserver le thème** sous **20 secondes**. **Rétablir**, Back ou le délai expiré restaure le précédent. Une prévisualisation interrompue relance Home avec Classic. Les thèmes intégrés et téléchargés choisis dans la liste installée sont appliqués et enregistrés immédiatement, sans minuterie. Cela inclut les thèmes reçus de l’ordinateur ou installés par URL. Seul Essayer le thème dans la galerie lance un essai de 20 secondes.

Les thèmes installés apparaissent sur une seule ligne à défilement horizontal. Le thème actif est toujours le premier et sa carte est mise en évidence. Utilisez Gauche/Droite pour parcourir la ligne.

La galerie affiche seulement les thèmes absents de ce téléviseur. Classic, Alpine et les thèmes téléchargés sont masqués, même si une version plus récente existe. Un thème supprimé réapparaît. Mettez à jour par URL ou depuis l’ordinateur.

Les cartes sont intégrées directement dans Apparence, à côté des catégories. La galerie, l’installation par lien et le transfert depuis un ordinateur s’ouvrent dans ce volet ; seul un essai de la galerie affiche temporairement Home.

Ouvrir la galerie ou choisir Actualiser vérifie les mises à jour validées du dépôt principal sans mettre à jour Home ni recharger la page. Les nouvelles entrées arrivent après la fusion normale ; un candidat non fusionné peut afficher le catalogue intégré. Hors ligne ou en cas d’erreur, les entrées et aperçus intégrés sont utilisés. Les thèmes intégrés correspondent à la version installée de Home. Ouvrez l’aperçu de Channel, puis **Télécharger le thème** (internet requis). Après téléchargement, essayez-le et choisissez **Conserver le thème** sous **20 secondes**. Les thèmes installés fonctionnent hors ligne. **Ajouter par URL** reste disponible pour les liens figés.

Pour tester un thème non publié, ouvrez d’abord **Paramètres → Apparence → Recevoir de l’ordinateur** sur le TV. Saisissez son adresse et son PIN à six chiffres dans **Send to TV** sur l’ordinateur, envoyez puis choisissez **Appliquer le thème** sur le TV. Le mode principal établit une connexion sortante du PC au TCP **8879 du TV**, sans modifier le pare-feu de l’ordinateur. Les appareils doivent partager le même réseau domestique de confiance. Le récepteur ferme après un envoi, une annulation, la sortie ou **10 minutes**. Le PIN n’est pas enregistré ; le thème installé fonctionne hors ligne. Aucune publication GitHub n’est nécessaire.

Pour un thème publié, ouvrez **Options supplémentaires → Ajouter par URL** et saisissez son identifiant (par exemple `102300a209`), `da.gd/102300a209` ou le lien GitHub complet. Home affiche l’adresse da.gd avant le chargement et vérifie la destination GitHub et le paquet. L’auteur peut copier l’identifiant depuis les notes de version ou **TV link → Copy ID** dans l’aperçu.

Les versions publiées peuvent ne pas encore proposer ces commandes. Les tests navigateur ne prouvent pas la compatibilité TV. [Guide complet](../THEMES.md).

Thèmes affiche les aperçus des thèmes intégrés et de tous ceux que vous avez installés, même hors ligne. Un bouton séparé ouvre le catalogue publié ; une installation personnelle ne publie pas le thème.

Dans la version candidate, Apparence affiche de grandes vignettes des thèmes installés et indique le thème sélectionné. La galerie et la réception depuis un ordinateur sont les actions principales. Plus d’options regroupe l’ajout par URL, le retour à Classic et la suppression des thèmes téléchargés. Les flèches parcourent les vignettes et boutons ; à gauche au bord, elles reviennent aux catégories.

Dans l’aperçu du navigateur, Recevoir depuis un ordinateur explique les étapes sur le téléviseur sans démarrer de récepteur TV sur l’ordinateur. Utilisez Send to TV au-dessus de l’aperçu. La suppression d’un thème téléchargé demande confirmation ; si le thème est actif, Classic est rétabli d’abord. Annuler conserve le thème.

<a id="catégories-des-paramètres-candidat-non-publié"></a>

## Catégories des paramètres (1.5.0)

Dans les deux éditions, les catégories sont à gauche et leurs réglages à droite : écran d’accueil, Apparence (thèmes et colonnes), Langue, Mises à jour et Avancé. No-root ajoute Developer Mode ; Root place le firmware LG dans les mises à jour et le son HDMI dans Avancé. Haut/Bas parcourt une colonne, Droite entre dans les réglages et Gauche revient aux catégories. Retour revient aux catégories, puis ferme les paramètres. Tab permet aussi d’atteindre le bouton de retour à Home.

Un point jaune sur Mises à jour et sur le bouton associé indique une mise à jour disponible. Les deux disparaissent lorsqu’une vérification réussie confirme son absence ; en cas d’échec, le dernier état confirmé reste affiché.
