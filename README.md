# CookiGram Contract

Contrat public et versionné entre un carnet de contenu CookiGram et le moteur
de compilation `cookigram-core`.

La version courante documentée est **1.1.0**. Le contrat décrit les entrées acceptées, les
artefacts produits par `cookigram build`, la provenance du build et les règles
de compatibilité. Il ne contient ni moteur de rendu ni recettes de production.

## Utilisation

```bash
python -m cookigram_contract validate examples/minimal-content
python -m cookigram_contract hash examples/minimal-content
python -m cookigram_contract verify-output _site
```

Le validateur ne modifie jamais le contenu. La spécification complète se
trouve dans [`CONTRACT.md`](CONTRACT.md), les schémas dans [`schema/`](schema/).

## Structure attendue

```text
content/
├── recipes/*.gram
├── .gram/ingredients.yaml
├── .gram/ingredient-provenance.yaml
├── site-config.yaml
└── static/{images,icons,illustrations}/
```

La version **1.0.0** reste le comportement générique historique. La version
**1.1.0** ajoute une validation Meal Composition opt-in via le paramètre
`contract_version` de `validate_recipe`; ses règles normatives sont définies
dans [`CONTRACT.md`](CONTRACT.md).

Les versions suivent SemVer : toute modification incompatible des chemins, de
la syntaxe Gram, des champs obligatoires ou des artefacts exige une version
majeure.

## Développement

```bash
python -m pip install -e '.[dev]'
pytest
```

Licence : MIT.

<!-- cookigram-ecosystem:start -->
## Écosystème CookiGram

**Ce dépôt :** le contrat public et versionné entre contenu et moteur. Il définit les entrées/artefacts compatibles et leur validation déterministe, sans embarquer le catalogue ni l'UI.

Repères : [catalogue public](https://github.com/CookiGram/cookigram) · [moteur](https://github.com/CookiGram/cookigram-core) · [contrat](https://github.com/CookiGram/cookigram-contract) · [CookiList](https://github.com/CookiGram/shopping-list) · [Home](https://github.com/CookiGram/home) · [MCP produit](https://github.com/CookiGram/cookigram-mcp) · [Bandleader](https://github.com/CookiGram/Bandleader) · [Orchestra](https://github.com/CookiGram/Orchestra) · [Journey](https://github.com/CookiGram/cookigram-journey).
<!-- cookigram-ecosystem:end -->
