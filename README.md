# FriendsVerse

> 一部由多个 AI 角色自主生活、持续发展人物关系的轻喜剧情景剧。  
> *A character-driven, autonomous AI sitcom — one episode at a time.*

## 项目状态

**阶段：T0/T1 已完成；T2 六人单日代码通过自动化测试；T3 七集连续实验已具备运行与证据导出入口。真实六人及七集故事质量仍待验收**（2026-10-24）。

本仓库已经加入第一阶段**两角色 T0/T1 最小代码**，包括 CLI、动作校验、独立记忆、SQLite 持久化和可选真实 LLM 适配器。T2 已加入六角色三时段的简化世界、事件驱动的有向关系更新与剧本输出；真实六人样片及更成熟的剪辑仍待验收。已完成首次真实 LLM 双集运行并验证跨集记忆输入（[验收报告](docs/T1_LIVE_VALIDATION_REPORT.md)）；但不代表六角色自主世界或剧集故事质量已经达到产品验收。

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
- [T1 真实 LLM 验收报告](docs/T1_LIVE_VALIDATION_REPORT.md)：真实双集剧本、Token、记忆延续、问题分析及 T2 入口建议。
- [T2 六角色端到端最小实现](docs/T2_MINIMUM_SLICE.md)：六人、三时段、自主行动、社会事件、关系更新、真实模型验收。
- [T3 七集连续实验](docs/T3_SEVEN_EPISODE_EXPERIMENT.md)：显式批量实验、可恢复状态、完整剧本与结构化评测证据。
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

## 运行六角色世界（T2）

```bash
python -m friendsverse init --mode ensemble --db friendsverse-six.db
python -m friendsverse next --provider fake --db friendsverse-six.db
python -m friendsverse inspect --db friendsverse-six.db
```

Fake 只用于验证工程链路。真实六角色剧情请使用 `--provider live`，或通过 [T2 ensemble live smoke](https://github.com/wangd237/FriendsVerse/actions/workflows/t2-live-validation.yml) 手动运行后查看事件/剧本产物。

## 运行七集连续实验（T3）

```bash
python -m friendsverse init --mode ensemble --db season.db
python -m friendsverse season --provider fake --days 7 --actors-per-period 3 --db season.db --out season-review
python -m friendsverse report --db season.db --out season-review
```

`season` 是专门的、由用户主动发起的七集实验批处理；普通 `next` 仍仅推进一集。Fake 只验证工程链路。真实实验可以手动运行 [T3 seven-episode live experiment](https://github.com/wangd237/FriendsVerse/actions/workflows/t3-season-validation.yml)，查看 `t3-season-review` 产物并实际阅读剧本。

## 当前里程碑

1. **产品需求基线**：固化定位、观看方式、优先级和核心用户流程（文档阶段）。
2. **Story Prototype**：T0 规则/记忆闭环完成；T1 两集真实模型技术验收通过（故事质量尚未完成产品验收）；T2 六人单集最小代码已实现、真实质量待验收；T3 七集实验运行/报告机制已开发，真实七集和用户试读待验收。
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
