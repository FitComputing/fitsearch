# FitSearch V2.17.6

Métamoteur local, léger et sans Docker, pensé pour Debian, Deepin et Arch Linux.

La V1.2 ajoute des filtres combinables par période, langue, source et domaine. Le filtre de langue est transmis aux sources qui le prennent nativement en charge, notamment Wikipédia et Open Library. Le filtre de période conserve uniquement les résultats possédant une date vérifiable.

La V1.3 ajoute une pagination progressive. Dix résultats sont affichés au départ ; le bouton « Afficher davantage » charge la page suivante sans effacer les résultats précédents et conserve la requête, le profil, la catégorie et tous les filtres actifs.

La V1.4 rend le classement explicable. Survolez un score — ou placez-y le focus au clavier — pour voir les points accordés à la fiabilité de la source, aux correspondances dans le titre et le résumé, à la fraîcheur et à la concordance entre plusieurs sources.

La V1.5 comprend les opérateurs `"expression exacte"`, `site:domaine`, `-mot` et `filetype:pdf`. Ils peuvent être combinés dans une même requête. `site:` remplit automatiquement le filtre de domaine, `-mot` retire les résultats contenant ce mot, et les résultats arXiv sont directement convertis en liens PDF lorsque `filetype:pdf` est demandé.

La V1.6 ajoute un cache SQLite local temporaire. Il est actif par défaut pendant 15 minutes et peut être réglé sur 5 minutes ou 1 heure. Une recherche identique réutilise les résultats locaux au lieu de rappeler les APIs. Le cache est limité aux 100 recherches les plus récentes, supprime automatiquement les entrées expirées et peut être désactivé ou vidé depuis les réglages. Les requêtes ne sont pas stockées en clair dans les clés du cache.

La V1.7 ajoute de véritables actualités via les flux RSS publics de **Le Monde**, **The Guardian** et **BBC News**. Les flux sont téléchargés en parallèle, filtrés localement selon la requête et la langue, normalisés, datés, dédupliqués puis classés avec les autres résultats. Ils fonctionnent avec le filtre de période et le cache temporaire.

La V1.8 ajoute des favoris locaux pour les résultats Web, Images et Actualités. Ils disposent de leur propre table SQLite, restent disponibles même lorsque l'historique est désactivé ou effacé, et sont accessibles depuis le bouton en forme de cœur dans l'en-tête. Aucune synchronisation ni aucun compte n'est utilisé.

La V1.9 exporte tous les résultats actuellement affichés en Markdown, CSV UTF-8 ou fichier HTML de marque-pages compatible avec les navigateurs. Les pages chargées via « Afficher davantage » sont incluses. La génération est locale, les champs HTML sont échappés et le CSV neutralise les cellules susceptibles d'être interprétées comme des formules.

La V2.0 ajoute les recherches enregistrées. Chaque raccourci mémorise la requête, la catégorie Web/Images/Actualités, le profil, le mode démo, la période, la langue, la source et le domaine. Une configuration identique met à jour son nom au lieu de créer un doublon. Ces raccourcis disposent de leur propre table SQLite et restent indépendants de l'historique et des favoris.

La V2.1 permet d'ajouter des flux RSS ou Atom personnels depuis les réglages. FitSearch vérifie le flux avant de l'enregistrer, permet de l'activer ou le désactiver, l'intègre au filtre Source, au profil Rapide, au classement et au cache. Les téléchargements sont limités à 2 Mo et les adresses locales, privées, les identifiants intégrés et les ports personnalisés sont bloqués afin de protéger les services internes de la machine.

La V2.2 renomme l'onglet **Actualités** en **Actualités/RSS**, regroupe les articles qui couvrent vraisemblablement le même sujet et affiche leurs sources associées sous un seul résultat. Elle ajoute aussi un bouton **Aperçu** : un panneau latéral présente le titre, le résumé, le site et l'adresse finale sans exécuter les scripts de la page. L'aperçu ne télécharge que les 512 Kio initiaux, suit au maximum quatre redirections et refuse les adresses locales ou privées.

La V2.3 corrige la répétition des flux personnels dans le filtre Source. Sur un ordinateur, laisser le pointeur environ une demi-seconde sur un résultat affiche désormais son aperçu ; le survol d'un autre résultat le remplace. Le bouton **Aperçu** fige le panneau afin de pouvoir le consulter tranquillement. Sur un écran tactile, seul le bouton ouvre l'aperçu.

Elle ajoute aussi une sauvegarde et une restauration depuis les réglages. Le fichier JSON contient les moteurs activés, les préférences, les flux RSS personnels, les favoris, l'historique et les recherches enregistrées. Le cache temporaire n'est pas sauvegardé. Une restauration contrôle le format et la taille du fichier, puis remplace les données locales uniquement après confirmation ; une erreur annule toute l'opération.

La V2.4 transforme l'aperçu en fiche de lecture. FitSearch extrait jusqu'à cinq paragraphes significatifs de la page et affiche son image éditoriale lorsqu'elle est déclarée par le site. L'image transite par un relais local protégé : seules les images JPEG, PNG, WebP, GIF et AVIF publiques de moins de 3 Mo sont acceptées. Le HTML lu est limité à 768 Kio et aucun script de la page n'est exécuté. Si un site bloque la lecture ou ne publie pas de métadonnées exploitables, l'aperçu conserve simplement les informations du résultat de recherche.

La V2.5 ajoute un tableau de santé des sources. FitSearch mémorise, uniquement lors des recherches réelles, leur disponibilité, le dernier temps de réponse, une moyenne glissante, le nombre de résultats, le dernier succès et la dernière erreur. Un voyant global apparaît dans l'en-tête et ouvre directement le diagnostic dans les réglages. Le bouton **Tester les sources actives** lance un contrôle volontaire ; aucune surveillance permanente n'est effectuée. Les mesures techniques sont temporaires et ne font pas partie des sauvegardes.

La V2.6 ajoute les deux raccourcis essentiels demandés : **Échap** ferme le panneau actif et **Ctrl + Entrée** lance la recherche. Le classement répartit aussi davantage les premières positions entre les sources et les domaines. La pertinence reste prioritaire, les scores ne sont pas artificiellement modifiés et aucun résultat n'est supprimé : seul l'ordre est rééquilibré pour éviter une liste trop uniforme.

La V2.7 étend l'aperçu aux résultats Images. Sur ordinateur, un survol maintenu 650 ms ouvre la fiche ; le bouton **Aperçu** la fige et reste l'unique déclencheur sur écran tactile. La fiche présente une image agrandie, la légende, un extrait de la page source, l'auteur ou le crédit, la licence et deux accès distincts vers la page source et le fichier original lorsque ces informations existent. Les illustrations d'aperçu passent toujours par le relais local sécurisé de FitSearch.

La V2.8 ajoute la mise à jour simplifiée dans les réglages. Sélectionnez une archive ZIP FitSearch de confiance : l'application contrôle sa structure, sa taille et sa version, sauvegarde la base SQLite, installe la nouvelle version puis redémarre le service utilisateur. Une installation incomplète restaure automatiquement les fichiers précédents. Les cinq sauvegardes automatiques les plus récentes sont conservées dans `~/.local/share/fitsearch/backups`. Une version antérieure, une archive ambiguë, un chemin dangereux ou un lien symbolique est refusé.

La V2.9 organise les sources dans les réglages grâce à une liste déroulante par grand domaine : Généralistes, Sciences & Santé, Culture & Médias, Technologie & Ingénierie, Nature & Environnement, Société & Monde et Mes sources. Elle ajoute dix sources publiques : **Wikidata**, **OpenAlex**, **Crossref**, **PubMed**, **GBIF**, **MusicBrainz**, **Electrical Engineering**, **Super User**, **Unix & Linux** et **Movies & TV**. Ce classement sert à rendre les réglages lisibles ; une même source peut naturellement apparaître dans plusieurs domaines.

La V2.9.1 remplace la lecture de la page MusicBrainz par un aperçu musical natif. La fiche réunit la pochette de Cover Art Archive, l’artiste, le type de publication, la première date de parution, les genres, le label, le pays, le nombre d’éditions et jusqu’à douze morceaux. Elle utilise les API publiques, respecte leur cadence et conserve temporairement les fiches déjà consultées pendant une heure. La page MusicBrainz n’est plus chargée dans l’aperçu ; elle reste accessible avec le bouton d’ouverture du résultat.

La V2.10 ajoute le domaine **Loisirs & Jeux** et la source **Scryfall · Magic**, activée par défaut. La recherche accepte aussi bien les noms ordinaires que la syntaxe avancée Scryfall. Son aperçu natif affiche les visuels, les deux faces lorsqu’une carte se transforme, le coût de mana, le type, les règles, les caractéristiques, l’extension, la rareté, l’artiste, les formats autorisés et les prix indicatifs disponibles. Les fiches restent une heure en mémoire. **Magic-Ville** est proposé comme accès externe francophone : il s’ouvre dans le navigateur sans contourner sa protection anti-robot.

La V2.11 ajoute **OpenHammer · Warhammer 40K** pour rechercher les unités, leurs caractéristiques, points, armes, aptitudes et mots-clés, ainsi que **Warhammer 40K Wiki** pour le lore. Les réglages proposent la 10e édition, la 11e ou les deux ; le choix est conservé dans SQLite et dans les sauvegardes. Les fiches OpenHammer portent clairement la mention communautaire et rappellent de vérifier règles et coûts dans les publications officielles. Warhammer Community et Lexicanum sont disponibles comme accès externes dans Loisirs & Jeux.

La V2.12 ajoute **GitHub**, **TMDB**, **Europeana**, **Discogs** et **DigiKey**. GitHub fonctionne immédiatement sans clé ; son jeton personnel reste facultatif. Les quatre autres connecteurs sont désactivés par défaut et disposent d'une fiche **Accès aux sources** permettant d'enregistrer, tester ou effacer leurs identifiants. Les secrets sont conservés dans `~/.local/share/fitsearch/credentials.json` avec des permissions limitées au compte utilisateur. Ils ne sont jamais copiés dans les sauvegardes FitSearch, le cache, les exports ou la base SQLite.

La V2.12.1 affiche directement la santé de chaque source dans sa ligne de réglage : pastille verte, orange, rouge ou grise, temps de réponse moyen et état compact. Le survol de la ligne fournit le dernier contrôle et le nombre de résultats observés. Le bouton ON/OFF et le tableau de santé détaillé sont conservés.

La V2.12.2 corrige la collision visuelle qui agrandissait les pastilles associées à « Aucun résultat ». Le nom et l’état sont désormais accolés sous la forme **Source : information**. Le curseur des interrupteurs actifs devient noir, le texte de **Enregistrer et tester** devient noir et le thème clair emploie un vert plus sombre pour les textes afin d'améliorer leur contraste sur fond blanc.

La V2.13 rassemble l’administration de FitSearch dans un centre de préférences unique. Le bandeau conserve seulement **Préférences** et **Thème**. La navigation interne donne accès aux Sources, à la Santé, aux Recherches enregistrées, aux Favoris, aux Clés et jetons, aux Flux RSS et au Système. Chaque rubrique n’affiche que son propre contenu. La pastille du bouton Préférences reprend l’état général des sources ; lorsqu’elle est orange ou rouge, un clic précis sur cette pastille ouvre directement le tableau de santé.

La V2.13.1 corrige le redimensionnement des lignes de santé portant l'état « Réponse vide ». Recherches enregistrées et Favoris sont maintenant réellement intégrés au même panneau, ce qui supprime toute fermeture ou réouverture lors du changement de rubrique. La navigation textuelle est remplacée par sept boutons-icônes compacts, chacun doté d'un nom accessible et d'une infobulle.

La V2.14 transforme **Mes sources** en véritable extension locale. Depuis **Préférences → Sources de recherche → Mes sources**, vous pouvez ajouter sans réinstaller FitSearch un raccourci de recherche, un wiki MediaWiki ou une API JSON publique. Chaque source est testée avant son ajout, peut être activée, désactivée ou supprimée, rejoint le filtre Source et le tableau de santé, et fait partie des sauvegardes locales. FitSearch n'accepte pas de code exécutable dans ces configurations.

La V2.14.1 ajoute le bouton **Analyser le site** à côté de l'adresse d'une source personnelle. FitSearch détecte les formulaires de recherche publics, MediaWiki et les flux RSS/Atom, propose un diagnostic puis peut remplir automatiquement le formulaire. L'analyse n'exécute aucun script distant et contrôle chaque redirection. Le mode Démo reste disponible, mais FitSearch démarre désormais en recherche réelle.

La V2.14.2 rend le bouton d'analyse plus compact grâce à une icône dédiée et le maintient sur la même ligne que l'adresse, y compris sur petit écran. Les flux RSS et Atom repérés sont désormais réellement interrogés et validés ; le diagnostic distingue clairement un flux fonctionnel d'une simple adresse supposée.

La V2.14.3 corrige définitivement l'alignement du champ URL et de son bouton d'analyse. Dans le tableau de santé, la catégorie **Mes sources** regroupe maintenant les flux RSS personnalisés et toutes les sources personnelles, tout en conservant chaque source dans son domaine thématique.

La V2.14.4 ajoute **Système → Limites des flux RSS**. Vous pouvez régler la taille maximale autorisée de 1 à 20 Mo et le nombre d'articles récents considérés de 25 à 500. Les valeurs par défaut sont 5 Mo et 100 articles ; elles sont locales, sauvegardées et immédiatement appliquées aux flux personnalisés.

La V2.14.5 corrige l'affichage de l'encadré **Mes sources** : il apparaît uniquement lorsque le sélecteur de domaines indique **Toutes les sources** ou **Mes sources**.

La V2.15 sépare clairement les **profils éditoriaux** des **types de contenus**. Les profils sont désormais Complet, Encyclopédies, News/RSS et Technologies ; les onglets deviennent Tous, Web, Images, Vidéos, Actualités et Livres. L'onglet Tous compose un mélange équilibré au lieu d'empiler les réponses. Internet Archive alimente réellement Vidéos et Livres, tandis qu'Open Library rejoint aussi l'onglet Livres. Les anciennes recherches enregistrées restent compatibles et sont automatiquement rattachées au nouveau profil équivalent.

La V2.15.1 ajoute le profil **Médias** et classe dans **Culture & Médias** Unsplash, Pexels, Pixabay, Burst, Gratisography, Flickr Creative Commons et Reshot. Ces services s'ouvrent par une recherche externe sûre et immédiate ; aucune page n'est extraite artificiellement. Scholarpedia est interrogé nativement par son interface MediaWiki, tandis qu'Universalis, The Free Dictionary et Larousse rejoignent le profil **Encyclopédies** sous forme de recherches externes. L'indicateur du profil actif devient dynamique et l'ascenseur parasite des onglets disparaît.

La V2.15.2 corrige la grille des résultats de l'onglet **Tous**. Les cartes possédant une vignette réservent désormais trois emplacements explicites — image, contenu et actions — afin que le titre, l'aperçu, les favoris et le score restent alignés. Sur petit écran, les actions passent proprement sous le texte. Les onglets spécialisés conservent leur présentation précédente.

La V2.15.3 trie alphabétiquement les sources du panneau de préférences, les sources personnelles, les flux RSS et la liste du filtre avancé, tout en conservant **Toutes les sources du profil** en première position. Elle ajoute HAL en interrogation native et Cochrane Library, Google Scholar, ScienceDirect et SpringerLink comme recherches scientifiques externes sûres. HAL retourne plusieurs notices directement dans FitSearch ; les quatre autres apparaissent comme résultats-raccourcis afin d'éviter le scraping et les API nécessitant des clés ou des autorisations particulières.

La V2.16 introduit un installateur Linux guidé sans Docker. Le mode **Utilisateur** conserve des données personnelles dans le dossier du compte et crée automatiquement le service systemd utilisateur. Le mode **Système** installe l'application dans `/opt/fitsearch`, les données partagées dans `/var/lib/fitsearch`, la configuration dans `/etc/fitsearch` et un service systemd renforcé exécuté par un compte technique sans connexion. Hôte, port, mode et répertoire de données sont désormais configurables par variables d'environnement. Le panneau Système indique clairement le type d'installation actif. L'exposition réseau reste volontairement bloquée jusqu'à l'arrivée de l'authentification serveur.

La V2.16.1 remplace la mention « 100 % local » du bandeau supérieur par le mode de déploiement réellement actif : **Utilisateur**, **Système** ou **Distant**, précédé d'un point vert.

La V2.16.2 laisse le champ de recherche vide au démarrage et affiche l'invitation grisée « Que souhaitez-vous rechercher ? ». Une validation accidentelle du champ vide ne déclenche aucune recherche.

La V2.16.3 remplace le mode de démonstration visible par le **Mode Actus**. Activé avec un champ vide, il sélectionne automatiquement le profil News/RSS et l'onglet Actualités, récupère jusqu'à sept publications récentes par flux RSS actif, déduplique les liens et les classe par date. Avec une requête, il recherche dans le profil News/RSS. Le moteur de démonstration reste disponible en interne pour le diagnostic.

La V2.16.4 ajoute **La langue française** comme source native des profils Complet et Encyclopédies. FitSearch vérifie l'existence exacte de l'entrée, extrait une courte définition et renvoie la page du dictionnaire. Un mot absent ne produit pas de faux résultat.

La V2.16.5 transforme Larousse en deux sources natives : **Larousse · Dictionnaire** vérifie une entrée et en extrait la définition, tandis que **Larousse · Encyclopédie** renvoie plusieurs articles avec leurs résumés et vignettes éventuelles. Universalis dispose désormais de deux raccourcis externes distincts et corrigés : **Universalis · Articles** et **Universalis · Médias**.

La V2.16.6 ajoute un assistant de traduction DeepL accessible à gauche du logo FitSearch. Il propose la détection automatique, le choix et l'inversion des langues, la copie, l'insertion dans le champ de recherche et le lancement direct. La clé DeepL est conservée dans le coffre local des identifiants et le texte n'est envoyé au service qu'au clic sur Traduire.

La V2.17 ajoute le mode serveur multi-utilisateur. L’invité anonyme peut effectuer les recherches encyclopédiques prévues par FitSearch, mais ne peut rien enregistrer ni ajouter. Chaque utilisateur authentifié possède ses propres réglages, favoris, recherches enregistrées, flux RSS, sources et clés API. Les administrateurs gèrent les comptes sans inscription publique. Les sessions utilisent un cookie sécurisé, les mots de passe sont hachés avec Argon2 et les écritures sont protégées contre les requêtes intersites. La V2.17.1 garantit en plus que la racine contenant les profils est toujours privée (`0700`), indépendamment du masque de permissions de la session d’administration. La V2.17.2 remet en forme l’administration des comptes : séparation visuelle, champs libellés et encadrés, commandes cohérentes avec le thème et suppression de tout débordement horizontal du panneau. La V2.17.3 limite désormais cette administration à la seule rubrique « Système » des préférences. La V2.17.4 ajoute les mises à niveau atomiques pour les installations système et serveur : préparation isolée, bascule du lien `current`, contrôle de santé et retour automatique à la version précédente. La V2.17.5 regroupe le choix de l’édition Warhammer 40K avec la source OpenHammer correspondante afin de réunir son activation et son paramétrage au même endroit. La V2.17.6 corrige la présentation de ce réglage dans le panneau étroit : le toggle reste aligné avec la source et le sélecteur d’édition occupe une sous-carte pleine largeur sans chevauchement.

## Démarrage rapide

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn fitsearch.main:app --host 127.0.0.1 --port 8765
```

Ouvrez ensuite <http://127.0.0.1:8765>. Le mode démo est actif au premier affichage : il fonctionne immédiatement, même sans réseau. Décochez-le pour interroger les vraies sources.

## Installation Linux guidée

```bash
chmod +x install.sh
./install.sh
```

Le script propose les modes utilisateur, système local et serveur.

### Installation utilisateur

```bash
./install.sh user
```

L'application est installée dans `~/.local/share/fitsearch/app`, les données restent personnelles et le service utilisateur est créé et démarré automatiquement. Aucun accès administrateur ni Docker n'est nécessaire.

### Installation système locale

```bash
sudo ./install.sh system
```

L'application active est exposée par `/opt/fitsearch/current` et les versions sont conservées dans `/opt/fitsearch/releases`. Lors de la première migration, l'ancienne installation `/opt/fitsearch/app` est conservée comme version de retour. FitSearch démarre dès l'allumage. Tous les comptes de la machine ouvrent `http://127.0.0.1:8765` et partagent les réglages, favoris, flux, historique et clés stockés dans `/var/lib/fitsearch`.

Ne lancez pas simultanément les installations utilisateur et système sur le même port. Arrêtez d'abord l'ancien service si vous changez de mode.

### Installation serveur multi-utilisateur

```bash
sudo ./install.sh server
sudo -u fitsearch env FITSEARCH_DATA=/var/lib/fitsearch \
  /opt/fitsearch/current/.venv/bin/fitsearch-accounts create adminthi --role admin
```

Ce mode conserve l’écoute interne sur `127.0.0.1:8765` et doit rester derrière un reverse proxy HTTPS. Il n’existe aucune inscription publique : un administrateur crée les comptes. Le premier administrateur reçoit une copie des données de l’ancienne installation système, si elles existent.

## Diagnostic et désinstallation

```bash
./fitsearch-doctor.sh user
./fitsearch-doctor.sh system
./fitsearch-doctor.sh server
./uninstall.sh user
sudo ./uninstall.sh system
```

La désinstallation conserve volontairement la base, les favoris et les réglages. Elle retire uniquement l'application et son service.

## Sources et confidentialité

- **Wikipédia** : API MediaWiki publique, résultats Web.
- **Wikimedia Commons** : API MediaWiki publique, images.
- **Hacker News** : API Algolia publique, Web et actualités/RSS techniques.
- **Open Library** : catalogue public de livres et d'auteurs.
- **Stack Overflow** : API Stack Exchange pour le profil Technique.
- **arXiv** : publications scientifiques pour le profil Technique.
- **Wikidata** : personnes, lieux, œuvres et données structurées.
- **OpenAlex** et **Crossref** : publications et références universitaires.
- **PubMed** : littérature biomédicale et santé.
- **GBIF** : espèces, taxonomie et biodiversité.
- **MusicBrainz** : artistes, albums et patrimoine musical.
- **Electrical Engineering**, **Super User** et **Unix & Linux** : électronique, informatique et systèmes.
- **Movies & TV** : cinéma et télévision via le réseau Stack Exchange.
- **Scryfall · Magic** : cartes Magic: The Gathering, textes, visuels, éditions et légalité par format.
- **Magic-Ville** : raccourci externe vers son moteur francophone ; aucune extraction automatisée.
- **OpenHammer · Warhammer 40K** : unités, caractéristiques, points, armes et aptitudes communautaires.
- **Warhammer 40K Wiki** : personnages, factions, batailles et histoire de l’univers.
- **Warhammer Community** et **Lexicanum** : raccourcis externes vers les documents officiels et l’encyclopédie.
- **GitHub** : dépôts publics, langage, licence, étoiles et activité récente ; jeton facultatif.
- **TMDB** : films, séries et personnalités avec affiches, résumés, dates et notes ; jeton requis.
- **Europeana** : œuvres, musées, institutions et patrimoine européen ; clé API requise.
- **Discogs** : disques, éditions, formats, labels et pochettes ; jeton personnel requis.
- **DigiKey** : composants, références fabricant, descriptions et disponibilité ; identifiants OAuth requis.
- **Le Monde** : flux RSS officiels « À la une » et « En continu », en français.
- **The Guardian** : flux RSS Monde et Technologie, en anglais.
- **BBC News** : flux RSS général, Monde et Technologie, en anglais.
- **Brave / DuckDuckGo HTML** : adaptateurs désactivés par défaut. Brave nécessite une clé ; le parsing HTML est volontairement évité car fragile et potentiellement contraire aux conditions du fournisseur.

Les requêtes en mode réel sont envoyées uniquement aux sources activées. FitSearch n'utilise ni cookie publicitaire ni télémétrie. En mode utilisateur, les réglages sont conservés dans `~/.local/share/fitsearch/fitsearch.db`. En mode serveur, chaque compte possède son profil séparé sous `/var/lib/fitsearch/profiles/`.

## Configurer les nouvelles sources

Ouvrez **Préférences → Clés et jetons**. Pour chaque service, collez la valeur demandée puis choisissez **Enregistrer et tester**. FitSearch n'enregistre l'identifiant que si le service répond correctement. Le bouton **Effacer** retire immédiatement le secret local.

- **GitHub** fonctionne déjà sans jeton. Un jeton personnel finement limité aux dépôts publics augmente seulement la capacité de recherche.
- **TMDB** demande le « jeton d'accès en lecture à l'API » disponible dans les paramètres API du compte. Son utilisation non commerciale impose l'attribution affichée par FitSearch.
- **Europeana** fournit une clé après création d'un compte gratuit sur son portail API.
- **Discogs** permet de créer un jeton personnel dans les paramètres développeur du compte.
- **DigiKey** demande de créer une application sur son portail développeur puis de copier le Client ID et le Client Secret.
- **DeepL API** demande une clé API Free ou Pro. FitSearch reconnaît automatiquement une clé Free à son suffixe `:fx` et choisit l'adresse appropriée.

Le fichier `credentials.json` n'est pas inclus dans la sauvegarde ou la restauration. Après une réinstallation sur un autre ordinateur, il faut donc ressaisir les clés. Ne communiquez jamais ce fichier et ne placez pas de secrets dans une archive FitSearch.

L'historique est strictement facultatif et désactivé par défaut. Lorsqu'il est activé, les 100 dernières recherches sont conservées uniquement dans cette base locale. Les suggestions combinent cet historique local et l'API OpenSearch de Wikipédia.

## Utiliser la traduction DeepL

Après avoir enregistré la clé DeepL, cliquez sur le bouton **文A** placé à gauche du logo FitSearch. Saisissez le texte, conservez la détection automatique ou choisissez une langue source, puis sélectionnez la langue cible. Les actions permettent de copier le résultat, de le placer dans le champ de recherche ou de lancer immédiatement la recherche. Le texte est envoyé à DeepL uniquement au clic sur **Traduire** ; FitSearch ne conserve pas les traductions.

## Rechercher des cartes Magic

Dans les filtres avancés, choisissez **Scryfall · Magic** comme source puis saisissez un nom ordinaire, par exemple `Foudre`. La syntaxe avancée Scryfall est conservée lorsque cette source est sélectionnée : `!"Black Lotus"` cherche ce nom exact, `type:dragon color:red` combine un type et une couleur, et `format:commander` limite les cartes à ce format. Laissez la langue sur Automatique pour toutes les éditions ou choisissez Français pour privilégier les impressions françaises.

Dans **Réglages → Sources de recherche → Loisirs & Jeux**, le lien Magic-Ville ouvre son moteur avancé dans le navigateur. Il ne participe pas à l'agrégation et n'est pas inclus dans le tableau de santé.

## Rechercher dans Warhammer 40,000

Dans **Réglages → Sources de recherche → Loisirs & Jeux**, activez **OpenHammer · Warhammer 40K** puis choisissez directement sur sa ligne la 10e édition, la 11e ou les deux. Dans les filtres avancés de la recherche, sélectionnez ensuite **OpenHammer · Warhammer 40K** pour les unités ou **Warhammer 40K Wiki** pour l’univers et son histoire.

Une recherche `Terminator` dans OpenHammer présente les unités correspondantes avec leurs points, caractéristiques, armes, aptitudes, règles spéciales et mots-clés. Une recherche `Roboute Guilliman` dans le Wiki affiche les articles de lore avec une fiche de lecture illustrée. OpenHammer et le Wiki sont des sources communautaires non officielles : les règles, coûts et mises à jour d’équilibrage doivent être vérifiés via le raccourci **Warhammer Community** avant une partie ou un tournoi.

## Mise à jour depuis une version précédente

Depuis le nouveau dossier décompressé, relancez simplement `./install.sh`, puis redémarrez le service avec `systemctl --user restart fitsearch`. La base SQLite et les réglages existants sont conservés.

## Sauvegarder et restaurer

Ouvrez **Réglages**, puis descendez jusqu'à **Sauvegarde locale**. **Sauvegarder maintenant** télécharge un fichier `fitsearch-sauvegarde-AAAA-MM-JJ-HHMM.json`. Conservez-le comme n'importe quel document personnel.

Pour le restaurer, choisissez **Restaurer une sauvegarde**, sélectionnez ce fichier et confirmez. Les données courantes sont remplacées en une seule opération, puis la page se recharge. FitSearch refuse les fichiers incompatibles ou dépassant 2 Mo. Le cache n'est ni sauvegardé ni restauré.

## Mettre FitSearch à jour

Si FitSearch est installé pour votre utilisateur, la V2.17.6 peut être appliquée avec son archive ZIP depuis **Système → Mise à jour**. Pour une installation système ou serveur, l'administrateur décompresse l'archive et relance respectivement `sudo ./install.sh system` ou `sudo ./install.sh server` ; l'application Web n'a volontairement pas le droit de modifier `/opt/fitsearch`.

Ouvrez **Réglages**, descendez jusqu'à **Mise à jour**, choisissez l'archive ZIP FitSearch reçue et confirmez. Utilisez uniquement une archive provenant d'une source de confiance : la vérification structurelle protège contre les fichiers accidentellement incorrects, mais ne constitue pas une signature cryptographique de l'auteur.

FitSearch refuse les versions antérieures et les archives dépassant 10 Mo. Avant l'installation, la base est copiée proprement avec le mécanisme de sauvegarde SQLite. Si le service systemd est actif, il redémarre automatiquement ; avec un lancement manuel, il faut arrêter puis relancer `fitsearch`. En cas d'échec, les fichiers applicatifs précédents sont restaurés.

## Vérifier la santé des sources

Le voyant rond dans l'en-tête ouvre directement le tableau de santé : gris signifie « pas encore mesuré », vert « sources mesurées disponibles », orange « une source est lente, vide ou en difficulté » et rouge « sources mesurées indisponibles ». Les recherches servies depuis le cache ne modifient pas ces mesures.

Le bouton **Tester les sources actives** interroge chaque source activée avec une requête minimale et met le tableau à jour. Ce diagnostic peut durer quelques secondes. FitSearch n'effectue aucun contrôle automatique en arrière-plan lorsque vous ne recherchez rien.

## Architecture

Chaque source est isolée dans `fitsearch/engines/` et implémente `SearchEngine.search()`. Le module `search.py` exécute les recherches en parallèle, normalise les URL, retire les paramètres de suivi, fusionne les doublons et trie par score. Pour ajouter une source, créez un adaptateur puis enregistrez-le dans `engines/__init__.py`.

## Profils

- **Rapide** : Wikipédia, Wikidata, Hacker News, Open Library et les trois sources RSS.
- **Complet** : toutes les sources actives compatibles.
- **Vie privée** : Wikipédia, Wikidata et Wikimedia Commons.
- **Technique** : Hacker News, Wikipédia, Wikidata, Stack Overflow, Electrical Engineering, Super User, Unix & Linux, arXiv, OpenAlex, Crossref, Guardian et BBC.

## Limites actuelles

Le regroupement des actualités repose sur la proximité des titres : il évite de fusionner les résultats trop différents, mais deux formulations très éloignées d'un même événement peuvent rester séparées. L'aperçu dépend des métadonnées publiées par le site et certains sites peuvent le refuser. Le classement combine la pertinence fournie par la source, la présence des mots recherchés dans le titre et le résumé, la fraîcheur du contenu et la concordance entre plusieurs sources. Les APIs distantes peuvent limiter les requêtes ou être temporairement indisponibles ; FitSearch bascule alors automatiquement sur les résultats de démonstration.

## Licence

FitSearch est un logiciel libre distribué sous la licence GNU Affero
General Public License version 3 ou toute version ultérieure
(`AGPL-3.0-or-later`).

Copyright © 2026 Thierry ROBLIN, entrepreneur individuel exerçant sous l’enseigne FitComputing

Consultez le fichier [LICENSE](LICENSE) pour le texte complet.
