# Navigation for people and AI

## Choose the purpose before the tree

Organize a work library around work goals; organize research material around topics. Reuse valid user structures. Each level should have one primary dimension and clear definitions, inclusion/exclusion boundaries, and overlap precedence. A file has one physical primary location; cross-project/topic discovery uses faceted tags, relationships, and saved views. There is no hard maximum depth, but ordinary documents generally benefit from a shallow two- or three-level tree. Preserve the internal structure of code and media projects instead of flattening them for shallow paths or numbering.

Numbering is an optional human browsing aid. category_id is the logical category ID; file_id is the file UUID; path is the current location; SHA-256 identifies observed bytes. Do not substitute a number for an ID, a hash for file identity, or infer content from a number range. A physical directory-page hash changes when its path changes; it is not a permanent folder ID.

## When to use number + name

1. Follow the user's established numbering/naming convention. If none exists, top-level examples include 10-Project Delivery, 20-Operations, 30-Research, and 40-Learning. These are examples, not mandatory categories for every library.
2. Allocate top-level numbers such as 10, 20, 30 with gaps. Use local second-level numbers such as 01-Contracts and 02-Delivery only when a fixed order is useful. A local 01 has meaning only with its full parent path; it is not globally unique. Customer or topic names usually do not need numbers.
3. Keep numbers stable. Do not renumber a tree because items were added, sorted, or renamed. Give new categories an unused number; do not automatically reuse a retired number for a different meaning. Keep taxonomy category IDs stable. If two-digit numbering runs out, design an extension instead of truncating values and creating collisions.
4. Prefer readable, evidence-based filenames. Add source dates/versions only when known. Do not require a number on each file or stuff every tag into a filename. “Final” is not version evidence.
5. Record number allocation, category IDs, definitions, and suggested paths in .filedb/rules.json or existing user rules. The Skill interprets these rules; the helper does not infer numbering semantics. Preview impacts before changing allocations and include changes in a later organization plan. Index-only authorization does not permit a rename just to add numbers.
6. 00-Inbox-Unclassified may be an approved intake location; 90-Needs-Review is an optional review queue. Do not automatically move unreadable files there. Describe parser issues, affected scope, available coverage, and solutions in the issue view while preserving location/context. Move only when user rules are clear and a move is suitable.

~~~text
Library/
├── AI_README.md / AI_INDEX.md / file-knowledge-base.html
├── 10-Project Delivery/
│   └── Customer A/
│       ├── 01-Contracts/Agreement_v2.pdf
│       └── 02-Delivery/ImplementationPlan.docx
├── 20-Operations/
├── 30-Research/
└── 40-Learning/
~~~

Topics, file types, dates, and states in this example may be tags; the same file need not be copied into multiple branches. If sibling categories mix projects and file types, revise the dimension and boundaries first.

## Human browsing

Open the offline HTML portal → use breadcrumbs/child folders to enter a top-level and subcategory → choose “include subfolders” or “current folder only” → combine category, document type, and content-review filters → inspect a file’s details and copy its path/ID or open the source. For an unknown location, return to “all files.” Show the active scope because retained filters affect results.

The portal reflects physical folders, including empty folders. Show logical category and physical location separately; a “suggested category path” must not imply that a file was moved. Classification/summary evidence differs from factual source locators. A copied path or ID helps locate a file but is not a verified fact citation until the source is checked.

## Precise AI retrieval

Read AI_README and the root index first, then use status to check for changes. With read-only permission, verify source files directly; refresh only when maintenance is authorized.

- **Known location:** use navigate from the root to the exact folder, then navigate that folder to get file IDs. Paginate child folders and direct files separately. Read only relevant branches/pages; do not load every Markdown index.
- **Unknown location:** query multiple keywords/synonyms and tags, inspect matching paths, then navigate to check versions/attachments in context. For cross-topic questions, search broadly before opening one physical branch.
- **Known ID:** use dump --file-id to obtain the current path/hash, then open the source file. Do not follow an old filename blindly. A unique same-hash manual move can retain an ID; ambiguous copies or simultaneous content changes may be treated as missing + new and need review.
- **Answer:** cite the current full path (root-relative or clickable), file_id when useful, and a verifiable page/line/slide/sheet/section/time locator. Finding the file does not guarantee a precise body locator. If only the file path is available, state that; never invent a page number.

## Maintenance details that are easy to miss

- Report classification completion, body-review completion, parser coverage, and source-citation verification separately. Inherited classification does not mean content was reviewed. New files without records still count as semantic review pending. One check does not prove long-term model quality.
- Build a retrieval acceptance set from user-approved queries/file labels; record found files, misses, source locators, and evidence. Synthetic benchmarks test only their fixed fixtures. Track versions, attachments, exports, and exact copies as distinct relationships; do not merge based on similarity.
- Folder renames can affect links inside and outside the library. Directory-plan inbound/internal text references are limited-risk signals. External shortcuts, dynamic paths, encoded links, and application dependencies still require context. Do not rewrite source content to maintain indexes automatically.
- When business work is complete, use archived state or a saved view first. Physical archiving follows user policy; archiving never triggers deletion. PARA may be an optional work-library template; a topical knowledge library need not use its four areas.
- SQLite, navigation, extracted-text caches, and summaries can contain sensitive metadata. The offline portal is not access control. Before sharing, check scope; host controls directory permissions/encryption. Tags and hidden files are not security controls.
- Operation-log rollback restores paths; a SQLite migration backup protects library records. Neither is an independent backup of source materials. Check existing backups/recovery ability before large changes. Do not create external backups or upload files automatically.

See [Methodology and sources](methodology.md) for references and boundaries.
