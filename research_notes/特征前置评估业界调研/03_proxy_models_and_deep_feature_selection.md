# 代理模型 vs 生产模型的特征评估保真度，以及深度推荐/CTR 模型的特征选择与特征下线

> 调研方法说明：本会话网络策略屏蔽了 arxiv.org、semanticscholar.org、liner.com，无法直接抓取论文全文。以下结论主要来自检索引擎返回的摘要/摘录（链接均为原始出处），**具体表格数值大多未能从全文二次核对**，引用时请注意。标注 [未核全文] 的条目只核对过摘要级信息。

---

## Q1. GBDT/LR 代理模型上测得的特征价值能否迁移到深度模型？以及 init_score / 残差学习 / 生产模型热启动等增量评估手段

### Takeaway
没有找到直接检验“GBDT/LR 上的特征增益能否迁移到深度 CTR 模型”的公开研究。现有的间接证据指向**特征重要性在不同模型家族间排序不一致**，例如 Thumbtack 的 DCN-V2 与 GBDT 对比、表格深度学习基准中 NN 对噪声特征更敏感。基于生产模型分数的 init_score 残差拟合在 LightGBM 里有原生 API 支持，但没有找到把它当成标准特征评估方法的工业论文。至于“在生产模型上零初始化新增特征 embedding 后热启动”，只找到了专利和机制层面的依据。

### Cited Findings
- **代理模型与深度模型的重要性排序不一致（工业案例）**：Thumbtack 把搜索排序从 GBDT 迁到 DCN-V2 后，对比两者的特征重要性，发现变化最大的是 device 特征，它在 DCN-V2 中的重要性明显上升。作者认为可能与 GBDT 更擅长处理隐式特征交互有关，但承认原因尚待检验 — [Thumbtack Engineering, "Leaves to Neurons"](https://medium.com/thumbtack-engineering/leaves-to-neurons-using-deep-cross-networks-for-ranking-search-results-65b711731de8)
- **NN 对噪声/无关特征比 GBDT 更敏感**：表格深度学习的特征选择基准报告，神经网络（尤其 MLP）对噪声特征的敏感度高于 GBDT，做特征选择后两者差距缩小。由此推论，在 GBDT 上“无害”的弱特征放进 DNN 未必无害 — [A Performance-Driven Benchmark for Feature Selection in Tabular Deep Learning (2023)](https://arxiv.org/pdf/2311.05877)
- **GBDT 作为特征变换器、LR 作为上层的经典 stacking**：Facebook 2014 年的 GBDT+LR 混合模型比单独任一模型好 3% 以上。论文结论是“加入一个高价值特征或选对模型”的收益远大于数据新鲜度、学习率、采样等调参，并且历史类特征（用户/广告历史统计）主导了其他类型特征 — [He et al., Practical Lessons from Predicting Clicks on Ads at Facebook (ADKDD 2014)](https://ai.meta.com/research/publications/practical-lessons-from-predicting-clicks-on-ads-at-facebook/)
- **LightGBM init_score 机制**：`fit` 支持 `init_score`，验证集对应 `eval_init_score`。init_score 是 boosting 的起点（raw score / logit 空间），它和 `init_model`（从已存模型继续训练）是两种不同机制 — [LightGBM API docs](https://lightgbm.readthedocs.io/en/latest/pythonapi/lightgbm.LGBMModel.html); [CRAN lightgbm](https://search.r-project.org/CRAN/refmans/lightgbm/html/lightgbm.html)
- **init_score 的已知坑**：有用户把已有模型概率的 logit 作为 init_score 后，模型完全不再 boosting，预测停在初始值。该例子只有 6 行数据、`min_data_in_leaf=1`，帖子没有公认答案 — [StackOverflow 66890815 镜像](https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/66890815/lightgbm-usage-of-init-score-results-in-no-boosting)
- **向生产模型注入新特征、零初始化 embedding 热启动（专利层面）**：一项“加速训练”专利描述了 warm start 做法：新模型中与旧模型匹配的 embedding 复制旧值，新特征的 embedding 可初始化为零等定值 — [USPTO patent 12462200](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12462200)
- **零初始化扩宽网络在函数层面保持等价的条件**：对 φ(0)=0 的 ReLU 类激活，新增宽度的权重为零时，扩宽后网络的输出与原网络相同。存在归一化层时该结论不直接成立 — [When is Warmstarting Effective for Scaling Language Models? (2026), App. C.1](https://arxiv.org/pdf/2605.13405)
- **LPFS 专门为热启动设计**：Kuaishou 的 LPFS 指出，训练后部分 gate 恰好为 0、其余接近 1，因此删掉 gate=0 的特征不会破坏已训练模型，适合工业 hot-start 流程 — [LPFS (Kuaishou, 2022), arXiv 2206.00267](https://arxiv.org/pdf/2206.00267)
- **增量训练受分布变化影响**：腾讯 CTR 实践中，简单增量训练在后期 AUC 明显下滑，冻结部分参数后效果改善 — [腾讯 CTR 建模过程中的实践总结](https://www.6aiq.com/article/1634679557947)

### Inferences
- 对 R2（代理基线组成和在线分数版本未定义）：由于跨模型家族的重要性排序不稳定（Thumbtack 案例），代理模型只适合做**粗筛/排序**，不宜输出“上线后 AUC 能涨多少”这类绝对承诺。建议在文档中把代理结论定位为“必要非充分”，并定期用“代理增益 vs 真实生产增益”的历史配对数据做校准（rank correlation）。
- 残差分析中把在线分数 Platt 校准后作为 init_score：必须**冻结并记录**在线分数对应的模型版本和特征快照，否则基线一漂移，残差增益就不可复现。这与 R2 直接相关。另外要确认 init_score 是 logit 空间而不是概率，并在验证集上同时传入 `eval_init_score`，否则评估口径不一致。
- 残差拟合只用候选特征时，有一个系统性偏差：如果候选特征的信息已经以**非线性交互**形式被生产 DNN 吸收，残差几乎为零，评估结果是正确的；但如果候选特征的价值主要来自与已有特征的交互，单特征树在残差上可能低估它。这种情况下可以考虑同时提供少量关键已有特征来拟合残差。
- “生产模型零初始化注入 + 热启动短训”是保真度最高的增量评估方式。公开资料只能证明它机制上可行（专利、LPFS 的 hot-start 设计），没有找到公开的成本/准确度对比数据。

### Gaps
- 没有找到量化研究：GBDT/LR 测得的单特征增益与深度 CTR 模型 A/B 增益之间的相关系数。
- 没有找到以“stacking on production logits / 残差 boosting”作为**标准特征准入评估**的公开工业论文（Meta/阿里/字节等）。
- 没有找到公开的“feature injection with zero-init embedding”增量评估流程的效果数据。

---

## Q2. 深度推荐模型的特征选择方法及其报告结果

### Takeaway
深度推荐的特征选择大致分三类：**门控/掩码类**（AutoField、LPFS、OptFS）、**实例自适应类**（AdaFS、MvFS，在推理时仍需全部特征，不省特征生产成本）、**基于梯度/Taylor 的重要性打分**（SHARK）。ERASE 基准（KDD 2024）发现两阶段方法（先选后重训）比单阶段方法更稳定，并在商业平台上把延迟降低约 20%。各论文结果的复现差异很大，例如 AutoField 在后续论文中的复现 AUC 明显低于原文。

### Cited Findings
**基准**
- **ERASE (KDD 2024)**：在 4 个公开数据集、私有工业数据集和一个真实商业平台上评测 11 种特征选择方法（含传统方法和深度方法）。论文提出 AUKC 指标，衡量方法在不同保留特征数量下的稳健性。结论之一是**两阶段方法比单阶段方法结果更稳定**；在商业平台上，基于结论的优化把延迟降低约 20%，效果不降 [未核全文] — [arXiv 2403.12660](https://arxiv.org/abs/2403.12660); [ACM DL 10.1145/3637528.3671571](https://dl.acm.org/doi/10.1145/3637528.3671571)
  - 注：作者署名为 Pengyue Jia 等；检索摘要未写明商业平台属于哪家公司，未能确认。另有一个同名但无关的 2026 年“ERASE”推荐系统 unlearning 基准（[arXiv 2603.08341](https://arxiv.org/abs/2603.08341)），注意不要混淆。

**门控/掩码类（全局特征集）**
- **AutoField (WWW 2022，非 2021)**：用 AutoML 方式自动选择特征域，作者来自 CityU HK、USTC、腾讯。原文称在 Avazu 上**去掉 50% 特征域**后 AUC 为 0.7773、Logloss 为 0.3813，优于所有基线 — [AutoField, arXiv 2204.09078](https://ar5iv.labs.arxiv.org/html/2204.09078)
  - **复现差异**：AEFS（2025）论文的表格中，AutoField 去掉 37.5% 特征域后，Avazu/MLP 的 AUC 为 0.7584（无选择时 0.7763），Criteo/MLP 为 0.7963（无选择时 0.8025），也就是说复现结果**低于**不做选择的基线 — [AEFS, arXiv 2509.12076](https://arxiv.org/pdf/2509.12076)
- **LPFS / LPFS++ (Kuaishou, 2022)**：在输入层放置基于 smoothed-ℓ0 的可学习极化门控。作者批评“按权重幅度删特征”既缺乏理论保证，也会伤害效果。在 Kuaishou 部署时**从 332 个特征域中选出 177 个**（约去掉 47%），10% 流量的两周 A/B 测试中累计收入 +1.058%，social welfare +1.046% — [LPFS, arXiv 2206.00267](https://arxiv.org/pdf/2206.00267)
  - 注：任务描述中的“LPFS = Large-scale Personalized Feature Selection, 2023”有误，实际是 Learnable Polarizing Feature Selection (2022)。
- **OptFS (2023)**：把特征交互的选择分解为对两个相关特征的选择，给每个特征（而不是特征域）加可学习 gate，用 learning-by-continuation 训练。在 3 个公开数据集上同时提升效果、降低存储和计算 [具体数值未核] — [OptFS, arXiv 2301.10909](https://arxiv.org/abs/2301.10909)

**实例自适应类**
- **AdaFS (KDD 2022)**：用 controller 网络为每条样本打分，自适应选择特征，并称能很好地迁移到主流深度推荐模型 [数值未核] — [dblp: KDD 2022 pp.3309-3317](https://dblp.org/rec/conf/kdd/LinZW0W22)
- **MvFS (CIKM 2023)**：指出 AdaFS 会偏向高频特征，改用多视角子网络，每个子网络针对一类特征模式的数据子集独立对各特征域打分。第三方综述称，它在 MLP/DeepFM/DCN/IPNN 上均有提升，而且在其实验中**静态方法 AutoField、OptFS 不如不做选择** [数值未核] — [MvFS, arXiv 2309.02064](https://arxiv.org/pdf/2309.02064); [Korea Univ. 记录](https://pure.korea.ac.kr/en/publications/mvfs-multi-view-feature-selection-for-recommender-system/)
- **AEFS (2025)**：表格显示，它在激活参数少 37.5% 的情况下与 AdaFS/MvFS 效果相当 — [AEFS, arXiv 2509.12076](https://arxiv.org/pdf/2509.12076)

**梯度/Taylor 重要性类**
- **SHARK (Kuaishou, CIKM 2023)**：用 Taylor 展开的一阶项作为特征域（embedding table）的重要性分数来剪枝，再配合 row-wise 差异化量化。Kuaishou 在短视频、电商、广告多个模型上做了 A/B 测试，短视频场景的压缩模型**存储节省 70%、效果不降**（摘要后半句“thousands of …”被截断，应是机器资源节省，未核实）— [SHARK, arXiv 2308.09395](https://arxiv.org/abs/2308.09395); [ACM DL 10.1145/3583780.3615499](https://dl.acm.org/doi/10.1145/3583780.3615499)
- **TayFCS (2025)**：沿用 Taylor 思路做特征组合选择，基于训练好的模型只需一次反向传播即可计算 — [TayFCS](https://www.alphaxiv.org/ja/abs/2507.03895)

**Embedding 维度搜索**
- **AutoDim (WWW 2021)**：端到端可微地为每个特征域计算各候选维度的权重，按最大权重得到离散结构后重训（arXiv 预印本原题 "Memory-efficient Embedding for Recommendations"）— [AutoDim, arXiv 2006.14827](https://ar5iv.labs.arxiv.org/html/2006.14827); [AMiner](https://aminer.cn/pub/60b9a257e4510cd7c8f7903e/autodim-field-aware-embedding-dimension-searchin-recommender-systems)

**新近工作（只看到标题/摘要）**
- FairFS（2026）讨论深度特征选择中的偏差 — [arXiv 2602.20001](https://arxiv.org/pdf/2602.20001)；Light-FMP（2026）做特征与模型联合剪枝 — [arXiv 2605.06441](https://arxiv.org/pdf/2605.06441)；LeAP（2026）提出可学习自适应 permutation 特征选择 — [arXiv 2606.01111](https://arxiv.org/pdf/2606.01111)。[均未核全文]

### Inferences
- 实例自适应方法（AdaFS/MvFS）在推理时仍需要全部特征的值，**不能省特征生产与存储成本**，只能降低部分计算。下线决策应该参考全局方法（LPFS、SHARK、两阶段的 ERASE 方案）。
- LPFS 和 SHARK 是两个**有工业 A/B 数据**的“生产模型内部打分”方案：前者在 Kuaishou 去掉约 47% 的特征域、收入 +1.06%；后者在短视频场景省 70% 存储、效果不降。它们都**直接在生产 DNN 上**评估特征，可作为代理模型之外的第二通道，尤其适合下线评估。
- AutoField 复现结果与原文差距明显（0.7584 vs 原文报告的约 0.777），而且 MvFS 的实验中静态方法不如不做选择。这说明这类 NAS/门控方法的结论对实现和超参很敏感，上线前必须**重训加 A/B 验证**，这也与 ERASE“两阶段更稳”的结论一致。
- 关于 FiBiNET/SENet 字段权重、注意力权重作为重要性：本次没有找到系统对比其作为特征选择依据可靠性的工作。LPFS 对“权重幅度≠重要性”的批评同样适用于这类方法。

### Gaps
- ERASE 中 11 种方法的完整排名、Shapley/permutation 等浅层方法与门控方法的对比细节、商业平台的名称：均未能读取全文。
- AdaFS、OptFS、MvFS 的具体 AUC 数值未核。
- 没有找到 FiBiNET SENet 权重或 attention 权重用于特征下线的公开评估。

---

## Q3. 业界特征下线（offboarding）实践：决策依据、冗余特征组联合删除、风险、非劣效框架

### Takeaway
公开资料中特征下线的主流做法有：定期做 leave-one-feature-out（LOFO）或分组消融，加上重要性打分（Taylor/门控），再结合成本。核心风险是 CACE（改变任何东西就改变一切）和相关特征的替代效应。逐个 LOFO 时，相关特征互相掩护，可能**每个都显示可删**，但一起删掉就会掉点。因此必须用分组消融或条件重要性做联合确认。Meta 风格的 IEFF（2026）提出在 serving 端逐步“淡出”特征而不是突然置零，减少了 50–55% 的线上效果损失。没有找到明确使用“非劣效检验”术语的公开工业文档。

### Cited Findings
- **冗余遗留特征是 ML 技术债的典型形态**：特征 F 早期加入，后来被新特征取代成为冗余却无人察觉；还有“bundled features”，在截止期压力下打包加入，其中部分特征价值很低。建议**定期做穷举的 leave-one-feature-out 评估**来发现并删除不必要的特征。CACE 原则指出，删除任何特征 x_j 都可能引起全局变化 — [Sculley et al., Hidden Technical Debt in ML Systems (NeurIPS 2015)](https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf)
- **IEFF：serving 端渐进淡出，免重训下线**：作者称传统下线流程依赖“突然置零加显式重训”，会造成分布突变；特征效率改动通常需要 3–6 个月的重训周期和大量 GPU。IEFF 在 serving 时逐步调整特征覆盖率和分布，借助模型的周期性 recurring training 自适应，并配有 guardrail、可回滚机制和监控。结果是下线 rollout 提速约 5 倍、无额外重训 GPU 开销，**渐进淡出比突然删除少了 50–55% 的线上效果下降** [公司归属检索未确认，可能是 Meta] — [IEFF, arXiv 2605.00324 (2026)](https://arxiv.org/abs/2605.00324)
- **特征删除框架专利**：通过计算模型所用特征的重要性分数来删除特征，以降低训练和推理开销 [受让方未确认] — [USPTO 11720808 "Feature removal framework to streamline machine learning"](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11720808)
- **相关特征下 permutation importance 不可靠**：对强相关特征做无约束 permutation 会迫使模型在训练分布外外推，重要性因此失真。建议改用条件重要性（从条件分布中 permute）或 drop-and-relearn / permute-and-relearn，后者没有外推偏差但每个特征都要重训，代价高 — [Hooker, Mentch & Zhou, Unrestricted Permutation Forces Extrapolation](https://arxiv.org/abs/1905.03151); [TRIP (2025) 综述 relearn 方法](https://arxiv.org/html/2507.07276v1)
- **条件 PFI 的实现**：用决策树构造条件子组，在子组内 permute，以保持联合分布 — [Molnar et al., DMKD 2023](https://link.springer.com/doi/10.1007/s10618-022-00901-9)
- **工业中按“单特征移除的 AUC 损失”排序**：RAMP（2026，非 Meta）逐一移除个性化特征，用 AUC 下降量给特征排序 — [RAMP, arXiv 2607.17473](https://arxiv.org/pdf/2607.17473)
- **LPFS 批评按权重幅度删特征**：权重幅度不能保证代表重要性，并可能伤害效果 — [LPFS](https://arxiv.org/pdf/2206.00267)
- **新增特征的边际收益递减**：需要和计算/内存成本权衡 — [腾讯云：CTR 预估模型的进化之路](https://cloud.tencent.com/developer/article/1005416)

### Inferences
- 对 R10（下线缺少联合确认）：公开证据支持三层流程。① 单特征打分做初筛（代理 LOFO、生产模型内的 Taylor/门控分数）；② 对候选删除集合中**相关性高的特征按组做联合消融**（drop-group-and-retrain，或条件/分组 permutation），确认整组删除后的效果；③ 线上用 IEFF 式的渐进淡出（覆盖率 100%→0%）配合 guardrail 和回滚。Hooker 等的结论说明，只做逐个 permutation/LOFO 会在相关特征上同时产生“高估”（外推）和“低估”（互相替代）两类错误。
- 对 ADR-0004（上线用优效检验，下线用非劣效检验）：这个框架在统计上是自洽的。下线的原假设应为“删除后效果劣于基线超过 margin δ”，要证明的是“不比基线差超过 δ”。需要注意的是：(a) 多个特征一起删时 δ 应作用于**整组**，而不是每个特征各用一个 δ，否则多个“各自非劣”的删除会累积成显著劣化，这正是 R10 的风险；(b) 多次下线批次之间也存在 δ 累积（“温水煮青蛙”），建议设一个周期性的累计 δ 预算。公开文献没有找到明确采用非劣效术语的推荐系统下线案例，这是基于临床试验统计惯例的推断。
- IEFF 报告的“渐进淡出比突然删除少 50–55% 效果损失”说明：**离线非劣效通过不等于线上平滑无损**，下线发布方式本身就影响结果。

### Gaps
- 没有找到阿里、字节、快手等公开的特征下线流程文档（阈值、审批、成本模型）。
- 没有找到公开数据给出“多个冗余特征逐个评估可删、合并删除却掉点”的量化案例。
- IEFF 的公司归属未能确认。

---

## Q4. ID 类 / 用户级常量特征在特征评估中的处理（记忆化、高基数泄漏）

### Takeaway
树模型会把用户级常量特征（如用户画像中取值几乎唯一的字段）当成用户 ID 来记忆。这在机制上等价于 target statistics 的目标泄漏，也就是 CatBoost 论文所说的 prediction shift。公开的缓解方法有：有序/out-of-fold 的目标统计、时间外验证集、对高基数特征做平滑或分桶。没有找到专门针对“特征前置评估里树代理记忆用户 ID”的工业文献。

### Cited Findings
- **目标统计导致的泄漏与 prediction shift**：用目标统计替换类别值会引入一种特殊的目标泄漏，造成预测偏移。CatBoost 的 ordered TS 只用随机排列中位于当前样本之前的样本计算编码，并加先验平滑以减少稀有类别的噪声；ordered boosting 保证每个样本的梯度来自没见过它标签的模型 — [Prokhorenkova et al., CatBoost (NeurIPS 2018), arXiv 1706.09516](https://ar5iv.labs.arxiv.org/html/1706.09516)
- **ID 特征冷启动与泛化特征替代**：腾讯实践指出，未训练的 ID embedding 会让预测偏向 0.5，建议逐步用泛化特征替代 ID 特征，或做在线学习 — [腾讯 CTR 建模过程中的实践总结](https://www.6aiq.com/article/1634679557947)
- **Facebook GBDT+LR 中历史统计特征占主导**：用户/广告的历史特征占据主导地位。这类特征和 ID 一样承载了“记忆”信息 — [Facebook 2014](https://ai.meta.com/research/publications/practical-lessons-from-predicting-clicks-on-ads-at-facebook/)
- **AdaFS 偏向高频特征**：MvFS 指出实例自适应选择会过度偏好高频出现的特征 — [MvFS](https://arxiv.org/pdf/2309.02064)

### Inferences
- 树代理把用户级常量特征当作 ID 记忆，等于在评估中引入了“用户身份”信息。如果训练集和验证集共享用户（随机切分），增益会被高估。缓解措施：(1) **按用户分组切分或时间外切分**做验证，看增益是否保持；(2) 对比“候选特征”和“随机生成的用户级常量（伪 user-ID）”的增益，后者作为记忆化基线，候选特征的增益必须显著高于它；(3) 限制树的 `min_data_in_leaf` 或对高基数特征做分桶/频次截断；(4) 在残差框架下，如果生产 DNN 已经有 user ID embedding，残差中的用户偏置已被吸收，候选特征的“伪 ID 增益”自然会变小。这一点可以作为残差分析优于独立代理模型的论据，但前提是 init_score 来自含 user ID 的生产模型。
- 以上是基于泄漏机制的推断，没有找到公开的工业案例直接验证。

### Gaps
- 没有找到专门讨论“特征评估代理中的 ID 记忆化”或“伪 ID 对照”的公开论文或工业博客。
