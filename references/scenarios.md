# Personal scenarios, choice prompt, and defaults

This Skill is for personal local files. A scenario guides the main classification dimension, category boundaries, and retrieval paths; the actual inventory must verify whether the template fits. A template is not authorization to act.

## Ask the user

Ask only when a classification is being created or changed and the purpose is unknown:

**“What are these materials mainly for? Choose the closest scenario. If none fits, describe the purpose in your own words.”**

| Common choice | Main dimension and template |
|---|---|
| General personal files (default) | general: preserve useful structure; find materials through metadata and saved views |
| Project work | work: project → stage/deliverable |
| Research | research: research question/topic → subtopic |
| Learning | learning: learning goal/course → knowledge topic |
| Personal affairs | personal: area of responsibility → specific matter |
| No preference; use the default | Explicitly select general, while still respecting this session’s scope, content, and write permissions |

If none fits, let the user enter a purpose, common retrieval questions, and preservation preferences. Use the custom template and complete its boundaries rather than forcing a preset. If a choice widget provides free text, use it; in plain chat, explicitly invite a custom answer after the options.

Do not re-ask a confirmed scenario/rule. Read-only search does not require full scenario setup. If the user says “you decide” or “use the default” and the task and permissions are clear, state that general will be used and continue. No answer is not a default selection or operation authorization. If only the scenario preference is unknown, continue already authorized inventory/indexing and pause only placement/move decisions that depend on purpose.

## Default configuration

assets/policy-presets.json contains candidate templates and 19 starter terms. General metadata separates resource_type (text/dataset etc.), document_type (contract/report etc.), format (PDF etc.), topic, project, and source. Do not invent unknown facts. Business lifecycle is managed separately; tags do not automatically trigger archive/delete operations.

By default, preserve a useful folder structure and intact software projects; provide type/topic navigation through metadata. If a new tree is needed, create a small number of defined top-level categories based on the actual materials; do not pre-create every possible empty folder. Numbering is a recommendation and never triggers an automatic rename. A format view does not split one project into separate trees by extension. Logical classification can differ from physical location.

A mixed library can use different main dimensions in different branches, recorded by scenario.branches with relative path, dimension, and definition. A deeper branch overrides its parent. If placement is unclear, keep the item in place and flag it for review. The taxonomy still needs category_id, definition, includes, and excludes; a scenario does not replace concrete category rules.

## Script workflow

Use the absolute path to this Skill’s scripts/folderdb.py.

~~~text
policy-template --root "<library>" --preset general
policy-get --root "<library>"
scenario-check --root "<library>" --input "<scenario.json>"
scenario-apply --root "<library>" --input "<scenario.json>" --reason "User selected general personal files" --expected-revision none --execute
~~~

template does not require a managed library and does not write. Other commands require a managed library; initialize it with scan only if already authorized. Input accepts a scenario object or a template result containing scenario. Preview returns current_revision. Replacing an existing rule requires that revision and a new document.version. Without execute, the command only previews.

SQLite meta.policy_scenario stores the active rule. policy-get can export it for review. Preserve valid user conventions in legacy rules.json; explain and merge them rather than overwriting. Scenario changes are versioned and flag affected classifications for review without moving original files. Concrete taxonomy revisions, vocabulary revisions, and document versions are managed separately.

## Personal feedback

Apply a correction to the named files first. Treat it as a general rule only when the user says to use it going forward. Before applying changed definitions/assignments, preview the affected count and stay within the confirmed maintenance scope. Preserve user-locked locations. New materials reuse the current scenario; silence does not reset it to the default. Suggest a local rule when a new purpose or ambiguity appears.

Method sources include Dublin Core’s distinction between type and format, PARA’s purpose-oriented organization, Johnny.Decimal’s broad categories/numbering, and NN/g’s progressive disclosure and card sorting. General is this Skill’s design, must be checked against actual files, and is not a universal industry standard. See [Methodology and sources](methodology.md).
