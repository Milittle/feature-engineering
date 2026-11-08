# 增量特征评估的统计协议（第二轮：原文核验 + 可落地协议）

> 范围：判断候选特征在 proxy 模型（LightGBM + LR）上是否有增量预测价值，给出四种结论之一：优效 / 等效（无实质增量）/ 有害 / 功效不足；覆盖 clustered Poisson bootstrap、训练随机性（seed / 训练样本）方差、MDE、多重比较、选择偏差（R3）、滚动窗口与多目标（R9）。
> 对照对象：`docs/总体方案设计.md` §3.2；原型 `feval/l2.py`（`paired_bootstrap` / `decide` / `confirm_jointly`）；第一轮笔记 `research_notes/特征前置评估业界调研/02_statistics_incremental_evaluation.md`。
> 标记约定：**[已核原文 + 位置]**：本次会话下载全文并读到对应段落；**[更正]**：第一轮表述有误或不精确，这里给出正确版本；**[仍未核]**：没拿到全文（付费墙或被拦），只能依据摘要或二手转述；**[设计推断]**：作者把文献结论迁移到本场景，不是文献原话。
> 全文来源：PMC HTML（Demler、Pepe、Lakens）、arXiv PDF（Bouthillier、Spotify、Johari、SAFFRON、LORD）、JMLR PDF（Zhou、Benavoli）、Google Research PDF（Chamandy）、Microsoft PDF（Deng 2021）、cnsgenomics 镜像 PDF（Kerr 2014）。Airbnb Lee & Shen 原文（ACM DL、Medium）被拦截，Nadeau & Bengio 原文（Springer / NeurIPS）没能取到 PDF。

---

## Q1. 第一轮引用的核验结果（逐条）

### Takeaway
第一轮的大部分表述与原文一致，但有 5 处需要更正或加限定条件：(a) Demler 2012 的结论限于**同一数据上建模和评估**（样本内）的嵌套模型；(b) Bouthillier 的 "51×" 是相对于"每次重跑超参搜索"的理想估计量节省的算力，**不是**相对单 seed 的节省；(c) Spotify 的 power 校正是 **β/(G+1)**，不是 β/G，且优效指标用 **α/S**；(d) Zhou et al. 的 α-investing 给出的是 mFDR 型保证，文中默认参数 W0 = αΔ = 0.5；(e) Airbnb 公式依然没能核到原文，只能通过 Deng 2021 的转述部分确认。

### Cited Findings
- **Demler, Pencina & D'Agostino 2012** [已核原文：Abstract；§2.3 图 1；§4；§7]：
  - 原文说的是"若新增预测变量与结局**无统计显著关联**，零分布非正态"，并把场景限定为 "models developed and validated on the same data"。在多元正态 + LDA 的模拟中（n=8261），金标准 F 检验的实际水平接近名义 0.05，DeLong 检验的实际水平仅 **0.001**。
  - 理论解释：嵌套模型在零假设下，ΔAUC 是**退化的广义 U 统计量**，渐近正态不成立。
  - 建议：先做关联检验，显著后再给 ΔAUC 的 CI。在备择假设下（非退化），DeLong CI 覆盖率良好；引 Obuchowski 等的研究称其优于 bootstrap 区间和 LR 区间。
  - 原文例子：舒张压 Wald p=0.01，DeLong p=0.47，ΔAUC=0.001 (0.0001, 0.0031)。
  - [PMC3684152](https://pmc.ncbi.nlm.nih.gov/articles/PMC3684152/)
- **Pepe, Kerr, Longton & Wang 2013** [已核原文：Abstract；§2 Theorem；§3–4 Table 1；Discussion]：
  - "无性能改进"的各类零假设等价于 H0: P(D=1|X,Y)=P(D=1|X)，唯一条件是 risk(X)、risk(X,Y) 的分布绝对连续。
  - i.i.d. 情形下 LRT 渐近最有功效。
  - 模拟（X 的病例均值 0.74、基线 AUC 0.7）：DeLong 与 percentile bootstrap 的 ΔAUC 检验在 100 病例 / 900 对照时 **size < 0.005**。在每个 bootstrap 样本中重新拟合系数的 "adjusted" 版本不那么保守，但仍然保守。
  - 结论原话："all currently available procedures for testing incremental value based on ΔAUC in the full dataset are unacceptably conservative"。建议用校准良好的模型并基于 β_Y 检验。
  - [PMC3625503](https://pmc.ncbi.nlm.nih.gov/articles/PMC3625503/)
- **Kerr et al. 2014, Epidemiology 25:114–121** [已核原文：Abstract；正文 NRI 分解与 CI 部分]：
  - category-free NRI 即使在独立验证数据上也会夸大增量。
  - 若要检验"无增量"，回归系数检验优于 NRI。
  - NRI 的 CI 应用 bootstrap，而非已发表的方差公式。
  - 两类 NRI 的事件 / 非事件组分即 ΔTPR / ΔFPR；不建议使用 ≥3 类 NRI。
  - 首选单数字增量摘要是 **net benefit 的改进**。
  - [Kerr PDF](https://cnsgenomics.com/data/teaching/SISG/module_10/Mod10_Session7Naomi/Resources/Kerr_NetReclassIndex.pdf)
- **Obuchowski 1997, Biometrics 53:567–578** [仍未核：期刊全文未取到]：只确认了 Cleveland Clinic 的 R 实现 `clusteredROC()` 以该文为依据，支持单条 ROC 和两条相关 ROC 的聚类分析，按 clusterID 聚类，并复现原文 MRA 例子（Table 3）——[clusteredROC help](https://www.lerner.ccf.org/quantitative-health/documents/clusteredROC_help.pdf)。design effect / 有效样本量的具体公式仍未核。
- **Chamandy, Muralidharan, Najmi & Naidu 2012**（投稿 Annals of Applied Statistics）[已核原文：§2 eq.(6) 后；§3；§5 实验]：
  - 把每条记录当独立样本"typically ignores positive correlation and leads to underestimation"（方差被低估）。
  - Poisson bootstrap：对每个单元抽 b 个独立 Pois(1) 权重 m_ij，复本统计量为 g(Σ m_ij X_i / Σ m_ij)。
  - "it is necessary to ensure that all fragments of data from the ith observation are given the same weight in each resample"，实现上**用单元 ID 的哈希为随机权重播种**。
  - 实验中记录单位是 query，"the correct exchangeable unit is the user"。
  - Poisson 与多项 bootstrap 的接近性及一致性有命题证明。
  - [Google Research PDF](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43157.pdf)
- **Bouthillier et al. 2021 (MLSys)** [已核原文：Abstract；§2 图 1；§3.3；§4.1；§5]：
  - **[更正] "51×"** 指：把"除超参搜索以外的所有变异源都随机化"的有偏估计量 FixedHOptEst(k,All)，比每个样本都重跑超参搜索的理想估计量 IdealEst 省 51 倍算力（原文：IdealEst(k=100) 1070 小时 vs FixedHOptEst(k=100) 21 小时），且在误差上最接近理想估计量。它**不是**"比单 seed 省 51 倍"。
  - 变异源："Bootstrapping data stands out as the most important source of variance"；模型初始化的方差一般不到数据 bootstrap 方差的 50%。
  - 建议 (§5)：随机化尽可能多的变异源；使用多次数据切分（out-of-bootstrap）。
  - 判据用 P(A>B) 并取 **γ=0.75**：percentile bootstrap CI 下界 > 0.5 视为"显著"，上界 > γ 视为"有意义"。模拟用 k=50 次数据切分。
  - [arXiv 2103.03098](https://arxiv.org/abs/2103.03098)
- **Nadeau & Bengio 2003** [仍未核原文；通过 Benavoli 2017 §2 转述核对]：
  - 修正 t 统计量 t = x̄ / sqrt(σ̂²(1/n + ρ/(1−ρ)))，ρ = n_te/n_tot，于是 ρ/(1−ρ) = n_te/n_tr，与第一轮写的 (1/J + n_te/n_tr) 一致。
  - Nadeau & Bengio 证明了不同折结果间的相关性不存在无偏估计量，ρ 是启发式取值。
  - Benavoli 的脚注指出，该启发式原本针对随机 train/test 划分，后来被普遍用于 k-fold。
  - [JMLR 16-305 PDF](https://www.jmlr.org/papers/volume18/16-305/16-305.pdf)
- **Benavoli et al. 2017** [已核原文：§2 eq.(1)(2)；§3 ROPE 例子]：correlated t 检验的贝叶斯版本给出 μ 的后验 Student 分布；以 ROPE [−0.01, 0.01] 为例，输出 P(左) / P(ROPE) / P(右) 三个概率——同上链接。
- **Lakens 2017** [已核原文：Introduction；TOST 节；Power 节 eq.(5)]：
  - NHST + 等效检验组合后有四种结果。
  - 可用 90% CI（α=0.05 时）代替两个 p 值。
  - 假设真实效应为 0 时，等效检验的样本量为 n = 2(z_α + z_{β/2})²/Δ²（来自 Chow, Shao & Wang 2002；注意用的是 **β/2**）。
  - [PMC5502906](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)
- **Schultzberg, Ankargren & Frånberg 2024 (Spotify)** [已核原文：Lemma 3.1、3.2；Decision Rule 1；Proposition 3.1]：
  - Lemma 3.1（UI，"任一拒绝即拒绝"）：每个检验用 α/M、power 1−β。
  - Lemma 3.2（IU，"全部拒绝才拒绝"）：每个检验用 α、power **1−β/M**。
  - Decision Rule 1：至少一个 success 指标显著优效 **且** 所有 guardrail 显著非劣。
  - **Proposition 3.1 [更正]**：G 个 guardrail 各用水平 α、按 power 1−β/(G+1) 设计；S 个 success 指标各用水平 **α/S**、同样按 power 1−β/(G+1) 设计。这样整个规则的 I/II 类错误分别 ≤ α、β。"+1" 来自把"至少一个 success"当作一个合成假设。
  - deterioration / quality 指标属于扩展规则（Decision Rule 2），本次未逐行核对其精确校正。
  - [arXiv 2402.11609](https://arxiv.org/abs/2402.11609)
- **Zhou, Foster, Stine & Ungar 2006** [已核原文：Fig.4 算法；§5；§6 开头]：
  - α-investing：初始 w1 = W0；第 i 个特征的阈值 α_i = w_i/(2i)；若 p < α_i 则入选，财富更新为 w_{i+1} = w_i + αΔ − α_i，否则 w_{i+1} = w_i − α_i。
  - 检验统计量为 Δlog-likelihood（等价于 t 统计量）。
  - "two user-adjustable parameters, αΔ and W0 … we set both of them to 0.5"。
  - 文中称控制 "FDR"，但其保证形式见 Javanmard & Montanari：α-investing 控制的是 mFDR。
  - 原文有笔误："added to the model if its p-value is greater than α"，与算法框图矛盾，应为 "less than"。
  - [JMLR zhou06a](https://jmlr.org/papers/volume7/zhou06a/zhou06a.pdf)
- **Javanmard & Montanari (LORD/LOND)** [已核原文：Abstract]：LOND 与 LORD 在线控制 FDR 与 mFDR，另有 LOND 的调整版应对任意相关——[arXiv 1502.06197](https://arxiv.org/abs/1502.06197)。
- **Ramdas et al. 2018 SAFFRON** [已核原文：§2.3、§4]：
  - 参数：目标 FDR α，常数 **λ（默认 1/2）**，初始财富 **W0 < α**，正的非增序列 γ_j（和为 1）。
  - 首个阈值 α1 = min{(1−λ)γ1W0, λ}；只有 p ≤ λ 的"候选"才可能被拒绝，候选不消耗财富。
  - 实验中 LORD 用 γ_j ∝ log(j∨2)/(j·e^{√log j})（对高斯均值渐近最优）；SAFFRON 用更激进的 γ_j ∝ j^{−s}（s>1）。
  - FDR 保证要求零假设 p 值相互独立。
  - [arXiv 1802.09098](https://arxiv.org/abs/1802.09098)
- **Johari, Pekelis & Walsh（Always Valid Inference）** [已核原文：§5 eq.(7)–(9)；§7 BH-G]：
  - mSPRT：Λ_n^H(s_n) = ∫ f_θ(s_n)/f_θ0(s_n) dH(θ)，首次 Λ_n ≥ 1/α 时拒绝。最优混合分布应与效应先验"匹配"，且性能对设定误差较稳健。
  - 文中写出任意相关下的 BH 版本（BH-G）：p_(j) ≤ αj/(m·Σ_{r=1}^m 1/r)，即 Benjamini-Yekutieli。
  - [arXiv 1512.04922](https://arxiv.org/abs/1512.04922)
- **Deng et al. KDD 2021** [已核原文：§1 图 1；§2.1–2.3；§6 表]：
  - 图 1：1026 个实验做随机 A/B 二分，在 A 半边按 p<0.1 选出 168 个；B 半边无偏，B 对 A 回归显示选择偏差。
  - CMLE（Reid et al.）方程：Δ−μ = σ[φ((K−μ)/σ) − φ((−K−μ)/σ)] / [Φ((−K−μ)/σ) + 1 − Φ((K−μ)/σ)]。
  - **Remark 1：Lee & Shen（Airbnb）用的是边际期望 E[(Δ−μ)1{|Δ|>K}] 且只迭代一步，因此只能校正"一组被选实验的合计效应"，不能逐个校正。**
  - 高斯先验 EB 得到 James-Stein 线性收缩，收缩因子依赖样本量；先验尾部比高斯更厚时，对大效应的收缩更小。
  - 实证中 Ghidorah（三成分混合先验）在 RMSE 与 CI 覆盖率上最好，Huber / LaplaceFitGhidorah 次之；线性 RwES 在样本量差异大时表现差。
  - [Microsoft PDF](https://www.microsoft.com/en-us/research/uploads/prod/2021/06/PostSelectionKDD2021.pdf)
- **Lee & Shen KDD 2018 (Airbnb)** [仍未核：ACM DL 与 Medium 均被拦]：只能通过 Deng 2021 Remark 1 确认其方法性质（边际期望、一步校正、作用于合计效应）。常见的二手公式 Bias ≈ Σ_{i∈sel} σ_i·φ((Δ̂_i − b_i)/σ_i)（b_i 为显著性阈值）**未能核对**，不要直接引用。

### Inferences
- [设计推断] Demler / Pepe 的"ΔAUC 检验极保守"针对的是**样本内**嵌套比较。我们的情形是在 train 上拟合、在时间外推的 valid 上评估。给定已训练的两个模型，valid 上的 Δ 是"这两个已拟合模型差异"的无偏估计，退化 U 统计量问题不完全成立。但对噪声特征，with/without 模型几乎相同，ΔAUC 的分布仍会高度集中在 0 附近且偏斜，percentile CI 的覆盖率要用负对照实测。这正是设计 §7.1 负对照校准的意义。

### Gaps
- Obuchowski 1997 的聚类方差公式、Nadeau-Bengio 原文、Airbnb 偏差公式没能核到原文。Benjamini-Yekutieli 2001 的 PRDS 结论（多元正态单侧检验、非负相关时满足 PRDS）只通过 Johari 文中的 BH-G 形式间接核对，PRDS 条件本身仍未核。

---

## Q2. 检验统计量、配对 clustered Poisson bootstrap 的正确做法、训练随机性方差

### Takeaway
主检验统计量用**配对的逐样本 ΔLogLoss**（可加、cluster 和近似正态、对应 LRT 精神）；ΔAUC / ΔGAUC 作为同一组 bootstrap 权重下的效应量与 CI。`l2.py` 目前对 with/without 共用同一权重矩阵，配对正确。但 LightGBM 用了默认的 subsample=1 和 colsample=1，**换 seed 几乎没有方差**，真正漏掉的是**训练样本的抽样方差**，应通过"按 user 对训练集做 Poisson 重加权后重训 R 次"来覆盖，并用 Var_total = V_eval + s²_train/R 合并。

### Cited Findings
- 逐 cluster 同权、权重由 cluster ID 哈希生成，是 Poisson bootstrap 在流式 / 分布式实现中保持一致性的要求；正确的可交换单元是 user — [Chamandy et al. §3, §5](https://static.googleusercontent.com/media/research.google.com/en//pubs/archive/43157.pdf)。
- LRT（逐样本对数似然差的和）在 i.i.d. 下渐近最有功效；ΔAUC 检验功效低——[Pepe 2013 §3](https://pmc.ncbi.nlm.nih.gov/articles/PMC3625503/)。α-investing 的特征检验统计量就是 Δlog-likelihood——[Zhou 2006 Table 3](https://jmlr.org/papers/volume7/zhou06a/zhou06a.pdf)。
- 数据抽样（bootstrap）是最大的方差来源，模型初始化方差一般不到它的 50%；各方差源不独立，不能简单相加——[Bouthillier 2021 §2](https://arxiv.org/abs/2103.03098)。
- 随机化更多变异源可以降低对期望性能估计的误差（与 bagging 的方差缩减相关）——[Bouthillier 2021 §5](https://arxiv.org/abs/2103.03098)。
- 训练集重叠导致朴素 t 检验低估方差；修正项为 n_te/n_tr——[Benavoli 2017 §2 转述 Nadeau-Bengio](https://www.jmlr.org/papers/volume18/16-305/16-305.pdf)。

### Inferences
**对 `feval/l2.py` 现状的判读** [设计推断，基于读代码]：
1. `paired_bootstrap` 中 `W = C[:, g]` 同时用于 `p_exp` 与 `p_base` 的 AUC 和 logloss，配对正确。ΔLogLoss 复本 = `W @ ll_gain / W.sum()`，是正确的比率估计量。加权 AUC 以 W·y、W·(1−y) 作为正负样本权重，正负样本对的权重等于 w_i·w_j，对应"整个 user 被复制 m 次"。✔
2. 权重目前用 `np.random.default_rng(seed)` 按 `np.unique(groups)` 的顺序生成。迁到 Spark 后，应改为 `hash(user_id, b)` 播种（Chamandy 做法），以保证跨候选、跨窗口、跨代理**使用同一组权重**。这是后面联合 bootstrap（多重比较、窗口合并）的前提。
3. `lgb_scores` 中 `random_state=0, deterministic=True`，且未设 `subsample/colsample_bytree`（LightGBM 默认 1.0），所以换 seed 基本没有方差。LR 是凸优化，本来就没有 seed 方差。因此"seed variance"在本原型里≈0；**真正缺的是训练样本方差**（设计 §3.2.2 也承认 bootstrap 只覆盖验证集）。
4. 使用 2.5/97.5 percentile 的 CI：每个代理是单侧 α=0.025。B=1000 时尾部只有约 25 个点，p 值分辨率是 0.001，对后面的 BH 不够（见 Q4）。

**推荐的方差模型**：
- 记 r=1..R 为训练端的重复。每次对训练集做 user 级 Poisson(1) 重加权（LightGBM / LR 都支持 sample_weight），或若打开 bagging 则同时换 seed（Bouthillier"随机化多源"）。同一 r 内 with / without **使用同一训练权重和同一 seed**（配对）。
- 每个 r 在 valid 上得到 Δ_r；评估端用共享的 B 组 user 权重得到 Δ_{r,b}。
- 点估计 Δ̄ = mean_r Δ_r。
- 评估端方差 V_eval = Var_b(mean_r Δ_{r,b})：先在每个复本内对 r 求平均，再取方差，自动包含 r 之间的相关。
- 训练端方差 s²_train = Var_r(Δ_r)（valid 固定，只反映训练变异）。
- **SE_total² ≈ V_eval + s²_train / R**。CI 取 Δ̄ ± t_{ν,1−α}·SE_total，ν 用 Satterthwaite：ν ≈ SE_total⁴ / [(s²_train/R)²/(R−1) + V_eval²/∞]。
- 不建议"每个复本随机抽一个 r"：那样估计的是**单次训练**的方差（V_eval + s²_train），不是 R 次平均的方差，会过宽。只有决策对象是"单次训练结果"时才合适。
- 训练集与 valid 的 user 重叠：两端独立重加权近似把它们当作独立，会略微低估方差（同一用户在两端都出现）。更严谨的做法是两端使用**同一个 user 哈希**的权重（二者相乘）；工程上建议先做下面的 κ 校准。

**R 的取法（校准协议）**：
- 先用约 20 个候选（含负对照、正对照）跑 R=10，估计 κ = (s²_train/R=1) / V_eval。
- 若中位 κ < 0.1：生产用 R=1，SE 乘以 sqrt(1+κ̂_90%)（κ 的 90 分位）。
- 若 κ ≥ 0.1：生产用 R=3–5（s²_train 的自由度 2–4，配合 t 分位数）。
- R 再大的收益递减：R=5 时训练端方差只剩 1/5。
- 这条是设计推断，κ 的典型量级需要内部实测（第一轮 Gap 未解决）。

**主检验统计量的选择**：
- **ΔLogLoss**（= 每样本对数似然增益的均值，正 = 更好）作为主检验统计量。理由有三：它是 cluster 和的比率估计量，CLT 适用；与 LRT / α-investing 一致；对零效应的分布偏斜远小于 ΔAUC。
- 注意：样本外零效应时 E[ΔLogLoss] 略 < 0（过拟合代价），用于 H0: Δ ≤ δ_min 的检验偏保守但有效。
- ΔAUC 作为"报告和业务门槛"的效应量，CI 在同一组权重下计算。设计 §3.2.2 当前以 ΔAUC 为主指标判定；若保留 ΔAUC 为主，至少"有害"判定应同时要求 ΔLogLoss 上界 < 0。
- 注意 LR 代理的 ΔLogLoss 含校准成分。若两个模型校准差异大，可在 valid 上做 Platt 重校准后再算（会消耗 valid 自由度，需 cross-fit）；或只把 ΔAUC 作为判断"判别力"的辅助。

### Gaps
- 没有找到 GBDT proxy 上"训练端方差 vs ΔAUC 典型增益"的公开测量。user 同时出现在训练和验证时两端权重的严格处理，也没有找到文献。

---

## Q3. MDE、试点估 SE、四分区决策、非劣效 margin

### Takeaway
每次评估都要输出 MDE。"功效不足"与"等效"的区别在于：CI 上界是否已经低于业务关心的最小增益 Δ_eq（SESOI）。用 cluster 级线性化给出 SE ∝ 1/√n_c 的规模律，从一次试点外推需要的用户数。非劣效 margin 不大于准入门槛，并按 Spotify 的 β/(G+1) 设计 power。

### Cited Findings
- 等效检验在真实效应为 0 时的样本量：n = 2(z_α + z_{β/2})²/Δ²（每组；Chow, Shao & Wang 2002）；边界越窄所需样本越大——[Lakens 2017 eq.(5)](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)。
- 四种结果（等效且不异于 0 / 异于 0 且不等效 / 异于 0 且等效 / 不确定）——[Lakens 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)。
- 非劣效的零假设是"劣于 NIM"，"无变化"在非劣效检验里属于备择假设；IU 结构不校正 α、校正 β——[Spotify 2024 Table 2, Lemma 3.2](https://arxiv.org/abs/2402.11609)。
- 把 "P(A>B) 的 CI 下界 > 0.5" 定为"显著"、"上界 > γ=0.75" 定为"有意义"，区分"显著"和"有意义"两个维度——[Bouthillier 2021 §4.1](https://arxiv.org/abs/2103.03098)。

### Inferences（公式均为 [设计推断]）
- **SE 的 cluster 级线性化**（ΔLogLoss 是比率估计量 Σd_i/Σ1）：
  - 定义 D_c = Σ_{i∈c} d_i，m_c 为 user c 的样本数，d̄ = ΣD_c/Σm_c。
  - SE² ≈ Σ_c (D_c − d̄·m_c)² / (Σ_c m_c)²。
  - 它与 Poisson bootstrap 方差一致，可作为 sanity check，并可以免 bootstrap 快速计算 SE。
- **规模律**：SE ≈ σ_u / (m̄·√n_c)，n_c 为用户数。从试点（n_c,0 个用户，SE_0）外推：SE(n_c) = SE_0·√(n_c,0/n_c)。加上训练端方差后，SE_total² = V_eval(n_c) + s²_train/R，其中只有 V_eval 随评估用户数下降。**加评估数据压不掉训练端方差**，这是 R 必须 > 1 的另一个原因。
- **MDE**（单侧水平 α_1，power 1−β）：MDE = δ_min + (z_{1−α_1} + z_{1−β})·SE_total。
  - 现行设计：每个代理 α_1=0.025，β=0.2，乘子 z = 1.960 + 0.842 = **2.80**。
  - 若按 Bonferroni 把双代理 OR 规则的总 α 压到 0.025，则每个代理 α_1=0.0125，乘子 = 2.241 + 0.842 = **3.08**。
  - 例：δ_min=0、SE_total=4e-5（ΔLogLoss）时 MDE ≈ 1.1e-4。
- **反解所需用户数**：n_c = n_c,0·[SE_0 / SE_target]²，其中 SE_target = (Δ_target − δ_min)/(z_{1−α_1}+z_{1−β}) 先扣除训练端方差（若 s²_train/R 已超过 SE_target²，就只能加大 R）。
- **四分区决策**（单代理，用 (1−2α_1) 双侧 CI [L, U]；Δ_eq = SESOI ≥ δ_min）：

  | 结论 | 条件 | 含义 / 动作 |
  |---|---|---|
  | **优效（建议入模）** | L > δ_min | 若同时 U < Δ_eq，标"显著但小于 SESOI"，由业务决定 |
  | **有害** | U < 0（建议用 −δ_harm 而非 0，δ_harm 取一个很小的正数） | 拒绝 |
  | **等效 / 无实质增量** | L ≤ δ_min 且 U < Δ_eq | 可以"确认没有值得要的增益"，移出候选池（单侧"非优效"检验；若还要 L > −Δ_eq 才算严格的 TOST 等效） |
  | **功效不足** | 其他（U ≥ Δ_eq 且 L ≤ δ_min） | 报告 MDE 与所需 n_c / R；进入"加窗口 / 加 R"复评队列，**不得**记为"无增量" |

  - 双代理合并：优效 = 任一代理（OR，需 α 校正，见 Q4）。有害、等效 = **两个代理都满足**（IU，不校正 α）。功效不足 = 其余情况。
  - 合理的等效判定要求 Δ_eq ≥ (z_{1−α_1} + z_{1−β/2})·SE_total，即约 **3.24·SE**（α_1=0.025、β=0.2）。否则即使真实增益为 0，也大概率得到"功效不足"。所以 Δ_eq 应在批次开始前按 SE 预算定好，而不是事后挑选。
- **非劣效 margin（下线 §5.4、共享底座次目标 §3.2.3、交叉替代父特征 §3.4）**：
  1. Δ_NI ≤ δ_min（若 δ_min=0，则用 Δ_NI ≤ Δ_eq 的一个比例）。否则会出现"刚准入的特征立即可下线"的不一致。
  2. 用业务锚点：例如历史已上线特征 ΔAUC 中位数的 10–20%，或线上 A/B 能检测到的最小离线差异折算值。
  3. 同时检验 G 个约束（多个次目标 / 两个代理）时，按 Spotify Prop 3.1 每个用 α、power 1−β/(G+1)，即 MDE 乘子中的 z_{1−β} 换成 z_{1−β/(G+1)}。例：G=2、β=0.2 → z_{0.933}=1.50，乘子变为 1.96+1.50=3.46。
  4. 批量下线必须对**联合移除**再做一次非劣效检验。

### Gaps
- 文献没有给出 ΔAUC / ΔLogLoss 的 SESOI 取值，只能内部用"离线 Δ → 线上 A/B lift"的历史对应关系来标定（建议纳入设计第 8 章待定项）。

---

## Q4. 多重比较：批内 BH vs BY、双代理 OR 规则、跨批 online FDR

### Takeaway
批内（10–100 个候选）用 BH 控制 FDR；由于候选共享 valid 与基线，统计量通常正相关，BH 一般可用，BY 作为敏感性分析（代价是阈值除以 H_m：m=10 时 2.93，m=100 时 5.19）。更好的做法是利用"同一组 user 权重"的联合 bootstrap 直接得到相关结构。双代理 OR 规则先在特征内用 Simes / Bonferroni 合并成一个 p 值再进 BH。跨批：每批已控制 FDR 时，长期累积问题比 FWER 小得多；只有逐个到达、逐个决策时才需要 LORD / SAFFRON。

### Cited Findings
- BH-I：p_(j) ≤ αj/m；任意相关下 BH-G：p_(j) ≤ αj/(m·Σ1/r)——[Johari et al. §7](https://arxiv.org/abs/1512.04922)。
- UI 结构（任一通过即通过）每个检验需 α/M——[Spotify Lemma 3.1](https://arxiv.org/abs/2402.11609)。
- α-investing：α_i = w_i/(2i)，入选后 +αΔ−α_i，否则 −α_i，默认 W0 = αΔ = 0.5（原文实验）——[Zhou 2006](https://jmlr.org/papers/volume7/zhou06a/zhou06a.pdf)。
- SAFFRON：λ=1/2 默认，W0 < α，γ_j ∝ j^{−s}（s>1）；LORD 的渐近最优序列 γ_j ∝ log(j∨2)/(j e^{√log j})；FDR 保证需要零假设 p 值独立——[Ramdas et al. 2018 §2.3, §4](https://arxiv.org/abs/1802.09098)。LOND 有任意相关的调整版——[Javanmard & Montanari](https://arxiv.org/abs/1502.06197)。
- α-investing / LORD / SAFFRON 在任意相关下控制 mFDR（第一轮引用的 Fisher 2021）——[arXiv 2110.08161](https://arxiv.org/pdf/2110.08161v1) [仍未核：本轮未重读]。

### Inferences [设计推断]
- **p 值来源**：percentile bootstrap 的 p 值分辨率是 1/B，BH 在 m=100、q=0.1 时最小阈值 0.001，B=1000 不够。建议用正态近似 p_j = 1 − Φ((Δ̂_j − δ_min)/SE_total,j)，CI 与 p 值都基于 SE_total（含训练端方差）；或者 B ≥ 10·m/q（m=100 时 10000）。
- **双代理合并**：每个特征 p_j = min(1, 2·min(p_lgb, p_lr))（Bonferroni），或 Simes：min(2·min(p), max(p))（PRDS 下有效，两个代理正相关时成立）。合并后进 BH。这把设计 §3.2.1 的"误放率上界 5%"收回到名义 α。若坚持现行"每个代理 2.5%"，那么合并后的特征级 α 实际为 5%，应在报告中写明。
- **BH vs BY**：
  - Δ_j 之间的主要相关来自共同的 valid 样本与基线预测。同一用户权重扰动会使 "with j" 的增益同向波动，多为正相关，接近 PRDS 条件。互为替代的特征在单独评估时也是正相关。
  - 推荐**主用 BH(q=0.1)**，并定期用负对照批验证。
  - 若负对照显示批内 FDR 超标，切到 BY 或 **Romano-Wolf / Westfall-Young 的 max-T 步降**（利用共享权重的联合 bootstrap 复本 {Δ*_{j,b}}，精确反映相关结构，控制 FWER）[方法本身仍未核原文]。
- **跨批 / 在线**：
  1. FDR 是比例型指标。每批 BH(q) 控制批内 FDR，长期的假阳性占比仍约 ≤ q，不会像"每批 α=0.05 的 FWER"那样累积失控。所以按周成批评估时，**每批 BH 已经足够**。
  2. 只有当候选逐个到达、需要立即决定（streaming）时才用 online FDR。推荐 SAFFRON(α=0.1, λ=0.5, W0=α/2, γ_j ∝ j^{−1.6}) 或 LORD++（γ 用上面的渐近最优序列）。注意它们的 FDR 保证需要独立性；我们共享 valid，只能期待 mFDR。
  3. α-investing 的 W0=αΔ=0.5 是原文为特征选择实验设的值，作为 FDR 水平太宽松，生产应取 W0 ≈ αΔ ≈ q（例如 0.05–0.1）。
- **重复评估同一候选**（功效不足 → 加数据再评）属于序贯检验。要么预设最多 2 次查看，用 Bonferroni α/2 或 O'Brien-Fleming 分配；要么用 Johari 的 mSPRT 得到 always-valid p 值（正态混合先验的方差与历史 Δ 分布的方差匹配）。

### Gaps
- 离线特征筛选里使用 LORD/SAFFRON 的工业案例依然没找到；在共享 valid 的相关结构下，BH 的实际 FDR 只能靠负对照实测。

---

## Q5. 选择偏差（R3）：数据拆分、经验贝叶斯收缩、保留多少数据

### Takeaway
R3 最便宜的修法是**时间拆分**：L1 只用训练期的天（valid 日之前），L2 的 valid 日对 L1 完全不可见，L2 的功效零损失。若 L1 必须用最新数据，就按 user 哈希拆分（例如 30% 给 L1，70% 给 L2，L2 的 SE 会膨胀约 1.2 倍）。入选后报告的 Δ 用 EB 收缩去除赢家诅咒（只影响报告值，不影响判定）。`confirm_jointly` 在同一 valid 上"先按 Δ 排序再检验"，同样有选择偏差，应移到确认窗口上做。

### Cited Findings
- 选择偏差随信噪比降低而增大；拆分后未参与选择的那一半是无偏的——[Deng 2021 §1 图 1、§2.2](https://www.microsoft.com/en-us/research/uploads/prod/2021/06/PostSelectionKDD2021.pdf)。
- 高斯先验 EB 得到 James-Stein 收缩（收缩因子依赖样本量）；效应分布尾部比高斯厚时应使用厚尾或混合先验（Ghidorah 在实证中最好），对大效应几乎不打折——[Deng 2021 §2.3, §6](https://www.microsoft.com/en-us/research/uploads/prod/2021/06/PostSelectionKDD2021.pdf)。
- Airbnb 的校正针对"一组被选实验的合计效应"，不能逐个校正——[Deng 2021 Remark 1](https://www.microsoft.com/en-us/research/uploads/prod/2021/06/PostSelectionKDD2021.pdf)。

### Inferences [设计推断]
- **方案 A（推荐）：时间隔离。** L1 的 IV / 单特征 AUC 只在训练窗口天上计算；L2 的 valid 日（以及滚动窗口的所有 valid 日）不参与 L1。L2 的 CI 在"给定 L1 选择"的条件下有效（数据独立）。代价：L1 用的数据稍旧，对快速漂移的特征不太敏感。
- **方案 B：user 哈希拆分。** 比例 f 给 L1，1−f 给 L2，SE_L2 膨胀 1/√(1−f)：f=0.2 → 1.12×，f=0.3 → 1.20×，f=0.5 → 1.41×。L1 是单变量统计，噪声小，f=0.2–0.3 足够；MDE 随之按相同倍数增加。
- **`confirm_jointly`**：它按单独增量排序、贪心加入，每步在同一 valid 上做优效判定，既有选择偏差，又有多重检验（序列中前一步的结果影响后一步的基线）。建议在**确认窗口**（时间上更晚的 valid 日，或 L2 拆出的确认半边）上执行，而且只做一次"联合集合 vs 基线"的整体优效检验，再加逐个"去掉后非劣"的检验。
- **EB 收缩（只用于报告与排序）**：
  - Δ̂_j^EB = μ̂ + B_j·(Δ̂_j − μ̂)，B_j = τ̂²/(τ̂² + SE_j²)。
  - μ̂ 与 τ̂² 用整批（含未入选）候选的矩估计：τ̂² = max(0, Var_j(Δ̂_j) − mean_j(SE_j²))，μ̂ 取逆方差加权均值。
  - 若历史 Δ 分布厚尾（预计如此：少数特征大增益、多数接近 0），改用"点质量 0 + Laplace"混合先验（Ghidorah 思路），避免把真正的大增益压太狠。
- **保留多少数据**：以 L2 MDE 为约束反推。目标 MDE 决定所需 n_c（Q3 公式），valid 日总用户数减去 n_c 后的余量才能给 L1。若余量 < 20%，就采用方案 A。

### Gaps
- 文献没有"筛选 / 确认拆分比例"的最优理论值可以直接照搬；Deng 2021 的实验用的是 50/50 的伪重复。

---

## Q6. 滚动多窗口、多目标、联合确认顺序（R9）

### Takeaway
各窗口的 valid 日互不重叠，但训练集重叠、用户重叠，所以各窗口的 Δ_w 正相关，直接做逆方差合并会低估 SE。正确做法是**同一组 user 哈希权重贯穿所有窗口**，在每个 bootstrap 复本内计算合并统计量。准入用"合并 Δ 的优效"（固定效应：这几个窗口的平均）；异质性 I² 与符号一致性作为稳定性诊断，不做第二次显著性检验。窗口数取 4–6。多目标按预注册的门控顺序：主目标优效 → 次目标非劣（IU，β 按 Spotify 校正）→ 确认窗口复现。

### Cited Findings
- 全部通过型（IU）不校正 α、需校正 β；任一通过型（UI）需 α/S——[Spotify Prop 3.1](https://arxiv.org/abs/2402.11609)。
- 多次数据切分能提高比较的功效与可推广性——[Bouthillier 2021 §5](https://arxiv.org/abs/2103.03098)。
- TOST 适用于 meta-analysis 合并效应——[Lakens 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5502906/)。
- DerSimonian-Laird、I²、HKSJ 小样本修正——[仍未核原文；DL 1986 doi:10.1016/0197-2456(86)90046-2；Higgins & Thompson 2002 doi:10.1002/sim.1186]。

### Inferences [设计推断]
- **合并统计量**：第 w 个窗口的增益为 Δ_w。
  - 合并 Δ̄ = Σ_w n_w Δ_w / Σ n_w（按样本量加权，ΔLogLoss 等价于把各窗口 valid 拼起来求均值）。
  - 每个复本 b 用相同的 user 权重算 Δ̄*_b，CI 来自 {Δ̄*_b}，自动包含窗口间相关。
  - 训练端方差：每个窗口各自 R 次重训，s²_train 按窗口取平均后除以 (R·K_eff)。窗口的训练集高度重叠时 K_eff < K，保守起见取 K_eff = 1。
- **固定效应 vs 随机效应**：
  - 准入问的是"未来窗口上的期望增益"，严格来说对应随机效应 / 预测区间。但 K=4–6 时 τ² 的估计极不稳定（DL 在研究数少时低估 τ²）。
  - 因此判定用合并 Δ̄ 的 CI（固定效应），另外报告：(i) Cochran Q / I²；(ii) 正号窗口数 k⁺/K；(iii) 留一窗口的 Δ̄ 范围。
  - 若 I² > 50% 或 k⁺/K < 2/3，标"不稳定"，转人工复核，而不是自动入模。这一层不消耗 α。
- **窗口数与重叠**：
  - valid 日之间至少间隔成熟期，避免 label 窗口重叠。
  - K=4–6（例如按周取 4–6 个 valid 日）：合并 SE 约降为单窗的 1/√K（用户重叠时降得更少）。K 再大会引入更多分布漂移，收益递减。
  - 不要"每个窗口都显著"（power^K），也不要"任一窗口显著"（α 约放大 K 倍）。
- **多目标**：设计 §3.5 规定 gate 只看主目标列，其余列仅供参考，所以非 gate 列不需要 α 校正。若主目标有 S=2 个，"任一优效"用 α/2（UI）。共享底座的次目标非劣约束是 IU，不校正 α，但 power 按 1−β/(G+1) 设计。
- **预注册的门控顺序**（固定序列，前一步不通过即停止，总 FWER ≤ α）：
  1. 主目标、合并窗口、ΔLogLoss 优效（批内 BH）
  2. 主目标 ΔAUC 的 CI 下界 > δ_min_AUC（业务门槛，可选）
  3. 次目标非劣（IU）
  4. 稳定性诊断（描述性）
  5. 联合确认在确认窗口执行

### Gaps
- 没有找到 ML 特征评估中专门讨论"滚动窗口 meta-analysis"的文献；窗口间相关下的 robust variance（Hedges 2010）未核。

---

## Q7. 最终协议伪代码（汇总）

### Takeaway
下列伪代码把 Q2–Q6 合成一个可落地流程。所有"判定参数"（α、q、δ_min、Δ_eq、Δ_NI、R、K、B）在批次开始前写进口径卡或 ADR，事后不再调整。

### Cited Findings
- 协议中各组件的出处见 Q1–Q6：Poisson bootstrap 与哈希播种（Chamandy）、LRT / ΔLogLoss 优先（Pepe、Zhou）、多源方差（Bouthillier）、TOST / 等效（Lakens）、IU/UI 的 α/β 校正（Spotify）、BH-G（Johari）、选择偏差与 EB（Deng）、online FDR（SAFFRON/LORD）。

### Inferences [设计推断：伪代码]
```text
# ---------- 0. 预注册参数（每批固定） ----------
alpha1   = 0.025          # 每个检验的单侧水平
q        = 0.10           # 批内 FDR
beta     = 0.20
delta_min_LL, delta_min_AUC   # 优效门槛（负对照校准）
Delta_eq                       # SESOI；要求 Delta_eq >= 3.24*SE_budget
Delta_NI <= delta_min 或 业务锚点
R (由 κ 校准决定: 1 或 3~5),  K = 4~6 个 valid 日（间隔 ≥ 成熟期）,  B = 2000

# ---------- 1. 数据隔离（R3） ----------
valid_days = 最近 K 个成熟日（间隔 ≥ 成熟期）;  confirm_day = 更晚的一个成熟日（或 user 哈希的 30%）
L1 只能读 train_days（< min(valid_days)）
w_eval[u, b] = Poisson(1) seeded by hash(u, b)      # 所有候选/代理/窗口共享
w_train[u, r] = Poisson(1) seeded by hash(u, "train", r)   # r=1 时可全取 1

# ---------- 2. 逐候选 L2 ----------
for cand j in batch:
  for proxy k in {lgb, lr}:
    for window w in 1..K:
      for r in 1..R:
        base = fit(proxy k, train_w, features=F,       weights=w_train[:, r], seed=r)
        exp  = fit(proxy k, train_w, features=F+[j],   weights=w_train[:, r], seed=r)
        d_i  = logloss(base) - logloss(exp)          # 每样本增益
        D[j,k,w,r]   = mean(d_i);   A[j,k,w,r] = AUC(exp) - AUC(base)
        D*[j,k,w,r,b]= Σ w_eval[u_i,b] d_i / Σ w_eval[u_i,b]   # 同一权重，配对
        A*[...]      = weightedAUC(exp, w_eval) - weightedAUC(base, w_eval)
    # 合并窗口 & 重训
    Dbar[j,k]  = Σ_w n_w * mean_r D[j,k,w,r] / Σ n_w
    V_eval     = Var_b( Σ_w n_w * mean_r D*[j,k,w,r,b] / Σ n_w )
    s2_train   = mean_w Var_r( D[j,k,w,r] )            # R>1 时
    SE[j,k]    = sqrt( V_eval + s2_train / (R * K_eff) ) # K_eff 保守取 1
    p[j,k]     = 1 - Φ( (Dbar[j,k] - delta_min_LL) / SE[j,k] )
    CI[j,k]    = Dbar ± z_{1-alpha1} * SE   ;   同法给出 ΔAUC 的 CI（报告与业务门槛）
    MDE[j,k]   = delta_min_LL + (z_{1-alpha1} + z_{1-beta}) * SE
    hetero[j,k]= I², 正号窗口占比, 留一窗口范围
  p_j = min(1, 2*min_k p[j,k])          # 或 Simes；把 OR 规则的 α 收回名义水平

# ---------- 3. 批内多重比较 ----------
admit_set = BH(p_j, q)                 # 负对照超标时改 BY 或 max-T(联合 bootstrap)
# 跨批：每批 BH 即可；若流式逐个决策则用 SAFFRON(α=q, λ=.5, W0=q/2, γ_j∝j^-1.6)

# ---------- 4. 四分区判定 ----------
for j:
  if j in admit_set and (可选) 某个 proxy 的 ΔAUC 下界 > delta_min_AUC:   label = 优效
  elif all_k U[j,k] < 0  (U 取 ΔLogLoss；最好也要求 ΔAUC 的 U < 0):      label = 有害
  elif all_k U[j,k] < Delta_eq:                                           label = 等效/无实质增量
  else:                                                                   label = 功效不足 (报告 MDE、所需 n_c / R)
  if label==优效 and (I²>50% or 正号窗口<2/3):  label = 优效-不稳定(人工复核)

# ---------- 5. 多目标（门控顺序） ----------
主目标 gate（步骤 2~4）→ 次目标（共享底座）非劣: all_k L_NI[j,k] > -Delta_NI，power 按 1-β/(G+1) 设计
→ 非 gate 列仅报告

# ---------- 6. 联合确认（在 confirm_day 上，一次性） ----------
S = 通过者集合
检验 F+S vs F 优效（单次，α 全额）；对每个 s∈S 检验 "F+S−{s} vs F+S" 非劣（IU）→ 非劣者视为冗余，去掉
报告值：入选者 Δ 用 EB 收缩 Δ^EB = μ̂ + τ̂²/(τ̂²+SE²)(Δ̂−μ̂)（厚尾时用 0 点质量+Laplace 先验）

# ---------- 7. 校准与回归测试（每批） ----------
负对照（置换/随机特征）误放率 ≈ 名义 α（批内 FDR ≈ q）；正对照漏放率 ≈ β（对应 MDE 处的效应）
κ = s2_train / V_eval 的分布 → 决定下批的 R
功效不足者复评：最多再看 1 次，α 按 Bonferroni 一分为二（或用 mSPRT 的 always-valid p 值）
```

### Gaps
- 伪代码中的阈值（I²>50%、2/3 符号一致、f=0.3、K=4–6、R=3–5、SAFFRON 的 s=1.6）都是工程默认值，没有文献给出最优值，必须用负对照和正对照批次标定。
