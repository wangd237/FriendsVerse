# FriendsVerse

> 一部由多个 AI 角色自主生活、持续发展人物关系的轻喜剧情景剧。  
> *A character-driven, autonomous AI sitcom — one episode at a time.*

## 项目状态

**阶段：T0 双角色原型已实现并通过 CI；T1 真实 LLM 仍待实际验收**（2026-10-23）。

本仓库已经加入第一阶段**两角色 T0/T1 最小代码**，包括 CLI、动作校验、独立记忆、SQLite 持久化和可选真实 LLM 适配器。尚未实现六角色完整故事世界、关系演化引擎或正式剧集剪辑。确定性 FakeClient 测试不代表真实 LLM 已通过验收。

## 产品概念

观众不需要扮演主角或指挥 Agent，而是观看六位拥有独立性格、记忆和社会关系的虚拟角色，在共享社区中自主行动、交往和生活，并将真实发生的模拟事件整理成轻松搞笑的**情景剧剧本**。

- **观看体验**：轻松搞笑、群像关系、有延续性的原创剧情。
- **推进方式**：用户手动点击「生成下一集」，而不是后台持续生成。
- **核心目标**：让观众因为关心人物关系的发展，主动想继续看下一集。
- **产品原则**：世界与角色产生事件；剧集整理器只选取、编排已经发生的事实，不能凭空改写角色行动。

当前方案以六位《老友记》人物为私人粉丝实验的初始人设参考。若公开运营、对外发行或商业化，需处理角色、名称、剧照、台词、商标及演员肖像等授权问题，或切换为原创角色 IP。本仓库不包含受版权保护的电视剧素材。

## 文档入口

- [产品需求文档（PRD）](docs/PRD.md)：产品定位、用户旅程、功能范围、规则、验收与阶段计划。
- [产品决策记录](docs/DECISIONS.md)：已确认决策、设计原则及尚未确定的问题。
- [Story Prototype 详细产品规格](docs/STORY_PROTOTYPE.md)：首个七集原型的角色、事件、叙事链路、关系证据与验收。
- [Character Design：六人角色与关系](docs/CHARACTER_DESIGN.md)：角色动机、行为倾向、15 组初始关系、独立认知及人物验证情境。
- [World & Interaction Design](docs/WORLD_INTERACTION.md)：社区场景、时段推进、主动社交、会面、有限对话与跨集连续性。
- [Story Prototype Technical Design](docs/STORY_PROTOTYPE_TECHNICAL_DESIGN.md)：T0–T3 工程模块、数据协议和实施顺序。
- [Coding T0–T1 实施说明](docs/T0_T1_IMPLEMENTATION.md)：已实现范围、安装运行、真实 LLM 验收与未完成能力。
- [Story Prototype Technical Design](docs/STORY_PROTOTYPE_TECHNICAL_DESIGN.md)：推荐技术栈、模块/数据边界、执行及持久化流程、T0–T3 验收计划。

## 运行最小双人演示

Python 3.11+：

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m friendsverse init --db friendsverse.db
python -m friendsverse next --db friendsverse.db --provider fake
python -m friendsverse next --db friendsverse.db --provider fake
python -m friendsverse inspect --db friendsverse.db
~~~

**注意：fake 输出是固定台词，仅用于 T0 运行/记忆测试。** 真实 T1 请配置本机环境变量或当前仓库 GitHub Actions secrets 的 LLM_API_KEY、LLM_MODEL_ID（可选 LLM_BASE_URL），运行两次 `--provider live`。详细步骤见 [实施说明](docs/T0_T1_IMPLEMENTATION.md)。

## 当前里程碑

1. **产品需求基线**：固化定位、观看方式、优先级和核心用户流程（文档阶段）。
2. **Story Prototype**：T0 两角色规则/记忆闭环完成；T1 真实模型效果待验收；T2 六人单集和 T3 七集验证尚未实现。
3. **MVP Web 应用**：剧集大厅、剧本阅读器、关系视图、手动逐集推进。
4. **体验验证与迭代**：基于角色辨识度、幽默度、连贯性、关系可信度和追剧意愿改进。

具体范围与验收口径请以 [PRD](docs/PRD.md) 为准。

## 文档维护约定

- **PRD 作为唯一当前需求基线**。修订时直接更新同一文件，修改版本号、日期与变更摘要。
- 已确认的产品选择记入 [DECISIONS](docs/DECISIONS.md)，避免同一议题被无意反复改变。
- 新想法先标为「待验证 / 待决策」，不自动升级为 P0。
- 功能实现状态（未开发 / 开发中 / 已验证）与需求优先级（P0 / P1 / P2）明确区分。
- 后续讨论中如明确提出修改，可直接经 GitHub 更新；涉及重要产品取舍时先征求确认。不执行无人值守的后台更新。

## 参考原型（调研对象，非当前项目依赖）

- [social-agent-sim](https://github.com/marcopatzelt/social-agent-sim)：Tick 驱动的多角色社会模拟。
- [Covel](https://github.com/ackness/covel)：角色、游戏世界、记忆与插件式叙事运行时。

目前 T0/T1 采用 Python、Pydantic、SQLite 和 OpenAI-compatible API 的最小实现；后续是否复用其他框架仍可在实测后评估。
