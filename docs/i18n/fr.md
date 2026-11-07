# Clean Your TV — guide d’utilisation

Clean Your TV donne à votre LG webOS un écran d’accueil personnel : vos applications dans votre ordre, sans rangées sponsorisées dans ce menu. Installez-le depuis un ordinateur ou un téléphone Android ; l’ordinateur peut ensuite rester éteint.

## 1. Télécharger l’installateur

Cliquez sur l’image de votre appareil. Les boutons téléchargent la dernière version publiée. Sur Mac, choisissez Apple Silicon (M1 ou plus récent) ou Intel : menu Apple → À propos de ce Mac.

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

### Configurer Developer Mode (No-root)

Developer Mode permet à CYTV d’installer des apps sur un TV sans root.

1. Sur le TV, ouvrez LG Apps, cherchez Developer Mode et installez cette app.
2. Ouvrez Developer Mode et connectez-vous avec votre compte LG Developer. Si nécessaire, créez un compte sur [LG Developer](https://webostv.developer.lge.com).
3. Activez Dev Mode Status. Le TV redémarre. Ouvrez ensuite Developer Mode à nouveau.
4. Activez Key Server et laissez Developer Mode ouvert. Saisissez son IP Address comme adresse du TV dans CYTV.
5. Saisissez la Passphrase : les six caractères affichés dans Developer Mode sur le TV. Respectez les majuscules et minuscules.

Utilisez le code du TV, pas le mot de passe du compte LG. Si aucun code n’apparaît, activez Key Server.

L’appairage est une étape distincte : quand le TV le demande, autorisez CYTV avec la télécommande.

Gardez Developer Mode actif : avant la fin du compte à rebours, ouvrez-le et appuyez sur EXTEND avec le TV connecté à Internet. À expiration, LG peut supprimer ces apps.

<a id="installation-et-langue"></a>

## 3. Ouvrir l’installateur

- **Windows x64 :** téléchargez `cytv-windows-x64-desktop.zip`, choisissez **Extraire tout** dans l’Explorateur, puis ouvrez `cytv-desktop/cytv-desktop.exe`. Gardez le dossier `_internal` à côté.
- **macOS 13+ :** décompressez `cytv-macos-arm64.zip` pour Apple Silicon ou `cytv-macos-x64.zip` pour Intel. Placez `cytv.app` dans Applications et ouvrez-la ; autorisez l’accès au réseau local. En cas de blocage d’un téléchargement fiable, utilisez Confidentialité et sécurité → Ouvrir quand même, sans désactiver Gatekeeper.
- **Linux x64 :** sous Ubuntu 22.04+, Debian 12+ ou Mint 21+, installez `cytv-linux-x64.deb` avec le gestionnaire graphique de paquets, puis ouvrez Clean Your TV depuis le menu. Internet peut être nécessaire pour les bibliothèques. Linux ARM n’est pas fourni.

**Android ARM64 :** utilisez un téléphone ARM 64 bits avec Android 7+ et WebView/Chrome 108+. Ouvrez l’APK téléchargé et autorisez l’installation depuis cette source si Android le demande. Ouvrez CYTV ; la langue se choisit en haut à droite. Mettez à jour sans désinstaller ni effacer les données.

L’assistant utilise initialement la langue du système et mémorise votre choix explicite. Sur le téléviseur, ouvrez **Paramètres → Langue** et choisissez une langue ou l’option automatique du système. Les préférences du téléviseur et de l’installateur sont indépendantes. Les codes figurent dans l’[index des langues](../LANGUAGES.md).

## 4. Installer sur le téléviseur

1. Dans CYTV, choisissez **Configurer mon téléviseur**. Sur ordinateur, sélectionnez une TV détectée ; sur Android, saisissez son adresse IP. Si la recherche ne trouve rien, saisissez l’adresse manuellement.
2. Choisissez **No-root** ou **Root** et vérifiez le téléviseur sélectionné avant de continuer.
3. No-root : saisissez le code de Developer Mode et acceptez la demande sur la TV. Root : utilisez vos identifiants SSH. N’acceptez une nouvelle identité SSH que pour votre propre TV sur un réseau fiable. Si une clé enregistrée a changé, arrêtez-vous et recherchez la cause.
4. Suivez l’assistant. Gardez la TV allumée, le même réseau et CYTV ouvert jusqu’à la fin. Ne forcez pas l’arrêt de l’application Android. Root active le contrôle de Home dès la récupération préparée.

## 5. Vérifier la télécommande

1. Ouvrez une autre application sur la TV et appuyez brièvement sur **Home**. Clean Your TV doit s’ouvrir. Indiquez votre observation dans l’assistant ; ignorez le test si vous ne l’avez pas effectué.
2. Vérifiez flèches, OK, Retour, volume et son. Testez séparément la veille/le réveil et un démarrage après débranchement du secteur. Une installation réussie ne vérifie pas ces actions à elle seule.

<a id="utilisation-et-récupération"></a>

## 6. Utilisation et récupération

Les flèches sélectionnent, OK ouvre ; maintenez OK pour réorganiser. Un appui bref sur Retour conserve la navigation et la confirmation de sortie de l’application. Home ouvre le lanceur si le contrôle est actif. Maintenez Retour pendant 1,2 seconde pour ouvrir LG Home une fois. L’interrupteur du contrôle de Home et vos paramètres restent inchangés.

**Appuyez trois fois sur Home en deux secondes**, en relâchant entre les appuis. Cela rétablit LG Home et arrête le contrôle sans effacer vos préférences.

No-root: Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé. Root : activez **Changer Home** dans les paramètres de Home pour reprendre. **Ouvrir LG Home** ouvre LG Home une fois sans modifier la destination de Home. Pour rétablir LG Home comme destination permanente, désactivez **Changer Home**. N’exécutez jamais les deux contrôleurs ensemble. Si la panne revient, laissez LG Home actif.

## Besoin d’aide ?

Après une interruption, utilisez la même connexion enregistrée et commencez par **Vérifier l’état du téléviseur**. Continuez uniquement avec l’action de récupération proposée par l’assistant. Si l’état est inconnu, enregistrez le rapport de diagnostic et arrêtez-vous ; conservez les données de récupération et ne réinstallez pas à l’aveugle.

Pendant la récupération, laissez le contrôle de Home désactivé et conservez les rapports de diagnostic originaux ainsi que la connexion enregistrée. Confirmez séparément la vérification et les modifications. Suivez le guide détaillé pour votre version installée ; ne forcez pas la réinstallation et n’effacez pas l’état de récupération.

Indiquez modèle de TV, micrologiciel, No-root ou Root, appareil d’installation, étape et message d’erreur. Retirez mots de passe, clés, adresses et données personnelles avant de partager le rapport. Rien n’est publié automatiquement.

[Signaler un problème](../FEEDBACK.md) · [Récupération — anglais](../RECOVERY.md) · [Mettre à jour ou supprimer — anglais](../MAINTENANCE.md) · [Autres langues](../LANGUAGES.md)

Dans les prochaines versions, l’avertissement et le bouton « Désactiver l’aperçu HDMI » apparaissent lorsque la 4K est sélectionnée ou active, uniquement pour les thèmes dont l’aperçu des entrées est activé. Pendant l’aperçu HDMI, le fond vidéo 4K est temporairement remplacé par une image fixe en 1080p. Désactivez l’aperçu des entrées pour conserver le fond en 4K.

### Candidat : suppression simple

Les boutons ci-dessus proposent toujours la version publiée. Dans le prochain candidat, choisissez **Désinstaller Clean Your TV** dans Maintenance avec la même connexion enregistrée. Confirmez une fois. Les applications et fichiers connus du projet présents sont supprimés ; les éléments absents sont ignorés, même après une installation partielle.

Quand demandé, débranchez l’alimentation TV, rebranchez-la, attendez le réseau et choisissez **Réessayer**. Veille ou Quick Start n’est pas un redémarrage complet ; CYTV ne redémarre pas le téléviseur automatiquement. En cas de déconnexion, vérifiez la connexion et réessayez la même suppression sans autre assistant de récupération. Si l’accès est refusé, utilisez la connexion Root demandée ; si le téléviseur est occupé, patientez et réessayez. Le succès apparaît seulement après vérification du nettoyage final. Gardez les clés et rapports d’origine. Les commandes d’urgence et le consentement au partage restent applicables.

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

Références détaillées en anglais : [prérequis](../COMPATIBILITY.md) · [commandes](../CONTROLS.md) · [thèmes](../THEMES.md) · [mises à jour](../UPDATES.md).

> Candidat non publié : Root Home expérimental est sélectionné selon les capacités Qt SDK 6–9, sans liste de modèles. Compatibilité matérielle et OTA normal non vérifiés. Les autres intégrations Home restent intactes ; après un arrêt de sécurité ou de courant, réactivez Home explicitement. [#364](../development/C1-NATIVE-GATE.md#unpublished-capability-based-compositor-admission-364).
