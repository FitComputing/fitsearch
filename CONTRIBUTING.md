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
