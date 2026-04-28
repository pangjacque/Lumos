# Installing Lumos for VS Code + GitHub Copilot

This guide installs Lumos as **per-workspace skills** in your VS Code project. Skills are symlinked into your workspace's `.github/skills/` folder, where VS Code Copilot scans for them.

## Prerequisites

- VS Code with the [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) extension
- Git
- Python 3.10+ with the dependencies in [`bin/requirements.txt`](../bin/requirements.txt) (`pip install -r bin/requirements.txt`)

## How it works

VS Code Copilot scans `<workspace>/.github/skills/<name>/` for skills. By creating junctions (Windows) or symlinks (macOS/Linux) from Lumos's `skills/` folders into your workspace's `.github/skills/`, you make `/lumos-everything`, `/lumos-chat`, and `/lumos-diff` available in that workspace's Copilot Chat.

> **Note:** This is **per-workspace** — repeat Step 2 for each project where you want Lumos available. Step 1 (cloning Lumos) only needs to be done once.

## Step 1 — Get Lumos onto your machine (one-time)

Pick any location that won't move and remember the path for Step 2.

### Option 1 — Git clone (preferred)

**Windows (PowerShell):**

> 💡 The example below uses drive `I:` and folder `\Lumos`, but **any drive (C:, D:, etc.) and any folder name work**. Keeping Lumos on the **same drive as your codebase** simplifies the symlink step and avoids cross-drive permission issues.

```powershell
git clone https://github.com/pangjacque/Lumos.git I:\Lumos
```

**macOS / Linux (Bash):**

```bash
git clone https://github.com/pangjacque/Lumos.git ~/lumos
```

### Option 2 — Download ZIP (if `git clone` is blocked)

Useful if your network blocks git protocol or you can't install Git.

1. Visit [https://github.com/pangjacque/Lumos](https://github.com/pangjacque/Lumos) in a browser
2. Click the green **`Code`** button → **`Download ZIP`**
3. Unzip the file at your chosen location

> ⚠️ GitHub names the ZIP `Lumos-main.zip` and the unzipped folder is `Lumos-main/` (not `Lumos/`). Either:
> - **Rename** the folder to `Lumos` after unzipping, or
> - **Use `Lumos-main`** in Step 2's `$lumosRepo` / `LUMOS_REPO` variable

Concrete example after unzipping on Windows:
```
I:\Lumos-main\        # if you didn't rename
I:\Lumos\             # if you renamed (matches the git clone example)
```

Either path works — just be consistent in Step 2.

## Step 2 — Symlink Lumos's skills into your workspace's `.github/skills/`

You'll edit two path variables: where Lumos lives, and which workspace you want Lumos available in.

### Windows (PowerShell)

```powershell
# === Edit these two paths to match your setup ===
$lumosRepo = "I:\Lumos"               # where you cloned Lumos in Step 1
$workspace = "I:\your_codebase"       # the project where you want Lumos available

# Create the .github/skills directory if needed
New-Item -ItemType Directory -Force -Path "$workspace\.github\skills" | Out-Null

# Create a junction for each Lumos skill
Get-ChildItem "$lumosRepo\skills" -Directory | ForEach-Object {
  $target = "$workspace\.github\skills\lumos-$($_.Name)"
  if (Test-Path $target) { Remove-Item $target -Force -Recurse }
  cmd /c mklink /J "$target" $_.FullName
}

# Verify
Get-ChildItem "$workspace\.github\skills" | Where-Object { $_.Name -like "lumos-*" }
```

You should see three junctions created: `lumos-chat`, `lumos-diff`, `lumos-everything`.

### macOS / Linux (Bash)

```bash
# === Edit these two paths to match your setup ===
LUMOS_REPO="$HOME/lumos"               # where you cloned Lumos in Step 1
WORKSPACE="$HOME/projects/my-project"  # the project where you want Lumos available

mkdir -p "$WORKSPACE/.github/skills"

for skill in "$LUMOS_REPO"/skills/*/; do
  name=$(basename "$skill")
  ln -sfn "$skill" "$WORKSPACE/.github/skills/lumos-$name"
done

# Verify
ls -la "$WORKSPACE/.github/skills/" | grep lumos-
```

## Step 3 — Reload VS Code

VS Code Copilot doesn't pick up new skills until the window reloads.

1. Open the workspace in VS Code: `code "<your workspace path>"`
2. Open the Command Palette: `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (macOS)
3. Run: **`Developer: Reload Window`**

## Verify

### Symlinks landed correctly

Your workspace's `.github/skills/` folder should now contain three Lumos skill symlinks, each with a `SKILL.md` inside (visible in VS Code's Explorer panel):

```
.github/
└── skills/
    ├── lumos-chat/
    │   └── SKILL.md
    ├── lumos-diff/
    │   └── SKILL.md
    └── lumos-everything/
        └── SKILL.md
```

If you see this structure, the symlinks are wired up correctly. (The folders are junctions/symlinks pointing at your Lumos clone — VS Code's Explorer shows them like real folders, but they reflect any updates you `git pull` in the Lumos repo.)

### Skills appear in Copilot Chat

Open the Copilot Chat panel and type `/`. You should see three Lumos entries in the autocomplete:

- **`/lumos-everything`** — full project scan (code, notebooks, docs, cross-boundary references)
- **`/lumos-chat`** — ask natural-language questions about the project
- **`/lumos-diff`** — impact analysis of unstaged changes

Run `/lumos-everything`. The orchestrator runs through 7 phases — expect output similar to:

```
Phase 1 — SCAN:       <N> files found (<n_code> code, <n_nb> notebooks, <n_doc> docs, <n_cfg> config, <n_data> data)
Phase 2 — CODE:       <N> Python nodes, <N> edges (Scala extractor needs tree-sitter installed if you have .scala files)
Phase 3 — NOTEBOOKS:  <N> nodes, <N> edges from <n_nb> notebooks
Phase 4 — DOCS:       <n_doc> files, <N> sections
Phase 5 — RESOLVE:    cross-boundary imports linked
Phase 6 — MERGE:      knowledge-graph.json produced
Phase 7 — REPORT:     report-force.html + report-cards.html generated

Files analyzed: <total>
Nodes: <total_nodes>
Edges: <total_edges>
```

(Numbers vary by project. Phases run in this order regardless of project size.)

After completion, you'll find these in the workspace's `.lumos/` folder:

- `knowledge-graph.json` — complete graph (nodes + edges)
- `report-cards.html` — hierarchy + notebook view
- `report-force.html` — interactive force-directed graph
- `metadata.json` — scan metadata (file hashes for incremental updates)

### Open the interactive report

Double-clicking the file in your file explorer usually works, but if it opens in VS Code's text editor instead, force a browser launch from the terminal:

**Windows (PowerShell)** — opens in your default browser:
```powershell
Start-Process "$workspace\.lumos\report-force.html"
# Or to force Chrome specifically (if installed):
# Start-Process "chrome.exe" "$workspace\.lumos\report-force.html"
```

**macOS (Bash):**
```bash
open "$WORKSPACE/.lumos/report-force.html"
# Or to force Chrome specifically:
# open -a "Google Chrome" "$WORKSPACE/.lumos/report-force.html"
```

**Linux (Bash):**
```bash
xdg-open "$WORKSPACE/.lumos/report-force.html"
```

The `report-cards.html` (hierarchy + notebook view) opens the same way — just swap the filename.

## Use Lumos in another workspace

Repeat **Step 2** with a different `$workspace` / `$WORKSPACE` value. Step 1 (cloning Lumos) doesn't need to be redone.

## Troubleshooting

**`mklink` fails with "You do not have sufficient privilege" (Windows):**
The `/J` flag creates a junction, which doesn't need admin. If you copy-pasted with `/D` instead, that requires admin. Re-check the command uses `/J`.

**Skills don't appear in Copilot Chat after `/`:**
- Confirm you reloaded the VS Code window (Step 3)
- Confirm you opened the **workspace** in VS Code, not the parent folder. The `.github/skills/` discovery is workspace-relative
- Confirm the junctions exist: `ls .github/skills/` in your workspace should show `lumos-chat`, `lumos-diff`, `lumos-everything`

**`Error: nbformat is required` during scan:**
Run `pip install -r <lumos repo>/bin/requirements.txt` (or just `pip install nbformat`).

## Uninstall

To remove Lumos from a workspace:

**Windows (PowerShell):**
```powershell
Remove-Item "$workspace\.github\skills\lumos-*" -Recurse -Force
```

**macOS / Linux (Bash):**
```bash
rm -rf "$WORKSPACE/.github/skills/lumos-"*
```

This removes only the symlinks/junctions; the original Lumos clone is untouched.

---

For the native Claude Code marketplace install, see the [main README](../README.md#-quick-start).
