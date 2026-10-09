# 方法依据

## v0.7 个人场景与词表补充

| 来源 | 本技能具体采用 | 适用边界 |
|---|---|---|
| [DCMI 类型词表](https://www.dublincore.org/specifications/dublin-core/dcmi-type-vocabulary/) 与 [元数据](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) | 基础资源类型；资料业务类型、格式、主题、来源分开 | 合同/报告是本技能扩展；按证据使用，不预填所有字段 |
| [W3C SKOS](https://www.w3.org/TR/skos-primer/) | 标准名、别名、范围定义、上下位/相关关系和变更说明 | JSON/SQLite 轻量实现；停用替代与执行修订为工程规则，不声明完整 SKOS 符合性 |
| [PARA](https://fortelabs.com/blog/para/) | 项目、持续事务、资源及归档的用途导向，作为可选场景参考 | 不作为所有库的强制树；归档由用户规则决定 |
| [Johnny.Decimal](https://johnnydecimal.com/documentation/areas-and-categories) | 较少较宽类别、编号浏览和自上而下/自下而上设计 | 使用本技能自己的稳定 ID；不声明完整 JD 编码实现 |
| [NN/G 渐进披露](https://www.nngroup.com/articles/progressive-disclosure/) | 首次展示常用场景与默认入口，进阶偏好按需展开 | 目录/读取/写入授权仍须明确 |
| [NN/G 卡片分类](https://www.nngroup.com/articles/card-sorting-definition/) | 用代表资料的个人反馈修订分类边界 | 单人轻量应用；不冒充多用户统计验证 |

内置 general 为本技能组合设计，优先保留有效结构和工程，再通过元数据视图浏览；格式目录树不是统一行业标准。模板、交互和执行分别见 [场景](scenarios.md) 与 [词表](vocabulary.md)。

| 方法 | 在本 Skill 的用法 |
|---|---|
| 文件计划/盘点 | 先确认用途和范围，再清点，最后设计目录和命名 |
| MECE/分面分类 | 主分类边界与覆盖检查，交叉属性多值标签 |
| 受控词表 | 稳定类别/标签 ID、同义词归一，认可后推广修正规则 |
| Dublin Core | 按需要选标题、创建者、日期、类型、格式、主题、标识、来源与关系 |
| W3C PROV | 文件版本为对象，扫描/分类/移动为活动，用户/模型/工具为参与者 |
| 完整性校验 | 内容哈希验证字节变化、操作后校验；不证明内容正确或备份可恢复 |
| 分层检索 | 根导航→局部索引/条件筛选→原文；全文词项基础，语义扩展可选 |
| 人工反馈/选择性分类 | 低置信留待确认；个案例外不自动变全局规则 |

索引是派生资料，变更使旧证据和摘要失效。归档不等于删除，保留期限由用户政策决定。不宣称满足完整档案标准。

参考：

- [NARA 文件计划](https://www.archives.gov/records-mgmt/scheduling/implementation)：用途、盘点与计划顺序；机构处置规则不直接套个人文件。
- [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/)：字段语义和资源关系。
- [W3C PROV Primer](https://www.w3.org/TR/prov-primer/)：对象、活动、参与者与派生关系。
- [Library of Congress 完整性管理](https://www.loc.gov/programs/digital-collections-management/inventory-and-custody/data-integrity-management/)：校验信息监控内容变化。

Jevbox 启发分层定位与原文证据读取。本 Skill 不依赖其服务器、JEV 模型网关或权限服务。

## 公开实践对照与本地适配（2026-10-09核对）

| 一手来源 | 可借鉴的方法 | 本 Skill 的具体适配与边界 |
|---|---|---|
| [Microsoft SharePoint 信息架构](https://learn.microsoft.com/en-us/sharepoint/information-architecture-modern-experience) | 全局/局部导航、元数据、搜索共同设计；减少深层嵌套负担 | 导航从大类下钻小类；标签和保存视图支持交叉检索。普通文档优先较浅结构，不强制改变代码工程的目录。 |
| [SharePoint Document IDs](https://support.microsoft.com/en-us/sharepoint/admin/enable-and-configure-unique-document-ids) | 用标识定位文件，移动与复制需要不同身份处理 | 使用 UUID file_id＋当前 path＋字节哈希；改名/移动后追踪当前来源。手动移动且改内容、重复副本歧义不能可靠保留身份；本地库不具备 SharePoint 的永久链接服务。 |
| [Google Drive 文件搜索](https://support.google.com/drive/answer/2375114?hl=en) | 文本查询叠加类型等筛选，已知与未知位置各有入口 | 物理目录导航、关键词、分类、标签、读取状态组合；本地 helper 只做声明的字面/FTS 检索，不声称拥有 Drive 的自然语言搜索。 |
| [Johnny.Decimal 区域与类别](https://johnnydecimal.com/documentation/areas-and-categories) | 较宽类别、区域/类别编号，降低归档决策成本 | 借鉴稳定编号＋可读名称，不把严格的十进制层级限制强加所有库，也不宣称我们的两位编号就是完整 Johnny.Decimal。 |
| [Tiago Forte PARA](https://fortelabs.com/blog/para/) | 按正在实现的目标和责任组织资料，区分项目、责任、资源、归档 | 工作库可选 PARA 结构，主题研究库不必套用；活跃/归档可用已有 business_state 与视图表达，归档不触发删除。 |
| [DCMI Metadata Terms](https://www.dublincore.org/specifications/dublin-core/dcmi-terms/) | 标识、标题、来源、关系、类型和主题具有不同含义 | 分开 category_id/file_id/path/hash；附件、版本、格式导出分别记录关系，不用文件名代替证据。 |
| [Library of Congress 完整性管理](https://www.loc.gov/programs/digital-collections-management/inventory-and-custody/data-integrity-management/) | 尽早建立文件及聚合层校验信息，记录核验日志 | 文件哈希与目录树清单用于计划/执行/恢复核验；这些校验不替代独立资料备份、恢复演练或内容正确性判断。 |

以上是方法启发与本地适配，不声称实现这些产品的权限、合规、云同步或搜索服务。持续维护依靠真实状态检查与用户反馈；一次合成测试不能证明真实库的分类和检索质量。具体决策、操作与引用流程见 [navigation.md](navigation.md)。
