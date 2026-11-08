# 业界新特征离线 gate、离线-在线一致性、评估器回测：第二轮核验与深化

> 范围：逐条核验第一轮笔记 `research_notes/特征前置评估业界调研/01_industry_feature_onboarding_and_offline_online.md` 中标为 [摘要级]/[未核]/[训练知识] 的条目，并补充可直接落到设计里的细节，服务于《总体方案设计》的 R1（评估器没有用真值验证过）和 R13（准入阈值没有业务含义）。
> 方法：arXiv 全文 PDF 用 curl 下载，再用 pdftotext 抽文本后逐字检索（本轮 arxiv.org 可以访问）。Amazon Science 与 Google Research 的 PDF 同样拿到全文。仍然访问不到的站点：medium.com（403），以及 web.archive.org、enggist.vercel.app、sysdesign-wiki.pages.dev、blog.acolyer.org、www.uber.com（会话网络白名单之外，DNS 解析不了）。semanticscholar API 返回 429。
> 标注：**[已核原文 + 位置]** 表示逐字核对过；**[更正]** 表示原说法有误或不精确，已改正；**[仍未核 + 原因]** 表示仍未核对。日期：2026-10-29。

---

## Q1. 第一轮标记条目逐条核验

### Takeaway
本轮核验了 15 条以上的说法，大多数数字准确，但有几处需要更正：
- 2609.25408 是 Meta 关于**对话式 AI** 评估器的论文，与特征无关。"25.7 点"是在另一个 157-contrast 的共享切片上测得的。
- SIDE 的 0.0085%/0.0108% 是**同一特征两种编码**（SID 与 k-means）的 click NE 增益，不能当作"每个特征 0.0085–0.0108%"的区间。
- "Meta 数千特征"在 Meta 的 arXiv 论文 2605.00324 里有一手出处。
- "Meta 0.1% NE 显著"找不到出处。Meta 论文里实际写的门槛是 **0.02%–0.05% NE**。"0.1% 显著"有出处的是 Google（2022）的 PerQueryAUC。
- Pinterest L1 的"只有一两个实验臂在线上赢"仍然无法核对（medium 403）。

### Cited Findings

**回测类论文**

- **arXiv 2609.25408（Li, Nath, Amirkhani, Li, Deng；Meta Platforms，2026-09）** [已核原文：摘要、§1 贡献列表、§3 评估方法、§4.1–4.2]
  - **[更正]** 被评估对象是对话式助手（多轮 assistant）的离线 engagement proxy，候选变更"spanning model checkpoints to system-prompt tuning"，与推荐/广告特征无关。
  - 全量规模："489 paired offline–online contrasts ... from 27 experiments"。主检验原文为 "Our primary test uses the 113 contrasts from eight experiments that ran after the map was frozen: on these the composite reaches 81.1% F1, against 34.3% for the raw classifier score ... and makes no wrong-direction calls where that raw score makes 31"（摘要）。
  - **[更正]** "高 25.7 点"的原文是 "It exceeds the strongest of five other deployed offline evaluators by 25.7 F1 points"。比较发生在 "a shared slice of 157 pairwise contrasts across seven experiments"（§4.3 / Fig 面板 b），不是 113 个对比那个集合。
  - 81.1% 是 contrast-micro F1；同一集合的 experiment-macro F1 为 63.0%（raw 为 16.0%）（§4.2）。
  - "近显著给部分分"属实：§3 定义了 power-aware precision，用 s_i = clip[0,1](U_on/(U_on−L_on)) 给部分分，错向判断记 0 分。
  - 链接：[arXiv 2609.25408](https://arxiv.org/pdf/2609.25408)
- **arXiv 2604.09549（ContextSim, Bougie et al., Woven by Toyota, 2026）** [已核原文 §4.5]
  - 原文："a proprietary dataset of 55 historical A/B experiments on a large-scale food recommendation platform, each involving thousands of user sessions and hundreds of thousands of recommended item impressions"。主指标为 "average number of visited pages"。
  - 方法："initialize the agent only with information available before the test period ... compute the Spearman correlation between simulated and real-world outcomes across the 55 tests"。
  - **[更正/补充]** 正文**没有给出 Spearman 的具体数值**，只有 Fig 2 的图和 "improvements over all baselines are significant (p < 0.05)"。
  - 这是 LLM 用户模拟器的论文，不是特征评估器。链接：[arXiv 2604.09549](https://arxiv.org/pdf/2604.09549)
- **arXiv 2608.02345（Hut & Masoero, Amazon, COLM 2026）** [已核原文：摘要、§结果、Table 3]
  - 原文："Validated on 67 historical marketing A/B tests ... agreeing with the historical sign for roughly 70% of tests (sign accuracy 0.70, sign overlap 0.70); but measured against simple uninformed baselines and the sign-replication ceiling of the A/B tests, this agreement is not clear evidence of directional signal on this noisy set"。
  - **[补充，对设计很关键]** 原文："the sign-replication rate—the probability that two independent repetitions of the same experiment agree in sign, which is 0.69 here ... uninformed rules already reach 0.50 (a coin flip) and 0.57 (always predict positive)"。也就是说，0.70 已经落在噪声上限附近，**不能据此说明有信号**。
  - 其它数字：MAE 0.0893，launch alignment 0.41（随机底线 0.33），SE(sign acc)=0.06。
  - 链接：[arXiv 2608.02345](https://arxiv.org/pdf/2608.02345)
- **Jeunen, Potapov, Ustimenko 2023（arXiv 2307.15053，KDD'24，ShareChat）** [已核原文 §6.1–6.2]
  - 设定：单个线上实验，"over 40 million users"，为期一周。RQ1–3 用逐日 Pearson 相关。
  - RQ4 定义了三档对齐，原文："(1) ... sign agreement (2) For statistically significant improvements (as validated by the online experiment with p ≪ 0.001), does the offline metric show statistically significant improvements with p < 0.01? (i.e. True-Positive-Rate, recall or sensitivity). (3) ... the p-values"。
  - 样本量原文："5 days ... and 4 different reward signals, yielding 20 distinct statistically significant online metric improvements"。离线显著的判定是 "99% confidence interval for the metric difference is strictly positive"。
  - 结论原文："all offline estimators exhibit 100% directional sign agreement"。
  - **[更正]** 第一轮笔记写"一个个性化实验上各估计器 100% 方向一致"方向正确，但要补充：这 20 个正例都来自**同一个**实验，所以只衡量了 recall/TPR，没有负例，不能计算 precision。
  - 链接：[arXiv 2307.15053](https://arxiv.org/pdf/2307.15053)
- **Amazon Science：Wang, Gao, Jain, Edge, Ahuja，"How Well do Offline Metrics Predict Online Performance of Product Ranking Models?"（SIGIR'23）** [已核原文：摘要、§3.1、Table 1]
  - 金标数据原文："online performance of 114 ranker pairs through Balanced interleaving ... under a business metric called Purchased Units"，共 36 个离线指标。
  - 一致率定义原文："α = C/N ... we assume that agreement results follow a Binomial distribution ... we adopt Wilson score interval"。另外注明 Kruskal γ = 2α − 1。
  - 结果原文："they agree on which one of two ranking models is better up to 97% of times"。
  - Table 1：最好的 NDCG 变体在全部 114 对上 α=0.939 [0.879, 0.970]，在 101 个线上显著对上 α=0.970 [0.916, 0.990]。较差的指标（EU prob 类）只有约 0.62–0.78。
  - 原文另说明 "the same method can also be applied to A/B testing results"。
  - 链接：[Amazon Science PDF](https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf)

**离线-在线差距**

- **DoorDash（arXiv 2502.10514）** [已核原文 §8、§8.1 Table 3、§8.3]
  - 原文："We observed a relative 4.3% discrepancy between online and offline AUC during Milestone 3 ... First, the training data was three months old by the time the experiment was rolled out online. Second, Milestone 3 incorporated a substantial number of new features that lacked corresponding online logging ... Our final solution reduced the online-offline AUC gap to 0.76%"。
  - Table 3 的诊断设计：同一实验期（9 月）里，新模型在**线上日志特征**上为 −1.80%，在**离线 join 特征**上为 +2.45%，差 4.25%，正好对上线上线下差距。离线 join 数据在 9 月与 6 月分别为 +2.45% 和 +2.50%，相近，排除了分布漂移。
  - 根因是 Feature Staleness（特征管道延迟 1–2 天）和 Cached Residuals（线上 KV 只覆盖不淘汰）。
  - 解法：按每个特征选 join offset（−2d/−3d/−4d）对齐线上延迟，并对关键特征开启线上日志。
  - **[补充]** §7.2 的 hybrid 做法：新特征先用 backfill（offline join）训练，原因是 "the need to collect warm-up data for newly engineered features" 拖慢迭代。
  - 链接：[arXiv 2502.10514](https://arxiv.org/pdf/2502.10514)
- **Pinterest L1 转化模型（"Bridging the Gap"博客）** [仍未核：medium.com 403，archive.org 与镜像站都在白名单外]
  - 检索摘要显示：离线 LogMAE 下降约 20–45%，线上 "neutral or slightly worse CPA for key oCPM segments"。根因是 L1 embedding serving 路径的 feature coverage 缺口和 two-tower embedding version skew。
  - "only one or two arms delivered clear online wins"这句原话在摘要里搜不到，**降级为"未核"**。
  - 链接：[Pinterest medium 原文](https://medium.com/pinterest-engineering/bridging-the-gap-diagnosing-online-offline-discrepancy-in-pinterests-l1-conversion-models-1320faaaeefe)；[daily.dev 摘要](https://daily.dev/posts/bridging-the-gap-diagnosing-online-offline-discrepancy-in-pinterest-s-l1-conversion-models-ja30a39p5)
- **Pinterest Related Pins（arXiv 1702.07969）** [已核原文 §5.4]
  - 原文："we examined the results for several of our past ranking model changes. We examined the directionality as well as the magnitude ... PR AUC metrics are extremely predictive of closeups and clickthroughs in A/B experiments, but we had difficulty predicting the save behavior ... For now, we use offline metrics as a sanity check and rough estimation of potential impact"。
  - 这也是一个"用历史实验回测离线指标"的早期一手例子，但没有给出数字。链接：[arXiv 1702.07969](https://arxiv.org/pdf/1702.07969)
- **Airbnb（arXiv 1810.09591）** [已核原文]
  - 原文："an improvement of ∼1% in offline NDCG. But we failed to get any statistically significant improvement in online performance"（特征噪声增强一节）。
  - 原文："When tested online, the model increased long views by a large margin. But bookings remained neutral"。
  - 原文："The gains in online bookings eventually saturated with long spells of neutral experiments"。
  - 链接：[arXiv 1810.09591](https://arxiv.org/pdf/1810.09591)

**Meta**

- **SIDE（arXiv 2506.16698）** [已核原文 §6.2 Table 3 及公式]
  - **[更正]** Table 3 比较的是同一个 DPCA 编码 ad 内容特征的两种接入方式：k-means 特征的 Click NE gain 为 0.0108%、Conversion 为 0.0037%，cost ×1；SID 特征的 Click 为 0.0085%、Conversion 为 0.0101%，cost ×0.23，RoI ×5.57。Baseline 是 "a large-scale production ads-ranking model without the specific ad-features"。
  - 特征 RoI 公式原文："(NE_click + NE_conv) / (2C) to compute the overall RoI of the feature, where C is the logging cost of onboarding the feature"。成本以 kW 计（k-means 46.54kW，SID 10.84kW）。
  - **[更正]** SIDE 论文**没有**"thousands of features"这句话。
  - 链接：[arXiv 2506.16698](https://arxiv.org/pdf/2506.16698)
- **"Meta 数千特征"** [已核原文：一手出处找到]
  - Meta 论文 IEFF（arXiv 2605.00324, 2026）摘要与引言原文："Large-scale ranking systems depend on thousands of features"。该文还说明控制面 "track key system metrics, such as normalized entropy (NE) and online performance, and to revert rollouts"。
  - 链接：[arXiv 2605.00324](https://arxiv.org/pdf/2605.00324)
  - 第一轮引用的 Meta Analytics medium 帖子仍未核（403）。
- **Facebook 2014（He et al., "Practical Lessons from Predicting Clicks on Ads at Facebook"）** [已核原文 PDF]
  - NE 定义："equivalent to the average log loss per impression divided by what the average log loss per impression would be if a model predicted the background CTR"。
  - 原文："Tree feature transformations help decrease Normalized Entropy by more than 3.4% ... This is a very significant relative improvement. **For reference, a typical feature engineering experiment will shave off a couple of tens of a percent of relative NE**"（即一次典型特征实验约 0.2% 量级的相对 NE）。
  - Boosting Feature Importance 定义："summing the total reduction for a specific feature across all trees"。原文还给出 "the top 10 features are responsible for about half of the total feature importance, while the last 300 features contribute less than 1%"，以及 "The last 1,000 trees decrease NE by less than 0.1%"。
  - 链接：[PDF（作者主页镜像）](https://quinonero.net/Publications/predicting-clicks-facebook.pdf)
- **"Meta 0.1% NE 显著"** [更正：未找到；Meta 论文实际写的门槛更小]
  - External Large Foundation Model（arXiv 2502.17494，Meta）："an NE gain of 0.02% is considered significant for experiments on internal datasets"。
  - LLaTTE（arXiv 2601.20083）："a reduction in NE of 0.02% is considered statistically significant and sufficient to yield measurable revenue impact"。
  - SlimPer（arXiv 2607.12281，Instagram）："An NE improvement of approximately 0.03% is considered empirically significant"，并称 NE 是 "a standard offline metric that exhibits directional alignment with A/B test results"。
  - arXiv 2301.10443（ACTR2）："even a 0.05% difference in NE is considered significant for large-scale online advertising models"。
  - Wukong（arXiv 2403.02545，Meta）："A 0.02% Relative LogLoss improvement is considered as significant"（公开数据集）。
  - 链接：[2502.17494](https://arxiv.org/pdf/2502.17494)；[2601.20083](https://arxiv.org/pdf/2601.20083)；[2607.12281](https://arxiv.org/pdf/2607.12281)；[2301.10443](https://arxiv.org/pdf/2301.10443)；[2403.02545](https://arxiv.org/pdf/2403.02545)

**Google**

- **"Ad Click Prediction: a View from the Trenches"（KDD 2013）** [已核原文 PDF]
  - progressive validation 原文："We generally use progressive validation (sometimes called online loss) rather than cross-validation ... small improvements can have meaningful impact at scale and need large amounts of data to be observed with high confidence"。
  - 相对指标原文："We therefore always look at relative changes, usually expressed as a percent change in the metric relative to a baseline model ... only to compare metrics computed from exactly the same data"。
  - 显著门槛原文："in our setting **AucLoss reductions of 1% are considered large**"（AucLoss = 1−AUC）。
  - **[更正]** 原文没有"0.1% AUC/LogLoss 有实际意义"这句话。
  - 特征管理原文："a metadata index for managing consumption of thousands of input signals by hundreds of active models ... New signals can be vetted by automatic testing and whitelisted for inclusion"。
  - 链接：[research.google PDF](https://research.google.com/pubs/archive/41159.pdf)
- **Google "On the Factory Floor"（arXiv 2209.05310）** [已核原文]
  - 原文："Accuracy improvements above 0.1% are considered significant"（指标为 PerQueryAuc）；作为对照，"a naive scaling of the deep network by 2x yields a PerQueryAUC improvement of 0.13%"。
  - 评估方式同样是 progressive validation。评估新技术时取两个点："1) what is the improvement in accuracy when training cost is neutral and 2) what is the training cost improvement if model capacity is lowered until accuracy is neutral"。
  - 链接：[arXiv 2209.05310](https://arxiv.org/pdf/2209.05310)

**其它**

- **JD "+1‰ AUC ≈ $6M"** [已核原文：CSCNN, arXiv 2006.10337, KDD 2020, §4.3 与 §4.4]
  - 原文："In JD.com, every 1‰ increase in off-line AUC brings 6 million dollars lift in the overall advertising income"。另一处："1‰ increase in off-line AUC is significant and brings 6 million dollars lift"。
  - **注意：原文没有写时间单位**（年/季度）。
  - 同文的线上实验：离线 AUC +0.0086（0.7527 vs DCN），一周 A/B CTR +3.22%、eCPM +2.46%、CPC −0.62%。
  - 链接：[arXiv 2006.10337](https://arxiv.org/pdf/2006.10337)
- **Etsy（arXiv 1711.01377）** [已核原文 §4.1]
  - 原文："we not only wanted to seek a sign-correlation (e.g., an offline win indicates an online win or an offline lose implies an online lose) but also wanted to have the right magnitude (e.g., single digit AUC win indicates single digit CTR win for A/B tests) ... through multiple such studies, we have established ... AUC as a reliable indicator"。
  - 原文："Improvements in AUC (> 1%) have consistently resulted in significant CTR wins in multiple rounds of online A/B tests"。
  - 没有给出实验数量或相关系数。链接：[arXiv 1711.01377](https://arxiv.org/pdf/1711.01377)
- **"千分之一 AUC"规则** [已核原文，中外论文均有]
  - DCN（Google, arXiv 1708.05123）："an improvement of 0.001 in logloss is considered as practically significant"（Criteo 数据集）。
  - FuxiCTR / Open Benchmarking（华为, arXiv 2009.05794）："existing studies from Google and Microsoft reveal that an absolute improvement of 1‰ in logloss (or AUC) is considered as practically significant"，以及 "an improvement of AUC at 0.001 level is generally considered as practically significant for an industrial CTR prediction task"。
  - **注意：这是绝对值 0.001**，与 Meta/Google 的"相对 %"口径不同。
  - 链接：[arXiv 1708.05123](https://arxiv.org/pdf/1708.05123)；[arXiv 2009.05794](https://arxiv.org/pdf/2009.05794)

### Inferences
- 第一轮里的数字基本没错，但**场景标注**有偏差：2609.25408、2604.09549、2608.02345 都不是特征评估器。它们能为 R1 提供**回测协议**，不能提供"特征 gate 准确率"的基准。
- 能直接拿来类比"特征 gate 回测"的一手证据只有 Amazon（114 对，一致率最高 0.97）、Etsy/Pinterest（定性）和 Jeunen（只测 TPR）。

### Gaps
- Pinterest L1 "一两个实验臂"和 Meta Analytics 博客：需要在网络设置里放行 medium.com、web.archive.org 或 enggist.vercel.app 后再核。
- Booking.com "150 successful ML models"（KDD'19）中"模型性能与业务性能不相关"的原文和数字只看到二手摘要（[the morning paper 等](https://blog.acolyer.org/2019/10/07/150-successful-machine-learning-models/)），全文没拿到。[仍未核]

---

## Q2. 回测协议细节：冻结评估器、定义真值、指标、所需样本量

### Takeaway
现有一手文献已经能拼出一套可以照搬的协议，共 5 步：
1. 先冻结评估器（规格、阈值、映射全部版本化），只在冻结**之后**才跑的实验上验证，按时间顺序分成 discovery 和 replication 两批。
2. 用线上 CI 定义三值真值 y ∈ {+1, 0, −1}。
3. 用离线稳定性区间定义三值预测，允许弃权。
4. 报告 precision、recall、F1（区分 micro 和 macro）、错向数、方向一致率（带 Wilson CI）。
5. 用"重复实验的符号复现率"给方向一致率定上限。

样本量方面，公开研究用了 20–114 个对比。几十个对比的 CI 宽度大约是 ±0.10–0.15。

### Cited Findings
- **冻结与时间切分**（2609.25408 §4.1–4.2）
  - 原文："One versioned specification is held fixed across two chronologically sequential cohorts"。discovery 集是冻结后第一批 5 个实验共 90 个对比，replication 集是之后 8 个实验共 113 个对比。
  - 原文："The same serialized map is applied ... without refitting, row selection, or threshold tuning. The offline evaluations were completed before treatment exposure"。
  - 开发期选型用 leave-one-experiment-out（"with leave-one-experiment-out predictions inside the fitting slice to reduce same-experiment leakage"）。
  - 原文还强调 "contrasts within an experiment can share controls and populations"，所以对比之间不独立，bootstrap 要按**整个实验**重采样（"10,000 paired whole-experiment bootstrap resamples"）。
  - 链接：[arXiv 2609.25408](https://arxiv.org/pdf/2609.25408)
- **真值与指标定义**（2609.25408 §3）
  - y_i = +1 当 L_online > 0，y_i = −1 当 U_online < 0，否则为 0。预测 p_i 用离线区间以同样方式定义。
  - precision = #{p≠0 ∧ p=y} / #{p≠0}；recall = #{p≠0 ∧ p=y} / #{y≠0}。
  - micro F1 = 2ΣC_e / Σ(P_e + O_e)；macro F1 对每个实验分别计算后取平均。
  - 原文："online outcomes unresolved at the chosen confidence level [are treated] as negative decisions, without asserting that their true effects are null"。
  - 另报告排序指标 precision@20%（每个实验的头部和尾部各取 k = min(3, ⌈0.2m⌉)）。
  - 论文明确不用单纯的相关系数，原文："Point correlation and regression error are insufficient on their own: they can reward accurate estimates of near-zero effects while hiding abstention, missed significant movers, or confident wrong-direction calls"。
  - 链接：[arXiv 2609.25408](https://arxiv.org/pdf/2609.25408)
- **一致率与 Wilson CI**（Amazon SIGIR'23 §3.1）
  - α = C/N 按二项分布处理，用 Wilson 区间；同时报告"全部对"和"只取线上显著对"两种口径（114 对与 101 对）。
  - 链接：[Amazon Science PDF](https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf)
- **TPR 口径**（Jeunen §6.2）
  - 只取线上 p ≪ 0.001 的显著改进作为正例，看离线 99% CI 是否严格大于 0。另报告平均 p 值，原文："Lower p-values ... imply that the metric requires less data to achieve the significance level"。
  - 链接：[arXiv 2307.15053](https://arxiv.org/pdf/2307.15053)
- **噪声上限与无信息基线**（2608.02345）
  - 原文："sign-replication rate ... is an upper bound for any forecast no more informative than an independent rerun"。在 67 个营销实验上该值为 0.69；"总猜正向"能拿到 0.57。
  - 原文还提醒 "sign metrics do not separate genuine predictive information from a systematic directional lean"。
  - 链接：[arXiv 2608.02345](https://arxiv.org/pdf/2608.02345)
- **已发表回测的样本量汇总**
  - Jeunen：20 个正例（1 个实验 × 5 天 × 4 信号）。
  - 2609.25408：113（主检验），另有 90（discovery），总计 489。
  - 2604.09549：55。
  - 2608.02345：67。
  - Amazon：114。
  - 链接分别为：[2307.15053](https://arxiv.org/pdf/2307.15053)、[2609.25408](https://arxiv.org/pdf/2609.25408)、[2604.09549](https://arxiv.org/pdf/2604.09549)、[2608.02345](https://arxiv.org/pdf/2608.02345)、[Amazon](https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf)
- **Meta 内部的做法**：SlimPer 上线前经过 "pre-testing and backtesting"（原文 §上线），但没有披露回测协议。链接：[arXiv 2607.12281](https://arxiv.org/pdf/2607.12281)

### Inferences
以下为本笔记作者的推导，不是论文原话。

- **最少回测集规模**
  - 用 Wilson 95% CI 自算：真实一致率为 0.8 时，n=20 的区间为 [0.58, 0.92]，n=30 为 [0.63, 0.91]，n=50 为 [0.67, 0.89]，n=80 为 [0.70, 0.87]，n=114 为 [0.72, 0.86]。
  - 想证明"一致率显著高于 0.57（总猜正）"并且 CI 宽度不超过 ±0.1，**至少需要约 50 个历史特征实验**。20–30 个只够用来发现严重的问题。
  - 以上假设各对比相互独立；同一实验内的多个特征应按实验聚类，有效样本量会更小。
- **噪声上限可以从每个历史 AB 的 z 值估出来**
  - 若真实效应的 z 值为 z，两次独立重复实验符号一致的概率 ≈ Φ(z)² + Φ(−z)²。
  - z = 1 时约 0.73，z = 1.96 时约 0.95。
  - 因此回测集若大量由"线上不显著"的特征组成，方向一致率的上限本来就低。这时应改用 2609.25408 的三值口径，把这类样本记为 y = 0，而不是强行判正负。
- **对我们 L2 gate 的直接映射**
  - L2 的"CI 下界 > δ_min → 入模 / CI 上界 < 0 → 有害 / 其余 → 无显著增量"正好就是 2609.25408 的三值 p_i，可以原样套用它的 precision/recall/F1 和错向数定义。
  - 回测时，评估器（代理模型超参、δ_min、负对照校准）先打版本号并冻结，只对冻结后才上线 AB 的特征做前向验证。
  - 历史集只用于开发，开发时用 leave-one-experiment-out。

### Gaps
- 没有找到任何公司公开的"**特征级** gate 在历史 AB 上的 precision/recall"。现有回测都是模型级、策略级或对话 AI 级。
- 没有找到关于最少回测集规模的正式指南，上面的数字是自己用 Wilson 区间推算的。

---

## Q3. 离线增益如何换算成业务价值（斜率）以及准入门槛的业务含义（R13）

### Takeaway
公开一手资料里有三种换算方式：
- **固定汇率**：JD 每 +1‰ AUC 约 $6M 广告收入（未写时间单位）。Meta LLaTTE 的 0.25% NE 对应 +4.3% 转化，约"数亿美元/年"。
- **从历史 (离线Δ, 在线Δ) 对拟合映射**：2609.25408 用无截距加权回归。
- **成本归一化的 RoI**：Meta SIDE 的 ΣNE / (2C)。

"显著"门槛在不同公司之间差一个数量级，选门槛时必须写明口径。

### Cited Findings
- **JD**：原文 "every 1‰ increase in off-line AUC brings 6 million dollars lift in the overall advertising income"。同文的实际案例是 ΔAUC +0.0086，对应线上 CTR +3.22%、eCPM +2.46%。链接：[arXiv 2006.10337](https://arxiv.org/pdf/2006.10337)
- **Meta LLaTTE**：原文 "approximately 0.25% NE reduction on our flagship ads ranker, corresponding to a 4.3% conversion uplift on Facebook Feed and Reels, a business impact on the order of hundreds of millions of dollars in annual revenue"。同文把 0.02% NE 定为"statistically significant and sufficient to yield measurable revenue impact"。链接：[arXiv 2601.20083](https://arxiv.org/pdf/2601.20083)
- **2609.25408 的校准映射**
  - 公式原文：Δ̂_online = d_h · Σ_k β_k z_ik，"a no-intercept weighted sum of a small set of pre-exposure meta features"，K = 4。
  - 拟合方式是 "inverse online-CI-width weighting"，用 robust-H90 选型。
  - 原文提醒：bootstrap 区间 "are not future-effect prediction intervals"。
  - 链接：[arXiv 2609.25408](https://arxiv.org/pdf/2609.25408)
- **Meta SIDE 的特征 RoI**：RoI = (ΔNE_click + ΔNE_conv) / (2C)，C 为特征 logging 成本（kW）。链接：[arXiv 2506.16698](https://arxiv.org/pdf/2506.16698)
- **Google 的成本-精度两点评估**：原文 "improvement in accuracy when training cost is neutral" 与 "training cost improvement if model capacity is lowered until accuracy is neutral"。链接：[arXiv 2209.05310](https://arxiv.org/pdf/2209.05310)
- **各家"显著"门槛对照表**

  | 来源 | 门槛原文 | 口径 |
  |---|---|---|
  | Meta 2502.17494 / 2601.20083 | 0.02% NE | 相对 |
  | Meta SlimPer | ≈0.03% NE | 相对 |
  | ACTR2 2301.10443 | 0.05% NE | 相对 |
  | Facebook 2014 | 典型特征实验 "a couple of tens of a percent of relative NE"（约 0.2%） | 相对 |
  | Google 2022 | "above 0.1%" PerQueryAuc | 相对 |
  | Google 2013 | AucLoss 降 1% 算"large" | 相对 |
  | DCN / FuxiCTR / JD | 0.001（1‰）AUC 或 logloss | 绝对 |
  | Etsy | AUC > 1% 稳定带来显著 CTR 胜利 | 相对 |

  链接：见 Q1 中各条目。

### Inferences
以下为推导。

- 给 R13 的建议：δ_min 应该写成"业务口径"。
  - 先用历史 (ΔAUC_离线, Δ目标_线上) 对拟合斜率 b，最简单的形式为 Δ线上 ≈ b·ΔAUC，参照 2609.25408 采用无截距、按线上 CI 宽度倒数加权。
  - 然后令 δ_min = (特征年化成本 + AB 机会成本) / (b × 单位指标价值)。这与 Meta 的 RoI 思路一致。
- 还要注意两点：
  - 代理模型（LightGBM/LR）的 Δ 与生产 DNN 的 Δ 量级不同，所以斜率 b 必须拿**代理 Δ** 去回归线上 Δ，不能直接套用 JD/Meta 的生产模型汇率。
  - 1‰（绝对）的经验门槛放在游戏 CVR 这类低 AUC 场景时，量级上可能比 Meta 的 0.02% 相对 NE 宽松或严格很多，口径必须统一。

### Gaps
- 没有找到公开的"斜率 b 的拟合方法和置信区间"的专门指南。JD 的 $6M 没有给出推导方法和时间单位。

---

## Q4. LinkedIn / Uber / Airbnb / 字节 / 快手的特征准入 gate 一手资料

### Takeaway
本轮仍然**没有找到**这些公司公开的、带数值阈值的新特征准入 gate。现有公开资料集中在：
- 特征平台：LinkedIn Feathr、Airbnb Chronon、Uber Michelangelo。
- 部署安全：Uber 的回测和影子测试。
- Google 2013 的"新信号自动测试后白名单准入"机制。

### Cited Findings
- **Google 2013**：原文 "New signals can be vetted by automatic testing and whitelisted for inclusion ... Old signals which are no longer consumed are automatically earmarked for code cleanup"，规模为 "thousands of input signals by hundreds of active models"。这是目前找到的最接近"特征准入 gate"的一手描述。链接：[research.google PDF](https://research.google.com/pubs/archive/41159.pdf)
- **Uber**："Model Excellence Scores"（2024）与 "Raising the bar on ML model deployment safety" 两篇博客。据检索摘要，后者描述了基于历史生产数据的 backtesting、shadow testing，以及每次训练都会生成含 feature importance 的标准报告。[仍未核：www.uber.com 不在白名单] 链接：[Uber MES](https://www.uber.com/en-TH/blog/enhancing-the-quality-of-machine-learning-systems-at-scale)；[Uber deployment safety](https://www.uber.com/en-HN/blog/raising-the-bar-on-ml-model-deployment-safety)
- **LinkedIn**：只检索到 Feathr 特征平台（producer/consumer 分离、point-in-time 正确性），没有准入阈值。链接：[LinkedIn Engineering: Open sourcing Feathr](https://engineering.linkedin.com/blog/2022/open-sourcing-feathr---linkedin-s-feature-store-for-productive-m)
- **Airbnb**：论文中只有离线 NDCG +1% 但线上不显著的案例（见 Q1），没有找到 gate 规则。链接：[arXiv 1810.09591](https://arxiv.org/pdf/1810.09591)
- **快手 / 字节**：中文检索没有结果。

### Inferences
- 在业界公开资料里，"数值化特征准入 gate + 回测验证"仍是空白。我们方案中的 L2 三值判定加冻结前向回测，在公开文献里找不到直接先例。可借鉴的是 Meta/Amazon 在**模型级**评估器上的协议。

### Gaps
- 快手、字节、腾讯的一手技术博客：本轮检索未命中。另外 DataFunTalk、InfoQ 被拦截（infoq.cn 返回 451）。
- Uber、Booking、Pinterest 的博客原文需要放行对应域名后再核。
