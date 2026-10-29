# 负对照 / 噪声探针 / shadow / null importance / knockoffs：核验与校准协议（第二轮）

> 承接 `research_notes/特征前置评估业界调研/06_negative_controls_knockoffs.md`（下称"第一轮"）。
> 本轮方法：WebFetch 对 arxiv / jmlr / jstatsoft / feature-engine 文档站 / pmc.ncbi 仍报 DNS 拦截，但 **curl 经代理可达**，因此原文 PDF 用 curl 下载后 `pdftotext` 逐段核对；PMC 全文改走 Europe PMC REST（`ebi.ac.uk/europepmc/webservices/rest/{PMCID}/fullTextXML`）；Boruta / BorutaShap / feature-engine / ranger 直接读 GitHub 源码（比文档更权威）。
> 标注：**[已核原文 + 位置]** = 本会话读到原文对应段落；**[更正]** = 修正第一轮表述；**[仍未核]** = 本会话仍未读到原文。"推断"一律放在 Inferences，不与来源事实混写。
> 未能取得：Boruta 的 JSS 论文正文（jstatsoft 下载链接只返回 22 字节）、Altmann 2010 正文（OUP 拦截，非 OA）、Schuemie 2018 PNAS 正文（Europe PMC 只返回元数据）。

---

## Q1. 第一轮标注条目的逐项核验

### Takeaway
第一轮的方向性结论全部成立，但有 4 处需更正：(a) feature-engine `ProbeFeatureSelection` 默认阈值是探针重要性的**均值**（不是 max），对零特征约 50% 误放；(b) BorutaShap 文档称"exact two-sided"，代码实际是两个单侧二项检验；(c) Barber–Candès fixed-X 的"自然设定"是 **n ≥ 2p**（n ≥ p 是扩展）；(d) Winkler 2014 的论文题目是 "Permutation inference for the general linear model"。Boruta 的"二项检验 + Bonferroni"已在源码层面核实。

### Cited Findings

**Boruta（R 包，Kursa & Rudnicki 2010）** — [已核原文：CRAN 源码 `R/Boruta.R`，`Boruta.default`]
- 签名默认值：`pValue=0.01, mcAdj=TRUE, maxRuns=100, doTrace=0, holdHistory=TRUE, getImp=getImpFruZ`（默认重要性适配器 `getImpFruZ`：Kursa 自己的 `fru` 包随机森林的平均精度下降 Z 分数；旧版本默认用 ranger 的 `getImpRfZ`，具体随版本而变 [版本差异仍未核]）；`maxRuns` 必须 > 10 — [cran/Boruta R/Boruta.R](https://github.com/cran/Boruta/blob/master/R/Boruta.R)
- 每轮把未被拒绝的特征复制并置换成 shadow；命中规则：`curImp$imp > max(curImp$shaImp)`，即**本轮超过 shadow 最大值**才记一次 hit — 同上
- 判定：零假设下每轮命中概率 0.5；确认用上尾 `pbinom(hitReg-1, runs, 0.5, lower.tail=FALSE)`，拒绝用下尾 `pbinom(hitReg, runs, 0.5, lower.tail=TRUE)`；两者都过 `p.adjust(method="bonferroni")`（`mcAdj=TRUE` 时），乘数是全部属性个数；循环到无 Tentative 或达 `maxRuns`，未决者保持 Tentative，可用 `TentativeRoughFix` 处理 — 同上
- 第一轮"二项检验 + Bonferroni"→ 确认。JSS 论文正文本轮未取得，"Z 分布不是 N(0,1)"一句仍来自二手综述 [仍未核]

**BorutaShap** — [已核原文：GitHub `src/BorutaShap.py`]
- `__init__(model=None, importance_measure='Shap', classification=True, percentile=100, pvalue=0.05)`；`fit(..., n_trials=20, random_state=0, sample=False, train_or_test='test', normalize=True, stratify=None)` — [Ekeany/Boruta-Shap BorutaShap.py](https://github.com/Ekeany/Boruta-Shap/blob/master/src/BorutaShap.py)
- hit：`X_feature_import > np.percentile(Shadow_feature_import, self.percentile)`，默认 100 = shadow 最大值 — 同上
- 检验：二项检验 `binom_test(x, n=iteration, p=0.5)`，确认用 `alternative='greater'`、拒绝用 `'less'`，再做 Bonferroni（`pvals * n_tests`）后与 `pvalue` 比 — 同上
- **[更正]** 源码 docstring 写 "exact, two-sided"，实际是两个单侧检验；与 R 版 Boruta 一致。默认 pvalue 0.05 比 R 版 0.01 宽松。

**feature-engine `ProbeFeatureSelection`** — [已核原文：GitHub 源码 `feature_engine/selection/probe_feature_selection.py`]
- 参数与默认：`estimator`（必填）、`variables=None`、`collective=True`、`scoring="roc_auc"`、`n_probes=1`（每种分布的探针数）、`distribution="normal"`（可选 `normal/binary/uniform/discrete_uniform/poisson/all`）、`n_categories=10`、`threshold="mean"`（可选 `mean/max/mean_plus_std`）、`cv=5`、`groups=None`、`random_state=0`、`confirm_variables=False` — [feature_engine probe_feature_selection.py](https://github.com/feature-engine/feature_engine/blob/main/feature_engine/selection/probe_feature_selection.py)
- 阈值：`mean` = 探针重要性均值；`max` = 最大值；`mean_plus_std` = **均值 + 3×标准差**；只有一个探针列时忽略 `threshold`，直接用该探针重要性；特征重要性 **严格小于** 阈值才剔除 — 同上
- `collective=True` 用模型自带 `feature_importances_`/`coef_`；`False` 时逐特征单变量模型的 CV 性能 — 同上
- docstring 只引 Stoppiglia et al. 2003 — 同上
- **[更正]** 第一轮未说明默认值。默认是 `mean`，且默认只有 1 个正态探针（此时阈值 = 单个探针重要性）。对零特征而言这相当于"超过一个同分布噪声即保留"，误放约 50%。docstring 写 `'binomial'`，代码实际接受 `'binary'`。
- 支持 `groups` 参数传给 CV（可接 GroupKFold），但探针本身是行级 i.i.d.，没有分组结构的探针 — 同上

**Stoppiglia, Dreyfus, Dubois, Oussar, JMLR 3:1399–1414, 2003** — [已核原文：PDF §3、§3.1、§3.2、§5 结论]
- 场景：线性于参数的模型 + Gram-Schmidt 正交化逐步排序；探针 = 正态随机向量 — [JMLR PDF](https://www.jmlr.org/papers/volume3/stoppiglia03a/stoppiglia03a.pdf)
- 公式（§3.1）：随机向量与固定向量夹角平方余弦 x = cos²φ 在 ν 维下服从 Beta(1/2, (ν−1)/2)，密度 f_ν(x)=Γ(ν/2)/(Γ(1/2)Γ((ν−1)/2))·(1−x)^((ν−3)/2)/√x（式 2）；P_ν(cos²φ)=1−F_ν(cos²φ)（式 3）；第 n 步探针比已选 n 个特征中某一个更相关的概率递推 **G_n = G_{n−1} + P_{N−n}(cos²φ_n)(1 − G_{n−1})，G_0 = 0**（式 4） — 同上 p.1402
- 决策（§3.2）：先选风险 r（"选入一个不如随机特征相关的变量"的风险）；逐步计算 G_n，G_n < r 则保留并继续，否则停止。示例：15 个观测、10 个候选（5 个真）在 r = 10% 时恰好选出 5 个真特征（图 1）；另例用 1% 风险 — 同上 pp.1402–1405
- 风险选择："数据稀疏 → 低风险；数据充足 → 可接受更高风险" — 同上 §3
- 推广（§5）：也可不解析计算，而是"生成多个探针实现，用任意排序方法排序，得到探针秩的经验分布"，此时探针正态性假设可放宽 — 同上 pp.1409–1410
- 第一轮"[未在本会话核验]"→ 已核。注意：原文的风险 r 是"至少一个已选特征不如探针"的累积概率（类似 FWER 的逐步停止规则），不是每特征的错误率

**NIPS 2003 特征选择挑战（Guyon, Gunn, Ben-Hur, Dror）** — [已核原文：NIPS 2004 proceedings PDF，表 1、表 2、"Performance assessment"、调研小结]
- 探针占比（表 1）：Arcene 30%、Dexter 50%、Dorothea 50%、Gisette 30%、Madelon 96%；探针"从近似真实特征的分布中随机抽取，但不含标签信息" — [Result Analysis of the NIPS 2003 FS Challenge](https://proceedings.nips.cc/paper_files/paper/2004/file/5e751896e527c862bf67251a474b3819-Paper.pdf)
- 评估指标含 Ffeat（选中特征比例）与 **Fprobe（选中集合中探针比例）**；排名先比 BER/AUC（McNemar 检验），平局再看 Ffeat、Fprobe — 同上
- 结果（表 2a，12 月 1 日）：第一名 BayesNN-DFT BER 6.84%，用 80.3% 特征，**选中集合里 47.8% 是探针**；BayesNN-small BER 8.20%，用 4.7% 特征、探针 2.9%；RF+RLSC 用 22.5% 特征、探针 17.5%；CBAMethod3E（12 月 8 日）探针 0.1% — 同上
- 135 份提交中 56 份合格；在调研的 19 组里**只有 1 组用"random probes"跟踪误选比例** — 同上
- 第一轮"78 支队伍、13 周"本轮未在该 PDF 中找到 [仍未核]

**Altmann et al. 2010（PIMP）** — [已核：摘要（Europe PMC 元数据）+ ranger 实现源码]
- 摘要：RF 偏好多类别的类别变量；方法 = 多次置换结果向量，估计每个变量在无信息设定下的重要性分布，用观测重要性的 P 值作为校正后的重要性；模拟显示无信息变量不会得到显著 P 值 — [Bioinformatics 26(10):1340, doi:10.1093/bioinformatics/btq134](https://doi.org/10.1093/bioinformatics/btq134)（摘要经 [Europe PMC](https://europepmc.org/article/MED/20385727) 读取）
- ranger `importance_pvalues(method="altmann", num.permutations=100)`：每次置换 y 后用相同 `num.trees/mtry/min.node.size` 重训；p = (#{null ≥ 观测} + 1)/(S + 1)；文档写"作者推荐 50–100 次置换，但要更精确的 p 值需要大得多的次数" — [cran/ranger R/importance.R](https://github.com/cran/ranger/blob/master/R/importance.R)
- 第一轮"可拟合正态 / 对数正态 / 伽马"的参数化选项：本轮未读到正文 [仍未核]

**Barber & Candès 2015** — [已核原文：arXiv 1404.5609v3 = Ann. Statist. 43(5):2055–2085, DOI 10.1214/15-AOS1337]
- 定理 1（knockoff）：控制修正 FDR，E[#{零且选中}/(#{选中}+q⁻¹)] ≤ q；定义 2（knockoff+）：T = min{t : (1 + #{W_j ≤ −t}) / (#{W_j ≥ t} ∨ 1) ≤ q}；定理 2：knockoff+ 精确控制 FDR ≤ q — [arXiv 1404.5609](https://arxiv.org/abs/1404.5609) pp.6–7
- **[更正]** 构造的"自然设定"是 **n ≥ 2p**（§2.1.1），p ≤ n < 2p 的扩展在 §2.1.2；第一轮写成 n ≥ p — 同上 §2.1

**Candès, Fan, Janson, Lv 2018（Model-X）** — [已核原文：arXiv 1610.02351，定义 3.1、式 3.4–3.5、定理 3.4]
- 定义 3.1：(1) 对任意子集 S，(X, X̃)_swap(S) 与 (X, X̃) 同分布（成对可交换）；(2) X̃ ⊥ Y | X（构造时不看 Y 即满足） — [arXiv 1610.02351](https://arxiv.org/abs/1610.02351) p.9
- W_j = f_j(Z_j, Z̃_j)，f_j 为任意反对称函数，即满足 flip-sign 性质（如 W_j = Z_j − Z̃_j）— 同上 p.11
- 定理 3.4：knockoff 阈值控制 mFDR，knockoff+ 控制 FDR；"结果非渐近，且无论响应与协变量依赖如何都成立——事实上条件于 y 成立"；证明只需"零变量的 W 符号是 i.i.d. 硬币" — 同上 pp.13–14
- 期刊：JRSS-B 80(3):551–577（由 Berrett et al. 参考文献交叉确认）— [CPT 论文参考文献](https://arxiv.org/abs/1807.05405)

**Dai & Barber 2016（group knockoff）** — [已核原文：arXiv 1602.03589v1 摘要、§2、定理 1–2]
- 组级 FDR 控制，组内特征高度相关时功效更高；也适用于多任务回归；定理 1：W 满足 sufficiency 与 group-antisymmetry 时，group knockoff 控制修正组 FDR，group knockoff+ 控制组 FDR ≤ q — [arXiv 1602.03589](https://arxiv.org/abs/1602.03589)
- ICML 2016 / PMLR 48 的出版信息来自第一轮 PMLR 页，本轮 arXiv 文本中没有 [仍未核]

**Ren, Wei, Candès（derandomized knockoffs）** — [已核原文：arXiv 2012.02717v1 摘要、算法 1、式 (4)–(9)]
- 做法：运行 M 次 knockoff（基础程序取 Janson–Su 的 PFER 控制版），特征 j 的选择频率 Π_j = (1/M)Σ_m 1{j ∈ Ŝ_m}，最终 Ŝ = {j : Π_j ≥ η}；"除非另行说明，η 固定为 0.5"；证明控制 **PFER 与 k-FWER**（不是 FDR） — [arXiv 2012.02717](https://arxiv.org/abs/2012.02717) §2
- 出版信息 JASA 118(542):948–958, 2023 来自第一轮 IDEAS 页 — [IDEAS](https://ideas.repec.org/a/taf/jnlasa/v118y2023i542p948-958.html)

**OHDSI 经验校准三篇**
- Schuemie et al. 2014 *Stat Med* 33(2):209–218 — [已核原文：Europe PMC 全文 §2.6、表 1、图 2]：假设负对照 i 的对数效应估计 y_i ~ N(θ_i, τ_i²)，θ_i ~ N(μ, σ²)（"null（偏差）分布"），用极大似然估计 μ、σ²；新假设的校准 p 值基于 y_{n+1} ~ N(μ, σ² + τ_{n+1}²)，用 Φ 计算单侧 p 值；作者称高斯近似够好，混合高斯与非参数密度估计没有改善结果；表 1 的经验 null：队列 μ=−0.05、σ=0.54（原文表头写 variance/SD 需复核），病例对照 0.90/0.35，SCCS 0.79/0.28；校准后负对照 p<0.05 的比例：2/34（6%）、5/46（11%）、3/46（5%）；"至少 54% 的 p<0.05 发现在校准后不再显著" — [PMC4285234](https://europepmc.org/article/PMC/PMC4285234)
- Gruber & Tchetgen Tchetgen 2016 *Stat Med*（doi:10.1002/sim.6936） — [已核：摘要]：方法有效性依赖"偏差服从可正确估计均值与方差的正态分布"；轻度违背时偏保守，严重违背时反保守；校准会显著增加 II 类错误；认为常规使用为时尚早 — [PMC5012943](https://europepmc.org/article/PMC/PMC5012943)
- Schuemie, Hripcsak, Ryan, Madigan, Suchard 2016 *Stat Med* 35:3883–3888（doi:10.1002/sim.6977） — [已核原文：Europe PMC 全文]：反驳 Gruber 的模拟"偏差 OR=3 且异常同质"不现实；**校准需要负对照与目标假设之间的可交换性**；建议**始终对负对照做留一法校准评估**（每个负对照用其余负对照拟合 null，再看 p<α 的比例是否 ≈ α） — [PMC5108459](https://europepmc.org/article/PMC/PMC5108459)
- Schuemie et al. 2018 *PNAS*（doi:10.1073/pnas.1708282114） — [已核：摘要 + EmpiricalCalibration CI 校准 vignette]：把校准从 p 值推广到 CI；CI 校准需要正对照，靠"在负对照上注入模拟结局"合成；系统误差模型假设误差分布的**均值与 SD 都随真实效应量线性变化**（`fitSystematicErrorModel` 输出 meanIntercept、meanSlope、sdIntercept、sdSlope；示例 −0.067、0.933、0.187、0.003）；只有负对照时，默认假设误差不随效应量变化（`convertNullToErrorModel`）；正对照由负对照派生会相关，评估时用 `crossValidationGroup` 按来源分组留一 — [PMC5856503](https://europepmc.org/article/PMC/PMC5856503)；[CRAN vignette](https://cran.r-project.org/web/packages/EmpiricalCalibration/vignettes/EmpiricalCiCalibrationVignette.pdf)。PNAS 正文里的具体数值本轮未读 [仍未核]

**Strobl, Boulesteix, Zeileis, Hothorn 2007 *BMC Bioinformatics* 8:25** — [已核原文：摘要、表 1]
- 当预测变量的量纲或类别数不同时，RF 重要性不可靠；两个机制：单棵树的有偏变量选择，以及**有放回 bootstrap** 的效应；建议用无偏的条件推断树（cforest）+ **无放回子抽样** — [Strobl 2007 PDF](https://bmcbioinformatics.biomedcentral.com/counter/pdf/10.1186/1471-2105-8-25)
- 模拟设计：X1~N(0,1)，X2..X5 分别为 2/4/10/20 类的等概率离散变量；null case 中 Y~B(0.5) 与全部无关 — 同上表 1

**Winkler et al. 2014** — [已核原文：Europe PMC 全文]
- **[更正]** 题目是 "Permutation inference for the general linear model"，*NeuroImage* 92:381–397（PMC4010955）。定义 exchangeability blocks（EB）：**块内可交换**（只在块内置换）与**整块可交换**（块作为整体互换，块内顺序不变；符号翻转时整块一起翻）— [PMC4010955](https://europepmc.org/article/PMC/PMC4010955)
- 多层嵌套块是 2015 年的后续论文（*NeuroImage* 123:253–268），本轮未核 [仍未核]

**Prokhorenkova et al.（CatBoost）** — [已核原文：arXiv 1706.09516 §3.2、§4.1]
- Greedy TS 有目标泄漏：极端例子是类别特征**取值全部唯一**、P(y=1|类别)=0.5 时，训练集上一刀就能完美分类，测试集只有 50% 准确率（条件偏移，违反性质 P1：E(x̂|y) 训练测试一致）— [arXiv 1706.09516](https://arxiv.org/abs/1706.09516) §3.2
- Holdout TS 满足 P1，但浪费数据（违反 P2）；**Leave-one-out TS 仍然泄漏**（常量特征的反例）；Ordered TS 按随机排列只用"历史"样本计算，同时满足 P1、P2；boosting 本身也有同类泄漏导致的 prediction shift，用 ordered boosting 对抗 — 同上 §3.2、§4.1
- NeurIPS 2018 出版信息本轮未在 arXiv 文本中确认 [仍未核]

### Inferences
- NIPS 2003 的结果说明：强正则化模型可以带着大量探针拿到最好的预测指标（47.8% 探针、BER 第一）。**"模型整体性能好"不等于"特征选择干净"**，探针比例必须作为独立指标，不能指望 ΔAUC 自己把噪声特征拒掉。这与我们"L2 增量判定 + 每批负对照实测误放率"的分工一致。
- feature-engine 的默认值（mean、1 个探针）不能直接拿来做准入：零特征误放约 50%。如需借用，至少改为 `threshold="max"` 且 n_probes ≥ 19，或者自己实现分位数规则（见 Q2）。

### Gaps
- Boruta JSS 正文、Altmann 正文、Schuemie 2018 正文未取得；对应细节（Z 分数解释、参数化 null 拟合、PNAS 数值）仍需复核。

---

## Q2. 需要多少探针？max 规则 vs 分位数规则的性质；按粒度分层

### Takeaway
若零候选与 N 个探针可交换，"超过 N 个探针中第 k 大"的边际误放率**恰好是 k/(N+1)**；但对单批而言，实际误放率是随机的，服从 Beta(k, N+1−k)。mock 里每个粒度每批只有 3 个探针，等价于名义误放率 25% 的 max 规则。要让 L1 的分位数阈值稳定在 ±1 个百分点以内，每层需要几百个探针。L1 不用训练模型，几百个探针成本很低；L2 每个探针都要一次消融训练，应改用参数化经验 null（Q4）加跨批次累积。

### Cited Findings
- 置换/随机化检验的有限样本 p 值形式 p = (1 + Σ_m 1{T^(m) ≥ T}) / (1 + M)：CPT 式 (3) — [Berrett et al. arXiv 1807.05405](https://arxiv.org/abs/1807.05405)；ranger 的 Altmann 实现同式 — [ranger importance.R](https://github.com/cran/ranger/blob/master/R/importance.R)
- ranger 文档：作者推荐的 50–100 次置换只够粗略 p 值，"要更精确的 p 值需要大得多的次数" — 同上
- Boruta 用"超过本轮 shadow 最大值"计 hit，再对多轮 hit 数做二项检验（p=0.5），而不是单轮直接判定 — [Boruta.R](https://github.com/cran/Boruta/blob/master/R/Boruta.R)；BorutaShap 允许把 max 换成任意分位数 — [BorutaShap.py](https://github.com/Ekeany/Boruta-Shap/blob/master/src/BorutaShap.py)
- Stoppiglia 风险 r 是逐步累积概率 G_n 的阈值；可以用多次探针实现的经验秩分布代替解析式 — [JMLR 2003 §3.2、§5](https://www.jmlr.org/papers/volume3/stoppiglia03a/stoppiglia03a.pdf)
- 本仓库 mock：每个种子每个粒度 3 个探针（`probe_row_*`、`probe_userday_*`、`probe_user_*`），20 个种子合计 60 个 — `feval/mock.py` `probe_names(n_probes=3)`；L1 落入"观察"的比例：样本级 8%、用户×天级 15%、用户级常量 30% — `reports/calibration.md` §1

### Inferences（推导；标准次序统计量结论，数值由本会话用二项公式计算）
- **边际误放率**：零候选的统计量与 N 个探针可交换（同构 + 同一管线）时，它超过第 k 大探针的概率 = k/(N+1)。max-of-N（k=1）即 1/(N+1)：N=3 → 25%，N=19 → 5%。**因此 max 规则的严格度完全由 N 决定，N 必须固定或在报告中写明。**
- **条件误放率（单批）**：给定这一批探针，阈值对应的真实误放率 F̄(t) ~ Beta(k, N+1−k)。名义 5% 时的 90% 区间：

| N | k（第 k 大） | 名义误放 | 单批实际误放 90% 区间 | P(实际 > 10%) |
|---|---|---|---|---|
| 3 | 1 | 25% | 1.7%–63% | 0.73 |
| 19 | 1 | 5% | 0.3%–14.6% | 0.14 |
| 59 | 3 | 5% | 1.4%–10.3% | 0.06 |
| 99 | 5 | 5% | 2.0%–9.0% | 0.03 |
| 199 | 10 | 5% | 2.8%–7.8% | <0.01 |
| 399 | 20 | 5% | 3.3%–6.9% | <0.01 |
| 999 | 50 | 5% | 3.9%–6.2% | <0.01 |

- **"高置信不超标"（Wilks 型容许界）**：想以 95% 置信保证单批误放 ≤ α，用 max 规则需 N ≥ ln(0.05)/ln(1−α)：α=10% → 29，α=5% → 59，α=1% → 299。若要用第 k 大且仍保证 P(误放 ≤ 5%) ≥ 95%，k 最多为：N=100 → 2，N=200 → 5，N=500 → 17，N=1000 → 39。
- **max vs 分位数的取舍**：
  - max（k=1）：误放控制在"至少不超过 1/(N+1)"这一侧更稳，但对 N 敏感；N 变大时阈值上移，检出率下降。Boruta 再用多轮二项检验平均掉单轮抖动。
  - 分位数（k/(N+1) 固定）：误放率不随 N 漂移，N 增大只让它更精确；适合做"可配置误放率"。前提是 N 足够大（上表），否则单批波动很大。
  - mean / mean+3σ（feature-engine）：前者误放约 50%；后者依赖探针分布近似正态，重尾时（ΔAUC、IV 都右偏）会偏松。
- **按粒度分层**：可交换性只在同构类别内成立（Q3）。每层（行级 / 用户×天级 / 用户级 / 交叉 / 序列）各自需要上表规模的 N，不能把行级探针池借给用户级候选。mock 的数据说明了这一点：同样是纯噪声，用户级常量的 L1"观察"比例（30%）是行级（8%）的近 4 倍。
- **L1 vs L2 的成本差异**：L1 指标（IV、OOF 分桶 AUC 偏移）不训练模型，每层 200–500 个探针几乎没有成本，可以直接用经验分位数。L2 每个探针都要一次"基线 + 探针"的消融训练，每批几百个不现实。见 Q4 的参数化 null 与跨批次累积。

### Gaps
- 没有找到工业特征平台公开的"每层探针数 vs 误放率"实测；上表是理论值，需要在真实数据上用留一法核对（Q4）。

---

## Q3. 同构负对照的构造：块置换、交叉特征、序列特征、条件置换（CPT）

### Takeaway
负对照应是**候选本身的置换副本**，置换单元由零假设决定：用户级候选在用户之间整块置换；用户×天候选按要检验的问题选择块内（同一用户跨天）或块间（同一天跨用户）置换。交叉特征的增量零假设是"给定父特征无额外信息"，对应的同构对照是 f(a′, b)，其中 a′ 是 **a 在 b 的层内置换**（离散条件下的 CPT），而不是独立随机列。CPT 只要求对 X|Z 有近似模型，比完整 knockoff 好落地，而且在 X|Z 设错时，对最坏统计量它的 I 类错误膨胀不超过 CRT。

### Cited Findings
- Winkler 2014：块内可交换 = 只在块内置换；整块可交换 = 块整体互换、块内顺序不变 — [PMC4010955](https://europepmc.org/article/PMC/PMC4010955)
- CPT（Berrett, Wang, Barber, Samworth）：检验 X ⊥ Y | Z；**不重新抽 X，而是对已观测 X 值做非均匀置换**，权重来自 X|Z 的近似分布 q(·|z)，以保持 X 与 Z 的依赖；用并行成对交换 MCMC 实现，交换 (i, j) 的接受比为 q(X_π(j)|Z_i)·q(X_π(i)|Z_j) / (q(X_π(i)|Z_i)·q(X_π(j)|Z_j))（式 8，算法 1）— [arXiv 1807.05405](https://arxiv.org/abs/1807.05405) §4.1
- CPT 的 Z 为类别变量时，"按 Z 分组、组内置换"是经典做法；Z 连续时分箱再组内置换**不再保证** I 类错误，因为 X ⊥ Y | Z 推不出 X ⊥ Y | (Z ∈ 分箱 b) — 同上 §1
- CPT 有效性：q(·|z) 正确时 M+1 个三元组可交换（定理 1）；q 只需"正确到差一个基测度"（例如只对 X 的某个变换建模正确）即可有效；误设时 I 类错误膨胀以 d_TV(Q*ⁿ, Qⁿ) 为上界，最坏统计量下不超过 CRT — 同上定理 1、§3
- Model-X knockoff 要求 (X, X̃) 成对可交换（对全部特征的联合分布）— [arXiv 1610.02351 定义 3.1](https://arxiv.org/abs/1610.02351)；group knockoff 以组为发现单位 — [arXiv 1602.03589](https://arxiv.org/abs/1602.03589)
- NIPS 2003 的探针"从近似真实特征的分布中抽取"，即边际同构 — [NIPS 2003 analysis](https://proceedings.nips.cc/paper_files/paper/2004/file/5e751896e527c862bf67251a474b3819-Paper.pdf)
- Strobl：重要性偏差随类别数与量纲变化，有放回 bootstrap 会加剧 — [Strobl 2007](https://bmcbioinformatics.biomedcentral.com/counter/pdf/10.1186/1471-2105-8-25)

### Inferences（构造规则，供 R11 / #13 落地）
| 候选类型 | 零假设 | 同构负对照（shadow） | 说明 |
|---|---|---|---|
| 行级 x | x ⊥ y \| 基线 | 行级全局置换 perm(x) | 保持边际分布、缺失率、基数 |
| 用户级 x_u（用户内常量） | 用户间无信号 | **用户间整块置换**：把 x 的用户级取值表在用户间打乱再 join 回行 | 保持"用户内常量"结构、用户数、取值分布。mock 的 `probe_user_*` 在结构上已经同构 |
| 用户×天 x_{u,d} | (a) 无用户间信号 | 同一天内在用户之间置换 | 检验"跨用户区分度" |
| | (b) 无时间变化信号（超出用户均值） | 同一用户内跨天置换（块内） | 检验"时间维增量"，用户效应仍保留 |
| 交叉 f(a, b)，基线含 a、b | f(a,b) ⊥ y \| a, b | **f(a′, b)**，a′ = a 在 b 的层（离散 b 或 b 分箱）内置换；若 a 是用户级，在 b 层内按用户整块置换 | a′ ⊥ y \| (a, b) 且 (a′, b) 的联合分布近似 (a, b)，因此交叉后的基数与稀疏度同构。b 连续时分箱只是近似（CPT 原文的警告）；也可两个方向都做：f(a′, b) 与 f(a, b′) |
| 交叉（廉价版） | 噪声水平 | f(perm(a), b) | 只同构基数与稀疏度；a 与 b 的相关被打破，交叉列的分布可能变化 |
| 序列 s_u,t（ID / 类目序列） | 序列内容无信号 | 用户间整段置换序列（保留长度分布、元素频率） | 检验"序列内容"整体 |
| | 无时点信号 | 同一用户换用其他日期的序列快照（不得晚于样本时间，避免引入未来信息） | 检验"新近性 / 时点"增量 |
| | 无顺序信号 | 序列内打乱元素顺序 | 检验顺序 / 位置信息；与 3.3 节"统计代理 vs 压缩探针"对应 |
| target-aware 序列统计（命中次数等） | 同上 | 先对序列做上面的置换，再走**同一套**统计函数 | 函数同构，比直接置换统计结果更忠实 |

- **null importance（置换 y）在聚类数据上**：不应行级置换 y。应在用户之间整块置换 y 序列（保持用户内相关），或仅在用户内置换（检验"用户内变化"）。依据是 Winkler 的 EB 概念（推断）。
- **为什么不用完整 knockoff**：我们每批是"几十个候选 + 固定基线"的增量问题；knockoff+ 要求 (1 + #负) / #正 ≤ q，即至少选出 ⌈1/q⌉ 个特征才能报出任何发现（q=0.1 时 ≥ 10 个，由式 1.9 推出），批量小时功效受限；而且要对高维混合类型特征建联合分布。CPT 式的"对每个候选做条件置换副本"只需对单个候选建 X|Z 模型，或直接在离散层内置换，更适合逐候选的增量判定。

### Gaps
- 没有找到交叉特征"父特征条件置换"作负对照的已发表实践；上表是从 CPT/EB 原理推出的设计，需要在 mock 上验证（例如加入"交叉噪声"真值类）。
- 序列特征的负对照没有找到直接文献。

---

## Q4. 用负对照做经验校准（OHDSI 模型）并迁移到 ΔAUC / ΔLogLoss

### Takeaway
OHDSI 的做法可以直接搬过来：把每个负对照探针的 Δ_i 与其聚类 bootstrap 标准误 τ_i 视为"真增量为 0 + 系统误差"，按 Δ_i ~ N(μ, σ² + τ_i²) 用极大似然估 μ、σ；候选的校准判定用 Δ − z·√(σ̂² + τ²) > μ̂ + δ_min。σ̂ 正是"管线对这一类特征的系统性奖励"（如用户级记忆），μ̂ 是平均偏差。参数化拟合让 L2 每层只需 ~20–50 个探针就能给出平滑阈值，但要用留一法检查可交换性，并接受 Gruber 指出的功效损失。

### Cited Findings
- 模型：y_i ~ N(θ_i, τ_i²)，θ_i ~ N(μ, σ²)，极大似然估 μ、σ²；新估计 y_{n+1} ~ N(μ, σ² + τ_{n+1}²)，单侧 p 值由 Φ 计算；作者认为高斯够用，混合高斯与非参数估计没有改善 — [Schuemie 2014, PMC4285234 §2.6](https://europepmc.org/article/PMC/PMC4285234)
- 校准效果：负对照 p<0.05 的比例校准后为 6%、11%、5%（三种设计）— 同上 图 2
- 有效性前提：负对照与目标假设可交换；建议每次都做负对照留一法校准图 — [Schuemie 2016, PMC5108459](https://europepmc.org/article/PMC/PMC5108459)
- 风险：偏差非正态或均值/方差估计不准时，I 类错误可能保守或反保守；II 类错误显著上升 — [Gruber & Tchetgen Tchetgen 2016, PMC5012943](https://europepmc.org/article/PMC/PMC5012943)
- CI 校准：用合成正对照（在负对照上注入已知效应）拟合"系统误差均值与 SD 随真实效应量线性变化"的模型；只有负对照时默认假设误差与效应量无关；正对照由负对照派生，评估时按来源分组留一 — [EmpiricalCalibration CI vignette](https://cran.r-project.org/web/packages/EmpiricalCalibration/vignettes/EmpiricalCiCalibrationVignette.pdf)；[Schuemie 2018 PNAS 摘要](https://europepmc.org/article/PMC/PMC5856503)
- 本仓库现状：判定用"按用户聚类 Poisson bootstrap 的 CI 下界 > δ_min"；用户级常量探针在 LightGBM 下误放 17%，中位 ΔAUC +0.0018，CI 宽度 0.0083（样本级探针 −0.0006 / 0.0055）— `reports/calibration.md` §2、§4；`docs/总体方案设计.md` 3.2.2、7.1

### Inferences（迁移到 ΔAUC / ΔLogLoss 的具体公式）
- 每层 g（行 / 用户×天 / 用户 / 交叉 / 序列）、每个代理（LR、LightGBM）、每个指标分别拟合：
  - 输入：该层 n_g 个负对照探针的 (Δ_i, τ_i)，τ_i = 聚类 bootstrap 标准差（已有）。
  - 极大似然：max_{μ,σ≥0} Σ_i log φ((Δ_i − μ)/√(σ² + τ_i²)) − ½ log(σ² + τ_i²)。
  - 候选判定（单侧 α=2.5%，与现有单代理口径一致）：Δ_c − 1.96·√(σ̂² + τ_c²) > μ̂ + δ_min。σ̂ = 0、μ̂ = 0 时退化为现有规则，所以这是现有判据的**严格推广**。
  - 双代理"任一"合并：各自校准后取并，合并误放上界仍约 2×2.5%。
- **ΔLogLoss 的符号**：取 −ΔLogLoss（越大越好）后同样处理；logloss 增量对基线校准度敏感，负对照的 μ̂ 可能非零（例如加入噪声列导致轻微过拟合），这正是校准要吸收的部分。
- **用户级层的特殊含义**：mock 中用户级探针的 μ̂ > 0、σ̂ > 0，量化的就是"代理把用户级常量当 ID 记忆"的系统奖励。校准后，用户级候选必须超过"记忆一个用户 ID 能拿到的增益"才算入模。这正是 #13 的"与同批用户级随机探针比较"选项的统计化版本（是否应该这样做见 Q5）。
- **留一法自检**（Schuemie 2016 建议）：每个探针用其余探针拟合 (μ, σ)，算校准 p；画"p<α 的比例 vs α"。偏离对角线说明该层探针之间不可交换（例如探针生成方式混杂），或者高斯假设不成立。
- **正对照（回应 Gruber 的功效批评）**：按 OHDSI 的"注入"思路，在负对照上叠加已知强度的信号，例如 x_pc = shadow + λ·(已知有效特征的标准化值)，取 λ ∈ {小, 中, 大}，同时报告检出率曲线。现有 mock 的"弱增量"类可作 λ 小的一档。
- **探针数**：参数化 null 有两个参数，n_g ≈ 20–50 时 μ̂、σ̂ 已可用（推断）。L2 每批可只新增 20 个/层，并与最近若干批的探针**合并拟合**（前提：管线配置不变；配置一变就清空重来）。跨批 μ̂、σ̂ 的时间序列本身就是 A/A 式的管线监控。
- **L1 用非参数，L2 用参数**：L1 探针廉价，直接用经验分位数（Q2 表）；L2 用上面的高斯 null，并以经验分位数（跨批累积 ≥ 200 后）作交叉校验。

### Gaps
- 没有找到把 OHDSI 校准用在 ML 特征选择 ΔAUC 上的公开先例；上述迁移属于设计推断。
- ΔAUC 的系统误差是否近似正态未知（用户级层可能右偏）；需要在真实数据上看留一法校准图。若明显偏离，改用经验分位数或 t 分布 null。

---

## Q5. 用户 ID 记忆问题：分组验证、OOF / 有序目标统计、混合效应基线

### Takeaway
mock 里用户级常量随机数误放 17%，机制是"高基数且一一对应用户的取值 → 树模型学到用户效应 → 时间外推验证里同一批用户再次出现，记忆被兑现"。文献给出三条互补路线：(1) 新用户 holdout（GroupKFold 思想），让记忆无法兑现；(2) 在基线里加入不泄漏的用户目标统计（只用训练日、有序或 OOF），先把用户效应吸收掉；(3) 混合效应（随机截距）基线，例如 GPBoost。线上模型有用户 ID embedding，因此推荐 (2) 作为主口径，(1) 作为诊断，用户级 shadow 校准（Q4）作兜底。

### Cited Findings
- sklearn：若数据是"每个受试者多条样本"，而模型足够灵活、能学到个体特有特征，就可能无法泛化到新受试者；GroupKFold 保证同一组不同时出现在训练和测试中，"使检测这类过拟合成为可能" — [scikit-learn 3.1.2.4 Cross-validation iterators for grouped data](https://scikit-learn.org/stable/modules/cross_validation.html#group-k-fold)
- CatBoost：取值全部唯一的类别特征配 greedy TS，训练集一刀完美分类，测试集准确率 50%；LOO TS 仍泄漏；ordered TS（只用随机排列中的"历史"样本）同时满足无条件偏移（P1）与数据充分利用（P2） — [arXiv 1706.09516 §3.2](https://arxiv.org/abs/1706.09516)
- GPBoost（Sigrist）：把 boosting 与分组随机效应结合，作为"树 boosting 处理高基数类别变量"的新方案，可以对训练中未出现的新组做预测；模拟中 LightGBM 对**已有组**的预测优于 CatBoost，对**新组**则相反，作者解释为 LightGBM 能学到高基数类别变量的组效应，但方差更高、有过拟合 — [arXiv 2004.02653 §5、表 2 讨论](https://arxiv.org/abs/2004.02653)
- Strobl：树的变量选择偏好多取值 / 连续变量 — [Strobl 2007](https://bmcbioinformatics.biomedcentral.com/counter/pdf/10.1186/1471-2105-8-25)
- 本仓库 mock：用户级常量探针 LightGBM 误放 17%，LR 3%；按样本级重采样 27%；残差判据（线上分 + 候选）7% — `reports/calibration.md` §2；方案 3.2.1 已注明"代理没有 ID embedding"

### Inferences
- **机制确认（与 GPBoost 结论一致）**：1500 个用户、每人一个连续随机数，就等价于一个已排序的用户 ID；LightGBM 能切出用户组效应。valid 是最后一天、用户与训练集相同，所以这种记忆在验证集上是"真实有效"的。LR 做不到逐用户切分，所以只有 3%。
- **三条路线各自回答什么问题**：
  1. **新用户 holdout（时间外推 + 用户分组）**：train = 前几天 × 用户集 A，valid = 末日 × 用户集 B（A ∩ B = ∅）。随机用户常量在新用户上没有任何信息，真实用户属性（如设备、年龄段）仍然有效，因此这是最干净的判别实验。代价：样本减半，并且衡量的是"对新用户的泛化"，与线上分布（老用户占多数）不一致。**建议作为 #13 的诊断与校准实验，不作为主判据。**
  2. **基线加入用户历史目标统计**：在训练日上按用户计算 CTR/CVR 的平滑均值（贝叶斯先验平滑；训练行用 ordered 或 K 折 OOF，验证行用全部训练日），加入两个代理的基线。这样基线已经能"记住用户"，用户级随机探针的增量应回到 ≈ 0。剩下的增量才是"超出用户固定效应"的信息，这与线上有 ID embedding 的模型最对齐。CatBoost 论文说明训练行必须用有序 / OOF 计算，否则 TS 本身泄漏。
  3. **混合效应基线（GPBoost / 随机截距）**：效果等同路线 2 的"模型内版本"，统计上更规范，但要引入新依赖；可作为 V2 选项。
- **路线 2 之后的残余检查**：用户级 shadow（用户间整块置换）在新基线上的误放率应 ≤ 名义值。若仍偏高，说明 TS 平滑不足或泄漏，此时 Q4 的经验校准 σ̂ 会自动兜底。
- **为什么不建议只用"与同批用户级探针比较"**（第一轮已提，本轮补充依据）：GPBoost 的结果说明 LightGBM 学习组效应的能力随组数、每组样本数、树参数变化，所以"记忆奖励"的大小不稳定，阈值会随批次漂移。它还会把真实但弱的用户级特征一起压掉：真实特征的增量里也含同样的记忆成分（方案 3.2.1 已指出），但它是否超过阈值取决于信号强度与记忆奖励的相对大小。
- **残差分析（3.2.4）的作用**：线上分已含 ID embedding，所以"线上分 + 候选"天然吸收了用户效应。mock 中这一判据下用户级探针为 7%，接近名义值。它与路线 2 方向一致，可作为最终裁决，但依赖线上打分回放。

### Gaps
- 没有找到直接量化"每实体随机常量被 GBDT 当 ID 记忆"的论文；GPBoost 的组效应结论与 CatBoost 的唯一取值例子是最接近的证据。
- 没有找到"用户 TE 进基线后用户级探针误放率"的公开数据，需要在 mock 上实测（预期回到 ≈ 2.5% / 代理）。

---

## Q6. 校准协议（逐步，带默认值）

### Takeaway
一句话：**分层、同构、足量、校准、留一自检、正对照护功效。** 下面每一步的默认值都可以按 label 覆写；带"推断"的是本轮设计建议，不是文献给定值。

### Cited Findings（协议所依赖的已核事实，汇总）
- 置换 p 值 (1+#)/(1+M) — [CPT 式 3](https://arxiv.org/abs/1807.05405)；Boruta 多轮命中 + 二项检验 + Bonferroni — [Boruta.R](https://github.com/cran/Boruta/blob/master/R/Boruta.R)
- 块内 / 整块可交换 — [Winkler 2014](https://europepmc.org/article/PMC/PMC4010955)；离散条件下的层内置换与 CPT — [Berrett et al.](https://arxiv.org/abs/1807.05405)
- 经验 null N(μ, σ² + τ²)、留一法评估、正对照注入 — [Schuemie 2014](https://europepmc.org/article/PMC/PMC4285234)、[2016](https://europepmc.org/article/PMC/PMC5108459)、[CI vignette](https://cran.r-project.org/web/packages/EmpiricalCalibration/vignettes/EmpiricalCiCalibrationVignette.pdf)
- 校准的功效代价 — [Gruber 2016](https://europepmc.org/article/PMC/PMC5012943)
- 去随机化：多次运行，选择频率 ≥ η=0.5 — [Ren, Wei, Candès](https://arxiv.org/abs/2012.02717)
- 有序 / OOF 目标统计 — [CatBoost §3.2](https://arxiv.org/abs/1706.09516)；分组验证 — [sklearn GroupKFold](https://scikit-learn.org/stable/modules/cross_validation.html#group-k-fold)

### Inferences（协议）

**步骤 0：登记候选的结构类型**（元数据字段 `granularity ∈ {row, user_day, user, cross(a,b), seq}`、父特征、所属实体键）。没有登记就不能生成同构对照，评估拒绝运行。

**步骤 1：为每个候选生成同构 shadow（Q3 表）**
- 默认：每个候选 1 份自身 shadow 用于诊断展示；另按层生成通用探针池。
- 用户级 = 用户间整块置换；用户×天 = 同一天内跨用户置换（默认），可选同一用户内跨天置换；交叉 = f(a′, b)，a′ 在 b 的层内置换（b 连续时按 10 分位分箱）；序列 = 用户间整段置换。
- 每层再加"基线特征 + 噪声"的冗余型负对照 ≥ 5 个（落实 7.1 #6）。

**步骤 2：L1 阈值（决策 #14）—— 改用分层经验分位数，保留固定下限**
- 每层探针数 N_L1 = 199（默认，k=10 对应 5%；单批实际误放 90% 区间约 2.8%–7.8%）；要做"95% 置信 ≤ 5%"时用第 5 大（N=200）。
- "拒绝 / 观察"边界 = max(固定值 0.005, 该层探针 AUC 偏移的 95% 分位)；"观察 / 通过"边界 = max(固定值 0.02, 该层探针的 99.5% 分位)。IV 同理。固定值负责实用显著性，分位数负责统计显著性。
- 多重比较：一批候选数 m 较大时（交叉 500 个），"通过"线可改用经验 p 值 (1+#{探针 ≥ 候选})/(N+1) 加 BH 控制 FDR（推断；BH 需要 N ≫ m/q 才有分辨率，例如 m=500、q=0.1 时 N 至少几千，L1 成本仍可接受）。

**步骤 3：L2 增量（决策 #13 与 δ_min）**
- 3a. 基线加入用户历史目标统计（训练日内 5 折 OOF 或 ordered；验证日用全部训练日；贝叶斯平滑先验强度默认 20 条曝光）。LR 与 LightGBM 都加。
- 3b. 每层每批新增 n_L2 = 20 个探针，做消融（基线 vs 基线 + 探针），聚类 bootstrap 得 (Δ_i, τ_i)；与同配置最近批次合并，使每层累计 ≥ 50。
- 3c. 每层、每代理拟合经验 null (μ̂, σ̂)。判定：Δ_c − 1.96·√(σ̂² + τ_c²) > μ̂ + δ_min（δ_min 默认 0）。有害判定同理：上界 < μ̂。
- 3d. 留一法自检：该层探针的校准 p<0.05 比例应落在 [2%, 9%]（N=50 时的二项 95% 区间附近，推断）；超出则该层判定标"校准不可信"并回退到"人工 + 残差分析"。
- 3e. 诊断实验（每季度或管线变更时跑一次，不每批跑）：新用户 holdout 下重测用户级探针与用户级真实候选，确认步骤 3a 之后用户级 σ̂ 接近 0。

**步骤 4：去随机化**
- L2 对 shadow 种子与 bootstrap 种子各重复 R = 5 次（默认），候选"建议入模"的频率 ≥ η = 0.5 才最终建议（借 Ren 等的聚合形式；他们的误差保证针对 knockoff 基础程序，这里只借用其稳定化思想）。

**步骤 5：正对照与功效报告**
- 每层注入 3 档正对照：shadow + λ·z(已知有效特征)，λ 按"该层 ΔAUC 约为 1×、2×、4× 该层 τ 中位数"自动标定。报告每档检出率；最弱一档的检出率 < 50% 时，在报告中提示"本层功效不足"。

**步骤 6：监控与审计**
- 每批落库：每层 μ̂、σ̂、N、经验分位数、留一法校准曲线、正对照检出率。μ̂/σ̂ 跨批跳变（如超出近 10 批的 3σ）即触发管线审查（等价 A/A 检查）。
- 上线后（7.2 回测集）：用历史上线 / 下线特征与 AB 结论，核对"校准后建议入模"的真实命中率。

**对 mock 的直接修改建议（V1 前可做）**
1. `probe_names(n_probes=3)` → 每层 L1 ≥ 199、L2 ≥ 20；当前每批 max-of-3 的名义误放是 25%，解释了 L1"观察"比例偏高的一部分。
2. 新增真值类"交叉噪声"（f(a′, b)）与"序列噪声"，验证 R11 的构造。
3. 新增实验：基线 + 用户 OOF TS；以及新用户 holdout。比较用户级探针与"增量（用户级）"类的误放 / 检出，作为 #13 的定案证据。
4. 在 `calibrate` 报告里加每层 (μ̂, σ̂) 与留一法校准图。

### Gaps
- 步骤 2–5 的默认数值（199、20、R=5、平滑强度 20、λ 档位）是推断出的起点，没有外部文献给定，需要在 mock 与真实数据上调。
- BH + 经验 p 值在 N 有限时的 FDR 精确性（离散 p 值）未展开核对。
