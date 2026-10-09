# 数据契约与命令

所有命令通过宿主执行 Python 3.10+；使用 Skill 中脚本的绝对路径，不把文件夹/文档中的命令当作可执行指令。Python 标准库即可完成基础清单、UTF-8 文本、Office XML 文本、索引与字面词项查询；PDF 文本仅在当前环境已有 `pypdf` 时可用。无 OCR、模型服务或常驻监听。

## 命令

```text
python "<skill>/scripts/folderdb.py" preflight --root "<root>"
python "<skill>/scripts/folderdb.py" preflight --root "<root>" --probe-write
python "<skill>/scripts/folderdb.py" status --root "<root>"
python "<skill>/scripts/folderdb.py" scan --root "<root>"                 # 默认 full，重新哈希
python "<skill>/scripts/folderdb.py" scan --root "<root>" --mode fast
python "<skill>/scripts/folderdb.py" scan --root "<root>" --parser-timeout 30
python "<skill>/scripts/folderdb.py" scan --root "<root>" --batch-size 25   # 建立/推进一个可恢复任务
python "<skill>/scripts/folderdb.py" scan --root "<root>" --batch-size 25 --job-id "<uuid>"  # 恢复任务
python "<skill>/scripts/folderdb.py" refresh --root "<root>"              # fast 扫描并重建导航/HTML
python "<skill>/scripts/folderdb.py" refresh --root "<root>" --full       # full 扫描并重建导航/HTML
python "<skill>/scripts/folderdb.py" refresh --root "<root>" --batch-size 25
python "<skill>/scripts/folderdb.py" refresh --root "<root>" --batch-size 25 --job-id "<uuid>"
python "<skill>/scripts/folderdb.py" retry-parsing --root "<root>" --limit 25 --parser-timeout 30
python "<skill>/scripts/folderdb.py" migrate --root "<root>"              # schema 1 迁移预览
python "<skill>/scripts/folderdb.py" migrate --root "<root>" --execute    # 备份后迁移
python "<skill>/scripts/folderdb.py" dump --root "<root>" --limit 5
python "<skill>/scripts/folderdb.py" dump --root "<root>" --file-id "<id>" --text-offset 0 --text-limit 12000
python "<skill>/scripts/folderdb.py" navigate --root "<root>" --folder "10-项目交付/客户A" --folder-offset 0 --file-offset 0 --limit 20
python "<skill>/scripts/folderdb.py" lifecycle --root "<root>" --file-id "<id>" --business-state archived --reason "用户确认业务归档" --execute
python "<skill>/scripts/folderdb.py" lifecycle-list --root "<root>" --due-before "<YYYY-MM-DD>" --limit 20 --offset 0
python "<skill>/scripts/folderdb.py" history --root "<root>" --file-id "<id>" --limit 20 --offset 0
python "<skill>/scripts/folderdb.py" snapshot --root "<root>" --file-id "<id>" --execute
python "<skill>/scripts/folderdb.py" restore-copy --root "<root>" --file-id "<id>" --sha256 "<登记快照哈希>" --dst "恢复资料/新副本.pdf" --execute
python "<skill>/scripts/folderdb.py" annotate --root "<root>" --input "<annotations.json>"
python "<skill>/scripts/folderdb.py" index --root "<root>"
python "<skill>/scripts/folderdb.py" query --root "<root>" --query "预算 项目A" --limit 20 --offset 0
python "<skill>/scripts/folderdb.py" query --root "<root>" --folder "项目A/合同" --semantic-status reviewed
python "<skill>/scripts/folderdb.py" pending --root "<root>" --limit 100 --offset 0
python "<skill>/scripts/folderdb.py" duplicates --root "<root>" --kind file --limit 100 --offset 0
python "<skill>/scripts/folderdb.py" duplicates --root "<root>" --kind directory --limit 100 --offset 100
python "<skill>/scripts/folderdb.py" view-save --root "<root>" --name "待复核项目" --classification-status review
python "<skill>/scripts/folderdb.py" view-list --root "<root>"
python "<skill>/scripts/folderdb.py" query --root "<root>" --view-name "待复核项目" --limit 50 --offset 0
python "<skill>/scripts/folderdb.py" view-delete --root "<root>" --name "待复核项目"
python "<skill>/scripts/folderdb.py" plan-check --root "<root>" --plan "<plan.json>"
python "<skill>/scripts/folderdb.py" apply --root "<root>" --plan "<plan.json>"
python "<skill>/scripts/folderdb.py" apply --root "<root>" --plan "<plan.json>" --execute
python "<skill>/scripts/folderdb.py" directory-plan --root "<root>" --src "原子目录" --dst "10-项目交付/新子目录" --reason "有证据的归属理由"
python "<skill>/scripts/folderdb.py" directory-plan --root "<root>" --src "原子目录" --dst "10-项目交付/新子目录" --reason "有证据的归属理由" --save-as "directory-001.json"
python "<skill>/scripts/folderdb.py" directory-plan-check --root "<root>" --plan "<root>/.filedb/plans/directory-001.json"
python "<skill>/scripts/folderdb.py" directory-apply --root "<root>" --plan "<root>/.filedb/plans/directory-001.json" --execute
python "<skill>/scripts/folderdb.py" rollback --root "<root>" --run-id "<uuid>"
python "<skill>/scripts/folderdb.py" rollback --root "<root>" --run-id "<uuid>" --execute
python "<skill>/scripts/folderdb.py" quarantine --root "<root>"
python "<skill>/scripts/folderdb.py" quarantine --root "<root>" --execute
python "<skill>/scripts/folderdb.py" restore-quarantine --root "<root>" --run-id "<uuid>"
python "<skill>/scripts/folderdb.py" restore-quarantine --root "<root>" --run-id "<uuid>" --execute
```

- `preflight/status/dump/search/plan-check/quarantine` 只读预览；`quarantine --execute` 仅在用户明确要求去重且范围/规则清楚后，将完全重复项移动到隔离区。`restore-quarantine` 默认只预检；所有 `--execute` 都需由 Skill 的交互授权门控制。`--probe-write` 只测试自建临时文件。探针不能替代模型检查。
- `status` 识别 new/managed/incomplete/foreign/incompatible/corrupt/unsafe，并做廉价快照检查，不发布清单；托管库会附带一个运行中的 `pending_scan_job`（如有）。
- `scan` 创建/增量更新清单、重新核对源哈希（`--mode fast` 仅复用大小和修改时间未变文件的哈希），并输出重复组数量及最多 100 组预览。所有重复组保存在 SQLite 的 `duplicate_groups` 表，可用 `duplicates --kind file|directory|all --offset N --limit 1..100` 全量分页。文件重复按 SHA-256；目录组比较完整递归路径/文件哈希/空目录结构，隐藏/排除项、链接、扫描错误或哈希不稳定会阻止对应父目录进入重复组。`refresh` 默认执行 fast 盘点并重建 Markdown/HTML；`refresh --full` 会重新核验所有源哈希。默认抽取上限每文件 64 MiB、缓存 200,000 字符，`--max-bytes/--max-chars` 可按能力调整；上限不是系统资源沙箱。`--reextract` 重建同内容缓存，解析配置改变时也会重提取。
- `--batch-size 1..100` 开始或推进可恢复的全量扫描任务；返回 `state=running` 时保存 `job_id`，恢复时用相同根目录、模式、抽取上限和 `reextract` 选项再次调用并传入 `--job-id`。全量扫描分为 process、verify、ready 阶段，输入和解析暂存于同一个 `.filedb/catalog.sqlite` 的 `jobs/job_items/job_directories/job_skipped` 表；`status.pending_scan_job` 显示活跃任务。文件与目录清单在任务完成并通过源快照/内容哈希复核前不发布；检测到目录、源或数据库修订冲突则返回 `state=stale`，保留旧清单并要求启动新扫描。大任务的最终原子发布仍可能耗时；本地数据库的暂存会暂时占用额外磁盘空间。宿主进程退出后不会自动运行，需显式恢复。`refresh` 返回 `scan_pending` 时不生成新索引，完成后再次用同一 job ID 调用才会重建导航。
- `--parser-timeout 1..600` 设置 PDF/Office XML 子进程的硬墙钟上限，默认 30 秒；超时记录为 `read_error` 并给出超时原因。UTF-8 文本由字节和缓存字符限制，不单独启动超时子进程。
- `dump` 的文件清单用 `--offset/--limit` 翻页；缓存正文用 `--text-offset/--text-limit` 翻页。`text_next_offset` 为 null 只说明缓存读完，不保证原文完整。读取前实时哈希，过期时不返回旧正文/标注。
- `dump` 默认每批5文件，多文件列表每条正文最多2000字符；单文件模式正文默认12000、上限24000字符，避免整库内容一次进入上下文。
- `index` 生成根目录 AI_INDEX/AI_README、可选人类 README、离线 HTML、manifest、集中式目录页和大目录分片。子目录不写 AI_INDEX。保护用户文件和已人工修改的索引；旧版生成导航须同时匹配登记哈希及生成标记后才移动到备份目录，不删除。
- `search/query` 用缓存字面词项和元数据加权，空格分词，中文可用“预算”“采购”等词项；不是 embedding/JEV/语义推理。支持目录、标签、文档类型、分类/抽取/语义状态、问题原因筛选；`--offset/--limit` 分页且 `total` 是匹配总数。结果重新校验来源，过期命中标记待重扫，不展示旧摘要。`pending` 对读取/分类问题分页并提供原因、覆盖和下一步。
- `view-save` 将白名单内的查询词和筛选条件保存到当前库 SQLite；`view-list` 列出，`query --view-name` 分页执行，`view-delete` 删除该视图定义。视图不复制文件或改变分类，未知字段、任意 SQL 和不合法筛选会被拒绝；与 `--view-name` 同时传直接筛选会阻断，避免隐式合并。
- `文件知识库.html` 从 SQLite 导出完整活动清单元数据，不嵌入缓存全文；固定模板采用 JSON 数据节点和 `textContent`，不加载网络资源，不提供文件修改动作。HTML 是生成快照，不会自行检测磁盘变化。
- 所有修改命令有合作式单写锁。残留 LOCK 可能是活任务或崩溃，先确认任务结束再处理，不自动删除锁。
- `apply/rollback` 默认不改文件，`--execute` 是智能体在获得真实授权后使用的执行开关，JSON 计划本身不是授权。
- `quarantine` 根据最新扫描报告为每个精确重复组保留一个副本，人工位置锁定优先；目录组先于文件组，避免嵌套重复移动。执行前重新验证源哈希/目录清单，使用库内同卷 `rename` 移至 `.filedb/quarantine/<run-id>/`，登记为 `quarantined`，不删除业务文件。隔离项目不参与普通 dump/search/index；指定 file_id 的 dump 只返回隔离状态、原路径和 run-id。`restore-quarantine` 验证隔离对象未变、原位置空闲后将其移回。
- 隔离目录和 run 日志没有自动保留期限。永远不为“释放空间”或重复项过期而自动删除；用户明确要求删除时需另列准确路径/数量并取得针对删除动作的明确同意。
- 移动默认尊重 `location_locked`；只有用户明确要求重整这些文件时加 `--include-locked`。脚本不自动从这个标记推断用户授权。

`query/view-save` 可用 `--business-state`；保存视图仍是白名单条件。版本及生命周期命令的默认预览/执行、业务状态、当前版本组唯一约束、源新鲜度、复核日期和正文快照边界见 [lifecycle.md](lifecycle.md)。`lifecycle --execute` 只修改元数据；`snapshot --execute` 必须来自用户明确的保留可恢复版本请求，`restore-copy --execute` 必须来自明确恢复到该位置的请求；索引维护不自动包含正文复制。

去重计划读取 duplicate_groups 表中的全部组，不从首屏扫描预览推断完整任务。位置锁和已确认版本组成员优先保留；一个重复组存在多个受保护的业务版本/位置时只报告，不自动隔离其中一个。同名“最终版”或相似文本不是版本组确认，也不是重复依据。
- 标准输出为 UTF-8 JSON。退出 0 成功，1 执行失败（查 run），2 校验/访问失败。跨文件操作不宣称事务原子性。

## 标注输入示例

用扫描返回的真实 file_id 和 sha256 替换示例值。完整 taxonomy 作为一个对象导入；修改定义或类别需要新 version。`files` 可分批，每批复用同版完整 taxonomy。

```json
{
  "taxonomy": {
    "version": "1",
    "categories": [
      {"id": "project-a-research", "label": "项目A调研", "path": "项目A/调研", "definition": "以项目A决策为主要用途的调研资料", "includes": ["访谈记录"], "excludes": ["已签合同"]}
    ]
  },
  "files": [
    {
      "file_id": "扫描得到的UUID",
      "source_sha256": "扫描得到的64位哈希",
      "title": "项目A采购访谈",
      "summary": "采访记录讨论了设备采购的预算要求。",
      "category_id": "project-a-research",
      "classification_status": "confident",
      "classification_basis": ["content"],
      "semantic_status": "reviewed",
      "tags": [{"facet": "topic", "id": "budget", "label": "预算"}],
      "creator": null,
      "business_date": null,
      "relations": [],
      "read_coverage": "已读完整UTF-8文本；无附图",
      "evidence": [{"field": "category_id", "locator": "text:lines-3-8", "basis": "正文明确为项目A采购调研"}, {"field": "topic", "locator": "text:lines-3-8", "basis": "正文明确讨论采购预算"}]
    }
  ]
}
```

必填：file_id、source_sha256、title（最多300字符）、summary（最多4000字符）、category_id（可null）、classification_status、tags（最多64）、evidence、read_coverage。标签需 facet/id/label；证据需 field/locator/basis。状态 `confident/review/unknown`；confident 须有类别。可选 confidence 0..1 仅为模型建议，不是准确率。

classification_basis 必填，从 path/filename/content/user 选择；semantic_status 必填，为 unreviewed/partial/reviewed/unavailable。confident 分类必须有 category_id 的 content/user 定位，reviewed 必须有正文依据。以上示例的 UUID/哈希须替换为本库扫描结果，不能直接照抄。已生效个人场景/词表时，顶层还须添加 `policy_revisions`（由 policy-get/status 读取已生效项 UUID），且预算词条先独立建立；旧库无治理配置时仍兼容原标注。

新增个人配置命令：`policy-template/policy-get/scenario-check/scenario-apply/vocabulary-check/vocabulary-apply/vocabulary-list/vocabulary-resolve/policy-history`。check/apply 默认只读预览；执行必须 --execute、变更理由与当前 --expected-revision。具体契约见 [场景](scenarios.md) 与 [词表](vocabulary.md)。`query` 新增 --tag-facet、--file-format、--literal；保存视图支持前两项。dump 保留原 profile，并在来源新鲜时提供 effective_tags/vocabulary_version；查询和页面提供公共词表投影。

可补充 Dublin Core 相关 creator/business_date/source/relations；未知值 null。结构校验不验证每个 locator 在原文中真实存在，智能体必须回看来源，行为验收需真人/独立任务样本。

同一文件在当前磁盘和扫描记录中的哈希都需匹配，才接受标注。内容变化清空旧标注；taxonomy 修订只把受影响原分类记 review；路径人工变动保留元数据、设位置锁并将原主分类记待复核。

## 文件操作计划

以下 v1 仅用于单文件。整个目录的移动或重命名必须使用下方 v2 与目录命令，不把 v2 交给文件级 `plan-check/apply`。

```json
{
  "version": 1,
  "root": "用户选择并规范化的绝对库根路径",
  "operations": [
    {"file_id": "真实UUID", "src": "收件箱/访谈.txt", "dst": "项目A/调研/采购访谈.txt", "sha256": "当前真实哈希", "reason": "用户认可的调研主归属和可复核文件标题"}
  ]
}
```

路径为 `/` 分隔的库内相对路径，不含隐藏/保护目录和 `..`。一项一个文件，无覆盖、同名、循环/链式或仅大小写改名。source_sha256 在标注中，sha256 在计划中，均来自实际字节。

### 目录操作计划 v2

```json
{
  "version": 2,
  "root": "规范化的绝对库根路径",
  "operations": [
    {"src": "原子目录", "dst": "10-项目交付/新子目录", "manifest_sha256": "由directory-plan生成的完整树SHA-256", "reason": "有证据的归属理由"}
  ]
}
```

`directory-plan` 先检查库快照与未完成扫描，再计算全部后代文件字节哈希和空目录结构；默认返回计划与预检，不写文件。加 `--save-as` 只在 `.filedb/plans/` 新建一个 JSON，不覆盖，不改业务资料。每次生成一个目录操作，多目录可在不嵌套、不连锁、不循环的前提下合并 operations，然后重新 `directory-plan-check`；不得虚构 manifest 哈希。

目录含隐藏项、依赖目录、链接或无法完整盘点项时拒绝生成完整树计划；保留原位只索引。依赖探测在有限读取预算内报告工程标记、目录内部文字引用和库内其他活动文本文件的入站路径引用；跳过数量及限制随计划预检返回。命中时由 AI 审查调整范围；无命中不证明外部快捷方式、动态路径、编码链接或应用依赖不存在。不要自动修改正文内部引用。

`directory-apply` 默认只预检，`--execute` 才同卷移动目录并更新后代路径与 file_id 映射；人工位置锁需要用户已明确要求重整这些项目后再用 `--include-locked`。目录和后代文件不能在同一阶段混合执行；目录阶段完成后 `refresh`，下一阶段重新生成文件计划。恢复统一使用 run-id 与 `rollback`，不以复制索引替代恢复日志。

### 分层导航与完成统计

`navigate` 为只读物理目录导航，默认根目录；`--folder` 是精确库内相对目录路径，不是编号搜索。返回当前目录、父级面包屑、立即子目录、直接文件及 file_id，不含原文或摘要。`children_next_offset` 用 `--folder-offset` 继续，`files_next_offset` 用 `--file-offset` 继续，两者分别分页。`direct_files` 与 `subtree_files` 不同，空目录仍可导航；`index_page` 只指向已登记且存在的目录页。

先用 `status` 判断时效；navigate 是数据库快照，不能证明源文件新鲜。已知 file_id 用 `dump` 找当前路径并校验内容，再核验原文；未知位置用 `query` 检索。`status.classification_record_missing`（兼容旧字段 pending_classification）只统计无档案项；`classification_review_required` 统计尚非 confident 的所有活动文件，包括 inherited；`semantic_review_required` 统计尚非 reviewed 的活动文件，包括未建档、partial 和 unavailable。三者不能互相替代。

## 库识别与清单

SQLite schema=2，application_id=0x464B4231，meta.skill=folder-knowledge-base；不依据 Markdown 外观识别。`files` 保存稳定 UUID、当前/原始路径、字节哈希、大小/mtime、抽取内容及覆盖、标注、人工位置锁、active/missing；`directories` 保存空/非空目录；`indexes` 保存所有生成入口/索引/HTML/manifest 哈希；`categories/tag_vocabulary/file_tags/file_evidence/file_relations/issues/saved_views/jobs/duplicate_groups` 保存结构化词表、标注证据、问题队列、任务与重复组分页数据。

0.6.0 增加兼容表 `file_events/file_management/file_snapshots`，仅在获授权的 writer 连接中建立；旧 schema-2 库只读时查询仍正常，历史缺失明确返回。新历史从观察或 tracking_baseline 开始，不伪造既往记录；存储布局和接口见 lifecycle.md。

有唯一同哈希“本轮旧路径消失、新路径出现”时推断移动并保留 ID。副本歧义或移动同时改内容不能可靠识别，按缺失+新增并交用户复核。历史 missing 与新同哈希不自动绑定。文件首次出现新路径但没有唯一迁移匹配时新建 ID。

missing 只表示离开当前扫描快照，可能删除、移到库外或进入排除范围，不能仅据此断言磁盘物理删除。`status.needs_index` 还检查清单版本和缺失导航文件；没有源文件变化也可能需要重建索引。人工修改索引只报冲突，不当作新规则直接执行。
