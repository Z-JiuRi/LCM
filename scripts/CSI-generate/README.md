# 城市静态CSI反馈数据生成

日期：2026-10-26。项目脚本，不是DeepMIMO官方脚本。参考[官方 v4 源码](<../../reference/DeepMIMO-v4/>)；不宣称已完成端到端数值一致性验证。**本轮只运行合成路径/几何测试，没有跑全城RT。**

## 配置与流程

默认1km城市，5m室外网格、1.5m UE；当前部署6站/18扇区。每扇区1×32水平ULA，0.5波长阵元距、V极化；TX使用Sionna `tr38901` 阵元方向图和部署中实际方位角/10°下倾。这些是研究配置，不是运营商实测。

1. [city_geometry](<city_geometry.py>)读取正式环境城市场景，按每个面的材料键导出OBJ，保留源坐标与绕序。只省略世界z=0共面的建筑底面；不是三维水密/外法线认证。
2. 网格中心采样排除建筑/植被内部和缓冲，所有植被仍不参与传播。默认建筑净空2m、植被净空1m。
3. [generate_city_csi](<generate_city_csi.py>)每扇区一个spawn任务，RX按32个分批，每次固定 `samples_per_src=100000`，不乘除RX数量。默认2进程；共用GPU/统一内存可能限制加速，内存吃紧用1进程或更小chunk。
4. 每批保存完整天线分辨CIR、时延、有效路径mask、到达/出发角、交互类型和交互坐标，不先取前25条路径。保留实际求解参数、版本、哈希与随机seed。
5. 用路径系数解析合成CFR。默认 `--convention deepmimo`：N=1024、B=20MHz，bins=0,16,...,1008；偏移0..19.6875MHz，间隔312.5kHz，使用1/sqrt(1024)及tau>=N/B裁剪（原路径仍保留）。不是标准NR资源栅格，不是默认fftshift频点。
6. 按所有候选扇区的**天线平均逐径线性功率之和**选服务扇区；等发射功率44dBm时排序等价于路径增益最大。不是sum(abs(H))，也不是带负载/干扰/预编码的SINR关联。
7. 选首条在最强路径25dB以内的显著路径为tau_ref。乘exp(+j2pi*f*tau_ref)补偿公共频域时延斜率，逐UE做RMS归一化，实虚拆分，导出训练数据。保存tau_ref/RMS，能够还原选中频点的未归一化CFR；不能恢复未选频点或被裁剪路径。
8. 默认100m空间块按8:1:1分配（同块UE不跨集合），之后过滤无有效服务路径/零CFR。最终样本比例可能偏离8:1:1；未设隔离带，邻块信道仍可能相关。`--split-mode random`可匹配旧脚本随机UE划分，但有空间泄漏风险。

## 使用（根目录）

```sh
conda activate lcm
# 几何准备是CPU导出，不运行射线追踪。输出必须是新的目录。
python scripts/CSI-generate/city_geometry.py --spacing 5
# 默认新目录 data/csi/city-1km-geometry

# 只打印规模/配置，不初始化Sionna，不计算信道、不创建结果目录。
python scripts/CSI-generate/generate_city_csi.py --dry-run

# 如以后需要做真正的小测试：同时限制UE和扇区，不会只限扇区却跑全网格。
python scripts/CSI-generate/generate_city_csi.py --limit-ues 16 --limit-sectors 1 \
  --workers 1 --chunk 8 --samples-per-src 20000 \
  --output data/csi/feedback-smoke

# 全量命令仅提供给用户，本轮没有执行。
python scripts/CSI-generate/generate_city_csi.py --workers 2 --chunk 32 --samples-per-src 100000

# 全部轻量回归测试，不安装/导入Sionna，不运行RT。
python scripts/CSI-generate/test_city_csi.py
```

默认几何与输出路径由脚本位置解析，不依赖cwd；用户指定的相对参数路径按执行cwd解析。旧几何目录不能自动当作新适配已验证，建议用新几何导出目录；生成器核对manifest中已有哈希。拒绝覆盖已有结果目录；中途失败保留新目录和失败报告，以免旧成功结果被覆盖。

### 传播机制

默认LOS＋最多3次交互的镜面反射。按需显式开启：

```sh
python scripts/CSI-generate/generate_city_csi.py --diffraction --edge-diffraction --diffuse-reflection --dry-run
```

这只打印配置，去掉dry-run才会计算。Sionna支持绕射/漫散射；关掉不等于软件不支持。漫散射会产生大量路径、占用内存/磁盘，不能把任何小样本试验当作完整传播收敛证据。材料directive按alpha_r适配，none明确禁用漫散射；原参数和适配假设保存在几何manifest。道路材料标注1GHz参考但默认载频3.5GHz，需要进一步校准；植被电磁模型未实现。`--refraction`默认关闭，需要额外几何/材料验证。

### 两种频域约定

- `--convention deepmimo`：上述非负索引频点、1/sqrt(N)、N/B延迟窗，适合对齐已审查DeepMIMO生成方式。
- `--convention centered`：偏移[-10MHz,9.6875MHz]、不除sqrt(N)、不按N/B裁剪，类似Sionna未归一化CFR。两者不是同一幅度/相位基准，不能直接混训练。

这里使用的是Sionna已包含阵列/方向图的CIR系数，不再额外套DeepMIMO阵列响应；因此不是宣称与官方converter逐字节一致。

## 输出与最终维度

```text
report.json                   配置、输入哈希、状态、数量和限制
ue_positions.npy              [U,3]全部本次采样位置
source_ue_indices.npy          回指几何UE网格的索引
raw/sector-000/metadata.json   实际solver kwargs、版本、方位/下倾、逐批哈希
raw/sector-000/paths-*.npz     CIR [batch,1,32,P]及有效mask/延迟/角度/交互
raw/sector-000/csi.npy         [U,1,32,64] complex64，原始CFR
raw/sector-000/link_stats.npz  路径功率、首显著径、no_path_found和裁剪计数
serving_csi.npy                [U,1,32,64] complex64，服务扇区原始CFR
association.npz               扇区ID/索引、有效性、频点、尺度和split标签
train.npy / val.npy / test.npy [N_split,2,32,64] float32，实部/虚部
train_aux.npz 等               与每个训练数组行对齐的坐标、扇区、tau_ref、RMS
```

**单个训练样本为[2,32,64] float32，占16KiB。**N_split不是固定人口数，而是RT下有效并被分到该集合的采样位置数。全网无路径UE和选中CFR为零UE不混入压缩训练，但保留全部坐标和有效性记录。

原始系数/时延/交互mask仍完整保留，`no_path_found`只表示“本次配置没有找到路径”，不叫确定几何遮蔽。路径增益和CFR平均能量单独记录，不据此宣称接收功率dBm、SINR、吞吐率或全城覆盖已达标。

## 本轮验证

2026-10-27：[14项轻量测试](<test_city_csi.py>)全部通过（0.379秒）。包含频点、逐径叠加、N/B裁剪、零路径/零功率区分、显著径阈值、补偿/归一化逆变换、固定预算与物理开关、整块划分、功率关联、输出维度/sidecar对齐、dry-run不触发RT、混合面材料、凹面CDT和严格材料处理。另用假Sionna API执行实际worker/main控制流，检查2+1个RX分批预算不变、6D CIR抽取、逐批原始路径保存、完整训练导出及拒绝覆盖。**这不是物理RT验证**；真实城市几何适配和新生成器的端到端RT尚未重新验证。
