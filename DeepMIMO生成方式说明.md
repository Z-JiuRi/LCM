# DeepMIMO 是怎样生成信道的：场景、射线追踪、数据转换与 CSI 合成

日期：2026-10-27。

本文依据本地 [DeepMIMO 官方源码](<reference/DeepMIMO-v4/>) **v4.0.5**、本地下载场景的参数文件和当前项目脚本说明。结论来自静态阅读，本文没有执行射线追踪或生成城市信道；其他版本的行为应另行核对。官方项目地址：[DeepMIMO/DeepMIMO](https://github.com/DeepMIMO/DeepMIMO)。

## 1. 先回答：官方不同场景的“生成方式”是不是不一样？

**有些层面不同，有些层面共用同一套实现。不能笼统地说“每个场景有一套不同的 CSI 公式”。**

| 层次 | 不同场景之间可能不同吗？ | 具体是什么 |
|---|---|---|
| 场景与采样设计 | 是 | 建筑、地形、材料、载频、TX/RX 位置、室内外范围、静态/动态快照 |
| 射线追踪 | 是 | 使用哪个追踪器、开启哪些传播机制、反射/绕射次数、采样预算、阈值 |
| 原始结果转换 | 是 | 不同追踪器输出格式不同，需要各自的 converter；转换时还可能筛选或截断路径 |
| 路径到信道的合成 | 通常共用生成器 | 根据统一的路径参数，加上用户指定的阵列和 OFDM 参数，合成复数信道 |
| 机器学习预处理 | 由任务决定 | 选服务 BS、同步、归一化、抽频点、实虚拆分和训练集划分 |

因此，“ASU 使用最多6次反射，纽约使用最多3次反射”和“二者可以调用同一个 `compute_channels()`”完全不矛盾。

最重要的是区分两类参数：

- **RT 参数**决定能找到什么路径，以及路径的功率、相位、时延和方向。
- **信道合成参数**决定如何把已存路径变成所需维度和频点的信道矩阵。

把合成时的路径数改大，不能凭空补回原来没有追踪、没有导出或已经被转换器删除的绕射路径。

## 2. 完整流程：不是“导入建筑，然后一条公式得到 CSI”

```text
几何 + 材料 + TX/RX采样设计 + 载频 + RT配置
                         ↓
       Wireless InSite / Sionna RT / 其他追踪器
                         ↓
          每条传播路径的原始结果
                         ↓
        对应追踪器的 DeepMIMO converter
                         ↓
       统一路径矩阵 + 场景与追踪元数据
                         ↓
                 dm.load(...)
                         ↓
     用户指定阵列、方向图、路径数、OFDM参数
                         ↓
            dataset.compute_channels(...)
                         ↓
                    复数 H
                         ↓
        按研究任务加工成训练/验证/测试样本
```

官方 [README](<reference/DeepMIMO-v4/README.md#L67-L90>)分别给出了“下载已有数据并合成信道”和“将 RT 输出转换成 DeepMIMO”两条使用流程。

需要纠正此前一句过度简化的话：**不能说“DeepMIMO 完全没有 RT 功能”。**它的核心信道生成器不执行射线追踪，但官方工具链包含调用追踪后端的 pipeline，例如 [Sionna RT 调用封装](<reference/DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_raytracer.py#L152-L236>)。真正的电磁路径求解仍由后端负责。

## 3. 第一层：场景和射线追踪如何决定路径

### 3.1 场景作者需要先确定什么

1. **几何**：建筑外形、道路/地面、地形、其他物体。
2. **材料**：介电常数、电导率、厚度、散射参数等；参数适用频率也重要。
3. **发射/接收布置**：TX 站址、高度、RX 网格或轨迹、是否采样楼内、设备朝向。
4. **载频**：会影响波长、材料响应、阵列相位和传播损耗。
5. **机制及搜索配置**：直达、镜面反射、绕射、漫散射、透射/折射，以及深度、阈值、预算等。
6. **动态设置**：是否保存多个几何快照、移动设备或移动物体。

这些输入不同，路径结果当然不同。即使几何相同，两套追踪器的搜索算法、材料实现与数值容差也不一定相同。

### 3.2 追踪器实际做什么

对某个 TX–RX 链路，追踪器搜索符合已启用机制与几何约束的候选路径，求解每条路径的传播响应。路径可能是：

- 直达：TX → RX；
- 一次反射：TX → 墙面 → RX；
- 多次反射；
- 绕射边缘路径；
- 包含漫散射或透射的组合路径。

路径的衰减和相位不是简单“按反射次数扣固定 dB”：它们还与距离、角度、材料、极化及具体模型有关。

**“最大次数”是允许的上限，不是每条链路必定存在的次数；“开启机制”也不等于所有符合该机制的路径都已收敛找到。**

### 3.3 本地官方场景的真实例子

下面直接摘取各场景 `rt_params`，不是推测，也不是当前项目脚本的参数：

| 场景 | 追踪器 | 载频 | `max_path_depth` | `max_reflections` | `max_diffractions` | `max_scattering` | `max_transmissions` |
|---|---|---:|---:|---:|---:|---:|---:|
| ASU campus | Wireless InSite 3.3 | 3.5 GHz | 7 | 6 | 1 | 1 | 0 |
| New York | Wireless InSite 3.3 | 3.5 GHz | 4 | 3 | 1 | 1 | 0 |
| Huanggang | Wireless InSite 3.3.0 | 3.5 GHz | 6 | 5 | 1 | 1 | 0 |

出处：[ASU 参数](<data/deepmimo/asu_campus_3p5/params.json#L3-L24>)、[纽约参数](<data/deepmimo/city_0_newyork_3p5/params.json#L3-L24>)、[黄冈参数](<data/deepmimo/city_102_huanggang_3p5/params.json#L3-L24>)。

三者还记录了 `diffuse_reflections=2`、`diffuse_diffractions=1`、`diffuse_final_interaction_only=true` 等更细的散射设置。因此，不能只用一列 `max_scattering` 描述其完整散射模型，也不能机械地把各字段上限相加当作所有组合均被支持。

**这三个例子已经证明：即使采用同一种追踪器、同一个载频，官方场景的 RT 配置也不统一。**但这不证明官网每个场景都使用不同追踪器，更不能由三个例子外推所有场景。

此外，这些是已保存的元数据，不是我们重新运行并独立认证过的配置。不同后端的类似参数名也不一定有完全相同的语义。

### 3.4 Sionna 支持与官方封装暴露的功能是两回事

当前项目使用的 Sionna RT 支持相关反射、漫散射、绕射和折射机制；是否启用要看真正传给求解器的参数，而不能只看库是否有这个功能。

在所检查的官方 v4.0.5 [Sionna pipeline](<reference/DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_raytracer.py#L152-L163>)中，原生调用参数包括 `los`、`synthetic_array`、`samples_per_src`、`max_num_paths_per_src`、`max_depth`、`specular_reflection`、`diffuse_reflection`、`refraction`；该处没有显式转发 `diffraction`。这只能说明这一版本封装的调用内容，**不能据此说 Sionna 没有绕射模型**。

同一段实现将固定的 `n_samples_per_src` 传给原生 `samples_per_src`，RX 分批时复用这份配置。不能把转换器中对“射线数”元数据的估算，误当成 solver 执行时按 RX 或天线数拆分预算。

## 4. 第二层：DeepMIMO 保存的是什么

统一格式的核心通常是**逐路径参数**，而不是某个固定天线维度的最终神经网络输入。

| 字段 | 含义 | 常见单位 |
|---|---|---|
| `power` | 每条路径的功率记录，官方约定为0 dBW发射参考下的接收功率 | dBW |
| `phase` | 每条路径的初始复系数相位 | 度 |
| `delay` | 每条路径的传播时延 | 秒 |
| `aod_az`、`aod_el` | 发射方向的角度参数 | 度 |
| `aoa_az`、`aoa_el` | 接收方向的角度参数 | 度 |
| `inter` | 路径交互类型序列 | 编码 |
| `inter_pos` | 各交互点的位置 | 米 |
| `tx_pos`、`rx_pos` | 发射和接收采样位置 | 米 |
| `rt_params` | 原始追踪参数及相关记录 | 元数据 |

依据：[官方字段说明](<reference/DeepMIMO-v4/docs/quickstart.md#L77-L114>)。

交互编码中，0 表示 LOS，1 反射，2 绕射，3 散射，4 透射；例如 `121` 表示反射→绕射→反射。它是**已有路径的类型记录**，不是在合成 CSI 时请求新算这些机制的开关。

角度字段从追踪器转换到阵列内部计算时还涉及坐标系与角度定义；不要仅凭 `elevation` 名称就自行代入另一套三角函数。

### 4.1 为什么要有不同 converter

InSite、Sionna 和其他后端输出的文件、数组形状、单位、交互编码和复系数定义不同。转换器负责将它们放进统一的数据结构。

例如 Sionna 的交互枚举与 DeepMIMO 编码不同，官方 [类型映射](<reference/DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L85-L140>)将 Sionna 的漫散射标记映射为 DeepMIMO 的3、绕射标记映射为2。

统一了字段名称，**并不自动保证所有后端的物理模型、精度、相位参考与路径选择都完全等价**。转换器也是需要核对的一环。

另一个实际细节：官方 Sionna pipeline 的[默认 TX/RX 是1×1 isotropic/V](<reference/DeepMIMO-v4/deepmimo/pipelines/sionna_rt/sionna_utils.py#L115-L127>)；在 synthetic/shared-angle 布局下，[路径转换器取第一个 RX/TX 阵元对的系数](<reference/DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L216-L237>)，后续再做阵列合成。我们当前脚本却直接保留32阵元的天线分辨系数。因此不能因为两者都读取 `paths.a`，就称为同一条端到端实现。

### 4.2 路径保留上限属于不同阶段

至少要区分三种上限：

1. RT 后端最多搜索/存储多少路径；
2. converter 最多输出多少路径；
3. `compute_channels()` 最多使用多少已存路径。

所检查的 v4.0.5 Sionna converter 会先按原始索引取最多25条非零路径，再对这个子集按幅度排序；**不能把这个版本描述为从所有路径中选全局最强25条**。详见 [路径选择与字段写入](<reference/DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L250-L280>)。其他版本应重新核对，不把这一细节推广为永久的官方定义。

## 5. 第三层：统一路径如何合成 CSI

### 5.1 `compute_channels()` 不会重新追踪建筑

官方 [Dataset.compute_channels](<reference/DeepMIMO-v4/deepmimo/datasets/dataset.py#L464-L534>)的主要流程是：

1. 读取用户给定的信道参数；
2. 根据角度和阵列配置计算接收/发射阵列响应；
3. 截取所用的已存路径；
4. 将路径功率、相位、时延、Doppler 及 OFDM 配置交给信道生成器；
5. 返回复数信道矩阵。

它不会因为你增加 BS 阵元数，就重新穿过整个城市搜索一遍墙面反射；也不会因为你改 OFDM 参数就自动补算缺失的绕射。

### 5.2 静态、频域、接收滤波关闭时的核心公式

为了避免将阵列共轭约定混入通用符号，下面直接把代码最终使用的两个阵列响应分别记为 $A^{\mathrm{rx}}$、$A^{\mathrm{tx}}$：

$$
H_{u,r,m}[k]
=
\sum_{p\in\mathcal P_u}
A^{\mathrm{rx}}_{u,r,p}
A^{\mathrm{tx}}_{u,m,p}
\sqrt{\frac{P^{\mathrm{eff}}_{u,p}}{N}}
\exp(j\phi_{u,p})
\exp\left(-j2\pi\tau_{u,p}\frac{kB}{N}\right).
$$

其中：

- $u$：接收位置；$r$：RX 阵元；$m$：TX 阵元；$p$：路径；
- $P^{\mathrm{eff}}$：换算成线性值并计入生成器所用方向图增益等处理后的路径功率；
- $\phi$：已存路径相位，代入指数前由度转换为弧度；
- $\tau$：以秒为单位的路径时延；
- $B$：OFDM 合成带宽；$N$：总子载波数；
- $k$：选中的子载波索引，合成频偏为 $f_k=kB/N$；
- $\mathcal P_u$：本次实际参与合成的有效路径集合。

核心代码见 [OFDMPathGenerator.generate](<reference/DeepMIMO-v4/deepmimo/generator/channel.py#L357-L426>)。其中先使用 $T_s=1/B$ 将时延换成采样单位，所以代码里的 $\tau/T_s$ 与上式的秒制表达等价。

这不是“用随机数生成一个复矩阵”，而是多条确定路径在阵列和频率上的**相干叠加**。

### 5.3 阵列响应从哪里来

阵元相对位置及路径方向决定阵列内部的相位差，阵元间距通常以波长为单位。`spacing=0.5` 表示半波长，而不是0.5米。

当前版本内部面阵索引沿局部 Y/Z 方向构造，见 [阵列几何实现](<reference/DeepMIMO-v4/deepmimo/generator/geometry.py#L104-L141>)。不同库的阵列中心、索引顺序、旋转顺序可能不同，不能只把 `[32,1]` 或 `[1,32]` 原样互换就声称等价。

这种路径级解析阵列合成依赖其几何/平面波建模假设，不等于为每个阵元重新进行独立 RT。Sionna 的 `synthetic_array=True` 也使用设备参考位置路径与合成阵列响应，不应说它天然就是“每阵元精确追踪”。

### 5.4 几个影响结果的重要实现细节

- **选64个频点不等于 $N=64$。**例如 $N=1024$、选64个索引时，默认公式仍除以 $\sqrt{1024}$。
- **频点不自动居中。**代码直接使用选定的 $kB/N$，不自动减去 $B/2$。对于分数采样时延，不可随意把高索引频点改成负频偏并认为完全相同。
- **不自动减首径时延。**公式使用传入时延；任务需要时延对齐，应作为明确的额外步骤。
- **延迟窗处理。**当 $\tau\ge N/B$ 时，该频域生成实现将路径贡献置零；不能把这一数值窗处理解释成路径在物理上不存在。
- **可选接收滤波。**启用接收滤波时，使用有限窗口 sinc 时延响应再投影到选定频点，不再只是上式中的裸时延指数。
- **时域输出不等于均匀采样抽头栅格。**该接口的时域输出末轴是路径，路径时延另行保留。
- **多时刻与 Doppler。**系数可带 $\exp(j2\pi f_{D,p}t)$；这不等于每个时刻重新计算建筑遮挡、出现/消失路径。是否使用 Doppler 还取决于数据的速度/路径属性及实现分支，不能只看一个参数名。

### 5.5 官方库的默认合成参数是什么

以所检查的 v4.0.5 [ChannelParameters 默认值](<reference/DeepMIMO-v4/deepmimo/generator/channel.py#L149-L175>)为准：

| 参数 | 默认值 |
|---|---|
| BS 阵列 | `[8,1]`，8阵元 |
| UE 阵列 | `[1,1]`，1阵元 |
| 阵元间距 | 0.5波长 |
| 阵元方向图 | isotropic |
| 路径数参数 | 25（还受已存路径数限制） |
| 频域输出 | 开启 |
| OFDM 带宽 | 10 MHz |
| 总子载波数 | 512 |
| 选中索引 | **`[0]`，只有1个频点** |
| 接收滤波 | 关闭 |
| Doppler 参数默认值 | 0；通常静态零速度场景没有 Doppler，动态数据还需看实际分支 |

**这张表是“路径到信道”的默认值，不是“官方每个城市如何进行 RT”的统一配置表。**

静态输出通常为：

$$
[U,M_{\mathrm{rx}},M_{\mathrm{tx}},K].
$$

这里 $M_{\mathrm{tx}}$ 是 TX 阵元数，不是基站数量；多 TX 或多快照还涉及数据集容器组织，不能直接把这些轴混在一起。

## 6. 相位约定：必须纠正前面解释中的错误

这部分专门澄清此前对话中的误导，不能用“不同场景不同”来回避问题。

### 6.1 合成器如何使用相位是确定的

官方生成器接收 `phase`，将其从度转换为弧度，乘上 $\exp(j\phi_p)$，再乘频偏时延项。**这个计算本身是明确的。**

需要核对的是：某个 converter 写入的 `phase` 对应哪一种路径系数，使用什么参考位置、参考载频和延迟定义。

### 6.2 Sionna 的两类系数不能混为一谈

以本机 Sionna RT 2.2.0 的实现为依据：[CIR 定义](</Users/z-jiuri/.envs/miniconda3/envs/lcm/lib/python3.11/site-packages/sionna/rt/path_solvers/paths.py#L498-L508>)、[CFR 调用 CIR 后叠加频偏响应](</Users/z-jiuri/.envs/miniconda3/envs/lcm/lib/python3.11/site-packages/sionna/rt/path_solvers/paths.py#L819-L855>)。这两处是本机环境路径，不属于 DeepMIMO 仓库。

把 Sionna 原始路径系数记为 $b_p$，其原始系数尚未乘上公共传播载波项。**以下使用绝对路径时延，并对应 `normalize_delays=False`、静态时刻的比较。**Sionna 默认时延归一化会在载波旋转前改变所用时延，不能省略这个比较条件。其基带 CIR 系数可写为：

$$
a_p=b_p\exp(-j2\pi f_c\tau_p).
$$

用这个基带系数计算频偏 $\nu$ 处的频响：

$$
H(\nu)=\sum_p a_p\exp(-j2\pi\nu\tau_p)
       =\sum_p b_p\exp[-j2\pi(f_c+\nu)\tau_p].
$$

**这是正确的基带等效频响写法，不是重复计算载波相位。**此前把 `cir()` 加上基带频偏指数直接判为 bug，是错误的；也不能把 $\nu-f_c$ 叫作普通的居中 OFDM 频偏。

另一方面，所检查的官方 Sionna [exporter](<reference/DeepMIMO-v4/deepmimo/exporters/sionna_exporter.py#L70-L115>)导出原始 `paths.a`；[converter](<reference/DeepMIMO-v4/deepmimo/converters/sionna_rt/sionna_paths.py#L250-L280>)从导出系数取幅度、相位和时延。因此，这条特定版本链路与使用 `cir()` 系数的链路确有需要对照的相位差异。

这是**具体数据接口/版本的约定问题**，不能扩大成“DeepMIMO 的所有相位都不明确”，也不能仅凭这一点断言整个官方工具有统一的物理错误。

### 6.3 关于 InSite，目前能确认到哪一步

所检查的 [InSite 解析器](<reference/DeepMIMO-v4/deepmimo/converters/wireless_insite/p2m_parser.py#L55-L74>)解释了0 dBm与0 dBW参考下的归一化功率处理；其路径相位由源文件字段读入。

**仅靠这段解析代码，不能严格确定所有 InSite 配置下输出相位的参考原点、载波传播项和天线相位语义。**此前直接断言“InSite 一定包含某个载波相位项，并已与我们当前代码完全对齐”，证据不足，应撤回。

正确的工程做法是：明确选择系数约定，在同一小场景、同一阵列参考位置、同一频点和同一条路径集合上，进行单径以及至少双径的复数数值对照，再声明匹配范围。

### 6.4 为什么不是“差一点绝对相位，归一化就没事”

如果所有路径共同乘同一个相位，确实只是全信道的公共旋转；但不同路径的 $\tau_p$ 不同，$\exp(-j2\pi f_c\tau_p)$ 通常也不同。

以两条路径为例：

$$
H(\nu)=a_1e^{-j2\pi\nu\tau_1}+a_2e^{-j2\pi\nu\tau_2}.
$$

改变两条路径之间的相位差，会改变干涉项，因此可能改变 $|H(\nu)|$ 和频率选择性衰落。RMS 归一化只除去一个幅度尺度，不会消除这个问题。

所以，此前“只要单独训练就没有影响”“两种写法归一化后训练数据没有区别”的说法过强，**不成立**。数据集独立使用可以避免混用约定，但不等于任何约定都具有相同物理意义和统计特性。

## 7. 两条官方使用路线

### 路线 A：使用已发布的路径数据

下面是示意代码，不是本次实际运行记录：

```python
import numpy as np
import deepmimo as dm

# 需要包含路径矩阵的完整场景，不能只有 objects/vertices/params。
dataset = dm.load('asu_campus_3p5')

params = dm.ChannelParameters()
params.bs_antenna.shape = [32, 1]
params.bs_antenna.spacing = 0.5
params.ue_antenna.shape = [1, 1]
params.ofdm.bandwidth = 20e6
params.ofdm.subcarriers = 1024
params.ofdm.selected_subcarriers = np.arange(0, 1024, 16)
params.num_paths = 25

H = dataset.compute_channels(params)
# 单个对应数据集的静态频域输出预期为 [U, 1, 32, 64]。
```

参数接口可参考[官方信道生成教程](<reference/DeepMIMO-v4/docs/tutorials/3_channel_generation.py>)。上例没有改变发布场景原有的 RT 机制，也没有选服务 BS、做 RMS 归一化或生成 train/val/test。

当前本仓库 [data/deepmimo](<data/deepmimo/>)保留的是源几何/参数文件，不能仅因目录名字与官方场景一致，就假定已经包含运行上述信道合成所需的全部路径矩阵。

### 路线 B：生成自己设计的新城市

1. 准备新几何、材料和 TX/RX 位置；
2. 选择追踪器并明确传播配置；
3. 执行新的 RT；
4. 通过匹配的 converter 导出 DeepMIMO 格式，或自行定义清楚的原始路径接口；
5. 再合成阵列/频域信道并做任务预处理。

**把官方建筑搬到新的合成城市后，原路径不能跟着直接搬过来使用。**建筑相对位置、遮挡和站点都变了，必须重新追踪。使用官方建筑素材不等于新城市的信道已经由官方计算或认证。

## 8. 官网覆盖图与路径图为什么会显示绕射、散射

官方 [quickstart](<reference/DeepMIMO-v4/docs/quickstart.md#L49-L65>)使用 ASU 场景：

- `dataset.power.plot()` 默认选择第一条路径功率作图；不是自动计算所有路径相干合成的接收功率，也不是 SINR/容量图。
- `dataset.plot_rays(...)` 根据已存的路径几何和交互类型画图。

ASU 参数确实记录了 InSite 的反射、绕射、散射设置。因此图中的这些路径来自相应 RT 数据；不是画图函数临时计算的，也不能用它证明我们的新合成城市默认已经开启这些机制。

## 9. 当前项目脚本处于哪一层，与官方有什么区别

当前 [generate_city_csi.py](<scripts/CSI-generate/generate_city_csi.py>)走的是“**Sionna 求路径 → 直接用原始系数合成 CFR → 任务预处理**”的专用路线，没有直接调用官方 `Dataset.compute_channels()`。

| 项目 | 当前实现 | 应如何理解 |
|---|---|---|
| 场景 | 三座合成城市 | 复用官方源资产，不是发布场景的原布局/原信道 |
| 默认 RT | LOS＋镜面反射，最大交互深度3 | 项目简化默认值，非所有官方场景统一默认值 |
| 其他机制 | 绕射、自由边缘绕射、漫散射、折射默认关闭，有显式 CLI 开关 | 库支持不等于默认启用 |
| TX/RX | 32阵元水平 ULA / 单RX阵元；TX `tr38901`、V极化 | 不是官方库默认的8阵元 isotropic 配置 |
| 路径系数 | 读取 `paths.a`，不是 `paths.cir()` | 按当前选定约定执行；不能据此声明与官方完整链路数值等价 |
| 路径选择 | 不自行截取前25条，保留后端返回路径 | 不等于后端已找到全部物理路径 |
| OFDM | 20 MHz、总1024、每16取1得到64频点 | 用户任务配置，不是官方默认512/只选0号频点 |
| 同步与归一化 | 显著首径时延对齐＋逐样本 RMS | 任务预处理，不是官方核心公式自动要求 |
| 服务扇区 | 路径功率指标选取 | 不是干扰/调度/容量验证 |
| 数据集划分 | 空间块分 train/val/test | 任务设置，仍存在邻块相关性问题 |

配置出处：[求解器参数与阵列](<scripts/CSI-generate/generate_city_csi.py#L139-L167>)、[原始系数提取](<scripts/CSI-generate/generate_city_csi.py#L194-L209>)、[CLI 默认值](<scripts/CSI-generate/generate_city_csi.py#L291-L320>)。

所以，“默认 LOS＋最多3次镜面反射”**是当前代码行为的准确描述**，但不是“已经实现了 ASU 那套6反射＋绕射＋散射设置”，也不是“所有官方场景都这样算”。

当前脚本可固定参数、固定接口，但要称为“经过验证的官方等价生成器”，仍需要独立数值对照。此前多次仅凭自写公式或单径试验声称完整一致，不够严谨。

## 10. 总结：哪些是确定的，哪些需要验证

**已经明确的实现事实：**

1. 不同官方场景的几何、追踪器和 RT 参数可以不同；本文三个 InSite 场景已有具体参数证据。
2. 转换后的路径可通过共用生成器合成信道；`compute_channels()` 本身不重新执行城市 RT。
3. 官方核心 OFDM 计算、单位、缩放与延迟窗可以从源码明确读出，并非一团不确定的公式。
4. 当前项目默认只开启 LOS 和镜面反射，深度3；其他机制必须显式开启。

**不能由上述事实直接保证的事情：**

- 不同追踪器在同一场景上会产生一样的路径和 CSI；
- 同名 `phase` 字段天然具有完全一致的参考约定；
- 打开全部机制、增大预算就一定得到真实准确的城市覆盖；
- 当前脚本已经与官方端到端数值等价；
- 仅有几何或 UE 可视化就已经拥有 CSI 数据集。

一句话归纳：**DeepMIMO 是“不同 RT 数据来源 → 统一路径表示 → 可配置的信道合成”的工具链，而不是要求所有场景用同一种 RT 配置。统一的是接口和核心合成框架，不是世界上所有场景的传播条件。**
