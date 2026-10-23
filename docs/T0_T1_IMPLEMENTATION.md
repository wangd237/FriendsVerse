# Coding T0–T1 Implementation

**阶段**：最小双人垂直切片（不是完整的 FriendsVerse）  
**分支**：feat/story-prototype-t0-t1  
**日期**：2026-10-23

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

也可以在当前 GitHub 仓库的 Actions secrets 中配置以上字段后，手动运行 **T1 live LLM validation (manual)**。该工作流不会因普通 push 自动消耗真实模型 Token。它验证两集均来自 live 适配器、均有真实对白和可恢复的个人记忆；角色辨识度和是否真正利用前情仍需人工审查剧本。

## T0/T1 验收边界

| 检查项 | 当前实现 | 验证口径 |
|---|---|---|
| 动作 Schema 与规则校验 | 已编码 | pytest |
| 现场可见性、私有记忆 | 已编码 | pytest |
| 状态读写、版本检查与事务 | 已编码 | pytest |
| 两集 FakeClient 连续运行 | 已编码 | Actions fake smoke |
| OpenAI-compatible client 的格式错误重试 | 已编码 | mock transport test |
| 两集真实 LLM 自主互动 | 需要有效密钥实际运行 | 手动 live workflow；未完成则不能宣称 T1 通过 |
| 结构化承诺抽取与关系更新 | 未实现 | T2+，目前只保留目击对话记忆 |
| 六人世界、三时段、真正的剧集剪辑与七集验收 | 未实现 | T2/T3 |

## 有意推迟的工作

现在仅验证两名角色的会面与记忆。世界只有一个真实社交场景，脚本是原始对话格式，并未实现 **Character→Commitment** 结构化抽取、独立主观解释、关系变化引擎或长篇叙事编辑。因此本版本不应被当作成熟的 AI 情景喜剧生成器。

只有完成真实 T1 并明确其局限后，再扩展六位角色和 World Engine。切勿提前引入 DAG、多 Agent 主管、GraphRAG、复杂记忆向量库或视频网站前端。
