# 增量特征评估的统计方法（ΔAUC / ΔLogLoss 的推断、功效、等效/非劣效与多重比较）

> 适用背景：proxy 模型（LightGBM + LR）在 time-split 验证集上 with/without 候选特征，配对 clustered Poisson bootstrap（cluster=user）估计 ΔAUC 的 CI；准入 = 任一 proxy 的 CI 下界 > δ_min；有害 = 所有 proxy CI 上界 < 0；下线计划用非劣效检验。待解决评审项：R3（L1/L2 共享验证日）、R4（"无显著增益" vs "无增益"，缺 MDE）、R9（滚动多窗口、多目标、联合确认顺序）、多重比较。
>
> 说明：带 [未在本次会话核实全文] 标记的来源为经典文献，引用基于书目信息/摘要，具体公式请以原文为准。

## Q1. 嵌套模型同数据 ΔAUC 的 CI / 检验方法（DeLong 及其问题、bootstrap、CV 类检验、LRT/LogLoss、NRI/IDI）

### Takeaway
对"加一个特征的嵌套模型"，DeLong 检验在零假设（新特征无关）下分布非正态、极度保守，**不应用于检验 ΔAUC=0**；生物统计主流建议是"用似然比/关联检验做显著性，用 ΔAUC 做效应估计+CI"。对 ML 场景（非线性模型、需重训练），应当用对**训练+评估全流程**做重采样或修正方差的 CV 检验；ΔLogLoss（即样本外对数似然差）是比 ΔAUC 更灵敏、更"proper"的增量指标；NRI/IDI 不推荐作为主判据。

### Cited Findings
- DeLong, DeLong & Clarke-Pearson (1988, Biometrics 44:837–845) 提出基于 U 统计量 structural components 的相关 ROC 曲线 AUC 比较非参数方法 —— 引自 [Hanley & McNeil 后续综述/摘要页](https://pubmed.ncbi.nlm.nih.gov/6878708/) 及 [Obuchowski 1997 摘要](https://www.bohrium.com/paper-details/nonparametric-analysis-of-clustered-roc-curve-data/812073859254583296-922)（后者明确称其扩展了 DeLong 1988 方法）。
- Hanley & McNeil (1983, Radiology 148:839–843)：同一批样本上的两个 AUC 相关，利用两者相关系数可显著缩小差值标准误、提高功效（类似配对 t 检验）—— [PubMed 6878708](https://pubmed.ncbi.nlm.nih.gov/6878708/)。
- **Demler, Pencina & D'Agostino (2012, Stat Med 31(23):2577–2587)《Misuse of DeLong test to compare AUCs for nested models》**：数值模拟+广义 U 统计量论证，当新增预测变量与结局无关时，ΔAUC 的零分布**非正态**，DeLong 检验因此**保守、功效损失大**（小/中效应时尤甚）；解释了"变量显著相关但 ΔAUC 不显著"的常见现象；建议嵌套模型只做新变量的关联检验，若显著再给 ΔAUC 的 CI（可用 DeLong 方差）；非嵌套模型或新变量确实有关联时不存在此问题 —— [PMC3684152](https://pmc.ncbi.nlm.nih.gov/articles/PMC3684152); [Duke Scholars](https://scholars.duke.edu/publication/952688)。
- **Pepe, Kerr, Longton & Wang (2013, Stat Med 32:1467–1482)《Testing for improvement in prediction model performance》**：ΔAUC=0、ΔNRI=0、ΔIDI=0 等"无改善"零假设都等价于"调整基线后新标志物不是风险因子"这一简单零假设；不考虑回归系数估计变异的标准程序（含 ΔAUC 的 DeLong）**极度保守**；理论显示**似然比检验（LRT）渐近更有功效**；建议性能指标聚焦**估计而非"无改善"检验** —— [PMC3625503](https://pmc.ncbi.nlm.nih.gov/articles/PMC3625503); [UW Biostat WP 379](https://biostats.bepress.com/uwbiostat/paper379)。
- Vickers, Cronin & Begg (2011, BMC Med Res Methodol 11:13)《One statistical test is sufficient for assessing new predictive markers》：同样主张对新标志物只做一次（关联/LR）检验，ΔAUC 的检验是冗余且低功效的 —— [BMC](https://bmcmedresmethodol.biomedcentral.com/articles/10.1186/1471-2288-11-13) [未在本次会话核实全文]。
- 后续工作（Michael 等预印本）仍将 Demler et al. (2012, 2017) 视为 AUC 差推断出错的典型例证 —— [haben-michael delong_null.pdf](https://haben-michael.github.io/preprints/delong_null.pdf)。
- **NRI/IDI 的批评**：Kerr et al. (2014, Epidemiology 25(1):114–121) 指出两类别 NRI 的组分就是 ΔTPR/ΔFPR，应直接用这两者报告；≥3 类 NRI 不能反映有临床意义的跨类迁移；**category-free NRI 即使在独立验证数据上也会夸大新标志物的增量价值**；应分别报告事件/非事件的 NRI —— [UW Biostat WP 393](https://biostats.bepress.com/uwbiostat/paper393); [Kerr PDF](https://cnsgenomics.com/data/teaching/SISG/module_10/Mod10_Session7Naomi/Resources/Kerr_NetReclassIndex.pdf)。Pepe, Janes, Kerr, Psaty 另有《Net Reclassification Index: a Misleading Measure of Prediction Improvement》工作论文 —— [PMC3625503 相关](https://pmc.ncbi.nlm.nih.gov/articles/PMC3625503)。
- **Nadeau & Bengio (2003, Machine Learning 52:239–281)《Inference for the Generalization Error》**：随机子采样（重复 train/test 划分）下朴素配对 t 检验因忽略训练集重叠导致的相关性而**低估方差、I 类错误膨胀**；修正重采样 t 检验将方差项乘以 (1/J + n_test/n_train)（J 为重复次数）—— [correctR vignette](https://archive.linux.duke.edu/cran/web/packages/correctR/vignettes/correctR.html); [MachineShop t.test 文档](https://rdocumentation.org/packages/MachineShop/versions/3.3.0/topics/t.test)。Bouckaert & Frank (2004, PAKDD, LNCS 3056) 将其扩展到重复 k-fold CV（corrected repeated k-fold cv test）并关注检验的**可重复性** —— [Springer](https://link.springer.com/chapter/10.1007%252F978-3-540-24775-3_3)。
- **Dietterich (1998, Neural Computation 10(7):1895–1924)**：比较五种检验，McNemar 与 **5×2cv 配对 t 检验** I 类错误低、功效尚可；Alpaydın (1999) 提出组合 5×2cv F 检验，I 类错误更低、功效更高 —— [5x2cv 说明](https://metricgate.com/calculator/5x2cv-paired-t-test); [Alpaydın 1999 PDF](https://typeset.io/pdf/combined-5-2-cv-f-test-for-comparing-supervised-1wq8lejop3.pdf)。Bouckaert 的相关工作发现 5×2cv、重采样与 10-fold cv 检验**可重复性低**（同一对算法、同数据、同检验，不同人得到不同结论）—— [同上检索结果，Bouckaert ICML 工作](https://typeset.io/pdf/choosing-between-two-learning-algorithms-based-on-calibrated-2lbw51syg4.pdf)。
- **贝叶斯替代**：Benavoli, Corani, Demšar & Zaffalon (2017, JMLR 18(77):1–36) 主张放弃 NHST，提出 Bayesian correlated t-test（继承 Nadeau-Bengio 的相关性修正）、层次相关 t 检验、Bayesian signed-rank；结合 ROPE（实际等价区域）可直接输出 P(A 更好)/P(实际等价)/P(B 更好) 三个概率 —— [JMLR v18/16-305](https://www.jmlr.org/papers/v18/16-305.html); 代码 github.com/BayesianTestsML/tutorial。

### Inferences
- 我们的 proxy 是 LightGBM（非参数、非嵌套意义上的严格似然模型），Demler/Pepe 的"LRT 代替 ΔAUC 检验"不能直接照搬；但**同一思想可迁移**：以 **ΔLogLoss（样本外平均对数似然差，= 每样本"LRT 贡献"）** 作为主检验统计量，ΔAUC 作为业务可解释的效应量报告。ΔLogLoss 是逐样本可加的（per-sample loss 差 d_i = ℓ_i^{without} − ℓ_i^{with}），配对 cluster bootstrap / cluster-robust t 检验都很自然，且近似正态性比 ΔAUC 好（ΔAUC 是双样本 U 统计量、在零附近有 Demler 所述的非正态问题）。
- 我们现有的"CI 下界 > δ_min"属于估计导向，符合 Pepe 2013 的建议；但应注意 **δ_min>0 时 Demler 的零附近非正态问题影响减弱**（检验的是 ΔAUC=δ_min 而不是 0），而"有害"判定（上界<0）恰在零附近，percentile bootstrap 可能保守 —— 建议用 BCa 或在 ΔLogLoss 上判定有害。
- 当前方案只对**评估集**做 bootstrap、未重训练模型，因此 CI 仅反映"给定这两个已训练模型，在验证分布上的差异"的抽样变异，不包含训练集抽样与训练随机性（见 Q3）。Nadeau-Bengio/5×2cv 类方法正是为"算法级"比较设计，但在 time-split + 大数据场景下成本高、且 CV 打乱时间顺序；更实际的是"多 seed 重训练 + 评估集 cluster bootstrap"的嵌套方差分解。
- NRI/IDI：不建议纳入准入判据；若业务需要分阈值解读，报告 ΔTPR/ΔFPR @ 业务阈值即可。

### Gaps
- 未找到专门针对 GBDT 类非参数 proxy 的"嵌套 ΔAUC 零分布"研究；Demler/Pepe 结论基于 logistic 回归。
- 未核实 Nadeau-Bengio 修正因子的原文精确形式（以上来自二手文档）。

## Q2. 聚类/相依数据下的方差：cluster bootstrap、block bootstrap、Poisson bootstrap、Obuchowski 聚类 AUC

### Takeaway
同一用户多条样本相关，忽略聚类会使 AUC 及 ΔAUC 的方差被低估、检验过于宽松；Obuchowski (1997) 给出聚类 AUC 的解析方差（design effect / 有效样本量思想），Chamandy et al. (2012) 的 Poisson bootstrap 是可在 MapReduce 中按 cluster 并行实现的标准工程方案；时间相依（日级效应）需要 block/stationary bootstrap 或按日聚类。

### Cited Findings
- **Obuchowski (1997, Biometrics 53:567–578)**：将 DeLong structural components 方法扩展到**聚类 ROC 数据**，借用 Rao & Scott (1992) 的 design effect 与有效样本量概念；模拟显示**假设独立的检验在簇内相关时过于宽松**；方法适用于多种簇内相关水平、连续/有序评分，并讨论了聚类设计的样本量规划 —— [摘要页](https://www.bohrium.com/paper-details/nonparametric-analysis-of-clustered-roc-curve-data/812073859254583296-922); [Cleveland Clinic clusteredROC R 实现](https://www.lerner.ccf.org/quantitative-health/documents/clusteredROC_help.pdf)。
- Wu (2020) 指出 Obuchowski 估计量对簇内/簇间配对比较等权，在中等簇内相关且簇很大时**对单个 AUC 及 AUC 差的效率损失可能很大**，提出加权版本 —— [RePEc lstaxx v49 i6](https://ideas.repec.org/a/taf/lstaxx/v49y2020i6p1446-1461.html)。
- **Chamandy, Muralidharan, Najmi & Naidu (2012, Google)《Estimating Uncertainty for Massive Data Streams》**：提出基于 bootstrap 与一种子抽样的两种流式不确定性估计方法；Poisson bootstrap（每个单元权重 ~ Poisson(1)）可在 MapReduce 框架中实现、天然并行 —— [Google Research](https://research.google/pubs/pub43157/)；该近似源自 Hanley & MacGibbon (2006) "bootstrap 重抽样频数可由 Poisson 频数良好近似" —— [arXiv 2202.10992](https://arxiv.org/pdf/2202.10992.pdf)。
- 块 bootstrap：Künsch (1989, Ann. Stat.) moving block bootstrap；Politis & Romano (1994, JASA) stationary bootstrap —— 经典文献 [未在本次会话核实全文]（Künsch: https://doi.org/10.1214/aos/1176347265 ；Politis & Romano: https://doi.org/10.1080/01621459.1994.10476870 ）。

### Inferences
- 我们"配对 + cluster=user 的 Poisson bootstrap"在方法论上与 Obuchowski 的思路一致且更通用（不依赖 U 统计量解析式）。关键实现要求：**同一 bootstrap 复本中 with/without 两个模型使用同一组 user 权重**（配对），AUC 用加权 AUC 计算（正负样本对权重 = w_i·w_j）。
- 还存在**时间相依**：验证集若跨多天，日级共同冲击（活动、流量结构）使同日样本相关；建议做两路（user × day）或至少检查"按天聚类"的方差与"按用户聚类"的方差，取较大者（保守），或采用 two-way cluster bootstrap（user 与 day 各自独立 Poisson 权重相乘，Owen 2007 "pigeonhole bootstrap" 思路 [未在本次会话核实]）。
- 用 Obuchowski 解析方差可作为 bootstrap 的 sanity check，并直接用于 MDE 的快速估算（见 Q4）。

### Gaps
- 未找到工业界公开的"按 user × day 双向聚类做 AUC CI"的具体案例。
- Chamandy et al. 全文未打开，具体理论结论未核实。

## Q3. 计入 proxy 模型训练随机性（seed variance）

### Takeaway
只对评估集做 bootstrap 会漏掉训练随机性（seed、bagging/feature fraction、数据顺序）和训练集抽样变异；Bouthillier et al. (2021) 证明把更多变异源纳入（即使是"有偏"的随机化多源估计）比只变一个 seed 更接近理想估计，且计算量可降 51 倍。对 LightGBM proxy，至少应对 with/without 各跑 R 个 seed，用嵌套方差分解给 CI。

### Cited Findings
- **Bouthillier et al. (2021, MLSys)《Accounting for Variance in Machine Learning Benchmarks》**：对完整 benchmark 流程建模，发现**数据抽样、参数初始化、超参选择**的随机性显著影响结果；在 5 个任务上测量"检测改进"的错误率；反直觉结论：**纳入更多变异源的有偏估计量更接近理想估计量，且计算成本降低 51×**；并给出比较性能的建议（如随机化尽可能多的变异源、用概率型改进判据 P(A>B)） —— [arXiv 2103.03098](https://arxiv.org/abs/2103.03098); [MLSys 2021](https://proceedings.mlsys.org/paper_files/paper/2021/hash/0184b0cd3cfb185989f858a1d9f5c1eb-Abstract.html)。
- Nadeau & Bengio (2003) 的核心即：算法级比较必须考虑训练集变异，否则 t 检验过于宽松 —— [correctR vignette](https://archive.linux.duke.edu/cran/web/packages/correctR/vignettes/correctR.html)。
- Picard (2021)《torch.manual_seed(3407) is all you need》报告仅改变随机种子即可在 CV 任务上产生与"论文间改进"同量级的差异 —— arXiv 2109.08203 [未在本次会话核实全文]。

### Inferences
- **推荐方差分解**：对每个 seed r=1..R，训练 with/without（**同 seed 配对**），得 Δ_r；对评估集做 B 次 cluster bootstrap 得 Δ_{r,b}。总方差 ≈ Var_boot（评估抽样，取 R 个 seed 的均值）+ Var_seed/R（若报告 R 个 seed 的平均 Δ）。更直接：**每个 bootstrap 复本随机抽一个 seed**（Bouthillier 式的"多源随机化"），用复本分布的分位数做 CI。
- 当 Var_seed 显著（GBDT 用 bagging_fraction/feature_fraction<1 时常见）而 R=1 时，现有 CI 偏窄 → 假阳性准入。建议先做一次校准实验：取若干**已知无用的随机噪声特征/置换特征**（null features）跑全流程，看准入率是否 ≈ 名义 α（这也是检验 I 类错误的最直接方法）。
- 对于"任一 proxy 下界>δ_min 即准入"的 OR 规则：两个 proxy 各自 α 水平，族错误率最高约 2α（LGBM 与 LR 结果正相关时更低）；需要 Bonferroni（各 α/2）或基于联合 bootstrap 的 max-statistic 校正（见 Q5）。

### Gaps
- 未检索到推荐系统/CTR 领域专门量化"重训练方差 vs ΔAUC 典型增益"的论文（如 0.1% AUC 级增益与 seed 方差对比）；此为重要缺口，建议内部实测。

## Q4. 功效分析 / MDE；"不确定" vs "等效"；TOST 等效与非劣效；在 ML 比较与在线实验中的应用

### Takeaway
"CI 下界不过 δ_min" 不等于 "没有增益"。应在每次评估时报告 MDE（或等价地报告 CI 宽度），并用三/四分区决策：**显著超优、等效（CI ⊂ (−Δ_eq, +Δ_eq)，TOST）、非劣（下界 > −Δ_NI）、不确定（CI 跨越边界）**。Spotify 2024 的风险感知决策框架是工业界把超优检验 + 非劣效检验组合、并对 power 做多重校正的范例。

### Cited Findings
- **Lakens (2017, SPPS 8(4):355–362)**：非显著结果常被误解为"无效应"；**TOST**：设定基于"最小关注效应量（SESOI）"的上下等效界 [−Δ_L, Δ_U]，两个单侧检验均显著（等价于 (1−2α) CI 完全落在等效界内）即宣称等效；需预先注册边界并做功效分析 —— [PMC5502906](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906); [TOSTER vignette](https://cran.r-project.org/web/packages/TOSTER/vignettes/IntroductionToTOSTER.html)。Lakens, Scheel & Isager (2018, AMPPS) 给出设边界与报告的教程 —— [同上 vignette 引用]。
- **Spotify：Schultzberg, Ankargren & Frånberg (2024)《Risk-aware product decisions in A/B tests with multiple metrics》**：指标分为 success、guardrail、deterioration、quality；guardrail 用**非劣效检验**（不期望提升、只需确认不劣于设定 margin）；决策规则：≥1 个 success 指标显著超优且所有 guardrail 通过非劣效检验（扩展版还要求 deterioration/quality 检验无失败）；**非劣效 guardrail 的 α 不需多重校正（因为要求"全部通过"是交集-并集结构），但 β（II 类错误）需按 guardrail 数量校正**才能保持期望功效；"无变化"状态在非劣效检验中属于备择假设、在超优检验中属于零假设 —— [arXiv 2402.11609](https://arxiv.org/abs/2402.11609); [Spotify Engineering 2024-03](https://engineering.atspotify.com/2024/3/risk-aware-product-decisions-in-a-b-tests-with-multiple-metrics)。
- Benavoli et al. (2017) 的 ROPE 给出"实际等价"的贝叶斯版本：直接输出 P(Δ∈ROPE) —— [JMLR](https://www.jmlr.org/papers/v18/16-305.html)。
- Booking.com：本次检索**未找到**其公开的非劣效检验方法文档；仅有二手资料称其早期质量看板中约 80% 实验缺少功效计算 —— [atticusli 博客（二手）](https://atticusli.com/blog/posts/how-booking-com-runs-experimentation/)。
- Hanley & McNeil (1983)：配对相关可显著提高 AUC 比较的功效，是 AUC 差样本量计算的基础 —— [PubMed](https://pubmed.ncbi.nlm.nih.gov/6878708/)；Obuchowski (1997) 讨论了聚类设计的样本量 —— [摘要](https://www.bohrium.com/paper-details/nonparametric-analysis-of-clustered-roc-curve-data/812073859254583296-922)。

### Inferences（推荐公式与协议）
- **MDE（单侧 α，功效 1−β）**：MDE = δ_min + (z_{1−α} + z_{1−β})·SE(Δ)，其中 SE(Δ) 由 bootstrap（含 seed 方差）估计。例：α=0.05 单侧、β=0.2 → MDE ≈ δ_min + 2.49·SE。若 δ_min=0.0005、SE=0.0003，则 MDE≈0.0012：真实增益 <0.0012 的特征有 >20% 概率被漏掉。
- SE 的规模律：SE ∝ 1/√(有效 cluster 数)，有效 cluster 数 = n_users / DEFF（DEFF = 1+(m̄−1)ρ，Rao-Scott/Obuchowski 思路）。可用一个 pilot 的 SE_0（n_0 用户）推算：所需用户数 n = n_0·(SE_0 / SE_target)²，SE_target = (MDE_target − δ_min)/(z_{1−α}+z_{1−β})。
- **四分区决策（建议替代当前二元判定，解决 R4）**：设 Δ_eq（等效界，≈δ_min 或业务 SESOI），用 (1−2α) 双侧 CI [L,U]：
  1. L > δ_min → **准入（超优）**
  2. −Δ_eq < L 且 U < Δ_eq → **等效/无实质增益**（TOST 成立，可"确认无增益"，从候选池淘汰）
  3. U < 0 → **有害**
  4. 其他 → **不确定（underpowered）**：报告 MDE，进入"加数据/加窗口/多 seed"复评或等待队列，而不是标记为"无增益"。
- **下线（非劣效）**：H0: Δ_remove ≤ −Δ_NI（去掉特征使 AUC 下降超过 margin）；当 (1−α) 单侧 CI 下界 > −Δ_NI 即可安全下线。Δ_NI 应 ≤ 准入 δ_min（否则会出现"刚准入的特征立即可下线"的不一致）；且多个特征**同时下线**时需对**联合移除**做一次非劣效检验（单个非劣不代表合计非劣），或按 Spotify 思路对 β 做 Bonferroni 校正以保证功效。
- 多 proxy：准入用 OR 规则（任一 proxy）时需 α 校正；有害判定用 AND（所有 proxy 上界<0）天然保守（intersection-union test，无需校正）；非劣效下线应要求**所有 proxy 都非劣**（IUT，同样不需 α 校正，但需 β 校正）。

### Gaps
- 未找到 Microsoft ExP / Booking 公开的非劣效 margin 设定方法；Spotify 博客全文未完全读取，margin 设定细节未核实。
- 没有找到专门针对 ΔAUC 的现成 MDE 表；需内部用 bootstrap SE 计算。

## Q5. 多候选特征的多重比较控制；共享验证数据的选择偏差（R3）与赢家诅咒

### Takeaway
批量筛选 = 大规模多重检验：对每批用 BH（或在相依下用 BY）控制 FDR；跨批次连续到来的候选适合 online FDR（alpha-investing → LORD/SAFFRON），Foster-Stine 系的 streamwise feature selection 本身就是为"特征逐个到来"设计的。被选中特征的观测 ΔAUC 系统性高估（winner's curse），应在独立数据上确认或做经验贝叶斯收缩；L1/L2 共用验证日违反"选择与评估独立"，需要数据拆分或 holdout 重估。

### Cited Findings
- Benjamini & Hochberg (1995, JRSS-B) BH 程序在独立/PRDS 下控制 FDR；Benjamini & Yekutieli (2001, Ann. Stat. 29:1165–1188) 在任意相依下将阈值除以 Σ_{i=1}^m 1/i 仍控制 FDR —— 经典文献 [未在本次会话核实全文]（BH: https://doi.org/10.1111/j.2517-6161.1995.tb02031.x ；BY: https://doi.org/10.1214/aos/1013699998 ）。
- **Zhou, Foster, Stine & Ungar (2006, JMLR 7)《Streamwise Feature Selection》**：特征逐个生成、每个只评估一次；提出 information-investing 与 **α-investing**，动态调整加入新特征所需的误差下降阈值，提供 FDR 型防过拟合保证 —— [JMLR v7/zhou06a](https://jmlr.org/papers/v7/zhou06a.html)。
- **Javanmard & Montanari（arXiv 1502.06197; Ann. Stat. 2018）**：提出 **LOND、LORD**，首次在在线设定下控制 FDR（Foster-Stine α-investing 仅控制 mFDR）；推广的 generalized alpha-investing 类在真零 p 值独立时控制在线 FDR，并扩展到 FDX —— [arXiv 1502.06197](https://arxiv.org/abs/1502.06197)。
- **Ramdas, Zrnic, Wainwright & Jordan (2018, ICML)《SAFFRON》**：在线版 Storey-BH，估计真零比例，自适应分配 α-wealth，功效优于 LORD；α_k 只能依赖过去 p 值 —— [arXiv 1802.09098](https://arxiv.org/abs/1802.09098); [PMLR v80](https://proceedings.mlr.press/v80/ramdas18a.html)。Fisher (2021) 将 LORD/SAFFRON 的 FDR 控制推广到非负相依，并指出 α-investing/LORD/SAFFRON 在任意相依下控制 mFDR —— [arXiv 2110.08161](https://arxiv.org/pdf/2110.08161v1)。
- **Johari, Pekelis, Walsh (2015 arXiv; Operations Research 2022 with Koomen)《Always Valid Inference》**：持续监控时传统 p 值/CI 失效；提出 always-valid p 值与 CI，可在任意停止时间保持有效，并用于序贯情形的多重检验控制；已在 Optimizely 落地 —— [arXiv 1512.04922](https://arxiv.org/abs/1512.04922)。
- **Airbnb：Lee & Shen (KDD 2018)《Winner's Curse: Bias Estimation for Total Effects of Features in Online Controlled Experiments》**：只上线显著正向实验时，被选中实验的观测效应系统性高估真实效应；修正方法为从观测 lift 中减去一个偏差项；验证需要 holdout —— [Airbnb Engineering 博客](https://medium.com/airbnb-engineering/selection-bias-in-online-experimentation-c3d67795cceb); [KDD 2018 讲座](https://videolectures.net/kdd2018_lee_curse_estimation)。Gelman 博客批评其本质是"显著性过滤"，建议多层模型替代 —— [statmodeling](https://statmodeling.stat.columbia.edu/?p=36203)。
- **Microsoft：Deng et al. (KDD 2021)《On Post-selection Inference in A/B Testing》**：post-selection 偏差（winner's curse）；提出经验贝叶斯方法（如零/高斯/拉普拉斯三成分混合先验的 Ghidorah）与实验拆分+回归方法 —— [Microsoft PDF](https://microsoft.com/en-us/research/uploads/prod/2021/06/PostSelectionKDD2021.pdf)。Azevedo, Deng, Montiel Olea & Weyl (AEA P&P 2019)：大量特征 A/B 测试的"赢家"是好特征与运气好的抽样之和，经验贝叶斯是分离二者的标准方法 —— [PDF](https://eduardomazevedo.github.io/papers/azevedo-et-al-ab-pnp.pdf)；Azevedo et al. (JPE 2020)《A/B Testing with Fat Tails》强调效应分布厚尾 —— [检索摘要](https://academicnewsletter.sufe.edu.cn/info/345894)。

### Inferences（建议协议）
- **批内**：每个候选计算单侧 p 值 p_j（H0: Δ_j ≤ δ_min；可用 bootstrap 分布中 ≤δ_min 的比例），对整批做 BH（q=0.1 等）；因候选间共享验证数据、p 值正相关（PRDS 通常近似成立），BH 一般可用；保守用 BY。多 proxy OR 规则：每个特征取 min(p_LGBM, p_LR)×2（Bonferroni）作为该特征 p 值再进 BH。
- **跨批（持续上新）**：用 LORD++/SAFFRON 维护 α-wealth（在线 FDR），避免"每批 α=0.05 → 长期累积大量假阳性"；与 Zhou-Foster-Stine 的 streamwise 设定天然契合。
- **R3（L1/L2 共用验证日）**：用同一数据既做筛选又做最终效应估计 → 选择偏差（winner's curse）。选项：(a) **样本拆分**：按 user（或按日）把验证集分为 screening 与 confirmation 两半，L1 只用前半筛选，L2 在后半给无偏 CI；(b) L2 用**新的、时间上更晚的**窗口（同时检验时间稳定性）；(c) 不能拆分时，对报告的 ΔAUC 做经验贝叶斯收缩：Δ̂_j^{EB} = μ + (τ²/(τ²+SE_j²))·(Δ̂_j − μ)，其中 μ、τ² 由整批所有候选（含未选中者）的 Δ̂ 分布估计（Deng 2021/Azevedo 2019 思路）。
- 若在 L1 中采用"看到不确定就加数据再看"，属于序贯监控，需 always-valid CI 或 alpha-spending，否则 I 类错误膨胀（Johari et al.）。

### Gaps
- 未找到在"离线特征筛选"语境下（而非线上 A/B）直接应用 LORD/SAFFRON 的工业案例；Zhou et al. 是最接近的学术先例。
- Airbnb 偏差项的精确公式未从原文核实。

## Q6. 滚动多窗口评估：跨时间窗口聚合、多目标、联合确认顺序（R9）

### Takeaway
将每个时间窗口的 Δ_w 及其 SE_w 视为一个"研究"，做 meta-analysis：固定效应（逆方差加权）给出合并估计，随机效应（DerSimonian-Laird）+ I² 量化跨窗口异质性；准入应基于随机效应合并的 CI（推广到未来窗口），并辅以方向一致性要求。多目标与多窗口的"联合确认"可用闭合/门控（gatekeeping）程序预先定义顺序。

### Cited Findings
- DerSimonian & Laird (1986, Controlled Clinical Trials 7:177–188) 随机效应 meta-analysis；Higgins & Thompson (2002, Stat Med 21:1539–1558) 提出 I² 量化异质性 —— 经典文献 [未在本次会话核实全文]（https://doi.org/10.1016/0197-2456(86)90046-2 ；https://doi.org/10.1002/sim.1186 ）。
- Lakens (2017) 的 TOST 框架明确覆盖 meta-analysis 场景（对合并效应做等效检验）—— [PMC5502906](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906)。
- Spotify 2024：多指标决策中，"所有 guardrail 都必须通过"的结构不需 α 校正但需 β 校正；success 指标间（任一显著即可）需 α 校正 —— [arXiv 2402.11609](https://arxiv.org/abs/2402.11609)。
- Bouthillier et al. (2021) 推荐对多种变异源随机化而非固定单一切分 —— [arXiv 2103.03098](https://arxiv.org/abs/2103.03098)。

### Inferences（建议协议）
- **合并**：Δ̄_FE = Σ w_w Δ_w / Σ w_w，w_w = 1/SE_w²；SE_FE = (Σ w_w)^{-1/2}。异质性 Q = Σ w_w(Δ_w − Δ̄)²，τ²_DL = max(0, (Q−(K−1))/(Σw − Σw²/Σw))，随机效应权重 1/(SE_w²+τ²)。注意：滚动窗口若**训练集重叠/验证期相邻**，各窗口 Δ_w 正相关，逆方差合并会低估 SE —— 应使用不重叠验证窗口，或在 bootstrap 中把多个窗口一起按 user 重抽样后直接计算合并统计量（自动包含窗口间相关）。
- **一致性要求**：除合并 CI 下界 > δ_min 外，可要求 ≥ k/K 个窗口点估计 > 0（方向一致），并在 I² 高时标为"不稳定"进入人工复审；这对应"时间稳健性"而非显著性，不应再作为第二个显著性检验（否则功效被重复消耗）。
- **多目标（如 CTR、CVR 多个 label）**：预先指定 primary 目标（超优检验，承担 α）与 secondary/guardrail 目标（非劣效检验，"全部通过"→ 无需 α 校正但需 β 校正）；若希望"任一目标超优即准入"，则对 primary 集合用 Holm/Bonferroni 或 BH。
- **联合确认顺序（固定序列/gatekeeping）**：预注册顺序，例如：① 主目标、合并窗口超优（α 全额）→ 通过后 ② guardrail 目标非劣效（IUT）→ ③ 跨窗口一致性/异质性检查（描述性）→ ④ 独立 confirmation 数据（R3 拆分后的另一半或更晚窗口）上复现 CI 下界 > 0。固定序列程序在前一步不拒绝时停止，可保证 FWER = α 而无需对每步再分 α。
- 不建议"每个窗口都要求显著"（K 个窗口的 AND 规则会使功效 ≈ power^K，严重漏检），也不建议"任一窗口显著即可"（OR 规则 α 膨胀约 K 倍）。

### Gaps
- 未检索到 ML 特征评估领域关于"滚动窗口 meta-analysis"的专门论文；以上协议为将生物统计 meta-analysis 与多重检验 gatekeeping 方法迁移到本场景的推断。
- 窗口间相关性下逆方差合并的修正（如 robust variance estimation, Hedges et al. 2010）未在本次检索中核实。
