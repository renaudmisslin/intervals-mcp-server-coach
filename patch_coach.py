#!/usr/bin/env python3
"""
Patch script pour la configuration multi-athlètes du MCP intervals-mcp-server.
À exécuter UNE SEULE FOIS depuis la racine du projet après avoir cloné le fork.

Usage:
    python patch_coach.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
TOOLS_DIR = ROOT / "src" / "intervals_mcp_server" / "tools"
SERVER_PY = ROOT / "src" / "intervals_mcp_server" / "server.py"
GITIGNORE = ROOT / ".gitignore"

IMPORT_LINE = "from intervals_mcp_server.athletes import get_athlete_credentials\n"

CREDENTIALS_CODE = (
    "    try:\n"
    "        athlete_id, api_key = get_athlete_credentials(athlete_name)\n"
    "    except ValueError as e:\n"
    "        return str(e)\n"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_import(text: str) -> str:
    """Add get_athlete_credentials import after the mcp_instance import line."""
    if "get_athlete_credentials" in text:
        return text
    return text.replace(
        "from intervals_mcp_server.mcp_instance import mcp\n",
        f"from intervals_mcp_server.mcp_instance import mcp\n{IMPORT_LINE}",
    )


def _remove_optional_params(text: str) -> str:
    """Strip athlete_id and api_key optional params from @mcp.tool() function signatures."""
    text = re.sub(r"\n    athlete_id: str \| None = None,?", "", text)
    text = re.sub(r"\n    api_key: str \| None = None,?", "", text)
    return text


def _add_athlete_name_param(text: str) -> str:
    """Insert athlete_name: str as the first parameter of every @mcp.tool() function."""

    def replacer(m: re.Match) -> str:
        header = m.group(1)
        # Already patched?
        if "athlete_name: str," in header or "athlete_name: str\n" in header:
            return m.group(0)
        return header + "\n    athlete_name: str,"

    # Match @mcp.tool() on its own line, then the async def funcname( opening
    pattern = r"(@mcp\.tool\(\)\nasync def \w+\()"
    return re.sub(pattern, replacer, text)


def _replace_credential_resolution(text: str) -> str:
    """Replace the config+resolve_athlete_id block with get_athlete_credentials."""
    # Remove standalone: config = get_config()
    text = re.sub(r"    config = get_config\(\)\n", "", text)

    # Replace the 3-line resolve block with get_athlete_credentials
    pattern = (
        r"    athlete_id_to_use, error_msg = resolve_athlete_id\([^\n]+\)\n"
        r"    if error_msg:\n"
        r"        return error_msg\n"
    )
    text = re.sub(pattern, CREDENTIALS_CODE, text)

    # In case there's no resolve block but there IS a get_config call left
    # (edge case: functions that call config but not resolve_athlete_id)
    # We inject after the docstring in such functions — handled below.

    return text


def _inject_after_docstring(text: str) -> str:
    """
    For any @mcp.tool() function that now has athlete_name but no credentials injection yet,
    insert CREDENTIALS_CODE right after the opening docstring.
    """
    if CREDENTIALS_CODE.strip() not in text:
        # Nothing was injected by replace_credential_resolution; try after-docstring injection
        lines = text.splitlines(keepends=True)
        result: list[str] = []
        state = "normal"  # normal | in_mcp_tool | after_def | in_docstring
        docstring_delim = ""

        for line in lines:
            result.append(line)
            stripped = line.strip()

            if state == "normal":
                if stripped == "@mcp.tool()":
                    state = "in_mcp_tool"

            elif state == "in_mcp_tool":
                if ") -> str:" in line:
                    state = "after_def"

            elif state == "after_def":
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    delim = stripped[:3]
                    # Single-line docstring?
                    rest = stripped[3:]
                    if rest.endswith(delim) and len(rest) > len(delim):
                        # e.g.  """Short doc."""
                        result.append(CREDENTIALS_CODE)
                        state = "normal"
                    else:
                        docstring_delim = delim
                        state = "in_docstring"
                else:
                    # No docstring; inject before first statement
                    result.insert(-1, CREDENTIALS_CODE)
                    state = "normal"

            elif state == "in_docstring":
                if docstring_delim in stripped:
                    result.append(CREDENTIALS_CODE)
                    state = "normal"

        return "".join(result)
    return text


def _fix_api_key_usage(text: str) -> str:
    """Remove fallback to config.api_key — credentials now always come from athletes.json."""
    text = re.sub(r"api_key\s*=\s*api_key\s+or\s+config\.api_key", "api_key=api_key", text)
    text = text.replace("athlete_id_to_use", "athlete_id")
    return text


def _remove_unused_imports(text: str) -> str:
    """Clean up imports that are no longer needed."""
    text = re.sub(r"from intervals_mcp_server\.config import get_config\n", "", text)
    # Remove resolve_athlete_id from validation imports (but keep other imports from that module)
    text = re.sub(
        r"(from intervals_mcp_server\.utils\.validation import )([^\n]+)\n",
        lambda m: (
            ""
            if m.group(2).strip() == "resolve_athlete_id"
            else m.group(0).replace(", resolve_athlete_id", "").replace("resolve_athlete_id, ", "")
        ),
        text,
    )
    return text


def patch_tool_file(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    text = original

    text = _add_import(text)
    text = _remove_optional_params(text)
    text = _add_athlete_name_param(text)
    text = _replace_credential_resolution(text)
    text = _inject_after_docstring(text)
    text = _fix_api_key_usage(text)
    text = _remove_unused_imports(text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"  ✓ Patché  : {path.name}")
    else:
        print(f"  — Inchangé: {path.name} (déjà patché ou aucun changement nécessaire)")


def patch_server(path: Path) -> None:
    """Remove the single-athlete startup validation from server.py."""
    if not path.exists():
        print(f"  ! Introuvable : {path}")
        return
    text = path.read_text(encoding="utf-8")
    original = text

    # Remove the validate_athlete_id call at startup
    text = re.sub(r"    validate_athlete_id\(config\.athlete_id\)\n", "", text)
    text = re.sub(r"    validate_athlete_id\([^)]+\)\n", "", text)

    # Remove now-unused imports
    text = re.sub(r"from intervals_mcp_server\.utils\.validation import validate_athlete_id\n", "", text)
    text = re.sub(r"from intervals_mcp_server\.config import get_config\n", "", text)
    text = re.sub(r"\s*config = get_config\(\)\n", "\n", text)

    # Add athlete_management tools import
    if "athlete_management" not in text:
        text = text.replace(
            "if __name__",
            "from intervals_mcp_server.tools.athlete_management import (\n"
            "    get_training_load,\n"
            "    list_athletes,\n"
            "    post_activity_comment,\n"
            ")\n\n"
            "if __name__",
        )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"  ✓ Patché  : server.py")
    else:
        print(f"  — Inchangé: server.py")


def update_gitignore() -> None:
    entries = ["athletes.json", ".env"]
    if not GITIGNORE.exists():
        GITIGNORE.write_text("\n".join(entries) + "\n", encoding="utf-8")
        print("  ✓ .gitignore créé")
        return
    text = GITIGNORE.read_text(encoding="utf-8")
    added = []
    for entry in entries:
        if entry not in text:
            text += f"\n{entry}"
            added.append(entry)
    if added:
        GITIGNORE.write_text(text.rstrip() + "\n", encoding="utf-8")
        print(f"  ✓ .gitignore mis à jour : {', '.join(added)} ajoutés")
    else:
        print("  — .gitignore déjà à jour")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║  Patch multi-athlètes — intervals-mcp-server             ║")
    print("╚══════════════════════════════════════════════════════════╝\n")

    if not TOOLS_DIR.exists():
        print(
            "ERREUR : le dossier src/intervals_mcp_server/tools/ est introuvable.\n"
            "Assurez-vous d'exécuter ce script depuis la RACINE du projet cloné.\n"
            f"Répertoire courant : {Path.cwd()}"
        )
        sys.exit(1)

    print("[ Patch des outils existants ]")
    skip = {"__init__.py", "athlete_management.py"}
    for f in sorted(TOOLS_DIR.glob("*.py")):
        if f.name not in skip:
            patch_tool_file(f)

    print("\n[ Patch du serveur ]")
    patch_server(SERVER_PY)

    print("\n[ Mise à jour de .gitignore ]")
    update_gitignore()

    print("\n✅ Patch terminé avec succès !")
    print("\nProchaines étapes :")
    print("  1. Créez athletes.json à la racine (voir athletes.json.example)")
    print("  2. Configurez Claude Desktop (voir COACH_SETUP.md)")
    print("  3. Redémarrez Claude Desktop\n")


if __name__ == "__main__":
    main()
