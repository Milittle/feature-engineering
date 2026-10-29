# 特征泄露检测、Point-in-Time 正确性与训练/服务偏差（Train-Serve Skew）检测：业界做法调研

> Review issue R7 对应的调研笔记：PIT 正确性和训练/服务一致性缺少测试方法，泄露阈值没有校准。
> 方法说明：本次会话的网络策略不允许直接抓取 tensorflow.org、developers.google.com、docs.feast.dev、arxiv.org、research.google.com 的页面（DNS 被拦截），所以下面的发现大多来自搜索结果摘要，以及官方或二手页面的片段。凡是只靠二手来源的地方都已标出。凭训练知识补充、本次没有核实的内容只写在 Inferences/Gaps 里，并注明“未核实”。

## 1. 泄露检测方法：taxonomy、启发式、对抗验证、工具与事故

### Takeaway
泄露检测在业界没有通用的硬阈值。可落地的做法是组合几类信号：单特征强度（AUC/PPS）偏高、train 与 test 上单特征强度的落差（deepchecks 默认 PPS 差 > 0.2 即告警）、按时间切分后效果明显回落、特征时间戳晚于标签时间。Kaufman et al. 的“learn-predict separation”是治本的思路：把数据按“预测时刻能拿到什么”来管理。这一点也直接说明，L1 上“单特征 AUC 很高 → 疑似泄露”只能作为触发人工或时间审计的信号，不能单独定罪。

### Cited Findings
- Kaufman, Rosset, Perlich, "Leakage in Data Mining: Formulation, Detection, and Avoidance"，KDD 2011，pp. 556–563，DOI 10.1145/2020408.2020496。期刊扩展版发表在 ACM TKDD 6(4), Article 15, Dec 2012，增加了作者 Ori Stitelman，并补充了基于因果图的泄露视角 — [dblp](https://dblp.uni-trier.de/rec/conf/kdd/KaufmanRP11.html); [IUCC CRIS](https://cris.iucc.ac.il/en/publications/leakage-in-data-mining-formulation-detection-and-avoidance-2/)
- 论文对泄露的定义是：模型拿到了关于预测目标、按理不应获得的信息。泄露被称为“top ten data mining mistakes”之一。论文提出两件事：一是用特定的数据管理方式加上“learn-predict separation”来避免泄露；二是在建模者无法控制数据采集时，给出若干事后检测泄露的方法 — [论文 PDF（UMB 课程镜像）](https://www.cs.umb.edu:443/~ding/history/470_670_fall_2011/papers/cs670_Tran_PreferredPaper_LeakingInDataMining.pdf); [IUCC CRIS](https://cris.iucc.ac.il/en/publications/leakage-in-data-mining-formulation-detection-and-avoidance-2/)
- 论文把 INFORMS 2010 Data Mining Challenge 等公开竞赛中的泄露争议作为动机案例 — [IUCC CRIS](https://cris.iucc.ac.il/en/publications/leakage-in-data-mining-formulation-detection-and-avoidance-2/)
- 经典事故：KDD Cup 2008（乳腺癌检测）的冠军方案利用了患者 ID 中带有的预测信息，即一种泄露。见 Rosset et al. "Medical data mining: insights from winning two competitions" — [IBM Research](https://researcher.ibm.com/publications/medical-data-mining-insights-from-winning-two-competitions); [IBM tech report RC24758](https://dominoweb.draco.res.ibm.com/reports/rc24758.pdf)。二手资料称 ID 区间之间的恶性率从约 36% 到约 1% 不等，这个数字未与原文核对 — [howaiworks glossary](https://howaiworks.ai/glossary/data-leakage)
- deepchecks `FeatureLabelCorrelationChange`（旧名 Single Feature Contribution Train-Test）用 Predictive Power Score（PPS）衡量单特征对标签的预测力。文档说明 PPS 接近 1 可能意味着泄露；更强的信号是 train PPS − test PPS 偏大（训练集上比测试集上更能预测标签，提示标签信息泄露进了训练集）。条件 `add_condition_feature_pps_difference_less_than` 的默认阈值是 0.2（0.9 版文档）。另有条件 `add_condition_feature_pps_in_train_less_than`（默认值未查到）。如果反过来 test PPS 明显更大，则可能是测试集漂移带来的偶然相关 — [deepchecks API (0.9)](https://docs.deepchecks.com/0.9/api/generated/deepchecks.tabular.checks.train_test_validation.FeatureLabelCorrelationChange.add_condition_feature_pps_difference_less_than.html); [deepchecks stable guide](https://docs.deepchecks.com/stable/tabular/auto_checks/train_test_validation/plot_feature_label_correlation_change.html); [单表版 FeatureLabelCorrelation](https://docs.deepchecks.com/dev/api/generated/deepchecks.tabular.checks.data_integrity.FeatureLabelCorrelation.html)
- 对抗验证（adversarial validation）：训练一个分类器区分 train 行和 test 行。AUC ≈ 0.5 说明两者可互换；AUC 明显高于 0.5 说明分布不同，此时看特征重要性可以定位是哪些特征造成的。常见原因是只在某一侧出现的取值，或者两侧处理逻辑不一致的特征工程。另一条建议是：对可疑特征做置换（permutation），如果效果骤降，就要核查该特征在预测时刻是否真的可得 — [allaboutdata substack](https://allaboutdata.substack.com/p/adversarial-validation-da-kaggle); [livaage ML resources: data leakage](https://livaage.github.io/ml_resources/topics/data-leakage.html); [adval (PyPI)](https://pypi.org/project/adval)（以上均为二手或社区来源）
- 用 permutation 来定位依赖、并核对“预测时刻可得性”的做法，以及“每个特征都有时间戳、每个 join 都遵守时间戳”的原则 — [livaage ML resources](https://livaage.github.io/ml_resources/topics/data-leakage.html)

### Inferences
- 对我们 L1 的建议是把“疑似泄露”拆成三个可校准的信号：
  1. 绝对强度：单特征 AUC 或 PPS。阈值应按业务场景用历史上已确认的干净特征和泄露特征做分位数校准，例如取历史干净特征单特征 AUC 的 P99 作为告警线。不要拍一个全局 0.9。
  2. 时间稳定性：按时间切分（T 训练、T+1 测试）后单特征 AUC/PPS 的回落幅度。参考 deepchecks，ΔPPS > 0.2 视为可疑。泄露特征通常在随机切分下极强，在按时间切分或线上回放时明显回落。
  3. 来源审计：特征时间戳与标签时间戳的比较（见第 2 节），以及“预测时刻是否可得”的元数据声明。
- 在按时间切分时，对抗验证的 AUC 本来就会高于 0.5，因为时间本身就会造成漂移。所以它更适合定位“哪个特征区分 train 和 test 最强”，不适合用来下泄露结论。这个看法来自上面的检索摘要，属于推理。
- Kaufman 的“learn-predict separation”落到工程上就是：每个样本只能用 cutoff 时刻之前已经物化的数据。这正对应 Feature Store 的 PIT join，以及在线落特征（log-and-wait）。

### Gaps
- 没能拿到 Kaufman 论文全文里检测方法的完整清单（例如“对 hold-out 做探索性分析”“看是否 too good to be true”等的原文表述），因为 arxiv/ACM 页面抓取受限。
- 没找到业界公开的“单特征 AUC > X 即判泄露”的具体数值。这类公开阈值很少，只能自建校准。
- AutoML 工具（如 H2O、DataRobot 的 target leakage 检测）的具体阈值本次未覆盖。训练知识中 DataRobot 有“Target Leakage”自动检测，但本次未核实。

## 2. Point-in-Time（PIT）正确性：Feature Store 实现、log-and-wait、回填陷阱与测试方法

### Takeaway
主流 Feature Store（Feast、Databricks、Chronon/Zipline）的 PIT join 语义一致：对每个 (entity, event_ts)，取 entity 相同、特征时间 ≤ event_ts、且在 TTL/lookback 窗口内的最新值，找不到就返回 null。剩下的主要风险在于“特征时间”是不是真实的“可得时间”。例如 Feast 默认不拿 created_timestamp 与 lookup 时间比较，所以事后的修正或回填可能被取到，造成穿越。最权威的 PIT 测试方法是：拿线上落下来的特征（logged）和离线回填（backfilled）的值对比。Chronon/Zipline 把“Backfilled vs Logged”作为一致性测试项，用 SMAPE、不等率、编辑距离来度量。

### Cited Findings
- **Feast**：默认 PIT join 对每个 entity 行取“相同 entity key、source event timestamp ≤ lookup 时间、且在 FeatureView TTL 内”的最新记录，否则为 null。entity DataFrame 的 `event_timestamp` 是查找时刻，source 的时间字段表示特征发生的时间 — [oneuptime: Feast PIT join nulls (2026, 二手)](https://oneuptime.com/blog/post/2026-08-15-feast-point-in-time-join-nulls/view); [oneuptime: event_timestamp](https://oneuptime.com/blog/post/2026-08-15-feast-event-timestamp-entity-dataframe/view)
- **Feast 的陷阱**：默认不把 `created_timestamp` 与 entity 行的 `event_timestamp` 比较，所以 lookup 时刻之后才创建的修正值或回填值仍可能被返回。建议显式建模“可得时间”（availability time） — [oneuptime (二手)](https://oneuptime.com/blog/post/2026-08-15-feast-event-timestamp-entity-dataframe/view)。旧版源码在排序时把 created timestamp 列也纳入时间列，推测作为同一 event_ts 下的 tie-breaker，未经官方文档确认 — [Feast v0.14 file offline store 源码](https://feast.readthedocs.io/en/v0.14.0/_modules/feast/infra/offline_stores/file.html)
- **Databricks Feature Store**：对每行取 `timestamp_lookup_key` 列时间点之前、主键匹配的最新特征值，不存在则返回 null。官方特别说明这类“time travel”与 Delta Lake time travel 无关。`lookback_window`（实验性）限制回看范围，设为 0 时只返回精确匹配。任何带主键加时间键的 UC Delta 表都可以作为 time series feature table（DBR 13.3 LTS+） — [Databricks docs: Point-in-time feature joins](https://docs.databricks.com/aws/machine-learning/feature-store/time-series); [FeatureLookup API](https://api-docs.databricks.com/python/feature-store/latest/ml_features.feature_lookup.html)
- **Chronon（Airbnb，前身 Zipline）**：README 称回填对大时间窗可扩展、对数据倾斜有韧性，并且是 “point-in-time accurate such that consistency with online serving is guaranteed”。每个特征都按 join 左侧的事件时间戳来计算，窗口聚合不会泄露未来数据 — [GitHub airbnb/chronon](https://github.com/airbnb/chronon); [Airbnb blog: Chronon open source (2024)](https://medium.com/airbnb-engineering/chronon-airbnbs-ml-feature-platform-is-now-open-source-d9c4dba859e8); [Airbnb blog: Chronon declarative framework (2023)](https://medium.com/airbnb-engineering/chronon-a-declarative-feature-engineering-framework-b7b8ce796e04)
- **Airbnb 对 log-and-wait 的评价**：log-and-wait 几乎“免费”保证了一致性，代价是新特征要等很久才能积累到足够的训练数据。Chronon 的思路是“定义一次，同时用于训练回填和在线服务” — [Airbnb blog (2023)](https://medium.com/airbnb-engineering/chronon-a-declarative-feature-engineering-framework-b7b8ce796e04)
- **Zipline 的一致性测试（Databricks 2022 分享幻灯片）**：把 “online offline consistency” 作为数据统计项。数值特征用 **SMAPE**，类别特征用**不等率（inequality %）**，列表特征用**编辑距离**。测试用例包括 “**Backfilled / Logged**” 和 “**PITC / Midnight accurate**”（点时正确与按天午夜快照的对比） — [Introducing Zipline (Databricks 2022 PDF)](https://microsites.databricks.com/sites/default/files/2022-07/Introducing-Zipline_An-Open-Source-Feature-Engineering-Platform.pdf); [Chronon Feature Store Summit 2024 slides](https://content.hopsworks.ai/hubfs/Feature%20Store%20Summit%202024/FS%20Summit%2024%20-%20Airbnb%20-%20Chronon.pdf)
- **Google Rules of ML，Rule #29**：保证训练与服务一致的最好办法，是把服务时用到的特征存下来，再用于训练。如果不能全量落日志，就抽样落一小部分，用来验证训练与服务的一致性。**Rule #31**：如果训练和服务时都去 join 一张表，这张表的数据可能在两次 join 之间变了，同一文档会得到不同预测，最容易的规避办法就是在服务时落特征 — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml/); [繁中译本：Training-Serving Skew 章节](https://leafwind.gitbooks.io/rules-of-machine-learning-traditional-chinese/content/ml-phase2-training-serving-skew.html)
- **Uber（Eats 推荐）feature logging**：在推理时落下模型实际使用的特征值作为训练来源，并在 Flink 中把曝光事件与 Kafka 里先前落下的预测特征 join，得到完整的推理记录。这样免去了昂贵的离线 join，也减少了 skew。推荐流量达 8M QPS，因此用 feature allow list 只落模型实际用到的特征 — [Uber blog: Taming the ML firehose](https://www.uber.com/blog/taming-ml-firehose/)
- **Meta/Facebook 广告 CTR（ADKDD 2014）**：Online Joiner 对曝光流和点击流做分布式流-流 join（HashQueue = FIFO 缓冲窗口 + hash map）。曝光在一个较长的等待窗口内没有点击才标为负例。窗口太短会误标，太长会拖慢实时训练数据 — [论文 PDF (typeset)](https://typeset.io/pdf/practical-lessons-from-predicting-clicks-on-ads-at-facebook-3v0cxs9foz.pdf); [summary](https://shagunsodhani.github.io/papers-I-read/Practical-Lessons-from-Predicting-Clicks-on-Ads-at-Facebook)。中文二手解读提到：joiner 故障会让样本全部变成负例，因此增加了样本流异常检测，异常时暂停在线学习 — [CSDN 解读](https://blog.youkuaiyun.com/u014033218/article/details/88382317)
- **字节 Monolith（2022, arXiv:2209.07663）**：用户行为和请求时的特征分别进入 Kafka 队列，Flink joiner 按 request key 匹配，迟到的行为可以回查磁盘 KV。join 后的样本同时供在线训练和落盘批训练，负采样在 joiner 内完成，服务时做 log-odds 校正（来自二手摘要） — [kingy.ai summary](https://kingy.ai/news/monolith-real-time-recommendation-system-withcollisionless-embedding-table-paper-summary/); [gilunga notes](https://gilunga.github.io/Papers/Real-time-Recommendations-at-ByteDance)
- **阿里 PAI-Rec 对实时特征的三层处理**：(1) 离线模拟回推历史请求时刻的实时特征；(2) FeatureStore 记录实时特征的增量更新并据此导出样本，官方估计准确率约 99%；(3) 通过 callback 接口记录请求时刻的特征（即落特征） — [阿里云开发者社区 1656547](https://developer.aliyun.com/article/1656547)
- **B站推荐数据流**：分析了推理特征与训练特征版本不一致的原因，包括实时特征的访问时间差、新稿件在离线侧缺失、批量特征版本更新导致的**特征穿越**，以及计算逻辑不一致 — [掘金：B站推荐模型数据流的一致性架构](https://juejin.cn/post/7452892770288025609)

### Inferences
- 可以直接采用的 **PIT 正确性测试方法**（R7 可落地项）：
  1. **Logged vs Backfilled 对比**（Zipline/Chronon 做法）：对线上抽样落下来的 (request_id, entity, ts, feature 值)，用离线 PIT join 逻辑在同一 ts 重新回填，逐特征计算一致率。数值特征用 SMAPE 或 |diff| ≤ ε 的比例，类别特征用不等率，序列特征用编辑距离或 Jaccard。
  2. **时间戳不变式断言**：对训练样本表，断言每个特征 `feature_available_ts ≤ sample_event_ts`，其中可得时间必须取 max(event_ts, created/ingest_ts)，不能只看 event_ts（避免 Feast 式 created_timestamp 漏洞）。
  3. **Midnight vs PIT 对照**（Zipline 测试项）：同一特征分别按“当天午夜快照”和“精确 PIT”计算，差异大说明日更特征被当作实时用，存在穿越或滞后。
  4. **“未来扰动”测试**：人为修改 event_ts 之后的源数据，重跑 PIT join。如果训练样本的特征值随之改变，说明发生了穿越。这是推理出的测试设计，不是某家公开的做法。
- Uber 的 allow list、Rule #29 的“抽样落日志”说明，小比例抽样（例如 1% 请求）就足以支撑一致性校验，不必全量落特征。

### Gaps
- Tecton 和 Hopsworks 的 PIT 实现细节（Tecton 的 `get_historical_features` / spine 语义，Hopsworks 的 as-of join）没有检索到一手文档。
- Feast 官方文档对 TTL 与 created_timestamp 语义的原文未能抓取，只有 2026 年的二手博客，需对照官方核实。
- 没有找到 LinkedIn（Feathr）和 Pinterest 关于 feature logging 的一手文章。Meta 除 2014 年论文外，近年的 feature logging 资料也没找到。
- Chronon 一致性度量的具体实现（采样率、阈值）没有公开数值，只有指标名称。

## 3. Training-Serving Skew 检测：TFDV、Rules of ML、ML Test Score、Evidently、业界线上 vs 离线对比

### Takeaway
skew 检测分两层。**分布层**比较训练集与服务数据的统计分布：TFDV 的 skew_comparator 对类别特征用 L∞、对数值特征用 JS 散度；BigQuery ML 封装的默认阈值是 0.3；Evidently 默认 Wasserstein 或 JS，阈值 0.1。**样本层**按 request_id 把线上落下的特征与离线重算的特征 join，逐值比对，算 match rate 和 diff rate。后者更精确，是推荐和广告业界（Uber、Hulu、阿里 PAI-Rec、Airbnb）普遍采用的方式，但公开的“合格线”数值很少。

### Cited Findings
- **TFDV 的 FeatureComparator** 有 `infinity_norm`、`jensen_shannon_divergence`、`normalized_abs_difference` 三种阈值字段，用于 skew_comparator / drift_comparator — [TFMD FeatureComparator API](https://www.tensorflow.org/tfx/tf_metadata/api_docs/python/tfmd/proto/schema_pb2/FeatureComparator); [DriftSkewInfo.Measurement](https://tensorflow.google.cn/tfx/tf_metadata/api_docs/python/tfmd/proto/anomalies_pb2/DriftSkewInfo/Measurement)
- **BigQuery ML `ML.TFDV_VALIDATE`**（TFDV 的托管封装）：阈值在 [0,1) 之间，类别和数值特征的默认阈值都是 **0.3**。类别特征默认用 **L_INFTY**，可选 JENSEN_SHANNON_DIVERGENCE；数值特征只支持 JS 散度 — [BigQuery ML.TFDV_VALIDATE docs](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-tfdv-validate?authuser=1)
- TFDV 没有官方推荐的 skew 阈值。课程或社区的建议是：阈值按特征重要性迭代设定，重要特征设得严、次要特征设得宽，并结合可接受的模型效果波动来定（社区意见，非官方） — [DeepLearning.AI 社区帖](https://community.deeplearning.ai/t/how-to-properly-set-jensen-shannon-divergence-infinity-norm-to-leverage-tfdv-drift-skew-check-features/118566)
- **Evidently 默认值**：数值列且样本 > 1000 时默认用 Wasserstein（归一化），阈值 0.1；类别列且样本 > 1000 时默认用 JS，阈值 0.1；PSI 可选，默认阈值 0.1（文档示例中把类别列设为 0.3）。样本 ≤ 1000 时，数值列用 K-S（p < 0.05），类别列用卡方或 z 检验。数据集层面，漂移列占比 ≥ 0.5 即判定数据集漂移 — [Evidently: Customize Data Drift](https://docs.evidentlyai.com/metrics/customize_data_drift); [Evidently 旧文档：drift 参数](https://docs-old.evidentlyai.com/user-guide/customization/options-for-statistical-tests)
- **Google Rules of ML** 中与 skew 相关的规则：#29 服务时落特征用于训练（全量做不到就抽样，用于验证一致性）；#31 训练和服务都 join 的表可能在两次 join 之间变化 — [Google Rules of ML](https://developers.google.com/machine-learning/guides/rules-of-ml/); [繁中译本 skew 章节](https://leafwind.gitbooks.io/rules-of-machine-learning-traditional-chinese/content/ml-phase2-training-serving-skew.html)
- **ML Test Score**（Breck, Cai, Nielsen, Salib, Sculley；Google，IEEE Big Data 2017）：共 28 项测试，分为 Data、Model、ML Infrastructure、Monitoring 四组 — [论文 PDF](https://research.google.com/pubs/archive/aad9f93b86b7addfea4c419b9100c6cdd26cacea.pdf)。二手资料提到 Monitoring 组含 “Training and serving are not skewed” 一项；手动执行得 0.5 分，自动化重复执行得 1 分；分数解读为 < 7 危险、14–21 合理、> 21 领先（均为二手，未与原文核对） — [nhuantdbk 博客](https://nhuantdbk.github.io/ml-test-score-part-one); [CMU MLiP 课件](https://mlip-cmu.github.io/s2024/slides/12_pipelinequality/pipelinequality.pdf)
- **Uber**：以推理时落下的特征作为训练来源，从根上消除 skew（见第 2 节） — [Uber blog](https://www.uber.com/blog/taming-ml-firehose/)
- **Hulu server-side feature logging**：线上特征写入数仓，与离线抽取的特征比对来计算漂移指标，再与标签合并成训练集。用动态 map 存特征，新增特征无需改 schema（二手来源） — [besthub: Hulu feature logging](https://besthub.dev/articles/how-hulu-eliminated-feature-drift-with-server-side-feature-logging-62a6752b9ca4)
- **阿里 PAI-Rec 一致性检查**：控制台里的“故障排查工具 > 一致性检查”可以创建特征一致性检查任务。引擎把服务时的特征日志写入 MaxCompute，与离线样本特征自动比对，排查特征名、类型、缺失、取值逻辑等不一致 — [阿里云 PAI-Rec 一致性检查文档](https://help.aliyun.com/zh/airec/what-is-pai-rec/user-guide/consistency-check/); [英文版](https://www.alibabacloud.com/help/en/airec/what-is-pai-rec/user-guide/consistency-check)
- **阿里的不一致成因**：离线拼样本时用的特征版本与线上请求时的版本不同（流水线延迟，流程越长越严重）；实时特征从埋点上报到流计算完成存在时间差 — [阿里云开发者社区 1739872](https://developer.aliyun.com/article/1739872)
- **预防手段：同一份代码**。PAI-Rec 的 FG（Feature Generation）对离线和在线的变换做统一定义；EasyRec 的 RTP FG 离线和在线使用同一份 C++ 代码生成 match/lookup 等交叉特征，以保证一致 — [PAI-Rec FG 文档](https://www.alibabacloud.com/help/tc/airec/what-is-pai-rec/user-guide/feature-generation-overview-and-configuration); [EasyRec RTP FG](https://easyrec.readthedocs.io/en/latest/feature/rtp_fg.html)
- **Drifter（2023, arXiv:2309.08617）**：面向大规模推荐系统的在线特征监控与校验系统，实时监控特征分数、基数（cardinality）、覆盖率等指标，用于 CTR/CVR 场景 — [ar5iv: Drifter](https://ar5iv.labs.arxiv.org/html/2309.08617)
- **Zipline/Chronon 一致性指标**：数值特征用 SMAPE，类别特征用不等率，列表特征用编辑距离（见第 2 节） — [Introducing Zipline PDF](https://microsites.databricks.com/sites/default/files/2022-07/Introducing-Zipline_An-Open-Source-Feature-Engineering-Platform.pdf)

### Inferences
- 建议我们的预评估系统给每个候选特征加一个“**一致性门禁**”，分三档：
  1. **Schema 层**：名称、类型、缺失率、取值域一致。可用 TFDV schema 或 Great Expectations 的 expectation 实现。
  2. **分布层**：训练窗口 vs 线上抽样的分布比较。类别特征用 L∞，数值特征用 JS 或 Wasserstein。起始阈值可参考 BQML 的 0.3（宽松）和 Evidently 的 0.1（严格），再用历史上“无事故的上线特征”的分布差异分位数来校准。
  3. **样本层**（最关键）：按 request_id + feature 逐值比对，输出 match rate（完全一致率）、value diff rate、missing mismatch rate（单边缺失）、数值 SMAPE。PAI-Rec 的“约 99% 准确率”可以作为业界量级参考，但它描述的是回推实时特征的准确率，不是官方的合格线。
- 预防优于检测：落特征（Rule #29、Uber、Hulu、PAI-Rec callback）加上同一份特征代码（FG/RTP FG、Chronon 一次定义）。检测主要用于给回填特征（尚无线上日志的新特征）做上线前验收。
- 训练知识补充（未核实）：TFDV 还提供基于样本 ID 的 feature-level skew 检测（`tfdv.detect_feature_skew`，输出 match/mismatch/base_only/test_only 等计数），可以直接实现“样本层”比对。需要对照官方文档确认。

### Gaps
- TFDV 官方 get_started 页面（tensorflow.org）在本会话被网络策略拦截，没能获取 skew/drift 的原文示例和阈值写法。
- Great Expectations 没有专门检索。业界公开的“match rate ≥ X% 才可上线”这类具体数值几乎找不到。
- ML Test Score 中 skew 测试的原文条目编号和措辞（如 Monitor 3）因 PDF 抓取受限未能核实。

## 4. 中国业界实践（特征一致性校验、线上线下一致性、特征穿越检测）

### Takeaway
公开资料里阿里（PAI-Rec/EasyRec）的产品化最完整：落特征日志到 MaxCompute 加一致性检查任务、FG 统一离线和在线代码、实时特征三层回推。B站有关于“特征穿越”成因的专门分析。美团、字节、快手在本次检索中没有找到可引用的、专门讲“特征一致性校验”或“特征穿越检测”的一手技术博客。字节的公开材料主要是 Monolith 的 joiner 架构（请求时特征与行为按 request key 在线拼接），这本身就是一种以落特征为基础的防穿越设计。

### Cited Findings
- 阿里 PAI-Rec：一致性检查功能（服务特征日志 → MaxCompute → 与样本比对）；实时特征三层处理（离线回推、FeatureStore 增量记录，准确率约 99%、callback 记录请求时特征） — [一致性检查文档](https://help.aliyun.com/zh/airec/what-is-pai-rec/user-guide/consistency-check/); [开发者社区 1656547](https://developer.aliyun.com/article/1656547)
- 阿里关于不一致成因（特征版本与流水线延迟）以及打分与样本特征一致性检测工具 — [开发者社区 1739872](https://developer.aliyun.com/article/1739872)
- 阿里 EasyRec RTP FG：离线和在线使用同一份 C++ 代码 — [EasyRec docs](https://easyrec.readthedocs.io/en/latest/feature/rtp_fg.html)
- B站：批量特征版本更新导致特征穿越，实时特征存在访问时间差，新稿件离线缺失，计算不一致 — [掘金 B站文章](https://juejin.cn/post/7452892770288025609)
- 字节 Monolith：Kafka + Flink joiner 按 request key 拼接请求时特征与用户行为，迟到行为回查 KV（二手摘要） — [kingy.ai](https://kingy.ai/news/monolith-real-time-recommendation-system-withcollisionless-embedding-table-paper-summary/)
- 美团：本次只找到 BCP（业务正确性校验平台，事件触发核对规则，规则数 > 3000），它针对业务数据而非特征 — [美团 BCP 分享 PDF（转载）](https://wfuing.github.io/25/%E5%8E%82/bilibili/%E4%B8%80%E9%9D%A28.1/%e7%be%8e%e5%9b%a2%e4%b8%9a%e5%8a%a1%e6%ad%a3%e7%a1%ae%e6%80%a7%e6%a0%a1%e9%aa%8c%e5%b9%b3%e5%8f%b0%20BCP%e7%9a%84%e8%ae%be%e8%ae%a1%e4%b8%8e%e5%ae%9e%e8%b7%b5%e3%80%90tool.lu%e3%80%91.pdf)

### Inferences
- 国内推荐和广告的通行范式是 “**特征 dump（落特征）+ 实时样本拼接（以 request_id 为键）**”，用来规避特征穿越，再对回填或新特征做“dump 值 vs 离线重算值”的 diff 校验。这与 Uber、Hulu、Rules of ML #29 是同一思路。
- 对我们来说，“特征穿越检测”可以定义为两类断言：(a) 时间断言（特征可得时间 ≤ 样本时间）；(b) dump 对照断言（新特征离线回填值与上线后 dump 值的 diff rate 在阈值内）。新特征在上线前没有 dump 值时，可以先用影子流量（shadow）落几天日志再对比。

### Gaps
- 美团技术团队、字节、快手关于“特征一致性校验”“特征穿越”的一手博客本次没有检索到（中文搜索引擎覆盖较弱；tech.meituan.com、知乎、InfoQ 也未能抓取）。建议后续定向检索 tech.meituan.com 上的“特征平台/实时特征”文章、快手和字节在 InfoQ/DataFun 的分享。
- 国内公开的一致率合格线（例如“diff 率 < 0.1%”）没有找到可引用的来源。
