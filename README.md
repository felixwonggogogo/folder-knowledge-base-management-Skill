# AI Local File Knowledge Base

Create, organize, maintain, and search a personal local file knowledge base. The Skill identifies, classifies, tags, renames, and moves files after clarifying the user's goal and scope. It supports incremental maintenance, duplicate detection, lifecycle metadata, source citations, and AI-assisted retrieval.

This repository contains one installable English Skill at its root. Its human-facing HTML portal includes an English/Chinese language toggle.

![Workflow overview](docs/images/workflow-overview.svg)

## Install in Codex

Requirements: Codex Skills support and Python 3.10+ for the included local scripts. The package does not require Jevbox, MCP, a cloud API, or a network connection to manage a local library.

### Windows PowerShell

From a checkout of this repository, copy the Skill files into the Codex Skills folder:

~~~powershell
$skillPath = Join-Path $env:USERPROFILE ".codex/skills/folder-knowledge-base"
New-Item -ItemType Directory -Path $skillPath -Force | Out-Null
Copy-Item -Path ".\SKILL.md", ".\agents", ".\assets", ".\references", ".\scripts", ".\LICENSE" -Destination $skillPath -Recurse -Force
~~~

Restart or refresh Codex Skills if the new Skill does not appear. If your Codex installation uses a custom skills directory, copy the bundle there instead.

### macOS / Linux

From a checkout of this repository:

~~~sh
mkdir -p "$HOME/.codex/skills/folder-knowledge-base"
cp -R SKILL.md agents assets references scripts LICENSE "$HOME/.codex/skills/folder-knowledge-base/"
~~~

Use the Skills directory configured by your Codex installation if it differs from the default.

## Safe first use

Tell the Skill the exact local folder, the task (create, search, maintain, propose, or organize), what content it may read, and whether it may only write indexes or also rename/move files. The Skill asks before acting when a decision that affects scope or authorization is missing.

Permanent deletion always requires explicit consent for the specific target and action. Exact duplicates can be moved to a recoverable quarantine folder when the user explicitly requests deduplication. The Skill does not connect to another service or send content elsewhere by itself.

## What it creates and manages

A managed library has a root `AI_INDEX.md` for navigation, `AI_README.md` with retrieval instructions, an offline human-browsing HTML snapshot, and `.filedb/catalog.sqlite` for structured metadata. The portal is named `file-knowledge-base.html`; its interface defaults to English and can switch to Chinese. User-provided names, tags, and source content remain in their original language. Search results should be verified against the current original file and cited with its path and, when available, page, line, section, or time location.

The included scripts provide inventory, hashing, parsing where supported, duplicate comparison, incremental refresh, SQLite-backed search, planning, and recoverable file operations. The agent performs model-dependent semantic classification; a watcher or script alone cannot do that.

## Repository layout

~~~text
.
├── SKILL.md
├── agents/
├── assets/
│   ├── ai-readme-template.md
│   ├── library-readme-template.md
│   ├── policy-presets.json
│   └── portal-template.html
├── references/
├── scripts/
├── LICENSE
├── README.md
├── CHANGELOG.md
├── .gitignore
├── .gitattributes
└── docs/images/
    └── workflow-overview.svg
~~~

## Validation and known limits

See [references/validation.md](references/validation.md) for the available validation evidence and its limits. Local script checks do not establish behavioral acceptance on a real user's files. This Skill follows the Codex Skills convention; other agent platforms may need packaging changes. Parser coverage depends on the local environment. There is no built-in OCR, hosted semantic/vector search service, or always-on background updater.

## License and repository visibility

This repository is licensed under the MIT License. See [LICENSE](LICENSE). The GitHub repository is currently private; the license does not change its visibility.
