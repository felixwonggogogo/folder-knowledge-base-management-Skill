# Workflows

## Shared clarification gate for every mode

This Skill is for personal local files. Before creating/changing classification, use the [scenario choice](scenarios.md) if purpose is unknown; keep the main dimension consistent among siblings. Use policy-get to read existing rules. The default template is only a candidate until the user selects it or explicitly delegates the choice. Review/apply the scenario and [vocabulary](vocabulary.md) before annotation using current policy_revisions. Rule changes flag affected files for review; they do not move files automatically.

Use [Clarification and authorization gates](interaction-gates.md) to confirm target path, mode, content access, and write/organization permissions. If “organize this” lacks a directory or operation scope, ask first. Do not assume the working directory or scan before asking. A clear request to create a library can authorize writing its own indexes but does not authorize renaming/moving originals. A clear, actionable request to organize/rename/move/deduplicate a scope permits execution after plan validation without item-by-item approval. Deletion always requires explicit consent for the specific target.

## Create a library

“Create a library” permits index writes. Rename/move permissions come from a clearly scoped organization request. Ask for the root if missing; never scan an entire drive.

1. Preflight tools, parser support, and permission for content to enter the model.
2. scan to create/update the inventory and record exact duplicate files/folder trees, parse errors/truncation, directories, and exclusions. File duplicates use SHA-256. Directory duplicates compare recursive relative paths, file hashes, and empty folders; similar versions are not duplicates.
3. Read profiles in batches with dump. For content outside cache coverage, use an available host parser. Reuse annotations only when the source has not changed.
4. Check category definitions/MECE boundaries. Create title, summary, tags, source evidence, coverage, and confidence.
5. Import with annotate; use index or refresh to generate root entry points, AI instructions, centralized folder navigation, manifest, and human offline HTML. Record additional facts found by host tools in evidence fields; do not claim that helper full-text search covers those facts.
6. Report scanned/skipped/failed/truncated counts, duplicate groups, quarantined item count and recoverable run IDs, review queue, and index paths.

## Organization and recovery

For ordinary file operations, list file_id, old/new paths, sha256, reason, and library root in the plan. Run plan-check first. apply without --execute is validation only. With --execute it changes files. If the user clearly requested actual organization/moves in this defined scope, execute after plan validation. If the request was only to create a library or propose a plan, do not change original files.

Existing subfolders may be renamed or moved as a whole. Use directory-plan --src ... --dst ... --reason ... --save-as ... to produce a complete-tree hash and v2 plan. Review dependency risks, then run directory-plan-check and directory-apply --execute. Decide numbering according to user habits and [Navigation for people and AI](navigation.md). Keep file-level and directory-level stages separate; refresh after each stage and generate the next plan against the new state. Use the same rollback command to recover. Syntax is in contracts.md.

### Quarantine exact duplicates

Call quarantine only after an explicit user request to deduplicate. Clarify intent, path scope, and handling of nested directories. Preview the keeper and quarantined paths. Require SHA-256 or a complete tree manifest to prove exact equality. Prefer user-locked locations; skip conflicting locks or incomplete scans. Execute using same-volume rename into .filedb/quarantine/<run-id>/. Never overwrite, merge, or delete. Log original paths, hashes, and operation stages. After refreshing, quarantined items are excluded from ordinary search but can be traced through the run log.

For recovery, run restore-quarantine --root <library-root> --run-id <run-id> in preview mode. Execute only after confirming the original path is free. Stop if the quarantined bytes changed. There is no automatic expiry/cleanup. If the user wants permanent deletion, list exact items and get explicit consent separately.

The helper creates the destination exclusively, copies, verifies the hash, confirms the source did not change, then removes the source. Temporary duplicate copies may exist; database and disk changes are not one atomic transaction. ACLs, hard links, inode, and all extended-attribute semantics are not guaranteed. Use a dedicated host tool or index-only when these properties matter.

Write the operation log before file changes and update each stage. Stop immediately on failure. Inspect the run before rollback. rollback without --execute is a preview; with --execute it restores paths. Stop and report if the original path is occupied or destination content has changed. Rollback reverses file moves; it does not guarantee reversal of later manual annotations. Rescan and rebuild indexes after recovery.

## Add new materials

Confirm the host's real path for an attachment/outside file and the user-selected library. Use host tools to copy it into a selected library location (for example, Inbox); do not overwrite. Verify its hash and record original path/attachment ID. Preserve the source according to the user's choice. The helper does not copy data from outside the library, fetch URLs, or upload to cloud services.

Rescan using the current taxonomy/vocabulary. Suggest a structural revision only for a genuinely new topic. A copied file gets its own file_id; identical hashes are reported as a duplicate group.

## Search and maintenance

Read AI_README.md and AI_INDEX.md first, then run status. If changes exist and maintenance is authorized, use refresh by default. Use refresh --full to verify every source byte. A read-only query can read current source files directly and report that the index is stale; do not force a write.

Run query --query ... with optional folder/tag/semantic-status filters. Read all relevant pages using total/next_offset. For repeated filters, use view-save, view-list, query --view-name, and view-delete; paginate saved-view results too. Use pending for classification/parse issues and duplicates --kind file|directory --offset N for duplicate groups. Then use dump --file-id ... to check source hash and coverage, and return to the source file to verify facts. Cite current path and a page/line/section/time locator. State when a usable locator is unavailable. Empty search, sampling, the first 100 results, or truncated cache do not prove that information is absent.

For a file lock or active sync, wait only for a short host-approved retry, then verify the live hash. If it is still unstable, leave it pending and do not publish a profile that differs from the source.
