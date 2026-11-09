# Clean Your TV — guide d’utilisation

l’installateur demande un nom, **Home** par défaut ; CLI : `--tv-name "Aashiyaan"`. Après une mise à niveau, **Paramètres → Home → Nom du téléviseur** apparaît automatiquement. Enregistrez le nom ou rétablissez Home à tout moment. Le nom persiste après redémarrage et mises à jour compatibles ; les autres réglages restent conservés. Maximum 48 caractères. Les paramètres enregistrent le nom du lanceur. Pour changer l’écran de démarrage LG, appliquez le même nom avec l’installateur. Aucun second écran de chargement n’est ajouté ; le nom réseau reste inchangé.

Modification non publiée : avant une nouvelle installation, l’installateur de l’ordinateur recherche une version stable plus récente sur GitHub. Choisissez « Ouvrir GitHub et télécharger la dernière version » pour arrêter et la télécharger, ou « Non, installer cette version » pour continuer explicitement. Si la vérification échoue, vous pouvez continuer. Les opérations en attente et la récupération ignorent cette vérification.

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

Pour Root, l’installateur vérifie et choisit une méthode disponible pour contrôler Home. Si la compatibilité ne peut pas être vérifiée, l’installation s’arrête ; ne contournez pas le contrôle qui a échoué.

**No-root → Root:** Si No-root a été réinstallé après une suppression complète, le passage à Root peut nécessiter un nettoyage préalable. Sauvegardez les préférences de Home, choisissez **Désinstaller Clean Your TV** avec la connexion Root enregistrée et attendez la suppression vérifiée. Cela supprime aussi Home et Helper de No-root. Installez ensuite Root et conservez les données de récupération.

### Configurer Developer Mode (No-root)

Developer Mode permet à CYTV d’installer des apps sur un TV sans root.

1. Sur le TV, ouvrez LG Apps, cherchez Developer Mode et installez cette app.
2. Ouvrez Developer Mode et connectez-vous avec votre compte LG Developer. Si nécessaire, créez un compte sur [LG Developer](https://webostv.developer.lge.com).
3. Activez Dev Mode Status. Le TV redémarre. Ouvrez ensuite Developer Mode à nouveau.
4. Activez Key Server et laissez Developer Mode ouvert. Saisissez son IP Address comme adresse du TV dans CYTV.
5. Saisissez la Passphrase: les six caractères affichés dans Developer Mode sur le TV. Respectez les majuscules et minuscules.

Utilisez le code du TV, pas le mot de passe du compte LG. Si aucun code n’apparaît, activez Key Server.

L’appairage est une étape distincte: quand le TV le demande, autorisez CYTV avec la télécommande.

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
4. Suivez l’assistant. Gardez la TV allumée, le même réseau et CYTV ouvert jusqu’à la fin. Ne forcez pas l’arrêt de l’application Android. Root active le contrôle de Home dès la récupération préparée.

L’installation Root continue avec un avertissement si les entrées du TV ne peuvent pas être lues mais que la liste des applications est valide. Des entrées peuvent manquer dans Home ; une liste d’applications illisible ou vide arrête toujours l’installation. Enregistrez le rapport de diagnostic si l’avertissement persiste.

## 5. Vérifier la télécommande

1. Ouvrez une autre application sur la TV et appuyez brièvement sur **Home**. Clean Your TV doit s’ouvrir. Indiquez votre observation dans l’assistant ; ignorez le test si vous ne l’avez pas effectué.
2. Vérifiez flèches, OK, Retour, volume et son. Testez séparément la veille/le réveil et un démarrage après débranchement du secteur. Une installation réussie ne vérifie pas ces actions à elle seule.

<a id="utilisation-et-récupération"></a>

## 6. Utilisation et récupération

Prise en charge IR No-root: relâcher Home après un appui court programme Clean après environ 700 ms ; LG Home peut apparaître brièvement. Un appui long reste géré par webOS et trois appuis arrêtent toujours Helper. L’accès en Developer Mode standard reste non vérifié ; ne modifiez pas les permissions des périphériques d’entrée.

Les flèches sélectionnent, OK ouvre ; maintenez OK pour réorganiser. Un appui bref sur Retour conserve la navigation et la confirmation de sortie de l’application. Home ouvre le lanceur si le contrôle est actif. Maintenez Retour pendant 1,2 seconde pour ouvrir LG Home une fois. L’interrupteur du contrôle de Home et vos paramètres restent inchangés.

**Appuyez trois fois sur Home en deux secondes**, en relâchant entre les appuis. Cela rétablit LG Home et arrête le contrôle sans effacer vos préférences.

No-root: Pour relancer le contrôle de Home, ouvrez Home Helper, choisissez Démarrer Helper et confirmez. Votre choix d’écran Home est conservé. Root: activez **Changer Home** dans les paramètres de Home pour reprendre. **Ouvrir LG Home** ouvre LG Home une fois sans modifier la destination de Home. Pour rétablir LG Home comme destination permanente, désactivez **Changer Home**. N’exécutez jamais les deux contrôleurs ensemble. Si la panne revient, laissez LG Home actif.

Une mise à jour ne redémarre pas un Helper No-root arrêté. Relancez-le explicitement comme indiqué ci-dessus ; ne supprimez pas manuellement les marqueurs d’arrêt.

## Besoin d’aide ?

Si `ssh-identity-changed` apparaît après une réinitialisation ou une modification SSH, arrêtez: CYTV a bloqué la clé mémorisée modifiée avant l’authentification. La confirmation de confiance initiale ne la remplace pas ; une désinstallation en attente n’explique pas cet écart. Conservez le profil d’origine, les clés et les données de récupération. Aucune commande automatique de renouvellement de confiance n’est prise en charge. Il faut vérifier indépendamment l’identité/l’empreinte du TV, puis disposer d’une procédure revue préservant le profil: [récupération de l’identité SSH](../RECOVERY.md#ssh-identity-changed).

Après une interruption, utilisez la même connexion enregistrée et commencez par **Vérifier l’état du téléviseur**. Continuez uniquement avec l’action de récupération proposée par l’assistant. Si l’état est inconnu, enregistrez le rapport de diagnostic et arrêtez-vous ; conservez les données de récupération et ne réinstallez pas à l’aveugle.

Pendant la récupération, laissez le contrôle de Home désactivé et conservez les rapports de diagnostic originaux ainsi que la connexion enregistrée. Confirmez séparément la vérification et les modifications. Suivez le guide détaillé pour votre version installée ; ne forcez pas la réinstallation et n’effacez pas l’état de récupération.

Indiquez modèle de TV, micrologiciel, No-root ou Root, appareil d’installation, étape et message d’erreur. Retirez mots de passe, clés, adresses et données personnelles avant de partager le rapport. Rien n’est publié automatiquement.

[Signaler un problème](../FEEDBACK.md) · [Récupération — anglais](../RECOVERY.md) · [Mettre à jour ou supprimer — anglais](../MAINTENANCE.md) · [Autres langues](../LANGUAGES.md)

### Suppression simple

Choisissez **Désinstaller Clean Your TV** dans Maintenance avec la même connexion enregistrée. Confirmez une fois. Les applications et fichiers connus du projet présents sont supprimés ; les éléments absents sont ignorés, même après une installation partielle.

Sur les anciens téléviseurs sans application LG Home distincte, la suppression No-root peut afficher la TV en direct. Laissez le téléviseur allumé et effectuez le redémarrage demandé ; ne supprimez pas les données de récupération et ne réinitialisez pas le téléviseur.

Quand demandé, débranchez l’alimentation TV, rebranchez-la, attendez le réseau et choisissez **Réessayer**. Veille ou Quick Start n’est pas un redémarrage complet ; CYTV ne redémarre pas le téléviseur automatiquement. En cas de déconnexion, vérifiez la connexion et réessayez la même suppression sans autre assistant de récupération. Si l’accès est refusé, utilisez la connexion Root demandée ; si le téléviseur est occupé, patientez et réessayez. Le succès apparaît seulement après vérification du nettoyage final. Gardez les clés et rapports d’origine. Les commandes d’urgence et le consentement au partage restent applicables.

Une installation échouée ou interrompue propose directement la récupération. Si No-root ne peut pas continuer, confirmez une fois la suppression complète. La suppression effectue jusqu’à trois tentatives en cas de perte temporaire de connexion ou de processus CYTV occupé. Si Root est nécessaire, choisissez **Se connecter avec Root** pour le même téléviseur ; le nettoyage Root vérifié termine aussi sa suppression No-root bloquée. Après un échec d’activation Root, CYTV tente de rétablir et vérifier LG Home sans réactiver. Une annulation avec du travail inachevé conserve le rapport et les actions de récupération. L’arrêt d’urgence reste actif.

Après une erreur de connexion pendant la suppression, ouvrez les détails, vérifiez le réseau ou choisissez une clé SSH Root existante, puis réessayez. Adresse, édition, port et vérification de la clé du téléviseur restent fixes. No-root vérifie Helper avant l’association: arrêtez-le et confirmez la nouvelle vérification dans le même parcours. Seul un téléviseur vide vérifié sans installation en attente peut éviter le redémarrage ; après une suppression réelle, effectuez le redémarrage demandé. Si le service des entrées échoue, le nettoyage sûr des paquets continue ; le succès exige toujours la vérification du nettoyage du raccourci.

**Réinstaller Root :** Choisissez **Configurer mon téléviseur → Root** avec la connexion enregistrée et confirmez **Réinstaller Root ?**. L’installateur rétablit LG Home et supprime entièrement Clean Your TV, ses outils de mise à jour, Home Helper et les préférences enregistrées. Après vérification de la suppression, il installe et active les paquets et l’environnement Root fournis avec cet installateur. Les autres apps du TV et l’accès root/SSH existant sont conservés. Si la suppression s’arrête ou demande un redémarrage complet, terminez-la avant de relancer la configuration. **Désinstaller Clean Your TV** seul ne lance jamais une nouvelle installation.

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

## Météo

Ouvrez Réglages → Météo, sous Fonds d’écran. Activez la météo puis ouvrez Ville pour rechercher et choisir la bonne région et le bon pays, ou choisissez Automatique pour une ville approximative selon votre connexion. Un VPN peut modifier le résultat ; utilisez la recherche manuelle si la ville manque ou est incorrecte. La ville détectée ou choisie apparaît dans les réglages. Choisissez °C / m/s ou °F / mph et un format disponible : compact, actuel, détaillé ou quatre jours. L’aperçu suit le thème ; Exemple indique des données fictives. Liquid Glass accepte uniquement le format compact. Ribbon et Atmosphere n’affichent pas la météo. La désactivation arrête les requêtes et masque la ville, les unités et le format ; le choix de la source reste disponible. En cas de panne, les données récentes peuvent rester temporairement ; ensuite la météo est masquée jusqu’à son actualisation.

Choisissez la source des prévisions : Auto, MET Norway ou Open-Meteo. Auto commence par MET Norway, essaie une fois Open-Meteo en cas d’échec, puis réutilise la dernière source fonctionnelle et son cache. Le choix manuel ne change jamais automatiquement de source. Les nouveaux réglages utilisent Auto ; les anciens réglages sans source conservent Open-Meteo. La source réelle est affichée. La disponibilité dépend du réseau. MET s’actualise au plus toutes les trois heures ; le cache expire après six heures. Les champs absents sont masqués : MET ne fournit ni température ressentie ni probabilité de précipitations. Les plages quotidiennes résument des points de prévision, pas des extrêmes mesurés.

Les coordonnées sont envoyées à api.met.no ou api.open-meteo.com, les recherches de villes à geocoding-api.open-meteo.com. La localisation automatique facultative transmet votre IP publique à get.geojs.io. Les connexions utilisent HTTPS ; aucune clé API n’est nécessaire. Le lieu, la source et le cache restent sur le téléviseur. Sources des données présente les conditions et crédits, dont l’Institut météorologique norvégien (MET Norway, CC BY 4.0).

Le bouton Sources des données dans l’en-tête Météo ouvre les informations sur les services et licences.
