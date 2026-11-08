# 代理模型 vs 生产深度模型、残差/热启动评估、深度推荐特征选择与特征下线：第二轮核验与深化

> 方法：本轮网络可访问 arxiv.org，以下论文都下载了 PDF 全文，用 pdftotext 抽取后逐条核对。标记含义：
> - **[已核原文 + 位置]**：数字或表述已在原文对应位置核实；
> - **[更正]**：第一轮的表述有误或口径不准；
> - **[仍未核]**：本轮仍无法取得原文。medium.com 和 patentsgazette.uspto.gov 在本会话不可达，Google Patents 拒绝自动请求。
>
> 对应设计文档：`docs/总体方案设计.md` 3.2.1（双代理）、3.2.4（残差分析）、5.4（下线评估）、ADR-0004（入模优效 / 下线非劣效）；评审问题 R2、R10。
> 每节分为“Cited Findings”（有出处的事实）和“Inferences”（本文推断）。推断部分不应当作文献结论引用。

---

## Q1. 第一轮标注条目的逐条核验

### Takeaway
多数核心数字已在原文中核实，但有四处需要更正：
- IEFF 的作者单位确认是 **Meta**（广告排序平台）。
- SHARK 的“节省 70% 存储”是**特征剪枝 + 行级量化的合并效果**，单靠特征剪枝（F-Permutation）只把内存降到 60%。
- ERASE 的商业平台在论文里没有点名，但作者来自华为诺亚方舟实验室，线上指标是视频 vv 和播放时长。
- AutoField 的“复现掉点”取决于复现方：AEFS 的复现确实明显掉点，但 MvFS 的复现中 AutoField ≈ 不做选择。

美国专利 12462200 属于 Pinterest，权利要求中写的是“从旧模型特征 warm-start”，**权利要求中没有出现“零初始化”**。

### Cited Findings

**IEFF（arXiv 2605.00324，2026-05）**
- [已核原文 + 首页作者栏] 27 位作者全部署名 Meta（USA），例如 Jieming Di、Xiaoyu Chen、Ying She 等。第一轮写的“公司归属未确认”现已确认 — [IEFF, arXiv 2605.00324](https://arxiv.org/abs/2605.00324)
- [已核原文 + Abstract] 原文称：传统特征效率类改动依赖重训，迭代周期 3–6 个月；IEFF 让效率类 rollout 提速 5 倍，消除重训带来的 GPU 开销；渐进淡出（fading）比突然删除少 50–55% 的线上效果下降。Introduction 中的措辞是“prevents **up to** 50–55%” — [IEFF](https://arxiv.org/pdf/2605.00324)
- [已核原文 + §5.2] 线上 QRT（Meta 内部 A/B 框架）对比：top 50 个稀疏特征**直接置零**造成 0.83% 的线上效果回退，**渐进淡出**只回退 0.37%，损失约减少 55%。置零后出现瞬时尖峰，需要额外 **70–100 亿训练样本**才能恢复；淡出则平滑收敛 — 同上
- [已核原文 + Table 2] 离线 recurring training 中，覆盖率从 100% 降到 0% 的窗口内，每日 NE 绝对增量如下：Top 50 sparse (CTR) 置零 0.10%/天，淡出 0.05%/天；Top 30 sparse (CTR) 置零 0.04%/天，淡出 0.02%/天；Top 2 embedding (CVR) 置零 0.15%/天，淡出 0.075%/天。所有配置都约减少 50% — 同上
- [已核原文 + Table 3，§5.3] 覆盖率从 90% 逐日降到 0% 时，以淡出为 100% 基准，置零在 90–70%、70–40%、40–10%、10–0% 各阶段分别为 ~99.8%、~99.4%、~99.6%、~99.7%。**中段（70%–40%）差距最大，为 −0.6%** — 同上
- [已核原文 + §3.3] 机制如下：
  - 由中心化控制面和 serving 端 feature adapter 在线上调整特征的**覆盖率**（该请求是否带此特征）或**分布**（改变取值但不删除）。
  - 调整后的值同时用于推理并写入日志，供 recurring training 使用，从而保持训练和 serving 一致。
  - 淡出由“开始时间 + 淡出速率”参数化，速率由上线前的 fading QRT 确定。
  - 已验证的速率范围是每天 1%–10%。生产 rollout 用保守的 **1–2%/天**，边界实验和隐私类紧急下线用 5–10%/天。
  - 监控 NE 和业务指标，超过阈值时自动暂停或回滚。回滚时直接恢复原覆盖率，不需要重训 — 同上
- [已核原文 + §4.4/Table 1] 部署规模：2024–2026 年共淡出 **275 个特征，分 14 个批次**。速率从早期的 10%/天调整到大规模时的 1–5%/天。每个批次平均省掉约 10 次全量重训，累计约 140 次，年基础设施成本下降约 15% — 同上
- [已核原文 + §7 Limitations] 作者自述的局限：对于**强非线性交互或模型高度敏感的特征**，小幅覆盖率变化也可能带来不成比例的影响，仍可能需要显式重训。另外，淡出速率目前依赖人工 QRT 选择 — 同上

**LPFS（arXiv 2206.00267，Kuaishou）**
- [已核原文 + §4.7] 原文：“feature superset contains **332** feature fields … from which we select **177** features”，“online A/B test for **two weeks in July 2021** … increased the cumulative revenue by **1.058%** and the social welfare by **1.046%**, during the A/B test of **10% traffic**”。对照组是“之前线上使用的 SOTA 方法”，实验中“除输入特征域外不做任何改动”。离线方面，用 14 天日志评测，LPFS 的 AUC 相对 permutation importance 提升 0.209%，相对旧线上特征集提升 0.304% — [LPFS](https://arxiv.org/pdf/2206.00267)
- [已核原文 + §4.7] 多次运行选出的特征子集高度重合，作者以此说明方法稳健。已部署到 Kuaishou“数十个广告场景” — 同上
- [已核原文 + §4.8–4.9] 热启动细节：
  - 在预训练（或线上）checkpoint 上插入 gate。为保证插入前后模型输出不突变，**把所有 gate 函数除以其初始值，使初值为 1.0**。
  - 若基于线上 checkpoint 做选择，可以省掉预训练阶段。
  - T2 与 T1 的比例，pdftotext 抽出的是“about 14 𝑇1”，疑为 ¼ 的分式排版丢失，**以原文 PDF 为准** [仍未核确切值] — 同上
- [已核原文 + Fig.7 说明] 另一个 Kuaishou 工业离线数据集有 392 个特征域（250 个 user、46 个 item、96 个 combine），带 5 个辅助任务 — 同上
- [更正-补充] 原文 §1 提到，permutation、Gumbel-softmax、SE 类方法都**无法输出精确为 0 的重要性**，只能在连续直方图上卡阈值。LPFS 的极化 gate 让“删除前后模型不变”，这一点对热启动友好 — 同上

**SHARK（arXiv 2308.09395，CIKM 2023，Kuaishou）**
- [已核原文 + Abstract/§5] 原文：“For the short-video scenarios, the compressed model without any performance drop significantly saves **70% storage and thousands of machines**, improves **30% QPS**”。结论部分写的是“压缩 70% 存储后平均观看时长没有下降”。服务规模为 3 亿以上 DAU，100% 用户 — [SHARK](https://arxiv.org/pdf/2308.09395)
- **[更正]** 70% 是 **F-Permutation（特征剪枝）+ F-Quantization（行级混合精度）合并**后的效果。Table 4 的数据是：F-P 单独把内存降到 60%，F-Q 单独降到 50%，合并后降到 30%（=50%×60%）。合并版的 AUC 依次为 Click 0.7279（−0.05%）、Like 0.7493（−0.04%）、Follow 0.7941（+0.04%）。因此**单靠特征下线节省的是约 40% 的 embedding 内存**，不是 70% — 同上，Table 4
- [已核原文 + §3.1.1，式(1)–(4)] Taylor 打分细节：
  - permutation 误差定义为“把第 i 个域换成其他样本取值后的期望 loss 减去原 loss”。
  - 一阶 Taylor 近似为 error(i,x) ≈ ∂loss/∂v_i* · (E[v_i] − v_i*)，即**该域 embedding 的梯度与“域均值 embedding − 本样本 embedding”的内积**。
  - 复杂度从 O(|DATA|·N·T) 降到 O(3·|DATA|)：一次算均值，一次前向加反向。
  - 作者试过二阶展开，效果与一阶相近 — 同上
- [已核原文 + §3.1.2–3.1.3/Algorithm 1] 剪枝流程如下：
  - **迭代剪枝**：每轮只删得分最低的 f 个表，默认 f=1。理由是“信息耦合，删一些后其余的重要性会变”。
  - 每轮删除后**用小样本 fine-tune**恢复收敛，再重新打分。
  - 停止条件是内存降到 rate_c，或效果低于 T_accuracy。原文写“精度下降超过 0.15% 视为显著，因此 T_accuracy 设为基线的 99.25%”。0.15% 与 99.25% 在原文中不自洽，**照录存疑**。
  - 线上 A/B：基线和压缩模型各 10% 流量，持续 7 天。业务约束是“省 >40% 内存且精度降 <0.15%” — 同上
- [已核原文 + §4.2/Table 2] 在工业数据集（短视频精排主模型，180 个特征，百亿参数，MMoE 多任务）上，F-P 的打分耗时 1 小时、剪枝总耗时 1 天；FSCD、LASSO 打分各 3 天，Permutation 6 小时。在 Criteo 上，删掉少量特征（剩余域 >19 个）时“精度损失几乎为 0”，作者解释为特征域间信息高度耦合 — 同上

**ERASE（arXiv 2403.12660，KDD 2024）**
- [已核原文 + 首页] 作者来自 CityU HK（Pengyue Jia、Yejing Wang、Xiangyu Zhao 等）和**华为诺亚方舟实验室**（Zhaocheng Du、Yichao Wang、Bo Chen、Huifeng Guo、Ruiming Tang）。致谢中写明有 Huawei Innovation Research Program 资助 — [ERASE](https://arxiv.org/pdf/2403.12660)
- [已核原文 + §3.2/图例] 11 种方法分三类：浅层方法 Lasso、GBDT、RF、XGBoost；门控类 AutoField、AdaFS、OptFS、LPFS；敏感度类 Permutation、SHARK、SFS。backbone 有 DeepFM、W&D、DCN、FiBiNet — 同上
- [已核原文 + §3.2 观察] 原文：“The two-stage approach yields more stable results compared to the single-stage method across different backbone models”。作者给的理由是：两阶段方法筛出的特征组合在搜索阶段之后可以独立存在，而单阶段方法每次训练都要重新学习重要性 — 同上
- [已核原文 + §3.6] 线上实验内容：
  - 把部分 benchmark 改造并接入“our feature factory”，做冗余特征剔除。
  - 实验组**去掉 30% 特征**，在一个**时延敏感的线上推荐平台**上用 **5% 流量（约 100 万用户）**跑了 **1 周**。
  - 结果：推理**时延降低约 20%**，**vv（视频播放量）和平均播放时长持平**。
  - **原文没有点名平台**。由华为作者和视频指标推断，大概率是华为的某个视频业务 [推断，未核实] — 同上
- [已核原文 + §3.5] 工业离线实验在 FibiNet backbone 上选出 top 5 方法。**SHARK、AutoField、Permutation 能去掉约一半特征（80 个）而不掉精度**；AutoField 的 AUKC 最高；LPFS 在工业集上表现与公开集不一致，作者归因于极化模块敏感 — 同上

**AutoField（arXiv 2204.09078，WWW 2022）vs AEFS（arXiv 2509.12076）和 MvFS 的复现**
- [已核原文] AutoField 的作者是 Yejing Wang、Xiangyu Zhao（CityU）、Tong Xu（USTC）、Xian Wu（Tencent）。在 Avazu 的消融表（Table 3）中，AutoField 行的 AUC 为 0.7773、logloss 为 0.3813，去掉 11 个域 [1,5,7,8,12,13,15,16,18,19,21] — [AutoField](https://arxiv.org/pdf/2204.09078)
- [已核原文 + AEFS 主表] AEFS（TKDE 稿，2025）中，Avazu / MLP 的 No FS 为 0.7763，AutoField 为 0.7584（logloss 0.3823 → 0.3908）；Criteo / MLP 的 No FS 为 0.8025，AutoField 为 0.7963。AEFS 为了公平比较**统一删掉 37.5% 的域**，原文 AutoField 删的是 50%，口径不同。AEFS 原文称 AutoField “shows a significant decrease in AUC and Logloss across three datasets and all backbone” — [AEFS](https://arxiv.org/pdf/2509.12076)
- **[更正-补充]** MvFS（NAVER，CIKM 2023）Table 1 的复现结果中，AutoField 与不做选择基本持平。Avazu 上 MLP/DeepFM/DCN/IPNN 的 No Selection 为 .7823/.7836/.7839/.7864，AutoField 为 .7823/.7830/.7841/.7862；OptFS 为 .7814/.7850/.7859/.7861；AdaFS 为 .7832/.7835/.7854/.7837；MvFS 为 .7866*/.7871*/.7884*/.7898*。Criteo 上 No Selection 为 .8040/.8094/.8059/.8093，AutoField 为 .8038/.8095/.8060/.8093，OptFS 为 .8027/.8043/.8065/.8082。所以第一轮综述转述的“静态方法不如不做选择”**只对 OptFS 的部分设置成立，对 AutoField 的准确表述是“≈ 不做选择”** — [MvFS](https://arxiv.org/pdf/2309.02064)
- 结论：同一方法在三个复现中，AutoField 原文、MvFS、AEFS 的表现分别是“优于基线”、“持平”、“明显掉点”。复现差异是事实，但幅度取决于复现方的设定 — 以上三篇

**OptFS（arXiv 2301.10909）**
- **[更正]** 会议是 **WWW 2023**（ACM Web Conference 2023，Austin）。作者有 Fuyuan Lyu（McGill）、Xing Tang（FiT, Tencent）等。摘要只给出定性结论：在三个公开数据集上提升效果，并降低存储和计算。具体数值本轮没有逐表核对 — [OptFS](https://arxiv.org/pdf/2301.10909)

**MvFS（arXiv 2309.02064，CIKM 2023）**
- [已核原文] 作者来自 NAVER 和 UIUC。核心论点：AdaFS 只有单个 controller，容易偏向高频的主要特征；MvFS 改用多个子网络（MoE 思路），并让选择从 soft 逐步过渡到 hard（s_n = 0.5(1+tanh(τ(I_n − l)))，τ = max(5, 1+0.001t)）— [MvFS](https://arxiv.org/pdf/2309.02064)

**AdaFS（KDD 2022）**
- [部分核实] 作者 Weilin Lin、Xiangyu Zhao、Yejing Wang、Tong Xu、Xian Wu，KDD 2022 第 3309–3317 页 — [dblp](https://dblp.org/rec/conf/kdd/LinZW0W22)。方法是用 controller 给每个样本的每个特征域打分（soft 加权或 hard 丢弃）— [CityU 记录](https://rims.cityu-dg.edu.cn/en/publications/adafs-adaptive-feature-selection-in-deep-recommender-system/)。论文自报的 AUC 数值 [仍未核]，未找到 arXiv 版本。第三方复现数值见上面的 MvFS 和 AEFS 表格。

**Thumbtack GBDT → DCN-V2**
- [仍未核] medium.com 在本会话不可解析，本轮无法核对原文。第一轮的表述（device 特征在 DCN-V2 中重要性显著上升，原因待证）维持原状。

**表格基准中的噪声特征（Grinsztajn 2022；Cherepanova 2023）**
- [已核原文 + §5.3 Finding 2] Grinsztajn、Oyallon、Varoquaux（NeurIPS 2022 Datasets & Benchmarks，arXiv 2207.08815）的做法是按 RF 重要性逐步删特征，GBT 在删掉一半特征以内时精度几乎不受影响。结论是“MLP-like architectures are not robust to uninformative features”：删除无信息特征会缩小 MLP 与树模型的差距，增加无信息特征会拉大差距 — [Grinsztajn et al.](https://arxiv.org/pdf/2207.08815)
- [已核原文 + §4/§6] Cherepanova 等（arXiv 2311.05877，UMD、NYU、Capital One）发现：
  - MLP 比 XGBoost 更容易对无信息特征过拟合，而 **FT-Transformer 对噪声特征的稳健性与 XGBoost 大致相当**。
  - 在“高斯噪声额外特征”的设定下，用 **XGBoost / RF 的重要性给 MLP 做特征选择，与 Deep Lasso 等方法持平**；给 FT-Transformer 做选择时，RF/XGBoost 最好。
  - 但在 corrupted 或二阶（交互）额外特征的设定下，Deep Lasso 明显更好 — [Cherepanova et al.](https://arxiv.org/pdf/2311.05877)
  - 第一轮写的“NN 比 GBDT 更敏感”需要**收窄为“MLP 类”**，Transformer 类不一定。

**Hooker、Mentch、Zhou 对 permutation 的批评（arXiv 1905.03151）**
- [已核原文 + Abstract/§1] 标题是“Unrestricted Permutation forces Extrapolation: Variable Importance Requires at least One More Model, or There Is No Free Variable Importance”，后发表于 Statistics and Computing。观点如下：
  - permute-and-predict 打破了特征间的依赖，迫使模型外推到数据稀疏区域，从而**大幅高估相关特征**的重要性。
  - 推荐两类替代：按其他特征**条件生成**扰动值，或 **re-learning**（permute-and-relearn，或 LOCO 直接丢弃后重训）— [Hooker et al.](https://arxiv.org/pdf/1905.03151)

**美国专利 US 12,462,200 B1**
- [已核原文 + 首页] 名称为“Accelerated Training of a Machine Learning Model”，**申请人/受让人 Pinterest, Inc.**，发明人 Xi Liu、Jiajing Xu、Erzhuo Wang，申请日 2021-05-20，授权日 2025-11-04 — [USPTO PDF](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12462200)
- [已核原文 + 权利要求 9、13] 权利要求的内容：取第一个（旧）模型的 processing features，与新模型的初始训练特征合并；用户可以增删改；初始化后训练第二个模型。claim 13 写的是“initializing comprises **warm-starting** at least one feature … from a processing feature of the first machine learning model”。**权利要求中没有“新特征零初始化”的表述**。第一轮的“零等定值初始化”可能出自说明书，本轮没有逐页核对说明书 [仍未核] — 同上

### Inferences
- 引用这些数字时，SHARK 应写成“特征剪枝约省 40% embedding 内存，与量化合并后省 70%”；ERASE 应写成“华为系作者，某视频平台，去掉 30% 特征，时延 −20%”。
- IEFF 的 −0.83% 与 −0.37% 是 Meta 删掉 **top 50**（按重要性挑选的大批）稀疏特征时的数据。删除低价值特征时，置零与淡出的差距可能更小，这一点是推断，原文没有报告低价值特征的对照。

### Gaps
- Thumbtack 原文、专利说明书中的零初始化段落、AdaFS 原文数值、OptFS 主表数值、LPFS 中 T2/T1 的确切比值：本轮均未核到。

---

## Q2. 残差 / 热启动评估怎么设计才正确（R2：代理基线组成、在线分数版本）

### Takeaway
没有找到把“生产 logit 作 offset 加候选特征 boosting”作为**标准特征准入方法**的公开工业论文。可直接借鉴的一手做法有两类，都是在**生产 checkpoint 上原位改动后短训**：LPFS 在线上 checkpoint 上插入初值归一为 1 的 gate；SHARK 每删一个表就用小样本 fine-tune。工程细节方面，LightGBM 源码确认传入 init_score 后不再执行 boost_from_average。设计上必须固定“哪个模型版本、哪次打分、哪段样本”的分数，并且只在评估窗口之前的数据上做校准。

### Cited Findings
- [已核原文：LightGBM 源码] `GBDT::BoostFromAverage` 只在 `models_.empty() && !train_score_updater_->has_init_score()` 时把初始分设为标签均值。所以**一旦给了 init_score，平均值起点就被跳过**，boosting 完全从给定的 raw score（binary 时为 logit）出发 — [LightGBM src/boosting/gbdt.cpp](https://github.com/microsoft/LightGBM/blob/master/src/boosting/gbdt.cpp)
- [已核原文：Parameters 文档] `boost_from_average`（默认 true）只用于 regression、binary、multiclassova、cross-entropy，作用是把初始分调到标签均值；另外，`init_score` 不会写入 save_binary 生成的二进制数据集 — [LightGBM Parameters](https://github.com/microsoft/LightGBM/blob/master/docs/Parameters.rst)
- [已核原文] LPFS 在已训练好的模型上插 gate 时，把 gate 函数除以初值、使初值为 1，以保证“插入前后模型性能无突变”。基于线上 checkpoint 选特征可以省掉预训练。这是“在生产模型上原位做函数等价改动，再短训评估”的一手先例 — [LPFS §4.8–4.9](https://arxiv.org/pdf/2206.00267)
- [已核原文] SHARK 每删一个 embedding 表，就从训练集抽一小部分（DATA_support）fine-tune 恢复收敛，再在测试集上打分。作者明确说“从随机初始化重建太耗时；由于改动很小，用少量数据重训即可再次收敛” — [SHARK §3.1.2](https://arxiv.org/pdf/2308.09395)
- [已核原文] Pinterest 专利 claim 13 描述了从旧模型 warm-start 新模型特征的训练框架，没有给出成本或精度数据 — [US 12,462,200](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12462200)
- [已核原文] IEFF 指出 Meta 的模型通过 recurring training 持续在新日志上训练。它的“淡入 / 淡出”同样适用于 feature migration（fade-in 新表示、fade-out 旧表示）。这说明在持续训练体系里，“**新特征从 0 覆盖率渐进加入生产模型**”是一种已落地的上线方式，但论文没有把它当作评估方法来报告 — [IEFF §4.2](https://arxiv.org/pdf/2605.00324)
- 第一轮已引用：零初始化的新增宽度在 φ(0)=0 激活下函数等价，存在归一化层时不直接成立 — [arXiv 2605.13405 App. C.1](https://arxiv.org/pdf/2605.13405)（本轮未重核）

### Inferences（设计建议，非文献结论）
1. **“在线分数版本”至少要固定 5 个字段**（回应 R2）：模型版本 ID 或 checkpoint 时间戳；打分方式（serving 日志中的实际分数，还是离线用同一 checkpoint 回放）；特征快照时间点（防止回放时用到未来特征）；是否经过线上校准层或 bias 修正（例如负采样校正）；样本窗口。推荐优先使用**serving 时刻记录的 logit**：它与线上实际决策一致，不需要回放。如果只能回放，必须用评估窗口开始前就冻结的 checkpoint。若用评估窗口内已增量更新过的 checkpoint，该模型已经“见过”评估样本的标签，残差会被系统性压低，候选特征的增益会被低估。
2. **校准只能在评估窗口之前的数据上拟合**，或者只用 train 切分拟合、在 valid 上冻结。Platt 只有两个参数，泄漏有限，但 eval 必须传对应的 `eval_init_score`。LightGBM 的 `predict()` 输出的 raw score 是否包含 init_score 需要实测：经验上不包含，需要手动加回 [仍未核]。
3. **基线对照必须同构**：“线上分 + 候选”要对比“线上分 + 同样结构的空模型”，即同样的树数和正则、只喂常数或随机置换后的候选特征。不能直接对比“线上分本身”，否则 boosting 的少量自由度本身就会带来纠偏收益，把这部分误计为候选特征的价值。这与 3.2.1 的负对照思路一致。
4. **交互低估**：只用候选特征拟合残差，测不到“候选 × 已有特征”的交互。建议提供“候选 + 少量 top 已有特征”两个版本，取差值。
5. **保真度最高的通道是热启动**：在生产 checkpoint 上加一个零初始化的新 embedding 或 gate（初值使输出不变），用评估窗口前的数据短训，再在评估窗口上比较。LPFS 和 SHARK 都证明了“在生产 checkpoint 上原位改动 + 小样本恢复”在工业上可行，但**没有公开文献给出这种做法用于特征准入时的成本或准确度数据**。可以把它列为 L3（高成本、高保真）通道，只对代理和残差评估结论冲突的特征触发。

### Gaps
- 没有找到量化“残差 boosting 增益 vs 线上 A/B 增益”相关性的公开研究。
- 没有找到“零初始化 embedding 热启动短训”用于特征准入的成本 / 精度对比数据。

---

## Q3. 特征下线的具体流程（R10：联合确认、顺序、累计预算、渐进淡出、影子删除）

### Takeaway
已发表的工业流程中，最具体的是 SHARK 和 IEFF。SHARK 的离线流程是**迭代地每轮删一个表、小样本 fine-tune、重新打分，并设绝对精度阈值和内存目标作为停止条件**。IEFF 的线上流程是**按 1–2%/天渐进淡出覆盖率，用 QRT 选速率，设 NE 护栏和一键回滚**，并给出了置零与淡出的定量对比。ERASE 的工业经验是两阶段方法（选完再重训）更稳；冗余特征可以去掉一半而不掉点。这些都支持“组级联合确认 + 累计预算 + 渐进执行”。但“非劣效”这个术语和“累计 δ 预算”在公开推荐系统文献中仍然没有直接出处。

### Cited Findings
- **迭代顺序与重打分**：SHARK 每轮删得分最低的 f 个表（默认 1 个），理由是删除后其余特征的重要性会因信息耦合而变化，因此删完要 fine-tune 并重新打分。停止条件是达到内存目标，或效果低于绝对阈值 T_accuracy。注意这个阈值是**相对原始基线**的累计阈值，不是每步的阈值 — [SHARK §3.1.2–3.1.4](https://arxiv.org/pdf/2308.09395)
- **冗余的普遍性**：SHARK 在 Criteo 上删少量域时精度损失几乎为 0；ERASE 工业集上 SHARK、AutoField、Permutation 都能去掉约一半（80 个）特征不掉点；LPFS 在 Kuaishou 332 个域中保留 177 个后收入还涨了 — [SHARK](https://arxiv.org/pdf/2308.09395); [ERASE §3.5](https://arxiv.org/pdf/2403.12660); [LPFS §4.7](https://arxiv.org/pdf/2206.00267)
- **两阶段（先选再重训）更稳** — [ERASE §3.2](https://arxiv.org/pdf/2403.12660)
- **不同打分法挑出的特征不同**：ERASE 的 Spearman 热图显示，AutoField（门控）与 Permutation（敏感度）的排序**最不相似**。门控类擅长找信息丰富的特征，Permutation 擅长找信息少、冗余的特征。LPFS 与 OptFS 相似；SHARK 与 SFS 相似，两者都基于梯度 — [ERASE §3.7](https://arxiv.org/pdf/2403.12660)
- **渐进淡出的量化收益与速率**：数字见 Q1（−0.83% vs −0.37%；中段差距最大；1–2%/天；275 个特征分 14 批）— [IEFF](https://arxiv.org/pdf/2605.00324)
- **IEFF 的安全治理**：上线前必须通过 fading QRT；只对显式指定的特征淡出；用策略约束范围、速率、时长；监控 NE 和业务指标，超阈值时自动暂停或回滚；回滚只需改配置，不用重训 — [IEFF §3.4](https://arxiv.org/pdf/2605.00324)
- **相关特征的打分偏差**：permute-and-predict 会高估相关特征；应改用条件扰动或 drop-and-relearn — [Hooker et al.](https://arxiv.org/pdf/1905.03151)
- 第一轮已引用：Sculley 等建议定期做 leave-one-feature-out，并提出 CACE 原则 — [NeurIPS 2015](https://papers.neurips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf)

### Inferences（给 5.4 / ADR-0004 的具体流程建议）
1. **组级联合确认**（回应 R10）：
   - 把候选下线集合按相关性或冗余聚类（|ρ| 或互信息），一簇一组。
   - **非劣效检验对整组的 drop-and-retrain 做**，ε 作用于整组。不能逐个通过后再合并。
   - 这样做的依据是 Hooker 的相关特征偏差和 SHARK 的“删后重要性会变”。
2. **顺序**：采用 SHARK 式的贪心迭代，即删最低分的一组，然后重训或热启动 fine-tune，再重新打分，再删下一组。不要一次性按初始排名删光。
3. **累计非劣效预算**：
   - 照 SHARK 的做法，把阈值设为**相对“本轮下线开始前”的固定基线**，每批 Δ 累计扣减，用完即停。
   - 跨季度时也要以某个固定锚点版本为准，防止“每次都非劣、累计显著劣化”。
   - SHARK 的阈值是精度降低 0.15% 量级，只能作为数量级参考，不能直接照搬。
4. **打分来源双通道**：Permutation 类和门控类的排序差异很大（ERASE）。建议下线初筛同时看“生产模型内 Taylor 分数”（SHARK 式，几乎零成本）和代理 LOFO。两者都低才进提案，与设计文档 5.4 中“双代理都非劣”的精神一致。
5. **执行方式**：用 IEFF 式的渐进淡出代替设计文档 5.4 中的“停止进入新训练样本”。
   - 速率参考 1–2%/天，即 50–100 天到 0。若需更快，先用小流量实验验证速率。
   - **中段覆盖率（约 70%–40%）是风险最高的区间**，监控应在这一段加密。
   - 淡出后的值要同时用于推理和训练日志，避免训练与 serving 不一致。
6. **影子删除（shadow removal）**：公开文献中没有找到这个术语的工业流程。可以落地的近似做法是：在线上 serving 上并行跑一个“置零或淡出”的影子模型，只记录分数、不参与决策，用来比较 NE。不过影子模型不会经历 recurring training 的自适应，测到的结果接近“置零”的上界损失。这是推断。

### Gaps
- 没有找到明确使用“non-inferiority / 累计 margin 预算”术语的推荐系统下线案例。
- 没有找到“影子删除”的公开工业描述。
- 没有找到量化“逐个 LOFO 可删、合并删除却掉点”的公开案例（SHARK 只给出了定性理由）。

---

## Q4. GBDT 与 DNN 之间特征价值的迁移

### Takeaway
现在有了一项直接的推荐场景证据：ERASE 在 4 个公开 CTR 数据集上，用 GBDT、XGBoost、RF、Lasso 的重要性给深度推荐模型选特征，**总体上差于敏感度类和门控类方法**。在 Avazu（特征取值高度集中）上树方法明显变差，在 Criteo 上表现尚可。ERASE 还发现**深度 backbone 之间迁移相对一致**。跨领域的 SHAP 排序相关性研究显示，树与树之间 Spearman 约为 0.58–0.84，树与 NN 之间只有约 0.18–0.36。因此代理（GBDT/LR）结论只能作为必要而非充分的粗筛。

### Cited Findings
- [已核原文 + §3.3] ERASE 原文：“Overall, sensitivity-based feature selection methods outperform gate-based feature selection methods, both of which are superior to shallow feature selection methods.” 作者把浅层方法的劣势归因于“过于简单，无法刻画特征间复杂关系”。需要注意的是，§3.2 在峰值性能上的结论是“门控类优于浅层和敏感度类”，§3.3 用 AUKC 衡量稳健性时，则是敏感度类最好。两节都把浅层方法排在最后 — [ERASE](https://arxiv.org/pdf/2403.12660)
- [已核原文 + §3.2] ERASE 观察到：“XGBoost and GBDT … perform poorly on the Avazu dataset but well on the Criteo dataset”，原因是 Avazu 的特征取值集中在少数域，树模型容易过拟合，影响重要性评估。另一条观察：“The effectiveness of feature selection methods remains relatively consistent across different backbone models”（DeepFM、W&D、DCN、FiBiNet）— 同上
- [已核原文 + §3.7] ERASE 的 Spearman 热图中出现三个簇，即浅层、门控、敏感度三类方法各自内部相似。这说明树模型重要性的排序与深度方法的排序属于不同的簇 — 同上
- [已核原文 + Table 4/5] 一项人脸识别验证场景的分位数回归研究（Therezien & Clémençon，arXiv 2607.04431）中，mean |SHAP| 排序的 Spearman 相关如下：LightGBM 与 sklearn GBDT 之间为 0.58–0.84；NN 与树模型之间为 0.18–0.36。领域不同，外推需谨慎 — [arXiv 2607.04431](https://arxiv.org/pdf/2607.04431)
- [已核原文] Cherepanova 等在表格 NN 上发现：当额外特征是纯噪声时，XGBoost/RF 重要性作为 MLP 的选择器与最好的方法持平，对 FT-Transformer 甚至最好；**当额外特征是 corrupted 或二阶交互时，树方法不如 Deep Lasso**。RF 与 XGBoost 的排序高度相关 — [arXiv 2311.05877](https://arxiv.org/pdf/2311.05877)
- [已核原文] Grinsztajn 等发现 MLP 对无信息特征不稳健，而树模型对删掉一半低重要性特征不敏感 — [arXiv 2207.08815](https://arxiv.org/pdf/2207.08815)
- [仍未核] Thumbtack 的 GBDT → DCN-V2 案例（device 特征重要性上升）。

### Inferences
- **噪声或冗余特征的下线判断**在 GBDT 和 DNN 之间迁移较好（Cherepanova：随机噪声设定下各方法排序相关度最高；ERASE：冗余剔除时多种方法都能删一半）。**新特征的准入、交互或高基数类特征**的迁移较差（Cherepanova 二阶特征设定；ERASE 中 Avazu 上树方法失效；ADR-0004 中“只有深度模型能用的增益被保守拒绝”）。由此可以推出一个不对称的使用方式：代理模型做下线初筛相对可信，做准入时只能当粗筛。这与 ADR-0004 的不对称方向一致。
- 建议 7.1 的校准实验加一项：在历史上线或下线的特征上，统计“代理 Δ”与“生产模型 Δ（或 A/B Δ）”的 Spearman 相关，作为代理折扣系数的经验依据。目前没有公开文献给出 CTR 场景下的这个数值。

### Gaps
- 没有找到 CTR 或推荐场景下“GBDT 单特征增益 vs 深度模型 A/B 增益”的定量相关研究。ERASE 只比较了排序方法之间的相似度和下游 AUC，没有给出与线上增益的相关性。
