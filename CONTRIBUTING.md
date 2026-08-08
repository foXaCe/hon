# Contributing

Merci de votre intérêt pour l'intégration hOn !

## Bug reports

Utilisez le [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).

## Feature requests

Utilisez le [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).

## Pull requests

1. Fork
2. Branche dédiée : `git checkout -b feat/ma-feature`
3. Runner pre-commit installé :

   ```bash
   pipx install prek   # ou brew install j178/prek/prek
   prek install
   ```

   (prek est un drop-in Rust de pre-commit, 10× plus rapide. Si tu préfères la version Python : `pipx install pre-commit`.)

4. Code + tests : `pytest --cov=custom_components/hon`
5. Lint : `ruff check . && ruff format .`
6. Type check : `mypy custom_components/hon`
7. Commit (conventional commits) : `feat: …`
8. Push + PR vers `main`

## Setup local

Voir [.devcontainer/](.devcontainer/) ou installer manuellement les deps de `requirements_dev.txt`.

## Gestion des dépendances

Ce repo utilise **Renovate** (et non Dependabot). Les PR de MAJ sont ouvertes
par le bot `@renovate[bot]`. Voir le [dashboard Renovate](../../issues?q=is:issue+author:app/renovate).
