# 独立词表、检索与修订

SQLite meta.policy_vocabulary 的 document 为生效来源；tag_vocabulary 是兼容投影。JSON 是审阅/交换载体，不与数据库独立同时写。旧库无生效词表时按已有表及档案读取、并集合并别名，不执行只读迁移；进入治理前补齐定义并解决冲突。

## 词条契约

```json
{
  "version": "1",
  "terms": [{
    "facet": "topic", "id": "artificial-intelligence", "label": "人工智能",
    "aliases": ["AI"], "definition": "人工智能相关研究与应用主题",
    "broader": [], "related": [], "status": "active", "replaced_by": null
  }]
}
```

稳定身份为 `(facet,id)`；标准名称、别名、定义、同分面上位/相关词、active/deprecated 状态和替代 ID 分别管理。语义参考 SKOS，但本实现使用 JSON/SQLite，不声明 RDF/SKOS 完整符合性。停用/替代状态及修订门是本技能工程规则。

脚本校验非空/大小、同分面 ID/标准名/别名冲突、归一后的大小写/全半角冲突、缺失引用、同义替代/上下位循环、上位与相关关系冲突及深度上限64。不同分面允许同名；检索须指定分面或说明歧义。词义真实性、同义关系和证据由 AI/用户核对，脚本不把“机器学习”自动等同“人工智能”。related 关系仅供提示，不隐含自动传递。

新词优先检查已有 ID/名称/别名/定义；明显已有词直接复用，确实新概念形成候选。用户确认本库通用规则后可在已授权元数据维护范围应用，不逐个审批确定词条。疑似同义、缩写多义、主题不明时询问。内置主题词表保持空，由证据建立；基础词表不是每文件必填字段。

## 命令

```text
policy-get --root "<库>"
vocabulary-list --root "<库>" --facet topic --offset 0 --limit 100
vocabulary-resolve --root "<库>" --term AI --facet topic
vocabulary-check --root "<库>" --input "<词表JSON>"
vocabulary-apply --root "<库>" --input "<词表JSON>" --reason "用户认可的别名规则" --expected-revision "<预览的current_revision>" --execute
policy-history --root "<库>" --kind vocabulary --limit 20
policy-history --root "<库>" --revision "<历史修订UUID>"
```

首次生效 expected-revision 为 none。新版本只在内容变化时要求；重复导入同一配置不写入。词表输入可为单独对象或模板输出中的 vocabulary。检查旧库时必须保留已有所有词条 ID，不用基础模板直接覆盖旧库。历史 ID 不删除，用 deprecated 表达停用；确认同义合并才设置 replaced_by，最终目标必须 active。历史原始标注保持原 ID，查询/HTML 以生效规则投影标准名与替代 ID，原词 ID 在 original_tag_id 可追溯。

policy-get 默认只返回场景、修订与词表摘要，实际词条通过 vocabulary-list 分页读取；需要完整 JSON 审阅/交换时显式加 --include-vocabulary，不把全词表默认灌入每次检索上下文。

检查返回全部影响计数，文件预览最多100条并声明截断；实际复核标记覆盖全部受影响档案。改名称/增加别名更新导航与检索；定义/关系/替代/状态变化产生 vocabulary_review 待办，源文件不移动。场景分类待办独立计数。

应用保存新 UUID 修订、配置正文、理由、时间和历史，并使索引待更新。`policy-history` 分页读取全部记录；带 revision 可取得旧 document。需要恢复时导出旧 document、赋予新的 version、再次 check/apply，记录恢复理由；只恢复规则，不自动回滚历史文件操作或抹除已经产生的复核待办。

## 标注与查询

生效后 annotate 顶层必须带当前 policy_revisions，例如 scenario/vocabulary 两个 UUID（只有已生效项）；文件只引用 active 词条，名称及别名须与公共词表一致。不能通过标注改名/新增词条。确认复核后重新标注会消除该文件的词表待办，并绑定当前规则修订。内容变化仍按原流程重新读取。

`query --tag AI --tag-facet topic` 通过公共词表命中旧文件，无需给每个文件重写别名。唯一明确的关键词词条映射会在 query_expansions 中列明；跨分面多义时不自动展开，标签过滤会明确报错并提供匹配项。`--literal` 关闭关键词扩展。上下位/相关扩展默认不执行；AI 说明范围后分别查询并合并 file_id，不把更广范围的命中说成精确同义命中。

document_type 为业务资料类型，format 为字节格式，resource_type 为通用资源形态。旧 file_type 档案和 --document-type .pdf 查询兼容，不依据旧字段自动猜测/重写全部标签；复核时按证据迁入明确分面。新增 --file-format 独立格式筛选；保存视图支持 tag_facet/file_format。

HTML 只检索导出的元数据，显示当前场景与词表版本，提供资料类型、格式、主题筛选以及别名搜索；不检索未导出的全文、不监听磁盘。AI 回答仍核验当前源文件并标注路径与原文位置。
