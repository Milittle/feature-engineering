# 特征生命周期 / Shadow·AB 集成 / 漂移处理 / 护栏指标 / 成本治理：第二轮核验与深化

> 对应设计：`docs/总体方案设计.md` 第 5 章（状态机、上线 gate、监控、下线）与 3.1.3（PSI ≥ 0.25 拒绝）。对应评审项：R6、R8、R13、R14。
> 首轮笔记：`research_notes/特征前置评估业界调研/05_lifecycle_drift_cost_governance.md`。
>
> **标记说明**
> - **[已核原文 + 位置]**：本轮已下载原文（PDF 用 pdftotext 抽取，网页抓取正文）并逐字核对。
> - **[更正]**：首轮表述有误，本轮已改正。
> - **[仍未核]**：本轮仍未拿到原文。
>
> **本轮网络情况**
> - 可直连：arxiv.org、huggingface.co、proceedings.neurips.cc、developers.google.com（仅 curl）、research.google / storage.googleapis.com、docs.cloud.google.com、docs.hopsworks.ai、docs.tecton.ai、docs.databricks.com、docs.feast.dev、nannyml.readthedocs.io、mail.vldb.org、infoq.com。
> - 不可达：medium.com（403）、web.archive.org（连接被重置）、uber.com（406）。Medium 第三方镜像被会话策略拒绝，未使用。
> - 每一节的 "Cited Findings" 只写有出处的事实；"Inferences" 是研究员基于这些事实的设计推论。两者分开写。

---

## Q0 首轮标记条目核验结果（汇总）

### Takeaway
首轮标为 [训练知识] 或"仅见摘要"的条目，大部分已在原文中核实。有四处需要更正：
1. ML Test Score 里没有 "The cost of each feature is worth its benefit" 这一条。实际是 Data 2 "All features are beneficial" 和 Data 3 "No feature's cost is too much"。
2. arXiv 2401.08348 讲的是 **PAPE**，不是 "M-CBPE"。
3. AdaEmbed 的 35–60% 来自"工业场景评估"，原文没说是"部署后观测"。
4. Airbnb 护栏的定量细节（StdErr < 0.8·t、每月约 25 个、约 20% 被叫停）只能经 InfoQ 二手核到，Medium 原文仍不可达。

Uber Palette 与 "Instagram 删除数千低影响特征" 两条仍未核实。本轮另找到 Meta 2026 年关于"特征渐隐下线"的一手论文（IEFF），可以替代 Instagram 那条说法。

### Cited Findings

**Sculley et al. 2015, Hidden Technical Debt** [已核原文：NeurIPS 2015 PDF 第 3 节 "Data Dependencies Cost More than Code Dependencies"]
- "Underutilized Data Dependencies" 段原文定义了四类特征：
  - **Legacy Features**："a feature F is included in a model early in its development. Over time, F is made redundant by new features but this goes undetected"。
  - **Bundled Features**：一组特征整体评估后被判为有益，"because of deadline pressures… all the features in the bundle are added… possibly including features that add little or no value"。
  - **ε-Features**："improve model accuracy even when the accuracy gain is very small or when the complexity overhead might be high"。
  - **Correlated Features**：两特征强相关但只有一个更直接因果，模型可能偏向非因果的那个，"This results in brittleness if world behavior later changes the correlations"。
- 原文建议："Underutilized dependencies can be detected via exhaustive leave-one-feature-out evaluations. These should be run regularly to identify and remove unnecessary features."
- 同节 "Unstable Data Dependencies"：
  - 上游信号会随时间变化，包括信号本身来自另一个会更新的模型，或由不同团队维护。
  - 即使是"改进"，例如修正此前错误的校准，也可能伤害下游模型。
  - 缓解办法是 "create a versioned copy of a given signal"（冻结版本），代价是陈旧和多版本维护成本。
- 同节 "Static Analysis of Data Dependencies"：自动化特征管理系统允许给数据源和特征加注解，自动检查依赖树，"This kind of tooling can make migration and deletion much safer in practice"。
- 第 2 节 "Undeclared Consumers"（未声明的消费者）和 CACE 原则（"Changing Anything Changes Everything"）均已核到。
- 监控部分列出三项：
  - **Prediction Bias**：预测标签分布应等于观测标签分布，"surprisingly useful diagnostic"，可按维度切片并自动告警。
  - **Action Limits**：例如出价类系统设置动作上限。
  - **Up-Stream Producers**：上游需要 SLO，告警要传到 ML 系统控制面。
- 来源：[NeurIPS 2015 PDF](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

**Breck et al. 2017, The ML Test Score** [已核原文：Google Research PDF 第 II 节 Data tests、第 III 节 Model、第 IV 节 Infra、第 V 节 Monitor] **[更正]**
- 首轮写的 "The cost of each feature is worth its benefit" 在原文中不存在。实际是两条：
  - **Data 2: "All features are beneficial"**：
    - 原文："A kitchen-sink approach to features can be tempting, but every feature added has a software engineering cost. Hence, it's important to understand the value each feature provides in additional predictive power (independent of other features)."
    - 做法："computing correlation coefficients, by training models with one or two features, or by training a set of models that each have one of k features individually removed."
  - **Data 3: "No feature's cost is too much"**：
    - 原文："It is not only a waste of computing resources, but also an ongoing maintenance burden to include ε-features that add only minimal predictive benefit."
    - 做法："To measure the costs of a feature, consider not only added inference latency and RAM usage, but also more upstream data dependencies, and additional expected instability incurred by relying on that feature. See Rule #22."
- 与本设计直接相关的其他条目：
  - **Model 2**："Offline proxy metrics correlate with actual online impact metrics"。做法是 "measured in one or more small scale A/B experiments using an intentionally degraded model"。
  - **Infra 6**："Models are tested via a canary process before they enter production serving environments"。
  - **Infra 7**："Models can be quickly and safely rolled back"。
  - **Monitor 3**："Training and serving features compute the same values"。
  - **Monitor 6**："…regressions in training speed, serving latency, throughput, or RAM usage"。
  - **Monitor 7**："The model has not experienced a regression in prediction quality on served data"。建议测切片上的 prediction bias，例如 "90% of predictions of probability 0.9 should in fact be positive"。
- 来源：[ML Test Score PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf)；[论文页](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)

**Google Rules of ML** [已核原文：developers.google.com 页面]
- **Rule #8** "Know the freshness requirements of your system"：原文举例，大多数广告系统每天有新广告，必须每日更新。
- **Rule #11** "Give feature columns owners and documentation"：要记录特征是什么、来源、"how it is expected to help"。
- **Rule #22** "Clean up features you are no longer using"：
  - 原文："Unused features create technical debt. If you find that you are not using a feature, and that combining it with other features is not working, then drop it out of your infrastructure… If necessary, someone can always add back your feature."
  - 同条还要求关注**覆盖率**：例如只有 8% 用户有个性化特征则效果有限；反过来，覆盖 1% 但其中 90% 为正例的特征 "punch above their weight"。
- **Rule #29**：在 serving 时记录特征集再用于训练，"Even if you can't do this for every example, do it for a small fraction"。
- **Rule #33**：在训练截止日之后的数据上测试。
- **Rule #37** "Measure Training/Serving Skew"：holdout 与 next-day 数据之间的大幅下降 "may indicate that some features are time-sensitive"。
- 来源：[Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

**JD 离线 AUC → 收入** [已核原文：arXiv 2006.10337（KDD 2020 CSCNN）实验节]
- 原文两处表述：
  - "Empirically, when the CTR prediction model is trained in binary classification, off-line AUC directly reflects the online performance. In JD.com, every 1‰ increase in off-line AUC brings 6 million dollars lift in the overall advertising income."
  - "on the real production data, 1‰ increase in off-line AUC is significant and brings 6 million dollars lift in the overall advertising income of JD.com."
- 原文未说明这 600 万美元的时间口径（年或其他）。
- 同文还报告：在线 A/B 时间为 2019-02-19 至 2019-02-26，CSCNN CTR +3.22%。
- 来源：[arXiv 2006.10337](https://arxiv.org/pdf/2006.10337)

**HF "580 experiments" 博文** [已核原文]
- 基本信息：作者 Santiago Viquez（NannyML），2024-06-03 发布。
- 实验设计：
  - 数据：Folktables（美国人口普查）二分类任务。
  - 模型：线性模型与提升树。
  - 方法：用单变量漂移（JS、KS、Chi2）和多变量漂移（PCA 重构误差、Domain Classifier）的结果作为特征，训练 "DriftSignal" 回归模型来估计 ROC AUC。
  - 评估指标：MASTE（按标准误缩放的 MAE）。
- 结果：PAPE 最准，CBPE 次之，"constant test set performance"（假设性能恒定的朴素基线）排第三，基于漂移信号的随机森林模型紧随其后。
- 结论原文："It is better to first estimate model performance and then, if it drops, review data drift results but not the other way around."
- 来源：[HF blog](https://huggingface.co/blog/santiviquez/data-drift-estimate-model-performance)

**arXiv 2401.08348** [已核摘要] **[更正]**
- 该论文是 **PAPE**（Probabilistic Adaptive Performance Estimation），作者 Białek、Kivimäki、Kuberski、Perrakis。首轮写成 "M-CBPE"，有误。
- 摘要要点：数据漂移检测这类代理方法 "fail to measure the effects of these shifts adequately"；PAPE 不依赖原模型内部、不假设协变量漂移形式；在 900+ 个数据集-模型组合上优于基线。
- 来源：[arXiv 2401.08348](https://arxiv.org/abs/2401.08348)

**NannyML CBPE / DLE** [已核原文：NannyML "How it works – Performance Estimation"]
- CBPE 的假设：
  1. 模型输出校准良好的概率；
  2. 协变量漂移不进入此前未见过的输入区域；
  3. 无概念漂移。原文："CBPE will not work under concept drift i.e. when P(Y|X) changes… there is no way to identify concept drift without any ground truth data"；
  4. 样本量足够。
- 原文还说 "CBPE will handle covariate shift well"。
- DLE（Direct Loss Estimation）：训练一个 "nanny model" 直接估计被监控模型每条样本的 loss，用于回归模型。
- 来源：[NannyML performance estimation](https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html)

**VLDB 2024 漂移论文** [已核原文：PVLDB Vol.17 No.11 摘要页]
- 作者：Sijie Dong、Qitong Wang、Sahri Soror、Themis Palpanas、Divesh Srivastava。
- 摘要原文："we observe that not all data drifts lead to degradation in prediction accuracy"。
- 方法：用决策树定位 "Data Distributions with Low Accuracy (DDLA)"，"advocate for model retraining only in cases of harmful drifts"。
- PDF 为 p3072。
- 来源：[PVLDB 摘要页](https://mail.vldb.org/pvldb/volumes/17/paper/Efficiently%20Mitigating%20the%20Impact%20of%20Data%20Drift%20on%20Machine%20Learning%20Pipelines)；[PDF](https://www.vldb.org/pvldb/vol17/p3072-dong.pdf)

**Vertex AI 漂移默认值** [已核原文]
- Feature Store 特征监控：
  - drift_threshold 取值 [0,1)，"If you don't enter a value, the threshold is set to 0.3, by default"。
  - 比较对象是**相邻两次 FeatureMonitorJob 的快照**，不是固定基期。
  - 计算用 BigQuery ML.TFDV_VALIDATE：类别特征用 L-infinity，数值特征用 Jensen-Shannon。
- Model Monitoring（v2）：
  - "By default, every categorical and numerical feature is monitored, with threshold values of 0.3"。
  - 另有 **Feature attribution** 监控目标：用 SHAP 跟踪特征贡献变化，例如 "track if a highly important feature suddenly drops in importance"。
- 注：该文档已迁移到 "gemini-enterprise-agent-platform" 路径下。
- 来源：[Vertex Feature Store monitor](https://docs.cloud.google.com/vertex-ai/docs/featurestore/latest/monitor-features)；[Model Monitoring overview](https://docs.cloud.google.com/vertex-ai/docs/model-monitoring/overview)

**Airbnb 2021 护栏框架** [仍未核原文（medium 403、archive 不可达）；已核 InfoQ 二手报道]
- 三个护栏：
  - **Impact**：指标相对变化低于逃逸阈值 −t 即升级评审，不论是否显著。
  - **Power**：要求 "StdErr < 0.8 * t"，保证实验跑够时长。
  - **Stat sig negative**：任何显著负向都升级，用于收入这类敏感指标。
- t 可以设为实验全局覆盖率的函数：覆盖率低时 t 放宽，使各实验的时长相近。
- 系统每月标记约 25 个实验，评审后约 20%（约 5 个）被叫停。
- 首轮中的以下内容本轮仍只见于检索摘要，**[仍未核]**："收入 0.1% ≈ 数百万美元"、"房屋守则"案例、"关键业务 / 用户体验 / 战略优先"三类。
- 来源：[InfoQ 2021-01-31](https://www.infoq.com/news/2021/01/airbnb-guardrails-change-impact/)；原文 [Medium](https://medium.com/airbnb-engineering/designing-experimentation-guardrails-ed6a976ec669)

**csAUC** [已核 arXiv 摘要：1904.10272，2019]
- 摘要原文："in practice, AUC often improves in offline evaluation, but online CPM does not… AUC can only reflect the order on CTR, but it does not reflect the order of CTR*Bid"。
- 来源：[arXiv 1904.10272](https://arxiv.org/abs/1904.10272)

**Hopsworks 废弃** [已核原文，latest 版]
- 原文："When a feature group is deprecated, user will be warned when they try to use it or use a feature view that depends on it."
- 来源：[Hopsworks deprecation](https://docs.hopsworks.ai/latest/user_guides/fs/feature_group/deprecation/)

**Tecton prevent_destroy** [已核原文]
- 已核的首轮内容：
  - 设为 True 时阻止 plan/apply 中的删除或重建。
  - 要删除必须先在 apply 中置为 False。
  - 用于防止误删生产 Feature Service，或误重建导致昂贵的重新物化。
- 本轮补充：
  - 对 Feature Service 设置后，会连带阻止其使用的 Feature View 被删除或重建。
  - "prevent_destroy is only enforced in live (i.e. non-dev) workspaces"。
  - Feature View 的 `online` / `offline` 物化开关默认都是 False。
- 来源：[Tecton BatchFeatureView](https://docs.tecton.ai/docs/sdk-reference/feature-views/BatchFeatureView)

**Uber Palette 废弃** [仍未核]
- uber.com 本轮返回 406，WebFetch 也不可解析。首轮转述需保留"未核"标记。
- 来源：[Uber blog](https://www.uber.com/en-US/blog/palette-meta-store-journey/)

**Instagram "删除数千低影响特征"** [仍未核，建议删去]
- 本轮仍未找到一手出处。可替代的一手材料是下面的 Meta IEFF 论文（见 Q1/Q4）。

**Meta 降本数字** [已核原文]
- **AdaEmbed** **[更正措辞]**：
  - 作者为 Meta 与 Fan Lai（密歇根大学）。
  - 原文："Our evaluations in industrial settings show that AdaEmbed saves 35-60% embedding size needed in deployment and improves model execution speed by 11-34%, while achieving noticeable accuracy gains."
  - 这是"工业场景评估"的结果，首轮写的"部署后"不准确。
  - 方法：按运行时访问频率和梯度大小评估 embedding 重要性，动态剪枝，"automatically determine per-feature embeddings"。
  - 来源：[par.nsf.gov PDF](https://par.nsf.gov/servlets/purl/10454226)
- **ROO**：在三个产品上，用相同存储把训练样本量提升 43%–150%。来源：[arXiv 2508.05640](https://arxiv.org/pdf/2508.05640v3)
- **Meta Lattice**：
  - 原文："10% revenue-driving top-line metrics gain, 11.5% user satisfaction improvement, 6% boost in conversion rate, with 20% capacity saving"。
  - 这是模型空间重设计的整体结果，不是特征治理的单独贡献。
  - 来源：[arXiv 2512.09200](https://arxiv.org/pdf/2512.09200)

**Etsy / 低秩压缩** [已核原文]
- Etsy 原文："Improvements in AUC (> 1%) have consistently resulted in significant CTR wins in multiple rounds of online A/B tests"。来源：[arXiv 1711.01377](https://arxiv.org/pdf/1711.01377)
- 低秩压缩论文：
  - 7 天在线 A/B，"our method only improves online AUC by 0.079‰"，Advertiser Value +2.34%。
  - 作者给的解释：基线 AUC 已很高，且用户基数大。
  - 来源：[arXiv 2405.18146](https://arxiv.org/pdf/2405.18146)

**以下仍未核（本轮未抓取）**
- Kohavi 等《Trustworthy Online Controlled Experiments》的 guardrail 分类。
- He et al. 2014（Facebook）关于校准与 NE 的表述。
- Moreno-Torres 2012、Gama 2014 的漂移分类。

### Inferences
- 设计文档如果引用 ML Test Score，应写作"Data 2 / Data 3"，并引原文的成本四要素：推理延迟、RAM、上游数据依赖、预期不稳定性。这四项可以直接作为成本账本的一级字段。
- Sculley 的 "Unstable Data Dependencies → versioned copy" 对特征平台有直接含义：上游信号变更（包括"修复"）应视为**新特征版本**，走评估流程，不应原地覆盖。

### Gaps
- Airbnb 原文、Uber Palette 原文需要放开 medium.com / web.archive.org / uber.com 后再核。
- JD "600 万美元" 的时间口径（年化或其他）原文未说明，无法补全。

---

## Q1 特征平台的生命周期数据模型（实体、状态、元数据、特征×模型用量、带血缘的下线流程）

### Takeaway
已核的平台都没有多状态的特征状态机。状态相关的能力只有三类：
- 删除保护：Tecton prevent_destroy，且只在 live workspace 生效。
- 软废弃告警：Hopsworks deprecated。
- dev 与 live workspace 的环境区分：Tecton。

"特征×模型"在 Feast 和 Databricks 中都以**血缘 / 反向索引**存在（可回答"改这个 feature view 会影响哪些模型"），不是带状态的实体。

本轮新发现 Meta IEFF（2026）给出了**下线的工业级流程**：
- 在 serving 层按日渐隐特征覆盖率，每天 1–2%，边界或紧急场景 5–10%。
- 先在 A/B（QRT）中验证安全速率，可回滚。
- 共渐隐 275 个特征，约免去 140 次重训，年基础设施成本约降 15%。

这直接支持把设计中的"停训观察"改为"渐隐下线"。

### Cited Findings

**Tecton**
- Feature View 的元数据字段：`name`、`description`、`owner`（"Typically the name or email of the Feature View's primary maintainer"）、`tags`（任意键值）、`prevent_destroy`、`online`/`offline`（物化开关，默认 False）、`ttl`、`feature_start_time`。
- prevent_destroy 只在 live（非 dev）workspace 强制执行；设在 Feature Service 上时，会连带保护其依赖的 Feature View。
- 来源：[Tecton BatchFeatureView](https://docs.tecton.ai/docs/sdk-reference/feature-views/BatchFeatureView)

**Hopsworks**
- 废弃是 Feature Group 级的布尔状态，可撤销。使用该 Feature Group 或依赖它的 Feature View 时给出告警，不阻断使用。
- 来源：[Hopsworks deprecation](https://docs.hopsworks.ai/latest/user_guides/fs/feature_group/deprecation/)

**Databricks**
- 在 Unity Catalog 中训练并记录模型时，"Tables and functions that were used to create the model are automatically tracked and displayed"。
- FeatureSpec 是 Unity Catalog 实体，"with full lineage tracking to their constituent offline feature tables and functions"。
- 来源：[Databricks Feature Store concepts](https://docs.databricks.com/aws/en/machine-learning/feature-store/concepts)

**Feast + MLflow**
- 文档列出的能力包括："Which models break if I change a feature view? -- reverse index via the Feast UI /api/mlflow-feature-usage endpoint"。
- 训练时的 entity DataFrame 作为 MLflow artifact 保存，用于复现。
- `feast apply` 和 `feast materialize` 被记录到单独的运维实验中。
- 来源：[Feast MLflow reference](https://docs.feast.dev/master/reference/mlflow)

**Meta IEFF（Intelligent Elastic Feature Fading，arXiv 2605.00324，2026-05）** [已核原文]
- 问题陈述：
  - 特征下线、清理、精度迁移等效率类变更通常与模型重训绑定，迭代周期 3–6 个月，GPU 成本高。
  - 直接把覆盖率从 100% 置 0（zero-out）会造成 NE 急剧上升。
- 机制：
  - 在 serving 层用中心化控制面加特征适配器，按"开始时间 + 渐隐速率"逐步降低覆盖率或调整分布。
  - 渐隐后的特征值同时用于推理和训练日志，靠常规的循环训练让模型逐步适应。
- 速率选择：
  - 先用 QRT（Meta 内部 A/B 框架）做渐隐前验证，再确定速率。
  - 已验证的范围是 1%–10%/天；生产上用 1–2%/天；5–10% 用于边界实验和隐私类紧急下线。
- 安全约束：
  - 只对显式指定的特征执行；
  - 受预定义策略约束（范围、速率、时长）；
  - 支持快速回滚；
  - 配有监控。
- 结果：
  - 共 3 个阶段、14 批、275 个特征；速率从 10%/天（早期验证）收敛到 1–5%/天（大规模推广）。
  - 每批约免去 10 次完整重训，合计约免去 140 次；"reduced annual infrastructure costs by approximately 15%"。
  - 效率类变更的推广提速 5×。
  - 与突然 zero-out 相比，渐隐 "prevents 50–55% of online performance degradation"。
- 来源：[arXiv 2605.00324](https://arxiv.org/pdf/2605.00324)

**Sculley 2015**
- 自动化特征管理系统允许给数据源和特征加注解，自动解析依赖树，"make migration and deletion much safer"。
- 来源：[NeurIPS 2015 PDF](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

### Inferences（面向 R6 的设计建议）

**1. 两层实体**
- **FeatureDefinition（定义级）**
  - 状态：`draft → registered → deprecated（软废弃、告警，参照 Hopsworks）→ archived`。
  - 进入 `archived` 的前置条件：反向索引中**没有处于 active 状态的 usage**。这对应 Tecton prevent_destroy 的语义，即"仍被生产服务引用就不可删"。
- **FeatureUsage（feature × model × 场景）**
  - 状态：`candidate → offline_evaluated → (shadow_logging) → ab_testing → online → offboard_proposed → fading → removed`，另有分支 `rejected / deferred`。
  - 设计中现有的"候选 / 已评估 / 在线 / 下线提案 / 停训观察 / 已下线"挂在这一层。

**2. 建议的 Usage 元数据字段**
- 标识：`feature_id@version`、`model_id`、`scene`、`owner`。
- 评估与实验：`eval_report_id`（L1/L2 报告）、`experiment_id`（AB 平台 ID）、`flag_key`（开关）、`stage_entered_at`、`exit_criteria_snapshot`（进入下一状态时各指标值的快照）。
- 成本与重要性：`cost_ledger_ref`、`importance_series_ref`。
- 下线相关：`fade_rate`、`fade_progress`（IEFF 式字段）。

**3. "停训观察" 改为 "渐隐（fading）"**
- 设计 5.4 中"停止进入新训练样本 → 观察一个完整训练周期"会造成一次分布突变（训练里没有、线上仍有，或反过来）。
- 改法：在 serving 和训练日志两侧同时按 1–2%/天降低覆盖率，并挂 AB 对照；指标回退即按 flag 回滚。
- 证据来自 IEFF（已核）。适用前提是模型有日更或周更的循环训练。

**4. 上游信号变更即新版本**
- 依据 Sculley 的 unstable dependency：版本号进入 usage 主键，新版本必须重新走评估。

### Gaps
- 下列平台本轮未核到状态模型的一手资料：Feathr、Chronon、Michelangelo/Palette（uber.com 不可达）。从已有资料推断它们同样没有多状态特征生命周期，但这一点**未经证实**。
- 没有找到任何公开平台把 feature×model usage 做成带状态的一等实体。这是我们设计上的扩展，没有直接先例。

---

## Q2 Shadow 上线、AB 集成与护栏指标（含非劣效检验）

### Takeaway
- 可核实的一手资料给出的上线路径是：canary（ML Test Score Infra 6）→ A/B → 可快速回滚（Infra 7）。
- 特征级的 dark launch 一手资料仍然稀缺。Meta IEFF 显示：特征级变更（包括下线）在 Meta 也是先过 A/B（QRT）、再按速率在 serving 层渐进推广。
- 护栏的统计检验方面，Spotify 2024 给出了可直接落地的规则：成功指标做优效检验，护栏指标做**非劣效检验**（且非劣效检验无需多重校正），所有指标再做劣化检验，同时做 SRM 等质量检验。
- Airbnb 的 Impact / Power / Stat-sig-negative 三护栏可作为阈值与时长设计的参考（经二手来源核实）。
- 广告排序必须把校准作为护栏：
  - LinkedIn 指出广告扣费与 CTR 概率挂钩，所以校准至关重要；
  - csAUC 指出 AUC 不反映 CTR×bid 的排序；
  - Sculley 和 ML Test Score 都把 prediction bias 列为核心监控项。

### Cited Findings

**Spotify 决策规则（Schultzberg 等，arXiv 2402.11609）** [已核原文]
- 指标分四类：
  - Success：superiority test（优效检验）；
  - Guardrail："do not want to see deteriorate more than a certain threshold, tested with non-inferiority tests"；
  - Deterioration：inferiority test（劣化检验）；
  - Quality：例如 SRM、pre-exposure bias。
- 所有 success 和 guardrail 指标同时也作为 deterioration 指标。
- Decision Rule 2：在以下四条同时成立时上线（ship）：
  1. 至少一个 success 指标显著优效；
  2. 所有 guardrail 指标显著非劣效；
  3. success、guardrail、deterioration 指标中没有任何一个显著劣化；
  4. 没有任何 quality 检验拒绝。
- 统计结论：
  - 护栏用非劣效检验时，其显著性水平不需要多重校正；
  - 但决策规则包含非劣效、劣化或质量检验时，**第二类错误需要校正**，才能保证决策层面的功效。具体修正见 Proposition 4.1。
- 来源：[arXiv 2402.11609](https://arxiv.org/pdf/2402.11609)

**Airbnb 三护栏**（经 InfoQ 二手核实）
- Impact：相对下降超过 t 则升级评审。
- Power：StdErr < F·t，例如 F = 0.8。
- Stat sig negative：任何显著负向都升级。
- t 可随实验覆盖率调整；每月约 25 个实验被升级，约 20% 被叫停。
- 来源：[InfoQ](https://www.infoq.com/news/2021/01/airbnb-guardrails-change-impact/)

**ML Test Score 的上线相关条目**
- Infra 6（canary）：原文 "Offline testing, however extensive, cannot by itself guarantee the model will perform well in live production settings"。
- Infra 7：可快速回滚。
- Monitor 6：延迟、吞吐、RAM 不发生回归。
- Monitor 7：线上预测质量不回归，测切片上的 prediction bias。
- Model 2：用故意劣化的模型做小规模 A/B，标定离线-在线指标关系。
- 来源：[ML Test Score PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf)

**Meta IEFF**
- 渐隐速率由 QRT 预先验证；推广过程配有 "strict safety guardrails, reversibility mechanisms, and comprehensive monitoring"。
- 渐隐在 serving 层执行，渐隐后的特征值同时用于推理和训练日志，保证训练与推理一致。
- 来源：[arXiv 2605.00324](https://arxiv.org/pdf/2605.00324)

**LinkedIn LiRank（KDD 2024）**
- 原文："Ads charging prices are linked to click-through rate (CTR) probabilities, making accurate calibration essential"。
- 原文："for Ads CTR and Job recommendations, we find that offline AUC measurement aligns well with online experiment outcomes"；Feed 排序则依赖 "offline replay metrics"，后者与线上 A/B 相关。
- 来源：[arXiv 2402.06859](https://arxiv.org/pdf/2402.06859)

**Rules of ML #29**
- 至少对一小部分样本记录 serving 时的特征，用于校验训练与服务的一致性。这是 shadow 阶段打日志的直接依据。
- 来源：[Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

**PCOC**
- 本轮检索未找到给出 PCOC（predicted clicks / observed clicks）上线阈值的一手资料，见 Gaps。

### Inferences（面向 R6 / R14 的设计建议）

**1. Usage 级各阶段的出口条件**

| 阶段 | 做什么 | 出口条件 | 建议时长 |
|---|---|---|---|
| `offline_evaluated` | 现有 L1/L2 | 现有 gate（PSI 规则需按 Q3 修改） | — |
| `shadow_logging` | 特征在线计算并打日志，不进模型 | ① 在线与离线回填一致率（参考 Chronon：数值用 SMAPE，类别用不等比例）达标；② 特征取数 P99 延迟增量和超时率在预算内；③ 线上覆盖率和缺失率与离线评估口径一致 | ≥ 1 个完整周期（7 天，覆盖周内波动）。对**无法离线回填的实时特征**，shadow 日志就是 L2 评估的数据来源，shadow 应排在 L2 之前 |
| `ab_testing` | 走 Spotify 式决策规则（见下） | 见下 | 由护栏的功效要求反推（Airbnb Power 护栏 StdErr < 0.8·t），不固定天数 |

**2. AB 阶段的决策规则**
- Success（优效）：主业务指标，例如 RPM、收入、CTR/CVR。
- Guardrail（非劣效，NIM 预先登记）：
  - 校准：分切片 PCOC 偏离 1 的程度，或 ECE；
  - 系统：P99 端到端延迟、超时率、CPU/内存；
  - 生态：广告主价值或 ROI、负反馈率、多样性。
- Deterioration：上述所有指标同时做劣化检验。
- Quality：SRM、pre-exposure bias（AA 期）。

**3. 特征下线也走 AB**
- 用 IEFF 的方式：下线 = 反向的"特征移除实验"。护栏同上；主判据是主指标非劣效，与设计 5.4 的"CI 下界 > −ε"一致。

**4. 护栏阈值的来源**
- 业务方给定 NIM。
- 同时用历史 AA / AB 方差反推可检测下限，避免设定无法达到功效的阈值（Airbnb Power 护栏的思路）。

### Gaps
- 未找到 Meta、Pinterest、字节、阿里等公开的 "PCOC ∈ [x, y]" 上线门槛一手出处；检索只命中低质量博客。阈值需由业务方标定。
- 未找到"新特征 shadow 阶段推荐时长"的一手量化建议；上文"≥ 7 天"是推论。
- Kohavi 书中 goal / driver / guardrail 的原文本轮未核。

---

## Q3 漂移：如何判断漂移是否伤害效果，准入时如何处理漂移特征

### Takeaway
已核的三组一手证据方向一致：**漂移不能当作效果下降的代理**。
- VLDB 2024：并非所有漂移都降低精度，只对有害漂移（DDLA）重训。
- NannyML 580 组实验：漂移信号估计性能的效果不如"假设性能恒定"的朴素基线；应先估计性能，再查漂移。
- PAPE 论文：漂移检测 "fail to measure the effects"。

工业平台把漂移定位为**监控**，不是准入拒绝：
- Vertex 默认阈值 0.3（JS / L∞），比较相邻快照，并提供基于 SHAP 的归因漂移监控。
- IEFF 表明，渐进的分布变化在循环训练下模型可以适应，**突变**才是主要风险。

因此设计 3.1.3 中"PSI ≥ 0.25 → 拒绝"应改为风险标签，再配合时间外推增益检验。

### Cited Findings
- **VLDB 2024（Dong 等）**："not all data drifts lead to degradation in prediction accuracy"；用决策树定位 DDLA；只在有害漂移时重训，成本效率显著优于基线、精度相当。来源：[PVLDB](https://mail.vldb.org/pvldb/volumes/17/paper/Efficiently%20Mitigating%20the%20Impact%20of%20Data%20Drift%20on%20Machine%20Learning%20Pipelines)
- **NannyML 580 组实验**：
  - 漂移信号回归模型（RF）不如 PAPE 和 CBPE，并略逊于 "constant test set performance"。
  - 原文："monitoring fine-grained metrics leads to nothing and… a change in an obscure feature might not mean anything"。
  - 来源：[HF blog](https://huggingface.co/blog/santiviquez/data-drift-estimate-model-performance)
- **PAPE**：无标签情况下估计二分类在协变量漂移下的混淆矩阵类指标，900+ 组合上最优。来源：[arXiv 2401.08348](https://arxiv.org/abs/2401.08348)
- **CBPE 的适用边界**：
  - 能处理协变量漂移；
  - 不能处理概念漂移；
  - 不能处理漂移到训练中未见过的区域；
  - 需要模型校准良好、样本量足够。
  - 来源：[NannyML docs](https://nannyml.readthedocs.io/en/stable/how_it_works/performance_estimation.html)
- **Vertex AI 的监控默认值**：
  - Feature Store 监控：默认阈值 0.3；数值特征用 JS，类别特征用 L∞；比较相邻两次 job 的快照。
  - Model Monitoring：默认对所有特征监控，阈值 0.3。
  - Feature attribution（SHAP）监控用于发现 "a highly important feature suddenly drops in importance"。
  - 来源：[Feature Store monitor](https://docs.cloud.google.com/vertex-ai/docs/featurestore/latest/monitor-features)；[Model Monitoring](https://docs.cloud.google.com/vertex-ai/docs/model-monitoring/overview)
- **Meta IEFF**：
  - "when feature coverage or distribution is adjusted gradually, models can often adapt through recurring training"；
  - 突然 zero-out 会造成 NE 急剧上升，渐隐可避免 50–55% 的线上退化。
  - 来源：[arXiv 2605.00324](https://arxiv.org/pdf/2605.00324)
- **Rules of ML**：
  - #33 用训练截止日之后的数据测试；
  - #37 若 holdout 与 next-day 之间大幅下降，"may indicate that some features are time-sensitive"。
  - 来源：[Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- **Sculley**：
  - Correlated Features 在 "world behavior later changes the correlations" 时变脆；
  - Prediction Bias 切片监控可发现 "the world behavior suddenly changes"。
  - 来源：[NeurIPS 2015](https://proceedings.neurips.cc/paper_files/paper/2015/file/86df7dcfd896fcaf2674f757a2463eba-Paper.pdf)

### Inferences（面向 R8 的设计建议）

**1. L1 不再因 PSI 拒绝**

PSI 改为 `stability_tag ∈ {stable, watch, drifting}`。仍按 0.1 / 0.25 分档，但这是信用评分行业的经验值，一手出处未找到。只有下面两类"伪漂移"才阻断：
- 缺失率或默认值占比突变、常量化、在线与离线不一致：这些是数据质量问题。
- 时点泄漏。

**2. 对 drifting 特征加严 L2：时间外推增益稳定性检验**
- 做法：滚动 k 个时间窗（例如训练 T 周 → 测 T+1 周，k ≥ 4），要求 ΔAUC/ΔGAUC 在 ≥ k−1 个窗口中 CI 下界 > 0，且最差窗口 ≥ −ε。
- 依据：Rules #33/#37 和 VLDB 的"漂移不等于有害"。
- 这是用效果直接验证"漂移是否伤害增益"，不再用分布距离做代理。

**3. 有害漂移的定位（可选，V1 后）**
- 参照 DDLA：在时间外推测试集上，用决策树按该特征分箱或切片找低精度区域，判断漂移是否落在这些区域。

**4. 上线后监控的优先级**
- 首选：带标签的效果监控。推荐和广告的标签回流快，可直接看 AUC 和分切片校准（prediction bias）。
- 次选：按重要性加权的漂移，或归因漂移（参照 Vertex 的 SHAP 归因监控）。
- 原始 PSI 仅用于定位原因。
- 依据：NannyML 580 组实验的结论。
- 设计 5.4 "PSI 长期超标" 作为下线触发条件时，应同时要求效果或重要性下降。

**5. 上线 gate 5.2-3 "连续 7 天 PSI < 0.1" 建议删除或降级**
- 替代条件：时间外推稳定性检验通过，且 shadow 阶段的在线/离线一致性达标。

**6. 特征改造建议（做法建议，非已核结论）**
- 对时间敏感的计数、价格、热度类特征，做相对化（比值、排名、按天 z-score）。
- 此类特征下线时同样走渐隐，避免突变（IEFF）。

### Gaps
- PSI 0.1 / 0.25 阈值的原始出处仍未找到。
- 未找到 Evidently 或 Arize 关于"重要性加权漂移"算法的一手文档；Vertex 的 SHAP 归因监控是可核的最接近做法。
- 未找到推荐场景中"稳定性加权特征选择"的一手工业报告。

---

## Q4 成本治理：单特征成本核算、成本感知选择、ROI 准入阈值、离线增益 → 业务价值

### Takeaway
- 单特征成本的定义可以直接采用 ML Test Score Data 3 的四要素：推理延迟、RAM、上游数据依赖、预期不稳定性。
- 成本感知选择有工业一手先例：阿里 FSCD（SIGIR 2021，淘宝搜索广告）。它用 c_j = γ1·o_j + γ2·e_j + γ3·n_j（在线计算复杂度、embedding 维度、key 数）设定特征保留先验 θ_j = 1 − σ(c_j)，与效果联合学习。
- 平台级计费粒度通常只到管道或作业（Databricks 的 FEATURE_STORE 计费），单特征成本需要自行分摊。
- 离线到业务的折算锚点均已核实，但斜率跨场景相差很大，必须分场景标定：
  - JD：离线 AUC +1‰ ≈ 600 万美元广告收入（时间口径未说明）；
  - Etsy：AUC > 1% 才稳定带来 CTR 显著提升；
  - 低秩压缩：在线 AUC +0.079‰ 对应 AV +2.34%。
- ML Test Score Model 2 给出标定方法：用故意劣化的模型做小规模 A/B，测离线-在线关系。

### Cited Findings

**成本定义**
- ML Test Score Data 3 的成本测量要素："added inference latency and RAM usage… more upstream data dependencies, and additional expected instability"。
- Data 2 的价值测量方法：相关系数、单 / 双特征模型、逐个移除 k 个特征。
- 来源：[ML Test Score PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf)

**阿里 FSCD（Ma 等，SIGIR 2021，arXiv 2105.07706）** [已核原文]
- 先验与复杂度定义：
  - 特征保留先验 θ_j = 1 − σ(c_j)，复杂度 c_j = G(o_j, e_j, n_j)。原文："measures the computational and storage complexity… including but not limited to the online computational complexity o_j, the embedding dimension e_j, and the number of keys n_j"。实践中用线性组合。
  - 后验 δ_j 作为特征重要性，与模型联合训练，最后取 top-K。
- o_j 按四类特征取值：简单 query/user 特征直接查 embedding、简单 item 相关特征需复杂计算、复杂 query/user 特征、复杂 item 相关特征。表中取值依次为 0.4 / 1.5 / 1.0 / 3.0，类型与数值的对应关系按 PDF 抽取顺序推断。
- 原文强调 query/user 特征每次请求只算一次，item 相关特征的成本随候选数增长。这是**按特征类型差异化计成本**的依据。
- 关于成本结构，原文："storage for feature embeddings exceeds over 95% of that for the whole model, while feature generation process for embeddings consumes as much resources as that needed for the online inference of the model"。
- 结果：
  - 246 个字段中选 K = 100：AUC 仅比其他方法低 0.0026，延迟和 CPU 低约 30%；K > 100 后 AUC 增长缓慢而复杂度显著上升。
  - 在线 30 天：CTR 和 RPM 均显著提升，CPU 消耗与向量内积模型基本持平。
- 来源：[arXiv 2105.07706](https://arxiv.org/pdf/2105.07706)

**平台计费粒度：Databricks**
- 物化在计费中记为 FEATURE_STORE，可按 `data_source`（DELTA_TABLE_SOURCE / KAFKA_SOURCE）和 `operation`（FEATURE_MATERIALIZATION / KAFKA_INGESTION）切分，并通过 job_id / pipeline_id 归集。
- 粒度是**管道级，不是特征级**。
- serving endpoint 按 Model Serving SKU 计费；在线存储按 Lakebase CU 和副本数计费。
- 来源：[Databricks Feature Store cost management](https://docs.databricks.com/aws/en/machine-learning/feature-store/cost-management)

**Meta 效率类证据**
- IEFF：渐隐 275 个特征后，年基础设施成本约降 15%。来源：[arXiv 2605.00324](https://arxiv.org/pdf/2605.00324)
- AdaEmbed：embedding 缩小 35–60%，执行速度提升 11–34%（工业场景评估），按特征自动决定 embedding 大小。来源：[par.nsf.gov](https://par.nsf.gov/servlets/purl/10454226)
- ROO：相同存储下样本量提升 43–150%。来源：[arXiv 2508.05640](https://arxiv.org/pdf/2508.05640v3)

**离线 → 业务折算**
- JD："every 1‰ increase in off-line AUC brings 6 million dollars lift in the overall advertising income"。来源：[arXiv 2006.10337](https://arxiv.org/pdf/2006.10337)
- Etsy："Improvements in AUC (> 1%) have consistently resulted in significant CTR wins"。来源：[arXiv 1711.01377](https://arxiv.org/pdf/1711.01377)
- 低秩压缩：在线 AUC +0.079‰，AV +2.34%（7 天 A/B）。来源：[arXiv 2405.18146](https://arxiv.org/pdf/2405.18146)
- LinkedIn：广告 CTR 场景离线 AUC 与线上一致性好。来源：[arXiv 2402.06859](https://arxiv.org/pdf/2402.06859)
- csAUC：离线 AUC 涨而 CPM 不涨的情况常见。来源：[arXiv 1904.10272](https://arxiv.org/abs/1904.10272)
- ML Test Score Model 2：用故意劣化的模型做小规模 A/B，测离线-在线关系。来源：[PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/4156.pdf)

### Inferences（面向 R13 与成本账本的设计建议）

**1. 成本账本字段（单特征 × 单 usage）**

| 维度 | 字段 | 分摊方法 |
|---|---|---|
| 离线计算 | 物化 / 回填作业 CPU·h | 管道级账单按该管道产出特征的行数或列字节占比分摊（Databricks 计费只到管道级） |
| 存储 | 离线表字节 × 保留期；在线 KV 字节 × 副本 | 直接计量 |
| 模型侧 | embedding 参数量 = n_j × e_j（FSCD 的 n、e）及显存 | 直接计量 |
| 在线 | 取数 P99 延迟增量、单请求开销 | 按 o_j 类型系数区分 user 侧（每请求一次）与 item 侧（× 候选数），参照 FSCD |
| 维护 / 风险 | 上游依赖数、近 90 天告警次数、在线/离线不一致率 | 对应 ML Test Score 的 "instability" |

各项统一折算为"元/天"。

**2. ROI 准入**
- 准入条件 = 增益显著（CI 下界 > δ_min，多时间窗稳定），且 `折算收益(元/天) ≥ k × 成本(元/天)`。
- 折算斜率 β = Δ线上核心指标 / Δ离线指标，按场景用历史 AB 回归标定，并按 ML Test Score Model 2 定期用"故意劣化模型"补点。
- JD 1‰ 与 Etsy 1% 相差一个数量级，不可跨场景照搬。
- 广告场景同时要求校准非劣效，原因是 csAUC 和 LinkedIn 指出的 AUC 局限。

**3. 下线 ROI**
- 设计 5.4 的触发条件 3（"单位增益成本超阈值"）可以直接用上表的成本除以去特征消融的 Δ。
- 执行时走 IEFF 式渐隐 + AB 非劣效。

**4. 成本感知选择（V1 后）**
- 在 L2 或特征组选择中，可借鉴 FSCD，把 c_j 作为先验惩罚，输出"效果-成本"帕累托前沿（FSCD 中 K = 100 的拐点即属此类）。

### Gaps
- 未找到国内大厂公开的"AUC 千分之一 ≈ 收入 x%"一手表述（JD 除外）。
- JD 600 万美元的时间口径未知。
- 未找到 Meta、Pinterest 等单特征计算成本记账系统的一手工程文档。Meta 的一手资料（IEFF、AdaEmbed、ROO、Lattice）只给出总量级的节省。
- ShareChat 特征库降本 10× 的演讲只见检索摘要，未核。来源：[HackerNoon](https://hackernoon.com/optimizing-a-fast-feature-store-for-costs-sharechats-lessons-learned)
- FSCD 表 1 中 o_j 与特征类型的对应关系，是按 PDF 文本抽取顺序推断的，引用时需对照原表核对。
