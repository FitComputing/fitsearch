# Déployer FitSearch V2.17.4 sous Linux

## Mode utilisateur

Commande : `./install.sh user`

- application : `~/.local/share/fitsearch/app`
- données : `~/.local/share/fitsearch`
- configuration : `~/.config/fitsearch/fitsearch.env`
- service : `~/.config/systemd/user/fitsearch.service`
- adresse : `http://127.0.0.1:8765`

Chaque compte Linux peut réaliser sa propre installation et possède alors ses données séparées.

## Mode système local

Commande : `sudo ./install.sh system`

- application active : `/opt/fitsearch/current`
- versions installées : `/opt/fitsearch/releases`
- données partagées : `/var/lib/fitsearch`
- configuration : `/etc/fitsearch/fitsearch.env`
- service : `/etc/systemd/system/fitsearch.service`
- compte technique : `fitsearch`, sans connexion interactive
- adresse : `http://127.0.0.1:8765`

Tous les comptes de la machine consultent la même instance et partagent sa configuration. Le service démarre avec la machine, sans ouverture de session. Ce mode reste mono-utilisateur au niveau applicatif.

## Mode serveur multi-utilisateur

Commande : `sudo ./install.sh server`

Le service continue d’écouter uniquement sur `127.0.0.1:8765` et doit être publié par un reverse proxy HTTPS. L’accès invité est limité aux recherches encyclopédiques. Les comptes authentifiés disposent chacun d’une base, de préférences et d’un coffre d’identifiants séparés.

Créer le premier administrateur après l’installation :

```bash
sudo -u fitsearch env FITSEARCH_DATA=/var/lib/fitsearch \
  /opt/fitsearch/current/.venv/bin/fitsearch-accounts create adminthi --role admin
```

Le mot de passe est demandé sans être affiché. Lors de la première création d’un administrateur, l’ancienne base mono-utilisateur et son coffre sont copiés vers son profil.

## Passer du mode utilisateur au mode système

1. Dans FitSearch utilisateur, créer une sauvegarde depuis **Préférences → Système**.
2. Arrêter l'ancien service : `systemctl --user disable --now fitsearch`.
3. Installer le mode système : `sudo ./install.sh system`.
4. Ouvrir FitSearch puis restaurer la sauvegarde.

Les clés et jetons ne figurent jamais dans une sauvegarde : il faut les saisir de nouveau dans l'instance système.

## Hôte et port

Le fichier `fitsearch.env` contient `FITSEARCH_HOST`, `FITSEARCH_PORT`, `FITSEARCH_DATA`, `FITSEARCH_MODE` et `FITSEARCH_AUTH_MODE`. Tous les modes imposent l'écoute interne sur `127.0.0.1`. Le mode serveur ajoute l’authentification applicative sans exposer directement Uvicorn au réseau.

Après une modification du port, redémarrer le service concerné :

```bash
systemctl --user restart fitsearch
sudo systemctl restart fitsearch
```

## Diagnostic

```bash
./fitsearch-doctor.sh user
./fitsearch-doctor.sh system
```

## Désinstallation

```bash
./uninstall.sh user
sudo ./uninstall.sh system
```

La désinstallation conserve les données. Leur suppression éventuelle doit rester une opération séparée et volontaire.
