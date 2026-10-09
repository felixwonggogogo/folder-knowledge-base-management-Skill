#!/usr/bin/env python3
"""Open generated and 10k synthetic portal pages in local Chromium via installed Playwright."""
from __future__ import annotations

import contextlib
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import folderdb


def safe_html(template, payload):
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    safe = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return template.replace("__KBASE_DATA__", safe)


def make_payload(total=10000):
    hostile = "</script><img src=x onerror=window.__xss=1>"
    files = []
    for index in range(total):
        name = f"文件-{index:05d}" + ("-needle-09999" if index == total - 1 else "") + ".txt"
        files.append({"file_id": f"synthetic-{index:05d}", "path": "资料/" + name, "name": name,
            "title": hostile if index == 0 else name, "extension": ".txt", "file_type_label": "文本",
            "size_human": "120 bytes", "category_id": "cat-a" if index % 2 == 0 else "cat-b",
            "category_label": "项目A" if index % 2 == 0 else "项目B", "classification_status": "inherited",
            "classification_label": "沿用目录/文件名", "classification_basis": ["path"],
            "classification_basis_label": "path", "semantic_status": "unreviewed", "semantic_label": "尚未审阅",
            "business_state_label": "未确认", "extraction_status": "text_cached", "extraction_label": "已提取文本",
            "summary": hostile if index == 0 else None, "legacy_note": None,
            "tags": [{"facet": "file_type", "id": ".txt", "label": "文本"}, {"facet": "topic", "id": "budget", "label": "预算"}],
            "evidence": [], "read_coverage": "合成元数据，无正文", "issue_codes": [], "location_locked": False})
    return {"library_name": "浏览器性能合成库", "generated_at": "synthetic", "last_scanned_at": "synthetic",
        "catalog_revision": "synthetic-10k", "scope": {"truncated": False, "omitted_count": 0, "included_count": total, "includes_file_content": False},
        "stats": {"active_files": total, "directories": 10, "inherited": total, "semantic_reviewed": 0, "parsing_limited": 0},
        "files": files, "issues": [{"path": "资料/待核实.txt", "reason_code": "read_error", "reason_label": "读取失败",
            "message": "合成问题说明", "certainty": "suspected", "certainty_label": "待核实", "next_action": "检查样本", "semantic_status": "unavailable"}]}


def run():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(json.dumps({"status": "skipped", "reason": "Playwright is not installed; no dependency was installed"}, ensure_ascii=False))
        return 2
    template = (HERE.parent / "assets" / "portal-template.html").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="folderdb-portal-browser-") as temp:
        temp_root = Path(temp).resolve()
        library = temp_root / "真实生成页面合成库"
        library.mkdir()
        (library / "alpha.txt").write_text("Alpha 预算", encoding="utf-8")
        (library / "beta.txt").write_text("Beta 合同", encoding="utf-8")
        (library / "10-项目/客户A/附件").mkdir(parents=True)
        (library / "10-项目/客户B").mkdir()
        (library / "10-项目/客户A/合同.txt").write_text("客户A合同，包含采购预算", encoding="utf-8")
        (library / "10-项目/客户A/附件/说明.txt").write_text("附件说明", encoding="utf-8")
        (library / "10-项目延伸").mkdir()
        (library / "10-项目延伸/其他.txt").write_text("另一项目", encoding="utf-8")
        folderdb.scan(library)
        with contextlib.closing(folderdb.connect(library)) as con:
            contract_id = con.execute("SELECT id FROM files WHERE path='10-项目/客户A/合同.txt'").fetchone()[0]
            archive_id = con.execute("SELECT id FROM files WHERE path='beta.txt'").fetchone()[0]
        folderdb.manage_lifecycle(library, contract_id, "synthetic user designation", "active", "customer-a-contract", "v1", True, "2026-12-01", True)
        folderdb.manage_lifecycle(library, archive_id, "synthetic archive", "archived", execute=True)
        policy = folderdb.policy
        policy.apply_policy(folderdb, library, "scenario", policy.template()["scenario"], "synthetic default selection", True, "none")
        vocab = policy.template()["vocabulary"]
        vocab["terms"].append({"facet": "topic", "id": "budget", "label": "预算", "aliases": [], "definition": "采购预算主题", "broader": [], "related": [], "status": "active", "replaced_by": None})
        first_vocab = policy.apply_policy(folderdb, library, "vocabulary", vocab, "synthetic vocabulary", True, "none")
        row = folderdb.dump(library, contract_id)["files"][0]
        folderdb.annotate(library, {"policy_revisions": folderdb.status(library)["policy_revisions"],
            "taxonomy": {"version": "1", "categories": [{"id": "contract", "label": "客户A合同", "path": "10-项目/客户A", "definition": "客户A合同材料"}]},
            "files": [{"file_id": contract_id, "source_sha256": row["sha256"], "title": "客户A合同", "summary": "合同含采购预算",
                "category_id": "contract", "classification_status": "confident", "classification_basis": ["content"], "semantic_status": "reviewed",
                "tags": [{"facet": "topic", "id": "budget", "label": "预算"}, {"facet": "document_type", "id": "contract", "label": "合同与协议"}],
                "read_coverage": "全文", "evidence": [{"field": "category_id", "locator": "text:line-1", "basis": "正文为客户A合同"}]}]})
        vocab["version"] = "2"
        vocab["terms"][-1]["aliases"] = ["PROCUREMENT_COST"]
        policy.apply_policy(folderdb, library, "vocabulary", vocab, "synthetic alias after annotation", True, first_vocab["revision"])
        folderdb.build_index(library)
        generated_page = library / "file-knowledge-base.html"
        large_page = temp_root / "portal-10000.html"
        large_page.write_text(safe_html(template, make_payload()), encoding="utf-8")
        errors, requests = [], []
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            context.set_offline(True)
            context.grant_permissions([])
            page = context.new_page()
            page.add_init_script("Object.defineProperty(navigator, 'clipboard', {value: undefined, configurable: true});")
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
            page.on("request", lambda request: requests.append(request.url))

            page.goto(generated_page.as_uri(), wait_until="load")
            if page.locator("#result-count").inner_text() != "5 items":
                raise AssertionError("Generated catalog page did not render all synthetic source files")
            if "General personal files (default)" not in page.locator("#scope-line").inner_text() or "Vocabulary revision: 2" not in page.locator("#scope-line").inner_text():
                raise AssertionError("Scenario/vocabulary revision is missing")
            page.locator("#language-switch").select_option("zh-CN")
            if page.locator("#result-count").inner_text() != "5 项" or "文件详情" not in page.locator("#inspector").inner_text():
                raise AssertionError("Chinese language switch did not translate the portal interface")
            if "场景：个人综合资料（默认）" not in page.locator("#scope-line").inner_text():
                raise AssertionError("The default scenario label did not switch to Chinese")
            page.locator("#language-switch").select_option("en")
            if page.locator("#result-count").inner_text() != "5 items" or "File details" not in page.locator("#inspector").inner_text():
                raise AssertionError("English language switch did not restore the portal interface")
            page.locator("#q").fill("PROCUREMENT_COST")
            if page.locator("#result-count").inner_text() != "1 item":
                raise AssertionError("Public alias did not find a historical annotation")
            page.locator("#q").fill("")
            page.locator("#topic-filter").select_option("budget")
            page.locator("#type-filter").select_option("合同与协议")
            page.locator("#format-filter").select_option(".txt")
            if page.locator("#result-count").inner_text() != "1 item":
                raise AssertionError("Topic/document-type/format filters did not combine")
            page.locator("#topic-filter").select_option("")
            page.locator("#type-filter").select_option("")
            page.locator("#format-filter").select_option("")
            page.locator("#business-filter").select_option("archived")
            if page.locator("#result-count").inner_text() != "1 item" or "Archived" not in page.locator("#inspector").inner_text():
                raise AssertionError("Archived lifecycle filter or detail is incorrect")
            page.locator("#business-filter").select_option("")
            page.locator("#folder-child").select_option("10-项目")
            if page.locator("#result-count").inner_text() != "2 items":
                raise AssertionError("Folder prefix collision included the sibling project")
            page.locator("#folder-child").select_option("10-项目/客户A")
            page.locator("#folder-scope").select_option("direct")
            if page.locator("#result-count").inner_text() != "1 item":
                raise AssertionError("Direct folder mode did not exclude descendants")
            if "File ID" not in page.locator("#inspector").inner_text():
                raise AssertionError("Human details did not expose the stable file ID")
            if "v1" not in page.locator("#inspector").inner_text() or "2026-12-01" not in page.locator("#inspector").inner_text():
                raise AssertionError("Human details omitted the declared version/review date")
            page.locator("#folder-scope").select_option("subtree")
            if page.locator("#result-count").inner_text() != "2 items":
                raise AssertionError("Subtree folder mode omitted descendants")
            page.locator("#folder-child").select_option("10-项目/客户A/附件")
            if page.locator("#result-count").inner_text() != "1 item":
                raise AssertionError("Third-level navigation did not isolate the attachment")
            page.locator("#breadcrumbs button").nth(1).click()
            page.locator("#folder-child").select_option("10-项目/客户B")
            if page.locator("#result-count").inner_text() != "0 items":
                raise AssertionError("Empty directory navigation is incorrect")
            page.locator("#breadcrumbs button").first.click()
            if page.locator("#result-count").inner_text() != "5 items":
                raise AssertionError("Breadcrumb root did not restore the complete scope")
            page.goto(large_page.as_uri(), wait_until="load")
            if page.locator("#result-count").inner_text() != "10,000 items":
                raise AssertionError("The 10k page did not expose the complete result count")
            if page.locator("#file-rows tr").count() != 40:
                raise AssertionError("The portal should render one bounded 40-row page")
            page.locator("#q").fill("needle-09999")
            if page.locator("#result-count").inner_text() != "1 item":
                raise AssertionError("Search did not find the 10k sentinel record")
            if "needle-09999" not in page.locator("#file-rows").inner_text():
                raise AssertionError("Search result path is not visible")
            row = page.locator("#file-rows tr").first
            row.focus()
            row.press("Enter")
            if "needle-09999" not in page.locator("#inspector").inner_text():
                raise AssertionError("Keyboard Enter did not open the selected record")
            page.locator("#inspector .copy-button").nth(1).click()
            if "Source: 资料/" not in page.locator("#inspector .copy-state").inner_text():
                raise AssertionError("Clipboard-unavailable path citation fallback did not appear")
            page.locator('[data-view="issues"]').click()
            if not page.locator("#issues").inner_text().strip():
                raise AssertionError("Issue view did not render")
            page.locator('[data-view="files"]').click()
            page.set_viewport_size({"width": 390, "height": 844})
            mobile_width = page.evaluate("({viewport: innerWidth, document: document.documentElement.scrollWidth})")
            if mobile_width["document"] > mobile_width["viewport"]:
                raise AssertionError("Narrow viewport introduces horizontal page overflow")
            context.close()

            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            static_page = no_js.new_page()
            static_page.goto(large_page.as_uri(), wait_until="load")
            if "Enable JavaScript" not in static_page.locator("noscript").inner_text() or "启用 JavaScript" not in static_page.locator("noscript").inner_text():
                raise AssertionError("Bilingual no-script navigation fallback is missing")
            no_js.close()
            browser_version = browser.version
            browser.close()
        external_requests = [url for url in requests if url.startswith(("http:", "https:"))]
        if errors:
            raise AssertionError("Browser errors: " + json.dumps(errors[:20], ensure_ascii=False))
        if external_requests:
            raise AssertionError("Unexpected network requests: " + json.dumps(external_requests, ensure_ascii=False))
        print(json.dumps({"status": "passed", "browser": "Chromium " + browser_version,
            "actual_generated_page": True, "synthetic_metadata_files": 10000, "page_size": 40,
            "search_sentinel": "found", "keyboard_details": "passed", "copy_fallback": "passed",
            "hierarchical_folders": "passed", "direct_subtree_scope": "passed", "empty_directory": "passed", "stable_file_id": "visible",
            "lifecycle_filter": "passed", "version_and_review_date": "visible",
            "public_vocabulary_alias": "passed", "topic_document_type_format_filters": "passed", "scenario_and_vocabulary_version": "visible",
            "issues_view": "passed", "narrow_viewport": mobile_width, "no_script_fallback": "passed",
            "external_requests": len(external_requests), "console_or_page_errors": errors}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
