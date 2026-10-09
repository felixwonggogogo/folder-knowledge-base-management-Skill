# Validation record and acceptance boundaries

Version: 0.7.0. Date: 2026-10-09.

## Local script verification

The source Skill's scripts/verify_local.py ran against a disposable synthetic directory on Python 3.11.9: 70 passed, 0 failed, 0 skipped. Coverage included new/legacy library recognition, schema migration, fast/full scans, resumable batch scans, preventing partial publish after source/directory changes, parser timeouts/retries, queries/saved views, classification-rule impact previews, exact duplicates/recoverable quarantine, file/folder move recovery, symlink protection, watcher start/stop, and AI/human entry-point generation.

Additional checks covered independent pagination for layered navigation; empty folders/prefix collisions; directory-plan generation, save, and recovery; inbound encoded links; missing-profile semantic accounting; version-group current markers/content-change invalidation; archive retrieval; historical metadata; content snapshots/recovery copies; concurrent destination protection; read-only schema-2 compatibility; business-version protections for duplicate groups; and plans spanning more than 100 groups.

scripts/verify_policy.py added 15 synthetic checks: six personal-scenario templates; zero-write template/read/check behavior; policy revision/version conflicts; new aliases matching old profiles (including full/half-width and English partial terms); protection of governed vocabulary from annotation edits; cross-facet ambiguity; same-facet alias conflicts; cycles/references/depth; deprecated replacements/review; history/restore; scenario changes respecting location locks and content; document type/format and saved views; legacy alias compatibility; and CLI preview/apply. Total: 85 checks, based on the final execution receipt in the source delivery.

Scan verification covered CLI resumption with --batch-size/--job-id; unchanged active inventory until completion; stale results after added files or byte changes with unchanged size/timestamp; and refresh rebuilding indexes only after scan completion. PDF/Office XML subprocess timeouts become read_error with a specific cause; plain text has byte/character limits but no claimed per-file wall-clock timeout.

Command:

~~~text
python -B -X utf8 "<skill-dir>/scripts/verify_local.py"
~~~

## Search benchmark and browser verification

- scripts/benchmark_search.py: four synthetic Chinese queries; SQLite FTS5 trigram was available, macro/micro recall were 1.0, and all hit sources were fresh. This result applies only to the fixed synthetic corpus. It does not establish accuracy on real files and is not vector/semantic search.
- scripts/verify_portal_browser.py: local Chromium 145.0.7632.6. The actual generated page and a 10,000-record synthetic metadata page passed checks for 40-row pagination; new governed aliases; topic/type/format filters; scenario/vocabulary revision display; layered folders/breadcrumbs/current-folder vs subtree scope; empty folders; file IDs; lifecycle filters; search; keyboard details; copy fallback; issue view; 390px narrow layout; and no-script notice. There were zero external requests and zero console/page errors. Synthetic business evidence does not establish user-material quality.
- scripts/folderdb_watch.py: lifecycle, status, log, and incremental reconciliation checks passed on a temporary synthetic library. Watching is off by default, registers no system service/task, calls no model, and changes no source file.

These historical checks were run against the Chinese-language source Skill before this English release. They cover script behavior on synthetic fixtures, but do not independently verify the English instructions, translations, or every documented workflow.

## SkillHub static tests and runtime simulation in the source package

The local SkillHub asset test covered normal, boundary, and rejection cases, currently 15 examples. Added cases covered scenario choice, custom input, no inferred authorization from silence, governed-alias search, and refusal to merge ambiguous terms. A model-less Host Surface simulation used the same 15 entry contracts with external network disabled and model_hit_rate=null. It establishes only local declarations, resource paths, and read contracts; it does not establish real model answers, classification, or UI choice behavior. Use the final receipt for pass counts and resource/routing proxies. Each release is tied to the ZIP SHA-256 in its receipt.

A release audit of references/workflows.md emitted one non-blocking review note for compliance-risk wording about directory/move authorization and “no deletion.” This was a textual review prompt, not a script failure; a human should verify alignment with the authorization gate.

## Limits

These results do not establish desktop-app import, cross-machine compatibility, real-model classification quality, OCR/PDF coverage for every format, unattended long-running operation, or independent backup/recovery. SkillHub import/review/publishing and real runtime behavior were not verified. Rename/move/lifecycle/snapshot checks ran only in temporary synthetic libraries, not user materials. Earlier scans/indexing of real directories do not constitute content-classification acceptance. A real library still requires review of rules, source text, and retrieval results.
