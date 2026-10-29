# 0005 生命周期拆成「特征定义」与「特征用量」两层（提议，v0.3 评审中）

v0.2 用一张状态机管「特征」。多目标场景下，一个特征可以在 CTR 模型里在用、同时在 CVR 模型里被提议移出：从某个模型移出便宜、可逆，停掉特征管道才真正省成本，两件事混在一张状态机里无法表达；「已评估 → 在线」之间也缺少影子落盘和 AB 这两个最耗时、最容易失败的阶段。决定：生命周期拆成两层——特征定义（`feature_id@version`，管道与存储）只有 draft / registered / deprecated / archived 轻状态；特征用量（`feature@version × 模型 × 场景`）承载 candidate → offline_evaluated → shadow_logging → ab_testing → online → offboard_proposed → fading → removed 的完整流程。定义只有在没有任何活跃用量时才能归档；上游信号的任何变更视为新版本。

## Considered Options

- 单层、以特征为主体（v0.2）：无法表达「在 A 模型在用、在 B 模型下线」。
- 单层、以特征 × 模型为主体：管道停产的时机无处判断。
- 两层（选定）。已核的特征平台（Feast、Tecton、Hopsworks、Databricks、Vertex）都只有定义级轻状态与「定义 → 模型」反向索引，没有把用量做成带状态的实体；用量层是本方案的扩展，没有直接先例。

## Consequences

- 前置评估、AB、下线的对象都是用量；成本节省只在定义归档时兑现。
- 元数据适配器（6.3）新增 `usages()` 反向索引；serving 日志适配器（6.7）新增，承载影子落盘与渐隐控制。契约修改按 ADR-0003 登记于此。
- 术语「特征定义」「特征用量」进入 `CONTEXT.md`。
- 下线执行从「停训观察」改为 serving 层渐隐（方案 5.4），依赖 serving 侧支持（第 8 章 #16）。
