#!/usr/bin/env python3
"""Personal scenario and vocabulary policy. SQLite is authoritative; no model/network."""
from __future__ import annotations

import contextlib
import copy
import json
from pathlib import Path
import unicodedata
import uuid


def norm(value):
    return unicodedata.normalize("NFKC", value).strip().casefold()


def bounded(value, field, cap=500):
    if not isinstance(value, str) or not value.strip() or len(value) > cap:
        raise ValueError("Require bounded nonempty " + field)
    return value


def text_list(value, field, cap=64):
    if not isinstance(value, list) or len(value) > cap:
        raise ValueError("Require bounded array: " + field)
    for item in value:
        bounded(item, field, 120)
    if len({norm(v) for v in value}) != len(value):
        raise ValueError("Duplicate normalized values: " + field)
    return value


def template(preset="general"):
    data = json.loads((Path(__file__).resolve().parent.parent / "assets/policy-presets.json").read_text(encoding="utf-8"))
    if preset not in data["scenarios"]:
        raise ValueError("Unknown scenario preset")
    return {"writes": False, "authorization_granted": False,
            "scenario": copy.deepcopy(data["scenarios"][preset]),
            "vocabulary": copy.deepcopy(data["vocabulary"])}


def stored(con, kind):
    row = con.execute("SELECT value FROM meta WHERE key=?", ("policy_" + kind,)).fetchone()
    return json.loads(row[0]) if row else None


def vocabulary(con):
    current = stored(con, "vocabulary")
    if current:
        return current["document"]
    # Old libraries keep their vocabulary without a read-time migration.
    terms = {}
    for row in con.execute("SELECT * FROM tag_vocabulary ORDER BY facet,tag_id"):
        terms[(row["facet"], row["tag_id"])] = {"facet": row["facet"], "id": row["tag_id"],
            "label": row["label"], "aliases": json.loads(row["aliases_json"]), "definition": "Legacy vocabulary term; definition needs review",
            "broader": [], "related": [], "status": "active", "replaced_by": None}
    # Recover aliases omitted by legacy last-writer updates without choosing new meanings.
    for row in con.execute("SELECT profile FROM files WHERE profile IS NOT NULL"):
        for tag in json.loads(row[0]).get("tags", []):
            key = (tag["facet"], tag["id"])
            item = terms.setdefault(key, {"facet": tag["facet"], "id": tag["id"], "label": tag["label"],
                "aliases": [], "definition": "Legacy vocabulary term; definition needs review", "broader": [], "related": [], "status": "active", "replaced_by": None})
            candidates = [tag["label"], *tag.get("aliases", [])]
            known = {norm(item["label"]), *map(norm, item["aliases"])}
            for candidate in candidates:
                if norm(candidate) not in known:
                    item["aliases"].append(candidate)
                    known.add(norm(candidate))
    return {"version": "legacy", "terms": list(terms.values())}


def validate_scenario(api, root, doc):
    if not isinstance(doc, dict) or set(doc) - {"version", "id", "label", "scope", "purpose", "primary_dimension", "facets", "preserve_existing", "branches", "example_queries", "numbering"}:
        raise ValueError("Unsupported scenario fields")
    for field in ("version", "id", "label", "purpose", "primary_dimension"):
        bounded(doc.get(field), field)
    if doc.get("scope") != "personal" or not isinstance(doc.get("preserve_existing"), bool):
        raise ValueError("Scenario requires personal scope and boolean preserve_existing")
    text_list(doc.get("facets"), "facets", 16)
    text_list(doc.get("example_queries", []), "example_queries", 12)
    if doc.get("numbering") not in {"stable_top_level", "preserve", "none"}:
        raise ValueError("Invalid numbering preference")
    branches = doc.get("branches", [])
    if not isinstance(branches, list) or len(branches) > 100:
        raise ValueError("Too many scenario branches")
    paths = set()
    for branch in branches:
        if not isinstance(branch, dict) or set(branch) != {"path", "dimension", "definition"}:
            raise ValueError("Branch requires path/dimension/definition")
        api.relative(root, branch["path"], destination=True)
        bounded(branch["dimension"], "branch dimension")
        bounded(branch["definition"], "branch definition")
        if norm(branch["path"]) in paths:
            raise ValueError("Duplicate scenario branch")
        paths.add(norm(branch["path"]))
    return copy.deepcopy(doc)


def validate_vocabulary(doc):
    if not isinstance(doc, dict) or set(doc) != {"version", "terms"}:
        raise ValueError("Vocabulary requires version and terms only")
    bounded(doc.get("version"), "version", 80)
    if not isinstance(doc["terms"], list) or len(doc["terms"]) > 2000:
        raise ValueError("Vocabulary exceeds 2000 terms")
    keys, labels, entries = {}, {}, []
    fields = {"facet", "id", "label", "aliases", "definition", "broader", "related", "status", "replaced_by"}
    for raw in doc["terms"]:
        if not isinstance(raw, dict) or set(raw) != fields:
            raise ValueError("Term requires facet/id/label/aliases/definition/broader/related/status/replaced_by")
        item = copy.deepcopy(raw)
        for f in ("facet", "id", "label"):
            bounded(item[f], f, 120)
            if item[f] != item[f].strip():
                raise ValueError("Term identity/label cannot have surrounding whitespace")
        bounded(item["definition"], "definition", 2000)
        for f in ("aliases", "broader", "related"):
            text_list(item[f], f, 32)
        if item["status"] not in {"active", "deprecated"}:
            raise ValueError("Invalid term status")
        if item["replaced_by"] is not None:
            bounded(item["replaced_by"], "replaced_by", 120)
            if item["status"] != "deprecated":
                raise ValueError("Only deprecated terms may redirect")
        key = (item["facet"], item["id"])
        if key in keys:
            raise ValueError("Duplicate term ID in facet")
        keys[key] = item
        entries.append(item)
        for label in [item["id"], item["label"], *item["aliases"]]:
            lookup = (item["facet"], norm(label))
            if lookup in labels and labels[lookup] != key:
                raise ValueError("Ambiguous ID/label/alias within facet: " + label)
            labels[lookup] = key
        if norm(item["label"]) in {norm(a) for a in item["aliases"]}:
            raise ValueError("Preferred label cannot also be an alias")
    for key, item in keys.items():
        refs = [*item["broader"], *item["related"], *([item["replaced_by"]] if item["replaced_by"] else [])]
        for ref in refs:
            if (key[0], ref) not in keys or ref == key[1]:
                raise ValueError("Missing/self/cross-facet term relation")
        if set(item["broader"]) & set(item["related"]):
            raise ValueError("Broader and related cannot name the same concept")
    for relation in ("broader", "replaced_by"):
        visiting, done = set(), set()
        def visit(key, depth=0):
            if depth > 64: raise ValueError("Term relationship depth exceeds 64")
            if key in visiting: raise ValueError("Cyclic " + relation)
            if key in done: return
            visiting.add(key)
            refs = keys[key][relation]
            if relation == "replaced_by": refs = [refs] if refs else []
            for ref in refs: visit((key[0], ref), depth + 1)
            visiting.remove(key)
            done.add(key)
        for key in keys: visit(key)
    # Keep associative relations apart from the whole broader chain.
    for key, item in keys.items():
        ancestors, todo = set(), list(item["broader"])
        while todo:
            ref = todo.pop()
            if ref not in ancestors:
                ancestors.add(ref)
                todo.extend(keys[(key[0], ref)]["broader"])
        if ancestors & set(item["related"]):
            raise ValueError("A related concept is also an ancestor")
        if item["replaced_by"] and terminal(keys, key)["status"] != "active":
            raise ValueError("Replacement chain must end at an active term")
    return {"version": doc["version"], "terms": sorted(entries, key=lambda t: (t["facet"], t["id"]))}


def terminal(keys, key):
    seen = set()
    item = keys[key]
    while item.get("replaced_by"):
        if key in seen: raise ValueError("Cyclic replacement")
        seen.add(key)
        key = (key[0], item["replaced_by"])
        item = keys[key]
    return item


def resolve(doc, value, facet=None):
    keys = {(t["facet"], t["id"]): t for t in doc["terms"]}
    candidates = {}
    for key, term in keys.items():
        if facet and term["facet"] != facet: continue
        if norm(value) in {norm(s) for s in [term["id"], term["label"], *term.get("aliases", [])]}:
            target = terminal(keys, key)
            candidates[(target["facet"], target["id"])] = {"facet": target["facet"], "id": target["id"],
                "label": target["label"], "status": target.get("status", "active")}
    return {"input": value, "facet": facet, "matches": list(candidates.values()), "ambiguous": len(candidates) > 1, "writes": False}


def projected_tags(doc, tags):
    keys = {(t["facet"], t["id"]): t for t in doc["terms"]}
    output, seen = [], set()
    for raw in tags:
        key = (raw["facet"], raw["id"])
        item = keys.get(key)
        projected = dict(raw)
        if item:
            target = terminal(keys, key)
            projected.update({"facet": target["facet"], "id": target["id"], "label": target["label"],
                "aliases": list(target.get("aliases", [])), "definition": target.get("definition", ""), "term_status": target.get("status", "active")})
            if target["id"] != raw["id"]: projected["original_tag_id"] = raw["id"]
        pkey = (projected["facet"], projected["id"])
        if pkey not in seen:
            output.append(projected)
            seen.add(pkey)
    return output


def binding_tags(con, tags):
    governed = stored(con, "vocabulary")
    if not governed: return tags  # Compatible legacy annotation until policy is activated.
    doc = governed["document"]
    keys = {(t["facet"], t["id"]): t for t in doc["terms"]}
    for raw in tags:
        term = keys.get((raw["facet"], raw["id"]))
        if not term or term["status"] != "active":
            raise ValueError("Unknown/deprecated vocabulary term; propose vocabulary update first")
        if raw["label"] != term["label"] or any(norm(a) not in set(map(norm, term["aliases"])) for a in raw.get("aliases", [])):
            raise ValueError("Annotation cannot change public vocabulary labels/aliases")
    return projected_tags(doc, tags)


def get(api, root, include_vocabulary=False):
    with contextlib.closing(api.connect(root)) as con:
        scenario = stored(con, "scenario")
        vocab = stored(con, "vocabulary")
        doc = vocabulary(con)
        return {"writes": False, "scope": "personal", "scenario": scenario,
            "default_scenario_candidate": template()["scenario"] if not scenario else None,
            "vocabulary": {"revision": vocab["revision"] if vocab else "none", "source": "governed" if vocab else "legacy",
                           "version": doc["version"], "term_count": len(doc["terms"]),
                           "document": doc if include_vocabulary else None}, "default_is_not_authorization": True}


def impacts(con, kind, old, new):
    rows = [dict(r) for r in con.execute("SELECT id,path,profile,location_locked FROM files WHERE state='active' ORDER BY path")]
    affected, review = [], []
    if kind == "scenario":
        meaning = ("purpose", "primary_dimension", "branches")
        changed = bool((old and any(old.get(k) != new.get(k) for k in meaning)) or (not old and new["primary_dimension"] != "preserve_existing"))
        affected = rows if changed else []
        review = [r for r in affected if r["profile"]]
        return affected, review, {"classification_rule_changed": changed}
    before = {(t["facet"], t["id"]): t for t in (old or {"terms": []})["terms"]}
    after = {(t["facet"], t["id"]): t for t in new["terms"]}
    removed = set(before) - set(after)
    if removed:
        raise ValueError("Retain old IDs as deprecated terms; do not remove historical vocabulary concepts")
    changed = {k for k in before if before[k] != after[k]}
    semantic_fields = ("definition", "status", "replaced_by", "broader", "related")
    semantic = {k for k in changed if any(before[k].get(f) != after[k].get(f) for f in semantic_fields)}
    used = set()
    for row in rows:
        tags = json.loads(row["profile"]).get("tags", []) if row["profile"] else []
        keys = {(t["facet"], t["id"]) for t in tags}
        used.update(keys)
        if keys & changed: affected.append(row)
        if keys & semantic: review.append(row)
    if used - set(after):
        raise ValueError("Vocabulary omits existing file tags; include them or migrate explicitly")
    return affected, review, {"added_terms": [list(k) for k in sorted(set(after) - set(before))],
        "changed_terms": [list(k) for k in sorted(changed)], "meaning_changed_terms": [list(k) for k in sorted(semantic)]}


def apply_policy(api, root, kind, document, reason="", execute=False, expected_revision=None):
    new = validate_scenario(api, root, document) if kind == "scenario" else validate_vocabulary(document)
    if execute: bounded(reason, "change reason", 1000)
    con = api.connect(root, write=execute)
    with contextlib.closing(con), api.lock(root) if execute else contextlib.nullcontext():
        current = stored(con, kind)
        revision = current["revision"] if current else "none"
        old = current["document"] if current else vocabulary(con) if kind == "vocabulary" else None
        if execute and expected_revision != revision:
            raise ValueError("Policy revision changed/missing; preview and provide --expected-revision")
        if current and old != new and old["version"] == new["version"]:
            raise ValueError("Policy changes require a new version")
        affected, review, details = impacts(con, kind, old, new)
        result = {"writes": False, "kind": kind, "current_revision": revision,
            "current_version": old.get("version") if old else None, "proposed_version": new["version"],
            "affected_count": len(affected), "review_count": len(review), "affected_locked_count": sum(r["location_locked"] for r in affected),
            "affected_files": [{"file_id": r["id"], "path": r["path"], "location_locked": bool(r["location_locked"])} for r in affected[:100]],
            "affected_files_truncated": len(affected) > 100, "user_files_changed": 0, **details}
        if not execute: return result
        if current and new == old:
            return {**result, "unchanged": True}
        con.execute("CREATE TABLE IF NOT EXISTS policy_history(revision TEXT PRIMARY KEY,kind TEXT NOT NULL,document_json TEXT NOT NULL,reason TEXT NOT NULL,recorded_at TEXT NOT NULL)")
        if not current and old:
            con.execute("INSERT INTO policy_history VALUES(?,?,?,?,?)", (str(uuid.uuid4()), kind, json.dumps(old, ensure_ascii=False), "legacy baseline", api.now()))
        new_revision = str(uuid.uuid4())
        envelope = {"revision": new_revision, "document": new, "reason": reason, "updated_at": api.now()}
        api.meta_set(con, "policy_" + kind, json.dumps(envelope, ensure_ascii=False))
        con.execute("INSERT INTO policy_history VALUES(?,?,?,?,?)", (new_revision, kind, json.dumps(new, ensure_ascii=False), reason, envelope["updated_at"]))
        if kind == "vocabulary":
            for t in new["terms"]:
                con.execute("INSERT INTO tag_vocabulary VALUES(?,?,?,?) ON CONFLICT(facet,tag_id) DO UPDATE SET label=excluded.label,aliases_json=excluded.aliases_json",
                    (t["facet"], t["id"], t["label"], json.dumps(t["aliases"], ensure_ascii=False)))
        for row in review:
            profile = json.loads(row["profile"])
            field = "scenario_review_required" if kind == "scenario" else "vocabulary_review_required"
            profile[field] = True
            if kind == "scenario":
                profile["classification_status"] = "review"
                profile["review_reason"] = "scenario policy changed"
            con.execute("UPDATE files SET profile=? WHERE id=?", (json.dumps(profile, ensure_ascii=False), row["id"]))
            api.set_issue(con, row["id"], row["path"], "classification_review" if kind == "scenario" else "vocabulary_review", "open", {"policy_revision": new_revision})
            api.record_file_event(con, row["id"], kind + "_review_required", None, row["path"], profile, {"policy_revision": new_revision})
        api.meta_set(con, "catalog_revision", str(uuid.uuid4()))
        con.commit()
        return {**result, "writes": True, "revision": new_revision, "index_required": True}


def history(api, root, kind=None, revision=None, offset=0, limit=20):
    if offset < 0 or not 1 <= limit <= 100: raise ValueError("Invalid pagination")
    with contextlib.closing(api.connect(root)) as con:
        if not api.table_exists(con, "policy_history"):
            return {"writes": False, "entries": [], "total": 0, "next_offset": None}
        clauses, values = [], []
        if kind: clauses.append("kind=?"); values.append(kind)
        if revision: clauses.append("revision=?"); values.append(revision)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        total = con.execute("SELECT count(*) FROM policy_history" + where, values).fetchone()[0]
        rows = con.execute("SELECT * FROM policy_history" + where + " ORDER BY recorded_at DESC,revision LIMIT ? OFFSET ?", (*values, limit, offset)).fetchall()
        entries = [{"revision": r["revision"], "kind": r["kind"], "reason": r["reason"], "recorded_at": r["recorded_at"],
            "version": json.loads(r["document_json"])["version"], **({"document": json.loads(r["document_json"])} if revision else {})} for r in rows]
        return {"writes": False, "entries": entries, "total": total, "next_offset": offset + len(rows) if offset + len(rows) < total else None}


def list_terms(api, root, facet=None, offset=0, limit=100, term=None):
    if offset < 0 or not 1 <= limit <= 100: raise ValueError("Invalid pagination")
    with contextlib.closing(api.connect(root)) as con:
        doc = vocabulary(con)
        if term is not None: return {**resolve(doc, term, facet), "version": doc["version"]}
        terms = [t for t in doc["terms"] if not facet or t["facet"] == facet]
        return {"writes": False, "version": doc["version"], "terms": terms[offset:offset+limit], "total": len(terms),
            "next_offset": offset + limit if offset + limit < len(terms) else None}
