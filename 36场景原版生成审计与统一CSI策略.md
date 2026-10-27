# 36 个 DeepMIMO 源场景的原版生成审计与统一 CSI 策略

日期：2026-10-27。

## 1. 明确结论

**当前 CSI 脚本有必要修改，而且不应只把反射次数从3改大，或简单打开所有开关。**

若目标是“尽可能完整、高保真、可解释的静态室外 CSI”，当前脚本有三类优先问题：

1. **响应定义**：目前使用原始 `paths.a` 的兼容表示；需要显式增加以 Sionna 基带 CIR/CFR 为准的物理载频相对响应，不能继续把两者混称为同一种 CSI。
2. **几何适配**：目前建筑导出为重复顶点的三角形集合；绕射依赖共享边拓扑，不能未经修复就宣布已支持正确建筑绕射。
3. **物理与数值完整性**：默认只算 LOS 和镜面反射，漫散射、绕射、植被等未进入默认方案，也没有完成采样预算、深度、路径容量与 RX 分批的收敛评估。

**可以统一的是一套物理定义、材料与几何规范、求解策略和质量门槛；不能在没有验证的情况下给出一组固定数字并保证它是“全城最优”。**

统一策略不等于按建筑来源切换原追踪规则。组合城市已是新场景，一条路径可能经过来自纽约、上海和 Boston 的建筑；其传播必须统一求解，不能在跨来源边界时突然改用不同算法或把旧路径拼接起来。

本报告是只读审计和建议：核对了36份本地官方参数、当前三城来源、官网36条场景记录、官方后端文档与当前代码。**没有修改生成算法，没有运行 RT，没有开展大规模基准。**

## 2. 证据范围：查到了什么，没有查到什么

### 2.1 本地与网络证据

- 本地 [DeepMIMO 源数据](<data/deepmimo/>)：36个来源的对象、顶点、参数；本次逐一解析了36份 `params.json` 的标准字段和 `raw_params`。
- 官网 [场景目录](https://deepmimo.net/scenarios)与其公开 [场景元数据 API](https://deepmimo.net/api/scenarios)：本次36个来源都匹配到 v4 记录，核对追踪器、反射次数、散射/绕射/透射标记、射线数和路径深度。
- 官网[纽约详情页](https://deepmimo.net/scenarios/v4/city_0_newyork_3p5)：实际打开核对了追踪器、频率和发布版本。目录页面可取得多数场景详情链接，但**没有声称逐一完整复原了36个原始 InSite 工程**。
- NVIDIA [Sionna 2.2.0 PathSolver API](https://nvlabs.github.io/sionna/rt/api/paths_solvers.html)、[官方技术报告的限制部分](https://nvlabs.github.io/sionna/rt/tech-report/S3.html#SS4)、[Paths API](https://nvlabs.github.io/sionna/rt/api/paths.html)、[材料 API](https://nvlabs.github.io/sionna/rt/api/radio_materials.html)。
- Remcom [X3D 官方说明](https://www.remcom.com/wireless-insite-em-propagation-software/high-fidelity-ray-tracing)：用于解释原后端的精确路径修正、Adjacent Path Generation（APG）等能力，不把厂商一般能力当作每个场景必然启用的功能。
- 当前 [几何适配器](<scripts/CSI-generate/city_geometry.py>)与[CSI 生成器](<scripts/CSI-generate/generate_city_csi.py>)，以及本机安装的 Sionna RT 2.2.0 源码。

证据优先级：**下载包实际参数与 raw 字段 > 官网概括字段 > 场景名称或通用教程**。但参数文件仍是配置记录，不是对实际输出路径和测量精度的独立认证。

### 2.2 官网确实存在字段冲突

14个早期美国城市的官网目录 `advancedParameters.pathDepth=25`，而本地参数记录 `max_path_depth=4`、`max_reflections=3`、`max_diffractions=1`。

这些场景的 raw APG 也保存了 `path_depth=25`。因此，**不能看到网页的25就认定原版追踪了25次物理反射**；这可能涉及不同层级字段或版本差异，本次没有证据证明具体映射原因。

官网的 `maxReflections`、散射/绕射标记等主要字段与本地配置相符。详情页纽约的旧发布版本与本地转换版本也不完全相同。结论是公开目录有助于交叉核对，但不能替代逐层读包内配置。

## 3. 36 个来源实际上怎么生成

### 3.1 原版共同点

本地36份参数一致记录：

- 追踪器均为 **Remcom Wireless InSite**，30个版本3.3、6个版本3.3.0。
- 载频均为 **3.5 GHz**。
- 标准化 `num_rays=259200`，raw 的 `ray_spacing=0.25`，uniform发射，方位360°/俯仰180°范围。
- `synthetic_array=true`，原始天线记录为 isotropic、vertical。
- 所有场景 `max_transmissions=0`，不是“原版把能开的传播机制都打开”。
- 地形反射开启，地形绕射和散射关闭；这不等于建筑绕射/漫散射关闭。
- raw APG 均启用；原版并不是只靠一个简单固定射线预算逐 RX 完全独立追踪。
- 保存的 diffuse 随机相位选项为 false，final-interaction-only为true；漫散射是否真正生效还要看 enable，不看参数是否存在。

**259,200 不能照搬成 Sionna 的“等效最佳预算”。**后端的初始方向、候选修正、APG、路径容量和交互采样不同，同一个计数不代表同样的采样覆盖或误差。

Remcom 对 APG 的说明是：先在较粗接收集合追踪，再利用这些路径的交互关系为密集接收点构造精确路径。它不是简单把粗网格复数 CSI 线性插值到细网格。我们目前脚本没有实现 InSite APG。

### 3.2 五组配置

下表深度是本地标准化 `max_path_depth`，R/D/S/T分别表示对应的上限记录，不是所有组合都必然生成。

| 分组 | 场景数 | 深度 | R反射 | D绕射 | S散射 | T透射 | raw漫散射启用 |
|---|---:|---:|---:|---:|---:|---:|---|
| ASU | 1 | 7 | 6 | 1 | 1 | 0 | 是 |
| Boston | 1 | 4 | 4 | 0 | 0 | 0 | 否 |
| 早期美国城市 | 14 | 4 | 3 | 1 | 1 | 0 | 是 |
| 中期国际城市 | 14 | 5 | 4 | 1 | 0 | 0 | 否 |
| 后期六城市 | 6 | 6 | 5 | 1 | 1 | 0 | 是 |

因此，36个中：**35个记录了绕射；21个启用了漫散射；0个开启透射。**

另有两个值得注意的差异：ASU原始波形带宽100 MHz，其余35个10 MHz；这不是当前训练数据必须照搬的 OFDM 带宽。ASU、Boston的 APG 深度还分别为10和50，其余为25；不要与上表物理路径深度混用。

### 3.3 来源与当前三城的实际对应关系

- 1 km：435个建筑资产、665个实例，实际建筑来自30个来源。
- 2 km：890个资产、2,306个实例，实际建筑来自32个来源。
- 4 km：1,317个资产、13,838个实例，36个来源全部实际使用。

核对时以资产 ID 建映射，而非把 ID 当数组下标；未发现失效实例引用、缺失建筑面材料键或拷贝材料记录与对应源定义不一致。

这里验证的是**来源与数据结构一致性**，不是材料参数准确或三城传播正确。详细36条配置见文末附表。

## 4. 为什么不能把36种配置按“最大值”拼成一个最好方案

### 4.1 追踪配置不属于建筑资产本身

“上海建筑”没有一种与生俱来的5次反射规则。反射上限是原来整个上海场景一次仿真的搜索配置，不是导入该建筑时必须继承的属性。

正确做法：保留每个面的材料来源，对新城市使用统一追踪规则。不能让同一条传播路径进入来自 Boston 的墙面就禁用绕射，走到另一个来源的墙面又恢复绕射。

### 4.2 最大值不等于最准确

- 更高反射深度需要更多搜索预算，否则只是扩大了尚未充分采样的路径空间。
- 不可靠的材料/表面散射系数可能比漏掉极弱高阶路径造成更大误差。
- 增加来源没有提供新城市的实测通道、墙体层结构、树木含水率或车辆状态。
- 更多返回路径也可能来自错误网格接缝、重复面片或不稳定的漫散射采样。
- 全波方法也不能在现有粗建筑数据上凭空恢复真实细节，更不能直接把公里级城市全波仿真当成本项目可用的默认选项。

所以，“最优”应定义为：**在给定场景/天线/物理模型条件下，对目标信道统计和复数响应满足明确误差门槛，同时记录尚未建模的不确定性。**

## 5. 当前脚本必须优先处理的具体问题

### 5.1 P0：物理基带响应与 DeepMIMO 兼容表示分开

当前实现读取原始 `paths.a`，之后对频偏进行指数叠加，默认还采用 DeepMIMO式缩放与延迟窗，见[系数提取](<scripts/CSI-generate/generate_city_csi.py#L194-L209>)与[合成函数](<scripts/CSI-generate/generate_city_csi.py#L80-L105>)。

若原始系数记为 $b_p$，Sionna定义的静态物理基带系数为：

$$
a_p=b_p\exp(-j2\pi f_c\tau_p),
\qquad
H_{r,m}(\nu)=\sum_p a_{r,m,p}\exp(-j2\pi\nu\tau_p).
$$

依据：[Sionna Paths官方文档](https://nvlabs.github.io/sionna/rt/api/paths.html)。比较时须明确 `normalize_delays=False`，接收机同步作为后续独立步骤。

**建议决策**：物理基带 CFR 作为新的主输出；如果需要复现特定 DeepMIMO Sionna converter，再单独提供有明确名称的兼容适配。不要用“deepmimo/centered”一个开关同时混合控制系数语义、频点、尺度和延迟裁剪。

- 频率轴、系数类型、幅度尺度、时延参考分别定义。
- 保存原始路径及未同步物理信道，另导出训练用同步/RMS结果。
- 物理 CFR 不因绝对时延大于 $N/B$ 就自动删路径；CP、接收窗口、同步和滤波单独建模。
- 用至少双径的复数结果对照 Sionna 原生 `cfr()`，而不只是“单径幅度一样”。

此前将 `cir()` 加基带频偏指数称为重复计算载波，是错误判断。当前推荐改主输出，是因为明确了物理 CSI 目标，**不是又把同一套约定随意来回切换**。变更应有模式名称、测试与输出版本边界。

### 5.2 P0：修绕射拓扑，而不只是加开关

[当前建筑导出](<scripts/CSI-generate/city_geometry.py#L191-L206>)对每个三角形重新追加3个顶点，再按材料分网格；[加载场景](<scripts/CSI-generate/generate_city_csi.py#L153-L163>)未明确请求重复顶点合并。

而后端的楔边相邻面由**同一网格的拓扑边**寻找，不仅是两个顶点坐标看起来一样。这使得当前方案不能保证建筑墙角被识别为预期楔边。

修改方向：

1. 输出共享索引的网格，并在同一建筑内按受控容差焊接顶点。
2. 保持三角化前后的面映射，排除平面内部三角形对角线成为假绕射边。
3. 检查法向、边方向、退化面、非流形、T形接缝、重面和共面重叠。
4. 加载后核对楔边数量与几何：不能只检查输出 OBJ 文件。
5. 处理跨材料屋顶/外墙边的拓扑；**每个材料网格内部焊接仍不等于跨材料共享边已连接**。若后端不支持所需的多材料楔边形式，须采用受验证的适配或明确报告近似，不能假装已解决。
6. 自由边缘绕射只对真实屏幕/薄边界开启，不用于补救所有断开的三角形接缝。

本机后端的具体证据：[共享边查找使用 `mesh.opposite_dedge`](</Users/z-jiuri/.envs/miniconda3/envs/lcm/lib/python3.11/site-packages/sionna/rt/utils/wedges.py#L75-L103>)、[SceneObject去重参数与加载](</Users/z-jiuri/.envs/miniconda3/envs/lcm/lib/python3.11/site-packages/sionna/rt/scene_object.py#L104-L144>)。这些是当前安装版本源码路径，不是未来版本的永久约束。

官方 [SceneObject说明](https://nvlabs.github.io/sionna/rt/api/scene_object.html)与[绕射教程](https://nvlabs.github.io/sionna/rt/tutorials/Diffraction.html)可作接口/小场景验证依据。保留源绕序不自动等于后端法向正确；实际加载还存在法向翻转约定。

### 5.3 P1：默认传播范围不足

当前[求解器设置](<scripts/CSI-generate/generate_city_csi.py#L139-L146>)为 LOS＋镜面反射、深度3，其他机制默认关闭。这低于35个源场景的绕射覆盖，也低于21个源场景的散射覆盖。

但在 Sionna 2.2.0 中，开全部选项仍有后端限制。官方技术报告明确写道：

> “The path solver supports only first-order diffraction and does not handle paths that contain both diffraction and diffuse reflection.”

出处：[Sionna技术报告3.4节](https://nvlabs.github.io/sionna/rt/tech-report/S3.html#SS4)。

因此当前后端支持的统一模型可包含：

- 多次镜面反射；
- 至多一次绕射，可与支持的镜面/透射链结合；
- 包含漫反射的多次交互链；
- **不包含同一路径上的漫散射＋绕射组合，也不包含多次绕射。**

不能对“缺失组合路径通常能量较小”的一般说明不加验证地套用到新城市的深 NLOS；也不能把独立几次运行简单相加，声称补全了同一路径的混合交互。

### 5.4 P1：散射系数与能量分配需要统一语义

当前使用的 Sionna `RadioMaterial` 将镜面反射振幅乘 $\sqrt{1-S^2}$，漫散射振幅乘 $S$。即反射能量内部划分与 $S^2$ 有关，而不是看到“coefficient=0.2”就理解为20%功率。

如果材料 $S>0$，但求解时关闭漫散射，省略的那部分不会自动全部返还为镜面反射。开启漫散射补入的是**该模型假设的分量**，不代表真实粗糙墙面的测量结果。

本地源记录的材料差异：

- 多数来源 concrete 使用 directive模型、系数0.2；wet-earth常为0.4。
- 14个国际来源材料虽写 directive，场景级 diffuse disabled；不能据材料字段认定原版启用了漫散射。
- Boston材料 model=none，虽保留非零数值，不能直接强行激活为相同散射模型。
- 当前适配会把 model=none 的散射置零；这是显式适配选择。

修改时需核对源 InSite 系数的场/功率定义、lobe归一化、XPD与Sionna的含义，材料名称相同不够。不能为了“更完整”统一把所有面设置为 $S=1$，那会抹掉镜面分量。

官方[散射教程](https://nvlabs.github.io/sionna/rt/tutorials/Scattering.html)和[材料说明](https://nvlabs.github.io/sionna/rt/api/radio_materials.html)支持能量/材料模型核验；不会为我们提供当地墙面的真实粗糙度。相干漫散射还需评估相位、随机性、种子与采样密度下的统计稳定性。

### 5.5 P1：材料频率与植被不能绕过去

当前建筑面材料与源记录一致，但这不等于它们是新城市的实测材料。

- 28个较早城市源中有 `Asphalt_1GHz`；当前合成道路也用带1 GHz参考标记的沥青数值，在3.5 GHz运行。
- [适配器保留参考频率](<scripts/CSI-generate/city_geometry.py#L304-L311>)，但生成器创建常数材料时不会自动按参考频率转换。
- 应采用有依据的频率响应/ITU经验族或显式常数近似＋敏感性，不要仅改掉频率标签。
- 源 Boston 简化植被体绑定 concrete，不能直接拿“绿色几何＋混凝土材料”当真实树木传播。
- 目前植被只用于排除 UE 点，根本没有进入 RT；植物下方不撒点不等于考虑了穿林损耗、树干遮挡和体散射。

植被需要独立有效模型和参数（频率、穿越深度、季节/密度等），或明确输出无植被基线与参数化敏感性。添加一个通用散射开关不能解决体积植被传播。

### 5.6 P1/P2：透射、天线、近场和边界

**透射**：原36场景均关闭，不是当前脚本唯一漏掉的“原版功能”。若目标扩展为更完整室外传播，应新增有限厚度薄板透射的明确分支。但Sionna当前并非厚介质体内按Snell方向追踪，墙体应符合其单面＋厚度假设；只有建筑外壳、没有内墙/楼板时，直接开启可能把穿过空壳内部的路径算得过强。土地边界、地面厚度、屋顶和双墙表示也要检查。

**天线**：固定1×32、V极化、`tr38901`是任务配置，不是实测硬件。单极化/静态本身不必为了“完整”改成不相关任务；但应允许配置形状、极化和朝向，正确记录总发射功率、端口与EIRP的关系。

在3.5 GHz、半波长间距下，32阵元ULA长度约1.33 m。常用 $2D^2/\lambda$ 参考距离约41 m；近阵列或近散射点的链路应与逐阵元追踪对照，而不是无条件认定 synthetic array充分。官方[阵列限制说明](https://nvlabs.github.io/sionna/rt/tech-report/S3.html#SS4)同样强调平面波条件。

**边界**：合成城市外没有建筑，不代表真实城市外也是真空。不要用任意距离裁剪排除反射物；若未来为加速做分区/裁剪，应有halo和误差检查。当前地图不含车辆、人、室内细节和动态环境，超出静态室外任务的部分应写清，而不是用更高射线数掩盖。

## 6. 我建议的统一策略：一个主模型，不按来源切换

### 6.1 统一目标与数据接口

目标：**3.5 GHz、静态室外、全场景、天线分辨的物理基带信道，在支持的几何光学/UTD/散射模型下尽量充分收敛；学习预处理独立。**

保持已有任务输出尺寸可行：仍可生成 `[U,1,32,64]`，再导出 `[U,2,32,64]`。高保真并不要求随意改变压缩网络输入维度。

频偏建议围绕3.5 GHz布置；明确给出64个偏移以及总FFT/带宽配置，不再仅叫“DeepMIMO模式”。如要保留原非负索引接口，作为明确的独立导出，不把两种频率轴混为一谈。

### 6.2 候选主传播配置——待验证，不是已证最优

| 项目 | 建议主方案 | 条件/限制 |
|---|---|---|
| LOS | 开启 | 有遮挡时自然无直达 |
| 镜面反射 | 开启；以源场景最大6反射作为参考包络 | 验证贡献随阶数收敛，不把6当自然常数 |
| 绕射 | 开启一次有效楔边绕射及其支持的反射组合 | 必须先修拓扑；Sionna不支持多次绕射 |
| 总交互深度 | 从7作为参考起点，比较5/7/9等 | `max_depth=7`并不严格等于“6反射＋1绕射”，还允许其他7次组合 |
| 漫散射 | 对经核对、确有非零有效模型的材料开启 | 参数/相位统计需验证；不强迫none模型虚构散射 |
| 自由边缘绕射 | 只在真实薄屏/边界存在时启用 | 不能把三角化缝都变成自由边 |
| 照明区绕射 | 作为完整一次UTD场连续性的主候选 | 检查阴影边界连续性和所用公式 |
| 透射 | 几何/墙厚模型通过检查后纳入高保真分支 | 不是为了省计算而永久排除，也不是默认无条件全开 |
| 植被 | 建立独立适配，否则明确作为待完善项 | 没有模型就不能标为完整环境传播 |
| 阵列 | 可配置，已有32阵元任务保持 | 近场链路单独比较逐阵元模式 |
| 路径数 | 不以25或固定小K作为物理真值上限 | 采用容量饱和检测与尾部贡献评估 |

若需要严格限制“R≤6、D≤1、散射最多某次数”，应有真正的交互配额或检查。仅事后过滤虽能控制保留路径，却不能让已经受限的搜索补回未找到的路径；若后端无此能力，报告其实际支持的超集，不谎称已精确复现InSite配额。

### 6.3 预算策略：统一误差门槛，不强制每个区域一样多射线

建议将预算配置为可扩展阶梯，例如 $10^5,5\times10^5,2\times10^6,10^7$，**这里只是试验设计例子，不是推荐立即全城执行的命令，也不是已证明最终需要千万射线**。

- 用少量分层链路选择预算：开阔LOS、街谷、转角NLOS、深NLOS、近树/近站、不同建筑密度与边界。
- 同时改变总深度、每源容量、随机种子；不要只增加射线数。
- 记录路径缓存是否达到上限、候选碰撞/截断风险，避免“几千条返回路径很丰富”掩盖搜索被截断。
- 改变 RX batch 大小、顺序应做稳定性检查。每源路径容量可能由这一批接收点共同占用，固定每源射线预算并不自动保证分批不影响结果。
- 高密度/深NLOS区域可以自动用更高预算，但必须满足同样的结果质量门槛，不能凭地区来源设置不同精度。
- 如果将多个seed的结果合并，镜面路径要按物理身份去重，漫散射要按估计器权重处理；不能直接把多次相干信道相加而重复计能量。

### 6.4 建议验收量与门槛

以下是**项目拟定的初始工程门槛，不是外部标准，也没有在本项目被实测通过**：

1. 分机制的路径增益/PDP、RMS时延扩展、角度扩展、K因子及阵列相关性随预算趋稳。
2. 预算再提高时，代表链路增益变化的中位数尽量≤1 dB，95分位≤2 dB；具体应按任务误差预算调整。
3. 时延扩展等统计量相对变化可先以5%作筛选条件，但接近零值时用绝对误差，不用不稳定百分比。
4. 对可稳定复现的确定性路径，比较原始复数H、允许公共相位对齐后的NMSE与相关系数；可暂以−20 dB NMSE作为对照目标，但不得把随机漫散射无法逐样本相等简单判成失败或成功。
5. 对漫散射比较集合统计、功率守恒与相关结构；几何不确定性下做毫米/厘米扰动敏感性，不能承诺绝对相位对应现实。
6. no-path点记录是“本配置没找到路径”；预算增加时无路径比例变化、深NLOS最坏链路都要看，不能只报全城平均值。
7. 训练集保留绝对尺度旁信息及坐标/扇区；RMS归一化之后看起来分布好，不代表传播已经正确。

建议小测试夹具：自由空间、双径地面、有限厚度板反射/透射、标准楔边、阴影边界、墙角反射＋绕射、漫散射半球功率、阵列朝向/近场对照。它们是以后需授权执行的验证计划，本次未跑。

## 7. 后端选择：是否必须换回 InSite

**不必须。**36个来源都由 InSite生成，只能说明原版的后端来源，并不证明新的合成城市只能由它模拟。

- 如果目标是“尽量复现原作者的后端行为”，有合适许可、工程导入与配置支持时，InSite X3D是更直接的参考候选，尤其可比较精确路径/APG及相关散射机制。
- 这仍不是把网页的R/D/S字段填入就能复现：需要原材料模型、搜索设置、版本和输出相位/阵列约定。
- 若目标是“开放、可复现、可在现有环境维护”，Sionna是合理主后端，但报告必须明确一次绕射与无散射–绕射混合路径等限制。
- 可以在少量标准场景或局部区域做双后端对照；这属于验证，不是把不同后端的路径无条件叠加到同一个H。
- 当前 Apple Metal环境与原版运行环境/加速方式不同，性能与数值容差应独立评估；不能凭8核就假设多进程线性加速，也不为本次分析另装后端。

**推荐的实际决策：先保留 Sionna 作为主后端，把接口、几何和验证补正确；是否引入 InSite作为参考后端由模型缺失对任务的实际影响与许可条件决定。**

## 8. 具体修改顺序

| 优先级 | 应修改内容 | 为什么不能省略 |
|---|---|---|
| P0 | 显式physical-baseband响应；兼容输出独立；原生CFR/解析双径对照 | 决定训练矩阵究竟代表哪种信道 |
| P0 | 索引网格/共享边/法向/跨材料楔边适配 | 否则绕射开关不代表正确建筑绕射 |
| P1 | 物理机制配置与能力检查，参考深度提升并记录真实支持组合 | 当前默认模型明显较简化 |
| P1 | 材料频率、散射幅度/功率/XPD/lobe一致性 | 不正确的材料会比缺弱路径影响更大 |
| P1 | 预算、深度、容量、seed、batch稳定性诊断 | 不能把固定预算当收敛证据 |
| P1 | 植被独立传播模型或显式缺失与敏感性 | 当前树木对射线完全不可见 |
| P2 | 有条件薄板透射、阵列近场、可配置极化/方向图 | 属于模型扩展，需符合几何和任务 |
| P2 | 续跑、分块原始输出、可控并行与磁盘预算 | 全城规模下保持可执行、可追溯，不以删路径代替资源管理 |

不需要为了“完整”无差别增加的项目：移动Doppler（若任务明确静态）、调度/干扰（若生成的是单链路CSI）、训练噪声/量化（应在后处理单独定义）、完整室内模型（除非扩展室内服务目标）。这些是不同任务维度，不宜塞进所有生成步骤。

## 9. 最终回答

**要改。当前版本适合称为专用的简化静态路径到CFR生成器，不应称为“最完整、最好、已验证”的城市CSI生产方案。**

36来源审计并不支持“按各源原配置原样拼接”；支持的是：新城市采用统一的高保真模型，保留材料局部差异，以正确拓扑、明确基带响应和统一误差门槛为基础，逐步加入有依据的绕射、漫散射、植被和透射。

我可以给出确定的架构与修改顺序，但在没有几何/材料核验和收敛结果时，不能诚实地把“7阶、某个固定射线数、全部开启”宣称为已证最优。**应交付的是一个能检验自己是否充分的生成器，而不是一组看起来足够大的参数。**

## 附表：36个来源逐项核对

表中深度/R/D/S/T均为本地下载参数；官网36条记录全部已匹配。14个早期美国城市的官网depth冲突已在第2.2节说明。来源名称链接到实际参数文件；官网链接只列实际从官网取得的地址，Unicode名称未取得详情链接的条目可由统一元数据API核对。

| 来源 | 数据版本 | 深度 | R | D | S | T | 漫散射开启 | 官网 |
|---|---|---:|---:|---:|---:|---:|---|---|
| [asu_campus_3p5](<data/deepmimo/asu_campus_3p5/params.json#L3-L24>) | 4.0.0a3 | 7 | 6 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/asu_campus_3p5) |
| [boston5g_3p5](<data/deepmimo/boston5g_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 4 | 0 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/boston5g_3p5) |
| [city_0_newyork_3p5](<data/deepmimo/city_0_newyork_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_0_newyork_3p5) |
| [city_100_bogotá_3p5](<data/deepmimo/city_100_bogotá_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [目录API](https://deepmimo.net/api/scenarios) |
| [city_102_huanggang_3p5](<data/deepmimo/city_102_huanggang_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_102_huanggang_3p5) |
| [city_10_austin_3p5](<data/deepmimo/city_10_austin_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_10_austin_3p5) |
| [city_11_santaclara_3p5](<data/deepmimo/city_11_santaclara_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_11_santaclara_3p5) |
| [city_14_charlotte_3p5](<data/deepmimo/city_14_charlotte_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_14_charlotte_3p5) |
| [city_15_indianapolis_3p5](<data/deepmimo/city_15_indianapolis_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_15_indianapolis_3p5) |
| [city_17_seattle_3p5](<data/deepmimo/city_17_seattle_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_17_seattle_3p5) |
| [city_18_denver_3p5](<data/deepmimo/city_18_denver_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_18_denver_3p5) |
| [city_19_oklahoma_3p5](<data/deepmimo/city_19_oklahoma_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_19_oklahoma_3p5) |
| [city_1_losangeles_3p5](<data/deepmimo/city_1_losangeles_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_1_losangeles_3p5) |
| [city_21_taito_city_3p5](<data/deepmimo/city_21_taito_city_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_21_taito_city_3p5) |
| [city_24_cairo_3p5](<data/deepmimo/city_24_cairo_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_24_cairo_3p5) |
| [city_27_rio_de_janeiro_3p5](<data/deepmimo/city_27_rio_de_janeiro_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_27_rio_de_janeiro_3p5) |
| [city_28_mumbai_3p5](<data/deepmimo/city_28_mumbai_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_28_mumbai_3p5) |
| [city_2_chicago_3p5](<data/deepmimo/city_2_chicago_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_2_chicago_3p5) |
| [city_30_singapore_3p5](<data/deepmimo/city_30_singapore_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_30_singapore_3p5) |
| [city_32_sydney_3p5](<data/deepmimo/city_32_sydney_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_32_sydney_3p5) |
| [city_38_toronto_3p5](<data/deepmimo/city_38_toronto_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_38_toronto_3p5) |
| [city_41_kyoto_3p5](<data/deepmimo/city_41_kyoto_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_41_kyoto_3p5) |
| [city_43_cape_town_3p5](<data/deepmimo/city_43_cape_town_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_43_cape_town_3p5) |
| [city_4_phoenix_3p5](<data/deepmimo/city_4_phoenix_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_4_phoenix_3p5) |
| [city_50_edinburgh_3p5](<data/deepmimo/city_50_edinburgh_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_50_edinburgh_3p5) |
| [city_53_sankt-peterburg_3p5](<data/deepmimo/city_53_sankt-peterburg_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_53_sankt-peterburg_3p5) |
| [city_55_madrid_3p5](<data/deepmimo/city_55_madrid_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_55_madrid_3p5) |
| [city_56_montreal_3p5](<data/deepmimo/city_56_montreal_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_56_montreal_3p5) |
| [city_5_philadelphia_3p5](<data/deepmimo/city_5_philadelphia_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_5_philadelphia_3p5) |
| [city_69_warszawa_3p5](<data/deepmimo/city_69_warszawa_3p5/params.json#L3-L24>) | 4.0.0a9 | 5 | 4 | 1 | 0 | 0 | 否 | [详情](https://deepmimo.net/scenarios/v4/city_69_warszawa_3p5) |
| [city_6_miami_3p5](<data/deepmimo/city_6_miami_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_6_miami_3p5) |
| [city_8_dallas_3p5](<data/deepmimo/city_8_dallas_3p5/params.json#L3-L24>) | 4.0.0a3 | 4 | 3 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_8_dallas_3p5) |
| [city_90_nanjing_3p5](<data/deepmimo/city_90_nanjing_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_90_nanjing_3p5) |
| [city_92_sãopaulo_3p5](<data/deepmimo/city_92_sãopaulo_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [目录API](https://deepmimo.net/api/scenarios) |
| [city_98_guangzhou_3p5](<data/deepmimo/city_98_guangzhou_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_98_guangzhou_3p5) |
| [city_99_shanghai_3p5](<data/deepmimo/city_99_shanghai_3p5/params.json#L3-L24>) | 4.0.0b11 | 6 | 5 | 1 | 1 | 0 | 是 | [详情](https://deepmimo.net/scenarios/v4/city_99_shanghai_3p5) |
