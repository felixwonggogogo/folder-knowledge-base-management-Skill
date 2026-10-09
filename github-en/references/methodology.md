# Methodology and sources

## Personal-scenario and vocabulary additions in v0.7

| Source | How this Skill uses it | Scope and limits |
|---|---|---|
| [DCMI Type Vocabulary](https://www.dublincore.org/specifications/dublin-core/dcmi-type-vocabulary/) and [Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) | Basic resource types; keep business document type, format, and topic distinct | Contract/report are Skill extensions; use fields when evidence supports them, not as required defaults |
| [W3C SKOS](https://www.w3.org/TR/skos-primer/) | Preferred labels, aliases, scope definitions, broader/related terms, and change notes | Lightweight JSON/SQLite implementation; deprecation/replacement and execution revisions are engineering rules, not a claim of full SKOS conformance |
| [PARA](https://fortelabs.com/blog/para/) | Optional purpose-oriented reference for Projects, Areas, Resources, and Archives | Not a mandatory tree for every library; archive decisions follow user policy |
| [Johnny.Decimal](https://johnnydecimal.com/documentation/areas-and-categories) | Broad categories, numbered browsing, and top-down/bottom-up design | The Skill uses its own stable IDs; it does not claim full Johnny.Decimal implementation |
| [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) | Offer common scenarios/default entry first; reveal advanced preferences when needed | Directory, read, and write permissions still require explicit scope |
| [NN/g card sorting](https://www.nngroup.com/articles/card-sorting-definition/) | Use feedback on representative materials to revise category boundaries | Lightweight individual use; not multi-user statistical validation |

The built-in general scenario is this Skill's composition: preserve useful structure/software projects and browse through metadata. A format-based folder tree is not a universal industry standard. See [Scenarios](scenarios.md) and [Vocabulary](vocabulary.md) for templates, interaction, and execution.

| Method | Application in this Skill |
|---|---|
| File plan and inventory | Confirm purpose/scope, inventory, then design folders and names |
| MECE and faceted classification | Check category boundaries and coverage; express cross-cutting attributes with multi-valued tags |
| Controlled vocabulary | Stable category/tag IDs and synonym resolution; apply rule changes only after user acceptance |
| Dublin Core | Select title, creator, date, type, format, subject, identifier, source, and relation as needed |
| W3C PROV | Treat files/versions as entities, scans/classification/moves as activities, and user/model/tools as agents |
| Integrity checks | Hashes detect byte changes and validate operations; they do not prove content correctness or backup recovery |
| Layered retrieval | Root navigation → local index/filtered candidates → original source; lexical retrieval is basic, semantic extension optional |
| Human feedback/selective classification | Leave low-confidence items for review; do not generalize a one-off exception into a global rule |

Indexes are derived data; changes invalidate old evidence and summaries. Archive does not mean delete, and retention periods follow user policy. The Skill does not claim conformance to a complete archival standard.

Further references:
- [NARA records scheduling implementation](https://www.archives.gov/records-mgmt/scheduling/implementation): purpose, inventory, and planning sequence. Institutional disposition rules do not directly apply to personal files.
- [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/): field semantics and resource relationships.
- [W3C PROV Primer](https://www.w3.org/TR/prov-primer/): entities, activities, agents, and derivation.
- [Library of Congress data integrity management](https://www.loc.gov/programs/digital-collections-management/inventory-and-custody/data-integrity-management/): checksums for monitoring content changes.

Jevbox inspired layered navigation and source-evidence retrieval. This Skill does not depend on its server, JEV model gateway, or permission service.

## Comparison with public practices and local adaptation (reviewed 2026-10-09)

| Primary source | Practice to learn from | Local adaptation and limits |
|---|---|---|
| [Microsoft SharePoint information architecture](https://learn.microsoft.com/en-us/sharepoint/information-architecture-modern-experience) | Design global/local navigation, metadata, and search together; reduce deep nesting | Navigate from broad categories to subcategories; tags and saved views support cross-cutting search. Keep ordinary documents shallow; do not restructure code projects automatically. |
| [SharePoint Document IDs](https://support.microsoft.com/en-us/sharepoint/admin/enable-and-configure-unique-document-ids) | Use identifiers for location and distinguish move identity from copy identity | Use UUID file_id + current path + byte hash. Track current source after rename/move. Ambiguous copies or simultaneous content changes require review. Local libraries do not provide SharePoint permanent links. |
| [Google Drive file search](https://support.google.com/drive/answer/2375114?hl=en) | Combine text search with type filters; offer paths for known and unknown locations | Combine physical-folder navigation, keywords, categories, tags, and review state. The local helper provides stated lexical/FTS search, not Drive's natural-language search. |
| [Johnny.Decimal areas and categories](https://johnnydecimal.com/documentation/areas-and-categories) | Broad categories and numbered browsing reduce filing decisions | Borrow stable numbers and readable names without imposing decimal hierarchy on every library. Two-digit numbering here is not full Johnny.Decimal. |
| [Tiago Forte PARA](https://fortelabs.com/blog/para/) | Organize around active outcomes and responsibilities; distinguish projects, areas, resources, archives | Offer PARA for work libraries; do not force it on topical research libraries. Express active/archive with business_state or views; archive does not delete. |
| [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) | Identifiers, titles, sources, relations, types, and topics have distinct meanings | Separate category_id/file_id/path/hash; record attachments, versions, and format exports as different relations instead of treating filenames as evidence. |
| [Library of Congress data integrity management](https://www.loc.gov/programs/digital-collections-management/inventory-and-custody/data-integrity-management/) | Establish file/collection checksums early and log verification | Use hashes and directory manifests to verify plans/execution/recovery. They do not replace independent backups, restore drills, or content correctness review. |

These are methodological references and local adaptations. The Skill does not claim the products' permissions, compliance, cloud sync, or search services. Ongoing maintenance depends on checking actual state and user feedback; one synthetic test cannot prove classification or retrieval quality on real files. See [navigation.md](navigation.md) for decision, operation, and citation procedures.
