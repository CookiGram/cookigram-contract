# Contrat CookiGram — version 1.1.0

Ce document est normatif. « Doit » indique une obligation ; « peut » indique
une capacité optionnelle. Le contrat porte sur la frontière contenu ↔ moteur,
pas sur l’implémentation interne du moteur.

## 1. Corpus d’entrée

Le moteur reçoit une racine de contenu (`--content-dir`) et, éventuellement,
un répertoire de recettes explicite (`--recipes-dir`). Les chemins sont
relatifs à la racine du corpus et utilisent `/` comme séparateur.

| Chemin | Obligatoire | Règle |
| --- | --- | --- |
| `recipes/*.gram` | oui, sauf `--allow-empty` pour `check` | Chaque fichier est une recette Gram valide. |
| `.gram/ingredients.yaml` | oui si une recette contient des ingrédients | Base YAML `ingredients`. |
| `.gram/ingredient-provenance.yaml` | oui si la base ingrédients existe | Chaque identifiant de la base a une provenance. |
| `site-config.yaml` | non | Configuration incluse dans `content_sha` si présente. |
| `static/` | non | Images, icônes et illustrations servies telles quelles. |

Une entrée présente doit être lisible et correctement formée. Le moteur ne
complète pas silencieusement une provenance ou une donnée nutritionnelle
manquante.

## 2. Format Gram

Une recette est un fichier UTF-8 composé d’un frontmatter YAML délimité par
`---`, suivi d’étapes. Le frontmatter doit contenir au minimum : `title`,
`portions` (entier positif), `prep_time`, `total_time`, `tags` (liste non
vide), `source`, `author`, `image`, `image_credit` (`author`, `source`,
`license`) et `scaling`. Une recette doit contenir au moins une étape.

Les champs optionnels `appliances`, `required_equipment`, `spiciness` (entier
de 0 à 5), `flavors` et `image_generation` sont définis par
[`schema/recipe-frontmatter.schema.json`](schema/recipe-frontmatter.schema.json).

Les ingrédients référencés par `@nom{…}` doivent être connus par leur nom ou un
alias dans `.gram/ingredients.yaml`. Chaque entrée possède une provenance
correspondante dans `.gram/ingredient-provenance.yaml`.

Une recette qui utilise `^{120 C}` ne peut déclarer que les modèles Thermomix
TM5, TM6 ou TM7 ; le TM31 ne possède pas ce palier.

## 3. Compilation et CLI

```text
cookigram build [--output DIR] [--site-url URL]
                [--content-dir DIR] [--recipes-dir DIR]
cookigram check [RECETTE ...] [--root DIR] [--allow-empty]
cookigram validate [RECETTE ...] [--root DIR] [--allow-empty]
cookigram gate [--fix] [--fast] [--all-recipes] [--root DIR]
```

Le code `0` signifie succès et le code `1` violation du contrat, validation ou
build échoué. Les autres codes sont réservés aux erreurs d’environnement.

## 4. Sortie minimale

Un build réussi doit produire `index.html`, `assets/`,
`recipes/<slug>/index.html`, `recipes/<slug>/cook/index.html`,
`manifest.webmanifest`, `sw.js`, `recipes.json`, `sitemap.xml`, `robots.txt`,
`feed.xml`, `.nojekyll` et `provenance.json`.

`provenance.json` respecte [`schema/provenance.schema.json`](schema/provenance.schema.json) :

```json
{"content_sha":"<sha256 hexadécimal>","core_sha":"<révision ou unknown>","built_at":"<instant UTC ISO-8601 se terminant par Z>"}
```

`content_sha` doit être identique pour un même corpus. Il est calculé sur les
fichiers d’entrée en ordre lexical, avec leur chemin relatif et leur contenu.
`built_at` ne participe jamais à cette empreinte.

## 5. Compatibilité

Un moteur déclare la version de contrat qu’il accepte. Une version majeure
différente est incompatible par défaut. Un moteur acceptant `1.x` doit ignorer
les champs optionnels inconnus et refuser toute absence de champ obligatoire.

### 5.1 Meal Composition (1.1.x opt-in)

`1.0.0` conserve son comportement historique. La validation Meal Composition
est activée uniquement lorsque le consommateur appelle `validate_recipe` avec
`contract_version="1.1.x"`; le paramètre vaut `1.0.0` par défaut.
L’absence de `meal` est valide et signifie `unknown`; aucune information du
titre, des ingrédients, des tags, de la nutrition ou du texte libre n’est
déduite.

Un bloc `meal` contient `completeness` (`complete`, `partial`, `component`),
un `role` optionnel ou requis selon la forme, et `needs` optionnel. Les rôles
sont `main`, `starch`, `vegetable`, `sauce`; les cibles de `needs` sont
`starch`, `vegetable` et `sauce`, donc jamais `main`. Les listes ne contiennent
pas de doublons et les listes vides sont équivalentes à l’absence.

- `component` exige exactement un rôle et aucun besoin ;
- `partial` exige exactement un rôle et au moins un besoin ;
- `complete` autorise un rôle informatif, mais aucun besoin.

Tout champ `meal` inconnu est rejeté, sauf `benefits_from`, toléré uniquement
pour compatibilité avec des annotations héritées et ignoré sans sémantique.
Il n’y a ni migration automatique ni négociation dynamique de capacités.

Les erreurs exposent uniquement un code stable (`invalid_type`, `invalid_value`,
`required`, `duplicate`, `forbidden`) et un chemin de champ.
