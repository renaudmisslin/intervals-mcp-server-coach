# Intervals.icu MCP Server

Model Context Protocol (MCP) server for connecting Claude and ChatGPT with the Intervals.icu API. It provides tools for authentication and data retrieval for activities, events, wellness data, power curves, and custom items.

If you find the Model Context Protocol (MCP) server useful, please consider supporting its continued development with a donation.

## Requirements

- Python 3.12 or higher
- [Model Context Protocol (MCP) Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- httpx
- python-dotenv

## Setup

### 1. Install uv (recommended)

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installation, find the full path to `uv` — you'll need it later when configuring Claude Desktop:

```powershell
where.exe uv
# Example output: C:\Users\<USERNAME>\.local\bin\uv.exe
```

### 2. Clone this repository

```bash
git clone https://github.com/mvilanova/intervals-mcp-server.git
cd intervals-mcp-server
```

### 3. Create and activate a virtual environment

```bash
# Create virtual environment with Python 3.12
uv venv --python 3.12

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

### 4. Sync project dependencies

```bash
uv sync
```

### 5. Set up environment variables

Make a copy of `.env.example` and name it `.env` by running the following command:

**macOS/Linux:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Then edit the `.env` file and set your Intervals.icu athlete id and API key:

```
API_KEY=your_intervals_api_key_here
ATHLETE_ID=your_athlete_id_here
```

#### Getting your Intervals.icu API Key

1. Log in to your Intervals.icu account
2. Go to Settings > API
3. Generate a new API key

#### Finding your Athlete ID

Your athlete ID is typically visible in the URL when you're logged into Intervals.icu. It looks like:

- `https://intervals.icu/athlete/i12345/...` where `i12345` is your athlete ID

## Updating

This project is actively developed, with new features and fixes added regularly. To stay up to date, follow these steps:

### 1. Pull the latest changes from `main`

> ⚠️ Make sure you don't have uncommitted changes before running this command.

**macOS/Linux:**
```bash
git checkout main && git pull
```

**Windows (PowerShell):**
```powershell
git checkout main; git pull
```

### 2. Update Python dependencies

Activate your virtual environment and sync dependencies:

**macOS/Linux:**
```bash
source .venv/bin/activate
uv sync
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\activate
uv sync
```

### Troubleshooting

If Claude Desktop fails due to configuration changes, follow these steps:

1. Delete the existing `Intervals.icu` entry in `claude_desktop_config.json`.
2. Reconfigure Claude Desktop from the `intervals-mcp-server` directory.

**macOS/Linux:**
```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

**Windows:** Re-add the entry manually as described in the [Windows configuration section](#windows).

#### Common errors

**`spawn uv ENOENT`** — Claude Desktop cannot find the `uv` executable. Use the full path to `uv` in the `command` field. Run `which uv` (macOS/Linux) or `where.exe uv` (Windows) to get it.

**`spawn /Users/... ENOENT` on Windows** — The config file contains a macOS/Linux-style path. Replace it with the correct Windows path using backslashes as described in the [Windows configuration section](#windows) below.

**Windows Store install: config changes not taking effect** — You may be editing the wrong config file. Claude Desktop installed from the Microsoft Store reads from `AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json`, not `AppData\Roaming\Claude\`.

#### Using Claude Code instead of Claude Desktop

> **Claude Code** (the CLI tool `claude` or the Claude Code Desktop Windows Store app) is a **different application** from Claude Desktop and requires a different setup.

With Claude Code, editing `claude_desktop_config.json` or adding `mcpServers` to `~/.claude/settings.json` has **no effect** for local stdio MCP servers — the app forwards the config to a remote SDK that cannot spawn a local process.

**Symptoms:** `claude mcp list` doesn't show your server; tools never appear in the session; logs show `serverCount=1` but tool count never increases.

**Fix — Windows:**

1. Create a wrapper script `run_server.cmd` in the project directory:
   ```batch
   @echo off
   cd /d "C:\Users\<USERNAME>\intervals-mcp-server-git"
   "C:\Users\<USERNAME>\.local\bin\uv.exe" run intervals-mcp-server
   ```
   (Find your uv path with: `(Get-Command uv).Source`)

2. Register the server:
   ```powershell
   claude mcp add intervals-coach --scope user "C:\Users\<USERNAME>\intervals-mcp-server-git\run_server.cmd"
   ```

3. Verify:
   ```powershell
   claude mcp list
   # Should show: intervals-coach: ... - √ Connected
   ```

4. Restart Claude Code and open a new session.

**Fix — macOS/Linux:**

```bash
claude mcp add intervals-coach --scope user -- uv --directory /path/to/intervals-mcp-server-git run intervals-mcp-server
```

## Usage with Claude

### 1. Configure Claude Desktop

To use this server with Claude Desktop, you need to add it to your Claude Desktop configuration.

#### macOS/Linux

1. Run the following from the `intervals-mcp-server` directory to configure Claude Desktop:

```bash
mcp install src/intervals_mcp_server/server.py --name "Intervals.icu" --with-editable . --env-file .env
```

2. If you open your Claude Desktop App configuration file `claude_desktop_config.json`, it should look like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/Users/<USERNAME>/.local/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with-editable",
        "/path/to/intervals-mcp-server",
        "mcp",
        "run",
        "/path/to/intervals-mcp-server/src/intervals_mcp_server/server.py"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Where `/path/to/` is the path to the `intervals-mcp-server` code folder in your system.

#### Windows

The `mcp install` command may fail on Windows due to environment or permission issues. Instead, configure Claude Desktop manually:

1. Find the Claude Desktop config file. If Claude Desktop was installed from the **Microsoft Store**, the config is located at:

   ```
   C:\Users\<USERNAME>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json
   ```

   If installed via the standard installer, it may be at:

   ```
   C:\Users\<USERNAME>\AppData\Roaming\Claude\claude_desktop_config.json
   ```

   If the file or folder does not exist, create it.

2. Add the following entry to `claude_desktop_config.json`, replacing the placeholders with your actual values:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "C:\\Users\\<USERNAME>\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with-editable",
        "C:\\path\\to\\intervals-mcp-server",
        "mcp",
        "run",
        "C:\\path\\to\\intervals-mcp-server\\src\\intervals_mcp_server\\server.py"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

- Use double backslashes (`\\`) for all Windows paths in JSON.
- To find the full path to `uv.exe`, run `where.exe uv` in PowerShell.
- To find the full path to the cloned repository, run `pwd` from inside the `intervals-mcp-server` folder.

> **Note for Windows Store installs:** Claude Desktop installed from the Microsoft Store sandboxes its config under `AppData\Local\Packages\...`. Editing `AppData\Roaming\Claude\claude_desktop_config.json` will have no effect — make sure you edit the correct file.

3. Restart Claude Desktop.

### 2. Use the MCP server with Claude

Once the server is running and Claude Desktop is configured, you can use the following tools to ask questions about your past and future activities, events, and wellness data.

- `get_activities`: Retrieve a list of activities
- `get_activity_details`: Get detailed information for a specific activity
- `get_activity_intervals`: Get detailed interval data for a specific activity
- `get_activity_streams`: Get raw data streams (power, heart rate, etc.) for a specific activity
- `get_athlete_power_curves`: Get best power output curves for selected durations and time periods
- `get_wellness_data`: Fetch wellness data
- `get_events`: Retrieve upcoming events (workouts, races, etc.)
- `get_event_by_id`: Get detailed information for a specific event
- `add_or_update_event`: Create or update an event (workout, race, note, etc.)
- `delete_event`: Delete a specific event
- `delete_events_by_date_range`: Delete events within a date range
- `get_custom_items`: Get custom items (charts, custom fields, zones, etc.) for an athlete
- `get_custom_item_by_id`: Get detailed information for a specific custom item
- `create_custom_item`: Create a new custom item for an athlete
- `update_custom_item`: Update an existing custom item
- `delete_custom_item`: Delete a custom item

## Export to Google Sheets

The `export_session_to_sheet` tool appends one row per training session into a Google Sheet. It reads column headers dynamically from the sheet, fetches activity + interval data from Intervals.icu, and fills in the mapped values automatically.

**Columns supported** (any subset, in any order — the tool reads headers from row 1):

| Column header (row 1) | Source |
|-----------------------|--------|
| `Date` | Session date from Intervals.icu |
| `Intervalles` | Detected interval structure, e.g. `3 x 20'` |
| `Volume total` | Distance (km) or duration (min) for indoor sessions |
| `Environnement` | `HT` (indoor / trainer) or `Ext` (outdoor) |
| `Ventilation` | Parameter passed at call time (default: `bouche`) |
| `Watts moy` | Avg power per work interval, e.g. `270-271-269` |
| `FC moy` | Avg heart rate per work interval, e.g. `145-146-142` |
| `Efficacité` | Efficiency Factor (watts ÷ HR) per interval, e.g. `1.86-1.87` |
| `T° moy` | Average temperature |

> Any column header not in this list is left blank. You can reorder or remove columns freely — the tool reads the actual headers at runtime.

### One-time setup: Google Service Account

This is a one-time setup. **Claude can guide you through each step** — just ask: *"Guide me through the Google Sheets setup for the MCP server"*.

#### Step 1 — Google Cloud Console

Go to https://console.cloud.google.com and select or create a project (any name).

**Verify:** You can see the project name in the top bar.

#### Step 2 — Enable Google Sheets API

In the left menu: **APIs & Services → Library → search "Google Sheets API" → Enable**.

**Verify:** The API status shows "Enabled" on its page.

#### Step 3 — Create a Service Account

**APIs & Services → Credentials → Create Credentials → Service Account**

- Name: `intervals-mcp-sheets` (or any name)
- Skip the role and user access steps (click Continue / Done)

**Verify:** The service account appears in the Credentials list with an email like `intervals-mcp-sheets@your-project.iam.gserviceaccount.com`.

#### Step 4 — Download the credentials JSON

Click the service account → **Keys tab → Add Key → Create new key → JSON → Create**.

A JSON file downloads automatically. Rename it `sheets_credentials.json` and place it at the root of this project:

```
intervals-mcp-server-git/
└── sheets_credentials.json   ← here
```

> This file is already in `.gitignore` — it will never be committed.

**Verify (PowerShell):**
```powershell
Test-Path "C:\Users\<USERNAME>\intervals-mcp-server-git\sheets_credentials.json"
# Should print: True
```

#### Step 5 — Share your Google Sheet with the service account

1. Open `sheets_credentials.json` and copy the `client_email` value (looks like `intervals-mcp-sheets@...iam.gserviceaccount.com`)
2. Open your Google Sheet → **Share** → paste the email → role **Editor** → Send

**Verify:** The service account email appears in the sheet's sharing list.

#### Step 6 — Install dependencies and restart

```powershell
cd C:\Users\<USERNAME>\intervals-mcp-server-git
uv sync
```

Then restart Claude Code so the new tool is loaded.

**Verify:** Ask Claude *"Which tools do you have for Google Sheets?"* — it should mention `export_session_to_sheet`.

### Usage

Once setup is done, tell Claude:

> *"Export session [activity_id] for renaud to the sheet"*

Or with a ventilation override:

> *"Export session [activity_id] for renaud, ventilation=nez"*

Claude calls `export_session_to_sheet(athlete_name="renaud", activity_id="...", ventilation="bouche")` and confirms the row that was added.

To find the activity ID, ask:

> *"Show me the last 5 activities for renaud"* — each line ends with `(id:abc123)`

### Troubleshooting: empty columns (Intervalles, Watts moy, FC moy…)

**Symptom:** the row is added but interval-related columns are blank, and Claude warns that no work intervals were detected.

**Most likely cause: the activity has no intervals defined on Intervals.icu.**

Intervals.icu only exposes interval data if they have been created for that activity — either automatically detected by the platform or added manually.

**Fix:**

1. Open the activity on intervals.icu
2. Check whether intervals are visible in the activity view (coloured blocks on the effort graph)
3. If not:
   - Use the scissors icon to **create intervals manually** by selecting the effort blocks
   - Or click **"Analyse"** if Intervals.icu offers automatic detection for that activity
4. Once intervals are visible, re-run the export

**Secondary check:** the activity title must contain a `NxM` pattern (e.g. `3x20min`, `6 x 20'`) so the tool knows how many intervals to look for and what duration to expect. Suffixes like `PL`, `ext`, `HT` are ignored.

---

## Adding a new Sheets export tool

This section explains how to add a new tool that writes different data to a Google Sheet (e.g. wellness data, training load, custom fields).

### How it works

All Sheets export logic lives in [`src/intervals_mcp_server/tools/sheets.py`](src/intervals_mcp_server/tools/sheets.py). The pattern is:

1. **Fetch data** from Intervals.icu via `make_intervals_request`
2. **Read headers** from the target Sheet with `_get_worksheet(tab_name).row_values(1)`
3. **Map fields** into a dict keyed by lowercase column header
4. **Append the row** with `ws.append_row(row, value_input_option="USER_ENTERED")`

### Step-by-step

**1. Define your column mapping**

In `sheets.py`, add a `_build_row_xxx()` function that takes your data and returns a `list[str]` aligned with the Sheet headers. Use the existing `_build_row()` as a template:

```python
def _build_row_wellness(headers: list[str], data: dict) -> list[str]:
    mapping = {
        "date": data.get("date", ""),
        "poids": str(data.get("weight", "")),
        "fc repos": str(data.get("restingHR", "")),
        # add more fields here
    }
    return [mapping.get(h.lower().strip(), "") for h in headers]
```

**2. Create the MCP tool**

Add a new `@mcp.tool()` async function in `sheets.py`:

```python
@mcp.tool()
async def export_wellness_to_sheet(
    athlete_name: str,
    date: str,
    sheet_tab: str = "Wellness",
) -> str:
    """Export daily wellness data for an athlete to a Google Sheet tab."""
    try:
        athlete_id, api_key = get_athlete_credentials(athlete_name)
    except ValueError as e:
        return str(e)

    result = await make_intervals_request(
        url=f"/athlete/{athlete_id}/wellness/{date}", api_key=api_key
    )
    if isinstance(result, dict) and "error" in result:
        return f"Error: {result.get('message')}"

    try:
        ws = _get_worksheet(sheet_tab)
        headers = ws.row_values(1)
    except Exception as exc:
        return f"Google Sheets error: {exc}"

    row = _build_row_wellness(headers, result)
    ws.append_row(row, value_input_option="USER_ENTERED")
    return f"✅ Wellness for {date} added to '{sheet_tab}'"
```

**3. Register in server.py**

Add the new function to the import:

```python
from intervals_mcp_server.tools.sheets import (
    export_session_to_sheet,
    export_wellness_to_sheet,   # ← add this
)
```

**4. Sync and restart**

```powershell
uv sync
# Restart Claude Code
```

Ask Claude *"Which Sheets export tools are available?"* to confirm.

---

## Usage with ChatGPT

ChatGPT’s beta MCP connectors can also talk to this server over the SSE transport.

1. Start the server in SSE mode so it exposes the `/sse` and `/messages/` endpoints:

   ```bash
   export FASTMCP_HOST=127.0.0.1 FASTMCP_PORT=8765 MCP_TRANSPORT=sse FASTMCP_LOG_LEVEL=INFO
   python src/intervals_mcp_server/server.py
   ```

   The startup log prints the full URLs (for example `http://127.0.0.1:8765/sse`). ChatGPT needs that public URL, so forward the port with a tool such as `ngrok http 8765` if you are not exposing the server directly.

2. In ChatGPT, open **Settings → Features → Custom MCP Connectors** and click **Add**. Fill in:

   - **Name**: `Intervals.icu`
   - **MCP Server URL**: `https://<your-public-host>/sse`
   - **Authentication**: leave as _No authentication_ unless you have protected your tunnel.

   You can reuse the same `ngrok http 8765` tunnel URL here; just ensure it forwards to the host/port you exported above.

3. Save the connector and open a new chat. ChatGPT will keep the SSE connection open and POST follow-up requests to the `/messages/` endpoint announced by the server. If you restart the MCP server or tunnel, rerun the SSE command and update the connector URL if it changes.

## Development and testing

Install development dependencies and run the test suite with:

```bash
uv sync --all-extras
pytest -v tests
```

### Running the server locally

To start the server manually (useful when developing or testing), run:

```bash
mcp run src/intervals_mcp_server/server.py
```

#### Enabling debug logging

To capture server logs for debugging, wrap the command in a shell and redirect stderr to a file.

**macOS/Linux** — modify your `claude_desktop_config.json` like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "/bin/bash",
      "args": [
        "-c",
        "/Users/<USERNAME>/.local/bin/uv run --with 'mcp[cli]' --with-editable /path/to/intervals-mcp-server mcp run /path/to/intervals-mcp-server/src/intervals_mcp_server/server.py 2>> /path/to/intervals-mcp-server/mcp-server.log"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then tail the log file to see output in real-time:

```bash
tail -f /path/to/intervals-mcp-server/mcp-server.log
```

**Windows** — modify your `claude_desktop_config.json` like this:

```json
{
  "mcpServers": {
    "Intervals.icu": {
      "command": "powershell",
      "args": [
        "-Command",
        "C:\\Users\\<USERNAME>\\.local\\bin\\uv.exe run --with 'mcp[cli]' --with-editable C:\\path\\to\\intervals-mcp-server mcp run C:\\path\\to\\intervals-mcp-server\\src\\intervals_mcp_server\\server.py 2>> C:\\path\\to\\intervals-mcp-server\\mcp-server.log"
      ],
      "env": {
        "INTERVALS_API_BASE_URL": "https://intervals.icu/api/v1",
        "ATHLETE_ID": "<YOUR_ATHLETE_ID>",
        "API_KEY": "<YOUR_API_KEY>",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then monitor the log file in real-time using PowerShell:

```powershell
Get-Content C:\path\to\intervals-mcp-server\mcp-server.log -Wait
```

## License

The GNU General Public License v3.0

## Featured

### Glama.ai

<a href="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@mvilanova/intervals-mcp-server/badge" alt="Intervals.icu Server MCP server" />
</a>
