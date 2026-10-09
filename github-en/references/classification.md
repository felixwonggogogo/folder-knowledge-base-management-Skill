# Classification, tags, and naming

## Decision priority

Explicit user rules → confirmed library rules → useful existing structure/context → source content → filename/path hints. Explain conflicts and preserve the original location. A user's manual move takes precedence over an older automated classification; keep a location lock unless the user asks to reorganize it.

## MECE and category boundaries

Determine the purpose before selecting a primary dimension: project/deliverable purpose for a project library, topic for a knowledge library, and business matter for financial records. Do not mix “Customer A,” “PDF,” “2026,” and “completed” as siblings; they represent different dimensions.

When purpose is unknown, offer the choices and free-text option in [Personal scenarios](scenarios.md). If the user explicitly selects no preference, use the general template: preserve useful structure and start with metadata/browsing views. Do not split projects by extension. Reuse confirmed scenarios and record branch dimensions for mixed libraries.

- Give each category a stable ID, label, target relative path, definition, and inclusion/exclusion examples.
- Use one partition dimension among siblings. When boundaries overlap, set a precedence rule or revise them.
- Give each confirmed file one primary category. Express cross-topic attributes with tags/relationships instead of physical copies.
- Route every file to a confirmed category or a review queue. A queue does not prove that all business categories have been covered.
- Create branches for real purposes; do not add a new category for every upload. Set depth based on volume and the user's habits.
- Check existing categories and synonyms before adding a category. A taxonomy version change triggers review of affected files, but does not move user-locked items.

Report coverage counts, ambiguous files, overlapping categories, uncovered topics, and revision proposals. Record rule matches separately from source evidence.

## Faceted tags

Use facets such as project/topic/document_type/time/status/source as needed; do not require every facet. Map synonyms to stable tag IDs and retain aliases. Keep business state, parse state, and classification-review state independent.

Separate document_type (business purpose such as contract/report), format (PDF/DOCX), and resource_type (text/dataset). Validate and revise governed vocabulary according to [Vocabulary governance](vocabulary.md). File annotations reference active IDs and do not overwrite public definitions. Do not invent unknown dates. Use lifecycle commands for business stages rather than driving operations from tags.

Dates come from source content or an explicit rule; never infer contract or publication dates from modification time. Set unknown author/date/project values to null. Both source facts and tags need evidence.

Versions, format variants, attachments, citations, and exact byte copies are distinct relationships. A matching hash proves identical bytes only. Similar text does not support automatic merging, and a “final” filename does not prove recency.

## Exact duplicates and retention

- Files qualify only when their complete SHA-256 hashes match. Directories qualify only when complete relative paths, all included file hashes, subdirectories, and empty-folder manifests match. An excluded or unstable descendant prevents its parent from being automatically declared a full duplicate.
- Run automated deduplication only when the user explicitly asks for it. Prefer an existing user-locked location. Skip a group with multiple locked locations. Otherwise choose a stable keeper by shallower folder depth, then relative-path order.
- Confirmed version-group members are also protected. If an exact-duplicate group contains multiple confirmed business versions or locked locations, report it; identical bytes do not prove that distinct business identities may be discarded. Use stable path ordering only when no protected item exists.
- Atomically move other copies to .filedb/quarantine/<run-id>/ and log the move so the user can restore them. Quarantined items are excluded from the active library and search indexes, but are not deleted. Never auto-clear, expire, or merge quarantine.
- Do not act on similar documents, differing versions, incomplete directory scans, links/reparse points, or conflicting user locks. Exact byte identity can still be an intentional reuse in different folders; report duplicates only unless the user asks to deduplicate.

## Naming

Numbering can help people sort and remember folders, but AI does not require it. When the user has no existing convention, stable two-digit numbers plus readable names are suggested for top-level groups, e.g. 10-Project Delivery, 20-Operations, 30-Research. Number subcategories only when a fixed order or many siblings makes it useful. Do not number every file or frequently renumber folders for sorting. See [Navigation for people and AI](navigation.md) for scope, allocation, examples, and location rules.

Keep the extension and use concise, evidence-based names. A name such as 2026-10-08_ProjectA_ResearchReport_v2.pdf may help when those values are known; do not invent dates or versions. Do not put every tag in the filename when metadata already records it.

Preserve original names, original paths, and all path changes. Reject path separators, control characters, Windows-invalid characters/device names, and trailing spaces or periods. For collisions, use a short ID or a user-approved suffix; never overwrite.

Case-only renames, name swaps, and chained paths need staged plans; the helper refuses to execute them directly. Software, media projects, internal links, and application data are index-only by default. Account for dependencies in any concrete plan and do not rewrite internal content.
