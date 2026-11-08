# 特征前置评估与生命周期管理

方案见 `docs/总体方案设计.md`（v0.3，评审中；评审问题清单见 `docs/评审问题清单-v0.2.md`，状态列已回填 v0.3 的处理位置），术语见 `CONTEXT.md`，决策记录见 `docs/adr/`。业界调研见 `reports/特征前置评估业界调研.md`（第一轮）与 `reports/特征前置评估调研核验与深化.md`（第二轮，逐条对原文核验，含对第一轮的更正），分方向笔记在 `research_notes/`。`feval/` 是 V0 本地原型（仍为 v0.2 口径，对齐 v0.3 的差距见方案 7.4）：用带真值的 mock 数据验证方案里的判据，随后上传公司环境、换真实数据运行。

## 阅读顺序

先读 [`CONTEXT.md`](CONTEXT.md)：方案里的术语有严格定义（比如「适用人群」和「特征定义域」是两回事），先过一遍术语表，正文读起来快很多。然后按目的选一条路线。

**快速了解（约 20 分钟）**

1. 本 README：仓库里有什么、怎么运行。
2. [`reports/mock-matrix.md`](reports/mock-matrix.md) 的前 25 行：工具最终产出的矩阵报告。
3. [方案](docs/总体方案设计.md)第 1 章（要解决的三个问题、三大能力）和 2.3 节（三条核心数据流）。
4. 方案第 7 章的路线图表格。

**评审方案（约 1.5–2 小时）**

1. `CONTEXT.md`。
2. 方案第 1 章、2.3 节；2.1、2.2 的架构图和模块表需要时再回查。
3. 第 3 章前置评估（全文核心）：3.0 口径卡；3.1 L1 快筛，重点是 3.1.3 的阈值与合成规则；3.2 L2 增量评估，重点是 3.2.1 双代理怎么合并、3.2.2 判定规则。3.3 序列、3.4 交叉可以先略读。
4. 第 5 章生命周期：状态机、上线 gate、下线判据。
5. 第 7 章与 7.1 节校准结论，细节见 [`reports/calibration.md`](reports/calibration.md)。
6. [`docs/adr/`](docs/adr/)：6 篇决策记录，每篇不到一页；最重要的是 0001（双层评估）、0004（入模优效、下线非劣效）和 v0.3 提议的 0006（L2 统计协议）、0005（两层生命周期）。
7. 方案第 8 章待定清单与 [`docs/评审问题清单-v0.2.md`](docs/评审问题清单-v0.2.md)：还没定的事和已发现的问题，也就是评审要讨论的内容。

第 4 章特征挖掘、第 6 章适配器接口到 V2 或真正实现时再读；[`docs/业界调研附录.md`](docs/业界调研附录.md) 用来查出处。读过 v0.2 的读者先看第 9 章变更记录，v0.3 的 26 条改动都标了位置和对应的评审问题编号，按表跳到对应小节；v0.1、v0.2 原文在 [`docs/archive/`](docs/archive/)。数字的出处与核验状态查第二轮调研报告。

**看代码**

1. 下文「实现约定」。
2. `feval/pipeline.py` 的 `evaluate()`：整条流程的入口，依次调用 L1、L2、联合确认。
3. `feval/l1.py` 的 `screen()`、`grade()`，再看 `feval/l2.py` 的 `paired_bootstrap()`、`decide()`、`confirm_jointly()`。
4. `feval/mock.py`：每类候选的真值是怎么构造的。
5. `tests/test_feval.py`：基准值与判定表，能看出每条规则的预期行为。

## 运行

```bash
uv venv .venv --python 3.10 && uv pip install --python .venv -r pyproject.toml --extra dev
.venv/bin/python -m pytest                     # 口径基准值 + 判定表 + 端到端冒烟
.venv/bin/python -m feval.pipeline             # mock 数据 → reports/mock-matrix.md（CTR、游戏两列）
.venv/bin/python -m feval.calibrate --reps 20  # 评估器校准 → reports/calibration.md（3 进程约 15 分钟）
```

## 模块

| 文件 | 方案位置 | 内容 |
|---|---|---|
| `feval/spec.py` | 3.0 | `TargetSpec`：口径卡 |
| `feval/l1.py` | 3.1 | 自适应分桶、计数表、IV / KS / MI / OOF AUC / PSI / 缺失率、合成规则 |
| `feval/l2.py` | 3.2 | LightGBM 与 LR 双代理、按分组键的 Poisson bootstrap、残差分析、通过者联合确认、入模判据 |
| `feval/pipeline.py` | 2.3、3.5 | 评估流水线与矩阵报告 |
| `feval/mock.py` | 7.1 | 带真值的 mock 数据：各类候选与负/正对照 |
| `feval/calibrate.py` | 7.1 | 多种子统计各判据的误放率与漏放率 |

## 实现约定

- **计数表是后端交接面**：L1 指标全部是 `(bin, pos, neg)` 计数表的纯函数。接 Spark 时用 `approxQuantile` 定桶边，再 `group by` 产出同一张计数表（PSI 按天、OOF AUC 按折各一张），指标代码不用改。`tests/test_feval.py` 里的基准值两端必须一致。
- **双代理判定**：`l2.decide` 接收各代理主指标的 CI；任一代理 CI 下界 > δ_min 即建议入模，全部代理 CI 上界 < 0 才判有害（方案 3.2.1）。联合确认用同一口径。
- **Poisson bootstrap**：每个分组（口径卡的分组键）独立抽 Poisson(1) 权重。Spark 上可以按分组键哈希逐行生成，不需要全局重采样。
- **残差分析**：线上分先在 train 上做 Platt 校准，再作 LightGBM 的 init_score，只用候选特征继续拟合。LightGBM 的预测不含 init_score，要手动加回。
- **正对照**：候选若本来就在基线里，`evaluate` 会先把它从基线移出再评估。
- **特征定义域**：`evaluate(..., domains={特征: 0/1 列})`，缺失率只在定义域内计算。

## 尚未实现

连续型 label 指标族（3.1.4）、时间分片 AUC 衰减、训练/推理 skew、时点正确性检查（需要特征快照时间戳）、序列与交叉特征评估（3.3、3.4）、滚动多窗、YAML 登记、六类适配器、Spark 后端。

## 迁移到公司环境

1. 用 Hive 取数替换 `make_ctr_mock`，产出同样列结构的 Polars DataFrame：label、日期、分组键、线上分、特征列。
2. 为目标模型填口径卡（`TargetSpec`），为行业专属等特征声明定义域。
3. 每批候选混入噪声探针（样本级或用户×天级随机数；用户级常量随机数会被代理当作用户 ID，不能当负对照，见方案 7.1），再从基线里挑 1–2 个已知强特征作正对照；按 `calibrate.py` 的统计口径（负对照误放率、正对照通过率）定 δ_min 后再出正式报告。
