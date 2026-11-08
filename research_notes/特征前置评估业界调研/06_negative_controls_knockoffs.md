# 负对照 / 随机噪声探针 / Knockoffs / 置换零分布：用于校准特征准入与控制假发现

> 调研范围：Boruta/BorutaShap、null importance(PIMP)、random probe、Model-X/fixed-X/deep/group knockoffs、流行病学负对照与经验校准(OHDSI)、A/A 测试、分组置换与可交换性、GBDT 对高基数/ID 类特征的记忆。
> 方法说明：本会话仅 WebSearch 可用，arxiv.org / core.ac.uk / feature-engine 文档等域名 WebFetch 被网络策略拦截，因此多数事实来自检索摘要与官方摘要页，未逐页核对全文。标注"[未在本会话核验]"的条目来自研究者既有知识，写报告时请复核。

---

## Q1. 基于"影子/探针/零重要性"的阈值方法：Boruta、BorutaShap、null importance(PIMP)、random probe

### Takeaway
所有这些方法的共同骨架是：构造"已知与目标无关"的特征（列置换的 shadow、随机生成的 probe、或置换 y 后的整套 null 重要性），用它们重要性的某个统计量（max / 分位数 / 均值+k·std / 经验 p 值）当准入阈值。它们只在"负对照与候选特征在边际分布与结构上同构、且模型对二者的偏置相同"时才是有效校准——这恰恰是我们 user 级常量随机特征失效的原因。

### Cited Findings
- **Boruta**（Kursa & Rudnicki, *J. Stat. Softw.* 36(11), 2010, doi:10.18637/jss.v036.i11）：RF 包装器，"迭代剔除经统计检验比随机探针（random probes）更不相关的特征"；shadow 由打乱原特征得到，每轮重新生成；输出记录每轮 shadow 的 max/mean/min 重要性 — [Boruta CRAN refman](https://cran.uni-muenster.de/web/packages/Boruta/refman/Boruta.html)；[rdrr Boruta](https://rdrr.io/cran/Boruta/man/Boruta.html)
- Boruta 用 Z 分数（平均精度损失/标准差）作重要性，但论文提醒该 Z 分布并非 N(0,1)，不能直接解释为显著性；决策参照"shadow 中最大 Z 值（MZSA）"，次级来源描述 — [ARFS 方法综述](https://arfs.readthedocs.io/en/latest/Methods%20overview.html)；[CRAN refman](https://ftp.fau.de/cran/web/packages/Boruta/refman/Boruta.html)。（细节：每轮特征 Z>MZSA 记一次 hit，对 hit 次数做二项检验 + Bonferroni，判 Confirmed/Rejected/Tentative —— [未在本会话核验全文]）
- **BorutaShap**：`percentile` 参数把阈值设为 shadow 重要性的某个分位数，默认 100 = 最大值（等价 R 版 Boruta）；文档明说"取 shadow 最大值作阈值有时非常保守"，降低 percentile 更宽松；`pvalue` 控制二项检验严格度；重要性可选 SHAP/gini/perm，作者推荐 SHAP — [BorutaShap PyPI](https://pypi.org/project/BorutaShap)
- **PIMP / null importance**（Altmann, Toloşi, Sander, Lengauer, *Bioinformatics* 26(10):1340–1347, 2010）：动机是 RF 重要性偏好多类别的类别变量；做法是多次置换 y、重训模型得到每个特征的零重要性分布，再给出 p 值（可拟合正态/对数正态/伽马或非参数）；用 PIMP 筛出的特征重建 RF 精度更好 — [PubMed 20385727](https://pubmed.ncbi.nlm.nih.gov/20385727/)
- ranger 实现了 Altmann 方法：`importance_pvalues(method="altmann")` — [ranger importance_pvalues](https://www.quantargo.com/help/r/latest/packages/ranger/0.12.1/importance_pvalues.html)
- **Kaggle null importance**：源自 Kaggle notebook "Feature Selection with Null Importances"（置换 target 构造零重要性分布、与真实重要性比较；优点是不破坏特征间交互）；被 2018 Home Credit 金牌第 10 名方案采用；`target-permutation-importances` 包用实际与随机运行重要性间的 Wasserstein 距离等打分，其自报基准：RandomForestClassifier 10/10 数据集优于内置重要性，XGBRegressor 7/12（作者自测，非独立验证） — [target-permutation-importances docs](https://target-permutation-importances.readthedocs.io/en/latest/)；[PyPI](https://pypi.org/project/target-permutation-importances/1.0.19/)。（notebook 作者常被认为是 Olivier Grellier，本次检索未能证实）
- **Random probe**（Stoppiglia, Dreyfus, Dubois, Oussar, *JMLR* 3:1399–1414, 2003）：对线性于参数的模型，在 Gram-Schmidt 正交化排序中加入随机探针特征，排名低于探针的变量被丢弃；作者称其与经典假设检验密切相关但更直观、放宽了部分假设，可间接用于其他模型 — [JMLR v3 stoppiglia03a](https://www.jmlr.org/papers/v3/stoppiglia03a.html)。（论文中按探针排名分布的分位数，例如"探针排在某变量之前的概率 ≤ 风险阈值"来定截断 —— [未在本会话核验全文]）
- **Guyon NIPS 2003 特征选择挑战**：在 5 个数据集中故意混入随机"probes"，用于评判算法过滤无关特征的能力；78 支队伍、13 周 — [Result Analysis of the NIPS 2003 FS Challenge](https://proceedings.nips.cc/paper_files/paper/2004/file/5e751896e527c862bf67251a474b3819-Paper.pdf)；[设计文档](https://api.sambuz.com/doc/design-of-experiments-for-the-nips-2003-variable-pdf-document-667666)。"被选特征中探针占比"可作为 FDR 的经验估计（挑战评估指标之一） [具体数值未检索到]
- **工业实现**：feature-engine `ProbeFeatureSelection` 以 Stoppiglia 2003 为参考，注入若干随机探针（正态/二项/均匀等分布），阈值可选探针重要性的均值、最大值或均值+3std 等 — [feature-engine 文档](https://feature-engine.trainindata.com/en/latest/api_doc/selection/ProbeFeatureSelection.html)（文档页未能 fetch，参数细节 [未在本会话核验]）
- **重要性偏置的根源**：Strobl et al. 2007 (*BMC Bioinformatics* 8:25)：当预测变量量纲或类别数不同时，RF 变量重要性不可靠；Gini 重要性在全部无信息变量的模拟中仍强烈偏好多类别变量与连续变量；原因是 bootstrap 抽样 + Gini 分裂准则；建议条件推断树（party::cforest） — [Strobl 2007 PDF](https://bmcbioinformatics.biomedcentral.com/counter/pdf/10.1186/1471-2105-8-25)；[Boulesteix 2011 TR](https://epub.ub.uni-muenchen.de/12224/1/TR.pdf)

### Inferences
- Shadow 特征（列置换）与 probe（独立随机生成）的关键区别：shadow 保留了候选特征自身的边际分布（基数、缺失率、取值离散程度），因此自动"同构"于候选——这是对抗 Strobl 型"高基数/连续偏好"的最直接手段；独立随机 probe 只能在你手动设定的分布上同构。对应我们的 R11：应优先用"候选列的置换副本"作负对照，而非通用随机数。
- 但"行级置换"会同时打乱候选特征的组内结构：若候选是 user 级常量，行级置换后它不再是 user 常量（变成行级噪声），反而更难被模型记忆 → 阈值偏低 → 系统性高估候选。正确的同构置换是"在 user 之间置换 user 级取值"（见 Q4）。
- Max 阈值（Boruta）控制的是近似 FWER 风格（"任一噪声都不该超过"），分位数阈值（BorutaShap percentile、mean+k·std）更接近 per-feature 的错误率控制；probe 数量越多，max 阈值越高（极值随 n 增长），所以"max of N probes"的严格程度依赖 N——若选 max 规则，必须固定 probe 数量或换用分位数。

### Gaps
- 未取得 Boruta 论文与 Stoppiglia 论文全文，二项检验与探针风险公式的精确表述需复核。
- 未找到对"max vs 分位数阈值"在真实工业数据上的系统性校准对比研究（假准入率/漏检率的实测数字）。

---

## Q2. Knockoffs：FDR 保证、对协变量依赖结构的要求、分组/聚类扩展、规模化局限

### Takeaway
Knockoff 是"同构负对照"的理论最严格版本：每个原特征配一个合成副本，要求 (X, X̃) 联合分布在任意交换下不变（成对可交换），且 X̃ 不看 y。正是这个"完整匹配依赖结构"的要求使 FDR 有有限样本保证；也正因为它，knockoff 在聚类/面板数据（user×day）上必须显式建模聚类结构，否则保证失效。

### Cited Findings
- **Fixed-X knockoffs**（Barber & Candès, *Annals of Statistics* 43(5):2055–2085, 2015, arXiv:1404.5609）：线性高斯模型、n ≥ p，构造 X̃ 使 X̃ᵀX̃ = XᵀX 且 XᵀX̃ = Σ − diag(s)，用 W 统计量与 knockoff+ 阈值得到有限样本 FDR 控制 — [arXiv 1404.5609](https://arxiv.org/abs/1404.5609) [未在本会话核验]
- **Model-X knockoffs**（Candès, Fan, Janson, Lv, *JRSS-B* 80(3):551–577, 2018）：把 knockoff 推广到任意条件分布 y|X（包括高维逻辑回归与一般非线性模型），在协变量分布已知时对任意 p 有有限样本有效性；代价是"X 的分布必须已知"，作者给出初步证据说明对估计分布有一定鲁棒性；在克罗恩病 GWAS 上发现数为原分析的两倍 — [EconPapers 摘要](https://econpapers.repec.org/RePEc:bla:jorssb:v:80:y:2018:i:3:p:551-577)；[JRSS-B PDF](https://archive.ymsc.tsinghua.edu.cn/pacm_download/21/11830-JRSSB-CFJL18.pdf)
- **Deep knockoffs**（Romano, Sesia, Candès, *JASA* 115(532):1861–1872, 2020）：用深度生成模型对未知分布采样近似 Model-X knockoff，训练准则基于 MMD，度量原特征与 knockoff 偏离成对可交换性的程度 — [EconPapers](https://econpapers.repec.org/RePEc:taf:jnlasa:v:115:y:2020:i:532:p:1861-1872)；[arXiv 1811.06687](https://www.arxiv.org/pdf/1811.06687)
- **Group knockoffs**（Dai & Barber, ICML 2016, PMLR 48:1851–1859）：以特征组为发现单位，控制组级 FDR，并在组内特征高度相关时功效更高；也扩展到多任务回归 — [PMLR](https://proceedings.mlr.press/v48/daia16.html)；[arXiv 1602.03589](https://arxiv.org/pdf/1602.03589)。组级 FDR 定义：选中组里"不含任何真重要变量"的组的期望比例 — [Harvard 讲义](https://aiawww.cfa.harvard.edu/astrostat/CHASC_1819/lj_20190409.pdf)
- 后续：原型（prototype/PCA）组 knockoff 在组内由少数隐因子驱动时可优于 Dai–Barber — [Caltech Authors](https://authors.library.caltech.edu/100909/)；多数据源组级 Model-X knockoff（N3C 数据） — [arXiv 2303.01599](https://arxiv.org/pdf/2303.01599)
- **聚类/面板数据的 knockoffs**（Bacci, Grilli, Rampichini, arXiv 2602.19398, 2026）：针对重复测量/面板数据，用线性随机截距模型，并**分别处理观测级与聚类级预测变量**；模拟中 sequential knockoffs 优于 Lasso 与 derandomized knockoffs — [arXiv 2602.19398](https://arxiv.org/html/2602.19398v1)（仅读到检索摘要）
- **时间序列**：Chi, Fan, Ing 的高维时序 knockoff 用子采样 + e 值，给出渐近 FDR 控制 — [CityU 讲座](https://www6.cityu.edu.hk/ma/news-events/high-dimensional-knockoffs-inference-time-series-data)
- **随机性与稳定性**：同一数据多次运行 Model-X knockoff 常选出不同集合；Derandomized knockoffs（Ren, Wei, Candès, *JASA* 118(542):948–958, 2023）聚合多次运行，在 Janson–Su 基础程序下控制 PFER 与 k-FWER；Ren & Barber（arXiv 2205.15461）把 knockoff 视为 e-BH，聚合 e 值实现 FDR 控制 — [IDEAS](https://ideas.repec.org/a/taf/jnlasa/v118y2023i542p948-958.html)；[arXiv 2012.02717](https://arxiv.org/abs/2012.02717)；[arXiv 2205.15461](https://arxiv.org/pdf/2205.15461v4)

### Inferences
- **与"同构负对照"(R11) 的对应**：knockoff 的成对可交换性 = 最强形式的同构——不仅边际分布相同，与其他所有特征的相关结构也相同。我们的 shadow/probe 只做到"边际同构"，因此只能校准"纯噪声的重要性水平"，不能校准"与已有特征相关但条件独立于 y"的冗余候选（这类候选在 knockoff 下应被拒绝，但在随机 probe 下常被准入）。对增量评估（候选 vs baseline）这是关键差别：用候选在 baseline 上的条件分布生成的 knockoff，才是"条件增量为零"的负对照。
- **user×day 数据**：独立同分布假设下构造的 knockoff 在聚类数据上不可交换；user 级候选应在 user 层级生成/置换（参考 Bacci 等"区分聚类级 vs 观测级预测变量"），本质上相当于把 user 当作样本单位。
- **交叉特征**：group knockoff 思路可用于把"一个交叉特征族"（如同一对父特征的多种交叉）作为一组整体判定，负对照也应为"父特征的 knockoff/置换副本做同样的交叉"，而不是一个独立随机列。
- **规模化局限**（推断）：Model-X 需要已知/可估的 X 分布（高维混合类型、重尾、高基数类别特征下难以准确建模）；每次需对全部候选生成副本使特征数翻倍；单次运行不稳定需多次去随机化，成本 ×K；FDR 保证要求 W 统计量满足反对称（"翻转符号"）性质，用 GBDT 增益重要性时需构造 W = imp(X_j) − imp(X̃_j)。在特征前置评估这种"一批几十个候选 + 固定 baseline"的场景，完整 knockoff 可行但不必要；更实用的是借用其"同构 + 差值统计量 + 多次去随机"三个思想。

### Gaps
- 未找到 knockoff 在大规模推荐/广告 GBDT 特征选择中的工业落地报告。
- Bacci 等 2026 论文仅读到摘要，具体 FDR 数值未知。

---

## Q3. 流行病学负对照、OHDSI 经验校准、A/B 中的 A/A 测试

### Takeaway
OHDSI 的经验校准是我们设计的最直接类比：用一批"已知无效"的负对照估计整个分析管线的经验零分布（随机误差 + 系统误差），再据此重算 p 值/阈值。它证明了"名义阈值在有系统偏差的管线中严重过松"，也暴露出其前提——负对照必须与真实候选在偏差上"可交换"。

### Cited Findings
- **Lipsitch, Tchetgen Tchetgen, Cohen, *Epidemiology* 21(3):383–388, 2010**：把实验室负对照引入观察性流行病学，用以发现混杂、回忆偏倚、分析缺陷；区分负对照暴露与负对照结局两类，并给出能探测混杂的条件；作者指出"负对照何时能灵敏探测其他误差来源"尚需研究 — [PMC3053408](https://pmc.ncbi.nlm.nih.gov/articles/PMC3053408/)
- **Schuemie, Ryan, DuMouchel, Suchard, Madigan, *Stat Med* 33(2):209–218, 2014**：对三种设计（病例对照、队列、SCCS）在负对照药物上运行，观察 p<0.05 的频率，拟合效应估计的经验零分布，计算同时考虑随机误差与系统误差的校准 p 值；结论：大多数观察性研究在无效应时也会宣布显著；校准把伪阳性降到期望的 5%；估计至少 54% 的 p<0.05 发现并不真正显著 — [PMC4285234](https://pmc.ncbi.nlm.nih.gov/articles/PMC4285234)；[EUR repository](https://repub.eur.nl/pub/67635)
- R 包 EmpiricalCalibration：用一组负对照假设估计特定研究设置的经验零分布 — [EmpiricalCalibration 手册](https://ohdsi.r-universe.dev/EmpiricalCalibration/doc/manual.html)；[Vignette](https://anorien.csc.warwick.ac.uk/CRAN/web/packages/EmpiricalCalibration/vignettes/EmpiricalPCalibrationVignette.pdf)
- **批评**（Gruber & Tchetgen Tchetgen, *Stat Med* 2016, doi:10.1002/sim.6936）：方法依赖"偏差服从可正确估计均值与方差的正态分布"；轻度偏离使 I 类错误控制保守，较大偏离则反保守；校准会显著增加 II 类错误（漏检）；认为常规使用为时尚早 — [QxMD 摘要](https://read.qxmd.com/read/26970249/limitations-of-empirical-calibration-of-p-values-using-observational-data)
- **回应**（Schuemie et al., *Stat Med* 2016, doi:10.1002/sim.6977）：关键假设是负对照与目标假设之间偏差可交换；批评中模拟的偏差（OR≈3 且异常同质）不现实 — [zendy 10.1002/sim.6977](https://zendy.io/title/10.1002/sim.6977)
- 负对照结局之间的相关会影响校准（OHDSI 2024 摘要） — [OHDSI Wang abstract](https://ohdsi.org/wp-content/uploads/2024/10/73-Wang-Abstract_Correlated_NCO-Elisse-Katzman.pdf)
- **A/A 测试**：Kohavi et al.《Trustworthy Online Controlled Experiments》(2020, p.188) 建议从已有数据重复重采样合成 A/A 测试，用 KS 检验看 p 值是否均匀；p 值不均匀说明假阳性率偏离名义 α，可用来识别易产生 I 类错误膨胀的设计 — [arXiv 2502.04793 "t-Testing the Waters"](https://arxiv.org/html/2502.04793v2)

### Inferences
- **直接映射**：我们的"每批混入噪声探针"= OHDSI 的负对照集合；"强 baseline 特征作正对照"= OHDSI 中的合成正对照（OHDSI 也用注入已知效应的正对照估计功效/覆盖率 [未在本会话核验]）。应同时报告两条曲线：负对照的假准入率（→ 校准 δ_min）与正对照的检出率（→ 防止过度保守，回应 Gruber 批评中的 II 类错误代价）。
- **可交换性是生死线**：Schuemie 的回应把有效性落在"负对照与目标偏差可交换"；我们 mock 数据中 user 级常量随机特征 17% 的假准入，正是"负对照与候选（行级随机 probe vs user 级候选）偏差不可交换"的实例——系统偏差（模型对 user 级常量的记忆）只作用于某一类特征，不能用另一类的零分布校准。结论：零分布必须按特征"粒度/结构类型"分层估计（user 级、user×day 级、交叉类各自一套）。
- A/A 的"p 值均匀性检验"可直接移植为管线自检：对噪声探针的增量指标算 p 值/秩，检验其是否在 [0,1] 均匀；不均匀即说明评估管线（CV 划分、泄漏、粒度）有系统偏差。

### Gaps
- 未找到 OHDSI 合成正对照的原文（Schuemie et al. 2018 PNAS "Empirical confidence interval calibration" 可能是来源，未检索）。

---

## Q4. 分组/聚类数据的置换检验与可交换性；为何 user 级常量随机特征像 ID；GBDT 对高基数/ID 特征的记忆与目标泄漏

### Takeaway
置换检验的有效性来自"零假设下被置换单元可交换"。user×day 数据中 user 内观测不独立，可交换单元是 user（或 user 内的 day）。user 级常量随机特征在训练集里是 user 的一一映射（近似 ID），树模型可借之记忆 user 级目标均值——这就是 CatBoost 论文所说的目标泄漏/预测偏移的同一机制；如果训练/验证按行而非按 user 划分，这种记忆会被验证集"奖励"，造成假准入。

### Cited Findings
- **可交换块**（Winkler, Ridgway, Webster, Smith, Nichols, *NeuroImage* 92:381–397, 2014）：在配对、重复测量、家系数据中全局可交换性不成立；定义 exchangeability blocks：块内自由置换，或整块作为整体置换 — [PMC4010955](https://pmc.ncbi.nlm.nih.gov/articles/PMC4010955)；多层嵌套块扩展（*NeuroImage* 123:253–268, 2015） — [brainder 博文](https://brainder.org/2015/12/07/permutation-tests-in-the-human-connectome-project/)
- **CatBoost**（Prokhorenkova et al., NeurIPS 2018, arXiv 1706.09516）：经多步 boosting 得到的模型依赖所有训练样本的目标，导致训练点上的预测分布相对测试点发生偏移（一种目标泄漏）；把类别转为目标统计量本身也是一个模型，同样会造成泄漏与预测偏移；提出 ordered boosting 与基于排列的有序目标统计量来对抗 — [arXiv 1706.09516](https://arxiv.org/pdf/1706.09516)；[ar5iv](https://ar5iv.labs.arxiv.org/html/1706.09516)
- **高基数偏置**：Strobl 2007 与 Altmann 2010 都报告树模型重要性偏好多类别/高基数变量（见 Q1） — [Strobl 2007](https://bmcbioinformatics.biomedcentral.com/counter/pdf/10.1186/1471-2105-8-25)；[Altmann 2010](https://pubmed.ncbi.nlm.nih.gov/20385727/)

### Inferences
- **机制**：一个 user 级常量连续随机数 r_u，在 N_user 个用户上几乎都不同，等价于一个已排序的 user ID；GBDT 可在 r_u 上切出足够细的区间以分离用户，从而拟合 user 级目标均值（user 固定效应）。若验证集与训练集共享用户（按行/按日随机划分），这部分"记忆"在验证上真实有效 → 增量 AUC/logloss 为正 → 被准入。所以 17% 假准入不是"噪声 probe 失效"，而是评估设计把"user 固定效应"当成了可泛化信号。
- **可行检验**：(a) 按 user 分组划分（GroupKFold / 时间外 + 新用户）重测 user 级随机 probe，若假准入率降回名义水平，则确认是记忆效应；(b) 在 baseline 中加入 user 历史统计（user 目标均值的 out-of-fold / 有序目标统计量，CatBoost 式）以"吸收"user 固定效应，之后 user 级随机 probe 应无增量。
- **置换方式与粒度绑定**（R11 具体化）：
  - 行级候选 → 行级置换 / 行级随机数；
  - user 级候选 → 在 user 之间整体置换候选的 user 级取值（Winkler 的"整块置换"），保持"user 内常量"结构；
  - user×day 候选 → 在 user 内跨天置换（块内置换）或在同一天跨 user 置换，取决于想检验的零假设（"无 user 间信号" vs "无时间变化信号"）；
  - 交叉特征 f(a,b) → 负对照应为 f(perm(a), b) 或 f(a, perm(b))（与候选同函数、同基数、同稀疏度），不是独立随机列。
- **目标置换（null importance）在聚类数据上**：应在 user 之间整块置换 y 序列（或在 user 内置换），否则零分布忽略了 user 内相关，零重要性被低估。

### Gaps
- 未找到专门研究"随机常量 per-entity 特征在 GBDT 中被当作 ID 记忆"的论文；上述机制解释是推断，与 CatBoost 目标泄漏论述一致，但没有直接的量化文献。

---

## Q5. 固定阈值 vs 同批噪声探针分布的分位数阈值；对未决决策 #13、#14 的建议

### Takeaway
文献实践几乎一致地采用"数据驱动、随批重估"的阈值（Boruta max、BorutaShap 分位数、PIMP p 值、knockoff+ 数据相关阈值、OHDSI 经验零分布），而不是固定数值。固定阈值无法吸收批次间的样本量、模型方差、目标漂移；但纯分位数在 probe 太少时方差大，需要足够多的 probe 与跨批次平滑。

### Cited Findings
- BorutaShap 默认用 shadow 最大值（100 分位），并承认其过于保守、提供更低分位数选项 — [BorutaShap PyPI](https://pypi.org/project/BorutaShap)
- PIMP 用置换 y 的零分布逐特征给 p 值，而非固定重要性阈值 — [Altmann 2010](https://pubmed.ncbi.nlm.nih.gov/20385727/)
- Knockoff 的阈值本身是数据相关的：选取使估计 FDP（knockoff 一侧超过阈值的个数 / 原特征超过阈值的个数）≤ q 的最小阈值 — [Candès et al. 2018](https://archive.ymsc.tsinghua.edu.cn/pacm_download/21/11830-JRSSB-CFJL18.pdf)
- OHDSI 经验校准：由负对照拟合的零分布替代名义 p 值，校准后伪阳性率降至 ~5%；但代价是功效下降（Gruber 批评） — [Schuemie 2014](https://pmc.ncbi.nlm.nih.gov/articles/PMC4285234)；[Gruber 2016](https://read.qxmd.com/read/26970249/limitations-of-empirical-calibration-of-p-values-using-observational-data)
- Derandomized knockoffs：单次运行的选择不稳定，聚合多次运行得到稳定决策 — [Ren, Wei, Candès 2023](https://ideas.repec.org/a/taf/jnlasa/v118y2023i542p948-958.html)

### Inferences（对未决决策的建议）
- **#14 L1 "observe" 阈值：建议用同批噪声探针分布的分位数，但加护栏**：
  1. 按粒度分层：每类候选（行级 / user×day / user 级 / 交叉）只和同构 probe 的分布比较（R11）。
  2. probe 数量足够：用第 q 分位作阈值时，若要求经验假准入率 ≈ α，每层至少需 ~1/α 量级 probe（如 α=5% 需 ≥20 个，最好 ≥50）；probe 少时退化为"max of N"规则，其严格度随 N 变化——需固定 N。（推断）
  3. 多次重采样（不同随机种子/CV 折）后取 probe 分布与候选分数的稳定统计（去随机化思想），避免一次运行的抖动。
  4. 设置下限 floor = max(固定业务最小增益 δ_floor, probe 分位数)：probe 分位数负责统计显著性，固定值负责"实用显著性"（即便统计显著也不值得上线的微小增益）。
  5. 用正对照（已知强特征的弱化版本，例如加噪到不同信噪比）同时跟踪检出率，防止 Gruber 指出的功效损失被忽视。
  6. 跨批次监控 probe 分位数本身的时间序列，若漂移，说明评估管线变化（等价 A/A 检查）。
- **#13 user 粒度候选的判定：三种方案并不互斥，推荐组合**：
  - (首选，消除根因) baseline 加入 user 历史统计（out-of-fold / 时间上严格在前的 user 目标均值、活跃度等），吸收 user 固定效应；同时评估按 user 分组划分或"新用户/时间外"验证。这样 user 级候选只有在提供"超出 user 固定效应"的信息时才得分。
  - (校准) 与同批 user 级随机 probe（在 user 之间置换的候选副本最佳，即 user 级 shadow）比较——在上一步之后，这些 probe 的增量应接近 0；若仍显著，说明划分仍有泄漏。
  - (诊断) 残差分析：在 baseline（含 user 统计）残差上检验 user 级候选与 user 平均残差的关联，按 user 聚合后再检验（样本单位 = user），等价于用 user 作为可交换单元的置换检验。
  - 不建议单独依赖"与 user 级随机 probe 比较"而不修 baseline/划分：那只是把阈值抬到"记忆 user ID 能拿到的增益"之上，会系统性漏掉弱但真实的 user 级特征，且阈值随用户数/树深变化。
- **R11 同构负对照**：最佳负对照 = 候选自身按其结构粒度做的置换副本（shadow），交叉特征则对父特征之一置换后再走同一交叉函数；进阶可借 group knockoff 思想把一组相关候选作为一组判定。

### Gaps
- 未找到公开的"probe 分位数阈值 vs 固定阈值"在工业特征平台中的假准入/漏检对照实测；建议在我们的 mock 数据上自测：对每种粒度，分别报告固定阈值与分位数阈值下的负对照假准入率、正对照检出率曲线（类似 OHDSI 的校准图）。
- 未检索到 Guyon 挑战中"被选探针比例"作为 FDR 估计的具体数值。
