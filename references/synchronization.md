# Incremental synchronization from observed changes

## Three trigger modes

1. **Refresh on invocation (default):** before maintenance/search, use status to compare file size, mtime_ns, paths, and directory snapshots. If changes exist and this session is authorized for maintenance, run refresh. Fast mode processes changes and rebuilds Markdown/HTML. A read-only query reports changes without writing the library.
2. **Scheduled rescans (only when the host supports them and the user authorizes them):** let the host run the same flow. Inventory/indexing is independent of the model; semantic classification requires a real agent task.
3. **File watcher (only when the host supports it and the user authorizes it):** coalesce/debounce events, wait for source files to stabilize, then rescan. Missed events, sleep, bulk paste, or a process crash are reconciled against the next snapshot. Never claim that this Skill created a background service when it did not.

status is a cheap path/size/time comparison. It cannot detect byte changes that retain the same size and timestamp. Fast refresh reuses hashes only for files whose metadata has not changed; refresh --full or the default scan recomputes hashes for all included files and reparses only changed content. Before citing source facts, use dump to recheck the live source hash. A host may optimize large-library event handling, but periodic full reconciliation is still needed.

Long scans can use --batch-size to create a resumable job. Each invocation processes a bounded set and returns job_id. The host/agent calls again with the same options and supplies --job-id when resuming. SQLite stages job inputs, progress, and parse cache; status reports pending_scan_job. During process/verify, the published active inventory is unchanged. The job verifies directory snapshots, database baseline, and source content before one final publish. Conflicts return stale; the old inventory remains available, and a new scan must be started after reconciliation. This is caller-driven resumption, not a resident task, and does not guarantee continuation after the desktop closes. Concurrent filesystem writes also limit snapshot consistency; validate again before publishing.

## What events mean

| Observed change | Inventory and content | Classification and indexes |
|---|---|---|
| New file | New ID, hash, parse state | Add to identification queue; do not move it |
| Changed content | Keep ID at same path; record new hash and invalidate old profile | Re-identify; keep user-locked location |
| Manual rename/move | Link only if exactly one missing + one new path share a hash | Update path and set location lock; do not move back automatically |
| Rename and content change | No stable OS ID proves identity | Treat as missing + new; leave relation for review |
| Several same-hash copies | Migration identity is ambiguous | Keep separate records; do not auto-merge |
| User explicitly requests exact deduplication | Revalidate duplicate group and keeper | Move other copies on the same volume to .filedb/quarantine/<run-id>/; exclude from ordinary search/index and log recovery |
| Restore a quarantined item | Verify quarantined bytes and original path availability | Update inventory/index; stop on destination conflict or changed bytes |
| File removed from scan | Keep missing history | Remove from active index; do not delete other files |
| Folder change | Update empty/nonempty folder snapshot | Rebuild centralized navigation; move old child indexes only if registered hash matches |
| Manual index edit | Generated-index hash differs from last recorded hash | Preserve it and report conflict |
| Rule/classification change | Increment taxonomy revision | Identify affected files; keep location locks |

A temporary read failure must not make an entire directory look deleted. If a directory cannot be enumerated, abort publication of that scan and retain the previous inventory. Record an unstable individual file as an issue; do not reuse old facts as current.

## Pending review and consistency

When a source changes, the index may mark it “needs re-identification” immediately; do not present the old summary as current. annotate must include the scan-time source_sha256 and compare it with the live file before import. If it differs, rescan and reclassify. refresh updates inventory and derived views only; it does not invent classifications or call a background model.

The disk is authoritative for file existence, paths, and bytes. The inventory is authoritative for indexed/annotation state. Markdown is generated navigation. Plans, classification queues, and indexes cannot reconstruct user-deleted source files.

Background updates use only user-authorized directories/actions. Existing library-creation authorization permits inventory refresh. It does not authorize moving new files, reclassifying the whole library, or moving files due to rule changes. A clear request to organize/deduplicate a defined scope authorizes execution of a validated rename/move/quarantine plan. Permanent deletion is separate and requires explicit consent for the specific file/folder.
