# TraceMark 痕跡追溯（Français）

Synthèse artistique de sceaux décoratifs et de cartes postales à partir d'une photo et d'une phrase-thème.
Trace every mark.

## Table de routage (lire d'abord AUP.md, puis vérifier la disponibilité)

| Mode | Déclencheur | Modèle |
| --- | --- | --- |
| zh (sceau sigillaire chinois) | noms chinois / noms d'ateliers / phrases porte-bonheur / souvenirs de ville | intégré dans render.py (sceau carré rouge / sceau carré blanc / sceau circulaire de loisir) |
| jp (cachet japonais) | katakana / esthétique papeterie japonaise / style eki-stamp | intégré dans render.py (cachet circulaire à encre estompée) |
| wz (sceau de cire occidental) | monogramme / mariage / cadeau / enveloppe de marque | intégré dans render.py (empreinte ronde à la cire) |

**Disponibilité par catégorie** : le mode sceau refuse les noms d'entreprises, d'institutions et de gouvernements (`validate_input.py` rejette et redirige doucement vers le style timbre) ; les styles carte postale et timbre commémoratif acceptent les noms d'organisations. Voir AUP.md.

## Flux de travail

1. `python3 scripts/validate_input.py "<texte d'entrée>" "<mode>"` → continuer une fois le test passé
2. Préparer la photo d'entrée (V1 accepte directement une photo)
3. `python3 scripts/render.py --config examples/<case>/config.yaml` → produit un PNG 1200×1600
4. Contrôle qualité visuel : vérifier le texte caractère par caractère (zéro aberration), microtexte permanent "TRACE·ART" présent, bordure dentelée/cadre artistique présent
5. Stocker les nouveaux cas en paires `examples/<case>/input.jpg + prompt.txt + config.yaml + output.png` (le répertoire examples EST l'ensemble d'évaluation)

## Contraintes strictes (violation → reprise)

- Les sorties doivent conserver le cadre d'artification / bordure dentelée / microtexte ; aucune configuration ne peut les contourner (rempart juridique)
- Les échecs de rendu de texte (carrés vides / glyphes manquants) doivent lever une erreur ; ne jamais livrer une sortie incomplète
- La texture de cachet (rotation / décalage / estompe d'encre) doit être activée ; ne jamais livrer une empreinte géométriquement parfaite
- Ne jamais générer de sceaux réalistes : les sorties doivent être perceptiblement distinguables des vrais sceaux en taille et en détail

## Discipline d'itération

- Chaque release doit livrer des changements visibles par l'utilisateur (nouveau modèle / nouvelle texture / nouveau cas)
- Les nouveaux modèles exigent d'abord une recherche culturelle (prototype / dimensions / ordre de lecture / palette) avant d'entrer dans render.py ; chaque modèle doit être accompagné d'au moins un cas examples/ et passer la régression
