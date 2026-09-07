# CookiGram Contract

Contrat public et versionné entre un carnet de contenu CookiGram et le moteur
de compilation `cookigram-core`.

La version courante est **1.1.0**. Le contrat décrit les entrées acceptées, les
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
**1.1.0**, explicitement choisie par le consommateur via le paramètre
`contract_version` de `validate_recipe`, ajoute la validation optionnelle du
bloc `meal` pour une valeur `1.1.x`.
Sans bloc `meal`, la qualification reste `unknown`; aucune inférence ni
migration n'est effectuée. `benefits_from` est toléré uniquement comme champ
hérité ignoré.

Les versions suivent SemVer : toute modification incompatible des chemins, de
la syntaxe Gram, des champs obligatoires ou des artefacts exige une version
majeure.

## Développement

```bash
python -m pip install -e '.[dev]'
pytest
```

Licence : MIT.
