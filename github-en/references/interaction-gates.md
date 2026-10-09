# Clarification and authorization gates

Understand the user’s intent before taking specific action on their selected directory. Ask questions only to resolve ambiguity that changes scope, data access, or file changes. Do not ask users to repeat clear instructions.

## What to clarify before acting

Use the conversation and ask only about missing decisions that affect execution:

1. **Target:** exact local root and included/excluded folders or file types. Do not assume the workspace, Desktop, Downloads, or Skill repository is the target.
2. **Mode:** create, search, maintain, propose a classification/organization plan, or actually rename/move files. A broad request such as “organize this” or “take a look” does not identify the mode.
3. **Content access:** what materials may be read and analyzed in this agent session. Local access does not authorize sending them to another service.
4. **Writes and file operations:** may the Skill create/update .filedb, AI_INDEX.md, and other derived knowledge-base files? For actual organization/deduplication, is the target scope and rule clear? A clear request to organize, rename, move, or deduplicate a defined scope authorizes this session to execute a validated plan without per-item approval.
5. **Deletion:** obtain explicit consent for the exact targets and deletion action before permanently deleting any user file or folder. “Organize,” “deduplicate,” “clean up,” and general move authorization do not authorize deletion. Exact duplicates are moved to recoverable quarantine by default.
6. **Purpose:** when creating/changing classification rules and the purpose is unknown, offer the common choices: general personal files (default), project work, research, learning, personal affairs, or no preference/use the default. Provide a free-text option if none fits. Reuse a confirmed scenario. Read-only search does not need scenario setup. The user may explicitly delegate selection of the general scenario; no response is not a choice and does not add authorization. See [Scenarios](scenarios.md).

Apply the same gate to versions and lifecycle. A clear request to maintain knowledge-base metadata can update business states and version records. Designate a current version only from the user's explicit selection, confirmed rules, or evidence in the source. Run snapshot --execute only after an explicit request to keep a recoverable content copy. Run restore-copy --execute only after an explicit request to restore to a new unused path. An ordinary index write does not authorize copying document bodies in bulk. A due review date or business archive does not authorize deletion, and historical snapshots are never cleaned automatically. If a decision is missing, pause only the action that depends on it; continue authorized indexing and search.

Bundle high-impact questions instead of asking a chain of low-impact preference questions. Offer a conservative proposal when useful, but do not treat a proposal or default as authorization before the user responds.

## Stop rules when information is missing

- **Root is unclear:** do not run status, scan, search, or content reads against candidate directories. General capability checks unrelated to the target may continue.
- **Mode or scope is unclear:** identify the ambiguity and ask; do not initialize a database, create indexes, classify, or move files.
- **Write permission is unclear:** limit work to authorized read-only inspection or a plan. Do not create .filedb, AI_INDEX.md, rules, or capability records.
- **Model access to content is unclear:** do not read document bodies. You may report file-name/format preparation needs and wait for a content-access decision.
- **Rename/move/deduplication scope or rule is unclear:** provide candidates and a per-item plan; do not execute. A plan file is itself a write, so save it only to an authorized location or show it in the response.
- **Deletion lacks consent for the exact target/action:** do not delete or interpret silence/refusal as consent. Continue separately authorized reversible moves or indexing.

## Continue after clarification

Restate the confirmed root, mode, and allowed side effects, then use the smallest sufficient workflow. A clear request for a concrete, fully scoped operation can itself be authorization; do not ask again. Related actions that were not requested remain unauthorized. For example, “create a knowledge base in D:\Files” permits writing its own indexes but not moving materials; “organize and deduplicate D:\Files\Contracts” permits validated renames/moves and quarantine of exact duplicates but not permanent deletion; “find contracts in D:\Files” permits read-only search but not a database write.

If inventory reveals a new ambiguity (overlapping categories, name conflicts, permission failures, or newly discovered files in a move plan), pause only the affected part. Report completed and unexecuted work, then ask about the new decision. Do not expand scope because a batch has started.

If the user changes the target, update the current scope to the latest explicit instruction. Stop actions that depend on the old target until the new path or permission is clear.
