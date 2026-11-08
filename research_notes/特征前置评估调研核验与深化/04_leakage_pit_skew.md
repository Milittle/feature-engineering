# 特征泄露检测、PIT 正确性与训练/服务偏差检测：第二轮核验与可落地参数

> 对应：方案 3.1（L1「疑似泄漏」）、5.2（上线 gate，含无出处的「一致率 ≥ 99.9%」）；评审 R5（候选特征如何进入评估样本）、R7（PIT 与 skew 无测试方法、泄露阈值未校准）。
> 第一轮笔记：`research_notes/特征前置评估业界调研/04_leakage_pit_skew.md`。
>
> 标记约定：
> - **[已核原文 + 位置]**：本轮直接读了一手原文或源码。
> - **[更正]**：一手原文与第一轮笔记的说法不一致，以本轮为准。
> - **[仍未核]**：本轮仍没拿到一手原文。
>
> 本轮取材方式：WebFetch 解析不了 tensorflow.org、developers.google.com、docs.deepchecks.com、docs.tecton.ai、help.aliyun.com、learn.microsoft.com 等域名，但用 **curl 经代理可以访问**，所以这些页面都是 curl 抓下来后转成纯文本阅读的。deepchecks、Evidently、TFDV、TFMD、Chronon、Feast、Hopsworks 直接读了 GitHub 上的源码或文档（raw.githubusercontent.com）。ML Test Score 和 Data Validation for ML 两篇论文是下载 PDF 全文阅读的。
>
> 本轮仍没拿到的一手资料：Kaufman 等的论文全文。cs.umb.edu 的 TLS 证书链无法验证，ACM 原文需登录，Semantic Scholar 标注为 CLOSED。Uber/Facebook 的资料本轮没有重新核对。

---

## 一、核验总表：第一轮的二手或未核说法逐条对照一手来源

### Takeaway
多数说法得到了一手原文的确认。有 5 处需要更正或补充：
1. ML Test Score 的计分是**取四组得分的最小值**，第一轮写的“< 7 危险、14–21 合理、> 21 领先”在 2017 版原文中不存在。
2. TFDV 的样本级 skew API 是 Beam PTransform **`tfdv.DetectFeatureSkew`**，不是函数 `detect_feature_skew`。
3. Feast master 文档已新增 **`filter_by_created_timestamp=True`**，可以修补 created_timestamp 带来的穿越。
4. Evidently 选默认检验时，还要看列的唯一值个数（nunique ≤ 5 时另有分支）。
5. deepchecks 条件 `add_condition_feature_pps_in_train_less_than` 的默认阈值是 **0.7**，补上了第一轮的空缺。

另外，Kaufman 论文的检测方法清单仍未核实。

### Cited Findings

**ML Test Score（Breck, Cai, Nielsen, Salib, Sculley，IEEE Big Data 2017）** — [论文 PDF](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- [已核原文，摘要与 §I] 共 28 项测试，分为 Data、Model、ML Infrastructure、Monitoring 四组，每组 7 项。作者调研了 Google 内部几十个团队，没有任何一项测试被超过 80% 的团队实现；访谈的系统共 36 个。
- [已核原文，§VI.A] 计分规则：
  - 手动执行并且结果有文档、有分发，得 0.5 分；
  - 有系统自动、重复地执行，得 1 分；
  - 四组各自求和，**最终 ML Test Score 取四组得分的最小值**（"taking the minimum of the scores aggregated for each of the 4 sections"）；
  - 所有测试分值相同。
- [已核原文，Table V] 分数解读：
  - 0：More of a research project
  - (0,1]：Not totally untested
  - (1,2]：first pass at basic productionization
  - (2,3]：Reasonably tested
  - (3,5]：Strong levels … appropriate for mission-critical systems
  - \>5：Exceptional
- [更正] 第一轮引用的二手资料（nhuantdbk、CMU 课件）说“< 7 危险、14–21 合理、> 21 领先”。这与 2017 正式版的计分规则矛盾：正式版取单组最小值，每组上限 7 分。那组数字可能出自更早的版本（例如 2016 年 NIPS workshop 的 "What's your ML test score?"），本轮未核实。
- [已核原文，§II、Table I] Data 组 7 项：
  - Data 1：Feature expectations are captured in a schema
  - Data 2：All features are beneficial
  - Data 3：No feature's cost is too much
  - Data 4：Features adhere to meta-level requirements
  - Data 5：privacy controls
  - Data 6：New features can be added quickly
  - Data 7：All input feature code is tested
- [已核原文，§II] Data 1 至 Data 7 的要点：
  - Data 2 的检验方法：计算相关系数、训练只用一两个特征的模型，或者训练 k 个各去掉一个特征的模型。
  - Data 6 说，高效团队从特征想法到上线可以只用 "one to two months"。
  - Data 7 说，特征代码的 bug 一旦进入数据生成过程就“几乎无法发现”，“尤其当它同时出现在训练和测试数据中时”。
- [已核原文，§IV] 与特征相关的 Infra 项：
  - Infra 1（Training is reproducible）举例：验证新旧特征生成代码训练出同一个模型，用来给重构做 diff-testing。
  - Infra 3：完整 pipeline 的集成测试。
- [已核原文，§III] Model 组相关项：
  - Model 2：离线代理指标与线上指标相关，方法是做一个故意降级的模型来跑小规模 A/B。
  - Model 6 给出了切片门槛的示例：绝对门槛 "error for slice x must be <5%"，增量门槛 "change … <1% compared to the previously released model"。
- [已核原文，§V，Monitor 2] 原文："Data invariants hold in training and serving inputs"。做法是用 Data 1 的 schema 检查数据，并 "careful tuning of alerting thresholds is needed to achieve a useful balance between false positive and false negative rates"。
- [已核原文，§V，Monitor 3] 标题原文是 "Training and serving features compute the same values"，Table IV 中的简称是 "Training and serving are not skewed"。原文写道：
  - "it is crucial to log a sample of actual serving traffic … adding identifiers to each example at serving time will allow direct comparison; **the feature values should be perfectly identical at training and serving time for the same example**. Important metrics to monitor here are **the number of features that exhibit skew, and the number of examples exhibiting skew for each skewed feature**."
  - 第二种做法是比较分布统计量（min、max、average、缺失比例），阈值同样 "must be carefully tuned"。
  - 新特征需要用独立代码路径做回填（backfill），原文明确把这种情况列为 skew 的来源之一。
- [已核原文，§VII.C] "Perhaps the most important and least implemented test is the one for training/serving skew (Monitor 3)."

**Data Validation for Machine Learning（Breck, Polyzotis, Roy, Whang, Zinkevich，SysML 2019，即 TFDV 背后的论文）** — [论文 PDF](https://mlsys.org/Conferences/2019/doc/2019/167.pdf)
- [已核原文，§4 "Training-Serving Skew"] 论文把 skew 分为三类：
  - **Feature skew**：同一样本的特征在训练和服务时取值不同。其中一种机制叫 **time travel**：特征值通过查询一个非静态数据源得到。例如训练时查询点击数，会把服务之后才发生的点击也算进去。
  - **Distribution skew**：批数据的分布不同，例如采样有偏。
  - **Scoring/Serving skew**：只有部分被打分的样本真正被展示，形成反馈环。论文说这一类最难检测。
- [已核原文，§4] 检测方法：服务端 "log a sample of the serving data"。检测 feature skew 时，"does a **key-join** between corresponding batches of training and serving data followed by a **feature wise comparison**"。skew 检测的参数作为约束写在 schema 里。
- [已核原文，§4 "Quantifying Distribution Distance"] 论文反对用卡方等拟合优度检验报警。实验：从 N(0,1) 取 1 亿个点，随机替换其中 1 万个为 N(0,2) 的样本（0.01% 噪声）；在 α = 1% 下，卡方检验 10 次中有 **7 次误报**。论文改用 **d∞(p,q) = max_i |p_i − q_i|**，理由是团队容易设阈值，例如 "allow changes of only up to 1% for each value"；报警时还会给出 "culprit" 取值，原文举的例子是值 '-1' 突增，对应某个后端故障时返回默认值。论文用 Dirichlet 先验做统计上稳健的估计（附录 B）。
- [已核原文，§6 案例] Google Play 用 TFDV 发现若干特征在线上日志中总是缺失、训练中却总是存在。消除这个 skew 后，A/B 实验显示主落地页的 app 安装率提升 **2%**。

**TFDV（tensorflow.org get_started、TFX guide、TFMD proto、TFDV 源码）**
- [已核原文，[TFDV Get Started](https://www.tensorflow.org/tfx/data_validation/get_started) "Checking data skew and drift" 节] 官方示例：
  - 代码：`tfdv.get_feature(schema, 'payment_type').skew_comparator.infinity_norm.threshold = 0.01`，然后调用 `tfdv.validate_statistics(statistics=train_stats, schema=schema, serving_statistics=serving_stats)`。
  - 原文 NOTE："L-infinity norm will only detect skew for the categorical features … specifying a jensen_shannon_divergence threshold in the skew_comparator would detect skew for both numeric and categorical features"。
  - 输出是 Anomalies proto。示例报文："The L-infinity distance between serving and training is 0.0435984 … above the threshold 0.01. The feature value with maximum difference is: Cash"。drift_comparator 的用法相同，示例阈值同样是 0.01。
  - [已核原文] 0.01 只是**文档示例**，不是默认值。
- [已核原文，[TFX TFDV guide (GitHub)](https://github.com/tensorflow/tfx/blob/master/docs/guide/tfdv.md) "Drift Detection" 节] drift 在类别特征上用 L-infinity distance，在数值特征上用 "approximate Jensen-Shannon divergence"。原文："Setting the correct distance is typically an iterative process requiring domain knowledge and experimentation."
- [已核原文，[TFMD schema.proto](https://github.com/tensorflow/metadata/blob/master/tensorflow_metadata/proto/v0/schema.proto)] 各度量的定义：
  - `InfinityNorm`：L∞(p,q) = max_i |p_i − q_i|，只看 top-k；取值在 [0,1]，"sensible bounds should be in the interval [0.0, 1.0)"。
  - `JensenShannonDivergence`：同样在 [0,1]；可选 `HistogramSelection`（DEFAULT / QUANTILES / STANDARD），"Currently the default is STANDARD. Calculations based on QUANTILES are more robust to outliers"。
  - `NormalizedAbsoluteDifference` = max_i |x_i − y_i| / Σ_i(x_i + y_i)，适合比较“绝对计数也应相近”的数据集。
  - `FeatureComparator` 由以上三者组成。
  - `DatasetConstraints` 包含 `num_examples_drift_comparator`、`num_examples_version_comparator`、`min_examples_count`、`max_examples_count`。
- [更正，[TFDV `__init__.py`](https://github.com/tensorflow/data-validation/blob/master/tensorflow_data_validation/__init__.py)；[feature_skew_detector.py](https://github.com/tensorflow/data-validation/blob/master/tensorflow_data_validation/skew/feature_skew_detector.py)] 样本级 skew 检测的公开 API 是 **`tfdv.DetectFeatureSkew`**（Beam PTransform），配套 `get_skew_result_dataframe`。它没有 `detect_feature_skew` 这个函数。实现方式：
  - 按 `identifier_features` 计算指纹，再 join baseline 与 test 样本；
  - 逐特征比较序列化后的值；
  - `float_round_ndigits` 控制浮点比较前保留的小数位（即数值容差）；
  - `allow_duplicate_identifiers` 控制是否允许重复 ID；
  - `ConfusionConfig` 可以输出 (base 值, test 值, count) 混淆计数，但只支持单值的 bytes 特征，int 和 float 不支持；
  - 可选输出 skew 样本对。
- [已核原文，[feature_skew_results.proto](https://github.com/tensorflow/data-validation/blob/master/tensorflow_data_validation/skew/protos/feature_skew_results.proto)] 输出字段：
  - `FeatureSkew`：`feature_name, base_count, test_count, match_count, base_only, test_only, mismatch_count, diff_count`，其中 **diff_count = base_only + test_only + mismatch_count**。所有计数只统计两侧都有 ID 的样本。
  - `MatchStats`：`base_with_id_count, test_with_id_count, identifiers_count, ids_missing_in_base_count, ids_missing_in_test_count, matching_pairs_count, duplicate_id_count, base_missing_id_count, test_missing_id_count`。
  - `SkewPair`：base 与 test 的原始样本，外加 base_only、test_only、matched、mismatched 特征列表。
- [仍为第一轮一手，未复核] BigQuery `ML.TFDV_VALIDATE` 默认阈值 0.3，类别特征默认 L_INFTY，数值特征用 JSD — [BQML docs](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-validate)

**Google Rules of ML** — [developers.google.com](https://developers.google.com/machine-learning/guides/rules-of-ml)（[已核原文，"Training-Serving Skew" 节及 Rule #5]）
- 定义："Training-serving skew is a difference between performance during training and performance during serving." 三类成因：训练与服务管线处理数据的方式不一致；训练和服务之间数据发生了变化；模型与算法之间的反馈环。
- **Rule #5**："Test the infrastructure independently from the machine learning." 包括检查本应有值的特征列确实有值；可能的话，把管线内的统计量与别处处理同一份数据得到的统计量对比；确保训练环境和服务环境中的模型对同一输入给出相同分数。
- **Rule #29**："The best way to make sure that you train like you serve is to save the set of features used at serving time, and then pipe those features to a log to use them at training time." 正文："Even if you can't do this for every example, do it for a small fraction, such that you can verify the consistency between serving and training (see Rule #37). Teams that have made this measurement at Google were sometimes surprised by the results." YouTube 首页改为服务时落特征后，"significant quality improvements and a reduction in code complexity"。
- **Rule #30**："Importance-weight sampled data, don't arbitrarily drop it!" 以 30% 概率采样的样本给权重 10/3。
- **Rule #31**："Beware that if you join data from a table at training and serving time, the data in the table may change." 最简单的办法是服务时落特征。如果表变化很慢，也可以按小时或按天做快照，但 "this still doesn't completely resolve the issue"。
- **Rule #32**："Re-use code between your training pipeline and your serving pipeline whenever possible." 用一个人类可读的中间对象，再由公共方法转换成模型输入格式；另外 "try not to use two different programming languages between training and serving"。
- **Rule #33**："If you produce a model based on the data until January 5th, test the model on the data from January 6th and after." 新数据上的表现 "shouldn't be radically worse"，AUC "should be reasonably close"。
- **Rule #34**：在过滤类任务中，留出 1% 流量作为 held out；如果只用来测量线上效果，比例可以更小，"say 0.1% or 0.001%"。原文："Ten thousand examples is enough to estimate performance quite accurately."
- **Rule #35**："Beware of the inherent skew in ranking problems."
- **Rule #36**："Avoid feedback loops with positional features."
- **Rule #37**："Measure Training/Serving Skew." 原文把 skew 分解为三段差距：
  1. 训练集与 holdout 的效果差：总会存在，不一定是坏事；
  2. holdout 与 "next-day" 数据的效果差：总会存在，但跌幅过大可能说明有时间敏感的特征；
  3. next-day 与线上的效果差："If you apply a model to an example in the training data and the same example at serving, it should give you exactly the same result … a discrepancy here probably indicates an engineering error."

**Feast** — [point-in-time-joins.md (feast master)](https://github.com/feast-dev/feast/blob/master/docs/getting-started/concepts/point-in-time-joins.md)；[feature-retrieval.md](https://github.com/feast-dev/feast/blob/master/docs/getting-started/concepts/feature-retrieval.md)
- [已核原文] 对每个 entity 行，"scan backward in time from the entity dataframe timestamp up to a maximum of the TTL"。原文："TTL is relative to each timestamp within the entity dataframe. TTL is not relative to the current point in time"。比最早特征还早的行，或超出 TTL 的行，都 join 不到值，返回 null。
- [已核原文] `event_timestamp` 是查询的上界，而且是**包含等号**的（"**upper bound (inclusive)**"），语义是取 "at or before" 的最新值，原文称之为 "last known good value"。
- [已核原文 + 更正] 原文："By default, point-in-time joins only constrain the feature's event timestamp. If a data source also has a `created_timestamp_column`, it is used to **deduplicate** rows that share an event timestamp (the row with the highest created timestamp wins), but it is not otherwise filtered. This means a value that was backfilled or corrected *after* an entity dataframe timestamp can still be returned." 这证实了第一轮的二手说法。但 master 文档已经新增 **`filter_by_created_timestamp=True`**，作用是给 join 加上 `created_timestamp <= entity_timestamp` 条件。启用后，created timestamp 为 NULL 的行会被排除；不支持该参数的 offline store 会**直接报错**，不会静默忽略。

**Tecton** — [Constructing training data (Tecton docs 镜像，文档版本未标明)](https://tecton-docs.pages.dev/docs/reading-feature-data/reading-feature-data-for-training/constructing-training-data)
- [已核原文，§2.3] 生成训练数据时用 AS OF join，把训练事件时间戳与特征的 `_effective_timestamp` 对齐，取 "closest timestamp … **less than or equal to**" 事件时间的那条记录。
- `_effective_timestamp` 的定义是 "**the earliest time the feature will be available in the online store for inference**"，并且总是 ≥ 特征时间戳。按特征视图类型计算如下：
  - Batch FV：物化任务的开始时间（由 batch_schedule 决定）加上 `data_delay`；
  - Stream FV，`TIME_INTERVAL` 模式：最后一个 aggregation_interval 的结束时刻；
  - Stream FV，`CONTINUOUS` 模式或不带窗口聚合：就是特征时间戳。

**Azure ML managed feature store** — [Point-in-time join concepts](https://learn.microsoft.com/en-us/azure/machine-learning/offline-retrieval-point-in-time-join-concepts)
- [已核原文] 对时间戳为 t 的观测事件，取窗口 **[t − temporal_join_lookback, t − source_delay]** 内最新的特征值。
  - `source_delay`：数据从发生到可用的延迟，默认 0。原文："without consideration of source delay, the model uses feature values from the nearest past … the predictive scores degrade"。
  - `temporal_join_lookback`：默认无穷大，必须大于 source_delay，否则 join 结果为空。

**Hopsworks** — [offline_api.md (logicalclocks docs 源)](https://github.com/logicalclocks/logicalclocks.github.io/blob/main/docs/concepts/fs/feature_view/offline_api.md)
- [已核原文] 用各 feature group 的 event_time 列，取 "the most recent (but not newer)" 特征值，join 到包含 label 的 feature group 上，后者的时间戳就是观测时间。也可以用 spine group 精确指定实体集合，避免同一实体在训练集中重复出现造成偏差。

**Databricks**
- [仍为第一轮一手，未复核] 对每行取 `timestamp_lookup_key` 之前的最新值；`lookback_window` 为实验性参数 — [Databricks docs](https://docs.databricks.com/aws/machine-learning/feature-store/time-series)

**Chronon** — [Online_Offline_Consistency.md (airbnb/chronon docs)](https://github.com/airbnb/chronon/blob/main/docs/source/test_deploy_serve/Online_Offline_Consistency.md)
- [已核原文] 原文："While 100% consistency is desirable, it is not always possible." 列出的成因：
  - 实时特征受 Kafka 和 KV 写入延迟影响，量级 "ms to seconds"；
  - 批特征计算加上传 KV 需要 "minutes or hours"，日更特征的不一致 "usually centered around midnight"。
- [已核原文，Design] 线上查询日志表 `query_logs(key_bytes, value_bytes, ts_millis, query_source)`，按 ds 和 join_name 分区，retention 90 天。
- 采样**按 key 抽样**（`hash(key_bytes) % 100 * 1000 <= sample_percent * 1000`），不随机抽查询，目的是抓到同一 key 的所有实例，并减少 bloom filter 要接受的 key 数。
- 计算方式：用 logged 表替换 join 的左表，重新离线计算 join，然后比较两边的值。
- 指标：
  - 通用：mismatch = count(a≠b)/count(\*)；missing = count(a=null & b≠null)/count(\*)；extra = count(a≠null & b≠null)/count(\*)（原文如此）。
  - 数值：smape = Σ|a−b| / Σ(a+b)，外加 delta 分布、logged 分布、backfilled 分布。
  - 序列：长度分布，以及 Levenshtein 编辑距离（插入和删除分开计数，不允许替换）。
  - map：标注为 TODO。
- 产出：每个 join 一张 `<join>_consistency_metrics` 表，分区为 ds、hr_minute、group_by_name。
- **原文没有给任何合格阈值。**
- 未来工作：支持给 groupBy 指定 write-lag，离线 join 时把查询时间戳整体后移这个量；lag 的大小可以用这套一致性框架来估计。

**deepchecks `FeatureLabelCorrelationChange`** — [源码 (deepchecks main)](https://github.com/deepchecks/deepchecks/blob/main/deepchecks/tabular/checks/train_test_validation/feature_label_correlation_change.py)
- [已核原文] 构造参数默认值：`n_top_features=5`、`n_samples=100_000`、`min_pps_to_show=0.05`、`ppscore_params=None`、`random_state=None`。
- [已核原文] `add_condition_feature_pps_difference_less_than(threshold=0.2, include_negative_diff=True)`：
  - 差值定义为 train PPS 减 test PPS；
  - 默认取**绝对值**比较，`include_negative_diff=False` 时只看正差；
  - 条件是 **`pps_diff >= threshold` 即判 FAIL**；
  - 文档对正差的解读："the test dataset is less predictive of the label than the train dataset, as this could indicate leakage of labels into the train dataset"。
- [已核原文，补第一轮空缺] `add_condition_feature_pps_in_train_less_than(threshold=0.7)`：训练集上单特征 PPS ≥ 0.7 即告警。

**Evidently** — [源码 stattests/registry.py (evidently main，legacy 路径)](https://github.com/evidentlyai/evidently/blob/main/src/evidently/legacy/calculations/stattests/registry.py)
- [已核原文 + 细化更正] 默认检验按 **reference 集行数**和**两集合并后的唯一值个数 nunique** 选择：
  - reference ≤ 1000 行：数值列 nunique ≤ 5 时用卡方（nunique > 2）或 z 检验（nunique ≤ 2），nunique > 5 时用 KS；类别列用卡方或 z 检验。
  - reference > 1000 行：数值列 nunique ≤ 5 时用 JS，> 5 时用 Wasserstein（归一化）；类别列用 JS。
  - 文本列另有处理。
- [已核原文，各 stattest 文件] 各检验的 `default_threshold`：
  - wasserstein：0.1
  - jensenshannon：0.1
  - psi：0.1
  - ks：0.05（p 值）
- [已核原文，data_drift.py] 数据集层面：`drift_share=0.5`，漂移列占比 **≥** 0.5 即判定数据集漂移。
- 第一轮说法基本正确，只是漏了 nunique ≤ 5 的分支，并且把“样本数”笼统地写成了 reference 行数以外的口径。

**阿里 PAI-Rec 一致性检查** — [阿里云文档：使用一致性检查解决离在线特征不一致](https://help.aliyun.com/zh/airec/what-is-pai-rec/user-guide/consistency-check/)
- [已核原文] 排查的问题类型：特征名称不一致、类型不匹配、特征缺失、特征值不匹配，以及模型 processor（EasyRec FG、默认值、特征加载）的处理逻辑错误。
- [已核原文] 九步流程：
  1. 控制台创建并开启任务；
  2. 引擎从配置中心拿到任务参数；
  3. 引擎把特征日志落盘到 MaxCompute；
  4. 配置中心**按采样比例**调用引擎的“特征重放 API”；
  5. 引擎以 debug 模式调用 EAS 模型，拿到模型 FG 前后的全部特征；
  6. 返回 debug 信息；
  7. debug 日志落盘；
  8. 把特征日志当作离线样本预测；
  9. 对比离线与在线的特征和打分。
- [已核原文] 采样比例最大 100%，文档举例：QPS=10、采样 10% 时，每秒采 1 条。
- [已核原文] 结果按 Userid、Itemid、Requestid 展示打分差异表（按差异降序）。原文："**一般 ScoreDiff 的值差异在小数点后四位以外，我们就可以认为离在线的打分是一致的了**"，即 |ScoreDiff| < 1e-4 视为一致。另外，在线 item_id 取值为 '-1024' 表示没有取到。这是本轮找到的**唯一公开的数值化一致性容差**，而且是打分层面的，不是特征层面的。

**Kaufman et al.（KDD 2011 / TKDD 2012）**
- [仍未核] 检测方法的原文清单没拿到：cs.umb.edu 镜像 TLS 证书链校验失败，ACM 原文需登录，Semantic Scholar 标注为 `openAccessPdf: CLOSED`。只确认了书目信息：KDD 2011 版 DOI 10.1145/2020408.2020496；TKDD 6(4) Art.15 版 DOI 10.1145/2382577.2382579，增加了作者 Stitelman — [Semantic Scholar API](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1145/2020408.2020496)；[DOI](https://www.doi.org/10.1145/2382577.2382579)

**Uber / Facebook**
- 本轮没有重新抓取，沿用第一轮的来源（[Uber blog](https://www.uber.com/blog/taming-ml-firehose/)；ADKDD 2014 论文镜像）。

### Inferences
- ML Test Score 的计分取四组最小值，这和我们的 gate 思路一致：任何一组短板都会拉低整体分。如果方案要引用 ML Test Score，应采用 Table V 的 0–5+ 刻度。
- 几个一手来源合起来，对 skew 测量方法的口径是一致的：
  - Monitor 3：按 ID join，逐值比较，统计“有 skew 的特征数”和“每个 skew 特征的样本数”；
  - Data Validation 论文：key-join 加逐特征比较；
  - TFDV：`DetectFeatureSkew`；
  - Chronon：logged 与 backfilled 对比。
  
  这几处都把“样本级逐值比对”当作主方法，分布比较只是补充。

### Gaps
- Kaufman 论文的检测方法清单仍然缺失，需要有 ACM 权限的人下载原文，或者放开 cs.umb.edu 的证书校验问题后再核。
- Feast 的 `filter_by_created_timestamp` 从哪个版本引入、哪些 offline store 支持，本轮没有核实（只看了 master 分支文档）。
- Evidently 新版 API（非 legacy 路径）的默认值是否与 legacy 相同，本轮没有核实。
- Tecton 文档镜像的版本号没有标明。

---

## 二、PIT 正确性：可执行的测试套件（回应 R5、R7）

### Takeaway
各家的 PIT 语义已统一核实：取“特征时间 ≤ 样本时间”的最新值，并受 TTL 或 lookback 限制。真正的分歧在于“特征时间”用哪个时间：

| 产品 | 默认用的“特征时间” | 是否考虑可得延迟 |
|---|---|---|
| Feast | event_timestamp | 默认不考虑；新增参数可按 created_timestamp 过滤 |
| Tecton | _effective_timestamp（物化时间 + data_delay） | 默认考虑 |
| Azure ML | 事件时间减去 source_delay | 显式参数，默认 0 |

因此我们的 PIT 断言必须基于 **availability time**，不能只看 event time。测试方法可以直接借 Chronon 的 logged 与 backfilled 对比，再加上本轮设计的“未来注入”测试。

### Cited Findings
- Feast：join 上界包含等号；TTL 相对每一行的时间戳；created_timestamp 默认只用于去重，因此回填或修正的值可能穿越；`filter_by_created_timestamp=True` 可以修补 — [Feast PIT docs](https://github.com/feast-dev/feast/blob/master/docs/getting-started/concepts/point-in-time-joins.md)
- Tecton：`_effective_timestamp` 是 "the earliest time the feature will be available in the online store for inference"；Batch FV 的值为物化开始时间加 data_delay — [Tecton docs](https://tecton-docs.pages.dev/docs/reading-feature-data/reading-feature-data-for-training/constructing-training-data)
- Azure ML：取窗口 [t − lookback, t − source_delay]；忽略 source_delay 会造成泄漏，上线后分数下降 — [Azure ML docs](https://learn.microsoft.com/en-us/azure/machine-learning/offline-retrieval-point-in-time-join-concepts)
- Hopsworks：取 "most recent (but not newer)"；可用 spine group 指定实体集合 — [Hopsworks docs 源](https://github.com/logicalclocks/logicalclocks.github.io/blob/main/docs/concepts/fs/feature_view/offline_api.md)
- Data Validation 论文：**time travel** 是 feature skew 的一种机制，即训练时查询非静态数据源，拿到了服务之后才发生的数据 — [Breck et al. 2019](https://mlsys.org/Conferences/2019/doc/2019/167.pdf)
- Rules of ML #31：训练和服务时 join 同一张会变化的表会产生 skew；按小时或按天快照只能缓解，不能根治 — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Chronon 的一致性检查做法：用线上 query log 替换 join 左表，离线重算后对比；不一致的来源是流延迟（ms 到 s 级）和批上传延迟（分钟到小时级，集中在午夜附近）；未来工作是用 groupBy write-lag 后移查询时间戳 — [Chronon consistency doc](https://github.com/airbnb/chronon/blob/main/docs/source/test_deploy_serve/Online_Offline_Consistency.md)
- ML Test Score Monitor 3 明确把“新特征需要用独立代码路径回填”列为 skew 来源 — [ML Test Score](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)

### Inferences（以下为设计推论，不是某一家公开的做法，除非另有注明）
**R5（候选特征如何进入评估样本）的建议口径**：评估样本的 spine 用线上请求日志，每行带 request_id、entity、sample_ts（请求时刻）。候选特征通过 PIT join 进入样本，join 条件为 `avail_ts ≤ sample_ts` 且 `sample_ts − avail_ts ≤ TTL`，其中：

```
avail_ts = max(event_ts, created_ts, 批物化完成时刻 + data_delay)
```

这个口径对齐 Tecton 的 effective_timestamp 和 Azure 的 source_delay。join 不到时填 null，并单独统计覆盖率。

**PIT 测试套件**：

| 编号 | 测试 | 方法 | 判定（建议） | 依据 |
|---|---|---|---|---|
| P1 | 可得时间断言 | 对样本表逐行断言 `avail_ts ≤ sample_ts`。窗口聚合的窗口右端点 < sample_ts，且不包含样本自身事件（对应方案 5.2 第 5 条） | 违规行数 = 0（硬门槛） | Feast、Tecton、Azure 的语义 |
| P2 | 未来注入（canary）测试 | 在源表中注入哨兵记录：(a) event_ts > sample_ts；(b) event_ts ≤ sample_ts 但 created_ts > sample_ts（模拟回填或修正）；(c) 落在窗口边界 = sample_ts 的事件。重跑特征生成和 join | 哨兵值出现在样本中的次数 = 0；(c) 的处理必须符合定义（包含或排除自身事件） | 推论；针对 Feast 默认语义的漏洞设计 |
| P3 | Logged vs Backfilled | 新特征先进影子模式落日志 N 天（按 key 哈希抽样），用离线 PIT 逻辑在同一 request_ts 回填后逐值比较 | 指标与阈值见第三节 S3 | Chronon；ML Test Score Monitor 3；Rule #29 |
| P4 | 延迟平移敏感性 | 把 sample_ts 整体前移 Δ（Δ 取 {声明的 data_delay、1h、1d}），重做 join 和单特征 AUC | 若 AUC 在 Δ = 声明延迟时明显下降，说明特征依赖的数据在线上拿不到，即可得时间被低估 | 推论；思路与 Chronon "groupBy lag" 未来工作一致 |
| P5 | Midnight vs PIT | 同一特征分别按日快照和精确 PIT 计算，比较差异 | 差异大的特征在线上必须按快照语义服务，否则视为不一致 | 第一轮 Zipline 幻灯片（二手 PDF） |
| P6 | TTL 与空值 | 统计 null 率随 sample_ts − 最近特征时间的分布 | 线上与离线的 null 率差异纳入 S3 的 missing 指标 | Feast TTL 语义 |

### Gaps
- 没有找到任何厂商公开的“PIT 违规率”或“哨兵注入”测试规范。P2 和 P4 属于自行设计，需要在我们的数据上试跑验证。

---

## 三、训练/服务 skew：分层检查与阈值来源（回应 R7、5.2 的 99.9%）

### Takeaway
一手来源里**没有任何“一致率 ≥ 99.9%”的出处**。各来源的立场如下：

| 来源 | 立场 |
|---|---|
| ML Test Score Monitor 3 | 同一样本的特征值 "should be perfectly identical"，监控“有 skew 的特征数”和“每个特征的 skew 样本数” |
| Rules of ML #37 | 同一样本在训练和线上 "should give you exactly the same result"，有差异 "probably indicates an engineering error" |
| Chronon | 承认 100% 一致不总是可能，但不给阈值 |
| PAI-Rec | 唯一的数值容差：|ScoreDiff| < 1e-4（打分层面） |
| TFDV、Evidently、BQML | 分布层只给了示例值或默认值（0.01、0.1、0.3），并且都明确要求按团队情况迭代调参 |

因此 5.2 的 99.9% 应改为“按特征类型定义的样本级指标 + 基于 A/A 噪声底的校准阈值”，并在文档中注明这是内部设定。

### Cited Findings
- Monitor 3 原文：同一样本 "should be perfectly identical"；监控指标为 "number of features that exhibit skew, and the number of examples exhibiting skew for each skewed feature"；分布比较的阈值 "must be carefully tuned to ensure a low enough false positive rate" — [ML Test Score](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Rule #37 的三段分解（训练 vs holdout、holdout vs next-day、next-day vs live），最后一段 "should give you exactly the same result" — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Rule #29：至少对 "a small fraction" 样本落特征，用于一致性校验 — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- Rule #34：用于测量线上效果的样本可以小到 0.1% 甚至 0.001%，"Ten thousand examples is enough to estimate performance quite accurately" — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- TFDV `DetectFeatureSkew`：输出 match_count、mismatch_count、base_only、test_only、diff_count 和 MatchStats；`float_round_ndigits` 作为浮点容差 — [TFDV 源码](https://github.com/tensorflow/data-validation/blob/master/tensorflow_data_validation/skew/feature_skew_detector.py)；[结果 proto](https://github.com/tensorflow/data-validation/blob/master/tensorflow_data_validation/skew/protos/feature_skew_results.proto)
- Data Validation 论文：d∞ 便于理解，例如 "allow changes of only up to 1% for each value"；卡方检验在大样本下会误报（实验中 10 次误报 7 次） — [Breck et al. 2019](https://mlsys.org/Conferences/2019/doc/2019/167.pdf)
- TFDV 示例阈值为 L∞ = 0.01（示例，不是默认值）；JSD 可选 QUANTILES 直方图，对离群值更稳健 — [TFDV get_started](https://www.tensorflow.org/tfx/data_validation/get_started)；[schema.proto](https://github.com/tensorflow/metadata/blob/master/tensorflow_metadata/proto/v0/schema.proto)
- Evidently 默认阈值：Wasserstein 0.1、JS 0.1、PSI 0.1、KS p 0.05；数据集漂移占比 ≥ 0.5 — [Evidently 源码](https://github.com/evidentlyai/evidently/blob/main/src/evidently/legacy/calculations/stattests/registry.py)
- Chronon 指标：mismatch、missing、extra、SMAPE、编辑距离；按 key 哈希抽样；不给阈值 — [Chronon doc](https://github.com/airbnb/chronon/blob/main/docs/source/test_deploy_serve/Online_Offline_Consistency.md)
- PAI-Rec："一般 ScoreDiff 的值差异在小数点后四位以外，我们就可以认为离在线的打分是一致的"；采样比例可配置，最大 100% — [PAI-Rec 一致性检查](https://help.aliyun.com/zh/airec/what-is-pai-rec/user-guide/consistency-check/)
- 业界对效果影响的公开证据：Google Play 消除“线上缺失、训练存在”的特征 skew 后，安装率提升 2% — [Breck et al. 2019](https://mlsys.org/Conferences/2019/doc/2019/167.pdf)；YouTube 首页改为落特征后 "significant quality improvements" — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)

### Inferences（设计建议；阈值数值均为建议起点，必须用下文的方法校准）
**S 层级一致性检查**：

| 层 | 内容 | 实现 | 起始阈值建议 | 出处与说明 |
|---|---|---|---|---|
| S1 Schema | 名称、类型、取值域、缺失率 | TFDV schema 或等价实现（ML Test Score Data 1、Monitor 2；PAI-Rec 排查的四类问题） | 名称或类型不一致：0 容忍 | 一手 |
| S2 分布 | 训练窗口 vs 线上抽样 | 类别特征：L∞；数值特征：JSD（用 QUANTILES 直方图）或归一化 Wasserstein；计数类：NormalizedAbsoluteDifference | L∞ 0.01 到 0.05（TFDV 示例 0.01；论文“每个值最多变 1%”）；JSD 或 Wasserstein 0.1（Evidently 默认）；0.3 只适合作为宽松上限（BQML 默认） | 数值来自文档示例或工具默认值，**都不是**业界标准 |
| S3 样本级 | 按 request_id + feature 逐值比较 | `DetectFeatureSkew` 或 Chronon 式自建 | 见下方 | Monitor 3、Rule #37 |
| S4 打分级 | 同一请求的离线分与在线分 | PAI-Rec 式特征重放 | \|Δscore\| < 1e-4 的请求占比 | PAI-Rec 一手 |
| S5 效果级 | Rule #37 三段差距 | next-day vs live 效果差 | 显著差距视为工程错误 | Rules of ML |

**S3 的指标定义**（建议替换 5.2 第 6 条）：对每个特征 f，在两侧都有 request_id 的样本上计算：
- `exact_match_rate = match_count / (match + mismatch + base_only + test_only)`，即 TFDV 的口径（diff_count = base_only + test_only + mismatch）；
- `missing_rate`（线上有、离线无）和 `extra_rate`（离线有、线上无），即 Chronon 的口径；
- 数值特征另算 `SMAPE = Σ|a−b|/Σ(a+b)`（Chronon），以及“容差内匹配率”（用 float_round_ndigits 或相对误差 ε 控制）；
- 序列特征算编辑距离分布；
- 另外报告 `ids_missing_in_base` 和 `ids_missing_in_test`，即样本 join 失败的比例，这一项本身就是一致性问题。

**阈值的校准方法**（回应 R7 的“阈值未校准”）：
1. **按特征类别分档**，不用一个全局 99.9%：
   - 确定性的批特征（离线和在线同一份代码、同一份快照）：目标是 exact_match = 100%。任何 mismatch 都按 Monitor 3 和 Rule #37 的口径视为工程错误，需要逐条解释。
   - 实时或流特征：允许由传播延迟造成的 mismatch。先用 P4 的延迟平移估出 lag，按 lag 对齐后再比较，阈值取校准值。
   - 日更特征：重点检查午夜附近的不一致，这是 Chronon 原文指出的集中区间。
2. **噪声底（A/A）校准**：对现有在线特征（视为“已知健康”）跑同样的 S3，取各类特征 mismatch_rate 的 P95 或 P99 作为该类阈值。新特征超过同类 P99 就判定不通过，并输出 TFDV SkewPair 式的样本对，供人工排查。
3. **样本量**：参考 Rule #34 "Ten thousand examples is enough"，以及 Chronon 的按 key 抽样，建议每个特征至少有 1 万个两侧都有 ID 的样本，并且覆盖至少 1 个完整日周期（覆盖午夜）。如果按二项分布要检验 mismatch ≤ 0.1%，1 万样本给出的 95% 置信上界约为观察值 + 0.06%，精度够用（这是推论，基于正态近似）。
4. 如果仍想保留“99.9%”这个形式，应在文档中写明：它是内部设定的“确定性特征的 exact match 下限”，没有外部出处；并说明 PAI-Rec 用的是打分级 1e-4 容差，Google 的口径是“完全一致”。

### Gaps
- 没有找到任何公开的“特征级 match rate 合格线”（例如“≥ 99.9%”“≥ 99%”）。第一轮引用的 PAI-Rec “约 99%”描述的是实时特征回推的准确率，不是合格线。
- Uber、Meta 的一致性阈值仍然缺少公开数值。

---

## 四、泄露检测启发式与阈值校准（回应 3.1 的 L1「疑似泄漏」、R7）

### Takeaway
能找到出处的现成泄露阈值只有两个，都来自 deepchecks：单特征 train PPS ≥ **0.7**，以及 |train PPS − test PPS| ≥ **0.2**。方案 3.1 用的“IV > 0.5 → 疑似泄漏”来自信用评分领域的经验分档，本轮没有找到泄露检测语境下的一手出处，并且 IV 和 PPS 尺度不同，无法直接换算。建议 L1 用多信号组合，并用**合成泄露注入**来校准阈值。

### Cited Findings
- deepchecks：`add_condition_feature_pps_in_train_less_than` 默认 0.7；`add_condition_feature_pps_difference_less_than` 默认 0.2，默认取绝对值，≥ 阈值即 FAIL；正差（train > test）提示标签泄露进了训练集；`n_samples=100_000`、`n_top_features=5` — [deepchecks 源码](https://github.com/deepchecks/deepchecks/blob/main/deepchecks/tabular/checks/train_test_validation/feature_label_correlation_change.py)
- Rules of ML #33：用之后日期的数据测试，效果 "shouldn't be radically worse"，AUC "should be reasonably close" — [Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml)
- ML Test Score Data 2 的单特征价值评估方法：相关系数、单特征或双特征模型、逐个去掉一个特征的 k 个模型 — [ML Test Score](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)
- Data Validation 论文：time travel，即训练时查询到服务之后的数据，本质上就是时间穿越型泄露 — [Breck et al. 2019](https://mlsys.org/Conferences/2019/doc/2019/167.pdf)
- [仍未核] Kaufman et al. 的检测方法原文清单（例如 EDA、"too good to be true"、按时间审计的具体措辞），见第一节。

### Inferences（设计建议）
**L1「疑似泄漏」由多个信号组成，任意一个触发就转人工，并强制跑 P1 和 P2**：

| 信号 | 计算 | 起始阈值 | 出处 |
|---|---|---|---|
| L-a 绝对强度 | 单特征 PPS 或 AUC（以及方案现有的 IV） | PPS ≥ 0.7（deepchecks 默认）；IV、AUC 用下文校准 | deepchecks 一手；IV 无出处 |
| L-b 时间稳定性 | 随机切分与按时间切分（T 训练、T+1 测试，即 Rule #33）的单特征 PPS 之差 | ΔPPS ≥ 0.2（deepchecks 默认）；AUC 差值另行校准 | deepchecks；Rules of ML |
| L-c 可得性 | P1 违规行数、P2 哨兵命中次数 | > 0 即判泄漏（硬门槛） | Feast、Tecton、Azure 的语义 |
| L-d 延迟敏感 | P4 在 Δ = 声明延迟时的 AUC 降幅 | 用下文校准 | 推论 |
| L-e 线上回落 | 影子期 logged 特征的单特征 AUC 与离线回填 AUC 之差 | 用下文校准 | 推论；参考 Monitor 3 |

**校准方法**（推论）：
1. **合成泄露注入**：在真实样本上构造一组已知泄露的特征，例如：
   - label 加噪声，按不同信噪比做出泄露强度梯度；
   - 窗口右端点越过 sample_ts 的聚合（未来 1h、1d）；
   - 用回填修正值替代原值。
   
   同时取一组已上线、已知干净的特征作为对照。对每个信号画 ROC，选阈值使“已知泄露的召回 ≥ 目标（例如 95%）”，同时“干净特征误报 ≤ 目标（例如 5%）”。
2. **按场景分位数**：把历史干净特征的单特征 AUC、IV、PPS 的 P99 作为该场景的告警线，替代全局固定的 IV 0.5。
3. **定期复核**：每季度用新确认的泄露事故（真阳性）和误报（假阳性）更新阈值，并记录在 ADR 中。

**对 5.2 第 5 条“时点正确性（硬）”的落地**：用 P1 和 P2 两个自动化断言实现，二者都要求 0 违规。这对应 ML Test Score 的计分口径：手动执行得 0.5 分，自动化重复执行得 1 分；建议直接做成自动化。

### Gaps
- IV > 0.5 作为“疑似泄漏”线，本轮没有找到一手出处，建议在方案中标注为“经验值，待校准”。
- DataRobot、H2O 等 AutoML 工具的 target leakage 自动检测阈值本轮没有覆盖。
- Kaufman 原文的检测方法清单依然缺失，见第一节。
