# 业界新特征离线评估与离线-在线一致性调研 (Industry feature onboarding & offline→online consistency)

> 研究方法与限制说明（重要）：本次会话的网络环境中，WebFetch 无法访问 arxiv.org、medium.com、infoq.cn、cdn.amazon.science、besthub.dev（DNS 解析失败，需在 session network settings 放行）。因此以下大部分事实来自搜索引擎结果摘要（由搜索工具对原文的摘录/概括），**未能逐字核对原文**。凡标注“[摘要级]”的条目，写报告前建议在可访问原文的环境中复核数字。标注“[训练知识]”的内容来自模型已有知识、本次未经检索验证，仅作线索。
> Date of research: 2026-10-29.

## Q1. 大厂公开描述的新特征准入流程：离线指标、阈值、规模、平台工具

### Takeaway
公开资料普遍描述的是“离线指标（NE/LogLoss/AUC/GAUC/PR-AUC）筛选 → 在线 A/B 决定”的两段式流程，且在线 A/B 是最终裁决；但几乎没有公司公开**数值化的特征准入阈值**或**离线 gate 的准确率**。Meta 公开了“特征池有数千特征、跨模型聚合的全局重要性、按 NE 增益与成本算特征 ROI”等做法；中国厂商公开资料以“特征平台/准入准出（针对 ID 稀疏特征的规模控制）”和“离线实验 + 在线 ABTest 联合筛选”为主。

### Cited Findings
**Meta / Facebook**
- 2014 年 Facebook 广告 CTR 论文（He et al., ADKDD 2014）核心结论：最重要的是有正确的特征，捕获用户/广告历史信息的特征主导其它特征；在特征和模型（GBDT+LR）正确后，数据新鲜度、学习率、采样等只带来小幅增益。主指标为 Normalized Entropy（NE = 每次曝光平均 logloss ÷ 背景 CTR 的熵；归一化使指标对背景 CTR 不敏感，越低越好）。树特征变换使 NE 改善约 3.4%；GBDT+LR 比单一方法好 3% 以上。[摘要级] — [Meta Research 页面](https://research.fb.com/publications/practical-lessons-from-predicting-clicks-on-ads-at-facebook/); [论文 PDF 镜像](https://typeset.io/pdf/practical-lessons-from-predicting-clicks-on-ads-at-facebook-3v0cxs9foz.pdf); [二手总结](https://shagunsodhani.github.io/papers-I-read/Practical-Lessons-from-Predicting-Clicks-on-Ads-at-Facebook)
  - 注：venue 有分歧，Meta 页面列为 ADKDD workshop，Herbrich 个人页列为 KDD 2014 proceedings — [herbrich.me](https://herbrich.me/computational-advertising/)
- Meta Analytics 团队博客（Medium，约 2025 年）：“Meta 的特征池中有数千个特征，选对特征对模型优化至关重要”；提出跨多个模型聚合的“全局特征重要性”作为单模型重要性的补充；用于剪除低重要性特征以降低复杂度、节省容量。[摘要级，非 engineering.fb.com 官方] — [Collective Wisdom of Models: Advanced Feature Importance Techniques at Meta](https://medium.com/@AnalyticsAtMeta/collective-wisdom-of-models-advanced-feature-importance-techniques-at-meta-1a7a8d2f9e27)
- Meta Lattice（AI at Meta 博客）提到“Pareto-front feature selection（MetaBalance）”，用于避免在数千个 domain、数十个目标上手动调优。[摘要级] — [ai.meta.com Lattice](https://ai.meta.com/blog/ai-ads-performance-efficiency-meta-lattice/)
- Meta 广告排序论文 SIDE（arXiv 2506.16698, 2025）中，一个语义 ID 特征带来的 click NE 增益约 0.0085%–0.0108%，且论文将 NE 增益与成本结合计算特征 ROI。说明 Meta 在大模型上单特征的 NE 增益量级可在 0.01% 级别仍被视为有意义。[摘要级] — [SIDE arXiv](https://arxiv.org/pdf/2506.16698)
- 用户问题中提到的“0.1% NE gain is significant at Meta”：本次检索**未找到原始出处**（搜索结果明确无此表述）。[训练知识，未验证] 该说法常见于 Meta DLRM/DHEN 等论文及业界访谈的转述（“0.02%–0.1% NE 即视为显著”），需核对原文。
- Meta Adaptive Ranking Model（engineering.fb.com, 2026-03）：Instagram 上对目标用户广告转化 +3%、CTR +5%（业务指标，非离线 NE）。— [Engineering at Meta](https://engineering.fb.com/2026/03/31/ml-applications/meta-adaptive-ranking-model-bending-the-inference-scaling-curve-to-serve-llm-scale-models-for-ads/)
- MISO（arXiv 2608.07035, 2026）：在广告排序 case study 中以更少验证运行改进 NE（相对手工/黑盒调参）。[摘要级，摘要未给数字] — [MISO](https://arxiv.org/pdf/2608.07035)

**Google**
- “On the Factory Floor: ML Engineering for Industrial-Scale Ads Recommendation Models”（Anil et al., Google, arXiv 2209.05310, 2022, RecSys’22 ORSUM workshop）：Google 搜索广告 CTR 模型的案例研究，强调除精度外的效率、可复现性、校准、credit attribution，并说明新 ML 方法如何在大规模工业环境中被评估。本次未能读取全文中关于离线/在线评估的细节。— [arXiv 2209.05310](https://arxiv.org/abs/2209.05310)
- [训练知识，未验证] McMahan et al., “Ad Click Prediction: a View from the Trenches”（KDD 2013）描述了 Google 的 progressive validation（在线 logloss/AUC，在训练前先在新样本上评估）、按 slice 报告相对 logloss/AUC 变化、以及“大量模型变体并行训练共享数据”的实验框架；论文指出 0.1%~ 级别的 AUC/LogLoss 变化在其规模下有实际意义。需核对原文措辞 — https://research.google/pubs/pub41159/

**Pinterest**
- Related Pins（arXiv 1702.07969, 2017, WWW）：PR AUC 类离线指标对 A/B 实验中的 closeup 和 clickthrough “极具预测性”，但**难以用离线评估预测 save（保存）行为**。[摘要级] — [Related Pins at Pinterest](https://arxiv.org/pdf/1702.07969)
- Pinterest 广告团队有两篇专门讲 online-offline discrepancy 的工程博客（见 Q2 详述）。— [Handling Online-Offline Discrepancy in Pinterest Ads Ranking System](https://medium.com/pinterest-engineering/handling-online-offline-discrepancy-in-pinterest-ads-ranking-system-8fd662da4c2d); [Bridging the Gap: L1 Conversion Models](https://medium.com/pinterest-engineering/bridging-the-gap-diagnosing-online-offline-discrepancy-in-pinterests-l1-conversion-models-1320faaaeefe)

**Airbnb**
- “Applying Deep Learning To Airbnb Search”（Haldar et al., KDD 2019, arXiv 1810.09591）：主离线指标 NDCG；论文 Figure 2 并列展示各模型离线 NDCG 相对提升与线上转化提升；第一个上线的 NN 与 GBDT 相比 booking 中性（同特征同目标）；新模型最终在 A/B 中看是否获得统计显著的转化提升。[摘要级] — [arXiv 1810.09591](https://arxiv.org/pdf/1810.09591); [the morning paper 解读](https://blog.acolyer.org/2019/10/09/applying-deep-learning-to-airbnb-search/)

**DoorDash**
- DoorDash 广告转化预测（arXiv 2502.10514, 2025）：离线与线上 AUC 相差约 4.3%，归因于训练数据陈旧和新特征缺乏线上日志；后续把差距缩小到 0.76%。DoorDash 博客另提到：离线用“前一天特征值”模拟线上推理，但线上实时推理 AUC 仍比离线低约 4%。[摘要级] — [arXiv 2502.10514](https://arxiv.org/pdf/2502.10514); [DoorDash 博客](https://careersatdoordash.com/?p=13497)

**Etsy**
- Etsy Promoted Listings CTR（arXiv 1711.01377, 2017）：团队要求离线指标满足 **sign-correlation**（离线赢 ⇒ 在线赢）和**量级正确**（个位数 AUC 提升对应个位数 CTR 提升）；称 AUC 经多次研究被确立为可靠的预测力指标。[摘要级] — [Etsy arXiv 1711.01377](https://arxiv.org/pdf/1711.01377)

**美团**
- 美团外卖特征平台：旧框架中新特征上线需同时改离线侧和在线侧代码，周期长；新平台配置化。**新特征评估流程：先从特征仓库检索候选集 → 结合“特征画像”筛选 → 离线实验流程 → 在线 ABTest，结合模型效果评估筛选出最终结果集。** [摘要级] — [InfoQ: 美团外卖特征平台的建设与实践](https://www.infoq.cn/article/i38hsz2hm8zs58stjclb); [CSDN 转载（美团技术）](https://blog.csdn.net/MeituanTech/article/details/114381336)
- 美团配送实时特征平台：特征上线从多天缩短到分钟级，收口新特征 60 多个。[摘要级] — [InfoQ](https://www.infoq.cn/article/40uuwny38rbvsf3wm3my)
- 美团效果广告实验配置平台（2019）：参照 Google 分层实验框架设计，在搜索广告投放系统全量上线，支持算法各方向垂直实验与配置审核。— [tech.meituan.com 2019/11/28](https://tech.meituan.com/2019/11/28/advertising-performance-experiment-configuration-platform.html)

**阿里妈妈**
- 搜索广告 CTR 模型：ID 类特征（userid/queryid/adid）无冲突表达需要“复杂的特征准入准出策略”以免模型规模随新特征线性膨胀；该策略在数据分布剧烈变化时需频繁调整、鲁棒性低。传统特征选择偏启发式、需与系统指标交替迭代，效率低；借鉴 Dropout Feature Ranking 把特征重要性纳入训练。[摘要级] — [阿里妈妈搜索广告预估模型2021思考与实践（知乎）](https://zhuanlan.zhihu.com/p/446993392); [6aiq 转载：搜索广告CTR模型“瘦身”](https://www.6aiq.com/article/1622767805531)
- FSCD（SIGIR 2021）：可学习的自动特征选择，把算力代价作为先验正则，使特征重要性同时考虑效果与效率，用于粗排并全量上线。[摘要级] — [知乎：三篇SIGIR论文详解](https://zhuanlan.zhihu.com/p/375938867)

**爱奇艺（iQIYI）**
- 广告特征评估由人工、工程密集流程改为基于 Opal 机器学习平台的自动化流水线，评估周期从 5 天缩短到 1.5 天。[摘要级，转载站点，原文未读] — [Opal 平台优化广告特征评估](https://besthub.dev/articles/optimizing-advertising-feature-evaluation-process-with-the-opal-machine-learning-platform-69358661913d)

### Inferences
- 业界公开资料的共同模式：离线 gate 是“必要非充分”条件，用于**淘汰**而非**决定上线**；在线 A/B 是唯一 ground truth。我们 L1/L2 设计与美团“特征画像筛选 → 离线实验 → 在线 AB”结构一致。
- Meta 的“NE 增益 × 成本 = 特征 ROI”与“跨模型全局重要性”对应我们 L2 中加入算力/存储成本项、以及在多模型（CTR/CVR/游戏）上聚合评估的方向。
- 单特征在成熟大模型上的真实增益可能只有 0.01% NE 量级（SIDE），这意味着用 LightGBM/LR 代理模型做 ablation 可能无法分辨这么小的效应——代理模型与生产 DNN 的“增益可迁移性”本身是需要验证的假设（R1 的一部分）。

### Gaps
- 未找到 Meta “0.1% NE 显著”阈值的一手出处；未找到 Meta 内部 feature exploration / FBLearner 特征实验平台的公开流程细节。
- 未检索到 LinkedIn (Frame/Feathr)、Uber Michelangelo、Airbnb Chronon/Zipline、Netflix、Twitter/X、Snap、Instacart、字节、快手、腾讯广告在“新特征准入阈值/流程”上的公开具体描述（受工具调用预算与 medium/arxiv 无法直接访问限制）；这些平台公开资料主要是 feature store/特征计算，而非“特征准入 gate”。
- 没有任何来源给出“每轮测试多少新特征”的具体数字（除美团配送“收口 60+ 新特征”）。

## Q2. 离线增益→在线 A/B 的一致性证据、失配原因与改进方法

### Takeaway
公开的定量证据显示：离线指标在**方向上**大体可用（中等相关、“sign agreement”是业界常用标准），但离线大幅增益经常在线上被“吃掉”——Pinterest 报告多个离线强增益的实验臂中只有 1–2 个在线显著获胜；DoorDash 报告离线/在线 AUC 差 ~4%。失配主因：特征穿越/线上线下特征不一致、样本空间（只有曝光样本）偏差、AUC 不反映校准与出价/拍卖、后链路（融分/重排/拍卖）、分群效应、统计噪声。

### Cited Findings
**定量证据**
- Pinterest L1 转化模型：在若干离线增益明显的实验臂中，**只有一到两个带来清晰的线上胜利**，且与召回（recall）实际变化之处吻合。诊断框架分三桶：(1) 离线指标是否可信（采样、标签、异常值、评估设计）；(2) serving 与特征是否与训练一致（特征覆盖、embedding 构建、模型版本、服务链路）；(3) 漏斗/效用设计是否抹掉了收益。离线用 LogMAE、KL，线上主指标是 CPA（受出价、预算、pacing、拍卖逻辑影响）。[摘要级] — [Pinterest: Bridging the Gap (L1 Conversion)](https://medium.com/pinterest-engineering/bridging-the-gap-diagnosing-online-offline-discrepancy-in-pinterests-l1-conversion-models-1320faaaeefe)
- Pinterest 广告排序：即使系统**无 bug**，离线与线上指标的变化也可能没有清晰相关，需要精细的指标设计；**有 bug** 的系统则表现为线上收益减弱或为负。[摘要级] — [Pinterest: Handling Online-Offline Discrepancy](https://medium.com/pinterest-engineering/handling-online-offline-discrepancy-in-pinterest-ads-ranking-system-8fd662da4c2d)
- Pinterest 电商检索（arXiv 2607.14161, 2026）：replay 对策略可控指标（如 triggering rate）几乎精确，但对下游 session 指标应视为“趋势估计器”而非点预测。[摘要级] — [arXiv 2607.14161](https://arxiv.org/pdf/2607.14161)
- Amazon Science “How well do offline metrics predict online performance of product ranking models”：直接研究产品排序模型离线指标对线上表现的预测力（本次无法下载 PDF，具体相关系数未获取）。— [Amazon Science PDF](https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf)
- 小型电商推荐（arXiv 1809.03186, 2018）：AUC、MRR、nDCG@100 与访问率、CTR 呈**中等相关**，且不同算法间相关性不一致。[摘要级] — [Off-line vs. On-line Evaluation in Small E-commerce](https://arxiv.org/pdf/1809.03186)
- Criteo “Offline A/B testing for Recommender Systems”（Gilotte et al., WSDM 2018, arXiv 1801.07030）：在商业推荐系统上，用线上 A/B 业务指标作为基准评估反事实估计器；传统 capped / normalised IPS 偏差-方差权衡不理想，提出的变体与线上业务指标相关更好。[摘要级] — [arXiv 1801.07030](https://arxiv.org/abs/1801.07030)
- CPM-sensitive AUC（arXiv 1904.10272）：离线 AUC 提升而线上 CPM 未必提升，因为 AUC 只衡量 CTR 排序而非 CTR×bid 排序。[摘要级] — [alphaxiv 1904.10272](https://alphaxiv.org/abs/1904.10272)
- Meta 相关的 USM 论文（arXiv 2412.10674, 2024）：上线 A/B 后计算线上 AUC 与校准，以检查离线-在线一致性。[摘要级] — [arXiv 2412.10674](https://arxiv.org/pdf/2412.10674)

**失配原因（中文业界经验，多为知乎/CSDN 经验帖，非权威研究）**
- 线上线下特征抽取实现不同（如离线截断最近 30 次行为、线上 20 次）、时间戳错误/特征穿越、线上特征缺失；样本空间不一致（离线只评曝光样本，线上面对更大候选集，SSB）；AUC 不反映打分绝对准确度，需看 PCOC 等校准指标；AUC 是全局指标，应看 GAUC；精排后还有融分/重排/混排；离线涨幅可能只是波动；新特征带位置等偏置。— [知乎: 推荐场景线上线下指标不一致](https://zhuanlan.zhihu.com/p/336959267); [知乎: AUC离线和在线表现不一致问题](https://zhuanlan.zhihu.com/p/574109405); [知乎: AUC涨了CTR却掉](https://zhuanlan.zhihu.com/p/1916515729613754862); [知乎: 为什么新增特征有时会带来负面影响](https://www.zhihu.com/question/269499064); [CSDN: 离线AUC涨在线无效果](https://blog.csdn.net/lolanlolan/article/details/119246846)
- 分群效应：AUC/NE 在全体样本上求和，一个对某群体有益、对另一群体有害的模型可在离线上显得中性但线上回退。[二手博客] — [Discrepancy in Offline & Online Evaluation](https://agrawalp.substack.com/p/discrepancy-in-offline-and-online)

### Inferences
- 对广告模型（CTR/CVR 用于 eCPM 排序与出价）而言，**校准指标（PCOC / calibration、NE）和按 bid 加权的 AUC** 应纳入 L2 gate，而不仅是 ΔAUC；游戏行业 CVR（付费/激活）稀疏、延迟反馈，更易出现 Pinterest 所述“离线强但线上弱”。
- “新特征缺少线上日志/回补特征存在穿越”是 DoorDash 与知乎经验共同指出的头号原因——对我们的回溯（backfill）特征评估尤为关键：L1/L2 应检查特征的 point-in-time 正确性与线上覆盖率（feature coverage）。
- 一致性目标宜设为“方向一致（sign agreement）+ 量级同阶”（Etsy 标准），而非高精度点预测（Pinterest replay 结论）。

### Gaps
- 未找到大厂公开的“离线 ΔAUC/ΔNE 与在线 Δ 指标的秩相关系数”具体数值（Amazon Science 论文可能有，但未能访问）。
- Netflix、LinkedIn、Booking 在离线-在线一致性上的公司专属定量数据本次未检索到。

## Q3. 是否有公司用“历史特征/实验 + 已知 AB 结果”作为 backtest 集来验证离线 gate？有无报告的 precision/recall？

### Takeaway
有，但公开且定量的多为**学术/2026 年新近论文**和专利，而非大厂特征 gate 的直接报告：做法是收集历史 A/B 实验作为 ground truth，衡量离线评估器的方向一致率（sign agreement）、F1、Spearman 相关等。尚未找到任何公司公开“特征准入 gate 的 precision/recall”。

### Cited Findings
- 食品推荐平台（arXiv 2604.09549, 2026）：使用 **55 个历史 A/B 实验**的专有数据集，计算模拟结果与真实结果的 Spearman 相关。[摘要级] — [Beyond Offline A/B Testing](https://arxiv.org/html/2604.09549v2)
- “From Offline Proxies to Online Decisions”（arXiv 2609.25408, 2026）：**冻结的离线评估器**在其冻结之后才运行的 8 个 A/B 实验、113 个对比上验证，F1 = 81.1%，在共享切片上比另外 5 个离线评估器高 25.7 个点；错误方向判为失败，接近显著的一致给予部分分。[摘要级] — [arXiv 2609.25408](https://arxiv.org/pdf/2609.25408)
- Agentic 模拟（arXiv 2608.02345, 2026）：67 个营销实验上方向一致率 0.70，但高估效应量。[摘要级] — [arXiv 2608.02345](https://arxiv.org/html/2608.02345v1)
- Jeunen et al.（arXiv 2307.15053, 2023）：以**统计显著的线上胜利**作为 ground truth，计算各离线估计器标出显著差异的真阳性率，并统计方向一致；在一个个性化实验上各估计器 100% 方向一致。[摘要级] — [On (Normalised) DCG as an Off-Policy Evaluation Metric](https://arxiv.org/pdf/2307.15053)
- 专利（US 11782821 / 11409637, “Page simulation system”）：描述选取在**过往 A/B 实验**上与线上指标强相关的离线指标，用于在 A/B 前拒绝弱变体。[摘要级] — [USPTO 11782821](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11782821)
- Etsy：明确把“sign-correlation + 量级”作为接受离线指标的标准，并称经多次研究确立 AUC 的可靠性（即用历史实验校验离线指标）。[摘要级] — [Etsy arXiv 1711.01377](https://arxiv.org/pdf/1711.01377)
- AutoOffAB（arXiv 2312.10624, 2023）：自动化离线 A/B 测试方向的研究。[仅标题级] — [arXiv 2312.10624](https://arxiv.org/pdf/2312.10624)

### Inferences
- 对 R1 的可行方案（推断，非已证实业界做法）：建立“特征 backtest 集”——收集过去 N 个已做过生产重训 + 在线 AB 的特征/特征组（含失败的），把它们回放过 L1/L2 gate，报告：(a) 方向一致率；(b) 以“线上显著正向”为正例的 precision/recall（或 F1，参照 2609.25408 的协议：错向=失败、近显著部分分）；(c) 离线 ΔAUC/ΔNE 与线上 Δ 指标的 Spearman 相关。评估器需**冻结后**再在新实验上前向验证，避免对历史集过拟合。
- 样本量现实：公开研究的历史实验数仅 8–67 个，说明几十个历史实验已足以给出有意义的方向一致率估计（但 CI 较宽）。
- 由于 gate 的作用是“淘汰”，应更看重**召回（不误杀线上会赢的特征）**与对“负向特征”的拦截率；可接受较低 precision，因为在线 AB 还会再过滤。

### Gaps
- 未找到 Meta/Google/字节/阿里等大厂公开其“特征准入 gate”在历史实验上的 precision/recall 或相关系数。
- 2026 年的几篇 arXiv 论文为新近预印本，未经同行评审，且本次只看到摘要。

## Q4. 中国业界（美团、阿里妈妈、字节/火山、快手、腾讯广告、知乎/InfoQ）关于特征准入/评估/上线流程

### Takeaway
中文公开资料中，“特征准入”多指**稀疏 ID 特征的准入准出（频次/规模控制）**，与“新特征价值评估”不同；新特征价值评估公开描述较少，典型为美团外卖“特征仓库检索 → 特征画像筛选 → 离线实验 → 在线 ABTest”。离线-在线不一致的经验总结大量存在于知乎/CSDN（特征一致性、样本空间、GAUC、PCOC 校准、后链路）。

### Cited Findings
- 美团外卖：新特征评估 = 特征仓库检索候选 → 特征画像筛选 → 离线实验流程 → 在线 ABTest，结合模型效果确定最终集合。— [InfoQ](https://www.infoq.cn/article/i38hsz2hm8zs58stjclb)
- 美团配送实时特征平台：特征上线多天→分钟级，收口 60+ 新特征。— [InfoQ](https://www.infoq.cn/article/40uuwny38rbvsf3wm3my)
- 美团效果广告实验平台（2019，Google 分层实验）。— [tech.meituan.com](https://tech.meituan.com/2019/11/28/advertising-performance-experiment-configuration-platform.html)
- 阿里妈妈：ID 特征“准入准出策略”控制模型规模，分布剧变时需频繁调整；Dropout Feature Ranking 将重要性融入训练；FSCD 将算力作为正则的可学习特征选择，粗排全量。— [知乎 2021 思考与实践](https://zhuanlan.zhihu.com/p/446993392); [知乎 SIGIR 三篇](https://zhuanlan.zhihu.com/p/375938867)
- 天池 IJCAI-18 阿里妈妈比赛方案：LightGBM 输出的特征重要性被认为不可靠且无法反映特征组合影响，改用 wrapper 式搜索选择特征。[竞赛经验，非生产] — [CSDN](https://blog.csdn.net/Bryan__/article/details/80600189)
- 爱奇艺 Opal：广告特征评估自动化，周期 5 天 → 1.5 天。— [besthub 转载](https://besthub.dev/articles/optimizing-advertising-feature-evaluation-process-with-the-opal-machine-learning-platform-69358661913d)
- 字节广告面经提到 SSB（样本选择偏差），线上数据受曝光机制、冷启动影响与离线数据不完全匹配。[面经，低可信度] — [CSDN 面经](https://blog.csdn.net/yin2567588841/article/details/146106676)
- 典型上线流程：离线评估 → 线上线下一致性测试 → A/B 分流（如先 10% 流量）→ 线上监控。— [阿里云开发者社区](https://developer.aliyun.com/article/1476105)

### Inferences
- 阿里 IJCAI-18 经验（树模型 importance 不可靠、需 wrapper/ablation）支持我们 L2 用 ablation 而非 gain importance；但 LightGBM/LR 代理模型与生产 DNN 的结构差异（无法捕捉 embedding/交叉）意味着代理 ΔAUC 需要在 backtest 中验证其与生产重训 Δ 的相关性。
- FSCD/Meta ROI 均把成本纳入特征价值，建议 lifecycle 管理中把“NE/AUC 增益 / 存储+算力+延迟成本”作为准出依据。

### Gaps
- 快手、腾讯广告、字节/火山引擎关于“新特征价值评估 gate / 阈值”的一手技术博客本次未检索到（检索预算与站点访问受限）；建议后续检索：“快手 特征 自动化 评估 平台”、“腾讯广告 特征 准入 AUC”、“火山引擎 特征平台 特征评估”、DataFunTalk 分享。
- 没有中文来源给出“离线 AUC 提升多少（如千分之几）才进入 AB”的公开数值阈值；业界口头常说“千分之一/千分之三 AUC 提升”，但本次未找到可引用的一手出处。
