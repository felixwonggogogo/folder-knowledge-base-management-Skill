#!/usr/bin/env python3
"""Policy, controlled vocabulary and retrieval checks in synthetic roots."""
import contextlib
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import folderdb as db
import folderdb_policy as p


class PolicyChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="folderdb-policy-")
        self.root = Path(self.temp.name).resolve()
        (self.root / "sample.txt").write_text("独立样本正文", encoding="utf-8")
        db.scan(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def term(self, facet="topic", id="ai", label="人工智能", aliases=None):
        return {"facet": facet, "id": id, "label": label, "aliases": aliases or [], "definition": "合成测试概念", "broader": [], "related": [], "status": "active", "replaced_by": None}

    def vocab(self, *terms, version="1"):
        return {"version": version, "terms": list(terms or [self.term()])}

    def activate(self, doc=None):
        return p.apply_policy(db, self.root, "vocabulary", doc or self.vocab(), "synthetic authorization", True, "none")

    def annotate(self, tags=None, revisions=True):
        row = db.dump(self.root)["files"][0]
        doc = {"taxonomy": {"version": "1", "categories": [{"id": "sample", "label": "样本", "path": "样本", "definition": "合成资料"}]},
            "files": [{"file_id": row["id"], "source_sha256": row["sha256"], "title": "样本", "summary": "独立样本正文",
                "category_id": "sample", "classification_status": "confident", "classification_basis": ["content"], "semantic_status": "reviewed",
                "tags": tags or [{"facet": "topic", "id": "ai", "label": "人工智能"}], "read_coverage": "全文",
                "evidence": [{"field": "category_id", "locator": "text:line-1", "basis": "合成授权分类"}]}]}
        if revisions: doc["policy_revisions"] = db.status(self.root)["policy_revisions"]
        return db.annotate(self.root, doc)

    def test_presets_read_only_and_personal_scope(self):
        untouched = self.root / "untouched"
        untouched.mkdir()
        cli = [sys.executable, "-B", str(Path(db.__file__)), "policy-template", "--root", str(untouched)]
        result = json.loads(subprocess.check_output(cli, encoding="utf-8"))
        self.assertFalse(result["authorization_granted"])
        self.assertFalse((untouched / ".filedb").exists())
        for preset in ("general", "work", "research", "learning", "personal", "custom"):
            t = p.template(preset)
            p.validate_scenario(db, self.root, t["scenario"])
            p.validate_vocabulary(t["vocabulary"])
        self.assertTrue(p.template()["scenario"]["preserve_existing"])

    def test_get_and_preview_do_not_modify_database(self):
        path = self.root / ".filedb/catalog.sqlite"
        before = db.digest(path)
        self.assertIsNone(p.get(db, self.root)["scenario"])
        self.assertFalse(p.apply_policy(db, self.root, "scenario", p.template()["scenario"])["writes"])
        self.assertFalse(p.apply_policy(db, self.root, "vocabulary", self.vocab())["writes"])
        self.assertEqual(db.digest(path), before)
        self.assertFalse((self.root / ".filedb/LOCK").exists())

    def test_expected_revision_and_version_required(self):
        first = self.activate()
        new = self.vocab(self.term(aliases=["AI"]), version="2")
        with self.assertRaises(ValueError): p.apply_policy(db, self.root, "vocabulary", new, "reason", True, "none")
        new["version"] = "1"
        with self.assertRaises(ValueError): p.apply_policy(db, self.root, "vocabulary", new, "reason", True, first["revision"])

    def test_alias_update_matches_old_files_without_reannotation(self):
        first = self.activate()
        self.annotate()
        original = db.dump(self.root)["files"][0]["profile"]
        new = self.vocab(self.term(aliases=["AI", "artificial intelligence"]), version="2")
        applied = p.apply_policy(db, self.root, "vocabulary", new, "add aliases", True, first["revision"])
        self.assertEqual(applied["review_count"], 0)
        self.assertEqual(db.search(self.root, "", tag="ＡＩ", tag_facet="topic")["total"], 1)
        self.assertEqual(db.search(self.root, "artificial")["total"], 1)
        by_keyword = db.search(self.root, "AI")
        self.assertEqual(by_keyword["total"], 1)
        self.assertEqual(by_keyword["query_expansions"][0]["matches"][0]["id"], "ai")
        self.assertEqual(db.dump(self.root)["files"][0]["profile"], original)
        self.assertIn("AI", db.dump(self.root)["files"][0]["effective_tags"][0]["aliases"])

    def test_annotation_cannot_overwrite_vocabulary(self):
        self.activate()
        with self.assertRaises(ValueError): self.annotate([{"facet": "topic", "id": "ai", "label": "改名"}])
        with self.assertRaises(ValueError): self.annotate([{"facet": "topic", "id": "new", "label": "新概念"}])
        with self.assertRaises(ValueError): self.annotate(revisions=False)
        self.assertEqual(p.get(db, self.root, True)["vocabulary"]["document"]["terms"][0]["label"], "人工智能")

    def test_cross_facet_ambiguity_requires_filter(self):
        self.activate(self.vocab(self.term(aliases=["AI"]), self.term("project", "ai", "AI")))
        self.annotate()
        with self.assertRaises(ValueError): db.search(self.root, "", tag="AI")
        self.assertEqual(db.search(self.root, "", tag="AI", tag_facet="topic")["total"], 1)
        self.assertTrue(p.list_terms(db, self.root, term="AI")["ambiguous"])

    def test_same_facet_collision_rejected(self):
        with self.assertRaises(ValueError): p.validate_vocabulary(self.vocab(self.term(aliases=["AI"]), self.term(id="other", label="其他", aliases=["ＡＩ"])))

    def test_cycles_invalid_relations_and_depth_rejected(self):
        a, b = self.term(id="a", label="甲"), self.term(id="b", label="乙")
        a["broader"], b["broader"] = ["b"], ["a"]
        with self.assertRaises(ValueError): p.validate_vocabulary(self.vocab(a, b))
        a["broader"], b["broader"] = ["absent"], []
        with self.assertRaises(ValueError): p.validate_vocabulary(self.vocab(a, b))
        chain = [self.term(id=f"t{i}", label=f"词{i}") for i in range(67)]
        for i in range(66): chain[i]["broader"] = [f"t{i+1}"]
        with self.assertRaises(ValueError): p.validate_vocabulary(self.vocab(*chain))

    def test_deprecation_redirect_and_review_queue(self):
        first = self.activate()
        self.annotate()
        old, new = self.term(), self.term(id="ai-new", label="智能技术")
        old["status"], old["replaced_by"] = "deprecated", "ai-new"
        doc = self.vocab(old, new, version="2")
        result = p.apply_policy(db, self.root, "vocabulary", doc, "confirmed merge", True, first["revision"])
        self.assertEqual(result["review_count"], 1)
        hit = db.search(self.root, "", tag="人工智能")["results"][0]
        self.assertEqual(hit["tags"][0]["id"], "ai-new")
        self.assertTrue(hit["vocabulary_review_required"])
        self.assertEqual(db.pending(self.root, "vocabulary_review")["total"], 1)
        self.annotate([{"facet": "topic", "id": "ai-new", "label": "智能技术"}])
        self.assertEqual(db.status(self.root)["vocabulary_review_required"], 0)

    def test_removed_ids_and_missing_existing_tags_rejected(self):
        self.annotate()
        with self.assertRaises(ValueError): self.activate(self.vocab(self.term(id="other", label="其他")))
        self.activate()
        current = p.get(db, self.root)["vocabulary"]
        with self.assertRaises(ValueError): p.apply_policy(db, self.root, "vocabulary", {"version": "2", "terms": []})

    def test_history_pagination_and_restore_through_new_version(self):
        first = self.activate()
        second = p.apply_policy(db, self.root, "vocabulary", self.vocab(self.term(aliases=["AI"]), version="2"), "alias", True, first["revision"])
        entries = p.history(db, self.root, "vocabulary", limit=1)
        self.assertIsNotNone(entries["next_offset"])
        previous = p.history(db, self.root, revision=first["revision"])["entries"][0]["document"]
        previous["version"] = "3"
        self.assertTrue(p.apply_policy(db, self.root, "vocabulary", previous, "restore old policy", True, second["revision"])["writes"])

    def test_scenario_change_preserves_source_and_locked_location(self):
        self.annotate()
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET location_locked=1")
            con.commit()
        general = p.apply_policy(db, self.root, "scenario", p.template()["scenario"], "default chosen", True, "none")
        original = db.digest(self.root / "sample.txt")
        scene = p.template("work")["scenario"]
        scene["version"] = "2"
        change = p.apply_policy(db, self.root, "scenario", scene, "user changed purpose", True, general["revision"])
        self.assertEqual(change["review_count"], 1)
        self.assertEqual(change["affected_locked_count"], 1)
        self.assertEqual(change["user_files_changed"], 0)
        self.assertEqual(db.digest(self.root / "sample.txt"), original)
        self.assertTrue(db.dump(self.root)["files"][0]["location_locked"])

    def test_document_type_format_and_saved_view(self):
        self.activate(self.vocab(self.term("document_type", "report", "报告", ["调研报告"])))
        self.annotate([{"facet": "document_type", "id": "report", "label": "报告"}])
        self.assertEqual(db.search(self.root, "", document_type="调研报告")["total"], 1)
        self.assertEqual(db.search(self.root, "", file_format="txt")["total"], 1)
        db.save_view(self.root, "reports", {"tag": "报告", "tag_facet": "document_type", "file_format": "txt"})
        self.assertEqual(db.query_view(self.root, "reports")["total"], 1)

    def test_legacy_alias_union_and_no_read_time_migration(self):
        self.annotate([{"facet": "topic", "id": "ai", "label": "人工智能", "aliases": ["AI"]}])
        self.annotate()
        legacy = p.get(db, self.root, True)
        self.assertEqual(legacy["vocabulary"]["source"], "legacy")
        self.assertIn("AI", legacy["vocabulary"]["document"]["terms"][0]["aliases"])
        self.assertEqual(p.history(db, self.root)["total"], 0)
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertFalse(db.table_exists(con, "policy_history"))

    def test_template_and_apply_cli(self):
        doc = self.root / ".filedb/scenario-input.json"
        doc.write_text(json.dumps(p.template()["scenario"], ensure_ascii=False), encoding="utf-8")
        cli = [sys.executable, "-B", str(Path(db.__file__)), "scenario-apply", "--root", str(self.root), "--input", str(doc), "--reason", "synthetic"]
        self.assertFalse(json.loads(subprocess.check_output(cli, encoding="utf-8"))["writes"])
        applied = json.loads(subprocess.check_output([*cli, "--expected-revision", "none", "--execute"], encoding="utf-8"))
        self.assertTrue(applied["writes"])
        self.assertEqual(p.get(db, self.root)["scenario"]["revision"], applied["revision"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
