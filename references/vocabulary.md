# Vocabulary governance, search, and revisions

The document stored in SQLite meta.policy_vocabulary is authoritative; tag_vocabulary is a compatibility projection. JSON is a review/exchange format, not a second independent write source. When a legacy library has no active governed vocabulary, read existing terms and annotations and merge their aliases without a read-time migration. Resolve conflicts before enabling governance.

## Term contract

~~~json
{
  "version": "1",
  "terms": [{
    "facet": "topic", "id": "artificial-intelligence", "label": "Artificial intelligence",
    "aliases": ["AI"], "definition": "Research and applications related to artificial intelligence",
    "broader": [], "related": [], "status": "active", "replaced_by": null
  }]
}
~~~

Identity is the pair (facet, id). Manage preferred label, aliases, definition, same-facet broader/related terms, active/deprecated state, and replacement ID separately. The design is informed by SKOS, but this implementation uses JSON/SQLite and does not claim full RDF/SKOS conformance. Deprecation/replacement behavior and revision gates are Skill engineering rules.

The script checks nonempty/bounded values, same-facet ID/label/alias conflicts, normalized case/full-width conflicts, missing references, synonym/replacement/broader cycles, broader-versus-related conflicts, and depth up to 64. Identical labels across facets are allowed; retrieval must specify a facet or disclose ambiguity. The AI/user must verify meaning and evidence. The script does not assume “machine learning” is an automatic synonym for “artificial intelligence.” Related terms are suggestions; they are not automatically expanded.

Before proposing a term, check existing IDs, labels, aliases, and definitions. Reuse an obvious existing concept; otherwise create a candidate. A user-approved general rule for this library can be applied within the authorized metadata-maintenance scope without one-by-one approvals. Ask about likely synonyms, ambiguous acronyms, or unclear topics. The built-in topic vocabulary is empty; populate it from evidence. Starter vocabulary terms are not required on every file.

## Commands

~~~text
policy-get --root "<library>"
vocabulary-list --root "<library>" --facet topic --offset 0 --limit 100
vocabulary-resolve --root "<library>" --term AI --facet topic
vocabulary-check --root "<library>" --input "<vocabulary.json>"
vocabulary-apply --root "<library>" --input "<vocabulary.json>" --reason "User-approved alias rule" --expected-revision "<preview current_revision>" --execute
policy-history --root "<library>" --kind vocabulary --limit 20
policy-history --root "<library>" --revision "<historical revision UUID>"
~~~

For first activation, expected-revision is none. A changed version requires a new version; importing the same configuration again does not write. Input may be a standalone vocabulary object or the vocabulary field from a template. When checking a legacy library, retain all existing term IDs; do not overwrite the library with the starter template. Never delete historical IDs: mark them deprecated. Set replaced_by only after confirming equivalence, and ensure the replacement chain ends at an active term. Preserve original annotation IDs; queries/HTML project current labels and replacement IDs, with original_tag_id available for traceability.

policy-get returns the scenario, revision, and vocabulary summary by default. Read terms in pages with vocabulary-list. Add --include-vocabulary only when a complete JSON review/export is needed; do not inject the entire vocabulary into every retrieval context.

Checks report total impact counts and preview up to 100 files, clearly indicating truncation. Actual review flags cover all affected records. Name/alias changes refresh navigation/search. Definition/relation/replacement/status changes create vocabulary_review tasks without moving source files. Scenario review is counted separately.

Applying saves a new UUID revision, document, reason, timestamp, and history record, then marks indexes stale. policy-history paginates records; with a revision it can return the historical document. To restore a prior rule, export its document, assign a new version, check/apply it again, and record the reason. This restores rules only; it does not roll back historical file operations or erase review tasks already created.

## Annotation and queries

Once governance is active, annotate must include current policy_revisions at the top level, such as scenario/vocabulary UUIDs for active policies. Files may use active terms only, with labels and aliases matching the shared vocabulary. An annotation cannot rename/add terms. After review, re-annotate to clear that file's vocabulary task and bind it to the current revisions. Content changes still require rereading.

query --tag AI --tag-facet topic resolves through the governed vocabulary and can find older records without rewriting each annotation. A unique explicit term/alias mapping is listed in query_expansions. Cross-facet ambiguity is not expanded automatically; a tag filter reports the ambiguity and candidates. Use --literal to disable keyword expansion. Broader/narrower/related expansion is off by default. The AI should explain the intended scope, query separately, and merge file IDs without describing broader matches as exact synonyms.

document_type is a business material type; format is a byte format; resource_type is a general resource form. Legacy file_type records and --document-type .pdf queries remain compatible. Do not guess/rewrite every old tag from a legacy field; migrate during evidence-based review. --file-format is the independent format filter. Saved views support tag_facet/file_format.

HTML searches only exported metadata, displays current scenario/vocabulary versions, and supports type/format/topic filters and alias search. It does not search non-exported full text or watch the disk. AI answers must still verify the current source file and cite its path and body locator.
