#!/usr/bin/env python3
"""Run the bundled synthetic Chinese retrieval benchmark; touches only a temp directory."""
import json
import contextlib
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import folderdb


def run():
    fixture = json.loads((HERE.parent / "references" / "search-benchmark.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="folderdb-search-benchmark-") as temp:
        root = Path(temp).resolve()
        for relative, content in fixture["corpus"].items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        folderdb.scan(root)
        query_cases = fixture["queries"]
        alias_case = next((case for case in query_cases if case.get("tag_alias")), None)
        if alias_case:
            with contextlib.closing(folderdb.connect(root)) as con:
                row = con.execute("SELECT id,sha256 FROM files WHERE path=?", (alias_case["relevant_paths"][0],)).fetchone()
            folderdb.annotate(root, {"taxonomy": {"version": "1", "categories": []}, "files": [{
                "file_id": row["id"], "source_sha256": row["sha256"], "title": "会议纪要", "summary": "",
                "category_id": None, "classification_status": "unknown", "classification_basis": ["path"],
                "semantic_status": "unreviewed", "tags": [{"facet": "topic", "id": "equipment-investment",
                "label": "设备投入", "aliases": [alias_case["tag_alias"]]}], "read_coverage": "未审阅",
                "evidence": []}]})
        reports = []
        total_relevant = total_retrieved_relevant = 0
        for case in query_cases:
            result = folderdb.search(root, case["query"], limit=20)
            actual = [item["path"] for item in result["results"]]
            expected = set(case["relevant_paths"])
            found = expected.intersection(actual)
            stale = [item["path"] for item in result["results"] if not item["source_fresh"]]
            total_relevant += len(expected)
            total_retrieved_relevant += len(found)
            reports.append({"query": case["query"], "expected": sorted(expected), "retrieved": actual,
                "recall": len(found) / len(expected), "precision_at_20": len(found) / len(actual) if actual else 0,
                "method": result["method"], "stale_sources": stale})
        recall = total_retrieved_relevant / total_relevant if total_relevant else 1
        summary = {"fixture_version": fixture["version"], "synthetic_only": True, "fts5_trigram_available": folderdb.fts5_trigram_available(),
            "queries": len(reports), "macro_recall": sum(item["recall"] for item in reports) / len(reports),
            "micro_recall": recall, "all_sources_fresh": all(not item["stale_sources"] for item in reports), "cases": reports}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        if summary["micro_recall"] != 1 or not summary["all_sources_fresh"]:
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(run())
