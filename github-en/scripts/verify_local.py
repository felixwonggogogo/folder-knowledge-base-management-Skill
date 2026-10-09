#!/usr/bin/env python3
"""Behavioral checks in disposable synthetic directories only."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import zipfile

import folderdb as db
import folderdb_watch as watch


class FolderDBChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="folderdb-check-")
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def row(self, path):
        with contextlib.closing(db.connect(self.root)) as con:
            return dict(con.execute("SELECT * FROM files WHERE path=?", (path,)).fetchone())

    def profile(self, path):
        row = self.row(path)
        return {"taxonomy": {"version": "1", "categories": [{"id": "budget", "label": "预算", "path": "项目A/预算", "definition": "项目A预算资料"}]},
                "files": [{"file_id": row["id"], "source_sha256": row["sha256"], "title": "预算资料", "summary": "项目A采购预算。", "category_id": "budget", "classification_status": "confident", "classification_basis": ["content"], "semantic_status": "reviewed", "tags": [{"facet": "topic", "id": "budget", "label": "预算"}], "read_coverage": "完整合成文本", "evidence": [{"field": "category_id", "locator": "text:line-1", "basis": "正文明确属于项目A预算"}, {"field": "topic", "locator": "text:line-1", "basis": "原文为预算"}]}]}

    def test_unannotated_and_inherited_files_count_as_unfinished(self):
        self.write("待识别.txt", "未知项目资料")
        self.write("预算.txt", "项目A采购预算")
        db.scan(self.root)
        before = db.status(self.root)
        self.assertEqual(before["classification_record_missing"], 2)
        self.assertEqual(before["classification_review_required"], 2)
        self.assertEqual(before["semantic_counts"]["unreviewed"], 2)
        self.assertEqual(before["semantic_review_required"], 2)
        db.annotate(self.root, self.profile("预算.txt"))
        after = db.status(self.root)
        self.assertEqual(after["classification_review_required"], 1)
        self.assertEqual(after["semantic_review_required"], 1)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET profile=? WHERE path='待识别.txt'", (json.dumps({"classification_status": "inherited", "semantic_status": "unavailable"}),))
            con.commit()
        inherited = db.status(self.root)
        self.assertEqual(inherited["classification_record_missing"], 0)
        self.assertEqual(inherited["classification_review_required"], 1)
        self.assertEqual(inherited["semantic_review_required"], 1)

    def test_navigate_exact_level_empty_directories_and_two_pagination_streams(self):
        self.write("10-项目/a.txt", "A")
        self.write("10-项目/b.txt", "B")
        self.write("10-项目/客户A/方案.txt", "C")
        self.write("10-项目延伸/其他.txt", "D")
        (self.root / "10-项目/客户B").mkdir()
        db.scan(self.root)
        node = db.navigate(self.root, "10-项目", limit=1)
        self.assertEqual(node["folder"]["direct_files"], 2)
        self.assertEqual(node["folder"]["subtree_files"], 3)
        self.assertEqual(node["children_total"], 2)
        self.assertEqual(node["files_total"], 2)
        self.assertEqual(node["children_next_offset"], 1)
        self.assertEqual(node["files_next_offset"], 1)
        next_page = db.navigate(self.root, "10-项目", 1, 1, 1)
        self.assertEqual(next_page["children"][0]["path"], "10-项目/客户B")
        self.assertEqual(next_page["children"][0]["subtree_files"], 0)
        self.assertEqual(next_page["files"][0]["path"], "10-项目/b.txt")
        self.assertEqual([n["path"] for n in db.navigate(self.root, "10-项目/客户A")["breadcrumbs"]], ["", "10-项目", "10-项目/客户A"])
        self.assertIsNone(node["folder"]["index_page"])
        self.assertFalse(node["writes"])
        for invalid in ("../outside", ".filedb", "10-项目/missing"):
            with self.assertRaises(ValueError): db.navigate(self.root, invalid)

    def test_directory_plan_cli_preview_save_execute_and_identity_lookup(self):
        self.write("原目录/合同.txt", "合同正文")
        db.scan(self.root)
        old_id = self.row("原目录/合同.txt")["id"]
        cli = [sys.executable, "-B", str(Path(db.__file__)), "directory-plan", "--root", str(self.root),
            "--src", "原目录", "--dst", "10-项目/合同", "--reason", "合成授权：归入合同分支"]
        preview = json.loads(subprocess.check_output(cli, text=True, encoding="utf-8"))
        self.assertFalse(preview["writes"])
        self.assertFalse((self.root / ".filedb/plans").exists())
        saved = json.loads(subprocess.check_output([*cli, "--save-as", "directory-001.json"], text=True, encoding="utf-8"))
        plan_file = Path(saved["plan_path"])
        self.assertEqual(plan_file.parent, self.root / ".filedb/plans")
        self.assertEqual(saved["user_files_changed"], 0)
        with self.assertRaises(FileExistsError):
            db.make_directory_plan(self.root, "原目录", "10-项目/合同", "synthetic", "directory-001.json")
        with self.assertRaises(ValueError):
            db.make_directory_plan(self.root, "原目录", "10-项目/合同", "synthetic", "../outside.json")
        plan = json.loads(plan_file.read_text(encoding="utf-8"))
        run = db.apply_directory_plan(self.root, plan, True)
        self.assertEqual(run["status"], "completed")
        found = db.navigate(self.root, "10-项目/合同")["files"][0]
        self.assertEqual(found["file_id"], old_id)
        self.assertTrue(db.dump(self.root, old_id)["files"][0]["source_fresh"])
        self.assertEqual(db.rollback(self.root, run["run_id"], True)["status"], "rolled_back")

    def test_directory_plan_refuses_stale_source_and_protected_trees(self):
        source = self.write("原目录/a.txt", "stable")
        db.scan(self.root)
        plan = db.make_directory_plan(self.root, "原目录", "10-目录", "synthetic")["plan"]
        source.write_text("changed", encoding="utf-8")
        with self.assertRaises(ValueError): db.check_directory_plan(self.root, plan)
        with self.assertRaises(ValueError): db.make_directory_plan(self.root, "原目录", "10-目录", "synthetic")
        db.scan(self.root)
        (self.root / "原目录/.private").mkdir()
        with self.assertRaises(ValueError): db.make_directory_plan(self.root, "原目录", "10-目录", "synthetic")

    def test_directory_dependency_probe_reports_inbound_encoded_links(self):
        from urllib.parse import quote
        self.write("原项目/a.txt", "plain content without self references")
        self.write("引用.md", "[合同](" + quote("原项目/a.txt", safe="/") + ")")
        db.scan(self.root)
        result = db.make_directory_plan(self.root, "原项目", "10-项目", "synthetic")
        preview = result["preview"]
        self.assertTrue(preview["warnings_require_agent_review"])
        risks = preview["preview"][0]["dependency_risks"]
        self.assertEqual(risks["inbound_path_references"], ["引用.md"])
        self.assertEqual(risks["text_path_references"], [])
        self.assertIn("not proven absent", risks["limitation"])

    def test_directory_plan_respects_manual_location_locks(self):
        self.write("原目录/a.txt", "stable")
        db.scan(self.root)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET location_locked=1")
            con.commit()
        with self.assertRaises(ValueError): db.make_directory_plan(self.root, "原目录", "10-目录", "synthetic")
        checked = db.make_directory_plan(self.root, "原目录", "10-目录", "synthetic explicit locked scope", include_locked=True)
        self.assertEqual(checked["preview"]["preview"][0]["locked_files"], 1)

    def test_generated_navigation_parent_links_and_unreviewed_summary(self):
        self.write("10-项目/客户A/合同.txt", "UNIQUE_SOURCE_BODY_NOT_EXPORTED")
        db.scan(self.root)
        db.build_index(self.root)
        page = db.navigate(self.root, "10-项目/客户A")["folder"]["index_page"]
        self.assertIsNotNone(page)
        text = (self.root / page).read_text(encoding="utf-8")
        self.assertIn("Parent folder", text)
        self.assertIn("Root index", text)
        self.assertIn("classification review: 1", (self.root / "AI_INDEX.md").read_text(encoding="utf-8"))
        readme = (self.root / "AI_README.md").read_text(encoding="utf-8")
        self.assertIn("children_next_offset", readme)
        self.assertIn("navigate", readme)
        portal = (self.root / "file-knowledge-base.html").read_text(encoding="utf-8")
        payload = json.loads(portal.split('<script id="kb-data" type="application/json">', 1)[1].split('</script>', 1)[0])
        self.assertEqual(payload["stats"]["semantic_review_required"], 1)
        self.assertEqual(next(n for n in payload["directories"] if n["path"] == "10-项目")["subtree_files"], 1)
        self.assertNotIn("UNIQUE_SOURCE_BODY_NOT_EXPORTED", portal)

    def test_lifecycle_preview_current_group_and_archived_retrieval(self):
        self.write("合同_v1.txt", "v1合同")
        self.write("合同_v2.txt", "v2合同")
        db.scan(self.root)
        a, b = self.row("合同_v1.txt"), self.row("合同_v2.txt")
        before = db.digest(self.root / ".filedb/catalog.sqlite")
        preview = db.manage_lifecycle(self.root, a["id"], "synthetic user designation", "active", "contract", "v1", True, "2026-12-01")
        self.assertFalse(preview["writes"])
        self.assertEqual(before, db.digest(self.root / ".filedb/catalog.sqlite"))
        db.manage_lifecycle(self.root, a["id"], "synthetic", "active", "contract", "v1", True, "2026-12-01", True)
        db.manage_lifecycle(self.root, b["id"], "synthetic user chooses v2", "active", "contract", "v2", True, execute=True)
        selected = db.list_lifecycle(self.root, version_group="contract", current_only=True)
        self.assertEqual(selected["total"], 1)
        self.assertEqual(selected["items"][0]["file_id"], b["id"])
        db.manage_lifecycle(self.root, a["id"], "synthetic archive", "archived", execute=True)
        archived = db.search(self.root, "", business_state="archived")
        self.assertEqual(archived["results"][0]["file_id"], a["id"])
        db.save_view(self.root, "业务归档", {"business_state": "archived"})
        self.assertEqual(db.query_view(self.root, "业务归档")["total"], 1)
        self.assertTrue((self.root / "合同_v1.txt").is_file())
        self.assertEqual(db.list_lifecycle(self.root, due_before="2026-12-01")["total"], 1)

    def test_content_version_change_invalidates_current_and_preserves_observed_history(self):
        source = self.write("预算.txt", "项目A预算v1")
        db.scan(self.root)
        db.annotate(self.root, self.profile("预算.txt"))
        row = self.row("预算.txt")
        db.manage_lifecycle(self.root, row["id"], "synthetic verified current", "active", "budget", "v1", True, execute=True)
        source.write_text("项目A预算v2", encoding="utf-8")
        stale = db.list_lifecycle(self.root, current_only=True)["items"][0]
        self.assertFalse(stale["source_fresh"])
        self.assertFalse(stale["is_current"])
        with self.assertRaises(ValueError): db.save_snapshot(self.root, row["id"], True)
        db.scan(self.root)
        changed = db.list_lifecycle(self.root)["items"][0]
        self.assertEqual(changed["business_state"], "in_review")
        self.assertIsNone(changed["version_label"])
        self.assertTrue(changed["needs_review"])
        self.assertEqual(db.status(self.root)["version_review_required"], 1)
        history = db.file_history(self.root, row["id"])
        self.assertIn("content_changed", [e["event_type"] for e in history["events"]])
        prior = [e for e in history["events"] if e["event_type"] == "previous_revision"][0]
        self.assertEqual(prior["sha256"], row["sha256"])
        self.assertEqual(prior["profile"]["semantic_status"], "reviewed")
        self.assertEqual(self.row("预算.txt")["id"], row["id"])
        self.assertEqual(history["snapshots"], [])

    def test_snapshot_and_restore_as_new_copy_preserve_original_and_hash(self):
        source = self.write("合同.txt", "version one")
        db.scan(self.root)
        row = self.row("合同.txt")
        preview = db.save_snapshot(self.root, row["id"])
        self.assertFalse((self.root / preview["snapshot_path"]).exists())
        saved = db.save_snapshot(self.root, row["id"], True)
        self.assertFalse(saved["independent_backup"])
        self.assertEqual(db.digest(self.root / saved["snapshot_path"]), row["sha256"])
        db.save_snapshot(self.root, row["id"], True)
        self.assertEqual(len(db.file_history(self.root, row["id"])["snapshots"]), 1)
        source.write_text("version two", encoding="utf-8")
        db.scan(self.root)
        restored = db.restore_snapshot_copy(self.root, row["id"], row["sha256"], "恢复资料/合同_v1.txt", True)
        self.assertEqual(restored["overwritten_files"], 0)
        self.assertEqual(source.read_text(encoding="utf-8"), "version two")
        self.assertEqual((self.root / "恢复资料/合同_v1.txt").read_text(encoding="utf-8"), "version one")
        with self.assertRaises(ValueError): db.restore_snapshot_copy(self.root, row["id"], row["sha256"], "合同.txt", True)
        db.refresh(self.root)
        self.assertNotEqual(self.row("恢复资料/合同_v1.txt")["id"], row["id"])
        self.assertFalse(any(".filedb/versions" in p["path"] for p in db.dump(self.root)["files"]))

    def test_snapshot_restore_rejects_tampered_bytes_and_never_deletes_racing_target(self):
        self.write("合同.txt", "original bytes")
        db.scan(self.root)
        row = self.row("合同.txt")
        saved = db.save_snapshot(self.root, row["id"], True)
        destination = self.root / "新副本.txt"
        original_open = Path.open
        def race(path, *args, **kwargs):
            if path == destination and args and args[0] == "xb":
                with original_open(path, "w", encoding="utf-8") as stream: stream.write("user racing content")
                raise FileExistsError("synthetic concurrent user creation")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", race):
            with self.assertRaises(FileExistsError): db.restore_snapshot_copy(self.root, row["id"], row["sha256"], "新副本.txt", True)
        self.assertEqual(destination.read_text(encoding="utf-8"), "user racing content")
        (self.root / saved["snapshot_path"]).write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError): db.restore_snapshot_copy(self.root, row["id"], row["sha256"], "另一个副本.txt", True)
        self.assertFalse((self.root / "另一个副本.txt").exists())

    def test_legacy_schema2_history_read_is_zero_write_and_extension_is_opt_in(self):
        self.write("a.txt", "source")
        db.scan(self.root)
        row = self.row("a.txt")
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            for table in ("file_events", "file_management", "file_snapshots"): con.execute("DROP TABLE " + table)
            con.commit()
        before = db.digest(self.root / ".filedb/catalog.sqlite")
        self.assertEqual(db.file_history(self.root, row["id"])["events"], [])
        self.assertEqual(db.list_lifecycle(self.root)["total"], 1)
        self.assertEqual(db.status(self.root)["lifecycle_counts"]["unknown"], 1)
        self.assertEqual(before, db.digest(self.root / ".filedb/catalog.sqlite"))
        db.scan(self.root)
        self.assertEqual(db.file_history(self.root, row["id"])["events"][0]["event_type"], "tracking_baseline")

    def test_lifecycle_validation_and_cli_preview_are_non_destructive(self):
        self.write("a.txt", "source")
        db.scan(self.root)
        row = self.row("a.txt")
        with self.assertRaises(ValueError): db.manage_lifecycle(self.root, row["id"], "synthetic", "archived", "group", current=True, execute=True)
        with self.assertRaises(ValueError): db.manage_lifecycle(self.root, row["id"], "synthetic", "active", review_on="2026-02-30")
        cli = [sys.executable, "-B", str(Path(db.__file__)), "lifecycle", "--root", str(self.root), "--file-id", row["id"], "--business-state", "draft", "--reason", "synthetic"]
        result = json.loads(subprocess.check_output(cli, text=True, encoding="utf-8"))
        self.assertFalse(result["writes"])
        self.assertEqual(result["after"]["business_state"], "draft")
        self.assertEqual(db.list_lifecycle(self.root)["items"][0]["business_state"], "unknown")

    def test_deduplication_preserves_confirmed_business_version_identities(self):
        self.write("A.txt", "same bytes")
        self.write("B.txt", "same bytes")
        db.scan(self.root)
        a, b = self.row("A.txt"), self.row("B.txt")
        db.manage_lifecycle(self.root, b["id"], "synthetic confirmed current", "active", "family", "v2", True, execute=True)
        plan = db.quarantine_plan(self.root)
        self.assertEqual(plan["operations"][0]["src"], "A.txt")
        self.assertEqual(plan["operations"][0]["keep"], "B.txt")
        db.manage_lifecycle(self.root, a["id"], "synthetic separately confirmed version", "archived", "family", "v1", execute=True)
        protected = db.quarantine_plan(self.root)
        self.assertEqual(protected["operations"], [])
        self.assertIn("confirmed-version", protected["skipped"][0]["reason"])

    def test_quarantine_plan_uses_all_groups_beyond_scan_report_preview(self):
        for i in range(105):
            self.write(f"group-{i:03d}-a.txt", f"group {i} equal bytes")
            self.write(f"group-{i:03d}-b.txt", f"group {i} equal bytes")
        report = db.scan(self.root)
        self.assertEqual(len(report["duplicate_groups"]), 100)
        self.assertEqual(db.quarantine_plan(self.root)["file_moves"], 105)

    def test_schema1_migration_preserves_ids_and_downgrades_path_only_confidence(self):
        self.write("A/预算.txt", "预算文本")
        self.write("unknown.bin", "opaque")
        db.scan(self.root)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            row = con.execute("SELECT * FROM files WHERE path='A/预算.txt'").fetchone()
            profile = {"file_id": row["id"], "source_sha256": row["sha256"], "title": "预算.txt", "summary": "按现有目录继承主类 A；未逐份做语义摘要。", "category_id": "budget", "classification_status": "confident", "taxonomy_version": "1", "tags": [{"facet": "topic", "id": "budget", "label": "预算"}], "evidence": [{"field": "category_id", "locator": "path:A/预算.txt", "basis": "分类沿用路径 A"}], "read_coverage": "AI未逐份阅读全文"}
            con.execute("UPDATE files SET profile=? WHERE id=?", (json.dumps(profile, ensure_ascii=False), row["id"]))
            con.execute("UPDATE meta SET value='1' WHERE key='schema'")
            con.commit()
            original_id = row["id"]
        self.assertEqual(db.identity(self.root)["kind"], "incompatible")
        preview = db.migrate(self.root)
        self.assertFalse(preview["writes"])
        migrated = db.migrate(self.root, execute=True)
        self.assertEqual(migrated["status"], "completed")
        self.assertEqual(db.identity(self.root)["kind"], "managed")
        row = self.row("A/预算.txt")
        profile = json.loads(row["profile"])
        self.assertEqual(row["id"], original_id)
        self.assertEqual(profile["classification_status"], "inherited")
        self.assertEqual(profile["classification_basis"], ["path"])
        self.assertEqual(profile["semantic_status"], "unreviewed")
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertTrue(con.execute("SELECT 1 FROM tag_vocabulary WHERE facet='topic' AND tag_id='budget'").fetchone())
            issue = con.execute("SELECT reason_code FROM issues WHERE file_id=(SELECT id FROM files WHERE path='unknown.bin') AND state='open' AND reason_code='unsupported_format'").fetchone()
            self.assertEqual(issue[0], "unsupported_format")
        self.assertTrue(Path(migrated["backup"]).is_file())

    def plan(self, src, dst):
        row = self.row(src)
        return {"version": 1, "root": str(self.root), "operations": [{"file_id": row["id"], "src": src, "dst": dst, "sha256": row["sha256"], "reason": "synthetic authorized move"}]}

    def test_identity_and_preflight_do_not_initialize(self):
        self.assertEqual(db.preflight(self.root)["library"]["kind"], "new")
        db.preflight(self.root, True)
        self.assertFalse((self.root / ".filedb").exists())
        self.assertEqual(list(self.root.iterdir()), [])
        db.scan(self.root)
        self.assertEqual(db.identity(self.root)["kind"], "managed")

    def test_content_change_invalidates_profile_and_index(self):
        self.write("a.txt", "项目A采购预算")
        db.scan(self.root)
        db.annotate(self.root, self.profile("a.txt"))
        db.build_index(self.root)
        self.assertFalse(db.status(self.root)["needs_index"])
        self.write("a.txt", "合同条款已更新")
        with self.assertRaises(ValueError):
            db.build_index(self.root)
        result = db.scan(self.root)
        self.assertEqual(result["counts"]["modified"], 1)
        self.assertIsNone(self.row("a.txt")["profile"])
        self.assertTrue(db.status(self.root)["needs_index"])

    def test_metadata_only_change_reuses_profile(self):
        path = self.write("a.txt", "预算")
        db.scan(self.root)
        db.annotate(self.root, self.profile("a.txt"))
        profile = self.row("a.txt")["profile"]
        stamp = path.stat()
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
        self.assertTrue(db.status(self.root)["needs_scan"])
        db.scan(self.root)
        self.assertEqual(self.row("a.txt")["profile"], profile)

    def test_same_size_time_change_is_caught_by_live_hash(self):
        path = self.write("a.txt", "ABCD")
        db.scan(self.root)
        old = path.stat()
        path.write_bytes(b"WXYZ")
        os.utime(path, ns=(old.st_atime_ns, old.st_mtime_ns))
        self.assertFalse(db.status(self.root)["needs_scan"])
        self.assertFalse(db.dump(self.root)["files"][0]["source_fresh"])
        self.assertEqual(db.scan(self.root)["counts"]["modified"], 1)

    def test_manual_move_preserves_id_and_locks_location(self):
        path = self.write("a.txt", "预算")
        db.scan(self.root)
        db.annotate(self.root, self.profile("a.txt"))
        old_id = self.row("a.txt")["id"]
        (self.root / "手动目录").mkdir()
        path.rename(self.root / "手动目录/新名.txt")
        result = db.scan(self.root)
        row = self.row("手动目录/新名.txt")
        self.assertEqual(result["counts"]["moved"], 1)
        self.assertEqual(row["id"], old_id)
        self.assertEqual(row["location_locked"], 1)
        self.assertEqual(json.loads(row["profile"])["classification_status"], "review")
        with self.assertRaises(ValueError):
            db.check_plan(self.root, self.plan("手动目录/新名.txt", "另一目录/a.txt"))

    def test_ambiguous_duplicates_do_not_merge_ids(self):
        a = self.write("a.txt", "same")
        b = self.write("b.txt", "same")
        report = db.scan(self.root)
        old_ids = {self.row("a.txt")["id"], self.row("b.txt")["id"]}
        self.assertEqual(report["duplicate_group_count"], 1)
        a.rename(self.root / "c.txt")
        b.rename(self.root / "d.txt")
        report = db.scan(self.root)
        self.assertEqual(report["counts"]["moved"], 0)
        self.assertNotIn(self.row("c.txt")["id"], old_ids)

    def test_duplicate_groups_are_paginated_beyond_one_hundred(self):
        for i in range(105):
            self.write(f"source-{i}.txt", f"content-{i}")
            self.write(f"copy-{i}.txt", f"content-{i}")
        report = db.scan(self.root)
        self.assertEqual(report["duplicate_group_count"], 105)
        first = db.duplicates(self.root, "file", 0, 100)
        second = db.duplicates(self.root, "file", 100, 100)
        self.assertEqual(first["total"], 105)
        self.assertEqual(len(first["groups"]), 100)
        self.assertEqual(len(second["groups"]), 5)
        self.assertIsNone(second["next_offset"])

    def test_refresh_fast_reconciles_changes_and_republishes_views(self):
        self.write("existing.txt", "old")
        db.scan(self.root)
        db.build_index(self.root)
        self.write("new.txt", "new content")
        result = db.refresh(self.root)
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(result["verification_mode"], "fast")
        self.assertEqual(result["scan"]["counts"]["added"], 1)
        self.assertFalse(db.status(self.root)["needs_scan"])
        self.assertFalse(db.status(self.root)["needs_index"])

    def test_resumable_scan_stages_then_atomically_publishes_and_replays(self):
        for name in ("a.txt", "b.txt", "c.txt"):
            self.write(name, "内容 " + name)
        first = db.scan(self.root, mode="full", batch_size=1)
        self.assertEqual(first["state"], "running")
        self.assertFalse(first["catalog_published"])
        self.assertEqual(db.status(self.root)["pending_scan_job"]["job_id"], first["job_id"])
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files").fetchone()[0], 0)
        job_id = first["job_id"]
        result = first
        for _ in range(20):
            if result["state"] != "running":
                break
            result = db.scan(self.root, mode="full", batch_size=1, job_id=job_id)
        self.assertEqual(result["state"], "completed")
        self.assertTrue(result["catalog_published"])
        self.assertEqual(result["scan"]["files"], 3)
        self.assertEqual(db.scan(self.root, mode="full", batch_size=1, job_id=job_id)["state"], "completed")
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files WHERE state='active'").fetchone()[0], 3)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM job_items WHERE job_id=?", (job_id,)).fetchone()[0], 0)

    def test_resumable_scan_rejects_changed_inventory_without_partial_catalog(self):
        self.write("a.txt", "初始内容")
        first = db.scan(self.root, mode="full", batch_size=1)
        self.assertEqual(first["state"], "running")
        self.write("b.txt", "新增内容")
        stale = db.scan(self.root, mode="full", batch_size=1, job_id=first["job_id"])
        self.assertEqual(stale["state"], "stale")
        self.assertFalse(stale["catalog_published"])
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files").fetchone()[0], 0)

    def test_resumable_scan_full_hash_detects_same_metadata_content_change(self):
        path = self.write("a.txt", "ABCD")
        first = db.scan(self.root, mode="full", batch_size=1)
        stamp = path.stat()
        path.write_bytes(b"WXYZ")
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        stale = db.scan(self.root, mode="full", batch_size=1, job_id=first["job_id"])
        self.assertEqual(stale["state"], "stale")
        self.assertFalse(stale["catalog_published"])
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM files").fetchone()[0], 0)

    def test_batched_refresh_does_not_build_indexes_until_scan_completes(self):
        self.write("existing.txt", "old")
        db.scan(self.root)
        db.build_index(self.root)
        self.write("new.txt", "new content")
        pending = db.refresh(self.root, batch_size=1)
        self.assertEqual(pending["status"], "scan_pending")
        self.assertIsNone(pending["index"])
        job_id = pending["scan"]["job_id"]
        result = pending
        for _ in range(20):
            if result["status"] != "scan_pending":
                break
            result = db.refresh(self.root, batch_size=1, job_id=job_id)
        self.assertEqual(result["status"], "refreshed")
        self.assertEqual(result["scan"]["counts"]["added"], 1)
        self.assertFalse(db.status(self.root)["needs_scan"])
        self.assertFalse(db.status(self.root)["needs_index"])

    def test_batched_scan_cli_resumes_by_job_id(self):
        self.write("a.txt", "内容 A")
        self.write("b.txt", "内容 B")
        script = Path(db.__file__).resolve()
        def cli(*args):
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(script), "scan",
                "--root", str(self.root), *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        first = cli("--mode", "full", "--batch-size", "1")
        self.assertEqual(first["state"], "running")
        result = cli("--mode", "full", "--batch-size", "1", "--job-id", first["job_id"])
        while result["state"] == "running":
            result = cli("--mode", "full", "--batch-size", "1", "--job-id", first["job_id"])
        self.assertEqual(result["state"], "completed")
        self.assertTrue(result["catalog_published"])

    def test_exact_directory_duplicates_are_reported_as_maximal_trees(self):
        self.write("A/sub/file.txt", "identical bytes")
        self.write("B/sub/file.txt", "identical bytes")
        report = db.scan(self.root)
        self.assertEqual(report["duplicate_folder_group_count"], 1)
        self.assertEqual(report["duplicate_folder_groups"][0]["paths"], ["A", "B"])
        self.assertEqual(report["duplicate_folder_groups"][0]["manifest_sha256"],
            db.directory_manifest(self.root, "A")[0])

    def test_directory_duplicates_require_complete_matching_trees(self):
        self.write("A/sub/file.txt", "same")
        self.write("B/sub/file.txt", "same")
        self.write("A/.private/ignored.txt", "not inventoried")
        report = db.scan(self.root)
        self.assertEqual(report["duplicate_folder_groups"][0]["paths"], ["A/sub", "B/sub"])
        self.assertNotIn(["A", "B"], [group["paths"] for group in report["duplicate_folder_groups"]])
        self.assertTrue(report["incomplete_folder_scan"])

    def test_empty_duplicate_folders_are_detected(self):
        (self.root / "empty-a").mkdir()
        (self.root / "empty-b").mkdir()
        report = db.scan(self.root)
        self.assertEqual(report["duplicate_folder_groups"][0]["paths"], ["empty-a", "empty-b"])

    def test_duplicate_quarantine_moves_files_and_can_restore_without_deleting(self):
        self.write("a.txt", "same bytes")
        self.write("b.txt", "same bytes")
        db.scan(self.root)
        preview = db.quarantine_duplicates(self.root)
        self.assertEqual(preview["file_moves"], 1)
        self.assertFalse(preview["writes"])
        run = db.quarantine_duplicates(self.root, True)
        self.assertEqual(run["status"], "completed")
        self.assertTrue((self.root / "a.txt").exists())
        self.assertFalse((self.root / "b.txt").exists())
        hidden_copy = self.root / run["operations"][0]["dst"]
        self.assertEqual(hidden_copy.read_bytes(), b"same bytes")
        db.scan(self.root)
        with contextlib.closing(db.connect(self.root)) as con:
            quarantined_id = con.execute("SELECT id FROM files WHERE path LIKE '.filedb/quarantine/%'").fetchone()[0]
        quarantined = db.dump(self.root, quarantined_id)["files"][0]
        self.assertEqual(quarantined["state"], "quarantined")
        self.assertEqual(quarantined["original_path"], "b.txt")
        self.assertEqual(quarantined["quarantine_run_id"], run["run_id"])
        self.assertTrue(db.restore_quarantine(self.root, run["run_id"])["valid"])
        self.assertEqual(db.restore_quarantine(self.root, run["run_id"], True)["status"], "restored")
        self.assertEqual((self.root / "b.txt").read_bytes(), b"same bytes")
        self.assertTrue(hidden_copy.exists() is False)
        db.scan(self.root)
        self.assertEqual(db.status(self.root)["needs_scan"], False)

    def test_duplicate_folder_quarantine_and_restore(self):
        self.write("A/sub/file.txt", "same folder")
        self.write("B/sub/file.txt", "same folder")
        db.scan(self.root)
        preview = db.quarantine_duplicates(self.root)
        self.assertEqual(preview["directory_moves"], 1)
        self.assertEqual(preview["file_moves"], 0)
        run = db.quarantine_duplicates(self.root, True)
        self.assertEqual(run["status"], "completed")
        moved = self.root / run["operations"][0]["dst"]
        self.assertEqual((moved / "sub/file.txt").read_text(encoding="utf-8"), "same folder")
        db.scan(self.root)
        self.assertFalse(db.scan(self.root)["duplicate_folder_groups"])
        self.assertEqual(db.restore_quarantine(self.root, run["run_id"], True)["status"], "restored")
        self.assertTrue((self.root / "B/sub/file.txt").exists())
        self.assertEqual((self.root / "B/sub/file.txt").read_text(encoding="utf-8"), "same folder")

    def test_generated_indexes_do_not_break_directory_quarantine(self):
        self.write("A/file.txt", "same folder")
        self.write("B/file.txt", "same folder")
        db.scan(self.root)
        db.build_index(self.root)
        db.scan(self.root)
        preview = db.quarantine_plan(self.root)
        self.assertEqual(preview["directory_moves"], 1)
        run = db.quarantine_duplicates(self.root, True)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(db.restore_quarantine(self.root, run["run_id"], True)["status"], "restored")
        self.assertFalse((self.root / "A/AI_INDEX.md").exists())
        self.assertFalse((self.root / "B/AI_INDEX.md").exists())
        self.assertTrue((self.root / "AI_INDEX.md").exists())

    def test_quarantine_cli_preview_execute_and_restore(self):
        library = self.root / "CLI资料"
        library.mkdir()
        (library / "a.txt").write_text("same", encoding="utf-8")
        (library / "b.txt").write_text("same", encoding="utf-8")
        script = Path(__file__).with_name("folderdb.py").resolve()
        def cli(command, *args):
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(script), command,
                "--root", str(library), *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        cli("scan")
        preview = cli("quarantine")
        self.assertFalse(preview["writes"])
        run = cli("quarantine", "--execute")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(cli("restore-quarantine", "--run-id", run["run_id"])["valid"], True)
        self.assertEqual(cli("restore-quarantine", "--run-id", run["run_id"], "--execute")["status"], "restored")
        self.assertTrue((library / "b.txt").exists())

    def test_quarantine_keeps_user_locked_copy(self):
        self.write("a.txt", "same")
        self.write("b.txt", "same")
        db.scan(self.root)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET location_locked=1 WHERE path='b.txt'")
            con.commit()
        preview = db.quarantine_plan(self.root)
        self.assertEqual(preview["operations"][0]["src"], "a.txt")
        self.assertEqual(preview["operations"][0]["keep"], "b.txt")

    def test_quarantine_rejects_unscanned_changes(self):
        self.write("a.txt", "same")
        self.write("b.txt", "same")
        db.scan(self.root)
        self.write("c.txt", "new file")
        with self.assertRaises(ValueError):
            db.quarantine_duplicates(self.root, True)

    def test_delete_empty_folder_and_missing_history(self):
        self.write("a.txt", "abc")
        (self.root / "空文件夹").mkdir()
        db.scan(self.root)
        db.build_index(self.root)
        (self.root / "a.txt").unlink()
        self.assertTrue(db.status(self.root)["needs_scan"])
        db.scan(self.root)
        db.build_index(self.root)
        self.assertEqual(self.row("a.txt")["state"], "missing")
        self.assertFalse((self.root / "空文件夹/AI_INDEX.md").exists())
        self.assertNotIn("a.txt", (self.root / "AI_INDEX.md").read_text(encoding="utf-8"))

    def test_index_bundle_has_ai_human_manifest_and_offline_portal(self):
        self.write("项目A/预算.txt", "预算正文")
        db.scan(self.root)
        db.annotate(self.root, self.profile("项目A/预算.txt"))
        result = db.build_index(self.root)
        self.assertTrue((self.root / "AI_INDEX.md").is_file())
        self.assertTrue((self.root / "AI_README.md").is_file())
        self.assertTrue((self.root / "README.md").is_file())
        self.assertTrue((self.root / "file-knowledge-base.html").is_file())
        self.assertTrue((self.root / ".filedb/manifest.json").is_file())
        self.assertFalse((self.root / "项目A/AI_INDEX.md").exists())
        self.assertEqual(result["portal_files"], 1)
        portal = (self.root / "file-knowledge-base.html").read_text(encoding="utf-8")
        self.assertIn("项目A/预算.txt", portal)
        with contextlib.closing(db.connect(self.root)) as con:
            indexed = {r[0] for r in con.execute("SELECT path FROM indexes")}
        self.assertTrue({"AI_INDEX.md", "AI_README.md", "file-knowledge-base.html", ".filedb/manifest.json"}.issubset(indexed))

    def test_portal_embedded_json_escapes_script_boundary_and_omits_cached_body(self):
        self.write("danger.txt", "普通正文")
        db.scan(self.root)
        row = self.row("danger.txt")
        annotation = self.profile("danger.txt")
        annotation["files"][0]["summary"] = "</script><script>alert(1)</script>"
        db.annotate(self.root, annotation)
        db.build_index(self.root)
        html = (self.root / "file-knowledge-base.html").read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert", html)
        self.assertIn("\\u003c/script", html)
        self.assertNotIn('"text":"普通正文"', html)

    def test_user_index_is_never_overwritten(self):
        original = self.write("AI_INDEX.md", "my original index")
        db.scan(self.root)
        with self.assertRaises(ValueError):
            db.build_index(self.root)
        self.assertEqual(original.read_text(encoding="utf-8"), "my original index")

    def test_generated_index_manual_edits_are_preserved(self):
        self.write("a.txt", "预算")
        db.scan(self.root)
        db.build_index(self.root)
        path = self.root / "AI_INDEX.md"
        changed = path.read_text(encoding="utf-8") + "manual note\n"
        path.write_text(changed, encoding="utf-8")
        self.assertIn("AI_INDEX.md", db.status(self.root)["manual_index_conflicts"])
        with self.assertRaises(ValueError):
            db.build_index(self.root)
        self.assertEqual(path.read_text(encoding="utf-8"), changed)

    def test_missing_index_is_recreated_and_large_index_is_paged(self):
        for i in range(5): self.write(f"a{i}.txt", str(i))
        db.scan(self.root)
        db.build_index(self.root, page_size=2)
        self.assertEqual(len(list((self.root / ".filedb/indexes").rglob("page-*.md"))), 3)
        (self.root / "AI_INDEX.md").unlink()
        self.assertTrue(db.status(self.root)["needs_index"])
        db.build_index(self.root, page_size=2)
        self.assertTrue((self.root / "AI_INDEX.md").exists())

    def test_apply_preview_and_rollback_preserve_bytes(self):
        path = self.write("a.txt", "预算原始字节")
        original = path.read_bytes()
        db.scan(self.root)
        file_id = self.row("a.txt")["id"]
        plan = self.plan("a.txt", "分类/新名.txt")
        self.assertFalse(db.apply(self.root, plan)["writes"])
        self.assertTrue(path.exists())
        run = db.apply(self.root, plan, True)
        self.assertEqual(run["status"], "completed")
        self.assertFalse(path.exists())
        self.assertEqual((self.root / "分类/新名.txt").read_bytes(), original)
        db.scan(self.root)
        self.assertEqual(self.row("分类/新名.txt")["id"], file_id)
        self.assertEqual(self.row("分类/新名.txt")["location_locked"], 0)
        self.assertFalse(db.rollback(self.root, run["run_id"])["writes"])
        self.assertEqual(db.rollback(self.root, run["run_id"], True)["status"], "rolled_back")
        self.assertEqual(path.read_bytes(), original)

    def test_outside_collision_stale_plan_and_reserved_names_refused(self):
        self.write("a.txt", "abc")
        self.write("occupied.txt", "user content")
        db.scan(self.root)
        for destination in ("../outside.txt", "/outside.txt", "occupied.txt", "CON.txt", ".git/a.txt", "AI_INDEX.md"):
            with self.subTest(destination=destination), self.assertRaises(ValueError):
                db.check_plan(self.root, self.plan("a.txt", destination))
        plan = self.plan("a.txt", "new.txt")
        self.write("a.txt", "source changed")
        with self.assertRaises(ValueError): db.apply(self.root, plan, True)
        self.assertFalse((self.root / "new.txt").exists())

    def test_stale_annotation_and_taxonomy_version_check(self):
        self.write("a.txt", "预算")
        db.scan(self.root)
        profile = self.profile("a.txt")
        db.annotate(self.root, profile)
        profile["taxonomy"]["categories"][0]["definition"] = "changed definition"
        with self.assertRaises(ValueError): db.annotate(self.root, profile)
        self.write("a.txt", "changed content")
        with self.assertRaises(ValueError): db.annotate(self.root, profile)

    def test_search_withheld_stale_summary(self):
        self.write("a.txt", "预算")
        db.scan(self.root)
        db.annotate(self.root, self.profile("a.txt"))
        self.assertTrue(db.search(self.root, "预算")["results"])
        self.write("a.txt", "other")
        hit = db.search(self.root, "预算")["results"][0]
        self.assertFalse(hit["source_fresh"])
        self.assertIsNone(hit["summary"])

    def test_unrecognized_state_is_preserved(self):
        (self.root / ".filedb").mkdir()
        catalog = self.root / ".filedb/catalog.sqlite"
        catalog.write_bytes(b"user database content")
        before = catalog.read_bytes()
        self.assertEqual(db.identity(self.root)["kind"], "corrupt")
        with self.assertRaises(ValueError): db.scan(self.root)
        self.assertEqual(catalog.read_bytes(), before)

    def test_foreign_sqlite_is_not_reinitialized(self):
        (self.root / ".filedb").mkdir()
        path = self.root / ".filedb/catalog.sqlite"
        with contextlib.closing(sqlite3.connect(path)) as con:
            con.execute("CREATE TABLE user_data(value TEXT)")
            con.commit()
        self.assertEqual(db.identity(self.root)["kind"], "foreign")
        with self.assertRaises(ValueError): db.scan(self.root)
        with contextlib.closing(sqlite3.connect(path)) as con:
            self.assertIsNotNone(con.execute("SELECT name FROM sqlite_master WHERE name='user_data'").fetchone())

    def test_ooxml_extract_reports_partial_coverage(self):
        with zipfile.ZipFile(self.root / "sample.docx", "w") as z:
            z.writestr("word/document.xml", '<document><p><t>预算正文</t></p></document>')
        db.scan(self.root)
        row = self.row("sample.docx")
        self.assertIn("预算正文", row["text"])
        self.assertEqual(row["extraction_status"], "partial_format")
        self.assertFalse(json.loads(row["coverage"])["complete"])

    def test_directory_rename_adopts_only_known_generated_indexes(self):
        self.write("old/a.txt", "abc")
        db.scan(self.root)
        db.build_index(self.root)
        (self.root / "old").rename(self.root / "new")
        db.scan(self.root)
        db.build_index(self.root)
        self.assertFalse((self.root / "new/AI_INDEX.md").exists())
        self.assertIn("new", (self.root / "AI_INDEX.md").read_text(encoding="utf-8"))

    def test_interrupted_reverse_copy_reconciles_catalog(self):
        self.write("a.txt", "abc")
        db.scan(self.root)
        run = db.apply(self.root, self.plan("a.txt", "new/a.txt"), True)
        log = self.root / ".filedb/runs" / (run["run_id"] + ".json")
        data = json.loads(log.read_text(encoding="utf-8"))
        data["operations"][0]["recovery_started_at"] = db.now()
        log.write_text(json.dumps(data), encoding="utf-8")
        (self.root / "new/a.txt").rename(self.root / "a.txt")
        self.assertEqual(db.rollback(self.root, run["run_id"], True)["status"], "rolled_back")
        self.assertEqual(self.row("a.txt")["state"], "active")

    def test_recovery_refuses_changed_destination(self):
        self.write("a.txt", "abc")
        db.scan(self.root)
        run = db.apply(self.root, self.plan("a.txt", "new/a.txt"), True)
        self.write("new/a.txt", "changed by user")
        with self.assertRaises(ValueError): db.rollback(self.root, run["run_id"], True)
        self.assertEqual((self.root / "new/a.txt").read_text(encoding="utf-8"), "changed by user")

    def test_logged_copy_intent_without_created_target_is_recoverable(self):
        self.write("a.txt", "abc")
        db.scan(self.root)
        real_copy = db.copy_verified
        def stop_at_intent(src, dst, sha, phase):
            phase("copy_intent")
            raise OSError("interrupted before destination creation")
        with patch.object(db, "copy_verified", side_effect=stop_at_intent):
            run = db.apply(self.root, self.plan("a.txt", "new/a.txt"), True)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(db.rollback(self.root, run["run_id"], True)["status"], "rolled_back")
        self.assertTrue((self.root / "a.txt").exists())

    def test_reextract_respects_content_revision(self):
        self.write("a.txt", "预算")
        db.scan(self.root, max_chars=4)
        self.assertEqual(self.row("a.txt")["extraction_status"], "truncated")
        db.scan(self.root, max_chars=200000)
        self.assertEqual(self.row("a.txt")["extraction_status"], "text_cached")

    def test_parser_capabilities_and_bounded_ooxml_units(self):
        pptx = self.root / "slides.pptx"
        with zipfile.ZipFile(pptx, "w") as archive:
            archive.writestr("ppt/slides/slide1.xml", "<p><r><t>第一张</t></r></p>")
            archive.writestr("ppt/slides/slide2.xml", "<p><r><t>第二张</t></r></p>")
        status, text, coverage = db.extract(pptx, 1024 * 1024, 200000, max_units=1)
        self.assertEqual(status, "truncated")
        self.assertIn("第一张", text)
        self.assertNotIn("第二张", text)
        self.assertTrue(coverage["units_limited"])
        worker_status, worker_text, _ = db.extract_bounded(pptx, 1024 * 1024, 200000, timeout_seconds=10)
        self.assertEqual(worker_status, "partial_format")
        self.assertIn("第一张", worker_text)
        self.assertIn("第二张", worker_text)
        self.assertEqual(db.parser_capabilities()["resource_limits"]["archive_entries"], 10000)

    def test_complex_parser_timeout_is_a_reported_read_issue(self):
        path = self.write("slow.docx", "synthetic parser input")
        with patch.object(db.subprocess, "run", side_effect=subprocess.TimeoutExpired("parser-worker", 1)):
            status, text, info = db.extract_bounded(path, 1024 * 1024, 200000, timeout_seconds=1)
        self.assertEqual(status, "error")
        self.assertEqual(text, "")
        self.assertEqual(db.extraction_issue(status), "read_error")
        self.assertIn("wall-clock limit", info["reason"])
        self.assertEqual(info["timeout_seconds"], 1)

    def test_scan_stores_parser_timeout_guidance_for_retry(self):
        self.write("slow.docx", "synthetic parser input")
        with patch.object(db.subprocess, "run", side_effect=subprocess.TimeoutExpired("parser-worker", 1)):
            report = db.scan(self.root, parser_timeout_seconds=1)
        self.assertEqual(self.row("slow.docx")["extraction_status"], "error")
        self.assertTrue(any("wall-clock limit" in item["error"] for item in report["errors"]))
        pending = db.pending(self.root, "read_error")
        self.assertEqual(pending["items"][0]["reason_code"], "read_error")
        self.assertIn("wall-clock limit", pending["items"][0]["coverage"]["reason"])
        self.assertTrue(pending["items"][0]["next_action"])

    def test_parse_retry_job_resumes_in_bounded_idempotent_batches(self):
        self.write("a.txt", "预算")
        self.write("b.txt", "合同")
        db.scan(self.root)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET extraction_status='unsupported',text='' WHERE state='active'")
            con.commit()
        first = db.retry_parsing(self.root, limit=1)
        self.assertEqual(first["state"], "running")
        self.assertTrue(first["resumable"])
        second = db.retry_parsing(self.root, job_id=first["job_id"], limit=1)
        self.assertEqual(second["state"], "completed")
        self.assertFalse(second["resumable"])
        self.assertEqual(second["processed"], 2)
        self.assertEqual(self.row("a.txt")["extraction_status"], "text_cached")
        self.assertEqual(self.row("b.txt")["extraction_status"], "text_cached")
        again = db.retry_parsing(self.root, job_id=first["job_id"], limit=1)
        self.assertEqual(again["state"], "completed")
        self.assertEqual(again["processed"], 2)

    def test_taxonomy_impact_preview_is_read_only_and_counts_locked_files(self):
        self.write("a.txt", "项目A预算")
        db.scan(self.root)
        document = self.profile("a.txt")
        db.annotate(self.root, document)
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("UPDATE files SET location_locked=1 WHERE path='a.txt'")
            before = con.execute("SELECT value FROM meta WHERE key='catalog_revision'").fetchone()[0]
            con.commit()
        revised = json.loads(json.dumps(document["taxonomy"], ensure_ascii=False))
        revised["version"] = "2"
        revised["categories"][0]["definition"] = "项目A采购预算和资金计划资料"
        preview = db.taxonomy_check(self.root, {"taxonomy": revised})
        self.assertFalse(preview["writes"])
        self.assertEqual(preview["changed_categories"], ["budget"])
        self.assertEqual(preview["affected_profile_count"], 1)
        self.assertEqual(preview["affected_locked_count"], 1)
        with contextlib.closing(db.connect(self.root)) as con:
            self.assertEqual(con.execute("SELECT value FROM meta WHERE key='catalog_revision'").fetchone()[0], before)
        revised["version"] = "3"
        revised["categories"] = []
        removed = db.taxonomy_check(self.root, {"taxonomy": revised})
        self.assertEqual(removed["removed_categories"], ["budget"])
        self.assertEqual(removed["affected_profile_count"], 1)
        same_version_mutation = json.loads(json.dumps(document["taxonomy"], ensure_ascii=False))
        same_version_mutation["categories"][0]["definition"] = "未经升级版本的规则更改"
        with self.assertRaises(ValueError):
            db.taxonomy_check(self.root, {"taxonomy": same_version_mutation})

    def test_fts_chinese_substring_alias_and_no_fts_fallback(self):
        self.write("项目A/预算.txt", "项目A设备投入采购预算")
        db.scan(self.root)
        profile = self.profile("项目A/预算.txt")
        profile["files"][0]["tags"][0]["aliases"] = ["设备投入计划"]
        db.annotate(self.root, profile)
        long_query = db.search(self.root, "设备投入")
        self.assertTrue(long_query["results"])
        self.assertIn("fts5-trigram", long_query["method"])
        alias_query = db.search(self.root, "设备投入计划")
        self.assertTrue(alias_query["results"])
        short_query = db.search(self.root, "设备")
        self.assertTrue(short_query["results"])
        self.assertIn("python-substring", short_query["method"])
        with contextlib.closing(db.connect(self.root, write=True)) as con:
            con.execute("DROP TRIGGER IF EXISTS files_fts_insert")
            con.execute("DROP TRIGGER IF EXISTS files_fts_update")
            con.execute("DROP TRIGGER IF EXISTS files_fts_delete")
            con.execute("DROP TABLE IF EXISTS files_fts")
            con.commit()
        fallback = db.search(self.root, "设备投入")
        self.assertTrue(fallback["results"])
        self.assertIn("python-substring", fallback["method"])

    def test_directory_plan_move_and_rollback_preserve_descendant_identity(self):
        self.write("旧项目/资料/说明.txt", "path reference: 旧项目/资料/说明.txt")
        db.scan(self.root)
        manifest, _ = db.directory_manifest(self.root, "旧项目")
        plan = {"version": 2, "root": str(self.root), "operations": [{"src": "旧项目", "dst": "归档项目",
            "manifest_sha256": manifest, "reason": "synthetic authorized directory move"}]}
        preview = db.check_directory_plan(self.root, plan)
        self.assertTrue(preview["valid"])
        self.assertTrue(preview["warnings_require_agent_review"])
        original_id = self.row("旧项目/资料/说明.txt")["id"]
        run = db.apply_directory_plan(self.root, plan, True)
        self.assertEqual(run["status"], "completed")
        self.assertTrue((self.root / "归档项目/资料/说明.txt").exists())
        self.assertEqual(self.row("归档项目/资料/说明.txt")["id"], original_id)
        self.assertTrue(self.row("归档项目/资料/说明.txt")["location_locked"])
        self.assertTrue(db.rollback(self.root, run["run_id"])["valid"])
        rolled_back = db.rollback(self.root, run["run_id"], True)
        self.assertEqual(rolled_back["status"], "rolled_back")
        self.assertTrue((self.root / "旧项目/资料/说明.txt").exists())
        self.assertEqual(self.row("旧项目/资料/说明.txt")["id"], original_id)

    def test_directory_move_interruption_is_recoverable_from_journal(self):
        self.write("old/a.txt", "stable")
        db.scan(self.root)
        manifest, _ = db.directory_manifest(self.root, "old")
        plan = {"version": 2, "root": str(self.root), "operations": [{"src": "old", "dst": "new",
            "manifest_sha256": manifest, "reason": "synthetic interrupted move"}]}
        real_replace = os.replace
        def move_then_interrupt(src, dst):
            real_replace(src, dst)
            if Path(src) == self.root / "old":
                raise OSError("synthetic crash after atomic directory rename")
        with patch.object(db.os, "replace", side_effect=move_then_interrupt):
            failed = db.apply_directory_plan(self.root, plan, True)
        self.assertEqual(failed["status"], "failed")
        self.assertTrue((self.root / "new/a.txt").exists())
        recovered = db.rollback(self.root, failed["run_id"], True)
        self.assertEqual(recovered["status"], "rolled_back")
        self.assertTrue((self.root / "old/a.txt").exists())

    def test_opt_in_watcher_start_stop_status_and_log_in_temp_library(self):
        self.write("existing.txt", "stable")
        db.scan(self.root)
        db.build_index(self.root)
        started = watch.start(self.root, interval_seconds=1, debounce_seconds=0, full_interval_hours=24)
        self.assertIn(started["status"], {"starting", "running"})
        try:
            requested = watch.stop(self.root)
            self.assertTrue(requested["requested"])
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline and watch.watch_status(self.root)["status"] not in {"stopped", "failed", "stale"}:
                time.sleep(0.2)
            state = watch.watch_status(self.root)
            self.assertEqual(state["status"], "stopped")
            self.assertTrue(watch.tail_log(self.root)["lines"])
        finally:
            if watch.watch_status(self.root)["status"] in {"starting", "running", "stop_requested"}:
                watch.stop(self.root)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and watch.watch_status(self.root)["status"] != "stopped":
                    time.sleep(0.2)

    def test_watcher_reconciles_new_file_without_semantic_or_file_mutations(self):
        self.write("existing.txt", "stable")
        db.scan(self.root)
        db.build_index(self.root)
        token = "synthetic-watch-token"
        _, state_path, _, _, _ = watch.paths(self.root)
        watch.write_json(state_path, {"token": token, "status": "starting", "root": str(self.root),
            "started_at": watch.utc_now(), "started_epoch": time.time(), "heartbeat_epoch": time.time(),
            "interval_seconds": 1, "debounce_seconds": 0, "full_interval_hours": 24})
        self.write("new/新增预算.txt", "新增预算内容")
        report = watch.run_worker(self.root, token, interval_seconds=1, debounce_seconds=0,
            full_interval_hours=24, max_cycles=1)
        self.assertEqual(report["status"], "stopped")
        row = self.row("new/新增预算.txt")
        self.assertEqual(row["extraction_status"], "text_cached")
        self.assertIsNone(row["profile"])
        self.assertTrue((self.root / "AI_INDEX.md").is_file())
        directory_index = self.root / ".filedb/indexes" / ("dir-" + hashlib.sha256("new".encode("utf-8")).hexdigest()[:16] + ".md")
        self.assertIn("新增预算.txt", directory_index.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "old").exists())

    def test_cli_lifecycle_in_unicode_root(self):
        library = self.root / "合成资料库"
        library.mkdir()
        (library / "预算.txt").write_text("项目A采购预算", encoding="utf-8")
        script = Path(__file__).with_name("folderdb.py").resolve()
        def cli(command, *args):
            result = subprocess.run([sys.executable, "-B", "-X", "utf8", str(script), command, "--root", str(library), *args], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return json.loads(result.stdout)
        self.assertEqual(cli("preflight")["library"]["kind"], "new")
        cli("scan")
        file = cli("dump")["files"][0]
        annotation = {"taxonomy": {"version": "1", "categories": [{"id": "budget", "label": "预算", "path": "项目A/预算", "definition": "项目A预算"}]},
            "files": [{"file_id": file["id"], "source_sha256": file["sha256"], "title": "采购预算", "summary": "项目A采购预算", "category_id": "budget", "classification_status": "confident", "classification_basis": ["content"], "semantic_status": "reviewed", "tags": [], "read_coverage": "完整合成文本", "evidence": [{"field": "category_id", "locator": "text:line-1", "basis": "正文确认项目A预算"}, {"field": "title", "locator": "text:line-1", "basis": "原文标题"}]}]}
        source = self.root / "annotations.json"
        source.write_text(json.dumps(annotation, ensure_ascii=False), encoding="utf-8")
        cli("annotate", "--input", str(source))
        cli("index")
        self.assertFalse(cli("status")["needs_index"])
        self.assertTrue(cli("search", "--query", "预算")["results"])
        plan = {"version": 1, "root": str(library), "operations": [{"file_id": file["id"], "src": "预算.txt", "dst": "项目A/预算/采购预算.txt", "sha256": file["sha256"], "reason": "合成授权计划"}]}
        plan_file = self.root / "plan.json"
        plan_file.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        cli("plan-check", "--plan", str(plan_file))
        self.assertFalse(cli("apply", "--plan", str(plan_file))["writes"])
        run = cli("apply", "--plan", str(plan_file), "--execute")
        self.assertEqual(run["status"], "completed")
        self.assertEqual(cli("rollback", "--run-id", run["run_id"], "--execute")["status"], "rolled_back")
        cli("scan")
        cli("index")
        self.assertTrue((library / "预算.txt").exists())

    def test_reparse_links_are_excluded(self):
        self.write("real/a.txt", "abc")
        link = self.root / "linked"
        try:
            os.symlink(self.root / "real", link, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("host does not permit creating symbolic links")
        try:
            report = db.scan(self.root)
            self.assertTrue(any(s["path"] == "linked" and s["reason"] == "link/reparse" for s in report["skipped"]))
            with self.assertRaises(ValueError): db.relative(self.root, "linked/a.txt")
        finally:
            link.unlink()

    def test_partial_batch_failure_has_recoverable_journal(self):
        self.write("a.txt", "a")
        self.write("b.txt", "b")
        db.scan(self.root)
        plan = self.plan("a.txt", "new/a.txt")
        plan["operations"] += self.plan("b.txt", "new/b.txt")["operations"]
        real_copy = db.copy_verified
        def fail_second(src, dst, sha, phase):
            if src.name == "b.txt": raise OSError("synthetic interruption")
            return real_copy(src, dst, sha, phase)
        with patch.object(db, "copy_verified", side_effect=fail_second):
            run = db.apply(self.root, plan, True)
        self.assertEqual(run["status"], "failed")
        self.assertTrue((self.root / "b.txt").exists())
        self.assertEqual(db.rollback(self.root, run["run_id"], True)["status"], "rolled_back")
        self.assertTrue((self.root / "a.txt").exists())

    def test_saved_views_round_trip_through_cli_and_filters_are_allowlisted(self):
        self.write("项目A/采购预算.txt", "项目A采购预算与付款节点")
        db.scan(self.root)
        script = Path(db.__file__)
        def run(*args):
            result = subprocess.run([sys.executable, str(script), *args, "--root", str(self.root)],
                capture_output=True, text=True, encoding="utf-8", check=True)
            return json.loads(result.stdout)
        saved = run("view-save", "--name", "采购资料", "--query", "采购预算", "--folder", "项目A")
        self.assertTrue(saved["saved"])
        found = run("query", "--view-name", "采购资料")
        self.assertEqual(found["saved_view"], "采购资料")
        self.assertEqual([row["path"] for row in found["results"]], ["项目A/采购预算.txt"])
        self.assertEqual(run("view-list")["total"], 1)
        self.assertTrue(run("view-delete", "--name", "采购资料")["deleted"])
        self.assertEqual(run("view-list")["total"], 0)
        with self.assertRaises(ValueError):
            db.save_view(self.root, "unsafe", {"sql": "DROP TABLE files"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
