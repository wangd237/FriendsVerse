# Coding T0–T1 Implementation

**阶段**：最小双人垂直切片（不是完整的 FriendsVerse）  
**实现分支**：feat/story-prototype-t0-t1（已通过 PR #1 合并到 main）  
**更新日期**：2026-10-24

## 已实现

- 只有 Joey 与 Chandler 两个独立的 Character Agent，单个 evening 场景。各自 Persona、记忆和上下文隔离。
- 一次 LLM 决策只提出一个 Action，Runtime 校验 speak / wait / move_to / do(help_rehearse)，拒绝非法地点或不在场对话。
- 成功执行后记录带事件 ID 的原始对白/动作；仅在场角色记住本事件。
- 单独的候选世界快照 + SQLite 原子事务：发布成功才推进世界版本、插入新一集；失败不污染已发布世界。
- 简单剧本由实际已执行事件直接渲染；不虚构笑点/关系。
- CLI init / next / inspect，OpenAI-compatible 模型适配与本地 Pydantic JSON 动作校验。
- FakeClient + pytest 自动化规则测试与 GitHub Actions，另有手动真实模型验收 workflow。

## 安装和本地运行

Python 3.11+，在仓库根目录：

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m friendsverse init --db friendsverse.db
python -m friendsverse next --db friendsverse.db --provider fake
python -m friendsverse next --db friendsverse.db --provider fake
python -m friendsverse inspect --db friendsverse.db
~~~

**fake 为固定台词替身，只验证数据闭环，不是自主剧情能力证明。**

## T1：真实 LLM 的两集连续互动

**T1 技术验收已通过：** 2026-10-24 <https://github.com/wangd237/FriendsVerse/actions/runs/40078682932> 成功生成并提交两集真实模型对白，第二集接续第一集的排练主题，双方各读取到来自第一集的 4 条目击记忆。详见 [T1 真实验收报告](T1_LIVE_VALIDATION_REPORT.md)。该结果**不代表**关系演化或七集故事已完成。


在系统环境变量中设置以下两个必填字段（从不提交 API Key）：

- LLM_API_KEY：可用的模型服务 Key。
- LLM_MODEL_ID：服务提供的模型名称。
- LLM_BASE_URL：可选，兼容接口的 URL。

~~~bash
python -m friendsverse init --db friendsverse-live.db
python -m friendsverse next --db friendsverse-live.db --provider live
python -m friendsverse next --db friendsverse-live.db --provider live
python -m friendsverse inspect --db friendsverse-live.db
~~~

也可以在当前 GitHub 仓库设置 **Actions Secret** `LLM_API_KEY`。模型名称可以设置为仓库 **Actions Variable** `LLM_MODEL_ID`、同名 Secret，或者在手动运行时填写 `model_id` 输入参数。可选 `LLM_BASE_URL` 可以保存在 Actions Variable 或 Secret。

**2026-10-24 真实运行记录**：<https://github.com/wangd237/FriendsVerse/actions/runs/40076729623> 在环境检查阶段失败；日志中 `LLM_API_KEY` 与 `LLM_BASE_URL` 已存在，但 `LLM_MODEL_ID` 为空，因此 **没有发生真实模型调用、没有生成剧集**。这一轮修改新增模型 ID 的手动输入/Variables 回退，避免再次被无须保密的模型名称卡住。

配置后手动运行 **T1 live LLM validation (manual)**，可在 `Run workflow` 对话框填写模型名称。该工作流不会因普通 push 自动消耗真实模型 Token。它验证两集均来自 live 适配器、均有真实对白和可恢复的个人记忆，并检查第二集 `prior_memory_ids` 是否包含上一集的真实事件 ID。这能证明前情已经进入角色的输入上下文，**但不等于模型确实理解或利用了前情**；角色辨识度和前情引用的自然程度仍需人工审查剧本。

## 2026-10-24 主链路修正与验收证据

- 修复剧本位置一致性：角色可执行 move_to，事件在不同地点发生时，剧本按真实事件地点产生场景标题，不再硬编码全部发生在 Joey/Chandler 的公寓。
- 补充自动化测试：模拟两人先后移至走廊，然后真实在场交谈；检查事件的位置与剧本场景匹配。没有对白时显示角色所在的起始地点。
- 手动 T1 workflow 增加 `t1-live-review` 构建产物（JSON），保存两集**已经执行**的对白、动作、现场见证者、前情记忆来源 ID 及被拒绝的动作。
- **可验证的结论范围**：自动检查第二集收到第一集记忆；必须由阅读真实对话的人判断是否有自然的前情回应。不可将仅注入记忆误称为模型理解或关系演化。
- **历史说明**：在本次修正刚合并时，T1 尚未运行。此项状态已由 2026-10-24 成功的真实验收 Run #40078682932 替代；当前已经具备可复盘的真实剧本与事件证据。
- 这一轮只补齐 T1 的一致性和可观察性，没有增加世界模拟、长期关系演化或新 Agent 架构。

## T0/T1 验收边界

| 检查项 | 当前实现 | 验证口径 |
|---|---|---|
| 动作 Schema 与规则校验 | 已编码 | pytest |
| 现场可见性、私有记忆 | 已编码 | pytest |
| 状态读写、版本检查与事务 | 已编码 | pytest |
| 两集 FakeClient 连续运行 | 已编码 | Actions fake smoke |
| OpenAI-compatible client 的格式错误重试 | 已编码 | mock transport test |
| 两集真实 LLM 自主互动 | **已运行并通过基础技术验收** | [Run #40078682932](https://github.com/wangd237/FriendsVerse/actions/runs/40078682932) 和 [评估报告](T1_LIVE_VALIDATION_REPORT.md)；仅说明对话与跨集上下文，不证明关系演化 |
| 结构化承诺抽取与关系更新 | 未实现 | T2+，目前只保留目击对话记忆 |
| 六人世界、三时段、真正的剧集剪辑与七集验收 | 未实现 | T2/T3 |

## 有意推迟的工作

现在仅验证两名角色的会面与记忆。世界只有一个真实社交场景，脚本是原始对话格式，并未实现 **Character→Commitment** 结构化抽取、独立主观解释、关系变化引擎或长篇叙事编辑。因此本版本不应被当作成熟的 AI 情景喜剧生成器。

真实 T1 已完成基础技术验证，局限已记录在 [T1 真实验收报告](T1_LIVE_VALIDATION_REPORT.md)。下一步可以按报告提出的最小 T2 边界扩展六位角色和 World Engine。切勿提前引入 DAG、多 Agent 主管、GraphRAG、复杂记忆向量库或视频网站前端。
