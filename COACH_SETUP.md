# Guide d'installation — MCP Coach multi-athlètes

## Ce que ce projet fait concrètement

Ce MCP (connecteur) permet à Claude d'accéder directement aux données Intervals.icu de **plusieurs athlètes** à la fois. Vous pouvez demander à Claude : *"Montre-moi la charge d'entraînement de Thomas cette semaine"*, *"Compare les activités de Renaud et Sophie en mai"*, ou *"Poste un commentaire sur la dernière sortie vélo de Thomas"* — sans jamais quitter la conversation.

---

## Prérequis à installer

### 1. Claude Desktop
Téléchargez et installez depuis : **https://claude.ai/download**

### 2. Python 3.12 ou plus récent
- **Windows** : https://www.python.org/downloads/
  - Lors de l'installation, cochez **"Add Python to PATH"** ✅
  - Vérification : ouvrez PowerShell et tapez `python --version` → doit afficher `Python 3.12.x` ou plus

### 3. uv (gestionnaire de paquets Python rapide)
Ouvrez PowerShell et collez cette commande :
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Fermer et rouvrir PowerShell, puis vérifier :
```powershell
uv --version
```
→ doit afficher quelque chose comme `uv 0.5.x`

### 4. Git
- **Windows** : https://git-scm.com/download/win
  - Vérification : `git --version`

---

## Installation pas à pas

### Étape 1 — Forker et cloner le dépôt

Sur GitHub, allez sur votre fork du projet (celui que vous avez créé depuis `https://github.com/mvilanova/intervals-mcp-server`).

Copiez l'URL de votre fork (bouton vert **Code** → icône copier), puis dans PowerShell :

```powershell
# Cloner votre fork dans un dossier temporaire
cd C:\Users\$env:USERNAME
git clone https://github.com/VOTRE_NOM_GITHUB/intervals-mcp-server.git intervals-mcp-server-git
```

**Résultat attendu** : un dossier `C:\Users\VOTRE_NOM\intervals-mcp-server-git\` est créé avec tous les fichiers du projet.

---

### Étape 2 — Copier les fichiers coach dans le projet cloné

Claude a déjà préparé les fichiers coach dans `C:\Users\rmisslin\intervals-mcp-server\`.
Copiez-les dans le dossier cloné :

```powershell
$src = "C:\Users\rmisslin\intervals-mcp-server"
$dst = "C:\Users\rmisslin\intervals-mcp-server-git"

Copy-Item "$src\patch_coach.py"          "$dst\" -Force
Copy-Item "$src\athletes.json.example"   "$dst\" -Force
Copy-Item "$src\COACH_SETUP.md"          "$dst\" -Force
Copy-Item "$src\src\intervals_mcp_server\athletes.py" "$dst\src\intervals_mcp_server\" -Force
Copy-Item "$src\src\intervals_mcp_server\tools\athlete_management.py" "$dst\src\intervals_mcp_server\tools\" -Force
```

Ensuite, travaillez depuis le dossier cloné :

```powershell
cd C:\Users\$env:USERNAME\intervals-mcp-server-git
```

---

### Étape 3 — Appliquer le patch multi-athlètes

Depuis le dossier du projet :

```powershell
python patch_coach.py
```

**Résultat attendu** :
```
╔══════════════════════════════════════════════════════════╗
║  Patch multi-athlètes — intervals-mcp-server             ║
╚══════════════════════════════════════════════════════════╝

[ Patch des outils existants ]
  ✓ Patché  : activities.py
  ✓ Patché  : custom_items.py
  ✓ Patché  : events.py
  ...

✅ Patch terminé avec succès !
```

---

### Étape 4 — Installer les dépendances Python

```powershell
uv sync
```

**Résultat attendu** : téléchargement et installation des paquets. Dernière ligne : `All packages installed.` ou similaire.

---

### Étape 5 — Trouver votre Athlete ID et votre clé API

#### Sur Intervals.icu (navigateur web)

1. Connectez-vous sur **https://intervals.icu**
2. Cliquez sur votre **avatar / photo de profil** en haut à droite
3. Allez dans **"Settings"** (Paramètres)
4. Dans le menu de gauche, cliquez sur **"API"** (ou cherchez "Developer")
5. Vous y trouverez :
   - **Athlete ID** : une chaîne du type `i123456` (commence par `i`)
   - **API Key** : une longue chaîne de caractères — cliquez sur **"Show"** pour la voir

> 💡 Répétez cette opération pour chaque athlète que vous coachez.  
> Chaque athlète doit aller dans ses propres paramètres et vous communiquer son ID et sa clé API.

---

### Étape 6 — Créer le fichier athletes.json

Dans le dossier du projet (là où il y a `athletes.json.example`), créez un fichier `athletes.json` :

```powershell
Copy-Item athletes.json.example athletes.json
```

Puis ouvrez `athletes.json` avec le Bloc-notes (ou VS Code) et remplissez avec les vraies valeurs :

```json
{
  "athletes": {
    "renaud": {
      "id": "i123456",
      "api_key": "COLLER_LA_VRAIE_CLE_ICI"
    },
    "thomas": {
      "id": "i789012",
      "api_key": "CLE_API_DE_THOMAS"
    }
  }
}
```

> ⚠️ **Important** : le nom que vous mettez (`"renaud"`, `"thomas"`) est celui que vous utiliserez dans vos conversations avec Claude. Choisissez un nom court et sans accent.

> 🔒 **Sécurité** : `athletes.json` est déjà dans `.gitignore` — il ne sera jamais publié sur GitHub. Ne le partagez jamais.

---

### Étape 7 — Configurer Claude Desktop

Le fichier de configuration de Claude Desktop se trouve à cet emplacement selon votre système :

| Système | Chemin du fichier |
|---------|-------------------|
| **Windows** | `C:\Users\VOTRE_NOM\AppData\Roaming\Claude\claude_desktop_config.json` |
| **Mac** | `~/Library/Application Support/Claude/claude_desktop_config.json` |

#### Sur Windows

Ouvrez ce fichier (le créer s'il n'existe pas) avec le Bloc-notes :

```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

Collez le contenu suivant en remplaçant `VOTRE_NOM` par votre nom d'utilisateur Windows (le nom qui apparaît dans `C:\Users\...`) :

```json
{
  "mcpServers": {
    "intervals-coach": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\VOTRE_NOM\\intervals-mcp-server-git",
        "run",
        "intervals-mcp-server"
      ]
    }
  }
}
```

> 💡 Attention aux doubles antislashs `\\` dans le chemin Windows — c'est obligatoire dans ce format JSON.  
> Vérifiez que le chemin correspond bien à l'endroit où vous avez cloné le fork (dossier contenant `pyproject.toml`).

#### Sur Mac

```json
{
  "mcpServers": {
    "intervals-coach": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/VOTRE_NOM/intervals-mcp-server-git",
        "run",
        "intervals-mcp-server"
      ]
    }
  }
}
```

**Si vous avez déjà d'autres MCP configurés**, ajoutez seulement le bloc `"intervals-coach": { ... }` à l'intérieur de `"mcpServers"` existant, sans écraser le reste.

---

### Étape 8 — Redémarrer Claude Desktop

Fermez complètement Claude Desktop (vérifiez dans la barre des tâches / barre de menu), puis relancez-le.

---

### Étape 9 — Vérifier que tout fonctionne

Dans Claude Desktop, ouvrez une nouvelle conversation et posez cette question :

> **"Quels athlètes sont disponibles ?"**

Claude devrait répondre avec la liste des athlètes que vous avez configurés dans `athletes.json`.

Ensuite, testez une requête réelle :

> **"Montre-moi les 5 dernières activités de [nom_athlète]"**

---

## Ajouter un nouvel athlète

1. Demandez à l'athlète de vous communiquer son **Athlete ID** et sa **clé API** depuis ses paramètres Intervals.icu
2. Ouvrez `athletes.json` et ajoutez une entrée :
   ```json
   "sophie": {
     "id": "i345678",
     "api_key": "SA_CLE_API"
   }
   ```
3. **Pas besoin de redémarrer Claude** — la liste est rechargée automatiquement

---

## En cas de problème

### `spawn uv ENOENT` — Claude ne trouve pas uv

**Cause** : Claude Desktop ne voit pas `uv` car son chemin n'est pas dans le PATH système.

**Solution** : trouvez le chemin complet de `uv` et utilisez-le dans la config :
```powershell
(Get-Command uv).Source
# Exemple de résultat : C:\Users\rmisslin\.local\bin\uv.exe
```

Puis dans `claude_desktop_config.json`, remplacez `"command": "uv"` par le chemin complet :
```json
"command": "C:\\Users\\rmisslin\\.local\\bin\\uv.exe"
```

---

### `Athlète 'xyz' inconnu` — erreur de nom

**Cause** : le nom utilisé dans la conversation ne correspond pas exactement à celui dans `athletes.json`.

**Solution** : demandez à Claude `"Quels athlètes sont disponibles ?"` pour voir la liste exacte, puis utilisez le nom exact (sensible à la casse).

---

### Les données Strava ne sont pas disponibles / activités manquantes

**Cause** : Intervals.icu importe les activités depuis Strava avec un délai, ou la synchronisation est désactivée.

**Solution** :
1. Connectez-vous sur https://intervals.icu
2. Allez dans **Settings → Connections**
3. Vérifiez que Strava est bien connecté
4. Cliquez sur **"Sync now"** pour forcer la synchronisation

---

### Limite de contexte / réponse tronquée

**Cause** : trop de données retournées en une seule requête (ex. 500 activités d'un coup).

**Solution** : réduisez la période ou le nombre de résultats :
> *"Montre-moi les 10 dernières activités de renaud"* (au lieu de "toutes")
> *"Donne-moi la charge d'entraînement de thomas pour les 2 dernières semaines"*

---

### Le MCP n'apparaît pas dans Claude Desktop

**Vérifications** :
1. Avez-vous bien **fermé et relancé** Claude Desktop après avoir modifié `claude_desktop_config.json` ?
2. Le chemin dans la config pointe-t-il vers le bon dossier ? Vérifiez que ce dossier contient bien `pyproject.toml`
3. Sur Windows, les chemins utilisent-ils des `\\` doubles ?
4. Le JSON est-il valide ? Collez le contenu sur https://jsonlint.com pour vérifier

---

### Vous utilisez Claude Code (CLI ou app Desktop Claude Code) — pas Claude Desktop

> ⚠️ **Différence importante** : Claude Code et Claude Desktop sont deux applications distinctes d'Anthropic.
> - **Claude Desktop** (`claude.ai/download`) → utilise `claude_desktop_config.json`
> - **Claude Code** (CLI `claude` ou app Windows Store) → utilise `claude mcp add`

Avec **Claude Code**, modifier `claude_desktop_config.json` ou `~/.claude/settings.json` ne sert à rien pour les serveurs MCP stdio locaux. L'app envoie la config au SDK cloud distant qui ne peut pas démarrer un processus local sur votre machine.

**Symptômes** :
- Les logs montrent `serverCount=1` mais `toolCount` ne change pas
- `claude mcp list` ne montre pas votre serveur
- "Quels athlètes sont disponibles ?" ne déclenche aucun outil

**Solution — 3 étapes** :

#### Étape 1 — Créer un script wrapper

Créez le fichier `C:\Users\VOTRE_NOM\intervals-mcp-server-git\run_server.cmd` avec ce contenu :

```batch
@echo off
cd /d "C:\Users\VOTRE_NOM\intervals-mcp-server-git"
"C:\Users\VOTRE_NOM\.local\bin\uv.exe" run intervals-mcp-server
```

> Remplacez `VOTRE_NOM` par votre nom d'utilisateur Windows.  
> Vérifiez le chemin de `uv.exe` avec : `(Get-Command uv).Source`

#### Étape 2 — Enregistrer le serveur avec `claude mcp add`

```powershell
claude mcp add intervals-coach --scope user "C:\Users\VOTRE_NOM\intervals-mcp-server-git\run_server.cmd"
```

#### Étape 3 — Vérifier la connexion

```powershell
claude mcp list
```

Vous devez voir :
```
intervals-coach: C:\Users\...\run_server.cmd  - √ Connected
```

#### Étape 4 — Redémarrer Claude Code et tester

```powershell
Stop-Process -Name "Claude" -Force; Start-Process "shell:AppsFolder\Claude_pzs8sxrjxfjjc!Claude"
```

Puis dans une nouvelle conversation : **"Quels athlètes sont disponibles ?"**

---

## Structure des fichiers importants

```
intervals-mcp-server/
├── athletes.json          ← VOS DONNÉES (ne jamais publier sur GitHub)
├── athletes.json.example  ← Modèle vide pour documentation
├── patch_coach.py         ← Script de patch (à exécuter une seule fois)
├── COACH_SETUP.md         ← Ce guide
├── pyproject.toml         ← Configuration du projet Python
└── src/
    └── intervals_mcp_server/
        ├── athletes.py                    ← Chargement des credentials
        └── tools/
            ├── athlete_management.py      ← Outils coach : list_athletes, post_activity_comment, get_training_load
            ├── activities.py              ← Activités (patché)
            ├── events.py                  ← Événements (patché)
            ├── wellness.py                ← Bien-être (patché)
            └── ...
```
