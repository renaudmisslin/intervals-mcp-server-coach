# Guide d'installation — MCP Coach multi-athlètes (Intervals.icu)

## Ce que ce projet fait concrètement

Ce MCP permet à Claude de lire et gérer les données Intervals.icu de **plusieurs athlètes** simultanément, avec **une seule clé API** (la vôtre, en tant que coach).

Exemples de requêtes :
- *"Montre-moi la forme de luc cette semaine"*
- *"Compare les activités vélo de renaud et thomas en mai"*
- *"Planifie un entraînement pour thomas vendredi"*
- *"Quelle est la charge d'entraînement de renaud ?"*

---

## Prérequis

### 1. Claude Desktop
Téléchargez depuis : **https://claude.ai/download**

### 2. Python 3.12+
- **Windows** : https://www.python.org/downloads/ — cochez **"Add Python to PATH"**
- Vérification : `python --version`

### 3. uv
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
Fermer et rouvrir PowerShell, puis : `uv --version`

### 4. Git
https://git-scm.com/download/win — vérification : `git --version`

---

## Installation pas à pas

### Étape 1 — Cloner le dépôt

```powershell
cd C:\Users\$env:USERNAME
git clone https://github.com/renaudmisslin/intervals-mcp-server-coach.git intervals-mcp-server-coach
cd intervals-mcp-server-coach
```

### Étape 2 — Installer les dépendances

```powershell
uv sync
```

### Étape 3 — Configurer votre clé API coach

Créez le fichier `.env` à la racine du projet :

```powershell
Copy-Item .env.example .env
notepad .env
```

Remplissez avec **votre propre** Athlete ID et clé API (trouvés sur intervals.icu → Settings → API) :

```
INTERVALS_ICU_API_KEY=votre_cle_api_coach
INTERVALS_ICU_ATHLETE_ID=iVOTRE_ID
```

> ⚠️ **Important** : c'est **votre** clé API à vous (le coach), pas celle de vos athlètes. Vous n'avez pas besoin des clés API de vos athlètes.

### Étape 4 — Activer le coach access dans Intervals.icu

Pour chaque athlète que vous coachez :
1. L'athlète se connecte sur **https://intervals.icu**
2. Paramètres → **Athletes** → **Add Coach**
3. L'athlète entre votre adresse email Intervals.icu
4. Vous acceptez l'invitation depuis votre profil → Settings → Athletes

> ✅ Une fois accepté, votre clé API peut accéder aux données de l'athlète.

### Étape 5 — Configurer athletes.json

```powershell
Copy-Item athletes.json.example athletes.json
notepad athletes.json
```

Remplissez avec les noms et IDs de vos athlètes :

```json
{
  "athletes": {
    "thomas": "i67890",
    "sophie": "i11111"
  }
}
```

> Le nom (`"thomas"`) est celui que vous utiliserez dans vos conversations avec Claude.  
> L'ID (`"i67890"`) se trouve dans le profil de l'athlète sur intervals.icu (URL ou Settings → API).  
> 🔒 `athletes.json` est dans `.gitignore` — il ne sera jamais publié sur GitHub.

### Étape 6 — Configurer Claude Desktop

Ouvrez le fichier de config Claude Desktop :

```powershell
notepad "$env:APPDATA\Claude\claude_desktop_config.json"
```

Ajoutez (en remplaçant `VOTRE_NOM` par votre nom d'utilisateur Windows) :

```json
{
  "mcpServers": {
    "intervals-coach": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\VOTRE_NOM\\intervals-mcp-server-coach",
        "run",
        "intervals-icu-mcp"
      ]
    }
  }
}
```

> Si `"command": "uv"` échoue, utilisez le chemin complet :
> ```powershell
> (Get-Command uv).Source   # affiche le chemin, ex: C:\Users\rmisslin\.local\bin\uv.exe
> ```

### Étape 7 — Redémarrer Claude Desktop

Fermez complètement Claude Desktop puis relancez-le.

### Étape 8 — Vérifier

Dans une nouvelle conversation Claude :

> **"Quels athlètes sont disponibles ?"**

Claude doit appeler `icu_list_athletes` et vous retourner la liste de `athletes.json`.

Puis testez une requête réelle :

> **"Montre-moi les 5 dernières activités de thomas"**

---

## Utilisation quotidienne

### Pattern naturel — nommez l'athlète

Claude comprend les requêtes en langue naturelle. Il utilisera `icu_resolve_athlete_id` automatiquement pour résoudre le nom vers l'ID.

```
"Quelle est la forme de luc en ce moment ?"
"Montre-moi la charge d'entraînement de thomas ce mois-ci"
"Planifie un entraînement vélo pour renaud mardi"
"Compare les courbes de puissance de luc et thomas"
```

### Ajouter un nouvel athlète

1. L'athlète vous ajoute comme coach dans Intervals.icu (voir Étape 4)
2. Ouvrez `athletes.json` et ajoutez une ligne :
   ```json
   "marie": "i99999"
   ```
3. **Pas besoin de redémarrer Claude** — la liste est rechargée à chaque appel.

---

## En cas de problème

### `spawn uv ENOENT` — uv introuvable

Utilisez le chemin complet dans `claude_desktop_config.json` :
```powershell
(Get-Command uv).Source
```

### Erreur 401 / "Unauthorized"

- Vérifiez que `.env` contient bien votre clé API coach
- Vérifiez que l'athlète vous a bien ajouté comme coach sur intervals.icu

### Athlète non trouvé / `icu_list_athletes` vide

- Vérifiez que `athletes.json` existe à la racine du projet
- Vérifiez la syntaxe JSON (pas de virgule en trop, guillemets droits)

### Claude Code (CLI) au lieu de Claude Desktop

Avec Claude Code, utilisez :
```powershell
claude mcp add intervals-coach --scope user "C:\Users\$env:USERNAME\intervals-mcp-server-coach\run_server.cmd"
```

Créez d'abord `run_server.cmd` :
```batch
@echo off
cd /d "C:\Users\VOTRE_NOM\intervals-mcp-server-coach"
"C:\Users\VOTRE_NOM\.local\bin\uv.exe" run intervals-icu-mcp
```

---

## Structure des fichiers

```
intervals-mcp-server-coach/
├── .env                        ← VOS credentials coach (ne jamais publier)
├── athletes.json               ← Noms et IDs de vos athlètes (ne jamais publier)
├── athletes.json.example       ← Modèle vide
├── COACH_SETUP.md              ← Ce guide
└── src/
    └── intervals_icu_mcp/
        ├── athletes.py                 ← Résolution nom→ID
        ├── tools/
        │   ├── coach.py               ← icu_list_athletes, icu_resolve_athlete_id
        │   ├── activities.py          ← 10+ outils activités (athlete_id supporté)
        │   ├── events.py              ← Calendrier (athlete_id supporté)
        │   ├── event_management.py    ← Création/modification d'événements
        │   ├── wellness.py            ← Bien-être (athlete_id supporté)
        │   ├── athlete.py             ← Profil et forme (athlete_id supporté)
        │   ├── performance.py         ← Courbes de puissance (athlete_id supporté)
        │   ├── curves.py              ← Courbes FC/allure (athlete_id supporté)
        │   └── ...
        └── server.py
```
