# ExportToSiftrank

Script Ghidra (Jython) qui décompile toutes les fonctions du programme ouvert et les exporte en JSON, pour les donner à [SiftRank](https://github.com/noperator/siftrank).

## Ce que fait le script

- Parcourt toutes les fonctions du programme courant.
- Ignore les fonctions thunk, externes, celles dont la décompilation échoue, et celles dont le code décompilé dépasse la taille maximale choisie.
- Écrit le résultat dans `~/siftrank_exports/<nom_du_programme>_functions.json`.

Format de sortie :

```json
[
  {
    "name": "FUN_00401000",
    "address": "0x00401000",
    "signature": "int FUN_00401000(int a, char * b)",
    "code": "int FUN_00401000(int a, char *b) { ... }"
  }
]
```

## Installation

1. Dans Ghidra, ouvrir **Window > Script Manager**.
2. Cliquer sur l'icône **Manage Script Directories** (liste à puces en haut à droite).
3. Ajouter le dossier contenant `ExportToSiftrank.py`.
4. Le script apparaît dans la catégorie **Export**.

## Utilisation

1. Ouvrir un programme dans le CodeBrowser (et l'analyser si ce n'est pas déjà fait).
2. Dans le Script Manager, lancer `ExportToSiftrank.py`.
3. Saisir la taille maximale (en caractères de code décompilé) au-delà de laquelle une fonction est ignorée :
   - `8000` est la valeur suggérée ;
   - `0` désactive le filtre ;
   - annuler la boîte de dialogue utilise 8000.
4. Le chemin du fichier JSON et le nombre de fonctions exportées/ignorées s'affichent dans la console.

### Mode headless

La taille maximale peut être passée en argument :

```
analyzeHeadless <projet_dir> <projet> -process <binaire> -noanalysis \
    -scriptPath <dossier_du_script> -postScript ExportToSiftrank.py 4000
```
