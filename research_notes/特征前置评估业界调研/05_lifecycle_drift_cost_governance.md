# 特征生命周期管理、漂移处理、成本治理与 Shadow/AB 集成：业界调研笔记

> 对应评审项：R6（生命周期主体是"特征"还是"特征×模型"；缺 development/shadow/AB 状态）、R8（L1 用 PSI 阈值直接拒绝漂移特征）、R13（准入阈值缺业务口径与成本）、R14（缺护栏指标），以及计划中的"特征成本账本"。
>
> 来源说明：本次会话中 arxiv.org、huggingface.co 无法直接抓取（网络白名单限制），相关条目来自检索结果摘要。标记 **[训练知识]** 的条目是研究员已知的经典一手文献，本次会话未能在线复核全文，URL 为其公开地址。报告撰写时引用请保持此区分。

## Q1 业界特征平台的生命周期/状态模型：管理单元、元数据、下线流程与血缘影响分析

### Takeaway
没有一个主流特征平台把"特征"建模成多状态状态机。它们的管理单元是**特征视图/特征组/特征表**（一组特征），只有轻量的状态：活跃/已废弃（deprecated）/删除保护。生命周期治理靠三样东西：owner/tags 元数据、"模型→特征"的**消费血缘**（feature service / FeatureSpec / 模型日志），以及废弃时给出的告警。"特征×模型"关系在各平台里是一条**消费边**（usage/lineage），不是另一个生命周期主体。对 R6 的建议：特征本身走"定义级"生命周期（draft→registered→deprecated→deleted），"特征×模型"的 usage 走"实验级"生命周期（candidate→evaluated→shadow→AB→online→observed→offboarded），两层分开建模。

### Cited Findings
- **Tecton**：Feature View 有可选的 `owner`（主要维护者的名字或邮箱）和 `tags`（任意键值元数据）。`prevent_destroy` 标志用来防止误删生产中仍在使用的 Feature Service，或防止误重建 Feature View 触发昂贵的重新物化；要删除，必须先在 apply 中把它置为 False。修改 transformation 或 entity 被视为破坏性变更，会触发重新物化。检索中未找到 Tecton 的正式 "deprecated" 状态。— [Tecton BatchFeatureView SDK](https://tecton-docs.pages.dev/docs/sdk-reference/feature-views/BatchFeatureView)；[Tecton Feature Views](https://181797f1.tecton-docs.pages.dev/docs/defining-features/feature-views)
- **Hopsworks**：Feature Group 有显式的 deprecation。调用 `fg.update_deprecated()` 标记，`update_deprecated(deprecate=False)` 撤销，UI 中也有 Deprecate/Undeprecate。读取已废弃的 Feature Group，或读取基于它的 Feature View 时，系统会发出告警（软下线，不阻断）。— [Hopsworks Deprecation guide](https://docs.hopsworks.ai/4.8/user_guides/fs/feature_group/deprecation/)
- **Hopsworks 特征监控**：被定位为数据入库后对数据校验的补充，内容包括定时统计，以及与参考窗口做统计比较；配置只能用 Python，UI 只能启停或手动触发。— [Hopsworks Feature Monitoring](https://docs.hopsworks.ai/4.1/user_guides/fs/feature_group/feature_monitoring/)
- **Databricks（Unity Catalog）**：用 Feature Store 数据训练并记录的模型会自动跟踪到训练所用特征的血缘。Serving endpoint 通过 Unity Catalog 解析"被服务的模型→训练所用特征"，以及到 online store 的血缘。FeatureSpec 由 Unity Catalog 管理，带到底层特征表和函数的完整血缘，可在 Catalog Explorer 中查看。— [Databricks Feature Store concepts](https://docs.databricks.com/aws/machine-learning/feature-store/concepts)；[Databricks Feature Store](https://docs.databricks.com/machine-learning/feature-store)
- **Feast**：OpenLineage 集成在 apply feature view/feature service/entity 时，以及物化 START/COMPLETE/FAIL 时发出事件。Feature view 的 facets 带 owner 和 tags；feature service 会列出其包含的 feature views，可据此追踪依赖关系。— [Feast OpenLineage reference](https://docs.feast.dev/v0.60-branch/reference/openlineage)；[OpenLineage Feast integration](https://openlineage.io/docs/integrations/feast)
- **Feast + MLflow**：把特征检索记录到 MLflow run，能把模型映射回其 feature service，并支持反查"某 feature view 变更会影响哪些模型"。这是血缘驱动的影响分析。— [Feast MLflow integration](https://docs.feast.dev/master/reference/mlflow)
- **Vertex AI Feature Store**：数据源必须先注册到 Feature Registry 才能被监控。Monitor 建在 FeatureGroup 下，每次运行生成 FeatureMonitorJob（含统计与漂移结果）。默认漂移阈值 0.3，取值范围 [0,1)。计算方式是 BigQuery 的 ML.TFDV_VALIDATE：类别特征用 L-infinity 距离，数值特征用 Jensen-Shannon 散度。注意：Vertex 默认不用 PSI。— [Vertex AI Monitor features](https://docs.cloud.google.com/vertex-ai/docs/featurestore/latest/monitor-features)
- **Uber Palette（Michelangelo 特征库）**：用户在 Metastore 中创建和**废弃（deprecate）**特征，并登记 ownership、backfill、特征生成管道调度、离线训练、HDFS 位置、哪些特征需复制到在线服务、上游 SQL，以及变更审计。Palette 的定位是"Uber 内部精选 + 众包"的特征库，提供发现、创建、废弃、离线/在线服务配置。博文未说明触发废弃的条件（例如低使用率）。— [Uber: Palette Meta Store Journey](https://www.uber.com/en-ES/blog/palette-meta-store-journey/)
- **Airbnb Chronon**：用一致性作业（consistency job）比较在线服务值与离线回填值。度量方式：数值特征用 SMAPE，类别特征用不等比例，列表特征用编辑距离。Chronon 的出发点是替代 "log and wait"：先在线打日志、等数据积累再训练。这种方式保证一致性，但等待时间长。— [Chronon GitHub](https://github.com/airbnb/chronon)；[Airbnb: Chronon open source (2024)](https://medium.com/airbnb-engineering/chronon-airbnbs-ml-feature-platform-is-now-open-source-d9c4dba859e8)；[Zipline 演讲 PDF](https://microsites.databricks.com/sites/default/files/2022-07/Introducing-Zipline_An-Open-Source-Feature-Engineering-Platform.pdf)
- **[训练知识] Google "Rules of ML"**：Rule #11 "Give feature columns owners and documentation"，要求给每个特征列指定 owner 并编写文档。Rule #22 "Clean up features you are no longer using"：不再使用的特征会造成技术债，若某特征没在用、且与其他特征组合也无用，就删掉。— [Google Rules of ML (Zinkevich)](https://developers.google.com/machine-learning/guides/rules-of-ml)

### Inferences
- 业界的通行做法是：管理单元是**特征组/视图**，消费关系用 lineage 边来表达（Feast feature service、Databricks FeatureSpec/模型日志），"特征×模型"并不是一等的生命周期对象。我们的评估流程天然以"某候选特征对某目标模型的增益"为单位，所以 R6 的答案是**两者都需要**：
  1. **Feature（定义）级**：draft → registered/available → deprecated（软下线，告警，参考 Hopsworks）→ deleted（需"无消费者"校验，参考 Tecton `prevent_destroy`）。
  2. **Feature×Model（usage）级**：candidate → evaluated（离线）→ shadow（只打日志/只计算）→ AB → online → observed → offboarded。
  3. 约束：feature 只有在**所有** usage 都已 offboarded 后才能进入 deleted；某个 usage 被 offboard 不等于特征被下线。
- 影响分析应基于"特征→模型"的反向索引（参考 Feast+MLflow 的反查）。下线前列出全部消费模型，并给 owner 发通知。
- Vertex 的默认漂移度量是 JS/L∞，阈值 0.3，不是 PSI。这说明 PSI 只是可选度量之一，没有理由把它当作硬性准入指标。

### Gaps
- LinkedIn Feathr、Meta 内部特征平台、Twitter/X、Spotify、字节/阿里/美团的状态机细节未检索到一手资料。中文检索未命中三家技术博客中关于"特征下线/特征治理"的文章，建议在美团技术团队、字节火山引擎、阿里云文档站点内定向搜索。
- 未找到任何平台以"下线建议 = 无消费者 + 低重要性"自动驱动下线的公开实现细节。

## Q2 Shadow / dark launch / 只打日志阶段、canary 与实验平台集成；推荐/广告上线的护栏指标

### Takeaway
新特征上线的业界常见路径是：特征开关（flag）控制的**只计算、只打日志**阶段（dark launch/shadow），然后小流量 canary，再到正式 A/B，最后全量或回滚。shadow 阶段只能验证稳定性、延迟和线上线下一致性，不能衡量用户反应。护栏指标通常分三类：系统类（延迟、错误率、资源）、业务类（收入、预订等），以及用户体验/长期指标（评分、取消率、多样性等）。推荐/广告场景下还应加入校准（calibration）护栏。

### Cited Findings
- 推荐的发布路径：shadow（旧模型服务，新模型只算并记录对比）→ canary（小流量）→ 全量 A/B 测显著性 → 推全或回滚。shadow 无法得到真实在线 CTR，因为用户从未看到 shadow 的排序结果，它只验证稳定性和输出合理性。注：此为二手 MLOps 资料。— [machinelearningatscale: A/B testing ML models](https://www.machinelearningatscale.com/blog/a-b-testing-ml-models-production)；[helpmetest: Shadow mode & canary](https://helpmetest.com/blog/ab-testing-ml-models-production/)
- Martin Fowler 的 Dark Launching：在生产中先让新路径悄悄运行，用 feature flag 在性能出问题时快速关闭。— [Martin Fowler, DarkLaunching](https://martinfowler.com/bliki/DarkLaunching.html)
- Airbnb Experiment Guardrails（2021）：平台每周同时运行数千个在线实验，在 Airbnb 的规模下，收入下降 0.1% 可能意味着数百万美元。案例：结账页不展示"房屋守则"使预订上升、评分下降，被护栏标记并升级评审，没有直接上线。按二手总结，护栏每月触发约 25 个实验进入评审，并分为关键业务指标、用户体验指标、战略优先指标三类。— [Airbnb: Designing Experimentation Guardrails](https://medium.com/airbnb-engineering/designing-experimentation-guardrails-ed6a976ec669)
- Chronon 的在线/离线一致性作业：shadow 阶段可直接复用这套"在线服务值 vs 回填值"对比（SMAPE 等），作为进入 AB 前的门槛。— [Chronon GitHub](https://github.com/airbnb/chronon)；[Zipline PDF](https://microsites.databricks.com/sites/default/files/2022-07/Introducing-Zipline_An-Open-Source-Feature-Engineering-Platform.pdf)
- 只看 AUC 而忽略校准可能造成实际经济损失：csAUC 论文指出，实践中常见离线 AUC 上升但线上 CPM 不涨，原因是 AUC 只衡量 CTR 的排序，不反映 CTR×bid 的排序。— [CPM-sensitive AUC for CTR prediction](https://astro.paperswithcode.com/paper/cpm-sensitive-auc-for-ctr-prediction)
- **[训练知识]** Kohavi、Tang、Xu《Trustworthy Online Controlled Experiments》（2020）把指标分为 goal/driver/guardrail，guardrail 又分"组织护栏"（如延迟、收入）和"可信度护栏"（如 SRM 样本比例失衡）。书中引用的 Bing 实验显示，延迟增加会可测量地损害收入与用户指标。— [Cambridge University Press 书页](https://www.cambridge.org/core/books/trustworthy-online-controlled-experiments/D97B26382EB0EB2DC2019A7A7B518F59)
- **[训练知识]** He et al.（Facebook，ADKDD 2014）"Practical Lessons from Predicting Clicks on Ads at Facebook"：用 Normalized Entropy 和**校准**（预测 CTR/实际 CTR）评估广告模型，并强调数据新鲜度的影响。— [Meta Research 论文页](https://research.facebook.com/publications/practical-lessons-from-predicting-clicks-on-ads-at-facebook/)

### Inferences
- 对 R6 和 R14，建议在 usage 状态机中补齐以下状态：
  - `development`：特征开发与回填中。
  - `shadow`：线上计算并打日志，不进模型或不影响排序。出口条件：在线/离线一致性（SMAPE/缺失率）、P99 延迟增量、计算失败率、覆盖率达标。
  - `ab`：有护栏地放量。
  - 随后进入 `online`。
  - 出口条件统一挂到实验平台的实验 ID 上，用 flag 实现可回滚。
- 推荐/广告特征上线的护栏建议：
  - **系统**：P99 延迟增量、特征服务 QPS/超时率、特征缺失/默认值占比。
  - **业务**：收入/RPM、CTR/CVR。
  - **模型健康**：校准度（pcoc/ECE）。
  - **生态**：多样性/覆盖率/新内容曝光、负反馈率。
  - **可信度**：SRM。
- shadow 阶段同时是"log and wait"的数据积累窗口。对于离线无法回填的实时特征，shadow 日志是离线评估的唯一可靠数据源，因此 shadow 应排在 evaluated 之前或与之并行，不能只放在 evaluated 之后。

### Gaps
- 未找到 Meta/Netflix/Spotify 等一手博文专门描述"新特征（而非新模型）的 dark launch"流程，现有材料以模型级 shadow 为主。
- 未检索到 LinkedIn 护栏指标的一手资料（LinkedIn XLNT/T-REX 相关论文本次未能抓取）。

## Q3 漂移：漂移特征该拒绝吗？协变量漂移 vs 概念漂移，PSI 漂移何时真正影响效果，推荐处理方式

### Takeaway
主流观点是：**漂移不等于效果下降**，特征分布漂移只是效果下降的必要非充分信号。监控工具（NannyML、Arize 等）推荐"先估计或观测效果，效果掉了再看漂移"，并按特征重要性和业务风险给漂移告警排优先级。所以 L1 用 PSI 阈值直接拒绝特征过于激进（R8）。更合理的做法是：把稳定性作为评估维度和风险标签；用时间切分的评估直接测"漂移下的增益是否持续"；对漂移做归一化/相对化处理；上线后靠监控和重训兜底。

### Cited Findings
- VLDB（Dong et al., 2024）指出：并非所有数据漂移都会降低预测精度。论文提出定位"真正损害精度的漂移区域"，只针对有害漂移重训。— [VLDB: Efficiently Mitigating the Impact of Data Drift on ML Pipelines](https://mail.vldb.org/pvldb/volumes/17/paper/Efficiently%20Mitigating%20the%20Impact%20of%20Data%20Drift%20on%20Machine%20Learning%20Pipelines)
- 深度学习可靠性论文指出：模型可能对某些分布变化不敏感，而且这种不敏感往往正是想要的。— [Engineering Reliable Deep Learning Systems (arXiv 1910.12582)](https://arxiv.org/pdf/1910.12582)
- NannyML 研究者（Santiago Víquez）的博文报告了 580 组模型-数据集实验，结论是漂移信号推断效果下降的能力很差，建议先估计效果，效果下降时再查漂移。注：本次仅见检索摘要，未能抓取原文。— [HF blog: data drift & estimate model performance](https://huggingface.co/blog/santiviquez/data-drift-estimate-model-performance)
- NannyML 的 CBPE 用**校准后的置信度**在无标签情况下估计混淆矩阵，主要弱点是依赖校准，而校准在某些分布漂移下会恶化。后续 M-CBPE（2024 预印本）用于量化协变量漂移对效果的影响。— [NannyML quickstart](https://nannyml.readthedocs.io/en/stable/quick.html)；[Estimating Model Performance Under Covariate Shift Without Labels (arXiv 2401.08348)](https://arxiv.org/html/2401.08348v4)
- Arize：漂移不一定立即伤害指标，监控应按模型重要性和业务风险给特征排序。（厂商术语表，非同行评审。）— [Arize: What is data drift](https://arize.com/glossary/data-drift/)
- Vertex AI 的特征漂移是**监控**能力（定时 FeatureMonitorJob、阈值告警），不是准入拒绝。— [Vertex AI Monitor features](https://docs.cloud.google.com/vertex-ai/docs/featurestore/latest/monitor-features)
- **[训练知识]** 漂移类型的标准分类：covariate shift（P(x) 变，P(y|x) 不变）、prior/label shift、concept shift（P(y|x) 变）。只有后者必然使原映射失效；协变量漂移是否伤效果，取决于漂移是否落在模型误差大或外推的区域。— [Moreno-Torres et al., "A unifying view on dataset shift in classification", Pattern Recognition 2012](https://doi.org/10.1016/j.patcog.2011.06.019)；[Gama et al., "A survey on concept drift adaptation", ACM CSUR 2014](https://doi.org/10.1145/2523813)
- **[训练知识]** Rules of ML 中与漂移/时效相关的规则：Rule #8 "Know the freshness requirements of your system"（了解系统的数据新鲜度要求）；Rule #33 "If you produce a model based on the data until January 5th, test the model on the data from January 6th and after"（**按时间切分评估**）。— [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- **[训练知识]** 对抗验证（adversarial validation）：训练一个分类器区分"训练期 vs 评估期"样本，其特征重要性可定位漂移最强的特征。这是 Kaggle 社区的常用方法，用于诊断，而不是自动删除特征。（未找到权威一手论文出处。）

### Inferences
- R8 的建议改法：
  1. **L1 不再因 PSI 拒绝**，改为打"稳定性等级"标签（如 PSI<0.1 稳定、0.1–0.25 关注、>0.25 高漂移，这是信用评分行业的经验阈值，见 Gaps）。只有在漂移源于**口径/管道 bug**（缺失率突变、默认值占比突变、在线/离线不一致）时才阻断，这类本质是数据质量问题，不是漂移。
  2. 用**滚动时间切分评估**（多个连续时间窗训练→下一窗测试）衡量增益的**时间稳定性**，例如各窗 ΔAUC 的均值、最小值、方差，作为对高漂移特征的加严条件，不作为一票否决：高漂移特征需在 ≥k 个窗口中都有正增益。
  3. 对时间敏感的特征（计数、价格、热度），优先做**相对化/归一化**（占比、排名、与类目或全局均值之比、z-score 按天归一），并缩短统计窗口，从根源上降低 PSI。
  4. 上线后靠 observed 阶段的监控：按重要性加权的漂移告警，与效果估计（有延迟标签时用真实效果；推荐场景标签回流快，通常可直接看线上 AUC/校准）联动，触发重训或复评，而不是直接下线特征。
- 推荐/广告是标签回流较快的场景，"漂移→效果"可以直接观测。这进一步削弱了用 PSI 作为准入代理指标的必要性。

### Gaps
- 未找到 Evidently 官方关于"重要性加权漂移"的一手文档（检索未命中）。
- PSI 0.1/0.25 经验阈值源自信用评分实践，本次未找到可引用的原始出处。
- 未找到工业界公开的"稳定性加权特征选择"算法在推荐系统中的一手应用报告。

## Q4 特征成本与技术债：经典论述、成本敏感选择、业界剪枝降本、离线增益折算业务价值（准入阈值）

### Takeaway
Sculley 2015 和 Rules of ML 早已把"未充分利用的特征"（epsilon / legacy / bundled / correlated features）列为技术债，并建议定期做特征删除评估（leave-one-feature-out）。ML Test Score 要求"每个特征的收益都值得它的成本"。成本敏感/预算化特征选择有学术方法，但工业界公开资料多集中在 embedding 剪枝和样本去重。准入阈值的业务折算有公开锚点：JD 报告离线 AUC +1‰ ≈ 600 万美元广告收入；Airbnb 称收入 0.1% ≈ 数百万美元。同时有大量证据显示 AUC 与线上指标不一致，因此阈值应按场景标定，并结合校准与 AB。

### Cited Findings
- **[训练知识] Sculley et al., "Hidden Technical Debt in Machine Learning Systems", NeurIPS 2015**：在 "Underutilized Data Dependencies" 一节列出四类特征：Legacy Features（早期加入、后被新特征冗余）、Bundled Features（打包评估时一起加入，其中含无效特征）、ε-Features（提升极小但带来复杂度）、Correlated Features（与真正因果特征相关）。建议定期运行 leave-one-feature-out 评估来识别和删除。文中还讨论了 CACE（Changing Anything Changes Everything）、undeclared consumers、数据依赖的成本高于代码依赖。— [NeurIPS 2015 paper](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems)
- **[训练知识] Breck et al., "The ML Test Score: A Rubric for ML Production Readiness and Technical Debt Reduction", IEEE BigData 2017**：数据测试项包括 "The cost of each feature is worth its benefit"（考虑推理延迟、RAM、上游依赖、不稳定性），"No feature's cost is too much"，"Features adhere to meta-level requirements"，"Data pipeline has appropriate privacy controls"，"New features can be added quickly"，"All input feature code is tested"。监控项包括 "Data invariants hold in training and serving inputs"、"Training and serving features compute the same values"。— [Google Research 论文页](https://research.google/pubs/the-ml-test-score-a-rubric-for-ml-production-readiness-and-technical-debt-reduction/)
- **[训练知识] Rules of ML**：Rule #22 删除不再使用的特征；Rule #11 特征要有 owner 和文档；Rule #29 "The best way to make sure that you train like you serve is to save the set of features used at serving time"（训练即服务，打日志）。— [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- **成本敏感特征选择（学术）**：Raynal 等改造了 9 种特征选择方法以考虑单特征计算成本。各特征计算成本可相差几个数量级，在精度基本不变的前提下可把成本降低两个数量级（领域为网络模型选择，非推荐）。— [Cost-based feature selection for network model choice (arXiv 2101.07766)](https://ar5iv.arxiv.org/html/2101.07766)
- **推荐场景的成本正则**：DistDNAS 在特征交互搜索中使用"训练 FLOPs + 推理延迟"的成本度量和可微成本正则，报告在 Criteo Terabyte 上 AUC +0.001，同时节省 60% FLOPs。— [DistDNAS (arXiv 2311.00231)](https://arxiv.org/html/2311.00231v2)
- **Meta 相关降本研究**：
  - AdaEmbed（Meta 与密歇根大学）在训练中剪枝 embedding，部署后 embedding 缩小 35–60%，执行加速 11–34%，精度不降。— [par.nsf.gov PDF](https://par.nsf.gov//servlets/purl/10454226)
  - Request-Only Optimization 在日志层面对请求级特征去重，使训练样本量提升 43–150%。— [ROO (arXiv 2508.05640)](https://arxiv.org/html/2508.05640v1)
  - Meta Lattice 报告了 20% 的容量节省。— [Meta Lattice (arXiv 2512.09200)](https://arxiv.org/html/2512.09200v2)
  - 另有第三方转述称 Instagram Reels 做过特征审计、删除了数千个低影响特征，未能核实一手来源，**勿作为事实引用**。
- **离线增益 → 业务价值锚点**：
  - JD（Category-Specific CNN for Visual-aware CTR Prediction, KDD 2020）称，在其系统中离线 AUC 每提升 1‰，广告收入约增加 600 万美元（据检索摘要，原文未能抓取复核）。— [arXiv 2006.10337](https://arxiv.org/pdf/2006.10337)
  - Etsy：AUC 提升超过 1% 时，多轮线上 A/B 都带来显著的 CTR 提升。— [Etsy Promoted Listings CTR (arXiv 1711.01377)](https://arxiv.org/pdf/1711.01377)
  - 低秩压缩论文：线上 AUC 仅提升 0.079‰，广告主价值却提升 2.34%，原因是基线 AUC 已高、用户量大。— [Unified Low-rank Compression for CTR (arXiv 2405.18146)](https://arxiv.org/pdf/2405.18146)
  - Airbnb：收入下降 0.1% 可能对应数百万美元。— [Airbnb Experiment Guardrails](https://medium.com/airbnb-engineering/designing-experimentation-guardrails-ed6a976ec669)
- **AUC 与线上不一致的证据**：
  - csAUC 论文：离线 AUC 常上升而线上 CPM 不涨，浪费大量流量与人力。— [CPM-sensitive AUC](https://astro.paperswithcode.com/paper/cpm-sensitive-auc-for-ctr-prediction)
  - 竞价广告论文：离线 eCTR AUC 与线上 RPM 之间存在较大差异。— [Revenue Management in Sponsored Search (arXiv 1807.01827)](https://arxiv.org/pdf/1807.01827)

### Inferences
- **成本账本字段建议**（对标 ML Test Score 的"cost worth benefit"）：
  - 存储：离线表大小 × 保留期 + 在线 KV 占用。
  - 计算：回填和每日物化的 CPU/GPU 时，流式作业资源。
  - 在线：P99 取数延迟增量、QPS × 单次取数开销、embedding 参数量和显存。
  - 维护：上游依赖数、owner、近 90 天故障/告警次数、在线/离线不一致率。
  - 统一折算成"元/天"，用于计算 **ROI = 业务增益折算(元/天) / 成本(元/天)**。
- **R13 准入阈值建议**：
  1. 场景内用历史 AB 回归标定"ΔAUC/ΔGAUC → Δ线上核心指标"的斜率与置信区间。JD 的 1‰ 与 Etsy 的 1% 说明斜率随场景相差一个数量级，不能照搬。
  2. 准入条件 = 离线增益显著（多时间窗）且 折算收益 > k × 全生命周期成本。
  3. ε-features（增益 < 噪声下限，例如小于多 seed 的标准差）默认不进入 AB，除非成本极低。
  4. 校准指标作为并列门槛，因为 AUC 不反映 CTR×bid 排序。
- **下线策略**：定期（季度）对线上模型做 leave-one-feature-out 或 group ablation，结合成本账本输出"低 ROI 特征"清单（Sculley 的 legacy/bundled/ε 三类），走 Q1 中的 usage offboard → feature deprecate 流程。

### Gaps
- 未找到国内大厂（阿里/字节/美团）公开的"AUC 千分之一 ≈ 收入 x%"一手量化表述。"千分之一 AUC 是显著提升"在业界广泛流传，但本次没有检索到可引用的原始出处。
- 未找到 Pinterest/Meta 关于"按单特征计算成本记账"（compute-per-feature accounting）的一手工程博文；Meta 相关资料多为 embedding 剪枝或样本去重层面。
- JD 600 万美元数字及其前提，需在 arxiv 原文中复核（本次网络限制无法抓取）。
