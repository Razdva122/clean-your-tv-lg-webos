# Clean Your TV — guide d’utilisation

Non publié (#290) : **+ / Ajouter une app** propose la télévision en direct sous le nom fourni par le TV uniquement si le tuner est détecté comme installé. Les autres apps système masquées restent exclues. No-root nécessite Helper et installateur à jour ; Root nécessite le paquet Home à jour. Le lancement des chaînes reste à vérifier sur le TV.

**1.7.0 — sources de démarrage Root :** Dans Paramètres → Votre écran Home, activez **Modifier Home** pour régler **Ouvrir Clean Your TV en premier**. **LG Channels / TV en direct** est activé par défaut ; **YouTube** est désactivé. Quand Modifier Home est désactivé, les interrupteurs restent visibles mais indisponibles, et leurs valeurs sont conservées. Ces préférences restent privées sur ce téléviseur et ne sont pas incluses dans l’export portable du profil. Cela ne confirme pas le comportement au démarrage ou à la sortie de veille. Une source désactivée laisse le choix du démarrage au micrologiciel du téléviseur ; le retour à cette source n’est pas garanti. Aucun interrupteur de démarrage HDMI n’est proposé. [Limites du démarrage natif (anglais)](../../root-edition/README.md#candidate-native-startup-choices).

> Ce guide décrit la version 1.7.0. Utilisez les paquets disponibles dans les [versions publiées sur GitHub Releases](https://github.com/Razdva122/clean-your-tv-lg-webos/releases). Il inclut les cinq améliorations de l’installateur. À leur réouverture, les réglages Root lisent l’état réel ; un contrôle échoué n’active pas Home. System Updater 1.2.0 concerne une nouvelle installation admissible ou le remplacement vérifié de 1.1.0/1.1.1. Le 1.1.2 installé conserve ses anciens canaux ; aucune migration générale n’est fournie. Conservez les données de récupération et ne forcez pas le remplacement. [Versions et limites](../RELEASE-1.7.0.md).

> v1.5.0 : thèmes, galerie et transfert du PC au téléviseur. Limites Root connues : Appearance peut se décaler de 110 px ; Home peut ne pas s’ouvrir automatiquement après la veille. La validation par appareil reste limitée. [1.5.0](../RELEASE-1.5.0.md).

> **1.5.4:** les thèmes à disposition fixe conservent l’espace de la ligne Columns masquée pour préserver le défilement d’Appearance lors de l’application. Le pointeur, le clavier et les outils d’accessibilité ignorent Columns.

[Documentation](../README.md) · [Signaler un problème](../FEEDBACK.md)

**Résultats historiques de 1.5.4:** La validation C3 couvre les essais consignés d’alimentation, Home, focus, maintien de la désactivation et retour manuel à la version précédente. Les autres TV, le son eARC et les appareils Android physiques restent non vérifiés ; une installation réussie ne prouve pas la compatibilité. [Périmètre testé (anglais)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

**1.5.4:** console, ordinateur et Android indiquent chaque vérification du TV : non effectuée, en cours, réussie, échouée ou invérifiable. Les résultats restent visibles après une erreur. Node.js/Python est vérifié sur le TV ; `doctor` ne prépare pas Python et ne demande pas d’association de contrôle. Enregistrez le rapport avant de réessayer.

## Choisir une édition

No-root et Root sont des options équivalentes pour différentes configurations du téléviseur. Choisissez No-root pour LG Developer Mode ou Root si vous disposez déjà d’un accès root par SSH. La compatibilité et les essais réalisés sont propres à chaque édition.

- **No-root :** activez LG Developer Mode et Key Server. Saisissez la phrase secrète affichée sur le téléviseur et acceptez sur celui-ci la demande d’association distincte. Developer Mode doit rester actif : son expiration peut supprimer les applications installées ainsi. Surveillez son compteur officiel même avec le renouvellement Beta activé. La surveillance du Helper nécessite le réseau local.
- **Root :** un accès SSH root existant est nécessaire. L’installateur ne roote pas le téléviseur. N’activez pas Developer Mode sur une installation déjà rootée. Conservez l’accès root et les services de récupération.

Root nécessite les interfaces Home fonctionnelles de Settings Service et System Profile (`com.webos.service.systemprofile`) ; un accès root seul ne garantit pas la compatibilité.

> **1.6.0:** Root vérifie les interfaces Home requises avant de préparer Python privé ou les paquets. Un échec arrête l’installation ; une réussite ne prouve ni la compatibilité du micrologiciel ni le fonctionnement du bouton Home. Les erreurs de connexion connues affichent des conseils précis. Conservez profils, données de confiance et de récupération ; une opération en attente exige une récupération vérifiée, sans nouvel essai aveugle. Enregistrez et vérifiez le rapport. [Détails](../development/INSTALLER-PREFLIGHT-HELP.md).

## Prérequis

Allumez le téléviseur et reliez-le au même réseau local de confiance que l’ordinateur. L’ordinateur peut ensuite rester éteint. La compatibilité dépend du modèle, du micrologiciel et de la télécommande ; des essais matériels restent à terminer pour Root.

1.5.4 inclut Home Helper **0.6.21** pour Node.js **0.10.25+** sur le TV ; Root exige toujours Node.js **8+**. [Compatibility](../COMPATIBILITY.md).

**Modification non publiée pour webOS 1.x :** le prochain installateur No-root accepte Node.js **0.10.15+** du téléviseur après des tests Helper avec cette version exacte ; l’installateur publié 1.7.1 exige encore **0.10.25+**. Cela ne confirme pas la compatibilité avec l’ancien WebKit, les entrées natives ou Home. Ne remplacez pas le runtime du téléviseur et ne contournez pas les vérifications. Root exige toujours Node.js 8+. [Tests et limites](../COMPATIBILITY.md#webos-1x-runtime-floor-unreleased).

No-root Helper nécessite Node.js **0.10.25+** sur la TV. Root nécessite Node.js **8+** et Python **3.9+** fonctionnel. Au besoin, l’installateur télécharge un Python privé vérifié ; la préparation initiale demande **320 MiB** libres. Il ne remplace pas Python système. Conservez les environnements utilisés par la récupération. [Python (anglais)](../OPTIONAL-PYTHON.md). Le renouvellement Developer Mode est **Beta, désactivé par défaut** ; son fonctionnement réel sans root n’est pas confirmé. Surveillez toujours le compteur officiel.

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

**Candidat Android non publié :** pour une opération Root d’origine `install / coordinator-submitted`, l’examen de récupération peut effectuer une inspection en lecture seule après confirmation explicite, avec le profil et la clé d’hôte SSH d’origine. Ne désinstallez pas, n’effacez pas les données, ne remplacez pas le profil et ne relancez pas l’installation. Utilisez uniquement l’APK recompilé et signé indiqué par le mainteneur ; l’APK public ne contient pas encore ce parcours. [Procédure et limites](../../android/README.md#interrupted-root-installation-inspection-unreleased).

L’assistant utilise initialement la langue du système et mémorise votre choix explicite. Sur le téléviseur, ouvrez **Paramètres → Langue** et choisissez une langue ou l’option automatique du système. Les préférences du téléviseur et de l’installateur sont indépendantes. Les codes figurent dans l’[index des langues](../LANGUAGES.md).

Pour la CLI téléchargée séparément sous macOS/Linux, depuis son dossier décompressé :

```sh
chmod +x cytv
./cytv --language fr install
```

Choisissez le téléviseur ou son adresse IP, l’édition, puis vérifiez le récapitulatif. N’acceptez une nouvelle identité SSH que pour votre téléviseur sur un réseau fiable ; une clé enregistrée modifiée bloque la connexion. Root prépare la récupération et active Home immédiatement, sans essai temporaire ni étape de conservation. Testez flèches, OK, Home, Retour/Annuler, volume, veille et démarrage à froid.

**1.6.0:** vérification des paquets, démarrage et votre observation du bouton Home physique sont séparés. Une confirmation de lancement ou un processus Helper ne prouve pas l’interception de Home. Ouvrez une autre application, appuyez brièvement une fois sur Home et indiquez le résultat ; le choix par défaut est **Non testé / ignorer**. `--yes` ne répond pas à votre place et le mode non interactif laisse ce test non effectué. Un échec Home ou un test ignoré ne désinstalle rien et ne lance pas de réinstallation. Enregistrez le rapport local pour demander de l’aide ; aucune publication automatique. Autres commandes, son, veille et démarrage à froid restent séparés.

## Utilisation et récupération

Les flèches sélectionnent, OK ouvre ; maintenez OK pour réorganiser. Un appui bref sur Retour conserve la navigation et la confirmation de sortie de l’application. Home ouvre le lanceur si le contrôle est actif. Maintenez Retour pendant 1,2 seconde pour ouvrir LG Home une fois. L’interrupteur du contrôle de Home et vos paramètres restent inchangés.

**Appuyez trois fois sur Home en deux secondes**, en relâchant entre les appuis. Cela rétablit LG Home et arrête le contrôle sans effacer vos préférences. Avec No-root Helper jusqu’à 0.6.13 inclus, maintenez plutôt Home environ deux secondes. Maintenir Home n’est pas le geste d’urgence de Root.

No-root: Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé. Root : activez **Changer Home** dans les paramètres de Home pour reprendre. **Ouvrir LG Home** ouvre LG Home une fois sans modifier la destination de Home. Pour rétablir LG Home comme destination permanente, désactivez **Changer Home** ou exécutez `cytv restore`. N’exécutez jamais les deux contrôleurs ensemble. Si la panne revient, laissez LG Home actif.

> **1.5.4 — Root:** activer explicitement **Changer Home** avec Root en bon état crée une entrée native **Clean** appartenant à CYTV et mémorise Clean comme entrée. La désactivation du contrôle Home, un arrêt d’urgence, une erreur, une suspension pour mise à jour ou la désinstallation supprime cette entrée et restaure l’entrée précédente seulement si la valeur actuelle est encore celle de CYTV ; les autres entrées et applications au premier plan sont préservées. Les téléviseurs non compatibles ou les entrées qui n’appartiennent pas à CYTV conservent le contrôle Home habituel avec ses protections. L’affichage immédiat de Clean en toute première image n’est pas garanti. Les essais consignés du premier écran, de veille et de démarrage après coupure secteur sur C3 ont réussi, sans garantie universelle. Home peut rester désactivé après mise à jour/retour arrière (#202), et les paramètres afficher un état ancien (#206) : fermez/rouvrez les paramètres, activez explicitement Changer Home et attendez l’état Clean. [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md) · [Native input (English)](../development/ROOT-NATIVE-INPUT.md).

```sh
./cytv --language fr status
./cytv --language fr doctor --report
./cytv --language fr restore
./cytv --language fr uninstall
```

> **1.6.0 (#152):** si la désactivation de Helper est refusée, la restauration/suppression No-root pourra utiliser un arrêt vérifié par SSH. L’état d’arrêt est conservé ; un résultat incertain conserve le journal. Ne supprimez pas les fichiers d’état. La confirmation sur EF950V reste attendue. [#152](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/152)

> **1.6.0 (#201):** le statut No-root conserve le journal d’une installation ou suppression interrompue. Des fichiers identiques ou des applications absentes ne prouvent pas la fin de l’opération. Si la vérification est refusée, arrêtez et conservez le diagnostic ; les fichiers seuls ne permettent pas de contourner ce contrôle. [#201](../RECOVERY.md#unreleased-uncertain-no-root-package-operations-201)

Après interruption, lancez d’abord `status` et conservez les journaux. `restore` rétablit LG Home sans supprimer les applications ; `uninstall` le rétablit avant leur suppression. Les données de récupération Root sont conservées volontairement : ne les effacez pas pour forcer une réinstallation. Vérifiez les rapports avant partage ; ne publiez ni clés ni dossiers de profils.

Ouvrez **Paramètres de Home → Apparence → Colonnes** et choisissez de 1 à 8 colonnes, ou **Selon le thème** pour utiliser sa valeur (Classic : 5). Un nombre explicite est prioritaire sur le thème. Les thèmes à disposition fixe masquent l’option Colonnes et utilisent la valeur de l’auteur. Votre choix enregistré est rétabli lorsque vous passez à un thème qui prend en charge ce réglage. Dans Alpine téléchargé, les applications forment un ruban horizontal en boucle : Gauche/Droite fait défiler, Haut ouvre les raccourcis et Bas revient à la même application. Dans Alpine, la molette ou le pavé tactile fait aussi défiler le ruban ; Home reste immobile derrière une boîte de dialogue ouverte.

1.5.4: dans **Paramètres Home → Apparence**, désactivez **Afficher la tuile « Ajouter une app »** pour masquer +. Cette option est activée par défaut. Utilisez **Ajouter une app** dans la même section pour ajouter ou rétablir des apps lorsque + est masqué. Le déplacement et le masquage restent disponibles ; le choix est conservé au redémarrage. Si toutes les apps sont masquées, les commandes du haut et les paramètres restent accessibles.

1.7.0: le thème choisi détermine si **Entrées** utilise le menu d’en-tête ou une rangée HDMI ; il n’existe ni réglage global d’emplacement ni interrupteur **Afficher les entrées sur Home**. La rangée prend actuellement en charge uniquement `dock-grid`. Liquid Glass la choisit ; Classic et les thèmes sans cette option gardent le menu d’en-tête. Haut depuis le dock ouvre la rangée, encore Haut rejoint l’en-tête, Bas ou Retour revient au dock et OK ouvre la source. Si des tuiles de sources existent, la rangée remplace le menu Entrées de l’en-tête. Le nom de l’appareil provient des métadonnées des entrées uniquement si le micrologiciel le fournit ; sinon une source connectée affiche **Connecté**. Home n’invente pas de nom PlayStation et ne garantit pas l’identification CEC. Les ports vides restent sélectionnables. Les aperçus sont **activés par défaut** ; un choix Désactivé explicitement enregistré est conservé. Désactivez **Paramètres Home → Apparence → Aperçu de l’entrée sélectionnée** pour les arrêter. Quand ils sont activés et que le thème utilise la rangée, un HDMI connecté peut être prévisualisé après environ 0,8 seconde de sélection. Sur certains téléviseurs, les aperçus HDMI peuvent émettre du son ou activer le HDR ; le silence n’est pas garanti. Home ne modifie pas automatiquement la sourdine globale ni les réglages HDR du téléviseur. Live TV et les ports vides gardent des tuiles statiques. Root lit l’état des entrées via son propre service. No-root conserve EIM direct si autorisé ; un refus de permission utilise une requête en lecture seule via Helper déjà associé. En cas d’échec, l’état reste inconnu ; aucun nouveau réglage ni dialogue d’association n’est ajouté.

Dans les aperçus de thèmes de 1.5.4 avec barre latérale facultative, Haut/Bas sélectionne une entrée du menu, Droite passe aux applications et Gauche depuis leur première colonne revient au menu.

No-root 1.5.0 : Helper peut récupérer après un délai watchdog temporaire à la sortie de veille, avec au maximum cinq tentatives en dix minutes. Stop et trois pressions sur Home exigent toujours un démarrage explicite de Helper ; les échecs répétés le laissent arrêté. La validation sur TV reste à faire. [Comportement et limites (anglais)](../HELPER-DIAGNOSTICS.md#watchdog-recovery-unpublished-candidate-155).

## Mises à jour et suppression

Gardez les paquets fonctionnels et des sauvegardes privées des paramètres. Pour remplacer les paquets No-root depuis l’ordinateur, arrêtez d’abord Helper et mettez à jour sans désinstaller : la désinstallation peut effacer les réglages. Supprimer l’application de bureau ne supprime pas les applications TV. Ne remplacez pas un environnement Root actif par une IPK isolée ; utilisez le parcours explicite de récupération ou de réinstallation de cytv.

Ouvrez les paramètres Home → Mises à jour et vérifiez les versions avant confirmation. Mise à jour et retour arrière sur TV nécessitent **root, Homebrew Channel** et les composants de mise à jour correspondants préparés, même pour No-root. Sans root, utilisez l’ordinateur. La préparation des mises à jour complètes est une action explicite distincte : [mises à jour (anglais)](../UPDATES.md). Récupération indique la version sauvegardée ; les réglages ultérieurs peuvent être perdus lors du retour arrière.

**Installation 1.3.0 existante :** le System Updater d’origine peut refuser une infrastructure modifiée. Conservez l’opération interrompue et suivez la récupération et la préparation du remplacement vérifiées pour 1.5.0+ ; ne supprimez pas les journaux et ne réessayez pas à l’aveugle. Une mise à jour de l’app seule ne remplace pas l’infrastructure Root épinglée. [Migration et récupération (anglais)](../UPDATES.md#one-time-computer-preparation).

La correction du canal des réglages Home est publiée depuis 1.5.0. Mettez Home et Helper à jour ensemble avec un installateur publié compatible ; une mise à jour de Home seul ne modifie pas Helper. La validation reste propre aux modèles documentés. [#146](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/146).

La récupération audio HDMI Root est expérimentale et **désactivée par défaut** ; activez-la uniquement si nécessaire. Elle peut interrompre un son fonctionnel et ne valide pas eARC. [Récupération audio (anglais)](../development/ROOT-AUDIO-RECOVERY.md). Le **CYTV Installer Homebrew reste non publié** ; utilisez l’installateur publié pour ordinateur ou Android.

Homebrew Channel a refusé l’accès à cet installateur. Sur webOS 11, Homebrew 0.7.3 nécessite une mise à jour de compatibilité de ses développeurs. Utilisez l’installateur publié pour ordinateur ou Android jusqu’à ce qu’une version prise en charge de Homebrew intègre la correction. [#116](https://github.com/Razdva122/clean-your-tv-lg-webos/issues/116).

1.5.0+: si les anciens répertoires Root inscriptibles empêchent l’accès à l’API du micrologiciel, `cytv enable-firmware-access --edition root --repair-package-permissions` vérifie le paquet actuel avec les données privées fiables puis retire les droits d’écriture du groupe et des autres sur les seuls chemins propres à Root. Des fichiers inconnus ou modifiés arrêtent la réparation. Profil, choix Home et blocage du micrologiciel sont conservés ; [détails (anglais)](../LG-FIRMWARE-UPDATES.md#explicit-package-permission-repair-candidate).

1.5.0+: `cytv recover-system-rollback --edition root` traite un retour Root vérifié dont les installations de paquets sont terminées, mais dont le délai de disponibilité du lanceur a expiré. Le véritable lanceur doit confirmer son état ; les résultats d’installation inconnus sont refusés. Paquets, code et clés conservés, preuves d’échec et désactivation explicite de Home sont préservés. Une trace privée consigne cet essai limité. Une nouvelle exécution normale ne prolonge pas le délai. Après expiration des 120 secondes seulement, sans signal de disponibilité accepté ni résultat d’installation inconnu, `--new-recovery-attempt` archive la trace précédente complète sous son UUID/empreinte et ouvre explicitement un nouvel essai. Une récupération terminée reste idempotente ; aucun essai automatique. [Procédure et limites (anglais)](../RECOVERY.md#root-system-rollback-readiness-candidate).

1.6.0 : System Updater 1.2.0 concerne une nouvelle installation admissible ou le remplacement vérifié de 1.1.0/1.1.1 avec `cytv replace-system-updater --edition root`. Seul System Updater est remplacé ; les apps Root/Root Updater, le profil complet et le choix Home sont conservés, et l’ancien état est archivé. Les opérations inconnues ou inachevées arrêtent le remplacement. Une installation 1.1.2 reste épinglée avec ses anciens canaux ; aucune migration générale n’est fournie. Ne forcez pas le remplacement. Cela ne conditionne pas les flux No-root. [Procédure (anglais)](../RECOVERY.md#replace-the-root-system-updater-candidate)

## Aide et autres instructions

**1.6.0:** choisissez **Examiner les options de récupération** pour le même téléviseur enregistré ou lancez `cytv recover`. Vérification et modifications exigent des confirmations distinctes, avec Non par défaut ; `--yes` ne les autorise pas. Root continue uniquement après les vérifications existantes. No-root propose la suppression seulement si le contrôle du service de paquets le permet ; les préférences Home peuvent être réinitialisées. Aucune nouvelle installation ne démarre automatiquement. Si l’état est inconnu ou l’accès refusé, enregistrez le rapport et arrêtez. Conservez les journaux et ne répétez pas la suppression. Les preuves de fin de #201 et la récupération réelle de #216 restent à confirmer. [Recovery](../RECOVERY.md). Pour obtenir de l’aide, précisez modèle, micrologiciel, édition, version de l’installateur, étape en échec et résultat attendu/réel ; vérifiez et expurgez le rapport avant partage.

1.7.0: la récupération peut reprendre une suppression No-root arrêtée avant la première demande de paquet sans accès au statut global, si le journal original le prouve. Confirmez la suppression séparément, puis lancez une nouvelle installation après sa vérification. Les opérations inconnues ou déjà envoyées restent bloquées. Conservez la connexion et les journaux. Absent de 1.6.0. [Détails](../RECOVERY.md#no-root-removal-stopped-before-package-submission-unreleased).

[Documentation](../README.md) · [Signaler un problème](../FEEDBACK.md)

En développement : si aucune demande de suppression de paquet n’a été envoyée, un échec propose **Examiner les options de récupération** pour la même connexion TV enregistrée. La vérification et la suppression exigent des confirmations distinctes. Un refus de vérifier l’état des paquets arrête la récupération et propose un rapport. Son résumé `recovery` distingue une suppression non commencée, une opération héritée et des opérations sur les paquets interrompues sans publier le journal complet ; il n’autorise pas la récupération.

<!-- Anchors retained for links to earlier guide headings. -->
<a id="python-facultatif-pour-root-dans-v110"></a>
<a id="blocage-du-micrologiciel-lg-dans-120"></a>
<a id="nouveautés-de-130-récupération-guidée-sur-ordinateur"></a>
<a id="nouveautés-de-130--12"></a>
<a id="candidat-non-publié--installer-root-avec-homebrew"></a>
<a id="candidat-non-publié--récupération-du-son-hdmi-root"></a>

<a id="thèmes-154"></a>

## Thèmes

1.7.0: **Paramètres → Thèmes**. **Classic**, **Liquid Glass**, **Ribbon** sont intégrés, sans téléchargement du thème ; Classic reste le choix initial. **Channel** est un thème externe du showcase. Lors d’un essai dans la galerie : Choisissez le thème puis **Conserver le thème** sous **20 secondes**. **Rétablir**, Back ou le délai expiré restaure le précédent. Une prévisualisation interrompue relance Home avec Classic. Les thèmes intégrés et téléchargés choisis dans la liste installée sont appliqués et enregistrés immédiatement, sans minuterie. Cela inclut les thèmes reçus de l’ordinateur ou installés par URL. Seul Essayer le thème dans la galerie lance un essai de 20 secondes.

1.7.0: **Classic**, **Liquid Glass** et **Ribbon** sont intégrés. **Alpine 1.4.4** devient téléchargeable dans la **galerie de thèmes**. Un choix enregistré `builtin:alpine` revient à Classic avec l’avis de récupération visible existant ; Home ne télécharge pas automatiquement Alpine et ne le remplace pas par Liquid Glass. La version 1.6.0 inclut Classic, Alpine et Ribbon.

Les thèmes installés apparaissent sur une seule ligne à défilement horizontal. Le thème actif est toujours le premier et sa carte est mise en évidence. Utilisez Gauche/Droite pour parcourir la ligne.

La galerie affiche seulement les thèmes absents de ce téléviseur. Classic, Liquid Glass, Ribbon et les thèmes téléchargés sont masqués, même si une version plus récente existe. Un thème supprimé réapparaît. Mettez à jour par URL ou depuis l’ordinateur.

Les cartes sont intégrées directement dans Thèmes, à côté des catégories. La galerie, l’installation par lien et le transfert depuis un ordinateur s’ouvrent dans ce volet ; seul un essai de la galerie affiche temporairement Home.

Ouvrir la galerie ou choisir Actualiser vérifie les mises à jour validées du dépôt principal sans mettre à jour Home ni recharger la page. Les nouvelles entrées arrivent après la fusion normale ; un candidat non fusionné peut afficher le catalogue intégré. Hors ligne ou en cas d’erreur, les entrées et aperçus intégrés sont utilisés. Les thèmes intégrés correspondent à la version installée de Home. Ouvrez l’aperçu de Channel, puis **Télécharger le thème** (internet requis). Après téléchargement, essayez-le et choisissez **Conserver le thème** sous **20 secondes**. Les thèmes installés fonctionnent hors ligne. **Ajouter par ID** reste disponible pour les liens figés.

Pour tester un thème non publié, ouvrez d’abord **Paramètres → Thèmes → Recevoir de l’ordinateur** sur le TV. Saisissez son adresse et son PIN à six chiffres dans **Send to TV** sur l’ordinateur, envoyez puis choisissez **Appliquer le thème** sur le TV. Le mode principal établit une connexion sortante du PC au TCP **8879 du TV**, sans modifier le pare-feu de l’ordinateur. Les appareils doivent partager le même réseau domestique de confiance. Le récepteur ferme après un envoi, une annulation, la sortie ou **10 minutes**. Le PIN n’est pas enregistré ; le thème installé fonctionne hors ligne. Aucune publication GitHub n’est nécessaire.

Pour un thème publié, ouvrez **Ajouter par ID** et saisissez son identifiant (par exemple `102300a209`), `da.gd/102300a209` ou le lien GitHub complet. Home affiche l’adresse da.gd avant le chargement et vérifie la destination GitHub et le paquet. L’auteur peut copier l’identifiant depuis les notes de version ou **TV link → Copy ID** dans l’aperçu.

**1.6.0:** **Afficher le diagnostic** dans le panneau Home Helper affiche un petit instantané filtré de ses propres demandes d’état. L’affichage ne démarre pas Helper et ne change pas le contrôle de Home. Partagez uniquement ce JSON sur demande, après vérification ; [détails](../HELPER-DIAGNOSTICS.md#candidate-panel-caller-diagnostics-207).

[Themes (English)](../THEMES.md) · [1.5.4 QA (English)](../history/2026-10-31-release-1.5.3-signed-root-qa.md).

Les thèmes à ruban configurable de 1.5.4 peuvent placer Entrées, Wi-Fi et Paramètres en bas à gauche. Si activée, la navigation Gauche depuis la première application visible sélectionne Paramètres, puis Wi-Fi et Entrées ; Droite depuis Paramètres revient à la même application visible. Un thème nécessitant une nouvelle fonction Home est refusé à l’installation sur une version incompatible ; l’apparence et la sélection restent inchangées. Mettez Home à jour d’abord. Une rétrogradation ultérieure peut restaurer Classic au démarrage.

Thèmes affiche les aperçus des thèmes intégrés et de tous ceux que vous avez installés, même hors ligne. Un bouton séparé ouvre le catalogue publié ; une installation personnelle ne publie pas le thème.

Apparence contient Colonnes avec le nombre actuel et les commandes des applications. La catégorie Thèmes contient les thèmes installés, la galerie, la réception depuis un ordinateur et Ajouter par ID à droite (ex. 102300a209). Rétablissez Classic avec sa vignette et supprimez les téléchargements un par un. Langue propose directement le choix.

Dans l’aperçu du navigateur, Recevoir depuis un ordinateur explique les étapes sur le téléviseur sans démarrer de récepteur TV sur l’ordinateur. Utilisez Send to TV au-dessus de l’aperçu. La suppression d’un thème téléchargé demande confirmation ; si le thème est actif, Classic est rétabli d’abord. Annuler conserve le thème.

<a id="catégories-des-paramètres-candidat-non-publié"></a>

## Catégories des paramètres (1.5.4)

Dans les deux éditions, les catégories sont à gauche et leurs réglages à droite : écran d’accueil, Apparence, Thèmes, Langue, Mises à jour et Avancé. No-root ajoute Developer Mode ; Root place le firmware LG dans les mises à jour et le son HDMI dans Avancé. Haut/Bas parcourt une colonne, Droite entre dans les réglages et Gauche revient aux catégories. Retour revient aux catégories, puis ferme les paramètres. Tab permet aussi d’atteindre le bouton de retour à Home.

Un point jaune sur Mises à jour et sur le bouton associé indique une mise à jour disponible. Les deux disparaissent lorsqu’une vérification réussie confirme son absence ; en cas d’échec, le dernier état confirmé reste affiché.

<a id="résolution-graphique-automatique-candidat"></a>

## Résolution graphique automatique (1.6.0)

Les installateurs ordinateur/Android de 1.6.0 et clients OTA migrés choisissent 720p ou 1080p selon les capacités du téléviseur. Si elles ne peuvent être vérifiées, l’opération s’arrête. Les anciens outils de mise à jour installés séparément nécessitent la migration documentée depuis un ordinateur ; la récupération conserve ses paquets d’origine.

[HD/FHD details (English)](../development/HOME-GRAPHICS-RESOLUTION.md#automatic-selection-and-ota).

> **1.6.0:** conservez le rapport de l’échec initial. Les nouveaux rapports séparent la première erreur enregistrée des vérifications suivantes et contiennent un résumé filtré de Doctor/état. Un export est aussi proposé après une installation, une vérification d’état ou une restauration réussie. Les anciennes données manquantes restent inconnues ; ce rapport n’autorise aucune récupération. [↗](../development/INSTALLER-DIAGNOSTICS.md).
