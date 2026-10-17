# Contribuer à FitSearch

Merci de votre intérêt pour FitSearch.

## Avant de proposer une modification

- partez de la branche `main` à jour ;
- créez une branche dédiée ;
- ne placez aucun mot de passe, jeton, identifiant ou donnée personnelle
  dans le dépôt ;
- limitez chaque proposition à un sujet clairement identifié.

## Nommage des branches

Exemples :

- `feature/nom-de-la-fonctionnalite`
- `fix/description-du-correctif`
- `docs/sujet-documente`
- `security/description-non-sensible`

## Contrôles locaux

Avant chaque commit :

```bash
python3 -m compileall -q fitsearch
bash -n install.sh
bash -n uninstall.sh
bash -n fitsearch-doctor.sh
git diff --check

```

## Commits

- utilisez un message court décrivant clairement la modification ;
- vérifiez les changements avant de valider ;
- ne mélangez pas plusieurs sujets indépendants dans un même commit.

## Pull Requests

La Pull Request doit préciser :

- le problème traité ;
- la solution apportée ;
- les contrôles effectués ;
- les éventuelles conséquences sur l’installation ou la configuration.

## Licence des contributions

Toute contribution proposée à FitSearch est fournie sous la licence
`AGPL-3.0-or-later`, conformément à la licence du projet.
