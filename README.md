# AI 管理本地文件知识库

一个面向 Codex 的本地文件知识库 Skill。它帮助用户在自己指定的文件夹中盘点、分类和检索资料，并维护本地 SQLite 清单、AI 导航文件和人类可读的 HTML 快照。

English: A Codex skill for organizing, maintaining, and searching personal local file libraries. It uses local scripts and does not depend on Jevbox or MCP.

> 当前仓库用于私有预发布。独立发布许可尚未在此仓库声明；公开前请确认发布权限并补充适用的 `LICENSE`。

## 能做什么

- 按用户指定的目录、场景和权限范围建立或维护本地文件知识库。
- 盘点文件与精确重复，记录内容哈希、读取覆盖、分类状态和来源定位。
- 使用场景化分类、受控词表与多维标签整理资料，并保留待确认项。
- 生成 `.filedb/catalog.sqlite`、`AI_README.md`、`AI_INDEX.md`、目录导航和离线 HTML 页面。
- 通过关键词、元数据筛选和分页定位候选资料；回答时要求回到当前原文件核对并标明来源。
- 根据实际变化增量更新索引；支持文件生命周期记录和可恢复的改名/移动操作。

## 安全边界

- 操作前先确认目标目录、任务模式、内容读取范围和本轮允许的写入/文件操作。
- 只建库或查询不会自动扩大为原文件改名、移动或删除。
- 精确重复项可移入库内隔离区并记录原路径；不自动永久删除。删除必须取得针对具体目标的明确同意。
- 目录改名/移动先生成并校验计划；证据不足时保留原位置并标记待确认。
- 本地读取不等于允许把资料发送给外部模型或服务；具体内容处理范围取决于用户授权和当前 Agent 环境。

## 环境要求

- Codex 或兼容 Agent：能读取用户指定的本地目录，并在用户授权后执行本地脚本/写入索引。
- 使用内置脚本需要 Python 3.10 或更高版本及 SQLite FTS5 支持。PDF 文本提取需要当前环境已安装 `pypdf`；其他格式能力和限制见 [`references/contracts.md`](references/contracts.md) 与 [`references/capabilities.md`](references/capabilities.md)。
- 不需要 Jevbox、MCP 服务或本 Skill 自带的模型/API 密钥。Skill 不安装第三方依赖；可选解析器应由用户按需配置。

## 安装到 Codex（Windows）

仓库公开后，在 PowerShell 中运行：

```powershell
$codexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $env:USERPROFILE ".codex" }
$skillPath = Join-Path $codexHome "skills\folder-knowledge-base"
git clone "https://github.com/felixwonggogogo/folder-knowledge-base-management-Skill.git" $skillPath
```

如果你已经安装过此 Skill，请先备份本地修改，再按版本更新；不要对已有目录重复 `git clone`。安装后开始一个新 Codex 对话；若 Skill 未出现，再重启 Codex。

## 使用

可在 Codex 中明确调用 `$folder-knowledge-base`，并说明目标目录与需求，例如：

```text
使用 $folder-knowledge-base 查询 D:\资料库 中关于项目预算的文件；先检查索引状态，回答时给出文件路径和原文位置。
```

新建知识库时，Skill 会先澄清目录、场景、读取范围和允许的副作用。首次能力检查示例：

```powershell
python "$skillPath\scripts\folderdb.py" preflight --root "D:\资料库"
```

完整命令和工作流程见 [`SKILL.md`](SKILL.md)、[`references/workflows.md`](references/workflows.md) 和 [`references/navigation.md`](references/navigation.md)。

## 检索能力与限制

- 当前本地脚本以字面词项/FTS、词表别名和元数据筛选为主；不应把它描述成通用向量语义搜索。
- HTML 页面是生成时的静态快照，不会自行监听磁盘变化，也不包含未导出的全文。
- 读取、OCR、格式解析和回答能力受当前 Agent、系统工具及已安装解析器限制；扫描过不代表全文已理解。
- 没有常驻 watcher 时，文件改动通常在下一次状态检查或维护调用时发现。维护细节见 [`references/synchronization.md`](references/synchronization.md)。

## 版本与方法来源

- 当前 Skill 版本：**0.7.0**（与 `SKILL.md` frontmatter 一致）。
- 分类、元数据、来源追溯、完整性与生命周期设计的来源和适用边界见 [`references/methodology.md`](references/methodology.md)。
- 更新记录见 [`CHANGELOG.md`](CHANGELOG.md)。
