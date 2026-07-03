# Connecter un nouveau Google Sheet au MCP

Ce guide permet à Claude de guider quelqu'un qui veut connecter son propre Google Sheet
à l'outil d'export de séances (`export_session_to_sheet`).

**Scénario type** : l'utilisateur dit _"voilà mon Sheet : [URL], je veux exporter mes séances dedans"_.

---

## Pré-requis avant de commencer

Vérifier deux choses avant de lancer les étapes :

### A — Le fichier `sheets_credentials.json` existe-t-il ?

```powershell
Test-Path "C:\Users\$env:USERNAME\intervals-mcp-server-git\sheets_credentials.json"
```

- **True** → le Service Account est déjà configuré. Passer directement aux étapes 1 à 4.
- **False** → il faut d'abord créer le Service Account. Voir la section **"Créer le Service Account (première fois)"** dans `COACH_SETUP.md`.

### B — Quel est l'email du Service Account ?

```powershell
(Get-Content "C:\Users\$env:USERNAME\intervals-mcp-server-git\sheets_credentials.json" | ConvertFrom-Json).client_email
```

Conserver cet email — il sera utilisé à l'étape 2.

---

## Étape 1 — Récupérer l'ID du Sheet depuis l'URL

L'URL d'un Google Sheet ressemble à :
```
https://docs.google.com/spreadsheets/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/edit
```

L'**ID du Sheet** est la longue chaîne entre `/d/` et `/edit`.

**Exemple** : pour `https://docs.google.com/spreadsheets/d/17bx2t7ynvSRK4c5XoWaMhea7ovALw1-2qzESbfYTnvs/edit`  
→ l'ID est `17bx2t7ynvSRK4c5XoWaMhea7ovALw1-2qzESbfYTnvs`

---

## Étape 2 — Partager le Sheet avec le Service Account

1. Ouvrir le Google Sheet dans le navigateur
2. Cliquer sur le bouton **Partager** (en haut à droite)
3. Dans le champ "Ajouter des personnes", coller l'email du Service Account (récupéré ci-dessus)
4. Choisir le rôle **Éditeur**
5. Cliquer **Envoyer**

> ⚠️ Sans cette étape, le MCP obtiendra une erreur `403 Forbidden` ou `PERMISSION_DENIED` lors de l'écriture.

✅ **Vérification** : l'email du Service Account apparaît dans la liste des personnes ayant accès.

---

## Étape 3 — Mettre à jour l'ID du Sheet dans le code

Ouvrir le fichier `src/intervals_mcp_server/tools/sheets.py` et modifier la ligne :

```python
SHEET_ID = os.environ.get("SHEETS_ID", "ANCIEN_ID_ICI")
```

Remplacer l'ancien ID par le nouvel ID (récupéré à l'étape 1) :

```python
SHEET_ID = os.environ.get("SHEETS_ID", "NOUVEL_ID_ICI")
```

> 💡 Alternativement, définir la variable d'environnement `SHEETS_ID` dans Claude Desktop  
> (`claude_desktop_config.json` → `"env": { "SHEETS_ID": "NOUVEL_ID" }`) — sans toucher au code.

---

## Étape 4 — Ouvrir une nouvelle conversation

**Important** : il ne suffit pas de fermer/rouvrir l'application. Il faut ouvrir une **nouvelle conversation** (icône ✏️ ou "New chat").

> Pourquoi : la liste des outils MCP est chargée une seule fois au démarrage de chaque conversation. Si les outils ont été ajoutés après l'ouverture de la conversation en cours, ils n'apparaissent pas. Une nouvelle conversation recharge tout depuis zéro.

> Avec Claude Code : cliquer sur ✏️ "New chat" dans la barre latérale.  
> Avec Claude Desktop : même chose — nouvelle conversation, pas juste fermer/rouvrir la fenêtre.

---

## Étape 5 — Vérifier les onglets du Sheet

L'outil `export_session_to_sheet` écrit dans un **onglet spécifique** (paramètre `sheet_tab`).

Deux options :

### Option A — L'onglet existe déjà avec des en-têtes

Vérifier que la ligne 1 contient au moins certaines de ces colonnes (dans n'importe quel ordre) :

| En-tête exact (ligne 1) | Description |
|-------------------------|-------------|
| `Date` | Date de la séance |
| `Intervalles` | Ex. `3 x 20'` |
| `Volume total` | Durée de travail en minutes |
| `Environnement` | `HT` ou `Ext` |
| `Ventilation` | `bouche` ou `nez` |
| `Watts moy` | Puissance moyenne par intervalle |
| `FC moy` | Fréquence cardiaque moyenne par intervalle |
| `Efficacité` | Watts ÷ FC par intervalle |
| `T° moy` | Température moyenne arrondie |

> Les colonnes absentes seront laissées vides. L'ordre n'a pas d'importance.

### Option B — Créer un nouvel onglet automatiquement

Dire à Claude :
> _"Crée un onglet 'LT1' dans le Sheet avec les en-têtes standard"_

Claude utilisera l'outil `create_sheet_tab` pour créer l'onglet avec les bonnes colonnes, déjà en gras.

```
Outil : create_sheet_tab(tab_name="LT1")
```

---

## Étape 6 — Tester l'export

1. Trouver un `activity_id` en demandant à Claude :
   > _"Montre-moi les 5 dernières activités de [nom_athlète]"_
   
   Chaque activité s'affiche avec son ID entre parenthèses.

2. Lancer un export de test :
   > _"Exporte la séance [activity_id] de [nom_athlète] dans l'onglet 'LT1'"_

3. Ouvrir le Sheet dans le navigateur et vérifier que la ligne a bien été ajoutée.

---

## Erreurs courantes

### `PERMISSION_DENIED` ou `403 Forbidden`

Le Service Account n'a pas accès au Sheet. Refaire l'**étape 2** (partage avec l'email du Service Account).

### `Onglet 'LT1' introuvable`

L'onglet n'existe pas ou le nom est mal orthographié. Claude liste les onglets disponibles dans le message d'erreur. Utiliser `create_sheet_tab` pour créer l'onglet manquant.

### `Credentials Service Account introuvables`

Le fichier `sheets_credentials.json` n'existe pas dans le dossier du projet. Refaire la configuration initiale du Service Account (voir `COACH_SETUP.md`).

### La ligne s'ajoute mais les colonnes de données sont vides

Probable cause : aucun intervalle n'est détecté dans l'activité sur Intervals.icu.

**Solution en 3 étapes** :
1. Ouvrir l'activité sur intervals.icu
2. Aller dans l'onglet **Analyse** → icône ✂️ (ciseaux) ou bouton **Auto-analyser**
3. Relancer l'export

### `ValueError: invalid literal for int()` ou erreur de parsing

L'ID du Sheet copié est incorrect (espaces, slash en trop…). Vérifier que l'ID ne contient que des lettres, chiffres, `-` et `_`.

---

## Mémo — ce que Claude doit faire quand on lui dit "voilà mon Sheet, connecte-le"

1. **Demander l'URL du Sheet** si pas fournie
2. **Extraire l'ID** depuis l'URL
3. **Afficher l'email du Service Account** (lire `sheets_credentials.json`)
4. **Guider le partage** (étape 2 ci-dessus)
5. **Modifier `sheets.py`** ligne `SHEET_ID = ...` avec le nouvel ID
6. **Demander de redémarrer Claude**
7. **Créer les onglets** avec `create_sheet_tab` si nécessaire
8. **Tester** avec un export réel

---

## Architecture technique (référence)

```
sheets_credentials.json          ← clé du Service Account (gitignored)
src/intervals_mcp_server/tools/sheets.py
    SHEET_ID = os.environ.get("SHEETS_ID", "<id_par_defaut>")
    CREDENTIALS_FILE = Path(os.environ.get("SHEETS_CREDENTIALS", "...sheets_credentials.json"))
```

**Un seul Sheet actif à la fois.** Pour changer de Sheet → modifier `SHEET_ID` ou la variable `SHEETS_ID`.

**Outils disponibles** :
- `preview_session_intervals(athlete_name, activity_id)` → aperçu des groupes d'intervalles avant export
- `export_session_to_sheet(athlete_name, activity_id, sheet_tab, ventilation, power_min, power_max)` → export
- `create_sheet_tab(tab_name, copy_headers_from)` → créer un onglet avec en-têtes standard
