# 城市静态 CSI：来源可追溯的 Sionna 生成流程

更新：2026-10-27。本项目实现，不是 DeepMIMO 官方脚本，也不宣称与 InSite 等价或全城收敛。沿用现有合成城市几何/材料；本轮完成物理基带、索引拓扑、配置来源、轻量回归和本机有限真实 RT smoke。

## 1. 默认行为已改变

| 维度 | 当前默认 | 说明 |
|---|---|---|
| 传播配置 | `--propagation-profile source-informed` | 参考原始资料的统一项目策略，不是逐来源切换求解规则 |
| 载频 | 3.5 GHz | 来源共同载频 |
| 深度 | 7 | 统一候选策略，不是所有选中来源的最大值，不等于严格R≤6、D≤1 |
| LOS / 镜面反射 | 开 | 由遮挡和路径搜索决定结果 |
| 绕射 / 漫散射 | 开 / 开 | 绕射有拓扑门槛；散射保留材料模型差异 |
| 自由边缘绕射 / 透射 | 关 / 关 | 当前地形分组存在假自由边；全部36原来源均关闭透射 |
| 地形散射 | `off` | S=0的显式适配；与原后端全局开关并非严格等价 |
| 路径系数 | `physical-baseband` | 调用 `paths.cir(normalize_delays=False,num_time_steps=1)` |
| 频点 | `centered` | 默认[-10 MHz,9.6875 MHz]的64个频偏，间隔312.5 kHz |
| 幅度缩放 / 延迟窗 | `unit` / `none` | 不除sqrt(N)，不裁剪绝对时延 |
| 天线 | 1×32水平ULA，0.5λ、V极化 | TX tr38901、RX isotropic；这是任务配置，不是来源原天线 |
| 搜索预算 | 100000 samples/source，候选容量200000 | 可配置启发式，未证明收敛，不能等同原InSite射线数 |
| RT分批 | 32 RX | 固定每源预算，不按RX数乘除；换批大小可能改变候选竞争 |

**旧数据与新数据不能无标记混训练。**恢复旧的传播/信道表示需显式指定四个独立选项和legacy传播配置：

```sh
--propagation-profile legacy --coefficient-mode raw-passband \
--convention deepmimo --normalization ofdm --delay-window fft
```

这恢复旧的配置定义，但新索引网格及显式法向加载仍可能改变RT结果；不承诺旧文件逐字节复现。

## 2. 文件职责与来源

- [city_geometry.py](<city_geometry.py>)：CPU几何/UE导出。v2 manifest记录共享边、材料、来源、拓扑诊断和频率警告。
- [propagation_profiles.py](<propagation_profiles.py>)：只读取当前几何实际使用的来源参数，保留标准字段、raw字段、冲突和未知值；不把所有下载场景偷偷算作当前来源。
- [generate_city_csi.py](<generate_city_csi.py>)：真实RT、路径导出、CFR、服务选择及学习预处理。
- [smoke_city_csi.py](<smoke_city_csi.py>)：必须显式运行的有限真实RT smoke；最多16 UE、2扇区、5000 samples/source。

原资料位于[DeepMIMO数据](<../../data/deepmimo/>)，信道公式和转换规范参考[官方源码](<../../reference/DeepMIMO-v4/>)。原版36来源全是InSite。来源参数不是新城市的测量真值，也不提供Sionna等价射线预算。

当前1km实际使用30个来源，ASU不在其中，其原始深度为4/5/6；统一深度7是参考全来源范围选择的项目策略，**不是错误宣称当前30个来源中有depth7**。原全局漫散射开关与材料局部模型分别记录：统一开启全局散射是适配假设；`scattering_model=none`在材料映射中仍将S置0。

## 3. 几何与材料策略

建筑在每个实例内按精确坐标建立索引，材质分组保持逐面归属；不同建筑实例即使坐标重合也不焊接。源坐标/绕序保留，只省略世界z=0共面的建筑底面。生成器显式以 `flip_normals=False, face_normals=True` 加载OBJ，再使用 `SceneObject(mi_mesh=...,remove_duplicate_vertices=False)`，避免文件加载助手默认翻法向或全局去重。

拓扑诊断包括：共享边、内部三角化边、边界、非流形、绕序冲突、跨材料/分组的共面和非共面边。绕射请求默认必须通过相关门槛；`--allow-unverified-topology`仅为显式诊断覆盖，会留下记录，不是认证。

本次1km建筑为6940顶点、9080三角形，0非流形/绕序冲突/跨材料楔边。普通绕射检查通过；地形有1476条因材料/角色分组断开的共面接缝，**自由边缘绕射检查不通过**，防止将其当作真实屏障边。

地形保留15个面积≤1e-6平方米的极细源三角形，其中8个源法向向下；直接翻转会破坏共享边绕序。它们被记录而非自动删掉/移动。后端float32可改变这些细片的数值方向，因此当前几何不是完整的数值稳健性/外法向认证。未来需对这些退化近邻做受控修复和差异验证。

材料保留原始记录，严格检查模型和参数，directive使用alpha_r，none显式关闭；不伪造材料频率换算。生成报告比较实际载频与材料参考频率。道路参考1GHz而运行3.5GHz时会警告，原参数保留。`--terrain-scattering off`通过S=0关闭地形漫散射并将能量返回镜面，属于明确近似；`source-material`保留来源系数。树木仍只排除UE点，**不参与传播**。

## 4. 明确的信道契约

四个选项互相独立：

- `--coefficient-mode physical-baseband|raw-passband`：系数语义。
- `--convention centered|deepmimo`：仅频点；后者为0,16,...,1008非负FFT索引对应频偏。
- `--normalization unit|ofdm`：单位信道或1/sqrt(N)。
- `--delay-window none|fft`：保留全部时延或仅在CFR中裁剪tau≥N/B，原始路径仍保存。

默认物理基带：

$$
H_{r,m}(\nu_k)=\sum_p a^{\mathrm{BB}}_{r,m,p}\exp(-j2\pi\nu_k\tau_p).
$$

CIR提供载波相位，频偏指数提供基带频率响应，两者组合不是重复计算。阵列/方向图响应已在系数中，不额外重复套阵列因子。逐128路径分块计算，在complex128中累加，最后转complex64。

`--check-native-cfr`可将输出与同一份Paths的原生CFR对照；要求物理基带且无延迟窗。默认NMSE容差1e-6，仅用于有限检查；原生频点矩阵会增加显存开销，不建议全城无条件开启。此对照不是独立RT求解器验证。

## 5. 使用命令

从仓库根执行，使用Conda `lcm`。不覆盖已有目录。

```sh
conda activate lcm
# 纯CPU导出，不RT；输出须不存在。
python scripts/CSI-generate/city_geometry.py --output data/csi/city-1km-geometry-new

# 只核对输入、拓扑/来源和容量，不导入RT、不创建结果。
python scripts/CSI-generate/generate_city_csi.py \
  --geometry data/csi/city-1km-geometry-new --dry-run

# 显式有限真实RT：自由空间解析检查 + 8UE×2扇区，非全城。
python scripts/CSI-generate/smoke_city_csi.py \
  --geometry data/csi/city-1km-geometry-new \
  --output data/csi/smoke-new --ues 8 --sectors 2 --samples 2000

# 全部CPU合成/mock/来源/拓扑测试，不运行真实RT。
python -B -m unittest discover -s scripts/CSI-generate -p 'test_*.py' -v
```

`--dry-run`仍需要有效几何输入；缺文件不是检查成功。旧manifest未声明来源或未做拓扑检查应重新导出。生产运行去掉dry-run即会RT，不会自动替用户判断GPU空闲。

## 6. 输出、关联和训练预处理

```text
report.json                   schema_version=3、来源证据、适配策略、实际地块、状态、容量与限制
ue_positions.npy              [U,3]实际本次位置
source_ue_indices.npy          回指完整UE网格
raw/sector-000/metadata.json   solver kwargs、版本、seed、耗时、逐批诊断与CFR检查
raw/sector-000/paths-*.npz     raw passband + channel_coefficients、coefficient_mode、绝对时延
                              mask、角度、交互类型及坐标
raw/sector-000/csi.npy         [U,1,32,64] complex64
raw/sector-000/link_stats.npz  路径功率、显著径时延、路径数/延迟窗裁剪
sector_scores.npy             [sector,U] float64磁盘映射
serving_csi.npy                [U,1,32,64]服务信道
association.npz               关联、尺度、有效性、parcel_index和分数兼容字段
parcels/parcel-XXXX/csi.npy   每个实际地块全部UE的[U_parcel,2,32,64]；无效UE为显式零占位
parcels/parcel-XXXX/ue.npz   全部UE坐标、路径状态、服务扇区、RMS和源索引
parcels/parcel-XXXX/metadata.json  地块角色、数量、可用数量、哈希
parcel-catalog.json           实际地块与outside-parcels分组规则；不再生成train/val/test

```

按天线平均逐径功率和×TX功率选择服务扇区，不是相干波束赋形增益或SINR。等分保留首扇区。首条最强路径25dB以内显著径为tau_ref，频域时延对齐后做RMS归一化；保存旁信息可逆。按源场景真实地块多边形保存，不再随机/空间块8:1:1。地块边界用covers，重叠或边界并列按原数组较小索引归属。道路、公园等不在任何地块内的UE保留在outside-parcels，不强行归最近地块、不丢弃。所有UE均有行；无效CSI为零占位，必须用feedback_usable判定，不能当作物理零信道。无路径表示“本预算没找到”，不等于物理遮蔽。

逐批诊断记录有效路径数、非零交互码统计、平均RMS时延扩展和最终路径数/容量比；**不据此声称看到了内部候选占用或不存在截断**，candidate_saturation明确为unknown。

### 已生成结果的地块重导出（不重跑RT）

[export_parcels.py](<export_parcels.py>)只读取已完成的逐扇区CFR和统计，写入新的地块数据目录；原始路径不复制、不修改，来源目录必须保留。旧几何manifest没有内嵌地块时，会核对原始场景哈希后读取真实地块。

```sh
python scripts/CSI-generate/export_parcels.py \
  --source data/csi/smoke-source-informed-final/city \
  --output data/csi/parcel-export-new
```

实际1km地图61地块、29726UE；15803UE在地块内，13923UE在地块外。`parcels/`中包括61地块目录和一个outside-parcels目录；空地块也保留空数组与元数据。每个地块保存全部UE，不能把零占位的无效行当成可训练信道。

## 7. 性能与验证边界

本机M1 Pro/16GiB跑1km全量的已有smoke外推见[耗时估算](<本机1km耗时估算.md>)：当前只能判断数天到数周量级，建议按1–3周预留，不是实测承诺。地块分组只改变保存方式，不减少18扇区×29726UE的RT工作量。

此前多GPU常驻进程/静态场景缓存、有界异步写、压缩选择、CPU亲和性、流式关联、磁盘预检均保留，详见[服务器说明](<vipa-106加速说明.md>)。其硬件检查仍有效，但该文中的旧物理默认以本README为准。输出盘仍需预算：4km仅全扇区CFR约1.45TiB，原始路径额外占用。没有自动续跑、自动容量自适应或GPU最快配置认证。

当前71项CPU合成/mock/拓扑/来源/地块/RT可视化接口测试通过。本机 Sionna RT2.2.0/Mitsuba3.9.1/Metal 已完成实际小规模RT：

- 10/20m自由空间Friis幅度、时延及载波相位公式检查通过。
- 完整1km几何、8UE×2扇区、每批2UE、深度7、2000 samples/source、容量20000，绕射与漫散射开启，透射/自由边缘关闭。
- 端到端生成4个有效反馈样本；其余4UE只是本次低预算未找到路径。
- 同路径物理CFR与Sionna原生CFR对照通过；这不是搜索收敛或全城覆盖验证。

结果汇总见[真实smoke摘要](<../../data/csi/smoke-source-informed-final/smoke-summary.json>)。本次没有跑全城，没有改服务器环境；仍有Sionna一次绕射/无散射-绕射混合路径、薄板透射近似、植被缺失、synthetic-array近场假设、地形细片/材料参考频率等边界。
